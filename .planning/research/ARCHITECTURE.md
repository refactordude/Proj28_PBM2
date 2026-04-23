# Architecture Research

**Domain:** Streamlit intranet data-browsing app with EAV-form MySQL source and pluggable LLM NL2SQL agent
**Researched:** 2026-04-23
**Confidence:** HIGH (scaffolding read directly; Streamlit and SQLAlchemy patterns verified against official docs)

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        UI LAYER (Streamlit)                          │
│                                                                       │
│  streamlit_app.py (entrypoint / router / auth guard)                 │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │ Browse page  │ │  NL Query    │ │  History    │ │  Settings   │  │
│  │ (browse.py)  │ │ (nl_query.py)│ │ (history.py)│ │(settings.py)│  │
│  └──────┬───────┘ └──────┬───────┘ └──────┬──────┘ └──────┬──────┘  │
│         │                │                │               │          │
│    UI components (widgets, grids, charts, export buttons)            │
└─────────┼────────────────┼────────────────┼───────────────┼──────────┘
          │                │                │               │
          ▼                ▼                ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     SERVICE / DOMAIN LAYER                           │
│                                                                       │
│  ┌────────────────────────┐    ┌──────────────────────────────────┐  │
│  │  ufs_service.py        │    │  agent/runner.py                 │  │
│  │  (query builder,       │    │  (ReAct loop, max_steps=5,       │  │
│  │   pivot, normalizer,   │    │   timeout_s=30, row_cap=200)     │  │
│  │   LUN/DME parser)      │    │                                  │  │
│  └──────────┬─────────────┘    └──────────────┬───────────────────┘  │
│             │                                  │                      │
│  ┌──────────┴──────────────────────────────────┴────────────────────┐ │
│  │  agent/tools.py  (list_platforms, list_parameters,               │ │
│  │                   search_parameters, fetch_cells,                │ │
│  │                   run_readonly_sql)                              │ │
│  └───────────────────────────────────────────────────────────────── ┘ │
└─────────────────────────────────────────────────────────────────────┘
          │                                  │
          ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       ADAPTER LAYER (existing)                       │
│                                                                       │
│  app/adapters/db/         app/adapters/llm/                          │
│  ┌──────────────────┐    ┌───────────────────────────────────────┐   │
│  │  DBAdapter (ABC) │    │  LLMAdapter (ABC)                     │   │
│  │  MySQLAdapter    │    │  OpenAIAdapter   OllamaAdapter        │   │
│  │  registry.py     │    │  registry.py                          │   │
│  └────────┬─────────┘    └───────────────┬───────────────────────┘   │
│           │                              │                            │
│  (SQLAlchemy engine,                 (openai SDK /                    │
│   pool_pre_ping=True,                 httpx requests,                 │
│   read-only session)                  timeout=30s)                    │
└───────────┼──────────────────────────────┼───────────────────────────┘
            │                              │
            ▼                              ▼
┌────────────────────┐      ┌──────────────────────────────────────────┐
│  MySQL (ufs_data)  │      │  OpenAI API  /  Ollama (local)           │
│  read-only user    │      │  runtime-switchable via sidebar          │
└────────────────────┘      └──────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        CONFIG LAYER (existing)                       │
│                                                                       │
│  app/core/config.py          app/core/agent/config.py                │
│  Settings / DatabaseConfig   AgentConfig                             │
│  LLMConfig / AppConfig                                               │
│                                                                       │
│  Loaded at startup via load_settings() → st.cache_resource           │
│  Runtime overrides (active LLM name, active DB name) → session_state │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `streamlit_app.py` | Auth guard, page router, shared sidebar (LLM selector, DB status) | repo root / `app/` root |
| `pages/browse.py` | Platform picker, parameter picker, wide-form pivot grid, charts, export | `app/pages/` |
| `pages/nl_query.py` | NL input box, agent result display, streaming summary, history entry | `app/pages/` |
| `pages/history.py` | Recent query history viewer | `app/pages/` |
| `pages/settings.py` | DB connection CRUD, LLM endpoint CRUD, agent budget display | `app/pages/` |
| `app/services/ufs_service.py` | Domain queries: platform list, parameter catalog, fetch_cells, pivot, normalizer, LUN/DME parser | `app/services/` |
| `app/core/agent/runner.py` | ReAct loop (max_steps, timeout, row_cap enforcement), tool dispatch | `app/core/agent/` |
| `app/core/agent/tools.py` | Tool definitions exposed to LLM; wraps ufs_service calls | `app/core/agent/` |
| `app/adapters/db/` | SQLAlchemy engine, connection pool, raw SQL execution | existing |
| `app/adapters/llm/` | OpenAI/Ollama chat, generate_sql, stream_text | existing |
| `app/core/config.py` | Settings load/save, Pydantic models | existing |
| `app/core/agent/config.py` | AgentConfig budget constraints | existing |

---

## Recommended Project Structure

```
Proj28_PBM2/
├── streamlit_app.py            # entrypoint: auth, st.navigation, shared sidebar
├── app/
│   ├── __init__.py
│   ├── pages/
│   │   ├── browse.py           # Phase 1: browsing UI (platform + parameter pickers, pivot grid)
│   │   ├── nl_query.py         # Phase 2: NL input, agent results, summary
│   │   ├── history.py          # Phase 2+: recent query history
│   │   └── settings.py         # Phase 1: DB/LLM connection settings
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ufs_service.py      # Phase 1: domain logic — pivot, normalize, catalog
│   │   └── result_normalizer.py# Phase 1: Result field coercion, LUN/DME parsing
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # existing — Settings, DatabaseConfig, LLMConfig, AppConfig
│   │   └── agent/
│   │       ├── __init__.py
│   │       ├── config.py       # existing — AgentConfig
│   │       ├── runner.py       # Phase 2: ReAct loop
│   │       └── tools.py        # Phase 2: tool definitions for LLM
│   └── adapters/
│       ├── __init__.py
│       ├── db/                 # existing — DBAdapter, MySQLAdapter, registry
│       └── llm/                # existing — LLMAdapter, OpenAI, Ollama, registry
├── config/
│   ├── settings.yaml           # active config (gitignored)
│   ├── settings.example.yaml   # existing template
│   └── auth.yaml               # existing streamlit-authenticator credentials
├── .env                        # OPENAI_API_KEY, SETTINGS_PATH, AUTH_PATH, LOG_DIR
└── requirements.txt
```

### Structure Rationale

- **`app/pages/`** — Each surface (browse, NL, history, settings) is an independent `st.Page` file. The entrypoint (`streamlit_app.py`) registers them with `st.navigation`; common sidebar widgets live in the entrypoint.
- **`app/services/`** — Thin domain service layer between pages and adapters. Pages never call `DBAdapter.run_query()` directly; they call `ufs_service` functions. This makes the browsing UI testable without a live DB.
- **`app/services/result_normalizer.py`** — Isolated module for the `Result` field coercion pipeline. Keeping it separate prevents the complexity from bleeding into both the service layer and the agent tools layer.
- **`app/core/agent/`** — Agent runner and tool definitions sit inside `core/` alongside config because they share the `AgentConfig` budget constraints and depend on `ufs_service`, not directly on adapters.
- **`app/adapters/`** — Already exists; no restructuring needed. DB adapter is the only code that touches SQLAlchemy directly.

---

## Architectural Patterns

### Pattern 1: Layered read-only data flow (Pages → Service → Adapter)

**What:** Each page calls a `ufs_service` function that builds a parameterized SQL string, calls `DBAdapter.run_query()`, returns a raw `pd.DataFrame`, and then applies normalization + pivot client-side.

**When to use:** All three query shapes (lookup, compare, filter-by-value). The service layer handles query building; normalization and pivot always happen in Python, never in SQL (MySQL has no dynamic pivot).

**Trade-offs:** CPU overhead for large DataFrames is on the Streamlit server, not MySQL. Acceptable for 100k-row EAV tables because queries are always filtered to a target platform/parameter set before pivoting.

**Example flow:**
```python
# pages/browse.py
df_long = ufs_service.fetch_cells(db, platforms=selected, parameters=selected_params)
df_wide = ufs_service.pivot_wide(df_long)   # pandas.pivot_table(aggfunc="first")
st.dataframe(df_wide)
```

### Pattern 2: st.cache_resource for DBAdapter singleton

**What:** The `DBAdapter` instance (and its underlying SQLAlchemy engine with `pool_pre_ping=True, pool_recycle=1800`) is created once per app process and shared across all user sessions. The active *selection* of which DB config to use is stored in `st.session_state`.

**When to use:** Always. Creating a new engine per page rerun causes connection exhaustion and severe latency.

**Trade-offs:** All users share the same connection pool. Thread-safe because SQLAlchemy's connection pool is thread-safe by design. The `MySQLAdapter` already implements `pool_pre_ping=True` and `pool_recycle=1800`.

```python
# app/services/ufs_service.py or streamlit_app.py
@st.cache_resource
def get_db_adapter(config_name: str) -> DBAdapter:
    settings = load_settings()
    db_cfg = find_database(settings, config_name)
    return build_adapter(db_cfg)
```

### Pattern 3: st.cache_data for expensive catalog queries

**What:** Platform list (`DISTINCT PLATFORM_ID`) and parameter catalog (`DISTINCT InfoCategory, Item`) are expensive full-table scans. Cache them with `st.cache_data(ttl=300)` to avoid re-querying on every widget interaction.

**When to use:** `list_platforms()` and `list_parameters()` in `ufs_service.py`. Not for `fetch_cells()` — that result is query-specific and should not be cached between different user filter combinations.

**Trade-offs:** 5-minute staleness is acceptable for an intranet tool where the DB is updated by a separate upstream process, not in real-time.

```python
@st.cache_data(ttl=300)
def list_platforms(_db: DBAdapter) -> list[str]:
    df = _db.run_query("SELECT DISTINCT PLATFORM_ID FROM ufs_data ORDER BY PLATFORM_ID")
    return df["PLATFORM_ID"].tolist()
```

Note: `_db` prefix prevents Streamlit from trying to hash the adapter object.

### Pattern 4: st.session_state for runtime selections and history

**What:** Items that are per-user and per-session, not shared across users or worth caching globally, live in `st.session_state`. This includes the currently selected LLM name, currently selected DB name, and recent query history.

**Session state keys:**
```
st.session_state["active_db"]       # str: name of the selected DatabaseConfig
st.session_state["active_llm"]      # str: name of the selected LLMConfig
st.session_state["query_history"]   # list[dict]: last N NL queries + results
st.session_state["auth_status"]     # bool: set by streamlit-authenticator
st.session_state["username"]        # str: set by streamlit-authenticator
```

**What NOT to put in session state:** Raw DataFrames larger than ~50 rows (memory pressure per session), DB adapter objects (use `st.cache_resource` instead), Settings object (load fresh from YAML via `load_settings()` and cache with `st.cache_resource`).

### Pattern 5: ReAct agent with bounded tool loop (synchronous, single-threaded)

**What:** Given `max_steps=5` and `timeout_s=30`, the agent is a bounded synchronous loop. The LLM calls tools in sequence; each tool call is a Python function call (not async, not multi-agent). The loop terminates when the LLM emits a final answer, when `max_steps` is reached, or when the wall-clock timeout fires.

**Why synchronous:** Streamlit's execution model is single-threaded per session. An async agent loop would require `asyncio.run()` wrapping, adding complexity with no concurrency benefit for a single-user session. The 30-second timeout is enforced by a `signal.alarm` or a thread with a daemon timer.

**Architecture implied by AgentConfig:** `max_steps=5` means the loop is shallow — at most 5 tool calls. This rules out deep exploratory chains. The agent should resolve a question in: 1 step (direct lookup) or at most 3–4 steps (candidate parameter search → fetch cells → summarize). `row_cap=200` means `run_readonly_sql` appends `LIMIT 200` before execution. `max_context_tokens=30000` means the agent can hold a meaningful history + schema context in a single call.

```
Agent loop (runner.py):
  Step 0: Build system prompt with schema summary + AgentConfig constraints
  Step 1..N (N ≤ max_steps):
    → LLM call with tool definitions
    ← LLM returns tool_call or final_answer
    if tool_call: dispatch to tools.py, collect observation
    if final_answer: break
  Post-loop: if no final_answer, return best partial result + warning
```

---

## Data Flow

### Query Shape 1: Lookup (one platform, many parameters)

```
User selects platform + parameters in Browse page
    ↓
pages/browse.py → ufs_service.fetch_cells(db, platforms=[P], parameters=[p1, p2…])
    ↓
ufs_service builds:
  SELECT PLATFORM_ID, InfoCategory, Item, Result
  FROM ufs_data
  WHERE PLATFORM_ID = :p AND InfoCategory IN :cats AND Item IN :items
    ↓
DBAdapter.run_query(sql) → pd.DataFrame (long form)
    ↓
result_normalizer.normalize(df["Result"]) → cleans None/"None"/errors/whitespace
    ↓
ufs_service.pivot_wide(df) → pd.pivot_table(index=["InfoCategory","Item"],
                                              columns="PLATFORM_ID",
                                              values="Result",
                                              aggfunc="first")
    ↓
st.dataframe(df_wide) in browse.py
```

### Query Shape 2: Compare (many platforms, same parameters)

```
User selects multiple platforms + one or more parameters
    ↓
pages/browse.py → ufs_service.fetch_cells(db, platforms=[P1,P2,P3], parameters=[p1])
    ↓  (same SQL, WHERE PLATFORM_ID IN :platforms)
DBAdapter.run_query → long DataFrame
    ↓
result_normalizer.normalize → unified missing sentinel, hex/decimal coercion per-column
    ↓
pivot_wide → wide DataFrame with platforms as columns
    ↓
Optional: ufs_service.try_numeric(df_wide[p1]) → numeric series if parseable
    ↓
Plotly bar chart OR st.dataframe if mixed types
```

### Query Shape 3: Filter-by-value (which platforms have X ≥ threshold?)

```
This shape is primarily served by the NL agent, not the browse UI.

User asks: "Which platforms support HS400 Enhanced Strobe?"
    ↓
pages/nl_query.py → agent/runner.py.run(question, db, llm_adapter, agent_config)
    ↓
Agent loop:
  Tool: search_parameters("HS400") → returns [(InfoCategory, Item, sample_values)]
  Tool: fetch_cells(platforms=ALL, parameters=["dme/bHsEsSupport"]) → DataFrame
  LLM: generate final_answer with table + text summary
    ↓
runner.py returns AgentResult(dataframe, summary_text, steps_taken, sql_used)
    ↓
pages/nl_query.py: st.dataframe(result.dataframe), st.write_stream(result.summary)
    ↓
Append to st.session_state["query_history"]
```

### Result Normalization Pipeline

Normalization happens in `app/services/result_normalizer.py`, called by `ufs_service` before returning any DataFrame to the UI layer. It is per-query (lazy), never global.

```
Raw Result value (str | None)
    ↓
Stage 1 — Missing sentinel:
  SQL NULL → pd.NA
  "None" (string) → pd.NA
  "" (empty string) → pd.NA
  Whitespace-only → pd.NA
    ↓
Stage 2 — Error strings:
  starts with "cat: " → pd.NA  (captured shell error)
  "Permission denied" → pd.NA
  "No such file or directory" → pd.NA
  (store original in separate column if needed for debugging)
    ↓
Stage 3 — LUN prefix parsing (only for lun_info, lun_unit_descriptor, lun_unit_block):
  "0_WriteProtect" → lun_index=0, item="WriteProtect"
  Applied before pivot so each LUN becomes a distinct (InfoCategory, Item, lun_index)
    ↓
Stage 4 — DME local/peer splitting (only for dme category):
  "local=0x011101,peer=0x00010" → two rows: item+"_local", item+"_peer"
  Applied before pivot
    ↓
Stage 5 — Type coercion (optional, on-demand for numeric display/charting):
  try pd.to_numeric(series, errors='coerce')
  Hex strings ("0x01") → int via int(v, 16) if matches r'^0x[0-9a-fA-F]+'
  Space-delimited numbers → keep as string (don't explode)
  CSV lists → keep as string (don't split)
  (Coercion is per-column, per-query — never stored back to DB)
```

### Config / Settings Flow

```
Startup:
  load_settings() reads config/settings.yaml → Settings (Pydantic)
  @st.cache_resource: Settings object shared across all reruns
  OPENAI_API_KEY from os.environ → LLMConfig.api_key fallback (already in OpenAIAdapter)
  SETTINGS_PATH, AUTH_PATH, LOG_DIR from os.environ → override defaults

Runtime overrides (sidebar selections):
  st.session_state["active_db"]  → string key, resolved to DatabaseConfig via find_database()
  st.session_state["active_llm"] → string key, resolved to LLMConfig via find_llm()
  These are NOT stored back to Settings; they are ephemeral user preferences within a session.

Agent model override (from AgentConfig.model):
  If AgentConfig.model != "" → agent runner uses that model override
  Else → falls back to currently selected LLMConfig.model
  This is the accuracy-escalation path (e.g., use gpt-4.1 only for agent loops)
```

---

## Tool Design for the Agent

The agent has access to 5 tools, exposed through `app/core/agent/tools.py`. Each tool is a thin wrapper around `ufs_service` functions.

### Safe Tools (expose directly to LLM)

| Tool | Signature | Why Safe |
|------|-----------|----------|
| `list_platforms()` | `() → list[str]` | Returns DISTINCT PLATFORM_ID; no parameters, no injection surface |
| `list_parameters()` | `(category: str \| None) → list[dict]` | Returns catalog of (InfoCategory, Item); read-only scan |
| `search_parameters(query: str)` | `→ list[dict]` | LIKE-search on InfoCategory+Item names; no user-controlled SQL structure |
| `fetch_cells(platforms, parameters)` | `→ DataFrame` | Parameterized query; row_cap enforced inside tool | 
| `summarize_text(dataframe_json, question)` | `→ str` | Pure LLM call, no DB access; used for final summary generation |

### Restricted Tool (guarded, not raw)

| Tool | Signature | Guard |
|------|-----------|-------|
| `run_readonly_sql(sql: str)` | `→ DataFrame` | Validates against `allowed_tables`; strips/rejects DDL/DML keywords; appends `LIMIT {row_cap}`; uses read-only DB session |

**Do NOT expose:** A raw `run_sql()` without guards. Do NOT expose `pivot_wide()` or `normalize()` as LLM tools — these are post-processing steps called by the runner after tool results are collected, not tool calls themselves.

**Tool sequencing rationale:**
- The LLM almost always needs `search_parameters()` first to resolve a vague question to concrete (InfoCategory, Item) pairs.
- `fetch_cells()` is preferred over `run_readonly_sql()` for standard lookups because it enforces `allowed_tables` implicitly and returns pre-parameterized results.
- `run_readonly_sql()` is available as an escape hatch for queries that `fetch_cells()` cannot express (e.g., counting platforms with a specific value), but it is the last resort and always guarded.

---

## Multi-Page Navigation Structure

**Recommendation: `st.Page` + `st.navigation` (Streamlit 1.36+ API), not the legacy `pages/` directory.**

The modern `st.navigation` API (confirmed in Streamlit docs) allows conditional page lists based on auth state and shared sidebar elements in the entrypoint. This fits the auth-gated pattern the project already uses (`config/auth.yaml`).

```
streamlit_app.py (entrypoint):
  1. Run streamlit-authenticator
  2. If not authenticated → show only login form (no st.navigation pages)
  3. If authenticated:
     a. Render shared sidebar: DB selector, LLM selector, connection status
     b. Define pages:
        browse    = st.Page("app/pages/browse.py",   title="Browse",   icon="🔍")
        nl_query  = st.Page("app/pages/nl_query.py", title="Ask",      icon="💬")
        history   = st.Page("app/pages/history.py",  title="History",  icon="📜")
        settings  = st.Page("app/pages/settings.py", title="Settings", icon="⚙️")
     c. st.navigation({"Data": [browse, nl_query], "Config": [history, settings]}).run()
```

**Why not single-page with sidebar navigation:** The app has 4 distinct surfaces with clearly different widget sets (Browse has pickers + grid; Ask has text input + agent result; Settings has CRUD forms). Putting all of these in a single script with conditional rendering via sidebar radio buttons is the anti-pattern that `st.Page` was designed to replace. Multi-page with `st.navigation` keeps each surface testable and maintainable as an independent script.

---

## Build Order (Phase Dependencies)

The following ordering respects the user's stated priority: **browsing must work before NL agent is integrated**.

```
Phase 1 — Foundation (must exist before anything else)
  ├── app/core/config.py (DONE — existing)
  ├── app/core/agent/config.py (DONE — existing)
  ├── app/adapters/db/ (DONE — existing)
  ├── app/adapters/llm/ (DONE — existing)
  ├── streamlit_app.py (auth guard + st.navigation shell)
  └── app/pages/settings.py (DB/LLM config UI — users need to configure before browsing)

Phase 1 → Phase 2 (browsing layer; no LLM needed)
  ├── app/services/result_normalizer.py  ← must exist before ufs_service
  ├── app/services/ufs_service.py        ← must exist before browse page
  └── app/pages/browse.py               ← platform picker, parameter picker, pivot grid, export
      (depends on: DBAdapter, ufs_service, result_normalizer)

Phase 2 → Phase 3 (NL agent; depends on browsing layer being solid)
  ├── app/core/agent/tools.py           ← wraps ufs_service; needs ufs_service complete
  ├── app/core/agent/runner.py          ← ReAct loop; needs tools + LLMAdapter
  └── app/pages/nl_query.py            ← NL input, streaming summary, history
      (depends on: runner, tools, ufs_service, LLMAdapter)

Phase 3 → Phase 4 (polish; no new dependencies)
  └── app/pages/history.py             ← reads st.session_state["query_history"]
```

**Critical dependency:** `result_normalizer.py` must be written and tested against real sample data before `ufs_service.py` is written — the normalization logic is the domain's hardest problem (free-form `Result` field) and calling it correctly from the service layer requires a stable API.

---

## Error Surfacing Strategy

**Principle:** Every error has a specific landing zone. The agent runner catches LLM and DB exceptions and converts them into typed result objects; pages display them with `st.error()` or `st.warning()`. No raw Python tracebacks should reach the user in production.

```
DB connection failure:
  MySQLAdapter.test_connection() → (False, message)
  settings.py: shows st.error(message) with retry button
  ufs_service.py: wraps run_query() in try/except → raises ServiceError("DB unavailable")
  pages: catches ServiceError → st.error("Database unavailable. Check Settings.")

SQL timeout:
  MySQLAdapter uses connect_timeout=5 (connection), but no per-query timeout built in.
  Add: run_query() wraps pd.read_sql() with concurrent.futures.ThreadPoolExecutor + timeout
  On timeout: raises QueryTimeoutError
  Pages: st.warning(f"Query timed out after {timeout}s. Try narrowing your selection.")

LLM failure (OpenAI rate limit / network error):
  OpenAIAdapter: httpx.Timeout(30.0) already set
  Runner: wraps each LLM call in try/except → on exception, returns AgentResult with error flag
  nl_query.py: if result.error → st.error(result.error_message) + show partial results if any

Agent step budget exceeded:
  Runner: after max_steps, returns best partial AgentResult with warning
  nl_query.py: st.warning("Agent reached step limit. Showing partial results.") + display table

Ollama unavailable:
  OllamaAdapter: requests.post(..., timeout=120) → ConnectionError
  Bubble up as LLMUnavailableError with message "Ollama not running at {endpoint}"
  Sidebar: show red indicator next to LLM selector; nl_query.py: st.error(message)
```

---

## Scaling Considerations

| Scale | Architecture Adjustment |
|-------|------------------------|
| 1–5 simultaneous users (current intranet) | No changes needed; single Streamlit process, shared connection pool (existing) |
| 5–20 simultaneous users | Add query result caching for fetch_cells() with ttl=60s keyed on (platforms, parameters) hash; consider MySQL read replica |
| 20+ users | Deploy behind a reverse proxy with multiple Streamlit workers; connection pool size tuning on MySQLAdapter |

This is an intranet tool. 5-20 simultaneous users is the realistic ceiling. No distributed architecture is needed for v1.

---

## Anti-Patterns

### Anti-Pattern 1: Pages importing DBAdapter directly

**What people do:** `from app.adapters.db.mysql import MySQLAdapter` inside a page file; construct an engine on each rerun.

**Why it's wrong:** Creates a new SQLAlchemy engine (and connection pool) on every page rerun. Under Streamlit's rerun model, this means a new pool per widget interaction. Connection exhaustion within minutes.

**Do this instead:** Pages import from `app.services.ufs_service`; the service imports `DBAdapter` from `app/adapters` and the adapter singleton is managed via `@st.cache_resource` in the service or the entrypoint.

### Anti-Pattern 2: Storing large DataFrames in session_state

**What people do:** `st.session_state["result_df"] = big_df` after every query, as a cache.

**Why it's wrong:** Each Streamlit session holds its own in-process memory. 10 users × 5 queries × 200-row DataFrames × 20 columns = meaningful memory footprint. Session state is not garbage collected between reruns until the session ends.

**Do this instead:** Store only the query parameters (platform list, parameter list, question text) in session state. Re-fetch + re-pivot on re-render. Use `st.cache_data(ttl=60)` keyed on the query parameters if repeated fetches are a latency concern.

### Anti-Pattern 3: Passing raw user input to run_readonly_sql without validation

**What people do:** Agent tool receives LLM-generated SQL → passes it directly to `DBAdapter.run_query()`.

**Why it's wrong:** Even with a read-only DB user, the LLM can generate multi-table JOINs, subselects on system tables, or extremely expensive full-table scans that saturate the DB.

**Do this instead:** The `run_readonly_sql` tool in `tools.py` must: (1) parse the SQL with `sqlparse`, (2) reject any statement type other than `SELECT`/`SHOW`/`DESCRIBE`, (3) verify referenced tables are in `allowed_tables`, (4) append `LIMIT {row_cap}` if no LIMIT clause exists.

### Anti-Pattern 4: Global Result normalization at ingest time

**What people do:** Normalize the `Result` column once when the DataFrame comes back from MySQL, then cache the normalized result.

**Why it's wrong:** The same `Item` (e.g., `bMaxDataLanes`) legitimately appears as hex (`0x04`) on one platform and decimal (`4`) on another. Global normalization to a single type loses this information. A chart query wants numeric coercion; a text search wants the raw string.

**Do this instead:** Normalization is called lazily and per-query. `result_normalizer.normalize()` is always called before display, but numeric coercion (`try_numeric()`) is only called when the user requests a chart, not for the grid view.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| MySQL (`ufs_data`) | SQLAlchemy engine via `MySQLAdapter`; `@st.cache_resource` singleton | `readonly=True` enforces `SET SESSION TRANSACTION READ ONLY` |
| OpenAI API | `openai` SDK via `OpenAIAdapter`; `httpx.Timeout(30.0)` | API key from `OPENAI_API_KEY` env var or `LLMConfig.api_key` in settings |
| Ollama (local) | `requests.post` to `http://localhost:11434` via `OllamaAdapter` | Must be running locally; 120s timeout for large models |
| streamlit-authenticator | Runs in `streamlit_app.py` entrypoint; auth state stored in `st.session_state` | Credentials from `config/auth.yaml`; bcrypt hashed passwords |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `pages/*` → `services/ufs_service` | Direct function call | Pages never touch adapters directly |
| `services/ufs_service` → `adapters/db` | Direct function call via `DBAdapter` ABC | Swap DB type by changing registry |
| `core/agent/runner` → `core/agent/tools` | Function dispatch by tool name (dict lookup) | Tools are registered in `tools.py`; runner does not import tool implementations directly |
| `core/agent/tools` → `services/ufs_service` | Direct function call | Agent tools are wrappers; domain logic stays in service layer |
| `core/agent/runner` → `adapters/llm` | `LLMAdapter.generate_sql()` / tool-calling API | Adapter swaps between OpenAI and Ollama at runtime |
| `streamlit_app.py` → `core/config` | `load_settings()` once at startup, `@st.cache_resource` | Settings mutated only by settings page via `save_settings()` |

---

## Sources

- Streamlit multi-page apps — `st.Page` + `st.navigation` API: https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation
- Streamlit caching (`st.cache_data` vs `st.cache_resource`): https://docs.streamlit.io/develop/concepts/architecture/caching
- Streamlit session state: https://docs.streamlit.io/develop/concepts/architecture/session-state
- SQLAlchemy connection pool with Streamlit: https://discuss.streamlit.io/t/caching-a-database-connection-pool-for-multiple-users/81881
- NL2SQL system design guide 2025: https://medium.com/@adityamahakali/nl2sql-system-design-guide-2025-c517a00ae34d
- NL2SQL tool safe read-only execution (CrewAI reference): https://docs.crewai.com/en/tools/database-data/nl2sqltool
- ReAct loop architecture: https://www.waylandz.com/ai-agent-book-en/chapter-02-the-react-loop/

---
*Architecture research for: PBM2 — Streamlit + read-only MySQL EAV + pluggable LLM NL2SQL agent*
*Researched: 2026-04-23*
