"""Unit tests for build_pydantic_model() factory (NL-08).

Tests verify that the factory returns the correct PydanticAI model class for each
LLMConfig.type, applies default model name fallbacks, and raises ValueError for
unsupported types. No network calls are made — only instance type assertions.
"""
from __future__ import annotations

import pytest
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.ollama import OllamaModel

from app.core.config import LLMConfig
from app.adapters.llm.pydantic_model import build_pydantic_model


# ---------------------------------------------------------------------------
# Test 1: openai type returns OpenAIChatModel
# ---------------------------------------------------------------------------
def test_build_openai_returns_openai_chat_model():
    """build_pydantic_model with type='openai' returns an OpenAIChatModel instance."""
    cfg = LLMConfig(name="o", type="openai", model="gpt-4o-mini")
    model = build_pydantic_model(cfg)
    assert isinstance(model, OpenAIChatModel)


# ---------------------------------------------------------------------------
# Test 2: ollama type returns OllamaModel
# ---------------------------------------------------------------------------
def test_build_ollama_returns_ollama_model():
    """build_pydantic_model with type='ollama' returns an OllamaModel instance."""
    cfg = LLMConfig(name="l", type="ollama", model="qwen2.5:7b", endpoint="http://localhost:11434")
    model = build_pydantic_model(cfg)
    assert isinstance(model, OllamaModel)


# ---------------------------------------------------------------------------
# Test 3: unsupported type raises ValueError with correct message
# ---------------------------------------------------------------------------
def test_build_unsupported_type_raises_value_error():
    """build_pydantic_model with type='anthropic' raises ValueError containing 'Unsupported LLM type'."""
    cfg = LLMConfig(name="x", type="anthropic")
    with pytest.raises(ValueError, match="Unsupported LLM type"):
        build_pydantic_model(cfg)


# ---------------------------------------------------------------------------
# Test 4: empty endpoint for openai results in no custom base_url (uses default)
# ---------------------------------------------------------------------------
def test_build_openai_empty_endpoint_uses_default():
    """build_pydantic_model with endpoint='' passes base_url=None to OpenAIProvider (api.openai.com default)."""
    cfg = LLMConfig(name="o", type="openai", model="gpt-4o-mini", endpoint="")
    # Should not raise; provider defaults to api.openai.com/v1
    model = build_pydantic_model(cfg)
    assert isinstance(model, OpenAIChatModel)


# ---------------------------------------------------------------------------
# Test 5: empty model falls back to defaults
# ---------------------------------------------------------------------------
def test_build_empty_model_uses_fallback_defaults():
    """build_pydantic_model uses 'gpt-4o-mini' for openai and 'qwen2.5:7b' for ollama when model is empty."""
    # openai fallback
    cfg_openai = LLMConfig(name="o", type="openai", model="")
    model_openai = build_pydantic_model(cfg_openai)
    assert isinstance(model_openai, OpenAIChatModel)

    # ollama fallback
    cfg_ollama = LLMConfig(name="l", type="ollama", model="")
    model_ollama = build_pydantic_model(cfg_ollama)
    assert isinstance(model_ollama, OllamaModel)
