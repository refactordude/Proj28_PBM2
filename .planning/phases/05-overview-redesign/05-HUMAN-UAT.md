---
status: partial
phase: 05-overview-redesign
source: [05-VERIFICATION.md]
started: 2026-04-28T08:10:00Z
updated: 2026-04-28T08:10:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Sort UX cycle in live browser
expected: Clicking column headers cycles asc → desc → asc; URL updates with `?sort=<col>&order=<asc|desc>`; copy-paste between tabs round-trips sort state.
result: [pending]

### 2. Popover-checklist filter D-15b auto-commit + 250ms debounce
expected: Toggling a checkbox in any of the 6 multi-filter popovers (Status / Customer / AP Company / Device / Controller / Application) auto-commits after 250ms; trigger badge updates via OOB swap; table body swaps server-side without full reload.
result: [pending]

### 3. Visual parity with Phase 4 Browse pivot grid
expected: Side-by-side compare — striping, hover, sticky-top header, density, font sizing all match Browse `.pivot-table` styling.
result: [pending]

### 4. AI Summary cell end-to-end
expected: AI Summary button triggers LLM round-trip (Ollama default), spinner shows during request, summary text renders in-place after response; disabled state correct when no content page exists.
result: [pending]

### 5. Add platform input row + HX-Redirect full reload
expected: Datalist typeahead works for platform_id input; submit triggers full page reload to /overview (HX-Redirect).
result: [pending]

### 6. Korean unicode rendering
expected: `담당자` header renders correctly; `홍길동` (or other Korean) cell values render correctly in browser.
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps
