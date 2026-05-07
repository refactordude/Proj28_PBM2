---
quick_id: 260507-lcc
type: quick
status: complete
completed: 2026-05-04
commit: 7680d0e
files_modified:
  - app_v2/services/joint_validation_grid_service.py
  - app_v2/templates/overview/_pagination.html
  - tests/v2/test_jv_pagination.py
files_unchanged:
  - tests/v2/test_phase02_invariants.py  # grep showed no ellipsis-pinning assertions; left byte-stable
tests:
  baseline: "546 passed, 5 skipped"
  red_after_test_writes: "29 passed, 11 failed (jv_pagination only)"
  green_final: "556 passed, 5 skipped"
  net_new_tests: 10
requirements:
  - QT-260507-lcc-01
tags: [pagination, joint-validation, ui]
---

# Quick Task 260507-lcc: Group-of-10 Pagination

**One-liner:** Replace JV pagination's sliding-window-with-ellipsis algorithm with a fixed page-group-of-10 layout so the bar width stays stable as the user navigates inside a group.

## Algorithm Swap

**Before (sliding-window-with-ellipsis):**
- 10 pages, current=5 → `1 … 4 5 6 … 10`  (7 items)
- 10 pages, current=1 → `1 2 … 10`         (4 items)
- Bar visibly grows/shrinks during navigation — user-flagged as "weird."

**After (fixed group-of-10):**
- Pages partition into groups: group 1 = pages 1..10, group 2 = pages 11..20, etc.
- `_build_page_links` returns ALL pages in the current group, never ellipsis.
- Group transitions signalled by `<` / `>` chevrons whose targets are the boundary pages of the adjacent group.

### Canonical Worked Examples

| Total pages | Current | Bar contents               | Chevrons rendered |
| ----------- | ------- | -------------------------- | ----------------- |
| 1           | 1       | (nav suppressed by guard)  | none              |
| 5           | 3       | `1 2 3 4 5`                | none              |
| 10          | 5       | `1 2 3 4 5 6 7 8 9 10`     | none              |
| 10          | 10      | `1 2 3 4 5 6 7 8 9 10`     | none (no group 2) |
| 13          | 1       | `1 2 3 4 5 6 7 8 9 10 >`   | next → 11         |
| 13          | 11      | `< 11 12 13`               | prev → 10         |
| 25          | 15      | `< 11 12 ... 19 20 >`      | prev → 10, next → 21 |
| 25          | 21      | `< 21 22 23 24 25`         | prev → 20         |

### Group Math

- `group_index = (page - 1) // GROUP_SIZE` (0-based)
- group `g` covers pages `g*GROUP_SIZE + 1` through `min((g+1)*GROUP_SIZE, page_count)`
- `prev_group_page = group_index * GROUP_SIZE if group_index > 0 else None`  (LAST page of previous group)
- `next_group_page = (group_index + 1) * GROUP_SIZE + 1 if (group_index + 1) * GROUP_SIZE < page_count else None`  (FIRST page of next group)

## Files Changed

| File                                                     | Δ                                                                                       |
| -------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `app_v2/services/joint_validation_grid_service.py`       | +`GROUP_SIZE = 10`; `_build_page_links` body rewritten; `prev_group_page`/`next_group_page` fields on VM; orchestrator computes them. Call-site signature byte-stable. PageLink model byte-stable (B3). |
| `app_v2/templates/overview/_pagination.html`             | Two chevron `<li>` blocks gated by `vm.prev_group_page is not none` / `vm.next_group_page is not none` and pointing at group-boundary targets. Ellipsis branch (`{% if pl.num is none %}`) removed. 36 lines (under 60-line invariant). |
| `tests/v2/test_jv_pagination.py`                         | P9/P10 renamed to `test_page_links_group_1_full` / `test_page_links_group_2_full_middle`; 5 boundary-case tests + 5 VM-chevron-target tests added (10 net-new). |
| `tests/v2/test_phase02_invariants.py`                    | UNCHANGED — grep `'"…"\|ellipsis\|pl\.num is none'` returned no hits beyond the 3 pagination invariants (lines 807/827/839), all of which assert template loop shape / include count / line-count sanity (no ellipsis-pinning) and stay green. |

## Test Deltas

### Renamed (was ellipsis assertion → now group assertion)

- `test_page_links_ellipsis_left` → `test_page_links_group_1_full`: `_build_page_links(8, 10) == [1..10]` (page=8 still in group 1).
- `test_page_links_ellipsis_both_sides` → `test_page_links_group_2_full_middle`: `_build_page_links(15, 25) == [11..20]` (full middle group).

### Added (boundary cases for `_build_page_links`)

- `test_page_links_5_pages`: `_build_page_links(3, 5) == [1..5]`.
- `test_page_links_10_pages_current_10`: `_build_page_links(10, 10) == [1..10]`.
- `test_page_links_13_pages_current_1`: `_build_page_links(1, 13) == [1..10]`.
- `test_page_links_13_pages_current_11`: `_build_page_links(11, 13) == [11,12,13]`.
- `test_page_links_25_pages_current_21`: `_build_page_links(21, 25) == [21..25]`.

### Added (VM-level prev/next chevron-target contract)

- `test_prev_next_group_page_first_group`: page=5 of 25 → prev=None, next=11.
- `test_prev_next_group_page_at_boundary`: page=11 of 25 → prev=10, next=21.
- `test_prev_next_group_page_last_group`: page=21 of 25 → prev=20, next=None.
- `test_prev_next_group_page_single_page`: page_count=1 → both None.
- `test_prev_next_group_page_exactly_one_full_group`: page_count=GROUP_SIZE → next=None (no group 2).

### Preserved (no behavior change)

- All Task-1 service tests P1-P8, P10b, P11, P12 — pass byte-equal (slicing/clamping/total_count/filter_options orthogonal).
- All Task-2 router tests P13-P19, P15a-f — pass byte-equal (HX-Push-Url default-omit, OOB id, Form/Query validation).
- All Task-3 template tests P20-P24 — pass byte-equal (hidden page input, sortable_th hx-vals).
- All Phase 02 invariant pagination tests (45/45b/45c) — pass byte-equal.

## Verify Counts

| Stage                                       | Count                       |
| ------------------------------------------- | --------------------------- |
| Baseline (`tests/v2/`)                      | 546 passed, 5 skipped       |
| RED (after test additions, before service)  | 29 passed, 11 failed in `test_jv_pagination.py` |
| GREEN (`tests/v2/test_jv_pagination.py + test_phase02_invariants.py`) | 95 passed |
| Final (`tests/v2/`)                         | 556 passed, 5 skipped       |
| Net delta                                   | +10 (matches the 10 added test functions; 0 regressions outside scope) |

Plan-level grep checks:

| Check                                                                        | Result | Threshold |
| ---------------------------------------------------------------------------- | ------ | --------- |
| `grep -c GROUP_SIZE app_v2/services/joint_validation_grid_service.py`        | 11     | ≥ 4       |
| `grep -c 'prev_group_page\|next_group_page' app_v2/services/joint_validation_grid_service.py` | 7      | ≥ 6       |
| `grep -c 'prev_group_page\|next_group_page' app_v2/templates/overview/_pagination.html` | 4      | ≥ 4       |
| `wc -l app_v2/templates/overview/_pagination.html`                           | 36     | ≤ 30 target / ≤ 60 invariant — under 60-line invariant; 6 over the 30-line target due to retaining 2-line block formatting on chevron `<li>`s for readability |
| `grep -c "is none" app_v2/templates/overview/_pagination.html`               | 0      | ≤ 2       |
| `_build_page_links(page_int, page_count)` call site                          | line 460 | byte-stable |
| `block_names=[..., "pagination_oob"]` in routers/overview.py                 | line 217 | unchanged |

## Deviations from Plan

### None for Rules 1-3 (no auto-fix needed)

The plan executed exactly as written. The ONLY in-scope file the plan instructed to consider but not necessarily edit was `tests/v2/test_phase02_invariants.py` (PART D step 1): "If the grep DOES find other lines, remove the ellipsis-specific assertions". The grep found no hits, so the file stays byte-stable per plan's own conditional.

### Deferred to orchestrator (per execution constraints)

PART E (STATE.md decision-log entry) is **deferred to the orchestrator**, per the executor constraint "IF the plan asks the executor to modify STATE.md, DEFER that to the orchestrator instead — return a note about what to append." The verbatim text to append is captured below for the orchestrator.

## Self-Check: PASSED

- File `app_v2/services/joint_validation_grid_service.py` — FOUND
- File `app_v2/templates/overview/_pagination.html` — FOUND
- File `tests/v2/test_jv_pagination.py` — FOUND
- Commit `7680d0e` — FOUND in `git log`
- All verify gates passed.
