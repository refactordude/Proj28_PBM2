"""Tests for ufs_service — SQLite-backed _InMemoryAdapter fixture.

Covers:
  - pivot_to_wide: empty/default/swap/col-cap/duplicate-warning
  - fetch_cells: empty-platforms short-circuit, no-category filter,
                 row-cap, Result normalization, SAFE-01 non-fatal SQLite path
"""
from __future__ import annotations

import logging

import pandas as pd
import pytest
import sqlalchemy as sa
import streamlit as st

from app.adapters.db.base import DBAdapter
from app.core.config import DatabaseConfig
from app.services.ufs_service import fetch_cells, pivot_to_wide


# ---------------------------------------------------------------------------
# Test-only in-memory adapter
# ---------------------------------------------------------------------------

class _InMemoryAdapter(DBAdapter):
    """Wraps a SQLite in-memory engine; implements _get_engine() as required by
    ufs_service functions (which use _db._get_engine().connect() directly)."""

    def __init__(self, engine: sa.engine.Engine) -> None:
        self._engine = engine
        self.config = DatabaseConfig(name="test", type="mysql")

    def _get_engine(self) -> sa.engine.Engine:
        return self._engine

    def test_connection(self) -> tuple[bool, str]:
        return True, "ok"

    def list_tables(self) -> list[str]:
        return ["ufs_data"]

    def get_schema(self, tables: list[str] | None = None) -> dict[str, list[dict]]:
        return {}

    def run_query(self, sql: str) -> pd.DataFrame:
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_streamlit_cache():
    """Prevent cache bleed between tests."""
    st.cache_data.clear()
    st.cache_resource.clear()
    yield
    st.cache_data.clear()


@pytest.fixture
def mock_db():
    """SQLite in-memory DB pre-populated with 4 ufs_data rows."""
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(sa.text(
            "CREATE TABLE ufs_data "
            "(PLATFORM_ID TEXT, InfoCategory TEXT, Item TEXT, Result TEXT)"
        ))
        conn.execute(sa.text(
            "INSERT INTO ufs_data VALUES "
            "('p1','catA','item1','0x1F'),"
            "('p1','catA','item2','None'),"
            "('p2','catA','item1','42'),"
            "('p2','catA','item2','ok')"
        ))
    yield _InMemoryAdapter(engine)
    engine.dispose()


# ---------------------------------------------------------------------------
# Helper: build a basic long-form DataFrame for pivot tests
# ---------------------------------------------------------------------------

def _make_long_df(platforms=("p1", "p2"), items=("i1", "i2", "i3")) -> pd.DataFrame:
    rows = [
        {"PLATFORM_ID": p, "InfoCategory": "cat", "Item": it, "Result": f"{p}-{it}"}
        for p in platforms
        for it in items
    ]
    return pd.DataFrame(rows)


# ===========================================================================
# pivot_to_wide tests (pure function — no DB needed)
# ===========================================================================

def test_pivot_to_wide_empty_returns_empty():
    """Empty input DataFrame should return an empty DataFrame and capped=False."""
    empty = pd.DataFrame(columns=["PLATFORM_ID", "InfoCategory", "Item", "Result"])
    result_df, capped = pivot_to_wide(empty)
    assert result_df.empty
    assert capped is False


def test_pivot_to_wide_default_orientation_has_platform_id_column():
    """swap_axes=False: PLATFORM_ID becomes the index column (from reset_index).
    There should be 3 value columns (one per item) and capped=False."""
    df = _make_long_df(platforms=("p1", "p2"), items=("i1", "i2", "i3"))
    wide, capped = pivot_to_wide(df)
    assert "PLATFORM_ID" in wide.columns
    # 3 value columns + 1 PLATFORM_ID column = 4 total
    value_cols = [c for c in wide.columns if c != "PLATFORM_ID"]
    assert len(value_cols) == 3
    assert capped is False


def test_pivot_to_wide_swap_axes_has_item_column():
    """swap_axes=True: Item becomes the index column (from reset_index).
    PLATFORM_ID values become column headers."""
    df = _make_long_df(platforms=("p1", "p2"), items=("i1", "i2", "i3"))
    wide, capped = pivot_to_wide(df, swap_axes=True)
    assert "Item" in wide.columns
    assert capped is False


def test_pivot_to_wide_caps_at_30_columns():
    """If there are more than col_cap value columns, truncate and return capped=True.
    With 40 items and col_cap=30: 30 value columns + 1 index column = 31 total."""
    items = tuple(f"item{n:02d}" for n in range(40))
    df = _make_long_df(platforms=("p1",), items=items)
    wide, capped = pivot_to_wide(df, col_cap=30)
    assert capped is True
    # 1 index column (PLATFORM_ID) + 30 value columns
    assert len(wide.columns) == 31


def test_pivot_to_wide_warns_on_duplicates(caplog):
    """Duplicate (PLATFORM_ID, InfoCategory, Item) rows should log a warning
    containing 'duplicate'. aggfunc='first' keeps the first value."""
    rows = [
        {"PLATFORM_ID": "p1", "InfoCategory": "cat", "Item": "i1", "Result": "first"},
        {"PLATFORM_ID": "p1", "InfoCategory": "cat", "Item": "i1", "Result": "second"},
    ]
    df = pd.DataFrame(rows)
    with caplog.at_level(logging.WARNING, logger="app.services.ufs_service"):
        wide, _capped = pivot_to_wide(df)
    assert any("duplicate" in record.message.lower() for record in caplog.records)
    # aggfunc='first': result should contain "first", not "second"
    assert wide.loc[0, "i1"] == "first"


# ===========================================================================
# fetch_cells tests (SQLite in-memory fixture)
# ===========================================================================

def test_fetch_cells_empty_platforms_short_circuits(mock_db):
    """fetch_cells with empty platforms tuple must return empty DataFrame and
    capped=False WITHOUT executing any SQL (no exception from empty table either)."""
    df, capped = fetch_cells(mock_db, (), ("catA",), ("item1",))
    assert df.empty
    assert capped is False
    assert list(df.columns) == ["PLATFORM_ID", "InfoCategory", "Item", "Result"]


def test_fetch_cells_executes_without_category_filter(mock_db):
    """Empty infocategories tuple activates the no-category SQL branch.
    Should still return matching rows (filtered by platform + item only)."""
    df, capped = fetch_cells(mock_db, ("p1",), (), ("item1",))
    assert not df.empty
    assert "PLATFORM_ID" in df.columns
    assert (df["PLATFORM_ID"] == "p1").all()
    assert (df["Item"] == "item1").all()


def test_fetch_cells_caps_rows(mock_db):
    """Fixture has 4 rows for (p1+p2, catA, item1+item2). With row_cap=2,
    the returned DataFrame must have exactly 2 rows and capped must be True."""
    df, capped = fetch_cells(
        mock_db, ("p1", "p2"), ("catA",), ("item1", "item2"), row_cap=2
    )
    assert len(df) == 2
    assert capped is True


def test_fetch_cells_normalizes_result_column(mock_db):
    """The fixture has Result='None' for (p1, catA, item2).
    After normalization, that cell should be pd.NA — so isna() is True for it."""
    df, _capped = fetch_cells(mock_db, ("p1",), ("catA",), ("item2",))
    assert not df.empty
    assert df["Result"].isna().any()


def test_fetch_cells_survives_sqlite_read_only_stmt(mock_db):
    """SQLite does not understand SET SESSION TRANSACTION READ ONLY.
    fetch_cells must NOT raise an exception — SAFE-01 non-fatal semantics."""
    # Should complete without exception
    df, capped = fetch_cells(mock_db, ("p1",), ("catA",), ("item1",))
    assert not df.empty
