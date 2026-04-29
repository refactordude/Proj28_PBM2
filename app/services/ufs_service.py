"""UFS data service — the single entry point for Browse and Settings DB queries.

Handles server-side filtering, row-capping, pivot-to-wide, and @st.cache_data caching.

Public API — v1.0 Streamlit path (unchanged; @st.cache_data wrappers):
  list_platforms(_db) -> list[str]
  list_parameters(_db) -> list[dict]
  fetch_cells(_db, platforms, infocategories, items, row_cap=200) -> tuple[pd.DataFrame, bool]
  pivot_to_wide(df_long, swap_axes=False, col_cap=30) -> tuple[pd.DataFrame, bool]

Public API — v2.0 framework-agnostic path (NEW — used by app_v2/services/cache.py):
  list_platforms_core(db)
  list_parameters_core(db)
  fetch_cells_core(db, platforms, infocategories, items, row_cap=200)
  pivot_to_wide_core(df_long, swap_axes=False, col_cap=30)

Each _core function is the pure body; the Streamlit-decorated wrapper delegates to it.

Cache TTL contract:
  - list_platforms / list_parameters: ttl=300 (catalog data changes infrequently)
  - fetch_cells: ttl=60 (cell data is less stable than catalog; shorter eviction window)

Security notes (T-03-01, T-03-02):
  - _TABLE is sourced from settings.app.agent.allowed_tables[0] at module
    load — it is a configured constant, never interpolated from user data
    or HTTP input. _safe_table() validates against the same configured
    allowlist before any sa.text() interpolation.
  - User-supplied filter values (platforms, infocategories, items) go through
    sa.bindparam(..., expanding=True) — SQLAlchemy 2.x canonical parameterized IN clause.
  - No f-string interpolation of user-controlled values into SQL strings.

Single-DB caching limitation (T-03-04 / Pitfall-8):
  - _db is prefixed with underscore, telling @st.cache_data to skip hashing it.
  - The effective cache key for fetch_cells is (platforms, infocategories, items, row_cap).
  - In a multi-DB deployment, two sessions using different adapters would share the cache
    if they pass identical filter tuples. Phase 2 multi-DB support MUST add an explicit
    db_name: str argument to the cache key.
"""
from __future__ import annotations

import logging

import pandas as pd
import sqlalchemy as sa
import streamlit as st

from app.adapters.db.base import DBAdapter
from app.core.config import load_settings
from app.services.result_normalizer import normalize

logger = logging.getLogger(__name__)


def _load_table_config() -> tuple[str, frozenset[str]]:
    """Read primary table + allowlist from settings.yaml app.agent.allowed_tables.

    Returns (primary_table, allowed_tables_frozenset). Raises RuntimeError if
    the configured list is empty — no fallback, settings.yaml is the single
    source of truth for table names. Both the agent (cfg.allowed_tables) and
    Browse/Overview queries (this module's _TABLE) read from the same key.

    The first entry in app.agent.allowed_tables is treated as the primary
    table that Browse and Overview SELECT against. The full list (frozenset)
    is the SAFE-01 allowlist guard against SQL injection — _safe_table()
    rejects anything not in the list, so a future code path that interpolates
    a different name into an sa.text() string cannot leak.
    """
    settings = load_settings()
    allowed = settings.app.agent.allowed_tables
    if not allowed:
        raise RuntimeError(
            "settings.app.agent.allowed_tables is empty — define at least one "
            "table in config/settings.yaml under app.agent.allowed_tables.",
        )
    return allowed[0], frozenset(allowed)


_TABLE, _ALLOWED_TABLES = _load_table_config()


def _safe_table(name: str) -> str:
    """Return name unchanged if it is in the allowlist; raise ValueError otherwise.

    This guard prevents SQL injection — the table name is interpolated into
    sa.text() strings (not a bind parameter), so application-level validation
    is the only defense. The allowlist is sourced from settings.yaml at import
    time (see _load_table_config), so any string that is not in the configured
    app.agent.allowed_tables list is rejected.
    """
    if name not in _ALLOWED_TABLES:
        raise ValueError(f"Table '{name}' is not in the allowed table list")
    return name


# ---------------------------------------------------------------------------
# Catalog queries (cached 300 s — catalog data is immutable between ingestions)
# ---------------------------------------------------------------------------


def list_platforms_core(db: DBAdapter, db_name: str = "") -> list[str]:
    """Return sorted distinct PLATFORM_ID values — pure, un-cached, framework-agnostic.

    This is the framework-agnostic core called by:
      - list_platforms() (v1.0 Streamlit wrapper — adds @st.cache_data)
      - app_v2/services/cache.py (v2.0 FastAPI wrapper — adds cachetools.TTLCache + threading.Lock)

    No @st.cache_data decorator, no Streamlit dependency — safe to call from any Python
    process. Security contract (_safe_table + allowlist) is preserved.
    """
    tbl = _safe_table(_TABLE)
    with db._get_engine().connect() as conn:
        df = pd.read_sql_query(
            sa.text(f"SELECT DISTINCT PLATFORM_ID FROM {tbl} ORDER BY PLATFORM_ID"),
            conn,
        )
    return df["PLATFORM_ID"].dropna().astype(str).tolist()


@st.cache_data(ttl=300, show_spinner=False)
def list_platforms(_db: DBAdapter, db_name: str = "") -> list[str]:
    """v1.0 wrapper — delegates to list_platforms_core under @st.cache_data.

    Cache key contract unchanged: _db skipped (underscore prefix), db_name included.
    See list_platforms_core for the behavior.
    """
    return list_platforms_core(_db, db_name)


def list_parameters_core(db: DBAdapter, db_name: str = "") -> list[dict]:
    """Return sorted distinct (InfoCategory, Item) rows — pure, un-cached.

    See list_platforms_core for the framework-agnostic contract.
    """
    tbl = _safe_table(_TABLE)
    with db._get_engine().connect() as conn:
        df = pd.read_sql_query(
            sa.text(
                f"SELECT DISTINCT InfoCategory, Item FROM {tbl} "
                "ORDER BY InfoCategory, Item"
            ),
            conn,
        )
    return df.to_dict("records")


@st.cache_data(ttl=300, show_spinner=False)
def list_parameters(_db: DBAdapter, db_name: str = "") -> list[dict]:
    """v1.0 wrapper — delegates to list_parameters_core under @st.cache_data."""
    return list_parameters_core(_db, db_name)


# ---------------------------------------------------------------------------
# Cell query (cached 60 s — more volatile than catalog)
# ---------------------------------------------------------------------------


def fetch_cells_core(
    db: DBAdapter,
    platforms: tuple[str, ...],
    infocategories: tuple[str, ...],
    items: tuple[str, ...],
    row_cap: int = 200,
    db_name: str = "",
) -> tuple[pd.DataFrame, bool]:
    """Fetch long-form EAV rows filtered by platforms and items — pure, un-cached.

    This is the framework-agnostic core. All DATA-05 / SAFE-01 / T-03-01 contracts
    from the @st.cache_data wrapper (fetch_cells) are implemented here. See
    fetch_cells docstring for the full contract.
    """
    _EMPTY = pd.DataFrame(columns=["PLATFORM_ID", "InfoCategory", "Item", "Result"])

    # DATA-05 guard: never issue SQL with zero filter values on either dimension
    if not platforms or not items:
        return _EMPTY.copy(), False

    has_cat_filter = bool(infocategories)

    tbl = _safe_table(_TABLE)
    if has_cat_filter:
        sql = sa.text(
            f"SELECT PLATFORM_ID, InfoCategory, Item, Result FROM {tbl} "
            "WHERE PLATFORM_ID IN :platforms "
            "AND InfoCategory IN :categories "
            "AND Item IN :items "
            "LIMIT :cap"
        ).bindparams(
            sa.bindparam("platforms", expanding=True),
            sa.bindparam("categories", expanding=True),
            sa.bindparam("items", expanding=True),
        )
        params: dict = {
            "platforms": list(platforms),
            "categories": list(infocategories),
            "items": list(items),
            "cap": row_cap + 1,
        }
    else:
        sql = sa.text(
            f"SELECT PLATFORM_ID, InfoCategory, Item, Result FROM {tbl} "
            "WHERE PLATFORM_ID IN :platforms "
            "AND Item IN :items "
            "LIMIT :cap"
        ).bindparams(
            sa.bindparam("platforms", expanding=True),
            sa.bindparam("items", expanding=True),
        )
        params = {
            "platforms": list(platforms),
            "items": list(items),
            "cap": row_cap + 1,
        }

    with db._get_engine().connect() as conn:
        try:
            conn.execute(sa.text("SET SESSION TRANSACTION READ ONLY"))
        except Exception:
            logger.debug("read-only session statement not supported; continuing")

        df = pd.read_sql_query(sql, conn, params=params)

    capped = len(df) > row_cap
    if capped:
        df = df.head(row_cap)

    if not df.empty and "Result" in df.columns:
        df["Result"] = normalize(df["Result"])

    return df, capped


@st.cache_data(ttl=60, show_spinner=False)
def fetch_cells(
    _db: DBAdapter,
    platforms: tuple[str, ...],
    infocategories: tuple[str, ...],
    items: tuple[str, ...],
    row_cap: int = 200,
    db_name: str = "",
) -> tuple[pd.DataFrame, bool]:
    """v1.0 wrapper — delegates to fetch_cells_core under @st.cache_data.

    Preserves the underscore-prefix `_db` Streamlit cache-hashing convention.
    See fetch_cells_core for the full behavior contract (DATA-05, SAFE-01, T-03-01).
    """
    return fetch_cells_core(_db, platforms, infocategories, items, row_cap, db_name)


# ---------------------------------------------------------------------------
# Pivot to wide form (DATA-06, D-07, BROWSE-04)
# ---------------------------------------------------------------------------

def pivot_to_wide(
    df_long: pd.DataFrame,
    swap_axes: bool = False,
    col_cap: int = 30,
) -> tuple[pd.DataFrame, bool]:
    """Pivot a long-form EAV DataFrame to wide form.

    Args:
        df_long: Long-form DataFrame with columns [PLATFORM_ID, InfoCategory, Item, Result].
        swap_axes: False (default) = PLATFORM_ID as index, Item as columns.
                   True = Item as index, PLATFORM_ID as columns (D-07 toggle).
        col_cap: Maximum number of value columns (default 30, BROWSE-04).

    Returns:
        (wide_df, col_capped):
          wide_df — wide-form DataFrame with the index column included after reset_index.
          col_capped — True if value columns were truncated to col_cap.

    DATA-06:
        Uses aggfunc='first' to handle duplicates deterministically.
        Logs a WARNING when duplicate (PLATFORM_ID, InfoCategory, Item) rows are detected.
    """
    if df_long.empty:
        return df_long.copy(), False

    # DATA-06: detect duplicates and warn
    dup_count = df_long.duplicated(subset=["PLATFORM_ID", "InfoCategory", "Item"]).sum()
    if dup_count > 0:
        logger.warning(
            "pivot_to_wide: %d duplicate (PLATFORM_ID, InfoCategory, Item) rows detected; "
            "using aggfunc='first'",
            dup_count,
        )

    if swap_axes:
        index_col, columns_col = "Item", "PLATFORM_ID"
    else:
        index_col, columns_col = "PLATFORM_ID", "Item"

    wide = df_long.pivot_table(
        index=index_col,
        columns=columns_col,
        values="Result",
        aggfunc="first",
    )
    wide.columns.name = None
    wide = wide.reset_index()

    # BROWSE-04: enforce column cap on value columns (not the index column)
    value_cols = [c for c in wide.columns if c != index_col]
    col_capped = False
    if len(value_cols) > col_cap:
        keep = [index_col] + value_cols[:col_cap]
        wide = wide[keep]
        col_capped = True

    return wide, col_capped


# Alias for framework-agnostic import symmetry — plan 01-04 cache.py imports
# pivot_to_wide_core alongside the other _core functions. pivot_to_wide itself
# has no Streamlit decorator so the function object is identical.
pivot_to_wide_core = pivot_to_wide
