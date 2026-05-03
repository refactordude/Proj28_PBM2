---
phase: 02-ui-shell-rewrite-browse-footer-joint-validation-layout-parit
plan: "04"
subsystem: ui-jv-pagination
tags: [htmx, pagination, oob-swap, tdd, jinja2, pydantic, bootstrap5]
requires: [02-01, 02-03]
provides: [jv-pagination, jv-footer-pagination-control, jv-page-url-roundtrip]
affects:
  - app_v2/services/joint_validation_grid_service.py
  - app_v2/routers/overview.py
  - app_v2/templates/overview/index.html
  - app_v2/templates/overview/_pagination.html
  - app_v2/templates/overview/_filter_bar.html
  - tests/v2/test_jv_pagination.py
  - tests/v2/test_phase02_invariants.py
  - .planning/phases/02-ui-shell-rewrite-browse-footer-joint-validation-layout-parit/02-UI-SPEC.md
tech-stack:
  added: []
  patterns: [htmx-oob-merge-by-id, pydantic-submodel-pagelink, jinja2-partial-single-source, tdd-service-router-template, fastapi-query-form-bounds]
key-files:
  created:
    - app_v2/templates/overview/_pagination.html
    - tests/v2/test_jv_pagination.py
  modified:
    - app_v2/services/joint_validation_grid_service.py
    - app_v2/routers/overview.py
    - app_v2/templates/overview/index.html
    - app_v2/templates/overview/_filter_bar.html
    - tests/v2/test_phase02_invariants.py
    - .planning/phases/02-ui-shell-rewrite-browse-footer-joint-validation-layout-parit/02-UI-SPEC.md
decisions:
  - "D-UI2-13/14: JV_PAGE_SIZE=15 constant in service (imported by router); service slices sorted_rows[(p-1)*15:p*15]; total_count = pre-slice filtered count"
  - "B3: PageLink Pydantic submodel (not tuple) avoids Pydantic v2 tuple↔list coercion that breaks test equality assertions"
  - "B5: pagination markup defined once in overview/_pagination.html (31 lines); both block footer and block pagination_oob include the partial — no duplication"
  - "T-02-04-02: two-layer defense — FastAPI Query/Form(ge=1, le=10_000) rejects invalid values at HTTP layer; service clamps page > page_count to page_count"
  - "W2 fix: UI-SPEC contradictory footer-carries-count paragraph removed; footer carries pagination only (count stays in panel-header per D-UI2-11)"
  - "Comment text reworded in index.html to avoid grep false-matches on id=overview-pagination (same pattern as Plans 02-02/02-03 fixes)"
metrics:
  duration: "13min"
  completed: "2026-05-01"
  tasks: 3
  files: 8
---

# Phase 02 Plan 04: JV Pagination — 15/Page, Footer Control, HTMX URL Round-Trip Summary

**One-liner:** JV listing paginated at 15 rows/page via PageLink Pydantic submodel, Bootstrap `.pagination` control in the sticky footer (single-source partial), FastAPI Query/Form bounds validation, and HTMX HX-Push-Url state round-trips with filter/sort page-reset.

---

## What Was Built

Three TDD tasks added server-side pagination to the Joint Validation listing (D-UI2-13, D-UI2-14).

### Task 1 — Grid service slice + page metadata

`app_v2/services/joint_validation_grid_service.py` — four additions:

1. **`JV_PAGE_SIZE: Final[int] = 15`** constant (D-UI2-14). Declared at service layer so router imports it.

2. **`PageLink` Pydantic submodel** (B3): `label: str`, `num: int | None`. Avoids Pydantic v2's silent tuple→list coercion that would corrupt test equality assertions on `model_dump()` comparisons.

3. **`_build_page_links(page, page_count) -> list[PageLink]`** helper: always shows pages 1, N, current ± 1; inserts `PageLink(label="…", num=None)` ellipsis when gap > 1. Handles single-page (returns `[PageLink("1", 1)]`) and empty (returns `[]`) edge cases.

4. **`JointValidationGridViewModel`** extended with `page: int = 1`, `page_count: int = 1`, `page_links: list[PageLink]`.

5. **`build_joint_validation_grid_view_model()`** extended with `page: int = 1, page_size: int = JV_PAGE_SIZE` parameters. After sort: computes `total_count` (pre-slice), `page_count = max(1, ceil(total/size))`, clamps `page` to `[1, page_count]`, slices `sorted_rows[start:end]` — `rows` is the current-page slice only.

### Task 2 — Router wiring (co-committed with Task 3)

`app_v2/routers/overview.py` — five changes:

1. Import `JV_PAGE_SIZE` from service; add to `__all__`.
2. `_build_overview_url()`: new `page: int = 1` param; appends `page=N` only when `N > 1` (default omitted for clean URLs).
3. GET handler: `page: Annotated[int, Query(ge=1, le=10_000)] = 1` — rejects 0/negative/>10000/non-integer with HTTP 422 (T-02-04-02); passes to service.
4. POST handler: `page: Annotated[int, Form(ge=1, le=10_000)] = 1` — same bounds as GET; adds `"pagination_oob"` to `block_names`; `HX-Push-Url` uses `vm.page` (clamped value).

### Task 3 — Pagination partial + template wiring + doc sync

**`app_v2/templates/overview/_pagination.html`** (NEW, 31 lines — B5):
- Single source of truth for Bootstrap `.pagination` nav with prev/next arrows and page-number links.
- Iterates `vm.page_links` as `list[PageLink]` via `pl.label` / `pl.num` (B3 — no tuple unpacking).
- Renders nothing when `vm.page_count <= 1`.
- Both `block footer` and `block pagination_oob` in `index.html` include this partial.

**`app_v2/templates/overview/_filter_bar.html`**:
- Added `<input type="hidden" name="page" value="1">` after the sort/order hidden inputs — filter changes reset to page 1.

**`app_v2/templates/overview/index.html`** — three sub-edits:
- `sortable_th` macro: `hx-vals` extended with `"page": "1"` — sort clicks reset page.
- `{% block pagination_oob %}`: OOB wrapper with `hx-swap-oob="true"` includes the partial.
- `{% block footer %}`: initial-render wrapper (no `hx-swap-oob`) includes the partial.
- Comments reworded to avoid grep false-matches on `id="overview-pagination"` (same pattern as Plans 02-02/02-03).

**`02-UI-SPEC.md`** (W2 doc sync): removed the contradictory "footer-carries-count" paragraph that contradicted D-UI2-11. Canonical statement now: footer carries pagination only; `#overview-count` stays in panel-header.

**Test coverage**: 36 new tests across `test_jv_pagination.py` (P1-P24 + P10b + P15a-f) and `test_phase02_invariants.py` (tests 41-45e).

---

## Commits

| Hash | Type | Description |
|------|------|-------------|
| e18e482 | test | Add failing tests for JV pagination service + router + templates (RED) |
| fbcc0e6 | feat | Extend JV grid service with pagination — JV_PAGE_SIZE, PageLink, _build_page_links |
| 621edfb | feat | Wire page param through router + render pagination in footer (D-UI2-13/14) |

---

## Verification Results

- **442 passed, 5 skipped, 0 failures** — full v2 suite (5 skips are pre-existing from Phase 01 Plan 04).
- All 36 new pagination tests green (P1-P24, P10b, P15a-f).
- All 11 new invariant tests green (tests 41-45e).
- All pre-existing 403 tests from Plans 02-01/02/03 and Phase 01 remain green — zero regressions.

Key acceptance greps:
- `grep -c '^JV_PAGE_SIZE: Final\[int\] = 15$' joint_validation_grid_service.py` → `1`
- `grep -c 'def _build_page_links' joint_validation_grid_service.py` → `1`
- `grep -c 'Query(ge=1, le=10_000)' routers/overview.py` → `1`
- `grep -c 'Form(ge=1, le=10_000)' routers/overview.py` → `1`
- `grep -c '"pagination_oob"' routers/overview.py` → `1`
- `grep -c '{% include "overview/_pagination.html" %}' overview/index.html` → `2`
- `wc -l overview/_pagination.html` → `31` (≤ 60 — B5 sanity)
- `grep -c '<ul class="pagination' overview/index.html` → `0` (markup in partial only)
- `grep -c 'id="overview-pagination"' overview/index.html` → `2` (OOB emitter + footer receiver)
- `grep -c 'id="overview-count"' overview/index.html` → `2` (W2 — panel-header only)
- `grep -c 'Wait — the count caption' 02-UI-SPEC.md` → `0` (W2 contradictory paragraph removed)

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Tasks 2+3 committed together (blocking dependency)**
- **Found during:** Task 2 verification
- **Issue:** The router's POST handler now lists `"pagination_oob"` in `block_names`, but jinja2-fragments raises `BlockNotFoundError` if the block doesn't exist in the template. This broke existing `test_joint_validation_routes.py::test_post_overview_grid_returns_oob_blocks` (the test exercises POST /overview/grid which now requires the block). The plan intended router and template as separate commits, but the router change cannot be committed without the template change in place.
- **Fix:** Co-committed router changes (Task 2) with all template changes (Task 3) in one feat commit. TDD RED commit remained separate (e18e482). Service commit remained separate (fbcc0e6).
- **Files modified:** App commits restructured — same total files changed.
- **Commit:** 621edfb

**2. [Rule 1 - Bug] Comment text in index.html caused grep false-match on `id="overview-pagination"`**
- **Found during:** Task 3 acceptance grep verification
- **Issue:** The original comments in the `block pagination_oob` and `block footer` preambles contained the literal string `id="overview-pagination"`, making `grep -c 'id="overview-pagination"' overview/index.html` return 4 instead of the required 2.
- **Fix:** Moved comments inside the blocks (same pattern as Plans 02-02 and 02-03). Reworded to use `#overview-pagination slot` instead of `id="overview-pagination"`.
- **Files modified:** `app_v2/templates/overview/index.html`
- **Commit:** 621edfb

---

## Known Stubs

None — pagination renders real data from `vm.page`, `vm.page_count`, `vm.page_links` (all computed server-side from actual JV content). The `{% if vm.page_count > 1 %}` guard in the partial is correct behavior (single-page results show no pagination control), not a stub.

---

## Threat Surface Scan

All threats registered in plan's `<threat_model>` are mitigated:

| Threat | Status |
|--------|--------|
| T-02-04-01 — OOB target id tampering | Mitigated: exactly 2 occurrences of `id="overview-pagination"` enforced by test 45d |
| T-02-04-02 — page param DoS (HIGH) | Mitigated: `Query/Form(ge=1, le=10_000)` + service clamp; tests P15a-d + P3/P4 |
| T-02-04-03 — URL leakage via HX-Push-Url | Accepted: values are server-validated; `urllib.parse.urlencode(quote_via=quote)` used |
| T-02-04-04 — XSS via vm.page_links | Mitigated: labels rendered via `{{ pl.label \| e }}`; nums are server-computed integers |
| T-02-04-05 — URL-construction tampering | Mitigated: all inputs validated before `_build_overview_url`; urlencode escapes values |

No new unregistered trust boundaries introduced.

---

## Self-Check: PASSED

Files exist:
- `app_v2/services/joint_validation_grid_service.py` — FOUND
- `app_v2/routers/overview.py` — FOUND
- `app_v2/templates/overview/index.html` — FOUND
- `app_v2/templates/overview/_pagination.html` — FOUND
- `app_v2/templates/overview/_filter_bar.html` — FOUND
- `tests/v2/test_jv_pagination.py` — FOUND
- `tests/v2/test_phase02_invariants.py` — FOUND

Commits exist:
- e18e482 — FOUND
- fbcc0e6 — FOUND
- 621edfb — FOUND
