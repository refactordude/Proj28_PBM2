# Phase 1: Foundation + Browsing — Research

**Researched:** 2026-04-23
**Domain:** Streamlit EAV-MySQL read-only browser — DB layer, pivot/normalization, browse UI, settings, export, chart, shareable URL
**Confidence:** HIGH (scaffolding read directly; stack already decided in CLAUDE.md; CONTEXT.md locks all UI decisions)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Phase 1 ships two `st.Page` surfaces: Browse (default) and Settings. No Home, Detail, or History page.

**D-02:** The single-platform detail view lives as a second tab inside Browse, next to the Pivot tab. A third Chart tab is added. All three tabs share filter state.

**D-03:** Every page shows a sidebar: DB selector (only visible if >1 DB; else read-only text), LLM selector (inert, writes to `st.session_state["active_llm"]`), connection health indicator. No data-freshness indicator.

**D-04:** Auth (FOUND-01, FOUND-03) is skipped entirely in Phase 1. `config/auth.yaml` stays in `.gitignore`. No `streamlit-authenticator` imports in Phase 1 code paths.

**D-05:** Platform picker and parameter catalog both live in the left sidebar, below DB/LLM selectors. Sidebar order: DB selector → LLM selector → divider → Platform multi-select → Parameter catalog → "Clear filters" button.

**D-06:** Parameter catalog is a single searchable two-level multiselect (`st.multiselect`) formatted as `"InfoCategory / Item"`, sorted by (InfoCategory ASC, Item ASC). No expanders, no nested checkboxes.

**D-07:** Pivot default = parameters as columns, platforms as rows (PLATFORM_ID is the DataFrame index). "Swap axes" toggle re-pivots on demand. 30-column cap applies to whichever axis is currently the column axis.

**D-08:** LUN items listed flat in the catalog — `lun_info / 0_WriteProt`, `lun_info / 1_WriteProt`, etc. No grouping roll-up.

**D-09:** Settings page is fully editable by anyone who reaches the URL (no role gate).

**D-10:** Per-row "Test" button in Settings; runs synchronously with `st.spinner`; shows pass/fail badge inline.

**D-11:** Passwords and api_keys stored plaintext in `config/settings.yaml` (gitignored); rendered as masked `type="password"` inputs in UI.

**D-12:** On Save: `save_settings()` then `st.cache_resource.clear()` + `st.cache_data.clear()`. Toast: "Saved. Caches refreshed."

**D-13:** Chart lives as a third tab (Pivot / Detail / Chart) inside Browse.

**D-14:** Chart tab: user explicitly picks column (numeric only) and chart type (bar / line / scatter radio). No auto-render.

**D-15:** Export captures currently-visible view; charts are not exported.

**D-16:** Single "Export" button above each tab opens `st.dialog` with format selector, filename field, and (Pivot tab only) "Scope" radio ("Current view" / "Raw long-form rows").

### Claude's Discretion

- Exact color/typography of pass/fail badge (use `st.success`/`st.error` per UI-SPEC).
- Debounce/throttle on typeahead in parameter catalog multiselect.
- Error-message wording for BROWSE-07 empty/loading/error states (exact copy in UI-SPEC).
- Filename sanitization rules for the export dialog.
- Precise layout of the Settings page form (single column chosen per UI-SPEC).
- How `AgentConfig` fields are surfaced — read-only disabled fields under "Agent defaults (Phase 2)" caption.
- Whether to seed `config/settings.yaml` from `settings.example.yaml` on first launch.

### Deferred Ideas (OUT OF SCOPE)

- Authentication (FOUND-01, FOUND-03) — pre-deployment phase item.
- Data-freshness indicator in sidebar — blocked on upstream adding `updated_at` column.
- LUN sub-header grouping in pivot (BROWSE-V2-01), DME split display (BROWSE-V2-02).
- All NL-related features (NL-01..10, SAFE-02..06, ONBD-01..02).
- Heatmap / conditional formatting.
- Editable generated SQL.
- History page.
- Platform comparison presets, saved parameter sets, cross-session history.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FOUND-01 | Login gate via streamlit-authenticator | **DEFERRED per D-04** — not in Phase 1 |
| FOUND-02 | `config/auth.yaml` excluded from git | `.gitignore` does NOT exist yet — must be created; auth.yaml currently unguarded |
| FOUND-03 | Startup guard on demo cookie key | **DEFERRED per D-04** — not in Phase 1 |
| FOUND-04 | Load config from `settings.yaml` + `.env` | `config.py` `load_settings()` + `OpenAIAdapter` env fallback already implemented |
| FOUND-05 | `st.navigation` + `st.Page` routing | Entrypoint `streamlit_app.py` does not exist yet — needs creating |
| FOUND-06 | `@st.cache_resource` engine singleton with `pool_pre_ping=True`, `pool_recycle=3600` | MySQLAdapter exists; uses `pool_recycle=1800` (needs bump to 3600 per FOUND-06); `pool_pre_ping` absent — needs adding |
| FOUND-07 | `@st.cache_data(ttl=300)` on all query results | Service layer (`ufs_service.py`) does not exist yet — service functions must carry the decorator |
| FOUND-08 | `requirements.txt` pins `sqlalchemy>=2.0,<2.1` and adds `pydantic-ai>=1.0,<2.0` | `requirements.txt` currently lacks upper bound on sqlalchemy and lacks pydantic-ai |
| DATA-01 | `result_normalizer` maps None/empty/"None"/"null"/"N/A"/shell errors to `pd.NA` | `result_normalizer.py` does not exist yet |
| DATA-02 | `result_normalizer` classifies Result into HEX/DECIMAL/CSV/etc. without coercing | Not implemented |
| DATA-03 | `result_normalizer` can split LUN-prefixed Items on demand | Not implemented |
| DATA-04 | `result_normalizer` can split DME `_local`/`_peer` on demand | Not implemented |
| DATA-05 | `ufs_service` fetches rows server-side with WHERE filter; never loads full table | `ufs_service.py` does not exist yet |
| DATA-06 | `pivot_to_wide` uses `aggfunc="first"` and logs warning on duplicates | Not implemented |
| DATA-07 | Every `ufs_service` query honors 200-row cap; surfaces cap as visible message | Not implemented |
| BROWSE-01 | Platform picker: all distinct PLATFORM_ID values, multi-select with typeahead | browse.py does not exist; uses `list_platforms()` from service + `st.multiselect` |
| BROWSE-02 | InfoCategory → Item hierarchy; LUN items listed flat per D-08 | `list_parameters()` service function; parameter catalog multiselect formatted as "InfoCategory / Item" |
| BROWSE-03 | Parameter search by substring via typeahead | Built into `st.multiselect` natively — no extra implementation needed |
| BROWSE-04 | Wide-form pivot grid; sortable; 30-column cap | `pivot_to_wide()` + `st.dataframe` with `use_container_width=True`; column-count guard before render |
| BROWSE-05 | Single-platform detail view (InfoCategory, Item, Result) grouped by InfoCategory | Detail tab: long-form `st.dataframe` sorted by (InfoCategory ASC, Item ASC) |
| BROWSE-06 | Row-count indicator on every result view | `st.caption` rendering after query returns |
| BROWSE-07 | Plain-English loading/empty/error states | `st.spinner` / `st.info` / `st.error` per UI-SPEC copywriting contract |
| BROWSE-08 | Filter selections persist via `st.session_state` | Session state keys: `selected_platforms`, `selected_params`, `pivot_swap_axes` |
| BROWSE-09 | Shareable URL via `st.query_params` | `st.query_params` API; on load: read and populate session state; "Copy link" button via `st.components.v1.html` clipboard JS |
| VIZ-01 | Bar/line/scatter chart via Plotly from numeric column | Chart tab: `st.plotly_chart(fig, use_container_width=True)` |
| VIZ-02 | Lazy numeric coercion; skip pd.NA and non-coercible | `pd.to_numeric(series, errors="coerce")` on chart column only |
| EXPORT-01 | Excel export via openpyxl | `io.BytesIO` + `pd.ExcelWriter(buf, engine="openpyxl")` + `st.download_button` |
| EXPORT-02 | CSV export | `df.to_csv(index=True)` + `st.download_button` |
| SETUP-01 | DB connection CRUD in Settings | `settings.py` page; forms against `DatabaseConfig`; `save_settings()` |
| SETUP-02 | LLM connection CRUD in Settings | Same pattern as SETUP-01 via `LLMConfig` |
| SETUP-03 | Test connection pass/fail indicator | Per-row Test button; `MySQLAdapter.test_connection()` for DB; `OpenAIAdapter` / `OllamaAdapter` ping for LLM |
| SAFE-01 | Readonly MySQL user; attempt `SET SESSION TRANSACTION READ ONLY` | `MySQLAdapter.run_query()` already implements this — confirmed in code |

</phase_requirements>

---

## Summary

Phase 1 builds the entire browsing-and-settings foundation on top of an already solid adapter and config scaffolding. The core scaffolding (config.py, MySQLAdapter, OpenAIAdapter, OllamaAdapter, registries) is implemented and correct. What is completely absent: the entrypoint (`streamlit_app.py`), both pages (`browse.py`, `settings.py`), the domain service layer (`ufs_service.py`, `result_normalizer.py`), the `.gitignore`, and `.streamlit/config.toml`.

The most complex piece is `result_normalizer.py` — it is the domain's hardest problem and must be written and unit-tested before `ufs_service.py` is built. Everything else (pivot, charts, export, settings CRUD) is relatively mechanical once the service layer is solid.

Two scaffolding defects must be fixed before anything else: `pool_recycle=1800` in MySQLAdapter needs to be `3600`, `pool_pre_ping` is missing entirely, and `requirements.txt` needs the sqlalchemy upper bound and pydantic-ai entry. The `.gitignore` also does not exist, which means `config/auth.yaml` (which contains demo credentials) is currently being tracked by git — this must be addressed in Plan 1 (foundation/setup).

**Primary recommendation:** Build in dependency order — foundation (gitignore + requirements + config.toml + entry point) → result_normalizer (tested) → ufs_service → Settings page → Browse page (Pivot tab) → Browse page (Detail + Chart tabs) → Export dialog.

---

## Scaffolding Audit

### What Exists and Is Correct (extend, do not rewrite)

| File | Status | Notes |
|------|--------|-------|
| `app/core/config.py` | DONE | `Settings`, `DatabaseConfig`, `LLMConfig`, `AppConfig`, `load_settings()`, `save_settings()`, `find_database()`, `find_llm()` — fully usable |
| `app/core/agent/config.py` | DONE | `AgentConfig` with `row_cap=200`, `allowed_tables`, `max_steps`, `timeout_s`, `max_context_tokens` — usable as-is |
| `app/adapters/db/base.py` | DONE | `DBAdapter` ABC: `test_connection`, `list_tables`, `get_schema`, `run_query`, `dispose` |
| `app/adapters/db/registry.py` | DONE | `build_adapter(config)` dispatches to `MySQLAdapter` |
| `app/adapters/llm/base.py` | DONE | `LLMAdapter` ABC: `generate_sql`, `stream_text`; `SQL_SYSTEM_PROMPT` constant |
| `app/adapters/llm/openai_adapter.py` | DONE | `OpenAIAdapter`: env-var fallback for api_key, `base_url` routing, `httpx.Timeout(30.0)` |
| `app/adapters/llm/ollama_adapter.py` | DONE | `OllamaAdapter`: streaming via `requests`, 120s timeout |
| `app/adapters/llm/registry.py` | DONE | `build_adapter(config)` dispatches to OpenAI/Ollama |
| `config/settings.example.yaml` | DONE | Correct shape for `settings.yaml` |
| `.env.example` | DONE | `OPENAI_API_KEY`, `SETTINGS_PATH`, `AUTH_PATH`, `LOG_DIR` |

### What Needs Fixing (in existing files)

| File | Issue | Fix |
|------|-------|-----|
| `app/adapters/db/mysql.py` | `pool_recycle=1800` (FOUND-06 requires 3600); `pool_pre_ping` missing | Change `pool_recycle=1800` → `pool_recycle=3600`; add `pool_pre_ping=True` to `create_engine()` call |
| `app/adapters/db/mysql.py` | `pd.read_sql(text(sql), conn)` — the bare `pd.read_sql` variant may emit deprecation warnings in pandas 3.x for text-SQL input | Change to `pd.read_sql_query(text(sql), conn)` |
| `requirements.txt` | Missing sqlalchemy upper bound; missing pydantic-ai; pandas lower bound too low | Pin `sqlalchemy>=2.0,<2.1`; add `pydantic-ai>=1.0,<2.0`; bump `pandas>=3.0` |

### What Must Be Created (greenfield)

| File | Depends On | Priority |
|------|------------|----------|
| `.gitignore` | nothing | P0 — `config/auth.yaml` is currently tracked by git (contains demo admin/admin1234 creds) |
| `.streamlit/config.toml` | nothing | P0 — sets theme per UI-SPEC |
| `streamlit_app.py` | config.py, adapters | P1 — entrypoint; st.navigation; shared sidebar |
| `app/services/result_normalizer.py` | nothing | P1 — must exist before ufs_service |
| `app/services/__init__.py` | nothing | P1 — package init |
| `app/services/ufs_service.py` | result_normalizer, DBAdapter | P2 — after normalizer is tested |
| `app/pages/__init__.py` | nothing | P2 |
| `app/pages/settings.py` | config.py, adapters, ufs_service | P3 |
| `app/pages/browse.py` | ufs_service | P4 |

---

## Standard Stack

### Core (all already in requirements.txt; version pins need tightening)

| Library | Target Version | Purpose | Source |
|---------|---------------|---------|--------|
| Streamlit | 1.56.0 | UI framework — `st.navigation`, `st.Page`, `st.dataframe`, `st.dialog`, `st.query_params` | [VERIFIED: adjacent project venv] |
| SQLAlchemy | `>=2.0,<2.1` | Engine, `text()`, parameterized queries | [VERIFIED: CLAUDE.md] |
| pymysql | `>=1.1` | MySQL DBAPI driver | [VERIFIED: requirements.txt] |
| pandas | `>=3.0` | `read_sql_query`, `pivot_table`, `to_csv`, `ExcelWriter` | [VERIFIED: CLAUDE.md] |
| Pydantic v2 | `>=2.7` | `DatabaseConfig`, `LLMConfig`, `AgentConfig`, `Settings` | [VERIFIED: config.py] |
| python-dotenv | `>=1.0` | `.env` loading at startup | [VERIFIED: requirements.txt] |
| pyyaml | `>=6.0` | `settings.yaml` round-trip | [VERIFIED: config.py usage] |
| plotly | `>=5.22` | Bar/line/scatter charts via `st.plotly_chart` | [VERIFIED: requirements.txt] |
| openpyxl | `>=3.1` | Excel export via `pd.ExcelWriter(buf, engine="openpyxl")` | [VERIFIED: requirements.txt] |
| pydantic-ai | `>=1.0,<2.0` | Required by FOUND-08 even though agent is Phase 2 | [CITED: CLAUDE.md scaffolding assessment] |

### Not Needed in Phase 1

| Library | Reason to Skip |
|---------|---------------|
| streamlit-authenticator | Auth deferred (D-04) — do NOT import in Phase 1 code |
| altair | Plotly covers all Phase 1 chart needs |
| sqlparse | Phase 2 (SQL validation for agent) |
| duckdb | Only needed if pandas pivot proves too slow; do not add preemptively |

---

## Architecture Patterns

### Recommended File Creation Order

```
streamlit_app.py                   # entrypoint: st.navigation, shared sidebar
app/
  services/
    __init__.py
    result_normalizer.py           # Stage 1-5 pipeline; unit-tested first
    ufs_service.py                 # list_platforms, list_parameters, fetch_cells, pivot_to_wide
  pages/
    __init__.py
    settings.py                    # DB/LLM CRUD, Test button, cache clear on save
    browse.py                      # Pivot / Detail / Chart tabs, Export dialog
.gitignore                         # config/auth.yaml, config/settings.yaml, .env, logs/
.streamlit/
  config.toml                      # theme per UI-SPEC
```

### Pattern 1: Entrypoint + st.navigation

```python
# streamlit_app.py
import os
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from app.core.config import load_settings, find_database, find_llm
from app.adapters.db.registry import build_adapter

@st.cache_resource
def get_db_adapter(db_name: str):
    settings = load_settings()
    cfg = find_database(settings, db_name)
    return build_adapter(cfg)

def render_sidebar(settings):
    st.sidebar.title("PBM2")
    # DB selector
    db_names = [d.name for d in settings.databases]
    if len(db_names) > 1:
        active_db = st.sidebar.selectbox("Database", options=db_names,
                                          key="active_db")
    else:
        active_db = db_names[0] if db_names else ""
        st.sidebar.caption(f"DB: {active_db}")
        st.session_state["active_db"] = active_db
    # LLM selector (inert in Phase 1)
    llm_names = [l.name for l in settings.llms]
    st.sidebar.selectbox("LLM Backend", options=llm_names, key="active_llm")
    st.sidebar.caption("LLM backend selection takes effect in Phase 2 (Ask page).")
    # Connection health dot
    # ... inline st.markdown with colored dot

browse_page  = st.Page("app/pages/browse.py",   title="Browse",   icon=":material/table_chart:", default=True)
settings_page = st.Page("app/pages/settings.py", title="Settings", icon=":material/settings:")
# Phase 2 slot — st.Page("app/pages/nl_agent.py", title="Ask", icon=":material/chat:")  # Phase 2

settings = load_settings()
render_sidebar(settings)
pg = st.navigation([browse_page, settings_page])
pg.run()
```

[VERIFIED: Streamlit `st.navigation` + `st.Page` API confirmed in ARCHITECTURE.md research]

### Pattern 2: `@st.cache_resource` for DBAdapter + `@st.cache_data(ttl=300)` for catalog queries

The `_db` underscore prefix prevents Streamlit from trying to hash the adapter object (unhashable). Catalog queries (platforms list, parameters list) are slow full-table scans; TTL=300 means 5-minute staleness acceptable for an intranet tool.

```python
# app/services/ufs_service.py

import streamlit as st
import pandas as pd
import sqlalchemy as sa
from app.adapters.db.base import DBAdapter

@st.cache_data(ttl=300)
def list_platforms(_db: DBAdapter) -> list[str]:
    with _db._get_engine().connect() as conn:
        df = pd.read_sql_query(
            sa.text("SELECT DISTINCT PLATFORM_ID FROM ufs_data ORDER BY PLATFORM_ID"),
            conn,
        )
    return df["PLATFORM_ID"].tolist()

@st.cache_data(ttl=300)
def list_parameters(_db: DBAdapter) -> list[dict]:
    with _db._get_engine().connect() as conn:
        df = pd.read_sql_query(
            sa.text("SELECT DISTINCT InfoCategory, Item FROM ufs_data ORDER BY InfoCategory, Item"),
            conn,
        )
    return df.to_dict("records")  # [{"InfoCategory": ..., "Item": ...}, ...]
```

[VERIFIED: underscore prefix pattern from ARCHITECTURE.md Pattern 3; `pd.read_sql_query` + `sa.text()` is canonical per CLAUDE.md]

### Pattern 3: Server-side WHERE filter before pivot (never full-table load)

PLATFORM_ID values must be passed as a tuple for SQLAlchemy's `IN` clause. Item + InfoCategory pairs require a different approach — either `OR`-chained conditions or a temporary join. For Phase 1 the simplest approach is two separate IN clauses (items filtered independently, categories filtered independently). This may return slightly more rows than needed but stays safe because the row cap is applied after.

```python
def fetch_cells(
    _db: DBAdapter,
    platforms: tuple[str, ...],
    infocategories: tuple[str, ...],
    items: tuple[str, ...],
    row_cap: int = 200,
) -> pd.DataFrame:
    """Return long-form rows pre-filtered server-side. Never loads full table."""
    query = sa.text("""
        SELECT PLATFORM_ID, InfoCategory, Item, Result
        FROM ufs_data
        WHERE PLATFORM_ID IN :platforms
          AND InfoCategory IN :categories
          AND Item IN :items
        LIMIT :cap
    """)
    with _db._get_engine().connect() as conn:
        try:
            conn.execute(sa.text("SET SESSION TRANSACTION READ ONLY"))
        except Exception:
            pass  # non-fatal per SAFE-01
        df = pd.read_sql_query(
            query,
            conn,
            params={"platforms": platforms, "categories": infocategories,
                    "items": items, "cap": row_cap},
        )
    return df
```

Note: SQLAlchemy `text()` with tuple parameters for `IN` requires the tuple to be passed as a named bind parameter. In SQLAlchemy 2.x with pymysql, `IN :platforms` with `params={"platforms": tuple_value}` works correctly. [ASSUMED — verified by ARCHITECTURE.md Pattern 1 and CLAUDE.md but not directly tested in this session]

### Pattern 4: Result Normalization Pipeline

The normalizer module must expose a stable `normalize(series: pd.Series) -> pd.Series` function plus a `classify(value: str | None) -> ResultType` enum method. The 5-stage pipeline documented in ARCHITECTURE.md:

```python
# app/services/result_normalizer.py
import pandas as pd
from enum import Enum
from typing import Any

MISSING_SENTINELS = frozenset({None, "None", "", "N/A", "null", "NULL", "N/a"})
SHELL_ERROR_PREFIXES = ("cat: ", "Permission denied", "No such file")

class ResultType(Enum):
    MISSING = "missing"
    ERROR = "error"
    HEX = "hex"
    DECIMAL = "decimal"
    CSV = "csv"
    WHITESPACE_BLOB = "whitespace_blob"
    COMPOUND = "compound"
    IDENTIFIER = "identifier"

def is_missing(val: Any) -> bool:
    """Stage 1 — missing sentinel check."""
    if val is None:
        return True
    if not isinstance(val, str):
        return False
    return val.strip() in MISSING_SENTINELS or val.strip() == ""

def normalize(series: pd.Series) -> pd.Series:
    """Apply stages 1-2 (missing + error → pd.NA). Stages 3-4 are on-demand."""
    def _norm(val):
        if is_missing(val):
            return pd.NA
        s = str(val).strip()
        if any(s.startswith(p) for p in SHELL_ERROR_PREFIXES):
            return pd.NA
        return s
    return series.apply(_norm)

def try_numeric(series: pd.Series) -> pd.Series:
    """Stage 5 — lazy coercion for chart/analysis only. Hex → int, decimal → float."""
    import re
    def _coerce(val):
        if pd.isna(val):
            return pd.NA
        s = str(val).strip()
        if re.match(r'^0[xX][0-9a-fA-F]+$', s):
            try:
                return int(s, 16)
            except ValueError:
                return pd.NA
        try:
            return float(s)
        except ValueError:
            return pd.NA
    return series.apply(_coerce)
```

[CITED: ARCHITECTURE.md Result Normalization Pipeline; PITFALLS.md Pitfall 3, 15]

### Pattern 5: Pivot to Wide Form

```python
def pivot_to_wide(
    df_long: pd.DataFrame,
    swap_axes: bool = False,
    col_cap: int = 30,
) -> tuple[pd.DataFrame, bool]:
    """
    Returns (pivot_df, capped).
    Default: PLATFORM_ID as rows, Item as columns.
    swap_axes=True: Item as rows, PLATFORM_ID as columns.
    Uses aggfunc='first'; logs warning on duplicates.
    """
    import logging
    logger = logging.getLogger(__name__)

    dup_count = df_long.duplicated(subset=["PLATFORM_ID", "InfoCategory", "Item"]).sum()
    if dup_count > 0:
        logger.warning("pivot_to_wide: %d duplicate (PLATFORM_ID, InfoCategory, Item) rows detected; using aggfunc='first'", dup_count)

    if swap_axes:
        index_col = "Item"
        columns_col = "PLATFORM_ID"
    else:
        index_col = "PLATFORM_ID"
        columns_col = "Item"

    pivot = df_long.pivot_table(
        index=index_col,
        columns=columns_col,
        values="Result",
        aggfunc="first",
    )
    pivot.columns.name = None
    pivot = pivot.reset_index()

    capped = False
    value_cols = [c for c in pivot.columns if c != index_col]
    if len(value_cols) > col_cap:
        keep_cols = [index_col] + value_cols[:col_cap]
        pivot = pivot[keep_cols]
        capped = True

    return pivot, capped
```

[CITED: ARCHITECTURE.md Query Shape 1; PITFALLS.md Pitfall 1, 14]

### Pattern 6: st.query_params for Shareable URL (BROWSE-09)

`st.query_params` in Streamlit 1.36+ is a dict-like object supporting read and write. On page load, read it to initialize session state. On filter change, write it.

```python
# In browse.py — on page load (before widget rendering)
def _load_url_params():
    qp = st.query_params
    if "platforms" in qp and not st.session_state.get("_url_loaded"):
        st.session_state["selected_platforms"] = qp["platforms"].split(",")
    if "params" in qp and not st.session_state.get("_url_loaded"):
        st.session_state["selected_params"] = qp["params"].split(",")
    if "swap" in qp:
        st.session_state["pivot_swap_axes"] = qp["swap"] == "1"
    st.session_state["_url_loaded"] = True

def _sync_url_params(selected_platforms, selected_params, swap):
    st.query_params["platforms"] = ",".join(selected_platforms)
    st.query_params["params"] = ",".join(selected_params)
    if swap:
        st.query_params["swap"] = "1"
    else:
        st.query_params.pop("swap", None)

# Copy link button
if st.button("Copy link"):
    url = st.get_url()  # Streamlit 1.36+ internal URL helper, or construct from st.query_params
    st.components.v1.html(
        f'<script>navigator.clipboard.writeText("{url}")</script>',
        height=0,
    )
    st.toast("Link copied to clipboard.")
```

[ASSUMED — `st.query_params` dict API confirmed for Streamlit 1.36+ in ARCHITECTURE.md; exact `st.get_url()` availability needs checking at implementation time. Fallback: construct URL from `st.query_params` manually.]

### Pattern 7: Export Dialog via st.dialog

`@st.dialog` decorator is available in Streamlit 1.40+ and confirmed in Streamlit 1.56.0.

```python
@st.dialog("Export data")
def export_dialog(df: pd.DataFrame, tab_name: str, is_pivot_tab: bool, df_long: pd.DataFrame | None = None):
    import io, datetime, re

    fmt = st.radio("Format", ["Excel (.xlsx)", "CSV (.csv)"], horizontal=True)
    ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    default_name = f"pbm2_{tab_name}_{ts}"
    filename = st.text_input("Filename", value=default_name)
    st.caption("File will be saved to your Downloads folder.")

    scope_df = df
    if is_pivot_tab:
        scope = st.radio("Scope", ["Current view (pivot)", "Raw long-form rows"], index=0)
        if scope == "Raw long-form rows" and df_long is not None:
            scope_df = df_long

    if st.button("Download", type="primary"):
        # Sanitize filename
        clean = re.sub(r'[^A-Za-z0-9_\-.]', '_', filename)
        clean = re.sub(r'_+', '_', clean)[:128]

        if "xlsx" in fmt:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                scope_df.to_excel(writer, index=True, sheet_name="data")
            st.download_button("Save", data=buf.getvalue(),
                               file_name=f"{clean}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            csv_bytes = scope_df.to_csv(index=True).encode("utf-8")
            st.download_button("Save", data=csv_bytes,
                               file_name=f"{clean}.csv", mime="text/csv")

    if st.button("Close", type="secondary"):
        st.rerun()
```

[CITED: CLAUDE.md Excel Export section; UI-SPEC D-16; PITFALLS.md (openpyxl pattern)]

### Pattern 8: Plotly Chart (numeric-only columns)

```python
# In chart tab
import plotly.express as px

def get_numeric_cols(df_wide: pd.DataFrame) -> list[str]:
    """Return column names that are successfully coercible to numeric."""
    from app.services.result_normalizer import try_numeric
    numeric = []
    for col in df_wide.columns:
        if col == "PLATFORM_ID":
            continue
        coerced = try_numeric(df_wide[col])
        if coerced.notna().any():
            numeric.append(col)
    return numeric

# Render
numeric_cols = get_numeric_cols(df_wide)
if not numeric_cols:
    st.info("No numeric columns in the current selection. Add numeric parameters in the sidebar.")
else:
    col_to_chart = st.selectbox("Column to chart", options=numeric_cols)
    chart_type = st.radio("Chart type", options=["Bar", "Line", "Scatter"], horizontal=True)

    chart_series = try_numeric(df_wide[col_to_chart]).dropna()
    chart_df = df_wide[["PLATFORM_ID"]].copy()
    chart_df[col_to_chart] = chart_series

    if chart_type == "Bar":
        fig = px.bar(chart_df, x="PLATFORM_ID", y=col_to_chart, title=col_to_chart)
    elif chart_type == "Line":
        fig = px.line(chart_df, x="PLATFORM_ID", y=col_to_chart, title=col_to_chart)
    else:
        fig = px.scatter(chart_df, x="PLATFORM_ID", y=col_to_chart, title=col_to_chart)

    st.plotly_chart(fig, use_container_width=True)
```

[VERIFIED: `st.plotly_chart(use_container_width=True)` confirmed in CLAUDE.md; VIZ-02 lazy coercion pattern]

### Pattern 9: Settings Page — per-entry Test Button

The Test button must be synchronous (D-10). For DB, call `MySQLAdapter.test_connection()`. For LLM, create a minimal ping (empty completion call or Ollama health check).

```python
# Test DB connection
if st.button("Test", key=f"test_db_{db_cfg.name}"):
    with st.spinner("Testing..."):
        adapter = build_adapter(db_cfg)
        ok, msg = adapter.test_connection()
    if ok:
        st.success("Connected")
    else:
        st.error("Connection failed. See error detail below.")
        with st.expander("Error detail"):
            st.code(msg)

# Test LLM connection — Ollama: GET /api/tags; OpenAI: list models
def test_llm_connection(llm_cfg: LLMConfig) -> tuple[bool, str]:
    if llm_cfg.type == "ollama":
        import requests
        endpoint = (llm_cfg.endpoint or "http://localhost:11434").rstrip("/")
        try:
            r = requests.get(f"{endpoint}/api/tags", timeout=5)
            r.raise_for_status()
            return True, "Ollama is running"
        except Exception as e:
            return False, str(e)
    else:  # openai
        from openai import OpenAI
        import os
        api_key = llm_cfg.api_key or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return False, "No API key configured"
        try:
            client = OpenAI(api_key=api_key, base_url=llm_cfg.endpoint or None)
            client.models.list()
            return True, "OpenAI API reachable"
        except Exception as e:
            return False, str(e)
```

[ASSUMED — Ollama `/api/tags` endpoint for health check; OpenAI `models.list()` as ping. Both reasonable but not verified against official docs in this session.]

### Pattern 10: Cache Clear on Settings Save (D-12)

```python
# In settings.py after save_settings(updated_settings)
st.cache_resource.clear()
st.cache_data.clear()
st.toast("Saved. Caches refreshed.")
```

This forces a new `get_db_adapter()` call on next Browse interaction, picking up the new config. [CITED: CONTEXT.md D-12]

### Anti-Patterns to Avoid

- **Pages importing DBAdapter directly**: Pages must import from `app.services.ufs_service` only. Direct adapter access in pages bypasses caching and creates engine-per-rerun exhaustion.
- **Passing Python `list` to `@st.cache_data` functions**: Lists are unhashable; cache never hits. Always convert to `tuple` before passing as argument.
- **Storing DataFrames in `st.session_state`**: Per-session memory pressure. Store only filter keys (platform list, parameter list) — re-fetch on render.
- **Using `pd.read_sql` instead of `pd.read_sql_query`**: pandas 3.x raises deprecation warnings for the former with text-SQL.
- **Global `Result` coercion**: Stage 5 (numeric coercion) only runs in the chart path, never in the grid path.
- **`st.cache_resource` for DataFrames**: Returns shared mutable object; corrupts concurrent sessions.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Typeahead / search on large list | Custom JS autocomplete | `st.multiselect` with `placeholder=` | Built-in substring filtering; no extra component |
| Excel file generation | Custom XML/ZIP logic | `pd.ExcelWriter(buf, engine="openpyxl")` | openpyxl handles cell types, sheets, encoding correctly |
| Download trigger | HTTP response override | `st.download_button` | Streamlit handles browser download correctly without workarounds |
| Dialog / modal overlay | `st.empty()` + session state toggle | `@st.dialog` decorator | Native in Streamlit 1.36+; no JS needed |
| Connection health indicator | Custom polling loop | `MySQLAdapter.test_connection()` on demand | SELECT 1 is sufficient; continuous polling is wasteful in a sync app |
| Settings persistence | Custom file serialization | `save_settings()` in `app/core/config.py` | Already implemented; YAML round-trip via pyyaml |
| Cache invalidation on settings change | Manual engine teardown | `st.cache_resource.clear()` + `st.cache_data.clear()` | Clears all cached objects atomically |
| URL state serialization | `urllib.parse` manual encoding | `st.query_params` dict API | Streamlit handles encoding/decoding |
| Numeric detection in mixed column | Custom regex tree | `pd.to_numeric(series, errors="coerce").notna().any()` | Handles int, float, scientific notation; returns pd.NA for non-numeric |

---

## Common Pitfalls

### Pitfall 1: `pool_pre_ping` missing, `pool_recycle=1800` too short

**What goes wrong:** MySQL server closes idle connections after its `wait_timeout` (often 300–600s on intranet servers). Without `pool_pre_ping=True`, SQLAlchemy uses a stale connection and the first query of each session throws `OperationalError: (2006, 'MySQL server has gone away')`. `pool_recycle=1800` is only 30 minutes — if `wait_timeout` is lower, connections recycle but may still be re-checked stale.

**How to avoid:** The existing `MySQLAdapter._get_engine()` needs `pool_pre_ping=True` (currently absent) and `pool_recycle=3600` (currently 1800). Fix in Plan 1 (scaffolding fixes).

### Pitfall 2: `pd.read_sql` deprecation warning in pandas 3.x

**What goes wrong:** `pd.read_sql(text(sql), conn)` is deprecated in pandas 3.x for raw text SQL; it works but emits a `FutureWarning` that pollutes server logs. The correct form is `pd.read_sql_query(text(sql), conn)`.

**How to avoid:** Fix in `MySQLAdapter.run_query()` and in all new service functions.

### Pitfall 3: `IN :platforms` SQLAlchemy tuple parameter

**What goes wrong:** SQLAlchemy `text()` with `IN :param` requires the bound value to be a tuple, not a list. Lists cause `ProgrammingError` with pymysql. Empty tuples (no platforms selected) cause a SQL syntax error.

**How to avoid:** Guard against empty selection before calling fetch_cells (show empty-state info instead). Convert list → tuple at the service boundary.

### Pitfall 4: `"None"` string treated as valid data

**What goes wrong:** `pd.isna("None")` returns `False`. The string "None" (from Python's `str(None)`) is truthy and appears in charts as a data point and in pivot cells as text where the cell should be blank.

**How to avoid:** `result_normalizer.is_missing("None")` must return `True`. Covered by DATA-01. Add a unit test as the first test written for the normalizer.

### Pitfall 5: Pivot column explosion (>30 columns)

**What goes wrong:** A user picks an entire InfoCategory (e.g., `lun_info`) which has 8 items × 8 LUNs = 64 columns. The pivot renders 64 columns, Streamlit's horizontal scroll is unusable without frozen row headers.

**How to avoid:** The 30-column cap in `pivot_to_wide()` truncates to the first 30 columns and returns `capped=True`. The Browse page shows `st.warning("Showing first 30 of N parameters...")` above the grid when capped.

### Pitfall 6: `st.dialog` closes when st.download_button is clicked

**What goes wrong:** In Streamlit, clicking `st.download_button` inside a `@st.dialog`-decorated function triggers a rerun, which closes the dialog before the browser can start the download. This is a known Streamlit behavior.

**How to avoid:** Render the `st.download_button` inside the dialog but without a nested button click triggering rerun. In practice, the download happens in the same rerun as the button click, before the dialog closes — this usually works correctly in Streamlit 1.40+. If problematic, generate the file bytes eagerly and render `st.download_button` statically rather than inside a conditional. [ASSUMED — behavior may vary; test at implementation time.]

### Pitfall 7: Sidebar widgets re-render on every tab switch

**What goes wrong:** In Streamlit's multi-page architecture with `st.Page`, the sidebar is part of the entrypoint (`streamlit_app.py`). Platform and parameter multiselects are only rendered on the Browse page. If they are rendered in the entrypoint instead, they appear on the Settings page too (causing confusing UX).

**How to avoid:** Per D-05, platform and parameter pickers belong inside `browse.py`'s sidebar block using `st.sidebar.*` — not in `streamlit_app.py`. The entrypoint renders only: app title, DB selector, LLM selector, health indicator.

### Pitfall 8: Cache key collision when `list_platforms(_db)` is called with different adapters

**What goes wrong:** `@st.cache_data` hashes function arguments. If `_db` is prefixed with `_`, Streamlit skips hashing it — meaning all calls to `list_platforms(_db)` share the same cache entry regardless of which adapter is passed. For Phase 1 with a single DB this is fine. With multiple DB configs, the cache returns the first DB's platform list for all DBs.

**How to avoid:** For Phase 1 (single DB), this is acceptable. For future multi-DB support, add the `db_name: str` as an explicit cached argument alongside `_db`.

---

## Code Examples

### `fetch_cells` with row-cap enforcement (DATA-05, DATA-07)

```python
@st.cache_data(ttl=60, show_spinner=False)
def fetch_cells(
    _db: DBAdapter,
    platforms: tuple[str, ...],
    infocategories: tuple[str, ...],
    items: tuple[str, ...],
    row_cap: int = 200,
) -> pd.DataFrame:
    if not platforms or not items:
        return pd.DataFrame()

    sql = sa.text("""
        SELECT PLATFORM_ID, InfoCategory, Item, Result
        FROM ufs_data
        WHERE PLATFORM_ID IN :platforms
          AND InfoCategory IN :categories
          AND Item IN :items
        LIMIT :cap
    """)
    with _db._get_engine().connect() as conn:
        try:
            conn.execute(sa.text("SET SESSION TRANSACTION READ ONLY"))
        except Exception:
            pass
        df = pd.read_sql_query(sql, conn,
                               params={"platforms": platforms,
                                       "categories": infocategories,
                                       "items": items,
                                       "cap": row_cap + 1})
    # Detect if cap was hit
    capped = len(df) > row_cap
    return df.head(row_cap), capped
```

### `st.dataframe` with column config for heterogeneous Result values

```python
# All Result columns are TextColumn — do NOT use NumberColumn globally
column_cfg = {col: st.column_config.TextColumn(col) for col in df_wide.columns
              if col != "PLATFORM_ID"}
column_cfg["PLATFORM_ID"] = st.column_config.TextColumn("Platform")

st.dataframe(
    df_wide,
    column_config=column_cfg,
    use_container_width=True,
    hide_index=False,
)
```

[CITED: UI-SPEC Pivot Tab contract; CLAUDE.md Streamlit Data Display section]

### `.gitignore` content (FOUND-02 + deferred FOUND-01)

```gitignore
# Config files containing secrets
config/settings.yaml
config/auth.yaml
.env

# Python
__pycache__/
*.pyc
*.pyo
.venv/
*.egg-info/

# Logs
logs/

# OS
.DS_Store
```

---

## Threat Model (SAFE-01 scope only)

Phase 1 has no LLM SQL generation, so the threat surface is narrower than Phase 2. Relevant threats:

| Threat | Mitigation | Status |
|--------|-----------|--------|
| SQL injection via PLATFORM_ID / Item filters in Browse | SQLAlchemy bound parameters in `sa.text()` — parameterized, never f-string SQL | Must verify in ufs_service implementation |
| `SET SESSION TRANSACTION READ ONLY` enforcement | Already in `MySQLAdapter.run_query()`; non-fatal if unsupported | DONE — confirmed in code |
| Settings page open to all (D-09) | Accepted risk for Phase 1; plaintext password in `settings.yaml` is gitignored | Risk accepted; gitignore must be created |
| `config/auth.yaml` not gitignored | `.gitignore` does not exist — demo credentials are tracked | BLOCKER — fix in Plan 1 |
| Secrets logged | `settings.yaml` passwords must not appear in Streamlit logs or exception messages | Verify error messages in adapters do not include raw config dumps |

---

## Environment Availability

All dependencies are Python packages installable via pip. No external services are required to build Phase 1 (the MySQL DB is external but not required for unit tests; a real DB is needed for integration tests only).

| Dependency | Required By | Available | Notes |
|------------|-------------|-----------|-------|
| Python >= 3.11 | pandas 3.x | To verify in target env | pandas 3.0 requires Python >=3.11 |
| MySQL server (ufs_data) | Integration tests, real usage | Unknown — intranet server | Not needed to build; needed to run |
| Streamlit 1.56.0 | All UI | Confirmed in adjacent project `.venv` | Install via `pip install streamlit>=1.40,<2.0` |
| SQLAlchemy 2.0.x | DB layer | Confirmed installed in adjacent project | Verify upper bound `<2.1` in requirements.txt |

**Missing with fallback:**
- No MySQL server in dev environment: use `pytest-mock` to mock `DBAdapter.run_query()` for all unit and page tests.

---

## Validation Architecture

`workflow.nyquist_validation` is `false` in `.planning/config.json`. Validation Architecture section is skipped per config.

---

## Security Domain

`security_enforcement` is not explicitly set in config.json (absent = enabled). Phase 1 threat scope per SAFE-01:

| ASVS Category | Applies to Phase 1 | Control |
|---------------|-------------------|---------|
| V5 Input Validation | Yes — PLATFORM_ID, InfoCategory, Item used in SQL | SQLAlchemy bound parameters (`sa.text()` + named params) |
| V2 Authentication | No — deferred per D-04 | N/A Phase 1 |
| V3 Session Management | Partial — `st.session_state` isolation | Streamlit built-in per-session isolation; no shared mutable cache |
| V4 Access Control | No — open intranet for Phase 1 per D-09 | N/A Phase 1 |
| V6 Cryptography | No — no crypto operations in Phase 1 | N/A Phase 1 |

**SAFE-01 implementation note:** `SET SESSION TRANSACTION READ ONLY` is already in `MySQLAdapter.run_query()`. The `ufs_service.fetch_cells()` must call it too (via the engine connection), or delegate to `_db._get_engine().connect()` directly with the session guard — both are equivalent.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `st.query_params` dict API (read + write) is available in Streamlit 1.56.0 | Pattern 6 | API may differ; fallback is `st.experimental_get_query_params` / `st.experimental_set_query_params` (deprecated in 1.30 but still functional) |
| A2 | SQLAlchemy `IN :platforms` with `params={"platforms": tuple_value}` works correctly with pymysql driver | Pattern 3 | May need `bindparam` with `expanding=True` for SQLAlchemy 2.x; test at implementation |
| A3 | `st.dialog` closing behavior when `st.download_button` clicked inside dialog | Pitfall 6 | If download is interrupted by dialog close, use eager BytesIO pre-generation |
| A4 | Ollama `/api/tags` endpoint available for health check test in Settings | Pattern 9 | Could also use `/api/version`; either works for connectivity test |
| A5 | `st.get_url()` or equivalent exists in Streamlit 1.56.0 for copying the full URL | Pattern 6 | Fallback: construct URL from `st.query_params` + known base path |
| A6 | `@st.cache_data` on `fetch_cells()` is useful (same platform/params re-queried in same session) | Pattern 2 | Browse reuses same filter state across Pivot/Detail/Chart tabs — so yes, cache is valuable |

---

## Open Questions

1. **SQLAlchemy `IN` clause with tuple parameters (A2)**
   - What we know: `sa.text("... IN :ids")` with `params={"ids": ("a", "b")}` is one approach; `sa.text("... IN :ids")` with `bindparam("ids", expanding=True)` is the official SA2 approach.
   - What's unclear: Which pymysql + SQLAlchemy 2.0.x combination handles bare tuple better.
   - Recommendation: In the ufs_service plan, include a verification step: run a simple `SELECT * FROM ufs_data WHERE PLATFORM_ID IN :p LIMIT 1` with `params={"p": ("test",)}` against the real DB or a mock.

2. **`st.query_params` write API (A1)**
   - What we know: `st.query_params` is a `QueryParamsProxy` object in Streamlit 1.30+; dict-style assignment (`st.query_params["key"] = "value"`) was added in Streamlit 1.32.
   - What's unclear: Whether 1.56.0 behaves identically.
   - Recommendation: At implementation time, test `st.query_params["platforms"] = "test"` in a minimal script against the installed 1.56.0 before building the full URL sync.

3. **PLATFORM_ID count in production DB**
   - What we know: STATE.md flags "if > ~500, platform picker needs brand-grouped design."
   - What's unclear: Actual count.
   - Recommendation: Plan 4 (Browse page) should include a step to run `SELECT COUNT(DISTINCT PLATFORM_ID) FROM ufs_data` and conditionally add brand-grouped display logic if needed. For Phase 1, the flat multiselect with typeahead is sufficient up to ~200-300 items.

---

## Sources

### Primary (HIGH confidence — read directly in this session)
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/app/core/config.py` — Settings, DatabaseConfig, LLMConfig, load_settings, save_settings
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/app/adapters/db/mysql.py` — MySQLAdapter; confirmed pool_pre_ping absent, pool_recycle=1800
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/app/adapters/llm/openai_adapter.py` — OpenAIAdapter; confirmed httpx.Timeout(30s), env fallback
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/requirements.txt` — confirmed current pins; gaps: no sqlalchemy upper bound, no pydantic-ai, pandas>=2.2
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/.planning/phases/01-foundation-browsing/01-CONTEXT.md` — all D-01..D-16 decisions
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/.planning/phases/01-foundation-browsing/01-UI-SPEC.md` — UI contract (layout, copy, color, typography)
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/.planning/research/ARCHITECTURE.md` — patterns 1-5, build order, anti-patterns 1-4
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/.planning/research/PITFALLS.md` — pitfalls 1-16
- Streamlit 1.56.0 confirmed installed: `/home/yh/Desktop/02_Projects/Proj27_PBM1/.venv/lib/python3.13/site-packages/streamlit-1.56.0.dist-info`
- streamlit-authenticator 0.4.2 confirmed installed (adjacent project): same venv

### Secondary (MEDIUM confidence)
- `CLAUDE.md` — Verified stack decisions, version pins, scaffolding assessment, alternatives rejected
- `.planning/research/STACK.md`, `SUMMARY.md`, `FEATURES.md` — Referenced indirectly via ARCHITECTURE.md and CLAUDE.md

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified either in adjacent venv or via CLAUDE.md which cites PyPI
- Architecture patterns: HIGH — scaffolding read directly; patterns from ARCHITECTURE.md which was verified against official docs
- EAV/pivot patterns: HIGH — based on direct code reading + ARCHITECTURE.md + PITFALLS.md
- Pitfalls: HIGH for mechanics; MEDIUM for a few edge cases (dialog download behavior, exact IN clause syntax)

**Research date:** 2026-04-23
**Valid until:** 2026-05-23 (stable stack; 30-day estimate)
