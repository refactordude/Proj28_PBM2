---
quick_task: 260507-rmj
type: execute
wave: 1
status: complete
completed: 2026-05-07
duration_minutes: 11
tasks_completed: 3
files_modified:
  - app_v2/services/joint_validation_grid_service.py
  - app_v2/routers/overview.py
  - app_v2/templates/overview/_grid.html
  - app_v2/templates/overview/_filter_bar.html
  - app_v2/templates/overview/index.html
  - config/presets.example.yaml
  - tests/v2/test_joint_validation_grid_service.py
  - tests/v2/test_joint_validation_routes.py
  - tests/v2/test_overview_presets.py
  - tests/v2/test_joint_validation_invariants.py
  - tests/v2/test_phase02_invariants.py
  - tests/v2/test_jv_pagination.py
commits:
  - hash: e575163
    type: refactor
    summary: "drop status/assignee/end from JV grid service core + router wiring"
  - hash: b2215b4
    type: refactor
    summary: "drop Status/담당자/End columns + Status picker + status from presets"
  - hash: 03e6fca
    type: test
    summary: "update v2 suite for 5-facet/9-column/no-Status reality"
test_count_before: 581
test_count_after: 580
test_count_delta: -1
key_decisions:
  - "ALL_METADATA_KEYS kept at 12 entries: status/assignee/end stay on JointValidationRow because the JV detail page still renders them (D-JV-04 invariant preserved). Only the LISTING-grid concept changed."
  - "DATE_COLUMNS reduced to 1-tuple ('start',) — tuple shape preserved (not bare string) so the `sort_col in DATE_COLUMNS` set-membership check shape elsewhere stays unchanged."
  - "Chip palette re-numbered c-1..c-5 (was c-1..c-6): customer/ap_company/device/controller/application now claim the lower-index slots; tests updated in lockstep."
  - "Disambiguation: user said 'Browse page' but meant the Joint Validation listing (active_tab=overview, route /overview). The actual /browse pivot grid + config/browse_presets.example.yaml were untouched."
---

# Quick Task 260507-rmj: Ditch Status/담당자/End columns + Status filter from JV listing

## One-liner

Cleaned up the Joint Validation listing: 12 → 9 sortable columns (drop Status/담당자/End headers+cells), 6 → 5 picker popovers (drop Status), 6 → 5 active-filter chip facets (palette c-1..c-5), Status removed from 2 of 3 seed presets in `config/presets.example.yaml`. All v2 tests green at 580 (-1 deleted).

## What Shipped

### Source code (5 files)

1. **`app_v2/services/joint_validation_grid_service.py`** — `FILTERABLE_COLUMNS` 6 → 5 (drop `"status"`); `SORTABLE_COLUMNS` 12 → 9 explicit tuple (drop `"status"`/`"assignee"`/`"end"`, no longer aliased to `ALL_METADATA_KEYS`); `DATE_COLUMNS` `('start','end')` → `('start',)`. `ALL_METADATA_KEYS` and `JointValidationRow` unchanged (parser surface + detail page preserved). Module docstring D-JV-10 / D-JV-11 lines updated.
2. **`app_v2/routers/overview.py`** — `_parse_filter_dict` / `_build_overview_url` / `get_overview` / `post_overview_grid` / `get_overview_preset` no longer accept or emit a `status` argument anywhere. Iteration tuple in `_build_overview_url` shrunk to 5 facets. Docstrings updated.
3. **`app_v2/templates/overview/_grid.html`** — 12 `sortable_th(...)` → 9 (drop status/assignee/end); 12 body `<td>` → 9; empty-state `colspan="13"` → `colspan="10"`. Header comment updated to "9 sortable column headers ... Action column is the 10th column".
4. **`app_v2/templates/overview/_filter_bar.html`** — Status `picker_popover(...)` block deleted; remaining 5 picker calls (customer, ap_company, device, controller, application) byte-stable. Top docstring updated to "5 picker dropdowns".
5. **`app_v2/templates/overview/index.html`** (filter_badges_oob block) — `ff_labels` and `ff_variants` maps drop `"status"` key; for-loop literal trimmed to 5 entries; chip palette re-numbered `c-1..c-5` so surviving facets re-occupy the lower-index slots (customer=c-1, ap_company=c-2, device=c-3, controller=c-4, application=c-5).

### Config (1 file)

6. **`config/presets.example.yaml`** — `korean-oems-in-progress` drops `status: ["In Progress"]` (keeps `customer: ["Samsung", "Hyundai"]`); `pending-ufs4` drops `status: ["Pending"]` (keeps `device: ["UFS 4.0"]`); `qualcomm-wearables` unchanged. Header comment updated to reflect the 5-key `FILTERABLE_COLUMNS` and notes the 260507-rmj rationale.

### Tests (6 files)

7. **`tests/v2/test_joint_validation_grid_service.py`** — Deleted `test_filter_status_in_progress_excludes_others`; renamed `test_six_filter_options_enumerated_from_full_set` → `test_five_filter_options_enumerated_from_full_set` and re-pinned against customer; `test_active_filter_counts_match_input` swaps status→customer in input/output dicts (5 keys); `test_invalid_sort_col_falls_back_to_default` now also asserts status/assignee/end fall back (formerly only "link").
8. **`tests/v2/test_joint_validation_routes.py`** — `test_get_overview_with_filters_round_trip_url` swaps `("status","In Progress")` → `("customer","Samsung")`; `test_empty_jv_root_renders_empty_state` colspan 13 → 10; chip-render test rewritten against customer (c-1) + ap_company (c-2); `_write_many_jv_status_values` renamed `_write_many_jv_customer_values` and writes `<Customer>` rows; chip-no-active probes `c-1..c-5` (was c-1..c-6).
9. **`tests/v2/test_overview_presets.py`** — Loader test pins `'status' not in filters` for korean / pending presets; malformed-entries YAML literal swaps every `status:` to `customer:` (so the test isolates the malformed dimension instead of also failing on unknown-facet for status); preset-override chip variants ap_company c-3 → c-2, application c-6 → c-5; stray-params probe `("status","Cancelled")` → `("device","X1")` (still-recognized facet, demonstrates "preset overrides even live-recognized stray params").
10. **`tests/v2/test_joint_validation_invariants.py`** (Rule 1 auto-fix) — `D-JV-11` picker_popover count `>= 6` → `>= 5`; section header comment updated.
11. **`tests/v2/test_phase02_invariants.py`** (Rule 1 auto-fix) — `D-UI2-09` picker_popover count `== 6` → `== 5`; docstring + assertion message updated to note the 260507-rmj reduction.
12. **`tests/v2/test_jv_pagination.py`** (Rule 1 auto-fix) — `test_filter_options_built_from_all_rows_not_paged` (P11) source facet status → customer (still exercises 20-distinct-values-across-pages contract).

## Test Results

```
580 passed, 5 skipped, 2 warnings in 51.27s
```

Net delta: **581 → 580 (-1)** — `test_filter_status_in_progress_excludes_others` deleted because Status is no longer filterable; no replacement needed (the surviving-facet variant of the same test is `test_five_filter_options_enumerated_from_full_set`). 5 skipped count unchanged.

Touched-module subset (151 tests): **all green** in 22.08s.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test invariants pinned the pre-260507-rmj 6-picker / status-facet shape**

- **Found during:** Task 3 verification run (full v2 suite)
- **Issue:** Three invariant tests outside the plan's `<files_modified>` list still pinned the old shape:
  - `tests/v2/test_joint_validation_invariants.py::test_jv_filter_bar_uses_picker_popover_macro_unmodified` — asserted `picker_popover(` count `>= 6`
  - `tests/v2/test_phase02_invariants.py::test_overview_filter_bar_six_picker_calls` — asserted `picker_popover(` count `== 6` exactly
  - `tests/v2/test_jv_pagination.py::test_filter_options_built_from_all_rows_not_paged` — wrote 20 unique `status` values and asserted `vm.filter_options["status"]` count
- **Fix:** Updated the three asserts to reflect the new 5-picker / customer-as-source-facet reality. These are direct, mechanical consequences of the plan's intent (the plan called out that drops + reductions are part of the contract change); the tests just hadn't been listed in `<files_modified>`.
- **Files modified:** `tests/v2/test_joint_validation_invariants.py`, `tests/v2/test_phase02_invariants.py`, `tests/v2/test_jv_pagination.py`
- **Commit:** `03e6fca`

### Out-of-scope Discoveries (not fixed)

- The user / a linter touched `app_v2/templates/overview/_grid.html` mid-task to change Actions column alignment from `text-end` → `text-center` and removed `<i class="bi bi-link-45deg">` icons before "edm" labels (adding a `jv-action-btn` class). This was a parallel task (`quick-260507-rvx`) — its commits `1bbba03` and `b42e2fe` interleaved with mine but did not conflict (different concerns: alignment/icons vs column drops). Left untouched in my commits.
- `app_v2/static/css/app.css` was modified by the same parallel task — left out of my commits.

## Verification Snapshot

| Check | Expected | Actual |
|-------|----------|--------|
| `_grid.html` `sortable_th(` count | 9 | 9 |
| `_grid.html` `colspan="10"` count | 1 | 1 |
| `_grid.html` `colspan="13"` count | 0 | 0 |
| `_filter_bar.html` `picker_popover(` count | 5 | 5 |
| `_filter_bar.html` `name="status"` count | 0 | 0 |
| `index.html` `"status": "Status"` count | 0 | 0 |
| `len(FILTERABLE_COLUMNS)` | 5 | 5 |
| `len(SORTABLE_COLUMNS)` | 9 | 9 |
| `DATE_COLUMNS` | `('start',)` | `('start',)` |
| `len(ALL_METADATA_KEYS)` | 12 (unchanged) | 12 |
| Router signatures contain `status:` | 0 | 0 |
| Parser `담당자` matches | ≥1 | 4 |
| `detail.html` Status/담당자/End rows preserved | yes | yes (lines 23, 31, 33) |
| `pytest tests/v2/` | green | green (580 passed) |

## Invariants Preserved

- **D-JV-04** — `joint_validation_parser.py` matches `"담당자"` byte-equal (4 occurrences in parser; `test_jv_parser_korean_label_byte_equal` still green).
- **D-JV-15 / D-OV-16** — `_DANGEROUS_LINK_SCHEMES` 5-tuple and `_sanitize_link` untouched.
- **JV detail page** — `app_v2/templates/joint_validation/detail.html` still renders Status (line 23), 담당자 (line 31), End (line 33) properties. `test_get_jv_detail_renders_properties_and_iframe` still asserts `"담당자" in r.text` against this page — green.
- **Browse and Ask regression smoke** — `test_browse_and_ask_tabs_unaffected` green; the actual /browse pivot grid + `config/browse_presets.example.yaml` were not touched.

## Disambiguation Note

The user said "Browse page" colloquially. The repository has THREE distinct tabs: **Joint Validation** (active_tab="overview", route /overview), **Browse** (active_tab="browse", route /browse, pivot grid), and **Ask**. The columns the user named — Status, 담당자, End — and the Status filter only existed on the **Joint Validation** listing. The actual `/browse` pivot grid renders dynamic platform×parameter columns and has no Status/담당자/End columns or Status filter, so it was NOT the target. The plan correctly disambiguated this; the executor did not touch the Browse tab or its preset YAML.

## Self-Check: PASSED

- File `app_v2/services/joint_validation_grid_service.py` — FOUND
- File `app_v2/routers/overview.py` — FOUND
- File `app_v2/templates/overview/_grid.html` — FOUND
- File `app_v2/templates/overview/_filter_bar.html` — FOUND
- File `app_v2/templates/overview/index.html` — FOUND
- File `config/presets.example.yaml` — FOUND
- File `tests/v2/test_joint_validation_grid_service.py` — FOUND
- File `tests/v2/test_joint_validation_routes.py` — FOUND
- File `tests/v2/test_overview_presets.py` — FOUND
- File `tests/v2/test_joint_validation_invariants.py` — FOUND
- File `tests/v2/test_phase02_invariants.py` — FOUND
- File `tests/v2/test_jv_pagination.py` — FOUND
- Commit `e575163` — FOUND
- Commit `b2215b4` — FOUND
- Commit `03e6fca` — FOUND
