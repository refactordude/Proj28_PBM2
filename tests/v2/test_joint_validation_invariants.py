"""Phase 1 Joint Validation invariants — Plan 06.

Replaces tests/v2/test_phase05_invariants.py. Grep-based policy guards that
enforce locked decisions D-JV-01..D-JV-17 at the source-file level. These
tests run fast (no app startup, no fixtures) and catch regressions where a
later commit accidentally re-introduces a deleted symbol or breaks a locked
contract (sandbox attribute, sync def discipline, etc.).
"""
from __future__ import annotations

import re
from pathlib import Path


REPO = Path(__file__).parent.parent.parent
APP = REPO / "app_v2"
TPL = APP / "templates"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# D-JV-03 — numeric-only ^\d+$ regex on JV folder names
# ---------------------------------------------------------------------------


def test_jv_store_enforces_numeric_only_regex() -> None:
    """D-JV-03: joint_validation_store must compile ^\\d+$ once at module level."""
    src = _read(APP / "services" / "joint_validation_store.py")
    # Either compiled at module level OR inline use; require the literal pattern.
    assert r"^\d+$" in src, (
        "joint_validation_store must enforce numeric-only regex (D-JV-03)"
    )
    assert "re.compile" in src, (
        "joint_validation_store must compile the regex once at module level"
    )


# ---------------------------------------------------------------------------
# INFRA-05 — sync def discipline in JV routers
# ---------------------------------------------------------------------------


def test_jv_routes_use_sync_def_only() -> None:
    """INFRA-05: every JV-touching route must be sync def (FastAPI threadpool)."""
    overview_src = _read(APP / "routers" / "overview.py")
    jv_src = _read(APP / "routers" / "joint_validation.py")
    assert "async def" not in overview_src, (
        "INFRA-05: routers/overview.py must use sync def"
    )
    assert "async def" not in jv_src, (
        "INFRA-05: routers/joint_validation.py must use sync def"
    )


# ---------------------------------------------------------------------------
# Iframe sandbox — locked 3-flag attribute literal (T-05-03)
# ---------------------------------------------------------------------------


def test_jv_detail_iframe_sandbox_locked_attribute() -> None:
    """detail.html must contain the locked 3-flag sandbox attribute literal."""
    src = _read(TPL / "joint_validation" / "detail.html")
    expected = 'sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"'
    assert expected in src, "detail.html must contain the locked sandbox attribute"
    # Combining the script-execution flag with allow-same-origin lets the
    # framed document remove the sandbox attr; allow-top-navigation lets it
    # navigate the parent; allow-forms lets it post arbitrary data.
    assert "allow-scripts" not in src, (
        "detail.html must NOT add the script-execution flag"
    )
    assert "allow-top-navigation" not in src, (
        "detail.html must NOT add allow-top-navigation"
    )
    assert "allow-forms" not in src, "detail.html must NOT add allow-forms"


# ---------------------------------------------------------------------------
# XSS defense — no `| safe` filter on dynamic values (autoescape on by default)
# ---------------------------------------------------------------------------


def test_jv_templates_have_no_safe_filter() -> None:
    """No JV template may use the | safe filter (autoescape is the only path)."""
    targets = [
        TPL / "joint_validation" / "detail.html",
        TPL / "overview" / "index.html",
        TPL / "overview" / "_grid.html",
        TPL / "overview" / "_filter_bar.html",
    ]
    for path in targets:
        src = _read(path)
        assert "| safe" not in src, (
            f"{path.name} must not use the | safe filter "
            "(D-JV-04 + D-JV-05 + XSS defense)"
        )


# ---------------------------------------------------------------------------
# D-JV-15 / D-OV-16 — URL sanitizer scheme list verbatim
# ---------------------------------------------------------------------------


def test_jv_url_sanitizer_scheme_list_verbatim() -> None:
    """D-JV-15: scheme list must be the verbatim port of D-OV-16."""
    src = _read(APP / "services" / "joint_validation_grid_service.py")
    # The tuple is split across multiple lines in the source for readability;
    # match the unique 5-scheme substring (which is byte-equal regardless of
    # the surrounding parentheses + trailing comma layout).
    expected = '"javascript:", "data:", "vbscript:", "file:", "about:"'
    assert expected in src, (
        "joint_validation_grid_service must contain the verbatim D-OV-16 "
        "scheme list (5 entries in the locked order)"
    )


# ---------------------------------------------------------------------------
# D-JV-05 — blank "" sentinel, NOT em-dash
# ---------------------------------------------------------------------------


def test_jv_no_em_dash_default_in_view_model() -> None:
    """D-JV-05: blank '' is the missing-field sentinel, NOT em-dash."""
    src = _read(APP / "services" / "joint_validation_grid_service.py")
    assert '= "—"' not in src, (
        "D-JV-05: blank '' is the missing-field sentinel, NOT em-dash"
    )
    assert "= '—'" not in src


# ---------------------------------------------------------------------------
# D-JV-13 + Pitfall 10 — explicit StaticFiles mount kwargs
# ---------------------------------------------------------------------------


def test_jv_static_mount_html_false_explicit() -> None:
    """JV static mount must explicitly set html=False + follow_symlink=False."""
    src = _read(APP / "main.py")
    jv_mount_idx = src.find('app.mount("/static/joint_validation"')
    # The mount call may be split across lines — fall back to finding the
    # path string alone if the single-line form isn't present.
    if jv_mount_idx < 0:
        jv_mount_idx = src.find('"/static/joint_validation"')
    assert jv_mount_idx >= 0, "main.py must mount /static/joint_validation"
    block = src[jv_mount_idx : jv_mount_idx + 500]
    assert "html=False" in block, "JV static mount must set html=False explicitly"
    assert "follow_symlink=False" in block, (
        "JV static mount must set follow_symlink=False"
    )
    assert 'directory="content/joint_validation"' in block


# ---------------------------------------------------------------------------
# D-JV-06 / D-JV-07 — no curated-Platform symbols left in routers/overview.py
# ---------------------------------------------------------------------------


def test_jv_no_overview_add_route() -> None:
    """D-JV-06/D-JV-07: routers/overview.py must not reference any deleted symbol."""
    src = _read(APP / "routers" / "overview.py")
    forbidden = [
        "add_platform",
        "OverviewEntity",
        "DuplicateEntityError",
        "OVERVIEW_YAML_PATH",
        "_resolve_curated_pids",
        "_entity_dict",
        "_build_overview_context",
        "build_overview_grid_view_model",
    ]
    for sym in forbidden:
        assert sym not in src, (
            f"D-JV-06/D-JV-07: routers/overview.py must not reference {sym!r}"
        )


# ---------------------------------------------------------------------------
# Pitfall 3 — JV summary cache key has 'jv' discriminator
# ---------------------------------------------------------------------------


def test_jv_summary_cache_key_has_jv_discriminator() -> None:
    """Pitfall 3: JV summary cache key must include 'jv' string discriminator."""
    src = _read(APP / "services" / "joint_validation_summary.py")
    assert 'hashkey("jv"' in src, (
        "Pitfall 3: JV summary cache key must include 'jv' discriminator "
        "to prevent collision with platform's cache key on the same numeric id"
    )


# ---------------------------------------------------------------------------
# D-JV-04 — Korean label byte-equal (no ASCII fold)
# ---------------------------------------------------------------------------


def test_jv_parser_korean_label_byte_equal() -> None:
    """D-JV-04: '담당자' label is matched byte-equal in the parser."""
    src = _read(APP / "services" / "joint_validation_parser.py")
    assert "담당자" in src, (
        "Parser must match the Korean label '담당자' byte-equal (no ASCII fold)"
    )


# ---------------------------------------------------------------------------
# D-JV-16 — AI Summary pre-processor decomposes <script>, <style>, <img>
# ---------------------------------------------------------------------------


def test_jv_summary_preprocess_decomposes_three_tags() -> None:
    """D-JV-16: AI Summary pre-processor must decompose <script>, <style>, <img>."""
    src = _read(APP / "services" / "joint_validation_summary.py")
    # Accept either list or tuple of the three tags. The current implementation
    # lives in joint_validation_parser.py + summary; check both files since
    # the contract might be honored in either location.
    parser_src = _read(APP / "services" / "joint_validation_parser.py")
    combined = src + "\n" + parser_src
    assert (
        '["script", "style", "img"]' in combined
        or "('script', 'style', 'img')" in combined
        or '"script", "style", "img"' in combined
    ), "D-JV-16: AI Summary pre-processor must decompose <script>, <style>, <img>"
    assert "decompose" in combined, (
        "D-JV-16: pre-processor must call BeautifulSoup decompose() to "
        "remove tag + attributes (NOT extract() or unwrap())"
    )


# ---------------------------------------------------------------------------
# yaml.load is banned project-wide — only yaml.safe_load is acceptable
# ---------------------------------------------------------------------------


def test_jv_no_yaml_load_in_phase_1_code() -> None:
    """yaml.load is banned project-wide; yaml.safe_load OK if YAML enters scope."""
    targets = [
        APP / "services" / "joint_validation_parser.py",
        APP / "services" / "joint_validation_store.py",
        APP / "services" / "joint_validation_grid_service.py",
        APP / "services" / "joint_validation_summary.py",
        APP / "routers" / "joint_validation.py",
        APP / "data" / "jv_summary_prompt.py",
    ]
    for path in targets:
        if not path.exists():
            # The data/jv_summary_prompt.py module is optional; skip silently
            # if a future refactor inlines its constants elsewhere.
            continue
        src = _read(path)
        assert not re.search(r"\byaml\.load\b(?!\w)", src), (
            f"{path.name}: yaml.load is banned (use yaml.safe_load if YAML "
            "is in scope)"
        )


# ---------------------------------------------------------------------------
# JV router registration in main.py
# ---------------------------------------------------------------------------


def test_jv_routes_register_in_main() -> None:
    """main.py must import + register the joint_validation router."""
    src = _read(APP / "main.py")
    assert "from app_v2.routers import joint_validation" in src, (
        "main.py must import the joint_validation router"
    )
    assert "app.include_router(joint_validation.router)" in src, (
        "main.py must register the joint_validation router on the app"
    )


# ---------------------------------------------------------------------------
# Pitfall 10 — child mount registered BEFORE parent /static
# ---------------------------------------------------------------------------


def test_jv_static_mount_registered_before_static() -> None:
    """Pitfall 10: longest-prefix-first is NOT automatic; registration order matters."""
    src = _read(APP / "main.py")
    jv_idx = src.find('app.mount("/static/joint_validation"')
    if jv_idx < 0:
        # Fall back to the path string in case the call is split across lines.
        jv_idx = src.find('"/static/joint_validation"')
    static_idx = src.find('app.mount("/static"')
    assert jv_idx >= 0 and static_idx >= 0, "Both mounts must exist"
    assert jv_idx < static_idx, (
        "JV mount must be registered BEFORE /static (Pitfall 10 — Starlette "
        "dispatches mounts by registration order, not by longest-prefix-first)"
    )


# ---------------------------------------------------------------------------
# D-JV-11 — 6 picker_popover invocations using the reused macro
# ---------------------------------------------------------------------------


def test_jv_filter_bar_uses_picker_popover_macro_unmodified() -> None:
    """D-JV-11: filter bar imports picker_popover from browse/_picker_popover.html."""
    fb = _read(TPL / "overview" / "_filter_bar.html")
    assert (
        '{% from "browse/_picker_popover.html" import picker_popover %}' in fb
    ), "Filter bar must import the macro from browse/_picker_popover.html (reuse)"
    assert fb.count("picker_popover(") >= 6, (
        "Filter bar must invoke picker_popover 6 times (D-JV-11)"
    )
    # The macro file must remain present (reused AS-IS — not duplicated).
    macro_src = _read(TPL / "browse" / "_picker_popover.html")
    assert macro_src.strip(), (
        "browse/_picker_popover.html must remain present (reused AS-IS)"
    )


# ---------------------------------------------------------------------------
# Quick task 260430-wzg — popover overflow-visible self-match selector
# ---------------------------------------------------------------------------


def test_jv_filter_popover_overflow_visible_self_match() -> None:
    """260430-wzg: app.css must expose BOTH selector forms so JV popovers
    (Status / Customer / AP Company / Device / Controller / Application)
    escape `.panel { overflow: hidden }` clipping.

    The JV filter bar is `<div class="overview-filter-bar panel">` —
    :has() only matches descendants, so the descendant selector cannot
    match when .panel and .overview-filter-bar are co-classes on the
    same element. Both forms must coexist:

      * `.panel:has(.overview-filter-bar)` — Browse-shaped wrapping (.panel
        contains a separate filter-bar child).
      * `.panel.overview-filter-bar` — JV-shaped self-match (.panel and
        the filter-bar are the SAME element).
    """
    css = _read(APP / "static" / "css" / "app.css")
    assert ".panel:has(.overview-filter-bar)" in css, (
        "app.css must keep the descendant-match selector "
        "`.panel:has(.overview-filter-bar)` (Phase 5 fix preserved)"
    )
    assert ".panel.overview-filter-bar" in css, (
        "app.css must contain the self-match selector "
        "`.panel.overview-filter-bar` so JV popovers escape "
        "`.panel { overflow: hidden }` clipping (260430-wzg)"
    )
