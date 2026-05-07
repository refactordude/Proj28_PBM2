"""Filter-preset tests (260507-obp).

Covers:
  - load_presets() — happy path returns 3 entries from the example YAML.
  - load_presets() — malformed entries are silently skipped.
  - GET /overview — chip strip renders with the 3 preset chips.
  - GET /overview/preset/<name> — overrides current filters and returns
    the 4 OOB blocks plus HX-Push-Url with the resolved filters.
  - GET /overview/preset/<name> — 404 on unknown preset.
"""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from fastapi.testclient import TestClient

from app_v2.main import app
from app_v2.services.joint_validation_store import clear_parse_cache
from app_v2.services.preset_store import load_presets
from app_v2.services.summary_service import clear_summary_cache


SAMPLE_HTML = b"""<!DOCTYPE html><html><body>
<h1>Test Joint Validation</h1>
<table>
  <tr><th><strong>Status</strong></th><td>In Progress</td></tr>
  <tr><th><strong>Customer</strong></th><td>Samsung</td></tr>
  <tr><th><strong>AP Company</strong></th><td>Qualcomm</td></tr>
  <tr><th><strong>Application</strong></th><td>Wearable</td></tr>
  <tr><th><strong>Device</strong></th><td>UFS 4.0</td></tr>
  <tr><th><strong>Start</strong></th><td>2026-04-01</td></tr>
</table>
</body></html>"""


@pytest.fixture(autouse=True)
def _reset_caches():
    clear_parse_cache()
    clear_summary_cache()
    yield
    clear_parse_cache()
    clear_summary_cache()


@pytest.fixture
def jv_dir_with_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Drop one matching JV folder so the preset queries return a row."""
    folder = tmp_path / "3193868200"
    folder.mkdir()
    (folder / "index.html").write_bytes(SAMPLE_HTML)
    monkeypatch.setattr("app_v2.services.joint_validation_store.JV_ROOT", tmp_path)
    monkeypatch.setattr("app_v2.routers.overview.JV_ROOT", tmp_path)
    monkeypatch.setattr("app_v2.routers.joint_validation.JV_ROOT", tmp_path)
    return tmp_path


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def test_load_presets_returns_three_seed_entries() -> None:
    """The committed config/presets.example.yaml seeds 3 entries verbatim."""
    presets = load_presets()
    assert len(presets) == 3, presets
    names = [p["name"] for p in presets]
    assert names == ["korean-oems-in-progress", "qualcomm-wearables", "pending-ufs4"]
    # Multi-value within a facet preserved.
    korean = next(p for p in presets if p["name"] == "korean-oems-in-progress")
    assert korean["label"] == "Korean OEMs in progress"
    assert korean["filters"]["status"] == ["In Progress"]
    assert korean["filters"]["customer"] == ["Samsung", "Hyundai"]
    # Multi-facet (AND-across-facets) preserved.
    qc = next(p for p in presets if p["name"] == "qualcomm-wearables")
    assert qc["filters"]["ap_company"] == ["Qualcomm"]
    assert qc["filters"]["application"] == ["Wearable"]


def test_load_presets_skips_malformed_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each malformed entry is silently dropped; valid entries survive."""
    yaml_text = dedent("""
        # 1 valid + 6 distinct malformed cases — only the valid one survives.
        - name: ok-preset
          label: OK preset
          filters:
            status: ["Pending"]
        - name: missing-label
          filters:
            status: ["Pending"]
        - label: missing-name
          filters:
            status: ["Pending"]
        - name: unknown-facet
          label: Unknown facet
          filters:
            no_such_facet: ["x"]
        - name: non-list-value
          label: Non-list value
          filters:
            status: "Pending"
        - name: empty-facet
          label: Empty facet
          filters:
            status: []
        - name: missing-filters
          label: Missing filters
        - "not even a mapping"
    """).strip()

    # Point load_presets at our tmp file by chdir-ing into a tmp dir whose
    # `config/presets.yaml` is the test file. This exercises the real
    # fallback chain (the example.yaml in the project root is bypassed
    # because cwd's config/presets.yaml takes precedence — first in the
    # chain).
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "presets.yaml").write_text(yaml_text, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    presets = load_presets()
    assert len(presets) == 1, presets
    assert presets[0]["name"] == "ok-preset"
    assert presets[0]["filters"] == {"status": ["Pending"]}


def test_load_presets_returns_empty_on_unparseable_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Syntactically broken YAML never raises; returns []."""
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "presets.yaml").write_text("[\nthis: is: not: valid: yaml", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert load_presets() == []


def test_load_presets_returns_empty_when_no_yaml_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No presets.yaml AND no presets.example.yaml → empty list."""
    monkeypatch.chdir(tmp_path)   # cwd has no `config/` dir at all
    assert load_presets() == []


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def test_get_overview_renders_preset_chip_strip(
    jv_dir_with_one: Path, client: TestClient
) -> None:
    r = client.get("/overview")
    assert r.status_code == 200
    # Strip wrapper present.
    assert 'id="overview-preset-row"' in r.text
    # 3 chips render with the seed labels and slugs.
    assert 'data-preset="korean-oems-in-progress"' in r.text
    assert 'data-preset="qualcomm-wearables"' in r.text
    assert 'data-preset="pending-ufs4"' in r.text
    assert "Korean OEMs in progress" in r.text
    assert "Qualcomm wearables" in r.text
    assert "Pending UFS 4.0" in r.text
    # Each chip wires hx-get + href + hx-push-url.
    assert 'hx-get="/overview/preset/qualcomm-wearables"' in r.text
    assert 'href="/overview/preset/qualcomm-wearables"' in r.text
    assert 'hx-push-url="true"' in r.text


def test_get_overview_omits_strip_when_no_presets(
    jv_dir_with_one: Path,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty load_presets() → strip wrapper is NOT rendered."""
    monkeypatch.setattr("app_v2.routers.overview.load_presets", lambda: [])
    r = client.get("/overview")
    assert r.status_code == 200
    assert "overview-preset-row" not in r.text
    assert "ff-preset-chip" not in r.text


# ---------------------------------------------------------------------------
# Click-apply
# ---------------------------------------------------------------------------


def test_get_overview_preset_overrides_filters_and_returns_oob_blocks(
    jv_dir_with_one: Path, client: TestClient
) -> None:
    r = client.get("/overview/preset/qualcomm-wearables")
    assert r.status_code == 200
    # Returns OOB blocks (not the full page shell) — same shape as POST /overview/grid.
    assert 'id="overview-grid"' in r.text
    assert 'id="overview-filter-badges" hx-swap-oob="true"' in r.text
    assert 'id="overview-count" hx-swap-oob="true"' in r.text
    assert 'id="overview-pagination" hx-swap-oob="true"' in r.text
    # Active-filter chips reflect the preset's values, not whatever was sent.
    assert 'data-facet="ap_company"' in r.text
    assert 'class="ff-chip c-3">Qualcomm</span>' in r.text
    assert 'data-facet="application"' in r.text
    assert 'class="ff-chip c-6">Wearable</span>' in r.text
    # No status / customer / device / controller chips (preset doesn't mention).
    assert 'data-facet="status"' not in r.text
    assert 'data-facet="customer"' not in r.text
    # HX-Push-Url carries the canonical /overview?... query string.
    push = r.headers.get("HX-Push-Url", "")
    assert push.startswith("/overview?"), push
    assert "ap_company=Qualcomm" in push
    assert "application=Wearable" in push
    # Preset apply does NOT carry over an old status/customer.
    assert "status=" not in push
    assert "customer=" not in push


def test_get_overview_preset_unknown_returns_404(
    jv_dir_with_one: Path, client: TestClient
) -> None:
    r = client.get("/overview/preset/no-such-preset")
    assert r.status_code == 404


def test_get_overview_preset_clicked_after_existing_filters_overrides_them(
    jv_dir_with_one: Path, client: TestClient
) -> None:
    """OVERRIDE semantics: previous filters do NOT bleed into the preset response.

    The HTTP-level test cannot easily simulate "user had existing filters
    then clicked a preset" because /overview/preset/<name> does not read
    filter query params from the request — but THAT is precisely the
    contract: the preset is the entire filter state, regardless of what
    the request URL contains. We pin the contract by sending stray query
    params and asserting they are ignored.
    """
    r = client.get(
        "/overview/preset/qualcomm-wearables",
        params=[("status", "Cancelled"), ("customer", "Apple")],
    )
    assert r.status_code == 200
    push = r.headers.get("HX-Push-Url", "")
    assert "status=" not in push
    assert "customer=" not in push
    assert "ap_company=Qualcomm" in push
    assert "application=Wearable" in push
