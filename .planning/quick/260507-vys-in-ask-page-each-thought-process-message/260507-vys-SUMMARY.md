---
phase: quick-260507-vys
plan: 01
subsystem: ask-chat-ui
tags: [css, ui, ask, chat, pills]
dependency_graph:
  requires:
    - "Quick 260504-30t (chat tool-call/result pills exist in Ask transcript)"
  provides:
    - "Chat tool-call and tool-result pills stack vertically (each on own line) in closed state"
    - "Closed pills retain chip aesthetic (rounded, content-sized via width: fit-content)"
    - "[open] expanded pills retain full-width card aesthetic via width: auto override"
  affects:
    - "app_v2/static/css/app.css"
tech_stack:
  added: []
  patterns:
    - "display: block + width: fit-content for stack-vertical chip layout"
    - "[open] state width: auto override to defeat width: fit-content from base rule"
key_files:
  created: []
  modified:
    - "app_v2/static/css/app.css"
decisions:
  - "Used display: block + width: fit-content (not flex column wrap) — minimal CSS surface, no parent-container changes, no risk to .chat-events flex/grid behavior"
  - "Added width: auto on [open] to defeat inheritance of width: fit-content (CSS only re-declares display in the [open] rule, not width — without width: auto, expanded cards would awkwardly hug content)"
metrics:
  duration: 4min
  tasks: 1
  files: 1
  completed: "2026-05-07"
---

# Quick 260507-vys: Stack Ask Chat Pills Vertically Summary

CSS-only fix to stack tool-call and tool-result pills on their own lines in the Ask transcript, replacing the previous horizontal-jumble layout (`▸ inspect_schema({}) ▸ inspect_schema ok ▸ get_distinct_values(...) ...`) while preserving chip aesthetic and the existing `[open]` expanded-card state.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Stack chat pills vertically (4 surgical CSS edits) | `7163edc` | `app_v2/static/css/app.css` |

## What Changed

Four targeted edits to `app_v2/static/css/app.css`:

1. `.chat-pill-tool-call` (closed, ~line 581): `display: inline-block` → `display: block; width: fit-content;`
2. `.chat-pill-tool-call[open]` (~line 595): added `width: auto;` after `display: block;`
3. `.chat-pill-tool-result-ok, .chat-pill-tool-result-rejected` (closed, ~line 614): `display: inline-block` → `display: block; width: fit-content;`
4. `.chat-pill-tool-result-ok[open], .chat-pill-tool-result-rejected[open]` (~line 629): added `width: auto;` after `display: block;`

Net diff: `1 file changed, 6 insertions(+), 2 deletions(-)`.

## Verification

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `grep -E "\.chat-pill-tool-(call\|result-(ok\|rejected))[^{]*\{[^}]*inline-block"` | 0 | 0 | PASS |
| `grep -c "width: auto;"` | 2 | 2 | PASS |
| `.chat-text-delta` `display:` rules | 0 (still inline span) | 0 | PASS |
| `.chat-thought` byte-stable | unchanged | unchanged | PASS |
| `.chat-final-card`, `.chat-summary-callout` byte-stable | unchanged | unchanged | PASS |
| Ask/chat tests (`-k "ask or chat"`) | 78 chat-relevant tests pass | 78 passed | PASS |

## Deviations from Plan

None — plan executed exactly as written. All 4 surgical edits landed; no auto-fixes (Rules 1-3) needed.

## Out-of-Scope Findings (Logged, Not Fixed)

The branch had pre-existing concurrent modifications from sibling quick task `260507-w7h` (browse highlight toggle) that introduced 3 unrelated test failures:

- `tests/v2/test_browse_routes.py::test_get_browse_without_highlight_renders_no_cell_highlight` — browse highlight markup assertion (sibling task in-progress)
- `tests/v2/test_main.py::test_get_root_contains_three_tab_labels` — top-nav literal "Browse" missing (template work-in-progress)
- `tests/v2/test_phase04_uif_components.py::test_showcase_inherits_topbar` — top-nav literal "Yhoon Dashboard" missing (template work-in-progress)
- `tests/v2/test_joint_validation_routes.py::test_browse_and_ask_tabs_unaffected` — DB engine `NoneType` (browse-side issue)

None of these touch chat-pill CSS. Per scope boundary in deviation rules, these were NOT fixed in this task — they belong to the sibling quick task's surface area. Documented here for awareness.

## Self-Check: PASSED

- Commit `7163edc` exists in `git log`: FOUND
- Modified file `app_v2/static/css/app.css`: FOUND (only file in commit)
- Diff scope respected: only chat-pill rules touched (4 edits across lines 581-634)
- Constraint compliance: `.chat-thought`, `.chat-text-delta`, `.chat-final-card`, `.chat-summary-callout` byte-stable
- `[open]` expanded state restored via `width: auto` (verified by grep count = 2)
