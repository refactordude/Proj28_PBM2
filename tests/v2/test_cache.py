"""Unit tests for app_v2/services/cache.py — INFRA-08.

Tests isolate the cache contract by mocking the underlying _core functions.
Each test clears the cache between cases (via clear_all_caches) so cross-test
pollution is impossible.
"""
from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app_v2.services import cache as cache_mod
from app_v2.services.cache import (
    clear_all_caches,
    fetch_cells,
    list_parameters,
    list_platforms,
)


@pytest.fixture(autouse=True)
def _clear_caches_between_tests():
    """Ensure no cross-test state leakage via cache survival."""
    clear_all_caches()
    yield
    clear_all_caches()


@pytest.fixture
def fake_db():
    """DBAdapter stand-in — never actually called; wrapper bypasses to _core."""
    return MagicMock(spec=object)


# ---------------------------------------------------------------------------
# list_platforms — hit/miss contract
# ---------------------------------------------------------------------------

def test_list_platforms_cache_hit_returns_same_object(fake_db):
    with patch("app_v2.services.cache.list_platforms_core",
               return_value=["A", "B", "C"]) as mock_core:
        r1 = list_platforms(fake_db, db_name="X")
        r2 = list_platforms(fake_db, db_name="X")
    assert r1 is r2, "cache hit should return identical list object"
    assert mock_core.call_count == 1, "core should be called exactly once on hit"


def test_list_platforms_distinct_db_name_separate_cache_entries(fake_db):
    with patch("app_v2.services.cache.list_platforms_core",
               side_effect=[["A"], ["B"]]) as mock_core:
        r_x = list_platforms(fake_db, db_name="X")
        r_y = list_platforms(fake_db, db_name="Y")
    assert r_x == ["A"]
    assert r_y == ["B"]
    assert mock_core.call_count == 2, "different db_name must miss the cache"


def test_list_platforms_key_excludes_adapter(fake_db):
    """Two different adapter instances with the same db_name share the cache."""
    other_db = MagicMock(spec=object)
    with patch("app_v2.services.cache.list_platforms_core",
               return_value=["A"]) as mock_core:
        list_platforms(fake_db, db_name="X")
        list_platforms(other_db, db_name="X")
    assert mock_core.call_count == 1, \
        "adapter identity must not partition cache — only db_name"


# ---------------------------------------------------------------------------
# list_parameters — same contract
# ---------------------------------------------------------------------------

def test_list_parameters_cache_hit(fake_db):
    with patch("app_v2.services.cache.list_parameters_core",
               return_value=[{"InfoCategory": "c", "Item": "i"}]) as mock_core:
        r1 = list_parameters(fake_db, db_name="X")
        r2 = list_parameters(fake_db, db_name="X")
    assert r1 is r2
    assert mock_core.call_count == 1


def test_list_parameters_independent_of_list_platforms(fake_db):
    """list_platforms and list_parameters have separate caches."""
    with patch("app_v2.services.cache.list_platforms_core",
               return_value=["P"]) as mp, \
         patch("app_v2.services.cache.list_parameters_core",
               return_value=[{"InfoCategory": "c", "Item": "i"}]) as mpp:
        list_platforms(fake_db, db_name="X")
        list_parameters(fake_db, db_name="X")
    assert mp.call_count == 1
    assert mpp.call_count == 1


# ---------------------------------------------------------------------------
# fetch_cells — tuple key correctness
# ---------------------------------------------------------------------------

def test_fetch_cells_cache_hit_on_identical_filters(fake_db):
    df = pd.DataFrame({"PLATFORM_ID": ["P1"], "InfoCategory": ["c"], "Item": ["x"], "Result": ["1"]})
    with patch("app_v2.services.cache.fetch_cells_core",
               return_value=(df, False)) as mock_core:
        r1 = fetch_cells(fake_db, ("P1",), (), ("x",))
        r2 = fetch_cells(fake_db, ("P1",), (), ("x",))
    assert r1 is r2
    assert mock_core.call_count == 1


def test_fetch_cells_different_platforms_miss(fake_db):
    df1 = pd.DataFrame({"PLATFORM_ID": ["P1"]})
    df2 = pd.DataFrame({"PLATFORM_ID": ["P2"]})
    with patch("app_v2.services.cache.fetch_cells_core",
               side_effect=[(df1, False), (df2, False)]) as mock_core:
        fetch_cells(fake_db, ("P1",), (), ("x",))
        fetch_cells(fake_db, ("P2",), (), ("x",))
    assert mock_core.call_count == 2


def test_fetch_cells_different_row_cap_separate_cache_entries(fake_db):
    """row_cap MUST be part of the cache key — changing row_cap should miss."""
    df = pd.DataFrame({"PLATFORM_ID": ["P1"]})
    with patch("app_v2.services.cache.fetch_cells_core",
               return_value=(df, False)) as mock_core:
        fetch_cells(fake_db, ("P1",), (), ("x",), row_cap=200)
        fetch_cells(fake_db, ("P1",), (), ("x",), row_cap=100)
    assert mock_core.call_count == 2


def test_fetch_cells_different_db_name_separate_cache_entries(fake_db):
    df = pd.DataFrame({"PLATFORM_ID": ["P1"]})
    with patch("app_v2.services.cache.fetch_cells_core",
               return_value=(df, False)) as mock_core:
        fetch_cells(fake_db, ("P1",), (), ("x",), db_name="A")
        fetch_cells(fake_db, ("P1",), (), ("x",), db_name="B")
    assert mock_core.call_count == 2


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------

def test_ttl_expiry_invalidates_entry(fake_db):
    """Simulate TTL expiry by advancing cachetools' time source.

    cachetools.TTLCache calls a timer function internally; we replace the cache's
    timer to advance it past the TTL between calls.
    """
    cache = cache_mod._platforms_cache
    original_timer = cache.timer
    fake_time = [1000.0]
    cache.timer = lambda: fake_time[0]

    try:
        with patch("app_v2.services.cache.list_platforms_core",
                   side_effect=[["A"], ["B"]]) as mock_core:
            r1 = list_platforms(fake_db, db_name="X")
            # Advance past the 300s TTL
            fake_time[0] += 301
            r2 = list_platforms(fake_db, db_name="X")
        assert r1 == ["A"]
        assert r2 == ["B"], "post-TTL call should re-invoke core"
        assert mock_core.call_count == 2
    finally:
        cache.timer = original_timer


# ---------------------------------------------------------------------------
# Thread safety — smoke test for threading.Lock coverage
# ---------------------------------------------------------------------------

def test_concurrent_list_platforms_no_runtime_error(fake_db):
    """10 threads calling list_platforms simultaneously must not raise."""
    errors: list[Exception] = []
    results: list[list[str]] = []

    def _call():
        try:
            results.append(list_platforms(fake_db, db_name="X"))
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    with patch("app_v2.services.cache.list_platforms_core",
               return_value=["A", "B"]):
        threads = [threading.Thread(target=_call) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

    assert not errors, f"concurrent calls raised: {errors}"
    assert len(results) == 10
    # All 10 should have received the same cached result
    assert all(r == ["A", "B"] for r in results)


# ---------------------------------------------------------------------------
# Import isolation — cache.py must be Streamlit-free
# ---------------------------------------------------------------------------

def test_cache_module_importable_without_streamlit():
    """Subprocess test: no Streamlit session needed to import cache.py."""
    import subprocess
    import sys
    r = subprocess.run(
        [sys.executable, "-c",
         "from app_v2.services.cache import list_platforms, list_parameters, fetch_cells; print('ok')"],
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, f"stderr: {r.stderr}"
    assert "ok" in r.stdout


# ---------------------------------------------------------------------------
# clear_all_caches helper
# ---------------------------------------------------------------------------

def test_clear_all_caches_invalidates_everything(fake_db):
    with patch("app_v2.services.cache.list_platforms_core",
               side_effect=[["A"], ["B"]]) as mock_core:
        list_platforms(fake_db, db_name="X")
        clear_all_caches()
        r = list_platforms(fake_db, db_name="X")
    assert r == ["B"]
    assert mock_core.call_count == 2
