"""Platform detail page + content CRUD routes (CONTENT-02..06, CONTENT-08, D-01..D-13).

All routes are ``def`` (INFRA-05 — sync, dispatched to threadpool by FastAPI).
PLATFORM_ID validated via ``Path(..., pattern=...)`` BEFORE any filesystem call.
Defense-in-depth: ``content_store._safe_target`` re-asserts containment via
``Path.resolve()`` + ``relative_to()`` (Pitfall 2 / D-04).

Import note (mirrors ``app_v2/routers/overview.py`` line 18 convention):
``pathlib.Path`` is aliased to ``_Path`` so it does not collide with FastAPI's
``Path`` (used for path-parameter validation). Module-level path-constant
annotation references the pathlib alias; FastAPI's ``Path`` stays unaliased.

Backend-name lookup uses the shared ``app_v2.services.llm_resolver`` module
(Plan 03-01) — eliminates the duplicated ``_resolve_backend_name`` helper that
would otherwise appear in both ``overview.py`` and ``platforms.py``.
"""
from __future__ import annotations

import logging
from pathlib import Path as _Path  # alias to avoid collision with fastapi.Path
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Path, Request
from fastapi.responses import HTMLResponse

from app_v2.data.platform_parser import parse_platform_id
from app_v2.data.soc_year import get_year
from app_v2.services.content_store import (
    DEFAULT_CONTENT_DIR,
    delete_content,
    read_content,
    render_markdown,
    save_content,
)
from app_v2.services.llm_resolver import resolve_active_backend_name
from app_v2.templates import templates

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/platforms", tags=["platforms"])

PLATFORM_ID_PATTERN = r"^[A-Za-z0-9_\-]{1,128}$"
MAX_CONTENT_LENGTH = 65536  # D-31

# Module-level path constant — tests monkeypatch this; production unchanged.
# Mirrors the pattern from app_v2/routers/overview.py CONTENT_DIR.
# NOTE: typed as _Path (pathlib), NOT fastapi.Path — these are different
# classes and this annotation must reference the pathlib alias.
CONTENT_DIR: _Path = DEFAULT_CONTENT_DIR


def _detail_context(request: Request, platform_id: str, raw_md: str | None) -> dict:
    """Build template context for detail.html, _content_area.html, _edit_panel.html."""
    brand, _model, soc_raw = parse_platform_id(platform_id)
    rendered_html = render_markdown(raw_md) if raw_md is not None else ""
    settings = getattr(request.app.state, "settings", None)
    return {
        "active_tab": "overview",
        "page_title": platform_id,
        "platform_id": platform_id,
        "brand": brand,
        "soc_raw": soc_raw,
        "year": get_year(soc_raw),
        "has_content": raw_md is not None,
        "raw_md": raw_md or "",
        "rendered_html": rendered_html,
        # Shared resolver (Plan 03-01) — single source of truth for backend label.
        "backend_name": resolve_active_backend_name(settings),
    }


@router.get("/{platform_id}", response_class=HTMLResponse)
def detail_page(
    request: Request,
    platform_id: Annotated[
        str, Path(pattern=PLATFORM_ID_PATTERN, min_length=1, max_length=128)
    ],
):
    """Render the full detail page (CONTENT-03)."""
    raw_md = read_content(platform_id, CONTENT_DIR)
    ctx = _detail_context(request, platform_id, raw_md)
    return templates.TemplateResponse(request, "platforms/detail.html", ctx)


@router.post("/{platform_id}/edit", response_class=HTMLResponse)
def edit_view(
    request: Request,
    platform_id: Annotated[
        str, Path(pattern=PLATFORM_ID_PATTERN, min_length=1, max_length=128)
    ],
):
    """Return the edit panel fragment (CONTENT-04). Replaces #content-area via outerHTML.

    Stashes the rendered-view (or empty-state) HTML into ``data-cancel-html`` on
    the panel element so the Cancel button can restore it client-side without a
    server round-trip (D-10). Jinja2's ``| e`` filter HTML-escapes the value
    on the way into the attribute (T-03-02-04 — attribute injection blocked).
    """
    raw_md = read_content(platform_id, CONTENT_DIR)
    ctx = _detail_context(request, platform_id, raw_md)
    # Render _content_area.html into a string for the data-cancel-html attribute.
    tmpl = templates.env.get_template("platforms/_content_area.html")
    ctx["stashed_render_or_empty"] = tmpl.render(ctx)
    return templates.TemplateResponse(request, "platforms/_edit_panel.html", ctx)


@router.post("/{platform_id}/preview", response_class=HTMLResponse)
def preview_view(
    request: Request,
    platform_id: Annotated[
        str, Path(pattern=PLATFORM_ID_PATTERN, min_length=1, max_length=128)
    ],
    content: Annotated[str, Form(max_length=MAX_CONTENT_LENGTH)] = "",
):
    """Render markdown to HTML preview (CONTENT-05). NO disk side-effects."""
    rendered_html = render_markdown(content)
    return templates.TemplateResponse(
        request,
        "platforms/_preview_pane.html",
        {"rendered_html": rendered_html, "platform_id": platform_id},
    )


@router.post("/{platform_id}", response_class=HTMLResponse)
def save_content_route(
    request: Request,
    platform_id: Annotated[
        str, Path(pattern=PLATFORM_ID_PATTERN, min_length=1, max_length=128)
    ],
    content: Annotated[str, Form(max_length=MAX_CONTENT_LENGTH)],
):
    """Atomically save markdown (CONTENT-06). Returns the rendered-view fragment.

    D-31 size enforcement (WR-02): ``Form(max_length=65536)`` is a coarse
    codepoint-count first-line guard; the authoritative check is ``save_content``,
    which rejects payloads whose UTF-8 byte length exceeds 65536 (a 65536-char
    emoji string is ~262KB on disk). Byte-overflow → HTTP 413.
    """
    try:
        save_content(platform_id, content, CONTENT_DIR)
    except ValueError:
        # Byte-size overflow OR (defense-in-depth) a path-traversal _safe_target
        # rejection. The route regex on platform_id pre-empts traversal, so in
        # practice this branch only fires on the byte cap. Either way, the
        # client sent a payload we cannot store — 413 is the correct verdict.
        raise HTTPException(
            status_code=413,
            detail=f"Content too large: {MAX_CONTENT_LENGTH} bytes max",
        )
    ctx = _detail_context(request, platform_id, content)
    return templates.TemplateResponse(request, "platforms/_content_area.html", ctx)


@router.delete("/{platform_id}/content", response_class=HTMLResponse)
def delete_content_route(
    request: Request,
    platform_id: Annotated[
        str, Path(pattern=PLATFORM_ID_PATTERN, min_length=1, max_length=128)
    ],
):
    """Delete the content file (CONTENT-08). Returns the empty-state fragment.

    Idempotent — does not raise on missing file; simply returns the empty-state.
    """
    delete_content(platform_id, CONTENT_DIR)
    ctx = _detail_context(request, platform_id, None)  # raw_md=None → has_content=False
    return templates.TemplateResponse(request, "platforms/_content_area.html", ctx)
