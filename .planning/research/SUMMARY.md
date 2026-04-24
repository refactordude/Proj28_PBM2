# Project Research Summary

**Project:** PBM2 v2.0 Bootstrap Shell
**Domain:** FastAPI + Bootstrap 5 + HTMX server-rendered intranet data browser (parallel rewrite of Streamlit v1.0)
**Researched:** 2026-04-23
**Confidence:** HIGH (all four files agree on technology choices; versions verified against PyPI and official docs)

---

## Executive Summary

PBM2 v2.0 is a parallel rewrite of a working Streamlit EAV-MySQL browser onto a FastAPI + Bootstrap 5 + HTMX stack. The v1.0 app (3080 LOC, 171 passing tests) stays archived and runnable throughout; v2.0 lives in a new `app_v2/` sibling directory and shares v1.0's framework-agnostic service, adapter, and core layers by import only — no code is copied. The new shell introduces a horizontal tab layout (Overview / Browse / Ask), a curated platform-entity overview with per-entity markdown content pages, in-place AI Summary via HTMX, and faceted filters, while carrying the v1.0 pivot grid and NL agent forward under the new UI.

The recommended approach is hypermedia-first: Jinja2 templates rendered server-side, HTMX driving all partial updates, Bootstrap 5 providing the visual shell and tab state, and `jinja2-fragments` enabling single-template-file block renders so full-page and HTMX fragment routes share one source of truth. All DB-touching routes use synchronous `def` handlers (FastAPI dispatches them to a threadpool automatically) because the underlying SQLAlchemy stack is synchronous and an `async def` + sync-DB pairing would block the event loop. Static assets (Bootstrap, HTMX) are vendored into `app_v2/static/vendor/` for intranet deployments that cannot reach jsDelivr.

Two pre-work items are non-negotiable before any v2.0 route can be written. First, `ufs_service.py` must have its `@st.cache_data` decorators extracted into bare `*_core()` functions (the decorated wrappers delegate to them, preserving v1.0 behavior); otherwise importing the module in a FastAPI process raises `NoSessionContext` at startup — the app cannot start. Second, the v1.0 NL safety harness (SAFE-02..06) currently lives in `ask_page.py`; it must be extracted to a framework-agnostic `nl_service.py` before the v2.0 Ask route is written, or the harness is silently bypassed. Both extractions touch only `app/` (v1.0) code and must be verified with the existing 171-test suite before any `app_v2/` code is committed.

---

## Key Findings

### Recommended Stack

v2.0 adds five new PyPI packages on top of the locked v1.0 stack: `fastapi[standard]>=0.136,<1.0` (ASGI framework + Jinja2 + python-multipart), `uvicorn>=0.46,<1.0` (ASGI server), `pydantic-settings>=2.14,<3.0` (replaces `@st.cache_resource` for the Settings singleton via `@lru_cache` + `Depends(get_settings)`), `cachetools>=7.0,<8.0` (replaces `@st.cache_data` via `TTLCache` + `threading.Lock()`), `markdown-it-py[linkify,plugins]>=4.0,<5.0` (CommonMark renderer for content pages), and `jinja2-fragments>=1.3` (block-level template rendering for HTMX partials). Bootstrap 5.3.8, Bootstrap Icons 1.13.1, and HTMX 2.0.10 are served from vendored files in `app_v2/static/vendor/` — no npm, no build step.

HTMX must be pinned at **2.x** (specifically 2.0.10). HTMX 4.0 entered alpha on 2026-04-09 with breaking changes in prop inheritance and history handling; it will not reach stable until early 2027. All required interactions (tab swap, filter swap, in-place AI Summary, content CRUD, filter debounce) map cleanly onto HTMX 2.x core attributes with no extensions needed.

**Core technologies:**
- FastAPI 0.136.1: ASGI framework — ships Starlette 1.0; `fastapi[standard]` pulls Jinja2 and python-multipart
- Starlette 1.0.0 (bundled): `TemplateResponse(request, name, context)` — `request` is first positional arg, NOT inside context dict; old form raises `TypeError` at runtime
- uvicorn 0.46.0: dev server (`--reload`) and production ASGI worker (behind gunicorn for multi-worker intranet)
- pydantic-settings 2.14.0: `BaseSettings` + `@lru_cache` replaces `@st.cache_resource` for settings; NOT included in `pydantic>=2.7` — must be added explicitly
- cachetools 7.0.6 + threading.Lock: TTL cache replacing `@st.cache_data`; thread-unsafe without lock
- markdown-it-py 4.0.0: **must use `MarkdownIt("js-default")` not `MarkdownIt()`** (default has `html=True`, enabling XSS via raw HTML passthrough)
- jinja2-fragments: `Jinja2Blocks` drop-in for `Jinja2Templates` adding `block_name=` parameter; single template file serves both full-page and fragment responses
- HTMX 2.0.10 (vendor): all interactions use core `hx-get/post/delete/target/swap/trigger/indicator/disabled-elt`; no extensions required
- Bootstrap 5.3.8 (vendor): tab state via `data-bs-toggle="tab"` + Bootstrap JS; no Alpine.js or custom JS framework
- Plotly (carried from v1.0): `fig.to_html(full_html=False, include_plotlyjs="cdn")` produces HTMX-injectable fragments

### Expected Features

**Must have (v2.0 launch blockers):**
- Horizontal tab nav (Overview / Browse / Ask) with `hx-push-url="/app?tab=<name>"` deep-link; no hash routing
- Overview: add platform via typeahead, remove platform, persist to `config/overview.yaml`
- Entity row: Brand badge | PLATFORM_ID title | SoC/Year/Notes badges | AI Summary / Edit / Remove actions
- Faceted filters: Brand, SoC, "Has notes" toggle; HTMX-swapped (`hx-trigger="change"`, `hx-include="[data-filter]"`)
- Content page CRUD: Add/Edit/Save/Delete via HTMX forms; `markdown-it-py` rendering; atomic file writes
- AI Summary: `hx-post` + `hx-indicator` + `hx-disabled-elt="this"`; in-place swap; error state as HTML fragment
- Browse tab pivot grid: port of v1.0 (Bootstrap table, same row/col caps, Excel/CSV export)
- Ask tab NL agent: port of v1.0, all routes call `nl_service.run_nl_query()` (SAFE-02..06 guaranteed)
- `ufs_service.py` refactor: extract `*_core()` functions (Phase 0 gate)
- `nl_service.py` extraction of safety harness (Phase 0 gate)
- All empty states: five distinct surfaces (overview empty, filter zero-results, no content, summary missing content, summary LLM error)
- Global `htmx:beforeSwap` error handler in `base.html` enabling 4xx/5xx swaps

**Should have (add after v2.0 validation):**
- Year filter derived from SoC lookup table (SM8450 → 2022)
- Session-level AI Summary cache with "Regenerate" + "generated N seconds ago"
- Preview tab in content editor (Bootstrap tabs: Write / Preview via `hx-post="/content/preview"`)
- URL round-trip for filter state (`hx-push-url="true"` on filter requests)
- Text search over entity names with `hx-trigger="keyup changed delay:300ms"` debounce

**Defer to v2.1+:**
- Drag-to-reorder entity list (SortableJS, high complexity)
- SSE streaming for AI Summary (only if LLM latency consistently > 10s)
- Rich WYSIWYG editor / EasyMDE
- Per-user curated lists (requires auth, deferred)

### Architecture Approach

`app_v2/` is a sibling to `app/` (v1.0 stays untouched except ufs_service refactor). FastAPI uses a `lifespan()` async context manager to initialize shared singletons (MySQLAdapter, TTLCache, agent registry) once at startup, stored in `app.state`. Routes declare `Depends(get_db)` and `Depends(get_settings)`. Router files split into `app_v2/routers/` (full-page `TemplateResponse`) and `app_v2/routers/htmx/` (fragment routes with `block_name=` via `jinja2-fragments`). A separate `requirements-v2.txt` adds only new packages; both files install into the same venv.

**Major components:**
1. `app_v2/main.py` — FastAPI app factory; lifespan, StaticFiles mount, router registration
2. `app_v2/dependencies.py` — `get_db()`, `get_settings()`, `get_agent()` (lazy per-backend, `threading.Lock`-protected)
3. `app_v2/routers/` — full-page routes for `/`, `/browse`, `/ask`, `/platforms/{id}`, `/settings`
4. `app_v2/routers/htmx/` — fragment routes for filter, summary, content CRUD, browse results, ask result
5. `app_v2/templates/base.html` — Bootstrap shell, nav tabs, HTMX script, global `htmx:beforeSwap` handler
6. `app_v2/services/cache.py` — `TTLCache` + `threading.Lock()` wrappers; imports `*_core()` from `app/services/ufs_service`
7. `app_v2/services/content_service.py` — atomic file r/w; regex + `Path.resolve()` path validation
8. `app_v2/services/overview_store.py` — YAML r/w; atomic write
9. `app/services/ufs_service.py` (MODIFIED) — `*_core()` functions extracted; `@st.cache_data` wrappers delegate; v1.0 API unchanged
10. `app/services/nl_service.py` (NEW) — `run_nl_query()` with full SAFE-02..06 harness; called by both v1.0 and v2.0

### Critical Pitfalls

1. **`ufs_service.py` Streamlit coupling** — `import streamlit as st` at module level raises `NoSessionContext` in a FastAPI process, crashing startup. Must extract `*_core()` functions before any `app_v2/` code exists. Phase 0 gate — not optional.

2. **NL safety harness not wired to v2.0** — SAFE-02..06 guards live in `app/pages/ask_page.py`, not in `nl_agent.py`. Importing `agent.run()` directly bypasses all SQL injection, DML generation, and data-leakage protections. Must extract to `nl_service.py`. Phase 0 gate — not optional.

3. **markdown-it-py XSS via default preset** — `MarkdownIt()` default has `html=True`; a `<script>` tag in a user-edited content page executes in every browser that views it. Use `MarkdownIt("js-default")` always. Single constructor argument; zero-cost fix. Intranet XSS can pivot to internal services.

4. **Starlette 1.0 `TemplateResponse` breaking change** — `TemplateResponse("template.html", {"request": request})` raises `TypeError` in Starlette 1.0. Correct form: `TemplateResponse(request, "template.html", context)`. Enforce from the first template written — no backwards-compat shim exists.

5. **HTMX silently discards 4xx/5xx** — FastAPI 422 validation errors, 400s, and 500s are ignored by HTMX; spinner disappears, page shows nothing. Fix: global `htmx:beforeSwap` handler in `base.html` setting `evt.detail.shouldSwap = true` for `xhr.status >= 400`. Must be in `base.html` before any forms are built.

6. **`async def` route + sync SQLAlchemy** — Calling `pd.read_sql_query` inside `async def` blocks the entire event loop. All DB-touching routes must be plain `def`; FastAPI dispatches them to a threadpool. Hard convention from Phase 1.

7. **Path traversal via `PLATFORM_ID`** — `platform_id` is HTTP input, not a DB value. Crafted `../../config/settings.yaml` bypasses naive file path construction. Fix: `Path(..., pattern=r'^[A-Za-z0-9_\-]{1,128}$')` + `Path.resolve()` prefix assertion in `content_service._validated_path()`.

8. **`cachetools.TTLCache` without lock** — Concurrent FastAPI threadpool calls cause `RuntimeError` during cache eviction. Every `TTLCache` must have a `threading.Lock()` in `@cached(lock=...)`. Cache key lambda must exclude the unhashable `db` adapter object.

---

## Implications for Roadmap

Based on combined research, the build order is strictly dependency-driven. Two pre-work gates (Phase 0) must clear before any `app_v2/` code is written.

### Phase 0: Pre-Work Gate (v1.0 surgery — prerequisite for all phases)

**Rationale:** Both modifications are in `app/` (v1.0) code. They must pass the existing 171-test suite before any `app_v2/` code exists. Failing to complete them first means either the v2.0 app cannot start (ufs_service coupling) or the v2.0 Ask tab ships without security controls (safety harness bypass). These are not parallelizable with Phase 1.

**Delivers:**
- `app/services/ufs_service.py` — `list_platforms_core()`, `list_parameters_core()`, `fetch_cells_core()` extracted; `@st.cache_data` wrappers delegate; all 171 tests still pass
- `app/services/nl_service.py` (NEW) — `run_nl_query()` with SAFE-02..06 harness; both `ask_page.py` (v1.0) and v2.0 Ask route call this

**Verification gate:** `pytest` 171/171 pass; `python -c "import app.services.ufs_service"` in a non-Streamlit process raises no exception.

**Avoids:** Pitfalls 1 (Streamlit coupling crash) and 2 (safety harness bypass)

### Phase 1: Foundation Shell (prerequisite for Phases 2–6)

**Rationale:** Bootstrap shell, static assets, lifespan wiring, `base.html` with error handling, and routing conventions must exist before any feature routes are written. Every subsequent phase extends `base.html` and inherits the `htmx:beforeSwap` handler, `TemplateResponse(request, ...)` signature, and `def`-route convention. Retrofitting these into existing routes is costly and error-prone.

**Delivers:**
- `requirements-v2.txt` + `v2.py` entrypoint
- `app_v2/main.py` with `lifespan()`, StaticFiles mount
- `app_v2/dependencies.py` with `get_db()`, `get_settings()`
- `app_v2/static/vendor/` with Bootstrap 5.3.8, Bootstrap Icons 1.13.1, HTMX 2.0.10
- `app_v2/templates/base.html` — Bootstrap shell, nav tabs, HTMX script, global `htmx:beforeSwap` error handler
- `app_v2/services/cache.py` — `TTLCache` + `threading.Lock()` wrappers
- `app_v2/services/content_service.py` — regex + `Path.resolve()` validation, atomic write
- `app_v2/services/overview_store.py` — YAML r/w, atomic write
- Verified: `GET /` returns HTTP 200 with Bootstrap nav; no Streamlit import errors

**Enforces:** `TemplateResponse(request, name, context)` signature; `def` routes for all DB-touching handlers; `MarkdownIt("js-default")`; `pool_size=2, max_overflow=3` during parallel deployment

**Avoids:** Pitfalls 3 (Starlette TemplateResponse), 4 (async def + sync DB), 5 (HTMX 4xx silenced), 7 (TTLCache thread safety), 8 (path traversal)

### Phase 2: Overview Tab + Faceted Filters

**Rationale:** The Overview tab is the primary v2.0 differentiating feature. It exercises the full HTMX filter-swap pattern and `jinja2-fragments` block render with simpler data (platform list) before the more complex content page CRUD and LLM integration in Phase 3. De-risking HTMX patterns here prevents compounding errors in later phases.

**Delivers:**
- `app_v2/routers/overview.py` + `app_v2/routers/htmx/overview.py`
- `app_v2/templates/overview.html` + `partials/overview_list.html` using `jinja2-fragments` `{% block overview_list %}`
- PLATFORM_ID parser (`parse_platform_id()`) extracting Brand, SoC from `Brand_Model_SoCID`
- Entity row layout with Brand/SoC/Year/Notes badges; five distinct empty states
- Brand + SoC + "Has notes" filters with `hx-trigger="change"`, `hx-include="[data-filter]"`
- `hx-push-url="/app?tab=overview"` deep-link pattern established here

**Uses:** `jinja2-fragments` `Jinja2Blocks`, Bootstrap `data-bs-toggle="tab"` + `hx-get` tab pattern

**Avoids:** Pitfall 6 (HTMX OOB silent ID mismatch — OOB targets kept in persistent shell, not tab content)

### Phase 3: Content Pages + AI Summary

**Rationale:** Content pages must exist before AI Summary has content to summarize. The LLM integration, atomic file writes, and markdown rendering are interdependent. The LLM backend cookie (replacing `st.session_state`) and `get_agent()` factory established here are reused by Phase 5 (Ask tab).

**Delivers:**
- `app_v2/routers/platforms.py` + `app_v2/routers/htmx/platforms.py`
- `app_v2/templates/platform_page.html` + `partials/ai_summary.html`
- markdown-it-py rendering via `MarkdownIt("js-default")`
- AI Summary: `hx-post`, `hx-indicator`, `hx-disabled-elt="this"`, 30s timeout, error fragment
- Edit/Save/Cancel in-place HTMX swap; explicit Save (no autosave)
- LLM backend preference in `SameSite=Lax` cookie (replaces `st.session_state["llm_backend"]`)
- `get_agent()` lazy singleton factory with `threading.Lock`

**Avoids:** Pitfalls 1 (markdown XSS), 3 (path traversal), 9 (double submit on Summary), 12 (session state replacement)

### Phase 4: Browse Tab Port

**Rationale:** Browse is the highest-value v1.0 feature. It can be developed in parallel with Phase 3 once Phase 0 and Phase 1 are complete, because it depends only on `cache.py` (established in Phase 1) and the v1.0 pivot logic (unchanged). No new HTMX patterns — pure port.

**Delivers:**
- `app_v2/routers/browse.py` + `app_v2/routers/htmx/browse.py`
- `app_v2/templates/browse.html` + `partials/browse_table.html`
- Platform + parameter pickers with typeahead; swap-axes; row/col caps
- Plotly chart injection via `fig.to_html(full_html=False, include_plotlyjs=False)`
- Excel + CSV export (browser download, not HTMX swap)
- `pool_size=2, max_overflow=3` comment verified for parallel deployment

**Avoids:** Pitfall 4 (async def + sync DB), Pitfall 11 (dual DB pool exhaustion)

### Phase 5: Ask Tab Port

**Rationale:** Ask tab depends on Phase 3's `get_agent()` factory and Phase 0's `nl_service.py`. By Phase 5, both are in place. The NL-05 two-turn confirmation flow requires special HTMX handling: candidate params from step 1 survive to step 2 via hidden form fields (no session state).

**Delivers:**
- `app_v2/routers/ask.py` + `app_v2/routers/htmx/ask.py`
- `app_v2/templates/ask.html` + `partials/ask_result.html`, `ask_clarification.html`, `ask_error.html`
- All Ask routes call `nl_service.run_nl_query()` — SAFE-02..06 guaranteed
- NL-05 two-turn flow: step-1 candidate params as checked checkboxes in hidden form; step-2 POST carries them as form fields
- Starter prompt gallery (8 prompts from v1.0)
- LLM backend radio reads from `SameSite=Lax` cookie from Phase 3

**Avoids:** Pitfall 2 (safety harness bypass), Pitfall 13 (NL-05 stateless two-turn over HTMX)

### Phase 6: Settings Port (parallelizable with Phase 4 or 5)

**Rationale:** Settings depends only on Phase 1's `get_settings()` dependency. Standard form POST patterns, no new HTMX complexity. Lowest-risk phase; assignable in parallel.

**Delivers:**
- `app_v2/routers/settings.py` + `app_v2/templates/settings.html`
- `GET /settings` renders current DB/LLM config; `POST /settings` saves
- Per-connection "Test" buttons via HTMX POST
- Health indicator as OOB-updated element in `base.html` persistent shell

---

### Phase Ordering Rationale

- **Phase 0 before everything:** Both v1.0 file modifications are the only places where existing passing tests can regress. All subsequent phases depend on these files being importable without Streamlit context.
- **Phase 1 before all `app_v2/` features:** Shell conventions (Starlette 1.0 signature, `def` routes, `htmx:beforeSwap`) are structural; adding them to partially-built pages is risky.
- **Phase 2 before Phase 3:** Overview de-risks `jinja2-fragments` and HTMX filter-swap patterns with simpler data before LLM integration is introduced.
- **Phase 3 before Phase 5:** `get_agent()` factory and LLM backend cookie introduced in Phase 3 are reused by Phase 5.
- **Phases 4 and 6 parallelizable:** Browse and Settings are independent once Phase 1 is complete.

### Research Flags

Phases requiring no additional research (well-documented, standard patterns):
- **Phase 1 (Foundation Shell):** FastAPI lifespan, StaticFiles, Jinja2 DI — official FastAPI docs have copy-paste examples
- **Phase 4 (Browse Port):** Pandas pivot + Bootstrap table + Plotly `to_html` — v1.0 logic reused; new rendering layer only
- **Phase 6 (Settings Port):** HTMX form POST + pydantic-settings — standard patterns

Phases where a `/gsd-research-phase` run should be considered:
- **Phase 2 (Overview + Filters):** Confirm `jinja2-fragments>=1.3` `Jinja2Blocks` works with Starlette 1.0's updated response model before writing routes. Fallback: manual block rendering wrapper.
- **Phase 3 (Content + AI Summary):** LLM backend cookie replacing `st.session_state` — confirm `SameSite=Lax` cookie reads correctly in FastAPI `Cookie(default="ollama")` dependency with HTMX partial requests.
- **Phase 5 (Ask Port):** NL-05 two-turn HTMX flow — hidden-field state carry between step 1 and step 2 has no prior art in the codebase; spike recommended.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI and official release pages on 2026-04-23; Starlette 1.0 breaking change confirmed via GitHub discussion |
| Features | HIGH (HTMX mechanics) / MEDIUM (PLATFORM_ID year parsing) | SoC→year lookup table cross-referenced Wikipedia + PhoneDB; no single authoritative source |
| Architecture | HIGH | Scaffolding read directly; FastAPI lifespan, jinja2-fragments, cachetools patterns verified against official docs |
| Pitfalls | HIGH (FastAPI async, HTMX quirks, markdown-it-py XSS) / MEDIUM (CSRF/session) | CSRF assessment applied general patterns to this specific intranet context |

**Overall confidence: HIGH**

### Gaps to Address

- **`jinja2-fragments` + Starlette 1.0 compatibility:** Confirm `Jinja2Blocks.TemplateResponse(request, name, context, block_name=)` accepts Starlette 1.0's `request`-first signature before Phase 2 begins. Architecture.md lists `>=1.3`; STACK.md omits explicit version — add to `requirements-v2.txt` explicitly.
- **cachetools version discrepancy:** ARCHITECTURE.md lists `>=5.3`; STACK.md lists `>=7.0,<8.0`. Use `>=7.0,<8.0` (STACK.md is the authoritative version document).
- **NL-05 HTMX state between turns:** Two-turn confirmation carries step-1 candidate params to step-2 via hidden form fields. No prior art in codebase. Spike recommended in Phase 5 planning.
- **Plotly CDN loading:** Using `include_plotlyjs=False` requires a Plotly CDN `<script>` in `base.html`. Confirm this does not conflict with HTMX's deferred script loading pattern (`defer` attribute on all scripts in base.html).
- **Intranet CDN access gate:** Before Phase 1, test whether `cdn.jsdelivr.net` is reachable from the deployment server. If not, all CDN URLs in STACK.md must be vendored — architecture already accounts for this (`app_v2/static/vendor/`).

---

## Sources

### Primary (HIGH confidence)
- FastAPI 0.136.1 + Starlette 1.0 — https://pypi.org/project/fastapi/ ; https://github.com/fastapi/fastapi/releases/latest
- Starlette 1.0 TemplateResponse change — https://github.com/fastapi/fastapi/discussions/15198
- HTMX 2.0.10 stable + 4.0 alpha — https://htmx.org/ ; https://htmx.org/essays/the-fetchening/
- markdown-it-py security (html=True default, js-default) — https://markdown-it-py.readthedocs.io/en/latest/security.html
- cachetools thread safety — https://cachetools.readthedocs.io/ ; https://github.com/tkem/cachetools/issues/294
- FastAPI async (sync def threadpool) — https://fastapi.tiangolo.com/async/
- FastAPI path params (pattern validation) — https://fastapi.tiangolo.com/tutorial/path-params/
- HTMX hx-disabled-elt — https://htmx.org/attributes/hx-disabled-elt/
- HTMX quirks (4xx silent discard) — https://htmx.org/quirks/
- jinja2-fragments — https://pypi.org/project/jinja2-fragments/ ; https://github.com/sponsfreixes/jinja2-fragments
- Bootstrap 5.3.8 CDN — https://getbootstrap.com/docs/5.3/getting-started/introduction/
- pydantic-settings 2.14.0 — https://pypi.org/project/pydantic-settings/
- FastAPI lifespan events — https://fastapi.tiangolo.com/advanced/events/
- OWASP path traversal — https://owasp.org/www-community/attacks/Path_Traversal

### Secondary (MEDIUM confidence)
- Bootstrap 5 tabs with HTMX (hasChildNodes guard) — https://marcus-obst.de/blog/use-bootstrap-5x-tabs-with-htmx
- Plotly to_html FastAPI HTMX — https://medium.com/codex/building-real-time-dashboards-with-fastapi-htmx-plotly-python-the-pure-python-charts-edition-2c29e77da953
- Qualcomm SoC year lookup — https://en.wikipedia.org/wiki/List_of_Qualcomm_Snapdragon_systems_on_chips
- HTMX + FastAPI patterns — https://testdriven.io/blog/fastapi-htmx/

---

*Research completed: 2026-04-23*
*Ready for roadmap: yes*
