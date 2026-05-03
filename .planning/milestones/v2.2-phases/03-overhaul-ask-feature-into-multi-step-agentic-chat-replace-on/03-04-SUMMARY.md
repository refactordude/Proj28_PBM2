---
phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
plan: 04
subsystem: ui
tags: [ask, chat, sse, htmx, plotly, jinja2-fragments, atomic-cleanup, d-chat-04, d-chat-05, d-chat-07, d-chat-08, d-chat-09, d-chat-10, d-chat-11, d-chat-12, d-chat-13, d-chat-14]

# Dependency graph
requires:
  - phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
    plan: 01
    provides: vendored Plotly + htmx-ext-sse bundles, base.html extra_head block, sse-starlette pin, AgentConfig.chat_max_steps
  - phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
    plan: 02
    provides: build_chat_agent + ChatAgentDeps + PresentResult + ChartSpec consumed by router-side _hydrate_final_card
  - phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
    plan: 03
    provides: chat_session helpers + chat_loop.stream_chat_turn driving the SSE event_generator
provides:
  - 4-route Ask surface (GET /ask, POST /ask/chat, GET /ask/stream/{turn_id}, POST /ask/cancel/{turn_id}) — D-CHAT-08 contract
  - pbm2_session cookie + session-cookie ownership gate on stream + cancel — T-03-04-01/02
  - WARNING-3 contract honored: _hydrate_final_card runs PresentResult.sql via SAFE-02..06 + builds Plotly chart server-side
  - 8 chat templates (3 shell + 5 event partials) covering UI-SPEC §A–§I
  - Phase 3 chat-surface CSS block appended to app.css (D-CHAT-07)
  - Atomic deletion of NL-05 templates + Phase 6 invariants test (D-CHAT-09)
affects: [03-05-cleanup-tests]

# Tech tracking
tech-stack:
  added: []  # All deps already pinned by plan 03-01
  patterns:
    - "ATOMIC commit (D-CHAT-09): rewrite + 4 deletions in single commit so working tree never has half-deleted artifacts"
    - "WARNING-3 contract: chat_loop emits STRUCTURED final payload {summary, sql, chart_spec_dict, new_messages}; router OWNS table_html + chart_html render via _hydrate_final_card — agent module stays DB-free + Plotly-free"
    - "OOB swap (hx-swap-oob='true') from terminal SSE fragments (_final_card.html, _error_card.html, _user_message.html) flips #input-zone between idle (form) and active (Stop) states — single-template two-state idiom"
    - "SAFE-02..06 reapplied at router boundary: agent-supplied SQL passes through validate_sql + inject_limit + READ ONLY tx + max_execution_time before _hydrate_final_card executes it (defense-in-depth even though the same harness already gated the agent's run_sql tool)"
    - "Plotly column-existence check inside router before figure construction — silent downgrade to chart_type='none' when df is empty or x_column/y_column missing (RESEARCH Open Question 3 RESOLVED)"
    - "_GridVM minimal view-model satisfies browse/_grid.html's vm.df_wide + vm.index_col_name contract without importing the heavyweight BrowseViewModel"

key-files:
  created:
    - app_v2/templates/ask/_user_message.html
    - app_v2/templates/ask/_input_zone.html
    - app_v2/templates/ask/_thought_event.html
    - app_v2/templates/ask/_tool_call_pill.html
    - app_v2/templates/ask/_tool_result_pill.html
    - app_v2/templates/ask/_final_card.html
    - app_v2/templates/ask/_error_card.html
    - .planning/phases/03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on/deferred-items.md
  modified:
    - app_v2/routers/ask.py (rewritten end-to-end)
    - app_v2/templates/ask/index.html (rewritten end-to-end)
    - app_v2/static/css/app.css (pure-append: 186 insertions, 0 deletions)
  deleted:
    - app_v2/templates/ask/_confirm_panel.html
    - app_v2/templates/ask/_abort_banner.html
    - app_v2/templates/ask/_answer.html
    - tests/v2/test_phase06_invariants.py

key-decisions:
  - "Atomic Task 1 commit covers ALL of: router rewrite + 3 NL-05 template deletions + Phase 6 invariants test deletion. The plan moved test_phase06_invariants.py deletion FROM plan 03-05 INTO this Task 1 because once the Phase 6 routes + templates are gone, that test file's assertions no longer hold and would break the suite at the Wave 3 commit boundary"
  - "Router uses SAFE-02..06 harness directly via validate_sql + inject_limit + sa.text — does NOT call into chat_agent._execute_and_wrap. Reason: that helper is module-private; reusing it would force a public-API extraction whose only consumer is this router. The duplicated harness code is the same compromise plan 03-02 made (verbatim port over shared helper) for the same D-CHAT-09 preservation reason"
  - "Plotly Figure constructed via lazy `import plotly.graph_objects as go` inside _build_plotly_chart_html — keeps top-level router import surface free of plotly so non-/ask requests do not pay the import cost"
  - "_GridVM is a tiny ad-hoc class (8 lines) — does NOT import or subclass BrowseViewModel. Reused only the two attributes the macro reads (df_wide, index_col_name). Avoids cross-feature coupling between Ask and Browse"
  - "Index column for the final-card pivot table = first column of the SQL result. The agent's PresentResult.sql is plain SELECT (no pivot), so we render df as-is using column 0 as the index. If the agent emits SELECT PLATFORM_ID, … the first column becomes the row label naturally"
  - "_unconfigured_event_generator returns 200 + a single SSE error frame (NOT 503). Aligns with Phase 6's ALWAYS-200 contract for the user-facing flow — the user sees the error card inline, not a browser-level error page"
  - "Stop button copy = 'Stop' (verbatim from CONTEXT.md <specifics>). Inline OOB swap from _user_message.html — no separate template. The Stop button does NOT live in _input_zone.html (which renders only the idle form state)"
  - "_starter_chips.html stays on disk untouched. RESEARCH Gap 13 audit shows no other consumer references it; planner Task 1 left it in place because deleting it adds no value and would break a hypothetical future plan that wanted to reintroduce starter prompts"
  - "Phase 6 LLM dropdown HTML lifted byte-for-byte: same Bootstrap classes, same hx-post=/settings/llm + hx-vals + hx-swap=none, same backend_name resolver, same trigger label format 'LLM: {{ backend_name }} ▾'. Verified by visual diff between old and new index.html"
  - "App.css append uses #cc2434 (not --red) for .btn-stop text+border and #8a5a00 (not --amber) for .chat-error-card-soft heading — both are AA-compliant variants per UI-SPEC §H + §G WCAG-AA rationale (4.74:1 and 5.37:1 respectively)"

requirements-completed: [D-CHAT-04, D-CHAT-05, D-CHAT-07, D-CHAT-08, D-CHAT-09, D-CHAT-10, D-CHAT-11, D-CHAT-12, D-CHAT-13, D-CHAT-14, D-CHAT-01]

# Metrics
duration: ~12min
completed: 2026-05-02
---

# Phase 03 Plan 04: Atomic Ask Router Rewrite + Chat Templates + CSS Summary

**Wave 3 atomic commit boundary (D-CHAT-09): rewrite app_v2/routers/ask.py end-to-end, atomically delete the 3 NL-05 templates and the Phase 6 invariants test file in the same commit, ship 8 new chat templates covering UI-SPEC §A–§I, append the Phase 3 chat-surface CSS block to app.css. The user-visible payload of Phase 3: navigating to /ask now shows the new chat shell.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-02T18:42:24Z
- **Completed:** 2026-05-02T18:54:54Z
- **Tasks:** 4 / 4 (Task 1, 2a, 2b, 4)
- **Files modified:** 3 (router, index.html, app.css)
- **Files created:** 8 (7 new templates + deferred-items.md)
- **Files deleted:** 4 (3 NL-05 templates + Phase 6 invariants test)
- **Tests:** 431 passed, 1 failed, 13 errored, 5 skipped (all 14 failures/errors are documented as deferred to plan 03-05; net change vs baseline: -33 tests, of which -19 are the intentional `test_phase06_invariants.py` deletion)

## Accomplishments

- **Task 1 — atomic router rewrite + 4 deletions in one commit (`7ff01b6`):**
  - Rewrote `app_v2/routers/ask.py` end-to-end: 4 routes (`GET /ask`, `POST /ask/chat`, `GET /ask/stream/{turn_id}`, `POST /ask/cancel/{turn_id}`); removed `POST /ask/query` and `POST /ask/confirm` (D-CHAT-09).
  - `pbm2_session` cookie helper (`uuid4().hex`, `HttpOnly`, `SameSite=Lax`, `Secure=False`, `max_age=31536000`) — set in `GET /ask` + `POST /ask/chat`.
  - Session-cookie ownership check on `/ask/stream` + `/ask/cancel` — 403 on mismatch, 404 on unknown turn (T-03-04-01/02 mitigations).
  - `_hydrate_final_card` — WARNING-3 PINNED CONTRACT: receives `{summary, sql, chart_spec_dict, new_messages}` from chat_loop; runs SAFE-02..06 (validate_sql + inject_limit + READ ONLY tx + max_execution_time) on the agent SQL; renders the Browse `_grid.html` macro through a tiny `_GridVM` view-model; constructs Plotly chart via `plotly.graph_objects.Figure(...).to_html(include_plotlyjs=False, full_html=False)` with silent downgrade when `chart_spec.x_column` / `y_column` missing in `df.columns`; persists `new_messages` via `append_session_history`.
  - `_unconfigured_event_generator` — single SSE error frame for the no-LLM / no-DB / no-agent_cfg case.
  - Atomically deleted `app_v2/templates/ask/_confirm_panel.html`, `_abort_banner.html`, `_answer.html`, and `tests/v2/test_phase06_invariants.py` in the SAME commit per D-CHAT-09 atomic-cleanup contract (the test deletion was moved here from plan 03-05 because Phase 6 contracts no longer hold once the route is rewritten).

- **Task 2a — chat shell skeleton (`58081d2`):** new `index.html` (extends base.html, opens `extra_head` to load Plotly + htmx-ext-sse, single `.panel` with `<h1 class="panel-title">Ask</h1>` + LLM dropdown verbatim from Phase 6 + `#chat-transcript` region with `aria-live="polite"` + `#input-zone` wrapper); new `_input_zone.html` (idle form, posts to `/ask/chat`, "Your question" label, v2.0 placeholder, "Run" CTA, "Clear question" aria-label); new `_user_message.html` (question + "Thinking…" placeholder + SSE consumer wrapping `sse-connect` + `sse-swap` + `sse-close="final error"` + OOB swap of `<button class="btn-stop">Stop</button>` into `#input-zone`).

- **Task 2b — 5 event partials (`d50b51d`):**
  - `_thought_event.html` — `<details class="chat-thought">` with 140-char `truncated` + full `full_content` (D-CHAT-12).
  - `_tool_call_pill.html` — `<details class="chat-pill-tool-call">` violet mono pill (D-CHAT-13).
  - `_tool_result_pill.html` — single template branched by `{{ rejected }}` to emit `chat-pill-tool-result-ok` (green, with truncated 10-row preview table) or `chat-pill-tool-result-rejected` (red, with full reason).
  - `_final_card.html` — three vertical sections: `chat-summary-callout`, Browse `table_html` + row-count caption, Plotly `chart_html`; trailing OOB swap to flip `#input-zone` back to idle. `| safe` whitelisted to `table_html` and `chart_html` only (both router-pre-rendered).
  - `_error_card.html` — single template branched by `{{ severity }}` to emit `chat-error-card-hard` or `chat-error-card-soft`; conditional Retry CTA gated on `{{ original_question }}`; trailing OOB swap to idle.
  - All agent-supplied template variables use Jinja's `| e` autoescape filter (T-03-04-04). The only `| safe` filter use across all 8 templates is on `table_html` and `chart_html` in `_final_card.html`.

- **Task 4 — chat-surface CSS (`45efb7f`):** appended a single `Phase 3 — Chat surface` comment-delimited block (186 insertions, 0 deletions) to `app_v2/static/css/app.css`. Implements every selector pinned in UI-SPEC §C–§H plus the AA-compliant color overrides for `.btn-stop` (`#cc2434`) and `.chat-error-card-soft strong` (`#8a5a00`). `tokens.css` untouched (no new tokens added per RESEARCH Gap 15).

## Task Commits

Each task committed atomically:

1. **Task 1: router rewrite + 4 atomic deletions (D-CHAT-08/09)** — `7ff01b6` (feat)
2. **Task 2a: chat-shell skeleton — index.html + _input_zone + _user_message** — `58081d2` (feat)
3. **Task 2b: 5 event partials — thought, tool_call, tool_result, final_card, error_card** — `d50b51d` (feat)
4. **Task 4: append Phase 3 chat-surface CSS to app.css (D-CHAT-07)** — `45efb7f` (feat)

## Files Created/Modified

### Created (7 templates + 1 deferred-items doc)
- `app_v2/templates/ask/_user_message.html`
- `app_v2/templates/ask/_input_zone.html`
- `app_v2/templates/ask/_thought_event.html`
- `app_v2/templates/ask/_tool_call_pill.html`
- `app_v2/templates/ask/_tool_result_pill.html`
- `app_v2/templates/ask/_final_card.html`
- `app_v2/templates/ask/_error_card.html`
- `.planning/phases/03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on/deferred-items.md`

### Modified (3)
- `app_v2/routers/ask.py` — rewritten end-to-end (~330 → ~410 lines; 4 routes; new `_hydrate_final_card`, `_GridVM`, `_build_plotly_chart_html`, `_unconfigured_event_generator`, `_ensure_session_cookie` helpers).
- `app_v2/templates/ask/index.html` — rewritten end-to-end (extra_head + chat-transcript + input-zone + LLM dropdown verbatim).
- `app_v2/static/css/app.css` — pure-append (186 insertions, 0 deletions) under "Phase 3 — Chat surface" header.

### Deleted (4)
- `app_v2/templates/ask/_confirm_panel.html`
- `app_v2/templates/ask/_abort_banner.html`
- `app_v2/templates/ask/_answer.html`
- `tests/v2/test_phase06_invariants.py` (moved here from plan 03-05 per the atomic-cleanup contract)

## Decisions Made

1. **Atomic Task 1 commit** covers router rewrite + 3 NL-05 template deletions + Phase 6 invariants test deletion. D-CHAT-09 explicitly forbids a working tree with half-deleted artifacts; the plan moved the test file deletion FROM plan 03-05 INTO this task because once the Phase 6 routes + templates are removed, the test file's `forbidden = "async" + " " + "def"` and `assert 'id="answer-zone"' in src` checks no longer hold and would fail the entire test suite at the Wave 3 commit boundary.

2. **Router applies SAFE-02..06 harness directly via `validate_sql` + `inject_limit` + `sa.text("SET SESSION TRANSACTION READ ONLY")` + `sa.text(f"SET SESSION max_execution_time={timeout_ms}")`** — does NOT call `chat_agent._execute_and_wrap`. That helper is module-private; reusing it would force a public-API extraction with this router as its sole external consumer. The duplicated harness code is the same compromise plan 03-02 made (verbatim port over shared helper) for the same D-CHAT-09 preservation reason.

3. **Plotly imported lazily inside `_build_plotly_chart_html`** via `import plotly.graph_objects as go` — top-level module import surface stays free of plotly. Browse / Joint Validation / Settings requests that route through other routers do not pay the plotly import cost. (Note: this still triggers `test_phase04_invariants.py::test_no_banned_export_or_chart_libraries_imported_in_app_v2[plotly]` because the regex matches any `import plotly` line; that test rewrite is deferred to plan 03-05 — see Deferred Issues below.)

4. **`_GridVM` is a tiny ad-hoc class (8 lines)** — does NOT import or subclass `BrowseViewModel`. Reused only the two attributes `browse/_grid.html` reads (`df_wide`, `index_col_name`). Avoids cross-feature coupling.

5. **Final-card pivot index column = `df.columns[0]`.** The agent's `PresentResult.sql` is a plain SELECT (no pivot); we render the result DataFrame as-is using the first column as the row label. Natural for `SELECT PLATFORM_ID, …` queries.

6. **`_unconfigured_event_generator` returns 200 + single SSE error frame** (not 503). Aligns with Phase 6's ALWAYS-200 contract for the user-facing flow — the user sees the error card inline, not a browser-level error page.

7. **Stop button is rendered inline by `_user_message.html`** as an OOB swap into `#input-zone` (no separate `_input_zone_active.html`). The active state is a single `<button class="btn-stop">Stop</button>` element; making a dedicated template for it would be over-engineering. `_input_zone.html` itself renders ONLY the idle (form) state.

8. **`_starter_chips.html` stays on disk untouched.** RESEARCH Gap 13 audit shows no remaining consumer (only an explanatory docstring in `templates/browse/_picker_popover.html` line 32, which is text content not an include). Deleting it adds no value; keeping it allows a hypothetical future plan to reintroduce starter prompts without a code-archaeology step.

9. **LLM dropdown HTML lifted byte-for-byte from Phase 6 (D-CHAT-11).** Same Bootstrap classes (`dropdown`, `dropdown-toggle`, `ms-auto`, `dropdown-menu-end`), same `hx-post="/settings/llm"` + `hx-vals` + `hx-swap="none"`, same `backend_name` + `llms` context vars, same trigger label format `LLM: {{ backend_name }} ▾`. Verified by visual diff between old and new `index.html`.

10. **app.css append uses `#cc2434` for `.btn-stop` text+border and `#8a5a00` for `.chat-error-card-soft strong`** — AA-compliant variants per UI-SPEC §H + §G WCAG-AA rationale (`4.74:1` and `5.37:1` respectively, vs `--red`'s `3.85:1` and `--amber`'s `1.95:1` which fail or barely pass for text). These hex literals are NOT promoted to tokens (RESEARCH Gap 15 — bake one-off values into rules).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Removed `agent.run_sync` literal mentions from new docstrings**

- **Found during:** Task 1 verification.
- **Issue:** Initial docstrings in the rewritten `app_v2/routers/ask.py` carried the literal phrase `agent.run_sync` in three explanatory comments ("does not call run_sync", "forbids agent.run_sync calls", "the body does not call agent.run_sync"). The plan's acceptance grep is `! grep -q "agent\\.run_sync\|\\.run_sync("` — it does not distinguish between docstring mentions and actual call sites.
- **Fix:** Reworded the three docstring lines to say "pure registry mutation" / "any synchronous PydanticAI runner call" instead of citing `agent.run_sync` literally. The semantic intent is preserved; the file no longer contains the substring.
- **Files modified:** `app_v2/routers/ask.py`
- **Commit:** `7ff01b6` (caught before commit).

No other deviations from plan. All 4 tasks executed exactly as specified, including the WARNING-3 pinned final-card contract, the atomic deletion contract, the LLM dropdown verbatim port, and the AA-compliant color overrides.

## Deferred Issues

Documented in `.planning/phases/03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on/deferred-items.md`. Two categories — both explicitly noted by the plan as "rewritten/replaced in plan 05":

1. **`test_phase04_invariants.py::test_no_banned_export_or_chart_libraries_imported_in_app_v2[plotly]`** now fails because the new `app_v2/routers/ask.py` introduces server-side Plotly chart construction (D-CHAT-05 + T-03-04-09 mitigation; the bundle was vendored in plan 03-01 specifically for this purpose). Plan 03-05 either narrows the invariant to whitelist `app_v2/routers/ask.py` or deletes the `plotly` parametrize entry.

2. **13 errored tests in `tests/v2/test_ask_routes.py`** — every test in that file asserts on Phase 6 contracts (`POST /ask/query`, `POST /ask/confirm`, `_answer.html`, `_confirm_panel.html`, `_abort_banner.html`, `loop-aborted` reason). Plan 03-05 rewrites or deletes the file end-to-end and replaces it with new tests covering the Phase 3 4-route surface + session-cookie 403 gate + SSE event ordering.

Test-count math: 431 passed + 1 failed + 13 errored + 5 skipped = 450 total observed; plan 03-03 baseline was 464 passed + 5 skipped = 469 total; the difference (-19) is exactly the 19-test `test_phase06_invariants.py` file we deleted intentionally. The 14 remaining failures/errors (1 failed + 13 errored) match the plan's documented expectation.

## Issues Encountered

None beyond the auto-fix above.

## User Setup Required

None — no external service configuration. The new `pbm2_session` cookie is set automatically on first GET `/ask` visit; the LLM dropdown still uses the existing `pbm2_llm` cookie threading from v2.0 Phase 6.

## Verification Performed

### Per-task verification

**Task 1:**
- 4-file deletion: `test ! -e _confirm_panel.html && test ! -e _abort_banner.html && test ! -e _answer.html && test ! -e tests/v2/test_phase06_invariants.py` → all pass.
- Route shape: `python -c "from app_v2.routers.ask import router; assert {'/ask','/ask/chat','/ask/stream/{turn_id}','/ask/cancel/{turn_id}'} ⊂ {r.path for r in router.routes} and '/ask/query' not in ... and '/ask/confirm' not in ..."` → OK.
- Substring greps: `_PBM2_SESSION_COOKIE = "pbm2_session"`, `def _hydrate_final_card`, `EventSourceResponse`, `from app.core.agent.chat_loop import stream_chat_turn`, `include_plotlyjs=False` all present; `agent.run_sync`, `/ask/query`, `/ask/confirm`, `starter_prompts`, `app.state.db_adapter` all absent.
- Smoke: `GET /ask` returns 200.

**Task 2a:**
- All 3 chat-shell template files exist and non-empty.
- `index.html` contains: `panel-title`, `chat-transcript`, `input-zone`, `aria-live="polite"`, `vendor/plotly/plotly.min.js`, `vendor/htmx/htmx-ext-sse.js`, `LLM:`. Does NOT contain `_starter_chips.html` or `id="answer-zone"`.
- `_user_message.html` contains: `sse-connect="/ask/stream/{{ turn_id }}"`, `sse-swap="thought,tool_call,tool_result,final,error"`, `sse-close="final error"`, `hx-swap-oob="true"`, `Thinking…`.
- `_input_zone.html` contains: `hx-post="/ask/chat"`, the placeholder copy, `Your question`, `Run`, `aria-label="Clear question"`.

**Task 2b:**
- All 5 event-partial files exist and non-empty.
- Each partial contains the UI-SPEC §C–§G class names + aria-labels.
- Smoke render with stub data via `templates.get_template(...).render(...)` succeeds for all 5 partials; `<b>` agent-supplied input renders as `&lt;b&gt;` (autoescape working).
- `| safe` filter audit: only `table_html` and `chart_html` in `_final_card.html` — every other partial passes the bare `grep "| safe" ... | grep -v -E "table_html|chart_html"` check (only docstring comments saying "NO | safe" remain, which are non-rendered).

**Task 4:**
- All UI-SPEC §C–§H selector greps pass (`.chat-thought`, `.chat-pill-tool-call`, `.chat-pill-tool-result-ok`, `.chat-pill-tool-result-rejected`, `.chat-summary-callout`, `.chat-plotly`, `.chat-error-card-hard`, `.chat-error-card-soft`, `.btn-stop`, `:focus-visible`, `prefers-reduced-motion`).
- AA color literals present: `#cc2434`, `#8a5a00`.
- No new `--chat-*` tokens added to `:root`.
- `git diff app_v2/static/css/tokens.css` returns 0 lines (untouched).
- `git diff --stat app_v2/static/css/app.css` shows 186 insertions, 0 deletions (pure-append).

### Plan-level verification

- `pytest tests/v2/test_main.py -x` → 18 passed, 2 skipped (zero regressions in the smoke-test boundary).
- Full suite: 431 passed + 1 failed + 13 errored + 5 skipped — the 14 failures/errors are documented in deferred-items.md as the plan's deliberate "rewritten in plan 05" set; the math `464 baseline - 19 deleted - 14 deferred = 431 net passing` checks out.
- `GET /ask` smoke: returns 200 with the new chat-shell HTML (panel-title `<h1>Ask</h1>`, `#chat-transcript`, `#input-zone`, Plotly + htmx-ext-sse script tags via `extra_head`, no `answer-zone`, no `starter_chips`).

## Threat Surface Audit

Per the plan's `<threat_model>`:

- **T-03-04-01 (Spoofing / Information Disclosure on `/ask/stream`):** mitigated. `request.cookies.get("pbm2_session")` compared against `chat_session.get_session_id_for_turn(turn_id)`; mismatch returns 403, missing turn returns 404. `turn_id` itself is `uuid4().hex` (128-bit entropy). Verified at `app_v2/routers/ask.py` `ask_stream` body.
- **T-03-04-02 (Tampering on `/ask/cancel`):** mitigated. Same session-cookie ownership gate as the SSE endpoint; same 403/404 disposition.
- **T-03-04-03 (Tampering / EoP via LLM-generated SQL):** mitigated. Two backstops both fire: (a) `chat_agent._execute_and_wrap` runs `validate_sql` + `inject_limit` + READ ONLY tx + `max_execution_time` + `scrub_paths` on every `run_sql` tool invocation (plan 02); (b) the router `_hydrate_final_card` re-runs the SAFE-02..06 harness on `PresentResult.sql` before executing it server-side. Read-only DB user (CLAUDE.md project rule) is the primary backstop.
- **T-03-04-04 (Information Disclosure via agent-string XSS):** mitigated. Every agent-supplied template variable uses `{{ var | e }}` autoescape. `| safe` is whitelisted to `table_html` (router-rendered Browse macro — every cell already escaped) and `chart_html` (router-constructed Plotly figure — Plotly internally escapes column values). No agent-supplied string flows into a `| safe` filter anywhere.
- **T-03-04-05 (Cookie information disclosure):** accepted. `pbm2_session` is `HttpOnly + SameSite=Lax + Secure=False` per RESEARCH Pitfall 8 / Gap 6 (intranet HTTP). Anonymous identifier — no PII bound.
- **T-03-04-06 (DoS via long SSE):** mitigated. `chat_max_steps` (default 12) caps tool calls per turn; `agent_cfg.timeout_s` (default 30s) caps each SQL; `BackgroundTask(pop_turn, turn_id)` cleans up the per-turn registry on connection close.
- **T-03-04-07 (Plotly bundle on every page):** mitigated. The `<script src=".../plotly.min.js" defer>` tag lives inside `{% block extra_head %}` on `ask/index.html` only — Browse / JV / Settings inherit `base.html`'s empty default `extra_head` block.
- **T-03-04-08 (NL-05 templates left on disk):** mitigated. All 3 templates atomically deleted in Task 1's commit. `find app_v2/templates/ask -name "_confirm_panel.html" -o -name "_abort_banner.html" -o -name "_answer.html"` returns empty.
- **T-03-04-09 (Plotly `| safe` exploitation):** mitigated. The router constructs `chart_html` server-side via `plotly.graph_objects.Figure(...).to_html(include_plotlyjs=False, full_html=False)` — `ChartSpec` fields are typed (`Literal["bar","line","scatter","none"]` for chart_type, plain str for column names). The agent only picks COLUMN NAMES; the router validates each name via `chart_spec.x_column in df.columns and chart_spec.y_column in df.columns` and silently downgrades to `chart_type="none"` (no chart) when missing. Plotly does its own escaping of column values inside the figure.

No new threat flags surfaced beyond the plan's pre-registered set.

## Threat Flags

None — no new security-relevant surface introduced beyond what the plan's `<threat_model>` already enumerated. The router introduces 4 new routes (already covered by T-03-04-01/02), session cookie (T-03-04-05), Plotly server-side render (T-03-04-09), and SAFE-02..06 reapplication on agent SQL (T-03-04-03) — all pre-registered.

## Next Phase Readiness

After this plan, navigating to `/ask` in a browser shows the new chat shell. Submitting a question kicks off the multi-step agent loop with SSE-streamed events. Plan 03-05 (the final wave) cleans up:

1. Rewrites `tests/v2/test_ask_routes.py` against the new 4-route surface (currently 13 errored tests there).
2. Narrows or removes the Phase 4 `test_no_banned_export_or_chart_libraries_imported_in_app_v2[plotly]` invariant to whitelist `app_v2/routers/ask.py` (currently 1 failed test there).
3. Adds new Phase 3 invariant tests: `async def` allowed only on `/ask/stream` and `/ask/cancel`; `| safe` filter whitelisted only on `table_html` / `chart_html` in `_final_card.html`; `_starter_chips.html` not included anywhere; etc.

## Self-Check

Verified file existence and commit hashes:

- `app_v2/routers/ask.py` (modified) → FOUND, contains `EventSourceResponse`, `_hydrate_final_card`, 4-route shape, no `/ask/query` or `/ask/confirm`
- `app_v2/templates/ask/index.html` (modified) → FOUND, contains `panel-title`, `chat-transcript`, `input-zone`, Plotly + htmx-ext-sse script tags
- `app_v2/templates/ask/_user_message.html` → FOUND
- `app_v2/templates/ask/_input_zone.html` → FOUND
- `app_v2/templates/ask/_thought_event.html` → FOUND
- `app_v2/templates/ask/_tool_call_pill.html` → FOUND
- `app_v2/templates/ask/_tool_result_pill.html` → FOUND
- `app_v2/templates/ask/_final_card.html` → FOUND
- `app_v2/templates/ask/_error_card.html` → FOUND
- `app_v2/templates/ask/_confirm_panel.html` → DELETED
- `app_v2/templates/ask/_abort_banner.html` → DELETED
- `app_v2/templates/ask/_answer.html` → DELETED
- `tests/v2/test_phase06_invariants.py` → DELETED
- `app_v2/static/css/app.css` (modified) → FOUND, contains `Phase 3 — Chat surface` block, `#cc2434`, `#8a5a00`, `prefers-reduced-motion`
- `.planning/phases/03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on/deferred-items.md` → FOUND
- Commit `7ff01b6` (Task 1) → FOUND in git log
- Commit `58081d2` (Task 2a) → FOUND in git log
- Commit `d50b51d` (Task 2b) → FOUND in git log
- Commit `45efb7f` (Task 4) → FOUND in git log

## Self-Check: PASSED

---
*Phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on*
*Plan: 04*
*Completed: 2026-05-02*
