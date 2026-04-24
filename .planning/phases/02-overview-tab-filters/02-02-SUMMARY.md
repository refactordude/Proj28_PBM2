---
phase: "02"
plan: "02"
subsystem: overview-routes
tags:
  - overview
  - fastapi
  - htmx
  - jinja2-blocks
  - templates
  - routes
  - tdd
dependency_graph:
  requires:
    - app_v2.data.platform_parser.parse_platform_id
    - app_v2.data.soc_year.get_year
    - app_v2.services.overview_store (load_overview, add_overview, remove_overview, DuplicateEntityError)
    - app_v2.services.cache.list_platforms
    - app_v2.templates.templates (Jinja2Blocks instance)
    - app_v2/templates/base.html
  provides:
    - GET / (overview_page — renders full Overview tab)
    - POST /overview/add (add_platform — returns entity row fragment or error alert)
    - DELETE /overview/{platform_id} (remove_platform — returns empty 200 or 404)
    - app_v2/templates/overview/index.html (full page + entity_list block)
    - app_v2/templates/overview/_entity_row.html (single entity row partial)
    - app_v2/templates/overview/_filter_alert.html (409/404 alert fragment)
    - _build_overview_context (helper for Plan 02-03 filter route)
  affects:
    - 02-03 (imports _build_overview_context; adds POST /overview/filter + /overview/filter/reset)
    - 03-xx (Phase 3 removes `disabled` from AI Summary button + wires content pages)
tech_stack:
  added: []
  patterns:
    - TDD red-green: failing tests committed before implementation
    - Jinja2Blocks block_name pattern: block entity_list for HTMX fragment rendering
    - PLATFORM_ID regex via FastAPI Form(pattern=...) and Path(pattern=...) — defense-in-depth
    - Exception-safe list_platforms call (catches all exceptions; degrades gracefully to empty list)
    - All routes are def (sync) per INFRA-05
key_files:
  created:
    - app_v2/routers/overview.py
    - app_v2/templates/overview/index.html
    - app_v2/templates/overview/_entity_row.html
    - app_v2/templates/overview/_filter_alert.html
    - tests/v2/test_overview_routes.py
  modified:
    - app_v2/main.py (added include_router(overview.router) before root)
    - app_v2/routers/root.py (removed Phase 1 GET / stub)
decisions:
  - "list_platforms always called (not guarded by db is not None) — wrapped in try/except so monkeypatched version works in tests without a real DB; production degrades gracefully to empty datalist"
  - "Fake catalog uses 3-part PLATFORM_IDs (brand_model_soc) so parse_platform_id correctly extracts soc_raw for year badge rendering in tests"
  - "Phase 1 GET / stub removed from root.py — overview router owns /; root.py retains /browse and /ask stubs only"
  - "_build_overview_context is a public helper (not prefixed with _) so Plan 02-03 can import it for filter route re-renders"
metrics:
  duration_seconds: 685
  completed_date: "2026-04-24"
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 2
  tests_added: 18
  tests_total: 258
---

# Phase 02 Plan 02: Overview Routes + Templates Summary

**One-liner:** Three sync FastAPI routes (GET /, POST /overview/add, DELETE /overview/{pid}) with three Jinja2 templates — the complete user-visible Overview tab surface backed by the Plan 02-01 data layer.

## What Was Built

### Task 1: Three Jinja2 Templates

**`app_v2/templates/overview/_entity_row.html`**

Single `<li class="list-group-item d-flex align-items-center">` partial. Left-to-right: PLATFORM_ID title (fw-bold fs-5), Brand badge (bg-primary), SoC badge (bg-info text-dark), Year badge (bg-success when known / bg-secondary when unknown), spacer (me-auto), navigate link (bi-arrow-right-circle), disabled AI Summary button with Phase 3 tooltip, HTMX Remove button (bi-x, hx-delete, hx-confirm). All verbatim copy strings from 02-UI-SPEC.md.

**`app_v2/templates/overview/_filter_alert.html`**

Dismissible Bootstrap alert fragment. Context keys: `alert_level` (warning/danger) and `message`. Used for 409 duplicate and 404 unknown responses.

**`app_v2/templates/overview/index.html`**

Full page extending `base.html`. Contains:
- Add platform form (hx-post="/overview/add", datalist typeahead, hx-on::after-request reset)
- Collapsible filter block (`<details id="filter-details">`) with Brand/SoC/Year selects and Has-content checkbox, all carrying `data-filter` attributes and `hx-trigger="change"` — structurally complete for Plan 02-03 to add route handler
- `{% block entity_list %}` — HTMX fragment target containing OOB filter-count-badge swap, entity rows (via `{% include "overview/_entity_row.html" %}`), empty-state alert, or zero-results message
- localStorage persistence script for filter block open/closed state

### Task 2: Overview Router + App Wiring

**`app_v2/routers/overview.py`** (~180 lines)

| Route | Method | Status codes | Returns |
|-------|--------|-------------|---------|
| `overview_page` | GET / | 200 | Full `overview/index.html` |
| `add_platform` | POST /overview/add | 200 / 404 / 409 / 422 | `_entity_row.html` / `_filter_alert.html` / FastAPI validation error |
| `remove_platform` | DELETE /overview/{pid} | 200 / 404 / 422 | Empty body / HTTPException / FastAPI validation error |

All three routes are `def` (not `async def`) — INFRA-05. PLATFORM_ID regex `^[A-Za-z0-9_\-]{1,128}$` enforced at:
1. `Form(pattern=PLATFORM_ID_PATTERN)` on POST /overview/add
2. `Path(pattern=PLATFORM_ID_PATTERN)` on DELETE /overview/{platform_id}

**`_build_overview_context` helper** — public function (importable by Plan 02-03's filter route). Builds the full template context including filter dropdown options (derived from current curated list, not full DB catalog). Year dropdown sorted descending per UI-SPEC.

**`app_v2/main.py`** — `include_router(overview.router)` added BEFORE `include_router(root.router)` (order matters: overview owns GET /).

**`app_v2/routers/root.py`** — Phase 1 `GET /` stub removed. File now contains only `browse_page` (GET /browse) and `ask_page` (GET /ask) with a docstring note that GET / is owned by routers/overview.py.

## HTTP Contract Matrix

| Scenario | Status | Body |
|----------|--------|------|
| GET / (empty store) | 200 | Full page with empty-state alert |
| GET / (entities present) | 200 | Full page with entity rows + badges |
| GET /?tab=overview | 200 | Same as GET / |
| POST /overview/add (valid, in catalog) | 200 | Single `<li>` entity row fragment |
| POST /overview/add (valid, duplicate) | 409 | `_filter_alert.html` with alert-warning |
| POST /overview/add (valid regex, unknown) | 404 | `_filter_alert.html` with alert-danger |
| POST /overview/add (regex fail) | 422 | FastAPI validation error |
| POST /overview/add (missing field) | 422 | FastAPI validation error |
| DELETE /overview/{pid} (exists) | 200 | Empty body |
| DELETE /overview/{pid} (not found) | 404 | HTTPException |
| DELETE /overview/{pid} (regex fail) | 422 | FastAPI validation error |

## PLATFORM_ID Regex Enforcement Sites

1. `Form(pattern=PLATFORM_ID_PATTERN, min_length=1, max_length=128)` in `add_platform` — blocks path traversal and special characters at the HTTP layer before any store or filesystem access
2. `Path(pattern=PLATFORM_ID_PATTERN, min_length=1, max_length=128)` in `remove_platform` — same protection for DELETE path parameter

## Integration Contract for Plan 02-03

Plan 02-03 adds `POST /overview/filter` and `POST /overview/filter/reset`. It will:

```python
from app_v2.routers.overview import _build_overview_context

# Inside the filter route:
ctx = _build_overview_context(
    entities=filtered_entities,
    all_platform_ids=all_platform_ids,
    selected_brand=brand,
    selected_soc=soc,
    selected_year=year,
    selected_has_content=bool(has_content),
    active_filter_count=count,
)
return templates.TemplateResponse(request, "overview/index.html", ctx, block_name="entity_list")
```

The filter form controls (`data-filter` attributes, `hx-trigger="change"`, `hx-post="/overview/filter"`) are already wired in the template. Plan 02-03 is purely a route addition — no template changes needed.

## Test Count

| File | Tests Added | Coverage |
|------|-------------|----------|
| tests/v2/test_overview_routes.py | 18 | GET (empty/entities/datalist/nav/filter/title), POST happy/409/404/422x3, DELETE found/not-found/regex, full-page badges, AI Summary disabled |
| **Total** | **18** | |

**Regression:** 240 prior tests + 18 new = 258 total (all passing). Target was ≥255.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] list_platforms guard removed from GET / and POST /overview/add**
- **Found during:** Task 2 TDD GREEN
- **Issue:** Route originally guarded `list_platforms` call with `if db is not None`, causing the datalist to always be empty in tests (where `db=None` but `list_platforms` is monkeypatched to return fake catalog)
- **Fix:** Removed `if db is not None` guard; wrapped call in `try/except Exception` instead. Monkeypatched version accepts any `db`; production version raises if `db` is None (caught, degrades to empty list). Same behavior in production, correct behavior in tests.
- **Files modified:** app_v2/routers/overview.py
- **Commit:** 84deaff

**2. [Rule 1 - Bug] Fake catalog platform ID corrected to 3-part format**
- **Found during:** Task 2 TDD GREEN — `test_get_root_after_add_shows_entity_row_with_correct_badges` failing
- **Issue:** `Xiaomi13_SM8550` is a 2-part ID; `parse_platform_id("Xiaomi13_SM8550")` gives `("Xiaomi13", "SM8550", "")` — soc_raw is empty, year resolves to None. Test asserted `"2023" in body` which never appeared.
- **Fix:** Changed test fake catalog entry to `Xiaomi13_Pro_SM8550` (3-part: brand=Xiaomi13, model=Pro, soc_raw=SM8550 → year=2023).
- **Files modified:** tests/v2/test_overview_routes.py
- **Commit:** 84deaff

**3. [Rule 1 - Bug] Test page title assertion corrected**
- **Found during:** Task 2 TDD GREEN
- **Issue:** Test asserted `"PBM2 — Overview"` but `base.html` renders `{{ page_title }} — PBM2 v2.0` producing `"Overview — PBM2 v2.0"`.
- **Fix:** Updated assertion to `"Overview — PBM2 v2.0"` with comment explaining the template pattern.
- **Files modified:** tests/v2/test_overview_routes.py
- **Commit:** 84deaff

## Filter Routes NOT Implemented (Deferred to Plan 02-03)

- `POST /overview/filter` — returns entity_list block fragment filtered by brand/soc/year/has_content
- `POST /overview/filter/reset` — returns unfiltered entity_list + OOB badge reset

The template is structurally complete for these routes. Plan 02-03 is purely a route addition.

## Known Stubs

None — all functions fully implemented. AI Summary button is intentionally disabled (not a stub — documented in D-06, deferred to Phase 3).

## Threat Flags

No new threat surface beyond the plan's threat model (T-02-02-01 through T-02-02-10). All mitigations applied: PLATFORM_ID regex at Form + Path validation sites, Jinja2 autoescape active, no `| safe` filter used.

## Self-Check: PASSED

Files created:
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/app_v2/routers/overview.py` — exists
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/app_v2/templates/overview/index.html` — exists
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/app_v2/templates/overview/_entity_row.html` — exists
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/app_v2/templates/overview/_filter_alert.html` — exists
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/tests/v2/test_overview_routes.py` — exists

Commits:
- 2753335: feat(02-02): add Overview tab templates (entity row, filter alert, index)
- 939040b: test(02-02): add failing tests for Overview router (TDD RED)
- 84deaff: feat(02-02): implement Overview routes — GET /, POST /overview/add, DELETE /overview/{pid}
