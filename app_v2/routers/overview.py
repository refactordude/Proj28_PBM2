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
verbatim from the Phase 5 file — JV-agnostic. 260507-rmj dropped Status
from the listing/preset facet set; the helpers now bundle 5 query keys
(customer, ap_company, device, controller, application).

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
    JV_PAGE_SIZE,                   # Phase 02 Plan 02-04 (D-UI2-14)
    JointValidationGridViewModel,
    build_joint_validation_grid_view_model,
)
from app_v2.services.joint_validation_store import JV_ROOT
from app_v2.services.preset_store import load_presets
from app_v2.templates import templates

router = APIRouter()


def _parse_filter_dict(
    customer: list[str],
    ap_company: list[str],
    device: list[str],
    controller: list[str],
    application: list[str],
) -> dict[str, list[str]]:
    """Bundle the 5 filter form lists into a dict shape the service expects.

    Filter columns enumerated explicitly (not iterated from FILTERABLE_COLUMNS)
    so the function signature mirrors FastAPI's Form() / Query() parameter
    list 1:1 — adding a new filter is a 3-line edit (sig + dict + form param).
    260507-rmj dropped status from the 6-tuple.
    """
    return {
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
    page: int = 1,
) -> str:
    """Compose canonical /overview?customer=A&customer=B&...&sort=start&order=desc&page=N URL.

    D-JV-14 (preserves D-OV-13 shape): repeated keys for multi-value
    (?customer=A&customer=B). Pitfall 6 from Phase 4 D-32: use
    quote_via=urllib.parse.quote so spaces encode as %20 (URL-style),
    not + (form-style).

    sort + order are always emitted (even when at defaults) so the URL is
    explicit and bookmarkable. Empty filter values are dropped.

    Phase 02 Plan 02-04 (D-UI2-13/14): page is included only when > 1 so
    that ?page=1 is omitted from bookmark URLs and browser history.

    260507-rmj: status was dropped from the facet tuple.
    """
    pairs: list[tuple[str, str]] = []
    for col in ("customer", "ap_company", "device", "controller", "application"):
        for v in filters.get(col, []) or []:
            if v:  # drop empty / None
                pairs.append((col, v))
    if sort_col:
        pairs.append(("sort", sort_col))
    if sort_order:
        pairs.append(("order", sort_order))
    # Only include page when not at default (page=1 omitted for clean URLs).
    if page > 1:
        pairs.append(("page", str(page)))
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
    customer:    Annotated[list[str], Query(default_factory=list)],
    ap_company:  Annotated[list[str], Query(default_factory=list)],
    device:      Annotated[list[str], Query(default_factory=list)],
    controller:  Annotated[list[str], Query(default_factory=list)],
    application: Annotated[list[str], Query(default_factory=list)],
    sort:        Annotated[str | None, Query()] = None,
    order:       Annotated[str | None, Query()] = None,
    # Phase 02 Plan 02-04 (D-UI2-13/14, T-02-04-02 mitigation):
    # - ge=1 rejects 0 / negative (HTTP 422).
    # - le=10_000 rejects extremely large values pre-emptively, blocking
    #   resource-exhaustion via huge slice computation. 10_000 pages × 15
    #   per page = 150_000 rows — far above any realistic JV dataset.
    # - Non-integer values return 422 via FastAPI's int parser.
    # - Service additionally clamps page > page_count to page_count.
    page:        Annotated[int, Query(ge=1, le=10_000)] = 1,
):
    """Render the Joint Validation listing (D-JV-01, D-JV-09, D-JV-12, D-JV-14).

    Re-globs content/joint_validation/ on every request (D-JV-09) — newly
    dropped folders appear immediately. Per-folder mtime cache lives inside
    the grid service; the directory glob itself is NOT memoized.
    """
    filters = _parse_filter_dict(customer, ap_company, device, controller, application)
    vm: JointValidationGridViewModel = build_joint_validation_grid_view_model(
        JV_ROOT,
        filters=filters,
        sort_col=sort,
        sort_order=order,  # type: ignore[arg-type]
        page=page,
    )
    # 260507-lox: thread Confluence base URL into the JV grid template
    # context. rstrip a single trailing "/" in Python so the template can
    # do a simple "{conf_url}/{page_id}" join (no Jinja-level rstrip used
    # elsewhere in this project — keep the cleanup in route code).
    settings_obj = getattr(request.app.state, "settings", None)
    conf_url = (settings_obj.app.conf_url.rstrip("/") if settings_obj else "")
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
        "conf_url": conf_url,
        # 260507-obp — preset chip strip rendered above filter_badges_oob.
        "presets": load_presets(),
    }
    return templates.TemplateResponse(request, "overview/index.html", ctx)


@router.post("/overview/grid", response_class=HTMLResponse)
def post_overview_grid(
    request: Request,
    # NOTE (Phase 4 04-02 lesson, mirrored from overview_grid line 308):
    # Pydantic v2.13.x + FastAPI 0.136.x reject `Form(default_factory=list)` AND
    # `= []` together. Form accepts `= []` literal default; pre-Phase-5 router
    # used the same pattern. Empty omitted form key still resolves to [].
    customer:    Annotated[list[str], Form()] = [],
    ap_company:  Annotated[list[str], Form()] = [],
    device:      Annotated[list[str], Form()] = [],
    controller:  Annotated[list[str], Form()] = [],
    application: Annotated[list[str], Form()] = [],
    sort:        Annotated[str | None, Form()] = None,
    order:       Annotated[str | None, Form()] = None,
    # Phase 02 Plan 02-04 (D-UI2-13/14, T-02-04-02 mitigation):
    # Same ge=1, le=10_000 validation as the GET route's Query param.
    page:        Annotated[int, Form(ge=1, le=10_000)] = 1,
):
    """HTMX fragment swap. Returns four OOB blocks; pushes canonical URL.

    Sets HX-Push-Url on the constructed TemplateResponse (NOT via an injected
    `Response` dependency — FastAPI's parameter-Response merge does not apply
    when the route returns its own Response object; the returned object's
    headers are authoritative. Mirrors Phase 5 routers/overview.py:349-358.)

    Phase 02 Plan 02-04: adds ``pagination_oob`` to block_names so HTMX
    receives the pagination control update alongside grid/count/badges.
    Uses vm.page (clamped by service) so HX-Push-Url reflects the actual
    page the user lands on after server-side clamping (T-02-04-02 alignment).
    """
    filters = _parse_filter_dict(customer, ap_company, device, controller, application)
    vm: JointValidationGridViewModel = build_joint_validation_grid_view_model(
        JV_ROOT,
        filters=filters,
        sort_col=sort,
        sort_order=order,  # type: ignore[arg-type]
        page=page,
    )
    # 260507-lox: same conf_url threading on the OOB re-render path —
    # the grid block also references {{ conf_url }} in the 컨플 button
    # template. Without this the OOB-swapped grid would render disabled
    # buttons even when conf_url is configured.
    settings_obj = getattr(request.app.state, "settings", None)
    conf_url = (settings_obj.app.conf_url.rstrip("/") if settings_obj else "")
    ctx = {
        "vm": vm,
        "selected_filters": filters,
        "active_tab": "overview",
        # Same transitional aliases as GET — see comment above.
        "active_filter_counts": vm.active_filter_counts,
        "all_platform_ids": [],
        "conf_url": conf_url,
        # 260507-obp — threaded into POST context too so any future
        # preset_chips_oob block has access; the strip itself is OUTSIDE
        # the OOB swap targets so it stays put across filter changes.
        "presets": load_presets(),
    }
    response = templates.TemplateResponse(
        request,
        "overview/index.html",
        ctx,
        block_names=["grid", "count_oob", "filter_badges_oob", "pagination_oob"],
    )
    # D-JV-12 + D-JV-14 + Pitfall 6 from Phase 4: server-set push URL
    # (canonical /overview?..., NOT /overview/grid).
    # Use vm.page (clamped) so URL reflects the actual landed page.
    response.headers["HX-Push-Url"] = _build_overview_url(
        filters, vm.sort_col, vm.sort_order, vm.page
    )
    return response


@router.get("/overview/preset/{name}", response_class=HTMLResponse)
def get_overview_preset(request: Request, name: str):
    """Apply a named preset — OVERRIDES current filters (clears + replaces).

    Looks up the preset by ``name`` in load_presets(); 404 if not found.
    Builds the JV grid view-model from the preset's filter dict (other
    facets default to empty lists), and returns the same four OOB blocks
    as POST /overview/grid plus an HX-Push-Url header carrying the
    canonical /overview?<facet>=... URL.

    OVERRIDE semantics (260507-obp design decision): we deliberately do
    NOT merge the preset on top of existing filters from the request. The
    preset is the entire filter state the user wants. Any facets the
    preset doesn't mention default to empty (= "any value matches")
    rather than carrying over from the previous request. This keeps the
    end state deterministic from the chip click alone.

    HTMX call site (overview/index.html):
        <a hx-get="/overview/preset/<name>"
           hx-target="#overview-grid"
           hx-swap="outerHTML"
           hx-push-url="true">…</a>

    The handler uses GET (not POST) because:
      1. It's idempotent — repeated clicks land on the same state.
      2. hx-push-url with GET produces a clean shareable URL in the bar.
      3. Tests can hit it with TestClient.get().
    """
    presets = load_presets()
    preset = next((p for p in presets if p["name"] == name), None)
    if preset is None:
        return HTMLResponse(status_code=404, content=f"preset '{name}' not found")

    # Build the canonical filter dict — preset values for any mentioned
    # facets, [] for the others. Reuses _parse_filter_dict for shape parity
    # with the GET / POST handlers (so the resulting `selected_filters`
    # dict in ctx is byte-equal in shape — same 5 keys always present).
    # 260507-rmj: status was dropped from the facet set.
    pf = preset["filters"]
    filters = _parse_filter_dict(
        customer=pf.get("customer", []),
        ap_company=pf.get("ap_company", []),
        device=pf.get("device", []),
        controller=pf.get("controller", []),
        application=pf.get("application", []),
    )

    vm: JointValidationGridViewModel = build_joint_validation_grid_view_model(
        JV_ROOT,
        filters=filters,
        sort_col=None,    # use service defaults — preset doesn't carry sort
        sort_order=None,
        page=1,           # always reset to page 1 on preset apply
    )

    settings_obj = getattr(request.app.state, "settings", None)
    conf_url = (settings_obj.app.conf_url.rstrip("/") if settings_obj else "")

    ctx = {
        "vm": vm,
        "selected_filters": filters,
        "active_tab": "overview",
        "active_filter_counts": vm.active_filter_counts,
        "all_platform_ids": [],
        "conf_url": conf_url,
        "presets": presets,
    }
    response = templates.TemplateResponse(
        request,
        "overview/index.html",
        ctx,
        block_names=["grid", "count_oob", "filter_badges_oob", "pagination_oob"],
    )
    response.headers["HX-Push-Url"] = _build_overview_url(
        filters, vm.sort_col, vm.sort_order, vm.page
    )
    return response


# Note: FILTERABLE_COLUMNS is re-exported from the JV grid service for symmetry
# (validation tests + future router additions). The legacy curated-Platform
# helpers and the legacy POST add-platform route are deleted per D-JV-07 +
# D-JV-09.
__all__ = [
    "router",
    "FILTERABLE_COLUMNS",
    "JV_PAGE_SIZE",
    "_parse_filter_dict",
    "_build_overview_url",
]
