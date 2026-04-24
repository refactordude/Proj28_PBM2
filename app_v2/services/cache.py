"""Thread-safe TTLCache wrappers for ufs_service _core() functions (INFRA-08).

v2.0 replacement for @st.cache_data. Every route in app_v2/ imports the wrapper
names from THIS module, never the raw _core functions from ufs_service.

Thread-safety contract (Pitfall 11):
    FastAPI `def` routes run concurrently in the threadpool. cachetools.TTLCache
    is NOT thread-safe — concurrent access during eviction can raise RuntimeError.
    Every TTLCache below is paired with a module-level threading.Lock() via the
    @cached(lock=...) parameter.

Key contract (Pitfall 11 / T-04-02):
    The DBAdapter object is NOT hashable. Including `db` in the cache key causes
    TypeError on every call (100% cache miss). All key lambdas use db_name:str
    as the cache partition identifier. Two adapters pointing at the same DB name
    share the cache (acceptable: db_name is semantically "which database" —
    identical db_name means identical data).

TTL rationale (mirrors v1.0 @st.cache_data values):
    - list_platforms: ttl=300s (catalog changes only on ingestion; ~5min is fine)
    - list_parameters: ttl=300s (same reasoning)
    - fetch_cells: ttl=60s (cell data more volatile; 1min bound for parallel
      deployment where v1.0 ingest job may write while v2.0 reads)
"""
from __future__ import annotations

import threading
from typing import Tuple

import pandas as pd
from cachetools import TTLCache, cached
from cachetools.keys import hashkey

from app.adapters.db.base import DBAdapter
from app.services.ufs_service import (
    fetch_cells_core,
    list_parameters_core,
    list_platforms_core,
)

# ---------------------------------------------------------------------------
# Module-level caches + locks. One lock per cache (cachetools supports shared
# locks across multiple caches but separate locks give finer-grained contention).
# ---------------------------------------------------------------------------

_platforms_cache: TTLCache = TTLCache(maxsize=64, ttl=300)
_platforms_lock = threading.Lock()

_parameters_cache: TTLCache = TTLCache(maxsize=64, ttl=300)
_parameters_lock = threading.Lock()

_cells_cache: TTLCache = TTLCache(maxsize=256, ttl=60)
_cells_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Wrappers — same public signatures as the v1.0 @st.cache_data functions but
# with `db` (no underscore — Streamlit convention is not relevant here) and
# explicit key lambdas that exclude the adapter.
# ---------------------------------------------------------------------------

@cached(
    cache=_platforms_cache,
    lock=_platforms_lock,
    key=lambda db, db_name="": hashkey(db_name),
)
def list_platforms(db: DBAdapter, db_name: str = "") -> list[str]:
    """Return sorted distinct PLATFORM_ID values (cached per db_name).

    Key: hashkey(db_name). The adapter is NOT hashed.
    """
    return list_platforms_core(db, db_name)


@cached(
    cache=_parameters_cache,
    lock=_parameters_lock,
    key=lambda db, db_name="": hashkey(db_name),
)
def list_parameters(db: DBAdapter, db_name: str = "") -> list[dict]:
    """Return sorted distinct (InfoCategory, Item) rows (cached per db_name)."""
    return list_parameters_core(db, db_name)


@cached(
    cache=_cells_cache,
    lock=_cells_lock,
    key=lambda db, platforms, infocategories, items, row_cap=200, db_name="":
        hashkey(platforms, infocategories, items, row_cap, db_name),
)
def _fetch_cells_cached(
    db: DBAdapter,
    platforms: Tuple[str, ...],
    infocategories: Tuple[str, ...],
    items: Tuple[str, ...],
    row_cap: int = 200,
    db_name: str = "",
) -> tuple[pd.DataFrame, bool]:
    """Internal cached function — stores the raw DataFrame in TTLCache.

    Do NOT call this directly. Use fetch_cells() which returns a defensive copy.
    """
    return fetch_cells_core(db, platforms, infocategories, items, row_cap, db_name)


def fetch_cells(
    db: DBAdapter,
    platforms: Tuple[str, ...],
    infocategories: Tuple[str, ...],
    items: Tuple[str, ...],
    row_cap: int = 200,
    db_name: str = "",
) -> tuple[pd.DataFrame, bool]:
    """Fetch long-form EAV rows (cached per filter tuple + db_name).

    Key: hashkey(platforms, infocategories, items, row_cap, db_name).
    The adapter is NOT hashed.

    Returns a defensive copy of the cached DataFrame on every call so callers
    can freely mutate (e.g. add computed columns) without corrupting the shared
    cached object for concurrent or subsequent requests (Pitfall 3 contract).

    The copy is made here, outside _fetch_cells_cached, because cachetools
    @cached returns the stored value directly on a hit — the decorated function
    body is bypassed — so a copy() inside the decorated function would only run
    on a cache miss.
    """
    df, capped = _fetch_cells_cached(db, platforms, infocategories, items, row_cap, db_name)
    return df.copy(), capped  # MUST copy — TTLCache returns same object to all callers


# ---------------------------------------------------------------------------
# Cache management helpers — used by tests and potentially by a future admin
# endpoint to force cache invalidation without a process restart.
# ---------------------------------------------------------------------------

def clear_all_caches() -> None:
    """Invalidate every cache. Use in tests between cases and by admin endpoints.

    Acquires each lock briefly; safe under concurrent reads (they block until
    clear completes).
    """
    for cache, lock in (
        (_platforms_cache, _platforms_lock),
        (_parameters_cache, _parameters_lock),
        (_cells_cache, _cells_lock),
    ):
        with lock:
            cache.clear()
