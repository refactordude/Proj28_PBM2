---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Bootstrap Shell — Active
status: executing
stopped_at: Completed 03-01-PLAN.md
last_updated: "2026-04-25T13:56:11.739Z"
last_activity: 2026-04-25
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 11
  completed_plans: 8
  percent: 73
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-25)

**Core value:** Fast ad-hoc browsing of the UFS parameter database — even if NL fails, the UI lets non-SQL users find platforms, compare parameters, chart, and export
**Current focus:** Phase 03 — content-pages-ai-summary

## Current Position

Phase: 03 (content-pages-ai-summary) — EXECUTING
Plan: 2 of 4
Status: Ready to execute
Last activity: 2026-04-25

Progress: [██████████] 100%

## Accumulated Context

### Decisions (v2.0 locked)

- Stack: FastAPI 0.136.x + Bootstrap 5.3.8 + HTMX 2.0.10 + Jinja2 + jinja2-fragments + markdown-it-py 4.x
- Scope: v2.0 is a parallel rewrite — v1.0 Streamlit code stays archived in `app/`; v2.0 lives in `app_v2/`
- Tabs (horizontal, top nav): Overview / Browse / Ask
- Entities on Overview = user-curated favorites (subset of PLATFORM_IDs from ufs_data), each with title + metadata badges + link + AI Summary button
- Filters: Brand / SoC / Year facets parsed from PLATFORM_ID + "has content page" toggle; all HTMX-swapped
- Content pages: markdown files at `content/platforms/<PLATFORM_ID>.md`, addable/editable/deletable via HTMX forms, rendered with `MarkdownIt("js-default")` (XSS-safe)
- AI Summary: reuses v1.0 LLM adapter (single-shot completion on the content markdown), HTMX in-place swap, TTLCache keyed by (platform_id, content_mtime, llm_name, llm_model)
- Browse tab: re-renders v1.0 pivot/swap-axes/caps/export under Bootstrap tables
- Ask tab: carries v1.0 NL agent (PydanticAI + dual OpenAI/Ollama + SAFE harness) forward under new UI; all routes go through nl_service.run_nl_query()
- Reuse: framework-agnostic v1.0 modules (result_normalizer, nl_agent, sql_validator/limiter/scrubber, build_pydantic_model, config models) imported, not copied
- Pre-work gates (Phase 1): ufs_service.py @st.cache_data → _core() extraction; nl_service.py safety harness extraction — both must pass 171 v1.0 tests before any app_v2/ code is written
- Auth: still deferred per v1.0's D-04 pattern; config/auth.yaml stays gitignored
- HTMX 4.0 is alpha — stay on 2.0.10
- All DB-touching FastAPI routes must be `def` (not `async def`) — FastAPI dispatches to threadpool; sync SQLAlchemy cannot be called inside async def
- cachetools TTLCache always paired with threading.Lock(); key lambda excludes unhashable db adapter object
- PLATFORM_ID path param validated with regex `^[A-Za-z0-9_\-]{1,128}$` + Path.resolve() prefix assertion before any file I/O
- Markdown rendered with MarkdownIt("js-default") — never the default constructor (html=True causes XSS)
- Pool sizes during parallel deployment: pool_size=2, max_overflow=3 on both apps to avoid MySQL max_connections exhaustion
- Cache wrapper names: list_platforms/list_parameters/fetch_cells (not cached_ prefix) — Phase 2+ imports from app_v2.services.cache
- TTL expiry test patches _Timer__timer (name-mangled inner callable) — cachetools v7 makes TTLCache.timer a read-only property
- Per-cache threading.Lock instances (not shared) — reduces contention under concurrent route access
- list_platforms called unconditionally (try/except) in overview routes — monkeypatch works in tests without real DB; production degrades to empty datalist
- Phase 1 GET / stub removed from root.py; overview router owns /; root.py retains /browse and /ask only
- 02-03: year filter normalization accepts str/int; unparseable strings map to sentinel year_int=-1 producing zero matches (safer than ignoring filter)
- 02-03: has_content_file uses Path.resolve() + Path.relative_to() (Pitfall 2 defense); ValueError is the documented traversal signal
- 02-03: CONTENT_DIR is module-level Path constant on app_v2.routers.overview (tests monkeypatch it); service stays pure with content_dir injected
- 02-03: POST /overview/filter/reset is stateless — no server-side filter selection cache; route returns unfiltered list with active_filter_count=0
- 03-01: atomic_write_bytes shared helper extracted (D-30) — overview_store and content_store both delegate to `app_v2/data/atomic_write.py`; default_mode parameter (0o644 default; 0o666 for overview YAML to preserve umask-applied 0o644)
- 03-01: llm_resolver shared module (Q2 RESOLVED) — `app_v2/services/llm_resolver.py` exposes resolve_active_llm + resolve_active_backend_name; eliminates 3-way duplication of inline _resolve_* helpers across overview/platforms/summary routers (Plans 03-02 / 03-03 consume)
- 03-01: Pitfall-18 deviation (RESEARCH.md Q3) — NO Ollama warmup ping in lifespan; rely solely on summary_service 60s read timeout (rationale comment in main.py makes the deviation auditable)
- 03-01: Dashboard CSS tokens.css + app.css wired in base.html — tokens BEFORE app for var(--*) ordering; .ai-btn / .panel / .markdown-content / .nav-pills overrides available globally for Phase 03 templates
- 03-01: Gitignore rescue rules for content/ — bare `content/` rule short-circuits descent; added `!content/` + `!content/platforms/` + `content/platforms/*` so the `!content/platforms/.gitkeep` negation actually applies (Rule-1 plan bug fix; deviation documented in 03-01-SUMMARY.md)

### Pending Todos

- Run `/gsd-plan-phase 1` to create the execution plan for Phase 1 (Pre-work + Foundation)

### Blockers/Concerns

None — roadmap complete, all 46 requirements mapped, research gaps noted in SUMMARY.md for phases 2, 3, 5.

## Session Continuity

Last session: 2026-04-25T13:56:11.694Z
Stopped at: Completed 03-01-PLAN.md
Resume file: None
Next action: `/gsd-plan-phase 1`
