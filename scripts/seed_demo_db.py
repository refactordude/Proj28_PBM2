"""Seed data/demo_ufs.db with realistic UFS-shaped EAV rows for v2.0 Browse UAT.

Idempotent: re-running deletes and recreates the file. Uses sqlite3 stdlib
only — no SQLAlchemy / pandas dependency.

Usage:
    python scripts/seed_demo_db.py
"""
from __future__ import annotations

import random
import sqlite3
from pathlib import Path

# Resolve repo root by walking up from this file (works from any CWD).
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DATA_DIR = _REPO_ROOT / "data"
_DB_PATH = _DATA_DIR / "demo_ufs.db"

PLATFORMS: tuple[str, ...] = (
    "SM8650_v1",
    "SM8650_v2",
    "SM8550_rev1",
    "MTK6989_rev2",
    "MTK6985_a",
    "MTK6983_b",
    "EXYNOS2400_a",
    "EXYNOS2200_b",
    "EXYNOS1380_c",
    "TENSOR_G3_x1",
    "TENSOR_G2_x2",
    "KIRIN9000s_a",
    "DIMENSITY9300_v1",
    "DIMENSITY9200_v2",
    "SDM_X75_v1",
    "MSM8998_legacy",
    "SC8275_auto",
    "QCS6490_iot",
    "MT8195_chrome",
    "RK3588_dev",
)

PARAMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("VendorInfo", "ManufacturerName", ("Samsung", "SK Hynix", "Micron", "Kioxia")),
    ("VendorInfo", "ProductName", ("KLUFG8RJ4C-B0C1", "H58Q2G8DDK", "MTFC512GAJDQ", "THGJFGT0T43BAIL")),
    ("DeviceInfo", "NumberOfLU", ("8", "16", "32")),
    ("DeviceInfo", "bDeviceVersion", ("0x0310", "0x0220", "0x0400")),
    ("GeometryDescriptor", "RawDeviceCapacity", ("1024209543168", "512104771584", "256052385792")),
    ("GeometryDescriptor", "SegmentSize", ("0x00080000", "0x00100000", "0x00200000")),
    ("GeometryDescriptor", "AllocationUnitSize", ("1", "2", "4")),
    ("UnitDescriptor", "dCapacityAdjFactor", ("1.0000", "0.9842", "0.9521")),
    ("UnitDescriptor", "bLogicalBlockSize", ("0x0C", "0x09")),
    ("PowerParameters", "bActiveICCLevelsForVCC", ("0x14", "0x1F", "0x0A")),
    ("InterconnectDescriptor", "bMaxRxHsGear", ("4", "5")),
    ("StringDescriptor", "oManufacturerName", ("0x80", "0xC0")),
)


def main() -> int:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if _DB_PATH.exists():
        print(f"Removing existing {_DB_PATH}")
        _DB_PATH.unlink()

    rng = random.Random(42)  # local RNG instance — does not pollute global state

    rows: list[tuple[str, str, str, str]] = []
    for pid in PLATFORMS:
        for category, item, pool in PARAMS:
            if rng.randrange(100) < 38:
                continue  # leave a gap so the pivot grid has visible holes
            rows.append((pid, category, item, rng.choice(pool)))

    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE ufs_data ("
            "PLATFORM_ID TEXT, InfoCategory TEXT, Item TEXT, Result TEXT)"
        )
        conn.execute("CREATE INDEX idx_platform ON ufs_data (PLATFORM_ID)")
        conn.executemany(
            "INSERT INTO ufs_data (PLATFORM_ID, InfoCategory, Item, Result) "
            "VALUES (?, ?, ?, ?)",
            rows,
        )

    print(f"Seeded {len(rows)} rows into {_DB_PATH}")
    print(f"Platforms: {len(PLATFORMS)}, parameters: {len(PARAMS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
