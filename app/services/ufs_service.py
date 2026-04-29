"""UFS data service — the single entry point for v2.0 Browse and NL queries.

Handles server-side filtering, row-capping, and pivot-to-wide. Caching is
layered ON TOP via app_v2/services/cache.py (TTLCache + threading.Lock —
INFRA-08); this module is framework-agnostic and has zero Streamlit /
FastAPI dependencies.

Public API:
  list_platforms(db, db_name="") -> list[str]
  list_parameters(db, db_name="") -> list[dict]
  fetch_cells(db, platforms, infocategories, items, row_cap=200, db_name="") -> tuple[pd.DataFrame, bool]
  pivot_to_wide(df_long, swap_axes=False, col_cap=30) -> tuple[pd.DataFrame, bool]

Security notes (T-03-01, T-03-02):
  - _TABLE is sourced from settings.app.agent.allowed_tables[0] at module
    load — configured constant, never interpolated from user data or HTTP
    input. _safe_table() validates against the allowlist before any
    sa.text() interpolation.
  - User-supplied filter values go through sa.bindparam(..., expanding=True).
  - No f-string interpolation of user-controlled values into SQL.
"""
from __future__ import annotations

import logging

import pandas as pd
import sqlalchemy as sa

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


def list_platforms(db: DBAdapter, db_name: str = "") -> list[str]:
    """Return sorted distinct PLATFORM_ID values."""
    tbl = _safe_table(_TABLE)
    with db._get_engine().connect() as conn:
        df = pd.read_sql_query(
            sa.text(f"SELECT DISTINCT PLATFORM_ID FROM {tbl} ORDER BY PLATFORM_ID"),
            conn,
        )
    return df["PLATFORM_ID"].dropna().astype(str).tolist()


def list_parameters(db: DBAdapter, db_name: str = "") -> list[dict]:
    """Return sorted distinct (InfoCategory, Item) rows."""
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


# ---------------------------------------------------------------------------
# Cell query (cached 60 s — more volatile than catalog)
# ---------------------------------------------------------------------------


def fetch_cells(
    db: DBAdapter,
    platforms: tuple[str, ...],
    infocategories: tuple[str, ...],
    items: tuple[str, ...],
    row_cap: int = 200,
    db_name: str = "",
) -> tuple[pd.DataFrame, bool]:
    """Fetch long-form EAV rows filtered by platforms and items.

    All DATA-05 / SAFE-01 / T-03-01 contracts are implemented here.
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
