"""Unit tests for overview_store YAML persistence (TDD RED phase).

All tests use tmp_path + monkeypatch so the real config/overview.yaml is never touched.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from app_v2.services import overview_store
from app_v2.services.overview_store import (
    DuplicateEntityError,
    OverviewEntity,
    add_overview,
    load_overview,
    remove_overview,
)


@pytest.fixture(autouse=True)
def isolate_yaml(tmp_path, monkeypatch):
    """Redirect OVERVIEW_YAML to a temp path for every test."""
    monkeypatch.setattr(overview_store, "OVERVIEW_YAML", tmp_path / "overview.yaml")


# --------------------------------------------------------------------------- #
# load_overview
# --------------------------------------------------------------------------- #

def test_load_overview_missing_file_returns_empty_list():
    assert load_overview() == []


def test_load_overview_empty_entities_list_returns_empty_list(tmp_path):
    yaml_path = overview_store.OVERVIEW_YAML
    yaml_path.write_text("entities: []\n", encoding="utf-8")
    assert load_overview() == []


def test_load_overview_malformed_yaml_returns_empty_list(tmp_path, caplog):
    yaml_path = overview_store.OVERVIEW_YAML
    yaml_path.write_text("not: valid: yaml: [[[", encoding="utf-8")
    import logging
    with caplog.at_level(logging.WARNING, logger="app_v2.services.overview_store"):
        result = load_overview()
    assert result == []
    assert caplog.records, "Expected at least one WARNING log for malformed YAML"


# --------------------------------------------------------------------------- #
# add_overview
# --------------------------------------------------------------------------- #

def test_add_overview_creates_file_and_returns_entity():
    entity = add_overview("Samsung_S22Ultra_SM8450")
    assert isinstance(entity, OverviewEntity)
    assert entity.platform_id == "Samsung_S22Ultra_SM8450"
    assert overview_store.OVERVIEW_YAML.exists()
    loaded = load_overview()
    assert len(loaded) == 1
    assert loaded[0].platform_id == "Samsung_S22Ultra_SM8450"


def test_add_overview_prepends_newest_first():
    add_overview("pid_a")
    time.sleep(0.01)  # ensure distinct added_at timestamps
    add_overview("pid_b")
    loaded = load_overview()
    assert loaded[0].platform_id == "pid_b"
    assert loaded[1].platform_id == "pid_a"


def test_add_overview_raises_duplicate_entity_error_on_existing_pid():
    add_overview("Samsung_S22Ultra_SM8450")
    with pytest.raises(DuplicateEntityError):
        add_overview("Samsung_S22Ultra_SM8450")


def test_add_overview_returned_entity_has_added_at_utc():
    entity = add_overview("Samsung_S22Ultra_SM8450")
    assert entity.added_at.tzinfo is not None
    # Verify it's UTC (offset zero)
    assert entity.added_at.utcoffset().total_seconds() == 0


# --------------------------------------------------------------------------- #
# remove_overview
# --------------------------------------------------------------------------- #

def test_remove_overview_returns_true_when_pid_existed():
    add_overview("Samsung_S22Ultra_SM8450")
    result = remove_overview("Samsung_S22Ultra_SM8450")
    assert result is True
    assert load_overview() == []


def test_remove_overview_returns_false_when_pid_not_found(tmp_path):
    yaml_path = overview_store.OVERVIEW_YAML
    add_overview("pid_a")
    mtime_before = yaml_path.stat().st_mtime
    result = remove_overview("NonExistent_PID")
    assert result is False
    # File should NOT have been rewritten when pid not found
    assert yaml_path.stat().st_mtime == mtime_before


def test_remove_overview_removes_exact_pid_only():
    add_overview("pid_a")
    time.sleep(0.01)
    add_overview("pid_b")
    time.sleep(0.01)
    add_overview("pid_c")
    remove_overview("pid_b")
    loaded = load_overview()
    pids = [e.platform_id for e in loaded]
    assert "pid_b" not in pids
    assert "pid_a" in pids
    assert "pid_c" in pids


# --------------------------------------------------------------------------- #
# OverviewEntity validation
# --------------------------------------------------------------------------- #

def test_overview_entity_rejects_empty_platform_id():
    with pytest.raises(Exception):  # Pydantic ValidationError
        OverviewEntity(platform_id="", added_at=datetime.now(timezone.utc))


# --------------------------------------------------------------------------- #
# Atomicity
# --------------------------------------------------------------------------- #

def test_write_is_atomic_on_os_replace_failure(tmp_path):
    """Monkeypatch os.replace to raise OSError; original file must be unchanged."""
    # Set up initial state with 3 entities
    add_overview("pid_1")
    time.sleep(0.01)
    add_overview("pid_2")
    time.sleep(0.01)
    add_overview("pid_3")

    initial_entities = load_overview()
    assert len(initial_entities) == 3

    # Monkeypatch os.replace to simulate a crash during atomic rename
    original_replace = os.replace
    with patch("os.replace", side_effect=OSError("simulated crash")):
        with pytest.raises(OSError, match="simulated crash"):
            add_overview("pid_4")

    # File must be unchanged — still 3 entities
    after_failure = load_overview()
    assert len(after_failure) == 3
    pids_after = {e.platform_id for e in after_failure}
    assert pids_after == {"pid_1", "pid_2", "pid_3"}


# --------------------------------------------------------------------------- #
# DuplicateEntityError is a ValueError subclass
# --------------------------------------------------------------------------- #

def test_duplicate_entity_error_is_valueerror_subclass():
    assert issubclass(DuplicateEntityError, ValueError)
    exc = DuplicateEntityError("test_pid")
    assert isinstance(exc, ValueError)
