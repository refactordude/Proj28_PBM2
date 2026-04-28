"""Route-level tests for app_v2/routers/settings.py (Phase 6, ASK-V2-05).

Verifies D-14 cookie attributes, D-15 silent fallback for invalid input,
and D-16 + Pitfall 4 response shape (204 + HX-Refresh: "true" lowercase
string).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


def _stub_settings():
    return SimpleNamespace(
        app=SimpleNamespace(default_llm="ollama-local"),
        llms=[
            SimpleNamespace(name="ollama-local", type="ollama"),
            SimpleNamespace(name="openai-prod", type="openai"),
        ],
    )


@pytest.fixture()
def settings_client():
    from app_v2.main import app
    with TestClient(app) as client:
        app.state.settings = _stub_settings()
        yield client


def test_post_settings_llm_valid_name_sets_cookie(settings_client):
    """ASK-V2-05 / D-14 / D-16: valid name -> 204 + cookie set + HX-Refresh."""
    resp = settings_client.post("/settings/llm", data={"name": "openai-prod"})
    assert resp.status_code == 204
    assert resp.headers.get("HX-Refresh") == "true"  # MUST be lowercase string (Pitfall 4)
    cookie_str = resp.headers.get("set-cookie", "")
    assert "pbm2_llm=openai-prod" in cookie_str


def test_post_settings_llm_cookie_attributes(settings_client):
    """D-14: Path=/, SameSite=Lax, Max-Age=31536000, HttpOnly, NO Secure."""
    resp = settings_client.post("/settings/llm", data={"name": "openai-prod"})
    cookie_str = resp.headers.get("set-cookie", "").lower()
    assert "path=/" in cookie_str
    assert "samesite=lax" in cookie_str
    assert "max-age=31536000" in cookie_str
    assert "httponly" in cookie_str
    # Pitfall 8 — Secure attr MUST NOT be present (intranet HTTP)
    # Strip "samesite=lax" to avoid matching "sec" inside a word in other tests
    stripped = cookie_str.replace("samesite=lax", "")
    assert "secure" not in stripped


def test_post_settings_llm_invalid_name_falls_back_to_default(settings_client):
    """D-15: invalid name -> silent fallback to settings.app.default_llm; still 204 + HX-Refresh."""
    resp = settings_client.post("/settings/llm", data={"name": "evil-tampered"})
    assert resp.status_code == 204
    assert resp.headers.get("HX-Refresh") == "true"
    cookie_str = resp.headers.get("set-cookie", "")
    assert "pbm2_llm=ollama-local" in cookie_str  # default, not "evil-tampered"


def test_post_settings_llm_empty_name_falls_back_to_default(settings_client):
    """Empty name -> falls back to default."""
    resp = settings_client.post("/settings/llm", data={"name": ""})
    assert resp.status_code == 204
    cookie_str = resp.headers.get("set-cookie", "")
    assert "pbm2_llm=ollama-local" in cookie_str


def test_post_settings_llm_route_is_sync_def(settings_client):
    """INFRA-05 / Pitfall 1: settings.set_llm must be `def`, not `async def`."""
    import inspect
    from app_v2.routers.settings import set_llm
    assert not inspect.iscoroutinefunction(set_llm), "set_llm must be sync def per INFRA-05"
