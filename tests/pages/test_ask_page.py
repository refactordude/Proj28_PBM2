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


# ---------------------------------------------------------------------------
# NL-05 param confirmation tests (Plan 02-05)
#
# Notes:
#   - AppTest runs ask.py in an isolated script context; monkeypatching imported
#     module objects has no effect (same limitation as documented in Plan 02-04).
#   - Tests that require the multiselect to render set active_db="" so that
#     get_db_adapter returns None, triggering the graceful-degradation path that
#     still renders the multiselect (using only agent-proposed params as options).
#   - This matches the actual degraded-DB UX — useful for offline/test scenarios.
# ---------------------------------------------------------------------------

def test_param_confirmation_multiselect_renders_when_pending():
    """NL-05: multiselect 'Parameters to include' renders when ask.pending_params is set."""
    at = AppTest.from_file("app/pages/ask.py", default_timeout=60)
    at.session_state["ask.pending_params"] = ["cat / item1", "cat / item2"]
    at.session_state["ask.pending_message"] = "Please confirm parameters."
    # active_db="" -> get_db_adapter returns None -> graceful degradation path
    at.session_state["active_db"] = ""
    at.run()
    assert not at.exception, f"Unexpected exception: {at.exception}"
    labels = [m.label for m in at.multiselect]
    assert "Parameters to include" in labels, (
        f"Expected 'Parameters to include' multiselect, got labels: {labels}"
    )
    # Caption should mention agent proposed 2 parameters
    caps = [c.value for c in at.caption]
    assert any("Agent proposed 2 parameters" in c for c in caps), (
        f"Expected caption with 'Agent proposed 2 parameters', got: {caps}"
    )


def test_no_confirmation_row_when_pending_empty():
    """NL-05: no param confirmation multiselect when ask.pending_params is empty."""
    at = AppTest.from_file("app/pages/ask.py", default_timeout=60)
    at.session_state["ask.pending_params"] = []
    at.run()
    assert not at.exception, f"Unexpected exception: {at.exception}"
    labels = [m.label for m in at.multiselect]
    assert "Parameters to include" not in labels, (
        f"Expected no confirmation multiselect but got: {labels}"
    )


def test_first_turn_ask_button_shown_when_no_pending():
    """NL-05: 'Ask' primary button visible when no pending params."""
    at = AppTest.from_file("app/pages/ask.py", default_timeout=60)
    at.session_state["ask.pending_params"] = []
    at.run()
    assert not at.exception, f"Unexpected exception: {at.exception}"
    button_labels = [b.label for b in at.button]
    assert "Ask" in button_labels, (
        f"Expected 'Ask' button but got labels: {button_labels}"
    )
    assert "Run Query" not in button_labels, (
        f"Expected no 'Run Query' button but got labels: {button_labels}"
    )


def test_run_query_button_shown_only_when_pending():
    """NL-05: 'Run Query' primary button visible when pending params exist."""
    at = AppTest.from_file("app/pages/ask.py", default_timeout=60)
    at.session_state["ask.pending_params"] = ["cat / item1"]
    # active_db="" -> get_db_adapter returns None -> graceful degradation path
    at.session_state["active_db"] = ""
    at.run()
    assert not at.exception, f"Unexpected exception: {at.exception}"
    button_labels = [b.label for b in at.button]
    assert "Run Query" in button_labels, (
        f"Expected 'Run Query' button but got labels: {button_labels}"
    )
