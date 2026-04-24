"""Tests for the framework-agnostic _core() functions in ufs_service (INFRA-06).

These tests prove the v2.0 contract: _core functions return identical results
to the @st.cache_data wrappers, and _core functions are importable in a process
with no active Streamlit session.
"""
from __future__ import annotations

import subprocess
import sys

import pandas as pd
import pytest
import sqlalchemy as sa
import streamlit as st

from app.adapters.db.base import DBAdapter
from app.core.config import DatabaseConfig
from app.services.ufs_service import (
    fetch_cells,
    fetch_cells_core,
    list_parameters,
    list_parameters_core,
    list_platforms,
    list_platforms_core,
    pivot_to_wide,
    pivot_to_wide_core,
)


# ---------------------------------------------------------------------------
# Test-only in-memory adapter — mirror of test_ufs_service.py fixture pattern
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


@pytest.fixture(autouse=True)
def _clear_streamlit_cache():
    """Prevent cache bleed between tests."""
    st.cache_data.clear()
    st.cache_resource.clear()
    yield
    st.cache_data.clear()


@pytest.fixture
def mock_db():
    """SQLite in-memory DB pre-populated with 4 ufs_data rows.

    Identical to the fixture in test_ufs_service.py — also has PLATFORM_ID rows
    so list_platforms/list_platforms_core can query them.
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
            "('p1','catA','item2','None'),"
            "('p2','catA','item1','42'),"
            "('p2','catA','item2','ok')"
        ))
    yield _InMemoryAdapter(engine)
    engine.dispose()


# ---------------------------------------------------------------------------
# Contract tests 1–5
# ---------------------------------------------------------------------------


def test_list_platforms_core_matches_wrapper(mock_db):
    """list_platforms_core returns same list as the @st.cache_data wrapper."""
    # Clear Streamlit cache first so the wrapper re-executes
    list_platforms.clear()
    result_core = list_platforms_core(mock_db)
    result_wrap = list_platforms(mock_db)
    assert result_core == result_wrap


def test_list_parameters_core_matches_wrapper(mock_db):
    """list_parameters_core returns same list[dict] as the @st.cache_data wrapper."""
    list_parameters.clear()
    result_core = list_parameters_core(mock_db)
    result_wrap = list_parameters(mock_db)
    assert result_core == result_wrap


def test_fetch_cells_core_matches_wrapper(mock_db):
    """fetch_cells_core returns an identical (df, capped) tuple as the wrapper."""
    fetch_cells.clear()
    platforms = ("p1",)
    items = ("item1",)
    core_df, core_capped = fetch_cells_core(mock_db, platforms, (), items)
    wrap_df, wrap_capped = fetch_cells(mock_db, platforms, (), items)
    pd.testing.assert_frame_equal(
        core_df.reset_index(drop=True),
        wrap_df.reset_index(drop=True),
    )
    assert core_capped == wrap_capped


def test_fetch_cells_core_empty_filter_short_circuit(mock_db):
    """DATA-05 guard: empty platforms or items -> empty DF, False, no SQL executed."""
    df, capped = fetch_cells_core(mock_db, (), (), ("item1",))
    assert df.empty
    assert capped is False
    assert list(df.columns) == ["PLATFORM_ID", "InfoCategory", "Item", "Result"]


def test_pivot_to_wide_core_is_pivot_to_wide():
    """pivot_to_wide_core is the exact function object — import-symmetry alias."""
    assert pivot_to_wide_core is pivot_to_wide


def test_core_functions_importable_without_streamlit_session():
    """Spawn a subprocess with NO `streamlit run` and import _core names."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.services.ufs_service import ("
                "list_platforms_core, list_parameters_core, "
                "fetch_cells_core, pivot_to_wide_core"
                "); print('ok')"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "ok" in result.stdout
