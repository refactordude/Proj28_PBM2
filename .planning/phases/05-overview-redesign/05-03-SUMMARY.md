---
phase: 05-overview-redesign
plan: 03
subsystem: service
tags: [pydantic-v2, sort, filter, view-model, overview, tdd]

# Dependency graph
requires:
  - phase: 05-overview-redesign-02
    provides: read_frontmatter(platform_id, content_dir) → dict[str, str] memoized by (pid, mtime_ns) on app_v2/services/content_store.py
  - phase: 02-overview-shell
    provides: has_content_file(platform_id, content_dir) → bool on app_v2/services/overview_filter.py
provides:
  - OverviewRow Pydantic v2 model (14 fields — 12 PM keys + platform_id + has_content)
  - OverviewGridViewModel Pydantic v2 model (rows + filter_options + active_filter_counts + sort_col + sort_order + has_content_map)
  - build_overview_grid_view_model orchestrator — pure-Python single source of truth for GET /overview + POST /overview/grid (D-OV-03)
  - Module constants — ALL_METADATA_KEYS, FILTERABLE_COLUMNS (6), SORTABLE_COLUMNS (12), DATE_COLUMNS, DEFAULT_SORT_COL='start', DEFAULT_SORT_ORDER='desc'
  - _parse_iso_date helper — ISO 8601 date parser returning None on malformed input (D-OV-08)
affects: [05-04-routes, 05-05-templates, 05-06-tests-and-invariants]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-pass stable sort to preserve secondary tiebreaker for both asc and desc orders (Python sort stability + reverse= flag)"
    - "Empty-partition pattern — filter empties into separate list, sort + concat at end, so 'sorts to END regardless of order' invariant survives"
    - "filter_options computed across ALL rows (not the filtered subset) — picker dropdowns must always show every available value"
    - "Pure-Python service module — zero FastAPI/Starlette imports, mirrors Phase 4 browse_service.py discipline"
    - "Hard-whitelist sort_col against tuple constant BEFORE getattr — defense against dunder traversal"

key-files:
  created:
    - app_v2/services/overview_grid_service.py
    - tests/v2/test_overview_grid_service.py
  modified: []

key-decisions:
  - "Two-pass stable sort algorithm chosen over functools.cmp_to_key — explicit and readable, with partition + sort-platform_id-asc-then-sort-primary-with-reverse pattern; stable sort means tiebreaker order survives the desc reversal of the primary key"
  - "Empty / None / malformed values partition into a separate list that always sorts platform_id ASC, regardless of primary order — guarantees 'sort to END' invariant from D-OV-08"
  - "filter_options derived from ALL rows (not the filtered subset) — picker UX must let users expand selection; narrowing on filter would create a trapdoor"
  - "_normalize_filters strips non-string and whitespace-only values (T-05-03-05 mitigation) — keeps active_filter_counts honest and prevents non-string filter values from poisoning row-matching"
  - "Title fallback to platform_id (D-OV-09) implemented at build_overview_grid_view_model level (NOT in OverviewRow model) — model stays oblivious to fallback policy; other missing PM fields stay None for template '—' rendering"
  - "read_frontmatter is the ONE point of contact between this service and the filesystem — no os/glob/Path.read_* calls inside this module; has_content_file (also pre-existing, framework-agnostic) is the only other I/O touch"

patterns-established:
  - "Two-pass stable sort for asc/desc with stable secondary tiebreaker — reusable for any future sortable view-model"
  - "Empty-partition + sort-then-concat pattern for 'sorts to END regardless of order' — reusable when null/missing values must always trail"
  - "Hard-whitelist input enum constants BEFORE attribute access — T-05-03-01 mitigation pattern reusable for any column-driven sort/filter"
  - "Test-mode invariant: structural model field set assertion (set(Model.model_fields.keys()) == expected) — locks Pydantic v2 model surface against accidental field drift"

requirements-completed: [OVERVIEW-V2-02, OVERVIEW-V2-04]

# Metrics
duration: 4min
completed: 2026-04-28
---

# Phase 5 Plan 3: Overview Grid Service Summary

**Pure-Python orchestrator (`build_overview_grid_view_model`) returning an `OverviewGridViewModel` Pydantic v2 model — single source of truth for GET /overview + POST /overview/grid; two-pass stable sort with empty-partition pattern preserves D-OV-07 platform_id ASC tiebreaker for both asc/desc and D-OV-08 'empty dates to END regardless of order'.**

## Performance

- **Duration:** ~4 min (235 s)
- **Started:** 2026-04-28T16:05:08+09:00 (TDD RED commit `43d9d60`)
- **Completed:** 2026-04-28T16:08:57+09:00 (TDD GREEN commit `4797893`)
- **Tasks:** 1 (TDD: RED + GREEN; no REFACTOR commit needed)
- **Files created:** 2 (1 service, 1 test)

## Accomplishments

- **OverviewGridViewModel (D-OV-03)** — Pydantic v2 model with the 6 documented fields (`rows`, `filter_options`, `active_filter_counts`, `sort_col`, `sort_order`, `has_content_map`) consumed by both `GET /overview` (full page) and `POST /overview/grid` (fragment swap) in Plan 05-04.
- **OverviewRow (D-OV-09)** — Pydantic v2 row model with 14 fields: `platform_id`, `title` (with fallback), `has_content` (bool), and 11 nullable PM fields (`status`, `customer`, `model_name`, `ap_company`, `ap_model`, `device`, `controller`, `application`, `assignee`, `start`, `end`).
- **Two-pass stable sort algorithm (`_sort_rows`)** — partitions rows into non-empty / empty groups, sorts non-empty by `platform_id` ASC then by primary key with `reverse=(order=='desc')` (Python's stable sort preserves the platform_id ASC ordering inside each primary-key group, even when reversed). Empty group always sorts `platform_id` ASC and concatenates AFTER non-empty, regardless of order. Verified by `test_tiebreaker_platform_id_asc_for_both_orders` (Test 5) and `test_empty_date_sorts_to_end_for_both_orders` (Test 3).
- **Multi-filter set membership (D-OV-13)** — `_row_matches` enforces AND across columns, OR within a column. Verified by `test_multi_filter_and_across_or_within` (Test 9).
- **filter_options invariant** — computed across ALL rows, NOT the filtered subset. Picker dropdowns always show every available option so users can expand selection. Verified by `test_filter_options_use_all_rows_not_filtered_subset` (Test 15).
- **18 unit tests passing** (15 from `<behavior>` + 3 invariant guards on constants and OverviewRow model fields). Full v2 suite: **308 passed, 1 skipped** (was 290+1 before this plan; +18 new, **zero regressions**).

## Task Commits

Each task was committed atomically (TDD pattern: RED → GREEN; no REFACTOR commit needed since GREEN landed clean):

1. **Task 1 RED: failing tests for overview_grid_service** — `43d9d60` (test)
2. **Task 1 GREEN: implement overview_grid_service** — `4797893` (feat)

**Plan metadata:** committed alongside this SUMMARY (final commit).

## Files Created/Modified

- `app_v2/services/overview_grid_service.py` (NEW, 341 lines) — pure-Python service: `OverviewRow` + `OverviewGridViewModel` Pydantic v2 models, `build_overview_grid_view_model` orchestrator, `_parse_iso_date` / `_validate_sort` / `_normalize_filters` / `_sort_rows` helpers, module-level constants (`ALL_METADATA_KEYS`, `FILTERABLE_COLUMNS`, `SORTABLE_COLUMNS`, `DATE_COLUMNS`, `DEFAULT_SORT_COL`, `DEFAULT_SORT_ORDER`).
- `tests/v2/test_overview_grid_service.py` (NEW, 341 lines) — 18 unit tests covering the 15 `<behavior>` cases plus 3 structural invariants. Uses `tmp_path` fixture and `_write_fm` helper to build content files; `_clear_frontmatter_cache` autouse fixture isolates `read_frontmatter` memoization between tests.

## Output spec — explicit answers (per `<output>` block of 05-03-PLAN.md)

### 1. Final shape of `OverviewGridViewModel` (6 fields)

| Field | Type | Purpose |
|---|---|---|
| `rows` | `list[OverviewRow]` | Sorted, filtered platform rows for the current request |
| `filter_options` | `dict[str, list[str]]` | Picker dropdown values per filterable column (6 keys; sorted case-insensitive; no None / empty / em-dash) |
| `active_filter_counts` | `dict[str, int]` | Number of selected values per filterable column (always 6 keys; 0 when filter inactive) |
| `sort_col` | `str` | Resolved sort column (one of `SORTABLE_COLUMNS`; falls back to `'start'`) |
| `sort_order` | `Literal["asc", "desc"]` | Resolved sort order (falls back to `'desc'`) |
| `has_content_map` | `dict[str, bool]` | Per-platform content-file existence (drives Phase 3 D-13 / D-OV-10 AI Summary disabled state) |

### 2. Final shape of `OverviewRow` (14 fields)

| # | Field | Type | Notes |
|---|---|---|---|
| 1 | `platform_id` | `str` | Required; tiebreaker source |
| 2 | `title` | `str` | Required; falls back to `platform_id` (D-OV-09) |
| 3 | `status` | `str \| None` | None → template renders `—` |
| 4 | `customer` | `str \| None` | None → template renders `—` |
| 5 | `model_name` | `str \| None` | None → template renders `—` |
| 6 | `ap_company` | `str \| None` | None → template renders `—` |
| 7 | `ap_model` | `str \| None` | None → template renders `—` |
| 8 | `device` | `str \| None` | None → template renders `—` |
| 9 | `controller` | `str \| None` | None → template renders `—` |
| 10 | `application` | `str \| None` | None → template renders `—` |
| 11 | `assignee` | `str \| None` | None → template renders `—`; supports Korean (e.g. `홍길동`) |
| 12 | `start` | `str \| None` | Raw ISO 8601; sort uses `_parse_iso_date` |
| 13 | `end` | `str \| None` | Raw ISO 8601; sort uses `_parse_iso_date` |
| 14 | `has_content` | `bool` | True iff `content/platforms/<pid>.md` exists; default False |

### 3. Confirmation: NO FastAPI / Starlette imports leaked

```bash
$ grep -cE 'from fastapi|from starlette' app_v2/services/overview_grid_service.py
0
```

Pure Python service module. The only third-party import is `from pydantic import BaseModel`. The only intra-package imports are `from app_v2.services.content_store import read_frontmatter` and `from app_v2.services.overview_filter import has_content_file`.

### 4. Exact `_sort_rows` algorithm chosen + why

**Two-pass stable sort with explicit empty-partition.** Algorithm:

1. **Partition** rows into `non_empty` and `empty`. For date columns: `_parse_iso_date(value) is None` ⇒ empty. For non-date columns: `value is None or value == ""` ⇒ empty.
2. **Stable secondary sort:** `non_empty.sort(key=lambda r: r.platform_id)` — establishes platform_id ASC as the underlying order.
3. **Stable primary sort with reverse:** `non_empty.sort(key=primary_key_fn, reverse=(order=='desc'))` — Python's sort is stable, so equal primary keys preserve the platform_id ASC order from step 2 even when the primary key is reversed for desc.
4. **Empty group always platform_id ASC:** `empty.sort(key=lambda r: r.platform_id)` — independent of primary order.
5. **Concatenate** `non_empty + empty` — empties land at END regardless of asc/desc.

**Why over `functools.cmp_to_key`:** the two-pass approach is more readable (the partition step makes the "sort to END" invariant a structural fact, not an implicit cmp consequence) and reuses Python's optimized C-level sort instead of a Python-level cmp callback. The plan explicitly allowed either approach as long as `<behavior>` tests pass; Test 5 (tiebreaker stable for desc) and Test 3 (empties to END for both asc and desc) both pass with this implementation.

**Why a single `sorted(..., key=..., reverse=desc)` does NOT work:** a single sort with `reverse=True` would also reverse the secondary `platform_id` order inside ties, violating D-OV-07's "tiebreaker is platform_id ASC, ALWAYS (regardless of asc/desc on the primary key)". The two-pass pattern decouples the primary order (toggleable) from the secondary order (locked).

### 5. Confirmation: `read_frontmatter` is the ONE filesystem touchpoint

```bash
$ grep -E '(read_frontmatter|has_content_file|os\.|open\(|Path\(|read_text|stat\()' app_v2/services/overview_grid_service.py
from app_v2.services.content_store import read_frontmatter
from app_v2.services.overview_filter import has_content_file
        fm = read_frontmatter(pid, content_dir)
        has_content = has_content_file(pid, content_dir)
```

Two intra-package helpers reach the filesystem on this service's behalf:
- `read_frontmatter` — sources the per-platform PM metadata dict (the entire row payload). Memoized by `(pid, mtime_ns)` per D-OV-12.
- `has_content_file` — answers a single bool per platform (drives `has_content` and `has_content_map`).

There is no `import os`, no `from pathlib` (the `Path` type is imported via `pathlib`-aware contracts only — `content_dir: Path` parameter — but no `Path` instantiation, no `read_text`, no `stat`). Single source of truth for filesystem I/O preserves Plan 05-02's path-traversal defenses (Pitfall 2 / D-04) without re-opening that attack surface here.

### 6. Test count + edge cases discovered beyond the 15 `<behavior>` cases

**Test count: 18** (plan gate ≥15). Breakdown:

- **Tests 1–15** (the 15 `<behavior>` cases) — all pass.
- **Test 16: `test_constants_filterable_columns_locked`** — pins `FILTERABLE_COLUMNS == ('status', 'customer', 'ap_company', 'device', 'controller', 'application')`. Catches accidental column addition / removal. Locks D-OV-13.
- **Test 17: `test_constants_sortable_columns_has_12_entries_with_dates`** — pins `len(SORTABLE_COLUMNS) == 12` and presence of `'start'` and `'end'`. Locks D-OV-07.
- **Test 18: `test_overview_row_model_fields`** — uses `set(OverviewRow.model_fields.keys())` to assert the model surface is exactly the 14 documented fields. Catches accidental field rename / addition during refactors.

**No additional behavioral edge cases discovered during TDD.** The plan's `<behavior>` block was comprehensive — every case (including the subtle "tiebreaker stays platform_id ASC even for desc" and "filter_options never narrow with current filter" invariants) was already enumerated.

### 7. Plan 05-04 dependency note

Routes will import:

```python
from app_v2.services.overview_grid_service import (
    build_overview_grid_view_model,
    OverviewGridViewModel,
    DEFAULT_SORT_COL,
    DEFAULT_SORT_ORDER,
    FILTERABLE_COLUMNS,
)
```

and call:

```python
# GET /overview
vm = build_overview_grid_view_model(
    curated_pids=overview_store.load_overview(),
    content_dir=CONTENT_DIR,
    filters={
        "status": status,        # FastAPI Query(default_factory=list) for GET
        "customer": customer,
        "ap_company": ap_company,
        "device": device,
        "controller": controller,
        "application": application,
    },
    sort_col=sort,
    sort_order=order,
)

# POST /overview/grid (fragment swap, HTMX)
vm = build_overview_grid_view_model(
    curated_pids=overview_store.load_overview(),
    content_dir=CONTENT_DIR,
    filters={
        "status": status,        # FastAPI Annotated[list[str], Form()] for POST
        "customer": customer,
        # ... etc.
    },
    sort_col=sort,
    sort_order=order,
)
```

The Phase 4 lesson from Plan 04-02 applies: GET query params use `Query(default_factory=list)`, POST form params keep `Form()` with literal `= []` default (Pydantic v2.13.x rejects mixing `default_factory` and literal default on `Form`).

## Decisions Made

(See `key-decisions` frontmatter and accumulated-context entries.)

- Two-pass stable sort over `functools.cmp_to_key` — readability + C-level sort performance.
- Empty-partition pattern over `(is_empty, primary, platform_id)` tuple key — guarantees "to END regardless of order" structurally.
- `filter_options` from ALL rows, not the filtered subset — picker UX invariant.
- `_normalize_filters` strips non-string + whitespace-only values — T-05-03-05 mitigation.
- Title fallback in orchestrator (NOT in `OverviewRow` model) — model stays policy-oblivious.
- `read_frontmatter` as the single filesystem touchpoint — preserves Plan 05-02's path-traversal defenses.

## Deviations from Plan

**None — plan executed exactly as written.**

The plan's `<action>` block included pseudo-code with a deliberate "wrong approach" comment in `_row_sort_key` followed by the correct two-pass approach in `_sort_rows`. I implemented the documented `_sort_rows` algorithm and omitted the `_row_sort_key` placeholder helper (which raised `NotImplementedError` in the pseudo-code purely to document the contract). All 15 `<behavior>` cases pass; 3 structural invariants added under the plan's "test count ≥15" gate.

## Issues Encountered

**None.** TDD RED → GREEN landed cleanly on the first implementation pass; no debugging cycle required. The two-pass stable sort algorithm, partitioning empties from non-empties before sort + concat, was the correct pattern from the start (verified by Tests 3 and 5 immediately).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Plan 05-04 (routes)** — fully unblocked. Service surface is locked: `build_overview_grid_view_model`, `OverviewGridViewModel`, `OverviewRow`, `FILTERABLE_COLUMNS`, `SORTABLE_COLUMNS`, `DEFAULT_SORT_COL`, `DEFAULT_SORT_ORDER` are all importable. `vm.rows`, `vm.filter_options`, `vm.active_filter_counts`, `vm.has_content_map` are all dict / list types that template context can consume directly.
- **Plan 05-05 (templates)** — `vm.rows[i]` is iterable for `<tbody>`; `vm.filter_options[col]` feeds the parameterized `picker_popover` macro from Plan 05-01 (passing `form_id="overview-filter-form"`, `hx_post="/overview/grid"`, `hx_target="#overview-grid"`). None values render as `—` per D-OV-09 contract.
- **Plan 05-06 (tests + invariants)** — the 18 unit tests in `tests/v2/test_overview_grid_service.py` are the foundation; route-level integration tests (Plan 05-04) and Phase 5 invariants (Plan 05-06) build on top.

## Self-Check: PASSED

**Files created (all exist):**
- `app_v2/services/overview_grid_service.py` — FOUND
- `tests/v2/test_overview_grid_service.py` — FOUND

**Commits exist:**
- `43d9d60` (TDD RED) — FOUND
- `4797893` (TDD GREEN) — FOUND

**Acceptance criteria all pass:**
- `OverviewRow` (BaseModel) defined — FOUND
- `OverviewGridViewModel` (BaseModel) defined — FOUND
- `build_overview_grid_view_model(` defined — FOUND
- All 4 module constants present — FOUND
- `read_frontmatter` import — FOUND
- `has_content_file` import — FOUND
- FastAPI/Starlette import count = 0 — VERIFIED
- `async def` count = 0 — VERIFIED
- 6 filter columns literal present — FOUND
- `"start", "end"` literal present — FOUND
- 18 tests pass (≥15 gate) — VERIFIED
- Phase 1-4 regression: 95 prior tests pass + 14 Phase 4 invariants pass — VERIFIED
- Full v2 suite: 308 passed, 1 skipped (zero regressions vs 290+1 baseline) — VERIFIED

---
*Phase: 05-overview-redesign*
*Completed: 2026-04-28*
