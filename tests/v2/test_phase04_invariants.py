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
