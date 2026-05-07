"""Browse tab orchestration — turns filter state into a BrowseViewModel.

Single source of truth for GET /browse and POST /browse/grid (Pattern 1 of
04-RESEARCH.md). Pure Python; NO FastAPI / Starlette imports here. Routes
construct context dicts from the returned dataclass.

Contracts (from 04-CONTEXT.md):
- D-12: full DB catalog source for both pickers (NOT the curated Overview list)
- D-13: parameter labels use ' · ' (middle dot U+00B7), sorted alphabetically
        by combined label. NEVER the v1.0 slash separator (Pitfall 3).
- D-23: row_cap=200, col_cap=30 (server-enforced, mirrors v1.0 BROWSE-04)
- D-29: aggfunc='first' for pivot duplicates (delegated to pivot_to_wide)
- D-30..D-33: URL round-trip via repeated keys + swap='1'/omitted

Threat mitigation:
- T-04-02-01: SQL injection — fetch_cells uses sa.bindparam(expanding=True)
  with parameterized IN; this module only passes lists, never builds SQL.
- T-04-02-02: garbage param labels — _parse_param_label returns None for
  malformed input; the comprehension silently drops them, preventing empty
  strings from reaching the SQL bind parameters.
"""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import Hashable

import pandas as pd

from app.services.ufs_service import pivot_to_wide
from app_v2.services.cache import (
    fetch_cells,
    list_parameters_for_platforms,
    list_platforms,
)

# D-13: middle dot U+00B7 with surrounding spaces. NEVER the v1.0 slash separator.
PARAM_LABEL_SEP = " · "

ROW_CAP = 200  # D-23
COL_CAP = 30   # D-23


@dataclass
class BrowseViewModel:
    """View model returned by build_view_model — consumed by browse routes.

    Fields are wired into Jinja2 templates in Plan 04-03. All collection
    fields are concrete `list[str]` (NOT Iterable) so templates can iterate
    multiple times safely.
    """

    df_wide: pd.DataFrame              # may be empty when is_empty_selection=True
    row_capped: bool
    col_capped: bool
    n_value_cols_total: int            # N for "Showing first 30 of {N} parameters"
    n_rows: int
    n_cols: int                        # value-cols actually shown (≤ COL_CAP)
    swap_axes: bool
    selected_platforms: list[str]
    selected_params: list[str]         # combined labels: "attribute · vendor_id"
    all_platforms: list[str]
    all_param_labels: list[str]
    is_empty_selection: bool
    params_disabled: bool              # NEW (260429-qyv): True iff selected_platforms is empty
    index_col_name: str                # "PLATFORM_ID" (default) or "Item" (swap_axes)
    # 260507-w7h — Highlight toggle: render-only minority cell decoration.
    highlight: bool = False
    minority_cells: set = None  # set[tuple[Hashable, str]] of (row_idx, col_name)

    def __post_init__(self):
        # Canonical mutable-default workaround for @dataclass without
        # importing `field`. Keep imports stable.
        if self.minority_cells is None:
            self.minority_cells = set()


def _parse_param_label(label: str) -> tuple[str, str] | None:
    """Split 'InfoCategory · Item' on the first ' · ' separator.

    Returns (cat, item) or None for malformed input. maxsplit=1 means labels
    containing extra ' · ' inside the Item name (rare) are preserved in the
    Item half — we never lose data, but we also never emit empty strings into
    the SQL bind parameters.

    Pitfall 3: NEVER use the v1.0 slash separator here — it would silently
    drop every v2.0 label.
    """
    parts = label.split(PARAM_LABEL_SEP, 1)
    return (parts[0], parts[1]) if len(parts) == 2 else None


def _compute_minority_cells(
    df_wide: pd.DataFrame,
    index_col: str,
    swap_axes: bool,
) -> set[tuple[Hashable, str]]:
    """Return {(row_label_from_iterrows, col_name)} for cells that are
    non-empty AND differ from the mode of non-empty values along the
    parameter axis.

    Axis semantics:
      swap_axes=False → parameter is a column → mode along axis=0 (per column,
                        across all platform rows)
      swap_axes=True  → parameter is a row    → mode along axis=1 (per row,
                        across all platform columns)

    Empty rule: NaN, None, and "" are treated identically — they never count
    toward mode and are never added to the result set. Use a single
    is-empty predicate `_is_empty(v)` that returns True for any of those.

    Tie rule: pandas Series.mode() returns sorted unique modes ascending.
    Take .iloc[0] (lowest-sorted) as the baseline.

    Iteration: enumerate via df_wide.iterrows() so the row keys in the set
    match the keys the template will use when looping with iterrows() in
    _grid.html (Pitfall — df_wide.index.tolist() can drift from iterrows()
    if multiindex enters; iterrows() is the canonical source).

    260507-w7h.
    """
    if df_wide.empty:
        return set()

    def _is_empty(v) -> bool:
        # pd.isna handles None + NaN; "" is a separate empty signal in EAV data.
        try:
            if pd.isna(v):
                return True
        except (TypeError, ValueError):
            pass
        return v == "" or v is None

    result: set[tuple[Hashable, str]] = set()
    value_cols = [c for c in df_wide.columns if c != index_col]

    if swap_axes:
        # Parameter is the row → mode per row, across value columns.
        for idx, row in df_wide.iterrows():
            non_empty = [row[c] for c in value_cols if not _is_empty(row[c])]
            if not non_empty:
                continue
            mode_baseline = pd.Series(non_empty).mode().iloc[0]
            for c in value_cols:
                v = row[c]
                if _is_empty(v):
                    continue
                if v != mode_baseline:
                    result.add((idx, c))
    else:
        # Parameter is a column → mode per column, across platform rows.
        for c in value_cols:
            col_values = df_wide[c]
            non_empty_mask = ~col_values.apply(_is_empty)
            non_empty = col_values[non_empty_mask]
            if non_empty.empty:
                continue
            mode_baseline = non_empty.mode().iloc[0]
            # Iterate via iterrows() so idx matches the template loop variable.
            for idx, row in df_wide.iterrows():
                v = row[c]
                if _is_empty(v):
                    continue
                if v != mode_baseline:
                    result.add((idx, c))

    return result


def build_view_model(
    db,
    db_name: str,
    selected_platforms: list[str],
    selected_param_labels: list[str],
    swap_axes: bool,
    highlight: bool = False,
) -> BrowseViewModel:
    """Pure orchestrator: catalog → filter → pivot → view-model.

    Empty-selection short-circuit avoids any DB call when either dimension is
    empty (matches v1.0 BROWSE behavior). DB calls only happen when BOTH
    platforms and params are present.

    260429-qyv: the Parameters catalog is sourced from
    list_parameters_for_platforms (NOT the unfiltered list_parameters), so
    the picker only ever surfaces parameters that exist for the currently
    selected platforms. When `selected_platforms` is empty, we set
    `params_disabled=True`, skip the call entirely, and surface
    `all_param_labels=[]`. Additionally, `selected_param_labels` is
    intersected against the platforms-filtered catalog BEFORE building the
    SQL filter — any "stale" label (e.g. checked while P2 was selected, then
    P2 was unchecked) is dropped server-side, so it cannot leak into
    fetch_cells.

    Catalog calls (list_platforms) ALWAYS run when db is set — popovers need
    the platforms list to render. They are TTLCache-backed (cheap).
    When `db is None` (lifespan permits this in Phase 1 smoke contracts),
    catalog calls are skipped and return empty lists; the view model is then
    a fully-empty placeholder.
    """
    params_disabled = not selected_platforms
    if db is None:
        all_platforms: list[str] = []
        all_param_labels: list[str] = []
    elif params_disabled:
        # Zero platforms selected → Parameters picker is disabled. We do NOT
        # query list_parameters_for_platforms with an empty tuple (the
        # data-layer short-circuit returns [] anyway, but skipping the call
        # avoids cache churn and makes the contract explicit at the
        # orchestrator level).
        all_platforms = list(list_platforms(db, db_name=db_name))
        all_param_labels = []
    else:
        all_platforms = list(list_platforms(db, db_name=db_name))
        # Sort + tuple-cast for stable cache key. Different orderings of the
        # same platform set must hit the same cache slot — matches the
        # fetch_cells caller-normalizes idiom.
        platforms_key = tuple(sorted(selected_platforms))
        all_params_raw = list(
            list_parameters_for_platforms(db, platforms_key, db_name=db_name)
        )
        # D-13: sort by COMBINED label, not (InfoCategory, Item) tuple.
        all_param_labels = sorted(
            f"{p['InfoCategory']}{PARAM_LABEL_SEP}{p['Item']}"
            for p in all_params_raw
        )

    # 260429-qyv: re-derive the checked-set on every call. Any param label
    # that is no longer in the filtered catalog is dropped from
    # selected_params, so stale "checked but invisible" parameters cannot
    # leak into fetch_cells. Order is preserved by iterating
    # selected_param_labels (user's original selection order) rather than
    # the catalog.
    available = set(all_param_labels)
    selected_params_filtered = [
        lbl for lbl in selected_param_labels if lbl in available
    ]

    index_col = "Item" if swap_axes else "PLATFORM_ID"

    # is_empty uses the FILTERED selected_params — a vm whose checked-set
    # was wiped by the intersection is treated as empty so the grid renders
    # the empty state and fetch_cells is not called with empty filters.
    is_empty = (not selected_platforms) or (not selected_params_filtered)
    if is_empty or db is None:
        return BrowseViewModel(
            df_wide=pd.DataFrame(),
            row_capped=False,
            col_capped=False,
            n_value_cols_total=0,
            n_rows=0,
            n_cols=0,
            swap_axes=swap_axes,
            selected_platforms=list(selected_platforms),
            selected_params=selected_params_filtered,
            all_platforms=all_platforms,
            all_param_labels=all_param_labels,
            is_empty_selection=True,
            params_disabled=params_disabled,
            index_col_name=index_col,
            highlight=highlight,
            # minority_cells defaults to empty set via __post_init__ — no
            # data to compute on in the empty branch.
        )

    # Parse labels from the FILTERED checked-set — the intersection above
    # is the source of truth. Garbage labels (no separator) still fall out
    # naturally via _parse_param_label, but they would already have been
    # dropped by the catalog intersection (they're not in any catalog).
    parsed = [
        p for lbl in selected_params_filtered if (p := _parse_param_label(lbl))
    ]
    infocategories = tuple(sorted({p[0] for p in parsed}))
    items = tuple(sorted({p[1] for p in parsed}))

    df_long, row_capped = fetch_cells(
        db,
        tuple(selected_platforms),
        infocategories,
        items,
        row_cap=ROW_CAP,
        db_name=db_name,
    )
    df_wide, col_capped = pivot_to_wide(
        df_long, swap_axes=swap_axes, col_cap=COL_CAP
    )
    # Subtract the index column from total columns to get the value-col count.
    n_value_cols_shown = max(0, len(df_wide.columns) - 1)

    # 260507-w7h — minority detection only runs when the user opts in via the
    # Highlight toggle. Pure render-layer decoration (no SQL or pivot effect).
    minority_cells = (
        _compute_minority_cells(df_wide, index_col, swap_axes)
        if highlight else set()
    )

    return BrowseViewModel(
        df_wide=df_wide,
        row_capped=row_capped,
        col_capped=col_capped,
        # n_value_cols_total uses the FILTERED count — that is the N for
        # "Showing first 30 of {N}" copy. After 260429-qyv, stale labels are
        # dropped before this count is computed, so the copy reflects what
        # was actually requestable, not the URL-param string length.
        n_value_cols_total=len(selected_params_filtered),
        n_rows=len(df_wide),
        n_cols=n_value_cols_shown,
        swap_axes=swap_axes,
        selected_platforms=list(selected_platforms),
        selected_params=selected_params_filtered,
        all_platforms=all_platforms,
        all_param_labels=all_param_labels,
        is_empty_selection=False,
        params_disabled=params_disabled,
        index_col_name=index_col,
        highlight=highlight,
        minority_cells=minority_cells,
    )


def _build_browse_url(
    platforms: list[str], params: list[str], swap: bool, highlight: bool = False
) -> str:
    """Compose /browse?platforms=...&params=...&swap=1&highlight=1 with repeated keys.

    Pitfall 6: use quote_via=urllib.parse.quote so spaces encode as %20
    (URL-style), not + (form-style). This makes the visible address-bar URL
    match what a manual <a href="?..."> would emit, and keeps shareable
    pasted URLs cosmetically consistent.

    D-30: repeated keys (?platforms=A&platforms=B) — NOT comma-separated.
    D-31: swap='1' if axes swapped, omitted otherwise.
    260507-w7h: highlight='1' if highlight toggle ON, omitted otherwise.
                Order pinned: highlight AFTER swap.
    """
    pairs: list[tuple[str, str]] = []
    pairs += [("platforms", p) for p in platforms]
    pairs += [("params", p) for p in params]
    if swap:
        pairs.append(("swap", "1"))
    if highlight:
        pairs.append(("highlight", "1"))
    if not pairs:
        return "/browse"
    qs = urllib.parse.urlencode(pairs, quote_via=urllib.parse.quote)
    return f"/browse?{qs}"
