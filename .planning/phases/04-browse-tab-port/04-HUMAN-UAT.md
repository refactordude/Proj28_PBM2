---
status: partial
phase: 04-browse-tab-port
source: [04-VERIFICATION.md]
started: 2026-04-26T23:45:00Z
updated: 2026-04-26T23:45:00Z
---

## Current Test

[awaiting human testing]

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
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
