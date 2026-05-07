"""Filter-preset loader for the Overview (Joint Validation) page (260507-obp).

Mirrors ``app_v2/services/starter_prompts.py`` deliberately — same fallback
chain shape (config/presets.yaml → config/presets.example.yaml → []), same
yaml.safe_load discipline (T-05-02-01: never use full Loader on user files).

Each returned entry has ``name`` (slug str), ``label`` (display str), and
``filters`` (dict[str, list[str]] keyed by a subset of FILTERABLE_COLUMNS).
Malformed entries are silently dropped — this never raises.

"Malformed" means ANY of:
  - top-level YAML is not a list → return []
  - entry is not a dict → drop
  - missing ``name`` or ``label`` (or non-string) → drop
  - ``filters`` missing or not a dict → drop
  - ANY filters key is not in FILTERABLE_COLUMNS → drop the entry entirely
    (NOT just the bad key — keep semantics simple: a typoed facet key in a
     preset means the whole preset is broken)
  - ANY filters value is not a list of strings → drop entry
  - empty values list for a facet → drop entry (defeats the point of a
    preset; an empty preset would clear all filters which the existing
    "Clear all" link already does)

Caching: not added. Same rationale as starter_prompts.py — called only on
GET /overview (page render) + GET /overview/preset/<name> (rare); YAML
file is < 4 KB; lru_cache would prevent live edits without restart.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TypedDict

import yaml

from app_v2.services.joint_validation_grid_service import FILTERABLE_COLUMNS

log = logging.getLogger(__name__)


class Preset(TypedDict):
    """Validated preset entry. Plain TypedDict (not Pydantic) — load_presets
    does the validation in plain Python so a malformed entry can be skipped
    without raising; Pydantic would force us into try/except per-entry."""
    name: str
    label: str
    filters: dict[str, list[str]]


def _coerce_entry(raw: object) -> Preset | None:
    """Return a validated Preset or None if anything is malformed.

    Logs the rejection reason at WARNING so users can debug a preset that
    "isn't showing up". Logging never aborts; loader always returns the
    valid subset.
    """
    if not isinstance(raw, dict):
        log.warning("preset rejected: not a mapping (got %s)", type(raw).__name__)
        return None
    name = raw.get("name")
    label = raw.get("label")
    filters = raw.get("filters")
    if not isinstance(name, str) or not name.strip():
        log.warning("preset rejected: missing or non-string 'name'")
        return None
    if not isinstance(label, str) or not label.strip():
        log.warning("preset rejected (%s): missing or non-string 'label'", name)
        return None
    if not isinstance(filters, dict):
        log.warning("preset rejected (%s): 'filters' is missing or not a mapping", name)
        return None
    cleaned: dict[str, list[str]] = {}
    for key, vals in filters.items():
        if key not in FILTERABLE_COLUMNS:
            log.warning(
                "preset rejected (%s): unknown facet '%s' — must be one of %s",
                name, key, FILTERABLE_COLUMNS,
            )
            return None
        if not isinstance(vals, list) or not vals:
            log.warning(
                "preset rejected (%s): facet '%s' must be a non-empty list",
                name, key,
            )
            return None
        if not all(isinstance(v, str) and v for v in vals):
            log.warning(
                "preset rejected (%s): facet '%s' values must be non-empty strings",
                name, key,
            )
            return None
        cleaned[key] = list(vals)
    if not cleaned:
        log.warning("preset rejected (%s): no valid facets", name)
        return None
    return Preset(name=name, label=label, filters=cleaned)


def load_presets() -> list[Preset]:
    """Load + validate presets from the YAML fallback chain.

    Returns:
        list of Preset dicts in YAML file order. Empty list on:
          - file not found in either location,
          - YAML parse error,
          - top-level not a list,
          - all entries malformed.
    """
    for filename in ("config/presets.yaml", "config/presets.example.yaml"):
        path = Path(filename)
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or []
            except yaml.YAMLError as exc:
                log.warning("preset YAML parse error in %s: %s", filename, exc)
                return []
            if not isinstance(data, list):
                log.warning("preset YAML in %s is not a list", filename)
                return []
            return [p for p in (_coerce_entry(e) for e in data) if p is not None]
    return []
