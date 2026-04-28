"""Unit tests for content_store.read_frontmatter (Phase 05, D-OV-02).

Covers:
- Valid frontmatter with 12 PM keys
- Defensive return-{} paths: no leading fence, missing closing fence,
  malformed YAML, file missing, path traversal, non-dict YAML, empty fences
- Unicode 한글 round-trip
- Memoize cache hit + miss-after-mtime-change
- Type coercion (date / int / bool / None)
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app_v2.services import content_store


def _write(tmp_path: Path, pid: str, body: str) -> Path:
    target = tmp_path / f"{pid}.md"
    target.write_text(body, encoding="utf-8")
    return target


@pytest.fixture(autouse=True)
def _clear_cache():
    """Each test starts with an empty memoize cache."""
    content_store._FRONTMATTER_CACHE.clear()
    yield
    content_store._FRONTMATTER_CACHE.clear()


# Test 1
def test_read_frontmatter_returns_dict_for_valid_yaml(tmp_path):
    body = (
        "---\n"
        "title: My Platform Project\n"
        "status: in-progress\n"
        "customer: Acme Corp\n"
        "model_name: Foo Pro\n"
        "ap_company: Samsung\n"
        "ap_model: Exynos 1380\n"
        "device: Phone\n"
        "controller: ABC\n"
        "application: Camera\n"
        "assignee: 홍길동\n"
        "start: 2026-04-01\n"
        "end: 2026-12-31\n"
        "---\n"
        "\n"
        "# Body markdown here\n"
    )
    _write(tmp_path, "P1", body)
    result = content_store.read_frontmatter("P1", tmp_path)
    for key in [
        "title",
        "status",
        "customer",
        "model_name",
        "ap_company",
        "ap_model",
        "device",
        "controller",
        "application",
        "assignee",
        "start",
        "end",
    ]:
        assert key in result
        assert isinstance(result[key], str)
    assert result["assignee"] == "홍길동"
    assert result["start"] == "2026-04-01"
    # Body must NOT leak into result
    assert "Body markdown here" not in str(result.values())


# Test 2
def test_read_frontmatter_no_leading_fence_returns_empty(tmp_path):
    _write(tmp_path, "P1", "# Just a heading\n\nNo frontmatter.\n")
    assert content_store.read_frontmatter("P1", tmp_path) == {}


# Test 3
def test_read_frontmatter_missing_closing_fence_returns_empty(tmp_path):
    _write(tmp_path, "P1", "---\ntitle: Foo\nstatus: open\n")
    assert content_store.read_frontmatter("P1", tmp_path) == {}


# Test 4
def test_read_frontmatter_malformed_yaml_returns_empty(tmp_path):
    _write(
        tmp_path,
        "P1",
        "---\ntitle: [unclosed bracket\nstatus: open\n---\n\nbody\n",
    )
    assert content_store.read_frontmatter("P1", tmp_path) == {}


# Test 5
def test_read_frontmatter_empty_fences_returns_empty(tmp_path):
    _write(tmp_path, "P1", "---\n---\n\n# body\n")
    assert content_store.read_frontmatter("P1", tmp_path) == {}


# Test 6
def test_read_frontmatter_missing_file_returns_empty(tmp_path):
    # Do NOT write the file
    assert content_store.read_frontmatter("Nonexistent_PID", tmp_path) == {}


# Test 7
def test_read_frontmatter_traversal_returns_empty(tmp_path):
    # _safe_target should raise ValueError, which read_frontmatter catches
    result = content_store.read_frontmatter("../../etc/passwd", tmp_path)
    assert result == {}


# Test 8
def test_read_frontmatter_unicode_korean_roundtrip(tmp_path):
    body = "---\nassignee: 홍길동\nstatus: 진행중\n---\n\n# body\n"
    _write(tmp_path, "P1", body)
    result = content_store.read_frontmatter("P1", tmp_path)
    assert result["assignee"] == "홍길동"
    assert result["status"] == "진행중"


# Test 9
def test_read_frontmatter_caches_on_first_call(tmp_path):
    body = "---\ntitle: Foo\n---\n\nbody\n"
    _write(tmp_path, "P1", body)
    result1 = content_store.read_frontmatter("P1", tmp_path)
    # Cache key (pid, mtime_ns) must be present after first call
    assert any(k[0] == "P1" for k in content_store._FRONTMATTER_CACHE)
    result2 = content_store.read_frontmatter("P1", tmp_path)
    assert result1 == result2


def test_read_frontmatter_does_not_reread_on_cache_hit(tmp_path, monkeypatch):
    body = "---\ntitle: Foo\n---\n\nbody\n"
    _write(tmp_path, "P1", body)
    # Prime cache
    _ = content_store.read_frontmatter("P1", tmp_path)
    # Now patch read_content — if cache hits, we never call it
    called = {"count": 0}
    original = content_store.read_content

    def _counting(*args, **kwargs):
        called["count"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(content_store, "read_content", _counting)
    _ = content_store.read_frontmatter("P1", tmp_path)
    assert called["count"] == 0, "Cache hit should NOT re-invoke read_content"


# Test 10
def test_read_frontmatter_invalidates_on_mtime_change(tmp_path):
    target = _write(tmp_path, "P1", "---\ntitle: Old\n---\n\nbody\n")
    result1 = content_store.read_frontmatter("P1", tmp_path)
    assert result1["title"] == "Old"
    # Re-write with explicit mtime bump (deterministic across filesystems)
    target.write_text("---\ntitle: New\n---\n\nbody\n", encoding="utf-8")
    old_stat = target.stat()
    new_mtime_ns = old_stat.st_mtime_ns + 1_000_000_000  # +1 second
    os.utime(target, ns=(old_stat.st_atime_ns, new_mtime_ns))
    result2 = content_store.read_frontmatter("P1", tmp_path)
    assert result2["title"] == "New", (
        f"Cache should miss after mtime change; got result1={result1}, result2={result2}"
    )


# Test 11
def test_read_frontmatter_coerces_date_to_str(tmp_path):
    # YAML auto-parses ISO dates to datetime.date — we must coerce to str
    _write(tmp_path, "P1", "---\nstart: 2026-04-01\n---\n\nbody\n")
    result = content_store.read_frontmatter("P1", tmp_path)
    assert result["start"] == "2026-04-01"
    assert isinstance(result["start"], str)


# Test 12
def test_read_frontmatter_coerces_int_bool_drops_null(tmp_path):
    _write(
        tmp_path,
        "P1",
        "---\nyear: 2026\nactive: true\nflag: null\n---\n\nbody\n",
    )
    result = content_store.read_frontmatter("P1", tmp_path)
    assert result["year"] == "2026"
    assert result["active"] == "True"
    assert "flag" not in result, "None values must be DROPPED, not stringified to 'None'"


# Test 13
def test_read_frontmatter_rejects_non_dict_yaml(tmp_path):
    _write(tmp_path, "P1", "---\n- item1\n- item2\n---\n\nbody\n")
    assert content_store.read_frontmatter("P1", tmp_path) == {}


# Test 14 (structural)
def test_frontmatter_cache_key_is_pid_mtime_tuple(tmp_path):
    _write(tmp_path, "P1", "---\ntitle: Foo\n---\n\nbody\n")
    _ = content_store.read_frontmatter("P1", tmp_path)
    for key in content_store._FRONTMATTER_CACHE:
        assert isinstance(key, tuple), f"Cache key must be tuple, got {type(key)}"
        assert len(key) == 2, f"Cache key must be 2-tuple (pid, mtime_ns), got {key}"
        assert isinstance(key[0], str)
        assert isinstance(key[1], int)
