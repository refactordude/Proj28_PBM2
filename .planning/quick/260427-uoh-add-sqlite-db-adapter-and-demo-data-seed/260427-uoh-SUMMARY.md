---
phase: 260427-uoh
plan: 01
type: quick
tags: [sqlite, db-adapter, demo-data, dev-fixture, uat-unblock]
subsystem: db-adapters
key-files:
  created:
    - app/adapters/db/sqlite.py
    - scripts/seed_demo_db.py
    - data/demo_ufs.db
    - config/settings.yaml  # gitignored per D-11; exists on disk only
  modified:
    - app/core/config.py
    - app/adapters/db/registry.py
decisions:
  - "config/settings.yaml is gitignored per D-11 (holds plaintext api_keys); file created on disk for runtime use, not committed"
  - "Smoke test polling loop used (0.5s intervals up to 10s) instead of fixed 2s sleep — Streamlit cache warnings add startup overhead beyond 2s"
metrics:
  completed: "2026-04-27"
  tasks: 3
  files_created: 4
  files_modified: 2
---

# Phase 260427-uoh Plan 01: Add SQLite DB Adapter and Demo Data Seed — Summary

**One-liner:** SQLiteAdapter + idempotent EAV seeder wiring `data/demo_ufs.db` into the v2.0 Browse lifespan via `config/settings.yaml`, enabling no-MySQL UAT.

## Files Created / Modified

### Created

| File | Purpose |
|------|---------|
| `app/adapters/db/sqlite.py` | `SQLiteAdapter` implementing all 5 `DBAdapter` methods (`test_connection`, `list_tables`, `get_schema`, `run_query`, `dispose`) + private `_get_engine()` |
| `scripts/seed_demo_db.py` | Idempotent CLI seeder using `sqlite3` stdlib only; 20 platforms × 12 params → 142 rows with `random.Random(42)` reproducibility |
| `data/demo_ufs.db` | Seeded SQLite file with `ufs_data` table + `idx_platform` index |
| `config/settings.yaml` | Runtime config pointing at demo SQLite (gitignored per D-11; exists on disk) |

### Modified

| File | Change |
|------|--------|
| `app/core/config.py` | Added `"sqlite"` to `DatabaseConfig.type` Literal |
| `app/adapters/db/registry.py` | Added `from app.adapters.db.sqlite import SQLiteAdapter` import and `"sqlite": SQLiteAdapter` entry to `_REGISTRY` |

## Verification Command Outputs

### 1. Adapter contract (Task 1 automated verify)

```
OK ['mysql', 'sqlite'] 연결 성공
```

### 2. Seeder output (Task 2 automated verify)

```
Seeded 142 rows into /home/yh/Desktop/02_Projects/Proj28_PBM2/data/demo_ufs.db
Platforms: 20, parameters: 12
rows=142 platforms=20 params=12
```

Second run (idempotency check):
```
Removing existing /home/yh/Desktop/02_Projects/Proj28_PBM2/data/demo_ufs.db
Seeded 142 rows into /home/yh/Desktop/02_Projects/Proj28_PBM2/data/demo_ufs.db
Platforms: 20, parameters: 12
```

### 3. Settings load (Task 3 verify step 1)

```
settings OK: Demo SQLite sqlite data/demo_ufs.db
```

### 4. Adapter against seeded DB (Task 3 verify step 2)

```
adapter OK: ['ufs_data']
```

### 5. Uvicorn smoke test (GET /browse)

```
GET /browse -> 200
SMOKE TEST PASSED
```

Startup log confirmed: `Application startup complete` followed by `GET /browse HTTP/1.1" 200 OK`.

### 6. Regression test suite

```
453 passed, 1 skipped, 3 warnings in 43.73s
```

All 453 existing tests pass (was 171 v1.0 tests + Phase 4 invariant guards and integration tests).

### 7. MySQL path unchanged

```
git diff app/adapters/db/mysql.py app/services/ufs_service.py
(empty — byte-identical)
```

## Deviations from Plan

### 1. config/settings.yaml not committed to git

- **Found during:** Task 3 commit
- **Issue:** `config/settings.yaml` is gitignored per the existing D-11 decision (line 2 of `.gitignore`: `config/settings.yaml` — reason: "holds plaintext passwords/api_keys"). `git add` fails with "ignored by gitignore" error.
- **Resolution:** File created on disk (verified present at 685 bytes). No force-add — D-11 is an explicit project decision that takes precedence. The file functions correctly at runtime (settings load, adapter build, and smoke test all pass with it).
- **Classification:** Not a deviation from the plan's intent — the plan says "exists on disk," not "tracked in git." The plan's `config/settings.yaml` artifact is satisfied.

### 2. Smoke test polling loop instead of fixed sleep

- **Found during:** Task 3 smoke test
- **Issue:** The Streamlit cache warm-up warnings (`No runtime found, using MemoryCacheStorageManager`) add ~2-3s startup overhead. Fixed `sleep 2` caused HTTP 000 (connection refused — server not yet bound).
- **Fix:** Used a 0.5s-interval polling loop (up to 10 iterations = 5s max) that exits as soon as the first successful curl returns 200. Server bound in approximately 3s on this machine.
- **Classification:** [Rule 3 - Blocking] — fixed inline; no behavior change to production code.

## Out-of-Scope Items Confirmed Untouched

| File/Directory | Status |
|----------------|--------|
| `app/adapters/db/mysql.py` | Byte-identical — no diff |
| `app/services/ufs_service.py` | Byte-identical — no diff |
| `tests/` (all files) | Not modified |
| `.planning/ROADMAP.md` | Not modified |
| `.planning/STATE.md` | Not modified |
| `.planning/phases/**/PLAN.md` | Not modified |
| `requirements.txt` | Not modified (sqlite3 is stdlib) |

## Self-Check

### Created files exist:
- `app/adapters/db/sqlite.py` — FOUND
- `scripts/seed_demo_db.py` — FOUND
- `data/demo_ufs.db` — FOUND
- `config/settings.yaml` — FOUND (on disk, gitignored)

### Commits exist:
- `d022bae` — feat: SQLiteAdapter + config + registry
- `43e51e1` — feat: seeder script + demo_ufs.db

## Self-Check: PASSED
