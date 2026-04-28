"""Starter-prompt loader for the Ask page (ASK-V2-08).

Ports v1.0's ``app/pages/ask.py::load_starter_prompts`` verbatim into a
framework-agnostic v2.0 service module. v1.0's ``app/pages/ask.py`` is
deleted in Plan 06-06; the v2.0 Ask route depends on this function existing
BEFORE that deletion happens (Plan 06-03 is the consumer).

Why a separate module instead of import-from-v1.0:
- ``app/pages/ask.py`` calls ``nest_asyncio.apply()`` at module top (line 9)
  and imports ``streamlit`` — both incompatible with the FastAPI process
  (RESEARCH.md Pitfall 5). A direct import would either fail or globally
  rewire the asyncio runner.
- Phase 6 D-22 deletes ``app/pages/ask.py`` outright. Re-implementing the
  loader in v2.0 keeps the v2.0 Ask page self-sufficient post-deletion.

Fallback chain (ASK-V2-08 / D-02 / v1.0 ONBD-02):
  1. ``config/starter_prompts.yaml`` (user-local, gitignored)
  2. ``config/starter_prompts.example.yaml`` (committed template, 8 entries)
  3. ``[]`` — graceful degradation: the Ask page renders without the chip
     gallery; everything else still works.

Each returned entry has ``label`` (str) and ``question`` (str). Malformed
YAML, non-list top-level, and entries missing either key are silently
dropped — the loader never raises.

Caching: not added. The loader is called only by ``GET /ask`` (page render),
not on every HTMX fragment swap. The YAML file is < 1KB. ``functools.lru_cache``
is unnecessary here and would prevent the user from seeing edits to
``config/starter_prompts.yaml`` without a server restart.
"""
from __future__ import annotations

from pathlib import Path

import yaml


def load_starter_prompts() -> list[dict]:
    """Load starter prompts from the YAML fallback chain.

    Returns:
        list of {"label": str, "question": str} dicts. Empty list on any
        failure path (no YAML found, malformed YAML, non-list top-level,
        no entries with both keys).
    """
    for filename in ("config/starter_prompts.yaml", "config/starter_prompts.example.yaml"):
        path = Path(filename)
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or []
                if isinstance(data, list):
                    return [
                        e for e in data
                        if isinstance(e, dict) and "label" in e and "question" in e
                    ]
            except yaml.YAMLError:
                return []
    return []
