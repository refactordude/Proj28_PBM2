---
phase: 04-browse-tab-port
plan: 03
subsystem: ui
tags: [browse, templates, jinja2, htmx, bootstrap, css, javascript, popover, sticky-header, picker-checklist]

# Dependency graph
requires:
  - phase: 01-foundation-shell
    provides: base.html shell + tokens.css token layer + app.css component classes (.shell/.panel/.panel-body/.panel-header) + Jinja2Blocks templates singleton + htmx-error-handler.js IIFE pattern
  - phase: 03-content-pages-ai-summary
    provides: app.css Phase 03 component classes intact (Phase 04 appends only — never modifies); design-token vocabulary (--bs-light, --line, --line-2, --ink, --ink-2, --mute, --dim, --bg, --panel)
  - phase: 04-browse-tab-port (plan 04-02)
    provides: BrowseViewModel dataclass (13 fields) + GET /browse + POST /browse/grid + HX-Push-Url canonical URL composition + block_names=["grid", "count_oob", "warnings_oob"] fragment-render contract — templates in this plan consume those fields and blocks verbatim
provides:
  - app_v2/templates/browse/index.html — full Browse page; defines blocks `grid`, `count_oob`, `warnings_oob` for fragment renders consumed by POST /browse/grid
  - app_v2/templates/browse/_filter_bar.html — filter bar fragment (Platforms picker + Parameters picker + Swap toggle + Clear-all link)
  - app_v2/templates/browse/_picker_popover.html — reusable Jinja macro `picker_popover(name, label, options, selected)` for both Platforms and Parameters pickers
  - app_v2/templates/browse/_grid.html — pivot table fragment with header/body parity (Issue 5 fix)
  - app_v2/templates/browse/_warnings.html — row-cap and col-cap alert fragments (verbatim D-24 copy)
  - app_v2/templates/browse/_empty_state.html — empty-state alert (verbatim D-25 copy — "above", not "in the sidebar")
  - app_v2/static/js/popover-search.js — 79-line IIFE handling popover search + Apply close + Clear + restore-on-close
  - app_v2/static/css/app.css — Phase 04 additions: .browse-filter-bar, .browse-grid-body, .pivot-table rules
  - app_v2/templates/base.html — popover-search.js script tag (defer, after htmx-error-handler.js)
affects: [04-04]

# Tech tracking
tech-stack:
  added: []   # No new dependencies — pure Bootstrap 5.3.8 / HTMX 2.0.10 / Jinja2 3.1.6 / vanilla JS / CSS
  patterns:
    - "Pattern 3 (RESEARCH.md) — HTMX form aggregation across both pickers via empty <form id=browse-filter-form> + form= attribute on checkboxes (Pitfall 4 defended)"
    - "Pattern 4 (RESEARCH.md) — popover-search.js: document-level event delegation over six handlers; no per-popover wiring; no MutationObserver needed because event delegation is bubbling-based"
    - "Pattern 5 (RESEARCH.md) — sticky thead inside vertical-scroll panel-body container (.browse-grid-body has max-height:70vh + overflow-y:auto so position:sticky on <thead> engages); Pitfall 1 defended"
    - "Pattern 6 (RESEARCH.md) — block-named fragment rendering with OOB swaps; #grid-count lives in .panel-header OUTSIDE #browse-grid so OOB swaps land in a stable element never replaced by the primary innerHTML swap (Pitfall 7 defended)"
    - "Issue 5 fix (plan-checker) — _grid.html <tbody> rows mirror <thead> structure: index cell rendered explicitly via row[vm.index_col_name] FIRST, then loop emits non-index value cells via `for col in vm.df_wide.columns if col != vm.index_col_name`. Header/body parity does NOT depend on pandas column order."
    - "IIFE + 'use strict' + document-level event delegation matches the htmx-error-handler.js style (single source of truth for both Platforms and Parameters pickers via bubbling events)"
    - "Defense-in-depth XSS: every dynamic Jinja2 output uses `| e` even though autoescape is globally on for .html templates (T-04-03-01..T-04-03-04 mitigations)"

key-files:
  created:
    - app_v2/templates/browse/index.html
    - app_v2/templates/browse/_filter_bar.html
    - app_v2/templates/browse/_picker_popover.html
    - app_v2/templates/browse/_grid.html
    - app_v2/templates/browse/_warnings.html
    - app_v2/templates/browse/_empty_state.html
    - app_v2/static/js/popover-search.js
  modified:
    - app_v2/static/css/app.css (Phase 04 block appended; Phase 03 rules untouched)
    - app_v2/templates/base.html (one-line script tag added — popover-search.js with defer, after htmx-error-handler.js)

key-decisions:
  - "Issue 5 fix (header/body parity) — rather than relying on pandas df_wide.columns order to put the index column first, _grid.html explicitly renders the index cell FIRST in both <thead> and <tbody>, then loops over `for col in vm.df_wide.columns if col != vm.index_col_name`. This guarantees the index column position regardless of pandas reset_index() conventions. A Jinja comment near <tbody> documents the intent so future editors don't 'simplify' the loop and reintroduce the parity bug."
  - "popover-search.js trimmed to 79 lines (acceptance criterion: <80) — eliminated multi-line JSDoc header in favor of a single-line module comment so `head -3 | grep 'use strict'` passes; behavior preserved verbatim across all six handlers (onInput, onCheckboxChange, onClearClick, onDropdownShow, onDropdownHide, onApplyClick)."
  - "Defense-in-depth `| e` on every dynamic output across all templates — even though Jinja2 autoescape is globally on for .html files, the explicit filter is belt-and-suspenders defense against future template-loader changes (autoescape off by accident → silent XSS). Plan 04-04 invariant test will assert no `| safe` filter appears anywhere in app_v2/templates/browse/."
  - "OOB count caption located in .panel-header (outside #browse-grid) — Pitfall 7 defended. The HTMX innerHTML swap on #browse-grid does NOT touch the persistent shell, so the OOB span lands in a stable target. Mirrors Phase 02's filter-count-badge pattern."
  - "Empty <form id=browse-filter-form> placed BEFORE the filter-bar include — Pitfall 4 defended. Picker checkboxes use form=… attribute association (HTML standard) so they participate in the form even though they're DOM-children of dropdown menus, not the form itself."
  - "popover-search.js uses ES5 var/function syntax (not arrow functions or const/let) — matches htmx-error-handler.js for stylistic consistency. No transpilation; works in any browser supporting Bootstrap 5.3.8 (Edge 79+, Chrome 60+, Firefox 60+, Safari 12+)."
  - "Phase 04 CSS appended verbatim from UI-SPEC §'New CSS Added to app.css (Phase 04)' — no Phase 03 rules modified. The .browse-grid-body { padding: 0 } declaration overrides Phase 03's .panel-body { padding: 26px 32px } via CSS source order (the Browse panel body element carries BOTH classes; later declarations win for `padding`)."

patterns-established:
  - "Picker-checklist Jinja macro pattern — reusable for any future multi-select widget on the page; macro signature is (name, label, options, selected) which is generic enough to drop into Phase 5 Ask tab parameter confirmation if needed"
  - "Issue-5-style header/body parity invariant — when rendering pandas DataFrame to HTML <table>, never trust df.columns order; always explicitly emit the index column FIRST and loop over `if col != index_col_name` for the rest. Future grid templates should follow this pattern."
  - "Single-line module comment + IIFE + 'use strict' pattern for utility JS — keeps `head -3` greppable for the strict-mode marker while still self-documenting on line 1"
  - "Empty form-shell + form= attribute association pattern for HTMX hx-include selectors targeting controls inside dropdowns/popovers/modals — extends to any future Bootstrap dropdown that needs to participate in form aggregation"

requirements-completed: [BROWSE-V2-02, BROWSE-V2-03]

# Metrics
duration: 9m
completed: 2026-04-26
---

# Phase 4 Plan 03: Browse Templates + popover-search.js + CSS Summary

**Six Jinja templates + 79-line popover-search.js + 53-line Phase 04 CSS append + 1-line base.html script wire-up. All four tasks executed cleanly with three small Rule-1 deviations (acceptance-grep compliance) and one Rule-3 deviation (popover-search.js trimmed to <80 LOC). Templates render end-to-end; FastAPI app starts; tests/v2 Phase 1-3 regression: 83 passed, 1 skipped.**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-04-26T13:37:32Z
- **Completed:** 2026-04-26T13:46:22Z
- **Tasks:** 4
- **Files created:** 7 (6 templates + popover-search.js)
- **Files modified:** 2 (app.css append + base.html one-line script tag)

## Accomplishments

- **Picker popover macro** (`_picker_popover.html`): single Jinja macro reused by both Platforms and Parameters pickers. Trigger button shows count badge ONLY when selection is non-empty (D-08). Popover dropdown stays open during checkbox interaction via `data-bs-auto-close="outside"` (D-09). Apply button fires `hx-post=/browse/grid` with `hx-include="#browse-filter-form input:checked"` and closes the dropdown via `bootstrap.Dropdown.getInstance(...).hide()` (D-14). Popover-internal Clear button empties checkboxes only — no HTMX (D-15).
- **Filter bar** (`_filter_bar.html`): single d-flex row containing both pickers, the swap-axes btn-check toggle (D-16: hx-trigger=change for immediate fire), and the Clear-all link (D-17, D-18: hidden via d-none when no selection, single hx-post with hx-vals='{}').
- **Pivot table** (`_grid.html`): `table table-striped table-hover table-sm pivot-table` with `<thead class="sticky-top bg-light">`. Issue 5 fix — `<tbody>` rows mirror `<thead>` structure (index cell explicit, then non-index loop) so header/body parity does NOT depend on pandas column order.
- **Cap warnings + empty state** (`_warnings.html`, `_empty_state.html`): verbatim D-24/D-25 copy. The exact strings "Result capped at 200 rows. Narrow your platform or parameter selection to see all data." and "Showing first 30 of {N} parameters. Narrow your selection to see all." and "Select platforms and parameters above to build the pivot grid." are pinned for Plan 04-04 invariant tests.
- **Index page** (`index.html`): full page shell extending base.html. `.panel-header` carries the persistent `<span id="grid-count">` (Pitfall 7 defended — outside `#browse-grid`). Empty `<form id="browse-filter-form">` placed BEFORE filter-bar include (Pitfall 4 defended). `.browse-grid-body` is the vertical-scroll container so `<thead class="sticky-top">` engages (Pattern 5 / Pitfall 1).
- **popover-search.js** (79 lines): IIFE + "use strict" + document-level event delegation over six handlers. No external network calls (HTMX is the only data fetcher). Mirrors htmx-error-handler.js style.
- **Phase 04 CSS** appended to app.css with a clear `============ Phase 04 — Browse Tab ============` header. Phase 03 rules untouched. New rules: `.browse-filter-bar`, `.browse-grid-body`, `.pivot-table` family. The `.browse-grid-body { padding: 0 }` declaration intentionally overrides Phase 03's `.panel-body { padding: 26px 32px }` via CSS source order on the same element.
- **base.html wiring**: one-line script tag for `popover-search.js` with `defer`, AFTER `htmx-error-handler.js`. Final load order: `bootstrap.bundle.min.js → htmx-error-handler.js → popover-search.js`, all `defer`, so document-source order ensures Bootstrap is parsed before popover-search.js calls `bootstrap.Dropdown.getInstance(...)`.

## Task Commits

Each task committed atomically:

1. **Task 1 — picker_popover macro + filter bar template** — `d1932eb` (feat)
2. **Task 2 — index page + grid/warnings/empty-state fragments** — `04e6179` (feat)
3. **Task 3 — popover-search.js + Phase 04 CSS additions** — `f4207c0` (feat)
4. **Task 4 — wire popover-search.js into base.html** — `2784ced` (feat)

**Plan metadata commit:** _pending — final commit covers SUMMARY + STATE + ROADMAP progress + REQUIREMENTS marks_

## Files Created

| Path | Lines | Purpose |
|------|-------|---------|
| `app_v2/templates/browse/_picker_popover.html` | 92 | Reusable Jinja macro `picker_popover(name, label, options, selected)` |
| `app_v2/templates/browse/_filter_bar.html` | 61 | Filter bar (Platforms picker + Parameters picker + Swap toggle + Clear-all) |
| `app_v2/templates/browse/index.html` | 71 | Full Browse page; defines blocks `grid`, `count_oob`, `warnings_oob` |
| `app_v2/templates/browse/_grid.html` | 51 | Pivot table with Issue 5 fix (header/body parity) |
| `app_v2/templates/browse/_warnings.html` | 18 | Row-cap + col-cap alerts (verbatim D-24 copy) |
| `app_v2/templates/browse/_empty_state.html` | 9 | Empty-state alert (verbatim D-25 copy — "above", not "in the sidebar") |
| `app_v2/static/js/popover-search.js` | 79 | IIFE with six event handlers; document-level delegation |

## Files Modified

| Path | Change |
|------|--------|
| `app_v2/static/css/app.css` | Phase 04 block appended (lines 80-137); Phase 03 rules untouched (verified — `.shell`, `.panel`, `.panel-header`, `.panel-body`, `.ai-btn`, `.markdown-content` all intact at original positions) |
| `app_v2/templates/base.html` | One-line addition: `<script src="…/popover-search.js" defer>` after `htmx-error-handler.js` (preceded by a 4-line Jinja comment explaining the defer-order rationale) |

## popover-search.js Final Composition

**Final line count:** 79 (acceptance criterion: <80; underflow by 1 line)

Six handlers, all retained verbatim per Pattern 4 of RESEARCH.md:

| Handler | Trigger | Behavior |
|---------|---------|---------|
| `onInput` | `input` event on `.popover-search-input` | Substring filter (case-insensitive); hides `<li>` rows where `data-label` doesn't include the query (D-10) |
| `onCheckboxChange` | `change` event on `.popover-search-root input[type="checkbox"]` | Updates `.popover-apply-count` badge with the count of checked checkboxes |
| `onClearClick` | `click` on `.popover-clear-btn` | Empties checkboxes, dispatches synthetic `change` events to update badge — does NOT fire HTMX (D-15) |
| `onDropdownShow` | `show.bs.dropdown` | Stashes original selection to `data-original-selection` (JSON-stringified array); focuses search input via `setTimeout(…, 0)` (Bootstrap fires the event before the menu becomes visible) |
| `onDropdownHide` | `hidden.bs.dropdown` | If `data-applied === '1'` (Apply was clicked), clear the flag and skip restore. Otherwise parse `data-original-selection`, restore each checkbox's `checked`, reset count badge to original length |
| `onApplyClick` | `click` on `.popover-apply-btn` (or descendant) | Marks `data-applied = '1'` so onDropdownHide skips restore. HTMX fires from the button's own `hx-post`. |

No handlers were consolidated or split; the six-handler decomposition matches Pattern 4 verbatim.

## Confirmation: OOB count span lives OUTSIDE #browse-grid

Verified at template level via Python depth-tracking:

```
$ python3 ...
#browse-grid span: chars 2651..2970, length=319
Pitfall 7: PASS — #grid-count is OUTSIDE #browse-grid
count_oob block: PASS — contains hx-swap-oob span
```

The persistent `<span id="grid-count">` is rendered inside `.panel-header` (above `#browse-grid` in the DOM); the OOB swap target in the `count_oob` block emits a SECOND `<span id="grid-count" hx-swap-oob="true">` on POST responses. HTMX detaches the OOB element from the response body and merges it into the existing `<span id="grid-count">` in the persistent shell. The primary innerHTML swap on `#browse-grid` does NOT touch this element.

Mirrors Phase 02's filter-count-badge pattern (`app_v2/templates/overview/index.html:43-48`).

## Confirmation: NO `| safe` filter anywhere

```
$ grep -c "| safe" app_v2/templates/browse/*.html
app_v2/templates/browse/_empty_state.html:0
app_v2/templates/browse/_filter_bar.html:0
app_v2/templates/browse/_grid.html:0
app_v2/templates/browse/index.html:0
app_v2/templates/browse/_picker_popover.html:0
app_v2/templates/browse/_warnings.html:0
```

Every dynamic output uses Jinja2 `| e` explicit-escape filter. Even though autoescape is globally on for `.html` templates (default for `Jinja2Blocks`), the explicit filter is belt-and-suspenders defense against future template-loader changes that might accidentally disable autoescape (T-04-03-01..T-04-03-04 HIGH-severity threats — all mitigated). Plan 04-04 invariant test will pin this absence with a regression guard.

## Confirmation: `_grid.html` `<tbody>` mirrors `<thead>` structure (Issue 5 fix from plan-checker)

`grep -c "if col != vm.index_col_name" app_v2/templates/browse/_grid.html` → **2** (once in `<thead>`, once in `<tbody>`).

`grep -Fq "row[vm.index_col_name]" app_v2/templates/browse/_grid.html` → succeeds (the explicit index cell render in `<tbody>`).

A Jinja comment near `<tbody>` documents the intent ("Issue 5 fix: body row structure mirrors thead — index col first, then non-index value cols. … Do NOT collapse this back to a single loop over df_wide.columns; that would reintroduce the parity bug if the index column ever drifts to a non-first position in df_wide.").

**End-to-end verification with a hostile DataFrame** (the index column intentionally placed LAST in `df.columns`):

```
df.columns ORIGINAL ORDER: ['attr · vid', 'attr · pid', 'PLATFORM_ID']
thead cells: ['PLATFORM_ID', 'attr · vid', 'attr · pid']
first tbody row: ['A', 'V1', 'P1']
populated-state render OK — Issue 5 (header/body parity) confirmed
```

Even when pandas places `PLATFORM_ID` LAST in `df_wide.columns`, the rendered `<thead>` and `<tbody>` BOTH place it FIRST — header/body parity holds.

## Smoke Render Output

**Empty-state render** (Task 4 verify):
```
empty-state render OK
```
The entire template tree compiles end-to-end with a stub view-model:
`base.html → browse/index.html → browse/_filter_bar.html → browse/_picker_popover.html (macro twice) → browse/_empty_state.html → browse/_warnings.html`.

**Populated-state render** (additional verification beyond the plan body):
```
populated-state render OK — Issue 5 (header/body parity) confirmed
```

**Script-load order in base.html** (Task 4 verify):
```
script-order OK
```

**FastAPI app smoke** (Task 4 verify):
```
Browse routes: ['/browse', '/browse/grid']
```

**Phase 1-3 regression suite** (Task 4 verify):
```
83 passed, 1 skipped in 13.27s
```
The 1 skipped test is the Plan 04-02 tombstone for the old Phase 1 `/browse` placeholder.

## Decisions Made

- **Trim popover-search.js JSDoc to a single-line module comment** — the original 17-line JSDoc header pushed `"use strict"` to line 21, making the acceptance check `head -3 popover-search.js | grep "use strict"` fail. Trimmed to `/* popover-search.js — Browse popover-checklist (D-10, D-14, D-15) */` on line 1 so the IIFE + strict-mode marker land in lines 2-3. Behavior unchanged across all six handlers.
- **Replace `htmx-error-handler.js` line 1 / `_picker_popover.html` comment phrasing** — the literal byte sequences `| safe` and `hx-push-url` in documentation comments tripped the acceptance grep that pins those strings to zero occurrences in the production templates. Comments rephrased ("NEVER bypass autoescape here", "NO client-side push-url") to preserve meaning without the literal bytes.
- **Replace `_empty_state.html` comment phrasing** — the literal string "in the sidebar" in the file's documentation comment tripped the same kind of acceptance grep. Rephrased to "v1.0 sidebar wording" / "not in a sidebar" — meaning preserved, no literal "in the sidebar" bytes.
- **Issue 5 fix kept STRICTLY as plan-body sketched** — `<thead>` and `<tbody>` both emit the index cell explicitly first, then loop with `if col != vm.index_col_name`. Did NOT consolidate to a single row loop over `df.columns` (which would have looked cleaner but reintroduced the parity bug). The Jinja comment near `<tbody>` is intentional anti-foot-gun documentation.
- **Issue 5 cell-rendering chain extended to the index cell too** — the plan body specified `| string | e if … is not none else ""` for value cells but did not explicitly specify the same chain for the index cell. Applied the chain to BOTH branches because Result/Item types are equally heterogeneous (int / Decimal / str) and identical defensive treatment is the only sane invariant. This also satisfies T-04-03-03 mitigation language ("the same chain for the explicit index cell").

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Acceptance grep flagged `| safe` byte sequence inside a documentation comment in `_picker_popover.html`**
- **Found during:** Task 1 acceptance criterion `grep -c "| safe" app_v2/templates/browse/_picker_popover.html app_v2/templates/browse/_filter_bar.html` → expected 0; got 1 (false positive on a docstring describing the policy)
- **Issue:** A header comment "NEVER ` | safe ` here" contained the literal `| safe` byte sequence the grep flags. The strict acceptance criterion forces removal of the literal even from documentation prose.
- **Fix:** Rephrased to "NEVER bypass autoescape here" — meaning preserved, no literal `| safe` bytes.
- **Files modified:** `app_v2/templates/browse/_picker_popover.html`
- **Verification:** `grep -c "| safe" app_v2/templates/browse/_picker_popover.html app_v2/templates/browse/_filter_bar.html` → 0 / 0 (success).
- **Committed in:** `d1932eb` (Task 1 commit, included in initial implementation)

**2. [Rule 1 - Bug] Acceptance grep flagged `hx-push-url` byte sequence inside a documentation comment in `_picker_popover.html`**
- **Found during:** Task 1 acceptance criterion `grep -c "hx-push-url" app_v2/templates/browse/_picker_popover.html` → expected 0; got 1 (false positive on a docstring explaining the design choice)
- **Issue:** A footer comment "NO hx-push-url on Apply; the server sets HX-Push-Url response header from Plan 04-02 D-32" contained the literal `hx-push-url` bytes that the strict acceptance grep flags to prevent accidental future addition of the attribute.
- **Fix:** Rephrased to "NO client-side push-url on Apply; the server sets HX-Push-Url response header" — meaning preserved, no literal `hx-push-url` bytes.
- **Files modified:** `app_v2/templates/browse/_picker_popover.html`
- **Verification:** `grep -c "hx-push-url" app_v2/templates/browse/_picker_popover.html` → 0 (success).
- **Committed in:** `d1932eb` (Task 1 commit, included in initial implementation)

**3. [Rule 1 - Bug] Acceptance grep flagged "in the sidebar" byte sequence inside a documentation comment in `_empty_state.html`**
- **Found during:** Task 2 acceptance criterion `grep -c "in the sidebar" app_v2/templates/browse/_empty_state.html` → expected 0; got 1 (false positive on a docstring describing the v1.0-vs-v2.0 wording change)
- **Issue:** A header comment "Verbatim copy contract — note 'above', NOT 'in the sidebar' (the v1.0 wording…)" contained the literal "in the sidebar" bytes the strict acceptance grep flags to prevent the v1.0 phrasing from leaking back into v2.0.
- **Fix:** Rephrased to "Verbatim copy contract — note 'above', NOT the v1.0 sidebar wording. The v1.0 phrasing is no longer applicable in v2.0 since the filter bar lives at the top of the panel, not in a sidebar." — meaning preserved, no literal "in the sidebar" bytes.
- **Files modified:** `app_v2/templates/browse/_empty_state.html`
- **Verification:** `grep -c "in the sidebar" app_v2/templates/browse/_empty_state.html` → 0 (success).
- **Committed in:** `04e6179` (Task 2 commit, included in initial implementation)

**4. [Rule 3 - Blocking] popover-search.js exceeded 80-line cap with verbose JSDoc header**
- **Found during:** Task 3 acceptance criteria `head -3 popover-search.js | grep -q "use strict"` → expected pass; failed (because line 1-19 was a multi-line JSDoc, pushing `"use strict"` to line 21) AND `wc -l < popover-search.js` < 80 → expected pass; got 104.
- **Issue:** The initial implementation had a 17-line JSDoc-style header documenting the six handlers, the IIFE pattern, and the htmx-error-handler.js style match. Both acceptance criteria (head -3 use-strict location AND <80 LOC) flagged this as a violation.
- **Fix:** Trimmed the multi-line JSDoc to a single-line module comment `/* popover-search.js — Browse popover-checklist (D-10, D-14, D-15) */` so `"use strict"` lands on line 3. Tightened the per-handler comments (consolidated some, removed redundant ones) so total file size dropped to 79 lines. All six handlers and their behavior preserved verbatim — no behavior regression.
- **Files modified:** `app_v2/static/js/popover-search.js`
- **Verification:** `head -3 popover-search.js | grep -q "use strict"` → pass; `wc -l < popover-search.js` → 79 (success).
- **Committed in:** `f4207c0` (Task 3 commit, included in revision before commit)

---

**Total deviations:** 4 auto-fixed (3 Rule-1 grep-acceptance compliance bugs, 1 Rule-3 acceptance blocking).
**Impact on plan:** All four deviations were forced by the plan's own strict acceptance grep criteria (the documentation prose collided with literal-string guards; the JSDoc header collided with both the head-3 marker location AND the <80 LOC cap). All four fixes preserve plan intent verbatim. Zero scope creep — no new features, no new dependencies, no behavior changes. Identical pattern to Plan 04-02's deviations 3 and 4 (literal-string acceptance compliance).

## Issues Encountered

None — four tasks executed cleanly. Each task's acceptance verification ran before commit. The plan-checker's Issue 5 fix is fully implemented in `_grid.html` and verified end-to-end with a hostile-DataFrame smoke render that places `PLATFORM_ID` LAST in `df.columns` and confirms the rendered HTML still places it FIRST in both `<thead>` and `<tbody>`.

## Visual Issues to Flag for Manual Browser Pass (after Plan 04-04)

When the user runs the live app and visits `/browse`, the following items are likely candidates for fine-tuning that this plan deliberately did NOT pre-empt (they are visual polish items, not contract violations):

- **Popover dropdown right-edge clipping on narrow viewports** — the `min-width: 320px; max-width: 480px` style on `.dropdown-menu.popover-search-root` may extend past the right edge on narrow windows (Pitfall 8 of RESEARCH.md). Bootstrap's Popper.js positioning will flip/shift but does not adjust min-width. Verify on a 1024px-wide window.
- **Sticky-thead z-index interaction with popover dropdowns** — `.pivot-table thead.sticky-top { z-index: 2 }` is below Bootstrap dropdowns (`z-index: 1000`) per the CSS, but if a user opens a picker AND scrolls the grid simultaneously, verify the popover still floats above the thead. Should work per Bootstrap defaults but worth eyeballing.
- **Em-dash pseudo-content `\2014` in `.pivot-table td:empty::after`** — only renders for cells where `row[col] is None`. If a Result value is the empty string `""` (not None), the cell will be visually blank without the em-dash. Plan 04-04 may want to extend the CSS or the Jinja chain to treat empty-string the same as None; this plan does not.
- **Swap-axes toggle visual feedback when `vm.swap_axes=True`** — `btn-check` controls the checked state of the underlying checkbox; the `<label class="btn btn-outline-secondary btn-sm">` should switch styling on `:checked`. Verify the active/inactive variants look distinct in the live app.
- **Filter bar `align-items-center` vs picker buttons with badges** — when one picker has a badge and another doesn't, the trigger buttons may have slightly different heights (Bootstrap's `.btn-sm` height is fixed, but a span inside affects line-height). Eyeball for vertical alignment in the populated state.
- **Search input focus on dropdown open** — `setTimeout(focus, 0)` should land focus AFTER Bootstrap makes the menu visible, but on slow devices or under heavy GC pressure the timing is racy. Worth verifying on realistic intranet hardware.

These are NOT contract violations — they are visual-polish backlog items that surface only on a real browser pass. None block Plan 04-04's TestClient suite.

## User Setup Required

None — no new dependencies, no new external services, no new env vars. The page renders fully from server-side state (BrowseViewModel from Plan 04-02) with no client-side fetches beyond the HTMX-driven Apply/Swap/Clear-all swaps.

## Next Phase Readiness

- **Plan 04-04** can begin immediately. The full template tree is wired and the FastAPI app starts cleanly with both `/browse` and `/browse/grid` routes registered. Plan 04-04 will:
  - Add `tests/v2/test_browse_routes.py` — TestClient end-to-end tests (full URL round-trip, Apply behavior, swap-axes, Clear-all, cap warnings, empty-state copy, count-caption OOB swap)
  - Add `tests/v2/test_phase04_invariants.py` — codebase invariant guards (no `| safe`, no `<script>` inline, no `import plotly`, no `import openpyxl`, no `import csv`, no `from app.components.export_dialog`, no `async def` on browse routes)
  - Verify Issue 5 fix end-to-end with a TestClient request that posts a hostile DataFrame layout
- **Phase 5 (Ask)** can adopt the picker_popover macro pattern for any future parameter-confirmation UI.

## Threat Flags

None — no new attack surface beyond what the plan's threat register (`<threat_model>`) already enumerates. All HIGH-severity threats (T-04-03-01..T-04-03-03, T-04-03-06) are mitigated by the explicit `| e` filter on every dynamic Jinja2 output PLUS Jinja2's global autoescape. The MEDIUM threat (T-04-03-04) is defended by the in-options check `{% if opt in selected %}` — only well-known options from `vm.all_platforms`/`vm.all_param_labels` (i.e., DB-sourced, regex-validated upstream) can be pre-checked. The LOW threats (T-04-03-05, T-04-03-07, T-04-03-08) are accept dispositions per the plan's threat register.

popover-search.js does not introduce any new attack surface — it has zero network calls (no `htmx.ajax`, no `XMLHttpRequest`, no `window.fetch(`), and only DOM-manipulates descendants of `.popover-search-root` which is a server-rendered class never set client-side.

## Self-Check: PASSED

- `app_v2/templates/browse/_picker_popover.html` — FOUND
- `app_v2/templates/browse/_filter_bar.html` — FOUND
- `app_v2/templates/browse/index.html` — FOUND
- `app_v2/templates/browse/_grid.html` — FOUND
- `app_v2/templates/browse/_warnings.html` — FOUND
- `app_v2/templates/browse/_empty_state.html` — FOUND
- `app_v2/static/js/popover-search.js` — FOUND
- `.planning/phases/04-browse-tab-port/04-03-SUMMARY.md` — FOUND
- Commit `d1932eb` (Task 1 — picker_popover macro + filter bar) — FOUND in `git log --oneline`
- Commit `04e6179` (Task 2 — index page + grid/warnings/empty-state) — FOUND in `git log --oneline`
- Commit `f4207c0` (Task 3 — popover-search.js + Phase 04 CSS) — FOUND in `git log --oneline`
- Commit `2784ced` (Task 4 — wire popover-search.js into base.html) — FOUND in `git log --oneline`

---
*Phase: 04-browse-tab-port*
*Completed: 2026-04-26*
