---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Ready to execute
stopped_at: Completed 03-04-PLAN.md
last_updated: "2026-05-02T18:58:23.426Z"
last_activity: 2026-05-02
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 15
  completed_plans: 14
  percent: 93
---

# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-29)

**Core value:** Fast ad-hoc browsing of the UFS parameter database — even if NL fails, the UI lets non-SQL users find platforms, compare parameters, chart, and export
**Current focus:** Phase 03 — Overhaul Ask feature into multi-step agentic chat

## Current Position

Phase: 03 (Overhaul Ask feature into multi-step agentic chat) — EXECUTING
Plan: 5 of 5
Milestone: v2.0 Bootstrap Shell — ✅ Shipped 2026-04-29 (tag `v2.0`)
Last activity: 2026-05-02

Progress: [——————————] no active milestone

## Shipped Milestones

| Version | Phases | Plans | Tests | Tag | Audit | Decisions log |
|---------|--------|-------|-------|-----|-------|---------------|
| v1.0 MVP | 2 | 13 | 171 | `v1.0` | [v1.0-MILESTONE-AUDIT.md](milestones/v1.0-MILESTONE-AUDIT.md) | (inline in archived ROADMAP/SUMMARY files) |
| v2.0 Bootstrap Shell | 6 | 30 | 506 | `v2.0` | [v2.0-MILESTONE-AUDIT.md](milestones/v2.0-MILESTONE-AUDIT.md) | [v2.0-DECISIONS-LOG.md](milestones/v2.0-DECISIONS-LOG.md) |

Per-phase artifacts (CONTEXT.md / PLAN.md / SUMMARY.md / REVIEW.md / VERIFICATION.md) live under `.planning/milestones/<version>-phases/`.

## Open UAT (carried from v2.0)

Five v2.0 phases have HUMAN-UAT items pending live-server browser validation. Items persist in their archived `*-HUMAN-UAT.md` files and surface via `/gsd-progress` and `/gsd-audit-uat`:

- Phase 1, 2, 3, 4, 6 — `*-HUMAN-UAT.md` items (Phase 5 was UAT-approved 2026-04-28)

Not blocking — the project's accepted pattern is to defer browser UAT until ready. Run `/gsd-audit-uat` to review or `/gsd-verify-work <phase>` to walk through items.

## Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260427-uoh | Add SQLite DB adapter and demo data seeder for Phase 4 UAT testing | 2026-04-27 | 43e51e1 | [260427-uoh-add-sqlite-db-adapter-and-demo-data-seed](./quick/260427-uoh-add-sqlite-db-adapter-and-demo-data-seed/) |
| 260429-e76 | Fix Overview filter popover clipping (extend `.panel:has()` to cover `.overview-filter-bar`) | 2026-04-29 | c9f9bcd | [260429-e76-fix-overview-filter-popover-clipping-ext](./quick/260429-e76-fix-overview-filter-popover-clipping-ext/) |
| 260429-ek7 | Restyle Link button to match AI button visual treatment (chain icon + `text-dark`) | 2026-04-29 | 4fed64d | [260429-ek7-restyle-active-state-link-button-in-over](./quick/260429-ek7-restyle-active-state-link-button-in-over/) |
| 260429-kc1 | Source `ufs_service._TABLE` from `settings.app.agent.allowed_tables` (no hardcoded "ufs_data") | 2026-04-29 | 747a610 | [260429-kc1-source-ufs-service-table-and-allowed-tab](./quick/260429-kc1-source-ufs-service-table-and-allowed-tab/) |
| 260429-kn7 | Remove v1.0 Streamlit shell — app_v2 becomes single source of truth (5 tasks, 507 tests green) | 2026-04-29 | 7266e00 | [260429-kn7-remove-v1-0-streamlit-shell-app-v2-fasta](./quick/260429-kn7-remove-v1-0-streamlit-shell-app-v2-fasta/) |
| 260429-qyv | Browse: Parameters filter depends on selected Platforms (server-side intersection, disabled when none, OOB picker refresh) | 2026-04-29 | f1e002b | [260429-qyv-browse-parameters-filter-depends-on-sele](./quick/260429-qyv-browse-parameters-filter-depends-on-sele/) |
| 260430-wzg | Fix Joint Validation filter popover clipping (extend `.panel { overflow: visible }` to cover `.panel.overview-filter-bar` self-match) | 2026-04-30 | 067fd37 | [260430-wzg-fix-joint-validation-filter-popover-clip](./quick/260430-wzg-fix-joint-validation-filter-popover-clip/) |
| 260502-jb2 | Add fake joint validation fixture folders to stress-test JV grid with 20+ results (16 new fakes → 22 total, page-2 active) | 2026-05-02 | cd9b417 | [260502-jb2-add-fake-joint-validation-fixture-folder](./quick/260502-jb2-add-fake-joint-validation-fixture-folder/) |
| 260502-sqi | Fix JV pagination losing sort state — thread sort/order into pagination hx-vals | 2026-05-02 | 2167592 | [260502-sqi-fix-jv-pagination-losing-sort-state-thre](./quick/260502-sqi-fix-jv-pagination-losing-sort-state-thre/) |
| 260502-v09 | Cleanup v1.0 Streamlit-era dead code — legacy LLM adapter cluster (4 files, ~226 LOC), 4 stale deps from requirements.txt, orphan `.streamlit/` + `config/overview.example.yaml` | 2026-05-02 | 03c9717 | [260502-v09-cleanup-v1-0-streamlit-era-dead-code-leg](./quick/260502-v09-cleanup-v1-0-streamlit-era-dead-code-leg/) |

## Blockers/Concerns

None.

## Session Continuity

Last session: 2026-05-02T18:58:13.519Z
Next action: `/gsd-new-milestone` to scope v2.1+ when ready
Stopped at: Completed 03-04-PLAN.md

## Accumulated Context

### Roadmap Evolution

- Phase 1 added: Overview Tab: Auto-discover Platforms from HTML Files (2026-04-30)
- Phase 3 added: Overhaul Ask feature into multi-step agentic chat — PydanticAI tool loop + SSE streaming + ephemeral history; full decisions captured in `.planning/notes/ask-chat-overhaul-decisions.md` (2026-05-03)

### Decisions

- **2026-04-30 (01-01):** Pin BS4+lxml at lower-bound + major-cap (no exact pins; matches existing project pin style — `>=4.12,<5.0` and `>=5.0,<7.0`)
- **2026-04-30 (01-01):** Generic AI Summary partial pattern — `summary/_success.html` and `_error.html` rebound from hardcoded `platform_id` to `entity_id` + `summary_url` so the JV summary route in Plan 04 reuses the same partials with no fork
- **2026-04-30 (01-01):** Keep `platform_id` key in TemplateResponse alongside `entity_id` for backward-compat (no other consumer reads it today, but cost-free safety net)
- [Phase 01]: Pydantic v2 BaseModel for ParsedJV (not @dataclass) — stack consistency with Phase 5 OverviewRow/OverviewGridViewModel
- [Phase 01]: Wrap every BS4 get_text() result in str() — Pitfall 9: NavigableString carries parent reference; leak prevention at extraction time
- [Phase 01]: Discovery glob NOT memoized; only parsed-metadata dict memoized — preserves D-JV-09 drop-folder UX (newly-dropped folders appear immediately)
- [Phase 01]: JointValidationRow.link is None (not '') — None signals 'no usable link' so template renders Report Link button in disabled state (D-JV-15)
- [Phase 01]: _sanitize_link verbatim port of D-OV-16 — Plan 06 invariant grep will confirm 5-scheme tuple (javascript:/data:/vbscript:/file:/about:) is byte-equal
- [Phase 01]: Plan 01-03: extract _call_llm_with_text(content, cfg, system_prompt, user_prompt_template) backend-agnostic helper from _call_llm_single_shot — both platform and JV summary paths share one chat.completions.create call site; canonical {markdown_content} placeholder shared by both prompt modules
- [Phase 01]: Plan 01-03: JV cache key shape hashkey('jv', confluence_page_id, mtime_ns, cfg.name, cfg.model) — literal 'jv' string discriminator AND 5-tuple length both prevent collision with platform's 4-tuple key on the same numeric id (Pitfall 3, T-03-02)
- [Phase 01]: Plan 01-03: JV summary service returns BARE SummaryResult (text/llm_name/llm_model/generated_at) — router (Plan 04 Task 3) renders markdown + computes age, mirroring routers/summary.py:156-180 verbatim
- [Phase 01]: Plan 01-04: HX-Push-Url must be set on the constructed TemplateResponse, NOT via an injected Response parameter — FastAPI's parameter-Response merge does not apply when the route returns its own Response object
- [Phase 01]: Plan 01-04: Pass active_filter_counts + all_platform_ids=[] as transitional context aliases on the JV listing context so the still-Phase-5-shaped overview templates render to 200 in the wave-3 interim state — Plan 05 deletes the bridge
- [Phase 01]: Plan 01-04: Three legacy test_content_routes.py tests (test_overview_row_ai_button_*, test_overview_has_global_summary_modal) marked skipped — they assert against the deleted POST /overview/add affordance and curated-Platform row markup; Plan 06 ships JV-shaped equivalents
- [Phase 01]: Plan 01-04: StaticFiles mount registration order matters — child mount /static/joint_validation registered BEFORE parent /static so longest-prefix wins (Pitfall 10 — Starlette dispatches by registration order)
- [Phase 01]: Plan 01-05: Iframe sandbox literal locked at 'allow-same-origin allow-popups allow-popups-to-escape-sandbox' — NO script-execution flag, NO allow-top-navigation, NO allow-forms (T-05-03 mitigation byte-pinned in app_v2/templates/joint_validation/detail.html for Plan 06 invariant grep)
- [Phase 01]: Plan 01-05: Pitfall 8 honored — sortable_th macro defined INSIDE {% block grid %} body so jinja2-fragments block_names=['grid', 'count_oob', 'filter_badges_oob'] rendering retains macro visibility for POST /overview/grid OOB swaps
- [Phase 01]: Plan 01-05: Auto-fixed 2 tests in tests/v2/test_main.py that asserted on the literal 'Overview' nav label — direct consequence of D-JV-01 nav-label rename in this plan; updated to 'Joint Validation' while preserving structural intent (3 tab labels + active class on the JV nav-link)
- [Phase 01-overview-tab-auto-discover-platforms-from-html-files]: Plan 01-06: Rule 3 batch-fix sibling test files BEFORE deletion (test_atomic_write.py, test_summary_routes.py, test_summary_integration.py, test_content_routes.py, test_phase03_invariants.py) so the v2 suite stays green between commits — alternative (delete first, fix breakage) would have left 23+ tests red mid-plan and broken git bisectability
- [Phase 01-overview-tab-auto-discover-platforms-from-html-files]: Plan 01-06: Test 5 invariant matches inner 5-string substring of the dangerous-link tuple, not the parens — actual source-code tuple in joint_validation_grid_service.py spans 3 lines for readability; substantive byte-equal contract preserved
- [Phase 01-overview-tab-auto-discover-platforms-from-html-files]: Plan 01-06: Test 11 invariant scans BOTH joint_validation_summary.py AND joint_validation_parser.py for the decompose 3-tag list — Plan 02 implementation puts the BeautifulSoup pre-processor in the parser module, so scanning the union honors the contract regardless of which module owns the implementation
- [Phase 02]: D-UI2-04: 4 type-scale tokens in tokens.css (logo 20px, h1 28px, th 12px, body 15px); no --font-size-nav token
- [Phase 02]: D-UI2-03: .shell reduced to padding:0; max-width:1280px and margin:0 auto removed for full-width content
- [Phase 02]: D-UI2-05: body flex-column + main.container-fluid flex:1 0 auto + .site-footer flex-shrink:0 implements sticky-in-flow footer without position:fixed
- [Phase 02]: D-UI2-06: Browse count caption moved from .panel-header into footer block; OOB emitter byte-stable; HTMX merges by id into footer receiver
- [Phase 02]: W6/W7: comments moved inside blocks to satisfy grep -B1 placement and grep -c count acceptance criteria
- [Phase 02]: D-UI2-07/11/12: JV two-panel collapsed into single panel; .page-head removed; h1 + count inside panel-header
- [Phase 02]: W1: count_oob emitter changed from div to span to match panel-header receiver tag; comment text reworded to avoid grep false-matches
- [Phase 02]: B1: filter badges visibility preserved; legacy outer wrapper removed; inner OOB div repositioned below filter bar above grid with px-3 pt-2
- [Phase 02]: D-UI2-13/14: JV_PAGE_SIZE=15 in service; PageLink Pydantic submodel (B3); Bootstrap .pagination in footer via _pagination.html partial (B5 single source); FastAPI Query/Form(ge=1,le=10000) two-layer DoS defense (T-02-04-02)
- [Phase 02]: W2 fix: UI-SPEC contradictory footer-carries-count paragraph removed; footer carries pagination only per D-UI2-11
- [Phase 03]: Plan 03-01: Extend AgentConfig with chat_max_steps:int field over new AgentChatConfig submodel — avoids YAML schema bump (Gap 12); default=12 leaves headroom for ~6-tool typical turn; le=50 caps DoS surface
- [Phase 03]: Plan 03-01: Plotly 2.35.2 + htmx-ext-sse 2.2.4 vendored under app_v2/static/vendor/; loaded only on /ask via per-page extra_head Jinja block — RESEARCH Pitfall 5 (4.5MB Plotly NOT in base.html)
- [Phase 03]: Plan 03-01: VERSIONS.txt manifests use append-not-overwrite when extending an existing vendor dir — preserves audit trail of prior pins (htmx@2.0.10 untouched while adding htmx-ext-sse@2.2.4)
- [Phase 03]: Plan 03-02: Verbatim port of SAFE-02..06 from nl_agent.run_sql to chat_agent._execute_and_wrap (NOT shared helper) — preserves D-CHAT-09 'nl_agent.py unchanged' promise; cost is two-harness sync, benefit is zero risk to existing test_nl_agent.py invariants
- [Phase 03]: Plan 03-02: Rejection prefix REJECTED: replaces SQL rejected: at chat-tier boundary only (D-CHAT-02) — nl_agent.run_sql still emits 'SQL rejected:' for legacy single-turn flow; the two prefixes coexist so plan 03's loop wrapper can string-prefix-match cleanly
- [Phase 03]: Plan 03-02: Module-private _execute_and_wrap (single-underscore prefix, excluded from __all__) — exposes a unit-test entry point under the underscore name without bloating the public surface; tests assert REJECTED-prefix contract directly on the helper
- [Phase 03]: Plan 03-03: chat_loop drives agent.run_stream_events (Open Question 1 RESOLVED) — public API, signature-verified; sufficient for D-CHAT-01 cancel between FunctionToolResultEvent boundaries; avoids unverified CallToolsNode.stream path
- [Phase 03]: Plan 03-03: WARNING-3 STRUCTURED final-payload contract — chat_loop emits {summary, sql, chart_spec_dict, new_messages} dict, NOT pre-rendered HTML; router (plan 03-04) owns _final_card.html render against request.app.state.db (T-03-04-09 alignment, keeps agent module DB-free)
- [Phase 03]: Plan 03-03: AgentRunResult.new_messages() called via run_result.new_messages() (NOT getattr(ev, 'new_messages')) — Rule 1 auto-fix; new_messages is a method on ev.result, not on AgentRunResultEvent itself
- [Phase 03]: Plan 03-03: asyncio.Event over threading.Event (RESEARCH Pitfall 6) — mixing threading.Event with asyncio leads to 'event set but generator never wakes'; per-session lock _SESSION_LOCK serializes append_session_history (Open Question 2 RESOLVED)
- [Phase 03]: Plan 03-03: app.state.chat_turns / chat_sessions are DOCUMENTATION hooks; canonical store is module-level _TURNS / _SESSIONS in chat_session.py; router interacts only via chat_session helpers
- [Phase 03]: Atomic Task 1 commit (D-CHAT-09): router rewrite + 4 deletions in single commit so working tree never has half-deleted artifacts
- [Phase 03]: WARNING-3 contract honored: chat_loop emits structured final payload; router OWNS table_html + chart_html via _hydrate_final_card — agent module stays DB-free + Plotly-free
- [Phase 03]: AA-compliant color overrides for .btn-stop (#cc2434) and .chat-error-card-soft (#8a5a00) baked into CSS rules — not promoted to tokens (RESEARCH Gap 15)

### Performance Metrics

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01    | 01   | 5min     | 2     | 5     |
| Phase 01 P02 | 6min | 3 tasks | 8 files |
| Phase 01 P03 | 8min | 2 tasks | 5 files |
| Phase 01 P04 | 19min | 3 tasks | 7 files |
| Phase 01 P05 | 7min | 3 tasks | 6 files |
| Phase 01-overview-tab-auto-discover-platforms-from-html-files P06 | 11min | 3 tasks | 17 files |
| Phase 02 P01 | 8min | 3 tasks | 4 files |
| Phase 02 P02 | 6min | 1 tasks | 2 files |
| Phase 02 P03 | 10min | 3 tasks | 4 files |
| Phase 02 P04 | 13min | 3 tasks | 8 files |
| Phase 03 P01 | 10min | 2 tasks | 8 files |
| Phase 03 P02 | 5min | 2 tasks | 1 files |
| Phase 03 P03 | 12min | 3 tasks | 3 files |
| Phase 03 P04 | 12min | 4 tasks | 11 files |
