"""AI Summary service: TTLCache + Lock + openai SDK single-shot (D-17..D-21, SUMMARY-04..06).

Architecture (Pattern 4-6 from 03-RESEARCH.md):

- Module-level ``TTLCache(maxsize=128, ttl=3600)`` — D-17 verbatim.
- Module-level ``threading.Lock`` — paired with cache (Pitfall 11). NEVER held
  during the LLM call (would serialize all summary requests behind a single
  slow Ollama cold-start).
- Cache key: ``hashkey(platform_id, mtime_ns, llm_name, llm_model)``. Sharpened
  from D-17's ``mtime`` (float) to ``mtime_ns`` (int) per Pitfall 13 — sub-second
  precision avoids stale summaries after a same-second edit on filesystems that
  round mtime to whole seconds.
- ``openai`` SDK with ``base_url`` for Ollama (OpenAI-compat ``/v1``) AND OpenAI
  direct (Pattern 5). No ``litellm``, no separate Ollama SDK.
- Errors classified to a fixed 7-string vocabulary; raw exception messages
  NEVER returned to the user (T-03-02 / UI-SPEC §8c).
- Regenerate (D-18): skip lookup, still write back. A subsequent normal click
  hits the new value.

Public surface used by ``app_v2/routers/summary.py``:

- ``SummaryResult`` dataclass — text + llm_name + llm_model + generated_at.
- ``LLMNotConfiguredError`` — raised when ``settings.llms`` is empty (route
  maps to amber error fragment with reason "LLM not configured").
- ``get_or_generate_summary(pid, cfg, content_dir, *, regenerate=False)``.
- ``_classify_error(exc, backend_name)`` — exception → 7-string vocabulary.
- ``_build_client(cfg)`` — OpenAI client factory (Ollama or OpenAI).
- ``clear_summary_cache()`` — test helper.
"""
from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
from cachetools import TTLCache
from cachetools.keys import hashkey
from openai import (
    OpenAI,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)

from app.core.config import LLMConfig
from app_v2.data.summary_prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from app_v2.services.content_store import (
    get_content_mtime_ns,
    read_content,
)

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SummaryResult:
    """Cached summary value object. Used by templates for the metadata footer."""

    text: str
    llm_name: str
    llm_model: str
    generated_at: datetime  # UTC tz-aware


class LLMNotConfiguredError(RuntimeError):
    """Raised when ``settings.llms`` is empty.

    The route maps this to a 200 response carrying the amber error fragment
    with reason "LLM not configured — set one in Settings".
    """


# D-17: TTLCache(maxsize=128, ttl=3600). Module-level singleton.
_summary_cache: TTLCache = TTLCache(maxsize=128, ttl=3600)
_summary_lock = threading.Lock()


def _build_client(cfg: LLMConfig) -> OpenAI:
    """Build an ``openai.OpenAI`` client for either Ollama or OpenAI.

    Ollama: ``base_url=<endpoint>/v1``, ``api_key='ollama'`` (any non-empty).
    OpenAI: ``base_url=<endpoint or default>``, api_key from cfg or
    ``OPENAI_API_KEY`` env.

    Pitfall 18 (Ollama cold-start) — DEVIATION from RESEARCH.md Q3:
    The 60s read timeout below is the chosen mitigation strategy. We do NOT
    implement the lifespan-time warmup ping that RESEARCH.md recommended.
    Rationale: the app must start cleanly even if Ollama is unreachable;
    first-request cold start is acceptable for an internal tool with low
    concurrency. Lifespan warmup is deferred until cold-start latency proves
    user-visible. See ``app_v2/main.py`` lifespan for the matching deviation
    comment on the app-startup side.
    """
    if cfg.type == "ollama":
        base_url = (cfg.endpoint or "http://localhost:11434").rstrip("/") + "/v1"
        return OpenAI(
            api_key="ollama",
            base_url=base_url,
            timeout=httpx.Timeout(60.0),
        )
    # OpenAI (or anything else — default to OpenAI semantics).
    api_key = cfg.api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OpenAI API key not configured")
    return OpenAI(
        api_key=api_key,
        base_url=cfg.endpoint or None,
        timeout=httpx.Timeout(30.0),
    )


def _call_llm_single_shot(content: str, cfg: LLMConfig) -> str:
    """Call ``chat.completions.create(stream=False)``; return stripped text.

    D-20: ``SYSTEM_PROMPT`` (untrusted-tag instruction) + ``USER_PROMPT_TEMPLATE``
    (wraps content in ``<notes>...</notes>``).
    D-21: ``stream=False`` (single-shot per SUMMARY-04 spec).
    """
    client = _build_client(cfg)
    # Default model fallbacks per Research Pattern 5.
    model = cfg.model or ("gpt-4o-mini" if cfg.type == "openai" else "llama3.1")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(markdown_content=content),
            },
        ],
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        stream=False,
    )
    return (resp.choices[0].message.content or "").strip()


def _classify_error(exc: Exception, backend_name: str) -> str:
    """Map openai 2.x / httpx exceptions to UI-SPEC §8c error vocabulary.

    Order matters: more-specific exception classes BEFORE more-general ones.
    Notably ``APITimeoutError`` is a subclass of ``APIConnectionError`` in the
    openai 2.x SDK — so the timeout check MUST come first or every timeout
    would be misclassified as a connection error.

    ``APIConnectionError`` typically wraps ``httpx.ConnectError``; the
    ``isinstance`` covers both at the same call site.

    Returns one of the 7 fixed user-facing strings (no leakage of stack/keys/paths).
    """
    # Timeout must be checked BEFORE APIConnectionError (which is its base class).
    if isinstance(exc, (APITimeoutError, httpx.ReadTimeout, httpx.WriteTimeout)):
        return "LLM took too long to respond"
    if isinstance(exc, (APIConnectionError, httpx.ConnectError, httpx.ConnectTimeout)):
        return f"Cannot reach the LLM backend ({backend_name})"
    if isinstance(exc, AuthenticationError):
        return "LLM authentication failed — check API key in Settings"
    if isinstance(exc, RateLimitError):
        return "LLM is rate-limited — try again in a moment"
    if isinstance(exc, APIStatusError):
        status = getattr(exc, "status_code", 500)
        if status >= 500:
            return f"LLM backend returned an error (HTTP {status})"
    if isinstance(exc, FileNotFoundError):
        return "Content page no longer exists"
    return "Unexpected error — see server logs"


def get_or_generate_summary(
    platform_id: str,
    cfg: LLMConfig,
    content_dir: Path,
    *,
    regenerate: bool = False,
) -> SummaryResult:
    """Cached single-shot summary.

    Reads content + ``mtime_ns`` from disk. Cache key:
    ``hashkey(pid, mtime_ns, name, model)``.

    On ``regenerate=True``: skip lookup BUT still write back (D-18).
    Lock guards only dict access — NEVER held during the LLM call.

    Raises ``FileNotFoundError`` if the content file does not exist.
    Raises any openai/httpx exception on LLM failure (caller classifies).
    """
    mtime_ns = get_content_mtime_ns(platform_id, content_dir)
    if mtime_ns is None:
        raise FileNotFoundError(f"No content for {platform_id}")
    content = read_content(platform_id, content_dir)
    if content is None:
        # Race between mtime_ns and read_content (file deleted between calls).
        raise FileNotFoundError(f"No content for {platform_id}")

    key = hashkey(platform_id, mtime_ns, cfg.name, cfg.model)
    # 1) Cache lookup (skipped on regenerate).
    if not regenerate:
        with _summary_lock:
            cached = _summary_cache.get(key)
        if cached is not None:
            return cached

    # 2) LLM call OUTSIDE the lock (Pitfall 11 — never serialize on slow LLM).
    text = _call_llm_single_shot(content, cfg)
    result = SummaryResult(
        text=text,
        llm_name=cfg.name,
        llm_model=cfg.model
        or ("gpt-4o-mini" if cfg.type == "openai" else "llama3.1"),
        generated_at=datetime.now(timezone.utc),
    )

    # 3) Write back under the same key (regenerate path included — D-18).
    with _summary_lock:
        _summary_cache[key] = result
    return result


def clear_summary_cache() -> None:
    """Test helper: clear the module-level TTLCache.

    Acquires the lock briefly; safe under concurrent reads (they block until
    clear completes).
    """
    with _summary_lock:
        _summary_cache.clear()
