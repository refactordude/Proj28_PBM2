"""Unit tests for overview_grid_service (Phase 05, D-OV-03/07/08/09/10/13).

Covers:
- Default sort (start desc) when sort args are None
- Sort asc/desc on date columns
- Date empty/None/malformed → END regardless of asc/desc
- Tiebreaker is platform_id ASC (stable, NOT reversed for desc)
- Title fallback to platform_id when frontmatter missing (D-OV-09)
- All other missing PM fields → None
- filter_options sorted alphabetically (case-insensitive), no None/empty
- filter_options computed across ALL rows (NOT the filtered subset)
- Multi-filter set membership: AND across columns, OR within a column
- Sort by non-date column case-insensitive
- Empty curated_pids → empty rows + 6 empty filter_options keys
- active_filter_counts mirrors filter selection
- Invalid sort_col / sort_order fall back to defaults
- has_content_map drives AI Summary disabled state (D-OV-10)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app_v2.services import content_store
from app_v2.services.overview_grid_service import (
    DEFAULT_SORT_COL,
    DEFAULT_SORT_ORDER,
    FILTERABLE_COLUMNS,
    OverviewGridViewModel,
    OverviewRow,
    SORTABLE_COLUMNS,
    build_overview_grid_view_model,
)


@pytest.fixture(autouse=True)
def _clear_frontmatter_cache():
    """Each test starts with an empty memoize cache (read_frontmatter is memoized)."""
    content_store._FRONTMATTER_CACHE.clear()
    yield
    content_store._FRONTMATTER_CACHE.clear()


def _write_fm(tmp_path: Path, pid: str, **kwargs) -> Path:
    """Write a content file with the given frontmatter kwargs."""
    lines = ["---"]
    for k, v in kwargs.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append("# body")
    target = tmp_path / f"{pid}.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Test 1 — default sort = start desc when sort args are None
# ---------------------------------------------------------------------------
def test_build_view_model_default_sort_is_start_desc(tmp_path):
    _write_fm(tmp_path, "P1", title="A", start="2026-04-01")
    _write_fm(tmp_path, "P2", title="B", start="2026-12-31")
    _write_fm(tmp_path, "P3", title="C", start="2025-01-15")
    vm = build_overview_grid_view_model(
        ["P1", "P2", "P3"], tmp_path, filters={}, sort_col=None, sort_order=None
    )
    assert isinstance(vm, OverviewGridViewModel)
    assert vm.sort_col == "start"
    assert vm.sort_order == "desc"
    assert [r.platform_id for r in vm.rows] == ["P2", "P1", "P3"]


# ---------------------------------------------------------------------------
# Test 2 — sort start asc
# ---------------------------------------------------------------------------
def test_sort_start_asc_oldest_first(tmp_path):
    _write_fm(tmp_path, "P1", title="A", start="2026-04-01")
    _write_fm(tmp_path, "P2", title="B", start="2026-12-31")
    _write_fm(tmp_path, "P3", title="C", start="2025-01-15")
    vm = build_overview_grid_view_model(
        ["P1", "P2", "P3"], tmp_path, filters={}, sort_col="start", sort_order="asc"
    )
    assert [r.platform_id for r in vm.rows] == ["P3", "P1", "P2"]


# ---------------------------------------------------------------------------
# Test 3 — empty/None date sorts to END regardless of asc/desc
# ---------------------------------------------------------------------------
def test_empty_date_sorts_to_end_for_both_orders(tmp_path):
    _write_fm(tmp_path, "P1", title="A", start="2026-04-01")
    # P2 has no start (omitted from frontmatter)
    _write_fm(tmp_path, "P2", title="B")
    _write_fm(tmp_path, "P3", title="C", start="2026-12-31")

    vm_desc = build_overview_grid_view_model(
        ["P1", "P2", "P3"], tmp_path, filters={}, sort_col="start", sort_order="desc"
    )
    assert [r.platform_id for r in vm_desc.rows] == ["P3", "P1", "P2"]

    vm_asc = build_overview_grid_view_model(
        ["P1", "P2", "P3"], tmp_path, filters={}, sort_col="start", sort_order="asc"
    )
    assert [r.platform_id for r in vm_asc.rows] == ["P1", "P3", "P2"]


# ---------------------------------------------------------------------------
# Test 4 — malformed date treated as empty (sorts to END)
# ---------------------------------------------------------------------------
def test_malformed_date_sorts_to_end(tmp_path):
    _write_fm(tmp_path, "P1", title="A", start="not-a-date")
    _write_fm(tmp_path, "P2", title="B", start="2026-04-01")
    vm = build_overview_grid_view_model(
        ["P1", "P2"], tmp_path, filters={}, sort_col="start", sort_order="desc"
    )
    assert [r.platform_id for r in vm.rows] == ["P2", "P1"]


# ---------------------------------------------------------------------------
# Test 5 — tiebreaker platform_id ASC (stable for both asc and desc)
# ---------------------------------------------------------------------------
def test_tiebreaker_platform_id_asc_for_both_orders(tmp_path):
    _write_fm(tmp_path, "P1", title="A", start="2026-04-01")
    _write_fm(tmp_path, "P2", title="B", start="2026-04-01")  # same date

    vm_desc = build_overview_grid_view_model(
        ["P1", "P2"], tmp_path, filters={}, sort_col="start", sort_order="desc"
    )
    assert [r.platform_id for r in vm_desc.rows] == ["P1", "P2"]

    vm_asc = build_overview_grid_view_model(
        ["P1", "P2"], tmp_path, filters={}, sort_col="start", sort_order="asc"
    )
    assert [r.platform_id for r in vm_asc.rows] == ["P1", "P2"]


# ---------------------------------------------------------------------------
# Test 6 — title falls back to platform_id (D-OV-09); other missing → None
# ---------------------------------------------------------------------------
def test_title_fallback_to_platform_id_when_no_frontmatter(tmp_path):
    # No content file written for P1 at all.
    vm = build_overview_grid_view_model(
        ["P1"], tmp_path, filters={}, sort_col=None, sort_order=None
    )
    assert len(vm.rows) == 1
    row = vm.rows[0]
    assert row.platform_id == "P1"
    assert row.title == "P1"          # D-OV-09 fallback
    assert row.status is None
    assert row.customer is None
    assert row.has_content is False


# ---------------------------------------------------------------------------
# Test 7 — filter_options sorted alphabetically, deduped
# ---------------------------------------------------------------------------
def test_filter_options_sorted_alphabetically(tmp_path):
    _write_fm(tmp_path, "P1", title="X", status="zebra")
    _write_fm(tmp_path, "P2", title="Y", status="alpha")
    _write_fm(tmp_path, "P3", title="Z", status="mango")
    vm = build_overview_grid_view_model(
        ["P1", "P2", "P3"], tmp_path, filters={}, sort_col=None, sort_order=None
    )
    assert vm.filter_options["status"] == ["alpha", "mango", "zebra"]
    # All 6 keys present
    assert set(vm.filter_options.keys()) == set(FILTERABLE_COLUMNS)


# ---------------------------------------------------------------------------
# Test 8 — filter_options exclude None / empty / em-dash sentinel
# ---------------------------------------------------------------------------
def test_filter_options_exclude_none_and_empty(tmp_path):
    _write_fm(tmp_path, "P1", title="X", status="open")
    # P2 — no content file (status is None)
    _write_fm(tmp_path, "P3", title="Z", status="open")
    vm = build_overview_grid_view_model(
        ["P1", "P2", "P3"], tmp_path, filters={}, sort_col=None, sort_order=None
    )
    assert vm.filter_options["status"] == ["open"]
    # No em-dash sentinel ever appears in filter options.
    assert "—" not in vm.filter_options["status"]


# ---------------------------------------------------------------------------
# Test 9 — multi-filter set membership: AND across columns, OR within a column
# ---------------------------------------------------------------------------
def test_multi_filter_and_across_or_within(tmp_path):
    _write_fm(tmp_path, "P1", title="A", status="open")
    _write_fm(tmp_path, "P2", title="B", status="closed")
    _write_fm(tmp_path, "P3", title="C", status="open", customer="Acme")
    _write_fm(tmp_path, "P4", title="D", status="open", customer="Beta")

    # Filter: status=open → P1, P3, P4 (P2 excluded)
    vm = build_overview_grid_view_model(
        ["P1", "P2", "P3", "P4"], tmp_path,
        filters={"status": ["open"]},
        sort_col=None, sort_order=None,
    )
    assert sorted(r.platform_id for r in vm.rows) == ["P1", "P3", "P4"]

    # AND across columns: status=open AND customer=Acme → only P3
    vm = build_overview_grid_view_model(
        ["P1", "P2", "P3", "P4"], tmp_path,
        filters={"status": ["open"], "customer": ["Acme"]},
        sort_col=None, sort_order=None,
    )
    assert [r.platform_id for r in vm.rows] == ["P3"]

    # OR within column: customer in {Acme, Beta} → P3 and P4
    vm = build_overview_grid_view_model(
        ["P1", "P2", "P3", "P4"], tmp_path,
        filters={"customer": ["Acme", "Beta"]},
        sort_col=None, sort_order=None,
    )
    assert sorted(r.platform_id for r in vm.rows) == ["P3", "P4"]


# ---------------------------------------------------------------------------
# Test 10 — sort by non-date column is case-insensitive
# ---------------------------------------------------------------------------
def test_sort_non_date_case_insensitive(tmp_path):
    _write_fm(tmp_path, "P1", title="X", customer="acme")
    _write_fm(tmp_path, "P2", title="Y", customer="ACME")
    _write_fm(tmp_path, "P3", title="Z", customer="Beta")

    vm = build_overview_grid_view_model(
        ["P1", "P2", "P3"], tmp_path,
        filters={}, sort_col="customer", sort_order="asc",
    )
    # Beta sorts last regardless of case; the two ACME/acme rows come first
    # in some order (deterministic by platform_id ASC tiebreaker).
    assert vm.rows[2].customer == "Beta"
    assert vm.rows[0].customer in {"acme", "ACME"}
    assert vm.rows[1].customer in {"acme", "ACME"}


# ---------------------------------------------------------------------------
# Test 11 — empty curated_pids → empty model with 6 keys present
# ---------------------------------------------------------------------------
def test_empty_curated_pids_returns_empty_model(tmp_path):
    vm = build_overview_grid_view_model(
        [], tmp_path, filters={}, sort_col=None, sort_order=None
    )
    assert vm.rows == []
    assert set(vm.filter_options.keys()) == set(FILTERABLE_COLUMNS)
    assert all(vm.filter_options[c] == [] for c in FILTERABLE_COLUMNS)
    assert vm.active_filter_counts == {c: 0 for c in FILTERABLE_COLUMNS}
    assert vm.has_content_map == {}
    assert vm.sort_col == DEFAULT_SORT_COL == "start"
    assert vm.sort_order == DEFAULT_SORT_ORDER == "desc"


# ---------------------------------------------------------------------------
# Test 12 — active_filter_counts reflects current selection
# ---------------------------------------------------------------------------
def test_active_filter_counts_reflects_selection(tmp_path):
    vm = build_overview_grid_view_model(
        [], tmp_path,
        filters={"status": ["a", "b"], "customer": ["x"]},
        sort_col=None, sort_order=None,
    )
    assert vm.active_filter_counts == {
        "status": 2, "customer": 1, "ap_company": 0,
        "device": 0, "controller": 0, "application": 0,
    }


# ---------------------------------------------------------------------------
# Test 13 — invalid sort_col OR sort_order falls back to defaults
# ---------------------------------------------------------------------------
def test_invalid_sort_col_falls_back_to_default(tmp_path):
    _write_fm(tmp_path, "P1", title="A", start="2026-04-01")
    vm = build_overview_grid_view_model(
        ["P1"], tmp_path, filters={},
        sort_col="link",            # not in SORTABLE_COLUMNS
        sort_order="sideways",      # not in {asc, desc}
    )
    assert vm.sort_col == DEFAULT_SORT_COL
    assert vm.sort_order == DEFAULT_SORT_ORDER


# ---------------------------------------------------------------------------
# Test 14 — has_content_map drives AI Summary disabled state (D-OV-10)
# ---------------------------------------------------------------------------
def test_has_content_map_reflects_file_presence(tmp_path):
    _write_fm(tmp_path, "P1", title="A")  # writes a content file
    # No content file for P2.
    vm = build_overview_grid_view_model(
        ["P1", "P2"], tmp_path, filters={}, sort_col=None, sort_order=None
    )
    assert vm.has_content_map == {"P1": True, "P2": False}
    # row.has_content mirrors the map.
    by_pid = {r.platform_id: r for r in vm.rows}
    assert by_pid["P1"].has_content is True
    assert by_pid["P2"].has_content is False


# ---------------------------------------------------------------------------
# Test 15 — filter_options computed across ALL rows, NOT filtered subset
# ---------------------------------------------------------------------------
def test_filter_options_use_all_rows_not_filtered_subset(tmp_path):
    _write_fm(tmp_path, "P1", title="A", status="open")
    _write_fm(tmp_path, "P2", title="B", status="closed")
    _write_fm(tmp_path, "P3", title="C", status="archived")

    # Apply a filter that narrows rows to P1 only.
    vm = build_overview_grid_view_model(
        ["P1", "P2", "P3"], tmp_path,
        filters={"status": ["open"]},
        sort_col=None, sort_order=None,
    )
    assert [r.platform_id for r in vm.rows] == ["P1"]
    # Picker dropdown MUST still show every status that exists across the
    # full curated list — otherwise the user could not expand selection.
    assert vm.filter_options["status"] == ["archived", "closed", "open"]


# ---------------------------------------------------------------------------
# Bonus invariant tests (constants and module surface)
# ---------------------------------------------------------------------------
def test_constants_filterable_columns_locked():
    assert FILTERABLE_COLUMNS == (
        "status", "customer", "ap_company", "device", "controller", "application",
    )


def test_constants_sortable_columns_has_12_entries_with_dates():
    assert len(SORTABLE_COLUMNS) == 12
    assert "start" in SORTABLE_COLUMNS
    assert "end" in SORTABLE_COLUMNS


def test_overview_row_model_fields():
    # OverviewRow has 15 fields (12 PM + platform_id + has_content + link).
    fields = set(OverviewRow.model_fields.keys())
    expected = {
        "platform_id", "title", "status", "customer", "model_name",
        "ap_company", "ap_model", "device", "controller", "application",
        "assignee", "start", "end", "has_content", "link",
    }
    assert fields == expected


# ---------------------------------------------------------------------------
# D-OV-16 — link sanitizer + frontmatter wiring.
# ---------------------------------------------------------------------------
def test_sanitize_link_drops_dangerous_schemes():
    """D-OV-16: javascript:/data:/vbscript:/file:/about: must return None
    so the template renders the disabled-state Link button instead of an
    XSS-vector href.
    """
    from app_v2.services.overview_grid_service import _sanitize_link
    for raw in (
        "javascript:alert(1)",
        "JavaScript:alert(1)",  # case-insensitive
        "  javascript:void(0)  ",  # leading whitespace
        "data:text/html,<script>alert(1)</script>",
        "vbscript:msgbox(1)",
        "file:///etc/passwd",
        "about:blank",
    ):
        assert _sanitize_link(raw) is None, f"Should reject {raw!r}"


def test_sanitize_link_returns_none_for_empty_input():
    from app_v2.services.overview_grid_service import _sanitize_link
    assert _sanitize_link(None) is None
    assert _sanitize_link("") is None
    assert _sanitize_link("   ") is None
    assert _sanitize_link("\n\t") is None


def test_sanitize_link_keeps_http_https_verbatim():
    from app_v2.services.overview_grid_service import _sanitize_link
    assert _sanitize_link("http://example.com") == "http://example.com"
    assert _sanitize_link("https://example.com/path?q=1") == "https://example.com/path?q=1"
    assert _sanitize_link("HTTPS://Example.Com") == "HTTPS://Example.Com"  # case preserved
    assert _sanitize_link("  https://example.com  ") == "https://example.com"


def test_sanitize_link_promotes_bare_domain_to_https():
    """`link: www.naver.com` (no scheme) → https://www.naver.com so the
    rendered <a href="..."> opens the external site, not a relative path.
    """
    from app_v2.services.overview_grid_service import _sanitize_link
    assert _sanitize_link("www.naver.com") == "https://www.naver.com"
    assert _sanitize_link("naver.com") == "https://naver.com"
    assert _sanitize_link("naver.com/path") == "https://naver.com/path"


def test_sanitize_link_promotes_protocol_relative_to_https():
    from app_v2.services.overview_grid_service import _sanitize_link
    assert _sanitize_link("//example.com/x") == "https://example.com/x"


def test_link_field_populated_from_frontmatter(tmp_path):
    """End-to-end: build_overview_grid_view_model reads `link:` from
    frontmatter, sanitizes it, and surfaces it on OverviewRow.link.
    Missing `link:` in frontmatter → row.link is None.
    """
    cd = tmp_path / "content"
    cd.mkdir()
    _write_fm(cd, "P1", title="Has link", link="www.naver.com")
    _write_fm(cd, "P2", title="No link")  # no link key
    _write_fm(cd, "P3", title="Bad link", link="javascript:alert(1)")

    vm = build_overview_grid_view_model(["P1", "P2", "P3"], cd)
    by_pid = {r.platform_id: r for r in vm.rows}
    assert by_pid["P1"].link == "https://www.naver.com"  # promoted
    assert by_pid["P2"].link is None                      # missing → None
    assert by_pid["P3"].link is None                      # dangerous → None
