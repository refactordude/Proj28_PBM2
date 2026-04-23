"""Export dialog — Excel + CSV downloads for Browse page (EXPORT-01, EXPORT-02).

Opens as @st.dialog triggered from the Pivot tab's Export button. Captures the
currently-visible wide pivot (D-15) or the raw long-form fetch_cells result (D-16
power-user scope).

Security note: _sanitize_filename provides defense-in-depth against path-traversal
and charset injection. The browser's save-as dialog is the ultimate gate on filesystem
writes (T-07-01, T-07-02).
"""
from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st

_EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_CSV_MIME = "text/csv"

_FMT_XLSX = "Excel (.xlsx)"
_FMT_CSV = "CSV (.csv)"
_SCOPE_WIDE = "Current view (wide)"
_SCOPE_LONG = "Full result (long)"


def _sanitize_filename(name: Optional[str]) -> str:
    """Path-traversal-safe filename sanitizer.

    Rules (applied in order):
    1. None input -> return 'ufs_export'
    2. Remove every occurrence of '..' (path traversal defense)
    3. Replace any character outside [A-Za-z0-9_-.] with '_'
    4. Collapse runs of '_' to a single '_'
    5. Strip leading/trailing '.' and '_'
    6. Truncate to 128 characters
    7. Empty result -> return 'ufs_export'

    T-07-01: strips '..' before charset clamp so path separators and traversal
    sequences are eliminated before the allowed-set filter runs.
    T-07-02: charset clamp removes all angle brackets, quotes, and ampersands.
    """
    if name is None:
        return "ufs_export"
    # Step 2: Remove '..' occurrences (defense against ../ path traversal)
    s = name.replace("..", "")
    # Step 3: Remap any character outside the allowed set to '_'
    s = re.sub(r"[^A-Za-z0-9_\-.]", "_", s)
    # Step 4: Collapse repeated underscores
    s = re.sub(r"_+", "_", s)
    # Step 5: Strip leading/trailing dots and underscores
    s = s.strip("._")
    # Step 6: Truncate to 128 characters
    s = s[:128]
    # Step 7: Fallback on empty
    return s or "ufs_export"


def _default_filename(scope_token: str, ext: str) -> str:
    """Build the default filename template 'ufs_{scope}_{YYYYMMDD}.{ext}'.

    Args:
        scope_token: 'wide' or 'long'
        ext: 'xlsx' or 'csv'
    """
    date = datetime.now().strftime("%Y%m%d")
    return f"ufs_{scope_token}_{date}.{ext}"


def _write_excel_bytes(df: pd.DataFrame, sheet_name: str = "UFS") -> bytes:
    """Write df to an in-memory xlsx via openpyxl. Auto-sizes columns by header length.

    Column width rule: min(50, max(12, len(header))) applied via openpyxl
    worksheet.column_dimensions[letter].width (1-based column index via
    openpyxl.utils.get_column_letter).

    Returns raw bytes starting with the PK zip header (xlsx is a zip archive).
    """
    import openpyxl.utils  # local import to keep module-level import cheap

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        worksheet = writer.sheets[sheet_name]
        for idx, column_name in enumerate(df.columns):
            header_len = len(str(column_name))
            width = min(50, max(12, header_len))
            letter = openpyxl.utils.get_column_letter(idx + 1)
            worksheet.column_dimensions[letter].width = width
    return buf.getvalue()


def _write_csv_bytes(df: pd.DataFrame) -> bytes:
    """Write df to CSV bytes with a utf-8-sig BOM prefix (EXPORT-02).

    Enables Excel double-click without mojibake on Windows/Mac.

    IMPORTANT: to_csv() without an encoding arg returns a plain str (no BOM).
    We then call .encode('utf-8-sig') to add exactly ONE BOM (0xEF 0xBB 0xBF).
    Do NOT pass encoding='utf-8-sig' to to_csv() AND also call .encode('utf-8-sig')
    — that yields a double-BOM (6 bytes: EF BB BF EF BB BF) which corrupts the
    first cell value in Excel.
    """
    return df.to_csv(index=False).encode("utf-8-sig")


@st.dialog("Export data")
def render_export_dialog(
    df_wide: Optional[pd.DataFrame],
    df_long: Optional[pd.DataFrame],
) -> None:
    """Render the export dialog. At least one DataFrame must be non-empty.

    Callers MUST disable the Export button when both are empty/None — a defensive
    ValueError is raised if this contract is violated.

    Behavior contract:
      - Format radio: 'Excel (.xlsx)' | 'CSV (.csv)'
      - Scope radio (only when both df_wide and df_long are non-empty):
        'Current view (wide)' | 'Full result (long)'
      - Filename: default 'ufs_{scope}_{YYYYMMDD}.{ext}'; user-editable;
        sanitized before use (path-traversal + charset clamp per T-07-01/02)
      - Download button: label 'Download', correct MIME per format
      - Close button: label 'Close' (not 'Cancel') — triggers st.rerun

    D-15: Export captures the currently-visible view. This function reads DataFrames
    passed by the caller (stashed from a previous rerun by _render_pivot_tab) — NOT
    a fresh fetch_cells call — so what the user sees is exactly what they get.

    Pitfall 6 mitigation: file bytes are built EAGERLY at the top of each dialog rerun
    (before the Download button renders) so st.download_button is primed with data on
    first render. Clicking it triggers the browser download immediately even if the
    subsequent rerun closes the dialog.
    """
    wide_ok = df_wide is not None and not df_wide.empty
    long_ok = df_long is not None and not df_long.empty
    if not wide_ok and not long_ok:
        raise ValueError(
            "render_export_dialog: at least one of df_wide or df_long must be non-empty. "
            "Callers must disable the Export button when both are empty/None."
        )

    # Format radio (EXPORT-01 + EXPORT-02)
    fmt = st.radio("Format", [_FMT_XLSX, _FMT_CSV], horizontal=True, key="export.format")
    ext = "xlsx" if fmt == _FMT_XLSX else "csv"

    # Scope radio — rendered only when both scopes are available (D-16)
    if wide_ok and long_ok:
        scope = st.radio(
            "Scope",
            [_SCOPE_WIDE, _SCOPE_LONG],
            index=0,
            key="export.scope",
        )
    elif wide_ok:
        scope = _SCOPE_WIDE
        st.caption(f"Scope: {_SCOPE_WIDE}")
    else:
        scope = _SCOPE_LONG
        st.caption(f"Scope: {_SCOPE_LONG}")

    scope_token = "wide" if scope == _SCOPE_WIDE else "long"
    scope_df: pd.DataFrame = df_wide if scope == _SCOPE_WIDE else df_long  # type: ignore[assignment]

    # Filename input with default template
    default_name = _default_filename(scope_token, ext)
    filename = st.text_input("Filename", value=default_name, key="export.filename")
    st.caption("File will be saved to your Downloads folder.")

    # Build file bytes EAGERLY so st.download_button is primed on first render (Pitfall 6)
    # Sanitize the stem (portion before last '.') then re-attach the canonical extension.
    base_stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    safe_stem = _sanitize_filename(base_stem)
    full_name = f"{safe_stem}.{ext}"

    if fmt == _FMT_XLSX:
        file_bytes = _write_excel_bytes(scope_df)
        mime = _EXCEL_MIME
    else:
        file_bytes = _write_csv_bytes(scope_df)
        mime = _CSV_MIME

    # Download + Close action row
    col_dl, col_close = st.columns([1, 1])
    with col_dl:
        st.download_button(
            "Download",
            data=file_bytes,
            file_name=full_name,
            mime=mime,
            type="primary",
            key="export.download",
        )
    with col_close:
        if st.button("Close", type="secondary", key="export.close"):
            st.rerun()
