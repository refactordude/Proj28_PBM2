"""AI Summary entry point for Joint Validation pages (D-JV-16, Plan 01-03 Task 2).

D-JV-16 pre-processes the Confluence-exported ``index.html`` to remove
``<script>``, ``<style>``, and ``<img>`` nodes (the user explicitly flagged
inline base64 image ``src`` attributes as a token-blow-up risk), calls
``BeautifulSoup.get_text(separator='\\n')``, and collapses runs of blank
lines. The pre-processed text is then handed to the shared LLM helper.

Reuses the Phase 3 ``summary_service`` plumbing — no body duplication:

- ``_summary_cache`` (TTLCache, ``maxsize=128, ttl=3600``) — module-global,
  shared across platform + JV summaries.
- ``_summary_lock`` — same ``threading.Lock`` (Pitfall 11: NEVER held
  during the LLM call).
- ``_call_llm_with_text`` — backend-agnostic chat.completions call
  (Plan 01-03 Task 1 refactor).
- ``SummaryResult`` — same frozen dataclass (``text``, ``llm_name``,
  ``llm_model``, ``generated_at``). The service returns a BARE
  ``SummaryResult``; the router renders the markdown to HTML and computes
  the cached age from ``result.generated_at`` itself. Mirrors
  ``routers/summary.py:156-180`` exactly.

Cache key includes a literal ``"jv"`` string discriminator so JV and
platform summaries cannot collide on the same numeric id (Pitfall 3,
T-03-02).

Per CONTEXT.md researcher_open_questions resolution #1: NO new truncation
step. The existing ``AgentConfig.max_context_tokens`` cap continues to
govern. The pre-processed text is passed straight to ``_call_llm_with_text``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from cachetools.keys import hashkey

# CANONICAL: LLMConfig lives at app.core.config. Verified at
# app_v2/services/summary_service.py:51. There is NO app_v2/core/ package.
from app.core.config import LLMConfig
from app_v2.data.jv_summary_prompt import JV_SYSTEM_PROMPT, JV_USER_PROMPT_TEMPLATE
from app_v2.services.summary_service import (
    SummaryResult,
    _call_llm_with_text,
    _summary_cache,
    _summary_lock,
)


def _strip_to_text(html_bytes: bytes) -> str:
    """Reduce a Confluence-export HTML to plain text suitable for an LLM prompt.

    Decomposes ``<script>``, ``<style>``, and ``<img>`` so their inner text
    and attributes never reach ``get_text()``. The ``<img src="data:...">``
    base64 payload is the specific bloat the user flagged in D-JV-16 —
    ``decompose()`` removes the tag entirely (including attributes), so even
    attribute serialization cannot leak base64 into the prompt.

    Returns plain ``str`` (wrapping with ``str(...)`` would cost almost
    nothing, but ``"\\n".join`` of ordinary strings already returns a plain
    ``str``; we preserve that contract via the explicit string conversion
    of the BS4 ``get_text`` result).
    """
    try:
        soup = BeautifulSoup(html_bytes, "lxml")
    except Exception:  # noqa: BLE001 — defensive parser fallback
        soup = BeautifulSoup(html_bytes, "html.parser")
    for tag in soup(["script", "style", "img"]):
        tag.decompose()
    text = str(soup.get_text(separator="\n"))
    # Collapse runs of >=2 blank lines to a single blank line.
    lines = [ln.rstrip() for ln in text.splitlines()]
    out: list[str] = []
    prev_blank = False
    for ln in lines:
        is_blank = not ln.strip()
        if is_blank and prev_blank:
            continue
        out.append(ln)
        prev_blank = is_blank
    return "\n".join(out).strip()


def get_or_generate_jv_summary(
    confluence_page_id: str,
    cfg: LLMConfig,
    jv_root: Path,
    *,
    regenerate: bool = False,
) -> SummaryResult:
    """Cached single-shot summary for a Joint Validation page.

    Cache: ``TTLCache(maxsize=128, ttl=3600)`` shared with platform summaries.
    Key shape: ``hashkey("jv", confluence_page_id, mtime_ns, cfg.name, cfg.model)``
    — the literal ``"jv"`` string discriminator prevents collision with
    platform summaries that hash on
    ``(platform_id, mtime_ns, cfg.name, cfg.model)``.

    Returns a BARE :class:`SummaryResult` (frozen dataclass: ``text``,
    ``llm_name``, ``llm_model``, ``generated_at``). The router caller
    renders the text to HTML and derives the cached age from these fields
    — mirrors ``routers/summary.py:156-180`` exactly.

    Raises :class:`FileNotFoundError` when ``index.html`` is missing —
    caller (router) wraps in try/except to honor the always-200 contract.
    """
    index_html = jv_root / confluence_page_id / "index.html"
    if not index_html.is_file():
        raise FileNotFoundError(f"No index.html for JV {confluence_page_id}")
    mtime_ns = index_html.stat().st_mtime_ns
    key = hashkey("jv", confluence_page_id, mtime_ns, cfg.name, cfg.model)

    if not regenerate:
        with _summary_lock:
            cached = _summary_cache.get(key)
        if cached is not None:
            # Return cached SummaryResult UNCHANGED — frozen dataclass, no
            # mutation. Age computation lives in the router (Plan 04 Task 3),
            # mirroring routers/summary.py lines 156-162.
            return cached

    html_bytes = index_html.read_bytes()
    text = _strip_to_text(html_bytes)

    # LLM call OUTSIDE the lock (Pitfall 11 — never serialize on slow LLM).
    raw = _call_llm_with_text(text, cfg, JV_SYSTEM_PROMPT, JV_USER_PROMPT_TEMPLATE)

    # SummaryResult is a frozen dataclass — fields EXACTLY:
    #   text, llm_name, llm_model, generated_at (UTC tz-aware datetime).
    # Verified at app_v2/services/summary_service.py:61-68.
    result = SummaryResult(
        text=raw,
        llm_name=cfg.name,
        llm_model=cfg.model,
        generated_at=datetime.now(timezone.utc),
    )
    with _summary_lock:
        _summary_cache[key] = result
    return result
