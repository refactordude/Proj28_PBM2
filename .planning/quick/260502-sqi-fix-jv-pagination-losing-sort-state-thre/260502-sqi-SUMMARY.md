# Quick Task 260502-sqi — Summary

**Description:** Fix JV pagination losing sort state — thread sort/order into pagination hx-vals
**Date:** 2026-05-02
**Status:** Complete

## Bug

Sorting the JV grid by clicking a column header (e.g. Customer) worked for page 1, but clicking page 2 dropped the sort and re-rendered the second page in default order (`start desc`).

## Root cause

`app_v2/templates/overview/_pagination.html` relied on `hx-include="#overview-filter-form"` to pull `sort` / `order` from the filter bar's hidden inputs and emitted only `{"page": "N"}` in `hx-vals`. After a column-header POST, the router responds with `block_names=["grid", "count_oob", "filter_badges_oob", "pagination_oob"]` — the filter bar (and its hidden `sort` / `order` inputs) is **not** in the OOB swap. So those hidden inputs still held the old sort values when pagination fired, sending `sort=start&order=desc&page=2`.

## Fix

Added `sort` and `order` directly to the `hx-vals` JSON of all three pagination links (Prev, numbered page links, Next). Since `hx-vals` wins on collisions with `hx-include`, pagination POSTs now always carry the current sort regardless of what the filter form's hidden inputs contain. The pagination partial is already in `pagination_oob`, so its `hx-vals` get re-rendered with the latest `vm.sort_col` / `vm.sort_order` after every swap.

## Verification

- 75/75 JV-related pytest tests pass (`tests/v2/test_jv_pagination.py`, `test_joint_validation_routes.py`, `test_joint_validation_grid_service.py`, `test_joint_validation_store.py`, `test_joint_validation_parser.py`).
- TestClient smoke after `POST /overview/grid sort=customer&order=asc&page=1` — pagination hx-vals on the response render as `{"page": "2", "sort": "customer", "order": "asc"}` (was `{"page": "2"}`).
- `POST /overview/grid sort=customer&order=asc&page=2` returns HTTP 200 with `HX-Push-Url: /overview?sort=customer&order=asc&page=2`.

## Files changed

- `app_v2/templates/overview/_pagination.html` — three lines updated (Prev, numbered, Next pagination links).
- `.planning/quick/260502-sqi-fix-jv-pagination-losing-sort-state-thre/260502-sqi-PLAN.md` (new)
- `.planning/quick/260502-sqi-fix-jv-pagination-losing-sort-state-thre/260502-sqi-SUMMARY.md` (new)
- `.planning/STATE.md` — Quick Tasks Completed row added.
