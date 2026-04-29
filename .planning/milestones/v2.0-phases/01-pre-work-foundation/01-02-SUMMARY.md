---
phase: "01"
plan: "02"
subsystem: "agent / safety-harness"
tags:
  - infrastructure
  - refactor
  - nl-agent
  - safety-harness
  - tdd
dependency_graph:
  requires:
    - "app/core/agent/nl_agent.py::run_agent (UNCHANGED)"
    - "app/services/sql_validator.py::validate_sql"
    - "app/services/sql_limiter.py::inject_limit"
  provides:
    - "app/core/agent/nl_service.py::NLResult"
    - "app/core/agent/nl_service.py::run_nl_query"
  affects:
    - "app/pages/ask.py (v1.0 Ask page — now delegates to nl_service)"
    - "app_v2/routers/ask.py (Phase 5 — will import run_nl_query directly)"
tech_stack:
  added: []
  patterns:
    - "NLResult discriminated dataclass (kind='ok'/'clarification_needed'/'failure')"
    - "Framework-agnostic orchestrator layer — no streamlit import in service module"
    - "TDD RED-GREEN cycle for INFRA-07 contract verification"
    - "Belt-and-braces SAFE-02 double-validation (tool path + post-agent path)"
key_files:
  created:
    - path: "app/core/agent/nl_service.py"
      description: "Framework-agnostic SAFE-02..06 harness entrypoint"
      exports: ["NLResult", "run_nl_query"]
      lines: 182
    - path: "tests/agent/test_nl_service.py"
      description: "6 contract tests for NLResult + run_nl_query"
  modified:
    - path: "app/pages/ask.py"
      description: "Refactored _run_agent_flow to delegate to nl_service.run_nl_query; removed inline harness"
      lines_before: 432
      lines_after: 406
      delta: "-26 net (removed ~57 lines of inline harness, added ~31 lines of NLResult dispatch)"
decisions:
  - "NLResult uses @dataclass with field(default_factory=list) for candidate_params — prevents shared mutable default across instances"
  - "Test file uses concrete _StubDB(DBAdapter) subclass instead of MagicMock — AgentDeps Pydantic model enforces is_instance of DBAdapter at construction time"
  - "run_nl_query engine_fn path mirrors _execute_read_only pattern exactly — same SET SESSION / max_execution_time / pd.read_sql_query idiom, different return type (DataFrame vs text)"
  - "regenerate=False parameter is reserved/no-op in this plan — Phase 5 (ASK-V2-03) will wire cache-bypass behavior without changing the public signature"
  - "ask.py retains unused imports (AgentRunFailure, ClarificationNeeded, SQLResult, run_agent) — they are still used in _render_banners type annotation and could be needed by future callers; removal is a nice-to-have"
metrics:
  duration: "12 minutes"
  completed_date: "2026-04-24T17:00:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
  files_created: 2
  tests_before: 177
  tests_after: 183
  tests_added: 6
---

# Phase 01 Plan 02: nl_service.py Safety Harness Extraction Summary

**One-liner:** Extracted the SAFE-02..06 post-agent SQL orchestration from ask.py into a new framework-agnostic `nl_service.py` with a single `run_nl_query() -> NLResult` entrypoint — zero regressions across all 183 tests.

## What Was Built

### Task 1 — app/core/agent/nl_service.py (TDD GREEN)

New module at `app/core/agent/nl_service.py` (182 lines).

**NLResult dataclass:**

```python
@dataclass
class NLResult:
    kind: Literal["ok", "clarification_needed", "failure"]
    # kind == "ok"
    sql: str = ""
    df: Optional[pd.DataFrame] = None
    summary: str = ""
    # kind == "clarification_needed"
    message: str = ""
    candidate_params: list[str] = field(default_factory=list)
    # kind == "failure"
    failure: Optional[AgentRunFailure] = None
```

Key design detail: `candidate_params` uses `field(default_factory=list)` — not `= []`. This prevents the classic Python mutable-default bug where two NLResult instances share the same list object (verified by Test 6).

**run_nl_query signature:**

```python
def run_nl_query(
    question: str,
    agent,               # pydantic_ai.Agent — type omitted to avoid import cycle
    deps: AgentDeps,
    *,
    regenerate: bool = False,   # Reserved for Phase 5 ASK-V2-03
) -> NLResult:
```

**Responsibility split (do not confuse):**

| Component | Responsibility |
|---|---|
| `nl_agent.run_sql` TOOL (unchanged) | SAFE-02 validate (pre-exec), SAFE-03 limit-inject, SAFE-06 scrub_paths (OpenAI), SAFE-05 `<db_data>` wrap → returns text rows to LLM |
| `nl_service.run_nl_query` (new) | SAFE-04 step-cap via run_agent UsageLimits; post-agent SQLResult SAFE-02 re-validate, SAFE-03 re-inject; READ ONLY session + max_execution_time; DataFrame fetch for UI display |

**Three outcome branches:**

1. `kind="failure"` — AgentRunFailure from run_agent (step-cap, timeout, llm-error) OR SAFE-02 second-pass rejection (reason="llm-error", detail="SQL rejected: ...")
2. `kind="clarification_needed"` — ClarificationNeeded with message + candidate_params copied
3. `kind="ok"` — LIMIT-injected safe_sql, fresh DataFrame from DB, agent explanation as summary

**New test file: `tests/agent/test_nl_service.py`** (6 tests)

| Test | Assertion |
|---|---|
| `test_step_cap_returns_failure` | UsageLimitExceeded → kind="failure", reason="step-cap" |
| `test_clarification_branch` | ClarificationNeeded → kind="clarification_needed", message+candidate_params preserved |
| `test_ok_branch_fetches_dataframe` | SQLResult → kind="ok", LIMIT in sql, df equals fake_df |
| `test_ok_branch_rejected_by_validator` | Disallowed table → kind="failure", reason="llm-error", "rejected" in detail |
| `test_nl_service_importable_without_streamlit` | subprocess import exits 0 — framework-agnostic |
| `test_nl_result_candidate_params_not_shared` | Two NLResult instances have independent candidate_params lists |

### Task 2 — app/pages/ask.py refactor

**Lines changed:** `_run_agent_flow` reduced from ~100 lines to ~70 lines (net file delta: -26 lines, 432 → 406).

**What moved OUT of ask.py into nl_service:**
- `from app.core.agent.nl_agent import _execute_read_only` (internal reuse import removed)
- `from app.services.sql_limiter import inject_limit` (local import removed)
- `from app.services.sql_validator import validate_sql` (local import removed)
- `validate_sql(output.query, cfg.allowed_tables)` call + rejection path
- `inject_limit(output.query, cfg.row_cap)` call
- `SET SESSION TRANSACTION READ ONLY` execution
- `SET SESSION max_execution_time={timeout_ms}` execution
- `pd.read_sql_query(sa.text(safe_sql), conn)` DataFrame fetch
- `isinstance(output, AgentRunFailure)` / `isinstance(output, ClarificationNeeded)` branching

**What stayed in ask.py (UI concerns):**
- `st.session_state` reads/writes
- `with st.spinner("Thinking..."):`
- `_append_history(...)` calls
- `_render_banners`, `_render_history`, `_render_answer_zone`, `_render_param_confirmation`
- Agent + deps construction (reads active_llm/active_db from session_state)
- `_run_confirmed_agent_flow` — unchanged (delegates to `_run_agent_flow`)

**New _run_agent_flow body (key section):**

```python
with st.spinner("Thinking..."):
    nl_result: NLResult = run_nl_query(question, agent, deps)

if nl_result.kind == "failure":
    st.session_state["ask.last_abort"] = nl_result.failure
    st.session_state["ask.last_df"] = None
    st.session_state["ask.last_summary"] = ""
    st.session_state["ask.last_sql"] = nl_result.failure.last_sql if nl_result.failure else ""
    _append_history(question, nl_result.failure.last_sql if nl_result.failure else "", 0, "failed")
    return

st.session_state["ask.last_abort"] = None

if nl_result.kind == "clarification_needed":
    st.session_state["ask.pending_params"] = list(nl_result.candidate_params)
    st.session_state["ask.pending_message"] = nl_result.message
    st.session_state["ask.confirmed_params"] = []
    return

assert nl_result.kind == "ok"
st.session_state["ask.last_sql"] = nl_result.sql
st.session_state["ask.last_df"] = nl_result.df
st.session_state["ask.last_summary"] = nl_result.summary
_append_history(question, nl_result.sql, len(nl_result.df) if nl_result.df is not None else 0, "ok")
```

**Session-state keys preserved (for Phase 5 planners):**

| Key | Populated by | Branch |
|---|---|---|
| `ask.last_abort` | `nl_result.failure` or `None` | failure / non-failure |
| `ask.last_df` | `nl_result.df` or `None` | ok / failure |
| `ask.last_sql` | `nl_result.sql` or `nl_result.failure.last_sql` | ok / failure |
| `ask.last_summary` | `nl_result.summary` or `""` | ok / failure |
| `ask.pending_params` | `list(nl_result.candidate_params)` | clarification_needed |
| `ask.pending_message` | `nl_result.message` | clarification_needed |

## Test Results

```
183 passed, 1 warning in 44.78s
```

- Pre-existing v1.0 tests: 171 (unchanged — zero regressions)
- New nl_service contract tests (this plan): 6
- Total from plan 01-01: 177 (unchanged)
- Total after this plan: 183

Regression bars verified:
- `tests/pages/test_ask_page.py`: 10/10 passed unchanged
- `tests/agent/test_nl_agent.py`: 10/10 passed unchanged

## Commits

| Hash | Type | Description |
|---|---|---|
| `233a2fd` | test | Add failing tests for nl_service orchestrator (INFRA-07 TDD RED) |
| `5319d87` | feat | Create nl_service.py with NLResult + run_nl_query() (INFRA-07 TDD GREEN) |
| `c4a7399` | feat | Refactor ask.py _run_agent_flow to delegate to nl_service (INFRA-07) |

## Deviations from Plan

**1. [Rule 1 - Bug] Test helper used concrete _StubDB instead of MagicMock**
- **Found during:** Task 1 GREEN (test execution)
- **Issue:** `AgentDeps` is a Pydantic BaseModel with `arbitrary_types_allowed=True` but still enforces `is_instance_of(DBAdapter)` at construction time. Passing `MagicMock()` (which is not a `DBAdapter` subclass) raises `ValidationError`.
- **Fix:** Added `_StubDB(DBAdapter)` concrete stub class to the test file — minimal implementation of all abstract methods, with `_engine_mock = MagicMock()` as the backing engine.
- **Files modified:** `tests/agent/test_nl_service.py`
- **Commit:** `5319d87`

No other deviations — plan executed as written.

## Known Stubs

None — this plan adds no UI-facing data paths. The `regenerate=False` parameter is documented as reserved/no-op and is not a stub (it's a forward-compatibility hook per plan spec).

## Threat Flags

No new security surface introduced. The refactor is an extraction, not an addition:
- No new network endpoints
- No new auth paths
- No new file I/O
- No schema changes
- SAFE-02 second-pass validate_sql is PRESERVED in nl_service.run_nl_query (T-02-01)
- SAFE-03 inject_limit double-application preserved (T-02-02)
- SET SESSION TRANSACTION READ ONLY preserved in nl_service DataFrame-fetch path (T-02-03)

## Self-Check: PASSED

| Check | Result |
|---|---|
| `app/core/agent/nl_service.py` exists | FOUND |
| `tests/agent/test_nl_service.py` exists | FOUND |
| `01-02-SUMMARY.md` exists | FOUND |
| Commit 233a2fd (TDD RED) | FOUND |
| Commit 5319d87 (TDD GREEN) | FOUND |
| Commit c4a7399 (ask.py refactor) | FOUND |
| `from app.core.agent.nl_service import NLResult, run_nl_query` in ask.py | YES (1 match) |
| `validate_sql(` in ask.py | 0 matches |
| `inject_limit(` in ask.py | 0 matches |
| `SET SESSION TRANSACTION READ ONLY` in ask.py | 0 matches |
| `max_execution_time` in ask.py | 0 matches |
| `^import streamlit` in nl_service.py | 0 matches |
| `python3 -c "from app.core.agent.nl_service import run_nl_query, NLResult"` | exits 0 |
| pytest total | 183 passed, 0 failed |
| tests/pages/test_ask_page.py | 10 passed |
| tests/agent/test_nl_agent.py | 10 passed |
| tests/agent/test_nl_service.py | 6 passed |
