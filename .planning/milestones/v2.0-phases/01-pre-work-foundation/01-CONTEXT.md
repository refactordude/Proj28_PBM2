# Phase 1: Pre-work + Foundation - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning
**Mode:** Infrastructure phase — smart discuss skipped (per autonomous workflow rule: goal is pure plumbing with no user-facing UI)

<domain>
## Phase Boundary

The FastAPI v2.0 app starts cleanly alongside v1.0 Streamlit, serves the Bootstrap shell at `/`, and shares v1.0 service code without Streamlit coupling. All 171 v1.0 tests still pass. No visible UI features — only the structural plumbing every subsequent phase depends on.

Delivers:
- `app_v2/` package (sibling to `app/`) with FastAPI entrypoint, lifespan, routing skeleton, Jinja2 template setup
- `base.html` Bootstrap shell with horizontal top-nav tabs (Overview / Browse / Ask), global HTMX error handler (`htmx:beforeSwap`), 404/500 pages
- Static assets vendored: Bootstrap 5.3.8 + HTMX 2.0.10 + bootstrap-icons 1.13.1 under `app_v2/static/vendor/`
- Pre-work on v1.0 code (must not break v1.0 tests):
  - `app/services/ufs_service.py`: extract `*_core()` pure functions from the `@st.cache_data` wrappers (list_platforms, list_parameters, fetch_cells, pivot_to_wide). v1.0 wrappers delegate to `_core`. v2.0 imports `_core` directly.
  - `app/core/agent/nl_service.py`: extract SAFE-02..06 harness from v1.0 `app/pages/ask.py` into a single `run_nl_query(question, agent, deps) -> NLResult` entrypoint. v1.0 `ask.py` refactored to call `nl_service`.
- `app_v2/services/cache.py`: `cachetools.TTLCache` + `threading.Lock()` wrappers for the `*_core()` functions.
- Dependencies appended to shared `requirements.txt`: fastapi>=0.136,<0.137, uvicorn[standard]>=0.32, jinja2>=3.1, jinja2-fragments>=1.3, python-multipart, markdown-it-py[plugins]>=3.0, cachetools>=7.0,<8.0, pydantic-settings>=2.14.

Scope out:
- NO feature UI (Overview list, Content pages, AI Summary, Browse grid, Ask NL flow) — those come in phases 2-5.
- NO auth — continues D-04 deferral.
- NO removal of v1.0 Streamlit code — parallel operation is the core contract.

</domain>

<decisions>
## Implementation Decisions

### Locked by research / roadmap
- **Stack**: FastAPI 0.136.x, Bootstrap 5.3.8 (vendored), HTMX 2.0.10 (vendored, NOT 4.0 alpha), Jinja2, jinja2-fragments >=1.3, markdown-it-py >=3.0 (Phase 3 actually renders but dep is added now), cachetools >=7.0,<8.0, pydantic-settings >=2.14, uvicorn[standard] >=0.32. All pinned per research/STACK.md.
- **Directory**: `app_v2/` at repo root, sibling to `app/`.
- **Template engine**: Jinja2 via `fastapi.templating.Jinja2Templates` wrapped with `jinja2_fragments.fastapi.Jinja2Blocks` for same-file full-page + fragment rendering.
- **TemplateResponse signature (Starlette 1.0 breaking change)**: `TemplateResponse(request, name, context_dict)` — request is the FIRST arg. Enforce from the first template written; not just `TemplateResponse(name, context)`.
- **Sync-def route convention**: All DB-touching routes are `def`, not `async def` (sync SQLAlchemy would block the event loop inside `async def`; `def` routes are dispatched to the threadpool by FastAPI).
- **HTMX error handling**: `base.html` includes a global `htmx:beforeSwap` event listener that allows 4xx/5xx responses to swap into an error container (otherwise HTMX silently drops them).
- **Cache thread safety**: Every `cachetools.TTLCache` instance is paired with `threading.Lock()` since FastAPI `def` routes run in a threadpool. Cache key lambdas exclude unhashable adapter objects — use `db_name: str`.

### v1.0 refactor contract (INFRA-06 + INFRA-07)
- **ufs_service refactor strategy** (from research/ARCHITECTURE.md option 1): extract the pure SQL/pandas body of `list_platforms`, `list_parameters`, `fetch_cells`, `pivot_to_wide` into co-located `*_core()` functions in the SAME file. Existing `@st.cache_data` wrappers delegate to `_core()` so v1.0 public API stays unchanged. This is the ONLY v1.0 file that changes for INFRA-06. v2.0 imports `_core()` directly and wraps them with its own `cachetools` layer (INFRA-08).
- **nl_service extraction strategy**: create new file `app/core/agent/nl_service.py` with `run_nl_query(question: str, agent: Agent, deps: AgentDeps) -> NLResult`. Move the step-cap enforcement, scrub-paths invocation, `<db_data>` wrapping orchestration from `app/pages/ask.py` into this function. v1.0 `ask.py` updated to `from app.core.agent.nl_service import run_nl_query` and call it. Existing v1.0 tests (including `tests/pages/test_ask_page.py`) must still pass unchanged.
- **Regression bar**: After BOTH refactors, `pytest tests/` exits 0 with all 171 tests green. This is Success Criterion #2 of the phase.

### FastAPI layout (from research/ARCHITECTURE.md)
- Entry: `app_v2/main.py` constructs `app = FastAPI(lifespan=lifespan, title="PBM2 v2.0")`, mounts StaticFiles at `/static`, registers routers from `app_v2/routers/`, adds exception handlers for 404/500.
- Lifespan initializes `app.state.db` (MySQLAdapter), `app.state.settings` (pydantic Settings), `app.state.agent_registry = {}` (lazy per-backend — populated in Phase 3/5).
- DI pattern: `get_db(request: Request) -> DBAdapter = request.app.state.db` via FastAPI `Depends(get_db)`. Same for settings and agent registry.
- Routers: one file per tab under `app_v2/routers/` (`root.py` for `/`, `htmx.py` for HTMX partial endpoints — Phase 2+ adds feature-specific routers).
- Templates: `app_v2/templates/` with `base.html` + feature subfolders added in Phase 2+. `app_v2/templates/base.html` is the ONLY template Phase 1 ships.
- Static: `app_v2/static/vendor/` for third-party assets, `app_v2/static/css/` for project custom CSS (minimal — rely on Bootstrap), `app_v2/static/js/` for htmx-extensions and the `htmx:beforeSwap` handler as a separate JS file.

### Deferred to phase 2+
- Actual route logic (GET /, GET /browse, GET /ask beyond a stub that renders base.html + tab hint)
- Content-page storage, markdown rendering (Phase 3)
- Cache layer actually being exercised (Phase 2)
- Agent registry population (Phase 3/5)

### Claude's Discretion
- Exact filenames for the HTMX beforeSwap JS handler (`app_v2/static/js/htmx-error-handler.js` suggested)
- Whether to split `requirements.txt` into a dev/test/runtime tier (not required — single file is fine)
- Whether `app_v2/` top-level `__init__.py` should re-export key public objects (not required — routers and main.py know paths)
- Exact StaticFiles mount path (`/static` standard)
- Exact test layout for v2.0 tests (suggest `tests/v2/` sibling to existing `tests/`)
- Whether `config.json` workflow.use_worktrees setting matters for execution (sequential mode is fine)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (v1.0 modules, framework-agnostic — import as-is)
- `app/core/config.py`: `DatabaseConfig`, `LLMConfig`, `AgentConfig`, `Settings`, `load_settings()`, `save_settings()`. Pydantic v2 models. Used verbatim by v2.0.
- `app/core/agent/nl_agent.py`: `build_agent(model)`, `SQLResult`, `ClarificationNeeded`, `AgentDeps`, `AgentRunFailure`, `run_agent()`. Framework-agnostic. Used by v2.0 Phase 5.
- `app/adapters/llm/pydantic_model.py`: `build_pydantic_model(cfg)` factory → `OpenAIChatModel` or `OllamaModel`. Used by v2.0 Phase 3 (AI Summary) and Phase 5 (Ask).
- `app/adapters/db/mysql.py`: `MySQLAdapter` with `pool_pre_ping=True`, `pool_recycle=3600`, `_get_engine()`. Used by both apps.
- `app/services/result_normalizer.py`: `normalize()`, `try_numeric()`, `classify()`. Used by Phase 4 (Browse).
- `app/services/sql_validator.py`, `sql_limiter.py`, `path_scrubber.py`: pure safety functions. Used by nl_service.py in Phase 1, consumed by Phase 5.

### Files that MUST be modified (INFRA-06, INFRA-07)
- `app/services/ufs_service.py`: extract `*_core()` functions; wrapper pattern.
- `app/pages/ask.py`: refactor to call `nl_service.run_nl_query()` instead of inlining the safety harness.

### New Files (v2.0 greenfield)
- `app_v2/__init__.py`
- `app_v2/main.py` (FastAPI app + lifespan)
- `app_v2/routers/__init__.py`
- `app_v2/routers/root.py` (GET / → redirect to /?tab=overview or render base.html with "Phase 2 coming soon")
- `app_v2/services/__init__.py`
- `app_v2/services/cache.py` (TTLCache wrappers)
- `app_v2/templates/base.html` (Bootstrap + HTMX shell)
- `app_v2/templates/404.html`, `app_v2/templates/500.html`
- `app_v2/static/vendor/bootstrap.min.css`, `bootstrap.bundle.min.js`, `htmx.min.js`, `bootstrap-icons.css`, `bootstrap-icons/*.woff2`
- `app_v2/static/js/htmx-error-handler.js`
- `app/core/agent/nl_service.py` (new — houses the extracted harness)
- `tests/v2/__init__.py`
- `tests/v2/test_main.py` (FastAPI TestClient smoke test — GET / returns 200 with Bootstrap markup)
- `tests/v2/test_cache.py` (TTLCache behavior)

### Integration Points
- v1.0 Streamlit app stays running on its own port (default 8501); v2.0 runs on port 8000. Separate processes, separate MySQL connection pools — POOL_SIZE should stay small (2) + overflow (3) on each to avoid exhausting MySQL `max_connections`.
- Both apps read the same `config/settings.yaml`; neither writes during Phase 1 (no Settings UI yet in v2.0).
- `app_v2/services/cache.py` imports `list_platforms_core` etc. from `app/services/ufs_service.py` — this cross-package import is expected and safe because the modules are framework-agnostic post-refactor.

</code_context>

<specifics>
## Specific Ideas

- The `htmx:beforeSwap` handler should target an error container div near the top of `base.html` body (e.g., `<div id="htmx-error-container"></div>`). Handler sets `event.detail.shouldSwap = true` for 4xx/5xx responses and swaps the response body there.
- Bootstrap vendoring: download the official minified bundle from getbootstrap.com/jsDelivr and place under `app_v2/static/vendor/bootstrap/`. Pin exact version (5.3.8) in a `VERSIONS.txt` in that dir for auditability.
- HTMX vendoring: download `htmx.min.js` (2.0.10) and `htmx.js.map`. Include in `app_v2/static/vendor/htmx/`.
- Bootstrap Icons: `bootstrap-icons.css` + the fonts subdir. Used for nav tab icons (`bi-list-ul` Overview, `bi-table` Browse, `bi-chat-dots` Ask) and small UI affordances later.
- `lifespan` uses `@asynccontextmanager` but the body is synchronous code — this is fine; FastAPI awaits the enter/exit but the body of the context manager itself is sync.
- TestClient smoke test should assert: response 200, content-type text/html, body contains `<nav class="nav nav-tabs"`, body contains `htmx.min.js`.
- For cache.py, test that calling the wrapper twice in quick succession returns the same DataFrame object (cache hit); that changing the `db_name` kwarg produces a different cache entry; that past-TTL invalidates.

</specifics>

<deferred>
## Deferred Ideas

- **CSRF protection** — intranet + no auth, same trust model as v1.0. Revisit when auth returns.
- **Sessions / cookies** — introduced in Phase 3 for LLM backend preference; Phase 1 does not set cookies.
- **Structured JSON logging** — nice-to-have for intranet ops; not in scope.
- **OpenTelemetry / metrics endpoint** — same reasoning; defer.
- **HTMX extensions (json-enc, loading-states)** — none needed for Phase 1; Phase 3+ may add some.
- **Separate requirements-v2.txt** — user explicitly opted against this during discuss; shared requirements.txt.
- **Dev-only reload configuration (uvicorn --reload)** — leave to dev-environment docs, not committed config.
- **Error telemetry (Sentry, Rollbar)** — out of scope for intranet app.

</deferred>

---

*Phase: 01-pre-work-foundation*
*Context gathered: 2026-04-25 via autonomous workflow (infrastructure phase — smart discuss skipped)*
