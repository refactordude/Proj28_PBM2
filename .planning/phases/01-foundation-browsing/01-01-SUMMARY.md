---
phase: 01-foundation-browsing
plan: "01"
subsystem: infra
tags: [streamlit, sqlalchemy, pymysql, pandas, pydantic, gitignore, requirements]

# Dependency graph
requires: []
provides:
  - .gitignore excluding config/auth.yaml, config/settings.yaml, .env (FOUND-02, T-01-01/02/03)
  - .streamlit/config.toml with UI-SPEC theme tokens (primaryColor #1f77b4, light base)
  - requirements.txt with tightened pins: sqlalchemy<2.1, pydantic-ai>=1.0,<2.0, pandas>=3.0
  - MySQLAdapter with pool_recycle=3600, pool_pre_ping=True, pd.read_sql_query (FOUND-06, SAFE-01)
  - streamlit_app.py entrypoint: load_dotenv, set_page_config, st.navigation, shared sidebar
  - app/pages/browse.py and app/pages/settings.py placeholder stubs for st.navigation
affects: [01-02, 01-03, 01-04, 01-05, 01-06, 01-07]

# Tech tracking
tech-stack:
  added:
    - pydantic-ai>=1.0,<2.0 (added to requirements.txt)
  patterns:
    - st.cache_resource for DBAdapter factory keyed by db_name string
    - load_dotenv() called before any Streamlit/settings code
    - Sidebar renders only entrypoint-level widgets; page-level widgets stay in page files
    - Health indicator with 60-second TTL via st.session_state timestamp check
    - pool_pre_ping=True + pool_recycle=3600 for MySQL connection stability

key-files:
  created:
    - .gitignore
    - .streamlit/config.toml
    - streamlit_app.py
    - app/pages/__init__.py
    - app/pages/browse.py
    - app/pages/settings.py
  modified:
    - requirements.txt
    - app/adapters/db/mysql.py

key-decisions:
  - "D-04 honored: streamlit-authenticator not imported anywhere in Phase 1; config/auth.yaml stays gitignored regardless"
  - "D-03 implemented: sidebar has DB selector (multi/single/empty cases), inert LLM selector with Phase 2 hint caption, health indicator dot with 60s TTL"
  - "D-01 implemented: st.navigation with Browse (default=True) + Settings; Ask page slot commented out for Phase 2"
  - "Multiline st.Page(...) format used for readability; functionally equivalent to single-line"

patterns-established:
  - "Pattern: @st.cache_resource factory get_db_adapter(db_name: str) — all downstream plans reuse this for DB access"
  - "Pattern: load_dotenv() at module top of streamlit_app.py before any env-dependent imports"
  - "Pattern: render_sidebar(settings) function owns only global sidebar widgets; page files own their own sidebar additions"

requirements-completed:
  - FOUND-02
  - FOUND-04
  - FOUND-05
  - FOUND-06
  - FOUND-08
  - SAFE-01

# Deferred requirements (per D-04 — no Phase 1 code produced)
requirements-deferred:
  - FOUND-01  # login page — deferred per D-04 (auth skipped in Phase 1)
  - FOUND-03  # cookie-key startup guard — deferred per D-04 (auth skipped in Phase 1)

# Metrics
duration: 2min
completed: "2026-04-23"
---

# Phase 01 Plan 01: Scaffolding Foundation Summary

**Streamlit entrypoint with st.navigation, shared sidebar (DB/LLM/health), corrected MySQLAdapter (pool_recycle=3600, pd.read_sql_query), and gitignore secrets exclusion**

## Performance

- **Duration:** ~2 minutes
- **Started:** 2026-04-23T19:06:21Z
- **Completed:** 2026-04-23T19:08:52Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- `.gitignore` excludes all secret config files (config/auth.yaml, config/settings.yaml, .env) — FOUND-02 and threat mitigations T-01-01/02/03 closed
- `.streamlit/config.toml` wires the UI-SPEC theme tokens (primaryColor #1f77b4, light base, secondary #f0f2f6)
- `requirements.txt` tightened: added upper bounds on sqlalchemy/streamlit, bumped pandas to >=3.0, added pydantic-ai>=1.0,<2.0
- `MySQLAdapter` fixed: pool_recycle 1800→3600 (FOUND-06), pd.read_sql→pd.read_sql_query (pandas 3.x idiom), SAFE-01 preserved
- `streamlit_app.py` entrypoint: load_dotenv, set_page_config, @st.cache_resource adapter factory, shared sidebar (DB/LLM/health), st.navigation (Browse default + Settings), Phase 2 Ask slot commented out
- `app/pages/browse.py` and `app/pages/settings.py` created as placeholder stubs so st.navigation has valid targets

## Task Commits

Each task was committed atomically:

1. **Task 1: Create .gitignore and .streamlit/config.toml** — `ca3106a` (chore)
2. **Task 2: Tighten requirements.txt and fix MySQLAdapter** — `5d0089c` (fix)
3. **Task 3: Create streamlit_app.py entrypoint** — `5adc133` (feat)

## Files Created/Modified

- `.gitignore` — Git exclusions for secrets (config/auth.yaml, config/settings.yaml, .env) and Python/OS artifacts
- `.streamlit/config.toml` — Streamlit theme tokens per UI-SPEC (primaryColor #1f77b4, light base)
- `requirements.txt` — Tightened pins: sqlalchemy<2.1, pandas>=3.0, pydantic-ai>=1.0,<2.0 added
- `app/adapters/db/mysql.py` — pool_recycle=3600, pd.read_sql_query, SET SESSION TRANSACTION READ ONLY preserved
- `streamlit_app.py` — Streamlit entrypoint (load_dotenv, set_page_config, get_db_adapter cache, sidebar, navigation)
- `app/pages/__init__.py` — Package init for Streamlit pages
- `app/pages/browse.py` — Placeholder stub for Browse page (Plans 05+06 will replace)
- `app/pages/settings.py` — Placeholder stub for Settings page (Plan 04 will replace)

## Decisions Made

- D-04 honored: `streamlit-authenticator` not imported anywhere; `config/auth.yaml` stays gitignored for when auth is re-enabled in a pre-deployment phase
- D-03 sidebar: DB selector has three cases (multi-DB selectbox, single-DB caption, zero-DB warning); LLM selector shows Phase 2 hint caption; health indicator uses inline-styled Unicode dot with 60-second TTL cache via `st.session_state` timestamp
- D-01 navigation: Browse is `default=True`; Settings is second entry; NL Ask page commented out with `# Phase 2 — uncomment when NL agent is wired` marker

## Deviations from Plan

None — plan executed exactly as written. All three tasks completed per specification without requiring auto-fixes.

**FOUND-01 and FOUND-03 deferral note:** These requirements are listed in the plan's frontmatter `requirements` field but produce no Phase 1 code per D-04. Recorded in `requirements-deferred` in this SUMMARY's frontmatter so the traceability table in REQUIREMENTS.md can be updated at phase close.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required for this plan. `config/settings.yaml` must be created by the user (copy from `config/settings.example.yaml` and fill in DB/LLM credentials) before the app can successfully connect to MySQL.

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| `st.info("Browse UI will be implemented in Plans 05 and 06.")` | `app/pages/browse.py` | Intentional placeholder — full Browse UI implemented in Plans 05 and 06 |
| `st.info("Settings UI will be implemented in Plan 04.")` | `app/pages/settings.py` | Intentional placeholder — full Settings UI implemented in Plan 04 |

These stubs are intentional by plan design. They do not prevent this plan's goal (runnable entrypoint with navigation scaffolding) from being achieved.

## Next Phase Readiness

- Plan 01-02 (result normalizer) can proceed immediately — no dependencies on this plan's files beyond `app/core/config.py` (pre-existing)
- All downstream plans can import `get_db_adapter` from `streamlit_app.py` or build their own via `build_adapter(cfg)` from `app/adapters/db/registry.py`
- The `streamlit run streamlit_app.py` entrypoint is functional; Browse and Settings stubs will be replaced by Plans 04, 05, 06

---
*Phase: 01-foundation-browsing*
*Completed: 2026-04-23*
