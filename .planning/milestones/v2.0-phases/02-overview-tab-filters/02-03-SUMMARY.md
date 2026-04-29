---
phase: "02"
plan: "03"
subsystem: overview-filters
tags:
  - overview
  - filters
  - htmx
  - jinja2-blocks
  - oob-swap
  - path-traversal-defense
  - tdd
dependency_graph:
  requires:
    - app_v2.routers.overview._build_overview_context (Plan 02-02)
    - app_v2.routers.overview._entity_dict (Plan 02-02)
    - app_v2.routers.overview.PLATFORM_ID_PATTERN (Plan 02-02)
    - app_v2.services.overview_store.load_overview (Plan 02-01)
    - app_v2.data.platform_parser.parse_platform_id (Plan 02-01)
    - app_v2.data.soc_year.get_year (Plan 02-01)
    - app_v2.templates.templates (Phase 1)
    - app_v2/templates/overview/index.html (Plan 02-02 — entity_list block + OOB badge already wired)
  provides:
    - app_v2.services.overview_filter.apply_filters
    - app_v2.services.overview_filter.count_active_filters
    - app_v2.services.overview_filter.has_content_file
    - POST /overview/filter (filter_overview)
    - POST /overview/filter/reset (reset_filters)
    - app_v2.routers.overview.CONTENT_DIR (module constant)
  affects:
    - 03-xx (Phase 3 will read+write CONTENT_DIR/<pid>.md; constant already in place)
tech_stack:
  added: []
  patterns:
    - TDD red-green: failing tests committed before implementation (per task)
    - Pure-function service module (no FastAPI imports in overview_filter.py)
    - Path.resolve() + Path.relative_to() defense in depth (Pitfall 2)
    - Sync def routes only (Pitfall 4 / INFRA-05)
    - Jinja2Blocks block_name="entity_list" for HTMX fragment rendering
    - HTMX OOB swap embedded inside the entity_list block — present on every response
    - Stateless filter (no server-side filter selection cache)
key_files:
  created:
    - app_v2/services/overview_filter.py
    - tests/v2/test_overview_filter.py
  modified:
    - app_v2/routers/overview.py (added CONTENT_DIR constant, two new routes, overview_filter import)
decisions:
  - "year filter normalization accepts str ('2022') OR int (2022); unparseable strings map to sentinel year_int=-1 producing zero matches rather than silently ignoring the filter — safer UX (user sees zero-results state and can clear)"
  - "has_content_file uses Path.resolve() on BOTH base and candidate then candidate.relative_to(base) — simpler and more robust than string-prefix comparison; ValueError from relative_to is the documented signal for traversal"
  - "CONTENT_DIR is a module-level Path constant on app_v2.routers.overview (not on the service) — tests monkeypatch the route module so the route uses tmp_path/content/platforms; service stays pure with content_dir as an injected parameter"
  - "filter routes call list_platforms via try/except (same pattern as Plan 02-02 GET /) — datalist population is non-fatal; production with no DB still serves the filter response"
  - "POST /overview/filter/reset is stateless — there is no server-stored filter selection to clear; the route simply returns the unfiltered list with active_filter_count=0 (OOB badge gets d-none)"
metrics:
  duration_seconds: 369
  completed_date: "2026-04-25"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 1
  tests_added: 32
  tests_total: 290
---

# Phase 02 Plan 03: Overview Filters Summary

**One-liner:** POST /overview/filter and POST /overview/filter/reset routes plus a pure-function `overview_filter` service with `apply_filters` (D-21 year-None semantics), `count_active_filters`, and `has_content_file` (Pitfall 2 path-traversal defense) — completing the Overview tab user-visible surface for Phase 2.

## What Was Built

### Task 1: overview_filter Service (pure functions)

**`app_v2/services/overview_filter.py`** (~120 lines)

| Function | Contract |
|----------|----------|
| `count_active_filters(brand, soc, year, has_content) -> int` | Returns 0–4; treats None / "" / False as inactive |
| `has_content_file(platform_id, content_dir) -> bool` | True iff `content_dir/<pid>.md` is a regular file inside content_dir; never raises |
| `apply_filters(entities, brand, soc, year, has_content, content_dir) -> list[dict]` | AND-semantic filter; year accepted as str OR int |

**D-21 year-None handling:** when year filter is empty/None, entities with `year=None` are INCLUDED. When year filter is set to a specific year, entities with `year=None` are EXCLUDED. This was verified by two dedicated tests (`test_year_filter_excludes_year_none_entities`, `test_year_empty_string_keeps_all_entities_including_none`) and again at the route layer (`test_post_filter_year_2022_excludes_year_none_entity`, `test_post_filter_empty_year_includes_year_none_entity`).

**Pitfall 2 path-traversal defense in `has_content_file`:**
```python
base = content_dir.resolve()
candidate = (content_dir / f"{platform_id}.md").resolve()
candidate.relative_to(base)  # raises ValueError if outside
return candidate.is_file()
```
`relative_to` is the documented Path API for asserting containment; ValueError + OSError are caught and return False. A platform_id like `"../outside"` or `"../../etc/passwd"` cannot read files outside content_dir even if such files exist (verified by `test_has_content_false_when_platform_id_escapes_dir`).

**Year filter robustness:** unknown/malformed year values (e.g. unparseable strings) map to sentinel year_int=-1 → no entity matches → zero-results state shown to user. Safer than ignoring a malformed filter.

No FastAPI imports — verified by `grep -c -E 'from fastapi|import fastapi' = 0`.

### Task 2: Filter Routes + CONTENT_DIR Constant

**`app_v2/routers/overview.py`** (extended)

Added at module top:
```python
CONTENT_DIR: _Path = _Path("content/platforms")
```

| Route | Method | Returns |
|-------|--------|---------|
| `filter_overview` | POST /overview/filter | 200 with entity_list fragment + OOB badge |
| `reset_filters` | POST /overview/filter/reset | 200 with full unfiltered entity_list + OOB badge (count=0) |

Both routes are `def` (not `async def`) — verified by `grep -c '^async def' app_v2/routers/overview.py = 0` (INFRA-05 preserved across all 5 Overview routes).

`block_name="entity_list"` is used in BOTH routes — verified by `grep -c 'block_name="entity_list"' = 2`.

The OOB badge `<span id="filter-count-badge" hx-swap-oob="true" ...>` was already embedded inside the entity_list block by Plan 02-02; Plan 02-03 routes simply pass `active_filter_count` through the context. The badge gets the `d-none` class when count=0 (badge hidden) and shows the count integer when > 0.

## HTTP Contract Matrix

| Scenario | Status | Body |
|----------|--------|------|
| POST /overview/filter (no fields, all empty) | 200 | Full entity_list fragment + OOB badge with d-none |
| POST /overview/filter (brand=Samsung) | 200 | Samsung entities only + OOB badge showing "1" |
| POST /overview/filter (brand=Samsung, year=2023) | 200 | One entity (AND semantics) + OOB badge showing "2" |
| POST /overview/filter (year=2022) | 200 | year=2022 entities; year=None entity EXCLUDED (D-21) |
| POST /overview/filter (year="") | 200 | All entities including year=None (D-21) |
| POST /overview/filter (no matches) | 200 | "No platforms match the current filters." copy |
| POST /overview/filter (has_content=1) | 200 | Only entities with `<pid>.md` in CONTENT_DIR |
| POST /overview/filter/reset | 200 | Full unfiltered list + d-none OOB badge |

All filter responses are FRAGMENTS — verified by `<nav class="navbar"` and `<html` not appearing in body (`test_post_filter_response_is_fragment_not_full_page`).

## Test Count

| File | Tests Added | Coverage |
|------|-------------|----------|
| tests/v2/test_overview_filter.py (Task 1) | 19 | apply_filters all branches, count_active_filters, has_content_file (existence, missing, traversal, weird inputs) |
| tests/v2/test_overview_filter.py (Task 2) | 13 | POST /filter happy paths, brand/soc/year (D-21 incl/excl), multi-AND, zero matches copy, fragment-not-page, OOB badge content+count, has_content true with .md files, traversal defense, reset full list + d-none, regression with add/delete |
| **Total** | **32** | |

**Regression bar:** 258 prior tests + 32 new = **290 total (all passing)**. Target was ≥ 240. Easily exceeded.

## Filter Form → Server → Response Contract

```
HTMX form submit → POST /overview/filter
   form fields: brand, soc, year, has_content (each optional, "" or absent = no filter)

Server:
   has_content_bool = (has_content == "1")
   count = count_active_filters(brand, soc, year, has_content_bool)
   entities = [_entity_dict(e) for e in load_overview()]
   filtered = apply_filters(entities, brand or None, soc or None, year or None,
                            has_content_bool, CONTENT_DIR)
   ctx = _build_overview_context(filtered, all_platform_ids, ..., active_filter_count=count)
   return templates.TemplateResponse(request, "overview/index.html", ctx,
                                     block_name="entity_list")

Response (HTMX):
   <ul#overview-list innerHTML> swapped with the entity_list block fragment
   OOB <span id="filter-count-badge" hx-swap-oob="true"> swapped into shell
```

The OOB badge update is automatic — every filter/reset/add/remove response carries it because the `<span hx-swap-oob>` lives inside the entity_list block (Plan 02-02 design).

## Integration Confirmation

- Adding a platform via the typeahead → entity row prepended (Plan 02-02 path)
- Filtering by that platform's brand → narrowed entity list, OOB badge increments to 1
- Adding a second filter (year) → list narrows further, OOB badge increments to 2 (AND semantics)
- "Clear all" link (visible when count > 0) → POST /overview/filter/reset → full list, badge becomes d-none
- All operations stay within the page (no full reload) — confirmed by fragment response containing no navbar / no <html>

## Deviations from Plan

None — plan executed exactly as written. All TDD RED→GREEN cycles completed in order. All acceptance criteria met. No CLAUDE.md violations.

## Known Stubs

None. All filter logic is fully implemented with real behavior.

The CONTENT_DIR constant points at `content/platforms` which does not yet exist on disk — that is correct: Phase 3 will create the directory and add markdown files. In Phase 2 the `has_content` filter simply returns False for every entity until those files exist (the directory itself need not exist; `Path.resolve()` does not fail on missing dirs and the subsequent `relative_to` + `is_file` correctly return False).

## Threat Flags

No new threat surface beyond what the plan's threat model covers (T-02-03-01 through T-02-03-09). All mitigations applied:
- T-02-03-01 (Tampering / path traversal): `has_content_file` resolve()+relative_to() — verified by `test_has_content_false_when_platform_id_escapes_dir`
- T-02-03-02 (DoS / ReDoS): no regex on filter values — only string equality
- T-02-03-04 (Spoofing / unknown filter values): unknown values produce empty list, not 500 — verified by `test_unknown_brand_returns_empty` and `test_post_filter_zero_matches_returns_no_platforms_match_copy`
- T-02-03-06 (EoP / sync DB in async): both routes are def — verified by grep
- T-02-03-09 (Tampering / OOB silent failure): badge lives inside the persistent entity_list block which is always swapped before OOB processing

## Self-Check: PASSED

Files created:
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/app_v2/services/overview_filter.py` — exists
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/tests/v2/test_overview_filter.py` — exists

Files modified:
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/app_v2/routers/overview.py` — exists (now contains filter_overview + reset_filters + CONTENT_DIR)

Commits:
- 4a3295b: test(02-03): add failing tests for overview_filter service (TDD RED)
- 9e9b9df: feat(02-03): implement overview_filter service (FILTER-04 infra for FILTER-01..03)
- c480c41: test(02-03): add failing tests for POST /overview/filter + /reset (TDD RED)
- 2f7dbb3: feat(02-03): implement POST /overview/filter and /filter/reset with OOB badge swap (FILTER-01, FILTER-02, FILTER-03)

Acceptance criteria (Task 1):
- `^def apply_filters` count: 1 ✓
- `^def count_active_filters` count: 1 ✓
- `^def has_content_file` count: 1 ✓
- `relative_to` count: 3 (≥1) ✓
- `resolve()` count: 2 ✓
- No FastAPI imports ✓
- 19 unit tests pass ✓

Acceptance criteria (Task 2):
- `^def filter_overview` count: 1 ✓
- `^def reset_filters` count: 1 ✓
- `^async def` count: 0 (INFRA-05 preserved) ✓
- `block_name="entity_list"` count: 2 ✓
- `from app_v2.services.overview_filter import` count: 1 ✓
- `CONTENT_DIR` count: 2 ✓
- 32 total filter tests pass (19 unit + 13 TestClient) ✓
- 18 prior Plan 02-02 tests still pass ✓
- Full regression: 290 tests pass (target ≥240) ✓
