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
    # Phase 04 D-UIF-06: legacy <nav class="navbar"> + nav-tabs replaced
    # by the Helix .topbar primitive. The test name kept for git blame
    # continuity; the contract is "shell renders the top nav".
    assert 'class="topbar"' in r.text
    assert 'class="brand"' in r.text
    assert 'class="brand-mark">AE<' in r.text
    assert 'class="tabs"' in r.text


def test_get_root_contains_three_tab_labels(client):
    r = client.get("/")
    # Phase 1 Plan 05 (D-JV-01): top-nav label "Overview" was renamed to
    # "Joint Validation"; URL "/" stayed the same.
    # Quick 260507-mmv: topbar Browse/Ask tab labels were rebranded to the
    # Korean strings "Platform 브라우저" and "AI 질문하기" (single source of
    # truth in app_v2/templates/_components/topbar.html lines 25, 29).
    # Quick 260508-01a updated the Browse/Ask page headings to match these
    # tab labels verbatim, and this test follows in lockstep.
    assert "Joint Validation" in r.text
    assert "Platform 브라우저" in r.text
    assert "AI 질문하기" in r.text


def test_get_root_marks_overview_active(client):
    r = client.get("/")
    body = r.text
    # Phase 04 D-UIF-06: active-tab signal switched from `active` class
    # (Bootstrap nav-link convention) to `aria-selected="true"` on the
    # matching .tab anchor (Helix convention).
    topbar_start = body.find('class="topbar"')
    assert topbar_start >= 0, "topbar not found in body"
    topbar_section = body[topbar_start:topbar_start + 2000]
    label_idx = topbar_section.find("Joint Validation")
    assert label_idx >= 0, "'Joint Validation' not found in topbar"
    # Look backwards from the label for aria-selected="true" in the
    # enclosing <a> tag.
    window_start = max(0, label_idx - 300)
    window = topbar_section[window_start:label_idx]
    assert 'aria-selected="true"' in window, (
        f'Expected aria-selected="true" near Joint Validation tab; window: {window!r}'
    )


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

@pytest.mark.skip(
    reason="Phase 1 stub replaced by Phase 4 router. /browse now owned by "
    "app_v2/routers/browse.py; full-page render requires browse/index.html "
    "which ships in Plan 04-03. Plan 04-04 will add proper integration tests."
)
def test_get_browse_returns_200_with_phase_placeholder(client):
    r = client.get("/browse")
    assert r.status_code == 200
    assert "Coming in Phase 4" in r.text
    assert "alert" in r.text  # Bootstrap alert class


@pytest.mark.skip(
    reason="Phase 1 stub replaced by Phase 6 router. /ask now owned by "
    "app_v2/routers/ask.py; full-page render requires ask/index.html "
    "which ships in Plan 06-04. Plan 06-05 will add proper integration tests."
)
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
    # Phase 04 D-UIF-06: custom 404.html inherits base.html, so the
    # topbar must be present. If topbar is missing, FastAPI's default
    # JSON handler was returned instead.
    assert 'class="topbar"' in body, (
        'Expected custom 404.html with topbar, got default handler'
    )


def test_htmx_request_404_returns_fragment_not_full_page(client):
    """INFRA-02 (260429-qyv hotfix 3): when an HTMX request 404s, the
    response must be a FRAGMENT — no `<html>`, no shell topbar, no second
    `#htmx-error-container`. Otherwise htmx-error-handler.js swaps the
    entire base.html shell into `#htmx-error-container`, producing a
    duplicate topbar beneath the real one."""
    r = client.get("/this-does-not-exist", headers={"HX-Request": "true"})
    assert r.status_code == 404
    body = r.text
    # The alert content IS present.
    assert "404" in body
    assert "Page not found" in body
    # The shell is NOT — no second topbar, no nested error container.
    assert "<html" not in body.lower(), (
        "HTMX 404 must be a fragment, not a full HTML document"
    )
    assert 'class="topbar"' not in body, (
        "HTMX 404 fragment must not include the topbar"
    )
    assert 'id="htmx-error-container"' not in body, (
        "HTMX 404 fragment must not contain another #htmx-error-container "
        "(would nest under the real one and confuse subsequent error swaps)"
    )


@pytest.fixture
def crashing_client(monkeypatch):
    """TestClient with `raise_server_exceptions=False` so the registered
    `unhandled_exception_handler` is exercised instead of the test re-raising.
    Patches the JV grid view-model builder used by GET / and GET /overview to
    throw — any HTTP method on `/` then triggers the catch-all 500.

    Phase 1 Plan 04: previously patched `_build_overview_context`, which was
    deleted along with the curated-Platform helpers when GET /overview was
    rewritten to render the Joint Validation listing (D-JV-01). The new
    overview router calls `build_joint_validation_grid_view_model` instead;
    monkey-patching that attribute on the router module re-creates the same
    "any GET /overview triggers the 500 handler" behavior that the two
    fragment / full-page assertions below depend on.
    """
    from app_v2.routers import overview as overview_router

    def _explode(*_args, **_kwargs):
        raise RuntimeError("simulated upstream failure")

    monkeypatch.setattr(
        overview_router, "build_joint_validation_grid_view_model", _explode
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_htmx_request_500_via_unhandled_exception_returns_fragment(crashing_client):
    """INFRA-02 (260429-qyv hotfix 3): when an HTMX request triggers an
    unhandled exception, the catch-all handler must return a FRAGMENT,
    not the full 500.html page. Reproduces the duplicate-topbar bug from
    the Ask page when the LLM backend 500s."""
    r = crashing_client.get("/", headers={"HX-Request": "true"})
    assert r.status_code == 500
    body = r.text
    assert "500" in body
    assert "Internal server error" in body
    # The fragment must NOT contain the base.html shell.
    assert "<html" not in body.lower(), (
        "HTMX 500 must be a fragment, not a full HTML document — "
        "otherwise htmx-error-handler.js injects a second topbar."
    )
    assert 'class="topbar"' not in body
    assert 'id="htmx-error-container"' not in body


def test_browser_request_500_still_returns_full_page(crashing_client):
    """Direct browser navigation (no HX-Request header) must still get the
    full 500.html with the topbar — unchanged from prior behavior."""
    r = crashing_client.get("/")  # no HX-Request header
    assert r.status_code == 500
    body = r.text
    assert "500" in body
    # Full page DOES include the shell so direct navigation gets the topbar.
    assert "<html" in body.lower()
    assert 'class="topbar"' in body
    # The persistent error container is still in the shell for HTMX errors
    # that happen later.
    assert 'id="htmx-error-container"' in body


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


def test_lifespan_creates_content_platforms_directory(tmp_path, monkeypatch):
    """D-27: lifespan must mkdir content/platforms/ on startup.

    Runs the app from a temp working directory so we can assert the mkdir
    landed in `tmp_path/content/platforms/` and not in the real repo.
    """
    monkeypatch.chdir(tmp_path)
    from fastapi.testclient import TestClient as _TC
    from app_v2.main import app as _app

    # Before lifespan runs, the directory should not exist in tmp_path.
    assert not (tmp_path / "content" / "platforms").exists()

    with _TC(_app):
        # TestClient context-enters lifespan — mkdir runs before yield.
        assert (tmp_path / "content" / "platforms").is_dir(), (
            "lifespan must create content/platforms/ on startup (D-27)"
        )
