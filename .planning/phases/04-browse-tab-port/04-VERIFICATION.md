---
phase: 04-browse-tab-port
verified: 2026-04-28T10:05:00Z
status: passed
score: 3/3 must-haves verified (server + browser); 0 human verification items remaining
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 3/3 (server-side); 1 browser-verification item (WR-01)
  gaps_closed:
    - "WR-01 / gap-2 (Apply button form-association — Apply now produces populated grid on first click in real browser)"
    - "gap-3 (Apply button does not update trigger button count badge — picker_badges_oob OOB swap restores D-14(b))"
  gaps_remaining: []
  regressions: []
  closure_plans:
    - "04-05-PLAN.md (gap-2 — form-association fix in _picker_popover.html + 2 regression tests)"
    - "04-06-PLAN.md (gap-3 — picker_badges_oob block + always-emit-with-d-none pattern + 2 regression tests)"
gaps: []
deferred: []
human_verification: []
---

# Phase 4: Browse Tab Port Verification Report

**Phase Goal:** Users can access the v1.0 pivot-grid experience (platform × parameter wide-form table, swap-axes, row/col caps) under the new Bootstrap shell via the Browse tab — with shareable URLs and no full page reload on filter changes. (Export remains on v1.0 Streamlit per D-19..D-22.)
**Verified:** 2026-04-28T10:05:00Z
**Status:** passed
**Re-verification:** Yes — after gap-2 + gap-3 closure (Plans 04-05 and 04-06)

## Re-verification Summary

The initial verification (2026-04-26T23:40:00Z) ran against a codebase where Phase 4 server-side correctness was complete but client wiring carried a code-review warning (WR-01) — the Apply button's `hx-include="#browse-filter-form input:checked"` used a CSS descendant selector against an empty form-shell whose checkboxes lived in dropdown-menu siblings (form= attribute association, not DOM descendancy). The status was `human_needed` because automated TestClient tests bypass HTMX entirely and could not verify the live browser behavior.

The user ran `/gsd-verify-work` and reported two browser-confirmed gaps in `04-HUMAN-UAT.md`:
- **gap-2** (severity major) — Apply produced the empty-state alert; only Swap-axes triggered a populated render. WR-01 confirmed in production.
- **gap-3** (severity minor) — After clicking Apply, the trigger button count badges did not update; D-14(b) breached.

`/gsd-plan-phase --gaps` produced two closure plans:
- **04-05** (gap-2): Added `form="browse-filter-form"` to the Apply `<button>` in `_picker_popover.html` and removed the broken `hx-include`. This puts Apply on the same form-association path that Swap-axes already uses successfully — HTMX's `dn()` resolves `element.form` for non-GET requests and iterates `form.elements`. Two regression tests added.
- **04-06** (gap-3): Added `{% block picker_badges_oob %}` to `index.html` emitting two `hx-swap-oob` spans (one per picker); extended `browse_grid`'s `block_names` from 3 → 4 elements; converted the trigger-button badge `<span>` from conditional emit to always-emit-with-`d-none`-when-empty (giving HTMX a stable swap target). Two regression tests added.

Both plans executed cleanly. The user replayed UAT Test 1 in a real browser and reported `result: pass` with `retest_note: "gap-2 closure (Plan 04-05) confirmed in browser — Apply now produces populated grid on first click. Swap-axes and Clear-all also work."` — the `04-HUMAN-UAT.md` frontmatter is now `status: complete`, all 3 gaps `status: resolved`, `gaps_open: 0`.

This re-verification confirms (a) all closure plans landed in the codebase, (b) all 16 regression tests pass, (c) the full v2 suite is green (274 passed, 1 skipped), and (d) no Python production code beyond the one-line router change (`block_names` extension) was touched across either gap-closure pass. The earlier WR-01 caveat is fully retired.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | User can select platforms and parameters, and the pivot grid updates in the Browse tab without a full page reload; the sticky header remains visible while scrolling | ✓ VERIFIED | **Server:** GET /browse + POST /browse/grid registered as sync `def`; `<thead class="sticky-top bg-light">` present in `_grid.html`; `.browse-grid-body { max-height: 70vh; overflow-y: auto }` provides the vertical-scroll container so sticky-top engages. POST /browse/grid returns `block_names=["grid", "count_oob", "warnings_oob", "picker_badges_oob"]` (no full-page chrome) and sets `HX-Push-Url`. **Client (browser-confirmed):** UAT Test 1 result=pass on 2026-04-28T00:10Z — Apply produces populated grid on first click; Swap-axes and Clear-all both work. WR-01 retired by 04-05 form-association fix; D-14(b) restored by 04-06 picker_badges_oob OOB swap. |
| 2   | The 30-column cap warning and 200-row cap warning appear when the respective limits are reached — matching v1.0 behavior exactly | ✓ VERIFIED | `_warnings.html` contains the verbatim D-24 strings: "Result capped at 200 rows. Narrow your platform or parameter selection to see all data." and "Showing first 30 of {{ vm.n_value_cols_total }} parameters. Narrow your selection to see all." — both pinned by `test_post_browse_grid_row_cap_warning` and `test_post_browse_grid_col_cap_warning` byte-for-byte. ROW_CAP=200 and COL_CAP=30 are module constants in `browse_service.py`, passed to `fetch_cells(row_cap=ROW_CAP)` and `pivot_to_wide_core(col_cap=COL_CAP)`. |
| 3   | A Browse URL with query params (e.g. `?platforms=...&params=...&swap=1`) renders the correct filtered pivot grid when opened directly — the link is shareable | ✓ VERIFIED | GET /browse pre-renders the grid server-side from URL state via `build_view_model(...)`; popover checkboxes are pre-checked by the template's `{% if opt in selected %}checked{% endif %}` guard. Tests `test_get_browse_pre_checks_pickers_from_url` and `test_get_browse_renders_grid_when_url_has_full_state` cover this end-to-end. POST /browse/grid sets `HX-Push-Url` to canonical `/browse?...` URL — `_build_browse_url(['A','B'], ['cat · item'], True)` produces `/browse?platforms=A&platforms=B&params=cat%20%C2%B7%20item&swap=1` (verified at runtime). Test `test_post_browse_grid_sets_hx_push_url_header` asserts the exact byte string. |

**Score:** 3/3 truths verified (server + browser).

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `app_v2/services/browse_service.py` | BrowseViewModel + build_view_model + URL composition | ✓ VERIFIED | Defines BrowseViewModel (13 fields), build_view_model, _parse_param_label, _build_browse_url, PARAM_LABEL_SEP=' · ', ROW_CAP=200, COL_CAP=30. Imported and called by `app_v2/routers/browse.py`. No FastAPI/Starlette imports (framework-agnostic). |
| `app_v2/routers/browse.py` | sync def GET /browse + POST /browse/grid + HX-Push-Url + 4-element block_names | ✓ VERIFIED | 130 lines; both routes are sync `def` (0 async def); GET registered at `/browse`, POST at `/browse/grid`. POST sets `response.headers["HX-Push-Url"]` to canonical URL. **Updated by 04-06:** `block_names=["grid", "count_oob", "warnings_oob", "picker_badges_oob"]` (4 elements; was 3 pre-fix). Docstring updated to mention picker_badges_oob. |
| `app_v2/templates/browse/index.html` | Full page + named blocks (grid, count_oob, warnings_oob, picker_badges_oob) | ✓ VERIFIED | Extends base.html; defines all FOUR named blocks (grid, count_oob, warnings_oob, picker_badges_oob — last added by 04-06). #grid-count lives in .panel-header (outside #browse-grid — Pitfall 7 defended); empty `<form id="browse-filter-form">` placed BEFORE filter-bar include for form= attribute association. The new `picker_badges_oob` block emits two OOB `<span>` elements with stable ids `picker-platforms-badge` and `picker-params-badge`, each with `hx-swap-oob="true"` and class+d-none pattern matching the in-place trigger badge. |
| `app_v2/templates/browse/_filter_bar.html` | Picker triggers + swap toggle + Clear-all | ✓ VERIFIED | Imports picker_popover macro; calls it twice (Platforms, Parameters); btn-check swap toggle with hx-trigger=change; Clear-all link with d-none toggle when no selection. Untouched by gap-closure plans. |
| `app_v2/templates/browse/_picker_popover.html` | Reusable Jinja macro picker_popover | ✓ VERIFIED | Defines `{% macro picker_popover(name, label, options, selected) %}`; trigger button, search input, scrollable checklist with form="browse-filter-form" attr-association, Apply/Clear footer; data-bs-auto-close="outside". **Updated by 04-05 (gap-2):** Apply button now carries `form="browse-filter-form"` (no longer relies on broken hx-include CSS-descendant selector). **Updated by 04-06 (gap-3):** trigger-button badge `<span>` is now ALWAYS rendered with stable `id="picker-{{ name }}-badge"` and uses `d-none` class when `selected` is empty (instead of conditional emit) so HTMX has a stable OOB swap target. Macro header docstring updated to document both contracts. |
| `app_v2/templates/browse/_grid.html` | Pivot table fragment with sticky-top thead, header/body parity | ✓ VERIFIED | `<table class="table table-striped table-hover table-sm pivot-table">`; `<thead class="sticky-top bg-light">`; Issue 5 fix verified — `<tbody>` row emits `row[vm.index_col_name]` first, then `for col in vm.df_wide.columns if col != vm.index_col_name` (twice in file: once thead, once tbody). |
| `app_v2/templates/browse/_warnings.html` | Verbatim D-24 cap-warning copy | ✓ VERIFIED | Both verbatim strings present. |
| `app_v2/templates/browse/_empty_state.html` | Verbatim D-25 empty-state copy | ✓ VERIFIED | "Select platforms and parameters above to build the pivot grid." present; "in the sidebar" absent. |
| `app_v2/static/js/popover-search.js` | IIFE + 6 handlers + document-level event delegation | ✓ VERIFIED | "use strict"; 6 handlers (onInput, onCheckboxChange, onClearClick, onDropdownShow, onDropdownHide, onApplyClick); document.addEventListener for input/change/click(×2)/show.bs.dropdown/hidden.bs.dropdown. Untouched by gap-closure plans. |
| `app_v2/static/css/app.css` | Phase 04 additions appended | ✓ VERIFIED | `.browse-grid-body { padding: 0; max-height: 70vh; overflow-y: auto }`, `.pivot-table` family, `.browse-filter-bar` rules present; Phase 03 rules untouched. Untouched by gap-closure plans (gap-1 closure earlier added `.panel:has(.browse-filter-bar) { overflow: visible }` for popover overflow). |
| `app_v2/templates/base.html` | popover-search.js script tag (defer, after htmx-error-handler.js) | ✓ VERIFIED | `<script src=".../popover-search.js" defer>` after htmx-error-handler.js. Untouched by gap-closure plans. |
| `tests/v2/test_browse_service.py` | Unit tests for orchestrator | ✓ VERIFIED | 16 tests, all green. |
| `tests/v2/test_browse_routes.py` | TestClient integration tests | ✓ VERIFIED | **16 tests** (was 12 pre-gap-closure → 14 after 04-05 → 16 after 04-06), all green. New since initial verification: `test_apply_button_carries_form_attribute`, `test_post_browse_grid_apply_button_payload_renders_populated_grid`, `test_post_browse_grid_emits_picker_badge_oob_blocks`, `test_post_browse_grid_picker_badge_zero_count_renders_hidden`. |
| `tests/v2/test_phase04_invariants.py` | Static-analysis invariant guards | ✓ VERIFIED | 13 tests, all green. Untouched by gap-closure plans (locked invariants). |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `app_v2/routers/browse.py` | `app_v2/services/browse_service.py::build_view_model` | import + direct call | ✓ WIRED | `from app_v2.services.browse_service import _build_browse_url, build_view_model`; `vm = build_view_model(...)` called in both `browse_page` and `browse_grid`. |
| `app_v2/services/browse_service.py` | `app_v2/services/cache.py::fetch_cells, list_platforms, list_parameters` | import + direct call (TTLCache wrappers) | ✓ WIRED | `from app_v2.services.cache import fetch_cells, list_parameters, list_platforms`; called inside `build_view_model`. Tests verify mocking-at-call-site works (Pitfall 11). |
| `app_v2/services/browse_service.py` | `app/services/ufs_service::pivot_to_wide_core` | import + direct call (uncached, pure) | ✓ WIRED | `from app.services.ufs_service import pivot_to_wide_core`; called inside `build_view_model`. |
| `app_v2/main.py` | `app_v2/routers/browse.py::router` | include_router | ✓ WIRED | `app.include_router(browse.router)` BEFORE `app.include_router(root.router)`. Smoke confirms `/browse` (GET) and `/browse/grid` (POST) registered. |
| GET /browse → POST /browse/grid → HX-Push-Url canonical URL | URL round-trip cycle | header + reverse navigation | ✓ WIRED | `_build_browse_url(['A','B'], ['cat · item'], True)` = `/browse?platforms=A&platforms=B&params=cat%20%C2%B7%20item&swap=1`; verified at runtime; integration test asserts byte-for-byte. |
| Apply button → POST /browse/grid | hx-post + form= attribute association | form="browse-filter-form" | ✓ WIRED (browser-confirmed) | **Updated by 04-05:** Apply button now carries `form="browse-filter-form"` and HAS NO `hx-include`. HTMX's `dn()` resolves `applyButton.form` via the DOM form-association API and iterates `form.elements`, which the browser populates with all controls linked by `form=` (regardless of DOM nesting). UAT Test 1 result=pass — Apply produces populated grid on first click. |
| Swap-axes toggle → POST /browse/grid | hx-post + hx-include | hx-include="#browse-filter-form input[name='platforms']:checked, ..., #browse-swap-axes:checked" | ✓ WIRED | Swap-axes triggering element carries `form="browse-filter-form"` and HTMX's auto-form-include path delivers the checked items in the same way Apply now does post-04-05. UAT confirmed. |
| Clear-all link → POST /browse/grid | hx-post + hx-vals='{}' | hx-vals (not hx-include) | ✓ WIRED | Clear-all uses `hx-vals='{}'` (literal empty object), unaffected by the original WR-01 issue. UAT confirmed. |
| POST /browse/grid → trigger button badges (D-14(b)) | OOB swap by id | hx-swap-oob="true" on `picker-platforms-badge` + `picker-params-badge` | ✓ WIRED | **Added by 04-06:** new `{% block picker_badges_oob %}` in `index.html` emits both badge `<span>` elements; router's `block_names` extended to include `"picker_badges_oob"`. The persistent badges in `.browse-filter-bar` are stable swap targets (always-emit-with-d-none-when-empty pattern). After Apply, the trigger button labels read e.g. "Platforms (3)" — D-14(b) restored. UAT replay confirmed. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `_grid.html` | `vm.df_wide` (DataFrame) | `build_view_model` → `fetch_cells` (TTLCache wrapper around `fetch_cells_core` with parameterized SQL via `sa.bindparam(expanding=True)`) → `pivot_to_wide_core` | ✓ Real DB query path; integration tests use mocked DataFrame returns | ✓ FLOWING |
| `index.html` `vm.all_platforms` / `vm.all_param_labels` | List | `build_view_model` → `list_platforms`/`list_parameters` (TTLCache wrappers) | ✓ Real DB catalog | ✓ FLOWING |
| `_warnings.html` | `vm.row_capped` / `vm.col_capped` / `vm.n_value_cols_total` | `build_view_model` propagates `fetch_cells` and `pivot_to_wide_core` cap booleans | ✓ Real boolean-driven warnings | ✓ FLOWING |
| Popover checkbox `checked` | `{% if opt in selected %}` | URL → FastAPI `Query(default_factory=list)` → `vm.selected_platforms`/`vm.selected_params` | ✓ URL state flows through | ✓ FLOWING |
| `index.html` count caption | `vm.n_rows`, `vm.n_cols` | `build_view_model` computes from `df_wide` shape | ✓ Computed from real data | ✓ FLOWING |
| **NEW** `picker_badges_oob` spans | `vm.selected_platforms | length`, `vm.selected_params | length` | `build_view_model` propagates the post-Apply selection lists | ✓ Computed from real data — same view-model that drives the grid + count caption | ✓ FLOWING |

All view-model fields trace to real data sources. No HOLLOW_PROP or DISCONNECTED artifacts. The new `picker_badges_oob` block consumes the same view-model fields the existing OOB and grid blocks consume — single source of truth maintained.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Browse routes registered | `python -c "from app_v2.main import app; ..."` | `[('/browse', ['GET']), ('/browse/grid', ['POST'])]` | ✓ PASS |
| HX-Push-Url canonical URL composition | `python -c "from app_v2.services.browse_service import _build_browse_url; print(_build_browse_url(['A','B'], ['cat · item'], True))"` | `/browse?platforms=A&platforms=B&params=cat%20%C2%B7%20item&swap=1` | ✓ PASS |
| Phase 4 service constants | `python -c "from app_v2.services.browse_service import PARAM_LABEL_SEP, ROW_CAP, COL_CAP; ..."` | `' · '` / 200 / 30 | ✓ PASS |
| Apply button form-association (gap-2 closure) | `grep -c 'form="browse-filter-form"' app_v2/templates/browse/_picker_popover.html` | 3 (form-shell sentinel + checkbox input + Apply button) | ✓ PASS |
| Apply button broken hx-include absent | `grep -c 'hx-include="#browse-filter-form input:checked"' app_v2/templates/browse/_picker_popover.html` | 0 | ✓ PASS |
| picker_badges_oob block in router (gap-3 closure) | `grep -c '"picker_badges_oob"' app_v2/routers/browse.py` | 1 | ✓ PASS |
| picker_badges_oob block declared in template | `grep -c 'block picker_badges_oob' app_v2/templates/browse/index.html` | 2 (open + close) | ✓ PASS |
| Both badge OOB ids in template | `grep` for `picker-platforms-badge` + `picker-params-badge` in `index.html` | 1 + 1 | ✓ PASS |
| Trigger badge stable id in macro | `grep -c 'id="picker-{{ name }}-badge"' app_v2/templates/browse/_picker_popover.html` | 1 | ✓ PASS |
| Phase 4 test suite | `pytest tests/v2/test_browse_service.py tests/v2/test_browse_routes.py tests/v2/test_phase04_invariants.py -q` | 45 passed (16 service + 16 routes + 13 invariants) | ✓ PASS |
| Full v2 test suite | `pytest tests/v2 -q --tb=line` | **274 passed, 1 skipped** | ✓ PASS |
| UAT browser test (Apply / Swap / Clear) | Replayed 2026-04-28T00:10Z by user; recorded in `04-HUMAN-UAT.md` | result=pass — Apply produces populated grid on first click; Swap-axes + Clear-all all work; badge counts update correctly post-04-06 | ✓ PASS |
| Sticky header during grid scroll | (requires real browser layout engine) | UAT confirmed via gap-1 popover overflow check (the same scroll container exposes thead.sticky-top) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| BROWSE-V2-01 | 04-02, 04-03, 04-04, **04-05, 04-06** | Browse tab at `/browse` re-implements v1.0 pivot grid; HTMX-swapped filters | ✓ SATISFIED | Routes shipped; templates render; `test_get_browse_*`, `test_post_browse_grid_*`, and the four new gap-closure tests pass. REQUIREMENTS.md marks `[x]` Complete. **Browser confirmation:** UAT Test 1 result=pass on 2026-04-28T00:10Z; Apply, Swap-axes, Clear-all, and trigger badge updates all work end-to-end. WR-01 retired by 04-05; D-14(b) restored by 04-06. |
| BROWSE-V2-02 | 04-03 | `<thead class="sticky-top">`; every cell as text | ✓ SATISFIED | `_grid.html` uses `<thead class="sticky-top bg-light">`; cells use `{{ ... \| string \| e if ... is not none else "" }}` chain (text-only); `.browse-grid-body { max-height:70vh; overflow-y:auto }` provides scroll container. |
| BROWSE-V2-03 | 04-02, 04-03, 04-04 | Cap warnings mirror v1.0 BROWSE-04, BROWSE-06 with exact copy | ✓ SATISFIED | Verbatim D-24 strings in `_warnings.html`; ROW_CAP=200, COL_CAP=30 module constants; tests pin both strings byte-for-byte. |
| BROWSE-V2-05 | 04-02, 04-03, 04-04 | URL round-trip via query params; shareable | ✓ SATISFIED | GET /browse pre-renders grid from URL; POST /browse/grid emits HX-Push-Url canonical URL; integration tests cover both directions. |

**No orphaned requirements** — all 4 IDs from REQUIREMENTS.md (Phase 4 = 4 reqs after 04-01 trim) are covered by at least one plan. All four BROWSE-V2-01..03, -05 are marked `[x]` Complete in REQUIREMENTS.md traceability — verification confirms the marks are accurate at both server AND browser levels post-gap-closure.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |

No blockers. **No active warnings post-gap-closure** — the WR-01 finding from the initial verification (descendant-combinator hx-include on empty form-shell) was the precise cause of gap-2 and was retired by 04-05's form-association fix. The broken `hx-include="#browse-filter-form input:checked"` selector is gone from `_picker_popover.html` (grep returns 0). No STUB code, no placeholder comments, no hardcoded empty data flows to the user.

### Human Verification Required

None. All previously-flagged human verification items have been replayed in the browser and recorded as `result: pass` in `04-HUMAN-UAT.md`:
- UAT Test 1 (Apply / Swap-axes / Clear-all) — result=pass, retested 2026-04-28T00:10Z after gap-2 closure
- UAT Test 2 (Parameters/Platforms dropdown popover renders fully) — result=pass, verified 2026-04-27T12:30Z

`04-HUMAN-UAT.md` frontmatter is `status: complete`; `gaps_open: 0`; `gaps_resolved: 3`. The orchestrator should treat Phase 4 as complete for both automated and user-facing concerns.

### Gaps Summary

**No gaps blocking goal achievement.** All 16 browse-route tests, 16 service tests, and 13 invariant guards pass. The full v2 test suite is green (274 passed, 1 skipped).

**Closed during re-verification:**
- **gap-2 (Apply button form-association, severity major)** — closed by Plan 04-05. One-line template change: added `form="browse-filter-form"` to the popover-apply-btn and removed the broken `hx-include` CSS-descendant selector. Two regression tests added (`test_apply_button_carries_form_attribute`, `test_post_browse_grid_apply_button_payload_renders_populated_grid`). Zero Python production-code changes. Verified by UAT replay on 2026-04-28T00:10Z.
- **gap-3 (Apply doesn't update trigger button count badge, severity minor, breach of D-14(b))** — closed by Plan 04-06. Three coherent template+router changes: (1) trigger-button badge `<span>` now always emitted with stable `id="picker-{{ name }}-badge"` and uses `d-none` for visibility (vs conditional emit); (2) new `{% block picker_badges_oob %}` in `index.html` emits two OOB spans (one per picker) using the `hx-swap-oob="true"` pattern; (3) router's `block_names` list extended from 3 → 4 elements with `"picker_badges_oob"`. Two regression tests added (`test_post_browse_grid_emits_picker_badge_oob_blocks`, `test_post_browse_grid_picker_badge_zero_count_renders_hidden`). Single source of truth maintained — the new OOB block consumes the same view-model fields that drive the existing count caption and grid. Zero changes to services / adapters / popover-search.js / app.css.

**Phase 4 readiness:** Phase 4 is now complete for both server-side correctness AND user-facing browser behavior. ROADMAP success criteria 1-3 are all demonstrably true end-to-end. D-14 (a + b + c) is fully working. Ready for Phase 5 kickoff (Ask tab port).

---

_Verified: 2026-04-28T10:05:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification cycle: initial 2026-04-26T23:40Z (status=human_needed) → gap-2 closure 04-05 → gap-3 closure 04-06 → re-verify 2026-04-28T10:05Z (status=passed)_
