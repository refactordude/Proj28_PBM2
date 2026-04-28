"""Active-LLM resolution helpers (single source of truth for backend lookup).

Used by Phase 03 routers (overview, platforms, summary) to resolve which
LLMConfig is currently active and the user-facing backend label
("OpenAI" / "Ollama"). Extracted into its own module so:

- The 3-way copy-paste of `_resolve_backend_name` / `_resolve_active_llm`
  across routers is eliminated.
- The cycle-avoidance hack (`platforms.py` redefining the helper because
  importing from `overview.py` would create a router import cycle) is no
  longer needed — both routers import from this services-layer module.
- Future settings-shape changes (default_llm field rename, multiple-default
  support, etc.) modify ONE file.

RESEARCH.md Open Question #2 (RESOLVED): lookup pattern is
``next((l for l in settings.llms if l.name == settings.app.default_llm),
      settings.llms[0] if settings.llms else None)``.

Phase 6 D-17 extension: both functions accept an optional ``request: Any = None``
argument. When provided, the resolver reads the ``pbm2_llm`` cookie via
``request.cookies.get("pbm2_llm")``, validates against ``settings.llms[].name``,
and uses the cookie value when valid (silently falls through to default
otherwise per D-15).
"""
from __future__ import annotations

from typing import Any

from app.core.config import LLMConfig


def resolve_active_llm(settings: Any, request: Any = None) -> LLMConfig | None:
    """Return the active LLMConfig from a Settings-like object, or None.

    Resolution order (Phase 6 D-15 + D-17):
        1. ``pbm2_llm`` cookie (when ``request`` is provided AND cookie value is
           a valid name in ``settings.llms[].name``). Single source of truth for
           active backend across Ask + AI Summary.
        2. ``settings.llms`` entry whose ``name`` equals ``settings.app.default_llm``.
        3. ``settings.llms[0]`` if any LLMs configured.
        4. ``None`` when ``settings.llms`` is empty or ``settings`` is malformed.

    Cookie validation (D-15): the cookie value MUST match one of the configured
    LLM names. Any other value (missing, empty, tampered, stale-config) is
    silently dropped — the resolver falls through to the default. This is the
    entire defense against cookie tampering; no signing needed (intranet,
    closed set of two backends).

    Backward compatibility: callers that pass only ``settings`` continue to
    work — ``request=None`` skips the cookie lookup and the resolution order
    is identical to the pre-Phase-6 behavior.
    """
    try:
        llms = getattr(settings, "llms", None)
        if not llms:
            return None
        # D-17: cookie precedence — read pbm2_llm, validate against name set,
        # silently fall through on invalid value (D-15).
        cookie_name: str | None = None
        if request is not None:
            cookies = getattr(request, "cookies", None) or {}
            cookie_val = cookies.get("pbm2_llm") if hasattr(cookies, "get") else None
            if cookie_val:
                valid_names = {getattr(l, "name", None) for l in llms}
                if cookie_val in valid_names:
                    cookie_name = cookie_val
        target_name = cookie_name or getattr(getattr(settings, "app", None), "default_llm", None)
        cfg = next((l for l in llms if getattr(l, "name", None) == target_name), None)
        return cfg or llms[0]
    except Exception:  # noqa: BLE001 — defensive: never raise from resolver
        return None


def resolve_active_backend_name(settings: Any, request: Any = None) -> str:
    """Return the user-facing backend label: 'OpenAI' or 'Ollama'.

    Defaults to ``'Ollama'`` (D-19) when no LLM is configured or ``cfg.type``
    is anything other than ``'openai'``. Used by templates (loading text
    "Summarizing… (using {Ollama|OpenAI})", Ask-page LLM selector dropdown
    label "LLM: Ollama ▾" / "LLM: OpenAI ▾").

    Honors the same cookie precedence as ``resolve_active_llm`` when
    ``request`` is provided (Phase 6 D-17).
    """
    cfg = resolve_active_llm(settings, request)
    if cfg is None:
        return "Ollama"
    cfg_type = getattr(cfg, "type", "ollama")
    return "OpenAI" if cfg_type == "openai" else "Ollama"
