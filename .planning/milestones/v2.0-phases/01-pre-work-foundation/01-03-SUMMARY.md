---
phase: "01"
plan: "03"
subsystem: "app_v2 FastAPI shell / static assets"
tags:
  - infrastructure
  - fastapi
  - htmx
  - bootstrap
  - templates
  - vendoring
dependency_graph:
  requires:
    - "01-01 (v2.0 deps in requirements.txt, jinja2-fragments installed)"
  provides:
    - "app_v2/main.py::app (FastAPI entrypoint, lifespan, static mount, exception handlers)"
    - "app_v2/routers/root.py::router (GET /, /browse, /ask stub routes)"
    - "app_v2/templates/base.html (Bootstrap 5 shell, nav-tabs, HTMX error container)"
    - "app_v2/templates/404.html + 500.html (Bootstrap-styled error pages)"
    - "app_v2/static/vendor/* (Bootstrap 5.3.8, HTMX 2.0.10, Bootstrap Icons 1.13.1 vendored)"
    - "app_v2/static/js/htmx-error-handler.js (htmx:beforeSwap 4xx/5xx handler)"
    - "app_v2/templates/__init__.py::templates (Jinja2Blocks singleton)"
  affects:
    - "All subsequent app_v2 phases (2-5): use app.state.db/.settings/.agent_registry"
    - "Phase 2+: import templates from app_v2.templates; use block_name= for HTMX fragments"
tech_stack:
  added:
    - "fastapi==0.136.1 (installed into .venv)"
    - "jinja2-fragments>=1.3 (installed into .venv)"
    - "uvicorn[standard]>=0.32 (installed into .venv)"
    - "Bootstrap 5.3.8 (vendored CSS + JS bundle)"
    - "HTMX 2.0.10 (vendored JS, pinned to 2.x — NOT 4.0 alpha)"
    - "Bootstrap Icons 1.13.1 (vendored CSS + woff/woff2 fonts)"
  patterns:
    - "Starlette 1.0 TemplateResponse(request, name, context) — request first positional arg"
    - "INFRA-05: all routes are def (sync), not async def — FastAPI threadpool dispatch"
    - "Lifespan @asynccontextmanager pattern for startup/shutdown singletons"
    - "StaticFiles mount at /static before router registration for url_for() to work"
    - "Custom StarletteHTTPException handler for Bootstrap-styled 404/500 pages"
    - "htmx:beforeSwap handler enabling 4xx/5xx swap into #htmx-error-container (Pitfall 5 fix)"
key_files:
  created:
    - path: "app_v2/__init__.py"
      description: "Package init with docstring"
    - path: "app_v2/main.py"
      description: "FastAPI app factory with lifespan (INFRA-03), static mount (INFRA-04), exception handlers (INFRA-02), router registration"
      lines: 128
    - path: "app_v2/routers/__init__.py"
      description: "Routers package init"
    - path: "app_v2/routers/root.py"
      description: "GET /, /browse, /ask Phase 1 stub routes — all def (INFRA-05)"
    - path: "app_v2/templates/__init__.py"
      description: "Jinja2Blocks singleton (jinja2-fragments) for HTMX fragment rendering in Phase 2+"
    - path: "app_v2/templates/base.html"
      description: "Bootstrap 5 shell: nav nav-tabs (Overview/Browse/Ask), #htmx-error-container, vendored asset hrefs (no CDN)"
    - path: "app_v2/templates/404.html"
      description: "Bootstrap alert-warning error page extending base.html"
    - path: "app_v2/templates/500.html"
      description: "Bootstrap alert-danger error page extending base.html"
    - path: "app_v2/static/js/htmx-error-handler.js"
      description: "Global htmx:beforeSwap listener — forces 4xx/5xx swap into #htmx-error-container (Pitfall 5)"
    - path: "app_v2/static/vendor/bootstrap/bootstrap.min.css"
      description: "Bootstrap 5.3.8 CSS (232KB, vendored from jsDelivr)"
    - path: "app_v2/static/vendor/bootstrap/bootstrap.bundle.min.js"
      description: "Bootstrap 5.3.8 JS bundle with Popper (80KB, vendored)"
    - path: "app_v2/static/vendor/bootstrap/VERSIONS.txt"
      description: "Audit trail: version, source URL, download date"
    - path: "app_v2/static/vendor/htmx/htmx.min.js"
      description: "HTMX 2.0.10 (51KB, vendored — pinned to 2.x, not 4.0 alpha)"
    - path: "app_v2/static/vendor/htmx/VERSIONS.txt"
      description: "Audit trail including pin rationale (4.0 alpha)"
    - path: "app_v2/static/vendor/bootstrap-icons/bootstrap-icons.css"
      description: "Bootstrap Icons 1.13.1 CSS (87KB, vendored)"
    - path: "app_v2/static/vendor/bootstrap-icons/fonts/bootstrap-icons.woff"
      description: "Bootstrap Icons woff font (180KB)"
    - path: "app_v2/static/vendor/bootstrap-icons/fonts/bootstrap-icons.woff2"
      description: "Bootstrap Icons woff2 font (134KB)"
    - path: "app_v2/static/vendor/bootstrap-icons/VERSIONS.txt"
      description: "Audit trail: version, source URL, download date"
    - path: "tests/v2/__init__.py"
      description: "Test package init"
    - path: "tests/v2/test_main.py"
      description: "16 FastAPI TestClient smoke tests covering INFRA-01 through INFRA-05"
decisions:
  - "Jinja2Blocks placed in app_v2/templates/__init__.py as module-level singleton — imported by routers; avoids re-instantiating on every request"
  - "StaticFiles mounted before router registration — ensures url_for('static', path=...) resolves in templates at startup"
  - "lifespan resilient to missing DB config (app.state.db = None) — Phase 1 tests pass without a real DB connection"
  - "TemplateResponse calls formatted as single-line (request as first arg on same line) to satisfy plan acceptance criteria grep"
  - "test_get_root_marks_overview_active fixed to search nav section not full body — first 'Overview' occurrence is in <title>, not nav link"
metrics:
  duration: "~10 minutes"
  completed_date: "2026-04-24T16:54:00Z"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 0
  files_created: 19
  tests_before: 183
  tests_after: 199
  tests_added: 16
---

# Phase 01 Plan 03: FastAPI Shell + Vendored Assets Summary

**One-liner:** Bootstrapped the `app_v2/` FastAPI package with Bootstrap 5.3.8 / HTMX 2.0.10 / Bootstrap Icons 1.13.1 vendored under `/static/vendor/`, a Jinja2Blocks shell template with nav-tabs + HTMX error container, lifespan-initialized `app.state`, and 16 TestClient smoke tests — all INFRA requirements verified, 199 tests passing.

## What Was Built

### Task 1 — Vendor Bootstrap 5.3.8, HTMX 2.0.10, Bootstrap Icons 1.13.1 (INFRA-04)

Downloaded and committed vendor assets with VERSIONS.txt audit files:

| Asset | Version | File | Size |
|-------|---------|------|------|
| Bootstrap CSS | 5.3.8 | `static/vendor/bootstrap/bootstrap.min.css` | 232KB |
| Bootstrap JS bundle | 5.3.8 | `static/vendor/bootstrap/bootstrap.bundle.min.js` | 80KB |
| HTMX | 2.0.10 | `static/vendor/htmx/htmx.min.js` | 51KB |
| Bootstrap Icons CSS | 1.13.1 | `static/vendor/bootstrap-icons/bootstrap-icons.css` | 87KB |
| Bootstrap Icons woff2 | 1.13.1 | `static/vendor/bootstrap-icons/fonts/bootstrap-icons.woff2` | 134KB |
| Bootstrap Icons woff | 1.13.1 | `static/vendor/bootstrap-icons/fonts/bootstrap-icons.woff` | 180KB |

HTMX pinned to 2.0.10 explicitly — HTMX 4.0 is alpha (2026-04-09) per CONTEXT.md decision.

### Task 2 — FastAPI app_v2 shell (INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05)

**`app_v2/main.py`** (128 lines):
- `lifespan()` — loads Settings, initializes `app.state.db` (resilient to missing DB config), `app.state.settings`, `app.state.agent_registry = {}`. Disposes `app.state.db` on shutdown.
- `StaticFiles` mount at `/static` before router registration
- `@app.exception_handler(StarletteHTTPException)` — renders `404.html` / `500.html` via Bootstrap-styled templates
- `@app.exception_handler(Exception)` — catch-all renders `500.html` with type-only exception info (no `str(exc)` leakage)

**`app_v2/routers/root.py`** — three `def` (sync) routes:
- `GET /` → `base.html` with `active_tab="overview"`, no placeholder
- `GET /browse` → `base.html` with `active_tab="browse"`, "Coming in Phase 4" alert
- `GET /ask` → `base.html` with `active_tab="ask"`, "Coming in Phase 5" alert

**`app_v2/templates/base.html`**:
- Bootstrap 5 navbar with `ul.nav.nav-tabs` (Overview / Browse / Ask)
- All assets via `url_for('static', path='vendor/...')` — no CDN URLs
- `<div id="htmx-error-container">` in persistent shell (survives HTMX swaps)
- `htmx-error-handler.js` loaded with `defer` — attaches `htmx:beforeSwap` on `DOMContentLoaded`

**`app_v2/static/js/htmx-error-handler.js`**:
- Sets `evt.detail.shouldSwap = true` for `xhr.status >= 400`
- Reroutes swap target to `#htmx-error-container`
- Closes Pitfall 5 (silent 4xx/5xx discard)

### Task 3 — TestClient smoke tests (16 tests)

| Test | Assertion |
|------|-----------|
| `test_get_root_returns_200_html` | 200 + text/html |
| `test_get_root_contains_bootstrap_nav_tabs` | `nav nav-tabs` in body |
| `test_get_root_contains_three_tab_labels` | Overview, Browse, Ask |
| `test_get_root_marks_overview_active` | `active` in nav anchor before Overview |
| `test_get_root_references_vendored_bootstrap_css` | `/static/vendor/bootstrap/bootstrap.min.css` |
| `test_get_root_references_vendored_htmx` | `/static/vendor/htmx/htmx.min.js` |
| `test_get_root_references_htmx_error_handler_js` | `/static/js/htmx-error-handler.js` |
| `test_get_root_contains_htmx_error_container` | `id="htmx-error-container"` |
| `test_get_root_no_cdn_references` | no cdn.jsdelivr / unpkg.com |
| `test_get_browse_returns_200_with_phase_placeholder` | 200 + "Coming in Phase 4" + alert |
| `test_get_ask_returns_200_with_phase_placeholder` | 200 + "Coming in Phase 5" + alert |
| `test_get_nonexistent_route_returns_bootstrap_404` | 404 + nav-tabs (custom, not JSON) |
| `test_static_vendor_serves_bootstrap_css` | 200 + >1000 chars |
| `test_static_vendor_serves_htmx_js` | 200 + >5000 chars |
| `test_static_js_serves_htmx_error_handler` | 200 + htmx:beforeSwap in body |
| `test_lifespan_initializes_app_state` | app.state.{settings,agent_registry,db} exist |

## Test Results

```
199 passed, 1 warning in 49.45s
```

- Prior tests (183 from 01-01 + 01-02): all pass, zero regressions
- New smoke tests: 16
- Total: 199 (exceeds ≥197 target)

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `54e0d4c` | chore | Vendor Bootstrap 5.3.8, HTMX 2.0.10, Bootstrap Icons 1.13.1 (INFRA-04) |
| `174c92d` | feat | Add FastAPI app_v2 shell — lifespan, routers, templates, error handlers (INFRA-01-05) |
| `daff565` | test | Add FastAPI TestClient smoke tests for app_v2 shell (16 tests) |

## INFRA Requirements Verification

| Req | Check | Result |
|-----|-------|--------|
| INFRA-01 | `from app_v2.main import app; print(app.title)` → `PBM2 v2.0 Bootstrap Shell` | PASS |
| INFRA-02 | `htmx:beforeSwap` in JS; `htmx-error-container` in base.html; custom 404.html with nav | PASS |
| INFRA-03 | lifespan sets `app.state.db`, `.settings`, `.agent_registry`; verified by test | PASS |
| INFRA-04 | All assets under `/static/vendor/`; `grep -cE "cdn.jsdelivr\|unpkg.com" base.html` = 0 | PASS |
| INFRA-05 | `grep -c "^async def" app_v2/routers/*.py` = 0 | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_get_root_marks_overview_active false match on `<title>`**
- **Found during:** Task 3 test run
- **Issue:** `body.find("Overview")` matched the first occurrence in `<title>Overview — PBM2 v2.0</title>`, not the nav link. The 200-char backwards window from the title occurrence contained no `active` class, causing the test to fail.
- **Fix:** Changed the test to locate `nav nav-tabs` section first, then search for "Overview" within that 1000-char window — ensuring the nav-link occurrence is found.
- **Files modified:** `tests/v2/test_main.py`
- **Commit:** `daff565`

## Known Stubs

The following are **intentional** Phase 1 stubs — documented per plan and will be replaced in named phases:

| Stub | File | Line | Resolving Phase |
|------|------|------|-----------------|
| `placeholder_message = "Coming in Phase 4 — pivot grid port from v1.0."` | `app_v2/routers/root.py` | 35 | Phase 4 (Browse tab) |
| `placeholder_message = "Coming in Phase 5 — NL agent port from v1.0."` | `app_v2/routers/root.py` | 45 | Phase 5 (Ask tab) |
| `app.state.agent_registry = {}` (empty, not populated) | `app_v2/main.py` | 49 | Phase 3/5 (get_agent factory) |
| `app.state.db = None` when no DB configured | `app_v2/main.py` | 54 | Phase 2+ (requires real DB config) |

These stubs do not prevent the plan's goal (Bootstrap shell serving HTTP 200 at /, /browse, /ask with vendored assets and error handling). They are intentional scaffolding.

## Threat Flags

No new security surface beyond what the threat model documents. All T-03-* mitigations implemented:

| Threat ID | Status |
|-----------|--------|
| T-03-01 StaticFiles path traversal | Starlette handles; no app-level guard needed |
| T-03-02 Supply chain for vendored JS | Pinned at exact version, VERSIONS.txt committed |
| T-03-03 Sync-in-async DoS | INFRA-05 enforced — `grep -c "^async def" routers/*.py` = 0 |
| T-03-04 HTMX 4xx silent discard | htmx-error-handler.js + #htmx-error-container in place |
| T-03-05 Default JSON 404 | Custom exception_handler for StarletteHTTPException renders Bootstrap 404.html |
| T-03-06 500 exception string leakage | Only `type(exc).__name__` rendered, not `str(exc)` |
| T-03-07 hx-boost on tab nav | No hx-boost on nav — plain `<a href>` links only |
| T-03-10 HTMX 4.0 alpha CDN | Vendored at 2.0.10; no CDN in base.html |

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `app_v2/__init__.py` exists | FOUND |
| `app_v2/main.py` exists | FOUND |
| `app_v2/routers/root.py` exists | FOUND |
| `app_v2/templates/base.html` exists | FOUND |
| `app_v2/templates/404.html` exists | FOUND |
| `app_v2/templates/500.html` exists | FOUND |
| `app_v2/static/js/htmx-error-handler.js` exists | FOUND |
| `app_v2/static/vendor/bootstrap/bootstrap.min.css` exists (232KB) | FOUND |
| `app_v2/static/vendor/htmx/htmx.min.js` exists (51KB) | FOUND |
| `app_v2/static/vendor/bootstrap-icons/bootstrap-icons.css` exists | FOUND |
| `app_v2/static/vendor/bootstrap-icons/fonts/bootstrap-icons.woff2` exists | FOUND |
| `tests/v2/test_main.py` exists (16 tests) | FOUND |
| Commit 54e0d4c (vendor assets) | FOUND |
| Commit 174c92d (app_v2 shell) | FOUND |
| Commit daff565 (smoke tests) | FOUND |
| `from app_v2.main import app` exits 0 | OK |
| pytest tests/v2/test_main.py — 16 passed | OK |
| pytest tests/ — 199 passed, 0 failed | OK |
| `grep -c "^async def" app_v2/routers/*.py` = 0 | OK |
| `grep -cE "cdn.jsdelivr\|unpkg.com" app_v2/templates/base.html` = 0 | OK |
