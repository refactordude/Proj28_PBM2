"""Phase 04 codebase invariants — regression guards on locked decisions.

These tests grep the source for forbidden patterns and assert their absence.
They are NOT functional tests; they are policy enforcement.

Each test maps to a specific decision it guards:
  - D-03: no Plotly under app_v2/ (v1.0 still imports it; v2.0 does not)
  - D-13: PARAM_LABEL_SEP must be ' middle-dot ' (U+00B7), NEVER v1.0's slash
  - D-19: no openpyxl, no csv module, no /browse/export route — export removed
  - D-22: no `from app.components.export_dialog` import (v1.0-only component)
  - D-34 + INFRA-05: browse routes are sync `def`, never `async def`
  - Plan 04-02: browse stub removed from routers/root.py
  - Plan 04-02: browse router registered in main.py BEFORE root
  - XSS defense: no `| safe` filter in browse templates
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_V2_ROOT = REPO_ROOT / "app_v2"
BROWSE_TPL_DIR = APP_V2_ROOT / "templates" / "browse"


def _read(*parts: str) -> str:
    return APP_V2_ROOT.joinpath(*parts).read_text(encoding="utf-8")


# -----------------------------------------------------------------------
# D-03 / D-19 / D-22 — banned imports under app_v2/
# -----------------------------------------------------------------------

@pytest.mark.parametrize("library, regex", [
    ("plotly",   r"^\s*(import|from)\s+plotly\b"),
    ("openpyxl", r"^\s*(import|from)\s+openpyxl\b"),
    ("csv",      r"^\s*(import|from)\s+csv\b"),
])
def test_no_banned_export_or_chart_libraries_imported_in_app_v2(library, regex):
    """D-03 (plotly), D-19 (openpyxl, csv) — none of these belong in v2.0.

    Anchored to start-of-line + word boundary so docstrings and
    comments cannot trigger a false positive.
    """
    violations = []
    pattern = re.compile(regex)
    for path in APP_V2_ROOT.rglob("*.py"):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                violations.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}")
    assert violations == [], (
        f"{library} import found under app_v2/ — forbidden by Phase 04 decisions:\n"
        + "\n".join(violations)
    )


def test_no_export_dialog_imported_in_app_v2():
    """D-22: app/components/export_dialog stays exclusively v1.0 territory."""
    violations = []
    pattern_from = re.compile(r"\bfrom\s+app\.components\.export_dialog\b")
    pattern_imp = re.compile(r"\bimport\s+app\.components\.export_dialog\b")
    for path in APP_V2_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if pattern_from.search(text) or pattern_imp.search(text):
            violations.append(str(path.relative_to(REPO_ROOT)))
    assert violations == [], (
        "D-22 violation — app.components.export_dialog imported under app_v2/:\n"
        + "\n".join(violations)
    )


# -----------------------------------------------------------------------
# D-34 + INFRA-05 — no async def in browse router
# -----------------------------------------------------------------------

def test_no_async_def_in_browse_router():
    """D-34 + INFRA-05: browse routes MUST be sync `def` (threadpool dispatch)."""
    src = _read("routers/browse.py")
    offending = [
        line.rstrip()
        for line in src.splitlines()
        if re.match(r"^\s*async\s+def\s+", line)
    ]
    assert offending == [], (
        "D-34 violation in routers/browse.py — async def is forbidden:\n"
        + "\n".join(offending)
    )


# -----------------------------------------------------------------------
# D-13 — middle-dot separator (Pitfall 3)
# -----------------------------------------------------------------------

def test_param_label_separator_is_middle_dot_not_slash():
    """D-13: v2.0 uses U+00B7 (middle dot) as the InfoCategory/Item separator.

    Catch any accidental carryover of v1.0's slash separator.
    """
    svc = _read("services/browse_service.py")
    # MUST contain the middle-dot character somewhere (as the constant assignment).
    # Use the unicode escape form so this test file does not itself contain the
    # exact bytes that other invariants might guard against.
    middle_dot = "·"
    assert middle_dot in svc, (
        "D-13: PARAM_LABEL_SEP must use the middle dot (U+00B7) character "
        "in browse_service.py"
    )
    # MUST NOT use v1.0's slash separator as a string literal. Construct the
    # forbidden literals from character codes so the test source itself does
    # not contain them as a multi-character substring.
    slash_dq = '"' + " / " + '"'  # the 5-char sequence: " / "
    slash_sq = "'" + " / " + "'"  # the 5-char sequence: ' / '
    assert slash_dq not in svc, (
        "D-13: do not carry the v1.0 slash separator (double-quoted form found)"
    )
    assert slash_sq not in svc, (
        "D-13: do not carry the v1.0 slash separator (single-quoted form found)"
    )


# -----------------------------------------------------------------------
# D-19 — no /browse/export routes
# -----------------------------------------------------------------------

def test_no_browse_export_route_anywhere_in_app_v2():
    """D-19: no /browse/export endpoint may exist in v2.0.

    Scan all app_v2/routers/*.py for the substring '/browse/export'.
    """
    violations = []
    forbidden = "/browse/" + "export"  # split to avoid self-match in this test file
    for path in (APP_V2_ROOT / "routers").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if forbidden in text:
            violations.append(str(path.relative_to(REPO_ROOT)))
    assert violations == [], (
        "D-19 violation — /browse/export route declared somewhere:\n"
        + "\n".join(violations)
    )


# -----------------------------------------------------------------------
# XSS defense — no | safe in browse templates
# -----------------------------------------------------------------------

def test_no_safe_filter_in_browse_templates():
    """XSS regression guard — every dynamic output uses Jinja autoescape.

    The Jinja `safe` filter disables autoescape and is the textbook XSS
    vector. Phase 04 templates contain only static strings + escaped vm
    fields; the safe filter must NEVER appear in browse/*.html.
    """
    violations = []
    forbidden = "| " + "safe"  # split to avoid self-match in this test file
    for path in BROWSE_TPL_DIR.rglob("*.html"):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if forbidden in line:
                violations.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}")
    assert violations == [], (
        "XSS regression — `| safe` filter found in browse templates:\n"
        + "\n".join(violations)
    )


# -----------------------------------------------------------------------
# Plan 04-02 — browse stub removed from root router
# -----------------------------------------------------------------------

def test_no_browse_stub_in_root_router():
    """Plan 04-02 deleted the Phase 1 GET /browse stub from routers/root.py."""
    src = _read("routers/root.py")
    assert "def browse_page" not in src, (
        "Plan 04-02 contract: the Phase 1 GET /browse stub must be deleted "
        "from routers/root.py (the new browse router owns /browse)."
    )
    assert '@router.get("/browse"' not in src, (
        "Plan 04-02 contract: routers/root.py must not declare a /browse route."
    )
    # Sanity: the /ask stub should still be there (Phase 5 owns it later).
    assert "def ask_page" in src, (
        "Plan 04-02 must NOT remove the /ask stub — Phase 5 still relies on it."
    )


# -----------------------------------------------------------------------
# Plan 04-02 — browse router registered before root in main.py
# -----------------------------------------------------------------------

def test_browse_router_registered_in_main_before_root():
    """Plan 04-02 contract: main.py includes browse router BEFORE root."""
    main_src = _read("main.py")
    # Both imports present
    assert "from app_v2.routers import browse" in main_src
    assert "from app_v2.routers import root" in main_src
    # Both include_router calls present
    assert "app.include_router(browse.router)" in main_src
    assert "app.include_router(root.router)" in main_src
    # Browse comes first
    browse_pos = main_src.find("app.include_router(browse.router)")
    root_pos = main_src.find("app.include_router(root.router)")
    assert browse_pos > 0 and root_pos > browse_pos, (
        f"include_router order wrong: browse at {browse_pos}, root at {root_pos}; "
        "browse must come before root."
    )


# -----------------------------------------------------------------------
# Defensive: browse templates contain no banned chart/export references
# -----------------------------------------------------------------------

@pytest.mark.parametrize("token", ["plotly", "openpyxl", "export_dialog"])
def test_browse_templates_contain_no_banned_tokens(token):
    """Belt-and-suspenders: scan template HTML for forbidden references.

    Templates would never normally import these libraries (they're Python),
    but a CDN <script src="...plotly..."> tag or a rogue {{ export_dialog }}
    reference would slip past the Python-only invariants. Catch it here.
    """
    violations = []
    for path in BROWSE_TPL_DIR.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        if token in text:
            violations.append(str(path.relative_to(REPO_ROOT)))
    assert violations == [], (
        f"Banned token '{token}' found in browse templates:\n"
        + "\n".join(violations)
    )


# -----------------------------------------------------------------------
# D-15b — picker popover uses auto-commit on checkbox change with debounce
# (gap-5 closure 2026-04-28; supersedes D-14, D-15, D-15a)
# -----------------------------------------------------------------------

def test_picker_popover_uses_d15b_auto_commit_pattern():
    """D-15b regression guard — picker popover MUST use the auto-commit
    pattern (no Apply button; <ul class="popover-search-list"> carries
    hx-post + hx-trigger with delay:250ms). The close-event taxonomy from
    D-15a is REMOVED — popover-search.js must not contain the deleted
    primitives.

    Required markers in app_v2/templates/browse/_picker_popover.html:
      1. NO popover-apply-btn class (Apply button removed)
      2. <ul class="popover-search-list"> carries hx-post="/browse/grid"
      3. <ul class="popover-search-list"> carries hx-target="#browse-grid"
      4. <ul class="popover-search-list"> hx-trigger contains "delay:250ms"
      5. data-bs-auto-close="outside" on the trigger button stays (D-09)

    Required markers in app_v2/static/js/popover-search.js:
      6. NO dataset.cancelling (Esc-distinguisher removed)
      7. NO _selectionsEqual (no-op short-circuit removed; HTMX's delay
         modifier is the debouncer, not a selection-equality check)
      8. NO popover-apply-btn references (Apply button gone)
      9. NO onDropdownHide / hidden.bs.dropdown handler (close-event
         taxonomy is moot under auto-commit)
     10. D-15b citation in the file header comment
    """
    js_src = (APP_V2_ROOT / "static" / "js" / "popover-search.js").read_text(encoding="utf-8")
    tpl_src = _read("templates", "browse", "_picker_popover.html")

    # Marker 1: Apply button gone from template.
    assert "popover-apply-btn" not in tpl_src, (
        "D-15b marker 1 — popover-apply-btn class is back in "
        "_picker_popover.html. The Apply button must remain removed; "
        "auto-commit on change is the only commit path."
    )

    # Markers 2 + 3: hx-post + hx-target on the <ul>.
    # Use a regex that allows arbitrary attribute order/whitespace inside
    # the <ul ...> tag.
    ul_tag_pattern = re.compile(
        r'<ul\b[^>]*\bclass="[^"]*\bpopover-search-list\b[^"]*"[^>]*>',
        re.DOTALL,
    )
    ul_tags = ul_tag_pattern.findall(tpl_src)
    # Filter out short matches (e.g., literal <ul class="popover-search-list">
    # examples that may appear inside the macro docstring). The real opening
    # tag spans multiple lines and is well over 100 chars.
    ul_tags = [t for t in ul_tags if len(t) > 100]
    assert ul_tags, (
        "D-15b — could not locate the real <ul class=\"popover-search-list\"> "
        "opening tag in _picker_popover.html (no multi-line tag matched). "
        "The auto-commit checklist wiring lives on this element."
    )
    for tag in ul_tags:
        assert 'hx-post="/browse/grid"' in tag, (
            "D-15b marker 2 — <ul class=\"popover-search-list\"> missing "
            f"hx-post=\"/browse/grid\". Tag: {tag!r}"
        )
        assert 'hx-target="#browse-grid"' in tag, (
            "D-15b marker 3 — <ul class=\"popover-search-list\"> missing "
            f"hx-target=\"#browse-grid\". Tag: {tag!r}"
        )
        # Marker 4: delay:250ms in hx-trigger.
        assert "delay:250ms" in tag, (
            "D-15b marker 4 — <ul class=\"popover-search-list\"> hx-trigger "
            "must contain \"delay:250ms\" so quick toggle bursts collapse "
            f"to a single POST. Tag: {tag!r}"
        )

    # Marker 5: data-bs-auto-close="outside" preserved.
    assert 'data-bs-auto-close="outside"' in tpl_src, (
        "D-15b marker 5 — trigger button in _picker_popover.html must keep "
        "data-bs-auto-close=\"outside\" so the popover stays open across "
        "multiple toggles for ergonomics (D-09 precondition preserved)."
    )

    # Marker 6: dataset.cancelling absent.
    assert "dataset.cancelling" not in js_src, (
        "D-15b marker 6 — dataset.cancelling is back in popover-search.js. "
        "Under D-15b there is no Esc/cancel distinction; the entire "
        "close-event taxonomy is removed."
    )

    # Marker 7: _selectionsEqual absent.
    assert "_selectionsEqual" not in js_src, (
        "D-15b marker 7 — _selectionsEqual is back in popover-search.js. "
        "Under D-15b the no-op short-circuit is implemented by HTMX's "
        "delay:250ms trigger modifier, not by JS selection-equality."
    )

    # Marker 8: popover-apply-btn absent from JS.
    assert "popover-apply-btn" not in js_src, (
        "D-15b marker 8 — popover-apply-btn is back in popover-search.js. "
        "Under D-15b the Apply button is removed; no programmatic click "
        "is needed."
    )

    # Marker 9: no hidden.bs.dropdown listener.
    assert "hidden.bs.dropdown" not in js_src and "hide.bs.dropdown" not in js_src, (
        "D-15b marker 9 — Bootstrap dropdown lifecycle handler is back in "
        "popover-search.js. Under D-15b all close paths are equivalent "
        "(just close the popover); no commit/cancel logic on hide."
    )

    # Marker 10: D-15b citation.
    assert "D-15b" in js_src, (
        "D-15b marker 10 — popover-search.js does not cite D-15b in a "
        "comment. Future readers must see the locked contract documented."
    )
