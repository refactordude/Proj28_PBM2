---
phase: quick-260507-wf6
plan: 01
subsystem: joint-validation, topbar
tags: ui, css, sticky, iframe, gutter
requirements:
  - WF6-01  # Iframe gets adequate horizontal margin/gutter (no panel-body p-0)
  - WF6-02  # Topbar is sticky so the Joint Validation tab is reachable while scrolling
key-files:
  modified:
    - app_v2/templates/joint_validation/detail.html
    - app_v2/static/css/app.css
metrics:
  completed: 2026-05-07
  duration: ~5min
  tasks: 2
  commits: 2
---

# Quick 260507-wf6: Joint Validation Iframe Gutter + Sticky Topbar Summary

Two atomic UI fixes on the Joint Validation detail page: restored horizontal gutter around the embedded Confluence iframe by removing the `p-0` Bootstrap utility from its `.panel-body` wrapper, and pinned the topbar to the viewport via `position: sticky` so the JV / Browse / Ask tabs stay reachable while scrolling the 80vh iframe page.

## Fixes

**1. Iframe gutter (WF6-01) — commit `2c86059`:** Removed `p-0` utility from the iframe-wrapping `.panel-body` div in `app_v2/templates/joint_validation/detail.html` line 63. The `.panel-body` rule's default `padding: 26px 32px` (app.css:58) now applies, giving the iframe ~32px horizontal breathing room inside the rounded panel — matching the JV properties table directly above (which already uses bare `class="panel-body"`).

**2. Sticky topbar (WF6-02) — commit `bfeb3c6`:** Added three declarations to the existing `.topbar` rule in `app_v2/static/css/app.css` (lines 795-816): `position: sticky; top: 12px; z-index: 50`. `top: 12px` matches the rule's existing `margin: 12px 16px 0` so the pill re-settles into the same spot it occupied at scroll-top (no jank). `z-index: 50` sits above panels (no z-index) and below Bootstrap dropdown/modal layers (1000+); `.table-sticky-corner`'s 1/2/3 z-index ladder is in its own table-scoped stacking context so no collision.

## Test count before/after

| Metric | Before edits | After edits |
| ------ | ------------ | ----------- |
| `tests/v2` total | 599 | 599 |
| Passing | 592 | 592 |
| Failing | 2 (pre-existing, unrelated) | 2 (pre-existing, unrelated) |
| Skipped | 5 | 5 |

The two pre-existing failures (`test_main.py::test_get_root_contains_three_tab_labels` and `test_phase04_uif_components.py::test_showcase_inherits_topbar`) assert on the legacy `>Yhoon Dashboard<` brand wordmark literal. Commit `f32cac1` ("topbar: rename labels — Yhoon Dashboard → Platform Dashboard V1") renamed the wordmark in the template but did not update those assertions. **Out of scope** for this quick task per the deviation-rules SCOPE BOUNDARY (the failures are in unrelated test files and not caused by our two edits) — confirmed by re-running both tests against HEAD~2 (before our edits) where they still fail with the same assertion error. Logged for future cleanup.

The three plan-named invariant suites (`test_phase04_uif_invariants.py`, `test_joint_validation_invariants.py`, `test_phase03_chat_invariants.py`) — 47 tests total — all pass green. Locked invariants byte-stable:

- Sandbox attribute literal `sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"` byte-untouched (`test_jv_detail_iframe_sandbox_locked_attribute`).
- No `| safe` filter introduced on JV templates (`test_jv_templates_have_no_safe_filter`).
- `.navbar {` still absent from app.css (`test_navbar_css_rule_removed` — Phase 04 D-UIF-06).
- `.topbar {` substring still present (`test_topbar_css_rule_present` — Phase 04 D-UIF-06).
- `.table-sticky-corner` z-index ladder (3/2/1) byte-untouched.
- No new Plotly load on detail.html (`test_plotly_only_loaded_on_ask_page`).

## Smoke test

```
PYTHONPATH=. .venv/bin/python -c "
from fastapi.testclient import TestClient
from app_v2.main import app
c = TestClient(app)
r = c.get('/')
assert r.status_code == 200
assert 'class=\"topbar\"' in r.text
css = c.get('/static/css/app.css').text
assert 'position: sticky' in css
print('smoke OK')
"
# → smoke OK
```

JV listing route returns 200, body contains `class="topbar"`, and the served `/static/css/app.css` contains `position: sticky` — confirms the new rule is being served by Starlette's StaticFiles mount.

## Commits

- `2c86059` — `fix(joint-validation): remove p-0 from iframe wrapper to restore panel-body padding [quick-260507-wf6]`
- `bfeb3c6` — `fix(topbar): make .topbar position: sticky so tabs stay reachable while scrolling [quick-260507-wf6]`

## Deviations from Plan

None for the two file edits — both tasks executed verbatim against the plan's byte-precise specs.

**Note on Task 3 verification:** The plan's inline `.topbar` body-extraction regex `\.topbar\s*\{([^}]*)\}` truncated at the `}` inside the literal `{id}` written in the new comment block (the comment text "/jv/{id}" contains a closing brace that the dumb regex treats as rule-end). CSS parsers correctly ignore braces inside comments; the regex does not. Replaced with a brace-aware line scan that strips comments before counting braces — all 7 declaration assertions and the no-`.navbar` invariant pass green. No file edit needed; this was a verification-tooling fix only.

## Self-Check: PASSED

- File `app_v2/templates/joint_validation/detail.html` exists and contains `class="panel-body">` immediately before `<iframe` (verified via grep).
- File `app_v2/static/css/app.css` exists and the `.topbar` rule contains `position: sticky`, `top: 12px`, and `z-index: 50` (verified via brace-aware Python scan).
- Commit `2c86059` exists in `git log --oneline` (verified).
- Commit `bfeb3c6` exists in `git log --oneline` (verified).
- All three plan-named invariant test files pass: 47/47 green.
- Live smoke test green: JV listing 200 + topbar markup + sticky CSS served.
