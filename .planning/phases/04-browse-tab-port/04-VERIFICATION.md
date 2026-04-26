---
phase: 04-browse-tab-port
verified: 2026-04-26T23:40:00Z
status: human_needed
score: 3/3 must-haves verified (automated); 1 browser verification required (WR-01)
overrides_applied: 0
gaps: []
deferred: []
human_verification:
  - test: "Apply / Swap-axes / Clear-all in a real browser (WR-01)"
    expected: "Selecting platforms+parameters in the popover and clicking Apply triggers a POST /browse/grid carrying the checked items; the grid swaps in-place; HX-Push-Url updates the URL bar to /browse?platforms=...&params=...; the Swap-axes toggle re-renders the grid with axes flipped; Clear-all empties both pickers and shows the empty-state alert."
    why_human: "WR-01 (code review warning, non-blocking). The Apply button's `hx-include=\"#browse-filter-form input:checked\"` and the swap toggle's `hx-include=\"#browse-filter-form input[name='platforms']:checked, #browse-filter-form input[name='params']:checked, #browse-swap-axes:checked\"` use the CSS descendant combinator. The empty `<form id=\"browse-filter-form\"></form>` form-shell has NO DOM descendants — picker checkboxes live inside dropdown-menu siblings and are only associated by the HTML form= attribute. CSS `:scope #browse-filter-form input:checked` selectors do NOT traverse the form= association; they require DOM descendancy. Automated TestClient tests bypass HTMX entirely (they POST form data directly via `_post_form_pairs`), so they cannot detect this. A real browser visit to /browse, ticking checkboxes in the popover, and clicking Apply will likely send an empty request body — the grid will swap to empty-state instead of the expected results. Server-side handling (route + view-model + Jinja render) is correct; only the client wiring is suspect. Spotting this in the live app requires opening DevTools Network panel and confirming the POST /browse/grid payload contains the checked platforms/params."
---

# Phase 4: Browse Tab Port Verification Report

**Phase Goal:** Users can access the v1.0 pivot-grid experience (platform × parameter wide-form table, swap-axes, row/col caps) under the new Bootstrap shell via the Browse tab — with shareable URLs and no full page reload on filter changes. (Export remains on v1.0 Streamlit per D-19..D-22.)
**Verified:** 2026-04-26T23:40:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | User can select platforms and parameters, and the pivot grid updates in the Browse tab without a full page reload; the sticky header remains visible while scrolling | ✓ VERIFIED (server-side); ⚠️ HUMAN-NEEDED (client wiring per WR-01) | Server: GET/POST /browse routes registered (sync def); `<thead class="sticky-top bg-light">` in `_grid.html:25`; `.browse-grid-body { max-height: 70vh; overflow-y: auto }` provides the scroll container so sticky-top engages. POST /browse/grid returns block_names=["grid", "count_oob", "warnings_oob"] fragments (no full-page chrome) and sets `HX-Push-Url`. Test `test_post_browse_grid_returns_fragment_not_full_page` asserts no `<html` or `class="navbar` in fragment response. **Caveat:** see WR-01 — actual hx-include selector may not capture checked items in a real browser. |
| 2   | The 30-column cap warning and 200-row cap warning appear when the respective limits are reached — matching v1.0 behavior exactly | ✓ VERIFIED | `_warnings.html` contains the verbatim D-24 strings: "Result capped at 200 rows. Narrow your platform or parameter selection to see all data." and "Showing first 30 of {{ vm.n_value_cols_total }} parameters. Narrow your selection to see all." — both pinned by `test_post_browse_grid_row_cap_warning` and `test_post_browse_grid_col_cap_warning` byte-for-byte. ROW_CAP=200 and COL_CAP=30 are module constants in `browse_service.py:35-36`, passed to `fetch_cells(row_cap=ROW_CAP)` and `pivot_to_wide_core(col_cap=COL_CAP)`. |
| 3   | A Browse URL with query params (e.g. `?platforms=...&params=...&swap=1`) renders the correct filtered pivot grid when opened directly — the link is shareable | ✓ VERIFIED | GET /browse pre-renders the grid server-side from URL state via `build_view_model(...)`; popover checkboxes are pre-checked by the template's `{% if opt in selected %}checked{% endif %}` guard. Tests `test_get_browse_pre_checks_pickers_from_url` and `test_get_browse_renders_grid_when_url_has_full_state` cover this end-to-end. POST /browse/grid sets HX-Push-Url to canonical /browse?... URL — `_build_browse_url(['A','B'], ['cat · item'], True)` produces `/browse?platforms=A&platforms=B&params=cat%20%C2%B7%20item&swap=1` (verified at runtime). Test `test_post_browse_grid_sets_hx_push_url_header` asserts the exact byte string. |

**Score:** 3/3 truths verified server-side (1 needs browser confirmation per WR-01)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `app_v2/services/browse_service.py` | BrowseViewModel + build_view_model + URL composition | ✓ VERIFIED | 192 lines; defines BrowseViewModel (13 fields), build_view_model, _parse_param_label, _build_browse_url, PARAM_LABEL_SEP=" · ", ROW_CAP=200, COL_CAP=30. Imported and called by `app_v2/routers/browse.py`. No FastAPI/Starlette imports (framework-agnostic). |
| `app_v2/routers/browse.py` | sync def GET /browse + POST /browse/grid + HX-Push-Url | ✓ VERIFIED | 128 lines; both routes are sync `def` (0 async def); GET registered at `/browse`, POST at `/browse/grid`. POST sets `response.headers["HX-Push-Url"]` to canonical URL. Imports build_view_model from browse_service. |
| `app_v2/templates/browse/index.html` | Full page + named blocks (grid, count_oob, warnings_oob) | ✓ VERIFIED | 82 lines; extends base.html; defines all three named blocks; #grid-count lives in .panel-header (outside #browse-grid — Pitfall 7 defended); empty `<form id="browse-filter-form">` placed BEFORE filter-bar include for form= attribute association. |
| `app_v2/templates/browse/_filter_bar.html` | Picker triggers + swap toggle + Clear-all | ✓ VERIFIED | 67 lines; imports picker_popover macro; calls it twice (Platforms, Parameters); btn-check swap toggle with hx-trigger=change; Clear-all link with d-none toggle when no selection. **WR-01 caveat:** hx-include selectors use descendant combinator. |
| `app_v2/templates/browse/_picker_popover.html` | Reusable Jinja macro picker_popover | ✓ VERIFIED | 92 lines; defines `{% macro picker_popover(name, label, options, selected) %}`; trigger button, search input, scrollable checklist with form="browse-filter-form" attr-association, Apply/Clear footer; data-bs-auto-close="outside". **WR-01 caveat:** Apply button's hx-include uses descendant combinator. |
| `app_v2/templates/browse/_grid.html` | Pivot table fragment with sticky-top thead, header/body parity | ✓ VERIFIED | 49 lines; `<table class="table table-striped table-hover table-sm pivot-table">`; `<thead class="sticky-top bg-light">`; Issue 5 fix verified — `<tbody>` row emits `row[vm.index_col_name]` first, then `for col in vm.df_wide.columns if col != vm.index_col_name` (twice in file: once thead, once tbody). |
| `app_v2/templates/browse/_warnings.html` | Verbatim D-24 cap-warning copy | ✓ VERIFIED | 18 lines; both verbatim strings present. |
| `app_v2/templates/browse/_empty_state.html` | Verbatim D-25 empty-state copy | ✓ VERIFIED | 9 lines; "Select platforms and parameters above to build the pivot grid." present; "in the sidebar" absent. |
| `app_v2/static/js/popover-search.js` | IIFE + 6 handlers + document-level event delegation | ✓ VERIFIED | 79 lines; "use strict" on line 3; 6 handlers (onInput, onCheckboxChange, onClearClick, onDropdownShow, onDropdownHide, onApplyClick); document.addEventListener for input/change/click(×2)/show.bs.dropdown/hidden.bs.dropdown. |
| `app_v2/static/css/app.css` | Phase 04 additions appended | ✓ VERIFIED | `.browse-grid-body { padding: 0; max-height: 70vh; overflow-y: auto }`, `.pivot-table` family, `.browse-filter-bar` rules present; Phase 03 rules untouched. |
| `app_v2/templates/base.html` | popover-search.js script tag (defer, after htmx-error-handler.js) | ✓ VERIFIED | line 25: `<script src=".../popover-search.js" defer>` after htmx-error-handler.js (line 20). |
| `tests/v2/test_browse_service.py` | Unit tests for orchestrator | ✓ VERIFIED | 16 tests, all green. |
| `tests/v2/test_browse_routes.py` | TestClient integration tests | ✓ VERIFIED | 12 tests, all green. |
| `tests/v2/test_phase04_invariants.py` | Static-analysis invariant guards | ✓ VERIFIED | 13 tests, all green. |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `app_v2/routers/browse.py` | `app_v2/services/browse_service.py::build_view_model` | import + direct call | ✓ WIRED | `from app_v2.services.browse_service import _build_browse_url, build_view_model` (line 22); `vm = build_view_model(...)` called in both `browse_page` and `browse_grid`. |
| `app_v2/services/browse_service.py` | `app_v2/services/cache.py::fetch_cells, list_platforms, list_parameters` | import + direct call (TTLCache wrappers) | ✓ WIRED | `from app_v2.services.cache import fetch_cells, list_parameters, list_platforms`; called inside `build_view_model`. Tests verify mocking-at-call-site works (Pitfall 11). |
| `app_v2/services/browse_service.py` | `app/services/ufs_service::pivot_to_wide_core` | import + direct call (uncached, pure) | ✓ WIRED | `from app.services.ufs_service import pivot_to_wide_core`; called inside `build_view_model`. |
| `app_v2/main.py` | `app_v2/routers/browse.py::router` | include_router | ✓ WIRED | Line 154: `app.include_router(browse.router)` BEFORE `app.include_router(root.router)` (line 155). Smoke test confirms `/browse` (GET) and `/browse/grid` (POST) registered. |
| GET /browse → POST /browse/grid → HX-Push-Url canonical URL | URL round-trip cycle | header + reverse navigation | ✓ WIRED (server-side) | `_build_browse_url(['A','B'], ['cat · item'], True)` = `/browse?platforms=A&platforms=B&params=cat%20%C2%B7%20item&swap=1`; verified at runtime; integration test asserts byte-for-byte. |
| Apply button → POST /browse/grid | hx-post + hx-include | hx-include="#browse-filter-form input:checked" | ⚠️ NOT_WIRED (browser) | **WR-01:** the empty form-shell has no DOM descendants; checkboxes use form= attribute association which CSS descendant combinator does not traverse. Tests bypass HTMX (POST directly), so this gap doesn't surface in CI. |
| Swap-axes toggle → POST /browse/grid | hx-post + hx-include | hx-include="#browse-filter-form input[name='platforms']:checked, ..., #browse-swap-axes:checked" | ⚠️ NOT_WIRED (browser) | Same WR-01 issue — `#browse-filter-form input[name='platforms']:checked` requires DOM descendancy. The third selector `#browse-swap-axes:checked` works (direct ID lookup, not descendant). |
| Clear-all link → POST /browse/grid | hx-post + hx-vals='{}' | hx-vals (not hx-include) | ✓ WIRED (browser) | Clear-all uses `hx-vals='{}'` (literal empty object) instead of hx-include, so it does NOT depend on the form-shell descendancy bug. Functions correctly in browser. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `_grid.html` | `vm.df_wide` (DataFrame) | `build_view_model` → `fetch_cells` (TTLCache wrapper around `fetch_cells_core` with parameterized SQL via `sa.bindparam(expanding=True)`) → `pivot_to_wide_core` | ✓ Real DB query path; integration tests use mocked DataFrame returns | ✓ FLOWING |
| `index.html` `vm.all_platforms` / `vm.all_param_labels` | List | `build_view_model` → `list_platforms`/`list_parameters` (TTLCache wrappers) | ✓ Real DB catalog | ✓ FLOWING |
| `_warnings.html` | `vm.row_capped` / `vm.col_capped` / `vm.n_value_cols_total` | `build_view_model` propagates `fetch_cells` and `pivot_to_wide_core` cap booleans | ✓ Real boolean-driven warnings | ✓ FLOWING |
| Popover checkbox `checked` | `{% if opt in selected %}` | URL → FastAPI `Query(default_factory=list)` → `vm.selected_platforms`/`vm.selected_params` | ✓ URL state flows through | ✓ FLOWING |
| `index.html` count caption | `vm.n_rows`, `vm.n_cols` | `build_view_model` computes from `df_wide` shape | ✓ Computed from real data | ✓ FLOWING |

All view-model fields trace to real data sources. No HOLLOW_PROP or DISCONNECTED artifacts.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Browse routes registered | `python -c "from app_v2.main import app; ..."` | `[('/browse', ['GET']), ('/browse/grid', ['POST'])]` | ✓ PASS |
| HX-Push-Url canonical URL composition | `python -c "from app_v2.services.browse_service import _build_browse_url; print(_build_browse_url(['A','B'], ['cat · item'], True))"` | `/browse?platforms=A&platforms=B&params=cat%20%C2%B7%20item&swap=1` | ✓ PASS |
| Phase 4 test suite | `pytest tests/v2/test_browse_service.py tests/v2/test_browse_routes.py tests/v2/test_phase04_invariants.py -q` | 41 passed | ✓ PASS |
| Full v2 test suite | `pytest tests/v2 -q` | 270 passed, 1 skipped | ✓ PASS |
| Apply button click → POST /browse/grid carries checked checkboxes | (requires real browser DevTools) | ? not testable in CI | ? SKIP (WR-01 — needs human) |
| Sticky header stays visible during grid scroll | (requires real browser layout engine) | ? not testable in CI | ? SKIP (UI behavior) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| BROWSE-V2-01 | 04-02, 04-03, 04-04 | Browse tab at `/browse` re-implements v1.0 pivot grid; HTMX-swapped filters | ✓ SATISFIED (server) / ? NEEDS HUMAN (browser per WR-01) | Routes shipped; templates render; `test_get_browse_*` and `test_post_browse_grid_*` pass. REQUIREMENTS.md marks `[x]` Complete. **However** the HTMX-swapped filter behavior depends on hx-include resolution which WR-01 flags as suspect. Manual browser test required to confirm Apply/Swap actually carry filter state. |
| BROWSE-V2-02 | 04-03 | `<thead class="sticky-top">`; every cell as text | ✓ SATISFIED | `_grid.html:25` `<thead class="sticky-top bg-light">`; cells use `{{ ... \| string \| e if ... is not none else "" }}` chain (text-only); `.browse-grid-body { max-height:70vh; overflow-y:auto }` provides scroll container. |
| BROWSE-V2-03 | 04-02, 04-03, 04-04 | Cap warnings mirror v1.0 BROWSE-04, BROWSE-06 with exact copy | ✓ SATISFIED | Verbatim D-24 strings in `_warnings.html`; ROW_CAP=200, COL_CAP=30 module constants; tests pin both strings byte-for-byte. |
| BROWSE-V2-05 | 04-02, 04-03, 04-04 | URL round-trip via query params; shareable | ✓ SATISFIED | GET /browse pre-renders grid from URL; POST /browse/grid emits HX-Push-Url canonical URL; integration tests cover both directions. |

**No orphaned requirements** — all 4 IDs from REQUIREMENTS.md (Phase 4 = 4 reqs after 04-01 trim) are covered by at least one plan.

**Note on REQUIREMENTS.md status:** all four BROWSE-V2-01..03, -05 are already marked `[x]` Complete in the traceability table (lines 139-142). Verification confirms the marks are accurate at the server level; the WR-01 caveat does not invalidate them but does require browser confirmation before the user-facing behavior can be claimed end-to-end.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `app_v2/templates/browse/_picker_popover.html` | 81 | `hx-include="#browse-filter-form input:checked"` — descendant combinator on empty form-shell | ⚠️ Warning (WR-01, surfaced by code review) | Apply button likely sends empty body in real browser; tests bypass HTMX so CI passes. Manual browser test required. |
| `app_v2/templates/browse/_filter_bar.html` | 41 | `hx-include="#browse-filter-form input[name='platforms']:checked, ..."` — descendant combinator on empty form-shell | ⚠️ Warning (WR-01) | Swap-axes toggle similarly affected; the third `#browse-swap-axes:checked` selector works (direct ID), but the first two will not match anything in the browser. |

No blockers, no STUB code, no placeholder comments, no hardcoded empty data flows to the user.

### Human Verification Required

#### 1. Apply / Swap-axes / Clear-all in a real browser (WR-01)

**Test:**
1. Start the FastAPI app: `.venv/bin/uvicorn app_v2.main:app --port 8000`
2. Open DevTools → Network panel
3. Visit `http://localhost:8000/browse`
4. Click the "Platforms" picker, tick 2-3 platforms
5. Click the "Parameters" picker, tick 2-3 parameter labels
6. Click "Apply"
7. Inspect the POST /browse/grid request payload in DevTools

**Expected:**
- The POST body should contain `platforms=...&platforms=...&params=...&params=...` matching the checked items
- The grid should swap to show the pivot table with those filters
- The URL bar should update to `/browse?platforms=...&params=...` (HX-Push-Url)
- Toggle "Swap axes" → grid should re-render with axes flipped (index column changes from PLATFORM_ID to Item)
- Click "Clear all" → grid should swap to the empty-state alert

**If Apply sends an empty body** (the WR-01 prediction):
- The grid swaps to "Select platforms and parameters above to build the pivot grid."
- The URL bar updates to `/browse` with no query string

**Why human:** Automated TestClient tests bypass HTMX entirely (they POST form data directly via the `_post_form_pairs` helper). The actual hx-include CSS selector resolution happens in the browser DOM at request-build time. Confirming whether `#browse-filter-form input:checked` finds the checked checkboxes (when those checkboxes are inside dropdown-menu siblings of the empty form-shell, associated by `form="browse-filter-form"` attribute) requires running the live browser.

**If WR-01 is confirmed, the fix is small:** change the hx-include selector from descendant-of-form to attribute-association-aware. Two viable forms:
- Use `[form="browse-filter-form"]:checked` (CSS attribute selector, works regardless of DOM nesting)
- Use `input[name="platforms"]:checked, input[name="params"]:checked, #browse-swap-axes:checked` scoped only by name (no form-shell anchor)

### Gaps Summary

**No automated gaps blocking goal achievement.** All 41 Phase 4 tests pass; all 270 v2 suite tests pass (1 skipped — Phase 1 stub tombstone); all 13 invariant guards pass.

**One human-needed item (WR-01):** The hx-include selector for the Apply button and Swap-axes toggle uses CSS descendant combinator (`#browse-filter-form input:checked`) against an empty form-shell where the actual checkboxes sit in dropdown-menu siblings, associated only by `form=` attribute. This pattern is documented as Pitfall 4 in 04-RESEARCH.md and the templates explicitly call out the form= attribute association — but the chosen hx-include CSS selector does not honor that association. CSS descendant combinator only traverses DOM children, not form= attribute relationships.

The bug surfaces only in a real browser, not in TestClient tests. Server-side correctness is fully verified — the route, view-model, Jinja render, HX-Push-Url, security mitigations (XSS escape, SQL bind), and copy invariants are all intact. If a real browser shows that Apply does carry the checked items (e.g. via some HTMX behavior I'm not seeing), the warning is moot. If it shows an empty payload as predicted, a one-line selector change fixes it.

The Clear-all link (uses `hx-vals='{}'` instead of hx-include) is unaffected by WR-01 and works correctly.

### Code Review Cross-Reference

The just-completed code review reported:
- **0 critical, 5 warnings, 6 info findings (all non-blocking, advisory)**
- **WR-01** is the most material warning: `hx-include` selector + empty form-shell mismatch
- The other 4 warnings + 6 info findings are not surfaced here (they are advisory polish items per the user's note)

Verifier disposition: **Status set to `human_needed`** because WR-01 maps directly to ROADMAP success criterion #1 ("the pivot grid updates in the Browse tab without a full page reload") — a behavior that automated tests cannot validate end-to-end. Recommend running the browser test before marking Phase 4 complete in the human-facing sense; or accept the deviation explicitly via an override entry if the user has already confirmed WR-01 is intended.

---

_Verified: 2026-04-26T23:40:00Z_
_Verifier: Claude (gsd-verifier)_
