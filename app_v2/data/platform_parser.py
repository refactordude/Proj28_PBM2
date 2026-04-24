"""PLATFORM_ID parser per D-19.

Convention: Brand_Model_SoCID (e.g., Samsung_S22Ultra_SM8450). Phase 2 filters derive
brand + soc_raw from this parser; year is resolved by app_v2.data.soc_year.get_year(soc_raw).
"""
from __future__ import annotations


def parse_platform_id(pid: str) -> tuple[str, str, str]:
    """Split PLATFORM_ID on '_' with maxsplit=2. Missing trailing parts become ''.

    Never raises. See module docstring for convention.

    Examples:
        parse_platform_id("Samsung_S22Ultra_SM8450") -> ("Samsung", "S22Ultra", "SM8450")
        parse_platform_id("OnlyOne")                 -> ("OnlyOne", "", "")
        parse_platform_id("")                        -> ("", "", "")
        parse_platform_id("A_B_C_D_E")               -> ("A", "B", "C_D_E")  # maxsplit=2
    """
    parts = pid.split("_", 2)
    brand = parts[0] if len(parts) >= 1 else ""
    model = parts[1] if len(parts) >= 2 else ""
    soc_raw = parts[2] if len(parts) >= 3 else ""
    return brand, model, soc_raw
