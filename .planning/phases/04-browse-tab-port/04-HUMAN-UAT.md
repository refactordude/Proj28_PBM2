---
status: diagnosed
phase: 04-browse-tab-port
source: [04-VERIFICATION.md]
started: 2026-04-26T23:45:00Z
updated: 2026-04-28T12:30:00Z
---

## Current Test

[testing complete — gap-4 surfaced: outside-click on popover currently cancels per D-15; user reports this should auto-Apply]
[gap-4 closed by Plan 04-07 (2026-04-28); ready for UAT replay]
[2026-04-28 UAT replay surfaced gap-5: implicit-Apply path not landing the grid swap (only the in-popover Apply count badge updates) AND user requested removal of the Apply button entirely — design pivot to auto-commit on each checkbox change with client-side debounce. gap-4 marked superseded; gap-5 supersedes it.]

## Tests

### 1. Apply / Swap-axes / Clear-all in a real browser (WR-01)
expected: |
  Selecting platforms+parameters in the popover and clicking Apply triggers a
  POST /browse/grid carrying the checked items; the grid swaps in-place;
  HX-Push-Url updates the URL bar to /browse?platforms=...&params=...; the
  Swap-axes toggle re-renders the grid with axes flipped; Clear-all empties
  both pickers and shows the empty-state alert.

  Steps:
  1. Start FastAPI: `.venv/bin/uvicorn app_v2.main:app --port 8000`
  2. Open DevTools → Network panel
  3. Visit http://localhost:8000/browse
  4. Tick 2-3 platforms in Platforms picker, tick 2-3 params in Parameters picker
  5. Click Apply — confirm POST /browse/grid body contains the checked items
  6. Confirm grid renders with pivot data and URL bar updates
  7. Toggle Swap-axes — grid re-renders with axes flipped (index column changes)
  8. Click Clear-all — grid swaps to empty-state alert
result: pass
prior_result: issue
prior_reported: "when I first select a few Platforms/Parameters and push Apply, 'Select platforms and parameters above to build the pivot grid.' is shown until I click Swap axes button, which works like a refresh."
prior_severity: major
prior_verified: 2026-04-27T13:25:00Z
retested: 2026-04-28T00:10:00Z
retest_note: "gap-2 closure (Plan 04-05) confirmed in browser — Apply now produces populated grid on first click. Swap-axes and Clear-all also work. Separately surfaced gap-3 (badge counter staleness) during retest."

### 2. Parameters/Platforms dropdown popover renders fully (gap-1)
expected: |
  Clicking the Platforms or Parameters trigger opens the dropdown popover
  showing the search input on top, the full scrollable checklist (max-height
  320px) in the middle, and the sticky Clear / Apply footer on the bottom.
  At least 8-10 items should be visible without the popover being clipped
  by the parent panel.

  Steps:
  1. Visit http://localhost:8000/browse
  2. Click "Parameters" trigger
  3. Confirm at least ~8 items visible (or whole list if shorter than the
     320px max-height); search box + Apply/Clear footer visible
  4. Repeat for "Platforms" trigger
result: pass
verified: 2026-04-27T12:30:00Z

## Summary

total: 2
passed: 2
issues: 3
pending: 0
skipped: 0
blocked: 0
gaps_open: 1
gaps_resolved: 4
gaps_superseded: 1

## Gaps

### gap-2 — Apply button does not swap pivot grid; only Swap-axes triggers render
status: resolved
reported: 2026-04-27T13:25:00Z
diagnosed: 2026-04-27T14:30:00Z
resolved: 2026-04-27T23:50:00Z
test_ref: 1
severity: major
debug_session: .planning/debug/gap-2-apply-no-swap.md
symptom: |
  After ticking platforms+parameters in the pickers and clicking Apply, the
  grid region keeps showing the empty-state alert ("Select platforms and
  parameters above to build the pivot grid."). The grid only renders after
  clicking Swap-axes, which appears to act as a refresh. Suggests the
  POST /browse/grid HTMX swap is not landing in the grid container on the
  first Apply click — but the swap-axes interaction (which hits the same
  view-model path) does land correctly.
root_cause: |
  The Apply button in _picker_popover.html is a <button type="button"> with
  no form= attribute and no <form> ancestor in its DOM tree. Its hx-include
  uses the CSS selector "#browse-filter-form input:checked", which is a
  descendant combinator resolved via document.querySelectorAll(). Because the
  picker checkboxes live inside .dropdown-menu elements (not as DOM descendants
  of #browse-filter-form), this selector returns zero elements — the POST body
  arrives at /browse/grid with empty platforms/params, triggering is_empty_selection=True
  and the empty-state alert.

  The Swap-axes checkbox works because it carries form="browse-filter-form".
  HTMX's getInputValues (dn() in htmx.min.js) auto-includes the triggering
  element's associated form (via element.form DOM property) for all non-GET
  requests. form.elements (the browser DOM API) populates with ALL
  form-associated controls — including those linked via the form= attribute
  even when not DOM descendants. This gives Swap-axes access to all checked
  platform/param checkboxes automatically, without any explicit hx-include
  for them.

  Fix direction: add form="browse-filter-form" to the Apply button element, OR
  change hx-include to "#browse-filter-form" (the form element itself) so HTMX
  processes it as HTMLFormElement and iterates form.elements rather than the
  CSS descendant path.
fix: |
  Added form="browse-filter-form" to the popover-apply-btn <button> in
  app_v2/templates/browse/_picker_popover.html and removed the broken
  hx-include="#browse-filter-form input:checked" CSS-descendant selector.
  This puts Apply on the same form-association path that the Swap-axes
  checkbox in _filter_bar.html already uses successfully — HTMX's dn()
  resolves element.form for non-GET requests and iterates form.elements,
  which the browser populates with all controls linked by the form=
  attribute regardless of DOM tree position. Verified by two regression
  tests in tests/v2/test_browse_routes.py
  (test_apply_button_carries_form_attribute,
  test_post_browse_grid_apply_button_payload_renders_populated_grid).
  Closed by Plan 04-05; zero Python production-code changes. See
  .planning/debug/gap-2-apply-no-swap.md for full root-cause evidence.

### gap-3 — Trigger button count badge does not update after Apply (only after full page refresh)
status: resolved
reported: 2026-04-28T00:10:00Z
resolved: 2026-04-28T01:30:00Z
test_ref: 1
severity: minor
contract_ref: D-14(b)
symptom: |
  After clicking Apply (which now correctly produces the populated grid per the
  gap-2 fix), the count badge displayed next to the "Platforms" / "Parameters"
  trigger buttons does NOT update to reflect the new selection count. The
  badges only update on a full page refresh (F5 / hard navigation).
  
  Per CONTEXT.md D-14(b), Apply is contractually required to:
    (a) close the popover
    (b) update the trigger button's count badge
    (c) fire a single hx-post=/browse/grid swap with the new selection
  
  Steps (a) and (c) are working. Step (b) is broken.
  
  Reproduction:
  1. Visit http://localhost:8000/browse (badges show "(0)" or are hidden)
  2. Open Platforms picker, tick 3 platforms, click Apply
  3. Grid renders correctly (gap-2 fix confirmed) BUT trigger reads "Platforms" with
     no badge — should read "Platforms (3)" per D-14(b)
  4. Open Parameters picker, tick 5 params, click Apply
  5. Grid re-renders BUT Parameters trigger badge stays at original value — should
     read "Parameters (5)"
  6. Hard-refresh the page (F5) → badges finally show correct counts ((3) and (5))
fix_direction: |
  Likely: the `_filter_bar.html` trigger buttons aren't part of the
  hx-target=#browse-grid swap, so the server-rendered badge count never
  reaches them on Apply. Fix candidates (pick one in plan):
    - Add an OOB swap fragment for each trigger badge (server emits
      `<span id="platforms-badge" hx-swap-oob="true">(N)</span>` alongside
      grid swap response, lands in the persistent shell)
    - Add client-side badge sync in popover-search.js: after Apply click,
      count checked items in popover and update the trigger badge text
      directly (zero server round-trip beyond the existing grid swap)
  
  CONTEXT.md D-14(b) is the source of truth — the badge MUST update on Apply.
  This is a regression from the locked design, not a new behavior request.
fix: |
  Adopted Candidate A (server-side OOB) — extended the existing
  count_oob / warnings_oob OOB pattern with a new picker_badges_oob
  block in app_v2/templates/browse/index.html that emits two
  hx-swap-oob spans (id="picker-platforms-badge", id="picker-params-badge")
  on every POST /browse/grid response. The trigger button badge in
  _picker_popover.html is now ALWAYS rendered with a stable
  id="picker-{{ name }}-badge" and uses the d-none class when the
  selection is empty (instead of conditional <span> emission), so
  HTMX always has a stable swap target while D-08's "no badge when
  empty" visual contract is preserved. browse_grid's block_names
  list extended from 3 -> 4 elements with "picker_badges_oob"
  added; one-line router change. Verified by two regression tests
  in tests/v2/test_browse_routes.py
  (test_post_browse_grid_emits_picker_badge_oob_blocks,
  test_post_browse_grid_picker_badge_zero_count_renders_hidden).
  D-14(a) (popover close) and D-14(c) (single hx-post grid swap)
  continue to work; gap-2 form-association fix not regressed.
  Zero changes to services / adapters / popover-search.js / app.css;
  changes are confined to 2 templates + 1 router + 1 test file.
  Closed by Plan 04-06.

### gap-4 — Clicking outside the popover discards selection (should auto-Apply)
status: superseded
reported: 2026-04-28T11:00:00Z
resolved: 2026-04-28T01:55:00Z
superseded: 2026-04-28T12:30:00Z
superseded_by: gap-5
superseded_reason: |
  UAT replay confirmed the Plan 04-07 implicit-Apply implementation does not land the grid swap on outside-click — only the in-popover ".popover-apply-count" badge updates (via onCheckboxChange, not via implicit-Apply). Likely cause: by the time `hidden.bs.dropdown` fires, the Apply button's parent .dropdown-menu has been hidden by Bootstrap and the synthetic .click() on the button is rejected by HTMX or the form-association is lost. Independent of the bug, the user has decided to remove the Apply button entirely (design pivot — see gap-5), making D-15 amended + D-15a moot. gap-4 is therefore superseded rather than re-fixed.
test_ref: 1
severity: minor
contract_ref: D-15 (amended) + D-15a (locked) — both superseded by D-15b
symptom: |
  When the user opens the Platforms (or Parameters) picker, ticks one or more
  checkboxes, then clicks anywhere outside the popover (or presses Esc, or
  scrolls the page so Bootstrap auto-closes the dropdown), the selection is
  silently discarded — the popover restores the original checked-state and
  the grid does not swap. The user expected outside-click to commit the new
  selection (i.e. behave as Apply).

  Reproduction:
  1. Visit http://localhost:8000/browse
  2. Click "Platforms" trigger → popover opens
  3. Tick 3 platforms (do NOT click Apply)
  4. Click anywhere outside the popover (e.g. on the page background, on the
     Parameters trigger, or on the grid area)
  5. Popover closes; the trigger badge stays at the previous count; the grid
     does not swap

  This is the current intentional behavior per locked decision D-15
  ("Closing the popover without Apply restores original selection — restore-on-cancel
  via stashed state in `data-original-selection` on the popover root"). The
  popover-search.js `onDropdownHide` handler explicitly reads
  `dataset.originalSelection` and reverts checkbox state when
  `dataset.applied !== '1'`.

  User-reported expectation contradicts D-15 — they want outside-click to be
  treated as implicit Apply (commit), not Cancel (revert). This is a UX
  decision change, not a code regression.

fix_direction: |
  This is a CONTRACT change first, code change second. Two paths:

    Path 1 — Overturn D-15:
      Update CONTEXT.md D-15 (and any cross-references in D-09 / D-14) so
      that close-without-explicit-Cancel = implicit Apply. Modify
      popover-search.js so `onDropdownHide` fires the same path as
      `onApplyClick` (set dataset.applied=1 + trigger HTMX hx-post on the
      Apply button programmatically) UNLESS an explicit Cancel/Esc path
      was taken (Bootstrap fires `hide.bs.dropdown` with `e.clickEvent` —
      can distinguish outside-click from Esc / programmatic-close).
      Server-side picker_badges_oob block from gap-3 fix already gives a
      stable swap target — no new template work; the Apply button must
      still carry form="browse-filter-form" so the implicit-Apply request
      includes the popover's checked items.

    Path 2 — Keep D-15, add explicit visual cue:
      Tighten the popover footer copy or animation so the Apply button
      reads as the only commit affordance (e.g. pulse on close-without-
      Apply). Cheaper but doesn't satisfy the user's actual ask.

  Recommend Path 1. Risk: a misclick now permanently commits — but the
  Clear-all button is already a single-click revert, so the cost is low.
  Esc-as-cancel must still work to give users an opt-out.

  Plan should also extend tests in tests/v2/test_browse_routes.py to assert
  the implicit-Apply HTMX request contract on outside-click — and add a
  Phase 4 invariant in tests/v2/test_phase04_invariants.py that pins the
  new D-15 contract so it can't regress silently.

fix: |
  Implemented Path 1 (overturn original D-15) — CONTEXT.md amended
  2026-04-28 with D-15 (amended) + D-15a (close-event taxonomy);
  popover-search.js rewritten to implement the new contract.
  onDropdownHide now branches:
    (i)  dataset.applied=1 (explicit Apply already ran)         -> exit
    (ii) dataset.cancelling=1 (Esc was pressed)                  -> revert
    (iii) current sorted selection deep-equals originalSelection -> no-op
    (iv) otherwise                                               -> implicit Apply
                                                                     (programmatic
                                                                      popoverApplyBtn.click())
  A new document keydown listener (capture phase) sets
  dataset.cancelling=1 on Escape BEFORE Bootstrap fires
  hide.bs.dropdown — the canonical workaround for the fact that
  e.clickEvent on hide.bs.dropdown is null on BOTH Esc and
  programmatic close. The implicit-Apply path reuses the existing
  Apply button's HTMX wiring via programmatic click —
  gap-2 form-association (form="browse-filter-form") AND gap-3
  picker_badges_oob OOB swap both fire automatically with zero
  divergence from the explicit-Apply code path. A new
  _selectionsEqual helper drives the no-op short-circuit
  (sorted-array deep equality between current and stashed selection).
  Macro header comment in _picker_popover.html unchanged at the
  body — data-bs-auto-close="outside" on the trigger button (the
  precondition) preserved unchanged. Two server-side regression
  tests in tests/v2/test_browse_routes.py pin the implicit-Apply
  HTTP contract (test_post_browse_grid_implicit_apply_payload_shape,
  test_post_browse_grid_idempotent_unchanged_selection); one
  Phase 4 invariant in tests/v2/test_phase04_invariants.py
  grep-guards popover-search.js for the five D-15a contract
  markers (dataset.cancelling, capture-phase keydown listener,
  programmatic .popover-apply-btn click, _selectionsEqual helper,
  D-15a comment citation) AND pins data-bs-auto-close="outside"
  on the trigger button. TestClient cannot exercise the JS-side
  distinguisher directly — server-side tests + JS grep guards
  + manual UAT replay together pin the contract end-to-end. Suite:
  274 -> 277 passing. Closed by Plan 04-07; zero changes to
  routers / services / adapters / index.html / _filter_bar.html /
  app.css. See .planning/phases/04-browse-tab-port/04-CONTEXT.md
  D-15 (amended) and D-15a for the locked contract.


resolved: 2026-04-27T00:15:00Z
test_ref: 2
symptom: |
  When the dropdown popover opened, only the first ~1.5 items were visible
  before the popover was cut off by the panel's bottom edge. The search
  input and footer were also clipped depending on panel height.
root_cause: |
  app_v2/static/css/app.css:16-21 (Phase 03 .panel rule) sets
  `overflow: hidden` to clip rounded-corner children. Bootstrap dropdown
  popovers use position:absolute via Popper.js — they extend beyond the
  filter bar into the area below it. When the panel itself is short
  (empty-state, narrow viewport), the popover gets clipped at the panel
  boundary instead of rendering at full max-height: 320px.
fix: |
  Added `.panel:has(.browse-filter-bar) { overflow: visible }` to the
  Phase 04 CSS block in app_v2/static/css/app.css. The :has() selector
  scopes the override to the Browse panel only — Phase 03 panels (Overview,
  Content) keep their `overflow: hidden` rounded-corner clipping unchanged.
  Browser support: Chromium-based Edge / Chrome 105+, Safari 15.4+,
  Firefox 121+ (acceptable for the corporate-intranet target environment).

### gap-5 — Implicit-Apply does not land the grid swap; design pivot to remove Apply button entirely
status: open
reported: 2026-04-28T12:30:00Z
test_ref: 1
severity: major
contract_ref: D-14 (overturned), D-15 (superseded), D-15a (superseded), new D-15b
supersedes: gap-4
symptom: |
  UAT replay of the gap-4 closure (Plan 04-07): user opened the Platforms picker, ticked items, and clicked outside the popover. Observed:
  - In-popover "Apply (N)" count badge updated correctly (this is the onCheckboxChange handler, NOT implicit-Apply).
  - Trigger button badge did NOT update.
  - Pivot grid did NOT swap.
  - Only clicking the explicit Apply button OR the Swap-axes toggle commits.

  This means branch (iv) of `onDropdownHide` (`applyBtn.click()`) is failing to fire the HTMX request — likely because by the time `hidden.bs.dropdown` fires, the .dropdown-menu is already hidden by Bootstrap and the synthetic click on the now-hidden Apply button is rejected by HTMX or the form-association is lost.

  More importantly: the user has reported the entire 2-click Apply workflow as friction and explicitly requested removal of the Apply button. Design pivot: each checkbox toggle commits directly via debounced HTMX. The close-event taxonomy is moot — there is no commit gesture to taxonomize anymore.

fix_direction: |
  This is a CONTRACT change first, code change second.

  CONTRACT (new D-15b, supersedes D-14, D-15, D-15a):
    - Each checkbox change in either picker fires a single hx-post=/browse/grid request after a 250ms client-side debounce (collapses bursts so 5 quick toggles = 1 query, not 5).
    - The hx-* attributes are attached to the <ul class="popover-search-list"> checklist (not to individual checkboxes) so HTMX listens for bubbling change events and applies its built-in "delay:" trigger modifier as the debouncer.
    - Apply button is REMOVED from the popover footer.
    - Clear button stays — clicking it unchecks all in this picker, the change events bubble, and the debounce fires a single commit (showing the empty selection grid for this picker).
    - Top-level "Clear all" link (D-17) is unchanged.
    - Esc and outside-click and Tab-away all just close the popover. No commit/cancel distinction; the checkbox state at any moment IS the truth. (Once the user toggles a box, the commit is queued via debounce regardless of how the popover closes.)
    - Trigger button badge update path is unchanged — the picker_badges_oob OOB swap from gap-3 fires on every POST /browse/grid response; the badge updates server-side after the debounced request lands.
    - data-bs-auto-close stays "outside" so the popover stays open across multiple toggles (ergonomics — user picks N items in a row).

  CODE:
    1. _picker_popover.html: delete the popover footer's Apply button (keep the Clear button); add hx-post / hx-target / hx-swap / hx-trigger="change changed delay:250ms from:closest .popover-search-root" to the <ul class="popover-search-list"> element.
    2. popover-search.js: delete onDropdownHide, onApplyClick, onKeydown, _selectionsEqual, dataset.applied/cancelling/originalSelection logic. Keep onInput (search filter) and onClearClick (popover Clear button). Drop the onCheckboxChange in-popover badge update because the .popover-apply-count target is removed. Drop onDropdownShow's flag-clearing (no flags exist anymore).
    3. tests/v2/test_phase04_invariants.py: remove the D-15a invariant (test_popover_search_js_implements_d15a_close_event_taxonomy); add a new D-15b invariant pinning hx-post on the checklist <ul> + hx-trigger contains "delay:250ms" + no .popover-apply-btn in the template.
    4. tests/v2/test_browse_routes.py: remove the gap-4 implicit-Apply tests (they're moot); add a structural test confirming the Apply button is absent from GET /browse output and the checklist <ul> carries the expected hx-* attributes.

  This is a NET SIMPLIFICATION — popover-search.js shrinks by ~150 lines; the close-event taxonomy is replaced with HTMX's built-in `delay:` trigger; the contract is uniform across all close paths.


