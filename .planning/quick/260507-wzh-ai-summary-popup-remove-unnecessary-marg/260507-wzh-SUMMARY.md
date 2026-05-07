---
task: 260507-wzh
type: quick
status: complete
description: AI Summary popup — remove dead space above h1 heading
one_liner: "Add `.markdown-content > :first-child { margin-top: 0 }` to zero the dead space above the AI Summary modal's h1 (and any first child) inside `.markdown-content` containers."
files_modified:
  - app_v2/static/css/app.css
files_created: []
commits:
  - hash: bfeb3c6
    note: "Code change bundled here (under quick-260507-wf6) — see Deviations below."
duration_minutes: 4
completed: 2026-05-07
---

# Quick Task 260507-wzh: AI Summary popup — Remove Dead Space Above h1 Summary

## Root Cause

`app_v2/static/css/app.css` (line 132 pre-fix) set `margin-top: 1.5em` (~36px) on `.markdown-content h1`. The AI Summary's markdown response typically begins with `# Title` (per `app_v2/data/summary_prompt.py` and `jv_summary_prompt.py`), so pandoc/markdown rendered the `<h1>` as the **first child** of `<article class="markdown-content">` (see `app_v2/templates/summary/_success.html:18`). With nothing above it, the 1.5em top margin became a pure dead band between the modal's `.modal-body` natural padding and the visible heading. The margin is normally meant to space an h1 *away from preceding paragraphs* in long-form content — when h1 is the first child it serves no purpose and reads as broken vertical rhythm.

## Fix

Single additive CSS rule inserted between the base `.markdown-content` rule and the `h1` rule:

```css
/* 260507-wzh — kill dead space above the first rendered child (typically h1 in
   AI Summary popups). The h1/h2/h3 top margins below are designed to space
   headings AWAY from preceding paragraphs; when a heading is the first child
   they collapse into a visible gap above the modal/panel content. */
.markdown-content > :first-child { margin-top: 0; }
```

**Why universal `:first-child` (not just `h1:first-child`):** the LLM may occasionally start its summary with `## H2` or a paragraph instead of `# H1`. The universal selector handles every variant for free.

**Why child-combinator (`>`):** scopes the zero-margin to the *direct* first child of `.markdown-content`, avoiding side effects on nested `<li>` first children inside `<ul>`.

**Why additive (no edits to existing h1/h2/h3 rules):** preserves the correct behaviour for the *non-first* case (heading after a paragraph) — those `1.5em` / `1.4em` / `1.2em` top margins still apply to every heading that is **not** the first child.

## Files Changed

| File | Change |
|------|--------|
| `app_v2/static/css/app.css` | +5 lines (1 CSS rule + 4-line comment) at line 132–136 |

## Commit

| Task | Commit | Note |
|------|--------|------|
| 1 | `bfeb3c6` | Bundled with quick-260507-wf6 — see Deviations |

## Verification

**Automated grep checks (per plan §verify):**
- `grep -n "first-child { margin-top: 0" app_v2/static/css/app.css` → **`136:.markdown-content > :first-child { margin-top: 0; }`** ✓
- `grep -c "margin-top: 1.5em" app_v2/static/css/app.css` → **`1`** (h1 rule byte-stable) ✓

**Test suite** (`pytest tests/v2 -q`): **592 passed, 5 skipped, 2 pre-existing failures** unrelated to this change. The two failures (`test_get_root_contains_three_tab_labels`, `test_phase04_uif_components::test_showcase_inherits_topbar`) reproduce on a clean tree (verified via `git stash` cycle) and stem from the topbar rebrand drift (`Yhoon Dashboard` literal); they are not caused by this CSS-only change. Out of scope per the GSD scope-boundary rule — logged as pre-existing for the next visit.

**Manual visual check** (per plan §verification, step 2–4): not run by the executor (would require a live `uvicorn` smoke); covered by future browser UAT on the `/overview` and `/joint_validation` AI-Summary popups.

## Deviations from Plan

### 1. [Rule 3 — Already-applied code] Code change found pre-applied in `bfeb3c6`

**Found during:** Task 1, before staging.

**Issue:** When checking `git diff app_v2/static/css/app.css` after applying the Edit, the diff was empty. Investigation showed the exact 4-line comment + `:first-child` rule — including the `260507-wzh` marker — was already present in `HEAD`, having been committed as part of an unrelated topbar fix in commit `bfeb3c6` (titled `fix(topbar): make .topbar position: sticky [quick-260507-wf6]`). The `git show` of that commit reveals two hunks: the intended `position: sticky` topbar block AND the wzh markdown-content first-child rule, bundled into one commit.

**How this happened:** The wzh CSS edit was made against the working tree before quick-260507-wf6 was committed; the wf6 commit captured both modifications because they touched neighboring rules in the same file.

**Fix:** None needed — the file content is exactly what the wzh plan specifies. No new commit was created (would be empty). The code-shipped status of this task is therefore tied to commit `bfeb3c6` rather than a dedicated `quick-260507-wzh` commit.

**Files modified:** none in this run (already-applied).

### Auth Gates

None.

### Deferred Issues

- **Pre-existing test failures** (`test_main.py::test_get_root_contains_three_tab_labels`, `test_phase04_uif_components.py::test_showcase_inherits_topbar`): both assert on the literal `>Yhoon Dashboard<` topbar wordmark, which has since been renamed to `Platform Dashboard V1` in commit `f32cac1`. The test suite was not updated in lockstep with that rename. Out of scope for this CSS-only quick task. Logged for the next quick task or a follow-up `tests-rebrand` cleanup.

## Self-Check: PASSED

- File `app_v2/static/css/app.css` exists and contains the rule at line 136 (`grep` verified).
- Existing `margin-top: 1.5em` h1 rule byte-stable (count = 1, `grep -c` verified).
- Code commit `bfeb3c6` exists in `git log` (verified via `git log --all --oneline -S ".markdown-content > :first-child" -- app_v2/static/css/app.css`).
- No new files created (none claimed).
- Plan's §success_criteria met: AI Summary popup layout will sit flush below modal-header chrome (visual UAT deferred); 1 file touched, 1 rule added, no other rules modified.
