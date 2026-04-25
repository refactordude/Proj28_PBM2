"""Tests for app_v2.services.overview_filter pure-function service.

This file covers Task 1 (unit tests for apply_filters / count_active_filters /
has_content_file). Task 2 will append TestClient tests for POST /overview/filter
and POST /overview/filter/reset.

Reference: 02-03-PLAN.md, D-21 (year=None exclusion semantics), Pitfall 2 (path traversal).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app_v2.services.overview_filter import (
    apply_filters,
    count_active_filters,
    has_content_file,
)


# ---------------------------------------------------------------------------
# Shared fixtures — entity-dict catalog covering brand/soc/year variations.
# ---------------------------------------------------------------------------

SAMPLE = [
    {"platform_id": "Samsung_S22Ultra_SM8450", "brand": "Samsung", "soc_raw": "SM8450", "year": 2022},
    {"platform_id": "Samsung_S23Ultra_SM8550", "brand": "Samsung", "soc_raw": "SM8550", "year": 2023},
    {"platform_id": "Pixel8_GoogleTensor_GS301", "brand": "Pixel8", "soc_raw": "GS301", "year": 2022},
    {"platform_id": "Xiaomi_Mix4_UnknownSoc", "brand": "Xiaomi", "soc_raw": "UnknownSoc", "year": None},
]


@pytest.fixture()
def content_dir(tmp_path) -> Path:
    """A real on-disk content/platforms-style directory under tmp_path."""
    d = tmp_path / "content" / "platforms"
    d.mkdir(parents=True)
    return d


# ---------------------------------------------------------------------------
# apply_filters — unit tests
# ---------------------------------------------------------------------------

def test_no_filters_returns_input_unchanged(content_dir):
    """All filter args None/empty → returns the full list unchanged."""
    out = apply_filters(SAMPLE, brand=None, soc=None, year=None, has_content=False, content_dir=content_dir)
    assert len(out) == len(SAMPLE)
    pids = [e["platform_id"] for e in out]
    assert pids == [e["platform_id"] for e in SAMPLE]


def test_brand_filter_narrows_by_brand(content_dir):
    """brand='Samsung' → only the two Samsung entities."""
    out = apply_filters(SAMPLE, brand="Samsung", soc=None, year=None, has_content=False, content_dir=content_dir)
    pids = {e["platform_id"] for e in out}
    assert pids == {"Samsung_S22Ultra_SM8450", "Samsung_S23Ultra_SM8550"}


def test_soc_filter_narrows_by_soc_raw(content_dir):
    """soc='SM8550' → only the entity with that soc_raw."""
    out = apply_filters(SAMPLE, brand=None, soc="SM8550", year=None, has_content=False, content_dir=content_dir)
    pids = {e["platform_id"] for e in out}
    assert pids == {"Samsung_S23Ultra_SM8550"}


def test_year_filter_as_int_narrows_by_year(content_dir):
    """year=2022 (int) → entities with year==2022 (excludes year=None and year=2023)."""
    out = apply_filters(SAMPLE, brand=None, soc=None, year=2022, has_content=False, content_dir=content_dir)
    pids = {e["platform_id"] for e in out}
    assert pids == {"Samsung_S22Ultra_SM8450", "Pixel8_GoogleTensor_GS301"}


def test_year_filter_as_string_narrows_by_year(content_dir):
    """year='2022' (str — as it comes from HTML form) → same as int."""
    out = apply_filters(SAMPLE, brand=None, soc=None, year="2022", has_content=False, content_dir=content_dir)
    pids = {e["platform_id"] for e in out}
    assert pids == {"Samsung_S22Ultra_SM8450", "Pixel8_GoogleTensor_GS301"}


def test_year_filter_excludes_year_none_entities(content_dir):
    """D-21: entity with year=None is EXCLUDED when a specific year is selected."""
    out = apply_filters(SAMPLE, brand=None, soc=None, year=2022, has_content=False, content_dir=content_dir)
    pids = {e["platform_id"] for e in out}
    assert "Xiaomi_Mix4_UnknownSoc" not in pids, "year=None entity must be excluded when year filter active"


def test_year_empty_string_keeps_all_entities_including_none(content_dir):
    """D-21: entity with year=None is INCLUDED when year filter is empty."""
    out = apply_filters(SAMPLE, brand=None, soc=None, year="", has_content=False, content_dir=content_dir)
    pids = {e["platform_id"] for e in out}
    assert "Xiaomi_Mix4_UnknownSoc" in pids, "year=None entity must be included when year filter is empty"
    assert len(out) == len(SAMPLE)


def test_multi_filter_and_semantics(content_dir):
    """brand=Samsung AND year=2023 → exactly the one Samsung 2023 entity."""
    out = apply_filters(SAMPLE, brand="Samsung", soc=None, year=2023, has_content=False, content_dir=content_dir)
    pids = {e["platform_id"] for e in out}
    assert pids == {"Samsung_S23Ultra_SM8550"}


def test_unknown_brand_returns_empty(content_dir):
    """An unknown filter value returns [] without crashing."""
    out = apply_filters(SAMPLE, brand="DoesNotExist", soc=None, year=None, has_content=False, content_dir=content_dir)
    assert out == []


def test_has_content_true_includes_only_entities_with_content_file(content_dir):
    """has_content=True filters by Path(content_dir / f'{pid}.md').exists()."""
    # Create .md only for Samsung_S22Ultra_SM8450 and Pixel8.
    (content_dir / "Samsung_S22Ultra_SM8450.md").write_text("hello", encoding="utf-8")
    (content_dir / "Pixel8_GoogleTensor_GS301.md").write_text("hello", encoding="utf-8")

    out = apply_filters(SAMPLE, brand=None, soc=None, year=None, has_content=True, content_dir=content_dir)
    pids = {e["platform_id"] for e in out}
    assert pids == {"Samsung_S22Ultra_SM8450", "Pixel8_GoogleTensor_GS301"}


def test_has_content_false_applies_no_filter(content_dir):
    """has_content=False means no filtering on that dimension."""
    out = apply_filters(SAMPLE, brand=None, soc=None, year=None, has_content=False, content_dir=content_dir)
    assert len(out) == len(SAMPLE)


# ---------------------------------------------------------------------------
# count_active_filters — unit tests
# ---------------------------------------------------------------------------

def test_count_zero_when_all_falsy():
    assert count_active_filters(None, None, None, None) == 0
    assert count_active_filters("", "", "", False) == 0


def test_count_one_per_active_dimension():
    assert count_active_filters("Samsung", None, None, None) == 1
    assert count_active_filters(None, "SM8550", None, None) == 1
    assert count_active_filters(None, None, "2023", None) == 1
    assert count_active_filters(None, None, None, True) == 1


def test_count_four_when_all_set():
    assert count_active_filters("Samsung", "SM8550", "2023", True) == 4


def test_count_treats_empty_string_as_inactive():
    """brand='' should be treated as no-filter, not as a value."""
    assert count_active_filters("", "SM8550", "", False) == 1


# ---------------------------------------------------------------------------
# has_content_file — unit tests (Pitfall 2 path traversal defense)
# ---------------------------------------------------------------------------

def test_has_content_true_when_md_exists(content_dir):
    """File exists → returns True."""
    (content_dir / "Samsung_S22Ultra_SM8450.md").write_text("x", encoding="utf-8")
    assert has_content_file("Samsung_S22Ultra_SM8450", content_dir) is True


def test_has_content_false_when_md_missing(content_dir):
    """File does not exist → returns False, no exception."""
    assert has_content_file("Pixel8_GoogleTensor_GS301", content_dir) is False


def test_has_content_false_when_platform_id_escapes_dir(content_dir, tmp_path):
    """Pitfall 2: a platform_id like '../../etc/passwd' must not escape content_dir.

    Even creating a file outside content_dir to lure the function, the resolve()
    + relative_to() check rejects it.
    """
    # Create a tempting file outside content_dir
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")

    # platform_id with traversal should NOT find that file
    assert has_content_file("../outside", content_dir) is False
    assert has_content_file("../../etc/passwd", content_dir) is False


def test_has_content_never_raises_on_weird_inputs(content_dir):
    """Empty string, spaces, and odd inputs all return False (never raise)."""
    assert has_content_file("", content_dir) is False
    assert has_content_file("   ", content_dir) is False
    assert has_content_file("\x00null", content_dir) is False
