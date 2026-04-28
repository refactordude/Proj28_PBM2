---
status: complete
phase: 04-browse-tab-port
source: [04-VERIFICATION.md]
started: 2026-04-26T23:45:00Z
updated: 2026-04-28T00:10:00Z
---

## Current Test

[testing complete — gap-3 surfaced for diagnosis]

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
issues: 1
pending: 0
skipped: 0
blocked: 0
gaps_open: 1
gaps_resolved: 2

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
status: open
reported: 2026-04-28T00:10:00Z
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
status: resolved
reported: 2026-04-27T00:05:00Z
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
