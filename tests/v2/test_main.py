"""Smoke tests for app_v2/main.py — INFRA-01, INFRA-02, INFRA-04, INFRA-05.

These tests use FastAPI's synchronous TestClient (which is based on httpx). They
do NOT require a running uvicorn server — TestClient drives the app in-process.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app_v2.main import app


@pytest.fixture(scope="module")
def client():
    """Module-scoped TestClient — lifespan runs once per module (startup + teardown)."""
    with TestClient(app) as c:
        yield c


# --- GET / (Overview tab, default landing) ------------------------------

def test_get_root_returns_200_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")


def test_get_root_contains_bootstrap_nav_tabs(client):
    r = client.get("/")
    # Bootstrap 5 nav-tabs markup
    assert "nav nav-tabs" in r.text


def test_get_root_contains_three_tab_labels(client):
    r = client.get("/")
    assert "Overview" in r.text
    assert "Browse" in r.text
    assert "Ask" in r.text


def test_get_root_marks_overview_active(client):
    r = client.get("/")
    body = r.text
    # The active class is applied to the Overview nav-link specifically.
    # Strategy: find the nav nav-tabs section, then locate the Overview anchor within
    # it, then check that "active" appears between the <a and the "Overview" text.
    # This avoids the false match on "Overview" in the <title> tag.
    nav_start = body.find("nav nav-tabs")
    assert nav_start >= 0, "nav nav-tabs not found in body"
    nav_section = body[nav_start:nav_start + 1000]
    overview_idx = nav_section.find("Overview")
    assert overview_idx >= 0, "Overview not found in nav section"
    # Look backwards from Overview for the active class in the enclosing <a>
    window_start = max(0, overview_idx - 200)
    window = nav_section[window_start:overview_idx]
    assert "active" in window, f"Expected 'active' class near Overview nav-link; window: {window!r}"


def test_get_root_references_vendored_bootstrap_css(client):
    r = client.get("/")
    assert "/static/vendor/bootstrap/bootstrap.min.css" in r.text


def test_get_root_references_vendored_htmx(client):
    r = client.get("/")
    assert "/static/vendor/htmx/htmx.min.js" in r.text


def test_get_root_references_htmx_error_handler_js(client):
    r = client.get("/")
    assert "/static/js/htmx-error-handler.js" in r.text


def test_get_root_contains_htmx_error_container(client):
    r = client.get("/")
    assert 'id="htmx-error-container"' in r.text


def test_get_root_no_cdn_references(client):
    """INFRA-04: base.html must not reference cdn.jsdelivr or unpkg."""
    r = client.get("/")
    assert "cdn.jsdelivr" not in r.text
    assert "unpkg.com" not in r.text


# --- GET /browse, GET /ask (Phase 4/5 placeholders) ---------------------

def test_get_browse_returns_200_with_phase_placeholder(client):
    r = client.get("/browse")
    assert r.status_code == 200
    assert "Coming in Phase 4" in r.text
    assert "alert" in r.text  # Bootstrap alert class


def test_get_ask_returns_200_with_phase_placeholder(client):
    r = client.get("/ask")
    assert r.status_code == 200
    assert "Coming in Phase 5" in r.text
    assert "alert" in r.text


# --- 404 handler (INFRA-02) ----------------------------------------------

def test_get_nonexistent_route_returns_bootstrap_404(client):
    r = client.get("/this-does-not-exist")
    assert r.status_code == 404
    body = r.text
    assert "404" in body
    # Custom 404.html inherits base.html, so nav-tabs must be present.
    # If nav-tabs is missing, FastAPI's default JSON handler was returned instead.
    assert "nav nav-tabs" in body, "Expected custom 404.html with nav-tabs, got default handler"


# --- Static mount (INFRA-04) --------------------------------------------

def test_static_vendor_serves_bootstrap_css(client):
    """Static mount works — vendored assets are reachable."""
    r = client.get("/static/vendor/bootstrap/bootstrap.min.css")
    assert r.status_code == 200
    # Bootstrap CSS starts with a comment block
    assert r.text.lstrip().startswith(("/*", "@media", ".")) or len(r.text) > 1000


def test_static_vendor_serves_htmx_js(client):
    r = client.get("/static/vendor/htmx/htmx.min.js")
    assert r.status_code == 200
    # HTMX minified JS is a single-line IIFE typically starting with var/function/!
    assert len(r.text) > 5000


def test_static_js_serves_htmx_error_handler(client):
    r = client.get("/static/js/htmx-error-handler.js")
    assert r.status_code == 200
    assert "htmx:beforeSwap" in r.text


# --- Lifespan state initialization (INFRA-03) ---------------------------

def test_lifespan_initializes_app_state(client):
    """TestClient context-manager runs lifespan startup+shutdown around the test body."""
    # app.state is populated by lifespan startup. TestClient's context manager
    # runs startup on enter; by the time this test runs, state is ready.
    assert hasattr(app.state, "settings")
    assert hasattr(app.state, "agent_registry")
    assert isinstance(app.state.agent_registry, dict)
    # app.state.db may be None if no databases are configured — acceptable in Phase 1
    assert hasattr(app.state, "db")
