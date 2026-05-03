"""Phase 4 (UI Foundation) component + route tests.

Covers:
  - GET /_components returns 200 with all sections (D-UIF-02)
  - Showcase exercises every macro arg path (D-UIF-02)
  - Both popovers use Bootstrap 5 dropdown anchoring (D-UIF-03)
  - filters_popover emits chip-group .grp / .opts / .opt markup (D-UIF-04)
  - sparkline handles empty / single / constant data without crashing (D-UIF-09)
  - Routes inheriting base.html still render after Wave 3 swap (no regressions)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app_v2.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ----- D-UIF-02: showcase route -----

def test_showcase_returns_200(client):
    r = client.get("/_components")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")


def test_showcase_inherits_topbar(client):
    r = client.get("/_components")
    body = r.text
    assert 'class="topbar"' in body
    assert 'class="brand-mark">P<' in body
    assert ">PBM2<" in body


def test_showcase_no_active_tab(client):
    """active_tab='showcase' matches no PBM2 tab; no aria-selected=true on any tab."""
    r = client.get("/_components")
    body = r.text
    # Find the tabs region; ensure no aria-selected="true" appears within it
    topbar_start = body.find('class="topbar"')
    assert topbar_start >= 0
    # Search the topbar block (next ~2000 chars) for aria-selected="true"
    topbar_block = body[topbar_start:topbar_start + 2000]
    assert 'aria-selected="true"' not in topbar_block, (
        "Showcase active_tab='showcase' must not match any PBM2 tab"
    )


def test_showcase_renders_all_sections(client):
    """Every primitive section appears in the response."""
    r = client.get("/_components")
    body = r.text
    for section_label in [
        "Topbar",
        "Page-head",
        "Hero",
        "KPI 4-up",
        "KPI 5-up",
        "Sparklines",
        "Pills / Chips",
        "Date-range popover",
        "Filters popover",
        "Sticky-corner table",
    ]:
        assert section_label in body, f"Missing showcase section: {section_label}"


def test_showcase_hero_full_and_minimal(client):
    """Both hero variants render with correct labels."""
    r = client.get("/_components")
    body = r.text
    assert "Active validations" in body  # full hero label
    assert "Total platforms" in body     # minimal hero label
    # Full hero side panel (HeroSideStat with tone="red")
    assert 'class="v red"' in body
    assert 'class="v green"' in body
    # Hero-bar segments rendered
    assert 'class="hero-bar"' in body


def test_showcase_kpi_grids_render(client):
    """4-up and 5-up grids render."""
    r = client.get("/_components")
    body = r.text
    assert 'class="kpis"' in body
    assert 'class="kpis five"' in body
    # 4-up labels
    assert ">Open<" in body
    assert ">Closed<" in body
    # 5-up labels (platform names)
    assert ">SM8650<" in body
    assert ">SM8550<" in body


def test_showcase_sparkline_edge_cases_render(client):
    """Sparkline with empty / single / constant data renders without crashing."""
    r = client.get("/_components")
    assert r.status_code == 200
    # All 5 standalone sparklines + N inside KPI cards must produce SVG markup
    body = r.text
    # At least 5 SVGs (4-up has 3, 5-up has 5, standalone has 5; minimum 5)
    assert body.count("<svg") >= 5, (
        f"Expected >= 5 SVG sparklines, got {body.count('<svg')}"
    )


def test_showcase_filter_groups_hyphen_safe_naming(client):
    """D-UIF-04: filters_popover hyphen-safe group_name produces underscore form.

    Critical orientation INFO: UFS-eMMC chip group must produce
    name="ufs_emmc" (Python attr-safe). Hyphen form NOT present.
    """
    r = client.get("/_components")
    body = r.text
    assert 'name="ufs_emmc"' in body, (
        "UFS-eMMC group label must produce underscore form (D-UIF-04 hyphen-safe)"
    )
    assert 'name="ufs-emmc"' not in body, (
        "Hyphen form must NOT appear (D-UIF-04 macro replaces - with _)"
    )


def test_sparkline_constant_data_no_nan(client):
    """D-UIF-09 + INFO 9: constant data renders flat at mid-height, no NaN."""
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path

    REPO = Path(__file__).resolve().parents[2]
    env = Environment(
        loader=FileSystemLoader(str(REPO / "app_v2" / "templates")),
        autoescape=True,
    )
    tpl = env.from_string(
        '{% from "_components/sparkline.html" import sparkline %}{{ sparkline(data) }}'
    )
    constant = tpl.render(data=[5, 5, 5, 5, 5])
    assert "NaN" not in constant, "Constant data must not produce NaN paths"
    # Mid-height of viewBox 26 = 13. The sparkline uses height/2 fallback.
    assert " 13" in constant, (
        "Constant data must render flat horizontal line at mid-height (13 for "
        "default 26px viewBox)"
    )


def test_sparkline_empty_data_renders_bare_svg(client):
    """D-UIF-09: empty data renders bare <svg>, no path."""
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path

    REPO = Path(__file__).resolve().parents[2]
    env = Environment(
        loader=FileSystemLoader(str(REPO / "app_v2" / "templates")),
        autoescape=True,
    )
    tpl = env.from_string(
        '{% from "_components/sparkline.html" import sparkline %}{{ sparkline(data) }}'
    )
    empty = tpl.render(data=[])
    assert "<svg" in empty, "Empty data must still emit a <svg> element"
    assert "<path" not in empty, "Empty data must NOT emit any <path> elements"


# ----- D-UIF-03: both popovers use Bootstrap 5 dropdown anchoring -----

def test_popovers_use_bootstrap_dropdown_pattern(client):
    """Both new popovers are wrapped in dropdown + dropdown-menu pop."""
    r = client.get("/_components")
    body = r.text
    # Two .dropdown.pop-wrap occurrences (one per popover)
    assert body.count('class="dropdown pop-wrap"') >= 2
    # Two .dropdown-menu.pop occurrences
    assert body.count('class="dropdown-menu pop"') >= 2
    # data-bs-auto-close="outside" present (allows interactive popover content)
    assert 'data-bs-auto-close="outside"' in body


# ----- D-UIF-04: filters_popover chip-group markup -----

def test_filters_popover_chip_group_markup(client):
    r = client.get("/_components")
    body = r.text
    # Group label class
    assert 'class="grp"' in body
    assert 'class="grp-l"' in body
    # Chip option button (one with .on, others without)
    assert 'class="opt on"' in body
    # Hidden inputs for form association
    assert 'data-opt=' in body
    # Group names lowercased + underscored
    assert 'name="status"' in body
    assert 'name="oem"' in body
    # CTAs strengthened per UI-SPEC §Copywriting
    assert ">Reset Filters<" in body
    assert ">Apply Filters<" in body


def test_date_range_popover_markup(client):
    r = client.get("/_components")
    body = r.text
    # Date inputs with form-association
    assert 'type="date"' in body
    assert 'name="date_start"' in body
    assert 'name="date_end"' in body
    # WR-03 fix: the quick-range chip row (data-quick-days="...") was
    # removed because no JS read the attribute. Verify the dead UI is
    # gone — re-add this assertion only when a quick-range handler ships.
    assert 'class="qrow"' not in body
    assert 'data-quick-days=' not in body
    # CTAs (single-word per UI-SPEC §Copywriting)
    assert ">Reset<" in body
    assert ">Apply<" in body
    # WR-02 fix: reset controls are real <button type="button"> elements
    # (no <a href="#">) so chip-toggle.js can preventDefault before any
    # browser-default navigation to the page-top fragment.
    assert '<a href="#" data-action="reset"' not in body
    assert 'data-action="reset"' in body


# ----- D-UIF-10: sticky-corner table rendered -----

def test_sticky_corner_table_renders(client):
    r = client.get("/_components")
    body = r.text
    assert 'class="table-sticky-corner-wrap"' in body
    assert 'class="table-sticky-corner"' in body
    # Rows present
    assert ">SM8650<" in body
    assert ">UFS Ver<" in body  # column header


# ----- Regression: existing routes still work after Wave 3 -----

def test_root_still_renders_with_topbar(client):
    r = client.get("/")
    assert r.status_code == 200
    assert 'class="topbar"' in r.text


def test_browse_still_renders_with_topbar(client):
    r = client.get("/browse")
    assert r.status_code == 200
    assert 'class="topbar"' in r.text


def test_ask_still_renders_with_topbar(client):
    r = client.get("/ask")
    assert r.status_code == 200
    assert 'class="topbar"' in r.text
    # Ask page-specific contracts preserved (Plotly extra_head, htmx-ext-sse)
    assert "vendor/plotly/plotly.min.js" in r.text
    assert "vendor/htmx/htmx-ext-sse.js" in r.text
