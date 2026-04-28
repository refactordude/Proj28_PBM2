---
phase: 05-overview-redesign
plan: 01
subsystem: ui
tags: [docs, jinja, macro, picker-popover, byte-stable, prep, d-ov-06]

# Dependency graph
requires:
  - phase: 04-browse-tab-port
    provides: picker_popover Jinja macro + popover-search.js (D-15b auto-commit pattern)
provides:
  - PROJECT.md "Overview redesign (v2.0)" Active subsection (closes CONTEXT.md upstream-edit-3)
  - picker_popover macro with 3 additive kwargs (form_id, hx_post, hx_target) — single macro shared between Browse (Phase 4) and Overview (Phase 5) without forking
affects: [05-02-frontmatter-parser, 05-03-overview-grid-service, 05-04-routes, 05-05-templates, 05-06-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-page Jinja macro reuse via additive kwarg defaults preserving byte-stability for existing callers (D-OV-06)"
    - "Phase invariant tests assert on RENDERED macro output (not template source) when source uses Jinja substitutions — defense-in-depth that proves contract holds end-to-end"

key-files:
  created: []
  modified:
    - ".planning/PROJECT.md (Overview redesign (v2.0) Active subsection added)"
    - "app_v2/templates/browse/_picker_popover.html (macro signature + body — 3 additive kwargs)"
    - "tests/v2/test_phase04_invariants.py (D-15b marker assertions migrated from template-source grep to rendered-output grep)"

key-decisions:
  - "Macro kwargs hx_post and hx_target also parameterized (not just form_id) — without them, Phase 5 callers on /overview would still POST to /browse/grid, producing wrong server-side dispatch. Plan body explicitly mandates this (D-OV-06 expanded)."
  - "Phase 4 invariant test assertions migrated from template-source grep to rendered-macro grep — preserves D-15b contract enforcement while accommodating the parameterized macro. Defense-in-depth strengthened: now proves macro defaults match the Phase 4 contract end-to-end (template + Jinja2 binding)."
  - "Macro docstring comment block left intact — it still mentions browse-filter-form / browse/grid / browse-grid as illustrative examples. Updating it was explicitly out-of-scope per plan (byte-minimal edit). Only runtime markup changed."

patterns-established:
  - "D-OV-06 cross-page macro reuse: a single Jinja macro can serve multiple pages by parameterizing the page-specific identifiers (form id, HTMX endpoint, HTMX target) as kwargs with defaults that preserve the original caller's behavior. Future v2.0 macros (e.g., a future shared filter-bar) can follow the same pattern."
  - "Test-on-rendered-output for templates with Jinja substitutions: when a template invariant must guard a contract that is satisfied by Jinja substitution at render-time (not at template authorship), the test should render the macro/template with the contract's reference inputs and assert on the output. Pure template-source grep is brittle to refactors that introduce Jinja variables."

requirements-completed: [OVERVIEW-V2-03]

# Metrics
duration: 6min
completed: 2026-04-28
---

# Phase 5 Plan 01: Overview Redesign Prep — PROJECT.md subsection + picker_popover macro parameterization Summary

**Closed CONTEXT.md upstream-edit-3 (PROJECT.md gap) and parameterized the Phase 4 picker_popover Jinja macro with 3 additive kwargs (form_id, hx_post, hx_target) so Plan 05-05's Overview filter bar can reuse the same macro byte-stably for Browse and on its own form id + HTMX endpoints for Overview — no fork.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-04-28T06:44:38Z
- **Completed:** 2026-04-28T06:50:11Z
- **Tasks:** 2
- **Files modified:** 3 (PROJECT.md, _picker_popover.html, test_phase04_invariants.py)

## Accomplishments

- PROJECT.md Active section now has a 6-bullet "Overview redesign (v2.0)" subsection placed correctly between "Browse — v2.0" Validated block and "Ask carry-over (v2.0)" Active block — CONTEXT.md upstream-edit-3 closed.
- picker_popover macro signature is now `picker_popover(name, label, options, selected, form_id="browse-filter-form", hx_post="/browse/grid", hx_target="#browse-grid")`. All 3 hardcoded Browse-tab identifiers in the runtime markup (`form="browse-filter-form"`, `hx-post="/browse/grid"`, `hx-target="#browse-grid"`, `hx-include="#browse-filter-form"`) replaced with Jinja2 substitutions. Defaults preserve Phase 4 byte-stability.
- Dual-render Jinja smoke test confirmed end-to-end: Phase 4 callers produce byte-identical output via defaults; Phase 5 callers can pass `form_id='overview-filter-form'`, `hx_post='/overview/grid'`, `hx_target='#overview-grid'` to get the Overview-tab-correct rendered HTML.
- Full v2 test suite (275 passed, 1 skipped) — zero regression vs pre-edit baseline (also 275 passed, 1 skipped). All 30 Phase 4 tests (test_browse_routes.py + test_phase04_invariants.py) pass byte-stably.

## Task Commits

1. **Task 1: Add Overview redesign (v2.0) subsection to PROJECT.md** — `cbef66f` (docs)
2. **Task 2: Parameterize picker_popover macro for cross-page reuse (D-OV-06)** — `29fa7b6` (feat) — includes the Rule-1 invariant test fix

## Files Created/Modified

- `.planning/PROJECT.md` — added 8-line "Overview redesign (v2.0)" Active subsection (6 bullets covering OVERVIEW-V2-01..06)
- `app_v2/templates/browse/_picker_popover.html` — macro signature gained 3 additive kwargs; macro body uses `{{ form_id }}`, `{{ hx_post }}`, `{{ hx_target }}`, `#{{ form_id }}` substitutions in 4 places (1 macro signature + 1 ul opening tag with 3 attrs + 1 checkbox form= attr)
- `tests/v2/test_phase04_invariants.py` — `test_picker_popover_uses_d15b_auto_commit_pattern` markers 2/3/4b migrated from template-source grep to rendered-macro grep; renders the macro with Phase 4 default kwargs (`picker_popover("x", "X", ["a","b"], ["a"])`) and asserts the rendered `<ul ...>` tag carries `hx-post="/browse/grid"`, `hx-target="#browse-grid"`, `hx-include="#browse-filter-form"`. Test intent (D-15b contract) preserved; defense-in-depth strengthened.

## Diff: macro signature change

**Before:**
```jinja
{% macro picker_popover(name, label, options, selected) %}
```

**After:**
```jinja
{% macro picker_popover(name, label, options, selected, form_id="browse-filter-form", hx_post="/browse/grid", hx_target="#browse-grid") %}
```

**Body changes (3 substitutions, all in the macro body):**

| Line context | Before | After |
|---|---|---|
| `<ul ...>` hx-post | `hx-post="/browse/grid"` | `hx-post="{{ hx_post }}"` |
| `<ul ...>` hx-target | `hx-target="#browse-grid"` | `hx-target="{{ hx_target }}"` |
| `<ul ...>` hx-include | `hx-include="#browse-filter-form"` | `hx-include="#{{ form_id }}"` |
| `<input type="checkbox" ...>` form attr | `form="browse-filter-form"` | `form="{{ form_id }}"` |

## Decisions Made

- **Phase 4 invariant test migrated from template-source grep to rendered-macro grep** — see Deviations below for full rationale. This decision establishes a Phase-5+ pattern for any future invariant guarding a contract satisfied by Jinja substitution.
- **Macro docstring left untouched** — per plan ("updating the comment is optional — only the runtime markup must change"). Still references browse-filter-form / browse/grid / browse-grid as illustrative examples; the runtime markup is the source of truth.
- **All 3 kwargs (not just form_id) parameterized** — without `hx_post` and `hx_target`, Phase 5 picker checkboxes on /overview would POST to `/browse/grid`. Plan body explicitly mandated all 3 (D-OV-06 expanded discussion).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug / Rule 3 - Blocking] Phase 4 invariant test markers 2/3/4b grep template source for literals that no longer exist after macro parameterization**

- **Found during:** Task 2 verification — `pytest tests/v2/test_phase04_invariants.py -x -q` failed on `test_picker_popover_uses_d15b_auto_commit_pattern`
- **Issue:** Markers 2 (`hx-post="/browse/grid"`), 3 (`hx-target="#browse-grid"`), and 4b (`hx-include="#browse-filter-form"`) read the template source via `_read("templates", "browse", "_picker_popover.html")` and asserted the literal strings `hx-post="/browse/grid"`, etc., were present. After Task 2's edit, the template source contains `hx-post="{{ hx_post }}"`, `hx-target="{{ hx_target }}"`, `hx-include="#{{ form_id }}"` — Jinja substitution placeholders, NOT literals. The plan EXPLICITLY required Phase 4 tests to pass (acceptance criterion: `pytest tests/v2/test_browse_routes.py tests/v2/test_phase04_invariants.py -x -q` exits 0). This is a contradictory instruction set — Task 2 mandates the parameterization that breaks the source-grep test that Task 2 also requires to pass.
- **Fix:** Migrated markers 2/3/4b from template-source grep to **rendered-macro grep**. Inside the test, instantiate a Jinja2 `Environment` pointing at `app_v2/templates`, render `picker_popover("x", "X", ["a","b"], ["a"])` via a wrapper template using `{% from "browse/_picker_popover.html" import picker_popover %}`, then run the same `<ul ...>` regex on the rendered output and assert `hx-post="/browse/grid"`, `hx-target="#browse-grid"`, `hx-include="#browse-filter-form"` literals (now produced by the kwarg defaults). Marker 4 (`delay:250ms`) untouched — that's still a template literal. Marker 5 (`data-bs-auto-close="outside"`) and markers 1, 6, 7, 8, 9, 10 untouched.
- **Files modified:** `tests/v2/test_phase04_invariants.py`
- **Verification:** `pytest tests/v2/test_browse_routes.py tests/v2/test_phase04_invariants.py -x -q` → 30 passed; `pytest tests/v2/ -q` → 275 passed, 1 skipped (zero regression vs baseline).
- **Committed in:** `29fa7b6` (Task 2 commit)
- **Why this preserves the D-15b contract:** The original test's stated intent was to enforce that the picker_popover macro produces the auto-commit-with-debounce HTMX wiring on the `<ul class="popover-search-list">`. The migrated test still proves exactly that — and it's strictly stronger now: the rendered-output grep proves the contract holds end-to-end (template authorship + Jinja substitution + default kwargs all work together to produce the contract output) rather than only proving the template source contains the right literal. If a future refactor accidentally broke the kwarg defaults (e.g., `form_id="overview-filter-form"` as the default), the new test would catch it. The old test would not.

---

**Total deviations:** 1 auto-fixed (Rule 1 + Rule 3 — plan-internal contradiction between mandated parameterization and Phase 4 test stability)
**Impact on plan:** Auto-fix necessary for Task 2 acceptance criterion to pass. Test intent strengthened, not weakened. Zero scope creep — only the 3 marker assertions inside one test function changed.

## Issues Encountered

- None beyond the documented Rule-1/3 deviation.

## Phase 5 Reuse Verification (Plan 05-05 readiness)

The plan's "Phase 5 will call" example was directly tested as part of the dual-render smoke:

```jinja
{{ picker_popover('status', 'Status', filter_options['status'], selected_filters['status'],
                  form_id='overview-filter-form',
                  hx_post='/overview/grid',
                  hx_target='#overview-grid') }}
```

Renders to (verified by `phase-5-callable OK`):
- `form="overview-filter-form"` on each checkbox
- `hx-post="/overview/grid"` on the `<ul>`
- `hx-target="#overview-grid"` on the `<ul>`
- `hx-include="#overview-filter-form"` on the `<ul>`

Plan 05-05 (templates) can import `from "browse/_picker_popover.html" import picker_popover` and call it with the Overview-tab kwargs. No macro fork needed. D-OV-06 ("shared not forked") is now physically enforceable — Plan 05-06 (invariants) will add a static-analysis test that asserts `from "browse/_picker_popover.html" import picker_popover` is the ONLY import path for the macro and no `app_v2/templates/overview/_picker_popover.html` file exists.

## Next Phase Readiness

- **Plan 05-02** (read_frontmatter parser) — independent of this plan; no blocker.
- **Plan 05-05** (templates) — DIRECT consumer of this macro change. Ready to call `picker_popover(..., form_id="overview-filter-form", hx_post="/overview/grid", hx_target="#overview-grid")` immediately.
- **Plan 05-06** (invariants) — will assert "shared not forked" via a test that confirms `app_v2/templates/overview/_filter_bar.html` imports from `browse/_picker_popover.html` AND no `overview/_picker_popover.html` exists. The macro parameterization landed here makes this contract physically possible.

---
*Phase: 05-overview-redesign*
*Completed: 2026-04-28*

## Self-Check: PASSED

Verified files exist:
- FOUND: .planning/PROJECT.md (modified — Overview redesign subsection present, `grep -q "Overview redesign (v2.0)"` succeeds)
- FOUND: app_v2/templates/browse/_picker_popover.html (modified — macro signature `picker_popover(name, label, options, selected, form_id="browse-filter-form", hx_post="/browse/grid", hx_target="#browse-grid")` present)
- FOUND: tests/v2/test_phase04_invariants.py (modified — marker assertions 2/3/4b now render the macro and grep rendered output)

Verified commits exist:
- FOUND: cbef66f (Task 1: docs(05-01): add Overview redesign (v2.0) subsection to PROJECT.md)
- FOUND: 29fa7b6 (Task 2: feat(05-01): parameterize picker_popover macro for cross-page reuse (D-OV-06))

Verified test suite green:
- 30/30 Phase 4 regression tests pass (test_browse_routes.py + test_phase04_invariants.py)
- 275/276 v2 tests pass, 1 skipped (zero regression vs pre-edit baseline of 275 pass / 1 skip)
