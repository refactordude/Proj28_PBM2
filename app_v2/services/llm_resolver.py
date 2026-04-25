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
"""
from __future__ import annotations

from typing import Any

from app.core.config import LLMConfig


def resolve_active_llm(settings: Any) -> LLMConfig | None:
    """Return the active LLMConfig from a Settings-like object, or None.

    Resolution order (RESEARCH.md Q2):
        1. ``settings.llms`` entry whose ``name`` equals ``settings.app.default_llm``.
        2. ``settings.llms[0]`` if any LLMs configured.
        3. ``None`` when ``settings.llms`` is empty or ``settings`` is malformed.

    Accepts ANY object with a ``.llms`` attribute (duck-typed) — tests can pass
    monkeypatched stand-ins without constructing a full ``Settings``.
    """
    try:
        llms = getattr(settings, "llms", None)
        if not llms:
            return None
        default_name = getattr(getattr(settings, "app", None), "default_llm", None)
        cfg = next((l for l in llms if getattr(l, "name", None) == default_name), None)
        return cfg or llms[0]
    except Exception:  # noqa: BLE001 — defensive: never raise from resolver
        return None


def resolve_active_backend_name(settings: Any) -> str:
    """Return the user-facing backend label: 'OpenAI' or 'Ollama'.

    Defaults to ``'Ollama'`` (D-19) when no LLM is configured or ``cfg.type``
    is anything other than ``'openai'``. Used by templates (loading text
    "Summarizing… (using {Ollama|OpenAI})") and by the summary route's error
    classifier (passed as ``backend_name``).
    """
    cfg = resolve_active_llm(settings)
    if cfg is None:
        return "Ollama"
    cfg_type = getattr(cfg, "type", "ollama")
    return "OpenAI" if cfg_type == "openai" else "Ollama"
