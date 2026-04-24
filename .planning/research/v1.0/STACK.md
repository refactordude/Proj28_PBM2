# Stack Research

**Domain:** Streamlit intranet app — EAV MySQL browser + NL-to-SQL agent
**Researched:** 2026-04-23
**Confidence:** HIGH (all versions verified via PyPI / official docs)

---

## Verdict on Existing Scaffolding

The `requirements.txt` choices are sound. The specific version pins below replace the `>=` lower-bounds with verified current stable releases; there is no reason to swap any core library. The only areas where the scaffolding is thin or undecided are:

1. The NL agent framework (nothing committed yet — pick PydanticAI).
2. The LLM abstraction (nothing committed yet — use the openai client directly rather than adding litellm).
3. Caching strategy (no decision recorded — use st.cache_resource for the DB engine + st.cache_data with TTL for query results; DuckDB is optional but worth considering for pivot-heavy workloads).
4. The data grid component (nothing committed — use st.dataframe with column_config, not AgGrid).

---

## Recommended Stack

### Core Technologies

| Technology | Verified Version | Purpose | Why Recommended |
|------------|-----------------|---------|-----------------|
| Streamlit | 1.56.0 (2026-03-31) | Web app framework, all UI primitives | Production stable; `st.dataframe` column_config and programmatic selection support everything needed; `>=1.40` constraint in requirements.txt is satisfied |
| SQLAlchemy | 2.0.49 (2026-04-03) | DB engine, connection pooling | Stable series (2.1 is still beta as of 2026-04-16); `pool_pre_ping=True` + `pool_recycle=3600` prevents stale MySQL connections; `>=2.0` constraint is satisfied |
| pymysql | 1.1.x | MySQL DBAPI driver for SQLAlchemy | Pure-Python, no system libs required; the only practical choice for SQLAlchemy + MySQL without mysql-connector-python overhead |
| pandas | 3.0.2 (2026-03-31) | Client-side pivot, type coercion, export | Latest stable; `pd.read_sql_query` with a SQLAlchemy `Connection` is the standard idiom; 3.0 string dtype changes are backward-compatible for this workload |
| Pydantic v2 | 2.11.x | Settings models, agent structured output | Already in scaffolding as `DatabaseConfig`/`LLMConfig`/`AgentConfig`; v2 performance required for Settings hot-reload on every rerun |
| PydanticAI | 1.86.0 (2026-04-23) | NL-to-SQL agent framework | See NL Agent section below |
| openai | 1.78.x | OpenAI API client AND Ollama proxy client | The openai Python SDK is the correct abstraction for both backends (see LLM section) |
| streamlit-authenticator | 0.4.2 (2025-03-01) | Shared-credential intranet auth | YAML + bcrypt pattern; already scaffolded in `config/auth.yaml`; `>=0.3.3` constraint is satisfied by 0.4.2 |

### Supporting Libraries

| Library | Verified Version | Purpose | When to Use |
|---------|-----------------|---------|-------------|
| openpyxl | 3.1.x | Excel writer engine for pandas | Always — `pd.ExcelWriter(buf, engine="openpyxl")` inside `io.BytesIO` is the Streamlit download-button pattern |
| plotly | 5.24.x | Interactive charts | Bar / line / scatter for numeric parameters; use `st.plotly_chart(use_container_width=True)` |
| altair | 5.5.x | Declarative charts | Secondary option when Plotly is overkill; Streamlit's `st.altair_chart` is well-integrated |
| sqlparse | 0.5.x | SQL pretty-printing / AST | Already in scaffolding; use for displaying generated SQL to users and for lightweight SELECT-only validation before execution |
| python-dotenv | 1.0.x | `.env` loading | Already in scaffolding; load at startup before Pydantic Settings |
| pyyaml | 6.0.x | YAML settings file I/O | Already in scaffolding (`load_settings` / `save_settings`) |
| httpx | 0.27.x | Async HTTP | Already present; used by openai SDK internally; no direct usage needed in app code |
| bcrypt | 4.2.x | Password hashing | Used by streamlit-authenticator internally; keep pinned to avoid hash format drift |
| duckdb | 1.x (optional) | In-process pivot / filter queries | Add only if pivot performance on 100k+ rows proves unacceptable with pandas alone (see Caching section) |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | Unit + integration tests | Standard runner; pair with `streamlit.testing.v1.AppTest` for UI tests |
| streamlit AppTest | Streamlit-native headless UI testing | `AppTest.from_file("app/main.py")` — no browser required; runs in CI without Playwright overhead |
| pytest-mock | Mocking DB connections and LLM calls in tests | Mock `sqlalchemy.engine.Connection.execute` so tests never hit real DB |
| ruff | Linting + formatting | Replaces flake8 + black; single tool, fast |
| mypy | Type checking | Pydantic v2 generates stubs; run against `app/core/` at minimum |

---

## Sub-Question Answers

### 1. Streamlit Data Display (2026)

**Use `st.dataframe` with `column_config` for the read-only pivot grid. Do not use AgGrid.**

Rationale:

- `st.dataframe` in Streamlit 1.56.0 supports programmatic selection (`selection` parameter), always-visible column visibility toggle, `alignment` in column config, and `AudioColumn`/`VideoColumn` — sufficient for the EAV pivot grid.
- `column_config.NumberColumn`, `column_config.TextColumn`, and `column_config.CheckboxColumn` provide per-column type hints without requiring a separate library.
- AgGrid (`streamlit-aggrid`) is community-maintained by a solo developer; as of 2026 it is still alive but introduces a heavy JS dependency. For a read-only pivot display there is no feature AgGrid provides that `st.dataframe` + `column_config` does not.
- `st.data_editor` is for editable tables. Because the DB is strictly read-only, `st.data_editor` is the wrong primitive (it signals editability to users and returns mutation callbacks the app doesn't need).

**Pagination:** Implement server-side slicing with `st.session_state` page offset. Streamlit has no built-in pagination widget, but the pattern is trivial: `df_page = df.iloc[page * page_size : (page + 1) * page_size]`. For 100k-row tables, always apply a WHERE clause before pulling rows into pandas — never load the full table.

**Filter sidebar:** Standard pattern is `st.sidebar` with `st.multiselect` for platform picker and parameter picker. Streamlit 1.56.0 added a `filter_mode` parameter to `st.multiselect` and `st.selectbox` that enables type-ahead filtering without a custom component.

**What NOT to use:** `streamlit-aggrid` — unnecessary dependency, fragile against Streamlit version bumps, adds 200KB+ JS bundle, maintained by one person.

---

### 2. SQL Query Abstraction

**Use `pandas.read_sql_query(text("SELECT ..."), con=engine.connect())` with SQLAlchemy 2.x Core.**

The correct pattern for this project:

```python
# engine created once at startup, cached with st.cache_resource
engine = create_engine(
    "mysql+pymysql://...",
    pool_pre_ping=True,
    pool_recycle=3600,
)

# per-query
with engine.connect() as conn:
    df = pd.read_sql_query(
        sa.text("SELECT PLATFORM_ID, InfoCategory, Item, Result FROM ufs_data WHERE ..."),
        con=conn,
        params={...},
    )
```

Rationale:

- `pd.read_sql_query` with `sa.text(...)` and explicit `params` is the idiomatic pandas 3.x / SQLAlchemy 2.x pairing. The raw string form (`pd.read_sql`) was deprecated for text SQL in pandas 2.x; `read_sql_query` is the correct function.
- SQLAlchemy ORM is overkill — there is one table, no relationships, no ORM models to define.
- SQLAlchemy Core (not ORM) is the right level: use `engine.connect()` as context manager, `sa.text()` for parameterized queries, and `sa.select()` for programmatic query building when filters accumulate.
- `pool_pre_ping=True` is mandatory for MySQL: it tests connections on checkout, preventing "MySQL server has gone away" errors that appear after idle periods in an intranet app.
- `pool_recycle=3600` prevents connections older than 1 hour from being reused (MySQL's default `wait_timeout` is 8 hours but intranet servers often set it lower).
- Do NOT use SQLAlchemy 2.1.x yet — it is in beta (2.1.0b2 as of 2026-04-16). Pin to `sqlalchemy>=2.0,<2.1` until 2.1 reaches stable.

**What NOT to use:**
- Raw `pymysql.connect()` without SQLAlchemy — loses connection pooling, parameter escaping, and pandas integration.
- SQLAlchemy ORM — unnecessary mapping overhead for a single-table read-only workload.

---

### 3. NL-to-SQL Agent Framework

**Use PydanticAI (1.86.0) with a custom `run_sql` tool. Do not use LangChain or Vanna.ai.**

**Recommendation: PydanticAI with structured output**

PydanticAI reached V1 (API-stable) in September 2025. It has a first-class SQL generation example in its official docs targeting exactly this pattern: single table, structured output union (`Success | InvalidRequest`), validation via EXPLAIN before execution. Key fit for this project:

- The agent's `result_type` can be a Pydantic union: `SQLResult(query: str, explanation: str) | ClarificationNeeded(message: str)` — structured output prevents the LLM returning prose when a query is needed.
- `@agent.tool` wraps `run_sql(sql: str) -> str` — the agent calls this once and the tool enforces `allowed_tables`, `row_cap`, and `timeout_s` from `AgentConfig`.
- Native support for OpenAI and Ollama (via `openai` client with custom `base_url`) — no adapter shim needed.
- Already aligns with the Pydantic v2 used throughout the codebase (`DatabaseConfig`, `LLMConfig`, `AgentConfig` are all Pydantic models).
- Minimal dependency surface: does not drag in LangChain's 50+ transitive dependencies.

**Why not LangChain SQLDatabaseToolkit:**
- LangChain's `SQLDatabaseToolkit` reflects the full schema into the prompt on every call — for a single-table app this is wasteful and adds context token overhead against the `max_context_tokens=30000` limit.
- LangChain requires `langchain-community` + `langchain-core` + `langchain` — 3 packages with fast-moving APIs and frequent breaking changes between minor versions.
- The `SQLDatabaseChain` / `create_sql_agent` pattern exposes `execute_query` tools that are harder to gate with `allowed_tables` without subclassing. The scaffolded `AgentConfig.allowed_tables` is a natural fit for PydanticAI's `RunContext` dependency injection, not for LangChain's callback-based safety checks.

**Why not Vanna.ai:**
- Vanna is a RAG-over-DDL system designed for multi-table databases where the agent needs to retrieve relevant schema snippets. With a single known table (`ufs_data`) and a static schema, the full RAG setup (embedding store, vector DB, training loop) is architectural overhead that adds no accuracy benefit.
- Vanna's offline/local mode is opaque; the dual OpenAI+Ollama switchability required here is cleaner to implement directly.

**Why not LlamaIndex NLSQLTableQueryEngine:**
- Adds the full LlamaIndex dependency tree without unique benefits over PydanticAI for a single-table case.

**Why not raw OpenAI function-calling directly:**
- Valid option but means writing the agent loop, retry logic, structured output parsing, and tool dispatch by hand — exactly what PydanticAI provides. For a greenfield project, pick the framework.

**Agent safety implementation:**
The `AgentConfig` already provides `allowed_tables`, `row_cap`, `max_steps`, and `timeout_s`. Implement these inside the `run_sql` tool function:

```python
@agent.tool
def run_sql(ctx: RunContext[AppDeps], sql: str) -> str:
    # 1. sqlparse to assert SELECT-only, single table in allowed_tables
    # 2. execute with LIMIT row_cap
    # 3. return as JSON string for the agent to reason over
```

The `readonly` DB user is the last-resort backstop; the tool-level check is the first line of defense.

---

### 4. LLM Abstraction (OpenAI + Ollama Dual Backend)

**Use the `openai` Python SDK directly, pointed at Ollama's OpenAI-compatible `/v1` endpoint. Do NOT add litellm.**

Ollama exposes `http://localhost:11434/v1` as an OpenAI-compatible endpoint. The `openai` SDK accepts a `base_url` parameter:

```python
from openai import OpenAI

def build_client(cfg: LLMConfig) -> OpenAI:
    if cfg.type == "openai":
        return OpenAI(api_key=cfg.api_key or os.environ["OPENAI_API_KEY"])
    elif cfg.type == "ollama":
        return OpenAI(
            base_url=f"{cfg.endpoint}/v1",  # must include /v1
            api_key="ollama",               # required but unused
        )
    # vllm / custom: same pattern with cfg.endpoint + cfg.api_key
```

This satisfies `LLMConfig.type in {"openai", "ollama", "vllm", "custom"}` with zero additional dependencies. The `endpoint` and `api_key` fields in the existing `LLMConfig` model are exactly the right abstraction.

**Why not litellm:**
- litellm (1.83.12) is a large SDK (~50MB installed) intended for routing across 100+ providers. For two providers (OpenAI + Ollama) that share the same wire protocol, litellm's value proposition is nil.
- litellm introduces its own proxy server concept and configuration format that would conflict with the existing `LLMConfig` / `Settings` model.
- litellm's proxy mode is a separate process; adding it to an intranet Streamlit app adds operational complexity for zero benefit.
- The openai SDK already handles both cases — this is the canonical Ollama recommendation from Ollama's own documentation.

**Runtime switching:** Store the selected LLM name in `st.session_state.selected_llm` (sidebar widget). On each agent run, call `build_client(find_llm(settings, selected_llm))`. No global state mutation needed.

**Critical detail:** `base_url` must include `/v1` (e.g., `http://localhost:11434/v1`), not just the host. The openai SDK appends `/chat/completions` directly to `base_url`, so omitting `/v1` results in 404 errors.

---

### 5. Caching Strategy for 100k+ Row EAV Data

**Use `st.cache_resource` for the SQLAlchemy engine. Use `st.cache_data(ttl=300, max_entries=20)` for query results. Consider DuckDB for pivot-heavy workloads.**

**Rule:**
- `st.cache_resource`: unserializable shared objects — the `sqlalchemy.engine.Engine`. One engine per Streamlit process, shared across all user sessions and reruns. Do NOT create a new engine on every rerun.
- `st.cache_data`: serializable data — `pd.DataFrame` results from `run_query(...)`. Cached per unique call signature (query string + params). Each session gets its own copy (important for thread safety).

```python
@st.cache_resource
def get_engine(db_url: str) -> Engine:
    return create_engine(db_url, pool_pre_ping=True, pool_recycle=3600)

@st.cache_data(ttl=300, max_entries=20)
def run_query(query_hash: str, sql: str, params: tuple) -> pd.DataFrame:
    engine = get_engine(...)
    with engine.connect() as conn:
        return pd.read_sql_query(sa.text(sql), conn, params=dict(params))
```

**TTL rationale:** The `ufs_data` table is populated upstream (not by this app). A 5-minute TTL (300s) balances freshness against repeated full-table scans. Increase to 1800s if upstream updates are infrequent.

**max_entries rationale:** With 100k+ rows and multiple filter combinations, unbounded cache entries will exhaust container memory. 20 entries covers typical usage patterns for a small team.

**DuckDB for pivot workloads (optional add in a later phase):**
The DuckDB + Streamlit official guide (March 2025) demonstrates ~300ms pivot query time on 100k rows. If `pd.pivot_table` on filtered DataFrames becomes a bottleneck (perceptible lag > 1s), load the filtered result into an in-process DuckDB connection and run a PIVOT SQL query there. Cache the DuckDB connection with `@st.cache_resource` per session (not globally — DuckDB in-memory connections are not safe to share across sessions).

**What NOT to do:**
- Do NOT cache the full 100k-row unfiltered table — it will OOM a typical intranet server.
- Do NOT use Redis — adds infrastructure dependency for a team that just wants a Streamlit app on the intranet; `st.cache_data` is sufficient.
- Do NOT use `st.cache_resource` for DataFrames — it returns the same mutable object to all sessions, creating race conditions on `.pivot_table()`.

---

### 6. Excel Export

**Use `pandas.to_excel` with `openpyxl` via `io.BytesIO` + `st.download_button`. No additional wrapper library.**

```python
import io
import pandas as pd
import streamlit as st

def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
    return buf.getvalue()

st.download_button(
    label="Export Excel",
    data=to_excel_bytes(pivot_df),
    file_name="ufs_data_export.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
```

`openpyxl` is already in `requirements.txt`. The in-memory `BytesIO` pattern avoids disk writes and is safe in containers. For CSV export, use `df.to_csv(index=False).encode("utf-8")` directly — no library needed.

**What NOT to use:**
- `xlwt` — Python 2 era, does not support `.xlsx`.
- `xlsxwriter` — More features (charts, conditional formatting) but heavier. Use only if the team needs formatted Excel with charts embedded; for raw data export `openpyxl` is simpler and already installed.
- `xlrd` — Read-only; irrelevant for export.

---

### 7. Testing Stack

**Use Streamlit AppTest + pytest. No Playwright for unit/integration tests.**

```python
# tests/test_browse_page.py
from streamlit.testing.v1 import AppTest

def test_platform_picker_renders():
    at = AppTest.from_file("app/pages/browse.py")
    at.run()
    assert not at.exception
    assert len(at.multiselect) > 0  # platform picker present

def test_filter_returns_data(mock_engine):
    at = AppTest.from_file("app/pages/browse.py")
    at.session_state["selected_platforms"] = ["Samsung_S22Ultra_SM8450"]
    at.run()
    assert len(at.dataframe) > 0
```

**Rationale:**
- `AppTest` (Streamlit's native headless testing framework) runs the app without a browser, in-process, with full access to `session_state`, widget values, and rendered elements. It integrates naturally with pytest and runs in CI without Playwright's Chromium dependency.
- Use `pytest-mock` / `unittest.mock` to patch `get_engine()` (returns a mock engine) and the LLM client. This isolates UI logic from real DB/LLM calls in unit tests.
- Use real DB connections (pointing at a test schema or a fixture MySQL container) only in integration tests tagged `@pytest.mark.integration`.

**What Playwright is good for (but not needed in Phase 1):**
- End-to-end login flow via `streamlit-authenticator` (AppTest cannot simulate the browser-side cookie/session flow).
- Screenshots for regression testing of the pivot grid layout.
- Defer Playwright until the UI is stable (Phase 3+).

**What NOT to use:**
- `pytest-streamlit` — a third-party package, effectively superseded by the official `AppTest` framework since Streamlit 1.18. Do not add it.
- Selenium — same story as Playwright but worse DX.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| PydanticAI | LangChain SQLDatabaseToolkit | 50+ transitive deps, full-schema reflection on every call, hard to gate `allowed_tables` cleanly |
| PydanticAI | Vanna.ai | RAG/embedding overhead unnecessary for single known table |
| PydanticAI | LlamaIndex NLSQLTableQueryEngine | Full LlamaIndex tree for no unique benefit on single-table case |
| openai SDK (dual base_url) | litellm | 50MB library for two providers that already share the same wire protocol |
| st.dataframe + column_config | streamlit-aggrid | Solo-maintained JS component, no features needed that native st.dataframe lacks |
| pandas 3.0.2 | pandas 2.2.x | 3.0 is current stable; no reason to stay on older series; requires Python 3.11+ |
| SQLAlchemy 2.0.49 | SQLAlchemy 2.1.x | 2.1 is still in beta; use stable series |
| AppTest + pytest | Playwright | Browser-level testing not needed until auth/E2E phase |
| st.cache_data + TTL | Redis | Infrastructure overkill for intranet app; add only if multi-process deployment needed |
| openpyxl via pandas | xlsxwriter | Same job, openpyxl already installed; xlsxwriter only worth it for formatted/charted Excel |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| LangChain / LangGraph | Heavy transitive deps; full-schema DB reflection; `allowed_tables` gating is awkward | PydanticAI with `@agent.tool` |
| litellm | 50MB for 2-provider use case; conflicts with existing LLMConfig model | `openai.OpenAI(base_url=..., api_key=...)` |
| Vanna.ai | RAG + embedding store overhead for single known table; offline mode is opaque | PydanticAI structured SQL output |
| streamlit-aggrid | Solo-maintained, JS-heavy, breaks on Streamlit version bumps | `st.dataframe` with `column_config` |
| SQLAlchemy ORM | No schema to map; single read-only table | SQLAlchemy Core (`sa.text()`, `sa.select()`) |
| Full 100k-row table load | OOM risk; slow pivot in-browser | Server-side WHERE filter before `read_sql_query` |
| `st.cache_resource` for DataFrames | Returns shared mutable object; concurrent sessions corrupt each other | `st.cache_data` for DataFrames |
| `pytest-streamlit` (third-party) | Superseded by official AppTest since Streamlit 1.18 | `streamlit.testing.v1.AppTest` |
| pandas 2.x `read_sql` with text SQL | Deprecated in 2.x; raises warning in 3.x | `pd.read_sql_query(sa.text(...), conn)` |

---

## Version Compatibility Notes

| Package | Pin | Compatibility Note |
|---------|-----|--------------------|
| SQLAlchemy | `>=2.0,<2.1` | SQLAlchemy 2.1 is beta until further notice; pandas 3.x is compatible with 2.0.x |
| pandas | `>=3.0` | Requires Python >=3.11; string columns return `pd.StringDtype` by default in 3.0 — handle in Result normalization |
| streamlit | `>=1.40,<2.0` | Existing pin is fine; 1.56.0 is current stable |
| streamlit-authenticator | `>=0.3.3,<1.0` | 0.4.2 is latest; API is stable across 0.3.x → 0.4.x; do not pin to exact version |
| pydantic | `>=2.7` | v2 throughout; do not mix v1 and v2 Models |
| pydantic-ai | `>=1.0,<2.0` | V1 reached API-stable in Sep 2025; safe to depend on |
| openai | `>=1.50` | Existing pin fine; 1.78.x is current; `base_url` parameter for Ollama routing stable since 1.x |
| pymysql | `>=1.1` | 1.1.x is current stable; mysqlclient is an alternative but requires system libmysqlclient |

---

## Installation

```bash
# Core (update requirements.txt to these minimums)
pip install \
  "streamlit>=1.40,<2.0" \
  "streamlit-authenticator>=0.3.3,<1.0" \
  "sqlalchemy>=2.0,<2.1" \
  "pymysql>=1.1" \
  "pandas>=3.0" \
  "pydantic>=2.7" \
  "pydantic-ai>=1.0,<2.0" \
  "openai>=1.50" \
  "openpyxl>=3.1" \
  "plotly>=5.22" \
  "altair>=5.3" \
  "sqlparse>=0.5" \
  "pyyaml>=6.0" \
  "python-dotenv>=1.0" \
  "bcrypt>=4.2" \
  "httpx>=0.27" \
  "requests>=2.32"

# Dev / test
pip install pytest pytest-mock ruff mypy

# Optional — add only if pivot performance is a bottleneck
pip install "duckdb>=1.0"
```

---

## Scaffolding Assessment

| Item | Assessment | Action |
|------|-----------|--------|
| `requirements.txt` `pandas>=2.2` | Current stable is 3.0.2; the lower bound is fine for install but code should target 3.x idioms (use `pd.read_sql_query` + `sa.text`, handle `pd.StringDtype`) | Update lower bound to `>=3.0` after verifying nothing in scaffolding uses deprecated 2.x APIs |
| `LLMConfig.type` includes `"anthropic"` | Not needed for v1 (PROJECT.md scope is OpenAI + Ollama) | Keep in model for extensibility; just don't expose in the sidebar picker for v1 |
| `AgentConfig.model: str = ""` | Empty string means "inherit from LLMConfig.model" — correct | Document this contract explicitly in `AgentConfig` docstring |
| No agent framework in `requirements.txt` | Intentionally deferred | Add `pydantic-ai>=1.0,<2.0` |
| No LLM abstraction decision | Intentionally deferred | Use `openai` SDK directly (already in requirements) with `base_url` for Ollama — no new dependency |
| `app/adapters/` skeleton packages | Right structure | Implement `DBAdapter` wrapping `get_engine` + `run_query` with the caching decorators; implement `LLMAdapter` as the `build_client()` factory |

---

## Sources

- Streamlit 1.56.0 — https://pypi.org/project/streamlit/ (version confirmed)
- Streamlit 2026 release notes — https://docs.streamlit.io/develop/quick-reference/release-notes/2026 (column_config, selection, filter_mode)
- SQLAlchemy 2.0.49 — https://pypi.org/project/SQLAlchemy/ (version confirmed; 2.1 beta confirmed at https://www.sqlalchemy.org/blog/2026/04/16/sqlalchemy-2.1.0b2-released/)
- pandas 3.0.2 — https://pypi.org/project/pandas/ (version confirmed; 3.0 release notes at https://pandas.pydata.org/docs/whatsnew/v3.0.0.html)
- PydanticAI 1.86.0 — https://pypi.org/project/pydantic-ai/ (version confirmed; SQL gen example at https://pydantic.dev/docs/ai/examples/data-analytics/sql-gen/)
- litellm 1.83.12 — https://pypi.org/project/litellm/ (version confirmed — deliberately NOT added)
- streamlit-authenticator 0.4.2 — https://pypi.org/project/streamlit-authenticator/ (version confirmed)
- Ollama OpenAI compatibility — https://docs.ollama.com/api/openai-compatibility (base_url /v1 requirement confirmed)
- DuckDB + Streamlit — https://duckdb.org/2025/03/28/using-duckdb-in-streamlit (caching pattern, per-session connections, ~300ms on 100k rows)
- Streamlit caching — https://docs.streamlit.io/develop/concepts/architecture/caching (cache_data vs cache_resource rules confirmed)
- Streamlit AppTest — https://docs.streamlit.io/develop/concepts/app-testing (official testing framework confirmed)

---

*Stack research for: PBM2 — Streamlit EAV MySQL browser + NL-to-SQL agent*
*Researched: 2026-04-23*
