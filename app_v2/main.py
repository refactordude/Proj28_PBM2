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

# Static mount BEFORE router registration so url_for('static', path=...) resolves
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Render Bootstrap-styled 404/500 pages (INFRA-02).

    For 404 and 500 return the custom template. Other status codes fall through
    to the default response.
    """
    if exc.status_code == 404:
        return templates.TemplateResponse(request, "404.html", {"detail": exc.detail}, status_code=404)
    if exc.status_code == 500:
        return templates.TemplateResponse(request, "500.html", {"detail": exc.detail}, status_code=500)
    # Fall through to FastAPI default for other codes.
    # exc.detail is escaped to prevent XSS — Jinja2 autoescape does not apply here.
    return HTMLResponse(
        content=f"<h1>HTTP {exc.status_code}</h1><p>{escape(str(exc.detail))}</p>",
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all: render 500.html for any unhandled exception."""
    _log.exception("Unhandled exception on %s: %s", request.url.path, exc)
    return templates.TemplateResponse(request, "500.html", {"detail": f"{type(exc).__name__}: Internal server error"}, status_code=500)


# Router registration — keep imports at the bottom to avoid circular deps
from app_v2.routers import root  # noqa: E402

app.include_router(root.router)
