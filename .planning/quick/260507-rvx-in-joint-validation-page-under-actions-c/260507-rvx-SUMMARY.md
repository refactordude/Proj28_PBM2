---
phase: quick-260507-rvx
plan: 01
subsystem: joint-validation-ui
tags: [ui, joint-validation, grid, actions-column, css]
requires: []
provides:
  - "JV grid Actions column: equal-width buttons (edm / 컨플 / AI), centered, no leading icons"
  - ".jv-action-btn CSS class: min-width 56px + text-align center"
affects:
  - app_v2/templates/overview/_grid.html
  - app_v2/static/css/app.css
tech-stack:
  added: []
  patterns:
    - "Stable CSS-class hook (.jv-action-btn) applied to a 3-button row in a Bootstrap table cell to enforce uniform sizing without touching Bootstrap's .btn cascade"
key-files:
  created: []
  modified:
    - app_v2/templates/overview/_grid.html
    - app_v2/static/css/app.css
decisions:
  - "Append .jv-action-btn at end of each existing class string (Bootstrap class order is non-semantic) — keeps the diff minimal: single space + new token per class string."
  - "min-width: 56px chosen to comfortably fit the widest label (컨플 — 2 CJK glyphs ≈ 28-30px text-width + Bootstrap btn-sm padding-x 8px each side) with breathing margin."
  - "Explicit text-align: center on .jv-action-btn even though .btn already centers — defends against any inherited text-align from the parent <td class=\"text-center\">."
  - "컨플 button text preserved verbatim (no icon was present, no change required) — required by 5 existing tests asserting `\"컨플\" in body`."
metrics:
  duration: ~10min
  tasks: 2
  files: 2
  completed: 2026-05-07
---

# Quick Task 260507-rvx: Joint Validation Actions Column Cleanup — Summary

Three small UI tweaks to the Joint Validation grid's Actions column: stripped leading Bootstrap-Icon glyphs from the edm and AI buttons, made all three Actions buttons (edm / 컨플 / AI) render at uniform width via a new `.jv-action-btn` class, and switched the Actions column from right-aligned to center-aligned.

## What Was Done

### Task 1: `app_v2/templates/overview/_grid.html` — 5 markup edits (commit `1bbba03`)

| Edit | Element                          | Before                                                       | After                                                              |
| ---- | -------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------ |
| A    | Actions `<th>`                   | `class="text-end"`                                           | `class="text-center"`                                              |
| B    | Actions `<td>`                   | `class="text-end"`                                           | `class="text-center"`                                              |
| C    | edm active `<a>`                 | `btn btn-sm btn-outline-secondary text-dark` + `<i bi-link-45deg> edm` | `... text-dark jv-action-btn` + bare `edm`                         |
| D    | edm disabled `<button>`          | `btn btn-sm btn-outline-secondary` + `<i bi-link-45deg> edm` | `... jv-action-btn` + bare `edm`                                   |
| E    | 컨플 active `<a>`                | `btn btn-sm btn-outline-secondary text-dark ms-1`            | `... text-dark ms-1 jv-action-btn` (text unchanged: `컨플`)        |
| F    | 컨플 disabled `<button>`         | `btn btn-sm btn-outline-secondary ms-1`                      | `... ms-1 jv-action-btn` (text unchanged: `컨플`)                  |
| G    | AI `<button>`                    | `btn btn-sm btn-outline-primary ms-1` + `<i bi-magic> AI`    | `... ms-1 jv-action-btn` + bare `AI`                               |

(Edits C & D both touch the edm pair; E & F both touch the 컨플 pair → 5 distinct elements receive `.jv-action-btn`.)

**Preserved verbatim:** every `href`, `target`, `rel`, `aria-label`, `disabled`, all HTMX attrs (`hx-post`, `hx-target`, `hx-swap`, `hx-headers`, `data-bs-toggle`, `data-bs-target`), the 9 `sortable_th(...)` calls above the Actions header, and the empty-state `<td colspan="10" class="text-center text-muted py-4">` cell.

### Task 2: `app_v2/static/css/app.css` — 1 new CSS rule (commit `b42e2fe`)

Appended at end of file with traceability comment:

```css
/* JV grid Actions column — quick task 260507-rvx. ... */
.jv-action-btn {
  min-width: 56px;
  text-align: center;
}
```

No other CSS rule touched. `tokens.css` not modified.

## Verification

| Check                                                                          | Result   |
| ------------------------------------------------------------------------------ | -------- |
| `grep -c 'class="text-end"' _grid.html`                                        | `0`      |
| `grep -c 'bi-link-45deg' _grid.html`                                           | `0`      |
| `grep -c 'bi-magic' _grid.html`                                                | `0`      |
| `grep -c 'jv-action-btn' _grid.html`                                           | `5`      |
| `grep -q '<th class="text-center">Actions</th>'`                               | match    |
| `grep -q '<td class="text-center">'`                                           | match    |
| `grep -c 'jv-action-btn' app.css`                                              | `2` (rule selector + comment reference) |
| `grep -q 'min-width: 56px' app.css`                                            | match    |
| `tests/v2/` suite                                                              | 578 passed, 5 skipped, 2 deselected (see Deferred Issues) |

`컨플` literal preservation invariant: **HELD** (no change to 컨플 text in either the active anchor or the disabled button branch; 5 tests asserting `"컨플" in body` continue to pass).

Test count delta: **0** (pure UI tweak; no test files modified).

## Deviations from Plan

None — plan executed exactly as written. All 7 sub-edits applied verbatim, in the order specified.

## Deferred Issues

Three pre-existing test failures discovered while running the v2 suite. **Verified pre-existing** by re-running with the working tree stashed — failures reproduce on the clean baseline that the plan was authored against. Logged to `.planning/quick/260507-rvx-in-joint-validation-page-under-actions-c/deferred-items.md`:

1. `test_joint_validation_invariants.py::test_jv_filter_bar_uses_picker_popover_macro_unmodified` — D-JV-11 invariant in `_filter_bar.html`; asserts 6 `picker_popover(` calls, file has 5 (likely stale w.r.t. quick-260507-rmj which dropped Status/End columns).
2. `test_phase02_invariants.py::test_overview_filter_bar_six_picker_calls` — same root cause; D-UI2-09 invariant on the same file, also asserts exactly 6 picker calls.
3. `test_jv_pagination.py::test_filter_options_built_from_all_rows_not_paged` — transient ordering side effect; passes in isolation. Likely caused by the 6 new untracked `content/joint_validation/3193868*` fixture folders in the working tree.

None of these touch `_grid.html`, `app.css`, or the Actions column.

## Self-Check: PASSED

- `app_v2/templates/overview/_grid.html` modifications committed at `1bbba03`
- `app_v2/static/css/app.css` modification committed at `b42e2fe`
- All Task 1 + Task 2 `<verify>` automated commands pass
- All `<done>` criteria met for both tasks
- Plan's `must_haves.truths` (6 statements) all hold:
  - edm renders only `edm` text (active + disabled) — verified (no `bi-link-45deg`)
  - AI renders only `AI` text — verified (no `bi-magic`)
  - 컨플 text unchanged — verified (no diff to 컨플 lines)
  - Three Actions buttons render at same visual width — enforced by `.jv-action-btn { min-width: 56px }`
  - Actions `<th>` is center-aligned — verified (`<th class="text-center">Actions</th>`)
  - Actions `<td>` is center-aligned — verified (`<td class="text-center">`)
- Plan's `must_haves.artifacts` both satisfied:
  - `_grid.html` contains `text-center` — verified
  - `app.css` contains `.jv-action-btn` — verified
- Plan's `must_haves.key_links` satisfied:
  - `.jv-action-btn` class appears in both `_grid.html` (5x) and `app.css` (1 rule) — verified
