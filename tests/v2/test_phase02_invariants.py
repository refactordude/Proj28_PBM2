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


# ---------------------------------------------------------------------------
# Plan 02-02 — Browse count caption migration into footer (D-UI2-06)
# Tests 16-21
# ---------------------------------------------------------------------------

BROWSE_HTML = TPL / "browse" / "index.html"


def test_browse_panel_header_no_count() -> None:
    """Test 16: panel-header must NOT contain the ms-auto d-flex wrapper (it was deleted in Edit A)."""
    src = _read(BROWSE_HTML)
    assert 'class="ms-auto d-flex align-items-center gap-3"' not in src, (
        'browse/index.html must NOT contain class="ms-auto d-flex align-items-center gap-3" '
        "(the count wrapper in panel-header was deleted — D-UI2-06 Edit A)"
    )


def test_browse_footer_block_carries_count() -> None:
    """Test 17: browse/index.html must have {% block footer %} containing grid-count, n_rows, n_cols, &times;."""
    src = _read(BROWSE_HTML)
    assert "{% block footer %}" in src, (
        "browse/index.html must contain {% block footer %} (D-UI2-06 Edit B)"
    )
    assert "{% endblock footer %}" in src, (
        "browse/index.html must contain {% endblock footer %} (D-UI2-06 Edit B)"
    )
    # Check that inside the footer block the count span and required expressions are present
    footer_start = src.find("{% block footer %}")
    footer_end = src.find("{% endblock footer %}")
    assert footer_start < footer_end, "{% block footer %} must come before {% endblock footer %}"
    footer_region = src[footer_start:footer_end]
    assert 'id="grid-count"' in footer_region, (
        'browse/index.html {% block footer %} must contain id="grid-count" (D-UI2-06)'
    )
    assert "vm.n_rows" in footer_region, (
        "browse/index.html {% block footer %} must contain vm.n_rows (D-UI2-06)"
    )
    assert "vm.n_cols" in footer_region, (
        "browse/index.html {% block footer %} must contain vm.n_cols (D-UI2-06)"
    )
    assert "&times;" in footer_region, (
        "browse/index.html {% block footer %} must contain &times; (D-UI2-06)"
    )


def test_browse_grid_count_receiver_emitter_tag_alignment() -> None:
    """Test 17b (W7): receiver and emitter span opening tags must be consistent."""
    src = _read(BROWSE_HTML)
    receiver_tag = '<span id="grid-count" class="text-muted small" aria-live="polite">'
    emitter_tag = '<span id="grid-count" hx-swap-oob="true" class="text-muted small" aria-live="polite">'
    assert src.count(receiver_tag) == 1, (
        f"browse/index.html must contain exactly 1 occurrence of the receiver tag: {receiver_tag!r} "
        "(inside {% block footer %}) — W7 tag alignment"
    )
    assert src.count(emitter_tag) == 1, (
        f"browse/index.html must contain exactly 1 occurrence of the OOB emitter tag: {emitter_tag!r} "
        "(inside {% block count_oob %}) — W7 tag alignment"
    )


def test_browse_count_oob_unchanged() -> None:
    """Test 18: {% block count_oob %} must remain byte-stable with hx-swap-oob on #grid-count."""
    src = _read(BROWSE_HTML)
    assert 'id="grid-count" hx-swap-oob="true"' in src, (
        'browse/index.html must contain id="grid-count" hx-swap-oob="true" in count_oob block (unchanged)'
    )
    # Verify there is exactly ONE occurrence of hx-swap-oob="true" paired with id="grid-count"
    assert src.count('id="grid-count" hx-swap-oob="true"') == 1, (
        'browse/index.html must have exactly 1 occurrence of id="grid-count" hx-swap-oob="true"'
    )
    # The count_oob block must still have the vm.is_empty_selection guard
    count_oob_start = src.find("{% block count_oob %}")
    count_oob_end = src.find("{% endblock count_oob %}")
    assert count_oob_start >= 0 and count_oob_end > count_oob_start, (
        "{% block count_oob %} must still exist in browse/index.html (byte-stable)"
    )
    count_oob_region = src[count_oob_start:count_oob_end]
    assert "vm.is_empty_selection" in count_oob_region, (
        "{% block count_oob %} must still contain vm.is_empty_selection guard (byte-stable)"
    )


def test_get_browse_renders_count_in_footer() -> None:
    """Test 19: GET /browse — #grid-count must be inside the <footer class='site-footer'>."""
    client = TestClient(app)
    r = client.get("/browse")
    assert r.status_code == 200
    assert '<footer class="site-footer"' in r.text, (
        "GET /browse must render the site-footer element (D-UI2-05)"
    )
    footer_start = r.text.find('<footer class="site-footer"')
    assert footer_start >= 0
    footer_end = r.text.find("</footer>", footer_start)
    assert footer_end > footer_start, "site-footer must have a closing tag"
    footer_region = r.text[footer_start:footer_end]
    assert 'id="grid-count"' in footer_region, (
        'GET /browse response: id="grid-count" must be inside the <footer class="site-footer"> '
        "(D-UI2-06 — count migrated from panel-header to footer)"
    )


def test_post_browse_grid_emits_count_oob() -> None:
    """Test 20: POST /browse/grid must emit id="grid-count" with hx-swap-oob="true" in OOB fragment."""
    client = TestClient(app)
    # POST with empty form — vm will be empty-selection, but count_oob block is always emitted
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = client.post("/browse/grid", content="platforms=&params=&swap=0", headers=headers)
    assert r.status_code == 200, f"POST /browse/grid returned {r.status_code}"
    assert 'id="grid-count"' in r.text, (
        'POST /browse/grid response must contain id="grid-count" (OOB count fragment)'
    )
    assert 'hx-swap-oob="true"' in r.text, (
        'POST /browse/grid response must contain hx-swap-oob="true" (OOB swap mechanic intact)'
    )


def test_browse_panel_header_byte_stable_otherwise() -> None:
    """Test 21: panel-header must still contain <b>Browse</b> and Pivot grid tag."""
    src = _read(BROWSE_HTML)
    assert "<b>Browse</b>" in src, (
        "browse/index.html panel-header must still contain <b>Browse</b> (byte-stable)"
    )
    assert '<span class="tag">Pivot grid</span>' in src, (
        'browse/index.html panel-header must still contain <span class="tag">Pivot grid</span> '
        "(byte-stable)"
    )


# ---------------------------------------------------------------------------
# Plan 02-03 Task 1 — Overview filter bar CSS flex layout (D-UI2-08)
# Tests 22-25
# ---------------------------------------------------------------------------


def test_overview_filter_bar_flex_layout() -> None:
    """Test 22: .overview-filter-bar rule must have display:flex, align-items:center,
    gap:8px, flex-wrap:wrap, border-bottom:1px solid var(--line), padding:16px 24px 0."""
    src = _read(APP_CSS)
    # Find the .overview-filter-bar rule selector (not self-match .panel.overview-filter-bar)
    pattern = re.compile(r"^\.overview-filter-bar\s*\{", re.MULTILINE)
    match = pattern.search(src)
    assert match, "app.css must contain a standalone .overview-filter-bar { rule (D-UI2-08)"
    idx = match.start()
    block_end = src.find("}", idx)
    block = src[idx:block_end]
    assert "display: flex" in block, (
        ".overview-filter-bar must have display: flex (D-UI2-08)"
    )
    assert "align-items: center" in block, (
        ".overview-filter-bar must have align-items: center (D-UI2-08)"
    )
    assert "gap: 8px" in block, (
        ".overview-filter-bar must have gap: 8px (D-UI2-08)"
    )
    assert "flex-wrap: wrap" in block, (
        ".overview-filter-bar must have flex-wrap: wrap (D-UI2-08)"
    )
    assert "border-bottom: 1px solid var(--line)" in block, (
        ".overview-filter-bar must have border-bottom: 1px solid var(--line) (D-UI2-08)"
    )
    assert "padding: 16px 24px 0" in block, (
        ".overview-filter-bar must have padding: 16px 24px 0 (D-UI2-08)"
    )


def test_overview_filter_bar_old_padding_gone() -> None:
    """Test 23: app.css must NOT contain the old padding: 0 26px in the .overview-filter-bar rule."""
    src = _read(APP_CSS)
    assert "padding: 0 26px" not in src, (
        "app.css must NOT contain 'padding: 0 26px' (old .overview-filter-bar rule body replaced)"
    )


def test_browse_filter_bar_byte_stable() -> None:
    """Test 24: app.css .browse-filter-bar must still have padding:12px 26px 0 and border-bottom."""
    src = _read(APP_CSS)
    pattern = re.compile(r"^\.browse-filter-bar\s*\{", re.MULTILINE)
    match = pattern.search(src)
    assert match, "app.css must contain a .browse-filter-bar { rule (Browse is byte-stable)"
    idx = match.start()
    block_end = src.find("}", idx)
    block = src[idx:block_end]
    assert "padding: 12px 26px 0" in block, (
        ".browse-filter-bar must still have padding: 12px 26px 0 (byte-stable)"
    )
    assert "border-bottom: 1px solid var(--line)" in block, (
        ".browse-filter-bar must still have border-bottom: 1px solid var(--line) (byte-stable)"
    )


def test_overflow_safety_net_still_present() -> None:
    """Test 25: app.css must still contain .panel.overview-filter-bar paired with overflow:visible."""
    src = _read(APP_CSS)
    assert ".panel.overview-filter-bar" in src, (
        "app.css must preserve .panel.overview-filter-bar self-match selector "
        "(260430-wzg safety net per CONTEXT.md canonical_refs)"
    )
    # Find the multi-selector block that contains .panel.overview-filter-bar and overflow: visible
    ov_idx = src.find(".panel.overview-filter-bar")
    assert ov_idx >= 0
    # The overflow: visible must appear after this selector (within the same rule block)
    block_end = src.find("}", ov_idx)
    block = src[ov_idx:block_end]
    assert "overflow: visible" in block, (
        ".panel.overview-filter-bar must be in a rule with overflow: visible (260430-wzg)"
    )


# ---------------------------------------------------------------------------
# Plan 02-03 Task 2 — Restructure overview/_filter_bar.html (D-UI2-07/08/09/10)
# Tests 26-31
# ---------------------------------------------------------------------------

OVERVIEW_FILTER_BAR_HTML = TPL / "overview" / "_filter_bar.html"


def test_overview_filter_bar_no_panel_class() -> None:
    """Test 26: _filter_bar.html must NOT contain class="overview-filter-bar panel" (D-UI2-07)."""
    src = _read(OVERVIEW_FILTER_BAR_HTML)
    assert 'class="overview-filter-bar panel"' not in src, (
        'overview/_filter_bar.html must NOT contain class="overview-filter-bar panel" '
        "(D-UI2-07 — .panel class removed from wrapper; nested inside outer .panel in index.html)"
    )


def test_overview_filter_bar_picker_macro_byte_stable() -> None:
    """Test 27: _filter_bar.html must contain the browse picker_popover import exactly once (D-UI2-09)."""
    src = _read(OVERVIEW_FILTER_BAR_HTML)
    import_line = '{% from "browse/_picker_popover.html" import picker_popover %}'
    assert src.count(import_line) == 1, (
        f"overview/_filter_bar.html must contain exactly 1 occurrence of {import_line!r} "
        "(D-UI2-09 — no macro fork)"
    )


def test_overview_filter_form_flex() -> None:
    """Test 28: <form id="overview-filter-form"> must have d-flex, align-items-center,
    gap-2, flex-wrap, and w-100 classes (D-UI2-08 — form is the flex container)."""
    src = _read(OVERVIEW_FILTER_BAR_HTML)
    assert "d-flex" in src, (
        "overview/_filter_bar.html form must have class d-flex (D-UI2-08)"
    )
    assert "align-items-center" in src, (
        "overview/_filter_bar.html form must have class align-items-center (D-UI2-08)"
    )
    assert "gap-2" in src, (
        "overview/_filter_bar.html form must have class gap-2 (D-UI2-08)"
    )
    assert "flex-wrap" in src, (
        "overview/_filter_bar.html form must have class flex-wrap (D-UI2-08)"
    )
    assert "w-100" in src, (
        "overview/_filter_bar.html form must have class w-100 (D-UI2-08)"
    )


def test_overview_clear_all_ms_auto() -> None:
    """Test 29: the Clear all link must have ms-auto class (right-aligned, D-UI2-10)."""
    src = _read(OVERVIEW_FILTER_BAR_HTML)
    assert "ms-auto" in src, (
        "overview/_filter_bar.html Clear all link must have ms-auto class (D-UI2-10)"
    )
    # Specifically the Clear all anchor must carry ms-auto (not just some other element)
    assert "ms-auto btn btn-link btn-sm" in src, (
        "overview/_filter_bar.html Clear all link class must contain 'ms-auto btn btn-link btn-sm' "
        "(D-UI2-10 — ms-auto pushes it to far right of flex row)"
    )


def test_overview_filter_bar_six_picker_calls() -> None:
    """Test 30: _filter_bar.html must contain exactly 6 occurrences of picker_popover( (byte-stable)."""
    src = _read(OVERVIEW_FILTER_BAR_HTML)
    count = src.count("picker_popover(")
    assert count == 6, (
        f"overview/_filter_bar.html must contain exactly 6 picker_popover( calls, found {count} "
        "(D-UI2-09 — 6 filters byte-stable; import line does not count as it lacks opening paren)"
    )


def test_overview_filter_bar_form_id_preserved() -> None:
    """Test 31: <form id="overview-filter-form"> must appear exactly once (the form element tag itself)."""
    src = _read(OVERVIEW_FILTER_BAR_HTML)
    # Use '<form id=' prefix to avoid matching picker_popover's form_id="overview-filter-form" params
    assert src.count('<form id="overview-filter-form"') == 1, (
        'overview/_filter_bar.html must contain exactly 1 <form id="overview-filter-form" element '
        "(form-association anchor must be preserved; form_id= picker params are a different attribute)"
    )


# ---------------------------------------------------------------------------
# Plan 02-03 Task 3 — Restructure overview/index.html (D-UI2-07/11/12)
# Tests 32-40 (and 35b)
# ---------------------------------------------------------------------------

OVERVIEW_INDEX_HTML = TPL / "overview" / "index.html"


def test_overview_index_no_page_head() -> None:
    """Test 32: overview/index.html must NOT contain <div class="page-head (D-UI2-12)."""
    src = _read(OVERVIEW_INDEX_HTML)
    assert '<div class="page-head' not in src, (
        'overview/index.html must NOT contain <div class="page-head '
        "(D-UI2-12 — standalone outside-panel h1 wrapper removed)"
    )


def test_overview_index_single_panel() -> None:
    """Test 33: overview/index.html must contain exactly ONE <div class="panel"> (D-UI2-07)."""
    src = _read(OVERVIEW_INDEX_HTML)
    assert src.count('<div class="panel">') == 1, (
        'overview/index.html must contain exactly 1 <div class="panel"> '
        f"(found {src.count('<div class=\"panel\">')}; D-UI2-07 single-panel layout)"
    )


def test_overview_index_h1_inside_panel() -> None:
    """Test 34: overview/index.html must contain <h1 class="panel-title">Joint Validation</h1>
    positioned inside the outer .panel (D-UI2-12)."""
    src = _read(OVERVIEW_INDEX_HTML)
    assert '<h1 class="panel-title">Joint Validation</h1>' in src, (
        'overview/index.html must contain <h1 class="panel-title">Joint Validation</h1> (D-UI2-12)'
    )
    panel_idx = src.find('<div class="panel">')
    h1_idx = src.find('<h1 class="panel-title">Joint Validation</h1>')
    assert panel_idx >= 0 and h1_idx > panel_idx, (
        "<h1 class='panel-title'>Joint Validation</h1> must appear AFTER the outer "
        '<div class="panel"> opener — i.e. inside the panel (D-UI2-12)'
    )


def test_overview_index_count_in_panel_header() -> None:
    """Test 35: <span id="overview-count"> must be inside <div class="panel-header" (D-UI2-11)."""
    src = _read(OVERVIEW_INDEX_HTML)
    assert '<span id="overview-count"' in src, (
        'overview/index.html must contain <span id="overview-count" (D-UI2-11)'
    )
    panel_header_idx = src.find('<div class="panel-header"')
    count_idx = src.find('<span id="overview-count"')
    # count span (receiver) in panel-header must appear after panel-header opens
    assert panel_header_idx >= 0, (
        'overview/index.html must contain <div class="panel-header" (D-UI2-11)'
    )
    assert count_idx > panel_header_idx, (
        '<span id="overview-count" must appear after <div class="panel-header"> opener (D-UI2-11)'
    )
    # The receiver span must carry ms-auto for right-alignment
    receiver_src = src[count_idx:src.find(">", count_idx)]
    assert "ms-auto" in receiver_src, (
        '<span id="overview-count" in panel-header must carry ms-auto class (D-UI2-11)'
    )


def test_overview_count_receiver_emitter_tags_aligned() -> None:
    """Test 35b (W1): both overview-count occurrences must be <span> tags (not <div>).
    HTMX outerHTML OOB replaces the whole element including its tag; receiver and
    emitter must use the same element type to avoid tag mismatch in the DOM."""
    src = _read(OVERVIEW_INDEX_HTML)
    assert src.count('<span id="overview-count"') == 2, (
        'overview/index.html must contain exactly 2 occurrences of <span id="overview-count" '
        f"(found {src.count('<span id=\"overview-count\"')}; "
        "one in panel-header receiver + one in count_oob emitter; both must be <span> — W1)"
    )


def test_overview_index_count_oob_block_emits_span() -> None:
    """Test 36: the {% block count_oob %} block must emit <span id="overview-count" hx-swap-oob="true"
    (was <div>; now <span> to match the panel-header receiver shape)."""
    src = _read(OVERVIEW_INDEX_HTML)
    count_oob_start = src.find("{% block count_oob %}")
    count_oob_end = src.find("{% endblock %}", count_oob_start)
    if count_oob_end < 0:
        count_oob_end = src.find("{% endblock count_oob %}", count_oob_start)
    assert count_oob_start >= 0, "overview/index.html must contain {% block count_oob %}"
    assert count_oob_end > count_oob_start, "{% block count_oob %} must have a closing endblock"
    oob_region = src[count_oob_start:count_oob_end]
    assert '<span id="overview-count" hx-swap-oob="true"' in oob_region, (
        '{% block count_oob %} must emit <span id="overview-count" hx-swap-oob="true" '
        "(changed from <div> to match panel-header receiver shape — Test 36)"
    )


def test_overview_index_filter_bar_inside_panel() -> None:
    """Test 37: the {% include "overview/_filter_bar.html" %} must be positioned
    after panel-header and before the overview-grid div (D-UI2-07)."""
    src = _read(OVERVIEW_INDEX_HTML)
    include_line = '{% include "overview/_filter_bar.html" %}'
    assert include_line in src, (
        'overview/index.html must contain {% include "overview/_filter_bar.html" %}'
    )
    panel_header_idx = src.find('<div class="panel-header"')
    include_idx = src.find(include_line)
    grid_idx = src.find('<div id="overview-grid"')
    assert panel_header_idx < include_idx, (
        "Filter bar include must appear AFTER panel-header (D-UI2-07)"
    )
    assert include_idx < grid_idx, (
        "Filter bar include must appear BEFORE #overview-grid div (D-UI2-07)"
    )


def test_overview_index_grid_block_macro_inside_block() -> None:
    """Test 38: sortable_th macro definition must be inside {% block grid %} (Pitfall 8)."""
    src = _read(OVERVIEW_INDEX_HTML)
    grid_block_idx = src.find("{% block grid %}")
    macro_idx = src.find("{% macro sortable_th(col, label) %}")
    assert grid_block_idx >= 0, "overview/index.html must contain {% block grid %}"
    assert macro_idx >= 0, "overview/index.html must contain {% macro sortable_th(col, label) %}"
    assert macro_idx > grid_block_idx, (
        "{% macro sortable_th(col, label) %} must be INSIDE {% block grid %} (Pitfall 8 — "
        "jinja2-fragments block_names=['grid', ...] loses macros defined outside the block)"
    )


def test_get_overview_renders_panel_header_with_h1() -> None:
    """Test 39: GET /overview returns 200 with h1 panel-title and overview-count in body."""
    client = TestClient(app)
    r = client.get("/overview")
    assert r.status_code == 200, f"GET /overview returned {r.status_code}"
    assert '<h1 class="panel-title">Joint Validation</h1>' in r.text, (
        'GET /overview response must contain <h1 class="panel-title">Joint Validation</h1> (D-UI2-12)'
    )
    assert 'id="overview-count"' in r.text, (
        'GET /overview response must contain id="overview-count" (D-UI2-11)'
    )


def test_post_overview_grid_emits_count_oob_span() -> None:
    """Test 40: POST /overview/grid returns 200 with overview-count and hx-swap-oob="true"."""
    client = TestClient(app)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = client.post(
        "/overview/grid",
        content="sort=status&order=asc",
        headers=headers,
    )
    assert r.status_code == 200, f"POST /overview/grid returned {r.status_code}"
    assert 'id="overview-count"' in r.text, (
        'POST /overview/grid response must contain id="overview-count" (OOB count fragment)'
    )
    assert 'hx-swap-oob="true"' in r.text, (
        'POST /overview/grid response must contain hx-swap-oob="true" (OOB swap mechanic)'
    )
