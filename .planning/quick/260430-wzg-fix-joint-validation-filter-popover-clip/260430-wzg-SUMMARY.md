---
quick_task: 260430-wzg
title: Fix Joint Validation filter popover clipping (self-match overflow-visible)
type: quick
wave: 1
depends_on: []
requirements:
  - QUICK-260430-wzg
files_created:
  - tests/v2/test_joint_validation_invariants.py  # +1 new test function appended
files_modified:
  - app_v2/static/css/app.css                     # 5-selector overflow-visible rule (was 3)
key-decisions:
  - "Self-match selectors appended (not prepended) — preserves existing :has() order so reviewers can see the original Phase 5 fix unchanged at the top of the rule list"
  - "CSS-only fix — no template changes; same element keeps `class=\"overview-filter-bar panel\"` as designed by Phase 5"
  - "Comment block extended (not replaced) — original WHY preserved; new paragraph appended explaining the SELF-MATCH case"
  - "Pinned with one grep-based invariant test asserting BOTH descendant-match AND self-match selectors must coexist (catches future regression where someone removes either form)"
metrics:
  duration: ~3min
  tasks_completed: 2
  files_touched: 2
  test_count_baseline: 360
  test_count_after: 361
  net_test_delta: +1
  completed: 2026-04-30
---

# Quick Task 260430-wzg: Fix Joint Validation filter popover clipping

**One-liner:** Extend `.panel { overflow: visible }` rule to cover the self-match case (`.panel.overview-filter-bar`) so Joint Validation's 6 filter popovers (Status / Customer / AP Company / Device / Controller / Application) escape `.panel { overflow: hidden }` clipping when the filter bar element carries both classes on a single `<div>`.

## Root Cause

The Joint Validation filter bar root element carries BOTH classes on the SAME element:

```html
<!-- app_v2/templates/overview/_filter_bar.html:7 -->
<div class="overview-filter-bar panel" id="overview-filter-bar">
```

The Phase 5 popover-clipping fix used the descendant `:has()` selector:

```css
.panel:has(.overview-filter-bar) { overflow: visible; }
```

`:has()` only matches DESCENDANTS of `.panel`. When `.panel` and `.overview-filter-bar` are co-classes on the same element, the descendant selector never fires — so `.panel { overflow: hidden }` (line 20) wins and clips Bootstrap dropdown popovers.

Browse, by contrast, wraps `.browse-filter-bar` INSIDE a separate `.panel` element (`app_v2/templates/browse/index.html:27`), so the descendant `:has()` matches there and Browse popovers escape clipping correctly.

## Fix Shape

Smallest correct fix is two additional self-match selectors appended to the existing rule (CSS-only, no template changes):

```css
/* app_v2/static/css/app.css:121-125 */
.panel:has(.browse-filter-bar),
.panel:has(.overview-filter-bar),
.panel:has(#ask-confirm-form),
.panel.browse-filter-bar,
.panel.overview-filter-bar { overflow: visible; }
```

The trailing two selectors handle the SELF-MATCH case. Both forms coexist because Browse keeps the descendant-match path; only Joint Validation needs the self-match path.

The comment block above the rule was also extended with one paragraph explaining the self-match rationale, so future readers understand why both forms must remain present.

## Files Touched

Exactly 2 files, matching `<constraints>`:

| File | Change |
|------|--------|
| `app_v2/static/css/app.css` | Rule list extended from 3 selectors → 5 selectors; comment block extended with self-match paragraph |
| `tests/v2/test_joint_validation_invariants.py` | New test `test_jv_filter_popover_overflow_visible_self_match` appended at end of file |

No HTML templates modified. No Python source modules modified.

## Test Count Delta

| State | Count |
|-------|-------|
| Baseline (before this task) | 360 passed, 5 skipped |
| After this task | 361 passed, 5 skipped |
| Net delta | **+1** new passing test |

Final suite output:

```
361 passed, 5 skipped, 4 warnings in 24.42s
```

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | `13ee5b1` | `fix(css): extend overflow-visible to .panel.overview-filter-bar self-match` |
| 2 | `067fd37` | `test(jv): pin overflow-visible self-match selector for JV popovers` |

Both atomic — Task 1 ships the production fix; Task 2 pins it with the regression invariant.

## Deviations from Plan

None — plan executed exactly as written. CSS edit byte-equal to plan spec; test function byte-equal to plan spec. No auto-fixes triggered (Rules 1-3 not invoked).

## Verification

1. **Selector presence (grep):**
   - `.panel:has(.browse-filter-bar)` → present (line 121)
   - `.panel:has(.overview-filter-bar)` → present (line 122)
   - `.panel:has(#ask-confirm-form)` → present (line 123)
   - `.panel.browse-filter-bar` → present (line 124)
   - `.panel.overview-filter-bar` → present (line 125)
2. **`.panel { overflow: hidden }` rule on line 20** — unchanged.
3. **Files changed in last 2 commits** — exactly `app_v2/static/css/app.css` + `tests/v2/test_joint_validation_invariants.py` (no template files).
4. **Atomic commits in order** — Task 1 (`13ee5b1`) before Task 2 (`067fd37`).
5. **Full v2 suite** — 361 passed, 5 skipped.

## Open Follow-up — HUMAN-UAT

Before closing this quick task as fully resolved, a Joint Validation reviewer should click each of the 6 filter popovers (Status / Customer / AP Company / Device / Controller / Application) on a live `app_v2` server and visually confirm:

- Each popover renders fully visible — no top, bottom, or side clipping.
- The fix holds for the worst case (filter bar tall enough that the popover would otherwise overflow `.panel { overflow: hidden }`).
- Browse filter popovers (Platforms / Parameters) remain unclipped (no regression on the existing `:has()` path).

This is consistent with the project's UAT-deferred pattern (5 open Phase 1–6 UAT items still pending). Recommend folding this UAT click-through into the next Phase 1 UAT pass rather than running it standalone.

## Self-Check: PASSED

**Created files exist:**
- FOUND: `app_v2/static/css/app.css` (modified)
- FOUND: `tests/v2/test_joint_validation_invariants.py` (modified — new test appended)

**Commits exist:**
- FOUND: `13ee5b1` — `fix(css): extend overflow-visible to .panel.overview-filter-bar self-match`
- FOUND: `067fd37` — `test(jv): pin overflow-visible self-match selector for JV popovers`

**Test suite green:** 361 passed, 5 skipped (baseline 360 + 1).
