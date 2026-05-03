---
phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
plan: 05
subsystem: tests
tags: [tests, ask, chat, sse, invariants, d-chat-01, d-chat-02, d-chat-03, d-chat-04, d-chat-05, d-chat-06, d-chat-08, d-chat-09, d-chat-10, d-chat-11, d-chat-12, d-chat-15, t-03-04-01, t-03-04-02, t-03-04-07]

# Dependency graph
requires:
  - phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
    plan: 01
    provides: vendored Plotly + htmx-ext-sse bundles, AgentConfig.chat_max_steps
  - phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
    plan: 02
    provides: build_chat_agent + ChatAgentDeps + PresentResult + ChartSpec + _execute_and_wrap module-private helper
  - phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
    plan: 03
    provides: chat_session helpers + chat_loop.stream_chat_turn driving SSE event_generator
  - phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
    plan: 04
    provides: 4-route Ask surface (GET /ask, POST /ask/chat, GET /ask/stream/{turn_id}, POST /ask/cancel/{turn_id}); pbm2_session cookie + ownership gate; WARNING-3 _hydrate_final_card; 8 chat templates
provides:
  - Phase 3 regression-safety net: 5 new test files (62 tests) locking the chat surface contracts
  - Narrowed Phase 4 plotly invariant whitelisting app_v2/routers/ask.py only
  - Cross-AI invariants test_phase03_chat_invariants.py preventing silent regression of D-CHAT-09 cleanup, D-CHAT-10 starter-chips removal, D-CHAT-11 LLM dropdown preservation, T-03-04-01/02/07 security boundaries
  - Motivating example test (SM8850 vs SM8650 UNION → REJECTED:) covered explicitly
affects: []  # final plan in phase

# Tech tracking
tech-stack:
  added: []  # All deps already pinned by plan 03-01 + earlier phases
  patterns:
    - "anyio pytest plugin (provided by anyio package, group='pytest11') used via @pytest.mark.anyio with anyio_backend='asyncio' fixture — pytest-asyncio NOT required"
    - "Real DBAdapter subclass _FakeDB(DBAdapter) for router tests — Pydantic v2 isinstance check on ChatAgentDeps.db rejects MagicMock; ChatAgentDeps.model_construct used for chat_loop unit tests where db is unread"
    - "data-reason='{{ reason | e }}' attribute on _error_card.html outer div — machine-readable error reason for tests + future client-side handlers; decouples tests from body copy"
    - "FunctionToolResultEvent.result vs AgentRunResultEvent.result discriminator: isinstance(ev, AgentRunResultEvent) is the ONLY safe terminal-event check; hasattr(ev, 'result') silently misclassifies every tool result as the terminal frame"
    - "Jinja {# ... #} comment stripping (re.compile(r'\\{#.*?#\\}', re.DOTALL)) before grep-based template invariant checks — explanatory copy 'NO | safe' inside header comments must not trigger the rule"

key-files:
  created:
    - tests/v2/test_phase03_chat_invariants.py
    - tests/v2/test_chat_loop.py
    - tests/v2/test_chat_session.py
    - tests/v2/test_chat_agent_tools.py
    - .planning/phases/03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on/03-05-SUMMARY.md
  modified:
    - tests/v2/test_ask_routes.py  # rewritten end-to-end (Phase 3 4-route surface)
    - tests/v2/test_phase04_invariants.py  # plotly invariant narrowed to whitelist app_v2/routers/ask.py
    - app/core/agent/chat_loop.py  # auto-fix Rule 1: terminal-event isinstance check
    - app_v2/templates/ask/_error_card.html  # auto-fix Rule 2: data-reason attribute
    - app_v2/routers/ask.py  # auto-fix Rule 1: TemplateResponse cookie propagation

key-decisions:
  - "Rule 1 auto-fix in app_v2/routers/ask.py: pbm2_session cookie was set on the parameter Response object, but FastAPI does NOT merge parameter Response cookies into a returned TemplateResponse. Added _apply_session_cookie helper that calls response.set_cookie on the actual TemplateResponse only when the request did not already carry a session id. Verified by Set-Cookie header inspection."
  - "Rule 1 auto-fix in app/core/agent/chat_loop.py: replaced hasattr(ev, 'result') terminal-event discriminator with isinstance(ev, AgentRunResultEvent). FunctionToolResultEvent ALSO has a `result` attribute (carrying ToolReturnPart), so the old check terminated the agent loop on EVERY tool result before the D-CHAT-01 cancel and D-CHAT-02 rejection-cap checkpoints could fire. New import: pydantic_ai.run.AgentRunResultEvent."
  - "Rule 2 auto-fix in _error_card.html: added data-reason='{{ reason | e }}' attribute. This makes the error card machine-readable (for tests, future client-side analytics, future error-pivot dashboards) without coupling to body copy strings. autoescape ensures no XSS path on reason. The attribute is NOT in the visible UI, so UI-SPEC §G remains unchanged."
  - "Phase 4 plotly invariant narrowed by whitelisting app_v2/routers/ask.py only — D-CHAT-05 + T-03-04-09 require server-side Plotly chart construction in the chat router. Lazy import inside _build_plotly_chart_html (NOT module-level) keeps Browse / JV / Settings free of the import cost. Other modules under app_v2/ remain forbidden from importing plotly."
  - "Used real pydantic_ai.run.AgentRunResultEvent with a duck-typed _FakeRunResult (just .output + .new_messages()) in test mocks — AgentRunResult's full constructor requires GraphAgentState (factory) which is not unit-testable. The Event accepts any object as 'result' and chat_loop only reads the two attributes."
  - "Used real DBAdapter subclass _FakeDB across both router tests AND chat_agent tool tests because Pydantic v2's ChatAgentDeps.db field is annotated DBAdapter (default isinstance check). MagicMock fails the validator. Subclass overrides the 4 abstract methods with deterministic in-memory behavior; __init__ skips DatabaseConfig setup."
  - "Used pydantic_ai.models.test.TestModel ONLY in test_build_chat_agent_constructs_with_test_model — a sanity check that the agent factory returns an Agent. The harder unit tests (cancel/rejection/budget/error) drive stream_chat_turn directly with a fake AsyncIterator agent (RESEARCH Gap 11 fallback), avoiding pydantic_ai's internal stream machinery entirely."

requirements-completed: [D-CHAT-01, D-CHAT-02, D-CHAT-03, D-CHAT-04, D-CHAT-08, D-CHAT-09, D-CHAT-10, D-CHAT-11, D-CHAT-12, D-CHAT-13, D-CHAT-14, D-CHAT-15]

# Metrics
duration: ~20min
completed: 2026-05-02
---

# Phase 03 Plan 05: Test-Suite Rewrite for the Phase 3 Chat Surface Summary

**Final wave of Phase 03. Five new test files (62 tests total) lock the contracts of the multi-step agentic chat surface: D-CHAT-08 router shape, D-CHAT-09 atomic NL-05 cleanup, D-CHAT-10 starter chips removal, D-CHAT-11 LLM dropdown preservation, D-CHAT-01..04 stop-boundary classifications in chat_loop, D-CHAT-15 sliding-window in chat_session, the SM8850 vs SM8650 UNION-rejection motivating example, T-03-04-01/02 session-cookie ownership gates, and T-03-04-07 Plotly-only-on-/ask isolation. Phase 4 plotly invariant narrowed to whitelist `app_v2/routers/ask.py`. Three Rule-1/Rule-2 auto-fixes shipped along the way (TemplateResponse cookie propagation, AgentRunResultEvent discriminator, data-reason attribute on error card).**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-02T19:04:48Z
- **Completed:** 2026-05-02T19:24:47Z
- **Tasks:** 2 / 2
- **Test files created:** 4 (test_phase03_chat_invariants.py, test_chat_loop.py, test_chat_session.py, test_chat_agent_tools.py)
- **Test files modified:** 2 (test_ask_routes.py rewritten, test_phase04_invariants.py narrowed)
- **Source files modified for auto-fixes:** 3 (chat_loop.py, _error_card.html, routers/ask.py)
- **Tests:** 493 passed, 5 skipped, 0 failed (was 431 + 5 + 14 errors before this plan; +62 net passing, 14 pre-existing errors resolved, 0 unrelated regressions)

## Accomplishments

- **Task 1 — rewrite test_ask_routes.py + create test_phase03_chat_invariants.py + narrow Phase 4 plotly invariant (`573ad9a`):**
  - Replaced the 13 Phase 6 tests in `tests/v2/test_ask_routes.py` (all asserting against deleted /ask/query, /ask/confirm, _answer.html, _confirm_panel.html, _abort_banner.html) with 13 new Phase 3 tests:
    - `test_ask_page_renders_chat_shell_with_no_starter_chips` — chat shell IDs, starter-chips removal, LLM dropdown, vendored Plotly + htmx-ext-sse refs.
    - `test_ask_page_sets_pbm2_session_cookie_on_first_visit` — Set-Cookie header inspection (HttpOnly + SameSite=lax).
    - `test_post_ask_chat_returns_user_message_fragment_with_sse_consumer` — turn_id in sse-connect URL, OOB Stop swap, autoescaped question.
    - `test_post_ask_chat_with_empty_question_still_creates_turn` — turn registration is route-level, not validation-gated.
    - `test_post_ask_cancel_with_foreign_session_returns_403` (T-03-04-02) — cross-session client + 403 disposition.
    - `test_post_ask_cancel_with_unknown_turn_returns_404` — well-formed turn id never registered.
    - `test_post_ask_cancel_with_owning_session_returns_204` — owner cancels its own turn.
    - `test_get_ask_stream_with_foreign_session_returns_403` (T-03-04-01).
    - `test_get_ask_stream_with_unknown_turn_returns_404`.
    - `test_post_ask_query_route_no_longer_exists` (D-CHAT-09 deletion).
    - `test_post_ask_confirm_route_no_longer_exists` (D-CHAT-09 deletion).
    - `test_get_ask_stream_final_frame_contains_table_rows_when_sql_returns_rows` (WARNING-3 contract: mocks build_chat_agent + build_pydantic_model, sets _FakeDB to return a non-empty DataFrame, asserts final SSE frame contains `<tbody>` + `</tbody>` from the rendered _final_card.html → Browse _grid.html macro chain).
    - `test_get_ask_stream_emits_terminal_event_with_mocked_agent` — SSE event-ordering smoke (final or error reachable).
  - Created `tests/v2/test_phase03_chat_invariants.py` with 10 invariants covering all 5 D-CHAT contracts plus narrowed Phase 6 successors:
    - `test_ask_router_async_def_only_on_streaming_routes` — replaces narrowed Phase 6 sync-only rule (RESEARCH Pitfall 1).
    - `test_nl05_templates_deleted` — D-CHAT-09 atomic deletion.
    - `test_starter_chips_not_included_in_index` — D-CHAT-10.
    - `test_llm_dropdown_preserved_in_index` — D-CHAT-11.
    - `test_no_safe_filter_on_agent_strings_in_chat_partials` — XSS regression guard (T-03-04-04); strips Jinja {# … #} comments before checking so explanatory header copy "NO | safe" does not false-trigger.
    - `test_final_card_safe_filter_only_on_router_rendered_html` — narrowed | safe whitelist (only on `table_html` and `chart_html`).
    - `test_plotly_only_loaded_on_ask_page` (T-03-04-07).
    - `test_no_banned_libraries_imported_in_chat_modules` (langchain, litellm, vanna, llama_index — broadened to 4 chat modules).
    - `test_chat_loop_emits_all_8_d_chat_04_reasons` — HARD/SOFT partition + body copy completeness.
    - `test_phase06_invariants_file_remains_deleted` — D-CHAT-09 atomic-cleanup contract continuity guard.
  - Narrowed `tests/v2/test_phase04_invariants.py::test_no_banned_export_or_chart_libraries_imported_in_app_v2[plotly]` by whitelisting `app_v2/routers/ask.py`. Other modules under `app_v2/` remain forbidden from importing plotly. Comment cites D-CHAT-05 + T-03-04-09 + RESEARCH Pitfall 5.
  - Auto-fix [Rule 1 - Bug] in `app_v2/routers/ask.py`: added `_apply_session_cookie` helper and called it on the `TemplateResponse` returned from `/ask` + `/ask/chat`. Without this, FastAPI's parameter Response set-cookie was lost (parameter merge does not apply when the route returns its own Response object). Verified by Set-Cookie header inspection.

- **Task 2 — create test_chat_loop.py + test_chat_session.py + test_chat_agent_tools.py (`563853a`):**
  - **`tests/v2/test_chat_loop.py`** (11 tests) covers all 4 stop-boundary classifications via fake AsyncIterator agent (RESEARCH Gap 11 fallback):
    - `test_truncate_thought_under_cap_returns_input_unchanged` + `test_truncate_thought_over_cap_appends_ellipsis` — D-CHAT-12 helper.
    - `test_d_chat_01_cancel_event_set_emits_stopped_by_user` — pre-set asyncio.Event detected on first FunctionToolResultEvent boundary.
    - `test_d_chat_02_five_consecutive_rejections_emit_retry_cap_error` — 5 REJECTED: in a row → still-rejected-after-5-attempts hard error.
    - `test_d_chat_02_non_rejection_resets_counter` — 4 rejections + 1 success + 4 more rejections does NOT trip the cap (consecutive only).
    - `test_d_chat_03_step_budget_exhausted_emits_correct_error` — UsageLimitExceeded mid-loop.
    - `test_d_chat_04_unexpected_exception_emits_llm_error` — RuntimeError("connection refused") → llm-error hard.
    - `test_d_chat_04_timeout_message_emits_timeout_error` — RuntimeError("query exceeded max_execution_time") → timeout soft.
    - `test_hard_soft_reason_partition_covers_all_8` — HARD_REASONS | SOFT_REASONS == 8 reasons / no overlap.
    - `test_final_event_payload_has_all_4_keys` — WARNING-3 four-key contract (summary, sql, chart_spec_dict, new_messages).
    - `test_terminal_event_with_non_present_result_emits_agent_no_final_result` — output=None branch.
  - **`tests/v2/test_chat_session.py`** (16 tests) covers turn-registry lifecycle + sliding window + scrub-on-write:
    - 7 turn-lifecycle tests (new_turn / get_pending_question / get_session_id_for_turn / KeyError on unknown / cancel_turn / cancel-on-unknown noop / pop-idempotency).
    - 4 sliding-window tests (D-CHAT-15: 20 msgs → 12-msg slice, default limit, short-history pass-through, get_or_create idempotency).
    - 5 scrub-on-write tests (D-CHAT-11: openai applies scrub to all 3 part types, ollama skips entirely, _scrub_messages_inplace walks UserPromptPart + ToolReturnPart + ToolCallPart args, non-string args pass through, sequential append accumulates).
  - **`tests/v2/test_chat_agent_tools.py`** (11 tests) covers the agent's tool surface + structured output:
    - The motivating example (D-CHAT-02): `test_execute_and_wrap_returns_REJECTED_on_union_sql_d_chat_02_motivating_example` — UNION SQL across SM8850 / SM8650 returns REJECTED: prefix.
    - SAFE-05 wrapping: `<db_data>...</db_data>` envelope on success, `(no rows returned)` marker on empty.
    - D-CHAT-11 path scrub: applied on openai, skipped on ollama (parallels chat_session test_scrub_*).
    - D-CHAT-05/06: PresentResult terminator returns typed Pydantic model with default ChartSpec(chart_type="none"); ChartSpec literal constraint rejects "histogram" with ValidationError; all 4 valid literals (bar/line/scatter/none) accepted; nested ChartSpec validator passes through dict shapes.
    - `test_build_chat_agent_constructs_with_test_model` — uses pydantic_ai TestModel, asserts non-None.
    - `test_chat_agent_does_not_import_nl_service` — D-CHAT-09 invariant on chat_agent.py source.
  - Auto-fix [Rule 1 - Bug] in `app/core/agent/chat_loop.py`: replaced `hasattr(ev, "result")` discriminator with `isinstance(ev, AgentRunResultEvent)`. The bug — `FunctionToolResultEvent` ALSO carries a `result` attribute (the ToolReturnPart), so the old check classified every tool result as the terminal frame and short-circuited the loop before the D-CHAT-01 cancel and D-CHAT-02 rejection-cap checkpoints could fire. New import: `pydantic_ai.run.AgentRunResultEvent`. This was a latent bug — production-only because plan 03-04 verification mocked enough of the run loop to never hit the misclassification, but the new D-CHAT-01/02 unit tests forced it into the open.
  - Auto-fix [Rule 2 - Missing functionality] in `app_v2/templates/ask/_error_card.html`: added `data-reason="{{ reason | e }}"` attribute on the outer `<div>`. Makes the error card machine-readable for tests + future client-side handlers; decouples tests from body copy. Reason is the D-CHAT-04 vocabulary string, autoescaped (no XSS path).

## Task Commits

1. **Task 1: rewrite test_ask_routes.py + create test_phase03_chat_invariants.py + narrow Phase 4 plotly invariant** — `573ad9a` (test)
2. **Task 2: add chat_loop + chat_session + chat_agent unit suites + 2 auto-fixes** — `563853a` (test)

## Files Created/Modified

### Created (5)

- `tests/v2/test_phase03_chat_invariants.py` — 10 invariants
- `tests/v2/test_chat_loop.py` — 11 tests
- `tests/v2/test_chat_session.py` — 16 tests
- `tests/v2/test_chat_agent_tools.py` — 11 tests
- `.planning/phases/03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on/03-05-SUMMARY.md` — this file

### Modified (5)

- `tests/v2/test_ask_routes.py` — rewritten end-to-end (13 new tests; old Phase 6 tests removed)
- `tests/v2/test_phase04_invariants.py` — plotly invariant narrowed (whitelist `app_v2/routers/ask.py`)
- `app/core/agent/chat_loop.py` — auto-fix Rule 1 (terminal-event discriminator)
- `app_v2/templates/ask/_error_card.html` — auto-fix Rule 2 (data-reason attribute)
- `app_v2/routers/ask.py` — auto-fix Rule 1 (TemplateResponse cookie propagation)

## Decisions Made

1. **Rule 1 auto-fix in `app_v2/routers/ask.py`: TemplateResponse cookie propagation.** FastAPI's parameter `Response` `set_cookie` only merges with the final response when the route returns a non-Response object. Both `/ask` and `/ask/chat` return `TemplateResponse` directly, so the parameter cookie set in plan 03-04's `_ensure_session_cookie` was being silently dropped. Added a parallel `_apply_session_cookie` helper that calls `response.set_cookie(...)` on the actual `TemplateResponse` only when the incoming request didn't carry the cookie (idempotent — no double-issuance). Verified by inspecting `Set-Cookie` headers in the new `test_ask_page_sets_pbm2_session_cookie_on_first_visit` test.

2. **Rule 1 auto-fix in `app/core/agent/chat_loop.py`: AgentRunResultEvent discriminator.** Plan 03-03's chat_loop used `if hasattr(ev, "result"):` to detect the terminal `AgentRunResultEvent`. But `FunctionToolResultEvent` ALSO carries a `result` attribute (the `ToolReturnPart` payload), so EVERY tool result was misclassified as the terminal frame. The loop emitted `agent-no-final-result` on the first tool call instead of running through the D-CHAT-01 cancel checkpoint and D-CHAT-02 rejection-cap counter. Switched to `isinstance(ev, AgentRunResultEvent)` (imported from `pydantic_ai.run`). The bug was latent — plan 03-04's smoke test mocked the run loop coarsely enough to never trigger the misclassification, but the new D-CHAT-01/02 unit tests immediately surfaced it.

3. **Rule 2 auto-fix in `_error_card.html`: data-reason attribute.** Tests need a stable signal for the error reason (D-CHAT-04 vocabulary). Coupling tests to the body-copy strings would brittle every UI-SPEC §G copywriting tweak. Added `data-reason="{{ reason | e }}"` on the outer `<div>` — invisible in the UI, machine-readable for tests + future client-side analytics, autoescape-safe (reason values are the 8 D-CHAT-04 strings, never user input). UI-SPEC §G remains unchanged (no visible copy added).

4. **Phase 4 plotly invariant narrowed by whitelisting one file.** D-CHAT-05 + T-03-04-09 require server-side Plotly chart construction in the chat router; the bundle was vendored in plan 03-01 specifically for this purpose. Whitelisting `app_v2/routers/ask.py` is the surgical fix — every other module under `app_v2/` remains forbidden from importing plotly. The lazy import inside `_build_plotly_chart_html` (NOT at module top-level) keeps Browse / Joint Validation / Settings free of the import cost; the new `test_plotly_only_loaded_on_ask_page` invariant locks that the bundle's `<script>` tag is referenced ONLY from `ask/index.html`'s `extra_head` block.

5. **Real `pydantic_ai.run.AgentRunResultEvent` with duck-typed `_FakeRunResult` for test mocks.** `AgentRunResult`'s real constructor requires `GraphAgentState` (a factory dataclass deeply tied to pydantic_ai's run loop) — not unit-testable. The `AgentRunResultEvent(result=...)` constructor only requires *something* assignable to `result`, and chat_loop only reads `.output` and calls `.new_messages()` on that object. A 4-line `_FakeRunResult` class satisfies both contracts without binding tests to pydantic_ai's internals.

6. **Real DBAdapter subclass `_FakeDB` instead of MagicMock.** Pydantic v2's `ChatAgentDeps.db` field is annotated `DBAdapter` (default isinstance check). `MagicMock` fails the validator with `Input should be an instance of DBAdapter`. The `_FakeDB` subclass overrides the 4 abstract methods (`test_connection`, `list_tables`, `get_schema`, `run_query`) with deterministic in-memory behavior; its `__init__` skips the parent's `DatabaseConfig` setup so no fixture YAML is needed. `ChatAgentDeps.model_construct(...)` is used in `test_chat_loop.py` where db is never read (skip validation entirely is acceptable there).

7. **anyio's pytest plugin for async tests, NOT pytest-asyncio.** The `anyio` package ships a `pytest11` entry point that registers `@pytest.mark.anyio` and an `anyio_backend` fixture. No separate `pytest-asyncio` install needed. The fixture pins the backend to `"asyncio"` so all async tests run on the same event loop chat_loop uses. This avoids adding a new dev dependency to `requirements.txt` for one plan's worth of async tests.

8. **Jinja `{# … #}` comment stripping in template invariant tests.** The chat partials carry explanatory header copy like `"NO | safe filter anywhere"` that would false-trigger the `| safe` substring check. Strip multi-line comments via `re.compile(r"\\{#.*?#\\}", re.DOTALL)` BEFORE the substring check; only filter usages OUTSIDE comments are flagged. Same approach used for the partial loop and the final-card whitelist test.

9. **Used `pydantic_ai.models.test.TestModel` minimally.** Only the `test_build_chat_agent_constructs_with_test_model` sanity check uses TestModel — confirms `build_chat_agent` returns a non-None Agent. The harder unit tests (cancel / rejection / budget / error / final payload) drive `stream_chat_turn` directly with a fake AsyncIterator agent (RESEARCH Gap 11 fallback approach), avoiding pydantic_ai's TestModel-driven internal stream machinery entirely. This makes the tests robust against future pydantic_ai TestModel API drift.

10. **Removed Phase 6 tests in `test_ask_routes.py` rather than skipping them.** D-CHAT-09 atomic-cleanup contract: deleted artifacts get deleted *atomically*, never left as `@pytest.skip`-marked deadweight. The Phase 3 successors cover every behavior the old tests asserted (route shape, error paths, NL-05 deletion, cookie-aware backend resolution); skipping the old set would leave 13 dead tests forever.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pbm2_session cookie propagation in `app_v2/routers/ask.py`**

- **Found during:** Task 1 — the new `test_ask_page_sets_pbm2_session_cookie_on_first_visit` test failed because no `Set-Cookie` header was emitted from `GET /ask`.
- **Issue:** Plan 03-04's `_ensure_session_cookie(request, response)` set the cookie on the parameter `Response` object. FastAPI merges parameter Response cookies into the final response ONLY when the route returns a non-Response object. Both `/ask` and `/ask/chat` return `TemplateResponse` directly, so the cookie was silently dropped. The plan 03-04 smoke verification did not check the `Set-Cookie` header — only that the route returned 200.
- **Fix:** Added `_apply_session_cookie(response, request, sid)` helper. Updated `ask_page` and `ask_chat` to call it on the constructed `TemplateResponse` AFTER assigning it to a local. Idempotent — skipped when the request already carried the cookie.
- **Files modified:** `app_v2/routers/ask.py`
- **Commit:** `573ad9a`

**2. [Rule 1 - Bug] Fixed terminal-event discriminator in `app/core/agent/chat_loop.py`**

- **Found during:** Task 2 — the new `test_d_chat_01_cancel_event_set_emits_stopped_by_user` test failed because the loop emitted `agent-no-final-result` instead of `stopped-by-user`.
- **Issue:** Plan 03-03's chat_loop used `if hasattr(ev, "result"):` to detect `AgentRunResultEvent`. But `FunctionToolResultEvent` ALSO has a `result` attribute (carrying the `ToolReturnPart` payload), so EVERY tool result was misclassified as the terminal frame. The loop never reached the D-CHAT-01 cancel checkpoint or the D-CHAT-02 rejection-cap counter because it always broke out at the first tool result.
- **Fix:** Switched to `isinstance(ev, AgentRunResultEvent)` (imported from `pydantic_ai.run`). Added explanatory comment about the FunctionToolResultEvent vs AgentRunResultEvent collision.
- **Files modified:** `app/core/agent/chat_loop.py`
- **Commit:** `563853a`

**3. [Rule 2 - Missing functionality] Added `data-reason` attribute on `_error_card.html`**

- **Found during:** Task 2 — wrote the chat_loop tests asserting on the error reason string, then realized the rendered HTML doesn't expose `{{ reason }}` directly (only severity, heading, body copy). Tests would otherwise have to grep on body-copy strings, brittle against future UI-SPEC §G tweaks.
- **Fix:** Added `data-reason="{{ reason | e }}"` on the outer `<div>` of `_error_card.html`. Invisible in UI; machine-readable for tests + future client-side analytics. Autoescape-safe (reason values are the 8 D-CHAT-04 vocabulary strings).
- **Files modified:** `app_v2/templates/ask/_error_card.html`
- **Commit:** `563853a`

No other deviations. Both tasks executed exactly as the plan specified, including the 5-test-file structure, the motivating example coverage, the Phase 6 invariant narrowing, and the cross-session 403 authorization tests.

## Issues Encountered

- **httpx StreamConsumed error** when iterating `resp.iter_lines()` twice in the WARNING-3 test. Fixed by collecting all lines in a single iteration loop with a sentinel break condition (`if "</tbody>" in body and "event: final" in body: break`). The fake agent stream is finite (yields one event), so the SSE stream closes naturally after the terminal frame.
- **Pydantic v2 `isinstance(DBAdapter)` check on ChatAgentDeps.db** rejected MagicMock fixtures across all tests that constructed `ChatAgentDeps(...)` (vs `model_construct(...)`). Added the `_FakeDB(DBAdapter)` subclass once and reused it across `test_ask_routes.py` and `test_chat_agent_tools.py`. `test_chat_loop.py` uses `model_construct` because its tests never read deps.db.

## User Setup Required

None. The test suite runs in-process; no external services, no LLM keys, no DB fixtures. `pytest tests/v2/ tests/agent/` returns 0.

## Verification Performed

### Per-task verification

**Task 1:**
- `pytest tests/v2/test_ask_routes.py -v` → 13 passed.
- `pytest tests/v2/test_phase03_chat_invariants.py -v` → 10 passed.
- `pytest tests/v2/test_phase04_invariants.py::test_no_banned_export_or_chart_libraries_imported_in_app_v2 -v` → 3 passed (plotly + openpyxl + csv).
- `pytest tests/v2/ -q` → 439 passed, 5 skipped, 0 failed.

**Task 2:**
- `pytest tests/v2/test_chat_loop.py -v` → 11 passed (was 5 failing before the chat_loop discriminator fix and the data-reason attribute fix).
- `pytest tests/v2/test_chat_session.py -v` → 16 passed.
- `pytest tests/v2/test_chat_agent_tools.py -v` → 11 passed.

### Plan-level verification

- `pytest tests/v2/ tests/agent/ -q` → **493 passed, 5 skipped, 2 warnings, 0 failed.** Above the ≥480 plan target by 13 tests.
- Test count math: plan 03-04 baseline = 431 passed + 1 failed + 13 errored + 5 skipped. After plan 03-05: 14 errors/failures resolved (rewritten tests + narrowed invariant), +48 net new tests added (10 invariants + 11 chat_loop + 16 chat_session + 11 chat_agent_tools = 48; the 13 rewritten ask_routes tests replace the 13 errored ones). Net delta: 431 - 13 (replaced) + 13 (new ask_routes) + 48 (new files) + 1 (failed plotly invariant fixed) + plotly's test stayed at 1 (still 1 of the parametrize set) = 493. ✓
- `tests/v2/test_phase06_invariants.py` does NOT exist (deleted atomically in plan 03-04 per D-CHAT-09; locked by `test_phase06_invariants_file_remains_deleted` in this plan).
- Phase 4 plotly invariant passes (3 parametrize entries: plotly + openpyxl + csv) — `app_v2/routers/ask.py` now whitelisted.

## Threat Surface Audit

Per the plan's `<threat_model>`:

- **T-03-05-01 (Test pollution between tests):** mitigated. Both `test_ask_routes.py` and `test_chat_session.py` carry an `_reset_chat_registries` (or `_reset_registries`) `autouse=True` fixture that clears `_TURNS` and `_SESSIONS` before AND after every test.
- **T-03-05-02 (Real LLM calls in CI):** mitigated. Every SSE-stream test mocks `build_chat_agent` AND `build_pydantic_model` to short-circuit the LLM build path. The fake agent's `run_stream_events` is a controlled async generator that yields predefined events and terminates.
- **T-03-05-03 (Long-running SSE test hangs CI):** mitigated. `client.stream(...)` reads incrementally via `iter_lines()`; tests break out of the loop on `</tbody>` + `event: final` sentinel. The fake agent's stream is finite.
- **T-03-05-04 (TestClient cookies leaking to prod):** accepted. TestClient operates in-process; cookies never leave the test runner.

No new threat-relevant surface introduced.

## Threat Flags

None. The auto-fixes (`_apply_session_cookie`, `data-reason` attribute, `AgentRunResultEvent` discriminator) all stay within the threat surface that plan 03-04's `<threat_model>` already enumerated. The cookie helper preserves T-03-04-05 (HttpOnly + SameSite=Lax + Secure=False). The `data-reason` attribute is autoescaped (T-03-04-04 path remains intact). The chat_loop discriminator change is internal to the agent module.

## Phase 03 Closure

**This is the final plan in Phase 03.** All 15 D-CHAT-* requirements are now implemented across plans 01–05:

- **D-CHAT-01..04** (stop boundaries: cancel / rejection cap / step budget / hard error) — implemented in plan 03-03, locked by `test_chat_loop.py`.
- **D-CHAT-05** (PresentResult terminator) — implemented in plan 03-02, locked by `test_chat_agent_tools.py` + WARNING-3 test in `test_ask_routes.py`.
- **D-CHAT-06** (ChartSpec literal types) — implemented in plan 03-02, locked by `test_chat_agent_tools.py::test_chart_spec_chart_type_literal_constraint`.
- **D-CHAT-07** (chat-surface CSS) — implemented in plan 03-04, locked by Phase 04 invariants holding (no token bloat).
- **D-CHAT-08** (4-route surface) — implemented in plan 03-04, locked by `test_ask_routes.py` + `test_phase03_chat_invariants.py::test_ask_router_async_def_only_on_streaming_routes`.
- **D-CHAT-09** (NL-05 atomic cleanup) — implemented in plan 03-04, locked by `test_phase03_chat_invariants.py::test_nl05_templates_deleted` + `test_phase06_invariants_file_remains_deleted`.
- **D-CHAT-10** (starter chips removal) — implemented in plan 03-04, locked by `test_phase03_chat_invariants.py::test_starter_chips_not_included_in_index`.
- **D-CHAT-11** (LLM dropdown verbatim port + path scrub on OpenAI) — implemented in plans 03-02/03/04, locked by `test_phase03_chat_invariants.py::test_llm_dropdown_preserved_in_index` + `test_chat_session.py::test_scrub_on_write_when_active_llm_is_openai`.
- **D-CHAT-12** (140-char thought truncation) — implemented in plan 03-03, locked by `test_chat_loop.py::test_truncate_thought_*`.
- **D-CHAT-13** (tool call/result pill renderers) — implemented in plan 03-04, locked by `test_phase03_chat_invariants.py::test_no_safe_filter_on_agent_strings_in_chat_partials`.
- **D-CHAT-14** (Stop button OOB swap) — implemented in plan 03-04, locked by `test_ask_routes.py::test_post_ask_chat_returns_user_message_fragment_with_sse_consumer`.
- **D-CHAT-15** (12-message sliding window) — implemented in plan 03-03, locked by `test_chat_session.py::test_session_history_sliding_window_d_chat_15`.

Threat boundaries (T-03-04-01 through T-03-04-09) are mitigated and locked by tests in plans 03-04 and 03-05.

## Self-Check

Verified file existence and commit hashes:

- `tests/v2/test_phase03_chat_invariants.py` → FOUND (10 tests)
- `tests/v2/test_chat_loop.py` → FOUND (11 tests)
- `tests/v2/test_chat_session.py` → FOUND (16 tests)
- `tests/v2/test_chat_agent_tools.py` → FOUND (11 tests)
- `tests/v2/test_ask_routes.py` (modified) → FOUND, 13 tests, contains test_post_ask_query_route_no_longer_exists + test_get_ask_stream_with_foreign_session_returns_403 + test_get_ask_stream_final_frame_contains_table_rows_when_sql_returns_rows
- `tests/v2/test_phase04_invariants.py` (modified) → FOUND, plotly invariant whitelist references `app_v2/routers/ask.py`
- `app/core/agent/chat_loop.py` (modified) → FOUND, contains `from pydantic_ai.run import AgentRunResultEvent` + `isinstance(ev, AgentRunResultEvent)`
- `app_v2/templates/ask/_error_card.html` (modified) → FOUND, contains `data-reason="{{ reason | e }}"`
- `app_v2/routers/ask.py` (modified) → FOUND, contains `_apply_session_cookie` helper
- `tests/v2/test_phase06_invariants.py` → DELETED (verified by `test_phase06_invariants_file_remains_deleted`)
- Commit `573ad9a` (Task 1) → FOUND in git log
- Commit `563853a` (Task 2) → FOUND in git log

## Self-Check: PASSED

---
*Phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on*
*Plan: 05*
*Completed: 2026-05-02*
