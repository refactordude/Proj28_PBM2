<!-- GSD:project-start source:PROJECT.md -->
## Project

**PBM2**

PBM2 is an internal Streamlit website where a team of non-SQL users (PMs, analysts) can browse and query a large, EAV-form MySQL parameter database (`ufs_data`) that stores UFS subsystem profiles of Android platforms. The app lets users slice, pivot, filter, visualize, and export this long-form data — and ask natural-language questions on top — without ever writing SQL or reasoning about the schema themselves.

**Core Value:** **Fast ad-hoc browsing of the parameter database.** Even if the NL layer fails, the UI must let a non-SQL user quickly find the platforms they care about, the parameters they care about, and see them in a wide-form grid they can read, compare, chart, and export. NL query rides on top of this and enhances it — it does not replace it.

### Constraints

- **Tech stack**: Streamlit + SQLAlchemy (pymysql driver) + pandas + Pydantic v2 + python-dotenv — Why: scaffolding is already in place; no reason to diverge.
- **Data**: Single-table EAV MySQL (`ufs_data`), read-only — Why: Real deployment; write path is owned by another system.
- **Scale**: ~100k+ rows across many platforms — Why: User flagged "too large"; a full dump must be pre-filtered before it hits the LLM, a chart, or an export.
- **Deployment**: Company intranet, shared team creds — Why: User selected this explicitly; no public-internet exposure is planned.
- **LLM choice**: OpenAI (cloud) + Ollama (local), user-switchable at runtime — Why: Lets users pick cloud for quality vs local for data-sensitivity situationally.
- **Result heterogeneity**: Type coercion is lazy and per-query, never global — Why: Same `Item` legitimately appears hex on one platform and decimal on another.
- **Security**: Readonly DB user is the primary SQL-injection backstop for the NL agent — Why: Even if the LLM generates harmful SQL, the DB can't execute writes.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Verdict on Existing Scaffolding
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
## Sub-Question Answers
### 1. Streamlit Data Display (2026)
- `st.dataframe` in Streamlit 1.56.0 supports programmatic selection (`selection` parameter), always-visible column visibility toggle, `alignment` in column config, and `AudioColumn`/`VideoColumn` — sufficient for the EAV pivot grid.
- `column_config.NumberColumn`, `column_config.TextColumn`, and `column_config.CheckboxColumn` provide per-column type hints without requiring a separate library.
- AgGrid (`streamlit-aggrid`) is community-maintained by a solo developer; as of 2026 it is still alive but introduces a heavy JS dependency. For a read-only pivot display there is no feature AgGrid provides that `st.dataframe` + `column_config` does not.
- `st.data_editor` is for editable tables. Because the DB is strictly read-only, `st.data_editor` is the wrong primitive (it signals editability to users and returns mutation callbacks the app doesn't need).
### 2. SQL Query Abstraction
# engine created once at startup, cached with st.cache_resource
# per-query
- `pd.read_sql_query` with `sa.text(...)` and explicit `params` is the idiomatic pandas 3.x / SQLAlchemy 2.x pairing. The raw string form (`pd.read_sql`) was deprecated for text SQL in pandas 2.x; `read_sql_query` is the correct function.
- SQLAlchemy ORM is overkill — there is one table, no relationships, no ORM models to define.
- SQLAlchemy Core (not ORM) is the right level: use `engine.connect()` as context manager, `sa.text()` for parameterized queries, and `sa.select()` for programmatic query building when filters accumulate.
- `pool_pre_ping=True` is mandatory for MySQL: it tests connections on checkout, preventing "MySQL server has gone away" errors that appear after idle periods in an intranet app.
- `pool_recycle=3600` prevents connections older than 1 hour from being reused (MySQL's default `wait_timeout` is 8 hours but intranet servers often set it lower).
- Do NOT use SQLAlchemy 2.1.x yet — it is in beta (2.1.0b2 as of 2026-04-16). Pin to `sqlalchemy>=2.0,<2.1` until 2.1 reaches stable.
- Raw `pymysql.connect()` without SQLAlchemy — loses connection pooling, parameter escaping, and pandas integration.
- SQLAlchemy ORM — unnecessary mapping overhead for a single-table read-only workload.
### 3. NL-to-SQL Agent Framework
- The agent's `result_type` can be a Pydantic union: `SQLResult(query: str, explanation: str) | ClarificationNeeded(message: str)` — structured output prevents the LLM returning prose when a query is needed.
- `@agent.tool` wraps `run_sql(sql: str) -> str` — the agent calls this once and the tool enforces `allowed_tables`, `row_cap`, and `timeout_s` from `AgentConfig`.
- Native support for OpenAI and Ollama (via `openai` client with custom `base_url`) — no adapter shim needed.
- Already aligns with the Pydantic v2 used throughout the codebase (`DatabaseConfig`, `LLMConfig`, `AgentConfig` are all Pydantic models).
- Minimal dependency surface: does not drag in LangChain's 50+ transitive dependencies.
- LangChain's `SQLDatabaseToolkit` reflects the full schema into the prompt on every call — for a single-table app this is wasteful and adds context token overhead against the `max_context_tokens=30000` limit.
- LangChain requires `langchain-community` + `langchain-core` + `langchain` — 3 packages with fast-moving APIs and frequent breaking changes between minor versions.
- The `SQLDatabaseChain` / `create_sql_agent` pattern exposes `execute_query` tools that are harder to gate with `allowed_tables` without subclassing. The scaffolded `AgentConfig.allowed_tables` is a natural fit for PydanticAI's `RunContext` dependency injection, not for LangChain's callback-based safety checks.
- Vanna is a RAG-over-DDL system designed for multi-table databases where the agent needs to retrieve relevant schema snippets. With a single known table (`ufs_data`) and a static schema, the full RAG setup (embedding store, vector DB, training loop) is architectural overhead that adds no accuracy benefit.
- Vanna's offline/local mode is opaque; the dual OpenAI+Ollama switchability required here is cleaner to implement directly.
- Adds the full LlamaIndex dependency tree without unique benefits over PydanticAI for a single-table case.
- Valid option but means writing the agent loop, retry logic, structured output parsing, and tool dispatch by hand — exactly what PydanticAI provides. For a greenfield project, pick the framework.
### 4. LLM Abstraction (OpenAI + Ollama Dual Backend)
- litellm (1.83.12) is a large SDK (~50MB installed) intended for routing across 100+ providers. For two providers (OpenAI + Ollama) that share the same wire protocol, litellm's value proposition is nil.
- litellm introduces its own proxy server concept and configuration format that would conflict with the existing `LLMConfig` / `Settings` model.
- litellm's proxy mode is a separate process; adding it to an intranet Streamlit app adds operational complexity for zero benefit.
- The openai SDK already handles both cases — this is the canonical Ollama recommendation from Ollama's own documentation.
### 5. Caching Strategy for 100k+ Row EAV Data
- `st.cache_resource`: unserializable shared objects — the `sqlalchemy.engine.Engine`. One engine per Streamlit process, shared across all user sessions and reruns. Do NOT create a new engine on every rerun.
- `st.cache_data`: serializable data — `pd.DataFrame` results from `run_query(...)`. Cached per unique call signature (query string + params). Each session gets its own copy (important for thread safety).
- Do NOT cache the full 100k-row unfiltered table — it will OOM a typical intranet server.
- Do NOT use Redis — adds infrastructure dependency for a team that just wants a Streamlit app on the intranet; `st.cache_data` is sufficient.
- Do NOT use `st.cache_resource` for DataFrames — it returns the same mutable object to all sessions, creating race conditions on `.pivot_table()`.
### 6. Excel Export
- `xlwt` — Python 2 era, does not support `.xlsx`.
- `xlsxwriter` — More features (charts, conditional formatting) but heavier. Use only if the team needs formatted Excel with charts embedded; for raw data export `openpyxl` is simpler and already installed.
- `xlrd` — Read-only; irrelevant for export.
### 7. Testing Stack
# tests/test_browse_page.py
- `AppTest` (Streamlit's native headless testing framework) runs the app without a browser, in-process, with full access to `session_state`, widget values, and rendered elements. It integrates naturally with pytest and runs in CI without Playwright's Chromium dependency.
- Use `pytest-mock` / `unittest.mock` to patch `get_engine()` (returns a mock engine) and the LLM client. This isolates UI logic from real DB/LLM calls in unit tests.
- Use real DB connections (pointing at a test schema or a fixture MySQL container) only in integration tests tagged `@pytest.mark.integration`.
- End-to-end login flow via `streamlit-authenticator` (AppTest cannot simulate the browser-side cookie/session flow).
- Screenshots for regression testing of the pivot grid layout.
- Defer Playwright until the UI is stable (Phase 3+).
- `pytest-streamlit` — a third-party package, effectively superseded by the official `AppTest` framework since Streamlit 1.18. Do not add it.
- Selenium — same story as Playwright but worse DX.
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
## Installation
# Core (update requirements.txt to these minimums)
# Dev / test
# Optional — add only if pivot performance is a bottleneck
## Scaffolding Assessment
| Item | Assessment | Action |
|------|-----------|--------|
| `requirements.txt` `pandas>=2.2` | Current stable is 3.0.2; the lower bound is fine for install but code should target 3.x idioms (use `pd.read_sql_query` + `sa.text`, handle `pd.StringDtype`) | Update lower bound to `>=3.0` after verifying nothing in scaffolding uses deprecated 2.x APIs |
| `LLMConfig.type` includes `"anthropic"` | Not needed for v1 (PROJECT.md scope is OpenAI + Ollama) | Keep in model for extensibility; just don't expose in the sidebar picker for v1 |
| `AgentConfig.model: str = ""` | Empty string means "inherit from LLMConfig.model" — correct | Document this contract explicitly in `AgentConfig` docstring |
| No agent framework in `requirements.txt` | Intentionally deferred | Add `pydantic-ai>=1.0,<2.0` |
| No LLM abstraction decision | Intentionally deferred | Use `openai` SDK directly (already in requirements) with `base_url` for Ollama — no new dependency |
| `app/adapters/` skeleton packages | Right structure | Implement `DBAdapter` wrapping `get_engine` + `run_query` with the caching decorators; implement `LLMAdapter` as the `build_client()` factory |
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
