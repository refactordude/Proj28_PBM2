---
phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
plan: 02
subsystem: agent
tags: [pydantic-ai, agent-tools, sql-harness, chat-agent, safe-02-06]

# Dependency graph
requires:
  - phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
    plan: 01
    provides: AgentConfig.chat_max_steps field — the per-turn step budget consumed by plan 03's stream_chat_turn loop wrapper (this plan's tools and harness do not read it directly)
provides:
  - ChartSpec Pydantic model (chart_type Literal['bar','line','scatter','none']) for D-CHAT-06
  - PresentResult Pydantic model (summary + sql + chart_spec) — the chat agent's output_type, ends a turn per D-CHAT-05
  - ChatAgentDeps Pydantic model — db + agent_cfg + active_llm_type threading for D-CHAT-11 path-scrub gate
  - build_chat_agent(model) factory registering 6 @agent.tool decorators (inspect_schema, get_distinct_values, count_rows, sample_rows, run_sql, present_result)
  - _execute_and_wrap module-private harness — verbatim port of SAFE-02..06 from nl_agent.run_sql with rejection prefix "REJECTED:" per D-CHAT-02
affects: [03-03-chat-loop, 03-04-routes, 03-05-templates, 03-06-cleanup]

# Tech tracking
tech-stack:
  added: []  # No new deps — all imports (pydantic_ai, pandas, sqlalchemy, app.services.*) already in tree from plan 03-01 and v1.0
  patterns:
    - "Parallel-agent pattern: build_chat_agent factory mirrors nl_agent.build_agent shape (model→Agent[Deps,Output] via output_type + deps_type) but emits PresentResult instead of SQLResult|ClarificationNeeded"
    - "Module-private harness helper (_execute_and_wrap) shared across 5 SQL-emitting tools — bug-fix locality and prevents 5x divergence on SAFE-02..06 invariants"
    - "Whitelist-by-tool: get_distinct_values whitelists ufs_data's 4 columns at the tool level so a malformed column name returns a tool-level REJECTED: string before _execute_and_wrap is reached (defense in depth on top of validate_sql's table-level check)"

key-files:
  created:
    - app/core/agent/chat_agent.py
  modified: []

key-decisions:
  - "Module-private _execute_and_wrap (single underscore prefix) — exposed for unit tests via the underscore name but excluded from __all__; tests import explicitly so a future refactor can rename it without breaking the public surface"
  - "Verbatim port of SAFE-02..06 from nl_agent.run_sql (NOT a reuse via shared helper) — preserves D-CHAT-09's promise that nl_agent.py is unchanged. Cost: two harness implementations to keep in sync. Benefit: zero risk of regressing the existing 10-test test_nl_agent.py suite or the SAFE-02..06 invariant scans"
  - "DBAdapter ABC (not Protocol) — the existing app/adapters/db/base.py exports DBAdapter as an ABC. ChatAgentDeps.db: DBAdapter happily accepts any subclass; arbitrary_types_allowed=True on the Pydantic config keeps Pydantic from trying to introspect the ABC's abstract methods"
  - "Tool surface count: 6 decorated tools + 1 module-level harness helper. grep '@agent.tool' returns 7 in chat_agent.py because line 123's docstring mentions '@agent.tool decorators' verbatim — actual decorators = 6"
  - "Path scrub policy from D-CHAT-11: applied to TOOL RESULTS in _execute_and_wrap when active_llm_type=='openai'. The 'apply to BOTH tool args and results' default from CONTEXT.md Claude's Discretion is satisfied at the tool-RESULT boundary here; the tool-ARG boundary fires when plan 03 walks message_history via _scrub_messages_inplace before replay (RESEARCH Gap 7)"
  - "REJECTED: prefix replaces SQL rejected: at the chat-tier boundary only — nl_agent.run_sql still emits 'SQL rejected:' for backward compat with the existing single-turn flow. The two prefixes coexist; tests for each path assert their respective prefix"

requirements-completed: [D-CHAT-05, D-CHAT-06, D-CHAT-11]

# Metrics
duration: ~5min
completed: 2026-05-02
---

# Phase 03 Plan 02: Chat Agent Module — Schemas, Factory, 6 Tools, SAFE-02..06 Harness

**Multi-step PydanticAI chat agent factory at `app/core/agent/chat_agent.py`: Pydantic schemas (ChartSpec, PresentResult, ChatAgentDeps), build_chat_agent factory, all 6 tools (inspect_schema, get_distinct_values, count_rows, sample_rows, run_sql, present_result), and `_execute_and_wrap` — the verbatim port of nl_agent.run_sql's SAFE-02..06 harness with the rejection prefix flipped to "REJECTED:" per D-CHAT-02.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-02T18:18:21Z
- **Completed:** 2026-05-02T18:23:07Z
- **Tasks:** 2 / 2
- **Files modified:** 0
- **Files created:** 1
- **Tests:** 464 passed, 5 skipped (no regressions vs plan 03-01's baseline)

## Accomplishments

- Created `app/core/agent/chat_agent.py` (278 lines) parallel to `nl_agent.py` — does not modify or import the legacy module, honoring D-CHAT-09's preservation contract.
- **D-CHAT-06 ChartSpec** with `chart_type: Literal["bar", "line", "scatter", "none"]` literal exact (byte-pinned for plan 03-04 invariant grep) + x_column / y_column / color_column string fields.
- **D-CHAT-05 PresentResult** with `summary` + `sql` + `chart_spec`. The agent's `output_type` is PresentResult so calling `present_result` ENDS the turn (PydanticAI recognizes the structured-output tool).
- **D-CHAT-11 ChatAgentDeps** carries `db` + `agent_cfg` + `active_llm_type: Literal["openai", "ollama"]`; threaded into every tool call via `RunContext[ChatAgentDeps]`.
- **`_CHAT_SYSTEM_PROMPT`** (33 lines) describes the 6 tools verbatim, includes the SM8850 vs SM8650 motivating example with explicit "UNION is rejected by the guard" and "two separate SELECT … WHERE PLATFORM_ID='…' queries" guidance, and reinforces the `<db_data>...</db_data>` CRITICAL SECURITY rule against prompt injection.
- **6 tools** registered as `@agent.tool` decorators inside `build_chat_agent`:
  - `inspect_schema` — static column list, cheap
  - `get_distinct_values(column)` — whitelisted to ufs_data's 4 columns; tool-level REJECTED for invalid columns
  - `count_rows(where_clause)` — `SELECT COUNT(*) FROM ufs_data WHERE …` pre-flight
  - `sample_rows(where_clause, limit)` — `limit` clamped into [1, agent_cfg.row_cap]
  - `run_sql(sql)` — agent's primary tool; passes through `_execute_and_wrap`
  - `present_result(summary, sql, chart_spec)` — returns the PresentResult Pydantic model; ends the turn
- **`_execute_and_wrap`** module-private helper (66 lines) — the verbatim SAFE-02..06 harness:
  - SAFE-02: `validate_sql(sql, cfg.allowed_tables)` (single SELECT, no UNION/CTE/comments, allowed tables)
  - SAFE-03: `inject_limit(sql, cfg.row_cap)` (row cap)
  - SAFE-04: `SET SESSION TRANSACTION READ ONLY`
  - SAFE-04b: `SET SESSION max_execution_time={timeout_s * 1000}` (ms)
  - SAFE-06: `scrub_paths(rows_text)` only when `active_llm_type == "openai"` (D-CHAT-11)
  - SAFE-05: `<db_data>\n{rows_text}\n</db_data>` wrapping
  - **Rejection prefix:** `f"REJECTED: {vr.reason}"` (was `"SQL rejected:"` in nl_agent.run_sql) per D-CHAT-02 so plan 03's loop wrapper can `result.startswith("REJECTED:")` to count rejections.
- **Motivating example verified at unit level:** `SELECT 1 UNION SELECT 2` → `"REJECTED: UNION / INTERSECT / EXCEPT are not allowed"` (D-CHAT-02 contract honored).

## Task Commits

Each task was committed atomically:

1. **Task 1: chat_agent.py shell — Pydantic schemas + factory** — `dd62206` (feat)
2. **Task 2: register 6 chat tools + _execute_and_wrap SAFE-02..06 harness** — `f03ffa1` (feat)

## Files Created/Modified

### Created
- `app/core/agent/chat_agent.py` (278 lines) — module exporting ChartSpec, PresentResult, ChatAgentDeps, build_chat_agent; module-private _execute_and_wrap helper.

### Modified
None — D-CHAT-09 preservation honored: `nl_agent.py`, `nl_service.py`, `pydantic_model.py` all unchanged. Confirmed via `git diff --stat HEAD~2 HEAD -- app/core/agent/nl_agent.py app/core/agent/nl_service.py` returning empty diff.

## Decisions Made

1. **Verbatim port over shared helper.** Two implementations of SAFE-02..06 exist now (nl_agent.run_sql + chat_agent._execute_and_wrap). The alternative — extracting a shared helper into a third module both could call — would have required modifying `nl_agent.py`, violating D-CHAT-09's "preserved unchanged" promise. Cost is the maintenance overhead of keeping two harnesses in sync; benefit is zero risk of regressing the existing 10-test test_nl_agent.py suite while wiring up the new contract.
2. **Module-private _execute_and_wrap (single underscore prefix).** Excluded from `__all__` but importable via the underscore name. Tests assert on it directly (the Task 2 acceptance criterion's REJECTED-prefix assertion runs at the unit level on this helper). A future refactor can rename it without affecting the four public exports.
3. **No `pytest tests/ -x` re-test loop after each task.** Task 1's tests already passed cleanly; Task 2 only added new code (no edits to public surface, no edits to other modules). The full v2 + agent suite ran once at the end of Task 2: **464 passed, 5 skipped**, identical to plan 03-01's baseline.
4. **Tool surface = 6 decorated + 1 helper.** RESEARCH Code Examples A specified all 6; the plan duplicated the spec verbatim; my implementation matches both. The 7th `@agent.tool` grep hit on line 123 is in a docstring — not a real decorator.
5. **DBAdapter is ABC, not Protocol.** The plan's `<interfaces>` block called it a Protocol; the actual `app/adapters/db/base.py` defines it as `class DBAdapter(ABC)`. Pydantic + `arbitrary_types_allowed=True` accepts the ABC fine. No deviation from the plan's intent — just a documentation correction the plan can absorb.

## Deviations from Plan

None — plan executed exactly as written. All 11 acceptance criteria from Task 1 + 11 from Task 2 passed on first attempt:

- File exists, ≥ 50 lines (actual: 278)
- 4 public exports + 1 helper present
- Exact ChartSpec Literal byte-pinned: `chart_type: Literal["bar", "line", "scatter", "none"]`
- Exact factory wiring: `output_type=PresentResult`, `deps_type=ChatAgentDeps`
- Imports `validate_sql`, `inject_limit`, `scrub_paths` from `app.services.*` directly (RESEARCH Gap 8 — no `app.core.agent.nl_service` import)
- No banned strings: `langchain`, `litellm`, `vanna`, `llama_index` all absent
- System prompt mentions: `ufs_data`, `present_result`, `<db_data>`, UNION rejection / two separate SELECTs
- 6 `@agent.tool` decorated functions (the `grep -c` returns 7 due to a docstring mention; visual inspection confirms 6)
- `_execute_and_wrap` module-private helper present
- `f"REJECTED: {vr.reason}"` literal byte-pinned (D-CHAT-02 prefix contract)
- `ctx.deps.active_llm_type == "openai"` literal byte-pinned (D-CHAT-11 path-scrub gate)
- `<db_data>`, `SET SESSION TRANSACTION READ ONLY`, `SET SESSION max_execution_time` all present (SAFE-04, SAFE-04b, SAFE-05 preserved)
- `__all__ = ["ChartSpec", "PresentResult", "ChatAgentDeps", "build_chat_agent"]` exact
- `python -c` import + TestModel construct exits 0
- Unit-level REJECTED prefix assertion on `_execute_and_wrap` exits 0
- Full v2 + agent suite green: 464 passed, 5 skipped

## Issues Encountered

None.

## User Setup Required

None — module is purely additive code with no runtime effect until plan 03 imports `build_chat_agent` and plan 04 routes the new endpoints. Existing Ask page (v2.0 Phase 6 surface) continues rendering unchanged because nothing imports `chat_agent` yet.

## Verification Performed

Each task ran its `<verify>` block plus the plan's `<verification>` block:

- Task 1 verify: `python -c "from app.core.agent.chat_agent import ChartSpec, PresentResult, ChatAgentDeps, build_chat_agent; cs = ChartSpec(); assert cs.chart_type == 'none'; pr = PresentResult(summary='x', sql='SELECT 1'); assert pr.chart_spec.chart_type == 'none'; print('OK')"` → OK
- Task 2 verify: `python -c "from app.core.agent.chat_agent import build_chat_agent, ..., _execute_and_wrap; from pydantic_ai.models.test import TestModel; agent = build_chat_agent(TestModel()); assert callable(_execute_and_wrap)"` → `build_chat_agent constructed with Agent`
- Motivating example unit assertion: `_execute_and_wrap(ctx, 'SELECT 1 UNION SELECT 2')` → `"REJECTED: UNION / INTERSECT / EXCEPT are not allowed"` (starts with "REJECTED:")
- Full test suite: `pytest tests/agent/ tests/v2/ -x -q` → **464 passed, 5 skipped, 5 warnings** (zero regressions; baseline = 464/5 from plan 03-01)
- D-CHAT-09 preservation check: `git diff --stat HEAD~2 HEAD -- app/core/agent/nl_agent.py app/core/agent/nl_service.py` → empty diff (no changes to either preserved module)

## Threat Surface Audit

Per the plan's `<threat_model>`:

- **T-03-02-01 (Tampering, LLM-generated SQL via run_sql):** mitigated. PRIMARY backstop = read-only DB user (CLAUDE.md project rule). SECONDARY = `validate_sql` rejecting UNION/CTE/comments/non-SELECT/multi-statement; `inject_limit` capping rows; `SET SESSION TRANSACTION READ ONLY` defense-in-depth. Verbatim port from nl_agent.run_sql; existing test_nl_agent invariant tests confirm the harness.
- **T-03-02-02 (Tampering, where_clause in count_rows / sample_rows):** mitigated. The full assembled SELECT — `SELECT COUNT(*) FROM ufs_data WHERE {where_clause}` and `SELECT * FROM ufs_data WHERE {where_clause} LIMIT N` — passes through `validate_sql` in `_execute_and_wrap`, so a malicious `where_clause` containing `UNION SELECT …` or `; DROP TABLE` is rejected with `"REJECTED: UNION / INTERSECT / EXCEPT are not allowed"` or `"REJECTED: Only a single SELECT statement is allowed"`. Verified at unit level — same backstop as run_sql.
- **T-03-02-03 (Information Disclosure, /sys/* /proc/* /dev/* paths to OpenAI):** mitigated. `scrub_paths(rows_text)` runs in `_execute_and_wrap` exactly when `ctx.deps.active_llm_type == "openai"`. Verbatim port of SAFE-06; D-CHAT-11 carries the policy forward. Plan 03's session-store layer extends the same scrub to `message_history` arg replay (RESEARCH Gap 7) — that is the "apply to BOTH" half of CONTEXT.md Claude's Discretion.
- **T-03-02-04 (Information Disclosure, prompt-injection via tool result text):** mitigated. The `<db_data>...</db_data>` wrapper marks raw DB content as untrusted; `_CHAT_SYSTEM_PROMPT` "CRITICAL SECURITY" block reinforces verbally with example attack patterns (instruction-override and identity-swap) called out by name in the prompt body. SAFE-05 preserved.
- **T-03-02-05 (DoS, long-running SQL exhausting timeout_s):** mitigated. `SET SESSION max_execution_time={timeout_s * 1000}` server-side cap; `agent_cfg.timeout_s` bounded `[5, 300]` by Pydantic ge/le on AgentConfig.
- **T-03-02-06 (DoS, unbounded result rows OOMing):** mitigated. `inject_limit(sql, agent_cfg.row_cap)` injects/clamps LIMIT; default 200, max 10_000.
- **T-03-02-07 (Spoofing, present_result with attacker-controlled args):** accepted. All 6 tool args are typed via Pydantic; `present_result` only accepts strings + a ChartSpec model with Literal-typed chart_type. No path from a tool call payload to code execution.
- **T-03-02-08 (Repudiation, mismatched present_result.sql vs run_sql):** accepted. The router (plan 04) re-runs `present_result.sql` to render the final card table; mismatch is visible to the user. Defense-in-depth, not a privacy boundary.

No new threat flags surfaced beyond the plan's pre-registered set. The chat agent does not introduce new network endpoints, auth paths, file access patterns, or schema changes — it is pure agent factory code.

## Next Phase Readiness

All wave-1 contract surface for plans 03-03+ now in place:

- **Plan 03-03 (chat_loop.py):** can `from app.core.agent.chat_agent import build_chat_agent, ChartSpec, PresentResult, ChatAgentDeps` and drive `agent.iter()` / `agent.run_stream_events()`. The `_execute_and_wrap` rejection-prefix contract is the basis for the per-turn rejection counter (D-CHAT-02 retry cap = 5).
- **Plan 03-04 (router rewrite):** can construct `ChatAgentDeps(db=..., agent_cfg=..., active_llm_type=...)` and pass through to plan 03's loop wrapper. The `pbm2_llm` cookie threading from v2.0 Phase 6 already resolves to "openai" or "ollama" for the active_llm_type field.
- **Plan 03-05 (templates):** `_final_card.html` will render a `PresentResult` instance (summary string + Plotly chart from chart_spec) — the Pydantic schema is final and stable.
- **Plan 03-06 (cleanup):** no impact — this plan only added a new module and changed nothing else, so the cleanup plan's grep targets (NL-05 confirmation, _abort_banner.html) are untouched.
- **No runtime behavior change yet:** Ask page still renders the v2.0 Phase 6 surface. All existing tests green.

## Self-Check

Verified file existence and commit hashes:

- `app/core/agent/chat_agent.py` → FOUND (278 lines)
- Commit `dd62206` (Task 1) → FOUND in git log
- Commit `f03ffa1` (Task 2) → FOUND in git log
- `nl_agent.py` and `nl_service.py` unchanged across the plan → CONFIRMED via empty `git diff --stat`

## Self-Check: PASSED

---
*Phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on*
*Plan: 02*
*Completed: 2026-05-02*
