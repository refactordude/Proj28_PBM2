---
phase: 05-overview-redesign
plan: 06
subsystem: testing
tags: [tests, integration, invariants, overview, regression-guard, picker-popover-shared, htmx, fastapi-testclient, jinja2-fragments]

# Dependency graph
requires:
  - phase: 05-overview-redesign
    provides: |
      Plan 05-04 router surface (GET /overview, POST /overview/grid, POST /overview/add)
      and Plan 05-05 template surface (overview/index.html sortable table + _grid.html
      <tbody> partial + _filter_bar.html cross-template macro import) — both must be in
      place before this plan's TestClient + invariant guards can pass.
provides:
  - End-to-end TestClient coverage for the Phase 5 Overview surface (22 tests)
  - 11 codebase-invariant static-analysis guards (13 collected with parametrize) locking D-OV-02..13 + INFRA-05 + XSS + Plotly carry-over
  - Permanent regression guard against template-fragment macro-scope bug (sortable_th visibility under jinja2-fragments single-block render)
  - Updated test_content_routes.py AI-button assertions for the new table-cell button class
affects: [phase-06-ask-tab-port, future-overview-extensions, any-template-fragment-render]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Jinja2 macro scope under jinja2-fragments: when a route returns specific block_names, template-top macros are NOT carried into the fragment render — only the block's own enclosed definitions are. Solution: define the macro INSIDE the block (mirrors `maybe` in _grid.html)."
    - "Static-analysis invariant guards: forbidden literals constructed at runtime via string concatenation (`'| ' + 'safe'`) so the test source itself does not contain the substring it scans for under app_v2/."
    - "Repeated-key form posts: helper `_post_form_pairs(client, url, pairs)` uses `urllib.parse.urlencode + content= + explicit Content-Type` (httpx 0.28 dropped list-of-tuples on `data=`). Reused across browse + overview integration tests."
    - "Parametrized forbidden-route guards: single test function with `@pytest.mark.parametrize` over (regex, decision_id) pairs covers DELETE/POST/POST routes in 1 source location, 3 collected runs."

key-files:
  created:
    - "tests/v2/test_phase05_invariants.py — 11 invariant tests (13 collected) for D-OV-02..13 + INFRA-05 + XSS + Plotly + remove-button-gone"
  modified:
    - "tests/v2/test_overview_routes.py — full rewrite, legacy <select> tests removed, 22 new tests for OVERVIEW-V2-01..06 + D-OV-04 + D-OV-11 + D-OV-13"
    - "tests/v2/test_content_routes.py — 2 AI-button assertion updates (class + tooltip wording for Phase 5 _grid.html)"
    - "app_v2/templates/overview/index.html — Rule-1 deviation: hoist sortable_th macro INSIDE {% block grid %} so jinja2-fragments single-block render can see it"
  deleted:
    - "tests/v2/test_overview_filter.py — D-OV-14, legacy <select>+POST /overview/filter coverage that targets routes removed by Plan 05-04"

key-decisions:
  - "Macro scope under jinja2-fragments: the sortable_th macro had to move from template-top scope INTO {% block grid %} because jinja2-fragments renders only the requested block — template-top macros are not carried in. Mirrors the same constraint solved by inlining `maybe` inside _grid.html. Plan 05-05 SUMMARY noted the inheritance case (block-to-block) but missed the fragments case (block-rendered-standalone via block_names)."
  - "Plan 05-06 mandate to ship a green suite required updating 2 tests in test_content_routes.py (out of plan's literal <files> list) per the Rule-1 bug auto-fix protocol; deferred-items.md explicitly named those 2 tests as Plan 05-06 scope."
  - "Forbidden-route guards built as a single parametrized function over 3 (regex, decision_id) pairs — one source-of-truth test, 3 collected runs in CI. Same idiom as Phase 03 banned-libs guard."

patterns-established:
  - "Pattern: when a Jinja2 macro is consumed inside a block that may be rendered standalone via jinja2-fragments block_names, the macro definition MUST live inside that block (or be imported into it via {% import %}). Template-top macro scope does NOT survive a single-block fragment render."
  - "Pattern: static-analysis invariant guards split forbidden literals at runtime via string concatenation so the guard's own source file does not contain the substring it scans for — eliminates self-match false-positives without carve-out logic."
  - "Pattern: integration test for a new Phase 5 route surface = TestClient + monkeypatch the 3 collaborators (overview_store YAML path, list_platforms catalog, CONTENT_DIR for frontmatter reads) + clear caches (cache.clear_all_caches + content_store._FRONTMATTER_CACHE.clear) per-fixture."

requirements-completed:
  - OVERVIEW-V2-01
  - OVERVIEW-V2-02
  - OVERVIEW-V2-03
  - OVERVIEW-V2-04
  - OVERVIEW-V2-05
  - OVERVIEW-V2-06

# Metrics
duration: ~12 min
completed: 2026-04-28
---

# Phase 5 Plan 6: Overview Test Suite + Codebase Invariants Summary

**End-to-end TestClient coverage for the Phase 5 Overview surface (22 tests) + 11 codebase-invariant guards locking D-OV-02..13 + macro-scope bug fix in overview/index.html that surfaced under jinja2-fragments single-block render of POST /overview/grid.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-28T07:35:25Z
- **Completed:** 2026-04-28T07:47:04Z
- **Tasks:** 4 (all completed; 1 Rule-1 deviation auto-fixed inline)
- **Files modified:** 4 (1 deleted, 1 created, 3 edited)

## Accomplishments

- **tests/v2/test_overview_filter.py DELETED (D-OV-14)** — 32 obsolete `<select>`-based filter tests removed; routes they targeted (POST /overview/filter, /overview/filter/reset) were removed by Plan 05-04.
- **tests/v2/test_overview_routes.py rewritten (22 tests)** — covers OVERVIEW-V2-01..06 + D-OV-04 (forbidden routes) + D-OV-11 (HX-Redirect) + D-OV-13 (URL round-trip + repeated-key multi-filter) + XSS escape on hostile filter values + 6 OOB picker badges + HX-Push-Url canonical-not-/grid (Pitfall 2 from Phase 4).
- **tests/v2/test_phase05_invariants.py created (11 tests, 13 collected)** — codebase invariants for D-OV-02 (yaml.safe_load only), D-OV-04 (no forbidden routes), D-OV-05 (template inventory), D-OV-06 (picker_popover SHARED not forked), D-OV-10 (AI Summary contract preserved), D-OV-13 (Query default_factory), OVERVIEW-V2-01 (Phase 4 table classes), INFRA-05 (no async def), XSS defense (no `| safe`), no Plotly under app_v2/, no hx-delete to /overview/.
- **Rule-1 bug auto-fix in app_v2/templates/overview/index.html** — sortable_th macro moved INTO {% block grid %} so jinja2-fragments' single-block render of POST /overview/grid (block_names=["grid", ...]) can see it. Without the fix, every POST /overview/grid blew up with `'sortable_th' is undefined`.
- **tests/v2/test_content_routes.py — 2 AI-button assertions updated** — Phase 5 D-OV-05 moved the AI Summary button from `class="ai-btn ms-2"` (flex `<li>` utility) to `class="btn btn-sm btn-outline-primary ai-btn"` (Bootstrap-table cell button); tooltip wording changed from "Content page must exist first" to "No content page to summarize yet". SUMMARY-02 contract on hx-post / hx-target / hx-disabled-elt preserved verbatim per D-OV-10.
- **Full v2 suite GREEN: 293 passed + 1 skipped + 0 failed** (was 22 failures in deferred-items.md before Plan 05-06).
- **Phase 4 byte-stability preserved: 14/14 invariants + 16/16 browse routes pass.**

## Task Commits

Each task was committed atomically:

1. **Task 1: Delete tests/v2/test_overview_filter.py (D-OV-14)** — `50ca46d` (chore)
2. **Task 2: Rewrite tests/v2/test_overview_routes.py + content-routes ai-btn assertions + macro-scope bug fix** — `d2170b3` (test)
3. **Task 3: Create tests/v2/test_phase05_invariants.py** — `efa53fe` (test)
4. **Task 4: Full v2 regression run** — verification only; no code change → no commit per execute-plan.md task_commit_protocol.

**Plan metadata commit:** pending (this SUMMARY + STATE + ROADMAP).

## Files Created / Modified

- `tests/v2/test_overview_routes.py` — full rewrite (22 tests; 13 NEW for the Phase 5 surface; 9 KEPT from Phase 2 for basic GET / + POST /overview/add 422 paths). 350 insertions, 175 deletions.
- `tests/v2/test_phase05_invariants.py` — NEW (302 lines, 11 test functions, 13 collected with parametrize).
- `tests/v2/test_overview_filter.py` — DELETED (418 lines).
- `tests/v2/test_content_routes.py` — 2 test functions updated (AI button class + tooltip wording).
- `app_v2/templates/overview/index.html` — macro `sortable_th` removed from template-top, re-defined inside `{% block grid %}` (Rule-1 bug fix). Headers + macro now travel together when the block is rendered standalone via jinja2-fragments.

## Decisions Made

- **Macro scope under jinja2-fragments** — the canonical solution is to define the macro inside the block that uses it (NOT at template-top). Same idiom as `maybe` in _grid.html. Documented inline in index.html for future readers. Plan 05-05's earlier "hoist macro to template-top" fix solved the inheritance case (block-to-block visibility) but missed this orthogonal case (single-block fragment render).
- **2 test_content_routes.py tests updated even though out of Plan 05-06's literal `<files>` list** — the success criterion "Full v2 test suite green (no leftover failures from deferred-items.md)" is non-negotiable, and deferred-items.md explicitly named those 2 tests as Plan 05-06 scope. Treated as Rule-1 (bug) auto-fix to align test assertions with the Phase 5 _grid.html button class change.
- **Forbidden-route guard parametrization** — 3 forbidden patterns (DELETE, POST /filter, POST /filter/reset) packed into one `@pytest.mark.parametrize` test, mirroring the Phase 3 banned-libs guard pattern. One source location, 3 CI failures attributable to specific decisions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] sortable_th macro undefined under jinja2-fragments single-block render**
- **Found during:** Task 2 (running test_post_overview_grid_returns_fragment_with_hx_push_url for the first time)
- **Issue:** POST /overview/grid returned 500 with `jinja2.exceptions.UndefinedError: 'sortable_th' is undefined` — the macro was defined at template-top in index.html (between `{% extends %}` and `{% block content %}`), which works for the inheritance case (block-to-block visibility within the same render) but NOT for jinja2-fragments' single-block render via `block_names=["grid", ...]`. When jinja2-fragments renders just the grid block in isolation, template-top macros are not carried into the fragment render — only the block's own enclosed definitions are.
- **Fix:** Removed the macro from template-top; re-defined it INSIDE `{% block grid %}`. Mirrors the same idiom used by `maybe` in _grid.html (which Plan 05-05 SUMMARY explicitly cited as the precedent). Inline comment in index.html documents the constraint and the precedent.
- **Files modified:** app_v2/templates/overview/index.html
- **Verification:** All 22 test_overview_routes.py tests pass; Phase 4 byte-stability preserved (30/30 in test_browse_routes.py + test_phase04_invariants.py).
- **Committed in:** d2170b3 (Task 2 commit, alongside the rewrite + content-routes update)

**2. [Rule 1 - Bug] tests/v2/test_content_routes.py — 2 AI-button assertions stale**
- **Found during:** Pre-existing failures from deferred-items.md (Plan 05-05 deferred 22 failures into Plan 05-06's scope)
- **Issue:** Two tests in test_content_routes.py (`test_overview_row_ai_button_disabled_when_no_content`, `test_overview_row_ai_button_enabled_when_content_exists`) asserted on `class="ai-btn ms-2"` and tooltip text "Content page must exist first" — both wired to the legacy Phase 3 `<li>` utility class and tooltip wording. Plan 05-05 changed the AI Summary button to a table-cell button: `class="btn btn-sm btn-outline-primary ai-btn"` with tooltip "No content page to summarize yet". The SUMMARY-02 contract (hx-post, hx-target, hx-disabled-elt) was preserved verbatim per D-OV-10.
- **Fix:** Updated both test assertions to the new class + tooltip wording. Comment in each test references D-OV-05 + D-OV-10 for the contract pedigree.
- **Files modified:** tests/v2/test_content_routes.py
- **Verification:** All 35 content-routes tests pass.
- **Committed in:** d2170b3 (Task 2 commit; rolled in alongside the routes rewrite because both fixes flow from the same Phase 5 template change)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs)
**Impact on plan:** Both deviations are corrections of mismatches between the test layer and the production template/macro surface; no scope creep. The macro-scope fix is a Plan 05-05 oversight closure (Plan 05-05 SUMMARY said "hoisted to template-top scope where it is visible from all child blocks" — true under inheritance, false under fragments). The content-routes update is explicitly named in deferred-items.md as Plan 05-06's responsibility.

## Issues Encountered

- **jinja2-fragments macro scope mismatch** — surfaced only when Task 2's POST /overview/grid integration test ran for the first time. Plan 05-05's invariant `test_picker_popover_uses_d15b_auto_commit_pattern` rendered the macro via `{% from "..." import picker_popover %}` (cross-template import), which has its own scope rules and didn't catch this case. Plan 05-06 doesn't add a Phase 5 invariant for this specific bug class because Task 2's `test_post_overview_grid_returns_fragment_with_hx_push_url` (and 3 sibling /grid tests) now act as the regression guard end-to-end — any future macro-scope regression breaks them immediately.

## Self-Check: PASSED

**Files exist:**
- FOUND: tests/v2/test_phase05_invariants.py
- FOUND: tests/v2/test_overview_routes.py (rewrite)
- FOUND: tests/v2/test_content_routes.py (modified)
- FOUND: app_v2/templates/overview/index.html (macro hoisted into block)
- VERIFIED MISSING: tests/v2/test_overview_filter.py (deleted per D-OV-14)

**Commits exist:**
- FOUND: 50ca46d (Task 1 — chore: delete legacy filter test file)
- FOUND: d2170b3 (Task 2 — test: rewrite + macro fix + content-routes update)
- FOUND: efa53fe (Task 3 — test: add Phase 5 invariants)

**Test counts:**
- tests/v2/test_overview_routes.py: 22 collected, 22 passing
- tests/v2/test_phase05_invariants.py: 13 collected (11 functions + 2 extra parametrize cases), 13 passing
- tests/v2/test_phase04_invariants.py: 14 collected, 14 passing (byte-stable, no Phase 4 regression)
- Full v2 suite: 294 collected, 293 passed + 1 skipped + 0 failed (the skip is the Phase 1 stub-test in test_main.py tombstoned by Plan 04-02)

## Cross-Reference: 6 ROADMAP Phase 5 Success Criteria → Test

| ROADMAP Criterion | Test(s) verifying it |
|-------------------|----------------------|
| Overview tab renders curated platform list as sortable Bootstrap table mirroring Phase 4 styling | `test_get_overview_returns_table_with_phase4_classes` (routes) + `test_overview_index_uses_phase4_table_classes` (invariant) |
| Per-platform PM metadata sourced from YAML frontmatter; em-dash sentinel for missing fields | `test_get_overview_returns_table_with_phase4_classes` exercises this end-to-end (frontmatter `title=Project Alpha` rendered in the row) + Plan 05-02's existing 15 frontmatter parser tests + Plan 05-03's 18 grid-service tests |
| Six popover-checklist multi-filters reuse Phase 4's _picker_popover.html (no fork) | `test_picker_popover_macro_is_shared_not_forked` (invariant) + `test_post_overview_grid_emits_oob_filter_badges` (routes — confirms all 6 OOB badge ids appear) |
| Sortable column headers (asc → desc → asc) with default `start desc`; sort state survives URL round-trip | `test_get_overview_default_sort_is_start_desc` + `test_get_overview_url_roundtrip_pre_checks_filters` (routes) |
| AI Summary stays in row's last cell with existing Phase 3 in-place HTMX swap UX preserved | `test_ai_summary_cell_preserves_phase3_contract` (invariant — D-OV-10) + `test_overview_row_ai_button_disabled_when_no_content` + `test_overview_row_ai_button_enabled_when_content_exists` (content_routes) |
| Add platform input row preserved; legacy `<select>` brand/SoC/year/has_content filters and Remove (×) button removed | `test_post_overview_add_success_returns_hx_redirect` + 3 forbidden-route tests + `test_no_remove_button_hx_delete_in_overview_templates` (invariant) + `test_no_forbidden_route_in_overview_router` (parametrized invariant) |

## Cross-Reference: 6 OVERVIEW-V2-XX Requirements → Test(s)

| Requirement | Test(s) verifying it |
|-------------|----------------------|
| OVERVIEW-V2-01 (Phase 4 styling) | `test_get_overview_returns_table_with_phase4_classes`, `test_overview_index_uses_phase4_table_classes` |
| OVERVIEW-V2-02 (PM metadata from frontmatter) | `test_get_overview_returns_table_with_phase4_classes` (rendered title from frontmatter) + Plan 05-02 frontmatter tests + Plan 05-03 grid-service tests |
| OVERVIEW-V2-03 (6 popover-checklist multi-filters) | `test_picker_popover_macro_is_shared_not_forked`, `test_post_overview_grid_emits_oob_filter_badges`, `test_post_overview_grid_repeated_keys_multi_filter`, `test_post_overview_grid_escapes_xss_payload_in_filter_value` |
| OVERVIEW-V2-04 (sortable headers + URL round-trip) | `test_get_overview_default_sort_is_start_desc`, `test_get_overview_url_roundtrip_pre_checks_filters`, `test_post_overview_grid_returns_fragment_with_hx_push_url`, `test_overview_routes_use_query_default_factory_for_multi_value` |
| OVERVIEW-V2-05 (AI Summary contract preserved) | `test_ai_summary_cell_preserves_phase3_contract`, `test_overview_row_ai_button_disabled_when_no_content`, `test_overview_row_ai_button_enabled_when_content_exists` |
| OVERVIEW-V2-06 (Add row preserved; legacy filters/Remove removed) | `test_post_overview_add_success_returns_hx_redirect`, `test_post_overview_add_unknown_platform_returns_404_plain_text`, `test_post_overview_add_duplicate_returns_409_plain_text`, `test_delete_overview_pid_route_is_gone`, `test_post_overview_filter_route_is_gone`, `test_post_overview_filter_reset_route_is_gone`, `test_no_remove_button_hx_delete_in_overview_templates`, `test_no_forbidden_route_in_overview_router` (parametrized) |

## Next Phase Readiness

**Phase 5 is COMPLETE.** All 6 OVERVIEW-V2-XX requirements ship with end-to-end + invariant test coverage; full v2 suite green; Phase 4 byte-stability preserved.

Pending todos (added to STATE.md):
- `/gsd-verify-phase 5` — run Phase 5 verifier
- `/gsd-uat-phase 5` — Phase 5 UAT against running app
- Phase 6 (ask-tab carry-over) is the next phase per ROADMAP — its dependency on Phase 5 is now satisfied.

No blockers. No deferred items. Phase 5's `.planning/phases/05-overview-redesign/deferred-items.md` can be considered fully resolved (all 22 documented failures are now passing in the green suite).

---
*Phase: 05-overview-redesign*
*Plan: 06*
*Completed: 2026-04-28*
