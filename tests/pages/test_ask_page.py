"""Smoke test for app/pages/ask.py using Streamlit AppTest.

Notes on timeout:
  - ask.py imports pydantic_ai + nest_asyncio at module level, which adds ~12-15s
    of cold-start time in AppTest (in-process module loading). All tests use
    default_timeout=60 to accommodate this.
  - Sensitivity warning tests set SETTINGS_PATH to point at a fixture YAML file
    containing the desired LLM config, because AppTest runs ask.py as a subprocess
    and monkeypatching the already-imported module has no effect on the script run.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml
from streamlit.testing.v1 import AppTest


# ---------------------------------------------------------------------------
# Basic structural tests (from_file — require the full ask.py cold start)
# ---------------------------------------------------------------------------

def test_ask_page_module_imports_without_error():
    """Smoke: ensure ask.py parses and its top-level code runs in an AppTest."""
    at = AppTest.from_file("app/pages/ask.py", default_timeout=60)
    at.run()
    # On empty session state, page must not crash.
    assert not at.exception, f"Unexpected exception: {at.exception}"


def test_ask_page_shows_title():
    at = AppTest.from_file("app/pages/ask.py", default_timeout=60)
    at.run()
    titles = [t.value for t in at.title]
    assert "Ask" in titles


def test_ask_page_shows_starter_gallery_on_empty_history():
    at = AppTest.from_file("app/pages/ask.py", default_timeout=60)
    at.session_state["ask.history"] = []
    at.run()
    # Gallery subheader present
    subs = [s.value for s in at.subheader]
    assert "Try asking..." in subs


def test_ask_page_shows_history_panel_with_zero_count():
    at = AppTest.from_file("app/pages/ask.py", default_timeout=60)
    at.run()
    # Expander labeled "History (0)" present on empty state
    expander_labels = [exp.label for exp in at.expander]
    assert "History (0)" in expander_labels


# ---------------------------------------------------------------------------
# Sensitivity warning tests — use a fixture YAML file via SETTINGS_PATH so
# that load_settings() inside ask.py returns the desired LLM config.
# ---------------------------------------------------------------------------

def _make_settings_yaml(llm_type: str, llm_name: str) -> str:
    """Write a temporary YAML settings file and return its path."""
    data = {
        "databases": [],
        "llms": [{"name": llm_name, "type": llm_type, "model": "", "endpoint": ""}],
        "app": {"default_database": "", "default_llm": ""},
    }
    fd, path = tempfile.mkstemp(suffix=".yaml", prefix="pbm2_test_")
    with os.fdopen(fd, "w") as f:
        yaml.safe_dump(data, f)
    return path


def test_ask_page_sensitivity_warning_shown_when_openai_active():
    settings_path = _make_settings_yaml("openai", "dummy_openai")
    try:
        orig_settings = os.environ.get("SETTINGS_PATH")
        os.environ["SETTINGS_PATH"] = settings_path

        at = AppTest.from_file("app/pages/ask.py", default_timeout=60)
        at.session_state["active_llm"] = "dummy_openai"
        at.session_state["ask.openai_warning_dismissed"] = False
        at.run()

        assert not at.exception, f"Unexpected exception: {at.exception}"
        warnings = [w.value for w in at.warning]
        assert any("OpenAI's servers" in w for w in warnings), (
            f"Expected sensitivity warning but got: {warnings}"
        )
    finally:
        if orig_settings is None:
            os.environ.pop("SETTINGS_PATH", None)
        else:
            os.environ["SETTINGS_PATH"] = orig_settings
        Path(settings_path).unlink(missing_ok=True)


def test_ask_page_no_sensitivity_warning_when_ollama():
    settings_path = _make_settings_yaml("ollama", "dummy_ollama")
    try:
        orig_settings = os.environ.get("SETTINGS_PATH")
        os.environ["SETTINGS_PATH"] = settings_path

        at = AppTest.from_file("app/pages/ask.py", default_timeout=60)
        at.session_state["active_llm"] = "dummy_ollama"
        at.run()

        assert not at.exception, f"Unexpected exception: {at.exception}"
        warnings = [w.value for w in at.warning]
        assert not any("OpenAI's servers" in w for w in warnings), (
            f"Expected no sensitivity warning but got: {warnings}"
        )
    finally:
        if orig_settings is None:
            os.environ.pop("SETTINGS_PATH", None)
        else:
            os.environ["SETTINGS_PATH"] = orig_settings
        Path(settings_path).unlink(missing_ok=True)
