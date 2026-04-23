---
phase: 01-foundation-browsing
plan: "03"
subsystem: service
tags: [ufs_service, sqlalchemy, pandas, streamlit, cache, pivot, row-cap, tdd, parameterized-sql]

# Dependency graph
requires:
  - "01-01: MySQLAdapter._get_engine() method"
  - "01-02: result_normalizer.normalize() function"
provides:
  - "ufs_service.list_platforms(_db) -> list[str] — cached 300s (FOUND-07)"
  - "ufs_service.list_parameters(_db) -> list[dict] — cached 300s (FOUND-07)"
  - "ufs_service.fetch_cells(_db, platforms, infocategories, items, row_cap=200) -> tuple[pd.DataFrame, bool] (DATA-05, DATA-07, SAFE-01)"
  - "ufs_service.pivot_to_wide(df_long, swap_axes=False, col_cap=30) -> tuple[pd.DataFrame, bool] (DATA-06, D-07, BROWSE-04)"
  - "tests/services/test_ufs_service.py — 10 pytest tests with SQLite-backed fixture"
affects:
  - "01-04: Settings page — calls list_platforms, list_parameters for DB health checks"
  - "01-05: Browse page — calls all 4 functions for pivot grid, detail view, chart tab"
  - "01-06: Chart tab — calls fetch_cells then pivot_to_wide"
  - "01-07: Export — consumes DataFrames returned by fetch_cells / pivot_to_wide"

# Tech tracking
tech-stack:
  added:
    - sqlalchemy (installed in .venv; was already in requirements.txt)
    - streamlit (installed in .venv; was already in requirements.txt)
    - pyyaml + pydantic (installed to support config imports in tests)
  patterns:
    - "@st.cache_data(ttl=300, show_spinner=False) on catalog query functions (list_platforms, list_parameters)"
    - "@st.cache_data(ttl=60, show_spinner=False) on cell query function (fetch_cells)"
    - "Underscore prefix _db on DBAdapter arg disables Streamlit cache hashing — FOUND-07"
    - "sa.bindparam(..., expanding=True) for IN clauses — SQLAlchemy 2.x canonical pattern (T-03-01)"
    - "row_cap+1 LIMIT trick to detect whether cap was hit without a COUNT query"
    - "normalize() called inline after fetch to normalize Result column (DATA-01)"
    - "aggfunc='first' in pivot_table + logger.warning on detected duplicates (DATA-06)"
    - "SET SESSION TRANSACTION READ ONLY inside try/except — non-fatal SAFE-01 re-assertion"

key-files:
  created:
    - app/services/ufs_service.py
    - tests/services/test_ufs_service.py
  modified: []

key-decisions:
  - "Cache key for fetch_cells is (platforms, infocategories, items, row_cap) — _db is excluded via underscore prefix. Single-DB limitation documented (T-03-04 / Pitfall-8): multi-DB Phase 2 MUST add db_name: str as explicit cache key arg."
  - "Empty infocategories tuple activates no-category SQL branch (only PLATFORM_ID + Item filters) — correctly handles Browse page filtering when user selects items without category constraint."
  - "pivot_to_wide does not include InfoCategory in the pivot — the wide form shows one column per Item across platforms. InfoCategory remains available in the long-form df for the Detail tab."
  - "SET SESSION TRANSACTION READ ONLY has 3 occurrences in the file: 1 in code (the actual execute call), 0 in docstrings after cleanup. Grep count is exactly 1."

requirements-completed:
  - FOUND-07
  - DATA-05
  - DATA-06
  - DATA-07

# Metrics
duration: 4min
completed: "2026-04-23"
---

# Phase 01 Plan 03: ufs_service Summary

**4-function domain service layer with @st.cache_data TTL caching, parameterized IN-clause SQL, row capping, Result normalization, and aggfunc='first' pivot — backed by 10 pytest tests on a SQLite in-memory fixture**

## Performance

- **Duration:** ~4 minutes
- **Started:** 2026-04-23T19:21:56Z
- **Completed:** 2026-04-23T19:25:57Z
- **Tasks:** 2 (TDD RED + GREEN combined for both tasks)
- **Files modified:** 2

## Accomplishments

- `app/services/ufs_service.py` implements the full 4-function public API used by Plans 04-07
- `list_platforms` and `list_parameters` decorated with `@st.cache_data(ttl=300)` — catalog queries cached for 5 minutes (FOUND-07)
- `fetch_cells` decorated with `@st.cache_data(ttl=60)` — cell queries use a shorter TTL since data may change during a session
- `fetch_cells` uses `sa.bindparam(..., expanding=True)` for all IN clauses — SQLAlchemy 2.x canonical pattern, no f-string interpolation of user data (T-03-01)
- `fetch_cells` enforces `row_cap=200` default via LIMIT `row_cap+1` trick — detects overflow without a COUNT query (DATA-07)
- `fetch_cells` normalizes the Result column via `result_normalizer.normalize()` inline after the query (DATA-01)
- `fetch_cells` attempts `SET SESSION TRANSACTION READ ONLY` non-fatally inside `try/except` (SAFE-01)
- `fetch_cells` short-circuits immediately for empty platforms or items tuples — no SQL executed (DATA-05)
- `pivot_to_wide` uses `aggfunc="first"` and logs a WARNING on detected duplicates (DATA-06)
- `pivot_to_wide` supports `swap_axes` toggle (D-07) and enforces 30-column cap (BROWSE-04)
- 10 pytest tests — all passing via `pytest tests/services/ -x` (75 total: 65 normalizer + 10 service)

## Public API Reference (copy-paste ready for Plans 04-07)

```python
from app.services.ufs_service import (
    list_platforms,    # (_db: DBAdapter) -> list[str]
    list_parameters,   # (_db: DBAdapter) -> list[dict]  — each dict: {InfoCategory, Item}
    fetch_cells,       # (_db, platforms, infocategories, items, row_cap=200) -> (df, capped)
    pivot_to_wide,     # (df_long, swap_axes=False, col_cap=30) -> (wide_df, col_capped)
)
```

### Cache TTL contract

| Function | TTL | Reason |
|----------|-----|--------|
| `list_platforms` | 300 s | Catalog; changes only on new ingestion |
| `list_parameters` | 300 s | Catalog; changes only on new ingestion |
| `fetch_cells` | 60 s | Cell data; shorter TTL for responsiveness |

### fetch_cells argument rules

- `platforms` and `items` must be `tuple[str, ...]` (not `list`) — `@st.cache_data` cannot hash mutable args
- `infocategories` can be empty tuple `()` — activates no-category branch (filters by platform+item only)
- Empty `platforms` or `items` → `(empty DataFrame, False)` immediately, no SQL executed
- `row_cap` defaults to 200 (matches `AgentConfig.row_cap`); returned `capped=True` when limit hit

### pivot_to_wide orientation

| `swap_axes` | index column | value columns |
|-------------|-------------|---------------|
| `False` (default) | `PLATFORM_ID` | one per `Item` |
| `True` | `Item` | one per `PLATFORM_ID` |

## Task Commits

1. **TDD RED — failing tests** — `4c0f17f` (test)
2. **TDD GREEN — implementation** — `98ed176` (feat)

## Files Created/Modified

- `app/services/ufs_service.py` — 248 lines; 4 public functions; full docstrings
- `tests/services/test_ufs_service.py` — 201 lines; 10 test functions; SQLite fixture

## Decisions Made

- **Single-DB caching limitation (T-03-04 / Pitfall-8):** The `_db` underscore prefix excludes the adapter from the cache key. In Phase 1 single-DB deployment this is correct. Phase 2 multi-DB support MUST add `db_name: str` as an explicit (non-underscore) argument to the cached functions so that different DB configurations produce separate cache entries.
- **No InfoCategory in pivot:** `pivot_to_wide` pivots `PLATFORM_ID × Item` (or `Item × PLATFORM_ID`). InfoCategory is retained in the long-form df for the Detail tab (Plan 05) but not in the wide pivot — consistent with D-07 and the Browse page's primary view.
- **Empty infocategories = all categories:** The `fetch_cells` no-category branch allows callers to retrieve all parameter values for selected platforms+items regardless of InfoCategory. This maps to Browse UX where a user may select items without constraining by category.
- **sa.bindparam expanding=True:** SQLAlchemy 2.x canonical IN-clause parameterization. Tuple args are converted to `list` before passing because `expanding=True` expects a list. This is the documented escape-proof pattern for `IN` with variable-length lists.

## Deviations from Plan

None — plan executed exactly as written. All acceptance criteria met on first implementation pass.

**Pre-requisite deviation (Rule 3 — blocking issue):** SQLAlchemy and Streamlit were not yet installed in the `.venv`. Installed both via `pip install` before implementation. This was an infrastructure gap, not a code change.

## Known Stubs

None — all 4 functions are fully implemented and tested.

## Threat Flags

No new threat surface beyond what the plan's threat model captures. All T-03-01..05 mitigations are implemented as specified.

## Single-DB Caching Limitation Note (Pitfall-8)

Phase 1 is single-DB. The `_db` underscore prefix causes Streamlit to skip hashing the adapter instance, making the effective cache key `(platforms, infocategories, items, row_cap)` only. If two sessions use different DBAdapters with identical filter tuples, they will share the cache — this is the documented Pitfall-8 behavior. Phase 2 multi-DB support resolution: add `db_name: str` (non-underscore) as the first argument to `fetch_cells`, `list_platforms`, and `list_parameters`. The DB adapter itself stays underscore-prefixed.

## Self-Check: PASSED

---
*Phase: 01-foundation-browsing*
*Completed: 2026-04-23*
