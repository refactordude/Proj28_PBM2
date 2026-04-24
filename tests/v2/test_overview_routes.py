"""Tests for Overview tab routes — GET /, POST /overview/add, DELETE /overview/{platform_id}.

Uses FastAPI TestClient + monkeypatching to isolate:
- overview_store YAML file (redirected to tmp_path)
- list_platforms (patched to return a fixed catalog)

Covers OVERVIEW-01, OVERVIEW-02, OVERVIEW-03, OVERVIEW-04, OVERVIEW-06.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app_v2.main import app
import app_v2.services.overview_store as overview_store_mod

# Fixed fake catalog matching the three platforms used across tests.
_FAKE_CATALOG = [
    "Samsung_S22Ultra_SM8450",
    "Pixel8_GoogleTensor_GS301",
    "Xiaomi13_SM8550",
]


@pytest.fixture()
def isolated_overview(tmp_path, monkeypatch):
    """Fixture: redirect OVERVIEW_YAML to a temp file + patch list_platforms.

    Yields a TestClient(app) with both patches active.
    """
    # 1. Point overview_store at a temp path (no pre-existing file → empty list)
    monkeypatch.setattr(overview_store_mod, "OVERVIEW_YAML", tmp_path / "overview.yaml")

    # 2. Patch list_platforms at the point where overview.py imports it
    import app_v2.routers.overview as overview_mod

    monkeypatch.setattr(overview_mod, "list_platforms", lambda db, db_name="": list(_FAKE_CATALOG))

    # 3. Clear caches between test runs so stale state doesn't bleed
    from app_v2.services.cache import clear_all_caches
    clear_all_caches()

    with TestClient(app) as client:
        yield client


# ---------------------------------------------------------------------------
# GET / — Overview tab
# ---------------------------------------------------------------------------

def test_get_root_returns_200_with_overview_content(isolated_overview):
    """GET / returns 200 HTML with the empty-state copy when curated list is empty."""
    r = isolated_overview.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "No platforms in your overview yet" in r.text


def test_get_root_tab_overview_query_returns_same_page(isolated_overview):
    """GET /?tab=overview returns 200 with the typeahead form (OVERVIEW-01)."""
    r = isolated_overview.get("/?tab=overview")
    assert r.status_code == 200
    assert 'id="platform-input"' in r.text


def test_get_root_datalist_contains_fake_catalog_platforms(isolated_overview):
    """Datalist is populated from list_platforms catalog."""
    r = isolated_overview.get("/")
    body = r.text
    for pid in _FAKE_CATALOG:
        assert pid in body, f"Expected {pid} in datalist"


def test_get_root_nav_overview_has_active_class(isolated_overview):
    """The Overview nav-link has the 'active' CSS class."""
    r = isolated_overview.get("/")
    body = r.text
    nav_start = body.find("nav nav-tabs")
    assert nav_start >= 0, "nav nav-tabs section not found"
    nav_section = body[nav_start: nav_start + 1000]
    overview_idx = nav_section.find("Overview")
    assert overview_idx >= 0
    window = nav_section[max(0, overview_idx - 200): overview_idx]
    assert "active" in window, f"Expected 'active' near Overview link; window: {window!r}"


def test_get_root_contains_filter_block(isolated_overview):
    """Overview page contains the collapsible filter block."""
    r = isolated_overview.get("/")
    assert 'id="filter-details"' in r.text
    assert 'id="filter-form"' in r.text


def test_get_root_page_title(isolated_overview):
    """Page title matches the copywriting contract."""
    r = isolated_overview.get("/")
    assert "PBM2 — Overview" in r.text


# ---------------------------------------------------------------------------
# POST /overview/add — happy path
# ---------------------------------------------------------------------------

def test_post_add_happy_path_returns_200_with_entity_row_fragment(isolated_overview):
    """POST /overview/add with a valid catalog PID returns 200 with an entity row fragment."""
    r = isolated_overview.post(
        "/overview/add",
        data={"platform_id": "Samsung_S22Ultra_SM8450"},
    )
    assert r.status_code == 200
    body = r.text
    assert "Samsung_S22Ultra_SM8450" in body
    assert "list-group-item" in body
    # Brand badge
    assert "Samsung" in body
    # SoC badge
    assert "SM8450" in body
    # Year badge — SM8450 resolves to 2022 via SOC_YEAR
    assert "2022" in body


def test_post_add_pixel_returns_year_badge(isolated_overview):
    """Pixel8 row has its year resolved via GS301 → 2022 in SOC_YEAR."""
    r = isolated_overview.post(
        "/overview/add",
        data={"platform_id": "Pixel8_GoogleTensor_GS301"},
    )
    assert r.status_code == 200
    body = r.text
    assert "Pixel8" in body
    assert "GS301" in body
    assert "2022" in body


# ---------------------------------------------------------------------------
# POST /overview/add — duplicate handling (409)
# ---------------------------------------------------------------------------

def test_post_add_duplicate_returns_409_with_warning_alert(isolated_overview):
    """Adding the same PID twice returns 409 with 'Already in your overview'."""
    isolated_overview.post("/overview/add", data={"platform_id": "Samsung_S22Ultra_SM8450"})
    r = isolated_overview.post("/overview/add", data={"platform_id": "Samsung_S22Ultra_SM8450"})
    assert r.status_code == 409
    body = r.text
    assert "Already in your overview: Samsung_S22Ultra_SM8450" in body
    assert "alert-warning" in body
    assert "alert-dismissible" in body


# ---------------------------------------------------------------------------
# POST /overview/add — unknown platform (404)
# ---------------------------------------------------------------------------

def test_post_add_unknown_platform_returns_404_with_danger_alert(isolated_overview):
    """POST with a valid-regex but catalog-unknown PID returns 404 + danger alert."""
    r = isolated_overview.post(
        "/overview/add",
        data={"platform_id": "NotInCatalog_Unknown_XY1234"},
    )
    assert r.status_code == 404
    body = r.text
    assert "Unknown platform: NotInCatalog_Unknown_XY1234. Choose from the dropdown." in body
    assert "alert-danger" in body
    assert "alert-dismissible" in body


# ---------------------------------------------------------------------------
# POST /overview/add — invalid inputs (422)
# ---------------------------------------------------------------------------

def test_post_add_invalid_regex_returns_422(isolated_overview):
    """Path traversal string is rejected at Form validation — returns 422."""
    r = isolated_overview.post(
        "/overview/add",
        data={"platform_id": "../../etc/passwd"},
    )
    assert r.status_code == 422


def test_post_add_symbols_returns_422(isolated_overview):
    """Platform ID with forbidden symbols is rejected — returns 422."""
    r = isolated_overview.post(
        "/overview/add",
        data={"platform_id": "Too!Many$Symbols"},
    )
    assert r.status_code == 422


def test_post_add_missing_field_returns_422(isolated_overview):
    """POST without platform_id field returns 422."""
    r = isolated_overview.post("/overview/add", data={})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /overview/{platform_id} — happy path
# ---------------------------------------------------------------------------

def test_delete_existing_returns_200_empty_body(isolated_overview):
    """DELETE on an existing pid returns 200 with empty body; entity is removed."""
    # Add first
    isolated_overview.post("/overview/add", data={"platform_id": "Samsung_S22Ultra_SM8450"})
    # Delete
    r = isolated_overview.delete("/overview/Samsung_S22Ultra_SM8450")
    assert r.status_code == 200
    assert r.text == ""
    # Confirm removal: GET / should show empty state again
    r2 = isolated_overview.get("/")
    assert "No platforms in your overview yet" in r2.text


# ---------------------------------------------------------------------------
# DELETE /overview/{platform_id} — not found (404)
# ---------------------------------------------------------------------------

def test_delete_nonexistent_returns_404(isolated_overview):
    """DELETE on a pid that was never added returns 404."""
    r = isolated_overview.delete("/overview/Pixel8_GoogleTensor_GS301")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /overview/{platform_id} — regex validation (422)
# ---------------------------------------------------------------------------

def test_delete_invalid_regex_returns_422(isolated_overview):
    """DELETE with a path-traversal id is rejected — 422 or 404 (not 200)."""
    # URL-encoded path traversal
    r = isolated_overview.delete("/overview/..%2F..%2Fetc%2Fpasswd")
    assert r.status_code in (404, 422), f"Expected 4xx, got {r.status_code}"


# ---------------------------------------------------------------------------
# Full page after multiple adds — entity rows + badges correct
# ---------------------------------------------------------------------------

def test_get_root_after_add_shows_entity_row_with_correct_badges(isolated_overview):
    """Full-page render after two adds; both PIDs visible with correct badges."""
    isolated_overview.post("/overview/add", data={"platform_id": "Samsung_S22Ultra_SM8450"})
    isolated_overview.post("/overview/add", data={"platform_id": "Xiaomi13_SM8550"})
    r = isolated_overview.get("/")
    body = r.text
    assert "Samsung_S22Ultra_SM8450" in body
    assert "Xiaomi13_SM8550" in body
    assert "Samsung" in body
    assert "Xiaomi" in body
    assert "SM8450" in body
    assert "SM8550" in body
    # Both years
    assert "2022" in body  # SM8450
    assert "2023" in body  # SM8550


def test_get_root_ai_summary_button_disabled(isolated_overview):
    """AI Summary button is rendered but disabled with the Phase 3 tooltip."""
    isolated_overview.post("/overview/add", data={"platform_id": "Samsung_S22Ultra_SM8450"})
    r = isolated_overview.get("/")
    assert "AI Summary" in r.text
    assert "Content page must exist first (Phase 3)" in r.text
    assert "disabled" in r.text
