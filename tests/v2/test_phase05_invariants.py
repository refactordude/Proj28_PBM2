"""Phase 05 codebase invariants — regression guards on locked decisions.

These tests grep the source for forbidden / required patterns and assert
their presence / absence. They are NOT functional tests; they are policy
enforcement.

Each test maps to a specific decision it guards:
  - D-OV-02: yaml.safe_load is the ONLY YAML parser in content_store.py
  - D-OV-04: DELETE /overview/<pid>, POST /overview/filter, POST
    /overview/filter/reset routes are GONE
  - D-OV-05: overview/_filter_alert.html and overview/_entity_row.html
    are GONE; only index.html, _grid.html, _filter_bar.html remain
  - D-OV-06: picker_popover macro is SHARED from
    browse/_picker_popover.html, NOT forked under overview/
  - D-OV-10: AI Summary cell preserves Phase 3 contract
    (hx-post=/platforms/<pid>/summary, hx-target=#summary-<pid>,
    hx-disabled-elt)
  - D-OV-13: multi-value filter params use Query(default_factory=list);
    NEVER comma-separated parsing
  - OVERVIEW-V2-01: Phase 4 Browse pivot-grid table classes appear in
    overview/index.html
  - INFRA-05: no async def in app_v2/routers/overview.py
  - XSS defense: no `| safe` in any app_v2/templates/overview/*.html file
  - D-03 (Phase 4 carry-over): no Plotly under app_v2/
  - General: no `hx-delete` to /overview/<pid> anywhere in templates
    (Remove button gone per D-OV-04)
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_V2_ROOT = REPO_ROOT / "app_v2"
OVERVIEW_TPL_DIR = APP_V2_ROOT / "templates" / "overview"


def _read(*parts: str) -> str:
    return APP_V2_ROOT.joinpath(*parts).read_text(encoding="utf-8")


# -----------------------------------------------------------------------
# D-OV-02 — yaml.safe_load only; yaml.load NEVER
# -----------------------------------------------------------------------

def test_content_store_uses_yaml_safe_load_only():
    """D-OV-02 + T-05-02-01: read_frontmatter MUST use yaml.safe_load.

    yaml.load is unsafe — it can deserialize !!python/object tags and
    execute arbitrary Python. Acceptance: no `yaml.load(` (with paren)
    in content_store.py. The string `safe_load` is allowed.
    """
    src = _read("services/content_store.py")
    # Match `load(` but NOT `safe_load(` — anchor on the open paren AND
    # require the preceding 5 chars are NOT 'safe_'. Scan only lines
    # that mention yaml so unrelated `*.load(` calls in the file (none
    # today, but future-proof) cannot trip the guard.
    pattern = re.compile(r"(?<!safe_)load\s*\(")
    violations = []
    for line_no, line in enumerate(src.splitlines(), 1):
        if "yaml" not in line:
            continue
        if pattern.search(line):
            violations.append(f"line {line_no}: {line.strip()}")
    assert violations == [], (
        "D-OV-02 violation — yaml.load found in content_store.py "
        "(must use yaml.safe_load):\n" + "\n".join(violations)
    )
    # Sanity: confirm yaml.safe_load IS present (positive assertion)
    assert "yaml.safe_load(" in src, (
        "D-OV-02 — content_store.py must use yaml.safe_load, but the "
        "literal call was not found"
    )


# -----------------------------------------------------------------------
# D-OV-04 — forbidden routes are gone from app_v2/routers/overview.py
# -----------------------------------------------------------------------

@pytest.mark.parametrize("forbidden_pattern, decision_id", [
    (r'@router\.delete\(', "D-OV-04 (DELETE /overview/<pid> removed)"),
    (r'@router\.post\("/overview/filter"', "D-OV-04 (POST /overview/filter removed)"),
    (r'@router\.post\("/overview/filter/reset"', "D-OV-04 (POST /overview/filter/reset removed)"),
])
def test_no_forbidden_route_in_overview_router(forbidden_pattern, decision_id):
    """D-OV-04: legacy filter / DELETE routes must not exist in overview.py."""
    src = _read("routers/overview.py")
    violations = [
        line.rstrip() for line in src.splitlines()
        if re.search(forbidden_pattern, line)
    ]
    assert violations == [], (
        f"{decision_id} violation:\n" + "\n".join(violations)
    )


# -----------------------------------------------------------------------
# D-OV-05 — overview/ template inventory: only 3 files remain
# -----------------------------------------------------------------------

def test_overview_template_inventory():
    """D-OV-05: app_v2/templates/overview/ contains exactly 3 .html files:
    index.html, _grid.html, _filter_bar.html.

    Legacy _filter_alert.html and _entity_row.html are DELETED.
    """
    actual = sorted(p.name for p in OVERVIEW_TPL_DIR.glob("*.html"))
    expected = ["_filter_bar.html", "_grid.html", "index.html"]
    assert actual == expected, (
        f"D-OV-05 violation — overview/ template inventory mismatch.\n"
        f"  Expected: {expected}\n"
        f"  Actual:   {actual}"
    )


# -----------------------------------------------------------------------
# D-OV-06 — picker_popover macro is SHARED, not forked
# -----------------------------------------------------------------------

def test_picker_popover_macro_is_shared_not_forked():
    """D-OV-06: the picker_popover macro is sourced from
    browse/_picker_popover.html and imported by overview/_filter_bar.html
    via cross-template import. There must NOT be a forked copy of the
    macro under overview/.
    """
    # No fork under overview/
    forked = APP_V2_ROOT / "templates" / "overview" / "_picker_popover.html"
    assert not forked.exists(), (
        f"D-OV-06 violation — picker_popover macro forked at "
        f"{forked.relative_to(REPO_ROOT)}; the macro must be SHARED from "
        "browse/_picker_popover.html via "
        '{% from "browse/_picker_popover.html" import picker_popover %}.'
    )

    # The original macro file exists
    original = APP_V2_ROOT / "templates" / "browse" / "_picker_popover.html"
    assert original.exists(), (
        "D-OV-06 — the source macro file browse/_picker_popover.html is missing"
    )

    # _filter_bar.html imports the macro via cross-template path
    fb = (APP_V2_ROOT / "templates" / "overview" / "_filter_bar.html").read_text(encoding="utf-8")
    assert '{% from "browse/_picker_popover.html" import picker_popover %}' in fb, (
        "D-OV-06 — overview/_filter_bar.html must import the shared macro:\n"
        '  {% from "browse/_picker_popover.html" import picker_popover %}'
    )


# -----------------------------------------------------------------------
# D-OV-10 — AI Summary cell preserves Phase 3 contract
# -----------------------------------------------------------------------

def test_ai_summary_cell_preserves_phase3_contract():
    """D-OV-10: AI Summary button in overview/_grid.html preserves Phase 3
    SUMMARY-02 contract verbatim:
      - hx-post="/platforms/{pid}/summary"
      - hx-target="#summary-{pid}"
      - hx-disabled-elt="this"
      - disabled attr when not row.has_content
    """
    src = (OVERVIEW_TPL_DIR / "_grid.html").read_text(encoding="utf-8")
    assert "/platforms/{{ row.platform_id | e }}/summary" in src, (
        "D-OV-10 — AI Summary hx-post path missing or malformed"
    )
    assert 'hx-target="#summary-{{ row.platform_id | e }}"' in src, (
        "D-OV-10 — AI Summary hx-target missing"
    )
    assert 'hx-disabled-elt="this"' in src, (
        "D-OV-10 — AI Summary hx-disabled-elt missing"
    )
    assert "{% if not row.has_content %}disabled" in src, (
        "D-OV-10 + D-13 (Phase 3) — AI Summary disabled state must be "
        "driven by row.has_content"
    )


# -----------------------------------------------------------------------
# OVERVIEW-V2-01 — Phase 4 Browse pivot-grid table classes in overview/index.html
# -----------------------------------------------------------------------

def test_overview_index_uses_phase4_table_classes():
    """OVERVIEW-V2-01: overview/index.html must mirror Phase 4 Browse
    styling — `<table class="table table-striped table-hover table-sm">`
    + `<thead class="sticky-top bg-light">`.
    """
    src = (OVERVIEW_TPL_DIR / "index.html").read_text(encoding="utf-8")
    assert 'class="table table-striped table-hover table-sm overview-table"' in src, (
        "OVERVIEW-V2-01 — table classes must match Phase 4 pattern + add overview-table"
    )
    assert 'thead class="sticky-top bg-light"' in src, (
        "OVERVIEW-V2-01 — thead must use sticky-top bg-light (Phase 4 D-26)"
    )


# -----------------------------------------------------------------------
# INFRA-05 — no async def in app_v2/routers/overview.py
# -----------------------------------------------------------------------

def test_no_async_def_in_overview_router():
    """INFRA-05: overview routes MUST be sync `def` (threadpool dispatch)."""
    src = _read("routers/overview.py")
    offending = [
        line.rstrip() for line in src.splitlines()
        if re.match(r"^\s*async\s+def\s+", line)
    ]
    assert offending == [], (
        "INFRA-05 violation in routers/overview.py — async def is forbidden:\n"
        + "\n".join(offending)
    )


# -----------------------------------------------------------------------
# XSS defense — no | safe in overview templates
# -----------------------------------------------------------------------

def test_no_safe_filter_in_overview_templates():
    """XSS regression guard — every dynamic output uses Jinja autoescape.

    Mirrors Phase 04 invariant test_no_safe_filter_in_browse_templates.
    """
    violations = []
    forbidden = "| " + "safe"  # split to avoid self-match in this test file
    for path in OVERVIEW_TPL_DIR.rglob("*.html"):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if forbidden in line:
                violations.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}")
    assert violations == [], (
        "XSS regression — `| safe` filter found in overview templates:\n"
        + "\n".join(violations)
    )


# -----------------------------------------------------------------------
# D-OV-04 (Remove button gone) — no hx-delete to /overview/ anywhere
# -----------------------------------------------------------------------

def test_no_remove_button_hx_delete_in_overview_templates():
    """D-OV-04: the per-row Remove (×) button is gone. No `hx-delete`
    attribute pointing at /overview/<pid> may exist anywhere in
    app_v2/templates/.
    """
    violations = []
    # Pattern: hx-delete="..." or hx-delete='...' where the URL contains /overview/
    pattern = re.compile(r'''hx-delete\s*=\s*["'][^"']*/overview/''')
    templates_root = APP_V2_ROOT / "templates"
    for path in templates_root.rglob("*.html"):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                violations.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}")
    assert violations == [], (
        "D-OV-04 violation — hx-delete to /overview/ found in templates "
        "(Remove button must be gone):\n" + "\n".join(violations)
    )


# -----------------------------------------------------------------------
# D-03 (Phase 4 carry-over) — no Plotly under app_v2/
# -----------------------------------------------------------------------

def test_no_plotly_in_app_v2_phase5_carry_over():
    """Phase 4 D-03 carry-over: Plotly stays in v1.0; v2.0 never imports it.

    Phase 4 already has this invariant; Phase 5 re-asserts to catch any
    regression introduced during the Overview rewrite.
    """
    violations = []
    pattern = re.compile(r"^\s*(import|from)\s+plotly\b")
    for path in APP_V2_ROOT.rglob("*.py"):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                violations.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}")
    assert violations == [], (
        "D-03 (Phase 4) violation — plotly imported under app_v2/:\n"
        + "\n".join(violations)
    )


# -----------------------------------------------------------------------
# D-OV-13 — repeated-key URL idiom for multi-value filters
# -----------------------------------------------------------------------

def test_overview_routes_use_query_default_factory_for_multi_value():
    """D-OV-13: multi-value filter params use FastAPI's
    Annotated[list[str], Query(default_factory=list)] — same idiom as
    Phase 4 D-30. NEVER a comma-separated string.
    """
    src = _read("routers/overview.py")
    # At least one Query(default_factory=list) must appear (one per filter column)
    assert "Query(default_factory=list)" in src, (
        "D-OV-13 — overview routes must use Query(default_factory=list) "
        "for multi-value filter params"
    )
    # No comma-separated parsing (e.g. .split(","))
    # — would indicate a regression to a flawed pattern. The string
    # ',' inside a string literal is fine; we only flag .split(",") method calls.
    assert ".split(\",\")" not in src and ".split(',')" not in src, (
        "D-OV-13 — overview routes must NOT use .split(',') for filter "
        "value parsing; FastAPI parses repeated keys natively"
    )
