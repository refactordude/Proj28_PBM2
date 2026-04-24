"""Ollama JSON extraction fallback chain (NL-09, D-23).

Called when PydanticAI's tool-call parsing fails because a smaller Ollama model
emitted imperfect JSON. Pure function — no I/O, no logging beside returning None.

Chain order:
  1. json.loads(raw) — clean JSON
  2. Strip markdown code fences (```json...``` or ```...```), retry json.loads
  3. Regex first `{...}` block (DOTALL), retry json.loads
  4. Return None — all fallbacks failed

Only dict results are returned. JSON arrays (lists) are treated as failures
because the agent always produces a dict (SQLResult or ClarificationNeeded).
"""
from __future__ import annotations

import json
import re

# Matches opening ``` or ```json fence and closing ``` fence.
# re.DOTALL | re.IGNORECASE needed because the fence may span lines.
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.DOTALL | re.IGNORECASE)


def extract_json(raw: str) -> dict | None:
    """Try to extract a JSON dict from raw LLM output using a 3-stage fallback.

    Args:
        raw: Raw string output from the LLM — may be clean JSON, markdown-fenced
             JSON, or prose containing an embedded JSON block.

    Returns:
        A dict if any stage succeeds, or None if all fallbacks fail.
        Never raises an exception.
    """
    if not raw:
        return None

    # Stage 1: Try direct parse — handles clean JSON output
    try:
        loaded = json.loads(raw)
        if isinstance(loaded, dict):
            return loaded
    except json.JSONDecodeError:
        pass

    # Stage 2: Strip markdown code fences and retry
    # Handles: ```json\n{...}\n``` and ```\n{...}\n```
    stripped = _FENCE_RE.sub("", raw.strip())
    try:
        loaded = json.loads(stripped)
        if isinstance(loaded, dict):
            return loaded
    except json.JSONDecodeError:
        pass

    # Stage 3: Regex first { ... } block (DOTALL) — handles prose-wrapped JSON
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            loaded = json.loads(match.group())
            if isinstance(loaded, dict):
                return loaded
        except json.JSONDecodeError:
            pass

    # All fallbacks failed
    return None
