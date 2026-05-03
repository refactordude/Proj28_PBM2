---
status: partial
phase: 04-ui-foundation-helix-aligned-shell-primitives-build-reusable
source: [04-VERIFICATION.md]
started: 2026-05-03
updated: 2026-05-03
---

## Current Test

[awaiting human testing]

## Tests

### 1. Visual /_components smoke
expected: Visit `GET /_components` in a browser. All 10 primitive sections render correctly: topbar (brand "P PBM2" + JV/Browse/Ask tabs + PM avatar), page-head, hero (full + minimal), KPI 4-up + 5-up grids with visible sparklines, every chip / pill / tiny-chip variant, date-range popover, filters popover (chip groups including UFS-eMMC), sticky-corner table. Inter Tight weight 800 visibly heavier than 700 on `.page-title` and `.brand-mark` (Pitfall 1 fix).
result: [pending]

### 2. WR-03 quick-day chip removal — ROADMAP goal deviation
expected: ROADMAP phase goal mentions "date-range popover (7/14/30/60d quick chips + start/end inputs + reset/apply)". Implementation deliberately REMOVED the quick-day chips (commit `112f2d8`) because no JS handler reads `data-quick-days`. Decide: (a) accept deviation — quick chips deferred to follow-up phase, OR (b) re-add chips with a working handler in this phase.
result: [pending]

### 3. WR-04 disabled-input-on-OFF chip integrity
expected: Open `/_components` filters popover, toggle a chip OFF, submit form (e.g., via showcase test harness or browser dev tools). Confirm the OFF chip's hidden input is NOT included in form submission (because `disabled` attribute is set). When ON, the input value is the chip's value.
result: [pending]

### 4. Live route visual byte-stability
expected: Visit `/` (overview), `/browse`, `/ask` and any JV detail page. Confirm the `.ph` (formerly `.panel-header`) sections look visually identical to pre-Phase-04 baseline — Wave 5 consolidation preserved 18px 26px padding verbatim (rejecting the speculative 16px 24px) so no 2px-per-axis drift should be visible.
result: [pending]

### 5. Pitfall 1 / Google Fonts CDN reachability
expected: On the intranet deployment target, confirm `fonts.googleapis.com` is reachable. If blocked, follow-up phase needs to vendor woff2 files and switch to local @font-face rules. Currently the page degrades gracefully to system fallback (which previously masked the weight 800 problem).
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
