"""Tests for app_v2/services/joint_validation_summary.py — D-JV-16 (Plan 01-03 Task 2).

Covers:
- _strip_to_text decomposes <script>, <style>, <img> so script bodies, CSS,
  and base64 image src never reach the LLM (the user explicitly flagged
  inline base64 image src as a token-blow-up risk in D-JV-16).
- _strip_to_text uses BeautifulSoup.get_text(separator='\n') so adjacent
  block elements stay separated (not concatenated into a single token).
- _strip_to_text collapses runs of blank lines to a single blank line.
- _strip_to_text returns plain str (not NavigableString — Pitfall 9).
- get_or_generate_jv_summary caches by (page_id, mtime_ns) and reuses the
  Phase 3 _summary_cache + _summary_lock.
- Cache key has 'jv' string discriminator (Pitfall 3 — JV and platform
  summaries with same numeric id MUST NOT collide).
- get_or_generate_jv_summary calls _call_llm_with_text with the JV prompts
  (NOT the platform-notes prompts).
- Pre-processing applied BEFORE the LLM call.
- FileNotFoundError when index.html is missing (router translates to 200
  error fragment).
- regenerate=True bypasses cache lookup.
- Return shape is a BARE SummaryResult (text, llm_name, llm_model,
  generated_at) — router (Plan 04 Task 3) computes summary_html + age_s.

Mocking strategy: patch ``_call_llm_with_text`` in the joint_validation_summary
namespace so the real LLM is never called. Mirrors test_summary_service.py
``mocker.patch.object(summary_service, "_build_client", ...)`` idiom.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# CANONICAL: LLMConfig lives at app.core.config (verified at
# app_v2/services/summary_service.py:51). NOT app_v2.core.config.
from app.core.config import LLMConfig
from app_v2.data.jv_summary_prompt import (
    JV_SYSTEM_PROMPT,
    JV_USER_PROMPT_TEMPLATE,
)
from app_v2.services.joint_validation_summary import (
    _strip_to_text,
    get_or_generate_jv_summary,
)
from app_v2.services.summary_service import SummaryResult, clear_summary_cache


SAMPLE_HTML = b"""<!DOCTYPE html><html><body>
<script>alert('xss')</script>
<style>.x { color: red }</style>
<img src="data:image/png;base64,AAAABBBBCCCC">
<h1>Title</h1>
<p>kept paragraph</p>


<p>another paragraph</p>
</body></html>"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_cache():
    clear_summary_cache()
    yield
    clear_summary_cache()


@pytest.fixture
def llm_cfg() -> LLMConfig:
    """Mirrors test_summary_service.py::cfg_ollama — minimal valid LLMConfig.

    NOTE: LLMConfig has no timeout_s field (verified at app/core/config.py).
    Constructor args used here match the existing fixture pattern.
    """
    return LLMConfig(name="ollama-default", type="ollama", model="llama3.1")


@pytest.fixture
def jv_root(tmp_path: Path) -> Path:
    folder = tmp_path / "3193868109"
    folder.mkdir()
    (folder / "index.html").write_bytes(SAMPLE_HTML)
    return tmp_path


# ---------------------------------------------------------------------------
# _strip_to_text — D-JV-16 BS4 decompose pipeline
# ---------------------------------------------------------------------------


def test_strip_decomposes_script_style_img() -> None:
    text = _strip_to_text(SAMPLE_HTML)
    assert "kept paragraph" in text
    assert "alert" not in text
    # CSS rule body removed
    assert ".x" not in text or "color: red" not in text
    # base64 src payload removed (the specific user-flagged risk)
    assert "AAAABBBBCCCC" not in text
    assert "data:image" not in text
    assert "<img" not in text


def test_strip_collapses_runs_of_blank_lines() -> None:
    html = b"<html><body><p>A</p><p></p><p></p><p></p><p></p><p>B</p></body></html>"
    text = _strip_to_text(html)
    # No more than one consecutive blank line
    assert "\n\n\n" not in text


def test_strip_get_text_separator_newline() -> None:
    """Adjacent block elements are separated by '\\n', NOT concatenated."""
    html = b"<html><body><p>A</p><p>B</p></body></html>"
    text = _strip_to_text(html)
    # separator='\n' produces "A\nB" (with possible blank lines around);
    # the key invariant: 'AB' (no separator) MUST NOT appear.
    assert "AB" not in text
    assert "A" in text and "B" in text


def test_strip_returns_str_not_navigablestring() -> None:
    text = _strip_to_text(SAMPLE_HTML)
    assert type(text) is str


# ---------------------------------------------------------------------------
# get_or_generate_jv_summary — cache + LLM contract
# ---------------------------------------------------------------------------


def test_get_or_generate_jv_summary_caches_by_mtime(
    jv_root: Path, llm_cfg: LLMConfig
) -> None:
    with patch(
        "app_v2.services.joint_validation_summary._call_llm_with_text",
        return_value="# Cached output",
    ) as mock_llm:
        result1 = get_or_generate_jv_summary("3193868109", llm_cfg, jv_root)
        result2 = get_or_generate_jv_summary("3193868109", llm_cfg, jv_root)
    assert mock_llm.call_count == 1
    # Frozen dataclass: cache returns the same instance unchanged. The router
    # (Plan 04 Task 3) computes age_s from result.generated_at itself.
    assert result1 is result2
    assert result2.text == "# Cached output"


def test_get_or_generate_jv_summary_cache_key_has_jv_discriminator(
    jv_root: Path, llm_cfg: LLMConfig
) -> None:
    """The cache key MUST include the literal string 'jv' so JV and platform
    summaries on the same numeric id cannot collide (Pitfall 3, T-03-02)."""
    from app_v2.services.summary_service import _summary_cache

    with patch(
        "app_v2.services.joint_validation_summary._call_llm_with_text",
        return_value="# JV out",
    ):
        get_or_generate_jv_summary("3193868109", llm_cfg, jv_root)

    found_jv = False
    for k in _summary_cache.keys():
        if hasattr(k, "__iter__"):
            items = list(k)
            if "jv" in items and "3193868109" in items:
                found_jv = True
                break
    assert found_jv, "JV summary cache key missing 'jv' discriminator"


def test_get_or_generate_jv_summary_uses_jv_prompts(
    jv_root: Path, llm_cfg: LLMConfig
) -> None:
    with patch(
        "app_v2.services.joint_validation_summary._call_llm_with_text",
        return_value="out",
    ) as mock_llm:
        get_or_generate_jv_summary("3193868109", llm_cfg, jv_root)
    args, kwargs = mock_llm.call_args
    sys_prompt = args[2] if len(args) >= 3 else kwargs.get("system_prompt")
    usr_template = args[3] if len(args) >= 4 else kwargs.get("user_prompt_template")
    assert sys_prompt == JV_SYSTEM_PROMPT
    assert usr_template == JV_USER_PROMPT_TEMPLATE


def test_get_or_generate_jv_summary_passes_stripped_text(
    jv_root: Path, llm_cfg: LLMConfig
) -> None:
    """Pre-processing applied BEFORE the LLM sees the content (D-JV-16)."""
    with patch(
        "app_v2.services.joint_validation_summary._call_llm_with_text",
        return_value="out",
    ) as mock_llm:
        get_or_generate_jv_summary("3193868109", llm_cfg, jv_root)
    args, kwargs = mock_llm.call_args
    text = args[0] if args else kwargs.get("content")
    assert "<script>" not in text
    assert "<style>" not in text
    assert "<img" not in text
    assert "data:image" not in text
    assert "AAAABBBBCCCC" not in text
    assert "kept paragraph" in text  # body content survives


def test_get_or_generate_jv_summary_raises_filenotfound_for_missing_index(
    tmp_path: Path, llm_cfg: LLMConfig
) -> None:
    with pytest.raises(FileNotFoundError):
        get_or_generate_jv_summary("9999999", llm_cfg, tmp_path)


def test_get_or_generate_jv_summary_regenerate_skips_cache(
    jv_root: Path, llm_cfg: LLMConfig
) -> None:
    with patch(
        "app_v2.services.joint_validation_summary._call_llm_with_text",
        side_effect=["first", "second"],
    ) as mock_llm:
        result1 = get_or_generate_jv_summary("3193868109", llm_cfg, jv_root)
        result2 = get_or_generate_jv_summary(
            "3193868109", llm_cfg, jv_root, regenerate=True
        )
    assert mock_llm.call_count == 2
    # SummaryResult.text holds the LLM raw markdown (NOT pre-rendered HTML).
    assert result1.text == "first"
    assert result2.text == "second"


def test_get_or_generate_jv_summary_returns_bare_summaryresult(
    jv_root: Path, llm_cfg: LLMConfig
) -> None:
    """Service returns a BARE SummaryResult (text/llm_name/llm_model/generated_at).
    No summary_html, no backend_name, no cached_age_s — those are router concerns.
    Mirrors routers/summary.py:156-180 expectations of get_or_generate_summary."""
    with patch(
        "app_v2.services.joint_validation_summary._call_llm_with_text",
        return_value="# raw markdown",
    ):
        result = get_or_generate_jv_summary("3193868109", llm_cfg, jv_root)
    assert isinstance(result, SummaryResult)
    assert result.text == "# raw markdown"
    assert result.llm_name == llm_cfg.name
    assert result.llm_model == llm_cfg.model
    assert isinstance(result.generated_at, datetime)
    assert result.generated_at.tzinfo is not None  # UTC tz-aware
    # Negative checks: fields that DO NOT exist on the dataclass
    assert not hasattr(result, "summary_html")
    assert not hasattr(result, "backend_name")
    assert not hasattr(result, "cached_age_s")
