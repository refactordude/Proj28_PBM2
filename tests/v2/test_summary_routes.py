"""Tests for Phase 03 Plan 03-03 summary route — POST /platforms/{pid}/summary.

Contract under test (UI-SPEC §8b/§8c, D-12..D-21, SUMMARY-02..07):

- ALWAYS 200. The route NEVER returns 5xx — every LLM failure becomes a 200
  with the amber-warning fragment so the swap lands inline in
  ``#summary-{pid}``, NOT in the global ``#htmx-error-container``.
- Success body contains the rendered summary HTML, ``ai-btn regen`` Regenerate
  button, ``X-Regenerate`` header in the button's hx-headers attribute, and the
  metadata footer (``llm_name · llm_model``).
- Cache hit on second call (no extra LLM invocation).
- ``X-Regenerate: true`` header bypasses the cache lookup but writes the new
  result back under the same key (D-18).
- FileNotFoundError → 200 with error fragment carrying
  ``"Content page no longer exists"``.
- Empty ``settings.llms`` → 200 with error fragment carrying the explicit
  reason ``"LLM not configured — set one in Settings"`` (8th vocabulary entry).
- Path traversal (``..%2F..%2Fetc%2Fpasswd``, ``%2Fetc%2Fpasswd``,
  ``foo%00bar``) → status_code in (404, 422), no LLM call.
- Backend name + model thread through to the success metadata footer.

Fixture pattern mirrors ``tests/v2/test_content_routes.py::isolated_content``
(monkeypatches CONTENT_DIR + summary_service._build_client + app.state.settings).
"""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import AuthenticationError

from app.core.config import AppConfig, LLMConfig, Settings


_PID = "Samsung_S22Ultra_SM8450"
_FAKE_CATALOG = [
    "Samsung_S22Ultra_SM8450",
    "Pixel8_GoogleTensor_GS301",
    "Xiaomi13_Pro_SM8550",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_client(mocker, text: str = "• point 1\n• point 2"):
    fake_resp = mocker.MagicMock()
    fake_resp.choices = [
        mocker.MagicMock(message=mocker.MagicMock(content=text))
    ]
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = fake_resp
    return mock_client


def _httpx_response_mock(mocker, status: int):
    resp = mocker.MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.headers = {}
    return resp


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def isolated_summary(tmp_path, monkeypatch, mocker):
    """Redirect platforms.CONTENT_DIR + summary_service._build_client + settings.

    Yields ``(client, content_dir, mock_client)``.
    Tests pre-populate content via ``(cd / f"{pid}.md").write_text(...)``.
    The ``mock_client.chat.completions.create.return_value`` is the default
    fake response; tests can override ``side_effect`` to raise exceptions.
    """
    cd = tmp_path / "content" / "platforms"
    cd.mkdir(parents=True)

    import app_v2.routers.platforms as platforms_mod
    import app_v2.routers.overview as overview_mod
    import app_v2.services.overview_store as overview_store_mod
    from app_v2.services import summary_service

    monkeypatch.setattr(platforms_mod, "CONTENT_DIR", cd)
    monkeypatch.setattr(overview_mod, "CONTENT_DIR", cd)
    monkeypatch.setattr(overview_store_mod, "OVERVIEW_YAML", tmp_path / "overview.yaml")
    monkeypatch.setattr(
        overview_mod,
        "list_platforms",
        lambda db, db_name="": list(_FAKE_CATALOG),
    )

    # Patch the LLM client builder — no real OpenAI() instantiation.
    mock_client = _make_mock_client(mocker)
    mocker.patch.object(summary_service, "_build_client", return_value=mock_client)

    # Clear caches between tests.
    from app_v2.services.cache import clear_all_caches
    clear_all_caches()
    summary_service.clear_summary_cache()

    from app_v2.main import app
    with TestClient(app) as client:
        # Override settings AFTER lifespan ran (lifespan may load real config).
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


# ---------------------------------------------------------------------------
# Happy path — success fragment
# ---------------------------------------------------------------------------

def test_post_summary_returns_success_fragment_with_text(isolated_summary):
    """LLM succeeds → 200, summary text rendered, Regenerate button present."""
    client, cd, mock_client = isolated_summary
    (cd / f"{_PID}.md").write_text("# Notes\n\n- Quirk A", encoding="utf-8")
    r = client.post(f"/platforms/{_PID}/summary")
    assert r.status_code == 200
    body = r.text
    assert "point 1" in body
    assert 'class="ai-btn regen"' in body
    assert "Regenerate" in body
    assert 'class="mono"' in body  # metadata footer span
    # Metadata thread-through.
    assert "ollama-default" in body
    assert "llama3.1" in body


def test_post_summary_renders_markdown_in_summary(isolated_summary):
    """Summary text passed through render_markdown — bullets become <ul>/<li>."""
    client, cd, mock_client = isolated_summary
    fake_resp = mock_client.chat.completions.create.return_value
    fake_resp.choices[0].message.content = "- bullet A\n- bullet B"
    (cd / f"{_PID}.md").write_text("notes", encoding="utf-8")
    r = client.post(f"/platforms/{_PID}/summary")
    assert r.status_code == 200
    # Markdown bullets render to a <ul> inside .markdown-content.
    assert "<li>bullet A</li>" in r.text


# ---------------------------------------------------------------------------
# Cache + Regenerate (D-18)
# ---------------------------------------------------------------------------

def test_post_summary_returns_cached_on_second_call(isolated_summary):
    """Same (pid, mtime, llm) → second call hits cache (LLM count stays 1)."""
    client, cd, mock_client = isolated_summary
    (cd / f"{_PID}.md").write_text("notes", encoding="utf-8")
    r1 = client.post(f"/platforms/{_PID}/summary")
    r2 = client.post(f"/platforms/{_PID}/summary")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert "point 1" in r2.text
    assert mock_client.chat.completions.create.call_count == 1


def test_post_summary_regenerate_header_bypasses_cache(isolated_summary):
    """X-Regenerate: true → bypass lookup; subsequent normal call hits cache."""
    client, cd, mock_client = isolated_summary
    (cd / f"{_PID}.md").write_text("notes", encoding="utf-8")
    # First call: cache miss, LLM call 1.
    r1 = client.post(f"/platforms/{_PID}/summary")
    assert r1.status_code == 200
    assert mock_client.chat.completions.create.call_count == 1

    # Second call with X-Regenerate header: bypass cache, LLM call 2.
    r2 = client.post(
        f"/platforms/{_PID}/summary",
        headers={"X-Regenerate": "true"},
    )
    assert r2.status_code == 200
    assert mock_client.chat.completions.create.call_count == 2

    # Third call without header: should HIT the regenerated entry (no LLM).
    r3 = client.post(f"/platforms/{_PID}/summary")
    assert r3.status_code == 200
    assert mock_client.chat.completions.create.call_count == 2


# ---------------------------------------------------------------------------
# Error fragments — ALL status 200 (UI-SPEC mandate)
# ---------------------------------------------------------------------------

def test_post_summary_returns_error_fragment_on_connect_error(isolated_summary):
    """httpx.ConnectError → 200 with amber warning + 'Cannot reach the LLM backend'."""
    client, cd, mock_client = isolated_summary
    (cd / f"{_PID}.md").write_text("notes", encoding="utf-8")
    mock_client.chat.completions.create.side_effect = httpx.ConnectError("boom")
    r = client.post(f"/platforms/{_PID}/summary")
    assert r.status_code == 200, "route must NEVER return 5xx (UI-SPEC mandate)"
    body = r.text
    assert 'class="alert alert-warning' in body
    assert "Cannot reach the LLM backend" in body
    assert "Retry" in body


def test_post_summary_returns_error_fragment_on_timeout(isolated_summary):
    """httpx.ReadTimeout → 200 with 'LLM took too long to respond'."""
    client, cd, mock_client = isolated_summary
    (cd / f"{_PID}.md").write_text("notes", encoding="utf-8")
    mock_client.chat.completions.create.side_effect = httpx.ReadTimeout("slow")
    r = client.post(f"/platforms/{_PID}/summary")
    assert r.status_code == 200
    assert "LLM took too long to respond" in r.text


def test_post_summary_returns_error_fragment_on_auth_error(isolated_summary, mocker):
    """openai.AuthenticationError → 200 with 'LLM authentication failed'."""
    client, cd, mock_client = isolated_summary
    (cd / f"{_PID}.md").write_text("notes", encoding="utf-8")
    mock_client.chat.completions.create.side_effect = AuthenticationError(
        message="bad key",
        response=_httpx_response_mock(mocker, 401),
        body=None,
    )
    r = client.post(f"/platforms/{_PID}/summary")
    assert r.status_code == 200
    assert "LLM authentication failed" in r.text


def test_post_summary_returns_404_or_error_when_no_content(isolated_summary):
    """No content file → 200 with 'Content page no longer exists' (UI-SPEC §8c).

    Per UI-SPEC: the summary route NEVER returns 5xx. FileNotFoundError flows
    through ``_classify_error`` to the fixed string. The user sees the amber
    alert with Retry; no JSON 404 escapes to the HTMX swap target.
    """
    client, cd, mock_client = isolated_summary
    # Do NOT create the content file.
    r = client.post(f"/platforms/{_PID}/summary")
    assert r.status_code == 200
    body = r.text
    assert "Content page no longer exists" in body
    assert 'class="alert alert-warning' in body
    # No LLM call wasted.
    assert mock_client.chat.completions.create.call_count == 0


def test_post_summary_returns_error_when_no_llm_configured(isolated_summary):
    """settings.llms = [] → 200 with 'LLM not configured' fragment."""
    client, cd, mock_client = isolated_summary
    (cd / f"{_PID}.md").write_text("notes", encoding="utf-8")
    # Override settings with empty llms list.
    from app.core.config import AppConfig, Settings
    from app_v2.main import app
    app.state.settings = Settings(
        databases=[],
        llms=[],
        app=AppConfig(default_llm=""),
    )
    r = client.post(f"/platforms/{_PID}/summary")
    assert r.status_code == 200
    body = r.text
    assert "LLM not configured" in body
    assert 'class="alert alert-warning' in body
    # No LLM call wasted.
    assert mock_client.chat.completions.create.call_count == 0


# ---------------------------------------------------------------------------
# Path-traversal hardening
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad_pid",
    [
        "..%2F..%2Fetc%2Fpasswd",
        "%2Fetc%2Fpasswd",
        "foo%00bar",
    ],
)
def test_post_summary_path_traversal_rejected(isolated_summary, bad_pid):
    """All 3 attack strings → 404 or 422 BEFORE any LLM call."""
    client, cd, mock_client = isolated_summary
    r = client.post(f"/platforms/{bad_pid}/summary")
    assert r.status_code in (404, 422), (
        f"path traversal must be rejected at HTTP entry; got {r.status_code}"
    )
    # No LLM call should have been made.
    assert mock_client.chat.completions.create.call_count == 0
    # No content file leaked into the directory.
    assert list(cd.iterdir()) == []


# ---------------------------------------------------------------------------
# Backend resolution — metadata footer reflects active backend
# ---------------------------------------------------------------------------

def test_post_summary_uses_active_backend_name_in_metadata(isolated_summary):
    """Active LLMConfig.name + .model render in the metadata footer."""
    client, cd, mock_client = isolated_summary
    (cd / f"{_PID}.md").write_text("notes", encoding="utf-8")
    # Switch to a different LLM in settings.
    from app.core.config import AppConfig, LLMConfig, Settings
    from app_v2.main import app
    app.state.settings = Settings(
        databases=[],
        llms=[
            LLMConfig(
                name="my-openai",
                type="openai",
                model="gpt-4o-mini",
                api_key="sk-test",
            )
        ],
        app=AppConfig(default_llm="my-openai"),
    )
    r = client.post(f"/platforms/{_PID}/summary")
    assert r.status_code == 200
    body = r.text
    assert "my-openai" in body
    assert "gpt-4o-mini" in body


# ---------------------------------------------------------------------------
# Generic-partial parameterization (Phase 01 Plan 01 — entity_id + summary_url)
#
# These assert the regression-safe rebinding from `platform_id` to the generic
# `entity_id` + `summary_url` variables. Plans 04+05 will reuse the same
# partials with `entity_id=confluence_page_id` and
# `summary_url=/joint_validation/{cid}/summary`. The platform route MUST
# still render the same on-the-wire output.
# ---------------------------------------------------------------------------

def test_post_summary_success_renders_summary_url_in_hx_post(isolated_summary):
    """Regenerate button hx-post points at /platforms/{pid}/summary via summary_url."""
    client, cd, mock_client = isolated_summary
    (cd / f"{_PID}.md").write_text("notes", encoding="utf-8")
    r = client.post(f"/platforms/{_PID}/summary")
    assert r.status_code == 200
    assert f'hx-post="/platforms/{_PID}/summary"' in r.text


def test_post_summary_success_renders_entity_id_in_hx_indicator(isolated_summary):
    """Spinner hx-indicator references summary-{entity_id}-spinner."""
    client, cd, mock_client = isolated_summary
    (cd / f"{_PID}.md").write_text("notes", encoding="utf-8")
    r = client.post(f"/platforms/{_PID}/summary")
    assert r.status_code == 200
    # Phase 3 contract: hx-indicator id derived from entity_id (was platform_id).
    assert f'hx-indicator="#summary-{_PID}-spinner"' in r.text


def test_post_summary_error_retry_uses_summary_url(isolated_summary):
    """Retry button on error fragment hx-posts to /platforms/{pid}/summary."""
    client, cd, mock_client = isolated_summary
    # No content file → triggers FileNotFoundError → error fragment.
    r = client.post(f"/platforms/{_PID}/summary")
    assert r.status_code == 200
    assert "Retry" in r.text
    assert f'hx-post="/platforms/{_PID}/summary"' in r.text
    assert f'hx-indicator="#summary-{_PID}-spinner"' in r.text


# ---------------------------------------------------------------------------
# Always-200 invariant — meta-test
# ---------------------------------------------------------------------------

def test_post_summary_never_returns_5xx_on_any_exception(isolated_summary):
    """ANY exception from the LLM call → 200 with the error fragment, never 5xx.

    Tests an unclassified ValueError to exercise the 'fallback' branch of
    _classify_error → 'Unexpected error — see server logs'.
    """
    client, cd, mock_client = isolated_summary
    (cd / f"{_PID}.md").write_text("notes", encoding="utf-8")
    mock_client.chat.completions.create.side_effect = ValueError("???")
    r = client.post(f"/platforms/{_PID}/summary")
    assert r.status_code == 200, (
        f"unclassified exception leaked as {r.status_code} — UI-SPEC mandate violated"
    )
    assert "Unexpected error" in r.text
