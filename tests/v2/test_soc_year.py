"""Unit tests for SOC_YEAR lookup table and get_year (TDD RED phase)."""
from __future__ import annotations

import pytest

from app_v2.data.soc_year import SOC_YEAR, get_year

# Minimum required entries that must exist in SOC_YEAR
_REQUIRED_ENTRIES = {
    "SM8350": 2021,
    "SM8450": 2022,
    "SM8550": 2023,
    "SM8650": 2024,
    "SM8750": 2025,
    "MT6985": 2023,
    "MT6989": 2024,
    "Exynos2100": 2021,
    "Exynos2200": 2022,
    "Exynos2400": 2024,
    "GS301": 2022,
    "GS401": 2023,
}


def test_soc_year_contains_12_minimum_known_entries():
    for key, expected_year in _REQUIRED_ENTRIES.items():
        assert key in SOC_YEAR, f"Missing key {key!r} in SOC_YEAR"
        assert SOC_YEAR[key] == expected_year, (
            f"SOC_YEAR[{key!r}] expected {expected_year}, got {SOC_YEAR[key]}"
        )


def test_get_year_known_qualcomm_snapdragon():
    assert get_year("SM8450") == 2022
    assert get_year("SM8550") == 2023
    assert get_year("SM8650") == 2024


def test_get_year_known_exynos():
    assert get_year("Exynos2200") == 2022


def test_get_year_known_google_tensor():
    assert get_year("GS301") == 2022


def test_get_year_unknown_returns_none():
    assert get_year("UnknownChip") is None


def test_get_year_empty_string_returns_none():
    assert get_year("") is None


def test_get_year_does_not_mutate_soc_year():
    size_before = len(SOC_YEAR)
    get_year("SM8450")
    get_year("UnknownChip")
    get_year("")
    assert len(SOC_YEAR) == size_before
