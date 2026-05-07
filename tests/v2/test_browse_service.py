"""Pure-Python unit tests for app_v2.services.browse_service.

No DB calls. The cache layer (`fetch_cells`, `list_platforms`, `list_parameters`)
is mocked at the call site (the symbols re-bound inside browse_service, NOT at
the source module — Pitfall 11 of test reliability: mocker.patch must target
the importing module).

Covers:
- D-13 ' · ' middle-dot separator (NOT v1.0 ' / ' — Pitfall 3)
- D-23 row_cap=200 / col_cap=30
- D-29 aggfunc='first' (delegated to pivot_to_wide)
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
    _compute_minority_cells,
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
    """Test 5: both dimensions empty → is_empty_selection=True, fetch_cells NOT called.

    260429-qyv: when selected_platforms is empty the params catalog is also
    skipped (params_disabled=True) — list_parameters_for_platforms must NOT
    be called.
    """
    db = object()  # sentinel — non-None but never used (short-circuit before DB)
    mock_list_platforms = mocker.patch.object(
        browse_service, "list_platforms", return_value=["P1", "P2"]
    )
    mock_list_params_for_platforms = mocker.patch.object(
        browse_service,
        "list_parameters_for_platforms",
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
    # Platforms catalog still runs — popover needs the full platforms list.
    mock_list_platforms.assert_called_once()
    # Params catalog SKIPPED when no platforms — picker is disabled (260429-qyv).
    mock_list_params_for_platforms.assert_not_called()
    # And fetch_cells must NOT be called — short-circuit (DATA-05 echo).
    mock_fetch_cells.assert_not_called()


def test_build_view_model_partial_empty_still_short_circuits(mocker):
    """Test 6: platforms=[] but params=['a · b'] → still empty (BOTH must be present)."""
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=[])
    mocker.patch.object(browse_service, "list_parameters_for_platforms", return_value=[])
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
        "list_parameters_for_platforms",
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
        "list_parameters_for_platforms",
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
    """Test 9: pivot_to_wide returns col_capped=True → vm.col_capped=True
    AND n_value_cols_total equals the number of selected param labels.

    260429-qyv update: list_parameters_for_platforms must include all 35
    param labels so the intersection passes them through to fetch_cells.
    """
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=["P1"])
    mocker.patch.object(
        browse_service,
        "list_parameters_for_platforms",
        return_value=[
            {"InfoCategory": "flags", "Item": f"f{i}"} for i in range(35)
        ],
    )
    mocker.patch.object(
        browse_service, "fetch_cells", return_value=(_make_long_df(), False)
    )
    capped_wide = pd.DataFrame({"PLATFORM_ID": ["P1"], "vendor_id": ["0xA1"]})
    mocker.patch.object(
        browse_service, "pivot_to_wide", return_value=(capped_wide, True)
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
    """Test 10: swap_axes flips index_col_name between PLATFORM_ID and Item.

    260429-qyv update: list_parameters_for_platforms must include the
    selected vendor_id label so the intersection passes it to fetch_cells.
    """
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=["P1"])
    mocker.patch.object(
        browse_service,
        "list_parameters_for_platforms",
        return_value=[{"InfoCategory": "attribute", "Item": "vendor_id"}],
    )
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
    """Test 11: 'attribute · zzz' sorts BEFORE 'flags · aaa' (combined-label sort).

    260429-qyv: now sourced from list_parameters_for_platforms — the test
    must pass a non-empty selected_platforms so the catalog is queried at
    all (zero platforms -> params_disabled, all_param_labels=[]).
    """
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=["P1"])
    mocker.patch.object(
        browse_service,
        "list_parameters_for_platforms",
        return_value=[
            {"InfoCategory": "flags", "Item": "aaa"},
            {"InfoCategory": "attribute", "Item": "zzz"},
        ],
    )
    mocker.patch.object(browse_service, "fetch_cells")

    vm = build_view_model(
        db,
        db_name="x",
        selected_platforms=["P1"],
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

    260429-qyv update: list_parameters_for_platforms is the catalog source.
    The mock returns the two well-formed labels; the garbage label is
    dropped by the catalog intersection (it's not in any catalog) BEFORE
    _parse_param_label even gets a chance to filter it. Same end state.
    """
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=["P1"])
    mocker.patch.object(
        browse_service,
        "list_parameters_for_platforms",
        return_value=[
            {"InfoCategory": "attribute", "Item": "vendor_id"},
            {"InfoCategory": "flags", "Item": "f1"},
        ],
    )
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
        "is_empty_selection", "params_disabled", "index_col_name",
    }
    assert expected.issubset(fields), f"Missing fields: {expected - fields}"


# ---------------------------------------------------------------------------
# 260429-qyv: filtered parameters catalog + intersection + disabled state
# ---------------------------------------------------------------------------


def test_build_view_model_zero_platforms_disables_params(mocker):
    """Zero platforms → params_disabled=True, no list_parameters_for_platforms call.

    The picker is wholly disabled in the UI; the data layer is not touched
    for params. all_param_labels is empty, selected_params is empty.
    """
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=["P1", "P2"])
    mock_lpfp = mocker.patch.object(browse_service, "list_parameters_for_platforms")
    mock_fetch_cells = mocker.patch.object(browse_service, "fetch_cells")

    vm = build_view_model(
        db,
        db_name="x",
        selected_platforms=[],
        selected_param_labels=[],
        swap_axes=False,
    )

    assert vm.params_disabled is True
    assert vm.all_param_labels == []
    assert vm.selected_params == []
    mock_lpfp.assert_not_called()  # short-circuit at the orchestrator level
    mock_fetch_cells.assert_not_called()


def test_build_view_model_filtered_param_catalog(mocker):
    """selected_platforms=['P1'] → all_param_labels sourced from
    list_parameters_for_platforms(db, ('P1',), db_name='x').

    The platforms tuple passed to the data layer is sorted (stable cache key).
    params_disabled=False because at least one platform is selected.
    """
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=["P1", "P2"])
    mock_lpfp = mocker.patch.object(
        browse_service,
        "list_parameters_for_platforms",
        return_value=[{"InfoCategory": "attribute", "Item": "vendor_id"}],
    )
    mocker.patch.object(browse_service, "fetch_cells")

    vm = build_view_model(
        db,
        db_name="x",
        selected_platforms=["P1"],
        selected_param_labels=[],
        swap_axes=False,
    )

    assert vm.params_disabled is False
    assert vm.all_param_labels == ["attribute · vendor_id"]
    # The platforms-filtered catalog is queried with a sorted tuple for
    # stable cache keying.
    mock_lpfp.assert_called_once_with(db, ("P1",), db_name="x")


def test_build_view_model_drops_stale_param_labels(mocker):
    """The headline 260429-qyv contract:

    user has previously checked 'flags · stale_label' while a now-unselected
    platform was active. After the unselect, list_parameters_for_platforms
    no longer returns 'flags · stale_label', so the intersection drops it
    BEFORE fetch_cells is called. Result: vm.selected_params keeps only the
    still-valid label, AND fetch_cells's items tuple does NOT contain
    'stale_label'.
    """
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=["P1"])
    mocker.patch.object(
        browse_service,
        "list_parameters_for_platforms",
        return_value=[{"InfoCategory": "attribute", "Item": "vendor_id"}],
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

    vm = build_view_model(
        db,
        db_name="x",
        selected_platforms=["P1"],
        selected_param_labels=[
            "attribute · vendor_id",
            "flags · stale_label",   # was checked under a now-unselected platform
        ],
        swap_axes=False,
    )

    # The stale label is GONE from the checked-set after intersection.
    assert vm.selected_params == ["attribute · vendor_id"]
    # And — critically — fetch_cells receives ONLY the surviving label.
    args, _ = mock_fetch_cells.call_args
    _, _, infocats, items = args
    assert infocats == ("attribute",)
    assert items == ("vendor_id",)
    assert "stale_label" not in items


def test_build_view_model_multi_platform_widens_catalog(mocker):
    """selected_platforms=['P2','P1'] → list_parameters_for_platforms is
    called with the SORTED tuple ('P1','P2') for stable cache keying.

    The catalog returned represents the union of params for both platforms;
    that union becomes vm.all_param_labels.
    """
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=["P1", "P2"])
    mock_lpfp = mocker.patch.object(
        browse_service,
        "list_parameters_for_platforms",
        return_value=[
            {"InfoCategory": "attribute", "Item": "vendor_id"},
            {"InfoCategory": "flags", "Item": "f1"},
        ],
    )
    mocker.patch.object(browse_service, "fetch_cells")

    build_view_model(
        db,
        db_name="x",
        selected_platforms=["P2", "P1"],  # input order intentionally reversed
        selected_param_labels=[],
        swap_axes=False,
    )

    # platforms tuple is SORTED so order-variants share a cache slot.
    mock_lpfp.assert_called_once_with(db, ("P1", "P2"), db_name="x")


def test_build_view_model_full_catalog_ignored_when_no_platforms(mocker):
    """Zero platforms must NOT fall through to the unfiltered list_parameters
    catalog (the v1 mistake this task corrects).

    list_parameters_for_platforms is not called either — so the test asserts
    all_param_labels is empty even though list_parameters (the unfiltered
    cache wrapper) would, if accidentally referenced, return data.
    """
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=["P1"])
    # If browse_service accidentally referenced the unfiltered catalog wrapper,
    # this patch would be invoked and the assertion would fail. Asserting
    # `not hasattr` is too strict (the symbol exists in cache.py); instead
    # we patch the legacy attribute IF it ever leaked back into browse_service
    # and assert the patched function is never called.
    if hasattr(browse_service, "list_parameters"):
        mock_legacy = mocker.patch.object(
            browse_service,
            "list_parameters",
            return_value=[{"InfoCategory": "should_not", "Item": "appear"}],
        )
    else:
        mock_legacy = None
    mock_lpfp = mocker.patch.object(
        browse_service, "list_parameters_for_platforms"
    )
    mocker.patch.object(browse_service, "fetch_cells")

    vm = build_view_model(
        db,
        db_name="x",
        selected_platforms=[],
        selected_param_labels=[],
        swap_axes=False,
    )

    assert vm.all_param_labels == []
    assert vm.params_disabled is True
    mock_lpfp.assert_not_called()
    if mock_legacy is not None:
        mock_legacy.assert_not_called(), (
            "browse_service should NOT reference the unfiltered list_parameters "
            "anymore; it must use list_parameters_for_platforms exclusively."
        )


# ---------------------------------------------------------------------------
# 260507-w7h: highlight + _compute_minority_cells
# ---------------------------------------------------------------------------


def test_compute_minority_cells_all_equal_returns_empty():
    """Test A — all values in column equal → empty set (no minority)."""
    df = pd.DataFrame({
        "PLATFORM_ID": ["P1", "P2", "P3"],
        "vendor_id": ["X", "X", "X"],
    })
    result = _compute_minority_cells(df, index_col="PLATFORM_ID", swap_axes=False)
    assert result == set()


def test_compute_minority_cells_single_outlier():
    """Test B — single outlier → outlier (idx, col) in set; mode rows NOT in set."""
    df = pd.DataFrame({
        "PLATFORM_ID": ["P1", "P2", "P3"],
        "vendor_id": ["X", "X", "Y"],
    })
    result = _compute_minority_cells(df, index_col="PLATFORM_ID", swap_axes=False)
    # iterrows() yields the integer index 0..2 — the outlier is at row idx 2.
    assert (2, "vendor_id") in result
    # Mode-baseline rows are NOT in the set.
    assert (0, "vendor_id") not in result
    assert (1, "vendor_id") not in result


def test_compute_minority_cells_empty_cells_ignored():
    """Test C — empty cells (NaN/None/'') never appear; do NOT count toward mode.

    Fixture: column with values ['X', 'X', '', 'Y'] (4 rows). Mode of non-empty
    = 'X' (count 2). Expected: only (3, col) in set; empty row (2, col) NOT.
    """
    df = pd.DataFrame({
        "PLATFORM_ID": ["P1", "P2", "P3", "P4"],
        "vendor_id": ["X", "X", "", "Y"],
    })
    result = _compute_minority_cells(df, index_col="PLATFORM_ID", swap_axes=False)
    assert (3, "vendor_id") in result
    # Empty cell never marked.
    assert (2, "vendor_id") not in result
    # Mode rows never marked.
    assert (0, "vendor_id") not in result
    assert (1, "vendor_id") not in result

    # NaN/None variant — same contract.
    df_nan = pd.DataFrame({
        "PLATFORM_ID": ["P1", "P2", "P3", "P4"],
        "vendor_id": ["X", "X", None, "Y"],
    })
    result_nan = _compute_minority_cells(df_nan, index_col="PLATFORM_ID", swap_axes=False)
    assert (3, "vendor_id") in result_nan
    assert (2, "vendor_id") not in result_nan


def test_compute_minority_cells_tie_for_mode_lowest_sorted_wins():
    """Test D — tie for mode: pandas Series.mode() returns sorted modes;
    .iloc[0] (lowest) is the baseline. Fixture: ['A','A','B','B'] → 'A' wins;
    rows 2 and 3 ('B') are in the minority set.
    """
    df = pd.DataFrame({
        "PLATFORM_ID": ["P1", "P2", "P3", "P4"],
        "col1": ["A", "A", "B", "B"],
    })
    result = _compute_minority_cells(df, index_col="PLATFORM_ID", swap_axes=False)
    assert (2, "col1") in result
    assert (3, "col1") in result
    # 'A' is baseline → not in set.
    assert (0, "col1") not in result
    assert (1, "col1") not in result


def test_compute_minority_cells_swap_axes_flips_axis():
    """Test E — swap_axes=True: parameter is the row → mode computed across
    columns (axis=1) per row.
    """
    # When swap_axes=True, the index col is "Item" (or similar) and the
    # value cols are platform IDs. Each row is a parameter; mode is across
    # platform columns.
    df = pd.DataFrame({
        "Item": ["vendor_id", "device_id"],
        "P1": ["X", "Y"],
        "P2": ["X", "Y"],
        "P3": ["Z", "Y"],  # vendor_id row: P3 is the outlier ("Z" vs mode "X")
    })
    result = _compute_minority_cells(df, index_col="Item", swap_axes=True)
    # vendor_id row (idx=0): P3 is the outlier
    assert (0, "P3") in result
    # device_id row (idx=1): all "Y" → no minorities
    assert (1, "P1") not in result
    assert (1, "P2") not in result
    assert (1, "P3") not in result
    # Mode cells in row 0 are NOT marked.
    assert (0, "P1") not in result
    assert (0, "P2") not in result


def test_build_view_model_highlight_false_skips_compute(mocker):
    """Test F — highlight=False (default): vm.minority_cells is empty;
    _compute_minority_cells is NOT called.
    """
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=["P1"])
    mocker.patch.object(
        browse_service,
        "list_parameters_for_platforms",
        return_value=[{"InfoCategory": "attribute", "Item": "vendor_id"}],
    )
    df_long = pd.DataFrame({
        "PLATFORM_ID": ["P1"],
        "InfoCategory": ["attribute"],
        "Item": ["vendor_id"],
        "Result": ["0xA1"],
    })
    mocker.patch.object(
        browse_service, "fetch_cells", return_value=(df_long, False)
    )
    spy = mocker.spy(browse_service, "_compute_minority_cells")

    vm = build_view_model(
        db,
        db_name="x",
        selected_platforms=["P1"],
        selected_param_labels=["attribute · vendor_id"],
        swap_axes=False,
    )

    assert vm.highlight is False
    assert vm.minority_cells == set()
    assert spy.call_count == 0


def test_build_view_model_highlight_true_populates_minority_cells(mocker):
    """Test G — highlight=True with a fixture that has at least one outlier:
    vm.minority_cells is non-empty and vm.highlight is True.
    """
    db = object()
    mocker.patch.object(browse_service, "list_platforms", return_value=["P1", "P2", "P3"])
    mocker.patch.object(
        browse_service,
        "list_parameters_for_platforms",
        return_value=[{"InfoCategory": "attribute", "Item": "vendor_id"}],
    )
    # 3 platforms × 1 param. Two rows "X", one row "Y" → "Y" is the minority.
    df_long = pd.DataFrame({
        "PLATFORM_ID": ["P1", "P2", "P3"],
        "InfoCategory": ["attribute"] * 3,
        "Item": ["vendor_id"] * 3,
        "Result": ["X", "X", "Y"],
    })
    mocker.patch.object(
        browse_service, "fetch_cells", return_value=(df_long, False)
    )

    vm = build_view_model(
        db,
        db_name="x",
        selected_platforms=["P1", "P2", "P3"],
        selected_param_labels=["attribute · vendor_id"],
        swap_axes=False,
        highlight=True,
    )

    assert vm.highlight is True
    assert len(vm.minority_cells) > 0


def test_build_browse_url_with_highlight():
    """Test H — highlight=True appends 'highlight=1' to the query string;
    highlight=False omits it. Order is pinned: swap before highlight.
    """
    # No selections + highlight=True → /browse?highlight=1
    assert _build_browse_url([], [], False, highlight=True) == "/browse?highlight=1"

    # Full URL with highlight=True (after swap=1).
    url = _build_browse_url(["A", "B"], ["attribute · vendor_id"], True, highlight=True)
    assert url == (
        "/browse?platforms=A&platforms=B"
        "&params=attribute%20%C2%B7%20vendor_id"
        "&swap=1&highlight=1"
    )

    # highlight=False omits the key.
    url2 = _build_browse_url(["A"], [], False, highlight=False)
    assert url2 == "/browse?platforms=A"
    assert "highlight" not in url2

    # Default kwarg omitted altogether → False semantics.
    url3 = _build_browse_url(["A"], [], False)
    assert "highlight" not in url3
