---
phase: 05-overview-redesign
plan: 04
subsystem: routes
tags: [routes, fastapi, htmx, hx-push-url, hx-redirect, url-roundtrip, overview, sync-def]
requires:
  - app_v2/services/overview_grid_service.py::build_overview_grid_view_model
  - app_v2/services/overview_grid_service.py::OverviewGridViewModel
  - app_v2/services/overview_grid_service.py::FILTERABLE_COLUMNS
  - app_v2/services/overview_store.py::load_overview
  - app_v2/services/overview_store.py::add_overview
  - app_v2/services/overview_store.py::DuplicateEntityError
  - app_v2/services/overview_filter.py::has_content_file
  - app_v2/services/cache.py::list_platforms
  - app_v2/services/llm_resolver.py::resolve_active_backend_name
provides:
  - GET / and GET /overview (stacked decorators on overview_page; URL-state filter+sort)
  - POST /overview/grid (block_names=["grid","count_oob","filter_badges_oob"], HX-Push-Url canonical)
  - POST /overview/add (HTTP 200 + HX-Redirect: /overview on success per D-OV-11)
  - _resolve_curated_pids() — overview_store wrapper
  - _parse_filter_dict() — bundles 6 form lists into service-shape dict
  - _build_overview_url() — canonical /overview?... URL composer (urlencode + quote_via=quote, %20 spaces)
affects:
  - app_v2/templates/overview/index.html (Plan 05-05 will rewrite to consume `vm` instead of legacy keys)
  - tests/v2/test_overview_routes.py (legacy assertions on removed routes will fail until Plan 05-06 rewrites)
  - tests/v2/test_overview_filter.py (D-OV-14 — slated for DELETION in Plan 05-06)
tech-stack:
  added:
    - urllib.parse (canonical URL builder)
  patterns:
    - "Stacked route decorators (`@router.get('/') + @router.get('/overview')`) for two URLs → one handler"
    - "Sync `def` everywhere (INFRA-05) — FastAPI dispatches to threadpool"
    - "GET query params: `Annotated[list[str], Query(default_factory=list)]` WITHOUT literal `=[]` default (Phase 4 04-02 lesson)"
    - "POST form params: `Annotated[list[str], Form()] = []` (Pydantic accepts Form with literal default)"
    - "Server-set HX-Push-Url for canonical URLs (Pitfall 2 from Phase 4 — keeps shareable URL out of /grid POST path)"
    - "HX-Redirect for full-page reload after add (D-OV-11) — simpler than synthesizing a one-row swap"
    - "Plain-text 4xx Response (instead of template render) — decouples router from Plan 05-05 template deletions"
key-files:
  created: []
  modified:
    - app_v2/routers/overview.py
decisions:
  - D-OV-04 implementation: replace legacy filter routes with /overview/grid + canonical URL via HX-Push-Url
  - D-OV-11 implementation: add-platform success returns 200 + HX-Redirect (no fragment swap)
  - D-OV-13 URL shape: repeated keys for multi-value filters; urllib.parse.urlencode with quote_via=urllib.parse.quote (%20 spaces, NOT + signs)
  - Legacy helpers _entity_dict + _build_overview_context kept for transitional template render — they become dead code after Plan 05-05 rewrites overview/index.html, removable in a follow-up cleanup
  - GET signature drops literal `=[]` defaults on Query(default_factory=list) params — Phase 4 04-02 documented Pydantic v2.13 + FastAPI 0.136 reject the combination
metrics:
  duration: ~10 min
  tasks_completed: 1
  files_changed: 1
  insertions: 223
  deletions: 162
  completed_date: 2026-04-28
---

# Phase 05 Plan 04: Overview Router Rewire (D-OV-04 + D-OV-11) Summary

Replace Phase 2's legacy filter routes with the Phase 4-style GET /overview + POST /overview/grid split, route both `GET /` and `GET /overview` to one handler, remove DELETE /overview/<pid>, and switch POST /overview/add success to HX-Redirect per D-OV-11.

## Final Route Inventory (`app_v2/routers/overview.py`)

| Path                  | Method | Handler           | Purpose                                                                 |
| --------------------- | ------ | ----------------- | ----------------------------------------------------------------------- |
| `/`                   | GET    | `overview_page`   | Full-page render (root URL stays Overview's home)                       |
| `/overview`           | GET    | `overview_page`   | Same handler, second decorator — canonical Overview URL                  |
| `/overview/add`       | POST   | `add_platform`    | Add to curated list; success → 200 + `HX-Redirect: /overview` (D-OV-11) |
| `/overview/grid`      | POST   | `overview_grid`   | Fragment swap (3 blocks) + `HX-Push-Url` canonical URL (D-OV-04)        |

**Routes removed (D-OV-04):**
- `DELETE /overview/{platform_id}` — Remove button gone per user lock
- `POST /overview/filter` — replaced by `/overview/grid`
- `POST /overview/filter/reset` — clear-all is a fragment swap with empty form fields

**FastAPI app boot smoke (verified):**
```
['/', '/overview', '/overview/add', '/overview/grid']
```

## Imports Minimized

| Removed                                            | Reason                                              |
| -------------------------------------------------- | --------------------------------------------------- |
| `HTTPException`                                    | DELETE handler is gone (only consumer)              |
| `fastapi.Path`                                     | DELETE handler is gone (only consumer)              |
| `remove_overview`                                  | DELETE handler is gone                              |
| `apply_filters`                                    | Service handles filtering internally                |
| `count_active_filters`                             | `vm.active_filter_counts` carries this              |

| Added                                                                             | Why                                              |
| --------------------------------------------------------------------------------- | ------------------------------------------------ |
| `urllib.parse`                                                                    | Canonical URL builder (`_build_overview_url`)    |
| `Query` (from fastapi)                                                            | GET filter+sort param parsing                    |
| `FILTERABLE_COLUMNS`, `OverviewGridViewModel`, `build_overview_grid_view_model` (from `app_v2.services.overview_grid_service`) | Plan 05-03 service surface |

| Kept (rationale)                                   |
| -------------------------------------------------- |
| `has_content_file` — used by legacy `_entity_dict` (transitional helper for Phase 2 template; dies after Plan 05-05) |

## Helpers Added

```python
def _resolve_curated_pids() -> list[str]: ...          # overview_store → list[platform_id]
def _parse_filter_dict(status, customer, ...) -> dict[str, list[str]]: ...
def _build_overview_url(filters, sort_col, sort_order) -> str: ...
```

## Sample `_build_overview_url` Outputs

Verified by direct invocation:

| Input                                                           | Output                                                         |
| --------------------------------------------------------------- | -------------------------------------------------------------- |
| `({"status": ["open", "done"]}, "start", "desc")`               | `/overview?status=open&status=done&sort=start&order=desc`      |
| `({"customer": ["Acme Corp", "Foo Bar"]}, "start", "desc")`     | `/overview?customer=Acme%20Corp&customer=Foo%20Bar&sort=start&order=desc` |
| `({}, "", "")`                                                  | `/overview`                                                    |

Spaces encode as `%20` (URL-style), NOT `+` (form-style) — Pitfall 6 from Phase 4 D-32, enforced via `urllib.parse.urlencode(pairs, quote_via=urllib.parse.quote)`.

## Legacy Template Compatibility (Wave 3 transitional)

Both `GET /` and `GET /overview` pass BOTH context shapes in the same `ctx` dict:

| Key set                                                                                                       | Consumed by                                       |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| Legacy: `entities`, `all_platform_ids`, `filter_brands`, `filter_socs`, `filter_years`, `selected_*`, `active_filter_count`, `filters_open`, `backend_name`, `placeholder_message`, `active_tab`, `page_title` | Phase 2's existing `overview/index.html` (until Plan 05-05) |
| New: `vm` (OverviewGridViewModel), `selected_filters`, `active_filter_counts`, `sort_col`, `sort_order`        | Plan 05-05's rewritten `overview/index.html`      |

Both key sets coexisting is harmless — Jinja2 only reads what the template asks for. Once Plan 05-05 rewrites the template to consume only `vm`-related keys, the legacy keys silently become dead context entries (no perf impact, no cleanup required this plan).

## D-OV-11 Add-Platform Behavior Change

| Outcome           | HTTP | Body                                                            | Header                  |
| ----------------- | ---- | --------------------------------------------------------------- | ----------------------- |
| Success           | 200  | (empty)                                                         | `HX-Redirect: /overview` |
| Unknown platform  | 404  | `Unknown platform: {pid}. Choose from the dropdown.` (text/plain) | (none)                  |
| Already in list   | 409  | `Already in your overview: {pid}` (text/plain)                  | (none)                  |
| Regex failure     | 422  | (FastAPI default)                                               | (none)                  |

The 4xx text responses are surfaced by the global HTMX `htmx:beforeSwap` handler (Phase 1 INFRA-02) — same UX as before, just with text instead of an `_filter_alert.html` Bootstrap alert. This decoupling is deliberate: Plan 05-05 will delete `overview/_filter_alert.html`, and 05-04's add route must keep working through that deletion.

## Pydantic v2.13 + FastAPI 0.136 Compatibility (Phase 4 04-02 lesson reapplied)

GET query params use `Annotated[list[str], Query(default_factory=list)]` WITHOUT a literal `= []` default. The combination of both raises:

```
TypeError: cannot specify both default and default_factory
```

— exactly as documented in Phase 4 Plan 04-02 deviation. POST form params, by contrast, accept `Annotated[list[str], Form()] = []` (Pydantic treats `Form` differently from `Query`). The router file's `overview_page` (GET) and `overview_grid` (POST) signatures therefore look superficially asymmetric but follow the locked Phase 4 contract precisely. See inline comment on `overview_page` for the rationale.

## Tests

Ran the non-legacy v2 test set (per plan acceptance criterion):

```
.venv/bin/pytest tests/v2/test_main.py tests/v2/test_browse_routes.py
                 tests/v2/test_browse_service.py tests/v2/test_phase04_invariants.py
                 tests/v2/test_content_routes.py tests/v2/test_summary_routes.py
                 tests/v2/test_content_store_frontmatter.py
                 tests/v2/test_overview_grid_service.py -x -q
```

**Result: 144 passed, 1 skipped in 11.43s** (skip is the documented Phase 1 stub-test tombstone in `test_main.py`).

## Plan 05-06 Dependency

Two test files contain assertions on routes this plan removed:

| File                              | Status                                        |
| --------------------------------- | --------------------------------------------- |
| `tests/v2/test_overview_routes.py` | Legacy assertions on POST /overview/filter, POST /overview/filter/reset, DELETE /overview/{pid}, and 200+template responses on POST /overview/add will fail. **Plan 05-06 owns the rewrite.** |
| `tests/v2/test_overview_filter.py` | Targets the deleted `<select>`-based filter UI. **D-OV-14 — slated for DELETION in Plan 05-06.** |

This is documented in the plan's `<verification>` section. Plan 05-04's completion gate explicitly excludes both files; full overview-routes test coverage is the Plan 05-06 deliverable.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Cannot specify both default and default_factory in Query**

- **Found during:** Task 1 verification (`.venv/bin/python -c "from app_v2.routers.overview import router..."`)
- **Issue:** Plan body specified `Annotated[list[str], Query(default_factory=list)] = []` for the 6 GET filter params. Pydantic v2.13.x + FastAPI 0.136.x raise `TypeError: cannot specify both default and default_factory` at module-import time, blocking app boot.
- **Fix:** Drop the literal `= []` defaults on the GET filter params (keep `default_factory=list` only). POST `Form()` params correctly retain the `= []` literal — Pydantic accepts that combination with Form. Inline comment added quoting Phase 4 Plan 04-02's deviation note.
- **Files modified:** `app_v2/routers/overview.py` (lines 194-199)
- **Commit:** `c606a81`

The exact same incompatibility was discovered and fixed in Phase 4 Plan 04-02 (browse router) — the lesson was logged in STATE.md decisions but the Plan 05-04 body re-specified the broken pattern. This is a Rule 3 auto-fix; future plans should reference the Phase 4 04-02 idiom directly.

## Self-Check: PASSED

**Files:**
- FOUND: `app_v2/routers/overview.py` (modified, 370 lines)
- FOUND: `.planning/phases/05-overview-redesign/05-04-SUMMARY.md` (this file)

**Commits:**
- FOUND: `c606a81` `feat(05-04): rewire overview router for D-OV-04 (GET /overview + POST /overview/grid)`

**Smoke checks:**
- FastAPI app boots; overview routes = `['/', '/overview', '/overview/add', '/overview/grid']` — exactly the 4 required, none of the 3 forbidden
- All 21 acceptance grep checks pass (decorators, imports, helpers, headers, block_names)
- 144 non-legacy v2 tests green (1 documented Phase 1 skip)
- `_build_overview_url({"status": ["open", "done"]}, "start", "desc")` returns the canonical `/overview?status=open&status=done&sort=start&order=desc`
