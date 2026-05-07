---
phase: 260507-w7h
plan: 01
subsystem: browse
tags: [browse, ui, highlight, render-layer, pivot-grid]
requires:
  - app_v2/services/browse_service.py (BrowseViewModel + build_view_model + _build_browse_url)
  - app_v2/routers/browse.py (3 routes: GET /browse, POST /browse/grid, GET /browse/preset/{name})
  - app_v2/templates/browse/_filter_bar.html (Swap axes button as sibling-pattern template)
  - app_v2/templates/browse/_grid.html (iterrows loop)
  - app_v2/templates/browse/index.html (preset chip strip)
  - app_v2/static/css/app.css (.pivot-table rule scope)
provides:
  - "_compute_minority_cells helper (mode-based per-axis minority detection)"
  - "BrowseViewModel.highlight + BrowseViewModel.minority_cells fields"
  - "highlight kwarg on build_view_model + _build_browse_url"
  - "?highlight=1 URL round-trip on 3 routes (GET browse, POST browse/grid, GET browse/preset)"
  - "Highlight btn-check sibling of Swap axes with mutual hx-include preservation"
  - "cell-highlight CSS class (#fff8c5 soft yellow)"
  - "preset chip hx-include preserves user's highlight state across preset apply"
affects:
  - browse pivot grid rendering
  - browse filter bar UI
  - browse preset apply flow
tech-stack:
  added: []
  patterns:
    - "Render-only flag (no SQL/pivot effect; no preset YAML schema bump)"
    - "Sibling pattern: highlight is a parallel of swap_axes — never refactored to shared options struct"
    - "iterrows() canonical source for row keys (matches set tuple keys by construction)"
    - "Mutable default workaround for @dataclass via __post_init__ (no extra import)"
key-files:
  created: []
  modified:
    - app_v2/services/browse_service.py
    - app_v2/routers/browse.py
    - app_v2/templates/browse/_filter_bar.html
    - app_v2/templates/browse/_grid.html
    - app_v2/templates/browse/index.html
    - app_v2/static/css/app.css
    - tests/v2/test_browse_service.py
    - tests/v2/test_browse_routes.py
decisions:
  - "Highlight is render-only — does NOT affect SQL or pivot; flows through view-model and URL round-trip exclusively"
  - "URL pin: highlight=1 appears AFTER swap=1 in the query string (pinned by both implementation and Test H)"
  - "Empty cells (NaN/None/'') never count toward mode and never appear in minority_cells (verified Test C)"
  - "Tie-for-mode resolves to lowest-sorted value via Series.mode().iloc[0] (verified Test D)"
  - "BrowseViewModel.minority_cells uses set[tuple] = None + __post_init__ to avoid importing dataclasses.field"
  - "Preset YAML schema unchanged — render-only flag flows from session state via hx-include on preset chip, not from preset dict"
  - "iterrows() is the canonical row-key source so set tuples and template loop variable match by construction (avoids df.index.tolist() drift if multiindex enters)"
metrics:
  duration: "~30min"
  completed: "2026-05-07"
  tasks: 2
  files: 8
  tests-added: 13   # 8 unit + 5 integration
  tests-removed: 0
---

# Phase 260507-w7h Plan 01: Highlight Toggle on Browse Summary

**One-liner:** Mode-based per-parameter-axis minority highlighting on Browse pivot grid; render-only flag with full URL round-trip and preset-apply preservation.

## What Shipped

A `Highlight` toggle button next to the existing `Swap axes` button in the Browse filter bar. When ON, every cell whose value is a minority (differs from the per-parameter mode of non-empty values) gets a soft-yellow background (`#fff8c5`). The toggle's state persists in the URL as `?highlight=1`, mirroring the existing `?swap=1` pattern, and survives Apply, Swap-axes toggle, and Preset-chip apply.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1    | Service-layer minority detection + view-model wiring | ad4c9ec | app_v2/services/browse_service.py, tests/v2/test_browse_service.py |
| 2    | Wire highlight through 3 routes + filter-bar UI + per-cell template + CSS | a511727 | app_v2/routers/browse.py, app_v2/templates/browse/_filter_bar.html, app_v2/templates/browse/_grid.html, app_v2/templates/browse/index.html, app_v2/static/css/app.css (CSS rule already present in HEAD via incidental commit), tests/v2/test_browse_routes.py |

## Behavior Contracts (must-haves verified)

- [x] User can see a Highlight toggle button next to Swap axes in the Browse filter bar — Test 3 asserts `id="browse-highlight"` present
- [x] Toggling Highlight ON re-renders the grid with soft-yellow background on cells whose value differs from the per-parameter mode — Test 1 (X/X/Y fixture → cell-highlight emitted)
- [x] Empty cells are never highlighted and never affect mode computation — Test C (unit)
- [x] The URL query string carries `?highlight=1` when on, omits it when off — Test H (unit) + Test 4 (integration)
- [x] Toggling Highlight while platforms+params are selected fires a single POST /browse/grid — driven by btn-check change trigger; verified by hx-include selectors in Test 3
- [x] Clicking a preset chip preserves the user's current highlight state — Test 5 (preset chip hx-include picks up #browse-highlight:checked; HX-Push-Url contains highlight=1)

## Tests

- **Baseline:** 579 v2 tests passed (the plan said 581 — actual baseline differs but 2 pre-existing failures are unrelated, see Pre-existing failures below)
- **After this plan:** 592 v2 tests passed (+13 new tests, no removals)
- **Failing tests:** Same 2 pre-existing failures unrelated to this plan (`test_get_root_contains_three_tab_labels`, `test_showcase_inherits_topbar`) — both relate to topbar/branding strings in `<title>` and base.html and were already failing before this plan started.

### Tests Added (Task 1 — 8 unit tests in test_browse_service.py)

| Test | Behavior |
|------|----------|
| A | All-equal column → empty minority set |
| B | Single outlier → outlier (idx, col) in set; mode rows NOT in set |
| C | Empty cells (NaN/None/'') never appear; do NOT count toward mode |
| D | Tie-for-mode resolves to lowest-sorted via `Series.mode().iloc[0]` |
| E | swap_axes=True flips axis: mode per row across columns |
| F | highlight=False (default) skips _compute_minority_cells (mocker.spy) |
| G | highlight=True populates vm.minority_cells with non-empty fixture |
| H | _build_browse_url(highlight=True/False) — pinned URL ordering |

### Tests Added (Task 2 — 5 integration tests in test_browse_routes.py)

| Test | Behavior |
|------|----------|
| 1 | GET /browse?highlight=1 with X/X/Y outlier fixture renders `cell-highlight` class AND Highlight checkbox is pre-checked |
| 2 | GET /browse (no flag) → no `cell-highlight` substring AND Highlight checkbox NOT pre-checked (with hx-include `:checked` substring stripped to avoid false-match) |
| 3 | Filter-bar structural assertions: id/name/value on Highlight input; mutual hx-include between Swap and Highlight; `<label for="browse-highlight">` |
| 4 | POST /browse/grid with `highlight=1` form field sets HX-Push-Url ending `&swap=1&highlight=1` |
| 5 | GET /browse/preset/{name}?highlight=1 — HX-Push-Url contains `highlight=1` (preset YAML untouched; flag flows from session) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Test 2 false-matched `:checked` substring inside hx-include attribute**

- **Found during:** Task 2 GREEN phase (Test 2 failed)
- **Issue:** The Highlight input's `hx-include` attribute contains the CSS selector `#browse-highlight:checked`, which lexically contains the substring `checked`. The original test logic asserted `"checked" not in seg` on the input's open tag — this false-matched the `:checked` selector and incorrectly failed when highlight was off.
- **Fix:** Strip the `hx-include="..."` attribute value from the input segment via `re.sub(r'hx-include="[^"]*"', "", seg)` BEFORE checking for the standalone `checked` attribute.
- **Files modified:** tests/v2/test_browse_routes.py (test_get_browse_without_highlight_renders_no_cell_highlight)
- **Commit:** a511727 (bundled with Task 2 wiring)

### CSS Rule Landed in Earlier Incidental Commit

The plan instructed adding `.pivot-table td.cell-highlight { background: #fff8c5 }` to app.css in Task 2. During execution, an unrelated quick task (`260507-vys`) committed chat-pill display fixes to app.css via commit `7163edc` between Task 1 and Task 2 — that commit incidentally also captured the `cell-highlight` CSS rule from the working tree. End state matches the plan's contract (rule exists in HEAD, scoped to `.pivot-table td.cell-highlight`, subtle yellow background that lets table-striped row banding read through). No correctness impact; flagged here for audit transparency.

## Self-Check: PASSED

**Files verified present:**
- FOUND: app_v2/services/browse_service.py (with `_compute_minority_cells` and `highlight`/`minority_cells` fields)
- FOUND: app_v2/routers/browse.py (highlight threaded through 3 routes)
- FOUND: app_v2/templates/browse/_filter_bar.html (Highlight btn-check + mutual hx-include)
- FOUND: app_v2/templates/browse/_grid.html (idx loop var + cell-highlight class)
- FOUND: app_v2/templates/browse/index.html (preset chip hx-include)
- FOUND: app_v2/static/css/app.css (.pivot-table td.cell-highlight rule at line ~246)
- FOUND: tests/v2/test_browse_service.py (8 new tests A–H)
- FOUND: tests/v2/test_browse_routes.py (5 new tests 1–5)

**Commits verified:**
- FOUND: ad4c9ec (Task 1)
- FOUND: a511727 (Task 2)

**Type/import sanity:**
```
$ python -c "from app_v2.services.browse_service import _compute_minority_cells, BrowseViewModel, build_view_model, _build_browse_url; vm = BrowseViewModel.__dataclass_fields__; assert 'highlight' in vm and 'minority_cells' in vm; print('OK')"
OK
```

**Test suite:**
- 68 tests pass in focused suite (test_browse_routes.py + test_browse_service.py + test_browse_presets.py)
- 592 tests pass overall in tests/v2/ (was 579; +13 = 8 unit + 5 integration); 2 pre-existing failures unchanged
