---
phase: 01-pre-work-foundation
fixed_at: 2026-04-23T00:00:00Z
review_path: .planning/phases/01-pre-work-foundation/01-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 1: Code Review Fix Report

**Fixed at:** 2026-04-23
**Source review:** .planning/phases/01-pre-work-foundation/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### WR-01: `cache.py` `fetch_cells` returns the cached DataFrame by reference — callers can silently corrupt subsequent calls

**Files modified:** `app_v2/services/cache.py`, `tests/v2/test_cache.py`
**Commits:** `233da54`, `2d0b58e`
**Applied fix:**
Split `fetch_cells` into two functions: `_fetch_cells_cached` (the `@cached`-decorated internal function that stores the raw result in TTLCache) and a public `fetch_cells` wrapper that calls the cached function and returns `df.copy(), capped`. The copy must happen outside the decorated function because `cachetools @cached` bypasses the function body entirely on a cache hit — a `df.copy()` inside the decorated body only ran on a cache miss. The existing `test_fetch_cells_cache_hit_on_identical_filters` test was updated to reflect the new contract (distinct objects, equal content, core called once). A new regression test `test_fetch_cells_mutation_does_not_corrupt_cache` was added asserting that mutating a returned DataFrame does not affect the cached value seen by subsequent callers.

---

### WR-02: `ask.py` imports `ClarificationNeeded`, `SQLResult`, and `run_agent` from `nl_agent` — all three are now dead after `nl_service` extraction

**Files modified:** `app/pages/ask.py`
**Commit:** `b62b5b1`
**Applied fix:** Removed `ClarificationNeeded`, `SQLResult`, and `run_agent` from the `nl_agent` import block. The three retained names (`AgentDeps`, `AgentRunFailure`, `build_agent`) are all actively used in the module body.

---

### WR-03: `http_exception_handler` fallthrough path renders `exc.detail` into raw HTML without escaping

**Files modified:** `app_v2/main.py`
**Commit:** `cf2ab65`
**Applied fix:** Added `from html import escape` to the imports and changed the fallthrough `HTMLResponse` f-string from `{exc.detail}` to `{escape(str(exc.detail))}`. The 404 and 500 branches use Jinja2 templates (which have autoescape enabled) and were not changed.

---

### WR-04: `htmx-error-handler.js` does not null-check `getElementById` result before assigning to `evt.detail.target`

**Files modified:** `app_v2/static/js/htmx-error-handler.js`
**Commit:** `83c3f02`
**Applied fix:** Extracted `document.getElementById("htmx-error-container")` into a local variable `errorContainer` and wrapped the `evt.detail.target` assignment in `if (errorContainer) { ... }`. When the container element is absent, HTMX falls back to swapping into the original `hx-target` — still visible to the user, not silently dropped.

---

_Fixed: 2026-04-23_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
