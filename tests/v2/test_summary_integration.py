"""End-to-end integration tests for Phase 03: content + summary chain.

Differs from ``test_summary_routes.py`` (which mocks the SDK shape and tests the
route in isolation): these tests exercise the real FastAPI app via TestClient
with only the ``_build_client`` LLM client factory mocked (D-23 idiom). They
verify the integration seams between ``content_store`` (Plan 02),
``summary_service`` (Plan 03), and the route layer.

Coverage:
  1. POST save → POST summary → success card with bullets + metadata.
  2. Two summary calls with same content → 1 LLM call (cache hit).
  3. ``X-Regenerate: true`` bypasses lookup but writes back (D-18).
  4. Saving new content (mtime_ns changes) invalidates the summary cache.
  5. LLM ConnectError → 200 + amber alert (NEVER 5xx — UI-SPEC contract).
  6. Missing content → 200 + amber alert ("Content page no longer exists").
  7. Concurrent same-key threads do not corrupt the cache (single entry post-run).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient

import app_v2.routers.overview as overview_mod
import app_v2.routers.platforms as platforms_mod
import app_v2.services.overview_store as overview_store_mod
import app_v2.services.summary_service as summary_service_mod
from app.core.config import AppConfig, LLMConfig, Settings


_PID = "IntegTest_Pid_SM8550"
_FAKE_CATALOG = [_PID]


def _build_chat_response(mocker, text: str):
    """Create a fake openai chat-completion response with the given content."""
    fake = mocker.MagicMock()
    fake.choices = [mocker.MagicMock(message=mocker.MagicMock(content=text))]
    return fake


@pytest.fixture()
def integrated_app(tmp_path, monkeypatch, mocker):
    """Full app with isolated tmp content_dir + mocked LLM client + reset cache.

    Yields ``(client, content_dir, mock_client)``. The ``mock_client``
    ``chat.completions.create.return_value`` is the default fake response;
    tests can override ``side_effect`` to raise exceptions or return per-call
    responses.
    """
    cd = tmp_path / "content" / "platforms"
    cd.mkdir(parents=True)

    monkeypatch.setattr(platforms_mod, "CONTENT_DIR", cd)
    monkeypatch.setattr(overview_mod, "CONTENT_DIR", cd)
    monkeypatch.setattr(
        overview_store_mod, "OVERVIEW_YAML", tmp_path / "overview.yaml"
    )
    monkeypatch.setattr(
        overview_mod,
        "list_platforms",
        lambda db, db_name="": list(_FAKE_CATALOG),
    )

    # Reset summary cache between tests.
    summary_service_mod.clear_summary_cache()

    # Patch the LLM client builder — no real OpenAI() instantiation.
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = _build_chat_response(
        mocker, "• integration bullet 1\n• integration bullet 2"
    )
    mocker.patch.object(
        summary_service_mod, "_build_client", return_value=mock_client
    )

    from app_v2.main import app

    with TestClient(app) as client:
        # Override settings AFTER lifespan ran (lifespan loads real config).
        # Mirrors the proven pattern from tests/v2/test_summary_routes.py::isolated_summary.
        app.state.settings = Settings(
            databases=[],
            llms=[
                LLMConfig(
                    name="ollama-default",
                    type="ollama",
                    model="llama3.1",
                )
            ],
            app=AppConfig(default_llm="ollama-default"),
        )
        yield client, cd, mock_client

    # Clear cache after test to prevent bleed across tests.
    summary_service_mod.clear_summary_cache()


# ---------------------------------------------------------------------------
# 1. End-to-end save → summary
# ---------------------------------------------------------------------------

def test_save_then_summary_renders_success_card(integrated_app):
    """End-to-end: POST save → POST summary → success fragment with bullets."""
    client, cd, mock_client = integrated_app

    # Save content via the actual route (Plan 02).
    r_save = client.post(
        f"/platforms/{_PID}",
        data={"content": "# Integration\n\nThis is a test."},
    )
    assert r_save.status_code == 200, r_save.text
    target = cd / f"{_PID}.md"
    assert target.is_file()

    # Request summary.
    r_sum = client.post(f"/platforms/{_PID}/summary")
    assert r_sum.status_code == 200
    assert "integration bullet 1" in r_sum.text
    # NOT an error fragment.
    assert "alert alert-warning" not in r_sum.text
    assert "Regenerate" in r_sum.text
    # Metadata footer with backend identity.
    assert "ollama-default" in r_sum.text
    assert "llama3.1" in r_sum.text
    assert mock_client.chat.completions.create.call_count == 1


# ---------------------------------------------------------------------------
# 2. Cache hit on second call
# ---------------------------------------------------------------------------

def test_summary_cache_hit_returns_same_text_no_extra_llm_call(integrated_app):
    """Two summary calls with same content → 1 LLM call (cache hit on second)."""
    client, cd, mock_client = integrated_app

    client.post(f"/platforms/{_PID}", data={"content": "# notes"})
    r1 = client.post(f"/platforms/{_PID}/summary")
    r2 = client.post(f"/platforms/{_PID}/summary")

    assert r1.status_code == r2.status_code == 200
    assert "integration bullet 1" in r1.text
    assert "integration bullet 1" in r2.text
    assert mock_client.chat.completions.create.call_count == 1, (
        "Second call should hit cache; LLM call count should remain 1"
    )


# ---------------------------------------------------------------------------
# 3. X-Regenerate header behavior
# ---------------------------------------------------------------------------

def test_summary_regenerate_header_bypasses_cache(integrated_app):
    """X-Regenerate: true bypasses cache lookup and increments LLM call count.

    D-18: regenerate skips lookup BUT writes back. Subsequent normal call hits
    the refreshed cache (no third LLM call).
    """
    client, cd, mock_client = integrated_app

    client.post(f"/platforms/{_PID}", data={"content": "# notes"})
    client.post(f"/platforms/{_PID}/summary")  # call 1 — populates cache
    client.post(
        f"/platforms/{_PID}/summary",
        headers={"X-Regenerate": "true"},
    )  # call 2 — bypassed lookup, writes back
    client.post(f"/platforms/{_PID}/summary")  # call 3 — cache hit on refreshed value

    assert mock_client.chat.completions.create.call_count == 2, (
        "Regenerate bypasses lookup BUT writes back; subsequent normal call "
        "hits the new value"
    )


# ---------------------------------------------------------------------------
# 4. Cache invalidation on content edit (mtime_ns change)
# ---------------------------------------------------------------------------

def test_summary_after_content_edit_invalidates_cache(integrated_app, mocker):
    """Saving new content (mtime_ns changes) invalidates the summary cache for that pid.

    Cache key includes ``mtime_ns``; a fresh ``os.replace`` produces a fresh
    ``st_mtime_ns`` even within the same wall-clock second on Linux ext4 (the
    test FS), so the second request misses the cache and re-invokes the LLM.
    """
    client, cd, mock_client = integrated_app

    # Per-call response queue: first call returns "resp 1", second "resp 2".
    responses = [
        _build_chat_response(mocker, "# resp 1"),
        _build_chat_response(mocker, "# resp 2"),
    ]
    idx = [0]

    def _next_response(*_args, **_kwargs):
        i = min(idx[0], len(responses) - 1)
        idx[0] += 1
        return responses[i]

    mock_client.chat.completions.create.side_effect = _next_response

    # Save initial content; first summary returns "# resp 1".
    client.post(f"/platforms/{_PID}", data={"content": "first"})
    r1 = client.post(f"/platforms/{_PID}/summary")
    assert "resp 1" in r1.text

    # Save new content; mtime_ns changes → cache miss → second summary.
    client.post(
        f"/platforms/{_PID}", data={"content": "second different content"}
    )
    r2 = client.post(f"/platforms/{_PID}/summary")
    assert "resp 2" in r2.text


# ---------------------------------------------------------------------------
# 5. Error fragment on LLM failure (no 5xx)
# ---------------------------------------------------------------------------

def test_summary_returns_error_fragment_on_llm_failure(integrated_app):
    """LLM raises ConnectError → 200 with amber alert (NEVER 5xx)."""
    client, cd, mock_client = integrated_app
    mock_client.chat.completions.create.side_effect = httpx.ConnectError(
        "simulated"
    )

    client.post(f"/platforms/{_PID}", data={"content": "# notes"})
    r = client.post(f"/platforms/{_PID}/summary")
    # MUST be 200, not 5xx (UI-SPEC contract).
    assert r.status_code == 200, r.text
    assert "alert alert-warning" in r.text
    assert "Cannot reach the LLM backend" in r.text
    assert "Retry" in r.text


# ---------------------------------------------------------------------------
# 6. Error fragment when content file missing
# ---------------------------------------------------------------------------

def test_summary_returns_error_fragment_when_content_missing(integrated_app):
    """Summary on a platform with no content file → 200 with 'Content page no longer exists'."""
    client, _cd, _mc = integrated_app
    r = client.post(f"/platforms/{_PID}/summary")
    # No content file was created; summary_service raises FileNotFoundError →
    # classified to the fixed user-facing string.
    assert r.status_code == 200, r.text
    assert "alert alert-warning" in r.text
    assert "Content page no longer exists" in r.text


# ---------------------------------------------------------------------------
# 7. Concurrent same-key thread test (cache invariant under contention)
# ---------------------------------------------------------------------------

def test_concurrent_summary_same_key_no_cache_corruption(tmp_path, mocker):
    """8 threads call get_or_generate_summary concurrently with the same key.

    Lock guards only dict access; the LLM call may run multiple times
    (acceptable per Pitfall 11). Assert: no exception, all return
    SummaryResult, cache contains exactly 1 entry for the key.
    """
    from app_v2.services import summary_service

    cd = tmp_path / "content" / "platforms"
    cd.mkdir(parents=True)
    pid = "Concurrent_Pid_SM8550"
    (cd / f"{pid}.md").write_text("# notes", encoding="utf-8")

    summary_service.clear_summary_cache()

    fake_resp = _build_chat_response(mocker, "• thread bullet")
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = fake_resp
    mocker.patch.object(
        summary_service, "_build_client", return_value=mock_client
    )

    cfg = LLMConfig(name="ollama-default", type="ollama", model="llama3.1")

    def _call():
        return summary_service.get_or_generate_summary(pid, cfg, cd)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = [f.result() for f in [pool.submit(_call) for _ in range(8)]]

    assert len(results) == 8
    assert all(r.text == "• thread bullet" for r in results)
    # Cache should contain at most 1 entry for this key (some threads may have
    # written concurrently, but the dict mutation is lock-protected → final
    # state is exactly 1 entry).
    assert len(summary_service._summary_cache) == 1, (
        f"expected 1 cache entry, got {len(summary_service._summary_cache)}"
    )

    # Cleanup so cache state does not bleed into subsequent tests.
    summary_service.clear_summary_cache()
