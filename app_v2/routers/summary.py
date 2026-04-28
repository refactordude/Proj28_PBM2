"""AI Summary route — POST /platforms/{pid}/summary (SUMMARY-02..07).

Single endpoint; ALWAYS returns 200 (UI-SPEC "Note on summary error response":
error fragments swap inline into the summary slot, NOT into the global
``htmx-error-container`` — so the route NEVER raises HTTPException and NEVER
returns a 5xx response).

Dispatch:

- Resolve LLMConfig from ``app.state.settings`` via the shared
  ``app_v2.services.llm_resolver.resolve_active_llm``. If no LLM is configured
  → 200 with the error fragment "LLM not configured — set one in Settings"
  (8th vocabulary entry beyond UI-SPEC §8c's seven; justified because the
  default seven all assume a backend exists).
- Call ``summary_service.get_or_generate_summary``.
- On success → render ``summary/_success.html`` (markdown-rendered text +
  metadata footer + Regenerate button).
- On ``FileNotFoundError`` → 200 with the error fragment carrying the fixed
  string "Content page no longer exists".
- On any openai / httpx exception → 200 with the error fragment, reason
  classified by ``summary_service._classify_error`` (the 7-string vocabulary).
- ``X-Regenerate: true`` header → bypass cache lookup, still write back (D-18).

INFRA-05: route is ``def`` (sync, dispatched to threadpool by FastAPI).

Pitfall 18 (Ollama cold-start) — DEVIATION from RESEARCH.md Q3:
RESEARCH.md recommended a lifespan-time Ollama warmup ping. We deviate and
rely solely on the 60s read timeout configured in
``summary_service._build_client`` (httpx.Timeout(60.0) for Ollama vs 30.0 for
OpenAI). Rationale: the app must start cleanly even if Ollama is unreachable;
first-request cold start is acceptable for an internal tool with low
concurrency. Lifespan warmup is deferred until cold-start latency proves
user-visible. The summary route's error fragment path (D-16 amber alert)
handles the worst case gracefully. The matching deviation comment lives in
``summary_service._build_client`` and ``app_v2/main.py`` lifespan.

Local helpers eliminated (Plan 03-01 Q2 RESOLVED):

- ``_resolve_active_llm`` → ``llm_resolver.resolve_active_llm``
- ``_backend_display_name`` → ``llm_resolver.resolve_active_backend_name``

Both helpers are imported below. This removes the 3-way duplication
previously present across overview.py / platforms.py / summary.py.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

# Note: do NOT ``from pathlib import Path`` here. summary.py only uses
# FastAPI's Path (for path-parameter validation) and reaches pathlib paths
# transitively via ``platforms_router.CONTENT_DIR``. Importing both Path
# symbols would shadow pathlib.Path with fastapi.Path (the second import
# wins).
from fastapi import APIRouter, Header, Path, Request
from fastapi.responses import HTMLResponse

from app_v2.routers import platforms as platforms_router  # for CONTENT_DIR
from app_v2.services import summary_service
from app_v2.services.content_store import render_markdown
from app_v2.services.llm_resolver import (
    resolve_active_backend_name,
    resolve_active_llm,
)
from app_v2.templates import templates

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/platforms", tags=["summary"])

PLATFORM_ID_PATTERN = r"^[A-Za-z0-9_\-]{1,128}$"


def _resolve_target_id(hx_target: str | None, platform_id: str) -> str:
    """Pick the target id to thread into rendered fragments (D-OV-15).

    HTMX sends the ``HX-Target`` request header containing the id of the
    element that hx-target points at. The summary route honors that id so
    inner Retry / Regenerate buttons in ``_error.html`` / ``_success.html``
    swap into the same slot the caller rendered into:

      - Overview row ✨ button → ``HX-Target: summary-modal-body`` (D-OV-15)
      - Detail page button     → ``HX-Target: summary-{platform_id}``
      - Non-HTMX / curl        → no header → fall back to ``summary-{pid}``

    The fallback preserves the Phase 3 inline contract for any future
    caller that does not set hx-target.
    """
    if hx_target:
        return hx_target.lstrip("#")
    return f"summary-{platform_id}"


def _render_error(
    request: Request, platform_id: str, reason: str, target_id: str
) -> HTMLResponse:
    """Render the amber-warning error fragment with a classified reason.

    Always status 200 — UI-SPEC mandate (WR-03). The error fragment swaps
    inline into whichever slot the caller's hx-target named (D-OV-15:
    ``#summary-modal-body`` from Overview rows, ``#summary-{pid}`` from
    the detail page), NEVER into the global ``#htmx-error-container``.
    """
    return templates.TemplateResponse(
        request,
        "summary/_error.html",
        {"platform_id": platform_id, "reason": reason, "target_id": target_id},
        status_code=200,
    )


@router.post("/{platform_id}/summary", response_class=HTMLResponse)
def get_summary_route(
    request: Request,
    platform_id: Annotated[
        str, Path(pattern=PLATFORM_ID_PATTERN, min_length=1, max_length=128)
    ],
    x_regenerate: Annotated[str | None, Header()] = None,
    hx_target: Annotated[str | None, Header()] = None,
):
    """Return success or amber-warning fragment. ALWAYS status 200."""
    settings = getattr(request.app.state, "settings", None)
    cfg = resolve_active_llm(settings, request)
    backend_name = resolve_active_backend_name(settings, request)
    target_id = _resolve_target_id(hx_target, platform_id)
    if cfg is None:
        return _render_error(
            request, platform_id, "LLM not configured — set one in Settings", target_id
        )

    regenerate = (x_regenerate or "").lower() == "true"
    try:
        result = summary_service.get_or_generate_summary(
            platform_id=platform_id,
            cfg=cfg,
            content_dir=platforms_router.CONTENT_DIR,
            regenerate=regenerate,
        )
    except FileNotFoundError:
        # Classified independently because we know exactly what happened —
        # avoids re-routing through _classify_error's branchwork.
        return _render_error(
            request, platform_id, "Content page no longer exists", target_id
        )
    except Exception as exc:  # noqa: BLE001 — classified to user-readable string
        reason = summary_service._classify_error(exc, backend_name)
        _log.warning(
            "Summary failed for %s (%s): %s",
            platform_id,
            type(exc).__name__,
            exc,
        )
        return _render_error(request, platform_id, reason, target_id)

    # Compute cache age in seconds (0 → "(fresh)" branch in template).
    age_s = max(
        0,
        int(
            (datetime.now(timezone.utc) - result.generated_at).total_seconds()
        ),
    )

    # Render the LLM's markdown output via the same XSS-safe pipeline as
    # content pages (T-03-03-04 — LLM output is treated as untrusted markdown).
    summary_html = render_markdown(result.text)

    return templates.TemplateResponse(
        request,
        "summary/_success.html",
        {
            "platform_id": platform_id,
            "summary_html": summary_html,
            "llm_name": result.llm_name,
            "llm_model": result.llm_model,
            "cached_age_s": age_s,
            "backend_name": backend_name,
            "target_id": target_id,
        },
    )
