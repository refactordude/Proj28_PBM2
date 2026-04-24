"""Root full-page routes for /browse and /ask stubs.

NOTE: GET / is owned by routers/overview.py as of Phase 2.

INFRA-05 convention: ALL routes are `def` (sync), not `async def`. Even though
these Phase 1 stubs do not touch the DB, establishing the convention from the
first route written prevents accidental `async def` later when DB calls arrive.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app_v2.templates import templates

router = APIRouter()


@router.get("/browse", response_class=HTMLResponse)
def browse_page(request: Request):
    """Browse tab. Phase 4 replaces this with the pivot grid."""
    return templates.TemplateResponse(request, "base.html", {
        "active_tab": "browse",
        "page_title": "Browse",
        "placeholder_message": "Coming in Phase 4 — pivot grid port from v1.0.",
    })


@router.get("/ask", response_class=HTMLResponse)
def ask_page(request: Request):
    """Ask tab. Phase 5 replaces this with the NL agent UI."""
    return templates.TemplateResponse(request, "base.html", {
        "active_tab": "ask",
        "page_title": "Ask",
        "placeholder_message": "Coming in Phase 5 — NL agent port from v1.0.",
    })
