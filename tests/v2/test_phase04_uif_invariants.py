"""Phase 4 (UI Foundation) static-source invariants.

These tests grep the source for required patterns and forbidden patterns.
They are NOT functional tests; they enforce policy:
  - Wave 1 CSS rules present in app.css
  - Wave 1 Google Fonts link present in base.html (Pitfall 1)
  - Wave 3 base.html replaced legacy navbar with the topbar partial
  - chip-toggle.js exists as a sibling to popover-search.js (Pitfall 8)
  - .panel-header CSS rule still present in Wave 4 (Wave 5 atomically rewrites
    it to .ph rule together with the markup migration and Phase 02 invariant
    test updates)
  - _picker_popover.html UNCHANGED (D-UIF-05 / D-UI2-09)

File naming: test_phase04_uif_*.py to avoid collision with the v2.0
milestone's test_phase04_*.py (Browse Tab Port).
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
APP_CSS = REPO / "app_v2" / "static" / "css" / "app.css"
BASE_HTML = REPO / "app_v2" / "templates" / "base.html"
CHIP_TOGGLE_JS = REPO / "app_v2" / "static" / "js" / "chip-toggle.js"
POPOVER_SEARCH_JS = REPO / "app_v2" / "static" / "js" / "popover-search.js"
PICKER_POPOVER = REPO / "app_v2" / "templates" / "browse" / "_picker_popover.html"
COMPONENTS_DIR = REPO / "app_v2" / "templates" / "_components"


def _read(p: Path) -> str:
    return p.read_text()


# ----- Wave 1: CSS rules in app.css -----

def test_topbar_css_rule_present() -> None:
    """D-UIF-06: app.css must contain .topbar / .brand / .brand-mark / .av rules."""
    src = _read(APP_CSS)
    assert ".topbar {" in src
    assert ".brand-mark {" in src
    assert ".av {" in src
    assert "linear-gradient(135deg, #3366ff, #5e7cff)" in src


def test_tabs_css_rule_present() -> None:
    """D-UIF-07: app.css must contain .tabs / .tab / .tab[aria-selected=true] rules."""
    src = _read(APP_CSS)
    assert ".tabs {" in src
    assert ".tab {" in src
    assert '.tab[aria-selected="true"]' in src


def test_ph_css_rule_present_with_d_ui2_12_declarations() -> None:
    """D-UIF-01 (rename path) + D-UI2-12: .ph rule + .ph .panel-title rule with the
    D-UI2-12 declarations (font-size: 18px; font-weight: 700; margin: 0) must exist.

    Forward-compatible across Wave 4 (which still has .panel-header rules) and
    Wave 5 (which atomically rewrites .panel-header family rules to .ph family
    rules together with the markup migration and Phase 02 invariant test updates).
    Either state is acceptable to this Wave 4 test:
      - Wave 4 shipped, Wave 5 not yet: both .ph and .panel-header rules present.
      - Wave 5 shipped: only .ph rules present (D-UIF-01 LOCKED rename path complete).

    D-UI2-12 declarations MUST be present under EITHER selector — this is the
    load-bearing contract that survives the rename.
    """
    src = _read(APP_CSS)
    # .ph rule must exist (Wave 1 shipped this; Wave 5 may consolidate but never deletes it)
    assert ".ph {" in src, "app.css must contain a .ph rule"
    # D-UI2-12 declarations must exist under .ph .panel-title (Wave 5 rewrites
    # .panel-header .panel-title to .ph .panel-title with byte-equivalent decls).
    # Pre-Wave-5 the .panel-header .panel-title rule still satisfies D-UI2-12.
    # Post-Wave-5 only .ph .panel-title remains. Test accepts either.
    has_panel_header_pt = (
        ".panel-header .panel-title { font-size: 18px; font-weight: 700;" in src
        and "margin: 0;" in src
    )
    has_ph_pt = False
    if ".ph .panel-title" in src:
        block = src.split(".ph .panel-title", 1)[1].split("}", 1)[0]
        has_ph_pt = (
            "font-size: 18px" in block
            and "font-weight: 700" in block
            and "margin: 0" in block
        )
    assert has_panel_header_pt or has_ph_pt, (
        "D-UI2-12 declarations (font-size: 18px; font-weight: 700; margin: 0) "
        "must exist under either .panel-header .panel-title (pre-Wave-5) or "
        ".ph .panel-title (post-Wave-5). This is the load-bearing contract."
    )


def test_navbar_css_rule_removed() -> None:
    """D-UIF-06: legacy `.navbar { padding: 16px 0 }` rule removed (Wave 3)."""
    src = _read(APP_CSS)
    assert ".navbar {" not in src


def test_chip_chips_css_present() -> None:
    """D-UIF-04: chip + chip.on + chip .n CSS rules present."""
    src = _read(APP_CSS)
    assert ".chips {" in src
    assert ".chip {" in src
    assert ".chip.on {" in src


def test_hero_css_present() -> None:
    """D-UIF-11: hero / hero .num / hero-bar / hero .side rules present."""
    src = _read(APP_CSS)
    assert ".hero {" in src
    assert ".hero .num {" in src
    assert ".hero-bar {" in src
    assert ".hero .side {" in src


def test_kpis_grid_variants_present() -> None:
    """D-UIF-08: .kpis (4-up) + .kpis.five (5-up) grid rules present."""
    src = _read(APP_CSS)
    assert ".kpis {" in src
    assert ".kpis.five {" in src
    assert ".kpi .spark {" in src


def test_pop_dropdown_overrides_present() -> None:
    """D-UIF-03 + Pitfall 3: .pop overrides Bootstrap dropdown-menu min-width."""
    src = _read(APP_CSS)
    assert ".pop {" in src
    assert ".pop-wrap {" in src
    assert ".pop .opt.on {" in src
    # Pitfall 3 — explicit width override against Bootstrap default
    idx = src.find(".pop {")
    block_end = src.find("}", idx)
    block = src[idx:block_end]
    assert "width: 300px" in block, (
        ".pop must explicitly set width 300px to override Bootstrap"
    )


def test_tiny_chip_variants_present() -> None:
    """D-UIF-08 (Discretion): .tiny-chip + 5 variants (.ok .info .warn .neutral .err)."""
    src = _read(APP_CSS)
    assert ".tiny-chip {" in src
    for variant in [
        ".tiny-chip.ok",
        ".tiny-chip.info",
        ".tiny-chip.warn",
        ".tiny-chip.neutral",
        ".tiny-chip.err",
    ]:
        assert variant in src, f"Missing tiny-chip variant: {variant}"


def test_table_sticky_corner_z_index_ladder() -> None:
    """D-UIF-10 + Pitfall 5: sticky-corner z-index ladder (corner=3, thead=2, first-col=1)."""
    src = _read(APP_CSS)
    assert ".table-sticky-corner {" in src
    # The corner cell rule must contain z-index: 3
    assert ".table-sticky-corner thead th:first-child" in src
    idx = src.find(".table-sticky-corner thead th:first-child")
    block_end = src.find("}", idx)
    corner_block = src[idx:block_end]
    assert "z-index: 3" in corner_block, "Corner cell needs z-index: 3 (Pitfall 5 ladder)"
    # First-col body cell must be sticky with z-index: 1
    assert ".table-sticky-corner tbody td:first-child" in src
    idx2 = src.find(".table-sticky-corner tbody td:first-child")
    first_col_block = src[idx2:src.find("}", idx2)]
    assert "position: sticky" in first_col_block
    assert "z-index: 1" in first_col_block


# ----- Wave 1: Google Fonts link in base.html (Pitfall 1) -----

def test_google_fonts_link_present() -> None:
    """Pitfall 1: base.html must load Inter Tight + JetBrains Mono BEFORE tokens.css."""
    src = _read(BASE_HTML)
    assert "fonts.googleapis.com" in src
    assert "Inter+Tight:wght@400;500;600;700;800" in src
    assert "JetBrains+Mono:wght@400;500;600" in src
    # Order: fonts link before tokens.css link
    fonts_idx = src.find("fonts.googleapis.com/css2")
    tokens_idx = src.find("css/tokens.css")
    assert fonts_idx >= 0 and tokens_idx >= 0
    assert fonts_idx < tokens_idx, "Google Fonts link must come BEFORE tokens.css"


# ----- Wave 3: base.html topbar shape -----

def test_base_html_uses_topbar_macro() -> None:
    """D-UIF-06: base.html imports + invokes the topbar macro."""
    src = _read(BASE_HTML)
    assert '{% from "_components/topbar.html" import topbar %}' in src
    assert '{{ topbar(active_tab=active_tab|default("")) }}' in src


def test_base_html_no_legacy_navbar() -> None:
    """D-UIF-06: base.html has no <nav class="navbar"> / navbar-brand / nav-tabs."""
    src = _read(BASE_HTML)
    assert '<nav class="navbar' not in src
    assert "navbar-brand" not in src
    assert "nav nav-tabs" not in src


def test_base_html_loads_chip_toggle_js() -> None:
    """D-UIF-04 + Pitfall 8: base.html loads chip-toggle.js with defer."""
    src = _read(BASE_HTML)
    assert "js/chip-toggle.js" in src
    # chip-toggle.js must be loaded AFTER bootstrap.bundle.min.js
    bs_idx = src.find("bootstrap.bundle.min.js")
    ct_idx = src.find("chip-toggle.js")
    assert bs_idx >= 0 and ct_idx >= 0
    assert bs_idx < ct_idx, "chip-toggle.js must load AFTER bootstrap.bundle.min.js"


def test_base_html_footer_block_preserved() -> None:
    """D-UI2-05 byte-stable: <footer class="site-footer"> with whitespace-strip block."""
    src = _read(BASE_HTML)
    assert '<footer class="site-footer" id="site-footer">' in src
    assert "{%- block footer %}{% endblock footer -%}" in src


# ----- Pitfall 8: chip-toggle.js as SIBLING of popover-search.js -----

def test_chip_toggle_js_sibling_exists() -> None:
    """Pitfall 8: chip-toggle.js exists as a SIBLING (not modification) of popover-search.js."""
    assert CHIP_TOGGLE_JS.exists()
    assert POPOVER_SEARCH_JS.exists()
    chip = _read(CHIP_TOGGLE_JS)
    # Must use the precise selector + boundary check
    assert "closest('.pop .opt')" in chip
    assert "popover-search-root" in chip, "Pitfall 8 boundary marker must be present"


# ----- D-UIF-05: _picker_popover.html byte-stable -----

def test_picker_popover_byte_stable() -> None:
    """D-UIF-05 + D-UI2-09: _picker_popover.html exists and is unmodified.

    We can't easily compare to git HEAD here without subprocess; instead we
    assert its key contract markers exist (catches accidental refactors).
    """
    src = _read(PICKER_POPOVER)
    # Macro definition
    assert "{% macro picker_popover" in src
    # Bootstrap dropdown semantics
    assert 'data-bs-toggle="dropdown"' in src
    # Form-association attribute
    assert 'form="' in src


# ----- D-UIF-08: macro-per-file convention -----

def test_macro_per_file_convention() -> None:
    """D-UIF-08: each _components/*.html file exports ONE {% macro %} matching its filename."""
    expected = {
        "topbar.html": "topbar",
        "page_head.html": "page_head",
        "hero.html": "hero",
        "kpi_card.html": "kpi_card",
        "sparkline.html": "sparkline",
        "date_range_popover.html": "date_range_popover",
        "filters_popover.html": "filters_popover",
    }
    for fname, macro_name in expected.items():
        path = COMPONENTS_DIR / fname
        assert path.exists(), f"Missing partial: {fname}"
        src = path.read_text()
        assert src.count("{% macro ") == 1, (
            f"{fname} must export exactly ONE macro (D-UIF-08); "
            f"got {src.count('{% macro ')}"
        )
        assert "{% macro " + macro_name in src, (
            f"{fname} macro name must match filename (expected {macro_name})"
        )
