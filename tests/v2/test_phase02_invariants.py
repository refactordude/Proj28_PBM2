"""Phase 02 UI shell rewrite invariants — Plan 02-01.

Grep-based policy guards that enforce locked decisions D-UI2-01..D-UI2-05.
These tests run fast (no app startup, no fixtures needed for CSS/HTML checks)
and catch regressions where a later commit accidentally removes a token,
breaks the .shell full-width contract, or removes the sticky-footer block.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app_v2.main import app


REPO = Path(__file__).parent.parent.parent
APP = REPO / "app_v2"
CSS = APP / "static" / "css"
TPL = APP / "templates"

TOKENS_CSS = CSS / "tokens.css"
APP_CSS = CSS / "app.css"
BASE_HTML = TPL / "base.html"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Task 1 — Type-scale tokens in tokens.css (D-UI2-04)
# ---------------------------------------------------------------------------


def test_tokens_declare_type_scale() -> None:
    """D-UI2-04: tokens.css must declare all 4 type-scale custom properties."""
    src = _read(TOKENS_CSS)
    assert "--font-size-logo: 20px" in src, (
        "tokens.css must declare --font-size-logo: 20px (D-UI2-04)"
    )
    assert "--font-size-h1: 28px" in src, (
        "tokens.css must declare --font-size-h1: 28px (D-UI2-04)"
    )
    assert "--font-size-th: 12px" in src, (
        "tokens.css must declare --font-size-th: 12px (D-UI2-04)"
    )
    assert "--font-size-body: 15px" in src, (
        "tokens.css must declare --font-size-body: 15px (D-UI2-04)"
    )


def test_tokens_no_font_size_nav() -> None:
    """D-UI2-04: --font-size-nav must NOT be introduced (nav tabs share --font-size-body)."""
    src = _read(TOKENS_CSS)
    assert "--font-size-nav" not in src, (
        "tokens.css must NOT declare --font-size-nav "
        "(nav tabs share --font-size-body at 700 weight per UI-SPEC §Typography)"
    )


def test_tokens_existing_surface_tokens_preserved() -> None:
    """Existing surface tokens must not be churned by the type-scale addition."""
    src = _read(TOKENS_CSS)
    assert "--bg: #f3f4f6;" in src, "tokens.css must preserve --bg: #f3f4f6;"
    assert "--panel: #ffffff;" in src, "tokens.css must preserve --panel: #ffffff;"
    assert "--line: #eaecef;" in src, "tokens.css must preserve --line: #eaecef;"
    assert "--accent: #3366ff;" in src, "tokens.css must preserve --accent: #3366ff;"
    assert "--radius-panel: 22px;" in src, "tokens.css must preserve --radius-panel: 22px;"


def test_tokens_body_baseline_preserved() -> None:
    """The html, body font-size: 15px baseline must not be rewritten."""
    src = _read(TOKENS_CSS)
    assert "font-size: 15px" in src, (
        "tokens.css must preserve the html,body font-size: 15px baseline "
        "(Plan 02-01 declares --font-size-body token alongside, not instead)"
    )


# ---------------------------------------------------------------------------
# Task 2 — Shell-rewrite CSS rules in app.css (D-UI2-02, D-UI2-03, D-UI2-05)
# ---------------------------------------------------------------------------


def test_shell_full_width() -> None:
    """D-UI2-03: .shell must be reduced to padding: 0 (max-width and margin removed)."""
    src = _read(APP_CSS)
    assert "max-width: 1280px" not in src, (
        "app.css must NOT contain max-width: 1280px (D-UI2-03 full-width content)"
    )
    # The .shell rule's old padding must be gone
    assert "padding: 18px 24px 56px" not in src, (
        "app.css must NOT contain the old .shell padding: 18px 24px 56px"
    )


def test_body_flex_column() -> None:
    """D-UI2-05: app.css must have a body rule with display: flex, flex-direction: column, min-height: 100vh."""
    src = _read(APP_CSS)
    # Regex match with DOTALL to handle multi-line body { ... } block
    pattern = re.compile(
        r"body\s*\{[^}]*display:\s*flex[^}]*flex-direction:\s*column[^}]*min-height:\s*100vh[^}]*\}",
        re.DOTALL,
    )
    assert pattern.search(src), (
        "app.css must contain body { display: flex; flex-direction: column; "
        "min-height: 100vh; } for sticky-in-flow footer (D-UI2-05)"
    )


def test_main_flex_grow() -> None:
    """D-UI2-05: main.container-fluid must have flex: 1 0 auto to grow and push footer down."""
    src = _read(APP_CSS)
    assert "main.container-fluid" in src, (
        "app.css must contain a main.container-fluid rule (D-UI2-05)"
    )
    # Find the main.container-fluid block and check for flex: 1 0 auto
    idx = src.find("main.container-fluid")
    block_end = src.find("}", idx)
    block = src[idx:block_end]
    assert "flex: 1 0 auto" in block, (
        "app.css main.container-fluid must have flex: 1 0 auto (D-UI2-05)"
    )


def test_site_footer_rule() -> None:
    """D-UI2-05: app.css must contain a .site-footer rule with required properties."""
    src = _read(APP_CSS)
    # Search for the CSS selector form (with opening brace), not the comment mention
    rule_pattern = re.compile(r"\.site-footer\s*\{", re.MULTILINE)
    match = rule_pattern.search(src)
    assert match, (
        "app.css must contain a .site-footer { rule (D-UI2-05)"
    )
    idx = match.start()
    block_end = src.find("}", idx)
    block = src[idx:block_end]
    assert "flex-shrink: 0" in block, (
        ".site-footer must have flex-shrink: 0 (D-UI2-05)"
    )
    assert "background: var(--panel)" in block, (
        ".site-footer must have background: var(--panel) (D-UI2-05)"
    )
    assert "border-top: 1px solid var(--line)" in block, (
        ".site-footer must have border-top: 1px solid var(--line) (D-UI2-05)"
    )
    assert "min-height: 48px" in block, (
        ".site-footer must have min-height: 48px (D-UI2-05)"
    )


def test_navbar_padding_override() -> None:
    """D-UI2-02: app.css must contain a .navbar rule with padding-top: 16px and padding-bottom: 16px."""
    src = _read(APP_CSS)
    # There must be a .navbar rule (our new one, not the Bootstrap base)
    # that has both padding-top: 16px and padding-bottom: 16px
    assert "padding-top: 16px" in src, (
        "app.css must contain padding-top: 16px for taller nav bar (D-UI2-02)"
    )
    assert "padding-bottom: 16px" in src, (
        "app.css must contain padding-bottom: 16px for taller nav bar (D-UI2-02)"
    )
    # They must be inside a .navbar selector block
    idx = src.find(".navbar")
    assert idx >= 0, "app.css must contain a .navbar rule (D-UI2-02)"
    block_end = src.find("}", idx)
    block = src[idx:block_end]
    assert "padding-top: 16px" in block, (
        ".navbar rule must contain padding-top: 16px (D-UI2-02)"
    )
    assert "padding-bottom: 16px" in block, (
        ".navbar rule must contain padding-bottom: 16px (D-UI2-02)"
    )


def test_panel_title_rule() -> None:
    """D-UI2-12: app.css must contain .panel-header .panel-title with 18px/700."""
    src = _read(APP_CSS)
    assert ".panel-header .panel-title" in src, (
        "app.css must contain .panel-header .panel-title rule (D-UI2-12)"
    )
    idx = src.find(".panel-header .panel-title")
    block_end = src.find("}", idx)
    block = src[idx:block_end]
    assert "font-size: 18px" in block, (
        ".panel-header .panel-title must have font-size: 18px (D-UI2-12)"
    )
    assert "font-weight: 700" in block, (
        ".panel-header .panel-title must have font-weight: 700 (D-UI2-12)"
    )
    assert "margin: 0" in block, (
        ".panel-header .panel-title must have margin: 0 (D-UI2-12)"
    )


def test_overflow_visible_safety_net_preserved() -> None:
    """260430-wzg: app.css must preserve the .panel.overview-filter-bar self-match selector."""
    src = _read(APP_CSS)
    assert ".panel.overview-filter-bar" in src, (
        "app.css must keep the .panel.overview-filter-bar self-match selector "
        "(260430-wzg safety net per CONTEXT.md canonical_refs)"
    )
    assert "overflow: visible" in src, (
        "app.css must retain 'overflow: visible' for the filter-bar panels"
    )


# ---------------------------------------------------------------------------
# Task 3 — Footer block wired into base.html (D-UI2-05, D-UI2-01)
# ---------------------------------------------------------------------------


def test_base_html_has_footer_block() -> None:
    """D-UI2-05: base.html must contain the site-footer element with the footer block."""
    src = _read(BASE_HTML)
    assert '<footer class="site-footer" id="site-footer">' in src, (
        'base.html must contain <footer class="site-footer" id="site-footer"> (D-UI2-05)'
    )
    assert "{% block footer %}{% endblock footer %}" in src, (
        "base.html must contain {% block footer %}{% endblock footer %} inside the site-footer (D-UI2-05)"
    )
    # Footer must appear before </body>
    footer_idx = src.find('<footer class="site-footer"')
    body_close_idx = src.find("</body>")
    assert footer_idx < body_close_idx, (
        "The <footer class=\"site-footer\"> must appear before </body> in base.html"
    )
    # </footer> must also appear before </body>
    footer_close_idx = src.find("</footer>")
    assert footer_close_idx < body_close_idx, (
        "</footer> must appear before </body> in base.html"
    )


def test_base_html_nav_left_aligned() -> None:
    """D-UI2-01: nav tabs must NOT have ms-auto on the <ul> (already left-aligned)."""
    src = _read(BASE_HTML)
    # Find the nav-tabs ul
    ul_start = src.find('class="nav nav-tabs')
    assert ul_start >= 0, "base.html must contain a nav-tabs ul"
    # Check the same line/opening tag for ms-auto
    ul_end = src.find(">", ul_start)
    ul_tag = src[ul_start:ul_end]
    assert "ms-auto" not in ul_tag, (
        "The nav-tabs <ul> must NOT have ms-auto (D-UI2-01 — tabs are left-aligned)"
    )


def test_full_page_renders_with_footer() -> None:
    """D-UI2-05: GET /browse must return 200 with the site-footer element."""
    client = TestClient(app)
    r = client.get("/browse")
    assert r.status_code == 200
    assert '<footer class="site-footer"' in r.text, (
        "GET /browse response must contain <footer class=\"site-footer\" (D-UI2-05)"
    )


def test_overview_page_inherits_footer() -> None:
    """D-UI2-05: GET /overview (root) must return 200 with the site-footer element."""
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert '<footer class="site-footer"' in r.text, (
        "GET / (overview) response must contain <footer class=\"site-footer\" (D-UI2-05)"
    )
