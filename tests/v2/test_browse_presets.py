"""Browse-preset tests (260507-r0k).

Mirrors tests/v2/test_overview_presets.py shape: 9 tests covering
  - load_browse_presets() — happy path returns 3 entries from the
    example YAML.
  - load_browse_presets() — malformed entries are silently skipped.
  - load_browse_presets() — unparseable YAML returns [].
  - load_browse_presets() — missing YAML returns [].
  - GET /browse — chip strip renders with the 3 preset chips.
  - GET /browse — strip omitted when load_browse_presets() returns [].
  - GET /browse/preset/<name> — overrides current platforms+params and
    returns the OOB blocks plus HX-Push-Url with the resolved filters.
  - GET /browse/preset/<name> — 404 on unknown preset.
  - GET /browse/preset/<name> — stray query params do NOT bleed into
    the response (OVERRIDE semantics).
"""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app_v2.main import app
from app_v2.services.browse_preset_store import load_browse_presets


# Mock DB plumbing — same pattern as test_browse_routes.py
class MockConfig:
    name = "test_db"


class MockDB:
    config = MockConfig()


def _patch_cache(monkeypatch, *, platforms=None, params=None, fetch=None):
    """Patch cache layer at browse_service call-site (the import binding)."""
    if platforms is not None:
        monkeypatch.setattr(
            "app_v2.services.browse_service.list_platforms",
            lambda db, db_name="": list(platforms),
        )
    if params is not None:
        monkeypatch.setattr(
            "app_v2.services.browse_service.list_parameters_for_platforms",
            lambda db, platforms_tuple, db_name="": list(params),
        )
    if fetch is not None:
        monkeypatch.setattr(
            "app_v2.services.browse_service.fetch_cells", fetch,
        )


@pytest.fixture
def client(monkeypatch):
    """TestClient with MockDB on app.state.db AFTER lifespan ran."""
    with TestClient(app) as c:
        app.state.db = MockDB()
        yield c
        app.state.db = None


# ---------------------------------------------------------------------------
# Loader (4 tests)
# ---------------------------------------------------------------------------


def test_load_browse_presets_returns_three_seed_entries() -> None:
    """The committed config/browse_presets.example.yaml seeds 3 entries."""
    presets = load_browse_presets()
    assert len(presets) == 3, presets
    names = [p["name"] for p in presets]
    assert names == ["snapdragon-flagships", "exynos-lineup", "auto-iot-specials"]
    # Verbatim seed values preserved.
    sf = next(p for p in presets if p["name"] == "snapdragon-flagships")
    assert sf["label"] == "Snapdragon flagships"
    assert sf["platforms"] == [
        "SM8550_rev1", "SM8650_v1", "SM8650_v2", "SM8850_v1",
    ]
    assert sf["params"] == [
        "VendorInfo · ManufacturerName",
        "GeometryDescriptor · RawDeviceCapacity",
    ]
    assert sf["swap_axes"] is False
    # swap_axes:true on the third preset.
    auto = next(p for p in presets if p["name"] == "auto-iot-specials")
    assert auto["swap_axes"] is True
    assert auto["params"] == [
        "AutomotiveProfile · QualGradeLevel",
        "IoTPowerProfile · DeepSleepCurrentUA",
        "VendorInfo · ManufacturerName",
    ]


def test_load_browse_presets_skips_malformed_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each malformed entry is silently dropped; valid entry survives."""
    yaml_text = dedent("""
        # 1 valid + 7 distinct malformed cases — only the valid one survives.
        - name: ok-preset
          label: OK preset
          platforms: ["P1"]
          params: ["cat · item"]
        - name: missing-label
          platforms: ["P1"]
          params: ["cat · item"]
        - label: missing-name
          platforms: ["P1"]
          params: ["cat · item"]
        - name: non-list-platforms
          label: Non-list platforms
          platforms: "P1"
          params: ["cat · item"]
        - name: non-string-platform
          label: Non-string platform
          platforms: [42]
          params: ["cat · item"]
        - name: both-empty
          label: Both empty
          platforms: []
          params: []
        - name: bad-swap-axes
          label: Bad swap axes
          platforms: ["P1"]
          params: ["cat · item"]
          swap_axes: "yes"
        - "not even a mapping"
    """).strip()

    # Point load_browse_presets at our tmp file by chdir-ing into a tmp dir
    # whose `config/browse_presets.yaml` is the test file. Exercises the
    # real fallback chain — the project-root example.yaml is bypassed
    # because cwd's config/browse_presets.yaml takes precedence (first in
    # the chain).
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "browse_presets.yaml").write_text(yaml_text, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    presets = load_browse_presets()
    assert len(presets) == 1, presets
    assert presets[0]["name"] == "ok-preset"
    assert presets[0]["platforms"] == ["P1"]
    assert presets[0]["params"] == ["cat · item"]
    assert presets[0]["swap_axes"] is False


def test_load_browse_presets_returns_empty_on_unparseable_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Syntactically broken YAML never raises; returns []."""
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "browse_presets.yaml").write_text(
        "[\nthis: is: not: valid: yaml", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    assert load_browse_presets() == []


def test_load_browse_presets_returns_empty_when_no_yaml_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No browse_presets.yaml AND no browse_presets.example.yaml → []."""
    monkeypatch.chdir(tmp_path)
    assert load_browse_presets() == []


# ---------------------------------------------------------------------------
# Render (2 tests)
# ---------------------------------------------------------------------------


def test_get_browse_renders_preset_chip_strip(client, monkeypatch) -> None:
    _patch_cache(monkeypatch, platforms=["SM8550_rev1"], params=[
        {"InfoCategory": "VendorInfo", "Item": "ManufacturerName"},
    ])
    r = client.get("/browse")
    assert r.status_code == 200
    # Strip wrapper present.
    assert 'id="browse-preset-row"' in r.text
    # 3 chips render with the seed labels and slugs.
    assert 'data-preset="snapdragon-flagships"' in r.text
    assert 'data-preset="exynos-lineup"' in r.text
    assert 'data-preset="auto-iot-specials"' in r.text
    assert "Snapdragon flagships" in r.text
    assert "Exynos lineup" in r.text
    assert "Auto + IoT specials" in r.text
    # Each chip wires hx-get + href + hx-push-url.
    assert 'hx-get="/browse/preset/snapdragon-flagships"' in r.text
    assert 'href="/browse/preset/snapdragon-flagships"' in r.text
    assert 'hx-push-url="true"' in r.text
    # Strip renders BEFORE the filter bar (line ordering check).
    strip_idx = r.text.index('browse-preset-row')
    bar_idx = r.text.index('browse-filter-bar')
    assert strip_idx < bar_idx, "preset strip must render above filter bar"


def test_get_browse_omits_strip_when_no_presets(
    client, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty load_browse_presets() → strip wrapper is NOT rendered."""
    _patch_cache(monkeypatch, platforms=["P1"], params=[
        {"InfoCategory": "cat", "Item": "item"},
    ])
    monkeypatch.setattr(
        "app_v2.routers.browse.load_browse_presets", lambda: [],
    )
    r = client.get("/browse")
    assert r.status_code == 200
    assert "browse-preset-row" not in r.text
    assert "ff-preset-chip" not in r.text


# ---------------------------------------------------------------------------
# Click-apply (3 tests)
# ---------------------------------------------------------------------------


def test_get_browse_preset_overrides_filters_and_returns_oob_blocks(
    client, monkeypatch,
) -> None:
    # Patch cache to return the preset's platforms + params so the grid
    # actually renders rows. The test does NOT depend on the live demo
    # SQLite DB — it stubs the cache layer.
    _patch_cache(
        monkeypatch,
        platforms=["SM8550_rev1", "SM8650_v1", "SM8650_v2", "SM8850_v1"],
        params=[
            {"InfoCategory": "VendorInfo", "Item": "ManufacturerName"},
            {"InfoCategory": "GeometryDescriptor", "Item": "RawDeviceCapacity"},
        ],
        fetch=lambda db, p, ic, i, row_cap=200, db_name="": (
            pd.DataFrame({
                "PLATFORM_ID": ["SM8550_rev1"],
                "InfoCategory": ["VendorInfo"],
                "Item": ["ManufacturerName"],
                "Result": ["SK Hynix"],
            }), False,
        ),
    )
    r = client.get("/browse/preset/snapdragon-flagships")
    assert r.status_code == 200
    # Returns OOB blocks (not the full page shell) — same shape as
    # POST /browse/grid (origin != "params" branch).
    assert "<html" not in r.text.lower()
    assert 'class="navbar' not in r.text
    # Has the grid table (or at least the grid wrapper).
    assert 'pivot-table' in r.text
    # OOB count caption — fragment carries the OOB attribute.
    assert 'id="grid-count"' in r.text
    assert 'hx-swap-oob="true"' in r.text
    # OOB picker badges.
    assert 'id="picker-platforms-badge"' in r.text
    assert 'id="picker-params-badge"' in r.text
    # OOB params picker slot (origin != "params" for preset GET).
    assert 'id="params-picker-slot"' in r.text
    # HX-Push-Url carries the canonical /browse?... query string.
    push = r.headers.get("HX-Push-Url", "")
    assert push.startswith("/browse?"), push
    # Repeated keys for each platform.
    assert "platforms=SM8550_rev1" in push
    assert "platforms=SM8650_v1" in push
    assert "platforms=SM8650_v2" in push
    assert "platforms=SM8850_v1" in push
    # %20 (space) and %C2%B7 (middle dot) URL-encoded params.
    assert "VendorInfo%20%C2%B7%20ManufacturerName" in push
    assert "GeometryDescriptor%20%C2%B7%20RawDeviceCapacity" in push
    # No swap=1 — snapdragon-flagships has swap_axes=False.
    assert "swap=" not in push


def test_get_browse_preset_unknown_returns_404(client) -> None:
    r = client.get("/browse/preset/no-such-preset")
    assert r.status_code == 404


def test_get_browse_preset_clicked_after_existing_filters_overrides_them(
    client, monkeypatch,
) -> None:
    """OVERRIDE semantics: stray query params do NOT bleed into the response.

    The HTTP-level test cannot easily simulate "user had existing filters
    then clicked a preset" because /browse/preset/<name> does not read
    filter query params from the request — but THAT is precisely the
    contract: the preset is the entire filter state, regardless of what
    the request URL contains. We pin the contract by sending stray query
    params and asserting they are ignored.
    """
    _patch_cache(
        monkeypatch,
        platforms=["EXYNOS1380_c", "EXYNOS2200_b", "EXYNOS2400_a"],
        params=[
            {"InfoCategory": "DeviceInfo", "Item": "bDeviceVersion"},
            {"InfoCategory": "DeviceInfo", "Item": "NumberOfLU"},
        ],
        fetch=lambda db, p, ic, i, row_cap=200, db_name="": (
            pd.DataFrame({
                "PLATFORM_ID": ["EXYNOS1380_c"],
                "InfoCategory": ["DeviceInfo"],
                "Item": ["NumberOfLU"],
                "Result": ["8"],
            }), False,
        ),
    )
    # Pass stray query params that the preset does NOT mention.
    r = client.get(
        "/browse/preset/exynos-lineup",
        params=[
            ("platforms", "SOME_OTHER_PLATFORM"),
            ("params", "stray · param"),
            ("swap", "1"),
        ],
    )
    assert r.status_code == 200
    push = r.headers.get("HX-Push-Url", "")
    # Stray values are NOT in the canonical URL.
    assert "SOME_OTHER_PLATFORM" not in push
    assert "stray" not in push
    assert "swap=" not in push  # exynos-lineup has swap_axes=False
    # Preset values ARE in the canonical URL.
    assert "platforms=EXYNOS1380_c" in push
    assert "platforms=EXYNOS2200_b" in push
    assert "platforms=EXYNOS2400_a" in push
    assert "DeviceInfo%20%C2%B7%20bDeviceVersion" in push
    assert "DeviceInfo%20%C2%B7%20NumberOfLU" in push
