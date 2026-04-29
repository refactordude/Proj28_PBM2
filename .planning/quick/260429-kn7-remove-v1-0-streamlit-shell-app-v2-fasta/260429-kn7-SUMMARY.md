---
phase: 260429-kn7
plan: 01
subsystem: services/ufs_service, app_v2/services/cache, app_v2/services/browse_service, tests
tags: [streamlit-sunset, refactor, cleanup, deps]
dependency_graph:
  requires: []
  provides: [framework-agnostic-ufs-service, canonical-api-names, streamlit-free-repo]
  affects: [app/services/ufs_service.py, app_v2/services/cache.py, app_v2/services/browse_service.py]
tech_stack:
  removed: [streamlit, streamlit-authenticator, nest-asyncio, bcrypt]
  patterns: [framework-agnostic service layer, TTLCache wrappers with _uncached aliases]
key_files:
  deleted:
    - streamlit_app.py
    - app/pages/__init__.py
    - app/pages/browse.py
    - app/pages/settings.py
    - app/components/__init__.py
    - app/components/export_dialog.py
    - tests/pages/__init__.py
    - config/auth.yaml
    - tests/services/test_ufs_service_core.py
  modified:
    - app/services/ufs_service.py
    - app_v2/services/cache.py
    - app_v2/services/browse_service.py
    - tests/v2/test_cache.py
    - tests/v2/test_browse_service.py
    - tests/v2/test_browse_routes.py
    - tests/v2/test_phase06_invariants.py
    - requirements.txt
    - .env.example
    - CLAUDE.md
    - .planning/PROJECT.md
  created:
    - tests/services/test_ufs_service.py
decisions:
  - "Deleted v1.0 Streamlit shell atomically with its invariant flip (Task 1) so every commit SHA is green"
  - "Renamed *_core imports in cache.py to _*_uncached aliases to avoid self-shadowing in wrapper functions"
  - "Merged test_ufs_service.py + test_ufs_service_core.py into a single framework-agnostic test file"
  - "Preserved @st.cache_resource docstring reference in ask.py as documentation (not a decorator)"
metrics:
  duration: "~25 minutes"
  completed_date: "2026-04-29"
  tasks_completed: 5
  files_deleted: 9
  files_modified: 11
  files_created: 1
  deps_removed: 4
  tests_before: 506
  tests_after: 507
  tests_delta: "+1 (new test_ufs_service.py adds more pivot_to_wide + fetch_cells cases than removed)"
---

# Quick Task 260429-kn7: Remove v1.0 Streamlit Shell — app_v2 Becomes Single Source of Truth

**One-liner:** Deleted Streamlit pages/components/entry-point, dropped 4 deps, renamed `*_core` API to canonical names, and updated all import sites + patch targets atomically so every commit SHA stays green.

## What Was Done

### Task 1 — Delete v1.0 Streamlit UI surface (commit `511f1cb`)

Files deleted (git rm + disk):
- `streamlit_app.py` — v1.0 entry point (`st.navigation([Browse, Settings])`)
- `app/pages/browse.py` — v1.0 Browse with `@st.cache_resource`, sidebar widgets, Pivot/Detail/Chart tabs
- `app/pages/settings.py` — v1.0 Settings with `@st.dialog`
- `app/components/export_dialog.py` — v1.0 export modal with `@st.dialog`
- `app/pages/__init__.py`, `app/components/__init__.py`, `tests/pages/__init__.py`
- `config/auth.yaml` — streamlit-authenticator demo credentials (gitignored; removed from disk)

Additional changes:
- `.env.example`: removed `# AUTH_PATH=config/auth.yaml` comment block
- `tests/v2/test_phase06_invariants.py` lines 200-202: flipped from `streamlit_app.py.read_text()` guard to `assert not (REPO / "streamlit_app.py").exists()` — atomic with the deletion so the suite is green at this SHA

### Task 2 — Refactor ufs_service.py canonical API (commit `d247cbd`)

**app/services/ufs_service.py** — full rewrite:
- Removed `import streamlit as st`
- Deleted `@st.cache_data(ttl=300)` wrapper `list_platforms` and its `list_platforms_core` body (merged: body becomes `list_platforms`)
- Deleted `@st.cache_data(ttl=300)` wrapper `list_parameters` and its `list_platforms_core` body (merged)
- Deleted `@st.cache_data(ttl=60)` wrapper `fetch_cells` and its `fetch_cells_core` body (merged)
- Deleted trailing `pivot_to_wide_core = pivot_to_wide` alias
- Rewrote module docstring to document single canonical API

Before (dual API):
```
list_platforms_core / list_platforms (@st.cache_data)
list_parameters_core / list_parameters (@st.cache_data)
fetch_cells_core / fetch_cells (@st.cache_data)
pivot_to_wide / pivot_to_wide_core (alias)
```

After (single canonical API):
```
list_platforms(db, db_name="") -> list[str]
list_parameters(db, db_name="") -> list[dict]
fetch_cells(db, platforms, infocategories, items, row_cap=200, db_name="") -> tuple[pd.DataFrame, bool]
pivot_to_wide(df_long, swap_axes=False, col_cap=30) -> tuple[pd.DataFrame, bool]
```

**app_v2/services/cache.py** — import rename:
```python
# Before
from app.services.ufs_service import fetch_cells_core, list_parameters_core, list_platforms_core

# After
from app.services.ufs_service import (
    fetch_cells as _fetch_cells_uncached,
    list_parameters as _list_parameters_uncached,
    list_platforms as _list_platforms_uncached,
)
```
The `_uncached` aliasing prevents the public wrapper functions (`list_platforms`, etc.) from shadowing their own imports and calling themselves recursively.

**app_v2/services/browse_service.py:**
- `from app.services.ufs_service import pivot_to_wide_core` → `pivot_to_wide`
- `pivot_to_wide_core(df_long, ...)` call → `pivot_to_wide(df_long, ...)`
- Docstring references updated

**tests/v2/test_browse_service.py:**
- `mocker.patch.object(browse_service, "pivot_to_wide_core", ...)` → `pivot_to_wide`

**tests/v2/test_browse_routes.py:**
- Comment-only reference updated

**tests/v2/test_cache.py:** 15 patch-target strings renamed:
- `app_v2.services.cache.list_platforms_core` → `app_v2.services.cache._list_platforms_uncached`
- `app_v2.services.cache.list_parameters_core` → `app_v2.services.cache._list_parameters_uncached`
- `app_v2.services.cache.fetch_cells_core` → `app_v2.services.cache._fetch_cells_uncached`

**tests/services:** removed `test_ufs_service.py` (Streamlit-dependent) and `test_ufs_service_core.py` (wrapper-comparison tests). Created new `tests/services/test_ufs_service.py` covering:
- `list_platforms` / `list_parameters` basic queries
- `fetch_cells` DATA-05 short-circuit, category filter, row-cap, end-to-end without cache
- `pivot_to_wide` empty/default/swap-axes/col-cap/duplicate-warning
- subprocess import isolation (no Streamlit session needed)

### Task 3 — Drop 4 dependencies from requirements.txt (commit `573b7fa`)

Removed:
- `streamlit>=1.40,<2.0` — v1.0 framework; nothing imports it
- `streamlit-authenticator>=0.3.3,<1.0` — paired with deleted auth.yaml
- `nest-asyncio>=1.6` — was used by deleted `app/pages/ask.py` for event loop workaround; FastAPI sync routes don't need it
- `bcrypt>=4.2` — transitive dep of streamlit-authenticator; no v2.0 importer

### Task 4 — Rewrite project framing in docs (commit `7266e00`)

`.planning/PROJECT.md` changes:
- "What This Is": "Streamlit website" → "FastAPI + Bootstrap 5 + HTMX website"
- Constraints tech stack: Streamlit → FastAPI + Bootstrap 5 + HTMX + Jinja2 + jinja2-fragments line
- Out of Scope export entry: updated to reflect export_dialog removal and v2.0-native future
- Active Platform bullet: references v1.0 Streamlit removal
- Key Decisions: auth row outcome updated; export row resolved
- Last updated: timestamp updated to this quick task

`CLAUDE.md` changes:
- GSD:project-start block: mirrored FastAPI framing
- Added v2.0 supersession annotation before the research stack table (table preserved for historical record)

### Task 5 — Final verification gate (no commit needed — all gates passed)

## Verification Gates Passed

| Gate | Command | Result |
|------|---------|--------|
| Streamlit import audit | `grep -rE "^\s*import streamlit\|^\s*from streamlit" app/ app_v2/ tests/` | 0 hits |
| @st decorator audit | `grep -rE "^\s*@st\." app/ app_v2/` | 0 hits |
| _core suffix audit (key files) | `grep -rE "_core\b" ufs_service.py cache.py browse_service.py ...` | 0 hits |
| test_cache.py patch targets | `grep -cE "list_platforms_core\|..." tests/v2/test_cache.py` | 0 |
| Filesystem: streamlit_app.py absent | `test ! -e streamlit_app.py` | PASS |
| Filesystem: app/pages absent | `test ! -d app/pages` | PASS |
| Filesystem: app/components absent | `test ! -d app/components` | PASS |
| Filesystem: tests/pages absent | `test ! -d tests/pages` | PASS |
| Filesystem: config/auth.yaml absent | `test ! -e config/auth.yaml` | PASS |
| Dependency audit | `grep -E "^streamlit\b\|..." requirements.txt` | 0 hits |
| App import smoke test | `python -c "import app_v2.main; print('ok')"` | ok |
| Full pytest suite | `pytest tests/ -q` | 505 passed, 2 skipped |
| Doc audit: FastAPI in PROJECT.md | `grep -q "FastAPI" PROJECT.md` | PASS |
| Doc audit: FastAPI in CLAUDE.md | `grep -q "FastAPI" CLAUDE.md` | PASS |
| Doc audit: no "Streamlit website" | `! grep -q "Streamlit website" PROJECT.md` | PASS |

## Test Count

| | Count |
|--|-------|
| Before (v2.0 tag) | 506 |
| After this task | 507 (505 passed + 2 skipped) |
| Delta | +1 (new `test_ufs_service.py` adds more pivot + fetch_cells purity tests than the two old files combined) |

## Critical Preserves Confirmed

Per the D-22 keep-list and constraint spec, all of the following still exist:
- `app/core/agent/nl_service.py`
- `app/core/agent/nl_agent.py`
- `app/adapters/llm/pydantic_model.py`
- `app/core/config.py`
- `app/services/{result_normalizer,sql_validator,sql_limiter,path_scrubber,ollama_fallback}.py`
- All of `app/adapters/`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_pivot_to_wide_caps_at_30_columns assertion**
- **Found during:** Task 2, pytest run
- **Issue:** Test used `col_cap=2` against a fixture with exactly 2 value columns — no capping triggered, `capped=False`
- **Fix:** Changed to `col_cap=1` (1 cap < 2 available value columns → triggers cap correctly)
- **Files modified:** `tests/services/test_ufs_service.py`

**2. [Rule 2 - Observation] @st.cache_resource mention in ask.py docstring is documentation, not a decorator**
- **Found during:** Task 5 Step 5.2 grep audit
- **Issue:** `grep -rE "@st\."` matched a docstring line `\`\`get_nl_agent\`\` \`@st.cache_resource\` pattern` in `app_v2/routers/ask.py`
- **Decision:** Not an active decorator — the anchor `^\s*@st\.` (line-start) confirms it is documentation text. Left in place as historical reference.

## Suggested Next User Action

Tag `v2.1` (Streamlit Sunset milestone) when ready:

```bash
git tag -a v2.1 -m "v2.1: Streamlit shell sunset — FastAPI + Bootstrap + HTMX is the single UI"
git push origin v2.1
```

## Self-Check

## Self-Check: PASSED

All key files verified present on disk. All 4 task commits verified in git log:
- `511f1cb` — Task 1: delete v1.0 Streamlit UI surface
- `d247cbd` — Task 2: drop *_core suffix from ufs_service
- `573b7fa` — Task 3: drop 4 deps from requirements.txt
- `7266e00` — Task 4: rewrite project framing as FastAPI
