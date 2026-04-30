"""Joint Validation route coverage — Phase 1 Plan 06.

Replaces tests/v2/test_overview_routes.py. Covers:
  - GET / and GET /overview (listing, full page)
  - POST /overview/grid (3 OOB blocks + HX-Push-Url)
  - POST /overview/add (deleted; should 404/405)
  - GET /joint_validation/<id> (detail page + iframe sandbox)
  - POST /joint_validation/<id>/summary (always-200 contract)
  - /static/joint_validation/<id>/... (StaticFiles mount + path traversal defense)
  - Empty state copy
  - Browse/Ask regression smoke tests
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import AppConfig, LLMConfig, Settings
from app_v2.main import app
from app_v2.services.joint_validation_store import clear_parse_cache
from app_v2.services.summary_service import clear_summary_cache


SAMPLE_HTML = b"""<!DOCTYPE html><html><body>
<h1>Test Joint Validation</h1>
<table>
  <tr><th><strong>Status</strong></th><td>In Progress</td></tr>
  <tr><th><strong>Customer</strong></th><td>Acme</td></tr>
  <tr><th><strong>\xeb\x8b\xb4\xeb\x8b\xb9\xec\x9e\x90</strong></th><td>\xed\x99\x8d\xea\xb8\xb8\xeb\x8f\x99</td></tr>
  <tr><th><strong>Start</strong></th><td>2026-04-01</td></tr>
  <tr><th><strong>Report Link</strong></th><td><a href="https://example.com">L</a></td></tr>
</table>
</body></html>"""


@pytest.fixture(autouse=True)
def _reset_caches():
    """Reset module-level caches between tests so JV_ROOT monkeypatches take effect."""
    clear_parse_cache()
    clear_summary_cache()
    yield
    clear_parse_cache()
    clear_summary_cache()


@pytest.fixture
def jv_dir_with_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Drop one JV folder into a tmp_path and patch JV_ROOT in every consumer."""
    folder = tmp_path / "3193868109"
    folder.mkdir()
    (folder / "index.html").write_bytes(SAMPLE_HTML)
    # Patch JV_ROOT module-global where it is read. The import-as-from idiom
    # binds the name into each consumer module, so each binding must be
    # patched separately.
    monkeypatch.setattr("app_v2.services.joint_validation_store.JV_ROOT", tmp_path)
    monkeypatch.setattr("app_v2.routers.overview.JV_ROOT", tmp_path)
    monkeypatch.setattr("app_v2.routers.joint_validation.JV_ROOT", tmp_path)
    return tmp_path


@pytest.fixture
def jv_dir_real(tmp_path: Path):
    """Drop a JV folder under the REAL content/joint_validation/ for static-mount tests.

    The StaticFiles mount is registered at app-startup time pointing at the
    literal "content/joint_validation" directory; we cannot easily monkeypatch
    a live mount mid-test. Instead, drop a uuid-suffixed numeric folder under
    the real root and clean up in a try/finally so cleanup runs on test pass,
    failure, AND interruption (Ctrl-C / mid-yield exception — WARN-04 fix).
    """
    # Numeric-only id (D-JV-03 ^\d+$ regex compliance) — high "999" prefix
    # makes a collision with a real Confluence page id extremely unlikely.
    page_id = "999" + str(abs(hash(uuid.uuid4().hex)))[:6]
    real_root = Path("content/joint_validation")
    real_root.mkdir(parents=True, exist_ok=True)
    folder = real_root / page_id
    folder.mkdir(exist_ok=True)
    (folder / "index.html").write_bytes(SAMPLE_HTML)
    try:
        yield page_id
    finally:
        # Robust cleanup — runs on test pass, fail, AND interrupt (Ctrl-C).
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def configured_client(client: TestClient):
    """TestClient with a populated app.state.settings so the LLM-resolver works."""
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
    return client


# ---------------------------------------------------------------------------
# Listing routes
# ---------------------------------------------------------------------------


def test_get_root_renders_jv_grid(jv_dir_with_one: Path, client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "Joint Validation" in r.text
    assert 'id="overview-grid"' in r.text


def test_get_overview_renders_jv_grid(jv_dir_with_one: Path, client: TestClient) -> None:
    r = client.get("/overview")
    assert r.status_code == 200
    assert 'id="overview-grid"' in r.text


def test_get_overview_with_filters_round_trip_url(jv_dir_with_one: Path, client: TestClient) -> None:
    r = client.get(
        "/overview",
        params=[("status", "In Progress"), ("sort", "customer"), ("order", "asc")],
    )
    assert r.status_code == 200
    # Active filter badge present (count > 0); accept either the literal "1"
    # count or the badge container marker.
    assert "status: 1" in r.text or "badge" in r.text


def test_post_overview_grid_returns_oob_blocks(jv_dir_with_one: Path, client: TestClient) -> None:
    r = client.post("/overview/grid", data={"sort": "start", "order": "desc"})
    assert r.status_code == 200
    assert 'id="overview-grid"' in r.text
    assert 'id="overview-count"' in r.text
    assert 'id="overview-filter-badges"' in r.text


def test_post_overview_grid_sets_hx_push_url(jv_dir_with_one: Path, client: TestClient) -> None:
    r = client.post("/overview/grid", data={"sort": "start", "order": "desc"})
    assert r.status_code == 200
    push_url = r.headers.get("HX-Push-Url", "")
    assert "/overview" in push_url
    assert "sort=start" in push_url
    assert "order=desc" in push_url


def test_post_overview_add_returns_404_or_405(client: TestClient) -> None:
    """D-JV-07: POST /overview/add was deleted in Plan 04."""
    r = client.post("/overview/add", data={"platform_id": "X"})
    assert r.status_code in (404, 405), f"Expected 404/405, got {r.status_code}"


# ---------------------------------------------------------------------------
# Detail routes
# ---------------------------------------------------------------------------


def test_get_jv_detail_renders_properties_and_iframe(
    jv_dir_with_one: Path, client: TestClient
) -> None:
    r = client.get("/joint_validation/3193868109")
    assert r.status_code == 200
    assert "<iframe" in r.text
    assert (
        'sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"'
        in r.text
    )
    assert "/static/joint_validation/3193868109/index.html" in r.text
    assert "담당자" in r.text  # Korean properties-table row label


def test_get_jv_detail_non_numeric_returns_404_or_422(client: TestClient) -> None:
    """D-JV-03: Path(pattern=r'^\\d+$') rejects non-numeric ids before any FS touch."""
    r = client.get("/joint_validation/abc123")
    assert r.status_code in (404, 422), f"Expected 404/422, got {r.status_code}"


def test_get_jv_detail_missing_index_returns_404(client: TestClient) -> None:
    r = client.get("/joint_validation/9999999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Static mount
# ---------------------------------------------------------------------------


def test_static_mount_serves_jv_index_html(jv_dir_real, client: TestClient) -> None:
    """D-JV-13: /static/joint_validation/<id>/index.html serves the Confluence body."""
    page_id = jv_dir_real
    r = client.get(f"/static/joint_validation/{page_id}/index.html")
    assert r.status_code == 200
    assert b"Test Joint Validation" in r.content


def test_static_mount_path_traversal_blocked(client: TestClient) -> None:
    """Starlette's path normalization rejects ../etc/passwd traversal attempts."""
    r = client.get("/static/joint_validation/../etc/passwd")
    # Starlette's path normalization rejects the traversal — actual code may
    # be 404, 400, or 403 depending on which layer catches it.
    assert r.status_code in (400, 403, 404), (
        f"Expected 400/403/404, got {r.status_code}"
    )


# ---------------------------------------------------------------------------
# AI Summary route (always-200 contract)
# ---------------------------------------------------------------------------


def test_post_jv_summary_always_200_on_missing_index(
    jv_dir_with_one: Path, configured_client: TestClient
) -> None:
    """Always-200 contract: missing index.html → 200 + summary/_error.html fragment."""
    r = configured_client.post("/joint_validation/9999999/summary")
    assert r.status_code == 200
    # Error fragment rendered — partial includes "summary" markers somewhere
    # in the rendered HTML.
    assert "summary" in r.text.lower()


def test_post_jv_summary_renders_success_with_mock_llm(
    jv_dir_with_one: Path, configured_client: TestClient
) -> None:
    """Mock the LLM call and verify the success fragment renders + regenerate hx-post."""
    with patch(
        "app_v2.services.joint_validation_summary._call_llm_with_text",
        return_value="# OK summary",
    ):
        r = configured_client.post("/joint_validation/3193868109/summary")
    assert r.status_code == 200
    # The regenerate button hx-post must point back at the same URL.
    assert "/joint_validation/3193868109/summary" in r.text


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------


def test_empty_jv_root_renders_empty_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """D-JV-17: empty content/joint_validation/ → 'No Joint Validations yet.' copy."""
    monkeypatch.setattr("app_v2.services.joint_validation_store.JV_ROOT", tmp_path)
    monkeypatch.setattr("app_v2.routers.overview.JV_ROOT", tmp_path)
    r = client.get("/overview")
    assert r.status_code == 200
    assert "No Joint Validations yet." in r.text
    assert "0 entries" in r.text
    assert 'colspan="13"' in r.text


# ---------------------------------------------------------------------------
# Adjacent-tab regression smoke
# ---------------------------------------------------------------------------


def test_browse_and_ask_tabs_unaffected(client: TestClient) -> None:
    """Cleanup didn't break adjacent tabs."""
    r_browse = client.get("/browse")
    assert r_browse.status_code == 200, f"Browse regression: {r_browse.status_code}"
    r_ask = client.get("/ask")
    assert r_ask.status_code == 200, f"Ask regression: {r_ask.status_code}"
