"""SoC prefix -> release year lookup (D-20, D-21).

Initial table covers the most common Qualcomm Snapdragon / MediaTek / Samsung Exynos /
Google Tensor releases seen on the platforms the PBM2 team tracks. Sources:
Wikipedia SoC release timelines + PhoneDB (MEDIUM confidence per FEATURES.md).

Unknown SoCs return None — the UI (D-21) renders these as a 'Unknown' Year badge
styled bg-secondary and INCLUDES them in filter results when no Year filter is selected;
EXCLUDES them only when the user selects a specific year.

Extending the table: add to SOC_YEAR directly in a commit with a link to the source.
No YAML config file for this table in Phase 2 (overhead not justified at ~12 entries).
"""
from __future__ import annotations

SOC_YEAR: dict[str, int | None] = {
    # Qualcomm Snapdragon 8 series
    "SM8350": 2021,
    "SM8450": 2022,
    "SM8550": 2023,
    "SM8650": 2024,
    "SM8750": 2025,
    # MediaTek Dimensity flagship
    "MT6985": 2023,
    "MT6989": 2024,
    # Samsung Exynos flagship
    "Exynos2100": 2021,
    "Exynos2200": 2022,
    "Exynos2400": 2024,
    # Google Tensor
    "GS301": 2022,
    "GS401": 2023,
}


def get_year(soc_raw: str) -> int | None:
    """Return release year for a known SoC prefix, else None.

    O(1) dict lookup. No normalization — caller passes the raw SoC string returned
    by parse_platform_id()[2]. If the DB convention later introduces variant suffixes
    like 'SM8450-AB', add explicit normalization here and re-test.
    """
    return SOC_YEAR.get(soc_raw)
