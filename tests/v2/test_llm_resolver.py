"""Unit tests for app_v2.services.llm_resolver (TDD RED phase).

Resolver contract (RESEARCH.md Open Question #2 RESOLVED):
- resolve_active_llm(settings) — returns LLMConfig or None.
  1. Match settings.llms entry whose `name` equals settings.app.default_llm.
  2. Fall back to settings.llms[0] when no match.
  3. Return None when settings.llms is empty or settings is malformed.
- resolve_active_backend_name(settings) — returns "OpenAI" / "Ollama".
  Defaults to "Ollama" (D-19) when no LLM is configured or type is unknown.

Single source of truth — eliminates the 3-way duplication of inline
`_resolve_active_llm` / `_resolve_backend_name` across overview / platforms /
summary routers (consumed by Plans 03-02 and 03-03).
"""
from __future__ import annotations

from app.core.config import AppConfig, LLMConfig, Settings
from app_v2.services.llm_resolver import (
    resolve_active_backend_name,
    resolve_active_llm,
)


# --------------------------------------------------------------------------- #
# resolve_active_llm
# --------------------------------------------------------------------------- #

def test_resolve_active_llm_returns_default_match():
    """settings.app.default_llm matches the second of two LLMs → returns the second."""
    llms = [
        LLMConfig(name="cloud", type="openai", model="gpt-4o-mini"),
        LLMConfig(name="local", type="ollama", model="llama3"),
    ]
    settings = Settings(
        llms=llms,
        app=AppConfig(default_llm="local"),
    )
    cfg = resolve_active_llm(settings)
    assert cfg is not None
    assert cfg.name == "local"
    assert cfg.type == "ollama"


def test_resolve_active_llm_falls_back_to_first_when_name_unknown():
    """default_llm name does not exist in llms → returns settings.llms[0]."""
    llms = [
        LLMConfig(name="cloud", type="openai", model="gpt-4o-mini"),
        LLMConfig(name="local", type="ollama", model="llama3"),
    ]
    settings = Settings(
        llms=llms,
        app=AppConfig(default_llm="does-not-exist"),
    )
    cfg = resolve_active_llm(settings)
    assert cfg is not None
    assert cfg.name == "cloud", "should fall back to first LLM when default_llm is unknown"


def test_resolve_active_llm_returns_none_when_llms_empty():
    """settings.llms == [] → returns None."""
    settings = Settings(llms=[], app=AppConfig(default_llm="anything"))
    assert resolve_active_llm(settings) is None


def test_resolve_active_llm_returns_none_when_settings_missing_attr():
    """Defensive: object without .llms attribute → returns None (does not raise)."""
    class Bare:
        pass

    assert resolve_active_llm(Bare()) is None
    # Even None as input should not raise.
    assert resolve_active_llm(None) is None


# --------------------------------------------------------------------------- #
# resolve_active_backend_name
# --------------------------------------------------------------------------- #

def test_resolve_active_backend_name_openai():
    """cfg.type == 'openai' → 'OpenAI'."""
    settings = Settings(
        llms=[LLMConfig(name="cloud", type="openai", model="gpt-4o-mini")],
        app=AppConfig(default_llm="cloud"),
    )
    assert resolve_active_backend_name(settings) == "OpenAI"


def test_resolve_active_backend_name_ollama():
    """cfg.type == 'ollama' → 'Ollama'."""
    settings = Settings(
        llms=[LLMConfig(name="local", type="ollama", model="llama3")],
        app=AppConfig(default_llm="local"),
    )
    assert resolve_active_backend_name(settings) == "Ollama"


def test_resolve_active_backend_name_default_when_no_llm():
    """settings.llms == [] → returns 'Ollama' (D-19 default)."""
    settings = Settings(llms=[], app=AppConfig(default_llm=""))
    assert resolve_active_backend_name(settings) == "Ollama"


def test_resolve_active_backend_name_unknown_type_falls_back_to_ollama():
    """cfg.type is some unexpected value (e.g. 'vllm') → 'Ollama' (anything-non-openai)."""
    settings = Settings(
        llms=[LLMConfig(name="weird", type="vllm", model="x")],
        app=AppConfig(default_llm="weird"),
    )
    assert resolve_active_backend_name(settings) == "Ollama"


# --- Phase 6 D-15 / D-17: cookie-aware resolution ------------------------

def test_resolve_active_llm_cookie_overrides_default():
    """D-17: a valid pbm2_llm cookie value overrides settings.app.default_llm."""
    from types import SimpleNamespace
    settings = SimpleNamespace(
        app=SimpleNamespace(default_llm="ollama-local"),
        llms=[
            SimpleNamespace(name="ollama-local", type="ollama"),
            SimpleNamespace(name="openai-prod", type="openai"),
        ],
    )
    request = SimpleNamespace(cookies={"pbm2_llm": "openai-prod"})
    cfg = resolve_active_llm(settings, request)
    assert cfg is not None
    assert cfg.name == "openai-prod"


def test_resolve_active_llm_invalid_cookie_falls_back_silently():
    """D-15: cookie value not in settings.llms[].name → silent fallback to default."""
    from types import SimpleNamespace
    settings = SimpleNamespace(
        app=SimpleNamespace(default_llm="ollama-local"),
        llms=[
            SimpleNamespace(name="ollama-local", type="ollama"),
            SimpleNamespace(name="openai-prod", type="openai"),
        ],
    )
    request = SimpleNamespace(cookies={"pbm2_llm": "evil-tampered-value"})
    cfg = resolve_active_llm(settings, request)
    assert cfg is not None
    assert cfg.name == "ollama-local"  # default, not the tampered value
