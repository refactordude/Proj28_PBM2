---
phase: 04-browse-tab-port
plan: 06
subsystem: ui
gap_closure: true
closes_gaps: [gap-3]
tags: [bugfix, browse, htmx, oob-swap, regression-guard, gap-closure]

# Dependency graph
requires:
  - phase: 04-browse-tab-port (plan 04-03)
    provides: "app_v2/templates/browse/_picker_popover.html (picker_popover macro + trigger badge structure) + app_v2/templates/browse/index.html (Pattern 6 OOB blocks count_oob / warnings_oob — extended here)"
  - phase: 04-browse-tab-port (plan 04-05)
    provides: "form=\"browse-filter-form\" attribute on popover-apply-btn (gap-2 fix) — depends on NOT being regressed; Task 1 verification grep guards this explicitly"
provides:
  - "app_v2/templates/browse/_picker_popover.html — trigger button badge now ALWAYS rendered with stable id=\"picker-{{ name }}-badge\" and d-none for visibility (instead of conditional emit). Macro header comment extended to document the OOB-target contract"
  - "app_v2/templates/browse/index.html — new {% block picker_badges_oob %} emitting two hx-swap-oob spans (one per picker) using the count_oob pattern verbatim"
  - "app_v2/routers/browse.py — block_names list extended 3 -> 4 with \"picker_badges_oob\"; docstring Returns sentence updated"
  - "tests/v2/test_browse_routes.py — 16 tests now (14 prior + 2 new): test_post_browse_grid_emits_picker_badge_oob_blocks (non-empty: counts + visible) + test_post_browse_grid_picker_badge_zero_count_renders_hidden (empty: stable target hidden via d-none)"
  - ".planning/phases/04-browse-tab-port/04-HUMAN-UAT.md — gap-3 status: open -> resolved with resolved: timestamp + fix: paragraph populated; Summary block gaps_open 1 -> 0, gaps_resolved 2 -> 3"
affects: [phase-4-uat-replay, phase-5-ask-tab]

# Tech tracking
tech-stack:
  added: []   # No new dependencies
  patterns:
    - "Third OOB block in browse/index.html proves Pattern 6 (Pitfall 7) scales — count_oob (D-06), warnings_oob (D-24 reserved), picker_badges_oob (D-14(b), this plan). Each OOB block follows the same shape: top-level block outside the .panel/.shell containers, single id-tagged element with hx-swap-oob=\"true\" + the same data binding the in-place element uses on GET render. Future Phase 5+ work needing partial-DOM updates outside the primary swap target should reach for this pattern by default."
    - "Always-emit-with-d-none-when-zero pattern for HTMX OOB swap targets — for any element whose visibility depends on count > 0, emit ALWAYS with the same id and toggle the Bootstrap d-none class instead of {% if count %}<span>...</span>{% endif %}. Guarantees a stable HTMX merge target across the full state space (non-empty -> empty -> non-empty round trips). The visual contract is preserved because Bootstrap's d-none sets display:none !important — visually equivalent to omission, but DOM-wise persistent."

key-files:
  created:
    - .planning/phases/04-browse-tab-port/04-06-SUMMARY.md
  modified:
    - app_v2/templates/browse/_picker_popover.html (trigger badge: stable id + d-none visibility; macro header docstring extended ~7 lines for the OOB-target contract)
    - app_v2/templates/browse/index.html (new {% block picker_badges_oob %} after warnings_oob; emits two hx-swap-oob spans for platforms + params badges)
    - app_v2/routers/browse.py (block_names list extended 3 -> 4 with "picker_badges_oob"; docstring Returns sentence updated)
    - tests/v2/test_browse_routes.py (appended 2 regression tests + section header comment; existing 14 tests + helpers + imports byte-identical)
    - .planning/phases/04-browse-tab-port/04-HUMAN-UAT.md (gap-3: status open -> resolved + resolved: timestamp + fix: paragraph; Summary gaps_open 1 -> 0, gaps_resolved 2 -> 3; gap-2 entry byte-identical; trailing gap-1 entry byte-identical)

key-decisions:
  - "Candidate A (server-side OOB) over Candidate B (client-side JS in popover-search.js). Both close the gap behaviorally, but Candidate A matches the existing count_oob / warnings_oob pattern verbatim — codebase coherence, single source of truth (server count, not client checkbox-recount), TestClient-testable (no Playwright/AppTest needed since CONTEXT.md defers Playwright until Phase 3+ stabilizes). Candidate B would have introduced a SECOND source of truth that could drift; the regression test surface would have required JS execution which the existing 14 TestClient-based tests cannot exercise."
  - "Always-emit-with-d-none over conditional {% if selected %}<span>...</span>{% endif %} emission. The conditional pattern was the prior code (it was the ROOT cause of why HTMX could never merge into the badge — the span often did not exist in the DOM at all). Always-emit guarantees HTMX has a target across non-empty -> empty round trips; the d-none toggle preserves D-08's 'no visible badge when empty' contract. Test test_post_browse_grid_picker_badge_zero_count_renders_hidden specifically guards this — a regression to conditional emit would fail the assertion 'id=\"picker-platforms-badge\" in r.text' for the empty case."
  - "Reuse _patch_cache + client + _post_form_pairs verbatim. No new test infrastructure; both new tests fit the same shape as Plan 04-04's recording-mock tests and Plan 04-05's gap-2 regression pair. _patch_cache call count grows 15 -> 17, confirming reuse. Keeps test infra stable for Phase 5+."

patterns-established:
  - "Third OOB block (picker_badges_oob) cements the OOB pattern as the canonical mechanism for partial-DOM updates outside the primary hx-target swap. Future Phase 5+ Browse / Ask work involving sticky-shell elements (counts, badges, status pills) should default to this pattern."
  - "Always-emit-with-d-none-when-zero is the default for any HTMX OOB target whose visibility depends on count > 0. Conditional emit is now an explicit anti-pattern documented in the _picker_popover.html macro header comment."

requirements-completed: [BROWSE-V2-01]

# Metrics
duration: 8m
completed: 2026-04-28
---

# Phase 4 Plan 06: gap-3 Closure — Picker Badge OOB Swap on Apply Summary

**Closes gap-3 from `04-HUMAN-UAT.md` (severity: minor) — D-14(b) was breached: clicking Apply correctly produced the populated grid (gap-2 fix) but the trigger button count badges only updated on a full page refresh. Adopted Candidate A (server-side OOB) — extended the existing count_oob / warnings_oob OOB pattern with a new `picker_badges_oob` block emitting two `hx-swap-oob` spans (platforms + params) on every POST /browse/grid response. The trigger button badge in `_picker_popover.html` is now ALWAYS rendered with a stable `id="picker-{{ name }}-badge"` and uses the `d-none` class for visibility (instead of conditional `<span>` emission), so HTMX has a permanent merge target while D-08's "no badge when empty" visual contract is preserved. Two regression tests added (non-empty selection — counts + visible; empty selection — stable target hidden via d-none). Full v2 suite green: 274 passed, 1 skipped (up from 272 → 274 with the two new tests). Zero changes to services / adapters / popover-search.js / app.css.**

## Performance

- **Duration:** ~8 min wall clock
- **Started:** 2026-04-28T01:20:00Z
- **Completed:** 2026-04-28T01:35:00Z
- **Tasks:** 3
- **Files modified:** 5 (2 templates, 1 router, 1 test file, 1 UAT planning doc)
- **Files created:** 1 (this SUMMARY)
- **Production-code Python files modified:** 1 (`app_v2/routers/browse.py` — block_names list extension + docstring; zero behavior change beyond emitting an additional named block)
- **Production-code Python files created:** 0 (zero service / adapter changes)

## The Fix (literal diff)

### Before — `app_v2/templates/browse/_picker_popover.html` (trigger button label + badge, line 33)

```html
{{ label }}{% if selected %} <span class="badge bg-secondary ms-1">{{ selected | length }}</span>{% endif %} <i class="bi bi-chevron-down ms-1"></i>
```

### After

```html
{{ label }} <span id="picker-{{ name }}-badge" class="badge bg-secondary ms-1{% if not selected %} d-none{% endif %}" aria-live="polite">{{ selected | length }}</span> <i class="bi bi-chevron-down ms-1"></i>
```

**Stable id `picker-{{ name }}-badge` added; conditional emit replaced with always-emit + `d-none` for visibility; `aria-live="polite"` mirrors the existing `#grid-count` pattern so screen readers announce count updates after Apply.**

### Before — `app_v2/templates/browse/index.html` (no picker_badges_oob block existed)

```jinja2
{% block warnings_oob %}{% endblock warnings_oob %}
{% endblock %}
```

### After

```jinja2
{% block warnings_oob %}{% endblock warnings_oob %}

{# OOB picker badges — emitted by POST /browse/grid alongside the grid swap
   so the trigger button count badges in .browse-filter-bar refresh after
   Apply (D-14(b); gap-3 closure 2026-04-28). HTMX merges each <span> by id
   into the corresponding picker-{name}-badge in the persistent .panel
   shell. Both badges are ALWAYS emitted on every POST so a same-block swap
   (e.g., user only changed platforms) still corrects any stale-params
   display in case the params trigger drifted. The d-none class is toggled
   to match D-08 (no visible badge when count is 0) — text content is the
   integer count even when hidden, so HTMX's text replacement on the
   existing span is always correct. Stable target: precedent Pattern 6 /
   count_oob (lines 73-77 above). #}
{% block picker_badges_oob %}
  <span id="picker-platforms-badge" hx-swap-oob="true" class="badge bg-secondary ms-1{% if not vm.selected_platforms %} d-none{% endif %}" aria-live="polite">{{ vm.selected_platforms | length }}</span>
  <span id="picker-params-badge" hx-swap-oob="true" class="badge bg-secondary ms-1{% if not vm.selected_params %} d-none{% endif %}" aria-live="polite">{{ vm.selected_params | length }}</span>
{% endblock picker_badges_oob %}
{% endblock %}
```

**New top-level Jinja block emitting two OOB spans on every POST /browse/grid render. Both badges always emit (idempotent merge for the unchanged picker), guarding against drift if any future code path mutates the trigger badges out-of-band.**

### Before — `app_v2/routers/browse.py` (browse_grid block_names, line 123)

```python
response = templates.TemplateResponse(
    request,
    "browse/index.html",
    ctx,
    block_names=["grid", "count_oob", "warnings_oob"],
)
```

### After

```python
response = templates.TemplateResponse(
    request,
    "browse/index.html",
    ctx,
    block_names=["grid", "count_oob", "warnings_oob", "picker_badges_oob"],
)
```

**One-element extension of the named-block list. Plus a 1-line docstring update to the `Returns` sentence on `browse_grid` mentioning the new block.**

## Why It Works

The Browse page renders the picker trigger buttons (with their count badges) inside `.browse-filter-bar` — a region of the persistent `.panel` shell that lives **outside** `#browse-grid`. The Apply button's primary HTMX swap is `hx-target="#browse-grid"` with `hx-swap="innerHTML"`, so it can only replace the contents of the grid container. The trigger badges are unreachable by the primary swap.

HTMX's solution for this case is the OOB (out-of-band) swap mechanism: any element in the response carrying `hx-swap-oob="true"` is detached from the response body and merged by `id` into the existing DOM, regardless of where it appears in the response. Plan 04-03 already established this pattern with `count_oob` (the `#grid-count` caption in the panel header) and reserved `warnings_oob` for future cap-warning OOBs.

This plan extends the same pattern with a third block — `picker_badges_oob` — emitting two OOB spans (one per picker badge). HTMX merges each into its corresponding `<span id="picker-platforms-badge">` / `<span id="picker-params-badge">` in the persistent shell, refreshing the count text and the visibility class atomically.

The always-emit-with-d-none pattern is critical: if the badge `<span>` in `_picker_popover.html` were conditionally emitted (`{% if selected %}<span>...</span>{% endif %}`), then on the first GET render with no URL selection the span would not exist in the DOM at all — and HTMX would have nowhere to merge the post-Apply OOB fragment. By always emitting the span and toggling `d-none` for visibility, the merge target is permanently present; D-08's visual contract ("no badge when empty") is preserved because Bootstrap's `d-none` sets `display: none !important`, which is visually equivalent to omission.

After this fix, all three D-14 sub-clauses are demonstrable end-to-end on a single Apply click:
- (a) popover closes (existing `hx-on:click="bootstrap.Dropdown.getInstance(...).hide()"`)
- (b) trigger button count badge updates (this fix — picker_badges_oob)
- (c) single hx-post=/browse/grid fires with the new selection (gap-2 fix from Plan 04-05 — `form="browse-filter-form"`)

## Test Counts

| Suite | Before | After | Delta |
|------|-------|-------|-------|
| `tests/v2/test_browse_routes.py` | 14 | 16 | +2 |
| Full v2 suite (`tests/v2`) | 272 passed, 1 skipped | 274 passed, 1 skipped | +2 |
| `tests/v2/test_phase04_invariants.py` | 13 | 13 | 0 |

The 1 skipped test is the long-standing Plan 04-02 tombstone for the old Phase 1 `/browse` placeholder. No tests were modified or removed.

### New regression tests

**1. `test_post_browse_grid_emits_picker_badge_oob_blocks` (non-empty selection — smoke + behavior)**
- Posts `/browse/grid` with 2 platforms + 1 param
- Asserts both `picker-platforms-badge` and `picker-params-badge` spans appear in the response
- Asserts each carries `hx-swap-oob="true"`
- Asserts text content equals the integer count (`"2"` for platforms, `"1"` for params) — **non-tautological**: extracted via tag slicing, then string-equality check
- Asserts `d-none` is **not** present in either tag (visible per D-08 when count > 0)

**2. `test_post_browse_grid_picker_badge_zero_count_renders_hidden` (empty selection — stable target invariant)**
- Posts `/browse/grid` with empty body (Clear-all reset path, D-18)
- Asserts the empty-state alert renders in the grid block (sanity)
- Asserts both badge OOB spans STILL appear in the response — proves the always-emit contract (a regression to conditional emit would fail this)
- Asserts each carries `hx-swap-oob="true"` and `d-none` (visually hidden per D-08)
- Asserts text content equals `"0"` (count emitted even when hidden)

Both tests reuse the existing `_patch_cache` helper, `client` fixture, `_post_form_pairs` helper, and `MockDB` class verbatim. `_patch_cache` call count went from 15 → 17 (one per new test), confirming reuse. Zero new imports added at the top of the file.

## Confirmation: Production-code invariance (zero service / adapter / unrelated-template / static change)

```
$ git diff --quiet HEAD~2 -- \
    app_v2/services/browse_service.py \
    app_v2/services/cache.py \
    app_v2/services/ufs_service.py \
    app_v2/adapters/ \
    app_v2/templates/browse/_filter_bar.html \
    app_v2/templates/browse/_grid.html \
    app_v2/templates/browse/_warnings.html \
    app_v2/templates/browse/_empty_state.html \
    app_v2/static/js/popover-search.js \
    app_v2/static/css/app.css \
    tests/v2/test_phase04_invariants.py
$ echo $?
0
```

All services / adapters / unrelated Browse templates / static assets / Phase 4 invariant tests are byte-identical to pre-fix HEAD. The fix is confined to:
- 2 Browse templates (`_picker_popover.html` + `index.html`)
- 1 router (`browse.py` — block_names list + docstring)
- 1 test file (`test_browse_routes.py` — 2 appended tests)
- 2 planning docs (`04-HUMAN-UAT.md` + `04-06-SUMMARY.md`)

## Confirmation: gap-3 closed in 04-HUMAN-UAT.md

```
$ grep -A6 '^### gap-3' .planning/phases/04-browse-tab-port/04-HUMAN-UAT.md
### gap-3 — Trigger button count badge does not update after Apply (only after full page refresh)
status: resolved
reported: 2026-04-28T00:10:00Z
resolved: 2026-04-28T01:30:00Z
test_ref: 1
severity: minor
contract_ref: D-14(b)
```

`fix:` block populated with one paragraph documenting the picker_badges_oob OOB plumbing + always-emit-d-none pattern + the two regression tests + Plan 04-06 attribution + production-code invariance note. `## Summary` block updated: `gaps_open: 1 → 0`, `gaps_resolved: 2 → 3`. Other gap-3 sub-fields (`reported:`, `test_ref:`, `severity:`, `contract_ref:`, `symptom:`, `fix_direction:`) byte-identical. gap-2 entry byte-identical. Trailing gap-1 historical entry byte-identical.

## Task Commits

| Task | Description | Hash |
|------|-------------|------|
| 1 | Wire picker_badges_oob through template + router | `8e0dd00` |
| 2 | Add 2 regression tests for picker_badges_oob | `e0f7108` |
| 3 | Close gap-3 in UAT + write 04-06-SUMMARY.md | _pending — this commit_ |

**Plan metadata commit:** _pending — final commit covers SUMMARY + STATE + ROADMAP progress + REQUIREMENTS marks_

## Decisions Made

- **Candidate A (server-side OOB) over Candidate B (client-side JS in popover-search.js).** Server-side OOB matches the existing count_oob / warnings_oob pattern verbatim — codebase coherence, single source of truth (server count, not client checkbox-recount), TestClient-testable. Candidate B would have introduced a second source of truth that could drift; the regression test surface would have required JS execution which the existing 14 TestClient-based tests cannot exercise (CONTEXT.md "Defer Playwright until Phase 3+"). Candidate A is ~12-15 lines of template + 1 line of router; Candidate B is ~8 lines of JS — the size difference is negligible and the testability advantage is decisive.
- **Always-emit-with-d-none over conditional `{% if selected %}<span>{% endif %}` emit.** The conditional pattern was the ROOT cause of why HTMX could never merge into the badge — the span often did not exist in the DOM at all. Always-emit guarantees HTMX has a target across non-empty → empty round trips; the d-none toggle preserves D-08's 'no visible badge when empty' contract. The text content remains the integer count even when hidden, so HTMX's text replacement is always correct.
- **Reused `_patch_cache` + `client` fixture + `_post_form_pairs` helper verbatim.** No new test infrastructure; both new tests fit the same shape as Plan 04-04's recording-mock tests and Plan 04-05's gap-2 regression pair. Keeps test infra stable for Phase 5+.
- **Did not modify popover-search.js or app.css.** The fix is purely in the server-rendered template + router layer; no JS / CSS work is needed. This keeps the static-asset contract stable and the JS test surface (deferred to Phase 5+) unaffected.

## Deviations from Plan

None — plan executed exactly as written. Both Task 1 and Task 2 verification blocks passed on first run; Task 3 verification passed except for one awk-pattern sanity grep that is overly tight (the plan's `awk '/^### gap-3/,/^### |^$/'` regex stops at the first blank line because gap-3 has internal blank lines in `symptom:` and `fix_direction:` — verified via the equivalent `awk '/^### gap-3/{flag=1} /^### gap-1/{flag=0} flag' | grep '^fix: |$'` which confirms the fix block IS in the gap-3 section). No code or contract change.

The plan was unusually precise (gap-closure plans typically are). The macro header comment update, the OOB block structure, the test names, the `fix:` paragraph wording, and the `resolved:` timestamp format were all spelled out verbatim in the plan body — and all landed verbatim in the final files.

## Issues Encountered

None. All three tasks executed cleanly:
- **Task 1:** template + router edits applied; sanity-check greps all passed (badge id, OOB block, router block_names, gap-2 form-association preserved, broken hx-include not back); production-code invariance check returned 0; commit succeeded.
- **Task 2:** tests appended; targeted pytest on the two new tests passed; full file (16 tests) passed; full v2 suite (274 passed, 1 skipped) passed; commit succeeded.
- **Task 3:** UAT field-level edits applied; SUMMARY written; final invariance + grep verify pass succeeded.

## User Setup Required

None — no env vars, no external service config, no manual steps.

## Phase 4 Replay-Readiness

**Phase 4 ready for UAT replay** — D-14 fully demonstrable end-to-end on a single Apply click. The original UAT Test 1 reproduction steps from `04-HUMAN-UAT.md` should now produce the trigger button badge update on the FIRST Apply click without needing a full page refresh.

Manual reproduction steps:
```
.venv/bin/uvicorn app_v2.main:app --port 8000
# Open http://localhost:8000/browse — both badges hidden (count is 0)
# Tick 3 platforms in Platforms picker, click Apply
#   → trigger reads "Platforms 3" with count badge visible
# Tick 5 params in Parameters picker, click Apply
#   → trigger reads "Parameters 5" with count badge visible
# Click Clear-all
#   → both trigger badges hide; labels read just "Platforms" and "Parameters"
# Hard-refresh (F5) — badges remain hidden (state matches what server sees)
```

Phase 4 verification can be re-run:
```
/gsd-verify-phase 4    # all 3 ROADMAP success criteria fully demonstrable
/gsd-uat-phase 4       # UAT Test 1 should pass with badges updating on each Apply
```

Phase 4's three ROADMAP success criteria — filter swap (BROWSE-V2-01), caps mirror v1.0, URL round-trip — are all now demonstrable end-to-end with all D-14 sub-clauses (a, b, c) honored on a single round trip per Apply click.

## Threat Flags

None. The fix uses a well-established HTMX feature (`hx-swap-oob`) that has shipped in production for `count_oob` since Plan 04-03. No new attack surface introduced. The badge text is `{{ vm.selected_platforms | length }}` / `{{ vm.selected_params | length }}` — both integer values derived from the post-validation view-model. Jinja2 autoescape applies to the output. No user-controlled string flows into the OOB block; ids are static literals (`picker-platforms-badge`, `picker-params-badge`) — no id injection possible.

The threat-register entries from this plan's body (T-04-06-01..T-04-06-06) are all addressed:
- **T-04-06-01** (template refactor removes stable id / hx-swap-oob): mitigated by `test_post_browse_grid_emits_picker_badge_oob_blocks` — asserts both ids and both `hx-swap-oob="true"` attributes present
- **T-04-06-02** (always-emit-with-d-none replaced with conditional emit): mitigated by `test_post_browse_grid_picker_badge_zero_count_renders_hidden` — empty-selection assertion `id="picker-platforms-badge" in r.text` would fail on conditional emit
- **T-04-06-03** (block_names not extended in router): mitigated by Task 1's grep verification + Task 2's response-body assertion (block would not render → tests fail)
- **T-04-06-04** (information disclosure): accept — badge text is integer count of selection, no PII, no SQL, equivalent surface to existing count_oob
- **T-04-06-05** (cross-cutting regression): mitigated by `git diff --quiet HEAD~2 -- <list>` returning 0 + full v2 suite (274 passed) — Phase 4 invariants 13/13 pass
- **T-04-06-06** (OOB injection from a different element): accept — ids are template literals, no request-driven id derivation

Plan 04-05's gap-2 form-association mitigations (T-04-05-01..T-04-05-04) remain in place — Task 1's verification grep includes the gap-2 regression guard (`form="browse-filter-form"` present, broken `hx-include` absent).

## Self-Check: PASSED

- `app_v2/templates/browse/_picker_popover.html` modified — FOUND (`id="picker-{{ name }}-badge"` present; `class="badge bg-secondary ms-1{% if not selected %} d-none{% endif %}"` present; `aria-live="polite"` on the badge; macro header docstring extended with the gap-3 closure note; `form="browse-filter-form"` still on popover-apply-btn; broken `hx-include="#browse-filter-form input:checked"` absent)
- `app_v2/templates/browse/index.html` modified — FOUND (`{% block picker_badges_oob %}` declared after `{% block warnings_oob %}`; emits two `<span>` elements with ids `picker-platforms-badge` and `picker-params-badge`, each with `hx-swap-oob="true"` and the same class+d-none pattern as the in-place trigger badge)
- `app_v2/routers/browse.py` modified — FOUND (`block_names` list now contains `"picker_badges_oob"` as the 4th element; docstring `Returns` sentence mentions the new block)
- `tests/v2/test_browse_routes.py` modified — FOUND (16 test functions; 2 new tests appended; existing 14 byte-identical; section header comment for gap-3 added)
- `.planning/phases/04-browse-tab-port/04-HUMAN-UAT.md` modified — FOUND (gap-3: status open → resolved; resolved: 2026-04-28T01:30:00Z; fix: paragraph populated; Summary gaps_open 1 → 0, gaps_resolved 2 → 3; gap-2 byte-identical; trailing gap-1 historical block byte-identical)
- `.planning/phases/04-browse-tab-port/04-06-SUMMARY.md` — being written now (this file)
- Commit `8e0dd00` (Task 1 — picker_badges_oob template + router wiring) — FOUND in `git log --oneline`
- Commit `e0f7108` (Task 2 — 2 regression tests) — FOUND in `git log --oneline`

---
*Phase: 04-browse-tab-port*
*Plan: 06 (gap-closure for gap-3)*
*Completed: 2026-04-28*
