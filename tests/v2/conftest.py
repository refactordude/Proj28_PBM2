"""Shared pytest configuration for tests/v2/.

Registers custom markers used by the Phase 03 test suite so pytest does not
emit ``PytestUnknownMarkWarning`` (and so future ``-m 'not slow'`` selection
works in CI).

Markers:
- ``slow``: multiprocessing / fork / IO-heavy tests. Plan 03-04 D-24 cross-process
  race test is the canonical user. Skipped on Windows (no fork semantics).
"""
from __future__ import annotations


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (multiprocessing/integration); "
        "deselect with -m 'not slow'",
    )
