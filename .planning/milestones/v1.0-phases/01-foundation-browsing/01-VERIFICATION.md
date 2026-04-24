---
phase: 01-foundation-browsing
verified: 2026-04-23T20:00:00Z
status: human_needed
score: 16/16 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open the app in a browser (`streamlit run streamlit_app.py`), navigate to Browse, select 1+ platforms and 1+ parameters, and verify the pivot grid renders with a row-count caption showing 'N platforms × K parameters'."
    expected: "Wide-form grid appears; caption shows exact unicode × character; swap-axes toggle flips orientation."
    why_human: "st.dataframe rendering and toggle interaction require a live browser; cannot verify grid layout or widget interactivity programmatically."
  - test: "With a pivot result visible, click 'Export', choose Excel (.xlsx), and click Download. Open the downloaded file in Excel."
    expected: "File opens in Excel with a single sheet named 'UFS'; column widths are auto-sized; no encoding corruption."
    why_human: "Excel file correctness (column widths, sheet name display) requires visual inspection of an opened spreadsheet. CSV BOM correctness was verified programmatically but Excel rendering requires manual check."
  - test: "On the Browse page, click the 'Copy link' button in the sidebar. Open a new browser tab, paste the URL, and verify the same platforms/parameters/tab are pre-selected."
    expected: "URL contains `platforms=`, `params=`, `swap=` (if swapped), and `tab=` query params. Pasting the URL reproduces the same filter state."
    why_human: "navigator.clipboard.writeText runs in the browser; URL round-trip requires a live browser session with two tabs."
  - test: "On the Settings page, add a DB entry, click Test, fill credentials, click Save Connection. Verify the toast 'Saved. Caches refreshed.' appears and config/settings.yaml is updated."
    expected: "Toast appears; settings.yaml is written; subsequent Browse page reload uses new connection."
    why_human: "Streamlit toast display, dialog interactions, and filesystem write confirmation require a live browser session."
  - test: "On the Browse page, navigate to the Detail tab with exactly one platform selected. Verify long-form (InfoCategory, Item, Result) rows appear sorted by InfoCategory ASC, Item ASC."
    expected: "Detail tab shows rows with correct sort order; row-count caption shows 'K parameters across N categories'."
    why_human: "Sort order and detail view layout require visual verification against real DB data or a populated test fixture in a live session."
  - test: "On the Browse page, navigate to the Chart tab with numeric parameters selected. Verify axis selectors, chart-type radio, and Plotly chart render with the accent color #1f77b4."
    expected: "Chart renders with correct accent color; axis selectors are populated with PLATFORM_ID / Item and numeric columns only."
    why_human: "Plotly chart rendering and color accuracy require visual inspection in a live browser."
---

# Phase 1: Foundation + Browsing — Verification Report

**Phase Goal:** Users can browse, filter, visualize, and export UFS parameter data without writing SQL — and the app is safely deployable to the team intranet. (Auth deferred to pre-deployment phase per D-04; gitignore covers credential files.)
**Verified:** 2026-04-23T20:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | App runs on the team intranet without auth; `config/auth.yaml` and `.env` are gitignored (SC#1 / D-04) | ✓ VERIFIED | `.gitignore` has exact lines `config/auth.yaml`, `config/settings.yaml`, `.env`; `git check-ignore` confirms all three are ignored; no `streamlit_authenticator` import anywhere in Phase 1 code |
| 2 | User can configure, test, and save DB and LLM connections from the Settings page (SC#2) | ✓ VERIFIED | `app/pages/settings.py` (251 lines) has `_render_db_entry`, `_render_llm_entry`, `_test_db_connection`, `_test_llm_connection`, `_persist_and_clear_caches`; exact UI-SPEC copy strings present; password/api_key fields use `type="password"`; cache clears wired; file syntax-checks pass |
| 3 | User can select platforms and parameters and see a wide-form pivot grid with a row-count indicator (SC#3) | ✓ VERIFIED | `app/pages/browse.py` (552 lines) wires `list_platforms`, `list_parameters`, `fetch_cells`, `pivot_to_wide`; `_render_pivot_tab` renders `st.dataframe` with `TextColumn` for all columns; row-count caption with unicode `×` generated correctly; swap-axes toggle present |
| 4 | User can chart numeric columns and download as Excel or CSV (SC#4) | ✓ VERIFIED | `_render_chart_tab` uses per-column `try_numeric` detection + `px.bar/line/scatter` with `#1f77b4` accent; `app/components/export_dialog.py` delivers xlsx via `pd.ExcelWriter(engine="openpyxl")` and CSV via `to_csv().encode("utf-8-sig")`; Excel and CSV round-trip assertions pass |
| 5 | Filter selections persist via session_state and can be shared as a URL (SC#5) | ✓ VERIFIED | `selected_platforms`, `selected_params`, `pivot_swap_axes`, `browse.tab` all in session_state; `_load_state_from_url` / `_sync_state_to_url` write `platforms`, `params`, `swap`, `tab` to `st.query_params`; sidebar Copy link button present |
| 6 | MySQLAdapter uses `pool_pre_ping=True` and `pool_recycle=3600` (FOUND-06) | ✓ VERIFIED | Both present in `app/adapters/db/mysql.py`; `pd.read_sql_query` used (not deprecated `pd.read_sql`); `SET SESSION TRANSACTION READ ONLY` preserved |
| 7 | result_normalizer maps missing/error sentinels to pd.NA without coercing (DATA-01/02) | ✓ VERIFIED | All 10 public symbols present; 65 tests pass; `is_missing('None')` returns True; `classify('0x1F')` returns `ResultType.HEX` without coercion; smoke tests pass |
| 8 | ufs_service never loads the full table; uses parameterized IN clauses with row cap (DATA-05/07) | ✓ VERIFIED | `fetch_cells` short-circuits on empty inputs; 8 `expanding=True` bindparam usages; `LIMIT row_cap+1` row-cap trick; no f-string interpolation of user data; SQL injection audit passes |
| 9 | `requirements.txt` pins `sqlalchemy>=2.0,<2.1` and adds `pydantic-ai>=1.0,<2.0` (FOUND-08) | ✓ VERIFIED | Both pins present; `pandas>=3.0` also added as required |
| 10 | All DB query results are cached with `@st.cache_data(ttl=300)` keyed on immutable args (FOUND-07) | ✓ VERIFIED | `list_platforms` and `list_parameters` have `@st.cache_data(ttl=300, show_spinner=False)`; `fetch_cells` has `@st.cache_data(ttl=60)`; `_db` underscore prefix disables hashing |
| 11 | Pivot grid uses `TextColumn` for all Result columns — never `NumberColumn` (heterogeneity contract) | ✓ VERIFIED | `grep -c "st.column_config.NumberColumn" app/pages/browse.py` returns 0; `TextColumn` used for all columns in pivot and detail grids |
| 12 | VIZ-02: `try_numeric` is only called per-column, never globally on `df_wide` | ✓ VERIFIED | `grep -nE "try_numeric\(df_wide\)" app/pages/browse.py` returns zero matches; `numeric_series_cache` pattern used correctly |
| 13 | Export filename sanitization blocks path traversal; CSV has exactly one BOM | ✓ VERIFIED | `_sanitize_filename('../../../etc/passwd')` contains no `..` or `/`; `_write_csv_bytes` produces bytes starting with `0xEF 0xBB 0xBF` with no double-BOM; both smoke tests pass programmatically |
| 14 | SAFE-01: `SET SESSION TRANSACTION READ ONLY` attempted non-fatally in both MySQLAdapter and ufs_service | ✓ VERIFIED | Present in `mysql.py` `run_query` and in `ufs_service.py` `fetch_cells` inside `try/except`; SQLite test in `test_ufs_service.py` verifies non-fatal behavior |
| 15 | All Phase 1 source files parse as valid Python | ✓ VERIFIED | AST parse check passes for all 10 key files: `streamlit_app.py`, `mysql.py`, `result_normalizer.py`, `ufs_service.py`, `settings.py`, `browse.py`, `export_dialog.py`, `__init__.py` files |
| 16 | 75 unit tests pass (65 normalizer + 10 ufs_service) | ✓ VERIFIED | `pytest tests/services/ -x` returns "75 passed" |

**Score:** 16/16 truths verified

---

### Deferred Items

Items explicitly addressed in future phases.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | FOUND-01: Login page via `streamlit-authenticator` | Pre-deployment phase (post Phase 1) | D-04 decision; ROADMAP SC#1 revised; no Phase 2 roadmap SC covers this directly — user-acknowledged deferral |
| 2 | FOUND-03: Cookie-key startup guard | Pre-deployment phase (post Phase 1) | D-04 decision; CONTEXT.md deferred section |

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.gitignore` | Excludes auth.yaml, settings.yaml, .env | ✓ VERIFIED | All 3 exact-line matches; `git check-ignore` confirms |
| `.streamlit/config.toml` | UI-SPEC theme tokens | ✓ VERIFIED | `primaryColor="#1f77b4"`, `base="light"`, `secondaryBackgroundColor="#f0f2f6"` all present |
| `requirements.txt` | Correct version pins | ✓ VERIFIED | `sqlalchemy>=2.0,<2.1`, `pydantic-ai>=1.0,<2.0`, `pandas>=3.0`, `pymysql>=1.1` all present |
| `app/adapters/db/mysql.py` | pool_recycle=3600, pd.read_sql_query, SET SESSION | ✓ VERIFIED | All three confirmed; no deprecated `pd.read_sql` |
| `streamlit_app.py` | Navigation + sidebar + load_dotenv | ✓ VERIFIED | 191 lines; `st.navigation`, 2 `st.Page` entries, `default=True`, `@st.cache_resource`, `load_dotenv`, sidebar with `key="active_db"` and `key="active_llm"` |
| `app/pages/browse.py` | Full Browse page with all 3 tabs | ✓ VERIFIED | 552 lines; 10 helper functions; Pivot/Detail/Chart fully implemented (no Plan 06 stubs remain) |
| `app/pages/settings.py` | Full Settings page with CRUD | ✓ VERIFIED | 251 lines; DB CRUD, LLM CRUD, Test, Save, Delete dialog, AgentConfig readonly |
| `app/services/result_normalizer.py` | 10 public exports, 5-stage pipeline | ✓ VERIFIED | All 10 symbols present; 65 tests pass |
| `app/services/ufs_service.py` | 4 public functions with caching | ✓ VERIFIED | All 4 functions; correct TTLs; expanding bindparams; row cap; normalize call |
| `app/components/export_dialog.py` | Excel+CSV export dialog | ✓ VERIFIED | 202 lines; 5 functions; `@st.dialog`; xlsx round-trip and CSV BOM verified |
| `app/components/__init__.py` | Package namespace | ✓ VERIFIED | Exists |
| `tests/services/test_result_normalizer.py` | >= 25 tests | ✓ VERIFIED | 58 test functions (65 collected with parametrize); all pass |
| `tests/services/test_ufs_service.py` | >= 8 tests | ✓ VERIFIED | 10 test functions; all pass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `streamlit_app.py` | `app.core.config.load_settings` | import at module top | ✓ WIRED | `from app.core.config import ... load_settings` present |
| `streamlit_app.py` | `st.session_state['active_db']`, `['active_llm']` | sidebar selectbox widgets | ✓ WIRED | `key="active_db"` and `key="active_llm"` present |
| `app/adapters/db/mysql.py` | `sqlalchemy.create_engine` with `pool_pre_ping=True` | `_get_engine` method | ✓ WIRED | Both pool kwargs confirmed |
| `app/pages/browse.py` | `ufs_service.list_platforms` | sidebar multiselect options | ✓ WIRED | `list_platforms(adapter, db_name=db_name)` called |
| `app/pages/browse.py` | `ufs_service.list_parameters` | sidebar param multiselect | ✓ WIRED | `list_parameters(adapter, db_name=db_name)` called |
| `app/pages/browse.py` | `ufs_service.fetch_cells` | Pivot/Detail/Chart tabs | ✓ WIRED | 8 occurrences; called in all 3 tab renderers |
| `app/pages/browse.py` | `ufs_service.pivot_to_wide` | Pivot and Chart tabs | ✓ WIRED | 4 occurrences |
| `app/pages/browse.py` | `st.query_params` | URL round-trip | ✓ WIRED | 13 occurrences in read/write; `_load_state_from_url` + `_sync_state_to_url` |
| `app/pages/settings.py` | `app.core.config.save_settings` | Save Connection click | ✓ WIRED | `save_settings(draft)` inside `_persist_and_clear_caches` |
| `app/pages/settings.py` | `st.cache_resource.clear`, `st.cache_data.clear` | after save_settings (D-12) | ✓ WIRED | Both calls present in `_persist_and_clear_caches` |
| `app/pages/settings.py` | `app.adapters.db.registry.build_adapter` | Test button | ✓ WIRED | `build_db_adapter(cfg)` called in `_test_db_connection` |
| `app/services/ufs_service.py` | `result_normalizer.normalize` | after fetch_cells SELECT | ✓ WIRED | `from app.services.result_normalizer import normalize`; `df["Result"] = normalize(df["Result"])` |
| `app/services/ufs_service.py` | `streamlit.cache_data` | `@st.cache_data` decorators | ✓ WIRED | ttl=300 on catalog, ttl=60 on fetch_cells |
| `app/components/export_dialog.py` | `pandas.ExcelWriter` with openpyxl | `_write_excel_bytes` | ✓ WIRED | `pd.ExcelWriter(buf, engine="openpyxl")` present |
| `app/components/export_dialog.py` | `pandas.DataFrame.to_csv` with utf-8-sig | `_write_csv_bytes` | ✓ WIRED | `df.to_csv(index=False).encode("utf-8-sig")` — single BOM confirmed |
| `app/pages/browse.py` | `export_dialog.render_export_dialog` | Export button in Pivot tab | ✓ WIRED | Import present; `render_export_dialog(prior_wide, prior_long)` called on button click |
| `app/pages/browse.py` | `result_normalizer.try_numeric` | Chart tab per-column numeric detection | ✓ WIRED | `from app.services.result_normalizer import try_numeric`; called in `_render_chart_tab` per-column only (VIZ-02 compliant) |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `app/pages/browse.py` pivot grid | `df_wide` from `pivot_to_wide` | `fetch_cells` → MySQL `ufs_data` via `sa.bindparam(expanding=True)` | Yes — parameterized query; `normalize()` applied to Result; no static empty returns | ✓ FLOWING |
| `app/pages/browse.py` detail grid | `df_long` from `fetch_cells` | Same path as pivot; single-platform filter | Yes — same real fetch path | ✓ FLOWING |
| `app/pages/browse.py` chart | `chart_df` built from `numeric_series_cache` | `try_numeric` applied to `df_wide` columns; `dropna` removes pd.NA rows | Yes — real data flows through try_numeric per-column | ✓ FLOWING |
| `app/pages/settings.py` | `draft` (Settings object) | `load_settings()` reads `config/settings.yaml` on first render | Yes — reads YAML file; empty Settings if file absent | ✓ FLOWING |
| `app/components/export_dialog.py` | `scope_df` passed to writer | `st.session_state["pivot.df_wide"]` / `["pivot.df_long"]` stashed by `_render_pivot_tab` after `pivot_to_wide` | Yes — stash captures actual post-pivot DataFrame (D-15 fidelity) | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| result_normalizer smoke test | `.venv/bin/python -c "from app.services.result_normalizer import ..."` | `is_missing('None')=True`, `classify('0x1F')=HEX`, `split_lun_item('3_WriteProt')=(3,'WriteProt')`, `try_numeric(['0x1F']).iloc[0]=31` | ✓ PASS |
| 75 unit tests pass | `.venv/bin/pytest tests/services/ -x -q` | "75 passed in 5.44s" | ✓ PASS |
| Export xlsx round-trip | `_write_excel_bytes(df)` → `pd.read_excel` | PK header confirmed; 2 rows; correct columns; sheet "UFS" | ✓ PASS |
| Export CSV BOM | `_write_csv_bytes(df)` | First 3 bytes = `0xEF 0xBB 0xBF`; no double-BOM | ✓ PASS |
| Filename sanitization | `_sanitize_filename('../../../etc/passwd')` | No `..`, no `/`; safe basename returned | ✓ PASS |
| All key files parse as valid Python | `ast.parse` on 10 files | All pass | ✓ PASS |
| SQL injection audit | `grep -rE 'f"SELECT.*{(platforms|items...)}' app/services/` | Zero matches | ✓ PASS |
| Pivot tab browse.py wired correctly | Multi-grep on key strings | All acceptance criteria patterns confirmed | ✓ PASS |
| Live Streamlit rendering (pivot grid, tabs, export dialog) | Browser interaction required | Not testable via grep/AST | ? SKIP — route to human verification |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FOUND-01 | 01-01 | Login page via streamlit-authenticator | deferred (accepted) | D-04; ROADMAP SC#1 revised; no auth in Phase 1 by explicit decision |
| FOUND-02 | 01-01 | config/auth.yaml gitignored | ✓ SATISFIED | `.gitignore` has exact line; `git check-ignore` confirms |
| FOUND-03 | 01-01 | Cookie-key startup guard | deferred (accepted) | D-04 explicit deferral; no code produced |
| FOUND-04 | 01-01 | Load config from settings.yaml / .env via python-dotenv | ✓ SATISFIED | `load_dotenv()` at top of `streamlit_app.py`; `load_settings()` reads YAML |
| FOUND-05 | 01-01 | st.navigation + st.Page routing | ✓ SATISFIED | `st.navigation([ st.Page(...), st.Page(...) ])` with `default=True` in `streamlit_app.py` |
| FOUND-06 | 01-01 | SQLAlchemy engine with pool_pre_ping + pool_recycle=3600 | ✓ SATISFIED | Both confirmed in `mysql.py` |
| FOUND-07 | 01-03 | @st.cache_data(ttl=300) on query functions | ✓ SATISFIED | Both catalog functions decorated; `_db` underscore prefix |
| FOUND-08 | 01-01 | requirements.txt pins sqlalchemy<2.1, adds pydantic-ai | ✓ SATISFIED | Both pins verified |
| DATA-01 | 01-02 | Missing sentinel mapping to pd.NA | ✓ SATISFIED | 65 tests; all sentinel cases pass |
| DATA-02 | 01-02 | classify without coercion | ✓ SATISFIED | classify returns enum only; smoke test confirms |
| DATA-03 | 01-02 | split_lun_item for N∈{0..7} | ✓ SATISFIED | Regex `^([0-7])_(.+)$`; test for `8_x` → (None, ...) passes |
| DATA-04 | 01-02 | split_dme_suffix + unpack_dme_compound | ✓ SATISFIED | Both functions present and tested |
| DATA-05 | 01-03 | Server-side WHERE IN filters; full table never loaded | ✓ SATISFIED | `expanding=True` bindparams; empty-input short-circuit |
| DATA-06 | 01-03 | pivot_to_wide with aggfunc="first" + duplicate warning | ✓ SATISFIED | `aggfunc="first"` confirmed; `logger.warning` on duplicate count |
| DATA-07 | 01-03 | 200-row cap with visible message | ✓ SATISFIED | `row_cap+1` LIMIT trick; `capped=True` returned; UI-SPEC warning copy present in browse.py |
| BROWSE-01 | 01-05 | Platform multiselect with typeahead | ✓ SATISFIED | `st.sidebar.multiselect("Platforms", ..., key="selected_platforms", placeholder=...)` |
| BROWSE-02 | 01-05 | InfoCategory/Item hierarchy in sidebar | ✓ SATISFIED | Labels formatted as "InfoCategory / Item"; sorted (InfoCategory ASC, Item ASC) |
| BROWSE-03 | 01-05 | Substring search across InfoCategory and Item | ✓ SATISFIED | Single multiselect label format enables Streamlit's built-in typeahead |
| BROWSE-04 | 01-05 | 30-column cap with visible warning | ✓ SATISFIED | `col_cap=30` in `pivot_to_wide`; exact UI-SPEC warning copy present |
| BROWSE-05 | 01-06 | Single-platform detail view sorted by InfoCategory/Item | ✓ SATISFIED | `_render_detail_tab` checks `len(platforms) != 1`; `sort_values(["InfoCategory", "Item"], kind="stable")` |
| BROWSE-06 | 01-05 | Row-count indicator on every result view | ✓ SATISFIED | `st.caption(count_copy)` with `"N platforms × K parameters"` format; detail tab has `"K parameters across N categories"` |
| BROWSE-07 | 01-05 | Loading, empty, and error states | ✓ SATISFIED | All 5 exact UI-SPEC copy strings present: empty-state, "Fetching data...", error, row-cap warning, col-cap warning |
| BROWSE-08 | 01-05 | Filter selections persist via session_state | ✓ SATISFIED | `key="selected_platforms"`, `key="selected_params"`, `key="pivot_swap_axes"` all wired |
| BROWSE-09 | 01-05/06 | Shareable URL via st.query_params | ✓ SATISFIED | `_load_state_from_url` + `_sync_state_to_url`; `platforms`, `params`, `swap`, `tab` all synced; Copy link button in sidebar |
| VIZ-01 | 01-06 | Bar/line/scatter Plotly chart from numeric columns | ✓ SATISFIED | `px.bar`, `px.line`, `px.scatter` with `color_discrete_sequence=[_ACCENT_COLOR]` |
| VIZ-02 | 01-06 | Lazy per-query numeric coercion, skip non-coercible | ✓ SATISFIED | `try_numeric` per-column only; `numeric_series_cache`; `dropna(subset=[y_col])`; grep confirms no global coercion |
| EXPORT-01 | 01-07 | Excel download via openpyxl | ✓ SATISFIED | `pd.ExcelWriter(buf, engine="openpyxl")`; sheet "UFS"; auto-sized columns; xlsx round-trip passes |
| EXPORT-02 | 01-07 | CSV download | ✓ SATISFIED | `to_csv(index=False).encode("utf-8-sig")`; single BOM; CSV round-trip passes |
| SETUP-01 | 01-04 | DB connection CRUD from Settings | ✓ SATISFIED | `_render_db_entry`, `+ Add Database`, delete dialog all present |
| SETUP-02 | 01-04 | LLM connection CRUD from Settings | ✓ SATISFIED | `_render_llm_entry`, `+ Add LLM` all present |
| SETUP-03 | 01-04 | Test connection with pass/fail indicator | ✓ SATISFIED | Test button calls `_test_db_connection` / `_test_llm_connection`; `st.success("Connected")` / `st.error("Connection failed. See error detail below.")` |
| SAFE-01 | 01-01/03 | Read-only MySQL user; SET SESSION TRANSACTION READ ONLY | ✓ SATISFIED | Present in both `mysql.py` and `ufs_service.py fetch_cells`; try/except makes it non-fatal |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/pages/browse.py` | 168, 191 | `placeholder=` strings | ℹ️ Info | These are Streamlit widget placeholders (hint text in empty multiselects), not code stubs. Not a concern. |

No blockers or substantive anti-patterns found. The false positives from `grep -i placeholder` are legitimate Streamlit `st.multiselect(placeholder=...)` widget parameters, not code stubs.

---

### Human Verification Required

#### 1. Pivot Grid Live Rendering

**Test:** Open `streamlit run streamlit_app.py`, navigate to Browse, select platforms and parameters, and verify the pivot grid renders.
**Expected:** Wide-form `st.dataframe` with TextColumns, correct row-count caption "N platforms × K parameters", functional Swap axes toggle.
**Why human:** `st.dataframe` rendering, widget interaction, and visual layout cannot be verified via grep or AST analysis.

#### 2. Export Dialog End-to-End

**Test:** With a pivot result visible, click "Export", choose Excel, enter a filename, click Download. Open the file in Excel.
**Expected:** File downloads with sheet "UFS", auto-sized columns, no encoding corruption; CSV has correct BOM so Excel opens without mojibake.
**Why human:** Browser download flow and Excel rendering require a live session. (Bytes verified programmatically; dialog UX and download trigger require human.)

#### 3. URL Round-Trip Shareable Link

**Test:** Apply filters, click "Copy link" in the sidebar, open the copied URL in a new browser tab.
**Expected:** Same platforms, parameters, and tab pre-selected in the new tab.
**Why human:** `navigator.clipboard.writeText` runs in browser; URL parse/restore requires two live browser sessions.

#### 4. Settings Page CRUD and Save

**Test:** Add a DB entry, test it (with real or test credentials), click Save Connection.
**Expected:** "Saved. Caches refreshed." toast appears; `config/settings.yaml` is updated; browse page adapts.
**Why human:** Streamlit toast, dialog interactions, and filesystem write confirmation require a live session.

#### 5. Detail Tab Sort Order

**Test:** Select exactly one platform, navigate to Detail tab.
**Expected:** Long-form rows sorted InfoCategory ASC then Item ASC; "K parameters across N categories" caption correct.
**Why human:** Sort correctness against real DB data requires visual inspection.

#### 6. Chart Tab Rendering and Accent Color

**Test:** Select numeric parameters, navigate to Chart tab, pick Y-axis and chart type.
**Expected:** Chart renders with accent color `#1f77b4`; only numeric-coercible columns appear in Y-axis selector.
**Why human:** Plotly rendering and color accuracy require visual browser inspection.

---

### Gaps Summary

No gaps identified. All 16 observable truths are verified. All 32 Phase 1 requirements are either satisfied (30) or correctly deferred per explicit D-04 decision (FOUND-01, FOUND-03).

The 6 human verification items above are required because of the Streamlit UI nature of this phase — widget interactions, browser clipboard, dialog flows, and visual rendering cannot be verified programmatically. All automated checks (syntax, unit tests, behavioral spot-checks, data-flow traces, key link wiring) pass.

---

_Verified: 2026-04-23T20:00:00Z_
_Verifier: Claude (gsd-verifier)_
