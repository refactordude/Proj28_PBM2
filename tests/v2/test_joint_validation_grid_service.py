"""Tests for app_v2/services/joint_validation_grid_service.py — D-JV-05, D-JV-10, D-JV-11, D-JV-15."""
from __future__ import annotations

from pathlib import Path

import pytest

from app_v2.services.joint_validation_grid_service import (
    DEFAULT_SORT_COL,
    DEFAULT_SORT_ORDER,
    FILTERABLE_COLUMNS,
    JointValidationGridViewModel,
    JointValidationRow,
    SORTABLE_COLUMNS,
    _sanitize_link,
    build_joint_validation_grid_view_model,
)
from app_v2.services.joint_validation_store import clear_parse_cache


@pytest.fixture(autouse=True)
def _reset_cache():
    clear_parse_cache()
    yield
    clear_parse_cache()


def _write_jv(root: Path, page_id: str, *, title: str = "T", status: str = "",
              customer: str = "", start: str = "", end: str = "",
              link: str = "") -> None:
    folder = root / page_id
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    if status:
        rows.append(f"<tr><th><strong>Status</strong></th><td>{status}</td></tr>")
    if customer:
        rows.append(f"<tr><th><strong>Customer</strong></th><td>{customer}</td></tr>")
    if start:
        rows.append(f"<tr><th><strong>Start</strong></th><td>{start}</td></tr>")
    if end:
        rows.append(f"<tr><th><strong>End</strong></th><td>{end}</td></tr>")
    if link:
        rows.append(f'<tr><th><strong>Report Link</strong></th><td><a href="{link}">L</a></td></tr>')
    if title:
        body = "<h1>" + title + "</h1><table>" + "".join(rows) + "</table>"
    else:
        body = "<table>" + "".join(rows) + "</table>"
    (folder / "index.html").write_text(f"<html><body>{body}</body></html>", encoding="utf-8")


def test_view_model_shape(tmp_path: Path) -> None:
    _write_jv(tmp_path, "111", title="A", status="X")
    vm = build_joint_validation_grid_view_model(tmp_path)
    assert isinstance(vm, JointValidationGridViewModel)
    assert isinstance(vm.rows[0], JointValidationRow)
    assert set(vm.filter_options.keys()) == set(FILTERABLE_COLUMNS)
    assert set(vm.active_filter_counts.keys()) == set(FILTERABLE_COLUMNS)


def test_default_sort_start_desc_tiebreaker_page_id_asc(tmp_path: Path) -> None:
    _write_jv(tmp_path, "111", title="A", start="2026-03-15")
    _write_jv(tmp_path, "999", title="C", start="2026-04-01")
    _write_jv(tmp_path, "222", title="B", start="2026-04-01")
    vm = build_joint_validation_grid_view_model(tmp_path)
    assert [r.confluence_page_id for r in vm.rows] == ["222", "999", "111"]


def test_blank_start_sorts_to_end_regardless_of_order(tmp_path: Path) -> None:
    _write_jv(tmp_path, "1", title="A", start="2026-04-01")
    _write_jv(tmp_path, "2", title="B", start="")
    _write_jv(tmp_path, "3", title="C", start="2026-03-15")
    vm_desc = build_joint_validation_grid_view_model(tmp_path, sort_col="start", sort_order="desc")
    assert vm_desc.rows[-1].confluence_page_id == "2"
    vm_asc = build_joint_validation_grid_view_model(tmp_path, sort_col="start", sort_order="asc")
    assert vm_asc.rows[-1].confluence_page_id == "2"


def test_filter_status_in_progress_excludes_others(tmp_path: Path) -> None:
    _write_jv(tmp_path, "1", title="A", status="In Progress")
    _write_jv(tmp_path, "2", title="B", status="Done")
    _write_jv(tmp_path, "3", title="C", status="Blocked")
    vm = build_joint_validation_grid_view_model(tmp_path, filters={"status": ["In Progress"]})
    assert len(vm.rows) == 1
    assert vm.rows[0].status == "In Progress"


def test_six_filter_options_enumerated_from_full_set(tmp_path: Path) -> None:
    _write_jv(tmp_path, "1", title="A", status="X")
    _write_jv(tmp_path, "2", title="B", status="Y")
    vm = build_joint_validation_grid_view_model(tmp_path, filters={"status": ["X"]})
    # filter_options should still show both "X" and "Y" — built from full set
    assert sorted(vm.filter_options["status"]) == ["X", "Y"]


def test_sanitize_link_drops_javascript_scheme() -> None:
    assert _sanitize_link("javascript:alert(1)") is None
    assert _sanitize_link("DATA:text/html,evil") is None
    assert _sanitize_link("vbscript:msgbox") is None
    assert _sanitize_link("file:///etc/passwd") is None
    assert _sanitize_link("about:blank") is None


def test_sanitize_link_promotes_bare_domain_to_https() -> None:
    out = _sanitize_link("confluence.example.com/page")
    assert out == "https://confluence.example.com/page"
    assert _sanitize_link("https://example.com") == "https://example.com"
    assert _sanitize_link("http://example.com") == "http://example.com"


def test_title_fallback_to_page_id_when_h1_missing(tmp_path: Path) -> None:
    _write_jv(tmp_path, "999", title="", status="X")  # title="" → no <h1>
    vm = build_joint_validation_grid_view_model(tmp_path)
    assert vm.rows[0].title == "999"


def test_active_filter_counts_match_input(tmp_path: Path) -> None:
    _write_jv(tmp_path, "1", title="A", status="A")
    vm = build_joint_validation_grid_view_model(
        tmp_path,
        filters={"status": ["A", "B"], "customer": ["X"]},
    )
    assert vm.active_filter_counts == {
        "status": 2, "customer": 1, "ap_company": 0,
        "device": 0, "controller": 0, "application": 0,
    }


def test_invalid_sort_col_falls_back_to_default(tmp_path: Path) -> None:
    _write_jv(tmp_path, "1", title="A", start="2026-03-15")
    vm = build_joint_validation_grid_view_model(tmp_path, sort_col="link")
    assert vm.sort_col == DEFAULT_SORT_COL


def test_empty_jv_root_returns_zero_rows(tmp_path: Path) -> None:
    vm = build_joint_validation_grid_view_model(tmp_path)
    assert vm.rows == []
    assert vm.total_count == 0
    assert vm.filter_options == {c: [] for c in FILTERABLE_COLUMNS}


def test_link_field_default_none_when_no_report_link(tmp_path: Path) -> None:
    _write_jv(tmp_path, "1", title="A")  # no link in fixture
    vm = build_joint_validation_grid_view_model(tmp_path)
    assert vm.rows[0].link is None
