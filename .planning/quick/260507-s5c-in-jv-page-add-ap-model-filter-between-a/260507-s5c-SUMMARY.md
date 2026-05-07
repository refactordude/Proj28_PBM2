---
quick_task: 260507-s5c
type: summary
status: complete
date: 2026-05-07
duration: 6min
tasks: 3
files_changed: 9
commits:
  - 960d070  # Task 1 — service + router + service tests (5→6)
  - 64d385d  # Task 2 — templates + CSS comment + presets YAML
  - 166e138  # Task 3 — invariant + chip-palette tests
test_count:
  before: 580
  after: 580
  delta: 0
key-decisions:
  - "ap_model already on JointValidationRow + already in SORTABLE_COLUMNS + already rendered in _grid.html — change surface is purely 'expose-as-filter wiring' (parser/store/grid/pagination unchanged)"
  - "Chip palette extended c-1..c-5 → c-1..c-6 with ap_model claiming c-3; device/controller/application shifted one slot down (c-3→c-4, c-4→c-5, c-5→c-6); customer/ap_company keep c-1/c-2"
  - "Disambiguation: this is the JV listing (active_tab=overview, route /overview), NOT the Browse pivot grid — same disambiguation captured in 260507-rmj's SUMMARY"
  - "Seed presets in presets.example.yaml left untouched — header comment lists ap_model in FILTERABLE_COLUMNS but the 3 example presets don't claim ap_model values (preset_store loader returns [] for any unmentioned facet)"
key-files:
  modified:
    - app_v2/services/joint_validation_grid_service.py    # FILTERABLE_COLUMNS 5→6; D-JV-11 docstring + comments
    - app_v2/routers/overview.py                          # _parse_filter_dict / _build_overview_url / get_overview / post_overview_grid / get_overview_preset (5 sites)
    - app_v2/templates/overview/_filter_bar.html          # 6th picker_popover for ap_model between ap_company and device
    - app_v2/templates/overview/index.html                # filter_badges_oob block extended (ff_labels, ff_variants, for-loop)
    - app_v2/static/css/app.css                           # chip-palette mapping comment refreshed (rules byte-stable)
    - config/presets.example.yaml                         # header comment lists ap_model
    - tests/v2/test_joint_validation_grid_service.py      # rename test_five→test_six; active_filter_counts gains ap_model:0
    - tests/v2/test_joint_validation_invariants.py        # picker_popover( count >=5 → >=6
    - tests/v2/test_phase02_invariants.py                 # picker count == 6 (test name reality match)
    - tests/v2/test_joint_validation_routes.py            # empty-wrapper variant probe c-1..c-5 → c-1..c-6
    - tests/v2/test_overview_presets.py                   # application chip c-5 → c-6
  created: []
---

# Quick Task 260507-s5c: Add AP Model Filter Between AP Company and Device on JV Listing Summary

**One-liner:** Restore the JV listing to a 6-facet filter bar by inserting an AP Model picker between AP Company and Device — the mirror image of quick-260507-rmj's Status drop. All v2 tests stay green (580 → 580; no net delta).

## What Changed

The Joint Validation listing page (`/overview`) had 5 popover-checklist filters (customer, ap_company, device, controller, application) after 260507-rmj dropped Status. Quick task 260507-s5c re-expands the facet set to 6 by inserting **AP Model** in position 3, between AP Company and Device.

`ap_model` was already a fully-wired data attribute on every JV row — parsed by `joint_validation_parser.py`, stored on `JointValidationRow`, included in `SORTABLE_COLUMNS`, and rendered as a sortable `<th>`/`<td>` column in `_grid.html`. The only thing missing was its surface as a filter facet. This plan wires that surface end-to-end (UI → URL → form → service → view-model → chips).

## Files Changed (11 total)

### Source (6 files)

| File                                                | What changed |
|-----------------------------------------------------|---|
| `app_v2/services/joint_validation_grid_service.py`  | `FILTERABLE_COLUMNS` 5-tuple → 6-tuple with `ap_model` at index 2; D-JV-11 docstring + section comment + active-filter-counts comment refreshed |
| `app_v2/routers/overview.py`                        | `_parse_filter_dict` accepts 6 args (was 5); `_build_overview_url` iterates 6 facets; `get_overview` Query / `post_overview_grid` Form / `get_overview_preset` _parse_filter_dict call all thread `ap_model` |
| `app_v2/templates/overview/_filter_bar.html`        | 6th `picker_popover(...)` invocation for `ap_model`, inserted between the `ap_company` and `device` blocks (verbatim copy + s/ap_company/ap_model/g + label) |
| `app_v2/templates/overview/index.html`              | `filter_badges_oob` block extended: `ff_labels` / `ff_variants` / for-loop literal all gain `ap_model`; palette renumbered customer→c-1, ap_company→c-2, ap_model→c-3, device→c-4, controller→c-5, application→c-6 |
| `app_v2/static/css/app.css`                         | Chip-palette mapping comment refreshed for the post-260507-s5c facet→slot mapping. The `.ff-chip.c-1`..`.ff-chip.c-6` declarations themselves stay byte-stable (already provided 6 slots — only the comment was wrong) |
| `config/presets.example.yaml`                       | Header comment lists `ap_model` in the FILTERABLE_COLUMNS enumeration; new comment line records 260507-s5c. Seed preset entries unchanged (loader returns `[]` for any unmentioned facet — no breakage) |

### Tests (5 files)

| File                                                 | What changed |
|------------------------------------------------------|---|
| `tests/v2/test_joint_validation_grid_service.py`     | `test_active_filter_counts_match_input` expected dict gains `"ap_model": 0`; rename `test_five_filter_options_enumerated_from_full_set` → `test_six_filter_options_enumerated_from_full_set` (mirror-image rename of 260507-rmj's six→five) |
| `tests/v2/test_joint_validation_invariants.py`       | `test_jv_filter_bar_uses_picker_popover_macro_unmodified`: `count >= 5` → `count >= 6`; section header + assertion message updated for 260507-s5c |
| `tests/v2/test_phase02_invariants.py`                | `test_overview_filter_bar_six_picker_calls`: `count == 5` → `count == 6` (test name finally matches reality after the 260507-rmj→260507-s5c round trip) |
| `tests/v2/test_joint_validation_routes.py`           | `test_overview_filter_chips_no_active_filters_renders_empty_wrapper`: probe range `c-1..c-5` → `c-1..c-6`; comment updated |
| `tests/v2/test_overview_presets.py`                  | `test_get_overview_preset_overrides_filters_and_returns_oob_blocks`: application chip variant `c-5` → `c-6` (palette shifted by ap_model insertion at c-3); inline comment updated |

## Verification Snapshot

| Contract                          | Pre-260507-s5c                           | Post-260507-s5c                                                                |
|-----------------------------------|------------------------------------------|--------------------------------------------------------------------------------|
| `FILTERABLE_COLUMNS` length       | 5                                        | 6                                                                              |
| `_parse_filter_dict` arity        | 5 list args                              | 6 list args                                                                    |
| Picker count in `_filter_bar.html`| 5                                        | 6 (`ap_model` between `ap_company` and `device`)                               |
| `filter_badges_oob` for-loop      | `["customer","ap_company","device","controller","application"]` | `["customer","ap_company","ap_model","device","controller","application"]`    |
| Chip palette                      | c-1..c-5                                 | c-1..c-6                                                                       |
| `application` chip variant        | c-5                                      | c-6                                                                            |
| `customer` / `ap_company` chips   | c-1 / c-2                                | c-1 / c-2 (unchanged — insertion was below them)                               |
| `device` / `controller` chips     | c-3 / c-4                                | c-4 / c-5 (shifted by ap_model insertion)                                      |
| Full v2 test suite                | 580 passed, 5 skipped                    | 580 passed, 5 skipped (no net delta — renames + literal bumps only)            |
| Live smoke `GET /overview`        | 200                                      | 200                                                                            |
| Live smoke `GET /overview?ap_model=SM8450` | n/a (param ignored)             | 200 (param routed through service; chip renders when matching values exist)    |

## Atomic Commits (3)

| Commit  | Scope                              | Files |
|---------|------------------------------------|-------|
| 960d070 | Task 1 — service tuple + router signatures + service tests | 3 |
| 64d385d | Task 2 — templates + CSS comment + presets YAML            | 4 |
| 166e138 | Task 3 — invariant + chip-palette test bumps               | 4 |

Mirror-image of 260507-rmj's `e575163` / `b2215b4` / `03c9717` trio (interface-first → templates → tests).

## Decisions Made

1. **ap_model already on the row → no parser/model/grid changes.** `joint_validation_parser.py` (line 188), `JointValidationRow.ap_model` (line 114), `SORTABLE_COLUMNS` (line 73), and the `<th>`/`<td>` rendering in `_grid.html` were all ap_model-aware before this plan. The only missing surface was the filter — exposing it required wiring `ap_model` into `FILTERABLE_COLUMNS` and propagating that 5→6 expansion across the same 6 sites that 260507-rmj contracted in reverse.

2. **Chip palette extended c-1..c-5 → c-1..c-6 with ap_model claiming c-3.** Customer/ap_company keep c-1/c-2 (insertion was below them); device/controller/application shift one slot down. The `.ff-chip.c-1`..`.ff-chip.c-6` CSS declarations themselves were byte-stable (already provided 6 slots from the original Phase 02 design — Status had been c-1 pre-260507-rmj). Only the descriptive comment above them needed updating to match the post-260507-s5c facet→slot mapping.

3. **Seed presets in presets.example.yaml not modified.** The plan explicitly scoped this work to "expose existing data as a filter" — adding `ap_model:` keys to the 3 seed presets would have been out-of-scope feature work. The preset_store loader gracefully returns `[]` for any FILTERABLE_COLUMNS entry not mentioned in the YAML, so the 5-key seed presets keep loading correctly under the new 6-key `_parse_filter_dict` shape.

4. **Disambiguation note (mirror of 260507-rmj):** This change applies to the **JV listing** (`active_tab=overview`, route `/overview`, template `app_v2/templates/overview/`), NOT the Browse pivot grid (`active_tab=browse`, route `/browse`, template `app_v2/templates/browse/`). The Browse pivot grid uses a different filter shape (platforms[] + params[] + swap_axes — see 260507-r0k's SUMMARY) and is unaffected by this plan.

## Deviations from Plan

None — plan executed exactly as written.

The "Auto-fix discipline" sweep in Task 3 (grep for `class="ff-chip c-` pins on facets that shifted from c-3..c-5 to c-4..c-6) found no out-of-files-modified hits. All chip-variant pins live in the 4 test files already in the plan's `files_modified` list:

- customer pins (c-1, unchanged) — `test_joint_validation_routes.py` lines 387, 388, 421
- ap_company pins (c-2, unchanged) — `test_joint_validation_routes.py` line 391, `test_overview_presets.py` line 226
- application pin (c-5 → c-6, updated) — `test_overview_presets.py` line 228

No device/controller variant pins exist anywhere in `tests/v2/` (those facets are exercised by the empty-wrapper `c-N` probe in `test_overview_filter_chips_no_active_filters_renders_empty_wrapper` only, and that probe was already extended to `c-1..c-6`).

## Self-Check: PASSED

- `app_v2/services/joint_validation_grid_service.py` — modified, FILTERABLE_COLUMNS is the 6-tuple
- `app_v2/routers/overview.py` — modified, 5 wiring sites all thread ap_model
- `app_v2/templates/overview/_filter_bar.html` — modified, 6 picker_popover invocations
- `app_v2/templates/overview/index.html` — modified, filter_badges_oob block has 6-key maps
- `app_v2/static/css/app.css` — modified, palette comment refreshed
- `config/presets.example.yaml` — modified, header comment refreshed
- 5 test files — all modified per plan
- Commit 960d070 — found in `git log --oneline`
- Commit 64d385d — found in `git log --oneline`
- Commit 166e138 — found in `git log --oneline`
- `pytest tests/v2/` — 580 passed, 5 skipped (live verification pre-summary)
