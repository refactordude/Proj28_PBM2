"""Phase 4 — UI Foundation: HeroSpec view-model (D-UIF-11).

Pydantic v2 model passed to the `hero` macro in
`app_v2/templates/_components/hero.html`. Showcase route constructs
instances directly; downstream phases (Platform BM pivot, future
dashboards) pass computed instances from their routers.

Mirrors the JointValidationGridViewModel + PageLink convention in
`app_v2/services/joint_validation_grid_service.py` lines 106-137.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HeroSegment(BaseModel):
    """One segment of the hero's segmented bar."""

    label: str
    value: float       # percentage 0-100
    color: str         # CSS color string e.g. "#3366ff" or "var(--accent)"


class HeroSideStat(BaseModel):
    """One row of the hero's side-stats panel."""

    key: str
    value: str
    tone: Literal["default", "green", "red"] = "default"


class HeroSpec(BaseModel):
    """Full hero card spec.

    Empty `segments` list -> no segmented bar rendered.
    Empty `side_stats` list -> side panel not rendered (single-column
    layout). The macro handles both cases gracefully.
    """

    label: str
    big_number: int | float | str
    big_number_unit: str | None = None
    delta_text: str | None = None
    segments: list[HeroSegment] = Field(default_factory=list)
    side_stats: list[HeroSideStat] = Field(default_factory=list)
