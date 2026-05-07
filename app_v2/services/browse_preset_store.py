"""Filter-preset loader for the Browse (Pivot grid) page (260507-r0k).

Sibling to ``app_v2/services/preset_store.py`` (which serves the Overview
page). The two loaders are intentionally separate because the two pages
have different filter shapes:

  - Overview: 6-facet whitelist (status, customer, ap_company, device,
    controller, application) — preset_store.py imports FILTERABLE_COLUMNS
    from joint_validation_grid_service and rejects entries whose facet
    keys aren't in that whitelist.
  - Browse:   2-list model (platforms[] + params[]) + swap_axes bool.
    No facet whitelist; the values are free-form strings sourced from
    the live ufs_data table catalog at click-time.

Mirrors preset_store.py's structural decisions verbatim:
  - Same fallback chain shape: config/browse_presets.yaml →
    config/browse_presets.example.yaml → [].
  - yaml.safe_load discipline (T-05-02-01: never use full Loader on
    user files).
  - Per-entry validation in plain Python (TypedDict, NOT Pydantic) so a
    malformed entry can be skipped without raising.
  - Each rejection is logged at WARNING; never raises.
  - No caching — same rationale as starter_prompts.py and preset_store.py.

"Malformed" means ANY of:
  - top-level YAML is not a list → return []
  - entry is not a dict → drop
  - missing or non-string ``name`` → drop
  - missing or non-string ``label`` → drop
  - ``platforms`` present but not a list of non-empty strings → drop
  - ``params`` present but not a list of non-empty strings → drop
  - BOTH ``platforms`` and ``params`` empty/missing → drop (a preset with
    nothing selected would render the empty-state — same outcome as
    Clear all, no point in a preset for it)
  - ``swap_axes`` present but not a bool → drop (typed clearly so users
    don't accidentally pass strings)

Note: we deliberately do NOT validate platforms/params against the live
DB catalog here. A preset referencing a platform the DB no longer
contains will simply produce an empty grid at click-time — the same
behavior as a stale bookmarked /browse?platforms=… URL. Validating
against the live catalog at load time would couple the loader to the DB
adapter and require live DB access during test collection, which the
existing test suite explicitly avoids (TestClient + MockDB pattern).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TypedDict

import yaml

log = logging.getLogger(__name__)


class BrowsePreset(TypedDict, total=False):
    """Validated browse-preset entry.

    Plain TypedDict (not Pydantic) — load_browse_presets does the
    validation in plain Python so a malformed entry can be skipped
    without raising. ``swap_axes`` is optional (defaults to False at the
    consumer site).
    """
    name: str
    label: str
    platforms: list[str]
    params: list[str]
    swap_axes: bool


def _coerce_entry(raw: object) -> BrowsePreset | None:
    """Return a validated BrowsePreset or None if anything is malformed.

    Logs the rejection reason at WARNING so a user editing
    config/browse_presets.yaml can debug a preset that "isn't showing
    up". Never raises.
    """
    if not isinstance(raw, dict):
        log.warning("browse preset rejected: not a mapping (got %s)",
                    type(raw).__name__)
        return None
    name = raw.get("name")
    label = raw.get("label")
    if not isinstance(name, str) or not name.strip():
        log.warning("browse preset rejected: missing or non-string 'name'")
        return None
    if not isinstance(label, str) or not label.strip():
        log.warning("browse preset rejected (%s): missing or non-string 'label'",
                    name)
        return None
    platforms = raw.get("platforms", [])
    params = raw.get("params", [])
    if not isinstance(platforms, list) or not all(
        isinstance(v, str) and v for v in platforms
    ):
        log.warning(
            "browse preset rejected (%s): 'platforms' must be a list of "
            "non-empty strings", name,
        )
        return None
    if not isinstance(params, list) or not all(
        isinstance(v, str) and v for v in params
    ):
        log.warning(
            "browse preset rejected (%s): 'params' must be a list of "
            "non-empty strings", name,
        )
        return None
    if not platforms and not params:
        log.warning(
            "browse preset rejected (%s): both 'platforms' and 'params' "
            "are empty — preset would render the empty state", name,
        )
        return None
    swap_axes_raw = raw.get("swap_axes", False)
    if not isinstance(swap_axes_raw, bool):
        log.warning(
            "browse preset rejected (%s): 'swap_axes' must be a bool "
            "(true/false), got %s", name, type(swap_axes_raw).__name__,
        )
        return None
    out: BrowsePreset = {
        "name": name,
        "label": label,
        "platforms": list(platforms),
        "params": list(params),
        "swap_axes": swap_axes_raw,
    }
    return out


def load_browse_presets() -> list[BrowsePreset]:
    """Load + validate browse presets from the YAML fallback chain.

    Returns:
        list of BrowsePreset dicts in YAML file order. Empty list on:
          - file not found in either location,
          - YAML parse error,
          - top-level not a list,
          - all entries malformed.
    """
    for filename in (
        "config/browse_presets.yaml",
        "config/browse_presets.example.yaml",
    ):
        path = Path(filename)
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or []
            except yaml.YAMLError as exc:
                log.warning("browse preset YAML parse error in %s: %s",
                            filename, exc)
                return []
            if not isinstance(data, list):
                log.warning("browse preset YAML in %s is not a list", filename)
                return []
            return [
                p for p in (_coerce_entry(e) for e in data) if p is not None
            ]
    return []
