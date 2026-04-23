"""UFS data service — the single entry point for Browse and Settings DB queries.

Handles server-side filtering, row-capping, pivot-to-wide, and @st.cache_data caching.

Public API (stable — imported by Plans 04-07):
  list_platforms(_db) -> list[str]
  list_parameters(_db) -> list[dict]
  fetch_cells(_db, platforms, infocategories, items, row_cap=200) -> tuple[pd.DataFrame, bool]
  pivot_to_wide(df_long, swap_axes=False, col_cap=30) -> tuple[pd.DataFrame, bool]

Cache TTL contract:
  - list_platforms / list_parameters: ttl=300 (catalog data changes infrequently)
  - fetch_cells: ttl=60 (cell data is less stable than catalog; shorter eviction window)

Security notes (T-03-01, T-03-02):
  - _TABLE is a module constant — never interpolated from user data.
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
from app.services.result_normalizer import normalize

logger = logging.getLogger(__name__)

_TABLE = "ufs_data"  # SAFE-01: single allowed table name — module constant, not user input

# Security (T-03-01): allowlist guard so _TABLE can never be an arbitrary string
# even if the constant were changed to read from settings or env in future.
_ALLOWED_TABLES: frozenset[str] = frozenset({"ufs_data"})


def _safe_table(name: str) -> str:
    """Return name unchanged if it is in the allowlist; raise ValueError otherwise.

    This guard prevents SQL injection if _TABLE were ever sourced from settings,
    user input, or an environment variable.  Because the table name is not a SQL
    bind-parameter placeholder, it must be validated at the application level
    before being interpolated into an sa.text() string.
    """
    if name not in _ALLOWED_TABLES:
        raise ValueError(f"Table '{name}' is not in the allowed table list")
    return name


# ---------------------------------------------------------------------------
# Catalog queries (cached 300 s — catalog data is immutable between ingestions)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def list_platforms(_db: DBAdapter) -> list[str]:
    """Return sorted distinct PLATFORM_ID values.

    The underscore prefix on _db disables Streamlit cache hashing of the adapter
    (FOUND-07). Cached for 300 seconds — platform list changes only on new ingestion.
    """
    tbl = _safe_table(_TABLE)
    with _db._get_engine().connect() as conn:
        df = pd.read_sql_query(
            sa.text(f"SELECT DISTINCT PLATFORM_ID FROM {tbl} ORDER BY PLATFORM_ID"),
            conn,
        )
    return df["PLATFORM_ID"].dropna().astype(str).tolist()


@st.cache_data(ttl=300, show_spinner=False)
def list_parameters(_db: DBAdapter) -> list[dict]:
    """Return sorted distinct (InfoCategory, Item) rows as a list of dicts.

    Each dict has keys 'InfoCategory' and 'Item'. Sorted by (InfoCategory, Item).
    Cached for 300 seconds — parameter catalog is stable between ingestions.
    """
    tbl = _safe_table(_TABLE)
    with _db._get_engine().connect() as conn:
        df = pd.read_sql_query(
            sa.text(
                f"SELECT DISTINCT InfoCategory, Item FROM {tbl} "
                "ORDER BY InfoCategory, Item"
            ),
            conn,
        )
    return df.to_dict("records")


# ---------------------------------------------------------------------------
# Cell query (cached 60 s — more volatile than catalog)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def fetch_cells(
    _db: DBAdapter,
    platforms: tuple[str, ...],
    infocategories: tuple[str, ...],
    items: tuple[str, ...],
    row_cap: int = 200,
) -> tuple[pd.DataFrame, bool]:
    """Fetch long-form EAV rows filtered by platforms and items.

    Args:
        _db: DBAdapter instance (underscore prefix — Streamlit skips hashing it).
        platforms: Tuple of PLATFORM_ID values to include. Empty -> (empty DF, False).
        infocategories: Tuple of InfoCategory values. Empty -> no category filter applied.
        items: Tuple of Item values to include. Empty -> (empty DF, False).
        row_cap: Maximum rows to return (default 200, matching AgentConfig.row_cap).

    Returns:
        (df, capped):
          df — long-form DataFrame with columns [PLATFORM_ID, InfoCategory, Item, Result].
               Result column is normalized via result_normalizer.normalize.
          capped — True if the DB returned more rows than row_cap (rows were truncated).

    Security (T-03-01):
        All user-supplied filter values are bound via sa.bindparam(..., expanding=True).
        No f-string interpolation of user data.

    Safety (SAFE-01 / T-03-02):
        Attempts a read-only session statement non-fatally. SQLite and some
        MySQL configurations will raise; the exception is suppressed.

    DATA-05 guard:
        If platforms or items is empty, returns (empty DF, False) immediately without
        executing any SQL — prevents full-table scans.
    """
    _EMPTY = pd.DataFrame(columns=["PLATFORM_ID", "InfoCategory", "Item", "Result"])

    # DATA-05 guard: never issue SQL with zero filter values on either dimension
    if not platforms or not items:
        return _EMPTY.copy(), False

    # Empty infocategories is allowed — means "all categories for these items"
    has_cat_filter = bool(infocategories)

    # Build SQL with expanding bindparams (SQLAlchemy 2.x canonical IN clause pattern).
    # Converting tuple to list because sa.bindparam expanding=True expects a list.
    # _safe_table validates _TABLE against _ALLOWED_TABLES before interpolation (T-03-01).
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

    with _db._get_engine().connect() as conn:
        # SAFE-01: attempt read-only session — non-fatal; SQLite and some MySQL
        # configs don't support this statement.
        try:
            conn.execute(sa.text("SET SESSION TRANSACTION READ ONLY"))
        except Exception:
            logger.debug("read-only session statement not supported; continuing")

        df = pd.read_sql_query(sql, conn, params=params)

    # DATA-07: detect and enforce row cap
    capped = len(df) > row_cap
    if capped:
        df = df.head(row_cap)

    # DATA-01/02: normalize the Result column (stages 1-2) in place.
    # Stage 5 (try_numeric) is deferred to the chart path per DATA-02 — lazy coercion.
    if not df.empty and "Result" in df.columns:
        df["Result"] = normalize(df["Result"])

    return df, capped


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
