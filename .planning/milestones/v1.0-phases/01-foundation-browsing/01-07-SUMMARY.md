---
phase: 01-foundation-browsing
plan: "07"
subsystem: browse-page
tags: [export, excel, csv, openpyxl, dialog, EXPORT-01, EXPORT-02, D-15, D-16]

# Dependency graph
requires:
  - "01-05: browse.py Pivot tab, session state keys"
  - "01-06: ctrl_export slot is st.empty() placeholder; _sync_state_to_url takes 4 args"
  - "01-03: fetch_cells returns (df_long, row_capped); pivot_to_wide returns (df_wide, col_capped)"
provides:
  - "app/components/export_dialog.py — render_export_dialog + helpers"
  - "app/components/__init__.py — package namespace"
  - "Session state keys: pivot.df_wide (pd.DataFrame|None), pivot.df_long (pd.DataFrame|None)"
  - "Browse Pivot tab: Export button wired (D-16), stash updated after pivot_to_wide (D-15)"
affects:
  - "Phase 1 is now feature-complete (all EXPORT, BROWSE, VIZ, DATA, FOUND-04..08 requirements satisfied)"

# Tech tracking
tech-stack:
  added:
    - "openpyxl — installed into .venv (was listed in requirements.txt but missing from venv)"
  patterns:
    - "pd.ExcelWriter(BytesIO, engine='openpyxl') — in-memory xlsx generation; no temp file"
    - "df.to_csv(index=False).encode('utf-8-sig') — single BOM; never pass encoding to to_csv AND encode again"
    - "@st.dialog decorator — modal dialog owned by the function; caller triggers via button click"
    - "File bytes built EAGERLY before st.download_button renders (Pitfall 6 mitigation)"
    - "Previous-rerun stash pattern: Export reads pivot.df_wide/df_long from session_state set by prior rerun"

key-files:
  created:
    - app/components/__init__.py
    - app/components/export_dialog.py
  modified:
    - app/pages/browse.py

decisions:
  - "CSV encoding: to_csv(index=False) returns BOM-free str; .encode('utf-8-sig') adds exactly one BOM (0xEF BB BF). Double-BOM corruption avoidance: do NOT pass encoding='utf-8-sig' to to_csv AND call .encode('utf-8-sig') — that produces 6 BOM bytes and corrupts cell A1 in Excel."
  - "Export is Pivot-tab-only in Phase 1. Detail tab (long-form only, no Scope radio) and Chart tab (not exported per D-15) are explicitly out of Phase 1 scope."
  - "Session state keys pivot.df_wide and pivot.df_long store DataFrames, not filter selections. They are recomputed on every rerun that reaches pivot_to_wide — they are NOT persisted across browser sessions."
  - "Filename sanitization is defense-in-depth (T-07-01, T-07-02). The browser's save-as dialog is the ultimate gate on filesystem writes. Sanitized names are pure ASCII alphanumeric + dot/dash/underscore, max 128 chars."
  - "openpyxl was listed in requirements.txt but absent from the project venv — installed as Rule 3 auto-fix (missing dependency blocking task completion)."

# Metrics
duration: "4min"
completed: "2026-04-23"
---

# Phase 01 Plan 07: Export Dialog Summary

**Excel export (EXPORT-01) + CSV export (EXPORT-02) via a single st.dialog component wired into the Pivot tab's ctrl_export slot**

## Performance

- **Duration:** ~4 minutes
- **Started:** 2026-04-23T19:41:53Z
- **Completed:** 2026-04-23T19:45:30Z
- **Tasks:** 2 (each committed individually)
- **Files created:** 2 / **Files modified:** 1

## Accomplishments

- `app/components/__init__.py` created — new package namespace for reusable UI components
- `app/components/export_dialog.py` created (199 lines):
  - `render_export_dialog(df_wide, df_long)` — `@st.dialog("Export data")` entry point
  - `_sanitize_filename(name)` — path-traversal-safe: strips `..`, remaps non-`[A-Za-z0-9_-.]`, collapses `_`, truncates 128, falls back to `ufs_export`
  - `_default_filename(scope_token, ext)` — generates `ufs_{scope}_{YYYYMMDD}.{ext}`
  - `_write_excel_bytes(df, sheet_name="UFS")` — `pd.ExcelWriter(BytesIO, engine="openpyxl")` with auto-sized column widths via `worksheet.column_dimensions`
  - `_write_csv_bytes(df)` — `df.to_csv(index=False).encode("utf-8-sig")` — single BOM; Excel double-click works without mojibake
- `app/pages/browse.py` updated:
  - `from app.components.export_dialog import render_export_dialog` added
  - `st.empty()` placeholder in `ctrl_export` replaced with Export button (`key="pivot_export"`, `type="secondary"`)
  - Button disabled with `help="Select platforms and parameters first"` tooltip when no pivot stash exists
  - `st.session_state["pivot.df_wide"]` and `st.session_state["pivot.df_long"]` written after `pivot_to_wide`, before `st.dataframe` (D-15 fidelity)
  - Early-exit paths (empty df_long, exceptions) leave stash untouched

## Public API

### `render_export_dialog(df_wide, df_long)`

```python
@st.dialog("Export data")
def render_export_dialog(
    df_wide: Optional[pd.DataFrame],   # current Pivot grid (post-cap, post-swap)
    df_long: Optional[pd.DataFrame],   # raw fetch_cells long-form result
) -> None:
```

- At least one DataFrame must be non-empty; raises `ValueError` otherwise (caller must disable button)
- Format radio: `"Excel (.xlsx)"` | `"CSV (.csv)"` (horizontal)
- Scope radio: shown only when BOTH are non-empty; `"Current view (wide)"` | `"Full result (long)"`
- Filename: editable `text_input` with default `ufs_{scope}_{YYYYMMDD}.{ext}`, hint `"File will be saved to your Downloads folder."`
- Download: `st.download_button("Download", ...)` with correct MIME per format, `type="primary"`
- Close: `st.button("Close", type="secondary")` calls `st.rerun()`
- File bytes built eagerly (Pitfall 6 — dialog stays open during download trigger)

### Session State Keys Added

| Key | Type | Description |
|-----|------|-------------|
| `pivot.df_wide` | `pd.DataFrame \| None` | Exact DataFrame currently rendered in Pivot grid (post-cap, post-swap). Re-computed each rerun — NOT persisted across browser sessions. |
| `pivot.df_long` | `pd.DataFrame \| None` | Raw long-form fetch_cells result (pre-pivot). Same lifecycle as `pivot.df_wide`. |

Internal dialog keys (ephemeral): `export.format`, `export.scope`, `export.filename`, `export.download`, `export.close`

### MIME Constants

| Format | MIME |
|--------|------|
| xlsx | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| csv | `text/csv` |

## Security Notes

- **T-07-01 (path traversal):** `_sanitize_filename` strips `..` BEFORE the charset clamp, then remaps `/`, `\`, space, and all non-`[A-Za-z0-9_-.]` characters to `_`. Result is a pure basename. Browser save-as dialog is the ultimate filesystem gate.
- **T-07-02 (XSS via filename):** charset clamp removes all `<`, `>`, `"`, `'`, `&` — file_name is pure ASCII-alphanumeric + dot/dash/underscore.
- **T-07-03 (DoS via large export):** inherited from upstream caps — 200-row LIMIT in `fetch_cells` + 30-column cap in `pivot_to_wide`. Worst case ~200×30 xlsx is well within memory limits.
- **T-07-04 (unfiltered data leak):** D-15 contract — Export reads `session_state` stash, never issues a fresh `fetch_cells` call. What the user sees is exactly what they export.

## Phase 1 Scope Note

Export is **Pivot-tab-only** in Phase 1 per D-15 / D-16:

- **Detail tab:** Would need a different dialog shape (long-form only; no Scope radio). Out of Phase 1 scope.
- **Chart tab:** Explicitly not exported (D-15: "Charts are not exported; screenshot is user's responsibility").

## Task Commits

1. **Task 1: export_dialog component** — `23b2954` (feat)
2. **Task 2: wire Export button into browse.py** — `dce9c92` (feat)

## Files Created/Modified

- `app/components/__init__.py` — 2 lines; new package init
- `app/components/export_dialog.py` — 199 lines; full export dialog with helpers
- `app/pages/browse.py` — +22/-4 lines; Export button wired, stash added

## Decisions Made

- **CSV BOM encoding:** `to_csv(index=False).encode("utf-8-sig")` — single BOM. Never pass `encoding="utf-8-sig"` to `to_csv` AND also `.encode("utf-8-sig")` — double-BOM corrupts Excel cell A1.
- **Pivot-tab export only:** Detail and Chart tab export are out of Phase 1 scope per D-15/D-16.
- **pivot.df_wide / pivot.df_long are DataFrames not filter keys:** Re-computed each rerun. Not persisted across browser sessions.
- **Filename sanitization is defense-in-depth:** Browser save-as is the ultimate gate; `_sanitize_filename` is defense-in-depth for server-side safety.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Missing Dependency] openpyxl absent from project venv**

- **Found during:** Task 1 verification
- **Issue:** `openpyxl>=3.1` is listed in `requirements.txt` but was not installed in `.venv`. `_write_excel_bytes` raised `ModuleNotFoundError: No module named 'openpyxl'` during acceptance checks.
- **Fix:** Ran `.venv/bin/pip install openpyxl>=3.1` to install the package.
- **Files modified:** none (venv state only)
- **Commit:** n/a (runtime dependency install, not a code change)

## Known Stubs

None — all export functionality is fully wired. The Export button reads real session_state DataFrames and produces real xlsx/csv bytes.

## Threat Flags

No new threat surface beyond the plan's threat model. All T-07-01..06 dispositions implemented or accepted as documented.

## Self-Check: PASSED
