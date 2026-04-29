---
phase: 02-overview-tab-filters
fixed_at: 2026-04-25T12:30:00Z
review_path: .planning/phases/02-overview-tab-filters/02-REVIEW.md
iteration: 2
findings_in_scope: 1
fixed: 1
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report (Iteration 2)

**Fixed at:** 2026-04-25 (iteration 2)
**Source review:** `.planning/phases/02-overview-tab-filters/02-REVIEW.md`
**Iteration:** 2

**Summary:**
- Findings in scope: 1 (Critical: 0, Warning: 1)
- Fixed: 1
- Skipped: 0
- Info findings (10 total: IN-01..IN-10) were excluded from scope (`fix_scope=critical_warning`).

Iteration 2 addresses the single regression (WR-01R) introduced by the
iteration-1 fix for WR-01. All other Warnings from iteration 1 (WR-02, WR-03,
WR-04) remain resolved as documented in iteration 1's report — the re-review
confirmed each via commit lookup.

Full test suite re-run after the fix: **290 passed**, no regressions.

## Fixed Issues

### WR-01R: Visible `<summary>` badge `filter-count-summary` is never updated by filter responses (regression from WR-01 fix)

**Files modified:** `app_v2/templates/overview/index.html`, `app_v2/routers/overview.py`
**Commit:** `106ac34`
**Applied fix:**

The iteration-1 fix for WR-01 broke the user-facing filter badge: it renamed
the visible badge in `<summary>` to `id="filter-count-summary"` and kept the
OOB-swap carrier (`id="filter-count-badge"`) inside the `entity_list` block,
which is rendered into `<ul id="overview-list">`. Result: the OOB swap updated
a span hidden inside the `<ul>` while the user-visible badge in `<summary>`
stayed at its initial render value forever.

Adopted the cleanest variant of the recommended fix: the visible summary
badge IS the OOB swap target. Concrete changes:

1. **`templates/overview/index.html`** — wrapped the visible badge + "Clear
   all" link inside `<summary>` in a new `{% block filter_oob %}` block. The
   badge has `id="filter-count-badge"` and `hx-swap-oob="true"`; the link has
   `id="clear-filters-link"` and `hx-swap-oob="true"`. Removed the duplicate
   OOB span from inside the `entity_list` block (it lived inside `<ul>`,
   producing invalid HTML for the OOB swap target). Both elements are now
   single-instance in the DOM, so HTML id uniqueness is preserved.

2. **`routers/overview.py`** — `filter_overview` and `reset_filters` now
   render `block_names=["filter_oob", "entity_list"]` instead of
   `block_name="entity_list"`. `Jinja2Blocks.TemplateResponse` natively
   supports `block_names=[...]` (concatenates renderings in order). The
   filter-OOB pair appears in the response BEFORE the entity rows, matching
   the structural assertion suggested in IN-09 of the re-review.

3. **HTML structural correctness:**
   - The OOB target lives inside `<summary>` (NOT inside `<ul id="overview-list">`),
     which is valid HTML and makes the swap update the visible element.
   - On initial GET / render, `hx-swap-oob="true"` is harmless — htmx only acts
     on htmx-triggered responses, never on the first browser parse.
   - Both filter and reset routes emit the OOB pair, so applying any filter
     updates the badge AND switches the "Clear all" link visibility, and
     resetting hides both via `d-none` (count=0 branch).

**Test impact:**

All existing test assertions still hold by construction:
- `id="filter-count-badge"` and `hx-swap-oob="true"` continue to appear in
  filter / reset fragment responses (now from `filter_oob` block, not
  `entity_list`).
- The `<span\s+id="filter-count-badge"[^>]*>\s*(\d+)\s*</span>` regex still
  matches the OOB span (the count digit is unchanged).
- `<nav class="navbar` / `<html` absence checks still pass — fragment
  responses still render only blocks, never the base shell.
- `d-none` presence on count=0 still holds because both badge and clear-link
  in the new `filter_oob` block use the same `active_filter_count == 0`
  condition.

`pytest tests/ -x` reports **290 passed**.

**Logic-bug note:** This fix changes runtime DOM behavior in a way the unit
tests cannot directly verify (no htmx-aware end-to-end harness yet — IN-09
flagged this gap). The structural invariant the fix enforces (OOB span lives
outside `<ul id="overview-list">`) is testable via the regex assertion
suggested in IN-09 but adding that test is itself out of scope for the fixer
phase. The fix is verified by reading the rendered HTML structure and by
the 290 existing tests continuing to pass.

---

_Fixed: 2026-04-25 (iteration 2)_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
