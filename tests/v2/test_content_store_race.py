"""D-24 cross-process race test + single-process ThreadPool race for content_store.

The cross-process test requires fork semantics (POSIX-only). On Linux/macOS,
``multiprocessing.get_context("fork")`` inherits the test's cwd + env into both
workers. The worker function MUST be defined at module top-level (NOT nested or
lambdaed) so the fork can pickle it (Assumption A5 from RESEARCH.md).

Why this test exists (D-24 user override):

Single-process ThreadPool tests cannot detect cross-process races because the
GIL and per-process lock state serialize the writes within one Python
interpreter. Real intranet deployment runs uvicorn with multiple worker
processes — ``atomic_write_bytes`` must be correct across processes, not just
across threads. The test asserts the POSIX ``os.replace`` invariant: the final
file is one of the two written payloads in full, never a byte-level mix.

Assertions:
  1. Both processes exit cleanly (``exitcode == 0``).
  2. Target file exists with one of the two payloads in full (NOT a hybrid).
  3. No leftover tempfile in the content_dir
     (``atomic_write_bytes`` uses ``prefix=f".{target.name}."``, ``suffix=".tmp"``).
  4. File mode is 0o644 regardless of which process won.
"""
from __future__ import annotations

import multiprocessing
import stat
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest


def _save_in_worker(content_dir_str: str, pid: str, payload: str) -> None:
    """Worker target for cross-process save race.

    MUST be module-top-level for fork picklability (RESEARCH.md A5). Nested or
    lambdaed functions are not picklable for ``multiprocessing.Process``.
    """
    from app_v2.services.content_store import save_content

    save_content(pid, payload, content_dir=Path(content_dir_str))


@pytest.mark.slow
@pytest.mark.skipif(sys.platform == "win32", reason="multiprocessing fork is POSIX-only (D-24)")
def test_cross_process_save_race(tmp_path):
    """D-24: two fork()-spawned workers save different payloads to the same target.

    POSIX ``os.replace`` atomicity: the final file is one of two payloads in
    full; no hybrid; no leftover tempfile; mode is 0o644 regardless of which
    process won.
    """
    content_dir = tmp_path / "content" / "platforms"
    content_dir.mkdir(parents=True)
    pid = "Test_Race_Platform"
    payload_a = "A" * 3000
    payload_b = "B" * 3000

    ctx = multiprocessing.get_context("fork")
    p1 = ctx.Process(
        target=_save_in_worker, args=(str(content_dir), pid, payload_a)
    )
    p2 = ctx.Process(
        target=_save_in_worker, args=(str(content_dir), pid, payload_b)
    )
    p1.start()
    p2.start()
    p1.join(timeout=10)
    p2.join(timeout=10)

    assert p1.exitcode == 0, f"worker 1 exited with {p1.exitcode}"
    assert p2.exitcode == 0, f"worker 2 exited with {p2.exitcode}"

    # Assertion 1: target file exists with one of the two payloads (never hybrid).
    target = content_dir / f"{pid}.md"
    assert target.is_file(), f"target file missing: {target}"
    final = target.read_text(encoding="utf-8")
    assert final in (payload_a, payload_b), (
        f"hybrid content detected (first 60 chars): {final[:60]!r}"
    )

    # Assertion 2: no leftover tempfile in content_dir.
    # atomic_write_bytes uses prefix=f".{target.name}.", suffix=".tmp".
    leftovers = [
        p
        for p in content_dir.iterdir()
        if p.name.startswith(f".{pid}.md.") and p.name.endswith(".tmp")
    ]
    assert leftovers == [], f"tempfiles leaked: {[str(p) for p in leftovers]}"

    # Assertion 3: file mode is 0o644 (umask-aware default for new files).
    actual_mode = stat.S_IMODE(target.stat().st_mode)
    assert actual_mode == 0o644, f"expected 0o644, got 0o{actual_mode:o}"


def test_thread_pool_save_race_no_corruption(tmp_path):
    """Single-process ThreadPool race — verify no exception, no leftover tempfile.

    Within one process, the GIL serializes Python bytecode; the ``os.replace``
    syscall is atomic. The risks this catches are exception-on-cleanup and
    tempfile-leak under rare scheduling. Final content must equal one of the
    submitted payloads (no hybrid content under thread interleaving).
    """
    from app_v2.services.content_store import save_content

    content_dir = tmp_path / "content" / "platforms"
    content_dir.mkdir(parents=True)
    pid = "Thread_Race_Pid"
    payloads = [f"thread {i} payload " * 50 for i in range(8)]

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(save_content, pid, p, content_dir) for p in payloads]
        for f in futures:
            f.result()  # re-raises if a thread raised

    target = content_dir / f"{pid}.md"
    assert target.is_file()
    final = target.read_text(encoding="utf-8")
    assert final in payloads, "thread race produced hybrid content"

    # No tempfile leftover.
    leftovers = [
        p
        for p in content_dir.iterdir()
        if p.name.startswith(f".{pid}.md.") and p.name.endswith(".tmp")
    ]
    assert leftovers == [], f"tempfiles leaked: {[str(p) for p in leftovers]}"
