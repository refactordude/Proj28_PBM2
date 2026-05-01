---
phase: 02-ui-shell-rewrite-browse-footer-joint-validation-layout-parit
plan: "03"
subsystem: ui-jv-layout
tags: [htmx, oob-swap, tdd, jinja2, css, flex, browse-parity]
requires: [02-01, 02-02]
provides: [jv-single-panel, jv-panel-header-count, jv-horizontal-filter-row]
affects:
  - app_v2/templates/overview/index.html
  - app_v2/templates/overview/_filter_bar.html
  - app_v2/static/css/app.css
  - tests/v2/test_phase02_invariants.py
tech-stack:
  added: []
  patterns: [htmx-oob-merge-by-id, jinja2-include-inside-panel, tdd-grep-invariants, css-flex-filter-row]
key-files:
  created: []
  modified:
    - app_v2/templates/overview/index.html
    - app_v2/templates/overview/_filter_bar.html
    - app_v2/static/css/app.css
    - tests/v2/test_phase02_invariants.py
decisions:
  - "D-UI2-07: JV two-panel layout collapsed into one outer .panel; .overview-filter-bar wrapper loses .panel class — nested inside outer panel"
  - "D-UI2-08: .overview-filter-bar CSS updated to display:flex gap:8px align-items:center flex-wrap:wrap border-bottom; <form> is flex container (d-flex gap-2 flex-wrap w-100)"
  - "D-UI2-09: picker_popover macro import byte-stable from browse/_picker_popover.html — no fork"
  - "D-UI2-10: Clear all link class changed from ms-2 to ms-auto for right-alignment in flex row"
  - "D-UI2-11: <span id='overview-count'> moved from .panel-body into .panel-header right zone via ms-auto"
  - "D-UI2-12: <h1 class='panel-title'>Joint Validation</h1> inside panel-header; standalone .page-head block removed"
  - "W1 receiver/emitter alignment: count_oob block changed from <div> to <span> to match panel-header receiver tag — HTMX merge-by-id stays correct regardless"
  - "B1 filter badges: visibility preserved; legacy outer wrapper (overview-filter-badges-wrapper) removed; inner OOB div repositioned below filter bar above grid with px-3 pt-2 spacing"
  - "Test 30 fix: comment text 'picker_popover()' reworded to avoid false-match in 6-call grep"
  - "Test 31 fix: use '<form id=' prefix instead of 'id=' to avoid false-match on picker form_id= params"
  - "Test 35b fix: comment containing '<span id=\"overview-count\">' reworded to '#overview-count span' to avoid triple-count"
metrics:
  duration: "10min"
  completed: "2026-05-01"
  tasks: 3
  files: 4
---

# Phase 02 Plan 03: JV Layout Parity — Single Panel + Horizontal Filter Row Summary

**One-liner:** Joint Validation listing restructured into a single Browse-mirror `.panel` with `<h1>` + count in the panel-header, six filter dropdowns in a horizontal flex row via the byte-stable picker macro, and all OOB swap targets preserved by id.

---

## What Was Built

Three discrete tasks collapsed the JV two-panel structural mistake into one, matched Browse's visual language, and locked the design with 19 new invariant tests (tests 22-40 + 35b).

### Task 1 — CSS flex layout for .overview-filter-bar (D-UI2-08)

`app_v2/static/css/app.css` `.overview-filter-bar` rule replaced:

- Old: `padding: 0 26px` (single property — caused dropdowns to stack vertically as block elements)
- New: `padding: 16px 24px 0; border-bottom: 1px solid var(--line); display: flex; align-items: center; gap: 8px; flex-wrap: wrap;`

The `.panel.overview-filter-bar { overflow: visible }` self-match selector (260430-wzg safety net) was preserved byte-stable. Browse's `.browse-filter-bar` rule untouched.

### Task 2 — overview/_filter_bar.html horizontal flex form (D-UI2-07/08/09/10)

`app_v2/templates/overview/_filter_bar.html` rewritten:

- Wrapper `<div>`: `class="overview-filter-bar panel"` → `class="overview-filter-bar"` (D-UI2-07 — no `.panel` class)
- `<form>`: gains `class="d-flex align-items-center gap-2 flex-wrap w-100"` making the form the flex container (D-UI2-08)
- Clear all: class `ms-2 btn btn-link btn-sm` → `ms-auto btn btn-link btn-sm` (D-UI2-10 — right-aligned)
- `{% from "browse/_picker_popover.html" import picker_popover %}` byte-stable (D-UI2-09)
- Six `picker_popover()` calls byte-stable (parameters verbatim from Phase 01 Plan 05)

### Task 3 — overview/index.html single-panel Browse-mirror layout (D-UI2-07/11/12)

`app_v2/templates/overview/index.html` fully restructured:

- **Removed:** standalone `.page-head` div (h1 was outside the panel — D-UI2-12 fix)
- **Added:** single outer `<div class="panel">` wrapping everything
- **Added:** `<div class="panel-header" id="overview-panel-header">` containing:
  - `<h1 class="panel-title">Joint Validation</h1>` (left zone — D-UI2-12)
  - `<span id="overview-count" class="ms-auto text-muted small" aria-live="polite">` (right zone — D-UI2-11)
- **Changed:** `count_oob` block emitter from `<div>` to `<span>` to match receiver tag (W1)
- **Preserved:** filter badges div with `id="overview-filter-badges"` — still visible, repositioned below filter bar and above grid with `class="px-3 pt-2"`; legacy `overview-filter-badges-wrapper` outer div removed (B1)
- **Preserved byte-stable:** `sortable_th` macro inside `{% block grid %}` (Pitfall 8), AI Summary modal + JS listener, `{% include "overview/_grid.html" %}`
- **Preserved:** `block_names=["grid", "count_oob", "filter_badges_oob"]` — router unchanged, all three blocks still present by the same names

---

## Commits

| Hash | Type | Description |
|------|------|-------------|
| e3774c5 | feat | Update .overview-filter-bar CSS to flex-row layout (D-UI2-08) |
| 19fbb4e | feat | Restructure JV filter bar to horizontal flex form (D-UI2-07/08/09/10) |
| 39494b9 | feat | Restructure JV listing into single-panel Browse-mirror layout (D-UI2-07/11/12) |

---

## Verification Results

- 19 new invariant tests (22-40 + 35b) appended to `tests/v2/test_phase02_invariants.py` — all green.
- Full v2 suite: **403 passed, 5 skipped, 0 failures** — zero regressions.
- All acceptance greps pass:
  - `grep -c '<div class="page-head' overview/index.html` → `0`
  - `grep -c '<div class="panel">' overview/index.html` → `1`
  - `grep -c '<h1 class="panel-title">Joint Validation</h1>' overview/index.html` → `1`
  - `grep -c 'id="overview-count"' overview/index.html` → `2`
  - `grep -c '<span id="overview-count"' overview/index.html` → `2`
  - `grep -c 'padding: 0 26px' app.css` → `0`
  - `grep -c '\.panel\.overview-filter-bar' app.css` → `2` (safety net preserved)
  - `grep -c 'padding: 12px 26px 0' app.css` → `1` (Browse byte-stable)
  - `grep -c 'class="overview-filter-bar panel"' _filter_bar.html` → `0`
  - `grep -c 'picker_popover(' _filter_bar.html` → `6`
  - badges placement awk → `OK`
  - `grep -c 'visually-hidden' overview/index.html` → `0`

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test 30: comment text contained picker_popover() causing false 7th count**
- **Found during:** Task 2 GREEN verification
- **Issue:** The Jinja comment in `_filter_bar.html` said "The 6 picker_popover() calls are byte-stable" — the substring `picker_popover(` appears in this comment, making `src.count("picker_popover(")` return 7 instead of 6.
- **Fix:** Reworded comment to "The 6 picker macro calls are byte-stable" — removes the parenthesis from the comment text.
- **Files modified:** `app_v2/templates/overview/_filter_bar.html`
- **Commit:** 19fbb4e

**2. [Rule 1 - Bug] Test 31: id="overview-filter-form" substring matched inside form_id= params**
- **Found during:** Task 2 GREEN verification
- **Issue:** `src.count('id="overview-filter-form"')` returned 7: 1 for the `<form id="overview-filter-form"` element tag, plus 6 for the picker calls' `form_id="overview-filter-form"` parameters (the string `id="overview-filter-form"` appears as a substring of `form_id="overview-filter-form"`).
- **Fix:** Changed test assertion from `src.count('id="overview-filter-form"') == 1` to `src.count('<form id="overview-filter-form"') == 1` — the `<form id=` prefix is unambiguous and cannot match `form_id=`.
- **Files modified:** `tests/v2/test_phase02_invariants.py`
- **Commit:** 19fbb4e

**3. [Rule 1 - Bug] Test 35b: Jinja comment contained '<span id="overview-count">' causing triple count**
- **Found during:** Task 3 GREEN verification
- **Issue:** The comment block in `overview/index.html` explaining the OOB merge mechanism used the literal text `<span id="overview-count">`, which matched the test's `src.count('<span id="overview-count"')` check and returned 3 instead of the expected 2.
- **Fix:** Reworded comment to use `#overview-count span` and `div to span` phrasing — removes the exact tag substring from the comment text (same pattern as Plan 02-02's fix for `id="grid-count"` in comments).
- **Files modified:** `app_v2/templates/overview/index.html`
- **Commit:** 39494b9

---

## Known Stubs

None — this plan restructures layout only. All rendered data (`vm.total_count`, filter badges from `vm.active_filter_counts`, picker options from `vm.filter_options`) flows from the real view-model. No hardcoded placeholder values introduced.

---

## Threat Surface Scan

No new trust boundaries introduced. All changes are template structure and CSS:
- `overview/index.html` restructure moves existing OOB targets within the DOM — no new input surfaces, no new routes, no new user-data rendering paths.
- The `id="overview-count"` OOB target changes DOM location (panel-body → panel-header) but the id is unchanged — HTMX still merges by id; no new attack surface.
- Filter badges (`id="overview-filter-badges"`) similarly repositioned within the panel — same OOB mechanism, same id, no new surface.

Matches T-02-03-01 through T-02-03-06 in the plan's threat model — all mitigations in place (Tests 35/36/40 enforce single-id consistency; `| e` escaping unchanged; macro byte-stable; Clear all link hard-coded route unchanged).

---

## Self-Check: PASSED

Files exist:
- `app_v2/static/css/app.css` — FOUND
- `app_v2/templates/overview/index.html` — FOUND
- `app_v2/templates/overview/_filter_bar.html` — FOUND
- `tests/v2/test_phase02_invariants.py` — FOUND

Commits exist:
- e3774c5 — FOUND
- 19fbb4e — FOUND
- 39494b9 — FOUND
