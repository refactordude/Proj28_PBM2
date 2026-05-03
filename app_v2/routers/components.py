"""Phase 4 — UI Foundation: GET /_components showcase route (D-UIF-02).

Renders every Phase 4 primitive with realistic sample data. Always-on
(NOT dev-gated). Acts as the live design reference for downstream phases
(Platform BM pivot, JV chip-group filter retrofit, Ask AI sidebar) and
as the locus for invariant tests.

Sample data is hard-coded inline per UI-SPEC §showcase.html line 322 —
no fixture file indirection.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app_v2.services.filter_spec import FilterGroup, FilterOption
from app_v2.services.hero_spec import HeroSegment, HeroSideStat, HeroSpec
from app_v2.templates import templates

router = APIRouter()


@router.get("/_components", response_class=HTMLResponse)
def components_showcase(request: Request) -> HTMLResponse:
    """Render the components showcase page.

    active_tab="showcase" — no PBM2 tab matches; topbar renders all
    three tabs (Joint Validation / Browse / Ask) in their default
    unselected state. UI-SPEC §Showcase Route §Active tab.
    """
    # Hero — full variant (every arg populated)
    hero_full = HeroSpec(
        label="Active validations",
        big_number=128,
        big_number_unit="open",
        delta_text="+12 this week",
        segments=[
            HeroSegment(label="Pending", value=44.0, color="var(--accent)"),
            HeroSegment(label="In progress", value=36.0, color="var(--green)"),
            HeroSegment(label="Blocked", value=20.0, color="var(--red)"),
        ],
        side_stats=[
            HeroSideStat(key="Avg cycle time", value="4d 2h", tone="default"),
            HeroSideStat(key="Overdue", value="7", tone="red"),
            HeroSideStat(key="Closed this week", value="22", tone="green"),
        ],
    )

    # Hero — minimal variant (no segments, no side_stats — graceful single-column)
    hero_minimal = HeroSpec(
        label="Total platforms",
        big_number=42,
        big_number_unit=None,
        delta_text=None,
        segments=[],
        side_stats=[],
    )

    # KPI cards — 4-up grid (3 with sparkline, 1 without — exercises spark_data=None branch)
    kpi_4up = [
        {"label": "Open", "value": 128, "unit": "", "delta": "+12", "delta_tone": "up",
         "spark_data": [10, 14, 18, 22, 30, 28, 36]},
        {"label": "Closed", "value": 218, "unit": "", "delta": "+22", "delta_tone": "ok",
         "spark_data": [12, 18, 16, 24, 28, 32, 38]},
        {"label": "Overdue", "value": 7, "unit": "", "delta": "-3", "delta_tone": "down",
         "spark_data": [9, 8, 11, 12, 10, 8, 7]},
        {"label": "Avg cycle", "value": "4d 2h", "unit": "", "delta": "flat", "delta_tone": "flat",
         "spark_data": None},
    ]

    # KPI cards — 5-up grid (one with sparkline edge case: constant data)
    kpi_5up = [
        {"label": "SM8650", "value": 12, "unit": "", "delta": "", "delta_tone": "flat",
         "spark_data": [5, 5, 5, 5, 5]},          # constant -> flat line
        {"label": "SM8550", "value": 8, "unit": "", "delta": "+1", "delta_tone": "up",
         "spark_data": [3, 4, 5, 6, 8]},
        {"label": "SM8450", "value": 5, "unit": "", "delta": "", "delta_tone": "flat",
         "spark_data": [2]},                       # single point -> degenerate line
        {"label": "SM7475", "value": 3, "unit": "", "delta": "", "delta_tone": "flat",
         "spark_data": []},                         # empty -> bare svg
        {"label": "Other", "value": 14, "unit": "", "delta": "+4", "delta_tone": "ok",
         "spark_data": [4, 6, 8, 10, 14]},
    ]

    # Filters popover — chip-group sample data
    filter_groups = [
        FilterGroup(label="Status", options=[
            FilterOption(label="Open", value="open", on=True),
            FilterOption(label="Closed", value="closed"),
            FilterOption(label="Overdue", value="overdue"),
        ]),
        FilterGroup(label="OEM", options=[
            FilterOption(label="Samsung", value="samsung"),
            FilterOption(label="SK hynix", value="skhynix", on=True),
            FilterOption(label="Micron", value="micron"),
        ]),
        FilterGroup(label="UFS-eMMC", options=[
            FilterOption(label="UFS 3.1", value="ufs31"),
            FilterOption(label="UFS 4.0", value="ufs40", on=True),
            FilterOption(label="eMMC", value="emmc"),
        ]),
    ]

    # Sticky-corner table — 4x4 sample pivot fixture
    sticky_table_rows = [
        {"label": "SM8650", "values": ["3.1", "1024", "256", "v2.4"]},
        {"label": "SM8550", "values": ["3.1", "512", "128", "v2.3"]},
        {"label": "SM8450", "values": ["3.1", "512", "128", "v2.2"]},
        {"label": "SM7475", "values": ["2.1", "256", "64", "v1.9"]},
    ]
    sticky_table_columns = ["UFS Ver", "RAM (MB)", "Cache (KB)", "FW"]

    return templates.TemplateResponse(
        request,
        "_components/showcase.html",
        {
            "request": request,
            "active_tab": "showcase",
            "page_title": "Component Showcase",
            "hero_full": hero_full,
            "hero_minimal": hero_minimal,
            "kpi_4up": kpi_4up,
            "kpi_5up": kpi_5up,
            "filter_groups": filter_groups,
            "sticky_table_rows": sticky_table_rows,
            "sticky_table_columns": sticky_table_columns,
        },
    )
