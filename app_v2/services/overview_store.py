"""YAML-backed curated-entity store for the Overview tab (OVERVIEW-05, D-22..D-24).

Single source of truth for the curated list. ALL Phase 2 routes (02-02 add/remove,
02-03 filter) go through this module — routes never read/write the YAML directly.

Storage layout (D-22):
    config/overview.yaml  (gitignored)
      entities:
        - platform_id: Samsung_S22Ultra_SM8450
          added_at: 2026-04-25T10:30:00Z

Atomic writes (D-24): NamedTemporaryFile in the target directory + os.replace.
A mid-write crash leaves either the old file or the new file intact; never a
half-written YAML that would crash load_overview() on next startup.

Defensive reads (CONTEXT.md specifics): missing file = [], malformed YAML = [] (warn, don't crash).
"""
from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

_log = logging.getLogger(__name__)

# Module-level path constant — tests monkeypatch this; production value unchanged.
OVERVIEW_YAML: Path = Path("config/overview.yaml")


class OverviewEntity(BaseModel):
    """One curated entry. Per D-22 schema."""

    platform_id: str = Field(..., min_length=1)
    added_at: datetime

    @field_validator("platform_id")
    @classmethod
    def _platform_id_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("platform_id must be non-empty")
        return v


class DuplicateEntityError(ValueError):
    """Raised by add_overview when platform_id already exists in the list."""


def load_overview() -> list[OverviewEntity]:
    """Read config/overview.yaml; return entities sorted newest-first.

    Returns [] when the file is missing, empty, or malformed. Malformed YAML
    logs a warning (never raises) so startup and filter requests stay resilient.
    """
    path = OVERVIEW_YAML
    if not path.exists():
        return []
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        _log.warning("overview.yaml malformed; returning empty list: %s", exc)
        return []
    if not isinstance(raw, dict):
        _log.warning("overview.yaml top-level is not a mapping; returning empty list")
        return []
    entries = raw.get("entities") or []
    if not isinstance(entries, list):
        _log.warning("overview.yaml 'entities' is not a list; returning empty list")
        return []
    out: list[OverviewEntity] = []
    for item in entries:
        try:
            out.append(OverviewEntity.model_validate(item))
        except Exception as exc:  # noqa: BLE001
            _log.warning("skipping invalid overview entry %r: %s", item, exc)
    # D-24: newest-first (added_at desc).
    out.sort(key=lambda e: e.added_at, reverse=True)
    return out


def _atomic_write(entities: list[OverviewEntity]) -> None:
    """Write entities to OVERVIEW_YAML atomically (tempfile + os.replace).

    Creates parent directory if missing. Serializes added_at as ISO-8601 with Z.
    """
    path = OVERVIEW_YAML
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "entities": [
            {
                "platform_id": e.platform_id,
                # Format YYYY-MM-DDTHH:MM:SSZ — matches D-22 example.
                "added_at": e.added_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            for e in entities
        ],
    }
    # Tempfile in SAME directory so os.replace is a rename within one filesystem.
    fd, tmp_name = tempfile.mkstemp(
        prefix=".overview.", suffix=".yaml.tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            yaml.safe_dump(doc, fh, sort_keys=False, default_flow_style=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except Exception:
        # Clean up tempfile on any failure before re-raising.
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def add_overview(platform_id: str) -> OverviewEntity:
    """Prepend a new entity (newest-first). Raise DuplicateEntityError on conflict.

    D-22: insertion order preserved in the YAML list (newest at top).
    D-24: atomic write; DuplicateEntityError raised without modifying disk.
    """
    current = load_overview()
    if any(e.platform_id == platform_id for e in current):
        raise DuplicateEntityError(
            f"platform_id already exists in overview: {platform_id}"
        )
    new_entity = OverviewEntity(
        platform_id=platform_id,
        added_at=datetime.now(timezone.utc),
    )
    # Prepend — newest at top of file AND newest at index 0 of load_overview().
    _atomic_write([new_entity, *current])
    return new_entity


def remove_overview(platform_id: str) -> bool:
    """Remove platform_id if present. Return True if removed, False if not found.

    D-24: no write happens when platform_id is not found (no-op).
    """
    current = load_overview()
    remaining = [e for e in current if e.platform_id != platform_id]
    if len(remaining) == len(current):
        return False
    _atomic_write(remaining)
    return True
