"""FastAPI application entrypoint for app_v2 (v2.0 Bootstrap Shell, Phase 1).

Starts with: uvicorn app_v2.main:app --port 8000 [--reload for dev]

Lifespan (INFRA-03) initializes:
  app.state.settings          — Pydantic Settings loaded from config/settings.yaml
  app.state.db                — DBAdapter built from settings.databases[0] (None if
                                no databases configured — Phase 1 smoke tests allow this)
  app.state.agent_registry    — dict[str, Agent] — lazy per-LLM-backend cache,
                                populated by Phase 3/5 get_agent() factory

Exception handlers render Bootstrap-styled 404.html / 500.html (INFRA-02).

Static mount serves app_v2/static/ (vendored Bootstrap/HTMX/Bootstrap Icons) at
/static/ — intranet deployments do not need outbound internet access (INFRA-04).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from html import escape

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.adapters.db.registry import build_adapter
from app.core.config import load_settings

from app_v2.templates import templates

_log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared singletons on startup; dispose on shutdown.

    Body is synchronous — FastAPI awaits the enter/exit; the body runs inline
    (see CONTEXT.md decision). Do NOT add async work here unless it is genuinely
    awaitable (e.g., aiofiles startup). SQLAlchemy engine creation is sync and
    fine.
    """
    settings = load_settings()
    app.state.settings = settings
    app.state.agent_registry = {}  # populated lazily by Phase 3/5

    # Phase 3: per-turn registry (cancel_event + pending_question) — see app/core/agent/chat_session.py
    app.state.chat_turns = {}
    # Phase 3: per-session message_history store (D-CHAT-15 sliding window source) — same module
    app.state.chat_sessions = {}

    # Initialize default DB adapter if configured. Phase 1 smoke tests can run
    # without a DB (no queries executed yet) — if settings.databases is empty or
    # the default database cannot be resolved, lifespan still succeeds.
    app.state.db = None
    default_name = getattr(settings.app, "default_database", "")
    db_cfg = None
    if default_name:
        db_cfg = next((d for d in settings.databases if d.name == default_name), None)
    if db_cfg is None and settings.databases:
        db_cfg = settings.databases[0]
    if db_cfg is not None:
        try:
            app.state.db = build_adapter(db_cfg)
        except Exception as exc:  # noqa: BLE001 — startup resilience
            _log.warning("Failed to build DB adapter at startup: %s", exc)

    # D-27: ensure content/platforms/ exists for Phase 03 markdown CRUD.
    # Creating it at startup means content_store.read/write/delete never has
    # to handle a "directory missing" branch. Same idiom as overview_store
    # YAML directory creation in _atomic_write.
    content_dir = Path("content/platforms")
    try:
        content_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # noqa: BLE001 — startup resilience
        _log.warning("Failed to create content/platforms/: %s", exc)

    # Joint Validation drop-folder root (D-JV-13). Phase 1 Plan 04.
    # Mirrors content/platforms mkdir above so the StaticFiles mount below
    # has a guaranteed directory at startup (StaticFiles check_dir=True default
    # raises if missing) AND so the drop-folder workflow (D-JV-09) works on
    # cold-start without manual mkdir.
    jv_dir = Path("content/joint_validation")
    try:
        jv_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # noqa: BLE001 — startup resilience
        _log.warning("Failed to create content/joint_validation/: %s", exc)

    # NOTE on Pitfall 18 (Ollama cold-start) — DEVIATION from RESEARCH.md Q3:
    # RESEARCH.md recommended a lifespan-time Ollama warmup ping. We deviate
    # and rely solely on the 60s read timeout configured in summary_service
    # _build_client (see plan 03-03). Rationale: the app must start cleanly
    # even if Ollama is unreachable; a first-request cold start is acceptable
    # for an internal tool with low concurrency. Lifespan warmup is deferred
    # until cold-start latency proves user-visible. NO warmup call is added
    # here — this comment exists to make the deviation auditable.

    try:
        yield
    finally:
        db = getattr(app.state, "db", None)
        if db is not None and hasattr(db, "dispose"):
            try:
                db.dispose()
            except Exception as exc:  # noqa: BLE001
                _log.warning("Error disposing DB adapter: %s", exc)


app = FastAPI(
    lifespan=lifespan,
    title="PBM2 v2.0 Bootstrap Shell",
    # Hide /docs on intranet — enable explicitly when needed
    docs_url="/docs",
    redoc_url=None,
)

# Joint Validation static mount (D-JV-13). Registered BEFORE /static so that
# requests to /static/joint_validation/... match this mount instead of the
# parent /static mount. See RESEARCH.md Pitfall 10: Starlette dispatches mounts
# by registration order (longest-prefix-first is NOT automatic).
app.mount(
    "/static/joint_validation",
    StaticFiles(
        directory="content/joint_validation",
        html=False,            # Do NOT auto-serve index.html for bare folder URLs
        follow_symlink=False,  # Default; explicit for documentation
    ),
    name="joint_validation_static",
)

# Static mount BEFORE router registration so url_for('static', path=...) resolves
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _is_htmx_request(request: Request) -> bool:
    """Return True when the request was issued by HTMX.

    HTMX always sends `HX-Request: true` on its XHR calls. Used by the
    exception handlers to pick a fragment template (no base.html shell)
    over a full page — otherwise the htmx-error-handler.js swap would
    inject an entire HTML document (navbar + body + ...) into
    `#htmx-error-container`, producing a duplicate navbar beneath the
    real one.
    """
    return request.headers.get("HX-Request") == "true"


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Render Bootstrap-styled 404/500 pages (INFRA-02).

    For 404 and 500 return the custom template. Other status codes fall through
    to the default response. HTMX requests get fragment templates so
    htmx-error-handler.js can swap them into `#htmx-error-container` without
    re-injecting the base.html shell.
    """
    htmx = _is_htmx_request(request)
    if exc.status_code == 404:
        tpl = "_404_fragment.html" if htmx else "404.html"
        return templates.TemplateResponse(request, tpl, {"detail": exc.detail}, status_code=404)
    if exc.status_code == 500:
        tpl = "_500_fragment.html" if htmx else "500.html"
        return templates.TemplateResponse(request, tpl, {"detail": exc.detail}, status_code=500)
    # Fall through to FastAPI default for other codes.
    # exc.detail is escaped to prevent XSS — Jinja2 autoescape does not apply here.
    return HTMLResponse(
        content=f"<h1>HTTP {exc.status_code}</h1><p>{escape(str(exc.detail))}</p>",
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all: render 500 for any unhandled exception. Fragment for HTMX,
    full page for direct browser navigation."""
    _log.exception("Unhandled exception on %s: %s", request.url.path, exc)
    detail = f"{type(exc).__name__}: Internal server error"
    tpl = "_500_fragment.html" if _is_htmx_request(request) else "500.html"
    return templates.TemplateResponse(request, tpl, {"detail": detail}, status_code=500)


# Router registration — keep imports at the bottom to avoid circular deps
# ORDER MATTERS: overview first (owns GET /); platforms next (prefix=/platforms,
# Phase 03 detail page + content CRUD); summary AFTER platforms (also prefix
# =/platforms, owns POST /platforms/{pid}/summary); browse owns /browse +
# /browse/grid (Phase 04); ask owns /ask + /ask/query + /ask/confirm
# (Phase 06); settings owns /settings/llm (Phase 06); root last (now empty
# shell; Phase 06 deleted the GET /ask stub — see routers/root.py docstring).
# ask + settings registered BEFORE root as defense-in-depth: even if a future
# commit accidentally re-adds an /ask stub to root.py, the real ask router
# still wins. Mirrors the Phase 4 browse-before-root precedent.
from app_v2.routers import overview  # noqa: E402
from app_v2.routers import platforms  # noqa: E402
from app_v2.routers import summary  # noqa: E402
from app_v2.routers import joint_validation  # noqa: E402  Phase 1 Plan 04
from app_v2.routers import browse  # noqa: E402
from app_v2.routers import ask  # noqa: E402
from app_v2.routers import components  # noqa: E402  Phase 4 Plan 04 — GET /_components
from app_v2.routers import settings as settings_router  # noqa: E402 — alias to avoid collision with the Settings model
from app_v2.routers import root  # noqa: E402

app.include_router(overview.router)
app.include_router(platforms.router)
app.include_router(summary.router)
app.include_router(joint_validation.router)
app.include_router(browse.router)
app.include_router(ask.router)
app.include_router(settings_router.router)
app.include_router(components.router)  # Phase 4 Plan 04 — GET /_components showcase. Mounted before root per main.py:189-197 docstring (root last).
app.include_router(root.router)
