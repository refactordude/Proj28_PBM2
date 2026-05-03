"""Seed data/demo_ufs.db with realistic UFS-shaped EAV rows for v2.0 Browse UAT.

Idempotent: re-running deletes and recreates the file. Uses sqlite3 stdlib
only — no SQLAlchemy / pandas dependency.

The 20 demo platforms are grouped into FIVE tiers, each with its own subset
of the 12 base parameters PLUS a tier-light intra-tier sparseness (~5-10%).
Four single-platform parameters are added so unselecting a single specialty
platform definitively removes its unique parameters from the Browse filter.

This shape was chosen so the 260429-qyv feature ("Parameters filter depends
on selected Platforms") is exercisable in UAT — picking flagship platforms
shows ~13 parameters, picking the legacy chip shows ~5, picking only the
automotive chip surfaces an "AutomotiveProfile" parameter that no other
platform has, etc.

Usage:
    python scripts/seed_demo_db.py
"""
from __future__ import annotations

import random
import sqlite3
from collections import defaultdict
from pathlib import Path

# Resolve repo root by walking up from this file (works from any CWD).
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DATA_DIR = _REPO_ROOT / "data"
_DB_PATH = _DATA_DIR / "demo_ufs.db"

# ---------------------------------------------------------------------------
# Platforms — 20 total, grouped into 5 tiers. Tier name → ordered platforms.
# Tier order is preserved in the seeded rows for stable cursor diffs.
# ---------------------------------------------------------------------------
TIERS: dict[str, tuple[str, ...]] = {
    "modern_flagship": (
        "SM8850_v1",
        "SM8650_v1",
        "SM8650_v2",
        "MTK6989_rev2",
        "EXYNOS2400_a",
        "TENSOR_G3_x1",
        "KIRIN9000s_a",
        "DIMENSITY9300_v1",
        "SDM_X75_v1",
    ),
    "prev_gen_flagship": (
        "SM8550_rev1",
        "MTK6985_a",
        "EXYNOS2200_b",
        "TENSOR_G2_x2",
        "DIMENSITY9200_v2",
    ),
    "midrange": (
        "EXYNOS1380_c",
        "MTK6983_b",
    ),
    "legacy": (
        "MSM8998_legacy",
    ),
    "specialty": (
        "SC8275_auto",
        "QCS6490_iot",
        "MT8195_chrome",
        "RK3588_dev",
    ),
}
PLATFORMS: tuple[str, ...] = tuple(p for tier in TIERS.values() for p in tier)
assert len(PLATFORMS) == 21, f"expected 21 platforms, got {len(PLATFORMS)}"

# ---------------------------------------------------------------------------
# Base parameter pool — 12 (InfoCategory, Item) entries with their value pool.
# Entries are referenced from tier masks below by index.
# ---------------------------------------------------------------------------
PARAMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    # 0  vendor manufacturer
    ("VendorInfo", "ManufacturerName", ("Samsung", "SK Hynix", "Micron", "Kioxia")),
    # 1  vendor product
    ("VendorInfo", "ProductName", ("KLUFG8RJ4C-B0C1", "H58Q2G8DDK", "MTFC512GAJDQ", "THGJFGT0T43BAIL")),
    # 2  number of LUs
    ("DeviceInfo", "NumberOfLU", ("8", "16", "32")),
    # 3  bDeviceVersion (UFS spec rev — modern only)
    ("DeviceInfo", "bDeviceVersion", ("0x0310", "0x0220", "0x0400")),
    # 4  raw capacity
    ("GeometryDescriptor", "RawDeviceCapacity", ("1024209543168", "512104771584", "256052385792")),
    # 5  segment size (geometry depth)
    ("GeometryDescriptor", "SegmentSize", ("0x00080000", "0x00100000", "0x00200000")),
    # 6  allocation unit (geometry depth)
    ("GeometryDescriptor", "AllocationUnitSize", ("1", "2", "4")),
    # 7  capacity adjustment factor
    ("UnitDescriptor", "dCapacityAdjFactor", ("1.0000", "0.9842", "0.9521")),
    # 8  logical block size
    ("UnitDescriptor", "bLogicalBlockSize", ("0x0C", "0x09")),
    # 9  power active levels (mobile-only — auto strips this)
    ("PowerParameters", "bActiveICCLevelsForVCC", ("0x14", "0x1F", "0x0A")),
    # 10 interconnect HS gear (modern: 5, prev-gen: 4)
    ("InterconnectDescriptor", "bMaxRxHsGear", ("4", "5")),
    # 11 string descriptor (modern flagship only)
    ("StringDescriptor", "oManufacturerName", ("0x80", "0xC0")),
)

# ---------------------------------------------------------------------------
# Tier → param-index mask. Each tier has its own subset of the 12 base params.
# These were chosen so adjacent tiers visibly differ (e.g. legacy is a strict
# subset of midrange; modern_flagship is a strict superset of prev_gen).
# ---------------------------------------------------------------------------
TIER_PARAM_MASK: dict[str, frozenset[int]] = {
    # All 12 base params.
    "modern_flagship": frozenset(range(12)),
    # No StringDescriptor (11), no AllocationUnitSize (6); HS gear stays at 4.
    "prev_gen_flagship": frozenset({0, 1, 2, 3, 4, 5, 7, 8, 9, 10}),
    # Basic geometry only — drops Power (9), Interconnect (10), String (11),
    # AllocUnit (6), AdjFactor (7); keeps the headline UFS spec marker (3).
    "midrange": frozenset({0, 1, 2, 3, 4, 5, 8}),
    # UFS 2.x era — drops bDeviceVersion (3), Power, Interconnect, String,
    # SegmentSize (5), AllocUnit (6), AdjFactor (7).
    "legacy": frozenset({0, 1, 2, 4, 8}),
    # Specialty platforms get the basic + per-platform unique override
    # (defined separately below). Mask kept lean to leave room for the
    # specialty's unique parameter to stand out in the filter.
    "specialty": frozenset({0, 1, 2, 4, 8, 9}),
}

# ---------------------------------------------------------------------------
# Per-platform UNIQUE parameters — only this single platform has the row.
# Unselecting the platform definitively removes the parameter from the Browse
# Parameters filter (the headline win for 260429-qyv UAT scenario D).
# Mapping: PLATFORM_ID → (InfoCategory, Item, value-pool).
# ---------------------------------------------------------------------------
UNIQUE_PARAMS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "SC8275_auto": (
        "AutomotiveProfile", "QualGradeLevel", ("AEC-Q100-G2", "AEC-Q100-G3"),
    ),
    "QCS6490_iot": (
        "IoTPowerProfile", "DeepSleepCurrentUA", ("12", "18", "25"),
    ),
    "RK3588_dev": (
        "DevBoard", "DebugBuildId", ("rk3588-dev-2024.04", "rk3588-dev-2025.01"),
    ),
    "MSM8998_legacy": (
        "LegacyExtension", "eUFSGenerationTag", ("UFS2.1-classic", "UFS2.0-classic"),
    ),
}

# Intra-tier random drop probability — keeps tier siblings nearly identical
# but not perfectly uniform (small realistic gaps).
_INTRA_TIER_DROP_PCT = 8


def _platform_tier(pid: str) -> str:
    for tier, members in TIERS.items():
        if pid in members:
            return tier
    raise KeyError(f"platform {pid!r} is not in any tier")


def main() -> int:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if _DB_PATH.exists():
        print(f"Removing existing {_DB_PATH}")
        _DB_PATH.unlink()

    rng = random.Random(42)  # local RNG instance — does not pollute global state

    rows: list[tuple[str, str, str, str]] = []
    rows_per_platform: dict[str, int] = defaultdict(int)
    distinct_items_per_platform: dict[str, set[str]] = defaultdict(set)

    for pid in PLATFORMS:
        tier = _platform_tier(pid)
        mask = TIER_PARAM_MASK[tier]
        for idx, (category, item, pool) in enumerate(PARAMS):
            if idx not in mask:
                continue
            if rng.randrange(100) < _INTRA_TIER_DROP_PCT:
                continue  # small intra-tier gap so siblings aren't identical
            rows.append((pid, category, item, rng.choice(pool)))
            rows_per_platform[pid] += 1
            distinct_items_per_platform[pid].add(item)

        # Platform-unique parameter (no drop — UAT needs it deterministic).
        if pid in UNIQUE_PARAMS:
            u_cat, u_item, u_pool = UNIQUE_PARAMS[pid]
            rows.append((pid, u_cat, u_item, rng.choice(u_pool)))
            rows_per_platform[pid] += 1
            distinct_items_per_platform[pid].add(u_item)

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

    distinct_items_total = {item for _, _, item, _ in rows}
    print(f"Seeded {len(rows)} rows into {_DB_PATH}")
    print(f"Platforms: {len(PLATFORMS)}, distinct (Item) labels: {len(distinct_items_total)}")
    print()
    print("Per-tier parameter coverage (sample platform → distinct Item count):")
    for tier, members in TIERS.items():
        sample = members[0]
        print(
            f"  {tier:<20s} ({len(members)} platforms) "
            f"sample={sample}: {len(distinct_items_per_platform[sample])} distinct Items"
        )
    print()
    print("Platform-unique parameters (only on the named platform):")
    for pid, (cat, item, _) in UNIQUE_PARAMS.items():
        print(f"  {pid:<20s} → {cat}.{item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
