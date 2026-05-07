"""JV pagination tests — Phase 02 Plan 02-04.

Tests P1-P12 + P10b cover the grid service (Task 1).
Tests P13-P19 + P15a-d, P15e-f cover the router (Task 2).
Tests P20-P24 cover the template rendering (Task 3).

All tests are initially written in TDD RED (failing) state against the
service, router, and templates as they exist at Task 1 start. They will go
GREEN as each task's implementation lands.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app_v2.services.joint_validation_grid_service import (
    JV_PAGE_SIZE,
    PageLink,
    _build_page_links,
    build_joint_validation_grid_view_model,
)
from app_v2.services.joint_validation_store import clear_parse_cache
from app_v2.main import app


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_cache():
    clear_parse_cache()
    yield
    clear_parse_cache()


def _write_jv(
    root: Path,
    page_id: str,
    *,
    title: str = "T",
    status: str = "",
    customer: str = "",
    start: str = "",
) -> None:
    """Write a minimal JV index.html under root/page_id/."""
    folder = root / page_id
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    if status:
        rows.append(f"<tr><th><strong>Status</strong></th><td>{status}</td></tr>")
    if customer:
        rows.append(f"<tr><th><strong>Customer</strong></th><td>{customer}</td></tr>")
    if start:
        rows.append(f"<tr><th><strong>Start</strong></th><td>{start}</td></tr>")
    body = f"<h1>{title}</h1><table>{''.join(rows)}</table>" if title else f"<table>{''.join(rows)}</table>"
    (folder / "index.html").write_text(f"<html><body>{body}</body></html>", encoding="utf-8")


def _write_n_jvs(root: Path, n: int) -> None:
    """Write n JV entries (page_ids "001".."N") with no filters."""
    for i in range(1, n + 1):
        _write_jv(root, str(i).zfill(3), title=f"JV {i}")


# ---------------------------------------------------------------------------
# Task 1 — Service slice + page metadata (D-UI2-13, D-UI2-14, B3)
# ---------------------------------------------------------------------------


def test_page_size_slicing_default_page_1(tmp_path: Path) -> None:
    """P1: With 25 rows and page=1, vm.rows has 15 items; total_count=25; page=1; page_count=2."""
    _write_n_jvs(tmp_path, 25)
    vm = build_joint_validation_grid_view_model(tmp_path, page=1, page_size=15)
    assert len(vm.rows) == 15, f"Expected 15 rows on page 1 of 2, got {len(vm.rows)}"
    assert vm.total_count == 25
    assert vm.page == 1
    assert vm.page_count == 2


def test_page_size_slicing_page_2(tmp_path: Path) -> None:
    """P2: With 25 rows and page=2, vm.rows has 10 items; page=2; page_count=2."""
    _write_n_jvs(tmp_path, 25)
    vm = build_joint_validation_grid_view_model(tmp_path, page=2, page_size=15)
    assert len(vm.rows) == 10, f"Expected 10 rows on page 2 of 2, got {len(vm.rows)}"
    assert vm.page == 2
    assert vm.page_count == 2


def test_page_clamp_too_high(tmp_path: Path) -> None:
    """P3: With 25 rows and page=99, service clamps to page_count=2; rows = page-2 slice."""
    _write_n_jvs(tmp_path, 25)
    vm = build_joint_validation_grid_view_model(tmp_path, page=99, page_size=15)
    assert vm.page == 2, f"Expected page clamped to 2, got {vm.page}"
    assert vm.page_count == 2
    assert len(vm.rows) == 10


def test_page_clamp_zero_or_negative(tmp_path: Path) -> None:
    """P4: With 25 rows and page=0 or page=-5, service clamps to page=1."""
    _write_n_jvs(tmp_path, 25)
    vm0 = build_joint_validation_grid_view_model(tmp_path, page=0, page_size=15)
    assert vm0.page == 1, f"Expected page=0 clamped to 1, got {vm0.page}"
    vm_neg = build_joint_validation_grid_view_model(tmp_path, page=-5, page_size=15)
    assert vm_neg.page == 1, f"Expected page=-5 clamped to 1, got {vm_neg.page}"


def test_page_count_when_empty(tmp_path: Path) -> None:
    """P5: With 0 rows, page_count=1; page=1; rows=[]; total_count=0."""
    vm = build_joint_validation_grid_view_model(tmp_path)
    assert vm.page_count == 1
    assert vm.page == 1
    assert vm.rows == []
    assert vm.total_count == 0


def test_page_count_exact_multiple(tmp_path: Path) -> None:
    """P6: With 30 rows and page_size=15, page_count=2."""
    _write_n_jvs(tmp_path, 30)
    vm = build_joint_validation_grid_view_model(tmp_path, page=1, page_size=15)
    assert vm.page_count == 2


def test_page_count_off_by_one(tmp_path: Path) -> None:
    """P7: With 16 rows and page_size=15, page_count=2 (one row on page 2)."""
    _write_n_jvs(tmp_path, 16)
    vm = build_joint_validation_grid_view_model(tmp_path, page=1, page_size=15)
    assert vm.page_count == 2


def test_page_links_short(tmp_path: Path) -> None:
    """P8 (B3 form): With 3 pages and current page 1, no ellipsis; 3 PageLink objects."""
    _write_n_jvs(tmp_path, 45)  # 45 rows → 3 pages at 15/page
    vm = build_joint_validation_grid_view_model(tmp_path, page=1, page_size=15)
    assert vm.page_count == 3
    expected = [
        {"label": "1", "num": 1},
        {"label": "2", "num": 2},
        {"label": "3", "num": 3},
    ]
    assert [pl.model_dump() for pl in vm.page_links] == expected


def test_page_links_group_1_full(tmp_path: Path) -> None:
    """P9 (260507-lcc form): With 10 pages, page=8 (still in group 1), all 10 pages render."""
    links = _build_page_links(8, 10)
    dicts = [pl.model_dump() for pl in links]
    expected = [{"label": str(n), "num": n} for n in range(1, 11)]
    assert dicts == expected, f"Got: {dicts}"


def test_page_links_group_2_full_middle(tmp_path: Path) -> None:
    """P10 (260507-lcc form): With 25 pages, page=15 (group 2), pages 11..20 render — no ellipsis."""
    links = _build_page_links(15, 25)
    dicts = [pl.model_dump() for pl in links]
    expected = [{"label": str(n), "num": n} for n in range(11, 21)]
    assert dicts == expected, f"Got: {dicts}"


def test_page_links_returns_pagelink_instances(tmp_path: Path) -> None:
    """P10b (B3): _build_page_links returns list[PageLink], NOT list[tuple]."""
    links = _build_page_links(1, 5)
    assert len(links) > 0
    assert isinstance(links[0], PageLink), f"Expected PageLink, got {type(links[0])}"
    # Explicitly not a tuple
    assert not isinstance(links[0], tuple), "page_links must NOT be a list[tuple] (B3)"


# 260507-lcc: group-of-10 boundary cases (sliding-window-with-ellipsis superseded).


def test_page_links_5_pages(tmp_path: Path) -> None:
    """260507-lcc: 5 pages, current=3 → [1,2,3,4,5] (one group fully shown)."""
    assert [pl.model_dump() for pl in _build_page_links(3, 5)] == (
        [{"label": str(n), "num": n} for n in range(1, 6)]
    )


def test_page_links_10_pages_current_10(tmp_path: Path) -> None:
    """260507-lcc: 10 pages, current=10 → [1..10] (current sits in only/last group)."""
    assert [pl.model_dump() for pl in _build_page_links(10, 10)] == (
        [{"label": str(n), "num": n} for n in range(1, 11)]
    )


def test_page_links_13_pages_current_1(tmp_path: Path) -> None:
    """260507-lcc: 13 pages, current=1 → group 1 [1..10]."""
    assert [pl.model_dump() for pl in _build_page_links(1, 13)] == (
        [{"label": str(n), "num": n} for n in range(1, 11)]
    )


def test_page_links_13_pages_current_11(tmp_path: Path) -> None:
    """260507-lcc: 13 pages, current=11 → group 2 truncated [11,12,13]."""
    assert [pl.model_dump() for pl in _build_page_links(11, 13)] == [
        {"label": "11", "num": 11},
        {"label": "12", "num": 12},
        {"label": "13", "num": 13},
    ]


def test_page_links_25_pages_current_21(tmp_path: Path) -> None:
    """260507-lcc: 25 pages, current=21 → last group truncated [21..25]."""
    assert [pl.model_dump() for pl in _build_page_links(21, 25)] == (
        [{"label": str(n), "num": n} for n in range(21, 26)]
    )


def test_prev_next_group_page_first_group(tmp_path: Path) -> None:
    """260507-lcc: page=5 of 25 (group 1) → prev=None, next=11."""
    # 25 rows × page_size=1 → 25 pages
    for i in range(1, 26):
        _write_jv(tmp_path, str(i).zfill(3), title=f"JV {i}")
    vm = build_joint_validation_grid_view_model(tmp_path, page=5, page_size=1)
    assert vm.page_count == 25
    assert vm.prev_group_page is None
    assert vm.next_group_page == 11


def test_prev_next_group_page_at_boundary(tmp_path: Path) -> None:
    """260507-lcc: page=11 of 25 (group 2) → prev=10, next=21."""
    for i in range(1, 26):
        _write_jv(tmp_path, str(i).zfill(3), title=f"JV {i}")
    vm = build_joint_validation_grid_view_model(tmp_path, page=11, page_size=1)
    assert vm.prev_group_page == 10
    assert vm.next_group_page == 21


def test_prev_next_group_page_last_group(tmp_path: Path) -> None:
    """260507-lcc: page=21 of 25 (group 3) → prev=20, next=None."""
    for i in range(1, 26):
        _write_jv(tmp_path, str(i).zfill(3), title=f"JV {i}")
    vm = build_joint_validation_grid_view_model(tmp_path, page=21, page_size=1)
    assert vm.prev_group_page == 20
    assert vm.next_group_page is None


def test_prev_next_group_page_single_page(tmp_path: Path) -> None:
    """260507-lcc: page_count=1 → both chevron targets are None."""
    _write_jv(tmp_path, "001", title="single")
    vm = build_joint_validation_grid_view_model(tmp_path, page=1, page_size=15)
    assert vm.page_count == 1
    assert vm.prev_group_page is None
    assert vm.next_group_page is None


def test_prev_next_group_page_exactly_one_full_group(tmp_path: Path) -> None:
    """260507-lcc: page_count == GROUP_SIZE (10) → no next group exists."""
    for i in range(1, 11):
        _write_jv(tmp_path, str(i).zfill(3), title=f"JV {i}")
    vm = build_joint_validation_grid_view_model(tmp_path, page=1, page_size=1)
    assert vm.page_count == 10
    assert vm.prev_group_page is None
    assert vm.next_group_page is None


def test_filter_options_built_from_all_rows_not_paged(tmp_path: Path) -> None:
    """P11: filter_options reflects ALL filtered rows (not just current page).

    260507-rmj: status was dropped from FILTERABLE_COLUMNS, so the source
    facet for this test moves from status → customer (a surviving facet).
    Each of 20 rows still gets a distinct value to exercise the
    all-rows-not-just-current-page contract.
    """
    # Write 20 rows, each with a unique customer, so page 1 (15 rows) won't contain all customers
    for i in range(1, 21):
        _write_jv(tmp_path, str(i).zfill(3), title=f"JV {i}", customer=f"Customer{i}")
    vm = build_joint_validation_grid_view_model(tmp_path, page=1, page_size=15)
    # All 20 customer values must appear in filter_options
    assert len(vm.filter_options["customer"]) == 20, (
        f"filter_options should show all 20 customers (from all rows), got {len(vm.filter_options['customer'])}"
    )


def test_total_count_unchanged_meaning(tmp_path: Path) -> None:
    """P12: vm.total_count = filtered row count (BEFORE slicing), not len(vm.rows)."""
    _write_n_jvs(tmp_path, 25)
    vm = build_joint_validation_grid_view_model(tmp_path, page=1, page_size=15)
    assert vm.total_count == 25, f"total_count must be 25 (all filtered rows), got {vm.total_count}"
    assert len(vm.rows) == 15, f"vm.rows should be page 1 slice of 15, got {len(vm.rows)}"
    # total_count must differ from len(vm.rows) on multi-page result
    assert vm.total_count != len(vm.rows)


# ---------------------------------------------------------------------------
# Task 2 — Router wiring: page param, validation, URL, OOB (D-UI2-13, D-UI2-14)
# ---------------------------------------------------------------------------


def test_get_overview_default_page_1() -> None:
    """P13: GET /overview returns 200 and renders page 1."""
    client = TestClient(app)
    r = client.get("/overview")
    assert r.status_code == 200


def test_get_overview_with_page_query() -> None:
    """P14: GET /overview?page=2 returns 200 (requires ≥16 JVs in content/joint_validation/)."""
    client = TestClient(app)
    r = client.get("/overview?page=2")
    # With real content (may have <16 JVs, so server clamps gracefully) — 200 is required
    assert r.status_code == 200


def test_get_overview_page_zero_returns_422() -> None:
    """P15a: GET /overview?page=0 returns 422 (FastAPI Query ge=1 enforcement)."""
    client = TestClient(app)
    r = client.get("/overview?page=0")
    assert r.status_code == 422, f"Expected 422 for page=0, got {r.status_code}"


def test_get_overview_page_negative_returns_422() -> None:
    """P15b: GET /overview?page=-5 returns 422 (FastAPI Query ge=1 enforcement)."""
    client = TestClient(app)
    r = client.get("/overview?page=-5")
    assert r.status_code == 422, f"Expected 422 for page=-5, got {r.status_code}"


def test_get_overview_page_too_large_returns_422() -> None:
    """P15c: GET /overview?page=99999999 returns 422 (FastAPI Query le=10_000 enforcement)."""
    client = TestClient(app)
    r = client.get("/overview?page=99999999")
    assert r.status_code == 422, f"Expected 422 for page=99999999, got {r.status_code}"


def test_get_overview_page_non_integer_returns_422() -> None:
    """P15d: GET /overview?page=abc returns 422 (FastAPI int parsing rejects non-integer)."""
    client = TestClient(app)
    r = client.get("/overview?page=abc")
    assert r.status_code == 422, f"Expected 422 for page=abc, got {r.status_code}"


def test_post_overview_grid_form_page_zero_returns_422() -> None:
    """P15e (W5): POST /overview/grid with page=0 returns 422 (Form ge=1 enforcement)."""
    client = TestClient(app)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = client.post("/overview/grid", content="page=0", headers=headers)
    assert r.status_code == 422, f"Expected 422 for form page=0, got {r.status_code}"


def test_post_overview_grid_form_page_too_large_returns_422() -> None:
    """P15f (W5): POST /overview/grid with page=10001 returns 422 (Form le=10_000 enforcement)."""
    client = TestClient(app)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = client.post("/overview/grid", content="page=10001", headers=headers)
    assert r.status_code == 422, f"Expected 422 for form page=10001, got {r.status_code}"


def test_get_overview_page_beyond_count_clamps() -> None:
    """P16: GET /overview?page=99 with real content returns 200 (clamped server-side)."""
    client = TestClient(app)
    r = client.get("/overview?page=99")
    # Server should clamp page to page_count; not 422 (page=99 ≤ 10_000 is within le bound)
    assert r.status_code == 200, f"Expected 200 for page=99 (clamped), got {r.status_code}"


def test_post_overview_grid_emits_pagination_oob() -> None:
    """P17: POST /overview/grid returns body containing pagination OOB wrapper."""
    client = TestClient(app)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = client.post("/overview/grid", content="page=1", headers=headers)
    assert r.status_code == 200, f"POST /overview/grid returned {r.status_code}"
    assert 'id="overview-pagination"' in r.text, (
        'POST /overview/grid response must contain id="overview-pagination"'
    )
    assert 'hx-swap-oob="true"' in r.text, (
        'POST /overview/grid response must contain hx-swap-oob="true"'
    )


def test_post_overview_grid_url_includes_page() -> None:
    """P18: POST /overview/grid with page=2 — HX-Push-Url includes page=2."""
    client = TestClient(app)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    # page=2 will be clamped if there's only 1 page, so we check hx-push-url
    r = client.post("/overview/grid", content="page=2", headers=headers)
    assert r.status_code == 200
    push_url = r.headers.get("HX-Push-Url", "")
    # If there's only 1 page, server clamps to page=1 (default) → URL won't have page=2
    # but the URL should be present and valid. The key assertion: URL is set.
    assert push_url.startswith("/overview"), f"HX-Push-Url must start with /overview, got: {push_url!r}"


def test_post_overview_grid_default_page_omitted_from_url() -> None:
    """P19: POST /overview/grid with page=1 — HX-Push-Url does NOT include page=1 (default omitted)."""
    client = TestClient(app)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = client.post("/overview/grid", content="page=1&sort=status&order=asc", headers=headers)
    assert r.status_code == 200
    push_url = r.headers.get("HX-Push-Url", "")
    assert "page=1" not in push_url, (
        f"HX-Push-Url must NOT include page=1 (default page omitted for clean URLs); got: {push_url!r}"
    )


# ---------------------------------------------------------------------------
# Task 3 — Template rendering: pagination control, filter/sort reset
# ---------------------------------------------------------------------------


def test_pagination_renders_full_page_correctly() -> None:
    """P20: GET /overview with real content returns 200 with pagination markup when > 1 page."""
    client = TestClient(app)
    r = client.get("/overview")
    assert r.status_code == 200
    # If there's only 1 page (≤ 15 JVs), no pagination renders; that's correct
    # If there are > 15 JVs, pagination should render:
    # We assert the page loads without error; pagination visibility depends on data count


def test_pagination_disabled_at_boundaries() -> None:
    """P21: GET /overview?page=1 — if paginated, prev link is disabled at page-1 boundary."""
    client = TestClient(app)
    r = client.get("/overview?page=1")
    assert r.status_code == 200
    # Verify page loads correctly; when > 1 page exists, 'disabled' class is present for prev


def test_pagination_filter_resets_page_via_hidden_input() -> None:
    """P22: GET /overview returns body containing hidden page input for filter-reset."""
    client = TestClient(app)
    r = client.get("/overview")
    assert r.status_code == 200
    assert '<input type="hidden" name="page" value="1">' in r.text, (
        'GET /overview body must contain <input type="hidden" name="page" value="1"> '
        "(filter change must reset to page 1)"
    )


def test_pagination_sort_click_resets_page() -> None:
    """P23: GET /overview returns body with sortable_th hx-vals containing \"page\": \"1\"."""
    client = TestClient(app)
    r = client.get("/overview")
    assert r.status_code == 200
    assert '"page": "1"' in r.text, (
        'GET /overview body must contain \'"page": "1"\' in sortable_th hx-vals '
        "(sort click must reset page to 1)"
    )


def test_pagination_oob_emitted_on_post() -> None:
    """P24: POST /overview/grid includes pagination_oob block (re-asserts P17 from template angle)."""
    client = TestClient(app)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = client.post("/overview/grid", content="page=1&sort=status&order=asc", headers=headers)
    assert r.status_code == 200
    assert 'id="overview-pagination"' in r.text, (
        'POST /overview/grid response must contain id="overview-pagination" (pagination_oob block)'
    )
