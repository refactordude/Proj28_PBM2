"""Unit tests for atomic_write_bytes shared helper (D-30, CONTENT-06).

Single source of truth for atomic file writes. Used by overview_store (Phase 02
YAML curated list) AND content_store (Phase 03 markdown content pages).

Coverage:
    - basic write creates file with payload + parent dirs
    - mode preservation: chmod 0o600 on existing target survives the rewrite
    - new-file mode honors default_mode AND umask
    - tempfile cleaned up on os.fsync error
    - tempfile cleaned up on os.replace error
    - large payload (100 KB) round-trips byte-for-byte
"""
from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from app_v2.data.atomic_write import atomic_write_bytes


# --------------------------------------------------------------------------- #
# basic write
# --------------------------------------------------------------------------- #

def test_atomic_write_creates_file_with_payload(tmp_path: Path) -> None:
    """Writes payload to target, creating parent directory if missing."""
    target = tmp_path / "sub" / "nested" / "file.bin"
    payload = b"hello world"

    atomic_write_bytes(target, payload)

    assert target.exists(), "target file should exist after write"
    assert target.read_bytes() == payload
    assert target.parent.is_dir(), "parent directory should be created"


# --------------------------------------------------------------------------- #
# file-mode preservation (T-03-01-02 mitigation)
# --------------------------------------------------------------------------- #

def test_atomic_write_preserves_existing_mode(tmp_path: Path) -> None:
    """Existing chmod-applied mode (0o600) survives a rewrite (does NOT silently relax to 0o644)."""
    target = tmp_path / "perm.bin"
    target.write_bytes(b"old")
    os.chmod(target, 0o600)
    assert stat.S_IMODE(target.stat().st_mode) == 0o600

    atomic_write_bytes(target, b"new", default_mode=0o644)

    assert target.read_bytes() == b"new"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600, (
        "atomic_write_bytes must preserve target's existing file mode "
        "(does not silently broaden to default_mode)"
    )


def test_atomic_write_default_mode_for_new_file(tmp_path: Path) -> None:
    """New file uses default_mode & ~umask (umask-aware)."""
    target = tmp_path / "newfile.bin"
    assert not target.exists()

    # Pin umask to 0o022 for determinism (typical Linux default).
    old_umask = os.umask(0o022)
    try:
        atomic_write_bytes(target, b"x", default_mode=0o666)
    finally:
        os.umask(old_umask)

    expected_mode = 0o666 & ~0o022  # 0o644
    assert stat.S_IMODE(target.stat().st_mode) == expected_mode, (
        f"new file should be created with default_mode & ~umask = {oct(expected_mode)}; "
        f"got {oct(stat.S_IMODE(target.stat().st_mode))}"
    )


# --------------------------------------------------------------------------- #
# tempfile cleanup on errors (T-03-01-03 mitigation)
# --------------------------------------------------------------------------- #

def test_atomic_write_cleans_tempfile_on_write_error(tmp_path: Path) -> None:
    """os.fsync raises -> atomic_write_bytes raises -> no .tmp file remains in target.parent."""
    target = tmp_path / "victim.bin"

    # Snapshot of files in tmp_path BEFORE the call, so we can detect leakage.
    before = set(p.name for p in tmp_path.iterdir())

    with patch("app_v2.data.atomic_write.os.fsync", side_effect=IOError("simulated fsync fail")):
        with pytest.raises(IOError, match="simulated fsync fail"):
            atomic_write_bytes(target, b"data")

    after = set(p.name for p in tmp_path.iterdir())
    leaked = after - before
    assert not leaked, f"tempfile leaked after fsync failure: {leaked}"
    assert not target.exists(), "target should not exist when write fails before os.replace"


def test_atomic_write_cleans_tempfile_on_replace_error(tmp_path: Path) -> None:
    """os.replace raises -> tempfile is unlinked before re-raising."""
    target = tmp_path / "victim2.bin"

    before = set(p.name for p in tmp_path.iterdir())

    with patch("app_v2.data.atomic_write.os.replace", side_effect=OSError("simulated replace fail")):
        with pytest.raises(OSError, match="simulated replace fail"):
            atomic_write_bytes(target, b"data")

    after = set(p.name for p in tmp_path.iterdir())
    leaked = after - before
    assert not leaked, f"tempfile leaked after os.replace failure: {leaked}"


# --------------------------------------------------------------------------- #
# large payload round-trip
# --------------------------------------------------------------------------- #

def test_atomic_write_large_payload(tmp_path: Path) -> None:
    """100 KB binary payload round-trips byte-for-byte."""
    target = tmp_path / "big.bin"
    payload = os.urandom(100 * 1024)

    atomic_write_bytes(target, payload)

    assert target.read_bytes() == payload
    assert target.stat().st_size == len(payload)


# --------------------------------------------------------------------------- #
# overview_store regression guard (refactor invisibility)
# --------------------------------------------------------------------------- #

def test_overview_store_still_works_after_refactor(tmp_path, monkeypatch) -> None:
    """overview_store.add_overview / load_overview behave identically after the refactor."""
    from app_v2.services import overview_store
    from app_v2.services.overview_store import add_overview, load_overview

    monkeypatch.setattr(overview_store, "OVERVIEW_YAML", tmp_path / "overview.yaml")

    entity = add_overview("Samsung_S22Ultra_SM8450")
    assert entity.platform_id == "Samsung_S22Ultra_SM8450"

    loaded = load_overview()
    assert len(loaded) == 1
    assert loaded[0].platform_id == "Samsung_S22Ultra_SM8450"

    # YAML file should exist with the correct mode (umask-applied 0o644 typically).
    yaml_path = overview_store.OVERVIEW_YAML
    assert yaml_path.exists()
    mode = stat.S_IMODE(yaml_path.stat().st_mode)
    # With default umask 0o022, mode should be 0o644 (0o666 & ~0o022).
    # We don't pin umask here — we just assert it's not the tempfile-default 0o600.
    assert mode != 0o600, (
        f"After refactor, overview.yaml mode should be umask-applied (not the "
        f"tempfile default 0o600). Got {oct(mode)} — refactor regressed mode preservation."
    )
