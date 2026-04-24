# Stack Research

**Domain:** FastAPI + Bootstrap 5 + HTMX server-rendered web app — v2.0 Bootstrap Shell rewrite of PBM2
**Researched:** 2026-04-23
**Confidence:** HIGH (all versions verified via PyPI and official release pages)

---

## Scope of this document

This document covers ONLY the NEW libraries required for v2.0. The following v1.0 libraries are locked and carry forward unchanged — do not re-pin or re-research them:

| Locked Library | Pin from v1.0 |
|----------------|---------------|
| sqlalchemy | `>=2.0,<2.1` |
| pymysql | `>=1.1` |
| pandas | `>=3.0` |
| pydantic | `>=2.7` |
| pydantic-ai | `>=1.0,<2.0` |
| openai | `>=1.50` |
| sqlparse | `>=0.5` |
| openpyxl | `>=3.1` |
| plotly | `>=5.22` (see Charts section for v2.0 usage pattern) |
| python-dotenv | `>=1.0` |
| pyyaml | `>=6.0` |
| httpx | `>=0.27` |
| bcrypt | `>=4.2` |

Streamlit, streamlit-authenticator, and altair are v1.0-only. They are NOT added to v2.0's requirements.

---

## Recommended Stack — New Additions for v2.0

### Core Technologies

| Technology | Verified Version | Purpose | Why Recommended |
|------------|-----------------|---------|-----------------|
| FastAPI | 0.136.1 (2026-04-23) | ASGI web framework, routing, dependency injection | Current stable; ships with Starlette 1.0.0 as of 0.136.1; first-class `Jinja2Templates` and `StaticFiles` via Starlette; zero-overhead dependency injection is the cleanest way to thread `Settings` and DB engine into route handlers |
| Starlette | 1.0.0 | HTTP routing, middleware, StaticFiles, TestClient | Bundled with FastAPI 0.136.1; do not pin separately — let FastAPI pull the correct version; note Starlette 1.0 has a breaking `TemplateResponse` signature change (see Pitfall below) |
| Jinja2 | 3.x (bundled with FastAPI extras) | HTML templating | FastAPI pulls Jinja2 via `pip install fastapi[standard]`; no separate pin needed; `Jinja2Templates` from `fastapi.templating` wraps it correctly |
| uvicorn | 0.46.0 (2026-04-23) | ASGI server for dev and production | Current stable; `uvicorn app:app --reload` for dev; `gunicorn -k uvicorn.workers.UvicornWorker` for intranet production (see Deployment section) |
| pydantic-settings | 2.14.0 (2026-04-20) | Settings management with `.env` + YAML for FastAPI | `BaseSettings` reads `.env` automatically with Pydantic v2 validation; the `@lru_cache` + `Depends(get_settings)` pattern is the canonical FastAPI config injection approach; replaces `@st.cache_resource` for settings in v2.0; already compatible with existing `DatabaseConfig`/`LLMConfig`/`AgentConfig` models |
| cachetools | 7.0.6 (2026-04-20) | `TTLCache` with `@cached` decorator for `ufs_service.py` | Replaces `@st.cache_data` — the only Streamlit-specific caching primitive that needs to change; thread-safe with `lock=threading.Lock()`; 5-line drop-in for the existing service functions; no new infrastructure required |
| markdown-it-py | 4.0.0 (2026-08-11) | Render `content/platforms/<PLATFORM_ID>.md` to HTML | CommonMark 0.31.2 compliant; Python 3.11+ supported; install with `markdown-it-py[linkify,plugins]` to get `mdit-py-plugins` for fenced code, footnotes, and front-matter; the `plugins` extra pulls `mdit-py-plugins` automatically — no separate pin |

### Frontend (CDN, not PyPI)

Bootstrap and HTMX are served via CDN — no Python package, no build step, no npm.

| Asset | Version | CDN URL | Notes |
|-------|---------|---------|-------|
| Bootstrap CSS | 5.3.8 | `https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css` | Current stable; SRI hash available from jsDelivr; includes dark-mode support via `data-bs-theme` attribute |
| Bootstrap JS bundle | 5.3.8 | `https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js` | Includes Popper.js; required for dropdowns, modals, tooltips used in the nav shell |
| Bootstrap Icons | 1.13.1 | `https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css` | 2000+ icons; CSS font approach, no JS; co-versioned with Bootstrap 5 — zero friction |
| HTMX | 2.0.10 | `https://cdn.jsdelivr.net/npm/htmx.org@2.0.10/dist/htmx.min.js` | **Pin to 2.x, not 4.x** (see HTMX version rationale below); all `hx-get/post/target/swap/trigger/boost` attributes work identically; 14KB minified |

HTMX extensions needed for v2.0:
- No extensions required for the v2.0 feature set (Overview swap, form-based CRUD, AI Summary in-place swap). All target interactions use core `hx-get`, `hx-post`, `hx-target`, `hx-swap="outerHTML"`, `hx-trigger`, and `hx-indicator`.
- `hyperscript` (`_hyperscript`) is explicitly NOT needed — all interactivity is server-driven with Bootstrap JS handling client-side modal/tab state.

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| mdit-py-plugins | (pulled by `markdown-it-py[plugins]`) | Markdown extensions: fenced code, admonitions, front-matter | Included automatically with `markdown-it-py[linkify,plugins]`; do not pin separately |
| pytest-asyncio | latest (`>=0.23`) | Async pytest support for `httpx.AsyncClient` endpoint tests | Required because FastAPI route handlers are `async def`; configure with `asyncio_mode = "auto"` in `pytest.ini` |
| httpx | `>=0.27` (already in v1.0 requirements) | `httpx.AsyncClient` for testing HTMX endpoints | Already present; FastAPI's `TestClient` is synchronous (fine for sync routes); use `httpx.AsyncClient` with `ASGITransport(app=app)` for async routes — no new dependency |

### Development Tools (additions to v1.0 toolset)

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest-asyncio | Async test runner for FastAPI routes | Add `asyncio_mode = "auto"` to `pytest.ini` to avoid per-test `@pytest.mark.asyncio` decoration |
| gunicorn | Process manager wrapping uvicorn workers for intranet production | `gunicorn -k uvicorn.workers.UvicornWorker -w 4 app_v2.main:app`; workers = CPU cores; only needed for deployment, not dev |

---

## Sub-Question Answers

### 1. FastAPI version

**Pin: `fastapi>=0.136,<1.0`**

FastAPI 0.136.1 is current stable (released 2026-04-23). It bumped its Starlette dependency to 1.0.0. Key impact: the `TemplateResponse` call signature changed in Starlette 1.0 — the old `TemplateResponse(name, context_dict)` form is removed; the correct form is `TemplateResponse(request, name, context_dict)`. All v2.0 templates must use the new signature from day one.

Use `pip install fastapi[standard]` — this installs Jinja2, python-multipart (required for `Form` data), and the `fastapi-cli` dev server tool automatically.

### 2. Bootstrap 5 — CDN vs vendored

**CDN for v2.0. Vendor only if intranet has no external CDN access.**

jsDelivr is the Bootstrap project's recommended CDN. For an intranet deployment where the server may not have outbound internet access, vendor the three files (bootstrap.min.css, bootstrap.bundle.min.js, bootstrap-icons.min.css) into `app_v2/static/vendor/`. FastAPI serves them via `StaticFiles` mount — exact same pattern as any other static asset. Do not add a Python package for Bootstrap.

The decision gate: test at deployment time whether `jsDelivr` is reachable from the intranet server. If yes, use CDN (easier updates). If no, vendor the files into `static/vendor/` and update the Jinja2 base template's `<link>` and `<script>` hrefs.

### 3. HTMX version — use 2.x not 4.x

**Use HTMX 2.0.10 (current stable). Do not use HTMX 4.0 alpha.**

HTMX 4.0 entered alpha on 2026-04-09. It will not be marked `latest` until early 2027. It introduces breaking changes: prop inheritance disabled by default, history handling changed from DOM snapshot to network request, XHR replaced with Fetch API. HTMX 2.x is maintained indefinitely alongside 4.x. For a new production app starting in April 2026, pin to `htmx.org@2.0.10` — the same `hx-*` attributes work, no migration cost later is significant.

No HTMX extensions are required for the v2.0 feature set. The complete feature list (Overview list swap, AI Summary in-place swap, filter swap, content page CRUD) maps directly onto core HTMX 2.x primitives.

### 4. Jinja2 via fastapi.templating

**Use `Jinja2Templates` from `fastapi.templating`. No separate Jinja2 pin.**

```python
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="app_v2/templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"title": "PBM2"})
```

Critical Starlette 1.0 caveat: pass `request` as the FIRST positional argument, not inside the context dict. `TemplateResponse(request, "template.html", context)` is the Starlette 1.0 signature. The old `TemplateResponse("template.html", {"request": request})` will raise `TypeError: unhashable type: dict` at runtime.

For `url_for` in templates (`{{ url_for('static', path='/css/custom.css') }}`): works out-of-the-box once `StaticFiles` is mounted before the templates are initialized.

### 5. markdown-it-py

**Use `markdown-it-py[linkify,plugins]>=4.0`**

```python
from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin

md = MarkdownIt("commonmark", {"breaks": True, "html": False}).enable("table")
# For content pages, disable raw HTML to prevent injection:
# html=False is the safe default for user-authored content

def render_content_page(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    return md.render(text)
```

`html=False` is the safe choice for the `content/platforms/<PLATFORM_ID>.md` pages since those files are team-authored (not end-user input) but may be edited through the web UI in future milestones. Keeps XSS surface minimal.

The `linkify` extra enables bare-URL auto-linking. The `plugins` extra provides fenced-code-block highlighting, footnotes, and YAML front-matter stripping — useful if content pages grow to include metadata headers.

### 6. pydantic-settings FastAPI integration

**Use `pydantic-settings>=2.14` with `@lru_cache` + `Depends(get_settings)` pattern.**

```python
# app_v2/core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_url: str
    openai_api_key: str = ""
    # ... re-uses existing DatabaseConfig/LLMConfig as nested models

    model_config = SettingsConfigDict(env_file=".env", env_prefix="PBM2_")

@lru_cache
def get_settings() -> Settings:
    return Settings()

# In route handlers:
from fastapi import Depends
def my_route(settings: Settings = Depends(get_settings)):
    ...
```

The existing `.env` file (with `OPENAI_API_KEY`, `SETTINGS_PATH`, etc.) loads automatically. `@lru_cache` gives the equivalent of `@st.cache_resource` for the settings singleton — created once, reused across requests.

Note: `pydantic-settings` is a separate package from `pydantic` since Pydantic v2. It is NOT included in `pydantic>=2.7` — it must be added to `requirements.txt` explicitly.

### 7. Static file serving

**Use `app.mount("/static", StaticFiles(directory="app_v2/static"), name="static")` at app startup.**

```python
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="app_v2/static"), name="static")
```

Mount before route registration. The `name="static"` parameter enables `url_for("static", path="...")` inside Jinja2 templates. Static directory layout:

```
app_v2/static/
  css/           # custom CSS overrides
  js/            # custom JS (minimal)
  vendor/        # Bootstrap + HTMX files if vendoring (CDN fallback)
```

For HTMX partial responses (HTML fragments), return `HTMLResponse` directly rather than a full `TemplateResponse` — avoids rendering the base layout twice:

```python
@app.get("/overview/list", response_class=HTMLResponse)
async def overview_list_partial(request: Request, brand: str = ""):
    platforms = await get_filtered_platforms(brand)
    return templates.TemplateResponse(request, "partials/overview_list.html", {"platforms": platforms})
```

### 8. ASGI server — uvicorn vs gunicorn+uvicorn

**Dev:** `uvicorn app_v2.main:app --reload --port 8000`

**Intranet production:** `gunicorn -k uvicorn.workers.UvicornWorker -w 4 --bind 0.0.0.0:8000 app_v2.main:app`

Workers = CPU core count. The app is I/O-bound (MySQL + LLM calls), so 4 workers on a typical 4-core intranet server is sufficient. Do not use `--workers` > CPU cores for async workloads — async handles concurrency within each worker without additional processes.

`gunicorn` package (not `uvicorn`) is only needed in production; install it as a separate step in the deployment script, not in `requirements.txt` used during development. The `uvicorn.workers.UvicornWorker` class is provided by the `uvicorn` package — no `uvicorn-worker` PyPI package needed (that project is legacy).

### 9. Caching — replacing @st.cache_data in ufs_service.py

**Use `cachetools.TTLCache` with `@cached(cache=..., lock=threading.Lock())`.**

The refactor is minimal. Existing `ufs_service.py` has functions decorated with `@st.cache_data(ttl=300)`. The replacement:

```python
# Before (v1.0, Streamlit-specific):
@st.cache_data(ttl=300)
def get_platform_ids() -> list[str]: ...

# After (v2.0, framework-agnostic):
import threading
from cachetools import TTLCache, cached

_platform_cache = TTLCache(maxsize=1, ttl=300)

@cached(cache=_platform_cache, lock=threading.Lock())
def get_platform_ids() -> list[str]: ...
```

The `lock=threading.Lock()` is mandatory — `TTLCache` is not thread-safe on its own, and FastAPI with multiple uvicorn workers (or even with `--reload`) will have concurrent callers.

The SQLAlchemy `Engine` (equivalent of `@st.cache_resource`) becomes a module-level singleton initialized once at `app_v2/startup.py` and injected via `Depends()`:

```python
# app_v2/db.py
from sqlalchemy import create_engine
from functools import lru_cache

@lru_cache
def get_engine():
    return create_engine(settings.db_url, pool_pre_ping=True, pool_recycle=3600)
```

`@lru_cache` on `get_engine` gives singleton behavior (called once per process) — equivalent to `@st.cache_resource` for the engine.

### 10. Icon set

**Use Bootstrap Icons 1.13.1 via CDN.**

Bootstrap Icons is the correct choice because:
- Already co-versioned with the Bootstrap 5 CSS in use
- CSS font approach — single `<link>` tag, no JS, no SVG sprite management
- 2000+ icons covers every UI need in v2.0 (nav tabs, filter controls, export buttons, edit/delete actions, spinner)
- Feather Icons and Heroicons require either a JS bundle or manual SVG inlining; Bootstrap Icons has no such requirement

Do NOT add `pip install bootstrap-icons` (Python wrappers exist but are unnecessary wrappers around the CDN asset).

### 11. Testing HTMX endpoints

**Use `httpx.AsyncClient` with `ASGITransport` + `pytest-asyncio`. No browser required.**

```python
# tests/v2/test_overview.py
import pytest
from httpx import AsyncClient, ASGITransport
from app_v2.main import app

@pytest.mark.asyncio
async def test_overview_list_fragment(mock_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/overview/list", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert "platform-card" in response.text  # check HTML fragment content
    assert "<html>" not in response.text      # assert it is a partial, not full page
```

Key patterns:
- Pass `HX-Request: true` header to tell routes to return HTML fragments rather than full pages
- Assert fragment shape via string matching (simpler than BeautifulSoup for narrow fragments)
- Use `pytest-asyncio` with `asyncio_mode = "auto"` to avoid per-test `@pytest.mark.asyncio` decoration
- Override `Depends(get_engine)` via `app.dependency_overrides[get_engine] = mock_engine_factory` for DB isolation

### 12. Charts — plotly carries over with a new rendering path

**Keep plotly>=5.22 (already in v1.0 requirements). Use `fig.to_html(full_html=False, include_plotlyjs="cdn")` for server-rendered injection.**

Plotly generates self-contained HTML/JS fragments that HTMX can inject directly into the DOM. This is the standard pattern for FastAPI + HTMX + Plotly:

```python
import plotly.graph_objects as go

def build_chart_html(df: pd.DataFrame, x_col: str, y_col: str) -> str:
    fig = go.Figure(data=[go.Bar(x=df[x_col], y=df[y_col])])
    return fig.to_html(full_html=False, include_plotlyjs="cdn")

# In route:
@app.get("/browse/chart", response_class=HTMLResponse)
async def chart_partial(request: Request, ...):
    html = build_chart_html(pivot_df, ...)
    return HTMLResponse(content=html)
```

`include_plotlyjs="cdn"` injects a CDN `<script>` tag for the Plotly JS library only on first use. Alternatively use `include_plotlyjs=False` and include Plotly's CDN `<script>` in the base layout once.

Chart.js is NOT recommended here — it requires writing JavaScript configuration objects per chart, which partially defeats the "no-build, no-JS" ethos of the HTMX stack and introduces a JavaScript-side data serialization step that Plotly avoids.

---

## Installation — requirements additions for v2.0

```bash
# Add to requirements.txt (new entries only — v1.0 entries stay unchanged):
fastapi[standard]>=0.136,<1.0
uvicorn>=0.46,<1.0
pydantic-settings>=2.14,<3.0
cachetools>=7.0,<8.0
markdown-it-py[linkify,plugins]>=4.0,<5.0

# Dev / test additions (add to dev-requirements.txt or similar):
pytest-asyncio>=0.23
```

Bootstrap 5, Bootstrap Icons, and HTMX are CDN assets — no PyPI entry.

Streamlit and streamlit-authenticator are NOT in v2.0's requirements file. They remain in v1.0's requirements if `app/` (v1.0) and `app_v2/` (v2.0) have separate requirements files (recommended).

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| FastAPI + Jinja2 + HTMX | Django + HTMX | Django's ORM, admin, and migration system add weight with no benefit; the DB is read-only and single-table; FastAPI's dependency injection maps cleanly onto existing `DatabaseConfig`/`LLMConfig` Pydantic models |
| FastAPI + Jinja2 + HTMX | Flask + HTMX | Flask 3.x is a valid alternative; FastAPI chosen because PydanticAI 1.86 has first-class FastAPI integration examples, FastAPI's async-native path handles LLM calls without blocking, and the existing codebase is already Pydantic-typed throughout |
| HTMX 2.0.10 | HTMX 4.0 alpha | 4.0 is alpha as of 2026-04-09; will not be `latest` until early 2027; breaking changes in prop inheritance and history handling; 2.x maintained indefinitely |
| cachetools TTLCache | aiocache | aiocache is async-only and targets Redis/Memcached backends; `ufs_service.py` functions are synchronous (blocking SQLAlchemy calls in a thread pool); `cachetools` is the correct fit |
| cachetools TTLCache | diskcache | diskcache persists to disk, which adds I/O overhead and a cache invalidation problem; in-process `TTLCache` is sufficient for a single-process intranet server |
| cachetools TTLCache | fastapi-cache2 | Adds another dependency and a Redis/InMemory backend abstraction; the use case here is a single-process intranet app where `TTLCache` + `threading.Lock()` is the minimal-dependency equivalent |
| pydantic-settings | python-dotenv only | python-dotenv loads env vars but does not validate types; existing `DatabaseConfig`/`LLMConfig` are Pydantic models — `BaseSettings` extends this naturally with zero new concept |
| Bootstrap Icons | Heroicons | Heroicons requires SVG inlining or JS import; Bootstrap Icons is a pure-CSS font matching the Bootstrap design language already in use |
| Bootstrap Icons | Feather Icons | Same issue as Heroicons — JS dependency or SVG sprite; Bootstrap Icons is simpler for this stack |
| plotly (server HTML) | Chart.js | Chart.js needs JavaScript config objects — breaks the "Python-only, no build" model; Plotly's `to_html(full_html=False)` produces a self-contained HTMX-injectable fragment from Python alone |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Streamlit in v2.0 | v2.0 is explicitly a rewrite away from Streamlit; Streamlit and FastAPI cannot share a port or process cleanly | FastAPI |
| HTMX 4.0 alpha | Alpha as of 2026-04-09; breaking changes in inheritance model and history; not production-ready until 2027 | HTMX 2.0.10 |
| Alpine.js | Adds a second JavaScript framework for client-side state; v2.0 feature set (tab state, filter swap, AI summary swap) is achievable with Bootstrap JS + HTMX alone — Alpine would be used for nothing that isn't already covered | Bootstrap 5 tabs + HTMX |
| React / Vue / Svelte | SPA frameworks require a build step, a Node.js toolchain, and a JSON API surface — directly contradicts the HTMX philosophy and the "no-build" intranet constraint | HTMX + Jinja2 |
| litellm | Already rejected in v1.0 for two-provider case; still irrelevant in v2.0 | openai SDK with `base_url` |
| fastapi-htmx (PyPI package) | Third-party convenience wrapper around Jinja2Templates; adds dependency for minimal benefit; the decorator pattern it provides is trivially implemented with FastAPI's native `Depends` + manual `HX-Request` header check | Raw `fastapi.templating.Jinja2Templates` |
| `pytest-streamlit` | v2.0 has no Streamlit; this package is irrelevant | `httpx.AsyncClient` + `pytest-asyncio` |
| SQLAlchemy 2.1.x | Still beta as of 2026-04-16; same constraint as v1.0 | `sqlalchemy>=2.0,<2.1` |

---

## Version Compatibility Notes

| Package | Pin | Compatibility Note |
|---------|-----|--------------------|
| fastapi | `>=0.136,<1.0` | 0.136.1 depends on Starlette 1.0.0; let FastAPI manage the Starlette pin — do NOT add a separate `starlette` entry in requirements.txt |
| starlette | (managed by fastapi) | Starlette 1.0.0 removes `TemplateResponse(name, context_dict)` — all templates must use `TemplateResponse(request, name, context_dict)` |
| uvicorn | `>=0.46,<1.0` | 0.46.0 requires Python >=3.10 (satisfied; v1.0 already requires 3.11+) |
| pydantic-settings | `>=2.14,<3.0` | Compatible with `pydantic>=2.7`; `BaseSettings` is in `pydantic_settings` module, NOT `pydantic` — update all imports from `pydantic` to `pydantic_settings` |
| cachetools | `>=7.0,<8.0` | 7.x drops Python 3.8/3.9 (irrelevant; project requires 3.11+); `TTLCache` API unchanged |
| markdown-it-py | `>=4.0,<5.0` | 4.0 drops Python 3.8/3.9; CommonMark 0.31.2 compliant; `mdit-py-plugins` pulled automatically via `[plugins]` extra |
| htmx (CDN) | `@2.0.10` | Pin explicitly in CDN URLs and vendor copies to avoid surprise breaking change if 4.0 becomes `latest` |
| bootstrap (CDN) | `@5.3.8` | Pin explicitly; Bootstrap 6 is in pre-alpha and would require significant template changes |

---

## Sources

- FastAPI 0.136.1 — https://pypi.org/project/fastapi/ (version confirmed 2026-04-23; Starlette 1.0.0 bump confirmed at https://github.com/fastapi/fastapi/releases/latest)
- Starlette 1.0.0 TemplateResponse breaking change — https://github.com/fastapi/fastapi/discussions/15198 (MEDIUM confidence — community reports confirmed; official Starlette release notes at https://www.starlette.io/release-notes/)
- uvicorn 0.46.0 — https://pypi.org/project/uvicorn/ (version confirmed 2026-04-23)
- pydantic-settings 2.14.0 — https://pypi.org/project/pydantic-settings/ (version confirmed 2026-04-20)
- cachetools 7.0.6 — https://pypi.org/project/cachetools/ (version confirmed 2026-04-20; TTLCache thread-safety docs at https://cachetools.readthedocs.io/)
- markdown-it-py 4.0.0 — https://pypi.org/project/markdown-it-py/ (version confirmed 2026-08-11; plugins install pattern confirmed)
- Bootstrap 5.3.8 CDN — https://getbootstrap.com/docs/5.3/getting-started/introduction/ (version confirmed; jsDelivr SRI hashes verified)
- Bootstrap Icons 1.13.1 CDN — https://icons.getbootstrap.com/ (version confirmed via jsDelivr)
- HTMX 2.0.10 CDN — https://htmx.org/ (2.x stable confirmed; 4.0 alpha status confirmed at https://www.infoworld.com/article/4150864/htmx-4-0-hypermedia-finds-a-new-gear.html)
- HTMX 4.0 alpha status — https://htmx.org/essays/the-fetchening/ (alpha; not production ready until 2027)
- FastAPI templating pattern — https://fastapi.tiangolo.com/advanced/templates/ (StaticFiles + Jinja2Templates pattern confirmed)
- FastAPI settings with pydantic-settings — https://fastapi.tiangolo.com/advanced/settings/ (Depends(get_settings) pattern confirmed)
- FastAPI async testing — https://fastapi.tiangolo.com/advanced/async-tests/ (httpx.AsyncClient + ASGITransport pattern confirmed)
- Plotly to_html FastAPI HTMX — https://medium.com/codex/building-real-time-dashboards-with-fastapi-htmx-plotly-python-the-pure-python-charts-edition-2c29e77da953 (MEDIUM confidence — community article; pattern matches official Plotly interactive HTML export docs at https://plotly.com/python/interactive-html-export/)
- gunicorn + uvicorn workers — https://fastapi.tiangolo.com/deployment/server-workers/ (official FastAPI deployment docs)

---

*Stack research for: PBM2 v2.0 Bootstrap Shell — FastAPI + Bootstrap 5 + HTMX rewrite*
*Researched: 2026-04-23*
