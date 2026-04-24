---
phase: "02"
plan: "01"
subsystem: data-layer
tags:
  - data-layer
  - parser
  - storage
  - yaml
  - atomic-write
  - tdd
dependency_graph:
  requires: []
  provides:
    - app_v2.data.platform_parser.parse_platform_id
    - app_v2.data.soc_year.SOC_YEAR
    - app_v2.data.soc_year.get_year
    - app_v2.services.overview_store.OverviewEntity
    - app_v2.services.overview_store.DuplicateEntityError
    - app_v2.services.overview_store.load_overview
    - app_v2.services.overview_store.add_overview
    - app_v2.services.overview_store.remove_overview
  affects:
    - 02-02 (imports parse_platform_id, get_year, overview_store)
    - 02-03 (imports overview_store for filter logic)
tech_stack:
  added:
    - pyyaml (already present; used for YAML read/write in overview_store)
    - pydantic v2 (OverviewEntity model with field_validator)
  patterns:
    - TDD red-green: failing tests committed before implementation
    - Atomic write: tempfile.mkstemp + os.fsync + os.replace (same-filesystem rename)
    - Defensive reads: yaml.safe_load + YAMLError catch returning [] with warning
    - Module-level path constant (OVERVIEW_YAML) monkeypatched in tests
key_files:
  created:
    - app_v2/data/__init__.py
    - app_v2/data/platform_parser.py
    - app_v2/data/soc_year.py
    - app_v2/services/overview_store.py
    - config/overview.example.yaml
    - tests/v2/test_platform_parser.py
    - tests/v2/test_soc_year.py
    - tests/v2/test_overview_store.py
  modified:
    - .gitignore (added config/overview.yaml exclusion)
decisions:
  - "parse_platform_id uses pid.split('_', 2) — maxsplit=2 collapses extra underscores into soc_raw, which is the correct behavior for SoC IDs with underscores in them"
  - "SOC_YEAR is a plain Python dict (not YAML config) — 12 entries, overhead not justified at this scale; adding to YAML config deferred to when entries exceed ~50"
  - "OVERVIEW_YAML is a module-level Path constant so tests can monkeypatch it without touching real config/"
  - "os.fsync before os.replace ensures durability on ext4/xfs without barriers"
  - "DuplicateEntityError subclasses ValueError so callers can catch either"
metrics:
  duration_seconds: 302
  completed_date: "2026-04-24"
  tasks_completed: 2
  tasks_total: 2
  files_created: 8
  files_modified: 1
  tests_added: 27
  tests_total: 240
---

# Phase 02 Plan 01: Data Layer (parser + SoC year + overview store) Summary

**One-liner:** PLATFORM_ID parser (D-19), SoC→year lookup table (D-20/D-21), and atomic YAML overview store (D-22..D-24) — the three data-layer primitives that 02-02 and 02-03 import.

## What Was Built

### Task 1: PLATFORM_ID Parser + SoC Year Lookup

**`app_v2/data/platform_parser.py`**

`parse_platform_id(pid: str) -> tuple[str, str, str]` splits on `_` with `maxsplit=2`, returning `(brand, model, soc_raw)`. Missing trailing parts become empty strings. Never raises on any input including empty string or single-part IDs.

**`app_v2/data/soc_year.py`**

`SOC_YEAR` dict (12 entries) + `get_year(soc_raw) -> int | None`. O(1) lookup. Returns None for unknown SoCs (D-21 semantics: unknown SoCs render as "Unknown" Year badge and are included in unfiltered results).

Exact SOC_YEAR entries (for maintainer reference when extending):
```python
"SM8350": 2021,  # Qualcomm Snapdragon 888
"SM8450": 2022,  # Qualcomm Snapdragon 8 Gen 1
"SM8550": 2023,  # Qualcomm Snapdragon 8 Gen 2
"SM8650": 2024,  # Qualcomm Snapdragon 8 Gen 3
"SM8750": 2025,  # Qualcomm Snapdragon 8 Elite
"MT6985": 2023,  # MediaTek Dimensity 9200
"MT6989": 2024,  # MediaTek Dimensity 9300
"Exynos2100": 2021,
"Exynos2200": 2022,
"Exynos2400": 2024,
"GS301": 2022,   # Google Tensor G1
"GS401": 2023,   # Google Tensor G2
```

### Task 2: YAML-Backed Overview Store

**`app_v2/services/overview_store.py`** (~151 lines)

- `OverviewEntity(BaseModel)`: fields `platform_id: str` (non-empty, `min_length=1` + field_validator) and `added_at: datetime`
- `DuplicateEntityError(ValueError)`: message includes the duplicate platform_id
- `load_overview()`: reads OVERVIEW_YAML, returns entities sorted newest-first by added_at desc. Returns `[]` for missing file, empty entities list, or malformed YAML (logs warning)
- `add_overview(pid)`: checks for duplicate, creates OverviewEntity with `datetime.now(timezone.utc)`, prepends to list, atomic write, returns entity
- `remove_overview(pid)`: no-op returning False if not found; atomic write + return True if found
- `_atomic_write(entities)`: `tempfile.mkstemp` in target directory + `os.fsync` + `os.replace` — last-writer-wins, never half-written

**`config/overview.example.yaml`** — empty template committed to git:
```yaml
# Phase 2 curated-entity store
entities: []
```

**`.gitignore`** — added `config/overview.yaml` under existing "Config files containing secrets" block.

## Atomicity Test Strategy

The critical atomicity test (`test_write_is_atomic_on_os_replace_failure`) uses `unittest.mock.patch("os.replace", side_effect=OSError)`:

1. Populate store with 3 entities (confirmed via load_overview)
2. Patch `os.replace` to raise `OSError("simulated crash")`
3. Call `add_overview("pid_4")` — expect `OSError` to propagate
4. Assert `load_overview()` still returns exactly 3 entities with the same PIDs

This works because `_atomic_write` creates a tempfile, writes to it, flushes/fsyncs it, then calls `os.replace`. If `os.replace` fails, the exception propagates, the `except` block unlinks the tempfile, and the original YAML file is untouched.

## Test Count

| File | Tests Added | Coverage |
|------|-------------|----------|
| tests/v2/test_platform_parser.py | 7 | All parse_platform_id branches: 3-part, 4+part, 2-part, 1-part, empty string, return type |
| tests/v2/test_soc_year.py | 8 | 12 required entries, known Qualcomm/Exynos/Tensor, unknown returns None, immutability |
| tests/v2/test_overview_store.py | 13 | Missing file, empty list, malformed YAML, add creates file, prepend order, duplicate error, UTC timezone, remove true/false/exact, empty pid validation, atomicity, ValueError subclass |
| **Total** | **27** | |

**Regression:** 213 prior tests + 27 new = 240 total (all passing).

## Integration Contract for Plan 02-02

The exact import lines 02-02 router will use:

```python
from app_v2.data.platform_parser import parse_platform_id
from app_v2.data.soc_year import get_year
from app_v2.services.overview_store import (
    DuplicateEntityError,
    OverviewEntity,
    add_overview,
    load_overview,
    remove_overview,
)
```

No further scaffolding needed. All six names are importable and behave per the D-19/D-20/D-21/D-22/D-24 contracts.

## Deviations from Plan

None — plan executed exactly as written. All TDD RED→GREEN cycles completed in order. All acceptance criteria met.

## Known Stubs

None — all functions are fully implemented with real logic.

## Threat Flags

No new threat surface beyond what the plan's threat model covers (T-02-01-01 through T-02-01-06).

## Self-Check: PASSED

Files created:
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/app_v2/data/__init__.py` — exists
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/app_v2/data/platform_parser.py` — exists
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/app_v2/data/soc_year.py` — exists
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/app_v2/services/overview_store.py` — exists
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/config/overview.example.yaml` — exists
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/tests/v2/test_platform_parser.py` — exists
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/tests/v2/test_soc_year.py` — exists
- `/home/yh/Desktop/02_Projects/Proj28_PBM2/tests/v2/test_overview_store.py` — exists

Commits:
- 074ae10: test(02-01): add failing tests for platform_parser + soc_year (TDD RED)
- 2497fa9: feat(02-01): implement PLATFORM_ID parser + SoC year lookup (FILTER-04)
- c0e6e54: test(02-01): add failing tests for overview_store YAML persistence (TDD RED)
- 45f286f: feat(02-01): implement YAML-backed overview_store with atomic writes (OVERVIEW-05)
