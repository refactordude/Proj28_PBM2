---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Bootstrap Shell — Active
status: executing
stopped_at: Completed 05-01-PLAN.md (PROJECT.md subsection + picker_popover macro D-OV-06 parameterization)
last_updated: "2026-04-28T06:52:07.127Z"
last_activity: 2026-04-28
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 24
  completed_plans: 19
  percent: 79
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-25)

**Core value:** Fast ad-hoc browsing of the UFS parameter database — even if NL fails, the UI lets non-SQL users find platforms, compare parameters, chart, and export
**Current focus:** Phase 05 — overview-redesign

## Current Position

Phase: 05 (overview-redesign) — EXECUTING
Plan: 2 of 6
Status: Ready to execute
Last activity: 2026-04-28

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
- 04-01: v2.0 Browse is view-only by design (D-19..D-22) — BROWSE-V2-04 (Excel/CSV export) removed from REQUIREMENTS / ROADMAP / PROJECT. Phase 4 scope locked to BROWSE-V2-01, BROWSE-V2-02, BROWSE-V2-03, BROWSE-V2-05 (4 reqs + 3 success criteria). v1.0 Streamlit Browse remains the export surface until v1.0 sunset; v1.0's app/components/export_dialog.py is NOT touched, copied, or imported by app_v2/.
- 04-01: BROWSE-V2-01 `/?tab=browse` alias trimmed (Issue 1 plan-checker fix) — primary `/browse` path covers the requirement. No Phase 4 plan implements the alias as a 302 redirect.
- 04-01: REQUIREMENTS.md Totals reconciled to 45 v2.0 reqs (Phase 4 mapped count = 4); PROJECT.md Key Decisions table now contains the "Drop v2.0 Browse export to keep the port view-only" row with `⚠️ Revisit at v1.0 sunset planning` status.
- 04-01: 4 Rule-1 doc-bug fixes applied beyond literal plan body (Phase 4 summary line + Phase 4 Goal + plan-list narrative in ROADMAP.md; v2.0 milestone target features in PROJECT.md) — kept upstream docs internally consistent post-trim. Project intro paragraph and v1.0 milestone Excel claim preserved verbatim per plan directives.
- 04-02: BrowseViewModel single-orchestrator pattern — `build_view_model` is the ONE source of truth consumed by both GET /browse (full-page) and POST /browse/grid (block_names fragment). Routes only differ at the Jinja2 layer. Pure-Python service module — no FastAPI/Starlette imports inside `app_v2/services/browse_service.py`.
- 04-02: PARAM_LABEL_SEP=' · ' (UTF-8 bytes b' \xc2\xb7 ') with surrounding spaces is the SINGLE source of truth for InfoCategory/Item label format (D-13). Garbage labels silently dropped via `_parse_param_label` returning None — empty strings never reach SQL bind (T-04-02-02 mitigation).
- 04-02: ROW_CAP=200 / COL_CAP=30 module-level constants on `browse_service.py` (D-23) — not hardcoded in routes. `pivot_to_wide_core` reused unmodified for aggfunc='first' (D-29). `fetch_cells` (TTLCache wrapper) called with `row_cap=ROW_CAP` and `db_name` keyword.
- 04-02: Pydantic v2.13.x + FastAPI 0.136.x reject `Query(default_factory=list)` AND literal '= []' default together (TypeError: cannot specify both default and default_factory). Use `default_factory` only for GET query params; POST `Form()` params keep '= []' (Pydantic accepts Form with literal default). Plan acceptance grep regex still matches the canonical idiom.
- 04-02: browse router registered BEFORE root in main.py (lines 145-155) — defense-in-depth ordering. Even if a future commit accidentally re-adds a /browse stub to root.py, the real browse router still wins. Phase 1 stub-test in test_main.py marked `@pytest.mark.skip` with tombstone reason pointing to Plan 04-03 (templates) and Plan 04-04 (integration tests).
- 04-02: POST /browse/grid sets HX-Push-Url response header to canonical /browse?... URL composed via `urllib.parse.urlencode(..., quote_via=urllib.parse.quote)` for %20 spaces (Pitfall 6) — NOT the form-style + that urlencode emits by default. Address bar shows shareable URL, not the POST URL (which would 405 on reload, Pitfall 2).
- 04-02: build_view_model accepts db=None gracefully — returns fully-empty BrowseViewModel without DB call. Phase 1 lifespan contract permits no-database startup; route stays responsive. Catalog calls (`list_platforms`/`list_parameters`) ALWAYS run on non-None db so popovers render full lists; only `fetch_cells` (the SQL hit) is gated by the empty-selection short-circuit.
- 04-03: 6 Jinja templates + 79-line popover-search.js + 53-line Phase 04 CSS append + 1-line base.html script wire-up. Issue 5 fix in `_grid.html` — `<tbody>` rows mirror `<thead>` structure (index cell explicit FIRST, then non-index loop) so header/body parity does NOT depend on pandas df_wide.columns order. Defense-in-depth `| e` on every dynamic Jinja2 output (autoescape + explicit filter). OOB count caption lives in `.panel-header` outside `#browse-grid` so OOB swap target is stable (Pitfall 7). Empty `<form id="browse-filter-form">` placed BEFORE filter-bar include so picker checkboxes inside dropdown menus participate via form= attribute (Pitfall 4).
- 04-04: 12 end-to-end TestClient integration tests + 13 static-analysis invariant guards. Issue 2 fix VERIFIED — garbage-params test introspects `mock_fetch_cells.call_args` and asserts `items` and `infocategories` tuples are empty when URL carries a label without ` · ` separator (proves `_parse_param_label` filtered it out before SQL bind, NOT a tautological assertion).
- 04-04: httpx 0.28 dropped list-of-tuples support on `data=` (raises TypeError: sequence item 0: expected a bytes-like object, tuple found). Helper `_post_form_pairs(client, url, pairs)` uses `urllib.parse.urlencode` + `content=body` + explicit `Content-Type: application/x-www-form-urlencoded` — supported escape hatch for repeated form keys. Future tests for routes consuming `Annotated[list[str], Form()]` reuse this helper.
- 04-04: Two-plane SQLi/XSS test pattern — POST `/browse/grid` verifies the injection string flows to `fetch_cells` as a literal tuple element (SQLi defense via `sa.bindparam(expanding=True)`); GET `/browse` verifies the SAME string is HTML-escaped in the picker checkbox `value=` attribute (XSS defense via Jinja2 autoescape + explicit `| e`). Single test exercises both attack surfaces with one injection string.
- 04-04: Static-analysis tests construct forbidden literals at runtime (`'"' + ' / ' + '"'`, `"/browse/" + "export"`, `"| " + "safe"`) so the test file ITSELF does not contain the substring it scans for under `app_v2/`. Eliminates self-match false-positive risk; no carve-out logic needed.
- 04-04: 4 deviations — 1 Rule-3 (httpx 0.28 form encoding), 3 Rule-1 acceptance compliance (SQLi test split into POST+GET planes; tautological-literal docstring rephrase in test_browse_routes.py; v1.0-slash-separator literals removed from browse_service.py docstrings). Same pattern as Plan 04-02 / 04-03 deviations 3-4. Zero scope creep, zero behavior change in production code.
- 04-05: gap-2 closed via single-attribute fix in `_picker_popover.html` — Apply button now carries `form="browse-filter-form"` (mirrors Swap-axes pattern in `_filter_bar.html` line 38); broken `hx-include="#browse-filter-form input:checked"` CSS-descendant selector removed. HTMX's dn()/Nt() resolves element.form for non-GET requests and iterates form.elements (browser DOM API enumerates all form-associated controls regardless of DOM tree position). 2 regression tests added to `tests/v2/test_browse_routes.py` (smoke + recording-mock end-to-end) — file now has 14 tests. Full v2 suite green (272 passed, 1 skipped). Zero Python production-code changes — `git diff --quiet HEAD~2 -- routers/services/adapters/index.html/_filter_bar.html` returns 0. Plan executed exactly as written; zero deviations.
- 04-06: gap-3 closed via Candidate A (server-side OOB) — extended count_oob/warnings_oob OOB pattern with new `picker_badges_oob` block in `app_v2/templates/browse/index.html` emitting two `hx-swap-oob="true"` spans (id="picker-platforms-badge", id="picker-params-badge") on every POST /browse/grid. Trigger badge in `_picker_popover.html` now uses stable id + d-none for visibility (instead of conditional emit) so HTMX has a permanent merge target while D-08's "no badge when empty" visual contract is preserved. `block_names` extended 3 → 4 with "picker_badges_oob"; one-line router change. 2 regression tests added to `tests/v2/test_browse_routes.py` (non-empty: counts + visible; empty: stable target hidden via d-none) — file now has 16 tests. Full v2 suite green (274 passed, 1 skipped, up from 272). Production-code invariance: zero changes to services / adapters / popover-search.js / app.css / _filter_bar.html / _grid.html / _warnings.html / _empty_state.html / Phase 4 invariants. D-14 (a + b + c) now fully demonstrable end-to-end on a single Apply click. Plan executed exactly as written; zero deviations.
- 04-07: gap-4 closed via D-15a (locked) close-event taxonomy in popover-search.js. Capture-phase document keydown listener (`addEventListener('keydown', onKeydown, true)`) sets `dataset.cancelling=1` on Esc BEFORE Bootstrap fires `hide.bs.dropdown`; `onDropdownHide` branches across 4 paths — (i) explicit Apply already ran, (ii) Esc-cancel revert from `data-original-selection`, (iii) no-op short-circuit when current sorted selection deep-equals stash via new `_selectionsEqual` helper, (iv) implicit Apply via `popoverApplyBtn.click()` reusing the existing Apply button's full HTMX wiring with zero divergence (gap-2 form-association + gap-3 picker_badges_oob OOB swap inherited automatically). Bootstrap's `e.clickEvent` is null on BOTH Esc and programmatic close — the keydown trick is the canonical workaround. No visual cue distinguishes implicit-Apply from explicit-Apply (D-08 preserved); grid + trigger badge swap is the affordance. 2 server-side regression tests added (`test_post_browse_grid_implicit_apply_payload_shape`, `test_post_browse_grid_idempotent_unchanged_selection`) + 1 Phase 4 invariant (`test_popover_search_js_implements_d15a_close_event_taxonomy`) grep-guarding 5 JS source markers + the `data-bs-auto-close="outside"` template precondition. Suite 274 → 277 passing. 1 Rule-1 deviation: initial JS used `.picker-*` selectors / native `<div popover>` semantics; fixup commit aligned to `.popover-*` selectors / Bootstrap dropdown event model per the plan's `<interfaces>` section. All 4 gaps in 04-HUMAN-UAT.md now resolved (gap-1, gap-2, gap-3, gap-4); ready for UAT replay.
- 05-01: D-OV-06 picker_popover macro parameterization expanded — macro signature now `picker_popover(name, label, options, selected, form_id="browse-filter-form", hx_post="/browse/grid", hx_target="#browse-grid")`; 3 additive kwargs preserve Phase 4 byte-stability via defaults while enabling Plan 05-05 to call with `form_id="overview-filter-form"`, `hx_post="/overview/grid"`, `hx_target="#overview-grid"` on a single shared macro (no fork). Body uses `{{ form_id }}`, `{{ hx_post }}`, `{{ hx_target }}`, `#{{ form_id }}` substitutions in 4 places (1 ul tag with 3 attrs + 1 checkbox form= attr).
- 05-01: Phase 4 invariant `test_picker_popover_uses_d15b_auto_commit_pattern` markers 2/3/4b migrated from template-source grep to rendered-macro grep — preserves D-15b enforcement while accommodating the parameterized macro. Pattern: when a template invariant guards a contract satisfied by Jinja substitution at render-time (not template authorship), render the macro with the contract's reference inputs (Phase 4 default kwargs) and grep the rendered output. Defense-in-depth strengthened — now proves macro defaults match the Phase 4 contract end-to-end. Reusable pattern for any future v2.0 macro that gains kwargs.
- 05-01: PROJECT.md Active section now has Overview redesign (v2.0) subsection (6 bullets covering OVERVIEW-V2-01..06) inserted between Browse — v2.0 Validated block and Ask carry-over (v2.0) Active block — closes CONTEXT.md upstream-edit-3.

### Pending Todos

- `/gsd-verify-phase 4` — run Phase 4 verifier
- `/gsd-uat-phase 4` — Phase 4 UAT against running app
- Execute Phase 5 (ask-tab-nl-agent) when Phase 4 verification passes

### Blockers/Concerns

None — roadmap complete, 45 v2.0 requirements mapped (Phase 4 trimmed per D-19..D-22). Research gaps noted in SUMMARY.md for phases 2, 3, 5.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260427-uoh | Add SQLite DB adapter and demo data seeder for Phase 4 UAT testing | 2026-04-27 | 43e51e1 | [260427-uoh-add-sqlite-db-adapter-and-demo-data-seed](./quick/260427-uoh-add-sqlite-db-adapter-and-demo-data-seed/) |

## Session Continuity

Last session: 2026-04-28T06:52:07.108Z
Stopped at: Completed 05-01-PLAN.md (PROJECT.md subsection + picker_popover macro D-OV-06 parameterization)
Resume file: None
Next action: `/gsd-verify-phase 4` to verify Phase 4 (browse-tab-port) completion
