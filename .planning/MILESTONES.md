# Milestones

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
