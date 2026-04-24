"""Unit tests for parse_platform_id (TDD RED phase)."""
from __future__ import annotations

import pytest

from app_v2.data.platform_parser import parse_platform_id


def test_three_part_pid_returns_brand_model_soc_raw():
    assert parse_platform_id("Samsung_S22Ultra_SM8450") == ("Samsung", "S22Ultra", "SM8450")


def test_three_part_pid_pixel():
    assert parse_platform_id("Pixel8_GoogleTensor_GS301") == ("Pixel8", "GoogleTensor", "GS301")


def test_four_or_more_parts_collapse_into_soc_raw():
    assert parse_platform_id("A_B_C_D_E") == ("A", "B", "C_D_E")


def test_two_part_pid_returns_empty_soc_raw():
    assert parse_platform_id("Two_Parts") == ("Two", "Parts", "")


def test_single_part_pid_returns_empty_model_and_soc_raw():
    assert parse_platform_id("OnlyOne") == ("OnlyOne", "", "")


def test_empty_string_returns_three_empty_strings():
    assert parse_platform_id("") == ("", "", "")


def test_return_type_is_3_tuple_of_str():
    result = parse_platform_id("Samsung_S22Ultra_SM8450")
    assert isinstance(result, tuple)
    assert len(result) == 3
    assert all(isinstance(part, str) for part in result)
