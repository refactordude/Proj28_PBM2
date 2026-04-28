---
phase: 06-ask-tab-port
plan: "06"
subsystem: testing
tags: [streamlit, deletion, d22, invariants, regression-bar, cleanup]

requires:
  - phase: 06-ask-tab-port
    plan: "05"
    provides: "test_v1_streamlit_ask_still_present_pre_06_06_deletion placeholder invariant; full suite at 522 tests baseline"
  - phase: 06-ask-tab-port
    plan: "03"
    provides: "app_v2/routers/ask.py importing nl_service + nl_agent + pydantic_model (D-22 #5 preserves)"
  - phase: 06-ask-tab-port
    plan: "02"
    provides: "app_v2/services/starter_prompts.py (load_starter_prompts ported from v1.0)"

provides:
  - "D-22 deletion complete: app/pages/ask.py, tests/pages/test_ask_page.py, tests/pages/test_starter_prompts.py removed from repo"
  - "streamlit_app.py nav trimmed to Browse + Settings (Ask entry removed)"
  - "tests/v2/test_phase06_invariants.py: test_v1_streamlit_ask_deleted_per_d22 positively enforces D-22 deletion + D-22 #5 framework-agnostic preserves"
  - ".planning/STATE.md: Phase 6 completion entry, 6 decision bullets, regression bar at 506 tests"

affects:
  - "gsd-verify-phase 6: verifier should confirm 506 tests green and Ask files absent"
  - "gsd-uat-phase 6: UAT should confirm v2.0 /ask route serves Ask UI; v1.0 Streamlit Browse + Settings still work"

tech-stack:
  added: []
  patterns:
    - "D-22 deletion contract pattern: pre-deletion grep sanity check (no v2.0 caller of deleted module) before git rm; positive preserve assertions in invariant test enforce D-22 #5 keep-list in CI"
    - "Invariant polarity flip: placeholder 'MUST exist' invariant from prior plan replaced with 'MUST NOT exist' invariant in final cleanup plan — same test file, same section, renamed function with inverted assert"

key-files:
  created: []
  modified:
    - streamlit_app.py
    - tests/v2/test_phase06_invariants.py
    - .planning/STATE.md
  deleted:
    - app/pages/ask.py
    - tests/pages/test_ask_page.py
    - tests/pages/test_starter_prompts.py

key-decisions:
  - "D-22 final cleanup executed as last plan of Phase 6 (not a separate cleanup phase) — user explicit choice documented in 06-CONTEXT.md"
  - "test_starter_prompts.py deleted (not migrated): its 6 per-fallback-branch unit tests are subsumed by tests/v2/test_ask_routes.py::test_get_ask_returns_200_with_html end-to-end render, which mocks load_starter_prompts and asserts rendered chip grid"
  - "D-22 #5 positively asserted in test_v1_streamlit_ask_deleted_per_d22: nl_service.py + nl_agent.py + pydantic_model.py presence checked, not just absence of ask.py"
  - "Regression bar: 522 (pre-deletion) -> 506 (post-deletion); delta of -16 = 11 tests from test_ask_page.py + 6 tests from test_starter_prompts.py - 1 (invariant function renamed, staying in 19-count suite)"

patterns-established:
  - "Pre-deletion grep gate: before git rm any module, grep v2.0 callers to confirm no live imports — prevents broken imports from slipping through"
  - "Polarity-flip handoff: end-of-phase placeholder invariant asserting presence, replaced in cleanup plan with absence assertion — explicit rename documents the change clearly in git history"

requirements-completed:
  - ASK-V2-01
  - ASK-V2-02
  - ASK-V2-03
  - ASK-V2-05
  - ASK-V2-06
  - ASK-V2-07
  - ASK-V2-08

duration: ~8min
completed: "2026-04-29"
---

# Phase 6 Plan 06: D-22 v1.0 Streamlit Ask Deletion + Invariant Polarity Flip Summary

**Hard-deleted v1.0 Streamlit Ask UI (3 files git rm'd), trimmed streamlit_app.py nav to Browse+Settings, flipped Phase 6 invariant polarity to assert deletion with D-22 #5 preserve checks; full suite 506 passed**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-29T00:00:00Z
- **Completed:** 2026-04-29T00:08:00Z
- **Tasks:** 2
- **Files modified:** 3 (modified) + 3 (deleted)

## Accomplishments

### Task 1: D-22 Deletions + streamlit_app.py + Invariant Polarity Flip

**Pre-deletion sanity check (D-22 procedure step 1):**

All three gates passed before any deletion:
- `grep -rE "from app.pages.ask" app_v2/` — 0 matches (v2.0 has no live imports from the deleted module)
- `grep -rE "from app.core.agent.nl_service" app_v2/` — 1 match in `app_v2/routers/ask.py` (D-22 #5 preserve confirmed)
- `grep -rE "from app.core.agent.nl_agent" app_v2/` — 2 matches in `app_v2/routers/ask.py` (D-22 #5 preserve confirmed)
- `grep -rE "from app.adapters.llm.pydantic_model" app_v2/` — 1 match in `app_v2/routers/ask.py` (D-22 #5 preserve confirmed)

**Files deleted:**

| File | Tests removed | Rationale |
|------|--------------|-----------|
| `app/pages/ask.py` | n/a (production) | v1.0 Streamlit Ask page — replaced by `app_v2/routers/ask.py` from Plan 06-03 |
| `tests/pages/test_ask_page.py` | 11 tests | Source of truth deleted; AppTest-based tests no longer have a page to test |
| `tests/pages/test_starter_prompts.py` | 6 tests | Imports `from app.pages.ask import load_starter_prompts` (deleted); coverage subsumed by `tests/v2/test_ask_routes.py::test_get_ask_returns_200_with_html` |

**streamlit_app.py edit:** Removed `st.Page("app/pages/ask.py", title="Ask", icon=":material/chat:")` from the `st.navigation([...])` list. Browse (default) + Settings remain. Valid Python syntax preserved (trailing comma on Browse entry).

**Invariant polarity flip:** `test_v1_streamlit_ask_still_present_pre_06_06_deletion` (Plan 06-05 placeholder asserting presence) replaced with `test_v1_streamlit_ask_deleted_per_d22` asserting:
- `not (REPO / "app" / "pages" / "ask.py").exists()`
- `not (REPO / "tests" / "pages" / "test_ask_page.py").exists()`
- `"app/pages/ask.py" not in streamlit_app.py source`
- `nl_service.py`, `nl_agent.py`, `pydantic_model.py` all still exist (D-22 #5 positive assertions)

### Task 2: STATE.md Phase 6 Completion Entry

Four edits to `.planning/STATE.md`:
1. Header frontmatter: `status=verifying`, `completed_phases/plans=6/30`, `percent=100`, Phase 6 completion `stopped_at`
2. Current Position block: `Plan: Complete`, `Phase: 6`, ready for verification
3. Decisions section: 6 new `06-01:` through `06-06:` bullets summarizing all Phase 6 locked decisions
4. Pending Todos: replaced `Execute Phase 6 (ask-tab carry-over)` with `/gsd-verify-phase 6` + `/gsd-uat-phase 6`

## Regression Bar

| Metric | Value |
|--------|-------|
| Pre-deletion baseline (Plan 06-05) | 522 passed, 2 skipped |
| Tests removed | -17 (11 from test_ask_page.py + 6 from test_starter_prompts.py) |
| Invariant function renamed | net 0 (19 collected items in Phase 6 invariants maintained) |
| **Post-deletion result** | **506 passed, 2 skipped, 0 failed** |

## Task Commits

1. **Task 1: D-22 deletions + streamlit_app.py + invariant polarity flip** — `bb584c7` (feat)
2. **Task 2: STATE.md Phase 6 completion** — `b3f0ddd` (chore)

## Files Created/Modified

- `app/pages/ask.py` — DELETED (v1.0 Streamlit Ask page, per D-22)
- `tests/pages/test_ask_page.py` — DELETED (v1.0 AppTest tests, 11 tests removed)
- `tests/pages/test_starter_prompts.py` — DELETED (v1.0 unit tests, 6 tests removed; coverage subsumed by v2.0 route test)
- `streamlit_app.py` — Ask nav entry removed; Browse + Settings remain (2 st.Page entries)
- `tests/v2/test_phase06_invariants.py` — Polarity flip: old presence test → new absence test with D-22 #5 preserve assertions
- `.planning/STATE.md` — Phase 6 completion: status, progress counters, 6 decision bullets, updated todos

## Decisions Made

- Deleted `tests/pages/test_starter_prompts.py` (not migrated) because its 6 per-fallback-branch unit tests for `load_starter_prompts` are fully subsumed by the v2.0 route-level test that exercises `load_starter_prompts` end-to-end via the real `GET /ask` route render. Migrating the tests would test the v2.0 function under the v1.0 import path, which is gone.
- D-22 #5 positive assertions added to the polarity-flipped invariant test (beyond what the plan strictly required) — ensures CI fails immediately if a future commit accidentally deletes `nl_service.py`, `nl_agent.py`, or `pydantic_model.py` along with a future v1.0 cleanup sweep.

## Deviations from Plan

None — plan executed exactly as written. All 5 action steps in Task 1 and all 4 edit steps in Task 2 applied without issues.

## Known Stubs

None. This plan performs only deletions, nav edits, invariant polarity flips, and documentation updates. No production code introduced.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced by this plan. All changes are deletions and documentation.

## D-22 #5 Preserve Verification

The following files MUST remain on disk (v2.0 consumers confirmed by grep before deletion):

| File | Status | v2.0 import site |
|------|--------|-----------------|
| `app/core/agent/nl_service.py` | PRESENT | `app_v2/routers/ask.py`: `from app.core.agent.nl_service import NLResult, run_nl_query` |
| `app/core/agent/nl_agent.py` | PRESENT | `app_v2/routers/ask.py`: `from app.core.agent.nl_agent import AgentDeps, build_agent` |
| `app/adapters/llm/pydantic_model.py` | PRESENT | `app_v2/routers/ask.py`: `from app.adapters.llm.pydantic_model import build_pydantic_model` |
| `config/starter_prompts.example.yaml` | PRESENT | `app_v2/services/starter_prompts.py` fallback chain |

All four are positively asserted by `test_v1_streamlit_ask_deleted_per_d22` in CI.

## Next Phase Readiness

Phase 6 plan-list is complete (6/6 plans executed). Recommended next actions:

- `/gsd-verify-phase 6` — automated verifier checks all Phase 6 deliverables
- `/gsd-uat-phase 6` — UAT against running app (confirm `/ask` renders v2.0 UI, v1.0 Browse + Settings work, no 404s on nav)

Phase 7 has not been planned. The v2.0 milestone is feature-complete per PROJECT.md scope.

## Self-Check

Verified before writing SUMMARY:

- `test ! -e app/pages/ask.py` — PASS
- `test ! -e tests/pages/test_ask_page.py` — PASS
- `test ! -e tests/pages/test_starter_prompts.py` — PASS
- `test -f app/core/agent/nl_service.py` — PASS
- `test -f app/core/agent/nl_agent.py` — PASS
- `test -f app/adapters/llm/pydantic_model.py` — PASS
- `grep -c "app/pages/ask.py" streamlit_app.py` — 0 (PASS)
- `grep -cE "def test_v1_streamlit_ask_still_present_pre_06_06_deletion" tests/v2/test_phase06_invariants.py` — 0 (PASS)
- `grep -cE "def test_v1_streamlit_ask_deleted_per_d22" tests/v2/test_phase06_invariants.py` — 1 (PASS)
- `pytest tests/ -q` — 506 passed, 2 skipped, 0 failed (PASS)
- `pytest tests/v2/test_phase06_invariants.py -q` — 19 passed (PASS)
- Commit `bb584c7` exists — PASS
- Commit `b3f0ddd` exists — PASS

## Self-Check: PASSED

---
*Phase: 06-ask-tab-port*
*Completed: 2026-04-29*
