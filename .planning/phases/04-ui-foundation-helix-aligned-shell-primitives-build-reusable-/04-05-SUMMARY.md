---
phase: 04-ui-foundation-helix-aligned-shell-primitives-build-reusable
plan: 05
subsystem: ui
tags: [css, jinja2, atomic-migration, helix-design-language, panel-header-rename]

# Dependency graph
requires:
  - phase: 04-ui-foundation-helix-aligned-shell-primitives-build-reusable
    provides: .ph CSS primitive shipped additively (Wave 1); chip-toggle.js + macros (Wave 2); Helix topbar swap (Wave 3); /_components showcase + UIF invariants (Wave 4)
  - phase: 02-ui-shell-rewrite-browse-footer-joint-validation-layout-parit
    provides: D-UI2-12 (.panel-title 18px/700 styling rule), Phase 02 invariants pinning the legacy class literals (test_panel_title_rule, test_overview_index_count_in_panel_header, test_overview_index_filter_bar_inside_panel)
provides:
  - D-UIF-01 LOCKED rename path completed end-to-end — every existing surface (Browse / JV listing / Ask / JV detail) now carries `class="ph"` instead of the legacy class
  - app.css free of every legacy shell-header selector — only `.ph` family rules remain
  - Phase 02 invariants atomically rewritten to track the new class name; the contract each test protected (D-UI2-12 declarations exist; receiver placement; filter-bar placement) is preserved verbatim
  - Wave 1's speculative `.ph { padding: 16px 24px }` block consolidated away — the surviving `.ph { padding: 18px 26px }` rule preserves the legacy padding so shipped surfaces render byte-stable visually
  - Phase 04 UI Foundation phase complete: primitives + showcase + topbar + atomic shell-naming migration all delivered
affects:
  - All future phases that ship new "shell-header" sections — they bind to `.ph` directly with no historical alias to honor
  - Phase 02 invariant docstrings now narrate the post-D-UIF-01 contract
  - Future waves cannot accidentally re-introduce the legacy literal — the belt-and-suspenders negative assertions (`not in src`) in the rewritten tests force loud failure on regression

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Atomic migration commit: markup + CSS + tests in a single commit so the working tree never enters a half-broken state (same atomicity pattern as Wave 3)"
    - "Belt-and-suspenders negative assertions in rewritten tests (`assert legacy not in src`) — partial rollbacks fail loudly rather than silently regressing"
    - "ID rename done as auto-fix Rule 3: id='browse-panel-header' to id='browse-ph' so the migration completeness `grep -c 'panel-header' = 0` criterion can actually be met (the plan instructions preserved the id literally; without renaming the id the grep would find a substring inside the id attribute)"
    - "Comment hygiene: every reference to the literal class name removed from templates AND CSS comments — the migration completeness criterion forces narrative comments to track the rename rather than crystallizing the legacy name in repo-grep"
    - "Wave 1 speculative block deletion: the duplicate `.ph` rule with normalized 16px 24px padding was consolidated into the migrated `.ph { padding: 18px 26px }` block to preserve byte-stable visual layout on shipped surfaces"

# Key files
key-files:
  created: []
  modified:
    - app_v2/templates/browse/index.html
    - app_v2/templates/overview/index.html
    - app_v2/templates/ask/index.html
    - app_v2/templates/joint_validation/detail.html
    - app_v2/static/css/app.css
    - tests/v2/test_phase02_invariants.py

# Decisions
key-decisions:
  - "Atomic commit pattern — markup, CSS, and tests landed in a single commit (e7e4455) so no intermediate red-tree state exists. Splitting into separate commits would have broken bisectability (markup-only commit fails old tests; CSS-only commit fails byte-equivalence)."
  - "Padding preservation over 4px-grid normalization — the surviving `.ph { padding: 18px 26px }` rule keeps the legacy padding rather than adopting Wave 1's speculative 16px 24px. Shipping the normalized values would have produced 2px-per-axis visual drift on every shipped surface; UI-SPEC §Spacing rationale applies to NEW shell adoption, not migration of shipped surfaces."
  - "ID rename as Rule 3 auto-fix — the plan's migration completeness criterion `grep -c 'panel-header' = 0` was contradicted by the plan's verbatim instruction to preserve `id='browse-panel-header'` and `id='overview-panel-header'`. Renamed both ids to `id='browse-ph'` and `id='overview-ph'` since neither id had any test pin, JS handler, or template reference. Comment text rephrased to avoid the literal class name."
  - "Comment-text rephrasing — the plan instructed comment edits like `.ph (was .panel-header per D-UIF-01)` which still contains the literal `panel-header`. Rephrased to `.ph (post-D-UIF-01 shell-header class; legacy name retired)` so the migration completeness criterion is satisfied without crystallizing the legacy name in repo-grep."
  - "ASCII-art comment alignment preserved — the box-drawing `│` right edge alignment in ask/index.html was re-padded after replacing `panel-header` (12 chars) with `ph` (2 chars); 10 spaces added inside the box to maintain visual alignment of the closing `│`."

# Metrics
metrics:
  duration: ~9min
  tasks_completed: 2
  files_modified: 6
  tests_pass: "541 passed, 5 skipped"
  start: "2026-05-03T10:45:33Z"
  end: "2026-05-03T10:54:29Z"
---

# Phase 04 Plan 05: Atomic .panel-header to .ph Migration Summary

Atomically renamed the legacy `.panel-header` shell-header class to `.ph` across the four target surfaces (Browse / JV listing / Ask / JV detail), rewrote the four legacy CSS rules to the new selector with byte-equivalent declarations, and updated three Phase 02 invariant tests to track the new class name — all in a single commit (e7e4455) so the working tree never entered a half-broken state.

## Why This Plan

**Wave 5 of Phase 04 — D-UIF-01 LOCKED rename path completion.** The earlier waves shipped the `.ph` selector additively and migrated `base.html` to the Helix topbar; this wave performs the final atomic shell-naming migration so the codebase has exactly one shell-header class name (the new one). Splitting the markup migration from the CSS rule rewrite or from the Phase 02 invariant test updates would have left the working tree in a half-broken state — same atomicity pattern as Wave 3's topbar swap + test_main.py rewrite.

## What Changed

### Templates (4 files)

**1. `app_v2/templates/browse/index.html`** — line 29:
```diff
- <div class="panel-header" id="browse-panel-header">
+ <div class="ph" id="browse-ph">
```
Plus narrative comments at lines 12 and 80 rephrased to remove the legacy literal.

**2. `app_v2/templates/overview/index.html`** — line 11:
```diff
- <div class="panel-header" id="overview-panel-header">
+ <div class="ph" id="overview-ph">
```
Plus narrative comments at lines 5, 8, and the `count_oob` comment block rephrased.

**3. `app_v2/templates/ask/index.html`** — line 74:
```diff
- <div class="panel-header">
+ <div class="ph">
```
Plus the ASCII-art comment block at line 9 updated, with the box's right-edge `│` re-aligned (10 spaces added inside the box to compensate for `panel-header` (12 chars) being replaced by `ph` (2 chars)).

**4. `app_v2/templates/joint_validation/detail.html`** — line 13:
```diff
- <div class="panel-header">
+ <div class="ph">
```
Plus narrative comments at lines 6-8 rephrased.

### CSS (`app_v2/static/css/app.css`)

Four legacy `.panel-header` family rules (lines 58, 68-69, 74) rewritten to `.ph` family rules with byte-equivalent declarations:

```diff
- .panel-header { padding: 18px 26px; ... }
- .panel-header b { ... }
- .panel-header .tag { ... }
- .panel-header .panel-title { font-size: 18px; font-weight: 700; ... margin: 0; ... }
+ .ph { padding: 18px 26px; ... }
+ .ph b { ... }
+ .ph .tag { ... }
+ .ph .panel-title { font-size: 18px; font-weight: 700; ... margin: 0; ... }
+ .ph .spacer { flex: 1; }
```

Plus consolidated the duplicate `.ph` rules: deleted Wave 1's speculative `.ph { padding: 16px 24px }` block at the end of the file along with its descendant rules. The surviving `.ph { padding: 18px 26px }` rule preserves the legacy padding verbatim — UI-SPEC §Spacing's 4px-grid normalization applies to NEW shell adoption, not the migration of shipped surfaces (which would have produced 2-px-per-axis visual drift).

The Phase 04 banner comment on the second-half block was updated to reflect the migration is now complete.

### Tests (`tests/v2/test_phase02_invariants.py`)

Three tests rewritten to track the new class name while preserving each test's semantic contract:

**`test_panel_title_rule`** — was asserting `.panel-header .panel-title` carried D-UI2-12 declarations; now asserts the same declarations under `.ph .panel-title` and adds a belt-and-suspenders negative assertion that the legacy selector is gone.

**`test_overview_index_count_in_panel_header`** — was asserting `<span id="overview-count">` appeared after `<div class="panel-header"` with `ms-auto`; now asserts the same after `<div class="ph"` with `ms-auto` and a belt-and-suspenders negative assertion that `class="panel-header"` is absent.

**`test_overview_index_filter_bar_inside_panel`** — was asserting the filter-bar include appeared after `<div class="panel-header"` and before `<div id="overview-grid"`; now asserts the same after `<div class="ph"`.

All other Phase 02 invariants stay green unchanged (footer block, OOB blocks, count receivers, pagination, h1 panel-title literal, count receiver/emitter tag alignment, etc.).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] ID rename to satisfy migration completeness criterion**
- **Found during:** Task 1 Step 1a / 2a
- **Issue:** Plan's migration completeness criterion required `grep -c 'panel-header' = 0` across all four templates, but the plan's verbatim edit instructions preserved `id="browse-panel-header"` and `id="overview-panel-header"`. The id substring `panel-header` would have caused the grep count to never reach zero.
- **Fix:** Renamed `id="browse-panel-header"` to `id="browse-ph"` and `id="overview-panel-header"` to `id="overview-ph"`. Verified zero callers (no test pins, no JS handlers, no template references).
- **Files modified:** `app_v2/templates/browse/index.html`, `app_v2/templates/overview/index.html`
- **Commit:** e7e4455

**2. [Rule 3 - Blocking issue] Comment-text rephrasing to satisfy migration completeness criterion**
- **Found during:** Task 1 Steps 1b / 2b / 3b / 4b
- **Issue:** The plan's instructions for narrative-comment edits used phrasings like `.ph (was .panel-header per D-UIF-01)` which still contain the literal `panel-header`. The migration completeness criterion `grep -c 'panel-header' = 0` would fail.
- **Fix:** Rephrased every comment to use phrasings like `.ph (post-D-UIF-01 shell-header class; legacy name retired)` or `.ph (the shell-header class)` — eliminating the literal while preserving the narrative intent.
- **Files modified:** All four templates plus `app_v2/static/css/app.css`
- **Commit:** e7e4455

**3. [Rule 3 - Blocking issue] CSS comment hygiene**
- **Found during:** Task 1 Edit 5
- **Issue:** Verification block #3 in the plan requires `grep -c '\.panel-header' app_v2/static/css/app.css = 0`. The plan's narrative comments around the rewritten rules and the Phase 04 banner block contained literal `.panel-header` references.
- **Fix:** Rephrased every CSS comment to use phrasings like "legacy shell-header family rules" instead of the literal `.panel-header`. The deleted Wave 1 block's replacement comment also avoids the literal.
- **Files modified:** `app_v2/static/css/app.css`
- **Commit:** e7e4455

## Verification Results

```
$ pytest tests/v2/ -x -q
541 passed, 5 skipped, 2 warnings in 30.38s
```

```
$ grep -r 'class="panel-header"' app_v2/templates/{browse,overview,ask,joint_validation}/
(empty — zero matches)
```

```
$ grep -c '\.panel-header' app_v2/static/css/app.css
0

$ grep -c '\.ph \.panel-title' app_v2/static/css/app.css
1

$ grep -c '\.ph {' app_v2/static/css/app.css
1
```

```
$ python -c "from fastapi.testclient import TestClient; from app_v2.main import app
c = TestClient(app)
for path in ['/', '/browse', '/ask']:
    r = c.get(path)
    assert r.status_code == 200, path
    assert 'class=\"ph\"' in r.text, path
    assert 'class=\"panel-header\"' not in r.text, path
print('OK all routes')"
OK all routes return 200 with class=ph and no class=panel-header
```

Out-of-scope files verified byte-stable:
- `app_v2/templates/browse/_picker_popover.html` (D-UIF-05 / D-UI2-09)
- `app_v2/templates/browse/_filter_bar.html` (only `panel-header` reference is in a Jinja comment, not markup; out of D-UIF-01 scope)
- `app_v2/templates/platforms/_edit_panel.html` (D-UIF-01 explicitly scopes Browse / JV / Ask only)
- `app_v2/static/js/popover-search.js` (D-UI2-09)
- `app_v2/static/css/tokens.css` (D-UI2-04)

## Phase 04 Status

**Phase 04 UI Foundation is now fully delivered:**

- **Wave 1** (Plan 04-01): CSS primitives shipped — .ph, .topbar, .brand, .av, .tabs, .hero, .kpis, .pop, .chip, .tiny-chip, .table-sticky-corner, .btn-helix; Google Fonts loaded
- **Wave 2** (Plan 04-02): Jinja macros + Pydantic view-models shipped — topbar, page_head, hero, kpi_card, sparkline, date_range_popover, filters_popover; HeroSpec, FilterGroup; chip-toggle.js as sibling of popover-search.js
- **Wave 3** (Plan 04-03): Atomic Helix topbar swap in base.html — replaced legacy Bootstrap navbar with the new topbar macro; tests rewritten atomically
- **Wave 4** (Plan 04-04): /_components showcase route mounted; UIF invariant tests authored
- **Wave 5** (this plan): Atomic shell-naming migration on every existing surface

D-UIF-01 LOCKED rename path: complete. Every existing surface (Browse / JV / Ask) now uses the new `.ph` shell-header class with no legacy alias remaining.

## Self-Check: PASSED

Verified:
- `app_v2/templates/browse/index.html` — exists, modified, contains `class="ph"`, no `panel-header` literal
- `app_v2/templates/overview/index.html` — exists, modified, contains `class="ph"`, no `panel-header` literal
- `app_v2/templates/ask/index.html` — exists, modified, contains `class="ph"`, no `panel-header` literal
- `app_v2/templates/joint_validation/detail.html` — exists, modified, contains `class="ph"`, no `panel-header` literal
- `app_v2/static/css/app.css` — exists, modified, contains `.ph .panel-title` rule with D-UI2-12 declarations, zero `.panel-header` references
- `tests/v2/test_phase02_invariants.py` — exists, modified, three target tests rewritten with new literals + belt-and-suspenders negative assertions
- Commit `e7e4455` — exists in `git log`
- All 541 v2 tests pass (5 expected skips)
