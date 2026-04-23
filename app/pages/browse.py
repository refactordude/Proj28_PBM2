"""Browse page — Pivot / Detail / Chart tabs (D-02).

Sidebar filters (D-05, D-06, D-08): platform multiselect, parameter catalog multiselect,
Clear filters button. All three tabs share filter state via st.session_state.

Filter state also round-trips through st.query_params for BROWSE-09 shareable URLs.
Tab identity (browse.tab) round-trips via the 'tab' query param (Plan 06 extension).
"""
from __future__ import annotations

import logging

import pandas as pd
import plotly.express as px
import streamlit as st

from app.core.config import find_database, load_settings
from app.adapters.db.registry import build_adapter
from app.services.ufs_service import (
    fetch_cells,
    list_parameters,
    list_platforms,
    pivot_to_wide,
)
from app.services.result_normalizer import try_numeric
from app.components.export_dialog import render_export_dialog

logger = logging.getLogger(__name__)

_ACCENT_COLOR = "#1f77b4"  # UI-SPEC accent; Plotly default but pinned explicitly


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
    # Tab identity round-trip (Plan 06 — T-06-01: only accepted values from fixed dict)
    if "tab" in qp and qp["tab"]:
        tab_lower = qp["tab"].strip().lower()
        tab_map = {"pivot": "Pivot", "detail": "Detail", "chart": "Chart"}
        if tab_lower in tab_map:
            st.session_state.setdefault("browse.tab", tab_map[tab_lower])
    st.session_state["_browse_url_loaded"] = True


def _sync_state_to_url(
    platforms: list[str], params: list[str], swap: bool, tab: str = ""
) -> None:
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
    # Tab identity (Plan 06 extension)
    if tab:
        st.query_params["tab"] = tab.lower()
    else:
        st.query_params.pop("tab", None)


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
# Sidebar Copy link helper (Plan 06 — tab-independent; moved from Pivot ctrl_export)
# ---------------------------------------------------------------------------

def _render_sidebar_copy_link() -> None:
    """Sidebar Copy link button — tab-independent; always available once filters exist."""
    if st.sidebar.button("Copy link", key="sidebar_copy_link", type="secondary"):
        st.components.v1.html(
            "<script>navigator.clipboard.writeText(window.location.href);</script>",
            height=0,
        )
        st.toast("Link copied to clipboard.")


# ---------------------------------------------------------------------------
# Sidebar renderer (D-05, D-06, BROWSE-01, BROWSE-02, BROWSE-03)
# ---------------------------------------------------------------------------

def _render_sidebar_filters(db_name: str) -> tuple[list[str], list[str]]:
    """Render the Browse-page-specific sidebar widgets below the shared divider.

    Returns (selected_platforms, selected_params_labels).
    Does NOT render DB/LLM selectors — those are owned by streamlit_app.py (Pitfall 7).
    Sidebar order: Platforms -> Parameters -> Clear filters -> Copy link (Plan 06).
    """
    adapter = _get_db_adapter(db_name)
    # Note: the shared sidebar already renders a divider in streamlit_app.py;
    # this divider separates global controls from page-specific browse filters.

    if adapter is None:
        st.sidebar.warning("No active database. Configure one in Settings.")
        return [], []

    # Platform multiselect (BROWSE-01)
    try:
        platforms_all = list_platforms(adapter, db_name=db_name)
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
        params_all = list_parameters(adapter, db_name=db_name)
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

    # Copy link button (Plan 06 — sidebar position, tab-independent)
    _render_sidebar_copy_link()

    return selected_platforms, selected_params


# ---------------------------------------------------------------------------
# Pivot tab renderer (D-07, BROWSE-04, BROWSE-06, BROWSE-07, BROWSE-09)
# ---------------------------------------------------------------------------

def _render_pivot_tab(adapter, platforms: list[str], params_labels: list[str]) -> None:
    """Render the full Pivot tab content.

    Includes: swap-axes toggle, row-count caption, pivot grid.
    Handles empty/loading/error/row-cap/col-cap states per UI-SPEC.
    ctrl_export slot reserved for Plan 07 (Export dialog).
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
            df_long, row_capped = fetch_cells(
                adapter, platforms_t, infocategories, items,
                db_name=adapter.config.name,
            )
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

    # Export button (always rendered at top; reads previous-rerun stash for enabled state)
    prior_wide = st.session_state.get("pivot.df_wide")
    prior_long = st.session_state.get("pivot.df_long")
    has_exportable = (
        (prior_wide is not None and not prior_wide.empty)
        or (prior_long is not None and not prior_long.empty)
    )
    with ctrl_export:
        if st.button(
            "Export",
            key="pivot_export",
            type="secondary",
            disabled=not has_exportable,
            help="Select platforms and parameters first" if not has_exportable else None,
        ):
            render_export_dialog(prior_wide, prior_long)

    # Pivot to wide (D-07)
    df_wide, col_capped = pivot_to_wide(df_long, swap_axes=swap_axes, col_cap=30)

    # Stash the currently-visible view for the next rerun's Export dialog (D-15)
    st.session_state["pivot.df_wide"] = df_wide
    st.session_state["pivot.df_long"] = df_long

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
# Detail tab renderer (BROWSE-05)
# ---------------------------------------------------------------------------

def _render_detail_tab(adapter, platforms: list[str], params_labels: list[str]) -> None:
    """BROWSE-05 — single-platform long-form detail view."""
    # Empty / wrong-cardinality state
    if len(platforms) != 1:
        st.info("Select exactly one platform in the sidebar to see its full parameter detail.")
        return

    if not params_labels:
        st.info("Select parameters in the sidebar to see their values for this platform.")
        return

    # Reuse the same fetch path as Pivot so the 200-row cap and cache are honored consistently.
    parsed = [_parse_param_label(lbl) for lbl in params_labels]
    infocategories = tuple(sorted({p[0] for p in parsed}))
    items = tuple(sorted({p[1] for p in parsed}))
    platforms_t = tuple(platforms)

    try:
        with st.spinner("Fetching data..."):
            df_long, row_capped = fetch_cells(
                adapter, platforms_t, infocategories, items,
                db_name=adapter.config.name,
            )
    except Exception as exc:
        st.error("Could not load data. Check your database connection in Settings.")
        with st.expander("Error detail"):
            st.code(f"{type(exc).__name__}: {exc}")
        logger.exception("fetch_cells failed (detail tab)")
        return

    if df_long.empty:
        st.info("No data matches the current selection.")
        return

    if row_capped:
        st.warning("Result capped at 200 rows. Narrow your platform or parameter selection to see all data.")

    # Sort (InfoCategory ASC, Item ASC) per BROWSE-05
    df_sorted = df_long.sort_values(["InfoCategory", "Item"], kind="stable").reset_index(drop=True)

    # Row-count caption: "K parameters across N categories"
    k_params = len(df_sorted)
    n_categories = df_sorted["InfoCategory"].nunique()
    st.caption(f"{k_params} parameters across {n_categories} categories")

    # Render long-form. Use TextColumn for Result (heterogeneity contract).
    column_cfg = {
        "PLATFORM_ID": st.column_config.TextColumn("Platform"),
        "InfoCategory": st.column_config.TextColumn("Category"),
        "Item": st.column_config.TextColumn("Item"),
        "Result": st.column_config.TextColumn("Result"),
    }
    st.dataframe(
        df_sorted[["PLATFORM_ID", "InfoCategory", "Item", "Result"]],
        column_config=column_cfg,
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------------------------
# Chart tab renderer (VIZ-01 + VIZ-02)
# ---------------------------------------------------------------------------

def _render_chart_tab(adapter, platforms: list[str], params_labels: list[str], swap_axes: bool) -> None:
    """VIZ-01 + VIZ-02 — Plotly chart with explicit numeric-column picker and chart-type radio."""
    # Empty state — no selection
    if not platforms or not params_labels:
        st.info("Select platforms and parameters in the sidebar first.")
        return

    # Reuse the same fetch path as Pivot (same cache key, same 200-row cap).
    parsed = [_parse_param_label(lbl) for lbl in params_labels]
    infocategories = tuple(sorted({p[0] for p in parsed}))
    items = tuple(sorted({p[1] for p in parsed}))
    platforms_t = tuple(platforms)

    try:
        with st.spinner("Fetching data..."):
            df_long, row_capped = fetch_cells(
                adapter, platforms_t, infocategories, items,
                db_name=adapter.config.name,
            )
    except Exception as exc:
        st.error("Could not load data. Check your database connection in Settings.")
        with st.expander("Error detail"):
            st.code(f"{type(exc).__name__}: {exc}")
        logger.exception("fetch_cells failed (chart tab)")
        return

    if df_long.empty:
        st.info("No data matches the current selection.")
        return

    if row_capped:
        st.warning("Result capped at 200 rows. Narrow your platform or parameter selection to see all data.")

    # Pivot to wide using the same swap_axes as Pivot tab (D-02 — shared filter state includes swap).
    df_wide, _col_capped = pivot_to_wide(df_long, swap_axes=swap_axes, col_cap=30)

    # Identify the index column (PLATFORM_ID default; Item when swapped).
    index_col = "Item" if swap_axes else "PLATFORM_ID"
    if index_col not in df_wide.columns:
        # Defensive: pivot_to_wide resets index to a column; this should always hold.
        st.error("Could not load data. Check your database connection in Settings.")
        logger.error("chart tab: index_col %s missing from pivot columns %s", index_col, list(df_wide.columns))
        return

    # Numeric detection — VIZ-02 per-column lazy coercion. NEVER apply globally to df_wide.
    candidate_cols = [c for c in df_wide.columns if c != index_col]
    numeric_cols: list[str] = []
    numeric_series_cache: dict[str, pd.Series] = {}
    for col in candidate_cols:
        coerced = try_numeric(df_wide[col])
        if coerced.notna().any():
            numeric_cols.append(col)
            numeric_series_cache[col] = coerced

    if not numeric_cols:
        st.info("No numeric columns in the current selection. Add numeric parameters in the sidebar.")
        return

    # Axis + chart-type selectors (D-14 explicit pick; no auto-render)
    # X-axis: offer index_col (PLATFORM_ID or Item) as default option.
    x_options = [index_col]

    col_x, col_y, col_type = st.columns([1, 1, 1])
    with col_x:
        # Remember last pick
        default_x = st.session_state.get("chart.x_col", x_options[0])
        if default_x not in x_options:
            default_x = x_options[0]
        x_col = st.selectbox(
            "X-axis",
            options=x_options,
            index=x_options.index(default_x),
            key="chart.x_col",
        )
    with col_y:
        default_y = st.session_state.get("chart.y_col", numeric_cols[0])
        if default_y not in numeric_cols:
            default_y = numeric_cols[0]
        y_col = st.selectbox(
            "Y-axis (numeric)",
            options=numeric_cols,
            index=numeric_cols.index(default_y),
            key="chart.y_col",
        )
    with col_type:
        default_type = st.session_state.get("chart.type", "Bar")
        chart_type_options = ["Bar", "Line", "Scatter"]
        if default_type not in chart_type_options:
            default_type = "Bar"
        chart_type = st.radio(
            "Chart type",
            options=chart_type_options,
            index=chart_type_options.index(default_type),
            horizontal=True,
            key="chart.type",
        )

    # Build chart DF: keep X as-is, coerce Y via cached numeric series, drop NA rows (VIZ-02).
    chart_df = pd.DataFrame({
        x_col: df_wide[x_col].astype(str),  # X stays as display labels
        y_col: numeric_series_cache[y_col],
    }).dropna(subset=[y_col])

    if chart_df.empty:
        st.info("No numeric values in column '{0}' for the current selection.".format(y_col))
        return

    # Render via Plotly with explicit accent color (UI-SPEC).
    color_seq = [_ACCENT_COLOR]
    if chart_type == "Bar":
        fig = px.bar(chart_df, x=x_col, y=y_col, color_discrete_sequence=color_seq, title=y_col)
    elif chart_type == "Line":
        fig = px.line(chart_df, x=x_col, y=y_col, color_discrete_sequence=color_seq, title=y_col)
    else:  # Scatter
        fig = px.scatter(chart_df, x=x_col, y=y_col, color_discrete_sequence=color_seq, title=y_col)

    fig.update_layout(
        title=y_col,
        xaxis_title=x_col,
        yaxis_title=y_col,
        margin=dict(l=40, r=20, t=50, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------

st.title("Browse")

_load_state_from_url()

active_db_name: str = st.session_state.get("active_db", "")
selected_platforms, selected_params = _render_sidebar_filters(active_db_name)

swap_axes = st.session_state.get("pivot_swap_axes", False)
active_tab = st.session_state.get("browse.tab", "Pivot")
_sync_state_to_url(selected_platforms, selected_params, swap_axes, active_tab)

pivot_tab, detail_tab, chart_tab = st.tabs(["Pivot", "Detail", "Chart"])

with pivot_tab:
    st.session_state["browse.tab"] = "Pivot"
    adapter = _get_db_adapter(active_db_name)
    _render_pivot_tab(adapter, selected_platforms, selected_params)

with detail_tab:
    st.session_state["browse.tab"] = "Detail"
    adapter = _get_db_adapter(active_db_name)
    _render_detail_tab(adapter, selected_platforms, selected_params)

with chart_tab:
    st.session_state["browse.tab"] = "Chart"
    adapter = _get_db_adapter(active_db_name)
    _render_chart_tab(adapter, selected_platforms, selected_params, swap_axes)
