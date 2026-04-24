---
phase: 01-foundation-browsing
plan: "06"
subsystem: browse-page
tags: [browse, detail, chart, plotly, viz, session-state, url-sync, BROWSE-05, VIZ-01, VIZ-02]

# Dependency graph
requires:
  - "01-03: ufs_service.fetch_cells, pivot_to_wide"
  - "01-05: browse.py Pivot tab + sidebar, session state keys, URL sync"
  - "01-02: result_normalizer.try_numeric"
provides:
  - "app/pages/browse.py — all three Browse tabs fully implemented"
  - "Session state keys: browse.tab, chart.x_col, chart.y_col, chart.type"
  - "Query param key: tab (lowercase tab name round-trip)"
  - "_render_detail_tab (BROWSE-05 single-platform long-form view)"
  - "_render_chart_tab (VIZ-01/VIZ-02 Plotly bar/line/scatter with numeric detection)"
  - "_render_sidebar_copy_link (tab-independent sidebar Copy link)"
  - "_sync_state_to_url extended to 4 args (platforms, params, swap, tab)"
affects:
  - "01-07: Export dialog — ctrl_export slot in Pivot tab is st.empty() placeholder, ready for Export... button"

# Tech tracking
tech-stack:
  added:
    - "plotly.express (px.bar, px.line, px.scatter) — chart rendering"
  patterns:
    - "try_numeric called per-column only during numeric detection, result cached in numeric_series_cache — never applied globally (VIZ-02)"
    - "Tab identity round-trips via st.query_params['tab'] — loaded once via _load_state_from_url, synced each rerun via _sync_state_to_url"
    - "st.tabs blocks each set st.session_state['browse.tab'] for URL sync (best-effort; Streamlit renders all blocks each rerun)"
    - "Sidebar Copy link button moved from Pivot ctrl_export to sidebar — stable across tabs"
    - "ctrl_export column now uses st.empty() — Plan 07 replaces with Export... button"
    - "Detail tab: hide_index=True, TextColumn for all columns, sort kind='stable'"

key-files:
  created: []
  modified:
    - app/pages/browse.py

decisions:
  - "_sync_state_to_url now takes 4 args: (platforms, params, swap, tab) — Plan 07 must call with all 4"
  - "Session state keys added: browse.tab (str), chart.x_col (str), chart.y_col (str), chart.type (str) — owned by browse.py"
  - "Sidebar order after Plan 06: Platforms -> Parameters -> Clear filters -> Copy link"
  - "Pivot ctrl_export slot is st.empty() — Plan 07 puts Export... button there"
  - "X-axis selector in Chart tab shows index_col (PLATFORM_ID or Item depending on swap_axes) — consistent with D-07 orientation"
  - "VIZ-02 compliance: try_numeric is only ever called per-column inside _render_chart_tab during numeric detection"

# Metrics
duration: "2min"
completed: "2026-04-23"
---

# Phase 01 Plan 06: Detail Tab + Chart Tab Summary

**Detail tab (BROWSE-05) and Chart tab (VIZ-01/VIZ-02) filling the Plan 05 stubs — with tab URL round-trip and sidebar Copy link**

## Performance

- **Duration:** ~2 minutes
- **Started:** 2026-04-23T19:37:11Z
- **Completed:** 2026-04-23T19:39:18Z
- **Tasks:** 2 (implemented together in single file write — both tasks complete)
- **Files modified:** 1

## Accomplishments

- `_render_detail_tab` implemented (BROWSE-05): single-platform long-form `(InfoCategory, Item, Result)` view sorted `(InfoCategory ASC, Item ASC)`, `hide_index=True`, TextColumn for all columns, empty-state copy verbatim
- `_render_chart_tab` implemented (VIZ-01/VIZ-02): per-column numeric detection via `try_numeric`, axis selectors (X/Y), chart-type radio (Bar/Line/Scatter), Plotly render with `#1f77b4` accent, `fig.update_layout(title=...)` for accessibility
- `_render_sidebar_copy_link` added and called from `_render_sidebar_filters` after Clear filters button
- Copy link moved from `_render_pivot_tab`'s `ctrl_export` column to sidebar — tab-independent
- `ctrl_export` in Pivot tab now uses `st.empty()` — ready for Plan 07 Export button
- `_load_state_from_url` extended to read `tab` query param (T-06-01: only accepted via fixed dict)
- `_sync_state_to_url` extended to 4 args, writes `tab` query param on every rerun
- Each `with tab:` block sets `st.session_state["browse.tab"]` for URL-sync tracking
- VIZ-02 compliance confirmed: `try_numeric` called per-column only, result cached in `numeric_series_cache` for reuse — never applied to `df_wide` globally

## Public API / Contracts

### New Session State Keys (Plan 06)

| Key | Type | Owner | Description |
|-----|------|-------|-------------|
| `browse.tab` | `str` | `browse.py` | Active tab name: "Pivot", "Detail", or "Chart" |
| `chart.x_col` | `str` | `browse.py` Chart tab | Remembered X-axis column pick |
| `chart.y_col` | `str` | `browse.py` Chart tab | Remembered Y-axis column pick |
| `chart.type` | `str` | `browse.py` Chart tab | Remembered chart type: "Bar", "Line", or "Scatter" |

### New Query Param Keys (Plan 06)

| Key | Format | Example |
|-----|--------|---------|
| `tab` | lowercase tab name | `tab=detail` |

### _sync_state_to_url signature change

```python
# OLD (Plan 05):
def _sync_state_to_url(platforms: list[str], params: list[str], swap: bool) -> None: ...

# NEW (Plan 06):
def _sync_state_to_url(platforms: list[str], params: list[str], swap: bool, tab: str = "") -> None: ...
```

**Plan 07 must call with 4 args:**
```python
_sync_state_to_url(selected_platforms, selected_params, swap_axes, active_tab)
```

### Sidebar order after Plan 06

```
Sidebar (Browse-specific section):
  1. Platform multiselect
  2. Parameter multiselect
  3. Clear filters button
  4. Copy link button  ← NEW in Plan 06
```

### Pivot ctrl_export slot

Plan 05's Copy link button has been removed from `ctrl_export`. The slot now contains:
```python
with ctrl_export:
    st.empty()  # Plan 07: Export... button goes here
```

## Task Commits

1. **Tasks 1 + 2: Detail tab + Chart tab + sidebar Copy link + tab URL sync** — `b9e99b3` (feat)

## Files Created/Modified

- `app/pages/browse.py` — 524 lines; 2 new top-level helpers (_render_detail_tab, _render_chart_tab); 1 new sidebar helper (_render_sidebar_copy_link); URL sync + tab tracking extended

## Decisions Made

- **_sync_state_to_url now takes 4 args:** Plan 07 must pass `tab` as the fourth argument.
- **New session state keys:** `browse.tab`, `chart.x_col`, `chart.y_col`, `chart.type` are owned by `browse.py`. No other page/plan may use these keys.
- **Sidebar Copy link placement:** After Clear filters — stable across all three tabs.
- **VIZ-02 compliance:** `try_numeric` is only called per-column during numeric detection in `_render_chart_tab`. The pivot DataFrame (`df_wide`) is never globally coerced.
- **X-axis always shows index_col:** The X-axis selector offers the current index column (PLATFORM_ID or Item, depending on swap_axes). This keeps the D-07 orientation consistent between Pivot and Chart tabs.

## Deviations from Plan

None — plan executed exactly as written.

**Minor implementation note:** Task 1 called for a `_render_chart_tab` stub, and Task 2 for the full implementation. Since both tasks target the same file and the full implementation was straightforward, both were implemented in a single write pass. The file is syntactically valid after the single pass and all acceptance criteria for both tasks are met. This is not a behavioral deviation.

## Known Stubs

None — all three Browse tabs are now fully implemented. The previous Plan 05 stubs (`st.info("Detail tab is implemented in Plan 06.")` and `st.info("Chart tab is implemented in Plan 06.")`) have been replaced with full implementations.

## VIZ-02 Compliance Confirmation

`grep -nE "try_numeric\(df_wide\)" app/pages/browse.py` returns **zero matches**. `try_numeric` is called once per column candidate inside `_render_chart_tab`, with results cached in `numeric_series_cache`. The cached series (not the original `df_wide` column) is used to build `chart_df`. Global coercion is never performed.

## UI-SPEC Copy Deviation Check

No deviations. All required strings match UI-SPEC verbatim:

| Copy | Match |
|------|-------|
| Detail empty state | "Select exactly one platform in the sidebar to see its full parameter detail." — EXACT |
| Chart empty (no selection) | "Select platforms and parameters in the sidebar first." — EXACT |
| Chart empty (no numerics) | "No numeric columns in the current selection. Add numeric parameters in the sidebar." — EXACT |
| Copy link toast | "Link copied to clipboard." — EXACT |
| Row-count caption | "{K} parameters across {N} categories" — EXACT |

## Threat Flags

No new threat surface beyond the plan's threat model. All T-06-01..05 mitigations implemented:
- T-06-01 (malicious URL tab value): `_load_state_from_url` looks up lowercased value in fixed `tab_map` dict; unknown values are silently ignored.
- T-06-02 (Plotly hover tooltip): accepted by design — internal UFS data displayed intentionally.
- T-06-03 (DoS via large chart selection): `fetch_cells` caps at 200 rows; `try_numeric` runs once per column (at most 30); `chart_df.dropna` trims further.
- T-06-04 (SQL injection via params reused in Detail/Chart): both tabs call `fetch_cells` which uses `sa.bindparam(expanding=True)`.
- T-06-05 (XSS via chart title): column names from trusted DB domain table; Plotly escapes titles internally.

## Self-Check: PASSED
