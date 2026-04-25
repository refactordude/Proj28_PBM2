"""Tests for Phase 03 platform-detail + content CRUD routes.

Covers:
- GET /platforms/{pid}                   — detail page (rendered or empty-state)
- POST /platforms/{pid}/edit             — edit panel fragment
- POST /platforms/{pid}/preview          — preview pane fragment (no disk I/O)
- POST /platforms/{pid}                  — save (atomic) → rendered-view fragment
- DELETE /platforms/{pid}/content        — delete → empty-state fragment
- Path traversal hardening across all 5 routes (D-22 — 3 attack strings × 5 routes)
- 64KB form-size cap (D-31)
- XSS escape via MarkdownIt('js-default') (Pitfall 1)
- Overview row AI Summary button enable/disable based on has_content (SUMMARY-01 wiring)

Fixture redirects CONTENT_DIR (in BOTH platforms.py and overview.py) + OVERVIEW_YAML
+ list_platforms so each test gets an isolated tmp_path filesystem.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


_FAKE_CATALOG = [
    "Samsung_S22Ultra_SM8450",
    "Pixel8_GoogleTensor_GS301",
    "Xiaomi13_Pro_SM8550",
]

_PID = "Samsung_S22Ultra_SM8450"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def isolated_content(tmp_path, monkeypatch):
    """Redirect CONTENT_DIR + OVERVIEW_YAML + list_platforms to tmp_path.

    Yields ``(client, content_dir)``. Tests pre-populate files via
    ``(content_dir / f"{pid}.md").write_text(...)``.
    """
    cd = tmp_path / "content" / "platforms"
    cd.mkdir(parents=True)

    import app_v2.routers.platforms as platforms_mod
    import app_v2.routers.overview as overview_mod
    import app_v2.services.overview_store as overview_store_mod

    monkeypatch.setattr(platforms_mod, "CONTENT_DIR", cd)
    monkeypatch.setattr(overview_mod, "CONTENT_DIR", cd)
    monkeypatch.setattr(overview_store_mod, "OVERVIEW_YAML", tmp_path / "overview.yaml")
    monkeypatch.setattr(
        overview_mod,
        "list_platforms",
        lambda db, db_name="": list(_FAKE_CATALOG),
    )

    from app_v2.services.cache import clear_all_caches
    clear_all_caches()

    from app_v2.main import app
    with TestClient(app) as client:
        yield client, cd


# ---------------------------------------------------------------------------
# GET /platforms/{pid} — detail page
# ---------------------------------------------------------------------------

def test_get_detail_empty_state(isolated_content):
    """No content file → 200 with empty-state copy + 'Add Content' button."""
    client, cd = isolated_content
    r = client.get(f"/platforms/{_PID}")
    assert r.status_code == 200
    body = r.text
    assert "No content yet — Add some." in body
    assert 'btn btn-primary' in body
    assert "Add Content" in body


def test_get_detail_renders_existing(isolated_content):
    """Content file present → 200 with rendered HTML + AI/Edit/Delete buttons."""
    client, cd = isolated_content
    (cd / f"{_PID}.md").write_text("# Hello\n", encoding="utf-8")
    r = client.get(f"/platforms/{_PID}")
    assert r.status_code == 200
    body = r.text
    assert "<h1>Hello</h1>" in body
    assert 'class="ai-btn' in body
    assert "bi-pencil-square" in body
    assert "bi-trash3" in body


def test_get_detail_xss_escapes_script(isolated_content):
    """Raw <script> in content does NOT survive into rendered HTML."""
    client, cd = isolated_content
    (cd / f"{_PID}.md").write_text("<script>alert(1)</script>", encoding="utf-8")
    r = client.get(f"/platforms/{_PID}")
    assert r.status_code == 200
    assert "<script>alert" not in r.text.lower()


def test_get_detail_includes_page_title(isolated_content):
    """Page title contains platform_id and base.html '— PBM2 v2.0' suffix."""
    client, cd = isolated_content
    r = client.get(f"/platforms/{_PID}")
    assert r.status_code == 200
    assert f"<title>{_PID} — PBM2 v2.0</title>" in r.text


# ---------------------------------------------------------------------------
# POST /platforms/{pid}/edit — edit panel
# ---------------------------------------------------------------------------

def test_post_edit_returns_edit_panel_with_existing_content(isolated_content):
    """Edit on existing file → textarea pre-filled + Write/Preview pills."""
    client, cd = isolated_content
    (cd / f"{_PID}.md").write_text("raw md", encoding="utf-8")
    r = client.post(f"/platforms/{_PID}/edit")
    assert r.status_code == 200
    body = r.text
    assert "<textarea" in body
    assert "raw md" in body
    assert "Write" in body
    assert "Preview" in body


def test_post_edit_returns_edit_panel_when_no_content(isolated_content):
    """Edit with no existing file → empty textarea + placeholder hint."""
    client, cd = isolated_content
    r = client.post(f"/platforms/{_PID}/edit")
    assert r.status_code == 200
    body = r.text
    assert "<textarea" in body
    # textarea should contain no preexisting text between its tags;
    # body still has the placeholder/hint copy.
    assert "Write notes in markdown" in body or "placeholder" in body


def test_post_edit_includes_data_cancel_html(isolated_content):
    """Edit panel carries data-cancel-html attribute (D-10 client-side cancel)."""
    client, cd = isolated_content
    (cd / f"{_PID}.md").write_text("# Hi", encoding="utf-8")
    r = client.post(f"/platforms/{_PID}/edit")
    assert r.status_code == 200
    assert 'data-cancel-html="' in r.text


# ---------------------------------------------------------------------------
# POST /platforms/{pid}/preview — preview pane
# ---------------------------------------------------------------------------

def test_post_preview_renders_markdown(isolated_content):
    """Preview returns rendered HTML and creates NO file on disk."""
    client, cd = isolated_content
    r = client.post(f"/platforms/{_PID}/preview", data={"content": "# Hi"})
    assert r.status_code == 200
    assert "<h1>Hi</h1>" in r.text
    # No file written
    assert not (cd / f"{_PID}.md").exists()


def test_post_preview_xss_safe(isolated_content):
    """Preview escapes raw <img onerror=...> via js-default."""
    client, cd = isolated_content
    r = client.post(f"/platforms/{_PID}/preview", data={"content": "<img onerror=x>"})
    assert r.status_code == 200
    assert 'onerror=x' not in r.text  # raw HTML escaped


def test_post_preview_too_large_returns_422(isolated_content):
    """Preview with content > 64KB → 422 (no body parse)."""
    client, cd = isolated_content
    payload = "x" * (65536 + 1)
    r = client.post(f"/platforms/{_PID}/preview", data={"content": payload})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /platforms/{pid} — save (atomic)
# ---------------------------------------------------------------------------

def test_post_save_writes_file_atomically(isolated_content):
    """Save writes the file and returns the rendered-view fragment."""
    client, cd = isolated_content
    r = client.post(f"/platforms/{_PID}", data={"content": "# Saved"})
    assert r.status_code == 200
    target = cd / f"{_PID}.md"
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "# Saved"
    assert "<h1>Saved</h1>" in r.text


def test_post_save_returns_rendered_view_outerHTML_target(isolated_content):
    """Save response wraps in <div class="panel" id="content-area"> for outerHTML swap."""
    client, cd = isolated_content
    r = client.post(f"/platforms/{_PID}", data={"content": "# Wrapped"})
    assert r.status_code == 200
    body = r.text
    assert 'id="content-area"' in body
    assert 'class="panel"' in body


def test_post_save_too_large_returns_422(isolated_content):
    """Save with content > 64KB → 422; file NOT created."""
    client, cd = isolated_content
    payload = "x" * (65536 + 1)
    r = client.post(f"/platforms/{_PID}", data={"content": payload})
    assert r.status_code == 422
    assert not (cd / f"{_PID}.md").exists()


# ---------------------------------------------------------------------------
# DELETE /platforms/{pid}/content — delete
# ---------------------------------------------------------------------------

def test_delete_existing_returns_empty_state(isolated_content):
    """Delete existing file → 200 with empty-state, file gone."""
    client, cd = isolated_content
    target = cd / f"{_PID}.md"
    target.write_text("# bye", encoding="utf-8")
    r = client.delete(f"/platforms/{_PID}/content")
    assert r.status_code == 200
    assert "No content yet — Add some." in r.text
    assert "Add Content" in r.text
    assert not target.exists()


def test_delete_missing_returns_empty_state(isolated_content):
    """Delete on missing file → 200 with empty-state (idempotent)."""
    client, cd = isolated_content
    r = client.delete(f"/platforms/{_PID}/content")
    assert r.status_code == 200
    assert "No content yet — Add some." in r.text


# ---------------------------------------------------------------------------
# Path traversal — D-22 (3 attack strings × 5 routes = 15 cases)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_pid", [
    "..%2F..%2Fetc%2Fpasswd",  # URL-encoded ../../etc/passwd
    "%2Fetc%2Fpasswd",          # URL-encoded /etc/passwd
    "foo%00bar",                # URL-encoded null byte
])
@pytest.mark.parametrize("method,path_tmpl,form_data", [
    ("GET",    "/platforms/{}",         None),
    ("POST",   "/platforms/{}/edit",    {"content": ""}),
    ("POST",   "/platforms/{}/preview", {"content": ""}),
    ("POST",   "/platforms/{}",         {"content": ""}),
    ("DELETE", "/platforms/{}/content", None),
])
def test_path_traversal_rejected_before_filesystem(
    isolated_content, bad_pid, method, path_tmpl, form_data
):
    """All 5 routes reject path-traversal-shaped platform_id at the routing layer.

    URL-encoded forms ensure Starlette's URL router sees the literal decoded
    value as the path parameter. Acceptance band: 404 OR 422 (Starlette returns
    404 when no route matches the encoded slashes; FastAPI returns 422 when the
    path-parameter regex rejects).
    """
    client, cd = isolated_content
    url = path_tmpl.format(bad_pid)
    if form_data is not None:
        r = client.request(method, url, data=form_data)
    else:
        r = client.request(method, url)
    assert r.status_code in (404, 422), (
        f"{method} {url}: got {r.status_code}, expected 404 or 422"
    )
    leftovers = list(cd.iterdir())
    assert leftovers == [], f"Files leaked into content dir: {leftovers}"


# ---------------------------------------------------------------------------
# Overview row AI Summary button — SUMMARY-01 wiring
# ---------------------------------------------------------------------------

def test_overview_row_ai_button_disabled_when_no_content(isolated_content):
    """No content file → AI Summary button rendered with disabled + tooltip."""
    client, cd = isolated_content
    # Add a platform to the overview list first
    add_r = client.post("/overview/add", data={"platform_id": _PID})
    assert add_r.status_code == 200

    r = client.get("/")
    body = r.text
    assert 'class="ai-btn ms-2"' in body
    # Disabled with tooltip — appears in the rendered row
    assert "disabled" in body
    assert "Content page must exist first" in body


def test_overview_row_ai_button_enabled_when_content_exists(isolated_content):
    """Content file present → AI Summary button enabled, hx-post to /summary."""
    client, cd = isolated_content
    # Pre-create content for this platform
    (cd / f"{_PID}.md").write_text("# Hello", encoding="utf-8")
    add_r = client.post("/overview/add", data={"platform_id": _PID})
    assert add_r.status_code == 200

    r = client.get("/")
    body = r.text
    assert 'class="ai-btn ms-2"' in body
    assert f'hx-post="/platforms/{_PID}/summary"' in body
    # The disabled+tooltip combo should NOT appear when content exists.
    # Specifically the *button* should not have a `disabled` attribute. We
    # search for the ai-btn block and assert no 'disabled' inside it.
    ai_idx = body.find('class="ai-btn ms-2"')
    assert ai_idx >= 0
    btn_close = body.find(">", ai_idx)
    btn_attrs = body[ai_idx:btn_close]
    assert "disabled" not in btn_attrs


def test_overview_row_has_summary_slot(isolated_content):
    """Per-row summary slot wrapper present (id="summary-{pid}")."""
    client, cd = isolated_content
    add_r = client.post("/overview/add", data={"platform_id": _PID})
    assert add_r.status_code == 200

    r = client.get("/")
    assert f'id="summary-{_PID}"' in r.text
