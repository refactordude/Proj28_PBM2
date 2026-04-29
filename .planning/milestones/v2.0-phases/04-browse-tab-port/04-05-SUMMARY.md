---
phase: 04-browse-tab-port
plan: 05
subsystem: ui
gap_closure: true
closes_gaps: [gap-2]
tags: [bugfix, browse, htmx, regression-guard, gap-closure, form-association]

# Dependency graph
requires:
  - phase: 04-browse-tab-port (plan 04-03)
    provides: app_v2/templates/browse/_picker_popover.html (Apply button + hx-include attribute now corrected) + empty <form id="browse-filter-form"> placement in index.html (Pitfall 4 defended)
  - phase: 04-browse-tab-port (plan 04-04)
    provides: tests/v2/test_browse_routes.py (12 tests + _patch_cache helper + client fixture + _post_form_pairs helper) — appended-to verbatim, not modified
provides:
  - "app_v2/templates/browse/_picker_popover.html — Apply button now carries form=\"browse-filter-form\" (mirrors _filter_bar.html Swap-axes pattern); broken hx-include CSS-descendant selector removed"
  - "tests/v2/test_browse_routes.py — 14 tests now (12 original + 2 new regression guards): test_apply_button_carries_form_attribute (rendered-HTML smoke) + test_post_browse_grid_apply_button_payload_renders_populated_grid (end-to-end with recording mock)"
  - ".planning/phases/04-browse-tab-port/04-HUMAN-UAT.md — gap-2 status: open → resolved with resolved: timestamp + fix: paragraph populated"
affects: [phase-4-uat-replay, phase-5-ask-tab]

# Tech tracking
tech-stack:
  added: []   # No new dependencies
  patterns:
    - "HTML form-association via form= attribute on submit buttons inside Bootstrap dropdowns/popovers — same pattern Swap-axes already used in _filter_bar.html (line 38). HTMX's dn() (getInputValues) for non-GET requests calls Nt(triggeringElement)=element.form, then iterates form.elements (browser DOM API) which enumerates ALL form-associated controls regardless of DOM tree position. Eliminates the need for hx-include CSS selectors when the controls are inside dropdown menus."
    - "Two-tier regression test pattern for HTMX template attributes — a cheap rendered-HTML smoke test (catches macro edits at template-render time) PLUS an end-to-end behavioral test with recording mock (catches route-handler regressions and proves the form body actually carried the values). Both tests use existing _patch_cache + client fixture + _post_form_pairs helper from Plan 04-04 — zero new test infrastructure."

key-files:
  created: []
  modified:
    - app_v2/templates/browse/_picker_popover.html (Apply button: ADD form="browse-filter-form"; REMOVE hx-include="#browse-filter-form input:checked"; macro header comment extended to document the contract)
    - tests/v2/test_browse_routes.py (appended 2 regression tests + section header comment; existing 12 tests + helpers + imports byte-identical)
    - .planning/phases/04-browse-tab-port/04-HUMAN-UAT.md (gap-2 entry: status open→resolved + resolved: timestamp added + fix: paragraph populated; all other gap-2 sub-fields byte-identical; gap-1 byte-identical)

key-decisions:
  - "Use form= attribute (HTML form-association API), NOT change hx-include to '#browse-filter-form' (the form element itself). Both fixes work, but form= matches the working Swap-axes pattern verbatim — Apply now uses the same code path Swap-axes proves out in production. Eliminates the divergence that caused gap-2 in the first place."
  - "Regression test split into two planes: (a) static smoke test on rendered HTML asserts form= present AND broken hx-include absent — catches macro regressions BEFORE a browser ever sees them; (b) end-to-end behavior test with recording mock proves fetch_cells received the actual selected platforms+params tuple (not empty) — catches route-handler regressions AND proves the form-body shape HTMX produces post-fix actually round-trips through the route. Same recording-mock pattern as the Plan 04-04 garbage-params test (Issue 2 fix verification)."
  - "Macro header comment extended to document the contract — 'Each checkbox AND the Apply submit button use form=\"browse-filter-form\"'. Previous comment only covered the checkboxes, leaving the Apply button's contract implicit. Now any future editor reading the comment block sees the full form-association policy upfront."

patterns-established:
  - "form= attribute on submit buttons inside Bootstrap dropdowns/modals/popovers — the canonical fix for HTMX hx-include CSS selectors that target controls outside the form's DOM subtree. Future Phase 5+ template work involving popovers should adopt this pattern by default; reach for hx-include CSS selectors only when form-association cannot apply (e.g., aggregating across multiple form= ids)."
  - "Two-tier regression test for HTMX template contracts — rendered-HTML smoke test + end-to-end recording-mock behavior test. The smoke test is fast and catches the syntactic regression; the end-to-end test catches semantic regressions and proves the contract holds end-to-end. Both reuse the same _patch_cache + client fixture infrastructure, so the marginal cost per pair is ~30 lines of test code."

requirements-completed: [BROWSE-V2-01]

# Metrics
duration: 5m
completed: 2026-04-27
---

# Phase 4 Plan 05: gap-2 Closure — Apply Button Form-Association Summary

**Single-attribute fix to `_picker_popover.html` closing gap-2 from 04-HUMAN-UAT.md (severity: major). Apply button now carries `form="browse-filter-form"` (mirrors the working Swap-axes pattern in `_filter_bar.html`). Broken `hx-include="#browse-filter-form input:checked"` CSS-descendant selector removed. Two regression tests added (smoke + end-to-end) so the gap cannot silently re-open. Zero Python production-code changes — verified via `git diff --quiet HEAD` on routers/services/adapters/index.html/_filter_bar.html. Full v2 test suite green (272 passed, 1 skipped, up from 270 → 272 with the two new tests).**

## Performance

- **Duration:** ~5 min wall clock
- **Started:** 2026-04-27T23:48:04Z
- **Completed:** 2026-04-27T23:52:48Z
- **Tasks:** 2
- **Files modified:** 3 (1 template, 1 test file, 1 UAT planning doc)
- **Files created:** 0
- **Production-code Python files modified:** 0

## The Fix (literal diff)

### Before — `app_v2/templates/browse/_picker_popover.html` (Apply button block)

```html
<button type="button"
        class="btn btn-primary btn-sm popover-apply-btn"
        hx-post="/browse/grid"
        hx-include="#browse-filter-form input:checked"   {# ← CSS DESCENDANT SELECTOR — matches zero elements #}
        hx-target="#browse-grid"
        hx-swap="innerHTML swap:200ms"
        hx-on:click="bootstrap.Dropdown.getInstance(...).hide()"
        aria-label="Apply {{ label | lower }} selection">
  Apply <span class="popover-apply-count badge bg-light text-primary ms-1">{{ selected | length }}</span>
</button>
```

### After

```html
<button type="button"
        class="btn btn-primary btn-sm popover-apply-btn"
        form="browse-filter-form"                        {# ← FORM-ASSOCIATION ATTRIBUTE (HTML standard) #}
        hx-post="/browse/grid"
        hx-target="#browse-grid"
        hx-swap="innerHTML swap:200ms"
        hx-on:click="bootstrap.Dropdown.getInstance(...).hide()"
        aria-label="Apply {{ label | lower }} selection">
  Apply <span class="popover-apply-count badge bg-light text-primary ms-1">{{ selected | length }}</span>
</button>
```

**One line added (`form="browse-filter-form"`), one line removed (`hx-include="#browse-filter-form input:checked"`).** No other lines in the button block changed. Macro header comment extended to document that the Apply button now joins the picker checkboxes in form-associating with `#browse-filter-form`.

## Why It Works

The Browse page has an empty `<form id="browse-filter-form" class="visually-hidden">` declared in `index.html` BEFORE the filter-bar include (Pitfall 4 defense from Plan 04-03). Picker checkboxes inside `.dropdown-menu` siblings already carry `form="browse-filter-form"` so they participate in `form.elements` even though they are not DOM descendants. The Swap-axes checkbox in `_filter_bar.html` line 38 also uses this pattern and ships working since Plan 04-03.

The Apply button was the outlier — relying on `hx-include="#browse-filter-form input:checked"`, a CSS descendant combinator that matched zero elements (the form is empty; the checkboxes are siblings, not children). HTMX's `dn()` (getInputValues in htmx.min.js) for non-GET requests then sent the empty form body, triggering `is_empty_selection=True` in the route handler and rendering the empty-state alert.

Adding `form="browse-filter-form"` to the Apply button puts it on the SAME code path Swap-axes uses: HTMX's `dn()` calls `Nt(triggeringElement) = element.form`, resolves to the empty `<form id="browse-filter-form">`, then `fn()` iterates `form.elements` — which the browser DOM API populates with ALL form-associated controls regardless of tree position. The picker checkboxes are picked up automatically.

Full evidence with htmx.min.js source pointers: `.planning/debug/gap-2-apply-no-swap.md`.

## Test Counts

| Suite | Before | After | Delta |
|------|-------|-------|-------|
| `tests/v2/test_browse_routes.py` | 12 | 14 | +2 |
| Full v2 suite (`tests/v2`) | 270 passed, 1 skipped | 272 passed, 1 skipped | +2 |
| `tests/v2/test_phase04_invariants.py` | 13 | 13 | 0 |

The 1 skipped test is the long-standing Plan 04-02 tombstone for the old Phase 1 `/browse` placeholder. No tests were modified or removed.

### New regression tests

**1. `test_apply_button_carries_form_attribute` (rendered-HTML smoke)**
- Renders `GET /browse` and slices the Apply button block out of the HTML
- Asserts `form="browse-filter-form"` is present in the block
- Asserts the broken `hx-include="#browse-filter-form input:checked"` selector is absent
- Catches macro regressions at template-render time, before a browser is involved

**2. `test_post_browse_grid_apply_button_payload_renders_populated_grid` (end-to-end behavior with recording mock)**
- Posts the form-encoded body that HTMX will produce post-fix (`platforms=P1&platforms=P2&params=attribute · vendor_id`)
- Asserts the response contains the populated pivot table HTML, NOT the empty-state alert
- Asserts `fetch_cells` received `platforms=("P1","P2")` and `items=("vendor_id",)` — proves the form body carried the values; assertion is non-tautological (recording mock with affirmative invariant)

Both tests reuse the existing `_patch_cache` helper, `client` fixture, `_post_form_pairs` helper, and `MockDB` class verbatim. `_patch_cache` call count went from 13 → 15 (one per new test), confirming reuse.

## Confirmation: Production-code invariance (zero Python changes)

```
$ git diff --quiet HEAD~2 -- \
    app_v2/routers/browse.py \
    app_v2/services/browse_service.py \
    app_v2/services/ufs_service.py \
    app_v2/services/cache.py \
    app_v2/adapters/db/mysql.py \
    app_v2/templates/browse/index.html \
    app_v2/templates/browse/_filter_bar.html
$ echo $?
0
```

All Python production code (routers, services, adapters) AND the other Browse templates are byte-identical to pre-fix HEAD. The fix is purely a single-attribute change in one Jinja template (`_picker_popover.html`) plus the two regression tests in `tests/v2/test_browse_routes.py`. The `04-HUMAN-UAT.md` updates are planning-doc-only.

## Confirmation: gap-2 closed in 04-HUMAN-UAT.md

```
$ grep -A6 '^### gap-2' .planning/phases/04-browse-tab-port/04-HUMAN-UAT.md
### gap-2 — Apply button does not swap pivot grid; only Swap-axes triggers render
status: resolved
reported: 2026-04-27T13:25:00Z
diagnosed: 2026-04-27T14:30:00Z
resolved: 2026-04-27T23:50:00Z
test_ref: 1
severity: major
```

`fix:` block populated with one paragraph documenting the form-association change, the two regression tests added, and the zero-Python-changes invariant. Other gap-2 sub-fields (`reported:`, `diagnosed:`, `test_ref:`, `severity:`, `debug_session:`, `symptom:`, `root_cause:`) byte-identical. gap-1 entry untouched. File header untouched.

## Task Commits

| Task | Description | Hash |
|------|-------------|------|
| 1 | Apply button form-association fix in `_picker_popover.html` | `3d82b74` |
| 2 | Add 2 regression tests + close gap-2 in 04-HUMAN-UAT.md | `b0e6156` |

**Plan metadata commit:** _pending — final commit covers SUMMARY + STATE + ROADMAP progress + REQUIREMENTS marks_

## Decisions Made

- **Chose `form="browse-filter-form"` over `hx-include="#browse-filter-form"` (the form element itself).** Both fixes work — HTMX recognizes form elements in `hx-include` and would iterate `form.elements` correctly. But the form-association attribute matches the working Swap-axes pattern verbatim (`_filter_bar.html` line 38), eliminating the divergence between Apply and Swap-axes that caused gap-2 in the first place. Now both controls sit on the SAME code path. Future divergences will be loud (different attribute structures) instead of silent (subtly different selector semantics).
- **Two-tier regression test (smoke + end-to-end).** A pure HTML smoke test would catch macro regressions but not route-handler regressions; a pure end-to-end test would catch route-handler regressions but skip the cheap-and-fast layer. Pairing them gives both planes of defense. Marginal cost: ~30 lines of test code per pair.
- **End-to-end test uses recording mock + affirmative invariant.** Asserts `captured["platforms"] == ("P1", "P2")` AND `captured["items"] == ("vendor_id",)`, NOT just "the response is not the empty-state alert". This guards against a future regression where the route handler accidentally tolerates an empty body (e.g. by inferring platforms from session state) — the test would fail because `captured["platforms"]` would be the wrong tuple. Same non-tautological pattern as the Plan 04-04 garbage-params test (Issue 2 fix verification).
- **Did not extend `_post_form_pairs` or `_patch_cache`.** Existing helpers handled both new tests verbatim — no helper signature changes, no new helpers. This keeps the test infrastructure stable for future Plan 04-* / Phase 5 tests.

## Deviations from Plan

None — plan executed exactly as written. Both tasks' verification blocks passed on first run. No Rule-1, Rule-2, Rule-3, or Rule-4 deviations applied.

The plan was unusually precise (gap-closure plans typically are: a one-line bug fix is hard to deviate from). The macro header comment update, the test names, the `fix:` paragraph wording, and the `resolved:` timestamp format were all spelled out verbatim in the plan body — and all landed verbatim in the final files.

## Issues Encountered

None. Both tasks executed cleanly:
- Task 1: edit applied; smoke render via `templates.env.get_template().module.picker_popover(...)` confirmed `form="browse-filter-form"` lands inside the rendered Apply button block; production-code-invariance check (`git diff --quiet`) returned 0; commit succeeded.
- Task 2: tests appended; first pytest run on the two new tests passed; full file (14 tests) passed; full v2 suite (272 passed, 1 skipped) passed; gap-2 status update verified via `grep -A4 '^### gap-2' | grep status:`; commit succeeded.

## User Setup Required

None — no env vars, no external service config, no manual steps.

## Phase 4 Replay-Readiness

**Phase 4 ready for UAT replay** — gap-2 closed, the original UAT Test 1 reproduction steps from `04-HUMAN-UAT.md` should now produce the populated grid on the FIRST Apply click without the Swap-axes workaround.

UAT replay command:
```
.venv/bin/uvicorn app_v2.main:app --port 8000
# Open http://localhost:8000/browse
# Tick 2-3 platforms in Platforms picker
# Tick 2-3 params in Parameters picker
# Click Apply — pivot grid renders WITHOUT clicking Swap-axes first
```

Phase 4 verification can also be re-run:
```
/gsd-verify-phase 4    # all 3 ROADMAP success criteria are now actually demonstrable
/gsd-uat-phase 4       # UAT Test 1 should pass on first Apply click
```

Phase 4's three ROADMAP success criteria — filter swap (BROWSE-V2-01), caps mirror v1.0, URL round-trip — are all now demonstrable end-to-end without the Swap-axes "refresh hack" that was previously required.

## Threat Flags

None. The fix uses a long-standing HTML standard attribute (`form=`) that has been part of HTML4 since 1999. HTMX has supported the `form=`/`element.form` path since v1.x. No new attack surface introduced. The XSS / SQLi defenses tested in Plan 04-04 (`test_post_browse_grid_xss_escape_in_param_label`, `test_post_browse_grid_sql_injection_attempt_returns_safe`) continue to pass without modification — they are independent of form-association logic. The threat-register entries from Plan 04-05's plan body (T-04-05-01..T-04-05-04) are all `mitigate` dispositions and the mitigations are in place: T-04-05-01 (template regression) is mitigated by `test_apply_button_carries_form_attribute`; T-04-05-02 (vacuous test pass) is mitigated by the recording-mock + affirmative invariant in `test_post_browse_grid_apply_button_payload_renders_populated_grid`; T-04-05-03 (form= leakage to a different form) is impossible because the page has exactly ONE form id; T-04-05-04 (unintended Python regressions) is mitigated by the `git diff --quiet` invariance check + full v2 suite green.

## Self-Check: PASSED

- `app_v2/templates/browse/_picker_popover.html` modified — FOUND (`form="browse-filter-form"` present on popover-apply-btn; `hx-include="#browse-filter-form input:checked"` absent)
- `tests/v2/test_browse_routes.py` modified — FOUND (14 test functions; 2 new tests added; existing 12 byte-identical)
- `.planning/phases/04-browse-tab-port/04-HUMAN-UAT.md` modified — FOUND (gap-2 status: resolved; resolved: timestamp; fix: paragraph populated)
- `.planning/phases/04-browse-tab-port/04-05-SUMMARY.md` — being written now
- Commit `3d82b74` (Task 1 — Apply button form-association fix) — FOUND in `git log --oneline`
- Commit `b0e6156` (Task 2 — regression tests + gap-2 closure in UAT) — FOUND in `git log --oneline`

---
*Phase: 04-browse-tab-port*
*Plan: 05 (gap-closure for gap-2)*
*Completed: 2026-04-27*
