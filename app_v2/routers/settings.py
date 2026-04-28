"""Settings-side routes for v2.0 (Phase 6, ASK-V2-05).

Currently exactly one route — POST /settings/llm — which sets the
``pbm2_llm`` cookie that drives the active LLM backend across the entire
v2.0 app (Ask + AI Summary; Phase 6 D-17). The cookie is read by
``app_v2.services.llm_resolver.resolve_active_llm(settings, request)``.

Sync ``def`` per INFRA-05.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Form, Request, Response

_log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/settings/llm")
def set_llm(
    request: Request,
    name: Annotated[str, Form()] = "",
):
    """Set the ``pbm2_llm`` cookie to ``name`` (validated) and tell HTMX to refresh.

    Validation (D-15): ``name`` MUST equal one of ``settings.llms[].name``.
    Any other value (empty, missing, tampered, stale-config) silently falls
    back to ``settings.app.default_llm``. No 4xx — invalid input is a
    user-facing UX failure mode (the dropdown re-renders to default), not
    an attack to be loudly rejected.

    Cookie attributes (D-14):
        - Path=/         (cookie applies to every URL in the app)
        - SameSite=Lax   (CSRF-light defense; not a primary control given
                          intranet + no-auth posture)
        - Max-Age=31536000 (1 year — survives reasonable session lifetimes)
        - HttpOnly=True  (JS cannot read; not strictly needed but safe)
        - Secure=False   (intranet HTTP — Pitfall 8)

    Response (D-16): 204 No Content + ``HX-Refresh: true`` header (lowercase
    string per Pitfall 4). HTMX 2.x interprets ``HX-Refresh: true`` as
    ``window.location.reload()`` regardless of status code; the page reloads
    so the dropdown label re-renders with the new cookie value, any
    in-flight Ask state is cleared, and AI Summary picks up the new backend
    on the next click.
    """
    settings = getattr(request.app.state, "settings", None)
    llms = getattr(settings, "llms", None) or []
    valid_names = {getattr(l, "name", None) for l in llms}
    default_name = getattr(getattr(settings, "app", None), "default_llm", "") or ""
    cookie_val = name if name in valid_names else default_name
    response = Response(status_code=204)
    response.set_cookie(
        key="pbm2_llm",
        value=cookie_val,
        max_age=31536000,
        path="/",
        samesite="lax",
        httponly=True,
        secure=False,  # Pitfall 8 — intranet HTTP; never set Secure=True here
    )
    response.headers["HX-Refresh"] = "true"  # Pitfall 4 — lowercase string
    return response
