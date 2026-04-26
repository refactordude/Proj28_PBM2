"""Pure-Python unit tests for app_v2.services.browse_service.

No DB calls. The cache layer (`fetch_cells`, `list_platforms`, `list_parameters`)
is mocked at the call site (the symbols re-bound inside browse_service, NOT at
the source module — Pitfall 11 of test reliability: mocker.patch must target
the importing module).

Covers:
- D-13 ' · ' middle-dot separator (NOT v1.0 ' / ' — Pitfall 3)
- D-23 row_cap=200 / col_cap=30
- D-29 aggfunc='first' (delegated to pivot_to_wide_core)
- D-30..D-33 URL round-trip composition
- Empty-selection short-circuit (no DB call when either dimension empty)
- Garbage-label defense (silently dropped — T-04-02-02 mitigation)
"""
from __future__ import annotations

import pandas as pd
import pytest

from app_v2.services import browse_service
from app_v2.services.browse_service import (
    BrowseViewModel,
    PARAM_LABEL_SEP,
    _build_browse_url,
    _parse_param_label,
    build_view_model,
)


# ---------------------------------------------------------------------------
# Tests 1-4: PARAM_LABEL_SEP and _parse_param_label
# ---------------------------------------------------------------------------

def test_param_label_round_trip():
    """Test 1: split 'attribute · vendor_id' returns ('attribute', 'vendor_id')."""
    assert _parse_param_label("attribute · vendor_id") == ("attribute", "vendor_id")


def test_param_label_no_separator_returns_none():
    """Test 2: malformed label returns None (silently dropped)."""
    assert _parse_param_label("noseparator") is None


def test_param_label_split_first_only():
    """Test 3: maxsplit=1 — extra ' · ' inside the Item half is preserved."""
    assert _parse_param_label("a · b · c") == ("a", "b · c")


def test_param_label_sep_is_middle_dot():
    """Test 4: separator is exactly ' · ' — middle dot U+00B7 with surrounding spaces."""
    assert PARAM_LABEL_SEP == " · "
    assert PARAM_LABEL_SEP == " · "
    # Defense in depth: the v1.0 ' / ' separator must NOT be the value.
    assert PARAM_LABEL_SEP != " / "


# ---------------------------------------------------------------------------
# Tests 5-6: empty-selection short-circuit (no DB call)
# ---------------------------------------------------------------------------

def test_build_view_model_empty_selection_no_fetch(mocker):
    """Test 5: both dimensions empty → is_empty_selection=True, fetch_cells NOT called."""
    db = object()  # sentinel — non-None but never used (short-circuit before DB)
    mock_list_platforms = mocker.patch.object(
        browse_service, "list_platforms", return_value=["P1", "P2"]
    )
    mock_list_parameters = mocker.patch.object(
        browse_service,
        "list_parameters",
        return_value=[{"InfoCategory": "attribute", "Item": "vendor_id"}],
    )
    mock_fetch_cells = mocker.patch.object(browse_service, "fetch_cells")

    vm = build_view_model(
        db,
        db_name="x",
        selected_platforms=[],
        selected_param_labels=[],
        swap_axes=False,
    )

    assert vm.is_empty_selection is True
    assert vm.df_wide.empty
    assert vm.n_rows == 0
    assert vm.n_cols == 0
    assert vm.row_capped is False
    assert vm.col_capped is False
    # Catalog calls happen even on empty selection (popovers need full lists).
    mock_list_platforms.assert_called_once()
    mock_list_parameters.assert_called_once()
    # But fetch_cells must NOT be called — short-circuit (DATA-05 echo).
    mock_fetch_cells.assert_not_called()


def test_build_view_model_partial_empty_still_short_circuits(mocker):
    """Test 6: platforms=[] but params=['a · b'] → still empty (BOTH must be present)."""
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=[])
    mocker.patch.object(browse_service, "list_parameters", return_value=[])
    mock_fetch_cells = mocker.patch.object(browse_service, "fetch_cells")

    vm = build_view_model(
        db,
        db_name="x",
        selected_platforms=[],
        selected_param_labels=["a · b"],
        swap_axes=False,
    )

    assert vm.is_empty_selection is True
    mock_fetch_cells.assert_not_called()


# ---------------------------------------------------------------------------
# Test 7: fetch_cells called with the right tuples (sorted, unique, parsed)
# ---------------------------------------------------------------------------

def test_build_view_model_fetch_cells_args(mocker):
    """Test 7: valid selection → fetch_cells called once with sorted unique tuples."""
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=["P1", "P2"])
    mocker.patch.object(
        browse_service,
        "list_parameters",
        return_value=[
            {"InfoCategory": "attribute", "Item": "vendor_id"},
            {"InfoCategory": "flags", "Item": "f1"},
        ],
    )
    df_long = pd.DataFrame({
        "PLATFORM_ID": ["P1"],
        "InfoCategory": ["attribute"],
        "Item": ["vendor_id"],
        "Result": ["0xA1"],
    })
    mock_fetch_cells = mocker.patch.object(
        browse_service, "fetch_cells", return_value=(df_long, False)
    )

    build_view_model(
        db,
        db_name="x",
        selected_platforms=["P2", "P1"],  # NOT pre-sorted
        # Two labels with the same InfoCategory — verify de-duplication.
        selected_param_labels=["attribute · vendor_id", "attribute · vendor_id"],
        swap_axes=False,
    )

    mock_fetch_cells.assert_called_once_with(
        db,
        ("P2", "P1"),  # platforms passed in input order (not sorted)
        ("attribute",),  # de-duplicated + sorted
        ("vendor_id",),
        row_cap=200,
        db_name="x",
    )


# ---------------------------------------------------------------------------
# Tests 8-10: cap signaling and swap-axes index column
# ---------------------------------------------------------------------------

def _make_long_df():
    """2 platforms × 2 (cat, item) → fully populated long-form DataFrame."""
    return pd.DataFrame({
        "PLATFORM_ID": ["P1", "P1", "P2", "P2"],
        "InfoCategory": ["attribute", "flags", "attribute", "flags"],
        "Item": ["vendor_id", "f1", "vendor_id", "f1"],
        "Result": ["0xA1", "1", "0xA2", "0"],
    })


def test_build_view_model_row_capped_signal(mocker):
    """Test 8: fetch_cells returns row_capped=True → vm.row_capped=True."""
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=["P1", "P2"])
    mocker.patch.object(
        browse_service,
        "list_parameters",
        return_value=[
            {"InfoCategory": "attribute", "Item": "vendor_id"},
            {"InfoCategory": "flags", "Item": "f1"},
        ],
    )
    mocker.patch.object(
        browse_service, "fetch_cells", return_value=(_make_long_df(), True)
    )

    vm = build_view_model(
        db,
        db_name="x",
        selected_platforms=["P1", "P2"],
        selected_param_labels=["attribute · vendor_id", "flags · f1"],
        swap_axes=False,
    )

    assert vm.row_capped is True
    assert vm.is_empty_selection is False


def test_build_view_model_col_capped_signal(mocker):
    """Test 9: pivot_to_wide_core returns col_capped=True → vm.col_capped=True
    AND n_value_cols_total equals the number of selected param labels."""
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=["P1"])
    mocker.patch.object(browse_service, "list_parameters", return_value=[])
    mocker.patch.object(
        browse_service, "fetch_cells", return_value=(_make_long_df(), False)
    )
    capped_wide = pd.DataFrame({"PLATFORM_ID": ["P1"], "vendor_id": ["0xA1"]})
    mocker.patch.object(
        browse_service, "pivot_to_wide_core", return_value=(capped_wide, True)
    )

    selected_params = [
        f"flags · f{i}" for i in range(35)  # 35 params requested → triggers col cap
    ]
    vm = build_view_model(
        db,
        db_name="x",
        selected_platforms=["P1"],
        selected_param_labels=selected_params,
        swap_axes=False,
    )

    assert vm.col_capped is True
    assert vm.n_value_cols_total == 35  # the N for "Showing first 30 of {N}"
    assert vm.n_cols == 1  # value-cols actually shown (capped grid has 1 value col)


def test_build_view_model_index_col_swap(mocker):
    """Test 10: swap_axes flips index_col_name between PLATFORM_ID and Item."""
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=["P1"])
    mocker.patch.object(browse_service, "list_parameters", return_value=[])
    mocker.patch.object(
        browse_service, "fetch_cells", return_value=(_make_long_df(), False)
    )

    # swap_axes=False → "PLATFORM_ID"
    vm_normal = build_view_model(
        db,
        db_name="x",
        selected_platforms=["P1", "P2"],
        selected_param_labels=["attribute · vendor_id"],
        swap_axes=False,
    )
    assert vm_normal.index_col_name == "PLATFORM_ID"

    # swap_axes=True → "Item"
    vm_swapped = build_view_model(
        db,
        db_name="x",
        selected_platforms=["P1", "P2"],
        selected_param_labels=["attribute · vendor_id"],
        swap_axes=True,
    )
    assert vm_swapped.index_col_name == "Item"


# ---------------------------------------------------------------------------
# Test 11: all_param_labels sort by combined label (D-13)
# ---------------------------------------------------------------------------

def test_all_param_labels_sorted_by_combined_label(mocker):
    """Test 11: 'attribute · zzz' sorts BEFORE 'flags · aaa' (combined-label sort)."""
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=[])
    mocker.patch.object(
        browse_service,
        "list_parameters",
        return_value=[
            {"InfoCategory": "flags", "Item": "aaa"},
            {"InfoCategory": "attribute", "Item": "zzz"},
        ],
    )
    mocker.patch.object(browse_service, "fetch_cells")

    vm = build_view_model(
        db,
        db_name="x",
        selected_platforms=[],
        selected_param_labels=[],
        swap_axes=False,
    )

    assert vm.all_param_labels == ["attribute · zzz", "flags · aaa"]


# ---------------------------------------------------------------------------
# Test 12: garbage labels silently filtered before SQL bind
# ---------------------------------------------------------------------------

def test_build_view_model_garbage_labels_filtered(mocker):
    """Test 12: malformed labels (no separator) drop out before fetch_cells.

    Defense for T-04-02-02: a URL with `?params=garbage` must produce
    infocategories=() / items=() — never inject empty strings into SQL.
    """
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=["P1"])
    mocker.patch.object(browse_service, "list_parameters", return_value=[])
    mock_fetch_cells = mocker.patch.object(
        browse_service, "fetch_cells", return_value=(pd.DataFrame(), False)
    )

    build_view_model(
        db,
        db_name="x",
        selected_platforms=["P1"],
        # mix: one valid, one garbage, one another valid
        selected_param_labels=[
            "attribute · vendor_id",
            "garbage_no_sep",
            "flags · f1",
        ],
        swap_axes=False,
    )

    # Only the well-formed pairs reach the SQL layer.
    args, kwargs = mock_fetch_cells.call_args
    # signature: fetch_cells(db, platforms, infocategories, items, row_cap=, db_name=)
    _, _, infocats, items = args
    assert infocats == ("attribute", "flags")
    assert items == ("f1", "vendor_id")
    # No empty strings injected.
    assert "" not in infocats
    assert "" not in items


# ---------------------------------------------------------------------------
# Tests 13-15: _build_browse_url
# ---------------------------------------------------------------------------

def test_build_browse_url_empty():
    """Test 13: no selections → bare /browse (no query string)."""
    assert _build_browse_url([], [], False) == "/browse"


def test_build_browse_url_full_round_trip():
    """Test 14: full URL with %20 spaces and %C2%B7 middle-dot, swap=1 last.

    Per Pitfall 6 — quote_via=urllib.parse.quote forces URL-style %20 (NOT
    form-style + for spaces) so address-bar appearance is consistent with what
    a manual <a href="?..."> would emit.
    """
    url = _build_browse_url(["A", "B"], ["attribute · vendor_id"], True)
    assert url == (
        "/browse?platforms=A&platforms=B"
        "&params=attribute%20%C2%B7%20vendor_id"
        "&swap=1"
    )


def test_build_browse_url_no_swap_when_false():
    """Test 15: swap=False → no swap key in the query string."""
    assert _build_browse_url(["A"], [], False) == "/browse?platforms=A"


# ---------------------------------------------------------------------------
# Bonus sanity check: the dataclass exists and ROW_CAP/COL_CAP are exported
# ---------------------------------------------------------------------------

def test_module_constants_present():
    """ROW_CAP=200, COL_CAP=30, PARAM_LABEL_SEP exported."""
    assert browse_service.ROW_CAP == 200
    assert browse_service.COL_CAP == 30
    assert hasattr(browse_service, "BrowseViewModel")
    # BrowseViewModel is a dataclass — sanity check the fields are present.
    fields = {f.name for f in BrowseViewModel.__dataclass_fields__.values()}
    expected = {
        "df_wide", "row_capped", "col_capped", "n_value_cols_total",
        "n_rows", "n_cols", "swap_axes", "selected_platforms",
        "selected_params", "all_platforms", "all_param_labels",
        "is_empty_selection", "index_col_name",
    }
    assert expected.issubset(fields), f"Missing fields: {expected - fields}"
