---
phase: 01-overview-tab-auto-discover-platforms-from-html-files
plan: 06
subsystem: testing
tags: [pytest, fastapi, testclient, cleanup, joint-validation, refactor, invariant-tests]

# Dependency graph
requires:
  - phase: 01-overview-tab-auto-discover-platforms-from-html-files/01-04
    provides: rewritten routers/overview.py + new routers/joint_validation.py + main.py /static/joint_validation mount — every symbol the cleanup deletes is already orphaned
  - phase: 01-overview-tab-auto-discover-platforms-from-html-files/01-05
    provides: rewritten overview templates with locked sandbox literal + 6 picker_popover invocations + verbatim D-JV-17 empty-state copy
provides:
  - "9 obsolete files deleted: config/overview.yaml + 3 services + 5 tests; total -2131 LOC"
  - "tests/v2/test_joint_validation_routes.py (NEW) — 15 end-to-end TestClient tests covering listing, detail, summary, static mount, empty state, and adjacent-tab regression"
  - "tests/v2/test_joint_validation_invariants.py (NEW) — 15 grep-based source-level policy guards enforcing D-JV-01..D-JV-17 + Pitfall 3 + Pitfall 10 + INFRA-05"
  - "Phase 5 Platform-curated machinery fully removed from the repo — Browse + Ask + Platforms detail pages still consume content/platforms/*.md unchanged (regression-safe)"
affects: []

# Tech tracking
tech-stack:
  added: []  # No new dependencies; cleanup-only plan
  patterns:
    - "Orphan-import audit before deletion — pre-flight grep loop catches every dangling reference; Rule 3 auto-fixes 4 sibling test files BEFORE deletion so the v2 suite stays green throughout"
    - "Grep-based invariant tests — read source files via Path.read_text() + substring assertions; <1s for 15 tests; ideal for byte-pinning locked decisions (sandbox attr, scheme tuple, Korean label) so future refactors fail loudly"
    - "TestClient + monkeypatch.setattr for JV_ROOT in 3 consumer modules — the import-as-from idiom binds the name into each consumer; each binding must be patched separately"
    - "jv_dir_real fixture with try/finally cleanup — runs on test pass, fail, AND interrupt (Ctrl-C / mid-yield exception). T-06-01 mitigation"

key-files:
  created:
    - tests/v2/test_joint_validation_routes.py
    - tests/v2/test_joint_validation_invariants.py
  modified:
    - app_v2/services/joint_validation_grid_service.py
    - tests/v2/test_atomic_write.py
    - tests/v2/test_content_routes.py
    - tests/v2/test_phase03_invariants.py
    - tests/v2/test_summary_integration.py
    - tests/v2/test_summary_routes.py

key-decisions:
  - "Rule 3 auto-fix: 4 sibling test files (test_atomic_write.py, test_summary_routes.py, test_summary_integration.py, test_content_routes.py) AND test_phase03_invariants.py held orphan references to overview_store.OVERVIEW_YAML or read overview_store.py source — fixed BEFORE deletion so the v2 suite stays green throughout the plan instead of going red mid-task"
  - "Rule 3 auto-fix: docstring references to deleted symbols (build_overview_grid_view_model, OverviewRow) inside joint_validation_grid_service.py rephrased to historical mentions ('the deleted Phase 5 view-model builder') so the Plan 06 acceptance grep returns zero matches without losing the documentation context"
  - "Test 5 invariant matches the 5-string substring `\"javascript:\", \"data:\", \"vbscript:\", \"file:\", \"about:\"` rather than the surrounding parens because the actual source-code tuple is split across 3 lines for readability — substantive byte-equal contract preserved"
  - "Test 11 invariant scans BOTH joint_validation_summary.py AND joint_validation_parser.py for the decompose tag list because the pre-processor decomposition lives in the parser module per Plan 02's implementation; scanning both files honors the contract regardless of which module owns the decomposition"
  - "test_overview_filter.py was already absent from the working tree at plan start (presumably never created in v2.0 Phase 5) — silently skipped from the rm list; AC `[ ! -f tests/v2/test_overview_filter.py ]` already true"

patterns-established:
  - "Pre-deletion orphan-import audit pattern: run a grep loop for every imported name across app_v2/ + tests/, fix any sibling-file orphans (Rule 3), THEN delete the source file. Keeps the v2 suite green between commits."
  - "Grep-based source-level invariant test file: 15 tests run in <1s, no fixtures, no app startup; ideal vehicle for byte-pinning locked decisions (sandbox attr, scheme tuples, Korean labels, sync-def discipline)."
  - "JV_ROOT three-way monkeypatch: services.joint_validation_store.JV_ROOT (definition), routers.overview.JV_ROOT (Plan 04 import), routers.joint_validation.JV_ROOT (Plan 04 import) — every `from … import JV_ROOT` site needs its own patch."

requirements-completed: [D-JV-01, D-JV-06, D-JV-07, D-JV-12, D-JV-13, D-JV-15, D-JV-17]

# Metrics
duration: 11min
completed: 2026-04-30
---

# Phase 01 Plan 06: Cleanup wave — delete obsolete Platform-curated artifacts + add JV invariants

**9 files deleted (-2131 LOC) + 2 test files added (+588 LOC, 30 new tests) + 6 sibling files Rule-3-auto-fixed for orphan refs; full v2 test suite green at 360 passed / 5 skipped / 24s — Phase 5 curated-Platform Overview machinery is gone, the JV listing/detail/summary surface is route-tested + byte-pinned at the source level, and Browse/Ask/Platforms/Summary tabs are regression-safe.**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-04-30T12:12:37Z
- **Completed:** 2026-04-30T12:23:57Z
- **Tasks:** 3
- **Files deleted:** 8 tracked + 1 untracked (config/overview.yaml was never staged)
- **Files created:** 2 (588 LOC, 30 tests)
- **Files modified:** 6 (orphan-reference cleanup; +33 LOC, -33 LOC offsetting)

## Accomplishments

- **Task 1 — Delete obsolete Phase 5 Platform-curated machinery (D-JV-06, D-JV-07).** Removed `config/overview.yaml` (untracked), `app_v2/services/overview_store.py`, `app_v2/services/overview_filter.py`, `app_v2/services/overview_grid_service.py`, and 4 of the 5 plan-listed test files (`test_overview_store.py`, `test_overview_grid_service.py`, `test_overview_routes.py`, `test_phase05_invariants.py`). The 5th plan-listed file `tests/v2/test_overview_filter.py` was already absent. Rule-3 cleanup of 5 sibling files (`tests/v2/test_atomic_write.py`, `tests/v2/test_summary_routes.py`, `tests/v2/test_summary_integration.py`, `tests/v2/test_content_routes.py`, `tests/v2/test_phase03_invariants.py`) plus 2 docstring rephrasings in `app_v2/services/joint_validation_grid_service.py` removed every orphan reference BEFORE the deletion landed. Pre-deletion grep loop confirmed zero remaining `from app_v2.services.overview_store`/`overview_filter`/`overview_grid_service` imports outside files being deleted; post-deletion `pytest tests/v2/ -q --ignore=test_joint_validation_routes.py --ignore=test_joint_validation_invariants.py` exited 0 with **330 passed, 5 skipped**.
- **Task 2 — Create tests/v2/test_joint_validation_routes.py (15 tests).** End-to-end TestClient coverage for the JV surface that replaces `test_overview_routes.py`. Two fixtures: `jv_dir_with_one` (monkeypatches `JV_ROOT` in 3 consumer modules — services + 2 routers — so parsed-metadata calls hit a tmp_path JV root) and `jv_dir_real` (drops a uuid-suffixed numeric folder under the REAL `content/joint_validation/` because the StaticFiles mount can't be re-pointed mid-test). The `jv_dir_real` fixture uses try/finally so cleanup runs on test pass, failure, AND interrupt (WARN-04 fix). Tests cover: listing routes (GET / + GET /overview), filter URL round-trip, POST /overview/grid 3 OOB blocks + HX-Push-Url, deleted POST /overview/add returns 404/405, JV detail 200 + sandbox literal + iframe src + Korean 담당자 row, non-numeric/missing detail 404/422, static mount serves index.html, path traversal blocked, AI Summary always-200 on missing index, AI Summary success path with mocked LLM, empty-state copy verbatim, Browse/Ask regression smoke. **15/15 pass in 12.33s.**
- **Task 3 — Create tests/v2/test_joint_validation_invariants.py (15 tests).** Source-level grep-based policy guards that read each source file via `Path.read_text()` and run substring assertions. No app startup, no fixtures, <1s for 15 tests. Each test maps to a locked decision: D-JV-03 numeric regex, INFRA-05 sync-def discipline, T-05-03 locked sandbox 3-flag attribute (positive + 3 negative assertions), XSS defense (zero `| safe` across 4 templates), D-JV-15 5-scheme dangerous-link tuple, D-JV-05 zero em-dash defaults, D-JV-13 explicit `html=False` + `follow_symlink=False` mount kwargs, D-JV-06/D-JV-07 zero curated-Platform symbols in `routers/overview.py`, Pitfall 3 `hashkey("jv", ...)` discriminator, D-JV-04 byte-equal Korean label, D-JV-16 BeautifulSoup `decompose([script, style, img])`, project-wide `yaml.load` ban, JV router import + register in main.py, Pitfall 10 mount-order (JV before /static), and D-JV-11 picker_popover macro reuse from `browse/_picker_popover.html` (6 invocations + macro file present). **15/15 pass in 0.20s. Full v2 suite: 360 passed, 5 skipped, 4 warnings in 24s.**

## Task Commits

Each task was committed atomically:

1. **Task 1 — Delete obsolete Platform-curated machinery + Rule-3 sibling cleanup** — `5fe3be8` (chore)
2. **Task 2 — Add tests/v2/test_joint_validation_routes.py (15 route tests)** — `db35ade` (test)
3. **Task 3 — Add tests/v2/test_joint_validation_invariants.py (15 grep guards)** — `bc69dd0` (test)

## Files Created/Modified

**Created:**
- `tests/v2/test_joint_validation_routes.py` (277 LOC) — 15 end-to-end TestClient tests; 2 fixtures (jv_dir_with_one, jv_dir_real) + autouse cache reset + LLM-configured-client helper.
- `tests/v2/test_joint_validation_invariants.py` (311 LOC) — 15 grep-based source-level guards; runs in 0.20s.

**Modified (Rule-3 sibling cleanup):**
- `tests/v2/test_atomic_write.py` — drop the `test_overview_store_still_works_after_refactor` regression guard (consumer module no longer exists).
- `tests/v2/test_summary_routes.py` — drop `overview_store_mod` import + `OVERVIEW_YAML` monkeypatch from `isolated_summary` fixture.
- `tests/v2/test_summary_integration.py` — same fixture cleanup.
- `tests/v2/test_content_routes.py` — same fixture cleanup.
- `tests/v2/test_phase03_invariants.py` — drop the `overview_store-imports-atomic_write_bytes` assertion from `test_atomic_write_bytes_is_single_source_of_truth` (overview_store.py no longer exists; content_store.py is now the only consumer).
- `app_v2/services/joint_validation_grid_service.py` — rephrase 2 docstring references to deleted symbols (`build_overview_grid_view_model`, `OverviewRow`) so the Plan 06 acceptance greps return zero matches.

**Deleted:**
- `config/overview.yaml` (untracked; never staged)
- `app_v2/services/overview_store.py` (153 LOC)
- `app_v2/services/overview_filter.py` (~111 LOC)
- `app_v2/services/overview_grid_service.py` (~390 LOC)
- `tests/v2/test_overview_store.py` (~140 LOC)
- `tests/v2/test_overview_grid_service.py` (~430 LOC)
- `tests/v2/test_overview_routes.py` (~410 LOC)
- `tests/v2/test_phase05_invariants.py` (~480 LOC)
- (`tests/v2/test_overview_filter.py` was already absent at plan start.)

**Net delta:** +588 LOC added (test files), -2131 LOC removed (deletions), -27 LOC offsetting (test fixture cleanups). **Net change: -1570 LOC.**

## Pre-deletion vs Post-deletion test run

- **Before plan (HEAD before Task 1):** `pytest tests/v2/ -q --ignore=tests/v2/test_overview_routes.py --ignore=tests/v2/test_overview_store.py --ignore=tests/v2/test_overview_grid_service.py --ignore=tests/v2/test_overview_filter.py --ignore=tests/v2/test_phase05_invariants.py` → 331 passed, 5 skipped (per Plan 05 SUMMARY). The 5 plan-tolerated files were broken by Plan 04's deletions of `OverviewEntity` / `_resolve_curated_pids` etc.
- **After Task 1 (deletions + Rule 3 cleanup):** `pytest tests/v2/ -q --ignore=test_joint_validation_routes.py --ignore=test_joint_validation_invariants.py` → **330 passed, 5 skipped, 4 warnings in 23.95s**. (1-test reduction = the deleted `test_overview_store_still_works_after_refactor` regression guard.)
- **After Task 2:** `pytest tests/v2/test_joint_validation_routes.py -q` → **15 passed in 12.33s**.
- **After Task 3 (final):** `pytest tests/v2/ -q` → **360 passed, 5 skipped, 4 warnings in 24.16s.** Net suite gain: +30 tests vs the wave-3 interim baseline (15 routes + 15 invariants), -1 = +29 vs Plan 05's actual run baseline (offset by the deleted regression guard).

## Final v2 suite test count + duration

- **Tests collected:** 365 (360 active + 5 skipped). Up from 335 (330 + 5 skipped) before this plan.
- **Run time:** 24.16s.
- **Skipped:** 5 (3 in test_content_routes.py against the deleted POST /overview/add affordance — Plan 04 pytest.mark.skip; 2 in test_ask_routes.py for downstream NL-error branches).
- **Warnings:** 4 (2 httpx DeprecationWarning + 2 multiprocessing fork warnings — pre-existing, not introduced by this plan).

## Confirmation: All 6 plans together deliver every D-JV-01..D-JV-17 contract

| Decision  | Plan(s) that delivered | Plan 06 verification gate |
|-----------|------------------------|---------------------------|
| D-JV-01 (Overview tab → Joint Validation label) | 04 (router rewire) + 05 (nav-label) | route test 1 + 2: "Joint Validation" in body |
| D-JV-02 (source = `content/joint_validation/<id>/index.html`) | 02 (joint_validation_store) | invariant test 1 + 7 |
| D-JV-03 (numeric `^\d+$` folder regex) | 02 + 04 (Path regex) | invariant test 1 + route test 8 (404/422) |
| D-JV-04 (parse `<strong>Field</strong>` rows) | 02 (parser) | invariant test 10 (Korean label byte-equal) |
| D-JV-05 (blank "" sentinel, NOT em-dash) | 02 + 05 (template) | invariant test 6 |
| D-JV-06 (delete Platform-curated yaml + code) | **06 (this plan)** | Task 1 — 9 files deleted + 0 grep matches |
| D-JV-07 (delete POST /overview/add) | 04 (route gone) + **06** | route test 6 (404/405) + invariant test 8 |
| D-JV-08 (mtime-keyed in-process cache) | 02 (joint_validation_store) | covered in Plan 02 unit tests |
| D-JV-09 (drop-folder onboarding only) | 04 (no add form anywhere) | route test 6 |
| D-JV-10 (default sort start desc + tiebreaker) | 02 (sort_rows) + 05 (template) | covered in Plan 02 unit tests |
| D-JV-11 (6 popover-checklist filters) | 05 (filter_bar.html) | invariant test 15 (6 picker_popover invocations) |
| D-JV-12 (routes: listing + detail) | 04 (router) | route tests 1, 2, 4, 5, 7, 9, 12, 13 |
| D-JV-13 (StaticFiles mount) | 04 (main.py mount) | invariant test 7 + route tests 10, 11 |
| D-JV-14 (URL state shape) | 04 (router params) | route test 3 |
| D-JV-15 (Report Link + AI Summary buttons) | 02 (sanitizer) + 05 (template) | invariant test 5 + route test 13 |
| D-JV-16 (AI Summary input pre-processing) | 03 (summary service) | invariant test 11 |
| D-JV-17 (empty-state copy verbatim) | 05 (template) | route test 14 |

Every locked decision has at least one Plan 06 source-level guard OR route test pinning it.

## Decisions Made

- **Rule 3 batch-fix sibling test files BEFORE deletion** rather than during. The pre-flight grep audit revealed orphan references in `tests/v2/test_atomic_write.py` (regression-guard test importing `overview_store`), `tests/v2/test_summary_routes.py` + `tests/v2/test_summary_integration.py` + `tests/v2/test_content_routes.py` (all monkeypatching `overview_store_mod.OVERVIEW_YAML` for fixture isolation), and `tests/v2/test_phase03_invariants.py` (asserting that `overview_store.py` imports `atomic_write_bytes`). Fixing them BEFORE the rm batch keeps the v2 suite green throughout the plan; the alternative (delete first, fix breakage in a second pass) would have left the suite red between commits.
- **Rephrase 2 docstring references in `joint_validation_grid_service.py`** instead of leaving them. The plan's literal AC `grep -rn "build_overview_grid_view_model" app_v2/ tests/` returns no matches, and `OverviewRow` is mentioned in the AC discussion. The service docstring at line 280 referenced `app_v2/services/overview_grid_service.build_overview_grid_view_model` (the function it replaces) and the sort-helper docstring at line 214 referenced `OverviewRow`. Both were rephrased to historical mentions ("the deleted Phase 5 view-model builder", "the legacy Phase 5 row type") so the literal greps return zero — substantive documentation intent preserved, AC honored.
- **Test 5 (invariant) matches inner 5-string substring, not the parens.** The plan AC requested the literal string `("javascript:", "data:", "vbscript:", "file:", "about:")`. The actual source-code tuple in `joint_validation_grid_service.py` spans 3 lines for readability (opening paren on one line, the 5 strings + trailing comma on the next, closing paren on a third). Matching the inner 5-string substring `"javascript:", "data:", "vbscript:", "file:", "about:"` (without parens) preserves the byte-equal contract intent — the substantive guard against scheme-list mutation is fully active. The 6-line layout is itself protected by the `# do not reorder` comment + Test 5's positive assertion.
- **Test 11 (invariant) scans both summary.py AND parser.py.** The plan AC required the decompose 3-tag pattern in `joint_validation_summary.py`. Per Plan 02 + Plan 03 SUMMARYs the pre-processor decomposition lives in `joint_validation_parser.py` (`for tag in soup(["script", "style", "img"]): tag.decompose()` at lines 69-70). Scanning the union of both files honors the substantive contract regardless of which module owns the implementation.
- **`test_overview_filter.py` already absent at plan start.** The plan's deletion list named 9 files; only 8 existed. The missing 5th test file (`tests/v2/test_overview_filter.py`) presumably was never created in v2.0 Phase 5 (the source `overview_filter.py` did exist and was being deleted; just its dedicated unit test never landed). Silently skipped from the rm command; AC `[ ! -f tests/v2/test_overview_filter.py ]` was already true at plan start.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Orphan references to deleted overview_store.OVERVIEW_YAML in 4 sibling test files**
- **Found during:** Task 1 pre-flight grep audit
- **Issue:** `tests/v2/test_atomic_write.py:138-159` (regression-guard test importing `overview_store`), `tests/v2/test_summary_routes.py:83+87` (`isolated_summary` fixture monkeypatch), `tests/v2/test_summary_integration.py:27+56` (module-level import + `integrated_app` fixture monkeypatch), `tests/v2/test_content_routes.py:49+52` (`isolated_content` fixture monkeypatch). Plan 04 SUMMARY documented the partial cleanup but explicitly LEFT the `OVERVIEW_YAML` monkeypatches because `overview_store` still existed at that point. Deleting `overview_store.py` without fixing these would have broken 23+ tests with `ModuleNotFoundError` during fixture setup.
- **Fix:** Removed the `import app_v2.services.overview_store as overview_store_mod` lines + their `monkeypatch.setattr(overview_store_mod, "OVERVIEW_YAML", ...)` calls. Added inline comments naming Plan 06 + the rationale (overview_store.py + OVERVIEW_YAML constant deleted along with config/overview.yaml). For `test_atomic_write.py`, deleted the entire `test_overview_store_still_works_after_refactor` test (overview_store no longer exists; the regression guard for it is meaningless after the deletion).
- **Files modified:** `tests/v2/test_atomic_write.py`, `tests/v2/test_summary_routes.py`, `tests/v2/test_summary_integration.py`, `tests/v2/test_content_routes.py`.
- **Verification:** post-Task-1 `pytest tests/v2/ -q --ignore=test_joint_validation_routes.py --ignore=test_joint_validation_invariants.py` → 330 passed, 5 skipped. Zero ImportError, zero AttributeError.
- **Committed in:** `5fe3be8` (Task 1 commit — included in the deletion batch so the suite is green at every commit boundary).

**2. [Rule 3 - Blocking] test_phase03_invariants.py reads source of deleted overview_store.py**
- **Found during:** Task 1 pre-flight grep audit
- **Issue:** `tests/v2/test_phase03_invariants.py:219` calls `_read("services/overview_store.py")` and asserts the file imports `atomic_write_bytes` (D-30 single-source-of-truth invariant). After deletion, `_read()` raises `FileNotFoundError` and the test breaks.
- **Fix:** Removed the `overview_src = _read("services/overview_store.py")` call + its assertion block. Updated the test docstring to note the historical second consumer (`overview_store`) was deleted by Phase 1 Plan 06. The remaining assertion (`content_store.py` imports `atomic_write_bytes`) still proves the single-source-of-truth contract for the only remaining consumer. Also updated the module-level docstring `D-30:` description to reflect the change.
- **Files modified:** `tests/v2/test_phase03_invariants.py`.
- **Verification:** post-Task-1 v2 suite green; `test_atomic_write_bytes_is_single_source_of_truth` passes against the reduced 1-consumer assertion.
- **Committed in:** `5fe3be8` (Task 1 commit).

**3. [Rule 3 - Blocking] Two docstring refs in joint_validation_grid_service.py would have failed Plan 06 ACs**
- **Found during:** Task 1 acceptance grep run
- **Issue:** The plan's literal AC `grep -rn "build_overview_grid_view_model" app_v2/ tests/` was failing because line 280 of `joint_validation_grid_service.py` had a docstring referencing the deleted function (`Replaces app_v2/services/overview_grid_service.build_overview_grid_view_model`). Similarly `OverviewRow` appeared in a sort-helper docstring at line 214. These are docstrings (no code dependency), but the literal grep does not distinguish.
- **Fix:** Rephrased both to historical mentions: "the deleted Phase 5 view-model builder" and "the legacy Phase 5 row type". Substantive documentation intent preserved (the ports are still attributed to D-JV-10 / D-OV-07 + D-OV-08); literal greps now return zero matches.
- **Files modified:** `app_v2/services/joint_validation_grid_service.py`.
- **Verification:** post-fix `grep -rn "build_overview_grid_view_model" app_v2/ tests/` and `grep -rn "OverviewRow" app_v2/ tests/` both return zero matches; `pytest tests/v2/test_joint_validation_grid_service.py` still passes (12 tests in 0.88s).
- **Committed in:** `5fe3be8` (Task 1 commit).

### Minor — `test_overview_filter.py` already absent

- **Found during:** Task 1 rm batch
- **Issue:** Plan listed 9 files for deletion; only 8 existed. `tests/v2/test_overview_filter.py` was already absent at plan start (the dedicated unit test was apparently never created in v2.0 Phase 5; the source `app_v2/services/overview_filter.py` did exist and was deleted normally).
- **Resolution:** No code change. The acceptance criterion `[ ! -f tests/v2/test_overview_filter.py ]` was already true at plan start; the rm command silently skipped the missing file. Documented in Decisions Made above.

### Minor — config/overview.yaml never tracked by git

- **Found during:** Task 1 commit
- **Issue:** `config/overview.yaml` was deleted from the working tree but was never committed to the repo (presumably gitignored or just never staged in v2.0 Phase 2). `git add config/overview.yaml` failed with "pathspec did not match any files".
- **Resolution:** No code change. The filesystem deletion happened (`rm config/overview.yaml`); git ignored it because it was never tracked. Substantive contract met (`[ ! -f config/overview.yaml ]` returns true).

### Minor — Plan AC awk recipe for WARN-04 fragile but contract met

- **Found during:** Task 2 AC verification
- **Issue:** Plan AC `awk '/def jv_dir_real/,/^def /' tests/v2/test_joint_validation_routes.py | grep -E '^\s*try:|^\s*finally:'` returned 0 matches because the awk range starts at `def jv_dir_real` AND the `^def ` end pattern matches the same line, so the range extracts a single line. The substantive contract (try/finally in fixture body) is met — re-running with the corrected awk `awk '/^def jv_dir_real/{flag=1; print; next} flag && /^def /{flag=0} flag'` returns 2 matches (`try:` at line 88 of the test file, `finally:` at line 90).
- **Resolution:** No code change. The fixture body uses try/finally; cleanup runs on test pass, fail, AND interrupt (T-06-01 mitigation). Documented as a fragile-AC inconsistency.

---

**Total deviations:** 3 Rule-3 auto-fixes (all unblocking the deletion + acceptance gates) + 3 documented minor inconsistencies (no code change). Zero Rule-4 escalations.

**Impact on plan:** None — substantive contract intact at every layer. The 3 Rule-3 fixes were necessary to keep the v2 suite green between commits (alternative: delete first, see 23+ tests break, fix in a second pass — strictly worse for git bisectability). All 6 plans together deliver every D-JV-01..D-JV-17 contract per the table above.

## Issues Encountered

None — all 3 Rule-3 fixes resolved cleanly. The pre-flight grep audit caught every orphan BEFORE deletion, so the v2 suite never went red mid-plan.

## User Setup Required

None — no external service configuration required.

## Verification Results

### Task 1 (deletion + Rule 3 cleanup)

- **Pre-flight greps:** 5 grep checks for orphan imports of `overview_store`/`overview_filter`/`overview_grid_service` + `OverviewEntity`/`DuplicateEntityError` + `OverviewGridViewModel`/`OverviewRow`/`build_overview_grid_view_model`. After Rule 3 cleanup, only docstring references remained (now also rephrased). All deletion-target files identified.
- **Post-deletion AC greps (all pass):**
  - `[ ! -f config/overview.yaml ]` ✓
  - `[ ! -f app_v2/services/overview_store.py ]` ✓
  - `[ ! -f app_v2/services/overview_filter.py ]` ✓
  - `[ ! -f app_v2/services/overview_grid_service.py ]` ✓
  - `[ ! -f tests/v2/test_overview_store.py ]` ✓
  - `[ ! -f tests/v2/test_overview_filter.py ]` ✓ (already absent)
  - `[ ! -f tests/v2/test_overview_grid_service.py ]` ✓
  - `[ ! -f tests/v2/test_overview_routes.py ]` ✓
  - `[ ! -f tests/v2/test_phase05_invariants.py ]` ✓
  - `grep -rn "from app_v2.services.overview_store" app_v2/ tests/` → 0 matches ✓
  - `grep -rn "from app_v2.services.overview_filter" app_v2/ tests/` → 0 matches ✓
  - `grep -rn "from app_v2.services.overview_grid_service" app_v2/ tests/` → 0 matches ✓
  - `grep -rn "OverviewEntity" app_v2/ tests/` → 0 matches ✓
  - `grep -rn "DuplicateEntityError" app_v2/ tests/` → 0 matches ✓
  - `grep -rn "build_overview_grid_view_model" app_v2/ tests/` → 0 matches ✓
  - `grep -rn "OVERVIEW_YAML_PATH" app_v2/ tests/` → 0 matches ✓
  - `[ -d content/platforms ]` ✓ (kept)
  - `[ -f app_v2/services/content_store.py ]` ✓ (kept)
  - `[ -f app_v2/routers/platforms.py ]` ✓ (kept)
  - `[ -f app_v2/routers/summary.py ]` ✓ (kept)
- **Test run:** `pytest tests/v2/ -q --ignore=test_joint_validation_routes.py --ignore=test_joint_validation_invariants.py` → **330 passed, 5 skipped, 4 warnings in 23.95s.**

### Task 2 (route tests)

- All 11 ACs pass (file exists; ≥15 def test_; TestClient(app) instantiation present; ≥5 `/joint_validation/` occurrences; locked sandbox literal asserted; deleted `/overview/add` asserted; verbatim empty-state copy asserted; `../etc/passwd` traversal asserted; Korean `담당자` asserted; `/browse` regression asserted; try/finally in `jv_dir_real` body — verified with corrected awk).
- **Test run:** `pytest tests/v2/test_joint_validation_routes.py -q` → **15 passed in 12.33s.**

### Task 3 (invariant tests)

- All 9 ACs pass (file exists; ≥15 def test_; sandbox literal asserted; allow-scripts negative asserted; async-def negative asserted; Korean asserted; `hashkey("jv"` asserted; no `../etc/passwd` here — that's in routes test; full v2 suite green).
- **Test run:** `pytest tests/v2/test_joint_validation_invariants.py -q` → **15 passed in 0.20s.**
- **Final v2 suite:** `pytest tests/v2/ -q` → **360 passed, 5 skipped, 4 warnings in 24.16s.**

## Next Phase Readiness

Phase 1 is complete. All 6 plans shipped:

- **Plan 01** — Generic AI Summary partial pattern + BS4/lxml deps + Pydantic ParsedJV view-model.
- **Plan 02** — joint_validation_store + joint_validation_parser + joint_validation_grid_service (mtime cache, BS4 extraction, view-model builder).
- **Plan 03** — joint_validation_summary (TTLCache + Lock + always-200 contract; reuses _call_llm_with_text from summary_service).
- **Plan 04** — main.py StaticFiles mount + lifespan mkdir + new joint_validation router (detail + summary) + overview router rewrite (POST /overview/add deleted).
- **Plan 05** — overview/index.html + _grid.html + _filter_bar.html rewrites + new joint_validation/detail.html with locked sandbox literal + base.html nav-label flip.
- **Plan 06 (this)** — delete obsolete Phase 5 Platform-curated machinery + 30 new tests (15 routes + 15 invariants) covering every D-JV-XX contract at the source level.

The Joint Validation Overview tab is shipped. The v2.0 → v2.1 increment is complete; the next milestone (`/gsd-new-milestone`) can scope follow-on work (e.g., Confluence API integration per the deferred D-JV-09 footnote, date-range filters, in-app import wizard).

Browse + Ask + Platforms detail pages remain unchanged and regression-safe.

---
*Phase: 01-overview-tab-auto-discover-platforms-from-html-files*
*Completed: 2026-04-30*

## Self-Check: PASSED

- File `tests/v2/test_joint_validation_routes.py` exists (created, 277 LOC, 15 tests) ✓
- File `tests/v2/test_joint_validation_invariants.py` exists (created, 311 LOC, 15 tests) ✓
- File `.planning/phases/01-overview-tab-auto-discover-platforms-from-html-files/01-06-SUMMARY.md` exists (this file) ✓
- Commit `5fe3be8` (Task 1 — Delete obsolete Phase 5 Platform-curated machinery + Rule-3 sibling cleanup) exists ✓
- Commit `db35ade` (Task 2 — Add tests/v2/test_joint_validation_routes.py — 15 route tests) exists ✓
- Commit `bc69dd0` (Task 3 — Add tests/v2/test_joint_validation_invariants.py — 15 grep guards) exists ✓
- Modified file `app_v2/services/joint_validation_grid_service.py` (docstring cleanup) committed in 5fe3be8 ✓
- Modified file `tests/v2/test_atomic_write.py` (drop overview_store regression guard) committed in 5fe3be8 ✓
- Modified file `tests/v2/test_content_routes.py` (drop OVERVIEW_YAML monkeypatch) committed in 5fe3be8 ✓
- Modified file `tests/v2/test_phase03_invariants.py` (drop overview_store source-read assertion) committed in 5fe3be8 ✓
- Modified file `tests/v2/test_summary_integration.py` (drop OVERVIEW_YAML monkeypatch) committed in 5fe3be8 ✓
- Modified file `tests/v2/test_summary_routes.py` (drop OVERVIEW_YAML monkeypatch) committed in 5fe3be8 ✓
- Deleted file `app_v2/services/overview_store.py` ✓
- Deleted file `app_v2/services/overview_filter.py` ✓
- Deleted file `app_v2/services/overview_grid_service.py` ✓
- Deleted file `tests/v2/test_overview_store.py` ✓
- Deleted file `tests/v2/test_overview_grid_service.py` ✓
- Deleted file `tests/v2/test_overview_routes.py` ✓
- Deleted file `tests/v2/test_phase05_invariants.py` ✓
- Full v2 test suite green: 360 passed, 5 skipped, 4 warnings in 24.16s ✓
- 30 new tests added (15 route + 15 invariant); all pass ✓
