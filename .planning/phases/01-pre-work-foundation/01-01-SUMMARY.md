---
phase: "01"
plan: "01"
subsystem: "service-layer / dependencies"
tags:
  - infrastructure
  - refactor
  - dependencies
  - streamlit-decoupling
  - tdd
dependency_graph:
  requires: []
  provides:
    - "app/services/ufs_service.py::list_platforms_core"
    - "app/services/ufs_service.py::list_parameters_core"
    - "app/services/ufs_service.py::fetch_cells_core"
    - "app/services/ufs_service.py::pivot_to_wide_core"
    - "requirements.txt v2.0 deps block"
  affects:
    - "app_v2/services/cache.py (plan 01-04 will import _core names)"
    - "All v1.0 Streamlit pages (unchanged — delegation is transparent)"
tech_stack:
  added:
    - "fastapi>=0.136,<0.137"
    - "uvicorn[standard]>=0.32"
    - "jinja2>=3.1"
    - "jinja2-fragments>=1.3"
    - "python-multipart>=0.0.9"
    - "markdown-it-py[plugins]>=3.0"
    - "cachetools>=7.0,<8.0"
    - "pydantic-settings>=2.14"
  patterns:
    - "_core() / wrapper delegation pattern for @st.cache_data decoupling"
    - "TDD RED-GREEN cycle for refactor contract verification"
key_files:
  modified:
    - path: "requirements.txt"
      description: "Appended 8 v2.0 Bootstrap Shell dependencies under labeled comment section"
      lines: "19-27 (new block)"
    - path: "app/services/ufs_service.py"
      description: "Additive refactor: four _core functions added, three wrappers collapsed to delegates, module docstring updated"
      lines_before: 277
      lines_after: 290
  created:
    - path: "tests/services/test_ufs_service_core.py"
      description: "6 contract tests for _core() functions: equivalence with wrappers, DATA-05 guard, alias identity, subprocess importability"
decisions:
  - "Used db (no underscore) in _core() signatures — the underscore was a Streamlit cache-hashing convention meaningless outside the decorated wrapper context"
  - "pivot_to_wide_core is a name alias (=) not a wrapper — pivot_to_wide has no @st.cache_data decorator, so the function objects are identical"
  - "import streamlit as st retained at module top — the Streamlit wrappers require it; _core callers never invoke decorated paths so no session context is needed"
  - "CONTEXT.md version pins used for requirements.txt (fastapi<0.137, cachetools<8.0) — CONTEXT.md is the authoritative user-discussed artifact"
metrics:
  duration: "4 minutes"
  completed_date: "2026-04-24T16:30:26Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
  files_created: 1
  tests_before: 171
  tests_after: 177
  tests_added: 6
---

# Phase 01 Plan 01: Dependency Additions + ufs_service _core() Extraction Summary

**One-liner:** Appended 8 FastAPI/HTMX-stack deps to requirements.txt and extracted four `_core()` pure functions from `ufs_service.py`, keeping `@st.cache_data` wrappers as one-line delegates — zero regressions across all 177 tests.

## What Was Built

### Task 1 — requirements.txt v2.0 dep block (INFRA-09)

Added 9 lines (1 comment + 8 deps) to `requirements.txt`:

```
# --- v2.0 Bootstrap Shell additions (Phase 1, INFRA-09) ---
fastapi>=0.136,<0.137
uvicorn[standard]>=0.32
jinja2>=3.1
jinja2-fragments>=1.3
python-multipart>=0.0.9
markdown-it-py[plugins]>=3.0
cachetools>=7.0,<8.0
pydantic-settings>=2.14
```

All v1.0 entries unchanged. Version pins follow CONTEXT.md (authoritative user-discussed artifact) where it differs from STACK.md.

### Task 2 — ufs_service.py _core() extraction (INFRA-06)

Purely-additive refactor. File grew from 277 to 290 lines.

**New functions and their line ranges:**

| Function | Lines | Type |
|---|---|---|
| `list_platforms_core(db, db_name="")` | 74–90 | Pure function, no decorator |
| `list_parameters_core(db, db_name="")` | 103–117 | Pure function, no decorator |
| `fetch_cells_core(db, platforms, infocategories, items, row_cap=200, db_name="")` | 131–203 | Pure function, no decorator |
| `pivot_to_wide_core` | 289 | Name alias: `= pivot_to_wide` |

**Wrappers collapsed to delegates:**

- `list_platforms(_db, db_name="")` → `return list_platforms_core(_db, db_name)`
- `list_parameters(_db, db_name="")` → `return list_parameters_core(_db, db_name)`
- `fetch_cells(_db, ...)` → `return fetch_cells_core(_db, platforms, infocategories, items, row_cap, db_name)`

All three `@st.cache_data` decorators preserved. All security contracts preserved in `_core()`:
- `_safe_table()` allowlist check (T-01-01)
- `sa.bindparam(..., expanding=True)` — no f-string interpolation of user values (T-01-02)
- `row_cap + 1` LIMIT + post-fetch truncation (T-01-03)
- `SET SESSION TRANSACTION READ ONLY` non-fatal attempt (T-01-04)
- DATA-05 empty-filter short-circuit in `fetch_cells_core`

**New test file: `tests/services/test_ufs_service_core.py`** (6 tests)

| Test | Assertion |
|---|---|
| `test_list_platforms_core_matches_wrapper` | `_core()` returns same list as wrapper |
| `test_list_parameters_core_matches_wrapper` | `_core()` returns same list[dict] as wrapper |
| `test_fetch_cells_core_matches_wrapper` | `_core()` returns identical (df, capped) tuple |
| `test_fetch_cells_core_empty_filter_short_circuit` | DATA-05: empty platforms → (empty DF, False) |
| `test_pivot_to_wide_core_is_pivot_to_wide` | Alias identity: `pivot_to_wide_core is pivot_to_wide` |
| `test_core_functions_importable_without_streamlit_session` | Subprocess import exits 0, prints "ok" |

## Test Results

```
177 passed, 1 warning in 35.28s
```

- Pre-existing v1.0 tests: 171 (unchanged — zero regressions)
- New _core contract tests: 6
- Total: 177

Regression bar verified: `pytest tests/ --ignore=tests/services/test_ufs_service_core.py` → `171 passed`.

## Commits

| Hash | Type | Description |
|---|---|---|
| `f54fd5f` | chore | Append v2.0 bootstrap shell dependencies to requirements.txt (INFRA-09) |
| `681fd4a` | test | Add failing tests for _core() function contract (INFRA-06 TDD RED) |
| `c907ec2` | feat | Extract _core() pure functions from ufs_service.py (INFRA-06 TDD GREEN) |

## Deviations from Plan

None — plan executed exactly as written.

- All 8 v2.0 deps added at the exact version pins specified in CONTEXT.md
- All 4 `_core()` functions implemented per plan Step 1–5 verbatim
- All 6 contract tests added per plan Step 7 verbatim
- 177 total tests pass (171 pre-existing + 6 new), meeting the ≥177 success criterion

## Known Stubs

None — this plan adds no UI-facing data paths. The `_core()` functions are pure service logic with no stubs.

## Threat Flags

No new security surface introduced. The refactor is purely additive:
- No new network endpoints
- No new auth paths
- No new file I/O
- No schema changes
- SQL parameterization and table allowlist checks preserved verbatim in all `_core()` functions

## Self-Check: PASSED

| Check | Result |
|---|---|
| `requirements.txt` exists | FOUND |
| `app/services/ufs_service.py` exists | FOUND |
| `tests/services/test_ufs_service_core.py` exists | FOUND |
| `01-01-SUMMARY.md` exists | FOUND |
| Commit f54fd5f (requirements) | FOUND |
| Commit 681fd4a (TDD RED) | FOUND |
| Commit c907ec2 (TDD GREEN) | FOUND |
| `_core` names importable without streamlit session | OK |
| pytest total | 177 passed, 0 failed |
