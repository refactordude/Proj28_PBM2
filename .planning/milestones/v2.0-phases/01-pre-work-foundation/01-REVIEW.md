---
phase: 01-pre-work-foundation
reviewed: 2026-04-23T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - app/core/agent/nl_service.py
  - app/pages/ask.py
  - app/services/ufs_service.py
  - app_v2/main.py
  - app_v2/routers/root.py
  - app_v2/services/cache.py
  - app_v2/templates/__init__.py
  - app_v2/templates/base.html
  - app_v2/templates/404.html
  - app_v2/templates/500.html
  - app_v2/static/js/htmx-error-handler.js
  - requirements.txt
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-04-23
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Phase 1 delivers the FastAPI v2.0 Bootstrap shell and the two v1.0 pre-work refactors (`ufs_service` `_core` split and `nl_service` extraction). The overall quality is high. All 12 pitfalls from PITFALLS.md were checked; none are critically violated. The most impactful problems are a DataFrame mutability gap in `cache.py` that the PITFALLS.md explicitly called out as mandatory to fix, and three unused imports left in `ask.py` after the `nl_service` extraction. The remaining items are informational.

No critical security vulnerabilities were found. The TemplateResponse signature is correct everywhere (request first). All routes in `root.py` are `def` (not `async def`). Every `TTLCache` is paired with a `threading.Lock`. The HTMX error handler is present and functional. The `nl_service` module imports no Streamlit or FastAPI symbols.

---

## Warnings

### WR-01: `cache.py` `fetch_cells` returns the cached DataFrame by reference — callers can silently corrupt subsequent calls

**File:** `app_v2/services/cache.py:109`

**Issue:** `fetch_cells` returns `fetch_cells_core(...)` directly. `cachetools.TTLCache` stores the exact return value and hands back the **same object** to every caller until the TTL expires. PITFALLS.md P3 (and the Pitfall 3 example code) explicitly requires `df.copy()` here: *"the v2.0 code (or any code path) mutates the cached DataFrame ... subsequent callers get the mutated version."* The docstring says "Do NOT mutate", but that is documentation, not enforcement. Any Phase 2–5 route that does `df["Result"] = ...` after calling `cache.fetch_cells()` will corrupt the cache for every concurrent and subsequent request without raising an error.

**Fix:**
```python
def fetch_cells(
    db: DBAdapter,
    platforms: Tuple[str, ...],
    infocategories: Tuple[str, ...],
    items: Tuple[str, ...],
    row_cap: int = 200,
    db_name: str = "",
) -> tuple[pd.DataFrame, bool]:
    df, capped = fetch_cells_core(db, platforms, infocategories, items, row_cap, db_name)
    return df.copy(), capped  # MUST copy — TTLCache returns same object to all callers
```

The additional allocation is negligible at the typical row caps involved (200–1000 rows), and it prevents a class of silent data corruption bugs that are very hard to reproduce in single-user testing.

---

### WR-02: `ask.py` imports `ClarificationNeeded`, `SQLResult`, and `run_agent` from `nl_agent` — all three are now dead after `nl_service` extraction

**File:** `app/pages/ask.py:20-27`

**Issue:** The import block at lines 20–27 brings in six names from `nl_agent`. After the `nl_service` refactor, three of them are no longer used in the module body:
- `ClarificationNeeded` — appears only in a comment (line 381), never used as a type or in an `isinstance` check
- `SQLResult` — appears only in the import list; the callers now branch on `nl_result.kind` (a string)
- `run_agent` — the direct agent call was moved into `nl_service.run_nl_query`; `ask.py` never calls it

These will cause a `ruff F401` / mypy unused-import warning and will confuse future readers into thinking `ask.py` still bypasses `nl_service` for one code path. They also carry a small forward-compatibility risk: if `nl_agent` restructures those names, `ask.py` will break at import time even though it doesn't use them.

**Fix:** Remove the three unused names from the import:
```python
from app.core.agent.nl_agent import (
    AgentDeps,
    AgentRunFailure,
    build_agent,
)
```
`AgentDeps` (line 288), `AgentRunFailure` (lines 131, 299, 302, 305), and `build_agent` (line 120) are all used and must stay.

---

### WR-03: `http_exception_handler` fallthrough path renders `exc.detail` into raw HTML without escaping

**File:** `app_v2/main.py:103-104`

**Issue:** For HTTP status codes other than 404 or 500, the handler falls through to:
```python
return HTMLResponse(
    content=f"<h1>HTTP {exc.status_code}</h1><p>{exc.detail}</p>",
    status_code=exc.status_code,
)
```
`exc.detail` in Starlette's `HTTPException` is a string that can be set by application code or, for some framework-generated exceptions (e.g., 422 validation errors from RequestValidationError), can contain field names derived from the request. If an attacker crafts a request that causes a 4xx response with HTML in the detail string, it is injected verbatim into the response. Jinja2 autoescape does not apply here — this is a plain Python f-string.

The 404 and 500 branches are correctly routed through Jinja2 templates (which have autoescape enabled for `.html`). Only the fallthrough branch is affected.

**Fix:** HTML-escape `exc.detail` before interpolation:
```python
from html import escape

return HTMLResponse(
    content=f"<h1>HTTP {exc.status_code}</h1><p>{escape(str(exc.detail))}</p>",
    status_code=exc.status_code,
)
```
Alternatively, add a catch-all `else` branch that also routes to the `500.html` template with a generic message, which is cleaner and consistent with the existing style.

---

### WR-04: `htmx-error-handler.js` does not null-check `getElementById` result before assigning to `evt.detail.target`

**File:** `app_v2/static/js/htmx-error-handler.js:26`

**Issue:**
```javascript
evt.detail.target = document.getElementById("htmx-error-container");
```
If for any reason `#htmx-error-container` is absent from the DOM (e.g., a future template that does not extend `base.html`, or a test harness that injects partial HTML), `getElementById` returns `null`. Assigning `null` to `evt.detail.target` causes HTMX to silently drop the swap — the same "error disappears" behavior the handler exists to prevent. The element is currently always present in `base.html`, but the guard is missing and the failure mode is silent.

**Fix:**
```javascript
var errorContainer = document.getElementById("htmx-error-container");
if (xhr.status >= 400) {
    evt.detail.shouldSwap = true;
    evt.detail.isError = true;
    if (errorContainer) {
        evt.detail.target = errorContainer;
    }
    // If container missing, HTMX swaps into the original hx-target (acceptable fallback)
}
```

---

## Info

### IN-01: `cache.py` uses `from typing import Tuple` (deprecated form) — `tuple[...]` is available in Python 3.9+

**File:** `app_v2/services/cache.py:29`

**Issue:** `from typing import Tuple` is used for the `fetch_cells` type annotation. The project targets Python 3.11+ (pandas 3.0 requires it). The lowercase `tuple[str, ...]` built-in form has been available since Python 3.9 and is the preferred style per PEP 585.

**Fix:** Remove the `Tuple` import and update the annotation:
```python
def fetch_cells(
    db: DBAdapter,
    platforms: tuple[str, ...],
    ...
```

---

### IN-02: `ask.py` line 229 — hardcoded magic number `cfg_row_cap = 200` drifts from `AgentConfig.row_cap`

**File:** `app/pages/ask.py:229`

**Issue:** The cap-warning threshold is hardcoded as `200` with a comment saying "AgentConfig.row_cap default — refined when agent runs." If `AgentConfig.row_cap` is changed in `app/core/agent/config.py`, the warning threshold in the UI will silently diverge. The correct value is already available in the `deps.agent_cfg` object used during `_run_agent_flow`, but `_render_answer_zone` does not have access to it at render time.

**Fix (minimal):** Source it from `AgentConfig` default directly to avoid the drift:
```python
from app.core.agent.config import AgentConfig as _AgentCfg
cfg_row_cap = _AgentCfg.model_fields["row_cap"].default  # or read from session state if deps is stored
```
Or store `deps.agent_cfg.row_cap` in session state when `_run_agent_flow` runs and read it in `_render_answer_zone`.

---

### IN-03: `nl_service.py` engine detection uses private `_get_engine` duck-typing — fragile coupling to internal adapter API

**File:** `app/core/agent/nl_service.py:147-161`

**Issue:**
```python
engine_fn = getattr(deps.db, "_get_engine", None)
if engine_fn is None:
    df = deps.db.run_query(safe_sql)
else:
    with engine_fn().connect() as conn:
        ...
```
This introspects a private attribute (`_get_engine`) to decide which execution path to take. If `DBAdapter` is ever refactored to rename `_get_engine` (e.g., to `get_engine` without the underscore, or to replace it with a `connect()` context manager), `nl_service` silently falls back to the `run_query` path (which may not apply the read-only session or `max_execution_time` settings). The SAFE-01 read-only guarantee then silently degrades without any error or log.

**Fix:** Add a `get_engine()` public method to the `DBAdapter` base class (or protocol), and use that in `nl_service`. If the public method is not available, raise `AttributeError` explicitly rather than silently degrading:
```python
try:
    engine = deps.db.get_engine()
except AttributeError:
    _log.warning("DBAdapter has no get_engine(); falling back to run_query (no read-only session)")
    df = deps.db.run_query(safe_sql)
else:
    with engine.connect() as conn:
        ...
```

---

### IN-04: `ufs_service.py` still imports `streamlit as st` at module top-level

**File:** `app/services/ufs_service.py:42`

**Issue:** The module-level `import streamlit as st` at line 42 is still present. The `_core()` functions were correctly extracted without Streamlit dependencies, but the `@st.cache_data`-decorated wrappers (`list_platforms`, `list_parameters`, `fetch_cells`) remain in the same file and require the import. This means importing `ufs_service` in any Python process without a Streamlit context (including the FastAPI process) will succeed at import time — because `import streamlit` itself does not raise without a session — but calling the `@st.cache_data`-decorated functions from outside a Streamlit session will raise `StreamlitAPIException`.

This is the documented "acceptable" state of the refactor (v2.0 routes import only `*_core` functions and never call the decorated wrappers). However, the isolation is a convention, not enforced. If a future developer adds `from app.services.ufs_service import fetch_cells` (without `_core`) to a v2.0 route, it will fail at call time with a confusing Streamlit error.

**Fix (current scope):** Add a module-level comment above the `@st.cache_data` wrappers making the v2.0 import rule explicit:
```python
# v2.0 IMPORT RULE: import only *_core functions (list_platforms_core etc.)
# from v2.0 FastAPI routes. The @st.cache_data wrappers below require an
# active Streamlit session and will raise StreamlitAPIException in a FastAPI process.
```
A stronger enforcement option (deferred) would be to move the `@st.cache_data` wrappers into a separate `app/services/ufs_service_streamlit.py` file so that the import boundary is structural rather than conventional.

---

_Reviewed: 2026-04-23_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
