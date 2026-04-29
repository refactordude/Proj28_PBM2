---
phase: 01-pre-work-foundation
verified: 2026-04-25T02:30:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Start `uvicorn app_v2.main:app --port 8000` and open http://localhost:8000 in a browser. Check that the Bootstrap nav-tabs shell renders with Overview / Browse / Ask visible. Navigate to /browse and confirm the 'Coming in Phase 4' alert appears. Navigate to /ask and confirm 'Coming in Phase 5'. Try a nonexistent URL like /nonexistent and confirm a Bootstrap-styled 404 page renders (not JSON)."
    expected: "Bootstrap 5 shell with three horizontal nav tabs. No CDN requests (inspect Network tab — all assets should be from localhost:8000/static/vendor/). 'Coming in Phase N' alerts on /browse and /ask. Custom 404 page with nav-tabs retained."
    why_human: "Visual rendering and CSS correctness cannot be verified programmatically. The TestClient tests verify HTML structure but not that Bootstrap actually styles the page correctly in a real browser, and cannot verify that vendored font files render the Bootstrap Icons glyphs."
---

# Phase 1: Pre-work + Foundation Verification Report

**Phase Goal:** The FastAPI v2.0 app starts cleanly alongside v1.0 Streamlit, serves the Bootstrap shell at `/`, and shares v1.0 service code without Streamlit coupling. All 171 v1.0 tests still pass. No visible UI features — only the structural plumbing every subsequent phase depends on.
**Verified:** 2026-04-25T02:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `uvicorn app_v2.main:app` starts without error; `GET /` returns HTTP 200 with Bootstrap nav and three tabs (Overview / Browse / Ask) visible | ✓ VERIFIED | `from app_v2.main import app` exits 0, prints "PBM2 v2.0 Bootstrap Shell". TestClient `test_get_root_returns_200_html`, `test_get_root_contains_bootstrap_nav_tabs`, `test_get_root_contains_three_tab_labels` all pass. base.html contains `nav nav-tabs` + three tab anchors. |
| 2 | `pytest` still passes all 171 v1.0 tests after ufs_service and nl_service refactors — no regressions | ✓ VERIFIED | Full suite: **213 passed, 1 warning** (171 v1.0 baseline + 6 _core + 6 nl_service + 16 FastAPI smoke + 14 cache tests = 213). Running with `--ignore=tests/services/test_ufs_service_core.py --ignore=tests/agent/test_nl_service.py --ignore=tests/v2/` would recover exactly 171 v1.0 tests. |
| 3 | `python -c "import app.services.ufs_service"` in a plain Python process (no Streamlit server running) raises no exception | ✓ VERIFIED | `from app.services.ufs_service import list_platforms_core, list_parameters_core, fetch_cells_core, pivot_to_wide_core` exits 0 in-process. Subprocess test in `test_core_functions_importable_without_streamlit_session` passes. Note: Streamlit prints "No runtime found, using MemoryCacheStorageManager" warnings but does NOT raise — import succeeds. |
| 4 | Bootstrap 5, HTMX, and Bootstrap Icons are served from `/static/vendor/` (not CDN-dependent); page renders correctly with network blocked | ✓ VERIFIED | `grep -cE "cdn.jsdelivr\|unpkg.com" base.html` = 0. All three assets verified: `bootstrap.min.css` (232KB), `htmx.min.js` (51KB), `bootstrap-icons.css` exist under `app_v2/static/vendor/`. TestClient `test_get_root_no_cdn_references` passes. Static serving verified by `test_static_vendor_serves_bootstrap_css` / `test_static_vendor_serves_htmx_js`. |
| 5 | A validation error on any HTMX form (4xx/5xx response) shows a visible error message in the page — not silently discarded | ✓ VERIFIED | `htmx-error-handler.js` contains `htmx:beforeSwap` listener with `evt.detail.shouldSwap = true` for status >= 400. `<div id="htmx-error-container">` present in base.html. WR-04 null-guard fix applied: `if (errorContainer) { evt.detail.target = errorContainer; }`. TestClient `test_get_root_contains_htmx_error_container` passes. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Status | Evidence |
|----------|--------|----------|
| `requirements.txt` | ✓ VERIFIED | Contains all 8 v2.0 deps at exact CONTEXT.md pins: `fastapi>=0.136,<0.137`, `uvicorn[standard]>=0.32`, `jinja2>=3.1`, `jinja2-fragments>=1.3`, `python-multipart>=0.0.9`, `markdown-it-py[plugins]>=3.0`, `cachetools>=7.0,<8.0`, `pydantic-settings>=2.14`. All 18 v1.0 entries unchanged. |
| `app/services/ufs_service.py` | ✓ VERIFIED | 290 lines. Four `_core()` functions present (lines 74, 103, 131, 289). Three `@st.cache_data` wrappers collapse to single-line delegates. `pivot_to_wide_core = pivot_to_wide` alias at end. Security contracts (_safe_table, bindparam, row_cap, READ ONLY) preserved in `_core` functions. |
| `app/core/agent/nl_service.py` | ✓ VERIFIED | 182 lines. `@dataclass NLResult` with `field(default_factory=list)` for `candidate_params`. `run_nl_query()` with SAFE-02 second-pass validate_sql, SAFE-03 inject_limit, read-only session execution. Zero `import streamlit` / `from streamlit` lines. |
| `app/pages/ask.py` | ✓ VERIFIED | 404 lines. Imports `from app.core.agent.nl_service import NLResult, run_nl_query`. `_run_agent_flow` calls `run_nl_query()` and dispatches on `nl_result.kind`. Dead imports (ClarificationNeeded, SQLResult, run_agent) removed per WR-02. Zero `validate_sql(`, `inject_limit(`, `SET SESSION TRANSACTION READ ONLY` in file. |
| `app_v2/main.py` | ✓ VERIFIED | 122 lines. `@asynccontextmanager lifespan` sets `app.state.settings`, `app.state.db`, `app.state.agent_registry`. `StaticFiles` mount before routers. Custom `StarletteHTTPException` handler for 404/500 via Bootstrap templates. Fallthrough path uses `escape(str(exc.detail))` per WR-03. |
| `app_v2/routers/root.py` | ✓ VERIFIED | Three `def` (not async) routes. Starlette 1.0 `TemplateResponse(request, name, ctx)` signature on all 3 calls. "Coming in Phase 4/5" placeholders for `/browse` and `/ask`. |
| `app_v2/templates/base.html` | ✓ VERIFIED | `nav nav-tabs` present. `id="htmx-error-container"` present. No CDN URLs. References all three vendored assets via `url_for`. Loads `htmx-error-handler.js` with `defer`. |
| `app_v2/static/js/htmx-error-handler.js` | ✓ VERIFIED | `htmx:beforeSwap` listener. `shouldSwap = true` for status >= 400. `null`-guard on `getElementById` per WR-04 fix. |
| `app_v2/static/vendor/bootstrap/bootstrap.min.css` | ✓ VERIFIED | 232,111 bytes (>100KB threshold). |
| `app_v2/static/vendor/htmx/htmx.min.js` | ✓ VERIFIED | 51,238 bytes (>5KB threshold). |
| `app_v2/static/vendor/bootstrap-icons/bootstrap-icons.css` | ✓ VERIFIED | Exists. |
| `app_v2/static/vendor/*/VERSIONS.txt` | ✓ VERIFIED | `bootstrap: 5.3.8`, `htmx: 2.0.10`, `bootstrap-icons: 1.13.1` confirmed by grep. |
| `app_v2/services/cache.py` | ✓ VERIFIED | 149 lines. Three `@cached` wrappers with `TTLCache(maxsize=64/256, ttl=300/60)` and `threading.Lock()`. `_fetch_cells_cached` internal + public `fetch_cells` returns `df.copy(), capped` per WR-01 fix. Zero Streamlit imports. `clear_all_caches()` helper present. |
| `tests/services/test_ufs_service_core.py` | ✓ VERIFIED | 6 tests collected and passing. |
| `tests/agent/test_nl_service.py` | ✓ VERIFIED | 6 tests collected and passing. |
| `tests/v2/test_main.py` | ✓ VERIFIED | 16 tests collected and passing. |
| `tests/v2/test_cache.py` | ✓ VERIFIED | 14 tests collected and passing (plan expected 12+; 14 includes WR-01 regression test). |

### Key Link Verification

| From | To | Via | Status |
|------|-----|-----|--------|
| `ufs_service.py::list_platforms` wrapper | `list_platforms_core` | `return list_platforms_core(_db, db_name)` | ✓ WIRED — grep confirms `return list_platforms_core` (1 match) |
| `ufs_service.py::list_parameters` wrapper | `list_parameters_core` | `return list_parameters_core(_db, db_name)` | ✓ WIRED — grep confirms `return list_parameters_core` (1 match) |
| `ufs_service.py::fetch_cells` wrapper | `fetch_cells_core` | `return fetch_cells_core(...)` | ✓ WIRED — grep confirms `return fetch_cells_core` (1 match) |
| `ask.py::_run_agent_flow` | `nl_service.run_nl_query` | `nl_result = run_nl_query(question, agent, deps)` | ✓ WIRED — `run_nl_query(` appears in ask.py |
| `nl_service.py::run_nl_query` | `nl_agent.py::run_agent` | `output = run_agent(agent, question, deps)` | ✓ WIRED — `from app.core.agent.nl_agent import ... run_agent` in nl_service |
| `nl_service.py::run_nl_query` | `sql_validator.py::validate_sql` | SAFE-02 second pass | ✓ WIRED — `from app.services.sql_validator import validate_sql` confirmed |
| `app_v2/main.py::lifespan` | `app/core/config.py::load_settings` | `settings = load_settings()` | ✓ WIRED — line 49 of main.py |
| `app_v2/main.py::lifespan` | `app/adapters/db/registry.py::build_adapter` | `app.state.db = build_adapter(db_cfg)` | ✓ WIRED — line 65 of main.py |
| `base.html` | `/static/vendor/bootstrap/bootstrap.min.css` | `url_for('static', path='vendor/bootstrap/bootstrap.min.css')` | ✓ WIRED — confirmed in base.html |
| `base.html` | `/static/js/htmx-error-handler.js` | `url_for('static', path='js/htmx-error-handler.js')` | ✓ WIRED — grep confirms 2 references to `htmx-error-handler.js` in base.html |
| `app_v2/services/cache.py` | `ufs_service.py::list_platforms_core` | `from app.services.ufs_service import fetch_cells_core, list_parameters_core, list_platforms_core` | ✓ WIRED — confirmed in cache.py |
| `app_v2/services/cache.py::_fetch_cells_cached` | `cachetools.TTLCache + threading.Lock` | `@cached(cache=_cells_cache, lock=_cells_lock, key=...)` | ✓ WIRED — 3 `@cached(` + 4 `threading.Lock()` in cache.py |

### Data-Flow Trace (Level 4)

Not applicable for Phase 1. No routes render dynamic database data — all routes return Bootstrap shell stubs ("Coming in Phase N"). The data-flow chain (cache.py → _core() → DB) is structurally assembled and unit-tested but not exercised by any live route in this phase. Exercised in Phase 2+.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| FastAPI app imports cleanly | `.venv/bin/python -c "from app_v2.main import app; print(app.title)"` | `PBM2 v2.0 Bootstrap Shell` | ✓ PASS |
| All 4 _core functions importable | `.venv/bin/python -c "from app.services.ufs_service import list_platforms_core, list_parameters_core, fetch_cells_core, pivot_to_wide_core; print('OK')"` | `OK` (with Streamlit runtime warnings, no exception) | ✓ PASS |
| nl_service importable | `.venv/bin/python -c "from app.core.agent.nl_service import NLResult, run_nl_query; print('OK')"` | `OK` | ✓ PASS |
| cache.py importable | `.venv/bin/python -c "from app_v2.services.cache import list_platforms, list_parameters, fetch_cells, clear_all_caches; print('OK')"` | `OK` | ✓ PASS |
| Full test suite | `.venv/bin/python -m pytest tests/ -x --tb=line -q` | `213 passed, 1 warning` | ✓ PASS |
| Bootstrap CSS served locally | `GET /static/vendor/bootstrap/bootstrap.min.css` via TestClient | 200, >1000 chars | ✓ PASS (test_static_vendor_serves_bootstrap_css) |
| HTMX JS served locally | `GET /static/vendor/htmx/htmx.min.js` via TestClient | 200, >5000 chars | ✓ PASS (test_static_vendor_serves_htmx_js) |
| Custom 404 renders Bootstrap page | `GET /this-does-not-exist` via TestClient | 404 + `nav nav-tabs` in body | ✓ PASS (test_get_nonexistent_route_returns_bootstrap_404) |

### Requirements Coverage

| Requirement | Plan | Description | Status | Evidence |
|-------------|------|-------------|--------|----------|
| INFRA-01 | 01-03 | App runs via uvicorn; returns HTML at /, /browse, /ask | ✓ SATISFIED | `from app_v2.main import app` works; TestClient GET / = 200; GET /browse = 200; GET /ask = 200 |
| INFRA-02 | 01-03 | Bootstrap shell with nav-tabs, htmx:beforeSwap handler, 404/500 pages | ✓ SATISFIED | `nav nav-tabs` in base.html; `htmx-error-handler.js` with `shouldSwap=true` + null-guard; custom StarletteHTTPException handler renders 404.html |
| INFRA-03 | 01-03 | lifespan initializes app.state.db, settings, agent_registry | ✓ SATISFIED | `app.state.settings`, `app.state.agent_registry`, `app.state.db` set in lifespan; `test_lifespan_initializes_app_state` passes |
| INFRA-04 | 01-03 | Bootstrap 5.3.8 + HTMX 2.0.10 + bootstrap-icons 1.13.1 vendored | ✓ SATISFIED | All assets under `/static/vendor/`; VERSIONS.txt confirms exact versions; zero CDN URLs in base.html |
| INFRA-05 | 01-03 | All DB-touching routes are `def` not `async def` | ✓ SATISFIED | `grep -c "^async def" app_v2/routers/root.py` = 0; all three routes are `def` |
| INFRA-06 | 01-01 | ufs_service _core() functions extractable without Streamlit context | ✓ SATISFIED | Four _core functions added; wrappers delegate; subprocess importability test passes |
| INFRA-07 | 01-02 | nl_service.run_nl_query() as single SAFE-02..06 entry point | ✓ SATISFIED | nl_service.py 182 lines; ask.py delegates to run_nl_query; zero validate_sql/inject_limit/SET SESSION in ask.py |
| INFRA-08 | 01-04 | TTLCache + threading.Lock wrappers for _core() functions | ✓ SATISFIED | cache.py has 3 @cached decorators with lock=; df.copy() on fetch_cells; 14 tests all pass |
| INFRA-09 | 01-01 | requirements.txt extended with v2.0 deps | ✓ SATISFIED | 8 v2.0 deps confirmed at exact version pins; v1.0 deps unchanged |

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `app_v2/routers/root.py` lines 25, 35, 45 | `placeholder_message = "Coming in Phase N"` | ℹ️ Info (intentional stub) | Confirmed intentional per plan spec; resolves in Phase 4 (Browse) and Phase 5 (Ask) |
| `app_v2/main.py` line 56 | `app.state.db = None` when no DB configured | ℹ️ Info (intentional stub) | Phase 1 tests don't require DB; resolves when Phase 2 route handlers access `request.app.state.db` |
| `app_v2/main.py` line 51 | `app.state.agent_registry = {}` (empty dict) | ℹ️ Info (intentional stub) | Resolves in Phase 3/5 when `get_agent()` factory populates it |
| `app_v2/services/cache.py` line 28 | `from typing import Tuple` (deprecated since Python 3.9) | ℹ️ Info (IN-01 from review) | Non-blocking; `tuple[str, ...]` preferred but `Tuple` still valid in Python 3.13. No correctness impact. |

No blockers or warnings remain. All four code review warnings (WR-01 through WR-04) were resolved by the REVIEW-FIX phase.

### Code Review Post-Fix Status

All 4 warnings from 01-REVIEW.md resolved and confirmed:

| Warning | Fix Applied | Verified |
|---------|-------------|----------|
| WR-01: `fetch_cells` returns shared cached DataFrame by reference | Split into `_fetch_cells_cached` (internal) + public `fetch_cells` that returns `df.copy(), capped`; `test_fetch_cells_mutation_does_not_corrupt_cache` regression test added | `df.copy()` at line 129 of cache.py confirmed; mutation test at line 116 of test_cache.py confirmed |
| WR-02: Dead imports in ask.py (`ClarificationNeeded`, `SQLResult`, `run_agent`) | Removed from nl_agent import block | `grep -n "^from app.core.agent.nl_agent" ask.py` shows only `AgentDeps, AgentRunFailure, build_agent` |
| WR-03: Unescaped `exc.detail` in HTTP exception fallthrough path | `from html import escape` added; `escape(str(exc.detail))` in fallthrough HTMLResponse | `from html import escape` confirmed in main.py line 23 |
| WR-04: No null-guard on `getElementById("htmx-error-container")` | `var errorContainer = ...; if (errorContainer) { evt.detail.target = errorContainer; }` | Confirmed in htmx-error-handler.js lines 28-31 |

### Human Verification Required

1. **Bootstrap Shell Visual Rendering**

   **Test:** Start `uvicorn app_v2.main:app --port 8000` from the project root (with the venv active). Open http://localhost:8000 in a browser.

   **Expected:**
   - Page renders with a Bootstrap 5 navbar at top containing "PBM2" brand and horizontal tabs for Overview, Browse, and Ask.
   - The Overview tab is visually "active" (underline or highlight).
   - No browser console errors about missing assets (verify in DevTools Network tab — all requests should be to localhost:8000/static/vendor/).
   - Navigate to http://localhost:8000/browse — a blue info alert reads "Coming in Phase 4 — pivot grid port from v1.0." within the same Bootstrap shell.
   - Navigate to http://localhost:8000/ask — a blue info alert reads "Coming in Phase 5 — NL agent port from v1.0."
   - Navigate to http://localhost:8000/nonexistent — a custom Bootstrap 404 page with the nav-tabs still visible renders.
   - Bootstrap Icons glyphs (database icon in brand, list/table/chat-dots in nav tabs) render correctly (requires that the woff2 font file is served).

   **Why human:** CSS rendering correctness, font glyph rendering, and visual layout cannot be verified by TestClient HTML assertion. The TestClient confirms structural HTML but not that Bootstrap actually applies its styles or that the woff2 fonts serve correctly to a browser renderer.

---

## Summary

Phase 1 goal is **fully achieved** from a code and test perspective. All 9 INFRA requirements are satisfied, all 5 ROADMAP success criteria are verified, all 4 code review warnings are fixed, and the test suite has grown from the 171 v1.0 baseline to 213 (42 new tests covering _core, nl_service, FastAPI smoke, and cache contracts) with zero regressions.

The sole item requiring human verification is a visual browser smoke test to confirm Bootstrap CSS and Bootstrap Icons woff2 fonts serve correctly — a one-minute check that can unblock Phase 2 planning immediately.

**Test count breakdown:**
- v1.0 baseline (untouched): 171
- Plan 01-01 _core contract tests: 6
- Plan 01-02 nl_service tests: 6
- Plan 01-03 FastAPI TestClient smoke tests: 16
- Plan 01-04 cache tests: 14 (13 per plan spec + 1 WR-01 regression test)
- **Total: 213 passed, 1 warning, 0 failed**

---

_Verified: 2026-04-25T02:30:00Z_
_Verifier: Claude (gsd-verifier)_
