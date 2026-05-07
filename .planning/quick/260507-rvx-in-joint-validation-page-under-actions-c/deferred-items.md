# Deferred Items — quick task 260507-rvx

Pre-existing failures discovered while running `tests/v2/` after Task 1+2 edits.
Confirmed pre-existing by re-running with the working tree stashed (failures
reproduce on clean HEAD `b2215b421c63b1de7e166d1bf8852b0072cbc775` per the
plan's clean-baseline assertion).

These are **out of scope** for this quick task per the GSD scope-boundary rule
(only auto-fix issues directly caused by the current task's changes; log
unrelated failures and continue).

## 1. `test_joint_validation_invariants.py::test_jv_filter_bar_uses_picker_popover_macro_unmodified`
- **File:** `app_v2/templates/overview/_filter_bar.html`
- **Reason:** Test asserts `_filter_bar.html` invokes `picker_popover(` >= 6
  times (D-JV-11). File now contains 5 invocations, presumably because a
  separate task (likely quick-260507-rmj — "ditch Status and End columns")
  reduced the JV facet count. Test is stale w.r.t. that change.
- **Fix:** Update assertion to expected count, OR restore the dropped picker.
  Owner: whoever owns 260507-rmj.

## 2. `test_phase02_invariants.py::test_overview_filter_bar_six_picker_calls`
- **File:** `app_v2/templates/overview/_filter_bar.html`
- **Reason:** Same root cause as above — test asserts exactly 6
  `picker_popover(` calls (D-UI2-09); file has 5.
- **Fix:** Update Phase 02 invariant test to match the new JV facet count.

## 3. `test_jv_pagination.py::test_filter_options_built_from_all_rows_not_paged` (transient)
- **Trigger:** Failed once during a full-suite run; passes in isolation and
  passes in re-runs. Almost certainly an ordering/fixture-state side effect
  (likely the 6 new untracked `content/joint_validation/3193868*` fixture
  folders in the working tree affecting filter option lists when this test
  runs after a state-mutating sibling).
- **Fix:** None required from this quick task. Worth a small investigation
  whether the fixture folders should be `.gitignore`d or moved to a tmp dir
  by an autouse fixture, but unrelated to the Actions-column UI tweak.

None of these touch `_grid.html`, `app.css`, or the Actions column.
