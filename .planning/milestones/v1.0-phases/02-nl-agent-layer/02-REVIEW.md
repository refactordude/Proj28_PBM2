---
phase: 02-nl-agent-layer
reviewed: 2026-04-23T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - app/adapters/llm/pydantic_model.py
  - app/core/agent/nl_agent.py
  - app/pages/ask.py
  - app/services/ollama_fallback.py
  - app/services/path_scrubber.py
  - app/services/sql_limiter.py
  - app/services/sql_validator.py
  - streamlit_app.py
  - config/starter_prompts.example.yaml
  - requirements.txt
findings:
  critical: 2
  warning: 4
  info: 4
  total: 10
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-23
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

The Phase 2 NL agent layer is structurally sound. The PydanticAI wiring (`output_type`, `UsageLimits`, `result.output`, `nest_asyncio.apply()` placement) is all correct. The safety primitives (SAFE-02 through SAFE-06) are wired in the right order inside `run_sql`. The two critical findings are both in `sql_validator.py`: the `_extract_table_names` walker silently misses tables in UNION branches and CTE bodies, meaning a malicious or confused LLM can bypass the `allowed_tables` allowlist under those constructs. The primary backstop (read-only MySQL user) limits blast radius in production, but the validator should not have holes. The four warnings cover a missing timeout on the display-side DB execution in `ask.py`, a Regenerate button logic error that drops confirmed params, the path scrubber being case-sensitive (uppercase `/SYS/` paths leak to OpenAI), and exception detail text potentially surfacing to the LLM. The info items cover magic numbers, missing test cases for the new bypass vectors, and two minor UX inconsistencies.

---

## Critical Issues

### CR-01: SQL validator silently passes UNION branches — `allowed_tables` bypass

**File:** `app/services/sql_validator.py:77-125`

**Issue:** `_extract_table_names` walks tokens but stops after the first `FROM`-triggered `Identifier` match for each `from_seen` cycle. In a UNION query the second `SELECT … FROM <table>` clause is at the same token-depth as the first; after the first `ufs_data` Identifier is consumed `from_seen` resets to `False`. When the second `FROM` is reached and the table name happens to be a sqlparse reserved keyword (`admin`, `user`, `key`, `index`, `group`, `order`) sqlparse does NOT wrap it in an `Identifier` node — it emits a bare `Token.Keyword` token. The `from_seen` branch checks `isinstance(tok, Identifier)` only, so the keyword-named table is never added to the extracted set. The allowlist check then sees only `{'ufs_data'}` and passes the query.

Confirmed bypass examples:
```sql
SELECT 1 FROM ufs_data UNION SELECT password FROM admin
SELECT 1 FROM ufs_data UNION ALL SELECT 1 FROM user
SELECT 1 FROM ufs_data INTERSECT SELECT 1 FROM key
```

With a real MySQL schema these queries would hit whatever `admin`/`user` tables exist. The read-only DB user limits damage but the validator should not silently allow them.

**Fix:** After the `Identifier` branch, add a fallback that captures bare `Token.Name` tokens after `from_seen` (sqlparse uses `Token.Name` for unambiguous table names) and also capture the `Token.Keyword` ttype case for reserved words. The safest fix is to add a blanket rejection of `UNION`, `UNION ALL`, `INTERSECT`, and `EXCEPT` keywords at the top of `validate_sql`, since the agent prompt explicitly calls for single-table queries and has no legitimate use for set operations:

```python
# Add near the top of validate_sql(), after the statement count check:
_SET_OP_KEYWORDS = {"UNION", "INTERSECT", "EXCEPT"}
for tok in stmt.flatten():
    if tok.ttype is T.Keyword and tok.normalized.upper().split()[0] in _SET_OP_KEYWORDS:
        return ValidationResult(ok=False, reason="UNION / INTERSECT / EXCEPT are not allowed")
```

Alternatively, fix `_walk` to handle bare-keyword table names:
```python
elif from_seen:
    if isinstance(tok, Identifier):
        # ... existing logic
    elif tok.ttype in (T.Name, T.Keyword):  # bare table name or reserved-word table name
        if not tok.is_whitespace:
            tables.add(tok.normalized.lower())
            from_seen = False
```

---

### CR-02: SQL validator silently passes CTE bodies — `allowed_tables` bypass

**File:** `app/services/sql_validator.py:121`

**Issue:** `_walk` recurses into compound tokens with the guard:
```python
if hasattr(tok, "tokens") and not isinstance(tok, (Identifier, IdentifierList)):
    _walk(tok.tokens)
```
A CTE body takes the form `WITH evil AS (SELECT * FROM other_table) SELECT * FROM ufs_data`. sqlparse represents the CTE definition as an `Identifier` node (`evil AS (...)`). Because `Identifier` is excluded from recursion, `_walk` never descends into the Parenthesis containing `SELECT * FROM other_table`, so `other_table` is never checked against `allowed_tables`.

Confirmed bypass:
```sql
WITH evil AS (SELECT * FROM other_table) SELECT * FROM ufs_data
WITH t AS (SELECT * FROM admin) SELECT * FROM ufs_data
```

**Fix:** Option A — Add a blanket rejection of the `Token.Keyword.CTE` token type at the top of `validate_sql`:
```python
for tok in stmt.flatten():
    if tok.ttype is T.Keyword.CTE:  # sqlparse.tokens.Keyword.CTE
        return ValidationResult(ok=False, reason="WITH (CTE) is not allowed")
```

Option B — Fix `_walk` to recurse into `Identifier` nodes that contain a `Parenthesis` child:
```python
if isinstance(tok, Identifier):
    inner_parens = [t for t in tok.tokens if isinstance(t, Parenthesis)]
    for p in inner_parens:
        _walk(p.tokens)   # recurse into CTE body
    # Also extract the table name if no subquery
    if not inner_parens:
        name = tok.get_real_name()
        if name:
            tables.add(name.lower())
    from_seen = False
```

Option A (blanket CTE rejection) is simpler, safer, and consistent with the agent's scope: the system prompt describes only three single-table query shapes and has no need for CTEs.

---

## Warnings

### WR-01: Display-side SQL execution in `ask.py` has no `max_execution_time` timeout

**File:** `app/pages/ask.py:327-335`

**Issue:** After `run_agent` returns a `SQLResult`, `ask.py` re-executes the validated SQL a second time to get a `DataFrame` for display. This second execution block sets `SET SESSION TRANSACTION READ ONLY` but does NOT set `SET SESSION max_execution_time`. Only the first execution inside `_execute_read_only` (via the `run_sql` tool) has the timeout. If the LLM returns a broad query, the display-side re-execution can block the Streamlit worker for an unbounded duration.

```python
# ask.py lines 327-335 — missing timeout
if hasattr(db, "_get_engine"):
    with db._get_engine().connect() as conn:
        try:
            conn.execute(sa.text("SET SESSION TRANSACTION READ ONLY"))
        except Exception:
            pass
        # No SET SESSION max_execution_time here!
        df = pd.read_sql_query(sa.text(safe_sql), conn)
```

**Fix:** Mirror the `_execute_read_only` pattern exactly:
```python
timeout_ms = settings.app.agent.timeout_s * 1000
if hasattr(db, "_get_engine"):
    with db._get_engine().connect() as conn:
        try:
            conn.execute(sa.text("SET SESSION TRANSACTION READ ONLY"))
        except Exception:
            pass
        try:
            conn.execute(sa.text(f"SET SESSION max_execution_time={timeout_ms}"))
        except Exception:
            pass
        df = pd.read_sql_query(sa.text(safe_sql), conn)
```

---

### WR-02: Regenerate button ignores confirmed params — second-turn result replaced by raw question

**File:** `app/pages/ask.py:247-248`

**Issue:** The Regenerate button inside the SQL expander calls:
```python
if st.button("Regenerate", type="secondary", key="ask.regenerate"):
    _run_agent_flow(st.session_state.get("ask.question", ""))
```

`_run_agent_flow` sends the raw question without any confirmed params. If the prior run went through the NL-05 confirmation flow (`_run_confirmed_agent_flow`), the LLM received `"User-confirmed parameters: [...]\nOriginal question: ..."`. The Regenerate button discards those confirmed params and sends only the bare question. The agent will likely return `ClarificationNeeded` again, forcing the user through the confirmation UX a second time instead of regenerating the answer.

**Fix:** Check whether `ask.confirmed_params` is populated and dispatch accordingly:
```python
if st.button("Regenerate", type="secondary", key="ask.regenerate"):
    if st.session_state.get("ask.confirmed_params"):
        _run_confirmed_agent_flow()
    else:
        _run_agent_flow(st.session_state.get("ask.question", ""))
```

---

### WR-03: Path scrubber is case-sensitive — uppercase `/SYS/`, `/PROC/`, `/DEV/` paths not scrubbed

**File:** `app/services/path_scrubber.py:12`

**Issue:** The compiled pattern `re.compile(r"/(?:sys|proc|dev)/\S*")` has no `re.IGNORECASE` flag. Paths like `/SYS/BLOCK/sda`, `/Sys/kernel/foo`, `/PROC/cpuinfo`, `/DEV/null` are not scrubbed and are sent to OpenAI as-is. Android UFS platform data could store paths in various cases depending on the source. This partially defeats SAFE-06.

```python
_PATH_PATTERN = re.compile(r"/(?:sys|proc|dev)/\S*")  # BUG: no IGNORECASE
```

**Fix:**
```python
_PATH_PATTERN = re.compile(r"/(?:sys|proc|dev)/\S*", re.IGNORECASE)
```

The test suite (`tests/services/test_path_scrubber.py`) also needs a test case for uppercase paths:
```python
def test_uppercase_sys_scrubbed(self):
    result = scrub_paths("/SYS/BLOCK/sda")
    assert "<path>" in result
```

---

### WR-04: SQL execution error message including `str(exc)` sent to LLM — potential credential leak

**File:** `app/core/agent/nl_agent.py:173`

**Issue:** The `run_sql` tool returns error text directly into the LLM conversation context:
```python
except Exception as exc:
    return f"SQL execution error: {type(exc).__name__}: {exc}"
```

`str(exc)` for a SQLAlchemy `OperationalError` can include the full connection URI (e.g., `(pymysql.err.OperationalError) (2003, "Can't connect to MySQL server on 'db.internal:3306'")`). This text is sent to the LLM: for Ollama this stays local, but for OpenAI it leaves the intranet. The DB hostname/port is low-sensitivity for an intranet tool, but the pattern leaks whatever pymysql puts in the exception message.

**Fix:** Strip the exception message to just the type name before including it in LLM context, and keep the full detail only in the Python-side logger (or discard it):
```python
except Exception as exc:
    # Return only the class name to LLM; do not send exc details (may contain connection string).
    return f"SQL execution error: {type(exc).__name__}"
```

If the full error is needed for debugging, add a `logging.warning` call before truncating.

---

## Info

### IN-01: Magic number `200` in `ask.py` row-cap warning — stale if settings override `row_cap`

**File:** `app/pages/ask.py:228-230`

**Issue:**
```python
cfg_row_cap = 200  # AgentConfig.row_cap default — refined when agent runs
if len(last_df) >= cfg_row_cap:
    st.warning(f"Result capped at {cfg_row_cap} rows. ...")
```

The actual `row_cap` used during the run comes from `settings.app.agent.row_cap`. If someone sets `row_cap: 100` in `settings.yaml`, the warning still says "capped at 200 rows" even though only 100 were returned.

**Fix:** Read the live value from settings at render time:
```python
settings = load_settings()
cfg_row_cap = settings.app.agent.row_cap
```

Similarly, the abort banner in `_render_banners()` hardcodes "5-step limit" (line 133) and "30 seconds" (line 135). These should read `settings.app.agent.max_steps` and `settings.app.agent.timeout_s`.

---

### IN-02: `test_sql_validator.py` has no tests for UNION or CTE bypass vectors

**File:** `tests/services/test_sql_validator.py` (no line — missing tests)

**Issue:** The test file covers multi-statement rejection, non-SELECT types, comments, and disallowed tables, but has no test cases for UNION/UNION ALL set operations or CTE (`WITH` clause) queries. Since CR-01 and CR-02 are currently passing as `ok=True` in production code, a regression test is needed both to document the expected-reject behavior and to confirm the fix works.

**Fix:** Add to `TestDisallowedTables` or a new `TestSetOperations` class:
```python
class TestSetOperationsRejected:
    def test_union_select_rejected(self):
        result = validate_sql(
            "SELECT 1 FROM ufs_data UNION SELECT 1 FROM other_table", ALLOWED
        )
        assert result.ok is False

    def test_union_reserved_word_table_rejected(self):
        """Regression for sqlparse keyword-table bypass (admin, user, etc.)."""
        result = validate_sql(
            "SELECT 1 FROM ufs_data UNION SELECT 1 FROM admin", ALLOWED
        )
        assert result.ok is False

    def test_cte_rejected(self):
        result = validate_sql(
            "WITH t AS (SELECT * FROM other_table) SELECT * FROM ufs_data", ALLOWED
        )
        assert result.ok is False
```

---

### IN-03: `test_path_scrubber.py` has no test for uppercase paths

**File:** `tests/services/test_path_scrubber.py` (no line — missing test)

**Issue:** No test covers the case-sensitivity gap identified in WR-03. Without it, adding `re.IGNORECASE` to the fix has no regression guard.

**Fix:** Add to `TestSysPathScrubbed`:
```python
def test_uppercase_sys_not_leaked(self):
    """/SYS/ and /PROC/ uppercase variants must also be scrubbed (re.IGNORECASE)."""
    assert "<path>" in scrub_paths("/SYS/BLOCK/sda")
    assert "<path>" in scrub_paths("/PROC/cpuinfo")
    assert "<path>" in scrub_paths("/DEV/null")
```

---

### IN-04: `AgentRunFailure.last_sql` is never populated on step-cap or llm-error

**File:** `app/core/agent/nl_agent.py:200-206`

**Issue:** `AgentRunFailure` has a `last_sql: str = ""` field. `run_agent` never populates it:
```python
except UsageLimitExceeded as exc:
    return AgentRunFailure(reason="step-cap", detail=str(exc))  # last_sql stays ""
```

In `ask.py`, the "Partial output" expander checks `if abort.last_sql:` (line 139) before showing the SQL subheader. Because `last_sql` is always empty on step-cap, the expander opens but shows nothing — this contradicts D-22 which specifies "last tool call" shown in the partial output.

**Fix:** Capturing the last SQL from within the `agent.run_sync` call requires hooking into PydanticAI's message history. The practical approach is to access `result.all_messages()` in the exception handler context — but `result` is not assigned if `run_sync` raises. A simpler approximation is to capture the last `run_sql` tool call argument by wrapping the tool with a side-channel variable. For v1 the current behavior (empty partial output) is acceptable but the discrepancy from D-22 should be tracked as a known limitation.

---

_Reviewed: 2026-04-23_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
