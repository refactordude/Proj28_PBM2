"""Tests for app_v2/services/joint_validation_store.py — D-JV-02, D-JV-03, D-JV-08, D-JV-09."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from app_v2.services.joint_validation_store import (
    PAGE_ID_PATTERN,
    clear_parse_cache,
    discover_joint_validations,
    get_parsed_jv,
)


SAMPLE_HTML = b"""<!DOCTYPE html><html><body>
<h1>Test JV</h1>
<table><tr><th><strong>Status</strong></th><td>OK</td></tr></table>
</body></html>"""


@pytest.fixture(autouse=True)
def _reset_cache():
    clear_parse_cache()
    yield
    clear_parse_cache()


def _make_jv(root: Path, page_id: str, html: bytes = SAMPLE_HTML) -> Path:
    folder = root / page_id
    folder.mkdir(parents=True, exist_ok=True)
    index = folder / "index.html"
    index.write_bytes(html)
    return index


def test_discover_yields_only_numeric_folders_with_index_html(tmp_path: Path) -> None:
    _make_jv(tmp_path, "3193868109")
    _make_jv(tmp_path, "4242")
    # Non-numeric folder with index.html — must be skipped (D-JV-03)
    drafts = tmp_path / "_drafts"
    drafts.mkdir()
    (drafts / "index.html").write_bytes(SAMPLE_HTML)
    # README.md at root — must be skipped
    (tmp_path / "README.md").write_bytes(b"hello")
    # Numeric folder without index.html — must be skipped
    (tmp_path / "999").mkdir()
    (tmp_path / "999" / "notindex.html").write_bytes(SAMPLE_HTML)
    found = sorted(pid for pid, _ in discover_joint_validations(tmp_path))
    assert found == ["3193868109", "4242"]


def test_discover_skips_index_that_is_a_directory(tmp_path: Path) -> None:
    folder = tmp_path / "999"
    folder.mkdir()
    # Make index.html a DIRECTORY, not a file — must be skipped
    (folder / "index.html").mkdir()
    found = list(discover_joint_validations(tmp_path))
    assert found == []


def test_discover_returns_empty_when_root_missing(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"
    assert list(discover_joint_validations(missing)) == []


def test_discover_returns_empty_when_root_empty(tmp_path: Path) -> None:
    assert list(discover_joint_validations(tmp_path)) == []


def test_get_parsed_jv_caches_by_mtime(tmp_path: Path) -> None:
    index = _make_jv(tmp_path, "3193868109")
    parsed1 = get_parsed_jv("3193868109", index)
    parsed2 = get_parsed_jv("3193868109", index)
    # Same mtime → same object (cached)
    assert parsed1 is parsed2
    # Touch to bump mtime by at least 1 ns
    time.sleep(0.01)
    index.write_bytes(SAMPLE_HTML + b"<!-- changed -->")
    parsed3 = get_parsed_jv("3193868109", index)
    assert parsed3 is not parsed1


def test_get_parsed_jv_handles_concurrent_pages(tmp_path: Path) -> None:
    idx_a = _make_jv(tmp_path, "111")
    idx_b = _make_jv(tmp_path, "222")
    parsed_a = get_parsed_jv("111", idx_a)
    parsed_b = get_parsed_jv("222", idx_b)
    # Update only A's mtime
    time.sleep(0.01)
    idx_a.write_bytes(SAMPLE_HTML + b"<!-- a changed -->")
    parsed_a2 = get_parsed_jv("111", idx_a)
    parsed_b2 = get_parsed_jv("222", idx_b)
    assert parsed_a2 is not parsed_a
    assert parsed_b2 is parsed_b   # B unchanged → still cached


def test_clear_parse_cache_empties_dict(tmp_path: Path) -> None:
    index = _make_jv(tmp_path, "3193868109")
    parsed1 = get_parsed_jv("3193868109", index)
    clear_parse_cache()
    parsed2 = get_parsed_jv("3193868109", index)
    assert parsed1 is not parsed2


def test_page_id_pattern_rejects_non_digits() -> None:
    assert PAGE_ID_PATTERN.match("123") is not None
    assert PAGE_ID_PATTERN.match("3193868109") is not None
    assert PAGE_ID_PATTERN.match("..") is None
    assert PAGE_ID_PATTERN.match("../etc") is None
    assert PAGE_ID_PATTERN.match("12_3") is None
    assert PAGE_ID_PATTERN.match("abc123") is None
    assert PAGE_ID_PATTERN.match("") is None
