"""Phase 4 (UI Foundation) Pydantic view-model unit tests.

Covers D-UIF-11: HeroSpec / HeroSegment / HeroSideStat field validation,
defaults, Literal constraint enforcement.

Also covers D-UIF-04 view-models: FilterGroup / FilterOption.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app_v2.services.filter_spec import FilterGroup, FilterOption
from app_v2.services.hero_spec import HeroSegment, HeroSideStat, HeroSpec


# ----- HeroSpec -----

def test_hero_spec_minimal_valid():
    """HeroSpec with only required fields validates; optional defaults applied."""
    spec = HeroSpec(label="Test", big_number=42)
    assert spec.label == "Test"
    assert spec.big_number == 42
    assert spec.big_number_unit is None
    assert spec.delta_text is None
    assert spec.segments == []
    assert spec.side_stats == []


def test_hero_spec_full_valid():
    """HeroSpec with every field populated."""
    spec = HeroSpec(
        label="Full",
        big_number=128,
        big_number_unit="open",
        delta_text="+12 this week",
        segments=[HeroSegment(label="A", value=44.0, color="#3366ff")],
        side_stats=[HeroSideStat(key="x", value="y", tone="red")],
    )
    assert spec.big_number_unit == "open"
    assert spec.delta_text == "+12 this week"
    assert len(spec.segments) == 1
    assert spec.segments[0].label == "A"
    assert spec.segments[0].value == 44.0
    assert spec.side_stats[0].tone == "red"


def test_hero_spec_big_number_accepts_str():
    """big_number is `int | float | str` — strings allowed for things like '4d 2h'."""
    spec = HeroSpec(label="x", big_number="4d 2h")
    assert spec.big_number == "4d 2h"


def test_hero_spec_default_factory_unique_lists():
    """Field(default_factory=list) — each instance gets its own list."""
    spec1 = HeroSpec(label="A", big_number=1)
    spec2 = HeroSpec(label="B", big_number=2)
    spec1.segments.append(HeroSegment(label="x", value=1.0, color="#000"))
    # spec2 must NOT see spec1's append
    assert spec2.segments == []


def test_hero_spec_missing_required_raises():
    """label and big_number are required."""
    with pytest.raises(ValidationError):
        HeroSpec(big_number=42)
    with pytest.raises(ValidationError):
        HeroSpec(label="x")


# ----- HeroSideStat tone Literal -----

def test_hero_side_stat_tone_default():
    s = HeroSideStat(key="k", value="v")
    assert s.tone == "default"


def test_hero_side_stat_tone_valid_values():
    for tone in ("default", "green", "red"):
        s = HeroSideStat(key="k", value="v", tone=tone)
        assert s.tone == tone


def test_hero_side_stat_tone_invalid_raises():
    with pytest.raises(ValidationError):
        HeroSideStat(key="k", value="v", tone="blue")
    with pytest.raises(ValidationError):
        HeroSideStat(key="k", value="v", tone="amber")


# ----- HeroSegment -----

def test_hero_segment_required_fields():
    seg = HeroSegment(label="X", value=10.0, color="var(--accent)")
    assert seg.label == "X"
    assert seg.value == 10.0
    assert seg.color == "var(--accent)"


def test_hero_segment_value_coerced_to_float():
    """int -> float coercion for value field."""
    seg = HeroSegment(label="X", value=10, color="#000")
    assert seg.value == 10.0
    assert isinstance(seg.value, float)


# ----- FilterOption -----

def test_filter_option_default_off():
    opt = FilterOption(label="X", value="x")
    assert opt.on is False


def test_filter_option_on_explicit():
    opt = FilterOption(label="X", value="x", on=True)
    assert opt.on is True


# ----- FilterGroup -----

def test_filter_group_default_empty_options():
    grp = FilterGroup(label="Type")
    assert grp.options == []


def test_filter_group_with_options():
    grp = FilterGroup(label="Status", options=[
        FilterOption(label="Open", value="open", on=True),
        FilterOption(label="Closed", value="closed"),
    ])
    assert len(grp.options) == 2
    assert grp.options[0].on is True
    assert grp.options[1].on is False


def test_filter_group_default_factory_unique_options():
    """Each FilterGroup gets its own options list."""
    g1 = FilterGroup(label="A")
    g2 = FilterGroup(label="B")
    g1.options.append(FilterOption(label="x", value="x"))
    assert g2.options == []
