"""PydanticAI-native model factory for Phase 2 NL agent.

This is a NEW parallel path — the legacy OpenAIAdapter / OllamaAdapter in this
package remain for Phase 1 code (generate_sql / stream_text). The NL agent
does NOT use them. See RESEARCH.md Pitfall 2.

Threat mitigations (T-02-01-01, T-02-01-03):
- api_key is never logged or printed
- Unsupported cfg.type values raise ValueError immediately (no silent fallback)
"""
from __future__ import annotations

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider

from app.core.config import LLMConfig


def build_pydantic_model(cfg: LLMConfig):
    """Return a PydanticAI model object for the given LLMConfig (NL-08).

    Supported cfg.type values: "openai", "ollama". All other types raise ValueError.
    The legacy adapters in openai_adapter.py / ollama_adapter.py are NOT used
    by the PydanticAI agent — they serve the Phase 1 generate_sql path.

    Defaults:
      - openai model: "gpt-4o-mini" if cfg.model is empty
      - openai api_key: cfg.api_key or OPENAI_API_KEY env var (OpenAIProvider default)
      - openai base_url: cfg.endpoint or None (defaults to api.openai.com/v1)
      - ollama model: "qwen2.5:7b" if cfg.model is empty
      - ollama base_url: (cfg.endpoint or "http://localhost:11434") + "/v1"

    Security note (T-02-01-01): cfg.api_key is passed to OpenAIProvider but never
    logged or surfaced in error messages.
    """
    if cfg.type == "openai":
        provider = OpenAIProvider(
            api_key=cfg.api_key or None,
            base_url=cfg.endpoint or None,
        )
        return OpenAIChatModel(cfg.model or "gpt-4o-mini", provider=provider)

    if cfg.type == "ollama":
        endpoint = (cfg.endpoint or "http://localhost:11434").rstrip("/")
        provider = OllamaProvider(base_url=f"{endpoint}/v1")
        return OllamaModel(cfg.model or "qwen2.5:7b", provider=provider)

    raise ValueError(
        f"Unsupported LLM type for PydanticAI agent: {cfg.type!r}. "
        "Only 'openai' and 'ollama' are supported."
    )
