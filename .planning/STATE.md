---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Bootstrap Shell — Active
status: verifying
stopped_at: Completed 03-04-PLAN.md
last_updated: "2026-04-25T21:16:50.223Z"
last_activity: 2026-04-25
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 11
  completed_plans: 11
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-25)

**Core value:** Fast ad-hoc browsing of the UFS parameter database — even if NL fails, the UI lets non-SQL users find platforms, compare parameters, chart, and export
**Current focus:** Phase 03 — content-pages-ai-summary (COMPLETE)

## Current Position

Phase: 03 (content-pages-ai-summary) — COMPLETE
Plan: 4 of 4 (all four delivered)
Status: Phase complete — ready for verification
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
- 03-02: content_store stays content_dir-injected (pure); routes hold the single CONTENT_DIR module-level constant tests monkeypatch — service module reusable for any future caller (CLI dump, Plan 03-03 summary)
- 03-02: pathlib alias pattern (`from pathlib import Path as _Path`) mirrors overview.py:18 to avoid collision with fastapi.Path; module-level path-typed constants reference `_Path`
- 03-02: data-cancel-html stash via `templates.env.get_template().render(ctx)` + Jinja2 `| e` autoescape — D-10 client-side Cancel without server round-trip; T-03-02-04 attribute injection blocked
- 03-02: path traversal hardened at TWO layers — FastAPI `Path(pattern=...)` at HTTP entry returns 422; `content_store._safe_target` Path.resolve()+relative_to() at filesystem boundary; 15 parametrized tests (3 attacks × 5 routes)
- 03-02: standalone `disabled` HTML attribute coexists with `hx-disabled-elt="this"` on the AI button — `disabled` blocks click natively when no content file (D-13); hx-disabled-elt is for in-flight loading state when enabled
- 03-02: `_entity_dict` enriched with `has_content` (computed via `has_content_file(pid, CONTENT_DIR)`) — drives Phase 03 .ai-btn enable/disable replacing the Phase 02 disabled stub
- 03-02: backend_name (D-19 default 'Ollama') threaded through every overview-context-builder + per-row entity_row template via shared llm_resolver — single source of truth across overview/platforms
- 03-03: ALWAYS-200 contract for summary route — every error returns the amber-warning fragment with HTTP 200 (UI-SPEC mandate); HTMX swap lands inline in #summary-{pid}, never escalating to global #htmx-error-container
- 03-03: cache key uses hashkey(pid, mtime_ns, llm_name, llm_model) — mtime_ns (int) NOT mtime (float) per Pitfall 13; lock guards only dict get/set (NEVER held during LLM call) per Pitfall 11 — explicit smoke test verifies non-blocking acquire from inside chat.completions.create side_effect
- 03-03: 8th error vocabulary entry "LLM not configured — set one in Settings" added at the route level (resolve_active_llm returning None gates this BEFORE _classify_error). UI-SPEC §8c's 7 entries all assume a backend exists; the empty-settings.llms case needs its own copy
- 03-03: APITimeoutError ordered BEFORE APIConnectionError in _classify_error — APITimeoutError is a subclass of APIConnectionError in openai 2.x, so reversing would misclassify every timeout. Comment in classifier documents the constraint
- 03-03: `_build_client(cfg)` factory dispatches on cfg.type — Ollama (base_url=…/v1, api_key="ollama", 60s timeout) vs OpenAI (api_key from cfg or OPENAI_API_KEY env, 30s timeout). Pitfall 18 deviation comment in both summary_service.py and main.py
- 03-03: summary route NEVER imports `pathlib.Path` — collides with `fastapi.Path` (path-parameter validator); reaches pathlib paths transitively via `platforms_router.CONTENT_DIR`. Module docstring documents the choice; acceptance criterion enforces
- 03-04: Cross-process race test (D-24) uses fork-only POSIX semantics with module-top-level `_save_in_worker` (A5 picklability constraint). `@pytest.mark.slow` + `@pytest.mark.skipif(sys.platform == "win32")` keeps Windows CI green while Linux/macOS runs the real fork test. 3 explicit assertions verified on Linux ext4: file content equals one of two payloads in full (no hybrid), no leftover `.{pid}.md.*.tmp` tempfile, file mode is 0o644.
- 03-04: `tests/v2/conftest.py` registers the `slow` pytest marker via `pytest_configure` + `addinivalue_line` — directory-scoped registration avoids creating a project-level `pyproject.toml [tool.pytest.ini_options]` section. `-m "not slow"` opt-out works equivalently.
- 03-04: Per-call MagicMock response queue uses a closure with index list (`idx = [0]; idx[0] += 1`) to drive stateful `side_effect` — `type(r)()` cloning fails because MagicMock instances are not callable as types; closure pattern is the canonical pytest-mock idiom.
- 03-04: `test_summary_route_never_returns_5xx` uses `\braise\s+HTTPException\b` (word-boundary regex) so the docstring phrase "NEVER raises HTTPException" cannot trigger a false-positive on the static guard.
- 03-04: `test_no_banned_libraries_imported_in_app_v2` anchors `^\s*(import|from)\s+<lib>\b` so docstring/comment occurrences cannot trip the guard — only actual import statements at line start (with optional indent) are checked. Parametrized over langchain, litellm, vanna, llama_index per CLAUDE.md "What NOT to Use".
- 03-04: Integration fixture replaces `app.state.settings = Settings(...)` AFTER lifespan ran (mirrors `test_summary_routes.py::isolated_summary` proven pattern) instead of mutating sub-attributes — robust against future Pydantic v2 `frozen=True` schema tightening.
- 03-04: Codebase-level static-analysis grep guards as automated CI policy enforcement — pattern reusable in Phase 04+ for any locked decision (INFRA-05, Pitfall 1, UI-SPEC contracts, banned libs, D-numbers, atomic_write_bytes single-source-of-truth).

### Pending Todos

- Run `/gsd-plan-phase 1` to create the execution plan for Phase 1 (Pre-work + Foundation)

### Blockers/Concerns

None — roadmap complete, all 46 requirements mapped, research gaps noted in SUMMARY.md for phases 2, 3, 5.

## Session Continuity

Last session: 2026-04-25T21:16:50.203Z
Stopped at: Completed 03-04-PLAN.md
Resume file: None
Next action: `/gsd-plan-phase 1`
