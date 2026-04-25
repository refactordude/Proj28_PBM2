"""POSIX-atomic file write helper (D-30, CONTENT-06).

Single source of truth for atomic file writes across app_v2. Used by
overview_store (Phase 02 YAML curated list) AND content_store (Phase 03
markdown content pages). Both callers go through atomic_write_bytes —
file-mode-preservation and tempfile-cleanup behavior is centralized here.

Threat-model coverage (see 03-01-PLAN.md threat_model):
  T-03-01-01 (Tampering, tempfile)        — tempfile.mkstemp creates with 0o600
                                            in the SAME directory as target;
                                            no other process can read/write
                                            during the brief write window;
                                            chmod at the end applies target mode.
  T-03-01-02 (Information Disclosure)     — preserves existing target mode if
                                            file existed; default_mode & ~umask
                                            for new files.
  T-03-01-03 (DoS, tempfile leak)         — except clause os.unlink(tmp_name)
                                            on any exception before re-raise.
"""
from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path


def atomic_write_bytes(
    target: Path,
    payload: bytes,
    *,
    default_mode: int = 0o644,
) -> None:
    """Write ``payload`` to ``target`` atomically: tempfile in same dir → fsync → os.replace.

    - Preserves existing target file mode (chmod-applied values survive).
    - Falls back to ``default_mode & ~umask`` for newly-created files.
    - Creates parent directories with parents=True, exist_ok=True.
    - Cleans up the tempfile on any failure (IOError/OSError/etc.) before re-raising.

    D-30 (Phase 03 CONTEXT.md): atomic markdown writes for content pages.
    Phase 02 overview_store passes ``default_mode=0o666`` to match the prior
    umask-applied 0o644 result on new files.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target_mode = stat.S_IMODE(target.stat().st_mode)
    else:
        umask = os.umask(0)
        os.umask(umask)
        target_mode = default_mode & ~umask
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, target)
        os.chmod(target, target_mode)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
