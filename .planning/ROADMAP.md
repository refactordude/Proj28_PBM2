# Roadmap: PBM2

## Milestones

- ✅ **v1.0 MVP** — Phases 1-2 (shipped 2026-04-24) — see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- ✅ **v2.0 Bootstrap Shell** — Phases 1-6 (shipped 2026-04-29) — see [milestones/v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md)
- 📋 **v2.1+** — TBD (run `/gsd-new-milestone` to define next milestone)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-2) — SHIPPED 2026-04-24</summary>

- [x] Phase 1: Foundation + Browsing (7/7 plans) — completed 2026-04-23
- [x] Phase 2: NL Agent Layer (6/6 plans) — completed 2026-04-24

Full archive: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
Requirements archive: [milestones/v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)
Audit: [milestones/v1.0-MILESTONE-AUDIT.md](milestones/v1.0-MILESTONE-AUDIT.md)

</details>

<details>
<summary>✅ v2.0 Bootstrap Shell (Phases 1-6) — SHIPPED 2026-04-29</summary>

- [x] Phase 1: Pre-work + Foundation (4/4 plans) — completed 2026-04-24
- [x] Phase 2: Overview Tab + Filters (3/3 plans) — completed 2026-04-25
- [x] Phase 3: Content Pages + AI Summary (4/4 plans) — completed 2026-04-26
- [x] Phase 4: Browse Tab Port (7/7 plans) — completed 2026-04-28
- [x] Phase 5: Overview Tab Redesign (6/6 plans) — completed 2026-04-28
- [x] Phase 6: Ask Tab Port (6/6 plans) — completed 2026-04-29

Full archive: [milestones/v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md)
Requirements archive: [milestones/v2.0-REQUIREMENTS.md](milestones/v2.0-REQUIREMENTS.md)
Audit: [milestones/v2.0-MILESTONE-AUDIT.md](milestones/v2.0-MILESTONE-AUDIT.md)

</details>

## Progress

| Milestone | Phases | Plans | Status | Shipped |
|-----------|--------|-------|--------|---------|
| v1.0 MVP | 2 | 13 | ✅ Shipped | 2026-04-24 |
| v2.0 Bootstrap Shell | 6 | 30 | ✅ Shipped | 2026-04-29 |

## Next Milestone

Run `/gsd-new-milestone` to plan the next iteration:
- Discovery: what user need / problem area to address next
- Research: explore relevant patterns + tech in scope
- Requirements: fresh REQUIREMENTS.md scoped to milestone
- Roadmap: fresh phase list under a new milestone heading

### Phase 1: Overview Tab: Auto-discover Platforms from HTML Files

**Goal:** Replace the Overview tab's curated-Platform listing with auto-discovered Joint Validation rows parsed from `content/joint_validation/<numeric_id>/index.html` (BeautifulSoup4); add `/joint_validation/<id>` detail page (properties table + iframe sandbox of the Confluence export); reuse the Phase 5 grid/filter/sort + AI Summary modal patterns; delete the Platform-curated yaml + supporting code paths (D-JV-01..D-JV-17 locked in 01-CONTEXT.md).
**Requirements**: D-JV-01, D-JV-02, D-JV-03, D-JV-04, D-JV-05, D-JV-06, D-JV-07, D-JV-08, D-JV-09, D-JV-10, D-JV-11, D-JV-12, D-JV-13, D-JV-14, D-JV-15, D-JV-16, D-JV-17
**Depends on:** v2.0 Phase 5 (Overview Redesign — patterns reused)
**Plans:** 6 plans

Plans:
- [x] 01-01-PLAN.md — Add beautifulsoup4+lxml deps; parameterize summary partials with entity_id+summary_url
- [x] 01-02-PLAN.md — BS4 parser + discovery store + grid_service view-model + tests + fixtures
- [x] 01-03-PLAN.md — JV summary shim (D-JV-16 _strip_to_text + JV prompt + cache discriminator); refactor summary_service helper
- [x] 01-04-PLAN.md — Rewrite routers/overview.py for JV listing; add routers/joint_validation.py (detail + summary); StaticFiles mount in main.py
- [x] 01-05-PLAN.md — Rewrite templates/overview/{index,_grid,_filter_bar}.html; add templates/joint_validation/detail.html; flip nav label
- [x] 01-06-PLAN.md — Delete obsolete Phase 5 Platform-curated files (config/overview.yaml, overview_store.py, overview_filter.py, overview_grid_service.py + their tests + test_phase05_invariants.py + test_overview_routes.py); add test_joint_validation_routes.py + test_joint_validation_invariants.py

### Phase 2: UI Shell Rewrite + Browse Footer + Joint Validation Layout Parity + Pagination

**Goal:** Rewrite the global UI shell so every page inherits a taller nav with left-aligned tabs, full-width content, type-scale tokens, and a full-width sticky-in-flow white footer; migrate Browse's "N platforms × M parameters" count caption into the new footer; restructure the Joint Validation listing to mirror Browse's single-panel design (one outer `.panel`, horizontal flex filter row, h1 + entry count inside `.panel-header`); add 15-per-page server-side pagination on the JV listing with prev/next + ellipsis controls in the footer, full URL round-trip via `HX-Push-Url`, and filter/sort reset to page 1 (D-UI2-01..D-UI2-14 locked in 02-CONTEXT.md; visual contract pinned in 02-UI-SPEC.md).
**Requirements**: D-UI2-01, D-UI2-02, D-UI2-03, D-UI2-04, D-UI2-05, D-UI2-06, D-UI2-07, D-UI2-08, D-UI2-09, D-UI2-10, D-UI2-11, D-UI2-12, D-UI2-13, D-UI2-14
**Depends on:** Phase 1
**Plans:** 4/4 plans complete

Plans:
- [x] 02-01-PLAN.md — Shell rewrite: tokens.css type scale + app.css full-width .shell + body flex column + .site-footer + .navbar padding + .panel-title; base.html footer block (D-UI2-01..05)
- [x] 02-02-PLAN.md — Browse footer count migration: move `<span id="grid-count">` from panel-header into `{% block footer %}`; OOB count_oob byte-stable (D-UI2-06)
- [x] 02-03-PLAN.md — JV layout parity: single panel, horizontal flex filter form, h1 + count in panel-header, .overview-filter-bar without .panel class, picker macro byte-stable (D-UI2-07..12)
- [x] 02-04-PLAN.md — JV pagination: JV_PAGE_SIZE=15 constant, page query/form param with ge=1/le=10_000 validation, view-model rows slicing + page_links helper, footer pagination control with prev/next/ellipsis, hidden page input + sortable_th reset to page 1 (D-UI2-13, D-UI2-14)

### Phase 3: Overhaul Ask feature into multi-step agentic chat — replace one-shot Q&A with PydanticAI tool-using agent loop (run_sql, inspect_schema, get_distinct_values, sample_rows, present_result), SSE streaming of thought/tool_call/tool_result/final events via sse-starlette + HTMX, ephemeral session-scoped chat history using PydanticAI message_history, UI lockout + visible Stop button during reasoning, guard-rail rejections fed back as tool-result errors so the agent retries on its own. Anchor visual design to Dashboard_v2.html. Full architectural decisions, motivating example (SM8850 vs SM8650 UNION rejection), tool surface, stack alignment, and open questions for the planner are documented in .planning/notes/ask-chat-overhaul-decisions.md — the planner should read that note first.

**Goal:** Replace the v2.0 Phase 6 one-shot Ask page with a multi-step PydanticAI tool-using agent loop. The agent runs multiple SQL queries, inspects schema, samples distincts, reasons across tool results, and emits a structured final answer. SSE streaming via sse-starlette pushes `thought` / `tool_call` / `tool_result` / `final` / `error` events to an HTMX-driven chat surface. Cooperative cancellation via Stop button, guard-rail rejection retry (cap=5), step-budget enforcement (default=12), ephemeral 6-pair session history, NL-05 confirmation flow deleted in same atomic commit. LLM dropdown carried forward verbatim from Phase 6 (D-CHAT-11). Anchored visually to Dashboard_v2.html palette via existing Phase 02 tokens. 15 D-CHAT-* decisions locked in 03-CONTEXT.md.
**Requirements**: D-CHAT-01, D-CHAT-02, D-CHAT-03, D-CHAT-04, D-CHAT-05, D-CHAT-06, D-CHAT-07, D-CHAT-08, D-CHAT-09, D-CHAT-10, D-CHAT-11, D-CHAT-12, D-CHAT-13, D-CHAT-14, D-CHAT-15
**Depends on:** Phase 2
**Plans:** 5 plans

Plans:
- [x] 03-01-PLAN.md — Foundation: pin sse-starlette, add AgentConfig.chat_max_steps, base.html extra_head block, vendor htmx-ext-sse + Plotly bundles
- [x] 03-02-PLAN.md — Chat agent module: ChartSpec/PresentResult/ChatAgentDeps Pydantic models + build_chat_agent factory + 6-tool surface (REJECTED: prefix on guard rejections)
- [x] 03-03-PLAN.md — Chat plumbing: chat_session (per-turn registry + 12-msg sliding window + scrub-on-write) + chat_loop (stream_chat_turn async generator with cancel/retry-cap/step-budget/error classification) + main.py state init
- [x] 03-04-PLAN.md — Atomic rewrite: routers/ask.py end-to-end (4 new routes, session-cookie auth) + 8 new chat templates + delete NL-05 templates + chat-surface CSS append
- [x] 03-05-PLAN.md — Tests: rewrite test_ask_routes.py + Phase 3 invariants + chat_loop/chat_session/chat_agent unit tests + delete test_phase06_invariants.py

### Phase 4: UI Foundation — Helix-aligned shell & primitives

**Goal:** Build reusable Jinja partials and CSS for the visual system anchored to `Dashboard_v2.html` (sibling project `Proj27_PBM1_fork_bootstrap/Dashboard_v2.html`). Includes: topbar (brand + tab strip + avatar), page-head (28 px title + sub + actions), hero (1.3:1 grid with 72 px stat number, segmented bar, side-stats panel), KPI cards (4-up and 5-up with sparkline), panel + `.ph` header, status pills / chips / tiny-chips, date-range popover (7/14/30/60d quick chips + start/end inputs + reset/apply), filters popover (multi-select chip groups + reset/apply), sticky-corner table styling. Tokens already in `app_v2/static/css/tokens.css`; expand `app.css` and add partials under `app_v2/templates/_components/`. Stack: Jinja + HTMX (no React). Brand stays PBM2. Foundation consumed by downstream phases (Joint Validation list, Platform BM pivot on `browse/`, Ask AI sidebar + citations).
**Requirements**: D-UIF-01, D-UIF-02, D-UIF-03, D-UIF-04, D-UIF-05, D-UIF-06, D-UIF-07, D-UIF-08, D-UIF-09, D-UIF-10, D-UIF-11
**Depends on:** Phase 3
**Plans:** 5 plans

Plans:
- [x] 04-01-PLAN.md — Wave 1: Append all Helix primitive CSS rules to app.css + add Google Fonts link to base.html (.ph as new shell-header selector per D-UIF-01 rename path)
- [x] 04-02-PLAN.md — Wave 2: Create 7 Jinja macro partials in _components/ + HeroSpec/FilterGroup Pydantic models + chip-toggle.js sibling (UFS-eMMC hyphen-safe group_name)
- [x] 04-03-PLAN.md — Wave 3: Atomic shell integration — base.html topbar swap + chip-toggle.js script tag + .navbar rule removal + test_main.py + test_phase02_invariants.py updates
- [x] 04-04-PLAN.md — Wave 4: GET /_components showcase route + showcase.html sectioned page + 3 test files (test_phase04_uif_invariants/_components/_hero_spec)
- [ ] 04-05-PLAN.md — Wave 5: Atomic panel-header → .ph migration on existing surfaces (Browse / JV listing / Ask / JV detail) + CSS rule rewrite + atomic Phase 02 invariant test updates (D-UIF-01 LOCKED rename path completion)
