---
phase: 01-foundation-browsing
fixed_at: 2026-04-23T19:55:17Z
review_path: .planning/phases/01-foundation-browsing/01-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-04-23T19:55:17Z
**Source review:** .planning/phases/01-foundation-browsing/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (1 Critical + 5 Warning)
- Fixed: 6
- Skipped: 0

## Fixed Issues

### CR-01: f-string table name interpolation in SQL strings (ufs_service.py)

**Files modified:** `app/services/ufs_service.py`
**Commit:** 521d9b5
**Applied fix:** Added `_ALLOWED_TABLES` frozenset and `_safe_table()` guard function at module level. Updated all four SQL sites (`list_platforms`, `list_parameters`, and both branches of `fetch_cells`) to call `tbl = _safe_table(_TABLE)` and use `{tbl}` in the f-string instead of `{_TABLE}` directly. The allowlist guard raises `ValueError` if the table name is ever not `"ufs_data"`, making the defence independent of the constant's source.

---

### WR-01: Multi-DB cache collision — `_db` skipped in cache key (ufs_service.py)

**Files modified:** `app/services/ufs_service.py`, `app/pages/browse.py`
**Commit:** 2e4575a
**Applied fix:** Added `db_name: str = ""` parameter to `list_platforms`, `list_parameters`, and `fetch_cells`. The parameter is hashable so Streamlit includes it in the cache key automatically. Updated all three `fetch_cells` call sites in browse.py to pass `db_name=adapter.config.name`, and updated the `list_platforms` / `list_parameters` call sites in `_render_sidebar_filters` to pass `db_name=db_name` (the `db_name` argument already in scope from that function's signature).

---

### WR-02: Bare `except` swallows SQLAlchemy engine errors silently (mysql.py)

**Files modified:** `app/adapters/db/mysql.py`
**Commit:** bada288
**Applied fix:** Added `import logging` and `logger = logging.getLogger(__name__)` at module level. Changed the bare `except Exception:` in `get_schema` to `except Exception as exc:` and added `logger.debug("get_pk_constraint failed for table %s: %s", t, exc)` before `pk_cols = set()`. Exceptions are still swallowed (the correct behaviour for a missing PK constraint) but are now visible in debug logs during DB troubleshooting.

---

### WR-03: `pd.isna()` raises `TypeError` on scalar non-NA values in `try_numeric` (result_normalizer.py)

**Files modified:** `app/services/result_normalizer.py`
**Commit:** f5b72c7
**Applied fix:** Wrapped the `if pd.isna(val): return pd.NA` guard inside `try/except (TypeError, ValueError): pass` in `_coerce`, mirroring the safe pattern already used in `is_missing`. Array-like values that cause `pd.isna` to return an array (raising `ValueError` on bool coercion in pandas 3.x) now fall through to the string coercion path instead of raising.

---

### WR-04: `_sanitize_filename` step ordering — `/` unhandled until charset clamp (export_dialog.py)

**Files modified:** `app/components/export_dialog.py`
**Commit:** 44f7137
**Applied fix:** Extended step 2 to explicitly remove `/` and `\` in addition to `..`: `name.replace("..", "").replace("/", "").replace("\\", "")`. Added a comment explaining that this makes the path-traversal defence independent of step ordering — the charset clamp (step 3) remains as a second layer but is no longer the sole handler for path separators.

---

### WR-05: `browse.tab` session state written unconditionally in all three `with tab:` blocks (browse.py)

**Files modified:** `app/pages/browse.py`
**Commit:** 9db44d2
**Applied fix:** Removed all three unconditional `st.session_state["browse.tab"] = "..."` assignments from the `with pivot_tab:`, `with detail_tab:`, and `with chart_tab:` blocks. `browse.tab` is now set only by `_load_state_from_url` (one-shot on page load from the URL `?tab=` parameter) and persists across reruns via session_state. Added a comment in the pivot_tab block explaining why the writes were removed, so the intent is clear to future readers.

---

_Fixed: 2026-04-23T19:55:17Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
