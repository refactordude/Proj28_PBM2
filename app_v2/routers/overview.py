"""Overview tab routes — GET /, POST /overview/add, DELETE /overview/{platform_id}.

All routes are def (INFRA-05 — FastAPI dispatches to threadpool so sync SQLAlchemy
never blocks the event loop).

Security (PITFALLS.md Pitfall 2): every user-supplied platform_id is validated with
the ^[A-Za-z0-9_\\-]{1,128}$ regex via FastAPI Path(..., pattern=...) / Form validation
BEFORE it reaches overview_store or any filesystem-adjacent code. This plan does not
touch content/ directory files (Phase 3 does); the regex is still enforced here as
defense in depth because the filter task (Plan 02-03) WILL stat content/platforms/*.md.

Filter endpoints (POST /overview/filter, POST /overview/filter/reset) are implemented
in Plan 02-03 — this module pre-computes the filter dropdown options (brand/soc/year
sets derived from the curated list) so 02-03's filter route is purely a re-render.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Path, Request
from fastapi.responses import HTMLResponse, Response

from app.adapters.db.base import DBAdapter
from app_v2.data.platform_parser import parse_platform_id
from app_v2.data.soc_year import get_year
from app_v2.services.cache import list_platforms
from app_v2.services.overview_store import (
    DuplicateEntityError,
    add_overview,
    load_overview,
    remove_overview,
)
from app_v2.templates import templates

router = APIRouter()

# Pitfall 2: strict PLATFORM_ID regex — rejects `../` and any non-alnum-underscore-hyphen.
PLATFORM_ID_PATTERN = r"^[A-Za-z0-9_\-]{1,128}$"


def get_db(request: Request) -> DBAdapter | None:
    """Return the shared DBAdapter from app.state (set by lifespan)."""
    return getattr(request.app.state, "db", None)


def _entity_dict(entity) -> dict:
    """Enrich an OverviewEntity with brand/soc_raw/year for template rendering."""
    brand, _model, soc_raw = parse_platform_id(entity.platform_id)
    return {
        "platform_id": entity.platform_id,
        "brand": brand,
        "soc_raw": soc_raw,
        "year": get_year(soc_raw),
    }


def _build_overview_context(
    entities: list[dict],
    all_platform_ids: list[str],
    selected_brand: str | None = None,
    selected_soc: str | None = None,
    selected_year: str | None = None,
    selected_has_content: bool = False,
    active_filter_count: int = 0,
) -> dict:
    """Build the full template context for GET / and any filter/add fragment render.

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
    }


@router.get("/", response_class=HTMLResponse)
def overview_page(request: Request, db: DBAdapter | None = Depends(get_db)):
    """Render the full Overview tab (OVERVIEW-01).

    `?tab=overview` is accepted (OVERVIEW-01) — it does not change rendering since
    the root URL already IS the overview tab.
    """
    entities_raw = load_overview()
    entities = [_entity_dict(e) for e in entities_raw]
    all_platform_ids: list[str] = []
    try:
        all_platform_ids = list(list_platforms(db, db_name=""))  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 — catalog load is non-fatal (UI degrades gracefully)
        all_platform_ids = []
    ctx = _build_overview_context(entities=entities, all_platform_ids=all_platform_ids)
    return templates.TemplateResponse(request, "overview/index.html", ctx)


@router.post("/overview/add", response_class=HTMLResponse)
def add_platform(
    request: Request,
    platform_id: Annotated[str, Form(pattern=PLATFORM_ID_PATTERN, min_length=1, max_length=128)],
    db: DBAdapter | None = Depends(get_db),
):
    """Add a platform to the curated list (OVERVIEW-03).

    Returns:
      200 + _entity_row.html fragment on success
      404 + _filter_alert.html when platform_id is not in the DB catalog (D-11)
      409 + _filter_alert.html when platform_id is already in the list (D-10)
      422 (FastAPI) when platform_id fails the regex
    """
    # D-11: reject unknown platforms BEFORE touching the store.
    catalog: list[str] = []
    try:
        catalog = list(list_platforms(db, db_name=""))  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 — catalog load failure is non-fatal
        catalog = []
    if platform_id not in catalog:
        return templates.TemplateResponse(
            request,
            "overview/_filter_alert.html",
            {
                "alert_level": "danger",
                "message": f"Unknown platform: {platform_id}. Choose from the dropdown.",
            },
            status_code=404,
        )

    # D-10: duplicate handling.
    try:
        entity = add_overview(platform_id)
    except DuplicateEntityError:
        return templates.TemplateResponse(
            request,
            "overview/_filter_alert.html",
            {
                "alert_level": "warning",
                "message": f"Already in your overview: {platform_id}",
            },
            status_code=409,
        )

    # Success — return ONE <li> entity row fragment (hx-swap="afterbegin" prepends it).
    return templates.TemplateResponse(
        request,
        "overview/_entity_row.html",
        {"entity": _entity_dict(entity)},
    )


@router.delete("/overview/{platform_id}")
def remove_platform(
    platform_id: Annotated[
        str,
        Path(pattern=PLATFORM_ID_PATTERN, min_length=1, max_length=128),
    ],
):
    """Remove a platform from the curated list (OVERVIEW-04).

    Returns:
      200 + empty body on success (HTMX swaps outerHTML with empty = element removed)
      404 when platform_id is not in the list
      422 (FastAPI) when platform_id fails the regex
    """
    removed = remove_overview(platform_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Not in overview: {platform_id}")
    return Response(status_code=200, content="")
