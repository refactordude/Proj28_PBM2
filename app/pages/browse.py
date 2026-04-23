"""Browse page — Pivot / Detail / Chart tabs (D-02).

Sidebar filters (D-05, D-06, D-08): platform multiselect, parameter catalog multiselect,
Clear filters button. All three tabs share filter state via st.session_state.

Filter state also round-trips through st.query_params for BROWSE-09 shareable URLs.
"""
from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from app.core.config import find_database, load_settings
from app.adapters.db.registry import build_adapter
from app.services.ufs_service import (
    fetch_cells,
    list_parameters,
    list_platforms,
    pivot_to_wide,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DB adapter factory — mirrors entrypoint, deduped via @st.cache_resource
# ---------------------------------------------------------------------------

@st.cache_resource
def _get_db_adapter(db_name: str):
    """Return a cached DBAdapter for the named database.

    Mirrors get_db_adapter() in streamlit_app.py. @st.cache_resource deduplicates
    across the process — same db_name yields the same adapter singleton.
    """
    if not db_name:
        return None
    settings = load_settings()
    cfg = find_database(settings, db_name)
    if cfg is None:
        return None
    return build_adapter(cfg)


# ---------------------------------------------------------------------------
# URL param round-trip helpers (BROWSE-09)
# ---------------------------------------------------------------------------

def _load_state_from_url() -> None:
    """One-shot on page load: copy st.query_params into session_state defaults.

    Guarded by _browse_url_loaded flag so it only runs once per session.
    Calling on every rerun would overwrite the user's multiselect changes.
    """
    if st.session_state.get("_browse_url_loaded"):
        return
    qp = st.query_params
    if "platforms" in qp and qp["platforms"]:
        st.session_state.setdefault("selected_platforms", qp["platforms"].split(","))
    if "params" in qp and qp["params"]:
        st.session_state.setdefault("selected_params", qp["params"].split(","))
    if "swap" in qp:
        st.session_state.setdefault("pivot_swap_axes", qp["swap"] == "1")
    st.session_state["_browse_url_loaded"] = True


def _sync_state_to_url(platforms: list[str], params: list[str], swap: bool) -> None:
    """Write current filter state back into st.query_params."""
    if platforms:
        st.query_params["platforms"] = ",".join(platforms)
    else:
        st.query_params.pop("platforms", None)
    if params:
        st.query_params["params"] = ",".join(params)
    else:
        st.query_params.pop("params", None)
    if swap:
        st.query_params["swap"] = "1"
    else:
        st.query_params.pop("swap", None)


# ---------------------------------------------------------------------------
# Parameter label helpers (D-06)
# ---------------------------------------------------------------------------

def _format_param_label(row: dict) -> str:
    """Format a parameter dict as 'InfoCategory / Item' label."""
    return f"{row['InfoCategory']} / {row['Item']}"


def _parse_param_label(label: str) -> tuple[str, str]:
    """Parse 'InfoCategory / Item' label back to (category, item) tuple."""
    cat, _, item = label.partition(" / ")
    return cat, item


# ---------------------------------------------------------------------------
# Sidebar renderer (D-05, D-06, BROWSE-01, BROWSE-02, BROWSE-03)
# ---------------------------------------------------------------------------

def _render_sidebar_filters(db_name: str) -> tuple[list[str], list[str]]:
    """Render the Browse-page-specific sidebar widgets below the shared divider.

    Returns (selected_platforms, selected_params_labels).
    Does NOT render DB/LLM selectors — those are owned by streamlit_app.py (Pitfall 7).
    """
    adapter = _get_db_adapter(db_name)
    # Note: the shared sidebar already renders a divider in streamlit_app.py;
    # this divider separates global controls from page-specific browse filters.

    if adapter is None:
        st.sidebar.warning("No active database. Configure one in Settings.")
        return [], []

    # Platform multiselect (BROWSE-01)
    try:
        platforms_all = list_platforms(adapter)
    except Exception as exc:
        st.sidebar.error(
            "Could not load platforms. Check your database connection in Settings."
        )
        with st.sidebar.expander("Error detail"):
            st.sidebar.code(f"{type(exc).__name__}: {exc}")
        return [], []

    selected_platforms = st.sidebar.multiselect(
        "Platforms",
        options=platforms_all,
        default=st.session_state.get("selected_platforms", []),
        key="selected_platforms",
        placeholder="Search platforms...",
    )

    # Parameter catalog multiselect (BROWSE-02, BROWSE-03, D-06, D-08)
    try:
        params_all = list_parameters(adapter)
    except Exception as exc:
        st.sidebar.error(
            "Could not load parameters. Check your database connection in Settings."
        )
        with st.sidebar.expander("Error detail"):
            st.sidebar.code(f"{type(exc).__name__}: {exc}")
        return selected_platforms, []

    param_labels_all = sorted(
        [_format_param_label(p) for p in params_all],
        key=lambda lbl: (lbl.split(" / ")[0], lbl.split(" / ")[1]),
    )
    selected_params = st.sidebar.multiselect(
        "Parameters",
        options=param_labels_all,
        default=st.session_state.get("selected_params", []),
        key="selected_params",
        placeholder="Search parameters...",
    )

    # Clear filters (D-05)
    if st.sidebar.button("Clear filters", type="secondary", key="clear_filters"):
        st.session_state.pop("selected_platforms", None)
        st.session_state.pop("selected_params", None)
        st.session_state.pop("pivot_swap_axes", None)
        st.query_params.clear()
        st.rerun()

    return selected_platforms, selected_params


# ---------------------------------------------------------------------------
# Pivot tab renderer (D-07, BROWSE-04, BROWSE-06, BROWSE-07, BROWSE-09)
# ---------------------------------------------------------------------------

def _render_pivot_tab(adapter, platforms: list[str], params_labels: list[str]) -> None:
    """Render the full Pivot tab content.

    Includes: swap-axes toggle, row-count caption, copy-link button, pivot grid.
    Handles empty/loading/error/row-cap/col-cap states per UI-SPEC.
    """
    # Above-grid controls row (UI-SPEC: 1:1:4 columns)
    ctrl_swap, ctrl_count, ctrl_export = st.columns([1, 1, 4])
    with ctrl_swap:
        swap_axes = st.toggle("Swap axes",
            key="pivot_swap_axes",
            value=st.session_state.get("pivot_swap_axes", False),
        )

    # Empty state — no selection (BROWSE-07)
    if not platforms or not params_labels:
        st.info("Select platforms and parameters in the sidebar to build the pivot grid.")
        return

    # Parse labels back to (category, item) pairs for fetch_cells
    parsed = [_parse_param_label(lbl) for lbl in params_labels]
    infocategories = tuple(sorted({p[0] for p in parsed}))
    items = tuple(sorted({p[1] for p in parsed}))
    platforms_t = tuple(platforms)

    # Query (with loading state per BROWSE-07)
    try:
        with st.spinner("Fetching data..."):
            df_long, row_capped = fetch_cells(adapter, platforms_t, infocategories, items)
    except Exception as exc:
        st.error("Could not load data. Check your database connection in Settings.")
        with st.expander("Error detail"):
            st.code(f"{type(exc).__name__}: {exc}")
        logger.exception("fetch_cells failed")
        return

    if df_long.empty:
        st.info("No data matches the current selection.")
        return

    # Row-cap warning (DATA-07 surfacing, BROWSE-07)
    if row_capped:
        st.warning(
            "Result capped at 200 rows. Narrow your platform or parameter selection to see all data."
        )

    # Pivot to wide (D-07)
    df_wide, col_capped = pivot_to_wide(df_long, swap_axes=swap_axes, col_cap=30)

    # Row-count indicator (BROWSE-06)
    # Default orientation: rows = platforms, columns = parameters.
    # Swapped orientation: rows = parameters, columns = platforms.
    n_rows = len(df_wide)
    # Determine index column name based on orientation
    index_col_name = "Item" if swap_axes else "PLATFORM_ID"
    value_cols = [c for c in df_wide.columns if c != index_col_name]
    n_value_cols = len(value_cols)
    if swap_axes:
        count_copy = f"{n_value_cols} platforms × {n_rows} parameters"
    else:
        count_copy = f"{n_rows} platforms × {n_value_cols} parameters"
    with ctrl_count:
        st.caption(count_copy)

    # Column-cap warning (BROWSE-04)
    if col_capped:
        st.warning(
            f"Showing first 30 of {len(params_labels)} parameters. Narrow your selection to see all."
        )

    # Copy-link button in the export column (Plan 07 will add real Export dialog here)
    with ctrl_export:
        if st.button("Copy link", key="pivot_copy_link", type="secondary"):
            # Use a JS snippet to copy window.location.href to clipboard (Pattern 6).
            # No user-controlled string is interpolated — safe (T-05-02).
            st.components.v1.html(
                "<script>navigator.clipboard.writeText(window.location.href);</script>",
                height=0,
            )
            st.toast("Link copied to clipboard.")

    # Pivot grid (UI-SPEC: TextColumn for every result column — heterogeneous values)
    # NEVER use NumberColumn globally (PROJECT.md constraint: same Item may be hex on
    # one platform and decimal on another).
    column_cfg: dict = {}
    for c in df_wide.columns:
        if c == "PLATFORM_ID":
            column_cfg[c] = st.column_config.TextColumn("Platform")
        elif c == "Item":
            column_cfg[c] = st.column_config.TextColumn("Item")
        else:
            column_cfg[c] = st.column_config.TextColumn(str(c))

    st.dataframe(
        df_wide,
        column_config=column_cfg,
        use_container_width=True,
        hide_index=False,
    )


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------

st.title("Browse")

_load_state_from_url()

active_db_name: str = st.session_state.get("active_db", "")
selected_platforms, selected_params = _render_sidebar_filters(active_db_name)

swap_axes = st.session_state.get("pivot_swap_axes", False)
_sync_state_to_url(selected_platforms, selected_params, swap_axes)

pivot_tab, detail_tab, chart_tab = st.tabs(["Pivot", "Detail", "Chart"])

with pivot_tab:
    adapter = _get_db_adapter(active_db_name)
    _render_pivot_tab(adapter, selected_platforms, selected_params)

with detail_tab:
    st.info("Detail tab is implemented in Plan 06.")

with chart_tab:
    st.info("Chart tab is implemented in Plan 06.")
