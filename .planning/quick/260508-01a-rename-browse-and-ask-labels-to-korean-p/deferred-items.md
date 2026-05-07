# Deferred Items — Quick 260508-01a

Items discovered during execution that are out of scope for this quick task.
Tracked here per scope-boundary rule (only auto-fix issues directly caused by
the current task's changes).

## Pre-existing test failure (NOT caused by this task)

**Test:** `tests/v2/test_phase04_uif_components.py::test_showcase_inherits_topbar`

**Failure:**
```
assert ">Yhoon Dashboard<" in body
AssertionError
```

**Root cause:** The topbar wordmark literal in
`app_v2/templates/_components/topbar.html` line 16 currently reads
`<span>Platform Dashboard V1</span>`. The test pins the older `"Yhoon
Dashboard"` literal that quick task 260507-mmv shipped. A subsequent (pre-this-task)
edit changed the wordmark to "Platform Dashboard V1" but did not update this
test in lockstep.

**Evidence it predates this task:** Stashing all four files this task touches
and running the test against the parent commit (`c8c962b`) reproduces the same
failure. STATE.md also flags this exact test as pre-existing red in the Phase
04 P05 entry: *"the 2 failing tests in test_main.py + test_phase04_uif_components.py
predate this task — caused by f32cac1 topbar rebrand"*.

**Why deferred:** The fix touches the topbar wordmark contract — out of scope
for a quick task whose stated boundary is *"page heading text on Browse and
Ask pages, plus any tests that pin those headings"*. Should be addressed in a
separate quick task that decides the canonical wordmark literal (`"Yhoon
Dashboard"` vs `"Platform Dashboard V1"`) and synchronizes the test.

**Recommended follow-up quick task title:** `Reconcile topbar wordmark
literal with test_phase04_uif_components.py::test_showcase_inherits_topbar`.
