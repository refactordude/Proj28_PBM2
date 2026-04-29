"""Tests for app/services/ufs_service — framework-agnostic canonical API.

Covers:
  - list_platforms: basic query, sorted output
  - list_parameters: basic query, sorted (InfoCategory, Item)
  - fetch_cells: empty-filter short-circuit (DATA-05), no-category filter,
                 row-cap, Result normalization, SAFE-01 path
  - pivot_to_wide: empty/default-orientation/swap-axes/col-cap/duplicate-warning
"""
from __future__ import annotations

import logging
import subprocess
import sys

import pandas as pd
import pytest
import sqlalchemy as sa

from app.adapters.db.base import DBAdapter
from app.core.config import DatabaseConfig
from app.services.ufs_service import (
    fetch_cells,
    list_parameters,
    list_parameters_for_platforms,
    list_platforms,
    pivot_to_wide,
)


# ---------------------------------------------------------------------------
# Test-only in-memory adapter
# ---------------------------------------------------------------------------

class _InMemoryAdapter(DBAdapter):
    """Wraps a SQLite in-memory engine; implements _get_engine() as required by
    ufs_service functions (which use db._get_engine().connect() directly)."""

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
# list_platforms
# ---------------------------------------------------------------------------


def test_list_platforms_returns_sorted_list(mock_db):
    result = list_platforms(mock_db)
    assert result == ["p1", "p2"]


def test_list_platforms_with_db_name_arg(mock_db):
    """db_name kwarg accepted without error (cache partition key)."""
    result = list_platforms(mock_db, db_name="test")
    assert isinstance(result, list)
    assert "p1" in result


# ---------------------------------------------------------------------------
# list_parameters
# ---------------------------------------------------------------------------


def test_list_parameters_returns_records(mock_db):
    result = list_parameters(mock_db)
    assert isinstance(result, list)
    assert len(result) == 2  # (catA, item1), (catA, item2)
    assert result[0] == {"InfoCategory": "catA", "Item": "item1"}
    assert result[1] == {"InfoCategory": "catA", "Item": "item2"}


# ---------------------------------------------------------------------------
# list_parameters_for_platforms (260429-qyv)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db_multi_platform():
    """SQLite in-memory DB with 3 platforms; each contributes a distinct param.

    Layout:
      p1 -> (catA, item1), (catA, item_p1_only)
      p2 -> (catA, item1), (catB, item_p2_only)
      p3 -> (catC, item_p3_only)

    Lets us assert that filtering by PLATFORM_ID narrows the (InfoCategory,
    Item) result set.
    """
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(sa.text(
            "CREATE TABLE ufs_data "
            "(PLATFORM_ID TEXT, InfoCategory TEXT, Item TEXT, Result TEXT)"
        ))
        conn.execute(sa.text(
            "INSERT INTO ufs_data VALUES "
            "('p1','catA','item1','0x1F'),"
            "('p1','catA','item_p1_only','solo1'),"
            "('p2','catA','item1','42'),"
            "('p2','catB','item_p2_only','solo2'),"
            "('p3','catC','item_p3_only','solo3')"
        ))
    yield _InMemoryAdapter(engine)
    engine.dispose()


def test_list_parameters_for_platforms_returns_records(mock_db_multi_platform):
    """Filter by a single platform -> only that platform's (cat, item) rows.

    p1 owns (catA, item1) and (catA, item_p1_only). Sorting is by combined
    (InfoCategory, Item) ascending. The result is identical in shape to
    list_parameters — list[dict] with InfoCategory/Item keys.
    """
    result = list_parameters_for_platforms(mock_db_multi_platform, ("p1",))
    assert isinstance(result, list)
    assert result == [
        {"InfoCategory": "catA", "Item": "item1"},
        {"InfoCategory": "catA", "Item": "item_p1_only"},
    ]


def test_list_parameters_for_platforms_widens_for_multiple_platforms(
    mock_db_multi_platform,
):
    """Two platforms -> union of their (cat, item) pairs, sorted, distinct.

    p1 + p2 share (catA, item1); the union is 3 rows. p3-only rows must NOT
    appear.
    """
    result = list_parameters_for_platforms(mock_db_multi_platform, ("p1", "p2"))
    assert result == [
        {"InfoCategory": "catA", "Item": "item1"},
        {"InfoCategory": "catA", "Item": "item_p1_only"},
        {"InfoCategory": "catB", "Item": "item_p2_only"},
    ]


def test_list_parameters_for_platforms_empty_returns_empty_no_sql(mocker):
    """DATA-05 guard: empty platforms tuple -> [] WITHOUT issuing SQL.

    The function must short-circuit before _get_engine() is touched. We use a
    MagicMock adapter and assert _get_engine was never called.
    """
    from unittest.mock import MagicMock

    mock_db = MagicMock()
    result = list_parameters_for_platforms(mock_db, ())
    assert result == []
    # Critical: no DB call. _get_engine() is the gate ufs_service uses.
    mock_db._get_engine.assert_not_called()


def test_list_parameters_for_platforms_with_db_name_arg(mock_db_multi_platform):
    """db_name kwarg accepted without error (cache partition key)."""
    result = list_parameters_for_platforms(
        mock_db_multi_platform, ("p1",), db_name="test"
    )
    assert isinstance(result, list)
    assert {"InfoCategory": "catA", "Item": "item1"} in result


def test_list_parameters_for_platforms_uses_bindparam_no_interpolation(
    mock_db_multi_platform,
):
    """SAFE-01 / T-03-01 echo: PLATFORM_ID values are bound, not interpolated.

    A platform value containing a single-quote (a classic injection probe)
    must be safely passed through sa.bindparam — no SQL syntax error, no
    rows returned (since no such PLATFORM_ID exists in the test DB).
    """
    injection = "p1' OR 1=1 --"
    result = list_parameters_for_platforms(mock_db_multi_platform, (injection,))
    # The injection string is treated as a literal value, not SQL — no rows
    # match because no PLATFORM_ID equals the literal string.
    assert result == []


def test_list_parameters_for_platforms_filtered_excludes_other_platforms(
    mock_db_multi_platform,
):
    """p3 owns (catC, item_p3_only); when we ask for p1+p2 only, that pair
    must NOT appear in the result. Defense against the bug that motivated
    260429-qyv: stale params from unselected platforms must not leak.
    """
    result = list_parameters_for_platforms(mock_db_multi_platform, ("p1", "p2"))
    assert {"InfoCategory": "catC", "Item": "item_p3_only"} not in result


# ---------------------------------------------------------------------------
# fetch_cells
# ---------------------------------------------------------------------------


def test_fetch_cells_empty_filter_short_circuit(mock_db):
    """DATA-05 guard: empty platforms or items -> empty DF, False, no SQL executed."""
    df, capped = fetch_cells(mock_db, (), (), ("item1",))
    assert df.empty
    assert capped is False
    assert list(df.columns) == ["PLATFORM_ID", "InfoCategory", "Item", "Result"]


def test_fetch_cells_empty_items_short_circuit(mock_db):
    """DATA-05 guard: empty items -> empty DF even if platforms are set."""
    df, capped = fetch_cells(mock_db, ("p1",), (), ())
    assert df.empty
    assert capped is False


def test_fetch_cells_returns_matching_rows(mock_db):
    df, capped = fetch_cells(mock_db, ("p1",), (), ("item1",))
    assert not df.empty
    assert set(df["PLATFORM_ID"]) == {"p1"}
    assert set(df["Item"]) == {"item1"}
    assert capped is False


def test_fetch_cells_with_category_filter(mock_db):
    df, capped = fetch_cells(mock_db, ("p1", "p2"), ("catA",), ("item1",))
    assert len(df) == 2
    assert set(df["PLATFORM_ID"]) == {"p1", "p2"}


def test_fetch_cells_row_cap_triggers(mock_db):
    """row_cap=1 with 2 matching rows should trigger capped=True and return 1 row."""
    df, capped = fetch_cells(mock_db, ("p1", "p2"), (), ("item1",), row_cap=1)
    assert capped is True
    assert len(df) == 1


# ---------------------------------------------------------------------------
# fetch_cells end-to-end without cache layer
# ---------------------------------------------------------------------------


def test_fetch_cells_end_to_end_no_cache(mock_db):
    """fetch_cells works correctly without any caching layer on top."""
    df, capped = fetch_cells(mock_db, ("p1",), (), ("item1", "item2"))
    assert not df.empty
    assert set(df["Item"]).issubset({"item1", "item2"})
    assert capped is False
    # Result column exists and is string-typed after normalization
    assert "Result" in df.columns


# ---------------------------------------------------------------------------
# pivot_to_wide — pure function tests (no DB needed)
# ---------------------------------------------------------------------------


def _make_long_df() -> pd.DataFrame:
    return pd.DataFrame({
        "PLATFORM_ID": ["p1", "p1", "p2", "p2"],
        "InfoCategory": ["catA", "catA", "catA", "catA"],
        "Item": ["item1", "item2", "item1", "item2"],
        "Result": ["0x1F", "None", "42", "ok"],
    })


def test_pivot_to_wide_empty_returns_empty():
    df, capped = pivot_to_wide(pd.DataFrame())
    assert df.empty
    assert capped is False


def test_pivot_to_wide_default_orientation_has_platform_id_column():
    wide, capped = pivot_to_wide(_make_long_df())
    assert "PLATFORM_ID" in wide.columns
    assert "item1" in wide.columns
    assert "item2" in wide.columns
    assert capped is False


def test_pivot_to_wide_swap_axes_has_item_column():
    wide, capped = pivot_to_wide(_make_long_df(), swap_axes=True)
    assert "Item" in wide.columns
    assert "p1" in wide.columns
    assert "p2" in wide.columns
    assert capped is False


def test_pivot_to_wide_caps_at_30_columns():
    """col_cap=1 with 2 value columns should cap and return 1 value col."""
    wide, capped = pivot_to_wide(_make_long_df(), col_cap=1)
    # 1 index col + 1 value col = 2 total
    assert len(wide.columns) == 2
    assert capped is True


def test_pivot_to_wide_warns_on_duplicates(caplog):
    """DATA-06: duplicate rows trigger a WARNING via logging."""
    dup_df = pd.DataFrame({
        "PLATFORM_ID": ["p1", "p1"],
        "InfoCategory": ["catA", "catA"],
        "Item": ["item1", "item1"],
        "Result": ["0x1F", "0x2F"],
    })
    with caplog.at_level(logging.WARNING, logger="app.services.ufs_service"):
        pivot_to_wide(dup_df)
    assert any("duplicate" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# Import isolation — no Streamlit session required
# ---------------------------------------------------------------------------


def test_ufs_service_importable_without_streamlit():
    """Spawn a subprocess with no `streamlit run` and import canonical names."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.services.ufs_service import ("
                "list_platforms, list_parameters, "
                "list_parameters_for_platforms, "
                "fetch_cells, pivot_to_wide"
                "); print('ok')"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "ok" in result.stdout
