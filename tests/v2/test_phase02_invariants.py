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


# Phase 04 D-UIF-06: test_navbar_padding_override removed. The .navbar
# CSS rule it asserted (D-UI2-02) was deleted because the legacy
# <nav class="navbar"> markup it targeted was replaced by the Helix
# .topbar primitive. The .topbar rule itself is invariant-tested in
# tests/v2/test_phase04_uif_invariants.py (Wave 4).


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
    # 260502-ui: whitespace-strip markers `{%- ... -%}` keep the empty case
    # element-only so `.site-footer:empty { display: none }` matches when
    # no per-page extension overrides the block.
    assert "{%- block footer %}{% endblock footer -%}" in src, (
        "base.html must contain {%- block footer %}{% endblock footer -%} inside the site-footer "
        "(D-UI2-05 + 260502-ui whitespace strip)"
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


# Phase 04 D-UIF-06: test_base_html_nav_left_aligned removed. The
# legacy <ul class="nav nav-tabs"> it asserted on was replaced by
# the .topbar > .tabs flex layout in _components/topbar.html. Tabs
# are left-aligned by structure (between .brand and .top-right);
# Wave 4 invariant tests pin the topbar shape if needed.


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
    """Test 17 (260502-ui revision): browse/index.html must carry the grid-count
    receiver in a `.panel-footer` div inside the panel — NOT in `block footer`.

    Rationale: the prior global `.site-footer` band rendered as a square
    block disconnected from the rounded panel above; user feedback asked
    for a unified rounded-card silhouette. Moving the count receiver into
    a `.panel-footer` lets the panel's `border-radius` + `overflow:hidden`
    close the bottom corners cleanly. The OOB swap mechanism is preserved
    because the same `#grid-count` id stays as the merge target.
    """
    src = _read(BROWSE_HTML)
    # Locate the .panel-footer div and assert it carries the count.
    panel_footer_idx = src.find('<div class="panel-footer">')
    assert panel_footer_idx >= 0, (
        'browse/index.html must contain <div class="panel-footer"> '
        "(260502-ui — count receiver moved out of the global site-footer)"
    )
    # The .panel-footer must contain id="grid-count" + the required expressions.
    panel_footer_end = src.find("</div>", panel_footer_idx)
    pf_region = src[panel_footer_idx:panel_footer_end]
    assert 'id="grid-count"' in pf_region, (
        'browse/index.html .panel-footer must contain id="grid-count" '
        "(260502-ui — receiver moved from block footer to panel-footer)"
    )
    assert "vm.n_rows" in pf_region, "browse/index.html .panel-footer must contain vm.n_rows"
    assert "vm.n_cols" in pf_region, "browse/index.html .panel-footer must contain vm.n_cols"
    assert "&times;" in pf_region, "browse/index.html .panel-footer must contain &times;"


def test_browse_grid_count_receiver_emitter_tag_alignment() -> None:
    """Test 17b (W7): receiver and emitter span opening tags must be consistent.
    260502-ui: receiver now lives inside `.panel-footer` instead of `block footer`."""
    src = _read(BROWSE_HTML)
    receiver_tag = '<span id="grid-count" class="text-muted small" aria-live="polite">'
    emitter_tag = '<span id="grid-count" hx-swap-oob="true" class="text-muted small" aria-live="polite">'
    assert src.count(receiver_tag) == 1, (
        f"browse/index.html must contain exactly 1 occurrence of the receiver tag: {receiver_tag!r} "
        "(inside .panel-footer) — W7 tag alignment"
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


def test_get_browse_renders_count_in_panel_footer() -> None:
    """Test 19 (260502-ui revision): GET /browse — #grid-count must be inside
    a `.panel-footer` div, not the global `<footer class='site-footer'>` band.

    The panel-footer lives inside the rounded `.panel`, so the panel's
    border-radius + overflow:hidden close the bottom corners cleanly.
    The site-footer is hidden via CSS `:empty` rule when no page emits
    block footer content. Mechanism: same #grid-count id, same OOB merge.
    """
    client = TestClient(app)
    r = client.get("/browse")
    assert r.status_code == 200
    # Locate the .panel-footer in rendered HTML
    pf_start = r.text.find('<div class="panel-footer">')
    assert pf_start >= 0, (
        'GET /browse must render <div class="panel-footer"> (260502-ui — '
        "count receiver moved out of the global site-footer band)"
    )
    pf_end = r.text.find("</div>", pf_start)
    assert pf_end > pf_start, ".panel-footer must have a closing tag"
    pf_region = r.text[pf_start:pf_end]
    assert 'id="grid-count"' in pf_region, (
        'GET /browse: id="grid-count" must be inside <div class="panel-footer"> '
        "(260502-ui — receiver moved out of site-footer)"
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


# ---------------------------------------------------------------------------
# Plan 02-04 — JV pagination: filter bar, template blocks, partial, doc sync
# Tests 41-45, 45b-e
# ---------------------------------------------------------------------------

OVERVIEW_PAGINATION_HTML = TPL / "overview" / "_pagination.html"
UI_SPEC_MD = Path(__file__).parent.parent.parent / ".planning" / "phases" / \
    "02-ui-shell-rewrite-browse-footer-joint-validation-layout-parit" / "02-UI-SPEC.md"


def test_overview_filter_bar_has_hidden_page_input() -> None:
    """Test 41 (B4): _filter_bar.html must contain hidden page input that resets to page 1."""
    src = _read(OVERVIEW_FILTER_BAR_HTML)
    assert '<input type="hidden" name="page" value="1">' in src, (
        'overview/_filter_bar.html must contain <input type="hidden" name="page" value="1"> '
        "(filter changes must reset page to 1 — D-UI2-13)"
    )


def test_overview_index_has_pagination_oob_block() -> None:
    """Test 42: overview/index.html must contain {% block pagination_oob %} with
    id="overview-pagination" and hx-swap-oob="true" wrapper."""
    src = _read(OVERVIEW_INDEX_HTML)
    assert "{% block pagination_oob %}" in src, (
        "overview/index.html must contain {% block pagination_oob %} (Phase 02 Plan 02-04)"
    )
    # The OOB wrapper must carry hx-swap-oob="true"
    oob_start = src.find("{% block pagination_oob %}")
    oob_end = src.find("{% endblock pagination_oob %}")
    assert oob_start >= 0 and oob_end > oob_start, (
        "{% block pagination_oob %} must have a matching {% endblock pagination_oob %}"
    )
    oob_region = src[oob_start:oob_end]
    assert 'id="overview-pagination"' in oob_region, (
        'block pagination_oob must contain a div with id="overview-pagination"'
    )
    assert 'hx-swap-oob="true"' in oob_region, (
        'block pagination_oob wrapper must carry hx-swap-oob="true" (OOB merge target)'
    )


def test_overview_index_panel_footer_carries_pagination() -> None:
    """Test 43 (260502-ui revision): overview/index.html must carry the
    pagination receiver in a `.panel-footer` div inside the panel — NOT in
    `block footer`. Same #overview-pagination id is preserved as the OOB
    merge target (block pagination_oob still emits the OOB wrapper)."""
    src = _read(OVERVIEW_INDEX_HTML)
    pf_idx = src.find('<div class="panel-footer">')
    assert pf_idx >= 0, (
        'overview/index.html must contain <div class="panel-footer"> '
        "(260502-ui — pagination receiver moved out of the global site-footer)"
    )
    pf_end = src.find("</div>", pf_idx)
    # The panel-footer block must contain a wrapper carrying the canonical id.
    pf_region = src[pf_idx:pf_end + len("</div>")]
    assert 'id="overview-pagination"' in pf_region, (
        'overview/index.html .panel-footer must contain id="overview-pagination" '
        "(initial-render receiver for the pagination control — 260502-ui)"
    )


def test_sortable_th_macro_emits_page_1() -> None:
    """Test 44: sortable_th macro must include "page": "1" in hx-vals so sort resets to page 1."""
    src = _read(OVERVIEW_INDEX_HTML)
    assert '"page": "1"' in src, (
        'overview/index.html sortable_th macro hx-vals must include \'"page": "1"\' '
        "(sort click must reset page to 1 — D-UI2-13)"
    )


def test_pagination_uses_page_links_loop() -> None:
    """Test 45 (B5 form): _pagination.html iterates vm.page_links via {% for pl in vm.page_links %}
    and accesses pl.label / pl.num (NOT tuple-unpacking)."""
    src = _read(OVERVIEW_PAGINATION_HTML)
    assert "{% for pl in vm.page_links %}" in src, (
        'overview/_pagination.html must contain {% for pl in vm.page_links %} (B3 PageLink iteration)'
    )
    assert "pl.label" in src, (
        "overview/_pagination.html must access pl.label (PageLink attribute — B3)"
    )
    assert "pl.num" in src, (
        "overview/_pagination.html must access pl.num (PageLink attribute — B3)"
    )
    # Must NOT use tuple-unpacking syntax
    assert "for label, num in vm.page_links" not in src, (
        "overview/_pagination.html must NOT use tuple-unpacking 'for label, num in vm.page_links' "
        "(B3 — PageLink submodel, not tuple)"
    )


def test_pagination_partial_included_twice() -> None:
    """Test 45b (B5): overview/index.html must include _pagination.html exactly twice
    (once in `.panel-footer` initial render, once in block pagination_oob OOB —
    single source of truth, 260502-ui revision: panel-footer replaces block footer)."""
    src = _read(OVERVIEW_INDEX_HTML)
    include_count = src.count('{% include "overview/_pagination.html" %}')
    assert include_count == 2, (
        f'overview/index.html must include "overview/_pagination.html" exactly 2 times '
        f"(panel-footer + pagination_oob), found {include_count} (B5 — single source of truth)"
    )


def test_pagination_partial_size_sanity() -> None:
    """Test 45c (B5): _pagination.html must be ≤ 60 lines (single-source-of-truth sanity)."""
    line_count = len(_read(OVERVIEW_PAGINATION_HTML).splitlines())
    assert line_count <= 60, (
        f"overview/_pagination.html must be ≤ 60 lines (B5 size sanity), found {line_count} lines"
    )


def test_overview_index_count_id_count() -> None:
    """Test 45d (W2): id="overview-count" must appear exactly twice in overview/index.html
    (panel-header receiver + count_oob emitter). The footer must NOT carry the count."""
    src = _read(OVERVIEW_INDEX_HTML)
    count = src.count('id="overview-count"')
    assert count == 2, (
        f'overview/index.html must contain exactly 2 occurrences of id="overview-count" '
        f"(panel-header receiver + count_oob emitter), found {count} "
        "(W2 — footer carries pagination ONLY, not count)"
    )


def test_pagination_oob_wrapper_carries_oob_attr() -> None:
    """Test 45e (B5): pagination_oob wrapper must carry hx-swap-oob="true";
    panel-footer wrapper must NOT carry hx-swap-oob="true"
    (260502-ui revision: panel-footer replaces block footer as initial receiver)."""
    src = _read(OVERVIEW_INDEX_HTML)
    # OOB block: wrapper must carry the attribute
    oob_start = src.find("{% block pagination_oob %}")
    oob_end = src.find("{% endblock pagination_oob %}")
    oob_region = src[oob_start:oob_end]
    assert 'hx-swap-oob="true"' in oob_region, (
        'block pagination_oob wrapper must carry hx-swap-oob="true" (HTMX OOB merge)'
    )
    # Panel-footer wrapper: must NOT carry hx-swap-oob (initial-render receiver only)
    pf_idx = src.find('<div class="panel-footer">')
    pf_end = src.find("</div>", src.find('id="overview-pagination"', pf_idx))
    pf_region = src[pf_idx:pf_end + len("</div>")]
    assert 'id="overview-pagination" hx-swap-oob="true"' not in pf_region, (
        'panel-footer wrapper must NOT carry hx-swap-oob="true" '
        "(initial-render receiver, not OOB emitter)"
    )


# ---------------------------------------------------------------------------
# Task 5 — OOB block leakage guards (260501-ui hotfix)
#
# Same shape as the 260429-qyv hotfix for params_picker_oob: OOB-only blocks
# defined INSIDE {% block content %} render visibly on full-page GET, producing
# orphan spans below the panel and duplicate ids with the in-panel/in-footer
# receivers. These tests pin OOB blocks to "outside content" placement.
# ---------------------------------------------------------------------------


def test_get_browse_renders_exactly_one_grid_count() -> None:
    """260501-ui: GET /browse must render exactly ONE id="grid-count" span —
    the receiver inside the site-footer. Extra spans indicate the count_oob
    block leaked into the full-page render."""
    client = TestClient(app)
    r = client.get("/browse")
    assert r.status_code == 200
    assert r.text.count('id="grid-count"') == 1, (
        "260501-ui: GET /browse must render exactly ONE #grid-count "
        "(footer receiver). Extra spans mean count_oob is leaking into "
        "the full-page render — move it outside {% block content %}."
    )


def test_get_browse_renders_exactly_one_picker_badge_per_id() -> None:
    """260501-ui: GET /browse must render exactly ONE picker-{platforms,params}-badge
    each — both inside the picker_popover macro. Duplicates indicate the
    picker_badges_oob block leaked into the full-page render."""
    client = TestClient(app)
    r = client.get("/browse")
    assert r.status_code == 200
    for badge_id in ("picker-platforms-badge", "picker-params-badge"):
        assert r.text.count(f'id="{badge_id}"') == 1, (
            f"260501-ui: GET /browse must render exactly ONE #{badge_id} "
            "(inside picker_popover macro). Extra spans mean picker_badges_oob "
            "is leaking into the full-page render — move it outside "
            "{% block content %}."
        )


def test_get_overview_renders_exactly_one_overview_count() -> None:
    """260501-ui: GET /overview must render exactly ONE id="overview-count" span —
    the receiver inside .panel-header. Extra spans indicate the count_oob
    block leaked into the full-page render."""
    client = TestClient(app)
    r = client.get("/overview")
    assert r.status_code == 200
    assert r.text.count('id="overview-count"') == 1, (
        "260501-ui: GET /overview must render exactly ONE #overview-count "
        "(panel-header receiver). Extra spans mean count_oob is leaking into "
        "the full-page render — move it outside {% block content %}."
    )


def test_browse_oob_blocks_outside_content() -> None:
    """260501-ui: count_oob, warnings_oob, picker_badges_oob blocks in
    browse/index.html must be defined AFTER {% endblock %} closes block content
    so they only render via jinja2-fragments POST responses, not on GET."""
    src = _read(BROWSE_HTML)
    content_end = src.find("{% endblock %}")
    assert content_end > 0, "browse/index.html must close {% block content %}"
    for block_name in ("count_oob", "warnings_oob", "picker_badges_oob"):
        block_idx = src.find(f"{{% block {block_name} %}}")
        assert block_idx > content_end, (
            f"260501-ui: {{% block {block_name} %}} must be defined AFTER "
            "{% endblock %} (outside block content) so it is fragment-only "
            "and does not leak into GET /browse full-page render."
        )


def test_overview_count_oob_outside_content() -> None:
    """260501-ui: count_oob block in overview/index.html must be defined AFTER
    {% endblock %} closes block content so it only renders via jinja2-fragments
    POST responses, not on GET /overview."""
    src = _read(OVERVIEW_INDEX_HTML)
    content_end = src.find("{% endblock %}")
    assert content_end > 0, "overview/index.html must close {% block content %}"
    block_idx = src.find("{% block count_oob %}")
    assert block_idx > content_end, (
        "260501-ui: {% block count_oob %} must be defined AFTER {% endblock %} "
        "(outside block content) so it is fragment-only and does not leak "
        "into GET /overview full-page render."
    )


def test_overview_table_last_column_padding() -> None:
    """260501-ui: .overview-table last-child cells must carry padding-right: 24px
    so JV table text does not kiss the panel edge (mirrors first-child 24px)."""
    src = _read(APP_CSS)
    assert ".overview-table thead th:last-child { padding-right: 24px" in src, (
        "260501-ui: .overview-table thead th:last-child must declare "
        "padding-right: 24px to mirror the first-child padding-left."
    )
    assert ".overview-table tbody td:last-child { padding-right: 24px" in src, (
        "260501-ui: .overview-table tbody td:last-child must declare "
        "padding-right: 24px to mirror the first-child padding-left."
    )
