---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: v1.0 milestone complete
stopped_at: Completed 04-05-PLAN.md (Wave 5 — atomic .panel-header to .ph migration on Browse/JV/Ask + Phase 02 invariant rewrites)
last_updated: "2026-05-07T06:37:07.094Z"
last_activity: 2026-05-07
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 20
  completed_plans: 20
  percent: 100
---

# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-29)

**Core value:** Fast ad-hoc browsing of the UFS parameter database — even if NL fails, the UI lets non-SQL users find platforms, compare parameters, chart, and export
**Current focus:** Phase 04 — UI Foundation — Helix-aligned shell & primitives

## Current Position

Phase: 04
Plan: Not started
Milestone: v2.0 Bootstrap Shell — ✅ Shipped 2026-04-29 (tag `v2.0`)
Last activity: 2026-05-07 - Completed quick task 260507-mmv: Topbar rebrand (AE / Yhoon Dashboard / YH / bi-clipboard-check)

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
| 260504-114 | Ask UI: right-aligned user bubbles, animated thinking indicator, streaming assistant response | 2026-05-03 | c887eb4 | [260504-114-ask-ui-right-aligned-user-bubbles-animat](./quick/260504-114-ask-ui-right-aligned-user-bubbles-animat/) |
| 260504-220 | Ask UI follow-up: assistant response as plain prose (no panel chrome), thinking indicator moved to assistant side, perceived-streaming word-reveal | 2026-05-03 | 90d2530 | [260504-220-ask-ui-follow-up-assistant-response-as-p](./quick/260504-220-ask-ui-follow-up-assistant-response-as-p/) |
| 260504-2jl | Ask UI fix: visible summary (drop word-reveal), CSS `:has()` thinking-hide, block-level `.chat-thinking` (own line) | 2026-05-03 | 5adf7f4 | [260504-2jl-ask-ui-fix-empty-summary-bubble-thinking](./quick/260504-2jl-ask-ui-fix-empty-summary-bubble-thinking/) |
| 260504-30t | Ask streaming: server-side chunked emission of summary as `text_delta` SSE events between last tool_result and final | 2026-05-07 | eb4efb8 | [260504-30t-ask-streaming-server-side-chunked-emissi](./quick/260504-30t-ask-streaming-server-side-chunked-emissi/) |
| 260507-ksn | JV parser: handle Page Properties next-sibling-`<td>` shape + dedupe heading/table label matches + strip parens from Start/End | 2026-05-07 | 4b9a92b | [260507-ksn-jv-parser-handle-page-properties-next-si](./quick/260507-ksn-jv-parser-handle-page-properties-next-si/) |
| 260507-l5w | JV grid Report Link button: relabel `Link` → `edm`; available state styled `text-dark` for clear contrast vs disabled | 2026-05-07 | 790d2a9 | [260507-l5w-jv-link-button-relabel-link-to-edm-make-](./quick/260507-l5w-jv-link-button-relabel-link-to-edm-make-/) |
| 260507-lcc | JV pagination switched from sliding-window-with-ellipsis to fixed group-of-10 (stable bar width within a group; chevrons jump to adjacent group boundary) | 2026-05-07 | 7680d0e | [260507-lcc-pagination-switch-from-sliding-window-el](./quick/260507-lcc-pagination-switch-from-sliding-window-el/) |
| 260507-lox | JV parser: skip `<strong>` matches nested in h1-h6 (defense-in-depth for Status); add `AppConfig.conf_url` (settings.yaml only); per-row 컨플 button next to edm linking to `{conf_url}/{page_id}` | 2026-05-07 | ecb98ec | [260507-lox-jv-status-specific-h1-h6-skip-in-parser-](./quick/260507-lox-jv-status-specific-h1-h6-skip-in-parser-/) |
| 260507-mmv | Topbar rebrand: brand-mark `P`→`AE`, wordmark `PBM2`→`Yhoon Dashboard`, avatar `PM`→`YH`, JV tab icon `bi-list-ul`→`bi-clipboard-check`; `<title>` rebranded; tests updated in lockstep | 2026-05-07 | d9271d0 | [260507-mmv-in-main-page-instead-of-p-use-ae-instead](./quick/260507-mmv-in-main-page-instead-of-p-use-ae-instead/) |

## Blockers/Concerns

None.

## Session Continuity

Last session: 2026-05-03T10:56:17.638Z
Next action: `/gsd-new-milestone` to scope v2.1+ when ready
Stopped at: Completed 04-05-PLAN.md (Wave 5 — atomic .panel-header to .ph migration on Browse/JV/Ask + Phase 02 invariant rewrites)

## Accumulated Context

### Roadmap Evolution

- Phase 1 added: Overview Tab: Auto-discover Platforms from HTML Files (2026-04-30)
- Phase 3 added: Overhaul Ask feature into multi-step agentic chat — PydanticAI tool loop + SSE streaming + ephemeral history; full decisions captured in `.planning/notes/ask-chat-overhaul-decisions.md` (2026-05-03)
- Phase 4 added: UI Foundation — Helix-aligned shell & primitives (foundation for downstream JV list, Platform BM pivot, Ask AI sidebar+citations) (2026-05-03)

### Decisions

- **2026-05-07 (quick 260507-lcc):** JV pagination algorithm flipped from sliding-window-with-ellipsis to fixed group-of-10 (`GROUP_SIZE=10`) — bar width stays stable within a group; chevrons advance to first/last page of adjacent group. Supersedes the algorithm portion of D-UI2-13; D-UI2-14 (page_size=15, two-layer Query/Form validation, HX-Push-Url default-omit) unchanged. PageLink Pydantic submodel kept byte-stable (B3); `num=None` ellipsis sentinel no longer reachable but still a valid model.
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
- [Phase 03]: Plan 03-05: Rule 1 auto-fix in app_v2/routers/ask.py — pbm2_session cookie set on TemplateResponse directly via _apply_session_cookie helper; FastAPI parameter Response cookies don't merge into a returned Response object
- [Phase 03]: Plan 03-05: Rule 1 auto-fix in app/core/agent/chat_loop.py — terminal-event discriminator switched from hasattr(ev,'result') to isinstance(ev, AgentRunResultEvent); FunctionToolResultEvent ALSO has a result attribute, causing every tool call to misclassify as terminal
- [Phase 03]: Plan 03-05: Rule 2 auto-fix — added data-reason attribute on _error_card.html for machine-readable D-CHAT-04 vocabulary; tests assert on data-reason rather than body copy
- [Phase 03]: Plan 03-05: Phase 4 plotly invariant narrowed by whitelisting app_v2/routers/ask.py only — D-CHAT-05 + T-03-04-09 require server-side Plotly chart construction in chat router; lazy import inside _build_plotly_chart_html keeps Browse/JV/Settings free of import cost
- [Phase 03]: Plan 03-05: anyio's pytest plugin (group='pytest11', provided by anyio package) used via @pytest.mark.anyio + anyio_backend='asyncio' fixture — pytest-asyncio NOT required; avoids new dev dependency
- [Phase 03]: Plan 03-05: Real DBAdapter subclass _FakeDB instead of MagicMock — Pydantic v2 ChatAgentDeps.db field annotated DBAdapter rejects MagicMock with isinstance check; reused across test_ask_routes.py and test_chat_agent_tools.py
- [Phase 04]: Plan 04-01: D-UIF-01 rename path additive in Wave 1 — .ph shipped as new selector with normalized 16px 24px padding; existing .panel-header CSS rules at lines 58-74 stay byte-stable. Wave 5 atomically rewrites .panel-header CSS rules to .ph rules together with template markup migration and Phase 02 invariant test updates (same atomicity pattern as Wave 3's planned topbar swap + test_main.py rewrite).
- [Phase 04]: Plan 04-01: No new tokens added to tokens.css — researcher and planner confirmed no Phase 4 primitive uses --cyan or --cyan-soft (deferred to chat sidebar per CONTEXT.md §Deferred). All new rules consume existing tokens.css vars.
- [Phase 04]: Plan 04-01: Inter Tight + JetBrains Mono via Google Fonts CDN — fixes Pitfall 1 (.page-title font-weight 800 was silently degrading to system fallback ~700 because base.html had no <link> for the font). Loaded BEFORE tokens.css so @font-face rules are available when font-family declarations apply. Vendored woff2 fallback deferred to follow-up if intranet DNS restricts fonts.googleapis.com.
- [Phase 04]: Plan 04-01: btn-helix namespace (NOT overriding Bootstrap .btn) — Phase 4 primary-button rules apply only via .btn-helix class, avoiding site-wide Bootstrap button restyling. Co-exists with Bootstrap .btn (Bootstrap rules win for unscoped .btn callers; Phase 4 rules apply when paired with .btn-helix or used inside .pop).
- [Phase 04]: Plan 04-01: !important on .pop width/min-width to defeat Bootstrap --bs-dropdown-min-width: 10rem default (Pitfall 3) — when Wave 2 macros apply .pop to a .dropdown-menu, this guarantees the 300px width wins regardless of cascade tie-breaker.
- [Phase 04-ui-foundation-helix-aligned-shell-primitives-build-reusable-]: Plan 04-02: chip-toggle.js as SIBLING of popover-search.js (not fork) — D-UIF-05 + D-UI2-09 keep popover-search.js byte-stable; both helpers coexist via document-level capture-phase delegation with precise selectors (chip-toggle binds .pop .opt and early-returns inside .popover-search-root per Pitfall 8 boundary).
- [Phase 04-ui-foundation-helix-aligned-shell-primitives-build-reusable-]: Plan 04-02: chip-value-as-payload (NOT '1') in chip-toggle.js — when chip is ON, hidden input gets the chip's data-value; OFF clears it. Diverges from RESEARCH §Pitfall 8 sketch ('1' flag) so multi-option groups submit meaningful per-option values (?status=open&status=closed) instead of opaque flags.
- [Phase 04-ui-foundation-helix-aligned-shell-primitives-build-reusable-]: Plan 04-02: HeroSpec and FilterGroup live in SEPARATE files (hero_spec.py + filter_spec.py) — RESEARCH Open Question 2 resolved as separate-file; mirrors one-concept-per-file convention in app_v2/services/.
- [Phase 04-ui-foundation-helix-aligned-shell-primitives-build-reusable-]: Plan 04-02: kpi_card variant arg dropped per UI-SPEC line 280 — caller sets .kpis or .kpis.five wrapper class; macro renders ONE card. Reduces signature surface; Wave 4 showcase emits the wrapper directly.
- [Phase 04-ui-foundation-helix-aligned-shell-primitives-build-reusable-]: Plan 04-02: btn-helix used inside popovers + showcase to leverage Wave 1's namespaced primary button without fighting Bootstrap .btn cascade.
- [Phase 04-ui-foundation-helix-aligned-shell-primitives-build-reusable-]: Plan 04-02: hero macro inline-overrides grid-template-columns to 1fr when spec.side_stats is empty — only runtime-data-dependent style override; everything else lives in app.css.
- [Phase 04-ui-foundation-helix-aligned-shell-primitives-build-reusable-]: Plan 04-02: filters_popover hyphen-safe group_name (lowercase + replace ' '→'_' + replace '-'→'_') — UFS-eMMC label produces name='ufs_emmc' (Python attr-safe). BLOCKER 2 from plan revision honored (both space AND hyphen replaced).
- [Phase 04-ui-foundation-helix-aligned-shell-primitives-build-reusable-]: Plan 04-02: sparkline namespace() pattern + height/2 mid-height fallback for hi==lo — Jinja loop scope cannot reassign outer scalars; namespace is the canonical idiom. Constant data renders flat horizontal line at mid-height (13 for default 26px viewBox), no NaN.
- [Phase 04-ui-foundation-helix-aligned-shell-primitives-build-reusable-]: Plan 04-03: Single-commit atomicity for Wave 3 — markup swap + test rewrites + .navbar CSS rule removal landed in commit 395477b. Per RESEARCH §Migration Strategy + Pitfall 2: splitting them would leave the working tree red between commits (markup changed but tests pinning legacy literals, OR vice versa).
- [Phase 04-ui-foundation-helix-aligned-shell-primitives-build-reusable-]: Plan 04-03: test_get_root_marks_overview_active rewrite expanded backward-window from 200 to 300 chars — the new .tabs / .tab markup wraps differently and aria-selected="true" can sit on a different attribute line than href. 300 chars provides headroom without over-matching neighboring tabs.
- [Phase 04-ui-foundation-helix-aligned-shell-primitives-build-reusable-]: Plan 04-03: Comment text in base.html and app.css avoids echoing legacy literals (e.g. <nav class="navbar"> or .navbar { ... }) so grep-based acceptance criteria pass cleanly. Stub-comment-on-deletion pattern in tests preserves git blame continuity — function names retained, body documents the rename via Phase 04 D-UIF-06 comment.
- [Phase 04-ui-foundation-helix-aligned-shell-primitives-build-reusable-]: Plan 04-05: Atomic single-commit migration (e7e4455) — markup swap on 4 templates + CSS rule rewrite + Phase 02 invariant test updates landed together; same atomicity pattern as Wave 3's topbar swap. Splitting would have broken bisectability.
- [Phase 04-ui-foundation-helix-aligned-shell-primitives-build-reusable-]: Plan 04-05: Padding preservation over 4px-grid normalization — surviving .ph rule keeps 18px 26px padding from the legacy class. Wave 1's speculative 16px 24px block deleted to consolidate the duplicate .ph rules. UI-SPEC §Spacing 4px-grid normalization applies to NEW shell adoption only — adopting it on shipped surfaces would have produced 2px-per-axis visual drift.
- [Phase 04-ui-foundation-helix-aligned-shell-primitives-build-reusable-]: Plan 04-05: Rule 3 auto-fix — id rename and CSS comment hygiene. Plan's verbatim instructions preserved id='browse-panel-header' / id='overview-panel-header' and used comment phrasings like '.ph (was .panel-header per D-UIF-01)' which contained the literal panel-header. Migration completeness criterion grep -c 'panel-header' = 0 forced renaming the ids (zero callers — verified) and rephrasing comments to retire the legacy literal.

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
| Phase 03 P05 | 20min | 2 tasks | 9 files |
| Phase 04 P01 | 5min | 2 tasks | 2 files |
| Phase 04 P02 | 5min | 2 tasks | 11 files |
| Phase 04 P03 | 6min | 3 tasks | 4 files |
| Phase 04-ui-foundation-helix-aligned-shell-primitives-build-reusable- P05 | 9min | 2 tasks | 6 files |
