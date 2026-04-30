"""Overview tab routes — GET /, GET /overview, POST /overview/grid.

Phase 1 Plan 04 rewrite (D-JV-01, D-JV-07, D-JV-09, D-JV-12, D-JV-14):
the Overview tab content is now Joint Validation rows auto-discovered from
``content/joint_validation/<numeric_id>/index.html``. The tab URL stays
``/overview``; only the data source + grid view-model swap.

Routes:
- ``GET /`` and ``GET /overview`` — full page; both render the JV listing.
- ``POST /overview/grid`` — HTMX fragment swap; returns the three OOB blocks
  ``["grid", "count_oob", "filter_badges_oob"]`` and pushes a canonical
  ``/overview?...`` URL via ``HX-Push-Url``.

Deleted (D-JV-07 + D-JV-09 — drop-folder workflow only):
- ``POST /overview/add`` — there is no in-app form; new Joint Validations
  appear by dropping a folder under ``content/joint_validation/`` and the
  next request re-globs.

The ``_parse_filter_dict`` and ``_build_overview_url`` helpers are reused
verbatim from the Phase 5 file — JV-agnostic, same 6 query keys.

Sync ``def`` per INFRA-05 — FastAPI dispatches BS4-parse work to the
threadpool so it stays off the event loop.
"""
from __future__ import annotations

import urllib.parse
from typing import Annotated

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse

from app_v2.services.joint_validation_grid_service import (
    FILTERABLE_COLUMNS,
    JointValidationGridViewModel,
    build_joint_validation_grid_view_model,
)
from app_v2.services.joint_validation_store import JV_ROOT
from app_v2.templates import templates

router = APIRouter()


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

    D-JV-14 (preserves D-OV-13 shape): repeated keys for multi-value
    (?status=A&status=B). Pitfall 6 from Phase 4 D-32: use
    quote_via=urllib.parse.quote so spaces encode as %20 (URL-style),
    not + (form-style).

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
def get_overview(
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
    sort:        Annotated[str | None, Query()] = None,
    order:       Annotated[str | None, Query()] = None,
):
    """Render the Joint Validation listing (D-JV-01, D-JV-09, D-JV-12, D-JV-14).

    Re-globs content/joint_validation/ on every request (D-JV-09) — newly
    dropped folders appear immediately. Per-folder mtime cache lives inside
    the grid service; the directory glob itself is NOT memoized.
    """
    filters = _parse_filter_dict(status, customer, ap_company, device, controller, application)
    vm: JointValidationGridViewModel = build_joint_validation_grid_view_model(
        JV_ROOT,
        filters=filters,
        sort_col=sort,
        sort_order=order,  # type: ignore[arg-type]
    )
    ctx = {
        "vm": vm,
        "selected_filters": filters,
        "active_tab": "overview",
        # Transitional aliases consumed by the Phase 5 Platform-shaped templates
        # until Plan 05 rewrites overview/index.html / _filter_bar.html / _grid.html
        # for the JV column shape. The Phase 5 templates reference these keys at
        # the top level (vs the new templates which read vm.active_filter_counts
        # directly). Pass them as a no-op bridge so GET /overview returns 200 in
        # the wave-3 interim state. Plan 05 deletes these aliases.
        "active_filter_counts": vm.active_filter_counts,
        # Legacy "Add platform" form datalist — D-JV-07 deletes the form in
        # Plan 05; for now an empty list keeps the for-loop a no-op so the
        # template renders without 500.
        "all_platform_ids": [],
    }
    return templates.TemplateResponse(request, "overview/index.html", ctx)


@router.post("/overview/grid", response_class=HTMLResponse)
def post_overview_grid(
    request: Request,
    # NOTE (Phase 4 04-02 lesson, mirrored from overview_grid line 308):
    # Pydantic v2.13.x + FastAPI 0.136.x reject `Form(default_factory=list)` AND
    # `= []` together. Form accepts `= []` literal default; pre-Phase-5 router
    # used the same pattern. Empty omitted form key still resolves to [].
    status:      Annotated[list[str], Form()] = [],
    customer:    Annotated[list[str], Form()] = [],
    ap_company:  Annotated[list[str], Form()] = [],
    device:      Annotated[list[str], Form()] = [],
    controller:  Annotated[list[str], Form()] = [],
    application: Annotated[list[str], Form()] = [],
    sort:        Annotated[str | None, Form()] = None,
    order:       Annotated[str | None, Form()] = None,
):
    """HTMX fragment swap. Returns three OOB blocks; pushes canonical URL.

    Sets HX-Push-Url on the constructed TemplateResponse (NOT via an injected
    `Response` dependency — FastAPI's parameter-Response merge does not apply
    when the route returns its own Response object; the returned object's
    headers are authoritative. Mirrors Phase 5 routers/overview.py:349-358.)
    """
    filters = _parse_filter_dict(status, customer, ap_company, device, controller, application)
    vm: JointValidationGridViewModel = build_joint_validation_grid_view_model(
        JV_ROOT,
        filters=filters,
        sort_col=sort,
        sort_order=order,  # type: ignore[arg-type]
    )
    ctx = {
        "vm": vm,
        "selected_filters": filters,
        "active_tab": "overview",
        # Same transitional aliases as GET — see comment above.
        "active_filter_counts": vm.active_filter_counts,
        "all_platform_ids": [],
    }
    response = templates.TemplateResponse(
        request,
        "overview/index.html",
        ctx,
        block_names=["grid", "count_oob", "filter_badges_oob"],
    )
    # D-JV-12 + D-JV-14 + Pitfall 6 from Phase 4: server-set push URL
    # (canonical /overview?..., NOT /overview/grid).
    response.headers["HX-Push-Url"] = _build_overview_url(
        filters, vm.sort_col, vm.sort_order
    )
    return response


# Note: FILTERABLE_COLUMNS is re-exported from the JV grid service for symmetry
# (validation tests + future router additions). The legacy curated-Platform
# helpers and the legacy POST add-platform route are deleted per D-JV-07 +
# D-JV-09.
__all__ = [
    "router",
    "FILTERABLE_COLUMNS",
    "_parse_filter_dict",
    "_build_overview_url",
]
