"""Overview tab routes — GET /, GET /overview, POST /overview/add, POST /overview/grid.

All routes are def (INFRA-05 — FastAPI dispatches to threadpool so sync SQLAlchemy
never blocks the event loop).

Security (PITFALLS.md Pitfall 2): every user-supplied platform_id is validated with
the ^[A-Za-z0-9_\\-]{1,128}$ regex via FastAPI Form validation BEFORE it reaches
overview_store or any filesystem-adjacent code.

Phase 5 (D-OV-04) overhaul:
- GET / and GET /overview both render the full Overview page; both consume
  build_overview_grid_view_model from app_v2.services.overview_grid_service.
- POST /overview/grid replaces the legacy POST /overview/filter +
  /overview/filter/reset endpoints; it returns ONLY the grid + count_oob +
  filter_badges_oob blocks and sets HX-Push-Url to a canonical /overview?... URL.
- DELETE /overview/<pid> is REMOVED (Remove button gone per user lock).
- POST /overview/add is preserved per D-OV-11; success returns
  HTTP 200 with HX-Redirect: /overview so HTMX does a full page reload.

Filter and sort state is carried entirely in the URL query string per D-OV-13;
there is no server-side session.
"""
from __future__ import annotations

import urllib.parse
from pathlib import Path as _Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, Response

from app.adapters.db.base import DBAdapter
from app_v2.data.platform_parser import parse_platform_id
from app_v2.data.soc_year import get_year
from app_v2.services.cache import list_platforms
from app_v2.services.llm_resolver import resolve_active_backend_name  # Plan 03-01 — single source of truth
from app_v2.services.overview_filter import has_content_file
from app_v2.services.overview_grid_service import (
    FILTERABLE_COLUMNS,
    OverviewGridViewModel,
    build_overview_grid_view_model,
)
from app_v2.services.overview_store import (
    DuplicateEntityError,
    add_overview,
    load_overview,
)
from app_v2.templates import templates

router = APIRouter()

# Pitfall 2: strict PLATFORM_ID regex — rejects `../` and any non-alnum-underscore-hyphen.
PLATFORM_ID_PATTERN = r"^[A-Za-z0-9_\-]{1,128}$"

# Base directory for per-platform markdown content pages (Phase 3 CRUD target).
# Phase 5 reads frontmatter via build_overview_grid_view_model; tests
# monkeypatch this constant to a tmp_path/content/platforms location.
CONTENT_DIR: _Path = _Path("content/platforms")


def get_db(request: Request) -> DBAdapter | None:
    """Return the shared DBAdapter from app.state (set by lifespan)."""
    return getattr(request.app.state, "db", None)


def _entity_dict(entity) -> dict:
    """Enrich an OverviewEntity with brand/soc_raw/year/has_content for legacy template rendering.

    Phase 2 helper retained for transitional template compatibility during Wave 3
    (Plan 05-05 rewrites overview/index.html; until then the existing template
    needs this shape). Once Plan 05-05 lands, this becomes dead code.
    """
    brand, _model, soc_raw = parse_platform_id(entity.platform_id)
    return {
        "platform_id": entity.platform_id,
        "brand": brand,
        "soc_raw": soc_raw,
        "year": get_year(soc_raw),
        "has_content": has_content_file(entity.platform_id, CONTENT_DIR),
    }


def _build_overview_context(
    entities: list[dict],
    all_platform_ids: list[str],
    selected_brand: str | None = None,
    selected_soc: str | None = None,
    selected_year: str | None = None,
    selected_has_content: bool = False,
    active_filter_count: int = 0,
    backend_name: str = "Ollama",
) -> dict:
    """Build the legacy Phase 2 template context (transitional — see _entity_dict).

    Filter dropdown options are derived from the CURRENT curated list (not the full DB
    catalog) so dropdowns only show brands/SoCs/years actually present. Year dropdown
    is sorted DESCENDING (newest first) per UI-SPEC Specifics.
    """
    filter_brands = sorted({e["brand"] for e in entities if e["brand"]})
    filter_socs = sorted({e["soc_raw"] for e in entities if e["soc_raw"]})
    filter_years = sorted({e["year"] for e in entities if e["year"] is not None}, reverse=True)
    return {
        "active_tab": "overview",
        "page_title": "Overview",
        "placeholder_message": None,
        "entities": entities,
        "all_platform_ids": all_platform_ids,
        "filter_brands": filter_brands,
        "filter_socs": filter_socs,
        "filter_years": filter_years,
        "selected_brand": selected_brand,
        "selected_soc": selected_soc,
        "selected_year": selected_year,
        "selected_has_content": selected_has_content,
        "active_filter_count": active_filter_count,
        "filters_open": True,  # Server-rendered default; localStorage overrides client-side.
        "backend_name": backend_name,
    }


def _resolve_curated_pids() -> list[str]:
    """Load the curated PLATFORM_ID list from overview_store.

    Phase 2's overview_store is the source of truth (config/overview.yaml).
    This wrapper centralizes the call so route bodies stay short.
    """
    entities = load_overview()
    return [e.platform_id for e in entities]


def _parse_filter_dict(
    status: list[str],
    customer: list[str],
    ap_company: list[str],
    device: list[str],
    controller: list[str],
    application: list[str],
) -> dict[str, list[str]]:
    """Bundle the 6 filter form lists into a dict shape the service expects.

    Filter columns enumerated explicitly (not iterated from FILTERABLE_COLUMNS)
    so the function signature mirrors FastAPI's Form() / Query() parameter
    list 1:1 — adding a new filter is a 3-line edit (sig + dict + form param).
    """
    return {
        "status": status,
        "customer": customer,
        "ap_company": ap_company,
        "device": device,
        "controller": controller,
        "application": application,
    }


def _build_overview_url(
    filters: dict[str, list[str]],
    sort_col: str,
    sort_order: str,
) -> str:
    """Compose canonical /overview?status=A&status=B&...&sort=start&order=desc URL.

    D-OV-13: repeated keys for multi-value (?status=A&status=B). Pitfall 6
    from Phase 4 D-32: use quote_via=urllib.parse.quote so spaces encode as
    %20 (URL-style), not + (form-style).

    sort + order are always emitted (even when at defaults) so the URL is
    explicit and bookmarkable. Empty filter values are dropped.
    """
    pairs: list[tuple[str, str]] = []
    for col in ("status", "customer", "ap_company", "device", "controller", "application"):
        for v in filters.get(col, []) or []:
            if v:  # drop empty / None
                pairs.append((col, v))
    if sort_col:
        pairs.append(("sort", sort_col))
    if sort_order:
        pairs.append(("order", sort_order))
    if not pairs:
        return "/overview"
    qs = urllib.parse.urlencode(pairs, quote_via=urllib.parse.quote)
    return f"/overview?{qs}"


@router.get("/", response_class=HTMLResponse)
@router.get("/overview", response_class=HTMLResponse)
def overview_page(
    request: Request,
    # NOTE (Phase 4 04-02 lesson): Pydantic v2.13.x + FastAPI 0.136.x reject the
    # combination of `Query(default_factory=list)` AND a parameter default `= []`
    # — raises "cannot specify both default and default_factory". GET query params
    # use `default_factory` ONLY; POST `Form()` params keep `= []` (Pydantic
    # accepts Form with literal default). Empty omitted query key still resolves
    # to [], not None.
    status:      Annotated[list[str], Query(default_factory=list)],
    customer:    Annotated[list[str], Query(default_factory=list)],
    ap_company:  Annotated[list[str], Query(default_factory=list)],
    device:      Annotated[list[str], Query(default_factory=list)],
    controller:  Annotated[list[str], Query(default_factory=list)],
    application: Annotated[list[str], Query(default_factory=list)],
    sort:        Annotated[str, Query()] = "",
    order:       Annotated[str, Query()] = "",
    db: DBAdapter | None = Depends(get_db),
):
    """Render the full Overview tab (OVERVIEW-V2-01..06).

    Both GET / and GET /overview route here (D-OV-04). Filter and sort
    state come from URL query params per D-OV-13. Empty params → service
    uses defaults (sort_col='start', sort_order='desc'; no filters
    applied).

    Context dict carries BOTH the new `vm` (consumed by Plan 05-05's
    rewritten template) AND the legacy keys (entities, all_platform_ids,
    filter_brands, etc.) so the existing Phase 2 template renders without
    500 in the interim wave-3 state where the template rewrite has not
    yet landed. Once Plan 05-05 rewrites overview/index.html, the
    legacy keys become dead context entries — harmless.
    """
    curated_pids = _resolve_curated_pids()
    filters = _parse_filter_dict(status, customer, ap_company, device, controller, application)

    vm: OverviewGridViewModel = build_overview_grid_view_model(
        curated_pids=curated_pids,
        content_dir=CONTENT_DIR,
        filters=filters,
        sort_col=sort or None,
        sort_order=order or None,
    )

    # ---- Legacy Phase 2 context (kept for transitional template render) ----
    entities_raw = load_overview()
    entities = [_entity_dict(e) for e in entities_raw]
    all_platform_ids: list[str] = []
    try:
        all_platform_ids = list(list_platforms(db, db_name=""))  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 — catalog load is non-fatal (UI degrades gracefully)
        all_platform_ids = []
    backend_name = resolve_active_backend_name(getattr(request.app.state, "settings", None), request)
    legacy_ctx = _build_overview_context(
        entities=entities,
        all_platform_ids=all_platform_ids,
        backend_name=backend_name,
    )
    # ---- End legacy block ----

    ctx = {
        **legacy_ctx,
        "vm": vm,
        "selected_filters": filters,
        "active_filter_counts": vm.active_filter_counts,
        "sort_col": vm.sort_col,
        "sort_order": vm.sort_order,
    }
    return templates.TemplateResponse(request, "overview/index.html", ctx)


@router.post("/overview/add", response_class=HTMLResponse)
def add_platform(
    request: Request,
    platform_id: Annotated[str, Form(pattern=PLATFORM_ID_PATTERN, min_length=1, max_length=128)],
    db: DBAdapter | None = Depends(get_db),
):
    """Add a platform to the curated list (OVERVIEW-03 + OVERVIEW-V2-06).

    Per D-OV-11 (Phase 5), success returns HTTP 200 with HX-Redirect: /overview
    so HTMX triggers a full page reload. Synthesizing a one-row HTMX swap
    was rejected because the new row's frontmatter (content/platforms/<pid>.md)
    may not exist at the moment of add — full GET /overview is simpler and
    always correct.

    Error paths return plain-text Response with the relevant HTTP error
    code; the global HTMX `htmx:beforeSwap` 4xx handler (INFRA-02) surfaces
    the message in the global error banner. Plain text avoids coupling to
    Plan 05-05's deletion of overview/_filter_alert.html.

    Returns:
      200 + HX-Redirect: /overview on success
      404 + plain text on unknown platform_id
      409 + plain text on duplicate
      422 (FastAPI) on regex failure
    """
    catalog: list[str] = []
    try:
        catalog = list(list_platforms(db, db_name=""))  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 — catalog load failure is non-fatal
        catalog = []
    if platform_id not in catalog:
        return Response(
            status_code=404,
            content=f"Unknown platform: {platform_id}. Choose from the dropdown.",
            media_type="text/plain",
        )

    try:
        _ = add_overview(platform_id)
    except DuplicateEntityError:
        return Response(
            status_code=409,
            content=f"Already in your overview: {platform_id}",
            media_type="text/plain",
        )

    # D-OV-11: full GET /overview reload after successful add.
    return Response(status_code=200, headers={"HX-Redirect": "/overview"})


@router.post("/overview/grid", response_class=HTMLResponse)
def overview_grid(
    request: Request,
    status:      Annotated[list[str], Form()] = [],
    customer:    Annotated[list[str], Form()] = [],
    ap_company:  Annotated[list[str], Form()] = [],
    device:      Annotated[list[str], Form()] = [],
    controller:  Annotated[list[str], Form()] = [],
    application: Annotated[list[str], Form()] = [],
    sort:        Annotated[str, Form()] = "",
    order:       Annotated[str, Form()] = "",
    db: DBAdapter | None = Depends(get_db),
):
    """Grid fragment swap — fired by picker_popover auto-commit (D-15b)
    or sortable column header click (D-OV-07). Implements OVERVIEW-V2-04
    + OVERVIEW-V2-06.

    Returns ONLY the named blocks: 'grid' (innerHTML target #overview-grid),
    'count_oob' (OOB swap to the count caption), 'filter_badges_oob' (six
    picker badge spans, mirrors Phase 4 D-14(b) gap-3 pattern).

    Sets HX-Push-Url to canonical /overview?... URL so the address bar
    reflects the shareable URL, NOT /overview/grid (Pitfall 2 from Phase 4
    D-32).
    """
    curated_pids = _resolve_curated_pids()
    filters = _parse_filter_dict(status, customer, ap_company, device, controller, application)

    vm: OverviewGridViewModel = build_overview_grid_view_model(
        curated_pids=curated_pids,
        content_dir=CONTENT_DIR,
        filters=filters,
        sort_col=sort or None,
        sort_order=order or None,
    )

    ctx = {
        "vm": vm,
        "selected_filters": filters,
        "active_filter_counts": vm.active_filter_counts,
        "sort_col": vm.sort_col,
        "sort_order": vm.sort_order,
    }
    response = templates.TemplateResponse(
        request,
        "overview/index.html",
        ctx,
        block_names=["grid", "count_oob", "filter_badges_oob"],
    )
    # D-OV-04 + Pitfall 6 from Phase 4: server-set push URL (canonical, not /overview/grid).
    response.headers["HX-Push-Url"] = _build_overview_url(
        filters, vm.sort_col, vm.sort_order
    )
    return response


# Note: FILTERABLE_COLUMNS is imported for symmetry with the service surface
# (validation tests + future router additions). Re-exported intentionally.
__all__ = [
    "router",
    "PLATFORM_ID_PATTERN",
    "CONTENT_DIR",
    "FILTERABLE_COLUMNS",
]
