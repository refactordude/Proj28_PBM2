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
import threading
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

from app_v2.data.atomic_write import atomic_write_bytes

_log = logging.getLogger(__name__)

# Module-level path constant — tests monkeypatch this; production value unchanged.
OVERVIEW_YAML: Path = Path("config/overview.yaml")

# Module-level lock guarding the read-modify-write critical section in
# add_overview / remove_overview. FastAPI dispatches def routes to a threadpool
# (INFRA-05 / Pitfall 4), so two concurrent POST /overview/add requests can run
# in parallel threads. Without this lock, both threads would load_overview()
# before either _atomic_write()s, and the second write silently wipes the first.
# Per-process lock is sufficient (single-uvicorn-process intranet deployment).
# If multi-worker deployment is added, switch to fcntl.flock on the YAML file.
_store_lock = threading.Lock()


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
    """YAML-serialize entities and write atomically to OVERVIEW_YAML.

    Delegates the POSIX-atomic write + mode preservation to the shared helper
    ``app_v2.data.atomic_write.atomic_write_bytes`` (single source of truth —
    same idiom used by Phase 03 content_store for markdown files).

    ``default_mode=0o666`` preserves the prior overview_store new-file behavior
    (umask-applied 0o644 on a typical Linux system); the helper handles the
    ``& ~umask`` calculation and existing-mode preservation.
    """
    path = OVERVIEW_YAML
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
    payload = yaml.safe_dump(doc, sort_keys=False, default_flow_style=False).encode("utf-8")
    atomic_write_bytes(path, payload, default_mode=0o666)


def add_overview(platform_id: str) -> OverviewEntity:
    """Prepend a new entity (newest-first). Raise DuplicateEntityError on conflict.

    D-22: insertion order preserved in the YAML list (newest at top).
    D-24: atomic write; DuplicateEntityError raised without modifying disk.

    Thread-safe: the read-modify-write sequence is guarded by `_store_lock` so
    concurrent threadpool requests cannot wipe each other's adds.
    """
    with _store_lock:
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

    Thread-safe: the read-modify-write sequence is guarded by `_store_lock` so
    a concurrent add cannot resurrect a just-deleted entity (or vice versa).
    """
    with _store_lock:
        current = load_overview()
        remaining = [e for e in current if e.platform_id != platform_id]
        if len(remaining) == len(current):
            return False
        _atomic_write(remaining)
        return True
