"""Joint Validation routes (Phase 1 Plan 04).

Two routes:
- GET /joint_validation/{confluence_page_id} — properties table + iframe sandbox
- POST /joint_validation/{confluence_page_id}/summary — AI Summary modal target

Both routes path-validate confluence_page_id with regex ^\\d+$ at the FastAPI
layer (path-traversal defense + non-numeric folders 404 per D-JV-03).

Sync def per INFRA-05 (BS4 + summary_service are CPU/IO-bound but synchronous;
FastAPI dispatches to threadpool).

Mirrors app_v2/routers/summary.py:113-180 byte-stable except for:
- service call: get_or_generate_jv_summary instead of get_or_generate_summary
- entity prefix: /joint_validation/{id}/summary instead of /platforms/{pid}/summary
- error string for missing index: "Joint Validation page no longer exists"
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Path, Request
from fastapi.responses import HTMLResponse

from app_v2.services import summary_service  # for _classify_error
from app_v2.services.content_store import render_markdown
from app_v2.services.joint_validation_grid_service import (
    JointValidationRow,
    _sanitize_link,
)
from app_v2.services.joint_validation_store import (
    JV_ROOT,
    get_parsed_jv,
)
from app_v2.services.joint_validation_summary import get_or_generate_jv_summary
from app_v2.services.llm_resolver import (
    resolve_active_backend_name,
    resolve_active_llm,
)
# CANONICAL templates singleton (verified at app_v2/templates/__init__.py:16).
# Every other router (summary.py:66, overview.py:39, platforms.py:37) uses
# this exact import path. NEVER import via routers/overview module attribute
# — that creates a circular-import risk because overview.py is also under
# rewrite in this plan.
from app_v2.templates import templates


_log = logging.getLogger(__name__)
router = APIRouter(prefix="/joint_validation", tags=["joint_validation"])


# Path constraint: numeric only, 1-32 chars. Confluence page IDs in Atlassian
# Cloud are typically 8-12 digits; max_length=32 is generous.
_CONFLUENCE_PAGE_ID = Path(pattern=r"^\d+$", min_length=1, max_length=32)


def _resolve_target_id(hx_target: str | None, confluence_page_id: str) -> str:
    """Honor HX-Target header if present; fall back to summary-{id}.

    Mirrors app_v2/routers/summary.py:75-92. Overview-row ✨ button sends
    HX-Target: summary-modal-body; non-HTMX falls back to inline contract.
    """
    if hx_target:
        return hx_target.lstrip("#")
    return f"summary-{confluence_page_id}"


def _render_error_fragment(
    request: Request,
    confluence_page_id: str,
    summary_url: str,
    target_id: str,
    reason: str,
    backend_name: str,
) -> HTMLResponse:
    """Always-200 error fragment (Phase 3 contract). Renders summary/_error.html.

    The template was parameterized in Plan 01 Task 2 to accept entity_id +
    summary_url alongside the legacy platform_id alias.
    """
    return templates.TemplateResponse(
        request,
        "summary/_error.html",
        {
            "platform_id": confluence_page_id,    # backward-compat alias (Plan 01 Task 2)
            "entity_id": confluence_page_id,       # generic
            "summary_url": summary_url,            # generic
            "target_id": target_id,
            "reason": reason,
            "backend_name": backend_name,
        },
        status_code=200,
    )


@router.get("/{confluence_page_id}", response_class=HTMLResponse)
def get_joint_validation_detail(
    request: Request,
    confluence_page_id: Annotated[str, _CONFLUENCE_PAGE_ID],
):
    """Detail page: properties table + iframe sandbox of the Confluence export.

    D-JV-12: properties table on top, <iframe sandbox="..."> below pointing at
             /static/joint_validation/<id>/index.html.
    D-JV-15: link sanitized with the same _sanitize_link as the listing.
    """
    index_html = JV_ROOT / confluence_page_id / "index.html"
    if not index_html.is_file():
        raise HTTPException(status_code=404, detail=f"No Joint Validation {confluence_page_id}")
    parsed = get_parsed_jv(confluence_page_id, index_html)
    # Build a JointValidationRow so the template uses the same field set as the listing
    row = JointValidationRow(
        confluence_page_id=confluence_page_id,
        title=parsed.title or confluence_page_id,
        status=parsed.status,
        customer=parsed.customer,
        model_name=parsed.model_name,
        ap_company=parsed.ap_company,
        ap_model=parsed.ap_model,
        device=parsed.device,
        controller=parsed.controller,
        application=parsed.application,
        assignee=parsed.assignee,
        start=parsed.start,
        end=parsed.end,
        link=_sanitize_link(parsed.link or None),
    )
    ctx = {
        "jv": row,
        "active_tab": "overview",
    }
    return templates.TemplateResponse(request, "joint_validation/detail.html", ctx)


@router.post("/{confluence_page_id}/summary", response_class=HTMLResponse)
def get_joint_validation_summary(
    request: Request,
    confluence_page_id: Annotated[str, _CONFLUENCE_PAGE_ID],
    x_regenerate: Annotated[str | None, Header()] = None,
    hx_target: Annotated[str | None, Header()] = None,
):
    """AI Summary route — always-200 contract, mirrors routers/summary.py:113-180.

    Reuses summary/_success.html and summary/_error.html (parameterized for
    entity_id + summary_url in Plan 01 Task 2).
    """
    settings = getattr(request.app.state, "settings", None)
    cfg = resolve_active_llm(settings, request)
    backend_name = resolve_active_backend_name(settings, request)
    target_id = _resolve_target_id(hx_target, confluence_page_id)
    summary_url = f"/joint_validation/{confluence_page_id}/summary"

    # cfg-None error branch — present BEFORE the try/except (mirrors
    # routers/summary.py:127-130). Match the exact same reason string.
    if cfg is None:
        return _render_error_fragment(
            request,
            confluence_page_id,
            summary_url,
            target_id,
            "LLM not configured — set one in Settings",
            backend_name,
        )

    # Canonical X-Regenerate parsing: ONLY the literal "true" triggers
    # regenerate. Mirrors routers/summary.py:132 verbatim. Any other value
    # (None, "", "false", "True", "1") is treated as not-regenerate.
    regenerate = (x_regenerate or "").lower() == "true"

    try:
        result = get_or_generate_jv_summary(
            confluence_page_id, cfg, JV_ROOT, regenerate=regenerate
        )
    except FileNotFoundError:
        return _render_error_fragment(
            request,
            confluence_page_id,
            summary_url,
            target_id,
            "Joint Validation page no longer exists",
            backend_name,
        )
    except Exception as exc:  # noqa: BLE001 — always-200 contract; classified
        _log.warning(
            "JV summary failed for %s (%s): %s",
            confluence_page_id,
            type(exc).__name__,
            exc,
        )
        reason = summary_service._classify_error(exc, backend_name)
        return _render_error_fragment(
            request,
            confluence_page_id,
            summary_url,
            target_id,
            reason,
            backend_name,
        )

    # Compute age_s + summary_html in the ROUTER (mirrors routers/summary.py:156-180).
    # SummaryResult is a frozen dataclass with EXACTLY the four fields
    # text/llm_name/llm_model/generated_at — verified at
    # app_v2/services/summary_service.py:61-68.
    age_s = max(
        0,
        int((datetime.now(timezone.utc) - result.generated_at).total_seconds()),
    )
    summary_html = render_markdown(result.text)

    return templates.TemplateResponse(
        request,
        "summary/_success.html",
        {
            "platform_id": confluence_page_id,    # backward-compat alias (Plan 01 Task 2)
            "entity_id": confluence_page_id,       # generic
            "summary_url": summary_url,            # generic
            "target_id": target_id,
            "summary_html": summary_html,
            "llm_name": result.llm_name,           # SummaryResult field — direct
            "llm_model": result.llm_model,         # SummaryResult field — direct
            "cached_age_s": age_s,                 # router-computed
            "backend_name": backend_name,          # from resolve_active_backend_name
        },
    )
