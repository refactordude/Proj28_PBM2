"""Tests for app_v2/services/summary_service.py (Plan 03-03, SUMMARY-04..07).

Covers:
- Cache hit / miss with hashkey(pid, mtime_ns, llm_name, llm_model) — Pitfall 13.
- mtime mutation invalidates the cache (D-25 — os.utime advances ns by 1s).
- TTL expiry — patch _Timer__timer (Pitfall 14, cachetools v7 idiom from
  tests/v2/test_cache.py:179-205).
- Regenerate=True bypasses lookup AND writes back (D-18).
- Error classification — 7-string vocabulary (UI-SPEC §8c).
- _build_client for both Ollama and OpenAI (Pattern 5).
- FileNotFoundError raised when content is missing.

Mocking strategy (D-23):
``mocker.patch.object(summary_service, '_build_client', return_value=mock_client)``
— same module-level patch idiom as v1.0 ``tests/agent/test_nl_agent.py``.
Patching the builder dodges OpenAI() instantiation (which would otherwise
require api_key validation).

NOTE on openai 2.32.0 exception construction:
- ``AuthenticationError`` / ``RateLimitError`` / ``APIStatusError`` require
  ``message: str``, ``response: httpx.Response``, ``body: object | None``.
  We use ``MagicMock(spec=httpx.Response)`` to satisfy the signature.
- ``APIConnectionError`` requires ``request: httpx.Request`` keyword arg.
- ``APITimeoutError(request=...)`` — sole positional ``request`` arg.
- ``httpx.ConnectError`` / ``httpx.ReadTimeout`` — direct ``("msg")`` works.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import httpx
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)

from app.core.config import LLMConfig

# Importing under test — module path is verified at test-collection time.
from app_v2.services import summary_service
from app_v2.services.summary_service import SummaryResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_summary_cache():
    """Ensure no cross-test cache pollution."""
    summary_service._summary_cache.clear()
    yield
    summary_service._summary_cache.clear()


@pytest.fixture
def cfg_ollama():
    return LLMConfig(name="ollama-default", type="ollama", model="llama3.1")


@pytest.fixture
def cfg_openai():
    return LLMConfig(
        name="my-openai",
        type="openai",
        model="gpt-4o-mini",
        api_key="sk-test",
    )


@pytest.fixture
def content_dir(tmp_path):
    cd = tmp_path / "platforms"
    cd.mkdir()
    return cd


def _make_mock_client(mocker, text: str = "bullet 1\nbullet 2"):
    fake_resp = mocker.MagicMock()
    fake_resp.choices = [
        mocker.MagicMock(message=mocker.MagicMock(content=text))
    ]
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = fake_resp
    return mock_client


# ---------------------------------------------------------------------------
# Cache hit / miss / regenerate / mtime invalidation (D-25)
# ---------------------------------------------------------------------------


def test_summary_calls_llm_once_then_caches(mocker, cfg_ollama, content_dir):
    """Two consecutive calls with same key → LLM called once."""
    mock_client = _make_mock_client(mocker)
    mocker.patch.object(summary_service, "_build_client", return_value=mock_client)
    (content_dir / "PID1.md").write_text("# notes", encoding="utf-8")

    r1 = summary_service.get_or_generate_summary("PID1", cfg_ollama, content_dir)
    r2 = summary_service.get_or_generate_summary("PID1", cfg_ollama, content_dir)

    assert r1.text == r2.text == "bullet 1\nbullet 2"
    assert mock_client.chat.completions.create.call_count == 1


def test_summary_cache_invalidates_on_mtime_change(mocker, cfg_ollama, content_dir):
    """os.utime advancing mtime_ns by 1s → cache miss on next call."""
    mock_client = _make_mock_client(mocker)
    mocker.patch.object(summary_service, "_build_client", return_value=mock_client)
    target = content_dir / "PID1.md"
    target.write_text("# v1", encoding="utf-8")

    summary_service.get_or_generate_summary("PID1", cfg_ollama, content_dir)
    # Advance mtime by 1 full second (deterministic; doesn't depend on FS resolution).
    cur_ns = target.stat().st_mtime_ns
    os.utime(target, ns=(cur_ns + 1_000_000_000, cur_ns + 1_000_000_000))
    summary_service.get_or_generate_summary("PID1", cfg_ollama, content_dir)

    assert mock_client.chat.completions.create.call_count == 2


def test_summary_regenerate_bypasses_cache_but_writes_back(
    mocker, cfg_ollama, content_dir
):
    """D-18: regenerate=True skips lookup but stores result under same key.

    Sequence:
      1) call → miss, LLM call 1
      2) call regenerate=True → cache bypassed, LLM call 2 (different mock value)
      3) call regenerate=False → HIT on the freshly-written value (no LLM)
    """
    target = content_dir / "PID1.md"
    target.write_text("# notes", encoding="utf-8")

    mock_client = _make_mock_client(mocker, text="first")
    mocker.patch.object(summary_service, "_build_client", return_value=mock_client)

    r1 = summary_service.get_or_generate_summary("PID1", cfg_ollama, content_dir)
    assert r1.text == "first"

    # Switch the mock's return value before the regenerate call.
    fake_resp = mocker.MagicMock()
    fake_resp.choices = [
        mocker.MagicMock(message=mocker.MagicMock(content="second"))
    ]
    mock_client.chat.completions.create.return_value = fake_resp

    r2 = summary_service.get_or_generate_summary(
        "PID1", cfg_ollama, content_dir, regenerate=True
    )
    assert r2.text == "second"
    assert mock_client.chat.completions.create.call_count == 2

    # Third call: should HIT the regenerated value — LLM count stays at 2.
    r3 = summary_service.get_or_generate_summary("PID1", cfg_ollama, content_dir)
    assert r3.text == "second"
    assert mock_client.chat.completions.create.call_count == 2


def test_summary_returns_summary_result_with_metadata(mocker, cfg_ollama, content_dir):
    """SummaryResult fields populated; generated_at is tz-aware UTC."""
    mock_client = _make_mock_client(mocker, text="• one")
    mocker.patch.object(summary_service, "_build_client", return_value=mock_client)
    (content_dir / "PID1.md").write_text("# notes", encoding="utf-8")

    r = summary_service.get_or_generate_summary("PID1", cfg_ollama, content_dir)
    assert isinstance(r, SummaryResult)
    assert r.text == "• one"
    assert r.llm_name == "ollama-default"
    assert r.llm_model == "llama3.1"
    assert r.generated_at.tzinfo is not None  # UTC tz-aware


def test_summary_cache_key_uses_mtime_ns_not_float(mocker, cfg_ollama, content_dir):
    """Pitfall 13: cache key tuple must contain integer mtime_ns, not float."""
    mock_client = _make_mock_client(mocker)
    mocker.patch.object(summary_service, "_build_client", return_value=mock_client)
    target = content_dir / "PID1.md"
    target.write_text("# notes", encoding="utf-8")

    summary_service.get_or_generate_summary("PID1", cfg_ollama, content_dir)
    keys = list(summary_service._summary_cache.keys())
    assert len(keys) == 1, f"expected 1 cache entry, got {len(keys)}"
    key_tuple = tuple(keys[0])
    # Find the integer that is not pid/name/model and not None: the mtime_ns.
    int_components = [v for v in key_tuple if isinstance(v, int) and not isinstance(v, bool)]
    float_components = [v for v in key_tuple if isinstance(v, float)]
    assert int_components, f"expected an int component in key {key_tuple}"
    assert not float_components, (
        f"key contains a float — Pitfall 13 violation: {key_tuple}"
    )


def test_summary_raises_filenotfounderror_when_content_missing(
    mocker, cfg_ollama, content_dir
):
    """No file → FileNotFoundError (route maps to error fragment)."""
    mock_client = _make_mock_client(mocker)
    mocker.patch.object(summary_service, "_build_client", return_value=mock_client)
    with pytest.raises(FileNotFoundError):
        summary_service.get_or_generate_summary("MISSING", cfg_ollama, content_dir)
    # No LLM call wasted on a missing file.
    assert mock_client.chat.completions.create.call_count == 0


# ---------------------------------------------------------------------------
# TTL expiry (Pitfall 14 — _Timer__timer pattern)
# ---------------------------------------------------------------------------


def test_summary_cache_ttl_expiry(mocker, cfg_ollama, content_dir):
    """Advance the cachetools _Timer past 3600s → second call re-invokes LLM."""
    target = content_dir / "PID1.md"
    target.write_text("# notes", encoding="utf-8")

    mock_client = _make_mock_client(mocker)
    mocker.patch.object(summary_service, "_build_client", return_value=mock_client)

    cache = summary_service._summary_cache
    timer_obj = cache.timer
    original_inner = timer_obj._Timer__timer
    fake_time = [1000.0]
    timer_obj._Timer__timer = lambda: fake_time[0]
    try:
        summary_service.get_or_generate_summary("PID1", cfg_ollama, content_dir)
        # Advance past 3600s TTL.
        fake_time[0] += 3601
        summary_service.get_or_generate_summary("PID1", cfg_ollama, content_dir)
        assert mock_client.chat.completions.create.call_count == 2
    finally:
        timer_obj._Timer__timer = original_inner


# ---------------------------------------------------------------------------
# Error classification (D-26 / UI-SPEC §8c) — parametrized over the 7-string vocabulary
# ---------------------------------------------------------------------------


def _httpx_response_mock(mocker, status: int):
    """Build a MagicMock satisfying ``response: httpx.Response`` arg."""
    resp = mocker.MagicMock(spec=httpx.Response)
    resp.status_code = status
    return resp


def _httpx_request_mock(mocker):
    return mocker.MagicMock(spec=httpx.Request)


def test_classify_connect_error_to_string():
    s = summary_service._classify_error(httpx.ConnectError("boom"), "Ollama")
    assert s == "Cannot reach the LLM backend (Ollama)"


def test_classify_apiconnection_error_to_string(mocker):
    exc = APIConnectionError(request=_httpx_request_mock(mocker))
    s = summary_service._classify_error(exc, "OpenAI")
    assert s == "Cannot reach the LLM backend (OpenAI)"


def test_classify_timeout_error_to_string():
    s = summary_service._classify_error(httpx.ReadTimeout("slow"), "Ollama")
    assert s == "LLM took too long to respond"


def test_classify_apitimeout_error_to_string(mocker):
    exc = APITimeoutError(request=_httpx_request_mock(mocker))
    s = summary_service._classify_error(exc, "Ollama")
    assert s == "LLM took too long to respond"


def test_classify_auth_error_to_string(mocker):
    exc = AuthenticationError(
        message="bad key",
        response=_httpx_response_mock(mocker, 401),
        body=None,
    )
    s = summary_service._classify_error(exc, "OpenAI")
    assert s == "LLM authentication failed — check API key in Settings"


def test_classify_rate_limit_error(mocker):
    exc = RateLimitError(
        message="slow down",
        response=_httpx_response_mock(mocker, 429),
        body=None,
    )
    s = summary_service._classify_error(exc, "OpenAI")
    assert s == "LLM is rate-limited — try again in a moment"


def test_classify_status_error_5xx(mocker):
    exc = APIStatusError(
        message="bad gateway",
        response=_httpx_response_mock(mocker, 502),
        body=None,
    )
    s = summary_service._classify_error(exc, "OpenAI")
    assert s == "LLM backend returned an error (HTTP 502)"


def test_classify_file_not_found():
    s = summary_service._classify_error(FileNotFoundError("gone"), "Ollama")
    assert s == "Content page no longer exists"


def test_classify_unknown_exception():
    s = summary_service._classify_error(ValueError("???"), "Ollama")
    assert s == "Unexpected error — see server logs"


# ---------------------------------------------------------------------------
# _build_client (Pattern 5, D-19, Pitfall 18)
# ---------------------------------------------------------------------------


def test_build_client_ollama_uses_v1_base_url():
    cfg = LLMConfig(
        name="ollama",
        type="ollama",
        model="llama3.1",
        endpoint="http://localhost:11434",
    )
    client = summary_service._build_client(cfg)
    # OpenAI client coerces base_url to a URL object; use str() for compare.
    assert str(client.base_url).rstrip("/").endswith("/v1")


def test_build_client_ollama_default_endpoint_when_none():
    cfg = LLMConfig(name="ollama", type="ollama", model="llama3.1")  # endpoint=""
    client = summary_service._build_client(cfg)
    assert "11434" in str(client.base_url)
    assert str(client.base_url).rstrip("/").endswith("/v1")


def test_build_client_openai_uses_endpoint_or_none(cfg_openai):
    client = summary_service._build_client(cfg_openai)
    # api_key is set on the client; we don't compare directly because the SDK
    # may wrap it. Verify the attribute exists and is non-empty.
    assert getattr(client, "api_key", "") == "sk-test"


def test_build_client_openai_raises_when_no_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = LLMConfig(name="oai", type="openai", model="gpt-4o-mini", api_key="")
    with pytest.raises(RuntimeError):
        summary_service._build_client(cfg)


def test_build_client_openai_uses_env_var_when_cfg_empty(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fromenv")
    cfg = LLMConfig(name="oai", type="openai", model="gpt-4o-mini", api_key="")
    client = summary_service._build_client(cfg)
    assert getattr(client, "api_key", "") == "sk-fromenv"


# ---------------------------------------------------------------------------
# Lock-not-held-during-LLM-call invariant (smoke)
# ---------------------------------------------------------------------------


def test_lock_not_held_during_llm_call(mocker, cfg_ollama, content_dir):
    """The LLM call must run OUTSIDE the cache lock (Pitfall 11 rationale).

    We verify by trying to acquire the lock from a side-effect inside
    chat.completions.create; if the lock were held, this would deadlock and
    the test would hang (caught by pytest's per-test timeout in CI). For local
    runs, we use a non-blocking attempt and assert it succeeds.
    """
    (content_dir / "PID1.md").write_text("# notes", encoding="utf-8")

    lock_state = {"acquired_during_call": False}

    def _create_side_effect(*args, **kwargs):
        # Try a non-blocking acquire; if the outer code holds the lock this
        # returns False. We expect True (lock NOT held during the LLM call).
        if summary_service._summary_lock.acquire(blocking=False):
            lock_state["acquired_during_call"] = True
            summary_service._summary_lock.release()
        fake_resp = mocker.MagicMock()
        fake_resp.choices = [mocker.MagicMock(message=mocker.MagicMock(content="ok"))]
        return fake_resp

    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.side_effect = _create_side_effect
    mocker.patch.object(summary_service, "_build_client", return_value=mock_client)

    summary_service.get_or_generate_summary("PID1", cfg_ollama, content_dir)
    assert lock_state["acquired_during_call"], (
        "lock was held during LLM call — would serialize concurrent requests"
    )


# ---------------------------------------------------------------------------
# clear_summary_cache helper (parity with cache.py::clear_all_caches)
# ---------------------------------------------------------------------------


def test_clear_summary_cache_invalidates(mocker, cfg_ollama, content_dir):
    mock_client = _make_mock_client(mocker, text="first")
    mocker.patch.object(summary_service, "_build_client", return_value=mock_client)
    (content_dir / "PID1.md").write_text("# notes", encoding="utf-8")

    summary_service.get_or_generate_summary("PID1", cfg_ollama, content_dir)
    summary_service.clear_summary_cache()
    summary_service.get_or_generate_summary("PID1", cfg_ollama, content_dir)
    assert mock_client.chat.completions.create.call_count == 2
