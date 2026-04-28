---
phase: 04-browse-tab-port
verified: 2026-04-28T13:15:00Z
status: human_needed
score: 3/3 must-haves server-verified; 1 human verification item remaining (UAT browser replay of all 4 D-15a close-event branches)
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 3/3 (server + browser, after gap-2 + gap-3 closure on 2026-04-28T10:05Z)
  cycle: 3
  gaps_closed:
    - "WR-01 / gap-2 (Apply button form-association — Apply now produces populated grid on first click in real browser) [closed 04-05]"
    - "gap-3 (Apply button does not update trigger button count badge — picker_badges_oob OOB swap restores D-14(b)) [closed 04-06]"
    - "gap-4 (outside-click on popover should auto-Apply — D-15 amended + D-15a close-event taxonomy locked; popover-search.js implements 4-branch onDropdownHide via implicit-Apply through programmatic .popover-apply-btn.click()) [closed 04-07]"
    - "REVIEW WR-01 (dataset.applied/cancelling state leak between close cycles — fixed in commit 6b97921 by clearing both flags at start of onDropdownShow)"
    - "REVIEW WR-02 (dead-code Object.prototype.toString Array guard — replaced with Array.isArray in commit 6b97921)"
  gaps_remaining: []
  regressions: []
  closure_plans:
    - "04-05-PLAN.md (gap-2 — form-association fix in _picker_popover.html + 2 regression tests)"
    - "04-06-PLAN.md (gap-3 — picker_badges_oob OOB block + always-emit-with-d-none pattern + 2 regression tests)"
    - "04-07-PLAN.md (gap-4 — D-15a close-event taxonomy in popover-search.js: capture-phase keydown listener + 4-branch onDropdownHide + _selectionsEqual helper + 2 regression tests + 1 Phase 4 invariant)"
  review_findings_addressed:
    - "WR-01 (dataset.applied leak across close cycles → broken Esc-revert after no-op close)"
    - "WR-02 (dead-code operator-precedence bug in _selectionsEqual Array guard)"
  review_findings_deferred:
    - "WR-03 (e.target.querySelector() reach mismatch with Bootstrap dropdown event target — pre-existing pattern, not introduced by 04-07; UAT replay confirmed runtime behavior matches expectation; will revisit if browser DevTools reveals any issue during the final UAT pass)"
gaps: []
deferred: []
human_verification:
  - test: "Browser UAT replay of all 4 D-15a close-event branches in real Chrome/Firefox/Safari"
    expected: |
      After starting `.venv/bin/uvicorn app_v2.main:app --port 8000` and visiting http://localhost:8000/browse:
      (1) IMPLICIT-APPLY via outside-click: Open Platforms picker, tick 3 platforms, click on the page background — popover closes, grid swaps with the 3 platforms, trigger badge reads "Platforms 3", URL bar updates to /browse?platforms=...
      (2) EXPLICIT-CANCEL via Esc: Open Platforms picker (with current count=3), tick a 4th, press Esc — popover closes, trigger badge stays at "Platforms 3", grid does NOT re-swap, no POST in DevTools Network panel.
      (3) NO-OP SHORT-CIRCUIT: Open Platforms picker (no checkbox change), click outside — popover closes, no POST in Network panel, no grid swap, badge unchanged.
      (4) IMPLICIT-APPLY via click-on-other-trigger: With Platforms popover open and a pending checkbox change, click the Parameters trigger — Platforms popover closes (commits the pending change), Parameters popover opens, grid swaps for Platforms only.
      (5) WR-01 regression check: Open picker (no change), close (branch iii fires); reopen, tick a box, press Esc — checkbox MUST revert to unchecked (pre-fix this was broken because dataset.applied leaked across cycles).
    why_human: "TestClient cannot exercise the JS-side close-event distinguisher; Bootstrap dropdown lifecycle events, capture-phase keydown timing, and programmatic button click only run in a real browser. Server-side regression tests pin the HTTP contract; static-grep invariant pins the JS markers; the actual UX behavior requires human + browser confirmation. UAT frontmatter `status: diagnosed` reflects the same intent — flip to `status: complete` only after this replay passes."
---

# Phase 4: Browse Tab Port Verification Report

**Phase Goal:** Users can access the v1.0 pivot-grid experience (platform × parameter wide-form table, swap-axes, row/col caps) under the new Bootstrap shell via the Browse tab — with shareable URLs and no full page reload on filter changes. (Export remains on v1.0 Streamlit per D-19..D-22.)
**Verified:** 2026-04-28T13:15:00Z
**Status:** human_needed
**Re-verification:** Yes — third re-verification cycle, after gap-4 closure (Plan 04-07) + REVIEW WR-01/WR-02 fixes (commit 6b97921)

## Re-verification Summary

This is the **third** re-verification cycle for Phase 4:

1. **Initial verification (2026-04-26T23:40Z)** — status=human_needed, server-side complete, WR-01 caveat (browser-only check of hx-include selector against form-association DOM model).
2. **Cycle 2 (2026-04-28T10:05Z)** — after UAT surfaced gap-2 (Apply form-association) + gap-3 (badge counter staleness); plans 04-05 + 04-06 closed both; status flipped to passed.
3. **Cycle 3 (THIS REPORT, 2026-04-28T13:15Z)** — after user testing surfaced **gap-4** (outside-click should auto-Apply, contradicting the original D-15 "restore-on-close" contract); CONTEXT was amended (D-15 amended + D-15a new locked); plan 04-07 implemented the D-15a 4-branch close-event taxonomy in popover-search.js. A subsequent code review on 04-07 surfaced two warnings — **WR-01** (dataset.applied state leak between close cycles → broken Esc-revert after a no-op close) and **WR-02** (dead-code `Object.prototype.toString` Array guard inside `_selectionsEqual` due to operator-precedence) — both fixed in commit `6b97921`.

This cycle confirms (a) all 7 plans (04-01..04-07) landed in the codebase, (b) all 4 UAT gaps are `status: resolved`, (c) both REVIEW warnings (WR-01, WR-02) are resolved in commit 6b97921, (d) full v2 suite is green at **277 passed, 1 skipped** (was 274 + 1 pre-04-07; +3 new tests for D-15a), (e) all D-15a contract markers and their preconditions remain in the codebase. The UAT frontmatter is `status: diagnosed` — the user's stated intent is to replay all 4 close-event branches in a real browser before flipping to `complete`. Verification reflects this: server + automated checks all pass, but the final close-event branch behavior is JS-runtime-only and warrants human confirmation.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | User can select platforms and parameters, and the pivot grid updates in the Browse tab without a full page reload; the sticky header remains visible while scrolling | ✓ VERIFIED (server + browser to date) | **Server:** GET /browse + POST /browse/grid registered as sync `def`; `<thead class="sticky-top bg-light">` present in `_grid.html`; `.browse-grid-body { max-height: 70vh; overflow-y: auto }` provides the vertical-scroll container so sticky-top engages. POST /browse/grid returns `block_names=["grid", "count_oob", "warnings_oob", "picker_badges_oob"]` (no full-page chrome) and sets `HX-Push-Url`. **Client (cycle 2 confirmed):** UAT Test 1 result=pass on 2026-04-28T00:10Z — Apply produces populated grid on first click; Swap-axes and Clear-all both work. WR-01 retired by 04-05; D-14(b) restored by 04-06. **Cycle 3 (gap-4 D-15a):** server-side regression tests pin the implicit-Apply HTTP contract (test_post_browse_grid_implicit_apply_payload_shape, test_post_browse_grid_idempotent_unchanged_selection); static-grep invariant pins the 5 D-15a JS markers + the data-bs-auto-close="outside" template precondition. The runtime close-event UX (4 branches × WR-01 regression check) is the human verification item below. |
| 2   | The 30-column cap warning and 200-row cap warning appear when the respective limits are reached — matching v1.0 behavior exactly | ✓ VERIFIED | `_warnings.html` contains the verbatim D-24 strings; `test_post_browse_grid_row_cap_warning` and `test_post_browse_grid_col_cap_warning` pin both byte-for-byte. ROW_CAP=200 and COL_CAP=30 are module constants in `browse_service.py`. Untouched by gap-4 closure. |
| 3   | A Browse URL with query params renders the correct filtered pivot grid when opened directly — the link is shareable | ✓ VERIFIED | GET /browse pre-renders the grid server-side from URL state; popover checkboxes are pre-checked. POST /browse/grid sets `HX-Push-Url` to canonical URL. Tests `test_get_browse_pre_checks_pickers_from_url`, `test_get_browse_renders_grid_when_url_has_full_state`, `test_post_browse_grid_sets_hx_push_url_header` all pass. Untouched by gap-4 closure. |

**Score:** 3/3 truths server-verified. SC #1's runtime close-event behavior (4 D-15a branches) is the human verification item.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `app_v2/services/browse_service.py` | BrowseViewModel + build_view_model + URL composition | ✓ VERIFIED | Defines BrowseViewModel (13 fields), build_view_model, _parse_param_label, _build_browse_url, PARAM_LABEL_SEP, ROW_CAP=200, COL_CAP=30. Untouched by gap-4 closure. |
| `app_v2/routers/browse.py` | sync def GET /browse + POST /browse/grid + HX-Push-Url + 4-element block_names | ✓ VERIFIED | 130 lines; both routes sync `def`; `block_names=["grid", "count_oob", "warnings_oob", "picker_badges_oob"]`. Untouched by gap-4 closure. |
| `app_v2/templates/browse/index.html` | Full page + 4 named blocks (grid, count_oob, warnings_oob, picker_badges_oob) | ✓ VERIFIED | All four blocks present. Untouched by gap-4 closure. |
| `app_v2/templates/browse/_filter_bar.html` | Picker triggers + swap toggle + Clear-all | ✓ VERIFIED | Untouched by gap-4 closure. |
| `app_v2/templates/browse/_picker_popover.html` | Reusable Jinja macro picker_popover with form-association + stable badge id | ✓ VERIFIED | Apply button carries `form="browse-filter-form"` (gap-2); trigger badge always rendered with `id="picker-{{ name }}-badge"` and `d-none` when empty (gap-3); `data-bs-auto-close="outside"` on trigger button (D-09 precondition for D-15a). 04-07 made no template changes here (already had everything D-15a needed). |
| `app_v2/templates/browse/_grid.html` | Pivot table fragment with sticky-top thead | ✓ VERIFIED | Untouched by gap-4 closure. |
| `app_v2/templates/browse/_warnings.html` | Verbatim D-24 cap-warning copy | ✓ VERIFIED | Untouched by gap-4 closure. |
| `app_v2/templates/browse/_empty_state.html` | Verbatim D-25 empty-state copy | ✓ VERIFIED | Untouched by gap-4 closure. |
| `app_v2/static/js/popover-search.js` | IIFE + 6+ handlers + D-15a 4-branch close-event taxonomy + onKeydown + _selectionsEqual + WR-01/WR-02 fixes | ✓ VERIFIED | **203 lines (was 79 pre-04-07).** New onKeydown handler at lines 128-137 (capture-phase Esc → set dataset.cancelling=1). _selectionsEqual helper at lines 111-123 (Array.isArray guard ✓ WR-02 fixed). onDropdownShow now clears dataset.applied + dataset.cancelling at start (lines 91-92 ✓ WR-01 fixed). onDropdownHide implements 4-branch taxonomy (lines 139-187): (i) explicit Apply already ran, (ii) Esc → revert, (iii) no-op short-circuit, (iv) implicit Apply via popoverApplyBtn.click(). Capture-phase keydown listener registered at line 200. All 5 D-15a contract markers present (dataset.cancelling, capture-phase listener, .popover-apply-btn.click(), _selectionsEqual, D-15a comment citation). |
| `app_v2/static/css/app.css` | Phase 04 additions appended | ✓ VERIFIED | Untouched by gap-4 closure. |
| `app_v2/templates/base.html` | popover-search.js script tag | ✓ VERIFIED | Untouched by gap-4 closure. |
| `tests/v2/test_browse_service.py` | Unit tests for orchestrator | ✓ VERIFIED | 16 tests, all green. Untouched by gap-4 closure. |
| `tests/v2/test_browse_routes.py` | TestClient integration tests | ✓ VERIFIED | **18 tests** (was 16 pre-04-07 → +2 D-15a regression tests: test_post_browse_grid_implicit_apply_payload_shape, test_post_browse_grid_idempotent_unchanged_selection). All green. |
| `tests/v2/test_phase04_invariants.py` | Static-analysis invariant guards | ✓ VERIFIED | **14 tests** (was 13 pre-04-07 → +1 D-15a invariant: test_popover_search_js_implements_d15a_close_event_taxonomy). All green. |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `app_v2/routers/browse.py` | `app_v2/services/browse_service.py::build_view_model` | import + direct call | ✓ WIRED | Untouched by gap-4 closure. |
| `app_v2/services/browse_service.py` | `app_v2/services/cache.py::fetch_cells, list_platforms, list_parameters` | import + direct call | ✓ WIRED | Untouched by gap-4 closure. |
| `app_v2/services/browse_service.py` | `app/services/ufs_service::pivot_to_wide_core` | import + direct call | ✓ WIRED | Untouched by gap-4 closure. |
| `app_v2/main.py` | `app_v2/routers/browse.py::router` | include_router | ✓ WIRED | Untouched by gap-4 closure. |
| GET /browse → POST /browse/grid → HX-Push-Url canonical URL | URL round-trip | header + reverse navigation | ✓ WIRED | Untouched by gap-4 closure. |
| Apply button → POST /browse/grid | hx-post + form="browse-filter-form" | DOM form-association | ✓ WIRED (browser-confirmed cycle 2) | Untouched by gap-4 closure. UAT Test 1 result=pass on 2026-04-28T00:10Z. |
| Swap-axes toggle → POST /browse/grid | hx-post + form-association | hx-include="..." | ✓ WIRED | UAT confirmed cycle 2. |
| Clear-all link → POST /browse/grid | hx-post + hx-vals='{}' | hx-vals (not hx-include) | ✓ WIRED | UAT confirmed cycle 2. |
| POST /browse/grid → trigger button badges (D-14(b)) | OOB swap by id | hx-swap-oob="true" | ✓ WIRED | UAT confirmed cycle 2 after 04-06. |
| **NEW** Outside-click on popover → POST /browse/grid (D-15a IMPLICIT-APPLY) | onDropdownHide branch (iv) → popoverApplyBtn.click() | programmatic button click reuses gap-2 form-association + gap-3 OOB swap | ✓ WIRED (server contract pinned; runtime browser-only) | popover-search.js line 185-186 calls `applyBtn.click()` in branch (iv); reuses gap-2 + gap-3 wiring with zero divergent HTTP path. test_post_browse_grid_implicit_apply_payload_shape pins the resulting HTTP contract. **Runtime UX of the close-event distinguisher is the human verification item.** |
| **NEW** Esc on popover → revert from data-original-selection (D-15a EXPLICIT-CANCEL) | onKeydown sets dataset.cancelling=1 → onDropdownHide branch (ii) | capture-phase document keydown listener | ✓ WIRED (static markers verified) | popover-search.js line 128-137 + line 200 (capture-phase registration); branch (ii) at line 153-164 reverts checkboxes from JSON.parse(dataset.originalSelection). **Runtime UX is the human verification item.** |
| **NEW** No-change close → no HTMX (D-15a NO-OP SHORT-CIRCUIT) | _selectionsEqual + onDropdownHide branch (iii) | sorted-array deep equality | ✓ WIRED (Array.isArray guard fixed in 6b97921) | popover-search.js line 111-123 (_selectionsEqual with Array.isArray); line 165-176 branch (iii) sets dataset.applied=1 and returns without click. WR-01 fix (lines 91-92) ensures the next open clears dataset.applied so a subsequent Esc isn't swallowed. **Runtime UX is the human verification item.** |
| **NEW** Open popover → reset transient flags (WR-01 fix) | onDropdownShow lines 91-92 | delete root.dataset.applied + delete root.dataset.cancelling | ✓ WIRED | Commit 6b97921. Comment cites the exact failure mode (no-op short-circuit close → next Esc swallowed by branch (i)). |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `_grid.html` | `vm.df_wide` | `build_view_model` → cached `fetch_cells` → `pivot_to_wide_core` | ✓ Real DB query path | ✓ FLOWING |
| `index.html` `vm.all_platforms` / `vm.all_param_labels` | List | TTLCache wrappers | ✓ Real DB catalog | ✓ FLOWING |
| `_warnings.html` | `vm.row_capped` / `vm.col_capped` | View-model propagation | ✓ Boolean-driven | ✓ FLOWING |
| Popover checkbox `checked` | `{% if opt in selected %}` | URL → FastAPI Query → vm | ✓ URL state flows | ✓ FLOWING |
| `index.html` count caption | `vm.n_rows`, `vm.n_cols` | View-model from df_wide | ✓ Computed from real data | ✓ FLOWING |
| `picker_badges_oob` spans (gap-3) | `vm.selected_platforms\|length`, `vm.selected_params\|length` | View-model | ✓ Same source as count caption | ✓ FLOWING |
| **NEW (D-15a)** `_selectionsEqual` input | currentArr (live querySelectorAll), originalJsonStr (dataset.originalSelection set by onDropdownShow) | DOM checkbox state + JSON-stringified stash | ✓ Both sides flow from real DOM state; sorted-array comparison is order-independent; WR-02 fixed Array.isArray guard | ✓ FLOWING |

All view-model fields trace to real data. The new D-15a state machine in popover-search.js consumes the same DOM checkbox state that drives the existing onApplyClick path; the implicit-Apply branch (iv) reuses the same Apply button click (and therefore the same form-association + HTMX wiring) as explicit-Apply — single source of truth maintained across both code paths.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Browse routes registered | `python -c "from app_v2.main import app; ..."` | `[('/browse', ['GET']), ('/browse/grid', ['POST'])]` | ✓ PASS |
| Phase 4 service constants | `python -c "from app_v2.services.browse_service import PARAM_LABEL_SEP, ROW_CAP, COL_CAP"` | `' · '` / 200 / 30 | ✓ PASS |
| Apply button form-association (gap-2) | `grep -c 'form="browse-filter-form"' app_v2/templates/browse/_picker_popover.html` | 3 | ✓ PASS |
| picker_badges_oob in router (gap-3) | `grep -c '"picker_badges_oob"' app_v2/routers/browse.py` | 1 | ✓ PASS |
| picker_badges_oob block declared (gap-3) | `grep -c 'block picker_badges_oob' app_v2/templates/browse/index.html` | 2 (open + close) | ✓ PASS |
| **NEW** D-15a contract markers in popover-search.js | `grep -nE "dataset\.cancelling|popover-apply-btn.*click|_selectionsEqual|D-15a"` | 16 hits across header docstring + onKeydown + branch (ii) + _selectionsEqual + branch (iv) | ✓ PASS |
| **NEW** Capture-phase keydown listener | `grep "addEventListener\('keydown'" app_v2/static/js/popover-search.js` | line 200 with `, true` (capture phase) | ✓ PASS |
| **NEW (WR-01 fix)** Flag reset at popover open | `grep -n "delete root.dataset" app_v2/static/js/popover-search.js` | lines 91-92 inside onDropdownShow | ✓ PASS |
| **NEW (WR-02 fix)** Array.isArray guard | `grep -n "Array.isArray" app_v2/static/js/popover-search.js` | line 115 (replaces dead-code Object.prototype.toString check) | ✓ PASS |
| D-09 precondition preserved | `grep -n "data-bs-auto-close" app_v2/templates/browse/_picker_popover.html` | line 37 (trigger button) | ✓ PASS |
| Phase 4 test suite | `pytest tests/v2/test_browse_routes.py tests/v2/test_phase04_invariants.py` | 32 passed | ✓ PASS |
| Full v2 test suite | `pytest tests/v2 -q --tb=line` | **277 passed, 1 skipped** | ✓ PASS |
| Sticky header during grid scroll | (requires real browser layout engine) | UAT cycle 2 confirmed | ✓ PASS |
| Apply / Swap / Clear / badge update browser UX | UAT Test 1 cycle 2 (2026-04-28T00:10Z) | result=pass | ✓ PASS |
| **NEW** D-15a 4-branch close-event runtime UX | (requires real browser; TestClient cannot exercise JS-side distinguisher) | NOT YET REPLAYED in this cycle | ? HUMAN |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| BROWSE-V2-01 | 04-02, 04-03, 04-04, 04-05, 04-06, **04-07** | Browse tab at `/browse` re-implements v1.0 pivot grid; HTMX-swapped filters | ✓ SATISFIED (server + cycle-2 browser; cycle-3 D-15a awaits human replay) | Routes shipped; templates render; all 18 route tests + 14 invariants + 16 service tests pass; cycle-2 UAT confirmed Apply/Swap/Clear/badges; cycle-3 D-15a contract pinned at HTTP layer + JS marker layer; runtime UX is the human verification item. |
| BROWSE-V2-02 | 04-03 | `<thead class="sticky-top">`; every cell as text | ✓ SATISFIED | Untouched by gap-4 closure. |
| BROWSE-V2-03 | 04-02, 04-03, 04-04 | Cap warnings mirror v1.0 with exact copy | ✓ SATISFIED | Untouched by gap-4 closure. |
| BROWSE-V2-05 | 04-02, 04-03, 04-04 | URL round-trip via query params; shareable | ✓ SATISFIED | Untouched by gap-4 closure. |

**No orphaned requirements.** All 4 IDs from REQUIREMENTS.md (Phase 4 = 4 reqs after 04-01 trim) are covered. All four are marked `[x]` Complete in REQUIREMENTS.md traceability — verification confirms the marks are accurate at the server + automated layer; runtime D-15a close-event UX is the human verification item.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |

No blockers. The two REVIEW warnings from 04-07-REVIEW.md (WR-01 dataset.applied state-leak, WR-02 dead-code Array guard) are **resolved in commit 6b97921**. The third REVIEW finding (WR-03, e.target.querySelector reach mismatch) is a pre-existing pattern that predates 04-07 and was already exercised successfully in cycle-2 UAT (Apply / revert-on-close branches both worked). It is deferred to the final UAT replay — if DevTools shows the implicit-Apply branch fires correctly in real Bootstrap behavior, WR-03 is closeable as Info-only; otherwise the closest()-based widening fix in 04-07-REVIEW.md is the recommended remediation.

No active blockers post-fix. No STUB code, no placeholder comments. Single source of truth maintained — implicit-Apply path reuses the explicit-Apply HTMX wiring via programmatic .click() rather than rolling a divergent second hx-post.

### Human Verification Required

#### 1. Browser UAT replay of all 4 D-15a close-event branches

**Test:** Start the server (`.venv/bin/uvicorn app_v2.main:app --port 8000`), open http://localhost:8000/browse in Chrome/Firefox with DevTools Network panel open, and exercise each branch in sequence:

1. **IMPLICIT-APPLY via outside-click (branch iv):** Open Platforms picker, tick 3 platforms, click on the page background outside the popover.
   - Expected: popover closes; ONE POST to /browse/grid in Network panel; grid swaps with the 3 platforms; trigger badge reads "Platforms 3"; URL bar updates to /browse?platforms=...
2. **EXPLICIT-CANCEL via Esc (branch ii):** With trigger badge at "Platforms 3", open Platforms picker, tick a 4th platform, press Esc.
   - Expected: popover closes; NO POST in Network panel; trigger badge stays at "Platforms 3"; the 4th checkbox is unchecked on next open (revert worked).
3. **NO-OP SHORT-CIRCUIT (branch iii):** Open Platforms picker (DO NOT change anything), click outside.
   - Expected: popover closes; NO POST in Network panel; badge unchanged.
4. **IMPLICIT-APPLY via click-on-other-trigger (branch iv variant):** With Platforms popover open and a pending checkbox change, click the Parameters trigger.
   - Expected: Platforms popover closes (commits the pending change via implicit Apply); ONE POST; Parameters popover opens.
5. **WR-01 regression check (cycle-3-specific):** Open picker (no change), close (branch iii fires); reopen, tick a box, press Esc.
   - Expected: the new box MUST revert to unchecked. Pre-fix this was broken because dataset.applied leaked across close cycles, so the next Esc was swallowed by branch (i) instead of reverting per branch (ii).

**Expected (overall):** All 5 sub-tests pass per the steps above.

**Why human:** TestClient cannot exercise the JS-side close-event distinguisher; Bootstrap dropdown lifecycle events (`show.bs.dropdown` / `hidden.bs.dropdown`), capture-phase keydown timing for the Esc-detection trick, and programmatic button click only run in a real browser engine. Server-side regression tests pin the HTTP contract that the implicit-Apply path produces; the static-grep invariant pins the 5 D-15a JS markers + the `data-bs-auto-close="outside"` template precondition. The actual UX behavior across the 4 close-event branches × the WR-01 regression case requires a human + browser. UAT frontmatter `status: diagnosed` reflects the same intent — once this replay passes, flip UAT frontmatter to `status: complete` and verification status to `passed`.

### Gaps Summary

**No gaps blocking goal achievement at the automated layer.** All 277 v2 tests pass; all 4 UAT gaps are `status: resolved`; both REVIEW warnings (WR-01, WR-02) fixed in commit 6b97921; the third REVIEW finding (WR-03) is informational and pre-existing. The remaining work is a final browser UAT replay to confirm the D-15a 4-branch close-event taxonomy + the WR-01 regression case behave as designed at the runtime layer.

**Closed during cycle 3:**
- **gap-4 (outside-click should auto-Apply, severity minor, contract change against original D-15)** — closed by Plan 04-07. CONTEXT amended (D-15 amended + D-15a new locked); popover-search.js rewritten with capture-phase keydown listener (Esc detection) + 4-branch onDropdownHide (explicit Apply / Esc revert / no-op short-circuit / implicit Apply via programmatic .popover-apply-btn.click()). Reuses gap-2 form-association + gap-3 picker_badges_oob OOB swap with zero divergence from the explicit-Apply HTTP path. 2 server-side regression tests + 1 Phase 4 invariant added; suite went 274 → 277 passed.
- **REVIEW WR-01 (dataset.applied/cancelling state leak between close cycles)** — closed in commit 6b97921. `delete root.dataset.applied` + `delete root.dataset.cancelling` added at the start of `onDropdownShow` (lines 91-92) so each open-close cycle starts from a known clean state. Comment cites the exact failure mode (no-op short-circuit close → next Esc swallowed by branch (i) instead of reverting per branch (ii)).
- **REVIEW WR-02 (dead-code Array-type guard inside _selectionsEqual)** — closed in commit 6b97921. The buggy `if (!Object.prototype.toString.call(original) === '[object Array]')` line (operator-precedence trap → always false → unreachable) replaced with idiomatic `if (!Array.isArray(original)) return false;` at line 115. Duck-type fallback removed — Array.isArray is universally supported and removes the precedence trap entirely.

**Phase 4 readiness:** Phase 4 is complete at the automated and server-side layers. ROADMAP success criteria 1-3 are demonstrably true via tests + cycle-2 UAT; the cycle-3 D-15a runtime UX is the final human verification item. Once the UAT replay passes, Phase 4 is shippable; Phase 5 (Ask tab port) can kick off in parallel since Phase 5 has no Phase-4 dependencies in the ROADMAP graph (Phase 5 depends on Phase 1 + Phase 3).

---

_Verified: 2026-04-28T13:15:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification cycle 3: cycle 1 (2026-04-26T23:40Z, status=human_needed, WR-01 hx-include caveat) → cycle 2 (2026-04-28T10:05Z, status=passed after gap-2 + gap-3 closure) → cycle 3 (2026-04-28T13:15Z, status=human_needed pending D-15a 4-branch UAT replay + WR-01-regression check; gap-4 closed by 04-07; REVIEW WR-01/WR-02 closed by commit 6b97921)_
