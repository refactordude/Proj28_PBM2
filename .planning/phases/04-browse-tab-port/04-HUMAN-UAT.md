---
status: partial
phase: 04-browse-tab-port
source: [04-VERIFICATION.md]
started: 2026-04-26T23:45:00Z
updated: 2026-04-27T00:15:00Z
---

## Current Test

[awaiting human re-test after dropdown-clipping fix]

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
result: [pending — blocked by gap-1 until 2026-04-27; gap-1 fixed, ready to retest]

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
result: [pending — fixed in commit, awaiting retest]

## Summary

total: 2
passed: 0
issues: 1
pending: 2
skipped: 0
blocked: 0

## Gaps

### gap-1 — Parameters/Platforms popover clipped by .panel { overflow: hidden }
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
