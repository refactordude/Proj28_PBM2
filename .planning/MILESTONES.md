# Milestones

## v2.2 — JV+UI+Chat+UI-Foundation cycle (Shipped: 2026-05-03)

_Internal gsd-tools name: "v1.0" — this is the post-v2.1 cycle, not the original v1.0 MVP shipped 2026-04-24._

**Phases completed:** 4 phases, 20 plans, 44 tasks

**Key accomplishments:**

- BS4 4.14.3 + lxml 6.1.0 added to requirements.txt; summary/_success.html + _error.html rebound from hardcoded platform_id to generic entity_id + summary_url so Plan 04's /joint_validation/{cid}/summary route can reuse the same partials with no fork.
- Three-module data-extraction core for the Joint Validation tab: BS4 parser handling both Page Properties macro and `<p><strong>Field</strong>: value</p>` shapes (10 tests), mtime-keyed discovery store (8 tests), and 12-column-sort + 6-filter grid view-model builder (12 tests) — 30 tests green; downstream Plans 03/04/05 unblocked.
- `_call_llm_with_text` extracted from `_call_llm_single_shot` as a backend-agnostic helper; new `joint_validation_summary` service implements the D-JV-16 BS4 decompose pipeline (`<script>`/`<style>`/`<img>` removed before `get_text(separator='\n')` so base64 image src never reaches the LLM) and a `get_or_generate_jv_summary` shim that reuses Phase 3's TTLCache + Lock with a `'jv'`-discriminated cache key — 14 new tests green; Phase 3 platform-summary path still passes 50/50 with zero regressions.
- Found during:
- Five templates rewired for Joint Validation: nav-label flipped (D-JV-01), three overview/ templates fully rewritten (12 sortable column headers, 6 popover-checklist filters, AI Summary modal), and a new joint_validation/detail.html with the locked 3-flag iframe sandbox attribute. Three atomic commits, 109 tests green across the direct-impact suites + 331 passed in the wider regression run; zero regressions.
- 9 files deleted (-2131 LOC) + 2 test files added (+588 LOC, 30 new tests) + 6 sibling files Rule-3-auto-fixed for orphan refs; full v2 test suite green at 360 passed / 5 skipped / 24s — Phase 5 curated-Platform Overview machinery is gone, the JV listing/detail/summary surface is route-tested + byte-pinned at the source level, and Browse/Ask/Platforms/Summary tabs are regression-safe.
- One-liner:
- One-liner:
- One-liner:
- One-liner:
- Foundation primitives for the multi-step Ask-chat overhaul: sse-starlette pin, AgentConfig.chat_max_steps (default=12), per-page extra_head Jinja block, and vendored htmx-ext-sse@2.2.4 + Plotly 2.35.2 bundles.
- Multi-step PydanticAI chat agent factory at `app/core/agent/chat_agent.py`: Pydantic schemas (ChartSpec, PresentResult, ChatAgentDeps), build_chat_agent factory, all 6 tools (inspect_schema, get_distinct_values, count_rows, sample_rows, run_sql, present_result), and `_execute_and_wrap` — the verbatim port of nl_agent.run_sql's SAFE-02..06 harness with the rejection prefix flipped to "REJECTED:" per D-CHAT-02.
- Wave 2 plumbing wrapping plan 02's chat agent: per-turn registry (asyncio.Event cancel + uuid4 turn_id) + per-session message_history store with D-CHAT-15 sliding window + D-CHAT-11 'both' path scrub on write; stream_chat_turn async generator driving agent.run_stream_events with all 4 stop boundaries (D-CHAT-01/02/03/04) and the WARNING-3 STRUCTURED-payload final contract; minimal app.state.chat_turns + chat_sessions documentation hooks on the v2.0 lifespan.
- Wave 3 atomic commit boundary (D-CHAT-09): rewrite app_v2/routers/ask.py end-to-end, atomically delete the 3 NL-05 templates and the Phase 6 invariants test file in the same commit, ship 8 new chat templates covering UI-SPEC §A–§I, append the Phase 3 chat-surface CSS block to app.css. The user-visible payload of Phase 3: navigating to /ask now shows the new chat shell.
- Final wave of Phase 03. Five new test files (62 tests total) lock the contracts of the multi-step agentic chat surface: D-CHAT-08 router shape, D-CHAT-09 atomic NL-05 cleanup, D-CHAT-10 starter chips removal, D-CHAT-11 LLM dropdown preservation, D-CHAT-01..04 stop-boundary classifications in chat_loop, D-CHAT-15 sliding-window in chat_session, the SM8850 vs SM8650 UNION-rejection motivating example, T-03-04-01/02 session-cookie ownership gates, and T-03-04-07 Plotly-only-on-/ask isolation. Phase 4 plotly invariant narrowed to whitelist `app_v2/routers/ask.py`. Three Rule-1/Rule-2 auto-fixes shipped along the way (TemplateResponse cookie propagation, AgentRunResultEvent discriminator, data-reason attribute on error card).
- Helix primitive CSS foundation appended to app.css (.topbar / .brand-mark / .ph / .hero / .kpis / .pop / .tiny-chip / .table-sticky-corner / .btn-helix and 35+ supporting selectors) plus Google Fonts loaded for Inter Tight 400-800 + JetBrains Mono 400-600
- 7 Jinja macro partials (topbar / page_head / hero / kpi_card / sparkline / date_range_popover / filters_popover) + 2 Pydantic v2 submodules (HeroSpec / FilterGroup) + chip-toggle.js sibling helper — every Phase 4 stateful primitive declared in UI-SPEC §New Jinja Macros + §Pydantic View-Models now ships under app_v2/templates/_components/ + app_v2/services/, all driven by the CSS foundation Wave 1 already laid down
- Atomic shell integration: replaced the legacy `<nav class="navbar">` block in base.html (~30 lines) with a single `{{ topbar(active_tab=...) }}` macro call, loaded chip-toggle.js with defer after popover-search.js, removed the dead `.navbar { padding: 16px 0 }` CSS rule, and rewrote the four test assertions that pinned legacy `nav-tabs` / `navbar-brand` literals onto the new `.topbar` / `.brand` / `.brand-mark` / `aria-selected="true"` shape — all in a single commit so the working tree was never half-broken.
- Mounted always-on `/_components` showcase route exercising every Helix primitive, plus 50 invariant tests pinning class names, dimensions, sparkline edge cases, and the BLOCKER 2 hyphen-safe filter-group assertion.
- Wave 5 of Phase 04 — D-UIF-01 LOCKED rename path completion.

---

## v2.0 Bootstrap Shell (Shipped: 2026-04-29)

**Delivered:** Complete UX rewrite from Streamlit to FastAPI + Bootstrap 5 + HTMX with horizontal-tab shell, curated Overview, per-platform markdown content pages with in-place AI Summary, pivot-grid Browse, and NL-agent Ask — all backed by the v1.0 safety harness. v1.0 Streamlit Ask page deleted.

**Phases completed:** 6 phases, 30 plans, 65 tasks

**Stats:**

- Git range: `5adc133` (2026-04-24) → `bb584c7` (2026-04-29) over 6 days
- ~3,300 LOC Python in `app_v2/` + ~1,500 LOC Jinja templates + ~6,600 LOC tests
- Tests: 506 passing, 2 skipped (was 171 in v1.0 — 335 net new tests for v2.0)

**Key accomplishments:**

- **Phase 1 (Foundation):** FastAPI app + Bootstrap 5 + HTMX shell parallel to v1.0 Streamlit; `nl_service` extraction for framework-agnostic NL agent (INFRA-07); `cache.py` TTLCache wrappers replacing `@st.cache_data`; Dashboard `tokens.css` + `app.css` design system; vendored static assets (no CDN dependency).
- **Phase 2 (Overview + Filters):** Curated platform watchlist with `overview_store` YAML persistence; faceted Brand/SoC/Year filters via `popover-checklist.js`; HTMX-swapped add/remove/filter changes (no full page reload); `OverviewRow` view model.
- **Phase 3 (Content + AI Summary):** Per-platform markdown CRUD (GET/POST edit/POST preview/POST save/DELETE) with path-traversal hardening (regex + `relative_to`), MarkdownIt(`js-default`) XSS defense, 64KB size cap; AI Summary feature (TTLCache + threading.Lock + openai SDK single-shot, 7-string error vocabulary, always-200 contract, mtime_ns cache key); shared `llm_resolver` module.
- **Phase 4 (Browse Tab Port):** v1.0 pivot grid ported to Bootstrap; pure-Python `BrowseViewModel` orchestrator; sync `def` GET /browse + POST /browse/grid; `popover-search.js` + sticky-header CSS; `HX-Push-Url` URL round-trip for shareable links; gap-closure plans 04-05 + 04-06 fixed Apply form-association and picker badge OOB-swap.
- **Phase 5 (Overview Redesign):** Sortable Bootstrap table mirroring Browse pivot styling; YAML-frontmatter PM metadata (Title / Status / Customer / Model / AP Company / AP Model / Device / Controller / Application / 담당자 / Start / End); 6 popover-checklist multi-filters reusing Phase 4's `_picker_popover.html` macro (no fork) with D-15b auto-commit; AI Summary modal (D-OV-15 supersedes inline rendering); Link button with URL sanitizer (D-OV-16); Obsidian-style frontmatter properties table on detail page.
- **Phase 6 (Ask Tab Port):** v1.0 NL agent ported under FastAPI/HTMX with sync `def` routes (GET /ask, POST /ask/query, POST /ask/confirm); NL-05 two-turn confirmation reuses `_picker_popover.html` macro with `disable_auto_commit=True`; Ask-page-only Bootstrap LLM dropdown ("LLM: Ollama ▾" / "LLM: OpenAI ▾"); `pbm2_llm` plain unsigned cookie validated against `settings.llms[].name` (closed-set defense); 204 + `HX-Refresh: true` on backend switch; cookie threads through `llm_resolver` so Ask + AI Summary share a single backend choice (D-17 single source of truth); abort banner with five reason branches (step-cap / timeout / llm-error / unconfigured / loop-aborted) and verbatim v1.0 copy; v1.0 Streamlit Ask page hard-deleted per D-22 (`app/pages/ask.py` + 2 test files + nav entry).

### Cross-Phase Patterns Established

- **Sync `def` everywhere (INFRA-05):** Every router uses `def`, never `async def`, because SQLAlchemy + PydanticAI's `agent.run_sync()` would block uvicorn's event loop under `async`. Enforced by per-phase invariant tests.
- **Module-level imports for pytest-mock:** Every NL-touching route imports `run_nl_query` at module top so `mocker.patch("app_v2.routers.ask.run_nl_query")` works at module level (D-19).
- **Always-200 contract on user-input routes:** Summary and Ask routes never raise HTTPException for upstream LLM/DB failures — they render error fragments at HTTP 200 so HTMX swaps land cleanly. The error fragment carries the swap-target id for outerHTML idempotence.
- **Shared Jinja macros (no forking):** `_picker_popover.html` is the single source — Phase 5 Overview and Phase 6 Ask confirmation both `{% from "browse/_picker_popover.html" import picker_popover %}` with kwargs (form_id, hx_post, hx_target, disable_auto_commit) parameterized.
- **Cookie threading for backend choice (D-17):** Every caller of `resolve_active_llm`/`resolve_active_backend_name` passes the `request` so the `pbm2_llm` cookie applies globally — Ask sets it, AI Summary reads it.

### Out of Scope / Deferred

- **ASK-V2-04 (NL session history):** Out of Scope per Phase 6 D-05 (user explicit "no need for history"); folded into ASK-V2-F01 "Persistent NL history across sessions" for a future milestone.
- **BROWSE-V2-04 (v2.0 Excel/CSV export):** Out of Scope per D-19..D-22; v1.0 Streamlit Browse remains the export surface until v1.0 sunset; v2.0 Browse is view-only by design.
- **Auth (FOUND-01, FOUND-03):** Continued deferral from v1.0 per D-04; intranet shared credentials, no public-internet exposure planned.

### HUMAN-UAT Pending

5 phases (1, 2, 3, 4, 6) have UAT items pending in `{phase}-HUMAN-UAT.md` for live-server browser validation; Phase 5 was UAT-approved 2026-04-28. Items persist for `/gsd-progress` and `/gsd-audit-uat`.

### Tech Debt (advisory)

- `overview.py` legacy helpers (`_build_overview_context`, `_entity_dict`, `_resolve_curated_pids`) are dead code post-Phase-5; harmless at runtime, candidate for cleanup.
- `summary/_success.html` Regenerate button has unreachable `or` fallback in `hx-target`; cosmetic.

---

## v1.0 MVP (Shipped: 2026-04-24)

**Phases completed:** 2 phases, 13 plans, 16 tasks

**Key accomplishments:**

- Streamlit entrypoint with st.navigation, shared sidebar (DB/LLM/health), corrected MySQLAdapter (pool_recycle=3600, pd.read_sql_query), and gitignore secrets exclusion
- 5-stage EAV Result-field normalization pipeline with 65-test pytest suite covering hex/decimal/CSV/compound classification, LUN prefix parsing, DME side detection, and lazy numeric coercion
- 4-function domain service layer with @st.cache_data TTL caching, parameterized IN-clause SQL, row capping, Result normalization, and aggfunc='first' pivot — backed by 10 pytest tests on a SQLite in-memory fixture
- Sidebar filters + Pivot tab with swap-axes, 30-col/200-row warnings, URL round-trip, and copy-link button — replacing Plan 01 placeholder with the app's primary UI surface
- Detail tab (BROWSE-05) and Chart tab (VIZ-01/VIZ-02) filling the Plan 05 stubs — with tab URL round-trip and sidebar Copy link
- Excel export (EXPORT-01) + CSV export (EXPORT-02) via a single st.dialog component wired into the Pivot tab's ctrl_export slot
- NL-07/NL-08 dual backend: PydanticAI-compatible OpenAI/Ollama factory, sidebar LLM radio activated; `nest-asyncio` added for Streamlit event-loop interop
- SAFE-02/03/04(timeout)/06 and NL-09: 4 TDD-built pure safety functions (sqlparse SELECT-only validator, LIMIT injector, path scrubber, Ollama JSON fallback) with 53 tests — later hardened with UNION + CTE + uppercase-path regression tests after code review
- NL-06/SAFE-04(step-cap)/SAFE-05: PydanticAI agent with `output_type=SQLResult|ClarificationNeeded`, single `run_sql` tool composing all safety primitives + `<db_data>` prompt-injection wrapper, 10-test TestModel/FunctionModel coverage
- NL-01/02/03/04/10: Ask page (st.navigation third slot) with question input, SQL expander + Regenerate, collapsed history panel, OpenAI data-sensitivity dismissible banner, SAFE-04 abort banner with distinct step-cap vs timeout copy
- NL-05: two-turn ClarificationNeeded flow — multiselect pre-checked with agent-proposed (InfoCategory, Item) candidates, "Run Query" re-invokes agent with confirmed params injected as second-turn structured message
- ONBD-01/02: gitignored `config/starter_prompts.yaml` (committed `.example.yaml`) with 8 curated UFS prompts covering lookup/compare/filter shapes, rendered as 4×2 gallery that hides after first successful run

### Code Review Hardening (post-execution)

- Phase 1: 1 critical (table-name allowlist) + 5 warnings (multi-DB cache key, DB error logging, `pd.isna` guard, filename traversal order, browse.tab URL sync) + 1 re-review-surfaced XSS (escape DB name in sidebar health indicator) — all fixed with regression tests
- Phase 2: 2 critical SQL validator bypasses (UNION smuggle, CTE smuggle) + 4 warnings (display-side timeout, Regenerate discarded confirmed params, case-insensitive path scrub, pymysql error leak to LLM) — all fixed with regression tests

### Deferred / Accepted Gaps

- FOUND-01 (login page) and FOUND-03 (cookie-key startup guard) deferred to a pre-deployment phase per CONTEXT D-04. FOUND-02 (gitignore auth.yaml) IS in scope and complete so the scaffold cannot leak demo credentials when auth is enabled later.
- 12 items pending live-browser / live-LLM human validation, persisted in `01-HUMAN-UAT.md` + `02-HUMAN-UAT.md` for later `/gsd-verify-work`.

### Stats

- Git range: `b30664a` → `fa00e3d` (87 commits across 2026-04-23 → 2026-04-24)
- LOC: 3080 (app/) + 1711 (tests/) Python
- Tests: 171 passing (75 Phase 1 + 96 Phase 2)
- Requirements: 47/49 satisfied, 2 deferred (accepted per D-04)

---
