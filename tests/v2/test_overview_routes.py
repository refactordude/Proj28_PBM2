"""Tests for Overview tab routes — Phase 5 redesign.

Covers OVERVIEW-V2-01..06 + D-OV-04 (forbidden routes gone) + D-OV-11
(HX-Redirect on add success) + D-OV-13 (URL state shape).

Legacy <select>-based filter tests REMOVED (D-OV-14). Service-layer
filter logic tested in tests/v2/test_overview_grid_service.py; this file
exercises the route layer end-to-end (GET /overview, POST /overview/grid,
POST /overview/add) via FastAPI TestClient.

Fixture redirects:
- overview_store YAML to tmp_path
- overview.list_platforms to a fixed catalog
- overview.CONTENT_DIR to tmp_path/content (so frontmatter reads land in
  the test sandbox)

Tests rely on Plan 05-04 (router redesign) + Plan 05-05 (template rewrite)
having both landed.
"""
from __future__ import annotations

import urllib.parse
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app_v2.main import app
import app_v2.services.overview_store as overview_store_mod


# Fixed fake catalog matching the three platforms used across tests.
# All IDs use 3 underscore-separated parts (brand_model_soc) so parse_platform_id
# correctly extracts soc_raw for year lookups (preserved from Phase 2 fixture).
_FAKE_CATALOG = [
    "Samsung_S22Ultra_SM8450",
    "Pixel8_GoogleTensor_GS301",
    "Xiaomi13_Pro_SM8550",
]


def _write_fm(content_dir: Path, pid: str, **kwargs) -> Path:
    """Write a minimal markdown file with YAML frontmatter under content_dir.

    Each kwarg becomes a `key: value` line inside the frontmatter fence.
    A trivial body line follows to satisfy the parser (which only cares
    about the fenced region).
    """
    content_dir.mkdir(parents=True, exist_ok=True)
    target = content_dir / f"{pid}.md"
    lines = ["---"]
    for k, v in kwargs.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append("# body")
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def _post_form_pairs(client: TestClient, url: str, pairs):
    """POST with a manually-encoded form body to support repeated keys.

    httpx 0.28 dropped support for the list-of-tuples shape on `data=`
    (raises TypeError); `content=` + explicit Content-Type is the supported
    escape hatch — same helper as tests/v2/test_browse_routes.py.
    """
    body = urllib.parse.urlencode(list(pairs))
    return client.post(
        url,
        content=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


@pytest.fixture()
def isolated_overview(tmp_path, monkeypatch):
    """Fixture: redirect OVERVIEW_YAML + CONTENT_DIR + list_platforms.

    Yields a TestClient(app) with all patches active and per-test caches
    cleared. The frontmatter cache (Plan 05-02 D-OV-12) is keyed by
    (platform_id, mtime_ns) so test isolation requires explicit clear too.
    """
    # 1. Point overview_store at a temp path (no pre-existing file → empty list)
    monkeypatch.setattr(overview_store_mod, "OVERVIEW_YAML", tmp_path / "overview.yaml")

    # 2. Patch list_platforms at the point where overview.py imports it
    import app_v2.routers.overview as overview_mod
    monkeypatch.setattr(
        overview_mod, "list_platforms", lambda db, db_name="": list(_FAKE_CATALOG)
    )

    # 3. Redirect CONTENT_DIR so frontmatter reads land in the test sandbox
    fake_content_dir = tmp_path / "content"
    fake_content_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(overview_mod, "CONTENT_DIR", fake_content_dir)

    # 4. Clear caches between test runs so stale state does not bleed
    from app_v2.services.cache import clear_all_caches
    from app_v2.services import content_store
    clear_all_caches()
    content_store._FRONTMATTER_CACHE.clear()

    with TestClient(app) as client:
        yield client


# ---------------------------------------------------------------------------
# GET / + GET /overview — basic page rendering (kept from Phase 2)
# ---------------------------------------------------------------------------

def test_get_root_returns_200_with_overview_content(isolated_overview):
    """GET / returns 200 HTML with the new #overview-grid container."""
    r = isolated_overview.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    # New Phase 5 container — replaces the legacy <ul id="overview-list">
    assert 'id="overview-grid"' in r.text


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


def test_get_root_page_title(isolated_overview):
    """Page title includes 'Overview' and 'PBM2' per base.html template pattern."""
    r = isolated_overview.get("/")
    assert "Overview — PBM2 v2.0" in r.text


# ---------------------------------------------------------------------------
# GET /overview — full page rendering (OVERVIEW-V2-01, V2-02, V2-04)
# ---------------------------------------------------------------------------

def test_get_overview_returns_table_with_phase4_classes(isolated_overview, tmp_path):
    """OVERVIEW-V2-01: Overview table uses Phase 4 Browse styling exactly."""
    from app_v2.services.overview_store import add_overview
    add_overview("Samsung_S22Ultra_SM8450")
    _write_fm(
        tmp_path / "content",
        "Samsung_S22Ultra_SM8450",
        title="Project Alpha",
        status="in-progress",
        customer="Acme",
    )

    r = isolated_overview.get("/overview")
    assert r.status_code == 200
    body = r.text
    assert 'class="table table-striped table-hover table-sm overview-table"' in body
    assert 'thead class="sticky-top bg-light"' in body
    # 14-column header order — sample 4 anchor headers
    assert "Title" in body
    assert "Customer" in body
    assert "담당자" in body  # Korean assignee column
    assert "AI Summary" in body
    # Frontmatter title rendered in the row
    assert "Project Alpha" in body


def test_get_overview_with_no_curated_shows_empty_state(isolated_overview):
    """Empty curated list renders the 'add your first one' alert."""
    r = isolated_overview.get("/overview")
    assert r.status_code == 200
    assert "No platforms in your overview yet" in r.text


def test_get_overview_url_roundtrip_pre_checks_filters(isolated_overview, tmp_path):
    """OVERVIEW-V2-04 + V2-06: URL filter state pre-checks picker checkboxes."""
    from app_v2.services.overview_store import add_overview
    add_overview("Samsung_S22Ultra_SM8450")
    add_overview("Pixel8_GoogleTensor_GS301")
    _write_fm(
        tmp_path / "content",
        "Samsung_S22Ultra_SM8450",
        title="P1", status="in-progress", customer="Acme",
    )
    _write_fm(
        tmp_path / "content",
        "Pixel8_GoogleTensor_GS301",
        title="P2", status="done", customer="Beta",
    )

    r = isolated_overview.get(
        "/overview?status=in-progress&customer=Acme&sort=customer&order=asc"
    )
    assert r.status_code == 200
    body = r.text
    # 'in-progress' option is present in the picker (filter_options) and
    # 'Acme' likewise — both come from the curated rows' frontmatter values.
    assert 'value="in-progress"' in body
    assert 'value="Acme"' in body
    # asc sort glyph appears for the customer column when sort=customer&order=asc
    assert "bi-arrow-up-short" in body


def test_get_overview_default_sort_is_start_desc(isolated_overview, tmp_path):
    """D-OV-07: default sort is start descending; desc glyph rendered."""
    from app_v2.services.overview_store import add_overview
    add_overview("Samsung_S22Ultra_SM8450")
    _write_fm(
        tmp_path / "content",
        "Samsung_S22Ultra_SM8450",
        title="P1", start="2026-04-01",
    )
    r = isolated_overview.get("/overview")
    assert r.status_code == 200
    # bi-arrow-down-short for desc sort on the start column
    assert "bi-arrow-down-short" in r.text


# ---------------------------------------------------------------------------
# POST /overview/grid — fragment swap with HX-Push-Url (OVERVIEW-V2-04, V2-06)
# ---------------------------------------------------------------------------

def test_post_overview_grid_returns_fragment_with_hx_push_url(isolated_overview, tmp_path):
    """POST /overview/grid sets HX-Push-Url to canonical /overview?... URL."""
    from app_v2.services.overview_store import add_overview
    add_overview("Samsung_S22Ultra_SM8450")
    _write_fm(
        tmp_path / "content",
        "Samsung_S22Ultra_SM8450",
        title="P1", status="in-progress", start="2026-04-01",
    )

    r = _post_form_pairs(
        isolated_overview,
        "/overview/grid",
        [
            ("status", "in-progress"),
            ("sort", "start"),
            ("order", "desc"),
        ],
    )
    assert r.status_code == 200
    push_url = r.headers.get("HX-Push-Url")
    assert push_url is not None, "HX-Push-Url header missing"
    assert push_url.startswith("/overview"), f"got: {push_url}"
    # Pitfall 2 from Phase 4: never push /overview/grid as the URL.
    assert "/overview/grid" not in push_url, (
        "HX-Push-Url should NOT be /overview/grid (Pitfall 2)"
    )
    assert "status=in-progress" in push_url
    assert "sort=start" in push_url
    assert "order=desc" in push_url


def test_post_overview_grid_emits_oob_filter_badges(isolated_overview, tmp_path):
    """D-OV-04 + D-OV-06: POST /overview/grid emits 6 OOB picker badge spans."""
    from app_v2.services.overview_store import add_overview
    add_overview("Samsung_S22Ultra_SM8450")
    _write_fm(
        tmp_path / "content",
        "Samsung_S22Ultra_SM8450",
        title="P1", status="in-progress",
    )

    r = _post_form_pairs(
        isolated_overview,
        "/overview/grid",
        [("status", "in-progress")],
    )
    assert r.status_code == 200
    # 6 OOB picker badges, one per FILTERABLE_COLUMNS
    for col in ("status", "customer", "ap_company", "device", "controller", "application"):
        assert f'id="picker-{col}-badge"' in r.text, f"OOB badge missing for {col}"
    assert 'hx-swap-oob="true"' in r.text


def test_post_overview_grid_repeated_keys_multi_filter(isolated_overview, tmp_path):
    """D-OV-13: ?status=A&status=B parses to multi-filter via repeated keys."""
    from app_v2.services.overview_store import add_overview
    for pid in (
        "Samsung_S22Ultra_SM8450",
        "Pixel8_GoogleTensor_GS301",
        "Xiaomi13_Pro_SM8550",
    ):
        add_overview(pid)
    _write_fm(tmp_path / "content", "Samsung_S22Ultra_SM8450", title="A", status="in-progress")
    _write_fm(tmp_path / "content", "Pixel8_GoogleTensor_GS301", title="B", status="done")
    _write_fm(tmp_path / "content", "Xiaomi13_Pro_SM8550", title="C", status="archived")

    r = _post_form_pairs(
        isolated_overview,
        "/overview/grid",
        [
            ("status", "in-progress"),
            ("status", "done"),
        ],
    )
    assert r.status_code == 200
    # The OOB count caption shows "N platform(s)"; with status=in-progress&status=done
    # narrowing 3 rows down to 2, the count must read "2 platforms".
    assert "2 platforms" in r.text, "Filter should narrow to 2 of 3 platforms"


def test_post_overview_grid_escapes_xss_payload_in_filter_value(isolated_overview, tmp_path):
    """T-05-05-02 mitigation: hostile filter value is HTML-escaped in checkbox value."""
    from app_v2.services.overview_store import add_overview
    add_overview("Samsung_S22Ultra_SM8450")
    _write_fm(
        tmp_path / "content",
        "Samsung_S22Ultra_SM8450",
        title="P1", status="<script>alert(1)</script>",
    )

    r = isolated_overview.get("/overview")
    assert r.status_code == 200
    # The hostile string MUST be HTML-escaped wherever rendered.
    assert "<script>alert(1)</script>" not in r.text
    assert "&lt;script&gt;" in r.text or "&lt;script>" in r.text


# ---------------------------------------------------------------------------
# POST /overview/add — D-OV-11 HX-Redirect on success; plain-text errors
# ---------------------------------------------------------------------------

def test_post_overview_add_success_returns_hx_redirect(isolated_overview):
    """D-OV-11: POST /overview/add success returns 200 + HX-Redirect: /overview."""
    r = isolated_overview.post(
        "/overview/add",
        data={"platform_id": "Samsung_S22Ultra_SM8450"},
    )
    assert r.status_code == 200
    assert r.headers.get("HX-Redirect") == "/overview"


def test_post_overview_add_unknown_platform_returns_404_plain_text(isolated_overview):
    """Unknown platform → 404 + plain-text body."""
    r = isolated_overview.post(
        "/overview/add",
        data={"platform_id": "NotInCatalog_Unknown_XY1234"},
    )
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("text/plain")
    assert "Unknown platform" in r.text


def test_post_overview_add_duplicate_returns_409_plain_text(isolated_overview):
    """Duplicate platform → 409 + plain-text body."""
    isolated_overview.post(
        "/overview/add",
        data={"platform_id": "Samsung_S22Ultra_SM8450"},
    )
    r2 = isolated_overview.post(
        "/overview/add",
        data={"platform_id": "Samsung_S22Ultra_SM8450"},
    )
    assert r2.status_code == 409
    assert r2.headers["content-type"].startswith("text/plain")
    assert "Already in your overview" in r2.text


def test_post_overview_add_invalid_regex_returns_422(isolated_overview):
    """Path traversal string is rejected at Form validation — returns 422."""
    r = isolated_overview.post(
        "/overview/add",
        data={"platform_id": "../../etc/passwd"},
    )
    assert r.status_code == 422


def test_post_overview_add_symbols_returns_422(isolated_overview):
    """Platform ID with forbidden symbols is rejected — returns 422."""
    r = isolated_overview.post(
        "/overview/add",
        data={"platform_id": "Too!Many$Symbols"},
    )
    assert r.status_code == 422


def test_post_overview_add_missing_field_returns_422(isolated_overview):
    """POST without platform_id field returns 422."""
    r = isolated_overview.post("/overview/add", data={})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Forbidden routes (D-OV-04) — DELETE /overview/<pid>, POST /overview/filter, /reset
# ---------------------------------------------------------------------------

def test_delete_overview_pid_route_is_gone(isolated_overview):
    """D-OV-04: DELETE /overview/<pid> route REMOVED — Remove button gone."""
    r = isolated_overview.delete("/overview/Samsung_S22Ultra_SM8450")
    # Either 404 (no path registered for any HTTP method) or 405 (path
    # registered for another method but not DELETE) is acceptable. What
    # MUST NOT happen is 200 (legacy route survived).
    assert r.status_code in (404, 405), (
        f"DELETE /overview/<pid> should be gone; got {r.status_code}"
    )


def test_post_overview_filter_route_is_gone(isolated_overview):
    """D-OV-04: POST /overview/filter REMOVED."""
    r = isolated_overview.post("/overview/filter", data={"brand": "Samsung"})
    assert r.status_code in (404, 405)


def test_post_overview_filter_reset_route_is_gone(isolated_overview):
    """D-OV-04: POST /overview/filter/reset REMOVED."""
    r = isolated_overview.post("/overview/filter/reset")
    assert r.status_code in (404, 405)
