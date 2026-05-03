# Phase 3 — Deferred Items (for plan 03-05 cleanup)

This file tracks issues surfaced during plan execution that are explicitly out of scope for the current plan and must be addressed by plan 03-05.

## From plan 03-04 execution (2026-05-03)

### 1. Phase 4 invariant test now fails: `test_no_banned_export_or_chart_libraries_imported_in_app_v2[plotly]`

- **Test file:** `tests/v2/test_phase04_invariants.py:42`
- **Why it fails now:** The test asserts NO `import plotly` or `from plotly` line exists anywhere under `app_v2/`. My new `app_v2/routers/ask.py` `_build_plotly_chart_html` helper imports `plotly.graph_objects` lazily inside the function — this is the explicit Phase 3 design (server-side Plotly chart construction per D-CHAT-05 + T-03-04-09 mitigation; the bundle was vendored in plan 03-01 specifically for this purpose).
- **Plan 03-04 plan position:** Acceptance criterion line 480 explicitly requires the plotly Figure → to_html call. The verification block (line 1089) notes pre-existing tests will fail and are "rewritten/replaced in plan 05".
- **Fix in plan 03-05:** Either (a) narrow the Phase 4 invariant to whitelist `app_v2/routers/ask.py` (keep the rule for browse/joint_validation/etc.), or (b) delete this `plotly` parametrize entry and rely on the Phase 3 invariant (plan 03-05) to guard the Plotly placement separately.

### 2. Pre-existing tests in `tests/v2/test_ask_routes.py` now error/fail (13 tests)

- **Test file:** `tests/v2/test_ask_routes.py` (entire file)
- **Why they fail now:** Every test in this file asserts on Phase 6 contracts: `POST /ask/query` / `POST /ask/confirm` route existence, `_answer.html` / `_confirm_panel.html` / `_abort_banner.html` template rendering, NL-05 confirmation flow, `loop-aborted` reason on second-turn failure, etc. All of those routes/templates/reasons were intentionally removed in plan 03-04 Task 1 per D-CHAT-09.
- **Plan 03-04 plan position:** Verification block line 1089: *"Existing test files `tests/v2/test_ask_routes.py` and `tests/v2/test_phase06_invariants.py` will report failures referencing the deleted Phase 6 routes/templates — those tests are rewritten/replaced in plan 05."* (`test_phase06_invariants.py` was atomically deleted in Task 1; `test_ask_routes.py` remains pending plan 03-05.)
- **Fix in plan 03-05:** Delete or rewrite `tests/v2/test_ask_routes.py` end-to-end. New tests should cover the Phase 3 surface: GET /ask renders chat shell; POST /ask/chat creates a turn + returns the user-message fragment; GET /ask/stream/{turn_id} returns 403 on session-cookie mismatch and 200 with SSE on match; POST /ask/cancel/{turn_id} returns 204 on owner match.

## Test-count math at end of plan 03-04

| | Tests |
|--|--|
| Plan 03-03 baseline (passed) | 464 |
| Plan 03-04 deletions (`test_phase06_invariants.py`) | -19 |
| Plan 03-04 expected stable count | 445 |
| Actual passed after plan 03-04 | 431 |
| Actual failed (Phase 4 invariant — plotly) | 1 |
| Actual errored (Phase 6 contract — `test_ask_routes.py`) | 13 |
| Sum | 445 ✓ |

The 14 failing/erroring tests are exactly the set the plan documents as "rewritten/replaced in plan 05".
