"""Browse tab routes — pivot grid + URL round-trip (Phase 4).

Owns: GET /browse, POST /browse/grid.

Phase 1's GET /browse stub in routers/root.py is DELETED in this plan
(Task 3) — the include_router order in main.py registers `browse` BEFORE
`root`, but to avoid any chance of route shadowing the stub is removed.

INFRA-05 + D-34: ALL routes are sync `def`. SQLAlchemy is sync; FastAPI
dispatches `def` routes to the threadpool. NEVER use `async def` here.

URL round-trip (D-30..D-33):
- GET /browse?platforms=A&platforms=B&params=cat%20%C2%B7%20item&swap=1
  pre-renders the grid AND pre-checks the popover checkboxes (BROWSE-V2-05).
- POST /browse/grid sets HX-Push-Url to the canonical /browse?... URL so
  the address bar reflects the shareable URL, NOT /browse/grid (Pitfall 2).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse

from app.adapters.db.base import DBAdapter
from app_v2.services.browse_service import _build_browse_url, build_view_model
from app_v2.templates import templates

router = APIRouter()


def get_db(request: Request) -> DBAdapter | None:
    """Return the shared DBAdapter from app.state (set by lifespan).

    Mirrors overview/platforms idiom — None when no databases are configured
    (Phase 1 contract). build_view_model handles db=None gracefully.
    """
    return getattr(request.app.state, "db", None)


def _resolve_db_name(db: DBAdapter | None) -> str:
    """Pull the configured database name off the adapter for cache partitioning.

    The TTLCache wrappers in app_v2/services/cache.py partition by db_name
    (the adapter object itself is unhashable). Empty string is acceptable
    when the adapter is None — the empty-selection short-circuit handles it.
    """
    if db is None:
        return ""
    cfg = getattr(db, "config", None)
    return getattr(cfg, "name", "") if cfg is not None else ""


@router.get("/browse", response_class=HTMLResponse)
def browse_page(
    request: Request,
    # NOTE: Pydantic v2 (2.13.x) + FastAPI 0.136.x reject the combination
    # of `Query(default_factory=list)` AND a parameter default `= []` —
    # raises "cannot specify both default and default_factory". Use ONLY
    # default_factory (canonical Pydantic v2 idiom). Empty omitted query
    # key still resolves to [], not None.
    platforms: Annotated[list[str], Query(default_factory=list)],
    params: Annotated[list[str], Query(default_factory=list)],
    swap: Annotated[str, Query()] = "",
    db: DBAdapter | None = Depends(get_db),
):
    """Initial GET — pre-renders the grid from URL state (BROWSE-V2-05).

    Renders the FULL page including the pre-rendered grid (server-side).
    Pre-checking popover checkboxes happens via `vm.selected_platforms` /
    `vm.selected_params` consumed by the template (Plan 04-03); pre-rendering
    the grid avoids a redundant HTMX request after page load.

    swap is a string ("1" or "") per D-31. Coercion to bool happens at the
    boundary into build_view_model.
    """
    db_name = _resolve_db_name(db)
    vm = build_view_model(
        db,
        db_name,
        selected_platforms=platforms,
        selected_param_labels=params,
        swap_axes=(swap == "1"),
    )
    ctx = {"active_tab": "browse", "page_title": "Browse", "vm": vm}
    return templates.TemplateResponse(request, "browse/index.html", ctx)


@router.post("/browse/grid", response_class=HTMLResponse)
def browse_grid(
    request: Request,
    platforms: Annotated[list[str], Form()] = [],
    params: Annotated[list[str], Form()] = [],
    swap: Annotated[str, Form()] = "",
    db: DBAdapter | None = Depends(get_db),
):
    """Grid fragment — fired by Apply / swap-axes / Clear-all (BROWSE-V2-01).

    Returns ONLY the named blocks: `grid` (innerHTML target #browse-grid),
    `count_oob` (OOB swap to #grid-count), `warnings_oob` (cap-warning slot).

    D-32 + Pitfall 2: sets `HX-Push-Url` response header to the canonical
    /browse?... URL. The response header overrides the `hx-push-url`
    attribute so the address bar shows /browse?... (shareable), not the
    POST URL /browse/grid (which would 405 on reload).

    Clear-all (D-18) reuses this same route with empty form fields — no
    separate clear endpoint exists per CONTEXT.md decision D-18.
    """
    db_name = _resolve_db_name(db)
    vm = build_view_model(
        db,
        db_name,
        selected_platforms=platforms,
        selected_param_labels=params,
        swap_axes=(swap == "1"),
    )
    ctx = {"vm": vm}
    response = templates.TemplateResponse(
        request,
        "browse/index.html",
        ctx,
        block_names=["grid", "count_oob", "warnings_oob"],
    )
    response.headers["HX-Push-Url"] = _build_browse_url(
        platforms, params, swap == "1"
    )
    return response
