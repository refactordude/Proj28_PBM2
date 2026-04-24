---
phase: "01"
plan: "04"
subsystem: "app_v2 caching layer"
tags:
  - infrastructure
  - cache
  - ttlcache
  - thread-safety
  - tdd
dependency_graph:
  requires:
    - "01-01 (list_platforms_core, list_parameters_core, fetch_cells_core in ufs_service.py)"
    - "01-03 (app_v2/ package + tests/v2/ package established)"
  provides:
    - "app_v2/services/cache.py::list_platforms (TTLCache wrapper, maxsize=64, ttl=300)"
    - "app_v2/services/cache.py::list_parameters (TTLCache wrapper, maxsize=64, ttl=300)"
    - "app_v2/services/cache.py::fetch_cells (TTLCache wrapper, maxsize=256, ttl=60)"
    - "app_v2/services/cache.py::clear_all_caches (test/admin helper)"
  affects:
    - "Phase 2 Overview tab (will import list_platforms, list_parameters from cache)"
    - "Phase 4 Browse tab (will import fetch_cells from cache)"
tech_stack:
  added:
    - "cachetools 7.0.6 — TTLCache + @cached decorator (already in requirements.txt from 01-01)"
  patterns:
    - "TTLCache + threading.Lock per-cache (Pitfall 11 fix for FastAPI threadpool)"
    - "Key lambda excludes unhashable DBAdapter — only db_name:str partitions catalog caches"
    - "fetch_cells key: hashkey(platforms, infocategories, items, row_cap, db_name)"
    - "clear_all_caches() acquires each lock before clearing — safe under concurrent reads"
    - "TDD RED-GREEN cycle; TTL timer patching via _Timer__timer name-mangled attribute"
key_files:
  created:
    - path: "app_v2/services/__init__.py"
      description: "Package marker for v2.0-specific services"
    - path: "app_v2/services/cache.py"
      description: "Thread-safe TTLCache wrappers: list_platforms, list_parameters, fetch_cells, clear_all_caches"
      lines: 121
    - path: "tests/v2/test_cache.py"
      description: "13 unit tests: hit/miss, key separation, TTL expiry, concurrency, import isolation, cache invalidation"
decisions:
  - "Exported wrapper names are list_platforms/list_parameters/fetch_cells (not cached_ prefix) — matches plan spec and Phase 2 import contract"
  - "TTL expiry test patches _Timer__timer (name-mangled inner callable of cachetools._TimedCache._Timer) because TTLCache.timer is a read-only property in cachetools v7"
  - "Per-cache locks chosen over shared lock — reduces contention when platforms, parameters, and cells are queried concurrently from different routes"
  - "clear_all_caches acquires each lock in sequence (not simultaneously) — avoids potential deadlock with multiple callers"
metrics:
  duration: "~6 minutes"
  completed_date: "2026-04-24T17:06:43Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
  files_created: 3
  tests_before: 199
  tests_after: 212
  tests_added: 13
---

# Phase 01 Plan 04: Thread-safe TTLCache Wrappers (INFRA-08) Summary

**One-liner:** Created `app_v2/services/cache.py` with three `cachetools.TTLCache` + `threading.Lock()` wrappers around the v1.0 `_core()` functions, keyed by `db_name` (never the unhashable adapter), mirroring v1.0 TTLs — 13 new tests, 212 total passing.

## What Was Built

### Task 1 — app_v2/services/cache.py (INFRA-08)

Three `@cached` wrappers + one helper, ~121 lines:

| Function | Cache | TTL | maxsize | Key |
|---|---|---|---|---|
| `list_platforms(db, db_name="")` | `_platforms_cache` | 300s | 64 | `hashkey(db_name)` |
| `list_parameters(db, db_name="")` | `_parameters_cache` | 300s | 64 | `hashkey(db_name)` |
| `fetch_cells(db, platforms, infocategories, items, row_cap=200, db_name="")` | `_cells_cache` | 60s | 256 | `hashkey(platforms, infocategories, items, row_cap, db_name)` |
| `clear_all_caches()` | — | — | — | Acquires each lock, calls `.clear()` |

TTLs mirror v1.0 `@st.cache_data` values exactly (catalog 300s, cells 60s).

Thread-safety contract: every `TTLCache` is paired with its own `threading.Lock()` passed as `lock=` to `@cached`. FastAPI `def` routes run in a threadpool — without locks, concurrent evictions can raise `RuntimeError: dictionary changed size during iteration`.

Key contract: `DBAdapter` is not hashable. Key lambdas capture `db` by position but never include it in `hashkey(...)`. Only `db_name: str` partitions catalog caches; `fetch_cells` adds `(platforms, infocategories, items, row_cap)` to the key.

### Task 2 — tests/v2/test_cache.py (13 tests)

| Test | Contract verified |
|---|---|
| `test_list_platforms_cache_hit_returns_same_object` | Second call returns `is`-identical object; core called once |
| `test_list_platforms_distinct_db_name_separate_cache_entries` | Different `db_name` → core called twice |
| `test_list_platforms_key_excludes_adapter` | Two adapter instances with same `db_name` → core called once |
| `test_list_parameters_cache_hit` | Independent cache hit for `list_parameters` |
| `test_list_parameters_independent_of_list_platforms` | Two separate cache namespaces |
| `test_fetch_cells_cache_hit_on_identical_filters` | Identical filter tuple → same object returned |
| `test_fetch_cells_different_platforms_miss` | Different `platforms` → cache miss |
| `test_fetch_cells_different_row_cap_separate_cache_entries` | `row_cap` is part of the key |
| `test_fetch_cells_different_db_name_separate_cache_entries` | `db_name` is part of the cells key |
| `test_ttl_expiry_invalidates_entry` | Advancing fake timer past TTL → re-invokes core |
| `test_concurrent_list_platforms_no_runtime_error` | 10 threads simultaneously → no RuntimeError |
| `test_cache_module_importable_without_streamlit` | Subprocess import exits 0 (no Streamlit session needed) |
| `test_clear_all_caches_invalidates_everything` | After `clear_all_caches()` → next call re-invokes core |

## Phase 2 Import Contract

Phase 2 Overview tab imports:

```python
from app_v2.services.cache import list_platforms, list_parameters
```

Phase 4 Browse tab imports:

```python
from app_v2.services.cache import fetch_cells
```

These wrappers are drop-in replacements for the v1.0 `@st.cache_data` functions — same signatures, same TTLs, same behavioral contract. Routes must pass tuples (not lists) for `platforms/infocategories/items` since tuples are hashable cache-key components.

## clear_all_caches() in Phase 3+ Admin Endpoint Design

The `clear_all_caches()` helper acquires each lock in sequence and calls `.clear()`. A future Phase 3+ admin endpoint could expose:

```python
@router.post("/admin/cache/clear")
def admin_clear_cache():
    from app_v2.services.cache import clear_all_caches
    clear_all_caches()
    return {"status": "cleared"}
```

This is safe under concurrent reads — each lock acquisition blocks other accessors briefly during the clear operation.

## Test Results

```
212 passed, 1 warning in 50.76s
```

- Prior tests (199 from 01-01 through 01-03): all pass, zero regressions
- New cache tests: 13
- Total: 212 (exceeds >= 209 target)

## Commits

| Hash | Type | Description |
|---|---|---|
| `eb2d4c7` | test | Add failing tests for TTLCache wrapper contract (TDD RED) |
| `99febd3` | feat | Implement thread-safe TTLCache wrappers for ufs_service _core() (INFRA-08) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TTL expiry test for cachetools v7 read-only timer property**
- **Found during:** Task 2 TDD RED→GREEN transition
- **Issue:** The plan's test template used `cache.timer = lambda: fake_time[0]` but in cachetools v7, `TTLCache.timer` is a read-only property (returns a `_TimedCache._Timer` wrapper object). Assignment raises `AttributeError: property 'timer' of 'TTLCache' object has no setter`.
- **Fix:** Replaced the property assignment with direct mutation of the name-mangled `_Timer__timer` attribute on the `_Timer` wrapper object: `timer_obj._Timer__timer = lambda: fake_time[0]`. This is the only path to replace the inner callable without recreating the cache.
- **Files modified:** `tests/v2/test_cache.py`
- **Commit:** `99febd3`

## Known Stubs

None — this plan adds no UI-facing data paths. The wrappers are pure infrastructure that Phase 2+ will wire to actual route handlers.

## Threat Flags

No new security surface beyond the plan's threat model. All T-04-* mitigations implemented:

| Threat ID | Status |
|-----------|--------|
| T-04-01 Concurrent TTLCache mutation | Every `@cached` has `lock=` parameter; verified by `test_concurrent_list_platforms_no_runtime_error` |
| T-04-02 Unhashable adapter in key | `key=lambda db, ...: hashkey(db_name, ...)` on all three wrappers; verified by `test_list_platforms_key_excludes_adapter` |
| T-04-05 Unbounded cache growth | maxsize=64/256 enforced; LRU eviction under pressure |

## Self-Check: PASSED

| Check | Result |
|---|---|
| `app_v2/services/__init__.py` exists | FOUND |
| `app_v2/services/cache.py` exists (121 lines) | FOUND |
| `tests/v2/test_cache.py` exists (13 tests) | FOUND |
| Commit eb2d4c7 (TDD RED) | FOUND |
| Commit 99febd3 (feat cache.py) | FOUND |
| `from app_v2.services.cache import list_platforms, list_parameters, fetch_cells` exits 0 | OK |
| `grep -c "threading.Lock()" cache.py` = 4 (>= 3) | OK |
| `grep -c "^import streamlit" cache.py` = 0 | OK |
| `grep -c "@cached(" cache.py` = 4 (3 decorators + 1 in docstring) | OK |
| pytest tests/v2/test_cache.py — 13 passed | OK |
| pytest tests/ — 212 passed, 0 failed | OK |
