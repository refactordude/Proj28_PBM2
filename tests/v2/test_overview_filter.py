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


# ===========================================================================
# Task 2: TestClient tests for POST /overview/filter and POST /overview/filter/reset
# ===========================================================================

from fastapi.testclient import TestClient

from app_v2.main import app
import app_v2.services.overview_store as overview_store_mod


# Fake catalog matching the four entities used in the filter route tests.
# All IDs use 3-part brand_model_soc so parse_platform_id correctly extracts soc_raw.
_FILTER_CATALOG = [
    "Samsung_S22Ultra_SM8450",
    "Samsung_S23Ultra_SM8550",
    "Pixel8_GoogleTensor_GS301",
    "Xiaomi_Mix4_UnknownSoc",
]


@pytest.fixture()
def isolated_filter(tmp_path, monkeypatch):
    """Isolation fixture for filter route tests.

    Mirrors test_overview_routes.isolated_overview but additionally:
    - monkeypatches CONTENT_DIR in app_v2.routers.overview to tmp_path/content/platforms
    - pre-seeds overview.yaml with the four FILTER_CATALOG entities so load_overview
      returns a stable fixture across all filter route tests.
    """
    # 1. Point overview_store at a temp YAML.
    yaml_path = tmp_path / "overview.yaml"
    monkeypatch.setattr(overview_store_mod, "OVERVIEW_YAML", yaml_path)

    # 2. Patch list_platforms in routers.overview.
    import app_v2.routers.overview as overview_mod

    monkeypatch.setattr(
        overview_mod, "list_platforms", lambda db, db_name="": list(_FILTER_CATALOG)
    )

    # 3. Patch CONTENT_DIR to a tmp directory.
    fake_content_dir = tmp_path / "content" / "platforms"
    fake_content_dir.mkdir(parents=True)
    monkeypatch.setattr(overview_mod, "CONTENT_DIR", fake_content_dir)

    # 4. Clear caches between test runs.
    from app_v2.services.cache import clear_all_caches

    clear_all_caches()

    # 5. Pre-seed overview.yaml with all four entities (via the public API).
    with TestClient(app) as client:
        for pid in _FILTER_CATALOG:
            r = client.post("/overview/add", data={"platform_id": pid})
            assert r.status_code == 200, f"seed add failed for {pid}: {r.status_code}"
        yield client, fake_content_dir


# ---------------------------------------------------------------------------
# POST /overview/filter — happy paths
# ---------------------------------------------------------------------------

def test_post_filter_no_active_filters_returns_all_entities(isolated_filter):
    """Empty form (all filters inactive) → full list + OOB badge with d-none."""
    client, _ = isolated_filter
    r = client.post("/overview/filter", data={})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    body = r.text
    for pid in _FILTER_CATALOG:
        assert pid in body, f"Expected {pid} in unfiltered list"
    # OOB badge must be present
    assert 'id="filter-count-badge"' in body
    assert 'hx-swap-oob="true"' in body
    # When count is 0 the badge gets d-none
    assert "d-none" in body


def test_post_filter_brand_samsung_narrows_to_samsung_entities(isolated_filter):
    client, _ = isolated_filter
    r = client.post("/overview/filter", data={"brand": "Samsung"})
    assert r.status_code == 200
    body = r.text
    assert "Samsung_S22Ultra_SM8450" in body
    assert "Samsung_S23Ultra_SM8550" in body
    assert "Pixel8_GoogleTensor_GS301" not in body
    assert "Xiaomi_Mix4_UnknownSoc" not in body


def test_post_filter_soc_narrows_by_soc_raw(isolated_filter):
    client, _ = isolated_filter
    r = client.post("/overview/filter", data={"soc": "SM8550"})
    assert r.status_code == 200
    body = r.text
    assert "Samsung_S23Ultra_SM8550" in body
    assert "Samsung_S22Ultra_SM8450" not in body
    assert "Pixel8_GoogleTensor_GS301" not in body


def test_post_filter_year_2022_excludes_year_none_entity(isolated_filter):
    """D-21: year=2022 returns 2022 entities; entity with year=None is NOT in body."""
    client, _ = isolated_filter
    r = client.post("/overview/filter", data={"year": "2022"})
    assert r.status_code == 200
    body = r.text
    assert "Samsung_S22Ultra_SM8450" in body  # year=2022
    assert "Pixel8_GoogleTensor_GS301" in body  # year=2022 via GS301
    assert "Samsung_S23Ultra_SM8550" not in body  # year=2023
    assert "Xiaomi_Mix4_UnknownSoc" not in body  # year=None — D-21


def test_post_filter_empty_year_includes_year_none_entity(isolated_filter):
    """D-21: no year filter → entity with year=None IS in body."""
    client, _ = isolated_filter
    r = client.post("/overview/filter", data={"year": ""})
    assert r.status_code == 200
    body = r.text
    assert "Xiaomi_Mix4_UnknownSoc" in body, "year=None entity must be present when year filter empty"


def test_post_filter_multiple_filters_apply_and_semantics(isolated_filter):
    """brand=Samsung + year=2023 → exactly one entity."""
    client, _ = isolated_filter
    r = client.post("/overview/filter", data={"brand": "Samsung", "year": "2023"})
    assert r.status_code == 200
    body = r.text
    assert "Samsung_S23Ultra_SM8550" in body
    assert "Samsung_S22Ultra_SM8450" not in body
    assert "Pixel8_GoogleTensor_GS301" not in body


def test_post_filter_zero_matches_returns_no_platforms_match_copy(isolated_filter):
    """A filter combination matching nothing returns the verbatim copy."""
    client, _ = isolated_filter
    r = client.post("/overview/filter", data={"brand": "Samsung", "year": "2099"})
    assert r.status_code == 200
    body = r.text
    assert "No platforms match the current filters." in body


def test_post_filter_response_is_fragment_not_full_page(isolated_filter):
    """block_name='entity_list' fragment should NOT include the navbar shell."""
    client, _ = isolated_filter
    r = client.post("/overview/filter", data={"brand": "Samsung"})
    assert r.status_code == 200
    body = r.text
    assert '<nav class="navbar' not in body
    assert "<html" not in body.lower()


def test_post_filter_response_contains_oob_badge_with_active_count(isolated_filter):
    """Body must contain the OOB span with id and hx-swap-oob attribute, and the count.

    The badge is rendered twice (once outside the block via the <details> shell,
    once inside the block as the OOB swap). For a fragment response we only get
    the OOB copy. The count value 1 (single brand filter) appears in the rendered span.
    """
    client, _ = isolated_filter
    r = client.post("/overview/filter", data={"brand": "Samsung"})
    body = r.text
    assert 'id="filter-count-badge"' in body
    assert 'hx-swap-oob="true"' in body
    # Active count is 1 (just the brand filter)
    # The OOB badge content must be 1 (not d-none)
    assert "d-none" not in body or body.count("d-none") < body.count("filter-count-badge")
    # Stronger check: the rendered text "1" must appear inside a filter-count-badge span.
    import re as _re
    m = _re.search(
        r'<span\s+id="filter-count-badge"[^>]*>\s*(\d+)\s*</span>',
        body,
    )
    assert m is not None, f"OOB badge span not found in body. Body excerpt: {body[:500]}"
    assert m.group(1) == "1"


def test_post_filter_has_content_true_narrows_to_entities_with_md_file(isolated_filter):
    """has_content=1 → only entities whose <pid>.md exists in CONTENT_DIR."""
    client, content_dir = isolated_filter
    # Create .md only for two of the four
    (content_dir / "Samsung_S22Ultra_SM8450.md").write_text("hello", encoding="utf-8")
    (content_dir / "Pixel8_GoogleTensor_GS301.md").write_text("hello", encoding="utf-8")

    r = client.post("/overview/filter", data={"has_content": "1"})
    assert r.status_code == 200
    body = r.text
    assert "Samsung_S22Ultra_SM8450" in body
    assert "Pixel8_GoogleTensor_GS301" in body
    assert "Samsung_S23Ultra_SM8550" not in body
    assert "Xiaomi_Mix4_UnknownSoc" not in body


def test_post_filter_has_content_defense_against_traversal_in_pid_storage(isolated_filter, tmp_path):
    """Even if a pid in the curated list pretended to traverse, has_content_file rejects it.

    This is a unit-level sanity check: the route already regex-validates at add time,
    but if someone hand-edited overview.yaml the filter must remain safe.
    """
    client, content_dir = isolated_filter
    # Place a tempting .md file outside content_dir
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    # Direct call to has_content_file with a traversal pid — must return False.
    assert has_content_file("../outside", content_dir) is False


def test_post_filter_reset_returns_full_list_with_count_zero_badge(isolated_filter):
    """POST /overview/filter/reset returns the full unfiltered list + count=0 OOB badge."""
    client, _ = isolated_filter
    r = client.post("/overview/filter/reset")
    assert r.status_code == 200
    body = r.text
    for pid in _FILTER_CATALOG:
        assert pid in body, f"Expected {pid} in reset full list"
    assert 'id="filter-count-badge"' in body
    assert 'hx-swap-oob="true"' in body
    assert "d-none" in body  # count=0 → badge has d-none class
    # Reset response is a fragment, not a full page.
    assert '<nav class="navbar' not in body


def test_post_filter_regression_add_and_delete_still_work(isolated_filter):
    """Adding/deleting in combination with filtering still works (sanity)."""
    client, _ = isolated_filter
    # All four already pre-seeded. Delete Pixel8 then verify filter result.
    r = client.delete("/overview/Pixel8_GoogleTensor_GS301")
    assert r.status_code == 200
    r = client.post("/overview/filter", data={"year": "2022"})
    body = r.text
    assert "Samsung_S22Ultra_SM8450" in body  # still here, year 2022
    assert "Pixel8_GoogleTensor_GS301" not in body  # deleted
