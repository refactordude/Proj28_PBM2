---
quick_id: 260502-sqi
description: Fix JV pagination losing sort state — thread sort/order into pagination hx-vals
date: 2026-05-02
must_haves:
  - Each `<a class="page-link">` in `_pagination.html` includes `sort` + `order` in `hx-vals` alongside `page`
  - Manual smoke: sort by Customer asc → click page 2 → second page is still sorted by Customer asc (verified via curl POST /overview/grid)
  - All existing JV tests still pass: tests/v2/test_jv_pagination.py + tests/v2/test_joint_validation_routes.py + grid_service + store + parser
  - No router or service changes — template only
---

# Quick Task 260502-sqi — Plan

## Goal

Sort selection survives pagination. Today the pagination buttons rely on `hx-include="#overview-filter-form"` to pull sort/order from hidden form inputs, but those inputs are stale immediately after a column-header click because the filter bar is not in the OOB swap blocks. Solution: have the pagination buttons emit `sort` + `order` directly via `hx-vals`, the same way the column-header macro already does. Pagination is already in `pagination_oob`, so its `hx-vals` are re-rendered with the current `vm.sort_col` / `vm.sort_order` after every swap.

## Tasks

### Task 1 — Thread sort/order into pagination hx-vals

**Files:** `app_v2/templates/overview/_pagination.html`

**Action:** In all three `<a class="page-link">` elements (Prev, numbered page links, Next), expand the `hx-vals` JSON from `{"page": "..."}` to `{"page": "...", "sort": "{{ vm.sort_col | e }}", "order": "{{ vm.sort_order | e }}"}`. The `hx-include` attribute stays as is — `hx-vals` wins on collisions, so even when the filter form's hidden sort/order inputs are stale, the pagination POST sends the current values.

Three lines change:
- Prev button: line 9
- Numbered page link: line 18
- Next button: line 26

**Verify:** `grep -c "sort" app_v2/templates/overview/_pagination.html` returns ≥ 3 (one occurrence per pagination link's hx-vals).

**Done:** Template renders syntactically; manual repro shows page 2 honoring the active sort.

### Task 2 — Run JV tests + manual sort/page smoke

**Files:** None (read-only).

**Action:**
```
.venv/bin/python -m pytest -q tests/v2/test_jv_pagination.py tests/v2/test_joint_validation_routes.py tests/v2/test_joint_validation_grid_service.py tests/v2/test_joint_validation_store.py tests/v2/test_joint_validation_parser.py
```

Plus a TestClient smoke check: POST `/overview/grid` with `sort=customer&order=asc&page=2` and confirm the response renders rows in customer-asc order.

**Verify:** All five suites pass; smoke POST returns 200 and the rows on page 2 are sorted by customer ascending.

**Done:** No regressions, sort survives page change.

## Out of scope

- Filter bar OOB swap (alternative fix — heavier, not needed).
- Any service / router changes.
- New tests (existing pagination tests already cover the URL → service contract; the bug was purely client-side hx-vals omission).
