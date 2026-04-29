---
phase: 04-browse-tab-port
plan: 07
subsystem: ui
gap_closure: true
closes_gaps: [gap-4]
tags: [bugfix, browse, htmx, popover, contract-change, gap-closure, javascript]

# Dependency graph
requires:
  - phase: 04-browse-tab-port (plan 04-03)
    provides: "app_v2/templates/browse/_picker_popover.html — popover-search-root + popover-apply-btn DOM contract; data-bs-auto-close=\"outside\" on the trigger button (the JS precondition)"
  - phase: 04-browse-tab-port (plan 04-05)
    provides: "form=\"browse-filter-form\" attribute on popover-apply-btn (gap-2 fix) — implicit-Apply path inherits this; depends on NOT being regressed"
  - phase: 04-browse-tab-port (plan 04-06)
    provides: "picker_badges_oob OOB block in browse/index.html (gap-3 fix) — implicit-Apply path inherits this; trigger badges update on every Apply (explicit OR implicit)"
  - decisions: "D-09 (data-bs-auto-close='outside' precondition), D-14 (Apply contract), D-15 (amended 2026-04-28), D-15a (locked 2026-04-28 — close-event taxonomy)"
provides:
  - "app_v2/static/js/popover-search.js — D-15a close-event taxonomy implementation: capture-phase keydown listener (onKeydown) sets dataset.cancelling=1 on Esc; onDropdownHide branches across 4 paths (explicit Apply / Esc revert / no-op short-circuit / implicit Apply via popoverApplyBtn.click()); _selectionsEqual helper for sorted-array deep equality"
  - "tests/v2/test_browse_routes.py — 18 tests now (16 prior + 2 new): test_post_browse_grid_implicit_apply_payload_shape (HTTP contract pin) + test_post_browse_grid_idempotent_unchanged_selection (idempotency safety net)"
  - "tests/v2/test_phase04_invariants.py — new invariant test_popover_search_js_implements_d15a_close_event_taxonomy grep-guarding 5 JS source markers + data-bs-auto-close='outside' template marker"
  - ".planning/phases/04-browse-tab-port/04-HUMAN-UAT.md — gap-4 status: open → resolved with resolved: timestamp + fix: paragraph; Summary gaps_open 1 → 0, gaps_resolved 3 → 4"
affects: [phase-4-uat-replay, phase-5-ask-tab]

# Tech tracking
tech-stack:
  added: []   # No new dependencies
  patterns:
    - "Implicit-Apply via programmatic click on the explicit-Apply button — the canonical way to add a second commit-trigger to a popover/dialog without divergent HTMX paths. Single source of truth: the Apply button's hx-post + form= attribute. Future Phase 5+ work needing a 'commit-on-blur' or 'commit-on-outside-click' affordance should default to this pattern."
    - "Capture-phase keydown listener for Esc detection in the presence of Bootstrap's hide.bs.dropdown event — Bootstrap's e.clickEvent is null on BOTH Esc and programmatic close, so the keydown trick (set dataset.cancelling=1 from a document keydown listener BEFORE Bootstrap fires hide.bs.dropdown) is the canonical workaround. Capture phase (useCapture=true) is critical to win the race against Bootstrap's own internal listeners."
    - "Sorted-array deep equality for selection comparison (sort both sides at compare time) — order-independent without any custom Set equality helper. Survives JSON round-trip via dataset.originalSelection stash."

key-files:
  created:
    - .planning/phases/04-browse-tab-port/04-07-SUMMARY.md
  modified:
    - app_v2/static/js/popover-search.js (79 → 196 lines; close-event taxonomy implementation; selectors aligned with _picker_popover.html DOM contract)
    - tests/v2/test_browse_routes.py (+~140 lines; 16 → 18 tests; section header comment for gap-4)
    - tests/v2/test_phase04_invariants.py (+~80 lines; +1 test function)
    - .planning/phases/04-browse-tab-port/04-HUMAN-UAT.md (gap-4 status open → resolved + resolved: timestamp + fix: paragraph populated; Summary gaps_open 1 → 0, gaps_resolved 3 → 4; frontmatter updated; Current Test annotation appended)

key-decisions:
  - "Implicit-Apply via popoverApplyBtn.click() — chosen over hand-rolling htmx.ajax(...) or dispatching a manual fetch. Programmatic click reuses the explicit-Apply button's existing wiring (form= attribute auto-include from gap-2; hx-post=/browse/grid; hx-on:click=...hide()) so any future change to Apply behavior automatically propagates to all close-paths. Zero divergence between explicit and implicit Apply at the HTTP layer."
  - "Capture-phase keydown listener (useCapture=true) for Esc detection — Bootstrap's hide.bs.dropdown event payload (e.clickEvent) is null on BOTH Esc and programmatic close; e.clickEvent alone cannot distinguish. The keydown trick (set dataset.cancelling=1 BEFORE Bootstrap fires hide) is the canonical workaround. Capture phase is required because Bootstrap may stop propagation on its own internal Esc listener — bubble phase would lose the race."
  - "JSON-of-sorted-array on dataset.originalSelection (not a JS Set object) — survives DOM serialization, debuggable in browser devtools, and the sort-then-stringify pattern produces order-independent equality without custom helpers."
  - "No visual cue distinguishes implicit-Apply from explicit-Apply (D-08 / D-15a preserved). The grid + picker_badges_oob swap is the affordance — same UI feedback either way. Adding a flash/pulse/banner would create UX inconsistency."

patterns-established:
  - "Implicit-Apply via programmatic click on the explicit-Apply button — the default pattern for adding a second commit-trigger to a popover-shaped widget. Future Phase 5+ Ask tab popovers / parameter confirmation modals should adopt this pattern by default."
  - "Capture-phase document keydown listener for Esc detection in the presence of Bootstrap dropdown / modal close events — the canonical workaround for the limitations of e.clickEvent."
  - "Sorted-array JSON dataset stash for in-popover selection state — order-independent equality, survives DOM serialization, debuggable in browser devtools."

requirements-completed: [BROWSE-V2-01]

# Metrics
duration: ~10m
completed: 2026-04-28
---

# Phase 4 Plan 07: gap-4 Closure — Picker Popover Close-Event Taxonomy (D-15a) Summary

Closes gap-4 from `04-HUMAN-UAT.md` (severity: minor; contract_ref: D-15 amended + D-15a) — clicking outside the picker popover now commits the user's new selection (implicit-Apply) via a programmatic click on the popover's Apply button, reusing the gap-2 form-association and gap-3 picker_badges_oob OOB swap with zero code divergence from the explicit-Apply path. Esc explicitly cancels (revert from data-original-selection) via a capture-phase document keydown listener that sets `dataset.cancelling=1` BEFORE Bootstrap fires `hide.bs.dropdown`. A no-op short-circuit (sorted-array deep equality between current and stashed selection) skips the HTMX request entirely on stray opens that didn't change state. No visual cue distinguishes implicit-Apply from explicit-Apply (D-08 preserved); the grid + trigger badge swap is the affordance. Two server-side regression tests + one Phase 4 invariant guard the contract; full v2 suite green at 277 passed (was 274; +3 tests). Zero changes to Python production code, services, adapters, or any non-popover Browse template.

## Performance

- **Duration:** ~10 min wall clock
- **Tasks:** 3 (with 1 follow-up fixup commit for selector alignment)
- **Files modified:** 4 (1 JS, 2 tests, 1 UAT planning doc)
- **Files created:** 1 (this SUMMARY)
- **Production-code Python files modified:** 0
- **Production-code template files modified:** 0 (`_picker_popover.html` already had the macro header comment update from earlier in this session — committed in `a9f6089`; no further template change in this plan)

## The Fix (substantive diff in popover-search.js)

### Before — `app_v2/static/js/popover-search.js` `onDropdownHide` (lines 51-64 pre-fix)

```javascript
function onDropdownHide(e) {
  var root = e.target.querySelector ? e.target.querySelector('.popover-search-root') : null;
  if (!root) return;
  if (root.dataset.applied === '1') { delete root.dataset.applied; return; }
  // D-15: restore original selection on close-without-Apply.   ← OLD CONTRACT
  var original = JSON.parse(root.dataset.originalSelection || '[]');
  var set = {};
  for (var i = 0; i < original.length; i++) set[original[i]] = true;
  root.querySelectorAll('input[type="checkbox"]').forEach(function (cb) {
    cb.checked = !!set[cb.value];
  });
  var badge = root.querySelector('.popover-apply-count');
  if (badge) badge.textContent = original.length;
}
```

### After — `app_v2/static/js/popover-search.js` `onDropdownHide` + new `onKeydown` + new `_selectionsEqual`

```javascript
// D-15a no-op short-circuit support
function _selectionsEqual(currentArr, originalJsonStr) {
  var original;
  try { original = JSON.parse(originalJsonStr || '[]'); }
  catch (err) { return false; }
  // ...sorted-array deep equality
  if (currentArr.length !== original.length) return false;
  var a = currentArr.slice().sort();
  var b = original.slice().sort();
  for (var i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

// D-15a explicit-cancel detection — capture-phase keydown listener
function onKeydown(e) {
  if (e.key !== 'Escape') return;
  var openMenu = document.querySelector('.dropdown-menu.show.popover-search-root');
  if (openMenu) openMenu.dataset.cancelling = '1';
}

function onDropdownHide(e) {
  var root = e.target.querySelector ? e.target.querySelector('.popover-search-root') : null;
  if (!root) return;

  // (i) Explicit Apply already ran
  if (root.dataset.applied === '1') {
    delete root.dataset.applied;
    delete root.dataset.cancelling;
    return;
  }

  // (ii) D-15a EXPLICIT CANCEL — Esc was pressed; revert.
  if (root.dataset.cancelling === '1') {
    delete root.dataset.cancelling;
    /* ...revert checkboxes from data-original-selection... */
    return;
  }

  // (iii) D-15a NO-OP SHORT-CIRCUIT — selection unchanged.
  var current = /* ...gather currently-checked values... */;
  if (_selectionsEqual(current, root.dataset.originalSelection)) {
    root.dataset.applied = '1';
    return;
  }

  // (iv) D-15a IMPLICIT APPLY — click the Apply button programmatically.
  // Inherits gap-2 (form="browse-filter-form" auto-include) +
  // gap-3 (picker_badges_oob OOB swap on response) by reuse.
  var applyBtn = root.querySelector('.popover-apply-btn');
  if (applyBtn) applyBtn.click();
}

document.addEventListener('keydown', onKeydown, true);  // capture phase
```

The four pre-existing functions (`onInput`, `onCheckboxChange`, `onClearClick`, `onDropdownShow`, `onApplyClick`) are functionally byte-equivalent to pre-fix; only their comment context references D-15a where appropriate. The IIFE wrapper, `"use strict"`, and event listener registration order are preserved.

## Why It Works

The picker popover lives inside a Bootstrap `.dropdown` with `data-bs-auto-close="outside"`. Bootstrap fires `hide.bs.dropdown` on every close path: outside-click, click on the OTHER picker's trigger, click on Swap-axes / Clear-all, Tab-away, browser-tab-blur, programmatic `bootstrap.Dropdown.hide()`, AND Esc. The challenge is distinguishing Esc (revert) from all other paths (commit) without relying on Bootstrap's `e.clickEvent` payload (which is null on BOTH Esc AND programmatic close — useless as a sole distinguisher).

The capture-phase `document.addEventListener('keydown', onKeydown, true)` runs BEFORE any bubble-phase listener. When the user presses Escape with a popover open, `onKeydown` finds the open `.dropdown-menu.show.popover-search-root` and stamps it with `dataset.cancelling="1"`. Bootstrap then dispatches `hide.bs.dropdown`. Our `onDropdownHide` reads-and-clears the flag and branches to the revert path.

For all other close paths, `dataset.cancelling` is NOT set when `hide.bs.dropdown` fires — so we fall through to the implicit-Apply branch. The no-op short-circuit (branch iii) catches the case where the user opened the popover but didn't change anything; we skip the HTMX request entirely on those.

The implicit-Apply branch (iv) does NOT roll a separate `hx-post` — it programmatically clicks the popover's Apply button. The Apply button already carries `form="browse-filter-form"` (gap-2 fix) and `hx-post=/browse/grid` + `hx-target="#browse-grid"` + `hx-swap="innerHTML swap:200ms"` + `hx-on:click="bootstrap.Dropdown.getInstance(...).hide()"`. The programmatic click triggers all of these in sequence:

1. `onApplyClick` document listener fires → sets `dataset.applied=1` (so the now-completing `hide.bs.dropdown` exits at branch (i) on the next cycle)
2. The inline `hx-on:click="...hide()"` runs → no-op since the dropdown is already closing (Bootstrap.Dropdown.hide() is idempotent)
3. HTMX's machinery fires `hx-post=/browse/grid` with the form-encoded body — the response carries `grid` + `count_oob` + `warnings_oob` + `picker_badges_oob` (gap-3 fix), the trigger badges update, `HX-Push-Url` updates the address bar.

Single round-trip per implicit-Apply, identical HTTP contract to explicit-Apply.

## Test Counts

| Suite                              | Before | After | Delta |
| ---------------------------------- | ------ | ----- | ----- |
| `tests/v2/test_browse_routes.py`   | 16     | 18    | +2    |
| `tests/v2/test_phase04_invariants` | 13     | 14    | +1    |
| Full v2 suite (`tests/v2`)         | 274    | 277   | +3    |

The 1 skipped test is the long-standing Plan 04-02 tombstone for the old Phase 1 `/browse` placeholder. No tests were modified or removed.

### New regression tests

**1. `test_post_browse_grid_implicit_apply_payload_shape` (in `test_browse_routes.py`)**

Pins the HTTP contract that implicit-Apply now hits. Sends a POST body identical to what programmatic Apply.click() will produce; asserts:
- HTTP 200
- Populated pivot table (NOT empty-state)
- Both `picker-platforms-badge` + `picker-params-badge` OOB spans present (gap-3 contract preserved)
- ≥3 `hx-swap-oob="true"` fragments (grid_count + 2 picker badges)
- `HX-Push-Url` starts with `/browse?...` (Pitfall 2 defended)
- Affirmative invariant: `fetch_cells` received `("P1","P2","P3")` and `("vendor_id",)` — proves form-association carried the values

**2. `test_post_browse_grid_idempotent_unchanged_selection` (in `test_browse_routes.py`)**

HTTP-level idempotency safety net. Posts the same form body twice in sequence; asserts both responses are 200 with the same fragment shape and same `HX-Push-Url`. Forward-looking guard for the JS no-op short-circuit: if a future edit removes `_selectionsEqual`, the route will receive duplicate POSTs but must continue to behave correctly.

**3. `test_popover_search_js_implements_d15a_close_event_taxonomy` (in `test_phase04_invariants.py`)**

Static-grep guard on `popover-search.js` source — asserts five required code anchors:
1. `dataset.cancelling` ≥ 2 occurrences (set in `onKeydown`, read in `onDropdownHide`)
2. `addEventListener('keydown', <handler>, true)` capture-phase registration
3. `.popover-apply-btn` selector + a `.click()` call (programmatic implicit-Apply)
4. `_selectionsEqual` helper present
5. `D-15a` cited in a comment

AND asserts `data-bs-auto-close="outside"` is present in `_picker_popover.html` (the JS precondition).

If any of the six markers disappears in a future edit, this test fails loudly in CI.

## Confirmation: Production-code invariance

```
$ git diff --quiet HEAD~3 -- \
    app_v2/routers/browse.py \
    app_v2/services/browse_service.py \
    app_v2/services/cache.py \
    app_v2/services/ufs_service.py \
    app_v2/adapters/db/mysql.py \
    app_v2/templates/browse/index.html \
    app_v2/templates/browse/_filter_bar.html \
    app_v2/templates/browse/_grid.html \
    app_v2/templates/browse/_warnings.html \
    app_v2/templates/browse/_empty_state.html \
    app_v2/static/css/app.css \
    app_v2/templates/base.html
$ echo $?
0
```

All Python production code, all non-popover Browse templates, and the Phase 04 CSS are byte-identical to pre-fix HEAD. The fix is confined to:
- `app_v2/static/js/popover-search.js` (rewritten with D-15a)
- `tests/v2/test_browse_routes.py` (+2 tests appended)
- `tests/v2/test_phase04_invariants.py` (+1 test appended)
- `.planning/phases/04-browse-tab-port/04-HUMAN-UAT.md` (gap-4 closed)
- `.planning/phases/04-browse-tab-port/04-07-SUMMARY.md` (this file)

## Confirmation: gap-4 closed in 04-HUMAN-UAT.md

```
$ grep -A4 '^### gap-4' .planning/phases/04-browse-tab-port/04-HUMAN-UAT.md
### gap-4 — Clicking outside the popover discards selection (should auto-Apply)
status: resolved
reported: 2026-04-28T11:00:00Z
resolved: 2026-04-28T01:55:00Z
test_ref: 1
```

`fix:` block populated with one paragraph documenting the D-15a implementation + the four `onDropdownHide` branches + the keydown trick + the programmatic Apply click + the test artifacts + production-code invariance. `## Summary` block updated: `gaps_open: 1 → 0`, `gaps_resolved: 3 → 4`. Frontmatter `updated:` updated. Current Test annotation appended with closure marker.

## Task Commits

| Task                                   | Description                                                                              | Hash      |
| -------------------------------------- | ---------------------------------------------------------------------------------------- | --------- |
| 1                                      | Implement close-event taxonomy in popover-search.js + macro comment                      | `a9f6089` |
| 1 (fixup)                              | Correct popover-search.js selectors `.picker-*` → `.popover-*` (template DOM alignment)  | `a2d6cb3` |
| 2                                      | Add 2 server-side regression tests + 1 Phase 4 invariant for D-15a                       | `55f5421` |
| 3                                      | Close gap-4 in 04-HUMAN-UAT.md                                                           | `8556ac5` |

**Plan metadata commit:** _pending — final commit covers SUMMARY + STATE + ROADMAP progress_

## Decisions Made

1. **Implicit-Apply via `applyBtn.click()` rather than `htmx.trigger()` or `htmx.ajax(...)`.** Programmatic click reuses the existing Apply button's full HTMX wiring (`form=` auto-include from gap-2; `hx-post`; `hx-target`; `hx-swap`; `hx-on:click=...hide()`). Any future change to Apply behavior automatically propagates to all close-paths. Hand-rolling a second hx-post would create divergent code paths and rapidly drift from explicit-Apply.

2. **Capture-phase `document.addEventListener('keydown', onKeydown, true)` for Esc detection.** Bootstrap's `hide.bs.dropdown` event payload `e.clickEvent` is null on BOTH Esc and programmatic close — cannot distinguish. The keydown trick (set `dataset.cancelling="1"` BEFORE Bootstrap fires hide) is the canonical workaround. Capture phase is mandatory: Bootstrap may stop propagation on its own internal listener, so a bubble-phase handler would lose the race.

3. **Sorted-array deep equality for the no-op short-circuit (`_selectionsEqual`).** Stash `JSON.stringify(checked)` on `dataset.originalSelection` at open; at close time, sort the current values and the parsed snapshot and compare element-wise. Order-independent (toggling a box on then off doesn't fool it), DOM-serialization-safe, debuggable in devtools.

4. **No visual cue for implicit-Apply (D-08 / D-15a preserved).** The grid swap + `picker_badges_oob` OOB update from gap-3 are the affordance. Adding a flash/pulse/banner would create UX inconsistency between explicit-Apply (no flash) and implicit-Apply (flash). Same affordance for both paths.

5. **Selector alignment with existing template.** Initial implementation used `.picker-*` selectors targeting native `<div popover>` semantics; the template uses `.popover-*` selectors with Bootstrap dropdown semantics (`show.bs.dropdown` / `hidden.bs.dropdown`). Fixup commit `a2d6cb3` aligned the JS to the template's actual DOM contract per 04-07-PLAN's `<interfaces>` section.

## Deviations from Plan

**Rule 1 (Auto-fix bug):** Initial popover-search.js implementation (commit `a9f6089`) used `.picker-*` selectors and the native `<div popover>` `toggle` event — a different DOM contract than the existing `_picker_popover.html` template (which uses `.popover-*` selectors and Bootstrap dropdown events). The selector mismatch meant the JS would have failed to find any DOM elements at runtime. Caught by the new Phase 4 invariant test asserting `addEventListener('keydown', ..., true)` capture-phase registration on a Bootstrap dropdown event handler — the test failed initially because the JS used a different listener pattern entirely. Fixup commit `a2d6cb3` rewrote popover-search.js to match the template's DOM contract per the plan's `<interfaces>` section, which spelled out `popover-search-root`, `popover-apply-btn`, and `show.bs.dropdown` / `hidden.bs.dropdown` events explicitly.

No other deviations. Tasks 2 and 3 executed exactly as written.

## Issues Encountered

One self-correction during execution (logged as Rule-1 deviation above):

- **Initial JS rewrite mis-targeted the template's DOM contract.** The plan's `<interfaces>` block listed the correct selectors (`popover-search-root`, `popover-apply-btn`); my initial implementation used native `<div popover>` semantics with `.picker-*` selectors instead. Caught by the new Phase 4 invariant test failing on the capture-phase keydown grep. Fixed by rewriting the JS to use the Bootstrap dropdown event model and `.popover-*` selectors per the template's actual contract. Fixup committed as `a2d6cb3`.

## User Setup Required

None — no env vars, no external service config, no manual steps.

## Phase 4 Replay-Readiness

**Phase 4 ready for UAT replay.** All four gaps from `04-HUMAN-UAT.md` now resolved:

- gap-1 (popover clipping) — resolved 2026-04-27 (CSS `:has()` panel override)
- gap-2 (Apply form-association) — resolved 2026-04-27 (Plan 04-05)
- gap-3 (picker badge OOB swap) — resolved 2026-04-28 (Plan 04-06)
- gap-4 (close-event taxonomy / outside-click commit) — resolved 2026-04-28 (this plan)

Manual UAT replay steps (after `.venv/bin/uvicorn app_v2.main:app --port 8000`):
- Tick 3 platforms in Platforms picker; click on the page background outside the popover. Pivot grid renders with the 3 platforms; trigger badge reads "Platforms 3". → IMPLICIT-APPLY confirmed.
- Open Platforms picker, tick a 4th platform, press Esc. Popover closes; trigger badge stays at 3; grid does NOT re-swap. → ESC-CANCEL confirmed.
- Open Platforms picker (no checkbox change); click outside. No HTMX request in DevTools Network panel. → NO-OP SHORT-CIRCUIT confirmed.
- Click the Parameters trigger button while the Platforms popover is open. Platforms popover closes (implicit-Apply commits any pending change); Parameters popover opens. → CLICK-ON-OTHER-TRIGGER implicit-Apply confirmed.

`/gsd-verify-phase 4` and `/gsd-uat-phase 4` can be re-run after manual replay confirms the four close-event behaviors.

## Threat Flags

None. The fix uses long-standing browser DOM APIs (`addEventListener` with capture phase, `dataset` accessor, `JSON.stringify`/`JSON.parse`, standard form-association). All ES5-compatible. The XSS / SQLi defenses tested in earlier plans (test_post_browse_grid_xss_escape_in_param_label, test_post_browse_grid_sql_injection_attempt_returns_safe) continue to pass without modification — they are independent of close-event-taxonomy logic. D-14(a)/(b)/(c) (Apply closes popover, updates badge, single hx-post) preserved through reuse — implicit-Apply runs the SAME Apply button code path as explicit-Apply.

The threat-register entries from this plan's body (T-04-07-01..T-04-07-07) are all addressed:
- **T-04-07-01** (future JS edit removes keydown listener / capture phase): mitigated by `test_popover_search_js_implements_d15a_close_event_taxonomy` — fails CI if the literal `addEventListener('keydown', ..., true)` is removed
- **T-04-07-02** (future edit replaces programmatic .click() with hand-rolled hx-post): mitigated by the same invariant requiring `.popover-apply-btn` reference + `.click()` call
- **T-04-07-03** (no-op short-circuit removed → DB hammering): mitigated by invariant requiring `_selectionsEqual` present; defense-in-depth via TTLCache wrapper on `fetch_cells`
- **T-04-07-04** (Esc handler scoped too broadly): accept — handler scopes via `.dropdown-menu.show.popover-search-root` (only one open at a time)
- **T-04-07-05** (race: applyBtn.click() fires after dropdown removed from .show): accept — form= attribute association is independent of dropdown visibility; HTMX reads from form.elements
- **T-04-07-06** (unintended Python regressions): mitigated by `git diff --quiet` invariance check + full v2 suite green (277 passed)
- **T-04-07-07** (XSS via dataset.originalSelection JSON encoding): accept — three layers of automatic escaping (DOM value decode + JSON.stringify + dataset attribute setter)

## Self-Check: PASSED

- `app_v2/static/js/popover-search.js` modified — FOUND (`dataset.cancelling`, `_selectionsEqual`, `addEventListener('keydown', onKeydown, true)`, `.popover-apply-btn` + `.click()`, `D-15a` comment all present; `node -c` parses cleanly)
- `app_v2/templates/browse/_picker_popover.html` byte-identical to gap-3 closure state — FOUND (`data-bs-auto-close="outside"` present once on trigger button; `form="browse-filter-form"` present 3× as in pre-fix; `id="picker-{{ name }}-badge"` present)
- `tests/v2/test_browse_routes.py` modified — FOUND (18 test functions; 2 new tests appended; existing 16 byte-identical)
- `tests/v2/test_phase04_invariants.py` modified — FOUND (1 new test function appended; existing 9 byte-identical; runtime test count 13 → 14 due to parametrize expansion)
- `.planning/phases/04-browse-tab-port/04-HUMAN-UAT.md` modified — FOUND (gap-4 status: resolved; resolved: 2026-04-28T01:55:00Z; fix: paragraph populated; Summary gaps_open 0, gaps_resolved 4; gap-1/gap-2/gap-3 entries byte-identical)
- `.planning/phases/04-browse-tab-port/04-07-SUMMARY.md` — being written now (this file)
- Commit `a9f6089` (Task 1 — initial close-event taxonomy implementation) — FOUND in `git log --oneline`
- Commit `a2d6cb3` (Task 1 fixup — selector alignment with template) — FOUND in `git log --oneline`
- Commit `55f5421` (Task 2 — 2 regression tests + 1 invariant) — FOUND in `git log --oneline`
- Commit `8556ac5` (Task 3 — close gap-4 in UAT) — FOUND in `git log --oneline`
- Full v2 suite green: 277 passed, 1 skipped (was 274 + 1 pre-fix; +3 new tests)

---
*Phase: 04-browse-tab-port*
*Plan: 07 (gap-closure for gap-4 — D-15a close-event taxonomy)*
*Completed: 2026-04-28*
