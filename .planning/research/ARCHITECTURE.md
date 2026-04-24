# Architecture Research

**Domain:** FastAPI + Bootstrap 5 + HTMX parallel rewrite of a Streamlit EAV-MySQL browser (PBM2 v2.0)
**Researched:** 2026-04-23
**Confidence:** HIGH (scaffolding read directly; FastAPI/HTMX/jinja2-fragments patterns verified against official docs and PyPI)

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   BROWSER (Bootstrap 5 + HTMX 2.x)                              │
│  Full page load                    HTMX partial swap                            │
│  GET /  /browse  /ask  /platforms  hx-get → /htmx/overview/filter               │
│                                            /htmx/platforms/{id}/summary         │
│                                            /htmx/browse/results                 │
│                                            /htmx/ask/result                     │
└────────────────────┬─────────────────────────────┬───────────────────────────── ┘
                     │ full HTML                    │ HTML fragment only
                     ▼                              ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                  FASTAPI APP  (app_v2/main.py)                                   │
│                                                                                  │
│  lifespan:  loads Settings → builds MySQLAdapter → stores in app.state          │
│             init cachetools.TTLCache(maxsize=512, ttl=300) in app.state          │
│             init agent_registry dict (lazy per backend) in app.state            │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐   │
│  │              ROUTERS  (app_v2/routers/)                                   │   │
│  │  overview.py   browse.py   ask.py   platforms.py   htmx/   settings.py   │   │
│  └──────────────────────────────────┬────────────────────────────────────── ┘   │
│                                     │ Depends(get_db) / Depends(get_settings)   │
│  ┌───────────────────────────────── ▼────────────────────────────────────────┐  │
│  │              TEMPLATES  (app_v2/templates/)                               │   │
│  │  base.html  overview.html  browse.html  ask.html  platform_page.html     │   │
│  │  partials/  overview_list.html  browse_table.html  ai_summary.html        │   │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │              STATIC FILES  (app_v2/static/)                               │   │
│  │  vendor/bootstrap.min.css  vendor/htmx.min.js  css/app.css  js/app.js    │   │
│  └────────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │ direct import (no copy)
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│               SHARED SERVICE / DOMAIN LAYER  (app/services/ + app/core/)        │
│                                                                                  │
│  app/services/ufs_service.py   ← MODIFIED: @st.cache_data removed;             │
│                                  fetch_cells_core() extracted; TTLCache wrapper  │
│                                  lives in app_v2/services/cache.py              │
│  app/services/result_normalizer.py   — unchanged, imported directly             │
│  app/services/sql_validator.py       — unchanged, imported directly             │
│  app/services/sql_limiter.py         — unchanged, imported directly             │
│  app/services/path_scrubber.py       — unchanged, imported directly             │
│  app/core/agent/nl_agent.py          — unchanged, imported directly             │
│  app/core/config.py                  — unchanged, imported directly             │
│  app/core/agent/config.py            — unchanged, imported directly             │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│               ADAPTER LAYER  (app/adapters/)  — unchanged, shared               │
│  app/adapters/db/mysql.py (MySQLAdapter)                                         │
│  app/adapters/llm/openai_adapter.py / ollama_adapter.py / registry.py           │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│  MySQL (ufs_data, read-only)      OpenAI API / Ollama (local)                   │
│  content/platforms/*.md  (filesystem, r/w by v2.0 content CRUD)                 │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Recommended Project Structure

```
Proj28_PBM2/
├── streamlit_app.py                        # v1.0 — untouched, stays runnable
├── app/                                    # v1.0 — untouched (except ufs_service refactor)
│   ├── services/
│   │   ├── ufs_service.py                  # MODIFIED: extract fetch_cells_core() (see §Service Reuse)
│   │   ├── result_normalizer.py            # unchanged
│   │   ├── sql_validator.py                # unchanged
│   │   ├── sql_limiter.py                  # unchanged
│   │   ├── path_scrubber.py                # unchanged
│   │   └── ollama_fallback.py              # unchanged
│   ├── adapters/
│   │   ├── db/   (base.py, mysql.py, registry.py)   # unchanged
│   │   └── llm/  (base.py, openai_adapter.py, ollama_adapter.py, registry.py)
│   └── core/
│       ├── config.py                       # unchanged
│       └── agent/
│           ├── config.py                   # unchanged
│           └── nl_agent.py                 # unchanged
│
├── app_v2/                                 # NEW: v2.0 FastAPI app (sibling to app/)
│   ├── main.py                             # FastAPI app factory + lifespan
│   ├── dependencies.py                     # Depends() providers: get_db, get_settings, get_agent
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── overview.py                     # GET /
│   │   ├── browse.py                       # GET /browse
│   │   ├── ask.py                          # GET /ask, POST /ask/query
│   │   ├── platforms.py                    # GET /platforms/{id}
│   │   ├── settings.py                     # GET /settings, POST /settings
│   │   └── htmx/
│   │       ├── __init__.py
│   │       ├── overview.py                 # GET /htmx/overview/filter, POST /htmx/overview/add, DELETE /htmx/overview/remove
│   │       ├── browse.py                   # GET /htmx/browse/results
│   │       ├── ask.py                      # POST /htmx/ask/result
│   │       └── platforms.py               # GET /htmx/platforms/{id}/summary, GET/POST/DELETE /htmx/platforms/{id}/content
│   ├── services/
│   │   ├── __init__.py
│   │   ├── cache.py                        # TTLCache wrapper (replaces @st.cache_data)
│   │   ├── ufs_service_v2.py               # Thin shim: calls fetch_cells_core + cache.py
│   │   ├── content_service.py              # Markdown file r/w with atomic writes
│   │   └── overview_store.py               # Curated platform list persistence (JSON or YAML)
│   ├── templates/
│   │   ├── base.html                       # Bootstrap shell, nav tabs, HTMX script tag
│   │   ├── overview.html                   # extends base.html; includes partials/overview_list.html
│   │   ├── browse.html                     # extends base.html; includes partials/browse_table.html
│   │   ├── ask.html                        # extends base.html; includes partials/ask_result.html
│   │   ├── platform_page.html              # extends base.html; platform content + AI Summary btn
│   │   ├── settings.html                   # extends base.html
│   │   └── partials/
│   │       ├── overview_list.html          # HTMX swap target: platform cards list
│   │       ├── browse_table.html           # HTMX swap target: pivot table HTML
│   │       ├── ask_result.html             # HTMX swap target: NL result + explanation
│   │       └── ai_summary.html             # HTMX swap target: summary text block
│   ├── static/
│   │   ├── vendor/
│   │   │   ├── bootstrap.min.css           # vendored Bootstrap 5.3.x
│   │   │   ├── bootstrap.bundle.min.js     # vendored Bootstrap JS + Popper
│   │   │   └── htmx.min.js                 # vendored HTMX 2.x
│   │   ├── css/
│   │   │   └── app.css                     # project-specific styles
│   │   └── js/
│   │       └── app.js                      # minimal custom JS (column sort, etc.)
│   └── __init__.py
│
├── content/
│   └── platforms/                          # per-platform markdown files (r/w)
│       ├── Samsung_S22Ultra_SM8450.md
│       └── ...
│
├── config/
│   ├── settings.yaml                       # shared by v1.0 and v2.0
│   ├── settings.example.yaml
│   ├── auth.yaml                           # gitignored
│   └── overview.yaml                       # NEW: curated platform list persistence
│
├── requirements.txt                        # existing (v1.0)
├── requirements-v2.txt                     # NEW: FastAPI additions only
└── v2.py                                   # NEW: uvicorn entrypoint (2-liner)
```

---

## Structure Rationale

- **`app_v2/` as sibling to `app/`:** v1.0 runtime code stays in `app/` unchanged. A sibling package is cleaner than nesting `v2/` at repo root (avoids confusion with `app/` being v1-only). Import paths are `from app.services.result_normalizer import normalize` — identical whether called from `app/pages/` or `app_v2/routers/`.

- **`app_v2/routers/htmx/` sub-package:** Separating HTMX-fragment routes from full-page routes prevents route proliferation in one file. Full-page routes in `app_v2/routers/*.py` return `TemplateResponse` for the full page template. HTMX fragment routes in `app_v2/routers/htmx/*.py` return `TemplateResponse` for a partial only, with `block_name=` via `jinja2-fragments`.

- **`app_v2/services/` for v2-specific services:** `cache.py` and `content_service.py` are v2-specific concerns. They do not belong in `app/services/` which is the v1.0 service layer. The v2 shim (`ufs_service_v2.py`) imports `fetch_cells_core` from `app.services.ufs_service` and wraps it with the TTLCache.

- **`content/platforms/` at repo root:** The markdown content directory is not framework-specific; it should be accessible from both v1.0 and v2.0 if needed, and is conceptually separate from app code. Follows the convention of `config/` also living at repo root.

- **`requirements-v2.txt`:** Separate requirements file for v2 additions avoids polluting v1 with `fastapi`, `uvicorn`, `jinja2-fragments`, `markdown-it-py`, `cachetools`. Both files can be pip-installed in the same venv: `pip install -r requirements.txt -r requirements-v2.txt`.

- **`v2.py` entrypoint:** A minimal 2-liner (`uvicorn.run("app_v2.main:app", ...)`) keeps the entrypoint separate from `streamlit_app.py` so both apps can be started independently.

---

## Service Reuse Strategy: The `@st.cache_data` Decoupling

### The Problem

`app/services/ufs_service.py` has `@st.cache_data(ttl=300)` decorators on `list_platforms()`, `list_parameters()`, and `@st.cache_data(ttl=60)` on `fetch_cells()`. These decorators import `streamlit` at module level — which means `import app.services.ufs_service` from `app_v2/` would fail unless Streamlit is running.

### Recommended Approach: Extract Core Functions, Keep Decorators in v1

**Do not remove `@st.cache_data` from the existing functions.** The v1.0 archival promise requires that `streamlit_app.py` continues to work unchanged.

Instead, extract the SQL body of each cached function into an un-decorated `_core` variant in the same file, and leave the `@st.cache_data` wrappers as thin delegators:

```python
# app/services/ufs_service.py — after refactor

# NEW: un-decorated core functions, importable from anywhere
def list_platforms_core(db: DBAdapter, db_name: str = "") -> list[str]:
    """Raw implementation — no caching. Called by the @st.cache_data wrapper (v1.0)
    and by the TTLCache wrapper in app_v2/services/cache.py (v2.0)."""
    tbl = _safe_table(_TABLE)
    with db._get_engine().connect() as conn:
        df = pd.read_sql_query(
            sa.text(f"SELECT DISTINCT PLATFORM_ID FROM {tbl} ORDER BY PLATFORM_ID"),
            conn,
        )
    return df["PLATFORM_ID"].dropna().astype(str).tolist()


def list_parameters_core(db: DBAdapter, db_name: str = "") -> list[dict]:
    tbl = _safe_table(_TABLE)
    with db._get_engine().connect() as conn:
        df = pd.read_sql_query(
            sa.text(f"SELECT DISTINCT InfoCategory, Item FROM {tbl} ORDER BY InfoCategory, Item"),
            conn,
        )
    return df.to_dict("records")


def fetch_cells_core(
    db: DBAdapter,
    platforms: tuple[str, ...],
    infocategories: tuple[str, ...],
    items: tuple[str, ...],
    row_cap: int = 200,
    db_name: str = "",
) -> tuple[pd.DataFrame, bool]:
    # ... same SQL body as current fetch_cells, minus @st.cache_data ...


# EXISTING: @st.cache_data wrappers now delegate to _core (v1.0 unchanged externally)
@st.cache_data(ttl=300, show_spinner=False)
def list_platforms(_db: DBAdapter, db_name: str = "") -> list[str]:
    return list_platforms_core(_db, db_name)


@st.cache_data(ttl=300, show_spinner=False)
def list_parameters(_db: DBAdapter, db_name: str = "") -> list[dict]:
    return list_parameters_core(_db, db_name)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_cells(
    _db: DBAdapter,
    platforms: tuple[str, ...],
    infocategories: tuple[str, ...],
    items: tuple[str, ...],
    row_cap: int = 200,
    db_name: str = "",
) -> tuple[pd.DataFrame, bool]:
    return fetch_cells_core(_db, platforms, infocategories, items, row_cap, db_name)
```

`pivot_to_wide()` has no Streamlit coupling and is importable directly from `app_v2/` without any change.

### The v2.0 Cache Wrapper (`app_v2/services/cache.py`)

```python
# app_v2/services/cache.py
from cachetools import TTLCache, cached
from cachetools.keys import hashkey
import threading
from app.adapters.db.base import DBAdapter
from app.services.ufs_service import (
    list_platforms_core,
    list_parameters_core,
    fetch_cells_core,
)

_lock = threading.Lock()
_platforms_cache: TTLCache = TTLCache(maxsize=64, ttl=300)
_parameters_cache: TTLCache = TTLCache(maxsize=64, ttl=300)
_cells_cache: TTLCache = TTLCache(maxsize=256, ttl=60)


def list_platforms(db: DBAdapter, db_name: str = "") -> list[str]:
    key = hashkey(db_name)
    with _lock:
        if key not in _platforms_cache:
            _platforms_cache[key] = list_platforms_core(db, db_name)
        return _platforms_cache[key]


def list_parameters(db: DBAdapter, db_name: str = "") -> list[dict]:
    key = hashkey(db_name)
    with _lock:
        if key not in _parameters_cache:
            _parameters_cache[key] = list_parameters_core(db, db_name)
        return _parameters_cache[key]


def fetch_cells(db, platforms, infocategories, items, row_cap=200, db_name=""):
    key = hashkey(platforms, infocategories, items, row_cap, db_name)
    with _lock:
        if key not in _cells_cache:
            _cells_cache[key] = fetch_cells_core(db, platforms, infocategories, items, row_cap, db_name)
        return _cells_cache[key]
```

The `threading.Lock()` is mandatory: FastAPI runs routes concurrently (even in sync mode via threadpool), so the shared TTLCache must be protected. `st.cache_data` had Streamlit's session model to protect it; TTLCache does not.

### What This Achieves

| Concern | v1.0 (Streamlit) | v2.0 (FastAPI) |
|---------|-----------------|----------------|
| `list_platforms` | `@st.cache_data(ttl=300)` wrapper | `cache.py` TTLCache, lock-protected |
| `fetch_cells` | `@st.cache_data(ttl=60)` wrapper | `cache.py` TTLCache, lock-protected |
| `pivot_to_wide` | No cache (pure function) | Direct import, no cache needed |
| `result_normalizer` | Direct import | Direct import |
| `nl_agent` | Direct import | Direct import |
| `sql_validator/limiter/scrubber` | Direct import | Direct import |

---

## FastAPI Project Structure Patterns

### Pattern 1: lifespan() for startup singletons

**What:** A single `@asynccontextmanager` function passed to `FastAPI(lifespan=...)` initializes all shared resources (DB adapter, caches, agent registry) before the first request and disposes them on shutdown.

**When to use:** Always — this replaces `@app.on_event("startup")` which is deprecated.

```python
# app_v2/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import load_settings
from app.adapters.db.registry import build_adapter

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    db_cfg = next(iter(settings.databases), None)
    if db_cfg:
        app.state.db = build_adapter(db_cfg)
    app.state.settings = settings
    app.state.agent_registry = {}   # lazy: populated on first /ask request per backend
    yield
    if hasattr(app.state, "db"):
        app.state.db.dispose()

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app_v2/static"), name="static")

from app_v2.routers import overview, browse, ask, platforms, settings as settings_router
from app_v2.routers.htmx import overview as htmx_overview, browse as htmx_browse, ...

app.include_router(overview.router)
app.include_router(browse.router)
app.include_router(htmx_overview.router, prefix="/htmx")
# ...
```

### Pattern 2: Depends() for DB adapter and Settings

**What:** `app_v2/dependencies.py` provides typed `Depends()` callables. Routes declare them as parameters — FastAPI injects them per-request. No global state in route files.

```python
# app_v2/dependencies.py
from fastapi import Request
from app.adapters.db.base import DBAdapter
from app.core.config import Settings

def get_db(request: Request) -> DBAdapter:
    return request.app.state.db

def get_settings(request: Request) -> Settings:
    return request.app.state.settings
```

```python
# app_v2/routers/overview.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from app_v2.dependencies import get_db, get_settings
from app_v2.templates import templates   # Jinja2Blocks instance

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def overview_page(request: Request, db=Depends(get_db), settings=Depends(get_settings)):
    platforms = cache.list_platforms(db, settings.app.default_database)
    return templates.TemplateResponse("overview.html", {"request": request, "platforms": platforms})
```

### Pattern 3: jinja2-fragments for HTMX partials

**What:** `jinja2-fragments` (PyPI: `jinja2-fragments`, tested with FastAPI) provides `Jinja2Blocks` — a drop-in replacement for `Jinja2Templates` that accepts an optional `block_name` parameter on `TemplateResponse`. When `block_name` is set, only that Jinja2 `{% block %}` is rendered and returned; the rest of the template (including `{% extends "base.html" %}`) is ignored.

**When to use:** All HTMX routes return a `block_name=` render. All full-page routes return the full template (no `block_name`). Both share the same template file — no separate partial files required.

```python
# app_v2/templates/__init__.py
from jinja2_fragments.fastapi import Jinja2Blocks

templates = Jinja2Blocks(directory="app_v2/templates")
```

```html
<!-- app_v2/templates/overview.html -->
{% extends "base.html" %}

{% block content %}
  <div id="overview-list-container">
    {% block overview_list %}
      {% include "partials/overview_list.html" %}
    {% endblock %}
  </div>
{% endblock %}
```

```python
# app_v2/routers/htmx/overview.py  (HTMX fragment route)
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from app_v2.templates import templates

router = APIRouter()

@router.get("/overview/filter", response_class=HTMLResponse)
def filter_overview(
    request: Request,
    brand: str = "",
    soc: str = "",
    year: str = "",
    has_content: bool = False,
    db=Depends(get_db),
):
    platforms = filter_platforms(db, brand=brand, soc=soc, year=year, has_content=has_content)
    return templates.TemplateResponse(
        "overview.html",
        {"request": request, "platforms": platforms},
        block_name="overview_list",
    )
```

The HTMX trigger in the template:

```html
<!-- in partials/overview_list.html -->
<div id="overview-list"
     hx-get="/htmx/overview/filter"
     hx-trigger="change from:#brand-filter, change from:#soc-filter"
     hx-target="#overview-list"
     hx-swap="innerHTML">
  <!-- platform cards rendered here -->
</div>
```

### Pattern 4: Jinja2 template inheritance for Bootstrap shell

**What:** `base.html` contains the Bootstrap nav, `<head>` (with HTMX script tag and vendored CSS/JS `<link>`/`<script>` tags), and one `{% block content %}{% endblock %}`. All page templates `{% extends "base.html" %}` and fill the content block. HTMX partial routes render `block_name="..."` from within these same page templates.

```html
<!-- app_v2/templates/base.html -->
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}PBM2{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', path='vendor/bootstrap.min.css') }}">
  <link rel="stylesheet" href="{{ url_for('static', path='css/app.css') }}">
  <script src="{{ url_for('static', path='vendor/htmx.min.js') }}" defer></script>
  <script src="{{ url_for('static', path='vendor/bootstrap.bundle.min.js') }}" defer></script>
</head>
<body>
  <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container-fluid">
      <a class="navbar-brand" href="/">PBM2</a>
      <div class="navbar-nav">
        <a class="nav-link {% if active_tab == 'overview' %}active{% endif %}" href="/">Overview</a>
        <a class="nav-link {% if active_tab == 'browse' %}active{% endif %}" href="/browse">Browse</a>
        <a class="nav-link {% if active_tab == 'ask' %}active{% endif %}" href="/ask">Ask</a>
      </div>
    </div>
  </nav>
  <main class="container-fluid mt-3">
    {% block content %}{% endblock %}
  </main>
  <script src="{{ url_for('static', path='js/app.js') }}"></script>
</body>
</html>
```

**Structural difference between full-page templates and HTMX partials:**

| Concern | Full-page template | HTMX partial (block render) |
|---------|-------------------|-----------------------------|
| Inherits base.html | Yes (`{% extends %}`) | Implicit (block lives inside the extending template) |
| Bootstrap/HTMX scripts | In `<head>` via base | Not re-sent — already in DOM |
| Bootstrap nav | Yes | Not re-sent |
| `hx-target` | N/A | `#overview-list`, `#browse-table`, `#ai-summary-{id}` |
| `hx-swap` | N/A | `innerHTML` for list/table; `outerHTML` for AI Summary |

---

## URL Scheme

```
Full-page routes (tab navigation):
  GET /                                    → Overview tab (curated platform list)
  GET /browse                              → Browse tab (pivot grid)
  GET /ask                                 → Ask tab (NL agent)
  GET /platforms/{platform_id}             → Per-platform content page
  GET /settings                            → Settings (DB/LLM config)
  POST /settings                           → Save settings

HTMX fragment routes (no full page reload):
  GET  /htmx/overview/filter               → Filtered platform cards (query: brand, soc, year, has_content)
  POST /htmx/overview/add                  → Add platform to curated list; returns updated list fragment
  DELETE /htmx/overview/remove/{id}        → Remove platform; returns updated list fragment
  GET  /htmx/browse/results                → Pivot table fragment (query: platforms, items, swap_axes, row_cap)
  GET  /htmx/browse/export/excel           → Excel file download (not HTMX swap — browser download)
  GET  /htmx/browse/export/csv             → CSV file download
  POST /htmx/ask/result                    → NL query → result fragment (JSON body: {question, backend})
  GET  /htmx/platforms/{id}/summary        → AI Summary fragment (triggers LLM call)
  GET  /htmx/platforms/{id}/content        → Render markdown content fragment (for in-place preview)
  POST /htmx/platforms/{id}/content        → Save content (writes .md file atomically); returns updated fragment
  DELETE /htmx/platforms/{id}/content      → Delete .md file; returns empty-state fragment
```

**Naming rationale:**
- `/htmx/` prefix makes it easy to apply auth middleware, CORS rules, or rate-limiting to the fragment tier without affecting full-page routes.
- All mutating HTMX endpoints use `POST` or `DELETE` (not `GET`) — aligns with HTTP semantics and prevents accidental trigger from browser prefetch.
- Export endpoints are plain `GET` because the browser handles downloads directly; no HTMX swap occurs.

---

## FastAPI Startup / Shutdown Lifecycle

```
Process start
    │
    ▼
lifespan() startup block:
  1. load_settings() → Settings (reads config/settings.yaml, honors SETTINGS_PATH env)
  2. build_adapter(settings.databases[0]) → MySQLAdapter (SQLAlchemy engine created lazily on first query)
  3. Instantiate app.state.agent_registry = {}  (lazy: agents built on first /ask per backend type)
  4. Store app.state.db, app.state.settings, app.state.agent_registry
    │
    ▼
    yield  ← app serves requests
    │
    ▼
lifespan() shutdown block:
  1. app.state.db.dispose()  (closes SQLAlchemy connection pool)
  2. Clear agent_registry
```

**Agent factory pattern (lazy singleton per backend):**

```python
# app_v2/dependencies.py
from app.core.agent.nl_agent import build_agent
from pydantic_ai.models.openai import OpenAIChatModel

def get_agent(request: Request, backend: str = "ollama"):
    registry = request.app.state.agent_registry
    if backend not in registry:
        settings = request.app.state.settings
        llm_cfg = next((l for l in settings.llms if l.type == backend), None)
        if llm_cfg is None:
            raise ValueError(f"No LLM config found for backend '{backend}'")
        model = _build_pydantic_ai_model(llm_cfg)   # OpenAIChatModel or OllamaModel
        registry[backend] = build_agent(model)
    return registry[backend]
```

The agent objects are thread-safe to call (PydanticAI agents are stateless per `run_sync` call); the registry dict itself only needs protection during initial population (use a `threading.Lock` around the `if backend not in registry` block for safety under concurrent first-requests).

---

## Static Assets Strategy

**Use vendored files for intranet deployment.** CDN-based Bootstrap and HTMX require outbound internet access; an intranet server that cannot reach `cdn.jsdelivr.net` silently serves an unstyled page.

**Download once, commit to repo:**
```
app_v2/static/vendor/bootstrap.min.css        (Bootstrap 5.3.x)
app_v2/static/vendor/bootstrap.bundle.min.js  (Bootstrap 5.3.x + Popper)
app_v2/static/vendor/htmx.min.js              (HTMX 2.x)
```

**Mount in main.py:**
```python
app.mount("/static", StaticFiles(directory="app_v2/static"), name="static")
```

**Reference in base.html via `url_for`:**
```html
<link rel="stylesheet" href="{{ url_for('static', path='vendor/bootstrap.min.css') }}">
```

**Why not a build tool (webpack, vite):** The HTMX + minimal JS approach deliberately avoids a JS build step. For custom CSS, a single `app_v2/static/css/app.css` file is sufficient; no SASS compilation needed. If the team later wants a build step, the `static/` directory layout already separates vendor from app assets cleanly.

---

## Content Page Architecture

### Filesystem Layout

```
content/
└── platforms/
    ├── Samsung_S22Ultra_SM8450.md
    ├── Xiaomi_13Pro_SM8550.md
    └── ...
```

`PLATFORM_ID` values from `ufs_data` (`Brand_Model_SoCID`) map directly to filenames. This is safe for Linux filesystems (underscores are valid filename characters). The route parameter `{platform_id}` must be validated against a regex `^[A-Za-z0-9_-]+$` before being used as a filename.

### Atomic Write Pattern (`app_v2/services/content_service.py`)

```python
import os
import tempfile
from pathlib import Path

CONTENT_DIR = Path("content/platforms")

def read_content(platform_id: str) -> str | None:
    path = _validated_path(platform_id)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")

def write_content(platform_id: str, markdown: str) -> None:
    path = _validated_path(platform_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write: write to temp in same dir, then os.replace (rename is atomic on same FS)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(markdown)
            f.flush()
            os.fsync(f.fileno())   # durability before rename
        os.replace(tmp_path, path)  # atomic on POSIX (same filesystem guaranteed)
    except Exception:
        os.unlink(tmp_path)        # clean up temp on failure
        raise

def delete_content(platform_id: str) -> bool:
    path = _validated_path(platform_id)
    if not path.exists():
        return False
    path.unlink()
    return True

def _validated_path(platform_id: str) -> Path:
    import re
    if not re.fullmatch(r"[A-Za-z0-9_-]+", platform_id):
        raise ValueError(f"Invalid platform_id: {platform_id!r}")
    return CONTENT_DIR / f"{platform_id}.md"
```

**Why `os.replace` + same-directory temp:** `os.replace` is atomic on POSIX when source and destination are on the same filesystem. Creating the temp file in the same `content/platforms/` directory guarantees same-FS. `os.fsync()` before the rename ensures crash-safety: if the process dies mid-write, the original `.md` is untouched.

**Concurrent edit handling:** For an intranet tool with a small team, last-write-wins is acceptable. No distributed file lock is needed. If two users edit simultaneously, the last `POST /htmx/platforms/{id}/content` wins — same as editing a wiki page.

### Overview Store (`app_v2/services/overview_store.py`)

The curated platform list (add/remove from overview) needs lightweight persistence outside the DB. Use `config/overview.yaml` (add to `.gitignore` if it contains user-specific curation; or commit it as a shared team curated list). YAML load/save with `pyyaml` (already in requirements). Same atomic write pattern as content_service.

---

## Data Flow

### Full-Page Load (e.g., Overview Tab)

```
Browser GET /
    ↓
app_v2/routers/overview.py  get_overview_page()
    ↓
Depends(get_db) → app.state.db (MySQLAdapter)
Depends(get_settings) → app.state.settings
    ↓
app_v2/services/cache.py list_platforms(db, db_name)
    → TTLCache hit? return cached list
    → Miss? call app.services.ufs_service.list_platforms_core(db) → SQL → return
    ↓
overview_store.load_curated() → config/overview.yaml
content_service: which IDs have .md files (has_content map)
    ↓
templates.TemplateResponse("overview.html", {...})  ← full HTML (base + content block)
    ↓
Browser renders Bootstrap page with nav tabs
```

### HTMX Filter Swap (Overview Filter)

```
User changes Brand dropdown (hx-trigger="change from:#brand-filter")
    ↓
Browser sends:  GET /htmx/overview/filter?brand=Samsung&soc=&year=&has_content=false
                HX-Request: true  (header added by HTMX automatically)
    ↓
app_v2/routers/htmx/overview.py  filter_overview()
    ↓
filter_platforms(db, brand="Samsung", ...) → filtered list from cached platforms
    ↓
templates.TemplateResponse("overview.html", {...}, block_name="overview_list")
    ← renders ONLY the {% block overview_list %} block (no <html>, no nav, no scripts)
    ↓
Browser: hx-swap="innerHTML" on #overview-list → DOM updated in place
```

### HTMX AI Summary

```
User clicks "AI Summary" button
    ↓
hx-post="/htmx/platforms/{id}/summary"  hx-target="#ai-summary-{id}"
    ↓
app_v2/routers/htmx/platforms.py  get_ai_summary(platform_id)
    ↓
content_service.read_content(platform_id) → markdown text (or 404 if no file)
    ↓
LLMAdapter (via get_agent or direct client):
  - If OpenAI backend: scrub_paths(markdown) before sending (SAFE-06 precedent)
  - Single-shot completion: "Summarize this platform spec in 3 bullet points: {markdown}"
  - 30s timeout (httpx.Timeout)
    ↓
templates.TemplateResponse("overview.html", {"summary": text, ...}, block_name="ai_summary")
    ↓
Browser swaps summary block in-place; button replaced with summary text
```

### NL Ask Flow (HTMX)

```
User types question, submits form
    ↓
hx-post="/htmx/ask/result"  hx-target="#ask-result"  hx-swap="innerHTML"
    ↓
app_v2/routers/htmx/ask.py  run_ask(question, backend)
    ↓
agent = get_agent(request, backend)  (from registry — built once per backend)
deps = AgentDeps(db=get_db(request), agent_cfg=settings.app.agent, active_llm_type=backend)
result = run_agent(agent, question, deps)   ← same run_agent() from nl_agent.py
    ↓
if isinstance(result, ClarificationNeeded):
    → render partials/ask_clarification.html with candidate_params checkboxes
    → user checks candidates, submits second form
    → POST /htmx/ask/result with confirmed params → SQL execution
if isinstance(result, SQLResult):
    → fetch_cells or run_sql to get df
    → render partials/ask_result.html (table + explanation)
if isinstance(result, AgentRunFailure):
    → render partials/ask_error.html
    ↓
Browser swaps #ask-result in-place
```

---

## Build Order (Phase Dependencies)

This order ensures no phase can be coded before its dependencies exist:

```
Phase 1: Foundation (must exist before all other v2 phases)
  1a. requirements-v2.txt + v2.py entrypoint
  1b. app_v2/main.py (lifespan, static mount, router registration shell)
  1c. app_v2/dependencies.py (get_db, get_settings)
  1d. app_v2/templates/base.html (Bootstrap shell, HTMX script, nav tabs)
  1e. app_v2/static/vendor/ (Bootstrap 5.3.x + HTMX 2.x downloaded and committed)
  Note: No routes, no content yet — just a working "200 OK at /" with Bootstrap nav.

Phase 2: Service Refactor (must precede ALL data-fetching routes)
  2a. app/services/ufs_service.py — extract *_core() functions, keep @st.cache_data wrappers
  2b. app_v2/services/cache.py — TTLCache wrappers with threading.Lock
  2c. app_v2/services/content_service.py — atomic file r/w
  2d. app_v2/services/overview_store.py — curated list persistence
  Risk: This is the only v1.0 file that gets modified. Run full test suite (pytest) after.

Phase 3: Overview Tab
  3a. app_v2/routers/overview.py (GET /)
  3b. app_v2/routers/htmx/overview.py (filter, add, remove)
  3c. app_v2/templates/overview.html + partials/overview_list.html
  Depends on: Phase 1, Phase 2 (cache.py, overview_store.py)

Phase 4: Content Pages
  4a. app_v2/routers/platforms.py (GET /platforms/{id})
  4b. app_v2/routers/htmx/platforms.py (GET/POST/DELETE content)
  4c. app_v2/templates/platform_page.html
  Depends on: Phase 1, Phase 2 (content_service.py)

Phase 5: AI Summary
  5a. app_v2/dependencies.py — get_agent() lazy factory
  5b. app_v2/routers/htmx/platforms.py — POST /htmx/platforms/{id}/summary
  5c. app_v2/templates/partials/ai_summary.html
  Depends on: Phase 4 (content must exist for summary to summarize)

Phase 6: Browse Tab Port
  6a. app_v2/routers/browse.py (GET /browse)
  6b. app_v2/routers/htmx/browse.py (GET /htmx/browse/results, export endpoints)
  6c. app_v2/templates/browse.html + partials/browse_table.html
  Depends on: Phase 2 (cache.py with fetch_cells + pivot_to_wide already importable)

Phase 7: Ask Tab Port
  7a. app_v2/routers/ask.py (GET /ask)
  7b. app_v2/routers/htmx/ask.py (POST /htmx/ask/result + two-turn clarification)
  7c. app_v2/templates/ask.html + partials/ask_result.html, ask_clarification.html, ask_error.html
  Depends on: Phase 5 (get_agent factory), Phase 2 (nl_agent already importable)

Phase 8: Settings Port (optional, can run in parallel with Phase 6/7)
  8a. app_v2/routers/settings.py (GET/POST /settings)
  8b. app_v2/templates/settings.html
  Depends on: Phase 1 only (get_settings already injectable)
```

**Critical dependency summary:**
- Phase 2 (service refactor) is the only phase that touches v1.0 code. It must be fully tested before any subsequent phase is coded.
- Phase 5 (AI Summary) depends on Phase 4 (content pages) because the summary button is rendered on the platform page template and the summary endpoint reads a content file.
- Phase 6 and 7 can be developed in parallel once Phase 2 is done.

---

## Anti-Patterns

### Anti-Pattern 1: HTMX fragment endpoints as separate template files

**What people do:** Create `templates/partials/overview_list_fragment.html` as a standalone fragment file — no `{% extends %}`, just raw HTML. Full-page routes include it via `{% include %}`, HTMX routes render it directly.

**Why it's wrong:** The fragment and the full-page container can drift apart. Changes to data structure or Bootstrap classes must be made in two places. When the fragment is rendered standalone for HTMX, any Jinja2 variables the full page injected via `{% include %}` context are no longer available — subtle context-passing bugs.

**Do this instead:** Use `jinja2-fragments`. Keep one template file per page. HTMX routes render the same template with `block_name=` — single source of truth. The block gets all the same context the full page provides.

### Anti-Pattern 2: Instantiating MySQLAdapter in FastAPI Depends() per-request

**What people do:**
```python
def get_db(settings=Depends(get_settings)) -> DBAdapter:
    db_cfg = settings.databases[0]
    return MySQLAdapter(db_cfg)   # NEW adapter (and new SQLAlchemy engine!) per request
```

**Why it's wrong:** `MySQLAdapter._get_engine()` creates a new `create_engine()` call on each new adapter instance. A new engine = a new connection pool. Under concurrent load this exhausts MySQL's `max_connections` within minutes.

**Do this instead:** Build the adapter once in `lifespan()`, store in `app.state.db`. The `get_db` dependency reads from `app.state` — zero cost, same pool every request.

### Anti-Pattern 3: Writing files synchronously in async FastAPI route handlers

**What people do:**
```python
@router.post("/htmx/platforms/{id}/content")
async def save_content(platform_id: str, body: ContentForm):
    Path(f"content/platforms/{platform_id}.md").write_text(body.markdown)  # blocking I/O
```

**Why it's wrong:** `async def` routes in FastAPI run in the event loop. A blocking `write_text()` or `os.replace()` call blocks the entire event loop for all concurrent requests during that I/O.

**Do this instead:** Use `def` (not `async def`) for routes that do filesystem I/O, or wrap with `asyncio.to_thread()`. FastAPI automatically runs synchronous `def` routes in a threadpool. The `content_service.write_content()` function uses `def` — call it from a `def` route and FastAPI handles the threadpool dispatch.

### Anti-Pattern 4: Importing `app.services.ufs_service` at module level without the refactor

**What people do:** In `app_v2/services/cache.py`:
```python
from app.services.ufs_service import fetch_cells   # imports the @st.cache_data decorated version
```

**Why it's wrong:** The `@st.cache_data` decorated function imports `streamlit` at module level inside `ufs_service.py` (via `import streamlit as st`). In the v2.0 FastAPI context, Streamlit is not initialized — calls to the decorated function will raise `streamlit.errors.NoSessionContext` or silently miscache because there is no Streamlit session.

**Do this instead:** The Phase 2 service refactor (extract `*_core()` functions) must land before any `app_v2/` code imports from `app.services.ufs_service`. Cache.py imports only `fetch_cells_core`, `list_platforms_core`, `list_parameters_core` — these have no Streamlit import.

---

## Integration Points

### Modified vs. New vs. Unchanged

| File | Status | Change |
|------|--------|--------|
| `app/services/ufs_service.py` | MODIFIED | Extract `*_core()` un-decorated functions; wrap existing `@st.cache_data` functions to delegate to `*_core()`. v1.0 public API unchanged. |
| `app/services/result_normalizer.py` | UNCHANGED | Imported directly by `app_v2/` |
| `app/services/sql_validator.py` | UNCHANGED | Imported directly by `app_v2/` |
| `app/services/sql_limiter.py` | UNCHANGED | Imported directly by `app_v2/` |
| `app/services/path_scrubber.py` | UNCHANGED | Imported directly by `app_v2/` |
| `app/core/agent/nl_agent.py` | UNCHANGED | Imported directly by `app_v2/` |
| `app/core/config.py` | UNCHANGED | Imported directly by `app_v2/` |
| `app/adapters/db/mysql.py` | UNCHANGED | Used via `build_adapter()` in lifespan |
| `app/adapters/llm/*.py` | UNCHANGED | Used via LLM registry in `get_agent()` |
| `app_v2/` | NEW | FastAPI app package |
| `content/platforms/` | NEW | Markdown content directory |
| `config/overview.yaml` | NEW | Curated platform list persistence |
| `requirements-v2.txt` | NEW | FastAPI-specific additions |
| `v2.py` | NEW | `uvicorn.run("app_v2.main:app", ...)` entrypoint |

### Shared State Risks

| Risk | Scenario | Mitigation |
|------|----------|------------|
| SQLAlchemy connection pool contention | v1.0 Streamlit and v2.0 FastAPI running simultaneously, both using same MySQLAdapter (same engine) | They use DIFFERENT engine instances — each app creates its own via `build_adapter()`. No shared pool unless explicitly designed. |
| TTLCache coherence (v1 vs v2) | v1 `@st.cache_data` and v2 `TTLCache` have different TTL clocks for the same data | Acceptable: both are 300s TTL on catalog data. Slight staleness divergence is tolerable. |
| Content file concurrent writes | Two v2.0 users edit the same platform page simultaneously | Last-write-wins via `os.replace`. Acceptable for small intranet team. |
| Overview store concurrent writes | Multiple overview add/remove requests in flight | Same atomic write pattern. Last write wins. Add optimistic locking (ETag) only if contention is observed in practice. |
| Agent registry dict concurrent first-population | Two requests for `/ask?backend=openai` arrive before the first one populates the registry | Add `threading.Lock` around `if backend not in registry:` block in `get_agent()`. |

### New Library Dependencies (`requirements-v2.txt`)

| Library | Version | Purpose |
|---------|---------|---------|
| fastapi | `>=0.115,<1.0` | Web framework |
| uvicorn[standard] | `>=0.30` | ASGI server |
| jinja2 | `>=3.1` | Template engine (likely already transitively installed) |
| jinja2-fragments | `>=1.3` | Block-level template rendering for HTMX partials |
| python-multipart | `>=0.0.9` | Required for FastAPI form parsing (`Content-Type: multipart/form-data`) |
| markdown-it-py | `>=3.0` | Markdown → HTML rendering for content pages |
| cachetools | `>=5.3` | TTLCache replacement for `@st.cache_data` in v2.0 |

---

## Scaling Considerations

| Scale | Architecture Adjustment |
|-------|------------------------|
| 1–5 simultaneous users (current intranet) | No changes needed; single uvicorn worker, shared connection pool |
| 5–20 users | Increase `max_overflow` on SQLAlchemy engine; set `uvicorn --workers 2`; note that in-process TTLCache is not shared across workers — add Redis or restart workers on a schedule if cache coherence matters |
| 20+ users | Multi-worker uvicorn behind nginx; replace TTLCache with Redis (`fastapi-cache2` with Redis backend); consider MySQL read replica |

For this intranet tool, 1–5 simultaneous users is the realistic target. Single-worker uvicorn with the in-process TTLCache is the right starting point.

---

## Sources

- FastAPI lifespan events (official): https://fastapi.tiangolo.com/advanced/events/
- FastAPI static files (official): https://fastapi.tiangolo.com/tutorial/static-files/
- FastAPI Jinja2 templates (official): https://fastapi.tiangolo.com/advanced/templates/
- jinja2-fragments PyPI: https://pypi.org/project/jinja2-fragments/
- jinja2-fragments GitHub (FastAPI integration): https://github.com/sponsfreixes/jinja2-fragments
- HTMX template fragments essay: https://htmx.org/essays/template-fragments/
- cachetools PyPI: https://pypi.org/project/cachetools/
- Python atomic file writes (`os.replace` pattern): https://code.activestate.com/recipes/579097-safely-and-atomically-write-to-a-file/
- FastAPI + HTMX production guide: https://medium.com/@sylvesterranjithfrancis/complete-guide-building-production-ready-web-apps-with-fastapi-and-htmx-from-setup-to-deployment-3010b1c8ff5c
- FastAPI singleton + DI patterns: https://medium.com/@hieutrantrung.it/using-fastapi-like-a-pro-with-singleton-and-dependency-injection-patterns-28de0a833a52

---
*Architecture research for: PBM2 v2.0 Bootstrap Shell — FastAPI + Bootstrap 5 + HTMX parallel rewrite*
*Researched: 2026-04-23*
