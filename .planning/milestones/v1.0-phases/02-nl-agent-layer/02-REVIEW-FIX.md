---
phase: 02-nl-agent-layer
fixed_at: 2026-04-24T01:37:50Z
review_path: .planning/phases/02-nl-agent-layer/02-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-04-24T01:37:50Z
**Source review:** .planning/phases/02-nl-agent-layer/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (CR-01, CR-02, WR-01, WR-02, WR-03, WR-04)
- Fixed: 6
- Skipped: 0

## Fixed Issues

### CR-01: SQL validator silently passes UNION branches — `allowed_tables` bypass

**Files modified:** `app/services/sql_validator.py`, `tests/services/test_sql_validator.py`
**Commit:** a3c83be
**Applied fix:** Added blanket rejection of UNION / INTERSECT / EXCEPT keywords at the top of `validate_sql()` (before comment and table checks), iterating over `stmt.flatten()` and matching `tok.ttype is T.Keyword` with normalized value in `_SET_OP_KEYWORDS`. Added 5 regression tests in a new `TestSetOperationsRejected` class covering UNION, UNION ALL, INTERSECT, EXCEPT, and the reserved-word table-name bypass case (`admin`).

---

### CR-02: SQL validator silently passes CTE bodies — `allowed_tables` bypass

**Files modified:** `app/services/sql_validator.py`, `tests/services/test_sql_validator.py`
**Commit:** 9a855f4
**Applied fix:** Added blanket rejection of `T.Keyword.CTE` token type (confirmed via `sqlparse.parse` inspection that sqlparse emits `Token.Keyword.CTE` for the `WITH` keyword). The check is placed immediately after the set-operation check. Added 3 regression tests in a new `TestCTERejected` class covering `WITH ... other_table`, `WITH ... admin` (reserved-word table), and verification that the rejection reason contains "CTE" or "WITH".

---

### WR-01: Display-side SQL execution in `ask.py` has no `max_execution_time` timeout

**Files modified:** `app/pages/ask.py`
**Commit:** a84586d
**Applied fix:** Added `timeout_ms = int(cfg.timeout_s) * 1000` before the connection block, then added a `try/except` around `conn.execute(sa.text(f"SET SESSION max_execution_time={timeout_ms}"))` with a `pass` fallback (matching the Pitfall 8 comment pattern from `_execute_read_only`). The display-side execution block now mirrors `_execute_read_only` exactly for both read-only and timeout guards.

---

### WR-02: Regenerate button ignores confirmed params — second-turn result replaced by raw question

**Files modified:** `app/pages/ask.py`
**Commit:** f35aaab
**Applied fix:** Changed the `Regenerate` button handler to check `st.session_state.get("ask.confirmed_params")` and dispatch to `_run_confirmed_agent_flow()` when confirmed params are present, falling back to `_run_agent_flow(question)` when none are set. This preserves the NL-05 confirmation context on regeneration.

---

### WR-03: Path scrubber is case-sensitive — uppercase `/SYS/`, `/PROC/`, `/DEV/` paths not scrubbed

**Files modified:** `app/services/path_scrubber.py`, `tests/services/test_path_scrubber.py`
**Commit:** f3b8e8d
**Applied fix:** Added `re.IGNORECASE` flag to `_PATH_PATTERN = re.compile(r"/(?:sys|proc|dev)/\S*", re.IGNORECASE)`. Added 4 regression tests in a new `TestUppercasePathsScrubbed` class covering `/SYS/BLOCK/sda`, `/PROC/cpuinfo`, `/DEV/null`, and `/Sys/kernel/foo` (mixed case).

---

### WR-04: SQL execution error message including `str(exc)` sent to LLM — potential credential leak

**Files modified:** `app/core/agent/nl_agent.py`
**Commit:** fd6aff9
**Applied fix:** Added `import logging` and a module-level `_log = logging.getLogger(__name__)`. Changed the `run_sql` exception handler from `return f"SQL execution error: {type(exc).__name__}: {exc}"` to log the full detail server-side via `_log.warning(...)` and return only `f"SQL execution error: {type(exc).__name__}"` to the LLM. This prevents pymysql `OperationalError` messages (which can include the DB hostname/port/URI) from reaching OpenAI.

---

_Fixed: 2026-04-24T01:37:50Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
