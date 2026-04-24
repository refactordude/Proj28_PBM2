---
phase: "02-nl-agent-layer"
plan: "03"
subsystem: nl-agent-core
tags: [pydantic-ai, agent, run_sql, NL-06, SAFE-04, SAFE-05, SAFE-06, tdd]
dependency_graph:
  requires: [02-01, 02-02]
  provides:
    - app.core.agent.nl_agent.build_agent
    - app.core.agent.nl_agent.run_agent
    - app.core.agent.nl_agent.SQLResult
    - app.core.agent.nl_agent.ClarificationNeeded
    - app.core.agent.nl_agent.AgentDeps
    - app.core.agent.nl_agent.AgentRunFailure
  affects:
    - app/pages/ask.py (Plan 02-04 calls run_agent and imports result types)
    - app/pages/ask.py (Plan 02-04 wraps build_agent in @st.cache_resource)
tech_stack:
  added: []
  patterns:
    - PydanticAI Agent with Union output_type (SQLResult | ClarificationNeeded)
    - RunContext[AgentDeps] for tool dependency injection
    - UsageLimits(tool_calls_limit=max_steps) passed to agent.run_sync()
    - SET SESSION TRANSACTION READ ONLY + SET SESSION max_execution_time in _execute_read_only
    - TestModel(custom_output_args={...}) for scripted SQLResult in tests
    - FunctionModel for scripted ClarificationNeeded and step-cap loop scenarios
    - RunContext(deps=..., model=TestModel(), usage=RunUsage()) for direct tool invocation in tests
key_files:
  created:
    - app/core/agent/nl_agent.py
    - tests/agent/__init__.py
    - tests/agent/test_nl_agent.py
  modified: []
decisions:
  - "TestModel introspection uses agent._function_toolset.output_schema.toolset._tool_defs to find output tool names — PydanticAI 1.86 internal structure; documented in test as version-sensitive"
  - "FunctionModel used for ClarificationNeeded tests because TestModel.custom_output_args always targets the first union member (SQLResult); FunctionModel can select 'final_result_ClarificationNeeded' tool by name"
  - "build_agent() is cache-free — @st.cache_resource wrapping deferred to Plan 02-04 (ask.py) so tests can construct fresh agents without Streamlit cache interference"
  - "run_sql tool catches all DB exceptions internally and returns 'SQL execution error: ...' string — prevents stack traces leaking to LLM context or AgentRunFailure.detail"
  - "_execute_read_only falls back to db.run_query(sql) when db._get_engine is absent — supports public DBAdapter ABC surface without requiring _get_engine on all subclasses"
  - "System prompt is English per RESEARCH Open Question 4 — English produces better SQL across both OpenAI and Ollama backends"
metrics:
  duration: "9 minutes"
  completed_date: "2026-04-24"
  tasks_completed: 2
  files_changed: 3
requirements_satisfied: [NL-06, SAFE-04, SAFE-05]
---

# Phase 2 Plan 03: PydanticAI Agent Core Summary

**One-liner:** PydanticAI Agent with `output_type=SQLResult | ClarificationNeeded`, one `run_sql` tool composing all four safety primitives, and a `run_agent()` runner that enforces SAFE-04 step-cap and translates all PydanticAI exceptions to `AgentRunFailure`.

## What Was Built

### Public API

```python
# app/core/agent/nl_agent.py — the brain of the NL layer
from app.core.agent.nl_agent import (
    build_agent,       # (model) -> Agent — factory, cache-free
    run_agent,         # (agent, question, deps) -> SQLResult | ClarificationNeeded | AgentRunFailure
    SQLResult,         # BaseModel: query, explanation
    ClarificationNeeded,  # BaseModel: message, candidate_params
    AgentDeps,         # BaseModel: db, agent_cfg, active_llm_type
    AgentRunFailure,   # BaseModel: reason, last_sql, detail
)
```

**Caller contract (enforced by design):**
- Callers MUST NOT import `pydantic_ai` directly — all framework exceptions are translated to `AgentRunFailure` by `run_agent()`.
- `build_agent()` MUST be wrapped in `@st.cache_resource` by the caller (Plan 02-04 / `ask.py`) — `nl_agent.py` contains no Streamlit import.

### Module Details

**`app/core/agent/nl_agent.py` (208 lines)**

**Result types:**
- `SQLResult(query, explanation)` — both required fields with `Field(description=...)` for PydanticAI JSON schema
- `ClarificationNeeded(message, candidate_params)` — `candidate_params` defaults to empty list
- `AgentDeps(db, agent_cfg, active_llm_type)` — `ConfigDict(arbitrary_types_allowed=True)` for DBAdapter
- `AgentRunFailure(reason, last_sql, detail)` — `reason` is Literal["step-cap", "timeout", "llm-error"]

**`_execute_read_only(db, sql, timeout_s)`:**
- Detects `_get_engine` on the adapter; falls back to `db.run_query(sql)` if absent
- Issues `SET SESSION TRANSACTION READ ONLY` and `SET SESSION max_execution_time={ms}` — both wrapped in try/except (non-fatal; MySQL 5.7.8+ only for timeout, per Pitfall 8)
- Returns pipe-delimited text: `"col1 | col2\nval1 | val2"` or `"(no rows returned)"`

**`run_sql` tool (inside `build_agent()`):**
1. `validate_sql(sql, allowed_tables)` — rejects if not valid
2. `inject_limit(sql, row_cap)` — idempotent LIMIT injection
3. `_execute_read_only(db, sql, timeout_s)` — read-only DB fetch
4. `scrub_paths(rows_text)` — only when `active_llm_type == "openai"` (SAFE-06)
5. Returns `f"<db_data>\n{rows_text}\n</db_data>"` (SAFE-05)

**`run_agent(agent, question, deps)`:**
- Passes `usage_limits=UsageLimits(tool_calls_limit=deps.agent_cfg.max_steps)` to `agent.run_sync()` (SAFE-04)
- Catches `UsageLimitExceeded` → `AgentRunFailure(reason="step-cap")`
- Catches any exception with "timeout"/"max_execution_time"/"execution time" in message → `AgentRunFailure(reason="timeout")`
- Catches all other exceptions → `AgentRunFailure(reason="llm-error")`

**System prompt (NL-06 + SAFE-05):**
- English prose per RESEARCH Open Question 4
- Contains all three question shapes: Lookup one platform, Compare across platforms, Filter platforms by value
- `CRITICAL SECURITY INSTRUCTION` block explicitly marks `<db_data>` content as untrusted raw data, never instructions (SAFE-05 prompt injection defense)
- States only `ufs_data` table is queryable

### Test Coverage

**`tests/agent/test_nl_agent.py` (325 lines, 10 tests)**

| Test | What it verifies |
|------|-----------------|
| `test_build_agent_registers_run_sql_tool` | Exactly one tool named 'run_sql' in `_function_toolset.tools` |
| `test_build_agent_has_union_output_type` | Both SQLResult and ClarificationNeeded in output tools via `output_schema.toolset._tool_defs` |
| `test_run_agent_returns_sql_result_for_lookup_question` | TestModel with `custom_output_args` returns `SQLResult` with `query.startswith("SELECT")` |
| `test_run_agent_returns_clarification_needed_when_scripted` | FunctionModel returning `final_result_ClarificationNeeded` produces `ClarificationNeeded` |
| `test_run_agent_catches_usage_limit_exceeded` | FunctionModel looping on run_sql + `max_steps=1` → `AgentRunFailure(reason="step-cap")` |
| `test_run_sql_wraps_result_in_db_data_tags` | Direct RunContext invocation; result starts with `<db_data>` ends with `</db_data>` |
| `test_run_sql_rejects_disallowed_table` | `SELECT * FROM other_table` returns `"SQL rejected: ..."` |
| `test_run_sql_scrubs_paths_for_openai_only` | P1 row has `/sys/kernel/foo`; openai result has `<path>`, ollama result has `/sys/kernel/foo` |
| `test_run_agent_translates_generic_error_to_llm_error` | FunctionModel raising RuntimeError → `AgentRunFailure(reason="llm-error")` |
| `test_run_sql_injects_limit` | `row_cap=1` on 2-row SQLite fixture returns exactly 1 data row |

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written. The only adaptation was in test introspection:

**1. [Rule 1 - Bug] Agent output tool introspection path corrected**
- **Found during:** Task 2 (test_build_agent_has_union_output_type) — first run failed
- **Issue:** Plan specified `agent._function_tools` (dict) but PydanticAI 1.86 stores function tools under `agent._function_toolset.tools` (dict) and output tools under `agent._function_toolset.output_schema.toolset._tool_defs` (list)
- **Fix:** Updated test to use the correct attribute path — documented as version-sensitive in the test docstring
- **Files modified:** `tests/agent/test_nl_agent.py`
- **Commit:** 7362477 (single GREEN commit included the fix)

## Known Stubs

None — all functionality is fully implemented. `run_agent` returns real `AgentOutput | AgentRunFailure`. No placeholder values or hardcoded empty returns flow to callers.

## Threat Flags

No new security surface beyond the plan's threat model:

| Flag | File | Description |
|------|------|-------------|
| None | — | All trust boundaries (LLM output, tool arg, DB rows, exceptions) are handled as specified in the plan's STRIDE register |

All T-02-03-01 through T-02-03-09 mitigations are implemented:
- T-02-03-01/02: `<db_data>` wrapper + CRITICAL SECURITY INSTRUCTION in system prompt
- T-02-03-03: `validate_sql` rejects non-SELECT before execution
- T-02-03-04: `UsageLimits(tool_calls_limit=max_steps)` enforced
- T-02-03-05: `SET SESSION max_execution_time` with non-fatal fallback
- T-02-03-06: `scrub_paths` conditional on `active_llm_type == "openai"`
- T-02-03-07: `AgentRunFailure.detail` contains exception text only, never credentials
- T-02-03-08: Inherited from 02-02 `validate_sql` subquery token walk
- T-02-03-09: No caching at tool level — accepted risk

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| abc3340 | feat | NL agent factory, result types, run_sql tool, run_agent runner |
| 7362477 | test | nl_agent tests with TestModel and FunctionModel (10 tests) |

## Self-Check: PASSED
