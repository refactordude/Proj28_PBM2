"""Tests for load_starter_prompts (ONBD-01, ONBD-02)."""
from __future__ import annotations

import pathlib
import pytest
import yaml


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Create a clean config/ dir and chdir so load_starter_prompts reads from it."""
    cfg = tmp_path / "config"
    cfg.mkdir()
    monkeypatch.chdir(tmp_path)
    return cfg


def _write_yaml(path: pathlib.Path, entries: list[dict]) -> None:
    path.write_text(yaml.safe_dump(entries), encoding="utf-8")


def test_returns_empty_when_both_files_missing(isolated_config):
    from app.pages.ask import load_starter_prompts
    assert load_starter_prompts() == []


def test_falls_back_to_example(isolated_config):
    _write_yaml(
        isolated_config / "starter_prompts.example.yaml",
        [{"label": "A", "question": "q1"}, {"label": "B", "question": "q2"}],
    )
    from app.pages.ask import load_starter_prompts
    result = load_starter_prompts()
    assert len(result) == 2
    assert result[0]["label"] == "A"


def test_user_yaml_overrides_example(isolated_config):
    _write_yaml(
        isolated_config / "starter_prompts.example.yaml",
        [{"label": "Example", "question": "from example"}],
    )
    _write_yaml(
        isolated_config / "starter_prompts.yaml",
        [{"label": "User", "question": "from user"}],
    )
    from app.pages.ask import load_starter_prompts
    result = load_starter_prompts()
    assert len(result) == 1
    assert result[0]["label"] == "User"


def test_returns_empty_on_null_yaml(isolated_config):
    (isolated_config / "starter_prompts.example.yaml").write_text("", encoding="utf-8")
    from app.pages.ask import load_starter_prompts
    assert load_starter_prompts() == []


def test_filters_out_malformed_entries(isolated_config):
    _write_yaml(
        isolated_config / "starter_prompts.example.yaml",
        [
            {"label": "Good", "question": "q"},
            {"label": "Missing question"},  # no question key
            "not a dict",                    # str instead of dict
        ],
    )
    from app.pages.ask import load_starter_prompts
    result = load_starter_prompts()
    assert len(result) == 1
    assert result[0]["label"] == "Good"


def test_shipped_example_file_is_valid():
    """Meta-test: the committed example YAML has exactly 8 valid entries."""
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    path = repo_root / "config" / "starter_prompts.example.yaml"
    with path.open() as f:
        data = yaml.safe_load(f)
    assert isinstance(data, list)
    assert len(data) == 8
    for entry in data:
        assert "label" in entry and "question" in entry
        assert len(entry["label"]) <= 40
