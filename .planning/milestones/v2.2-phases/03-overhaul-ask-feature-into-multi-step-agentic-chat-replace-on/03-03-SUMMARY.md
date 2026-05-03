---
phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
plan: 03
subsystem: agent
tags: [pydantic-ai, sse, async-generator, asyncio-event, message-history, path-scrub, d-chat-01, d-chat-02, d-chat-03, d-chat-04, d-chat-11, d-chat-12, d-chat-13, d-chat-15]

# Dependency graph
requires:
  - phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
    plan: 01
    provides: AgentConfig.chat_max_steps (default=12, ge=1, le=50) — the per-turn step budget consumed by stream_chat_turn via UsageLimits(tool_calls_limit=...)
  - phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
    plan: 02
    provides: build_chat_agent factory + ChatAgentDeps + PresentResult + ChartSpec — the agent stream_chat_turn drives via run_stream_events; the REJECTED prefix in _execute_and_wrap is what stream_chat_turn's rejection counter strings-prefix-matches
provides:
  - chat_session module — per-turn cancel + per-session message_history store with D-CHAT-15 sliding window and D-CHAT-11 'both' path-scrub policy
  - chat_loop.stream_chat_turn async generator wrapping agent.run_stream_events with all 4 stop boundaries (D-CHAT-01/02/03/04) + truncation/render helpers (D-CHAT-12/13)
  - HARD_REASONS / SOFT_REASONS frozensets — D-CHAT-04 severity classification consumed by plan 03-04's _error_card.html template
  - app.state.chat_turns and app.state.chat_sessions documentation hooks on lifespan
  - WARNING-3 contract: stream_chat_turn emits STRUCTURED final payload {summary, sql, chart_spec_dict, new_messages} — NOT pre-rendered HTML; router renders _final_card.html itself
affects: [03-04-routes, 03-05-templates, 03-06-cleanup]

# Tech tracking
tech-stack:
  added: []  # No new deps — pydantic_ai, sse-starlette, sqlparse already pinned by plan 03-01
  patterns:
    - "async generator yielding {event, html|payload} dicts as the SSE wire-format-agnostic layer between agent loop and route handler — the route maps each yield to a sse_starlette.ServerSentEvent without coupling chat_loop to sse_starlette"
    - "Per-turn registry uses asyncio.Event (NOT threading.Event per RESEARCH Pitfall 6); per-process module-level dict guarded by threading.Lock for the dict-lookup; cancel_event flip is async-safe because asyncio.Event.set() is itself thread-safe-from-async-loop in Python 3.10+"
    - "WARNING-3 final-payload contract: agent module emits STRUCTURED data dict; route module owns DB read + chart construction + _final_card.html render — keeps agent module DB-free (T-03-04-09 alignment)"
    - "RESEARCH Pitfall 7 honored: ToolReturnPart vs RetryPromptPart branched in _extract_tool_content_from_result via .content / .model_response()"
    - "RESEARCH Anti-pattern honored: asyncio.CancelledError is RAISED, never swallowed — lets BackgroundTask cleanup run on browser disconnect"
    - "D-CHAT-15 [-12:] slice in chat_session.get_session_history; PydanticAI tolerates leading ModelResponse on replay (Pitfall 4)"

key-files:
  created:
    - app/core/agent/chat_session.py (255 lines)
    - app/core/agent/chat_loop.py (411 lines)
  modified:
    - app_v2/main.py (5-line diff — 2 init lines + 2 comments + 1 blank)

key-decisions:
  - "Use agent.run_stream_events (Open Question 1 RESOLVED) over agent.iter() — public API, signature-verified, sufficient for D-CHAT-01 cooperative cancellation between FunctionToolResultEvent boundaries; avoids unverified CallToolsNode.stream introspection path"
  - "AgentRunResult.new_messages() is a METHOD on ev.result (NOT on ev itself) — plan template's getattr(ev, 'new_messages', lambda: [])() was incorrect; actual call is run_result.new_messages() per pydantic_ai/run.py docstring"
  - "Per-session lock (_SESSION_LOCK) serializes append_session_history (Open Question 2 RESOLVED); multi-tab race window accepted — order across concurrent turns from same browser does not affect [-12:] slice replay"
  - "WARNING-3 final-payload contract honored: stream_chat_turn yields {event:'final', payload:{summary, sql, chart_spec_dict, new_messages}} — NOT pre-rendered HTML; chat_loop has zero DB access and zero Plotly construction; router (plan 03-04) owns _final_card.html render against request.app.state.db"
  - "asyncio.Event chosen over threading.Event per RESEARCH Pitfall 6 — mixing threading.Event with asyncio leads to 'event set but generator never wakes' bugs because the asyncio scheduler does not poll thread events"
  - "_render_* helpers delegate to plan 03-04 templates via Jinja2Blocks templates instance; templates do not exist yet but import succeeds because get_template() is called only at runtime by stream_chat_turn (not at module import time)"
  - "app.state.chat_turns / chat_sessions are DOCUMENTATION hooks; module-level _TURNS / _SESSIONS in chat_session.py are the canonical store — router (plan 03-04) interacts ONLY via chat_session helpers"
  - "_THOUGHT_TRUNCATE_CAP = 140 (UI-SPEC §C researcher pick over the D-CHAT-12 placeholder of 120) — last-whitespace cut with U+2026 ellipsis suffix per UI-SPEC §C"

requirements-completed: [D-CHAT-01, D-CHAT-02, D-CHAT-03, D-CHAT-04, D-CHAT-11, D-CHAT-12, D-CHAT-13, D-CHAT-15]

# Metrics
duration: ~12min
completed: 2026-05-03
---

# Phase 03 Plan 03: Chat Plumbing — Session Registry, Stream Generator, Lifespan Hooks Summary

**Wave 2 plumbing wrapping plan 02's chat agent: per-turn registry (asyncio.Event cancel + uuid4 turn_id) + per-session message_history store with D-CHAT-15 sliding window + D-CHAT-11 'both' path scrub on write; stream_chat_turn async generator driving agent.run_stream_events with all 4 stop boundaries (D-CHAT-01/02/03/04) and the WARNING-3 STRUCTURED-payload final contract; minimal app.state.chat_turns + chat_sessions documentation hooks on the v2.0 lifespan.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-03T16:21:33Z
- **Completed:** 2026-05-03T16:33:48Z
- **Tasks:** 3 / 3
- **Files modified:** 1
- **Files created:** 2
- **Tests:** 464 passed, 5 skipped (no regressions vs plan 03-02 baseline)

## Accomplishments

- Created `app/core/agent/chat_session.py` (255 lines) exposing the 11-name `__all__`:
  - **Turn lifecycle:** `new_turn(session_id, question) -> turn_id` (uuid4 hex), `get_cancel_event`, `get_pending_question`, `get_session_id_for_turn`, `cancel_turn`, `pop_turn` — all guarded by `_TURN_LOCK` (threading.Lock).
  - **Session lifecycle:** `get_or_create_session`, `get_session_history(session_id, limit=12)` returning `state.messages[-limit:]` (D-CHAT-15 sliding window), `append_session_history(session_id, msgs, *, active_llm_type)` — guarded by `_SESSION_LOCK`.
  - **Path-scrub on write (D-CHAT-11 "both"):** `_scrub_messages_inplace` walks UserPromptPart, ToolReturnPart, ToolCallPart args via existing `app.services.path_scrubber.scrub_paths` — fires only when `active_llm_type=='openai'`.
  - **Cooperative cancel primitive:** `asyncio.Event` (NOT `threading.Event` per RESEARCH Pitfall 6).
- Created `app/core/agent/chat_loop.py` (411 lines) exposing `stream_chat_turn` async generator:
  - **Drives `agent.run_stream_events(...)`** with `usage_limits=UsageLimits(tool_calls_limit=chat_max_steps)` (Open Question 1 RESOLVED — public API; signature verified against pydantic_ai/agent/abstract.py).
  - **D-CHAT-01 cancel checkpoint:** `cancel_event.is_set()` between `FunctionToolResultEvent` boundaries → emits `'stopped-by-user'`.
  - **D-CHAT-02 rejection cap:** consecutive `REJECTED:` tool results counted; `rejection_counter >= rejection_cap` (default `5`) → emits `'still-rejected-after-5-attempts'`.
  - **D-CHAT-03 step budget:** `UsageLimitExceeded` caught (only when raised before final per Open Question 4 RESOLVED) → emits `'step-budget-exhausted'`.
  - **D-CHAT-04 error classification:** all 8 reasons mapped to `HARD_REASONS` / `SOFT_REASONS` frozensets; `_ERROR_BODY_BY_REASON` locks UI-SPEC Copywriting Contract verbatim.
  - **WARNING-3 STRUCTURED final payload:** `{event:'final', payload:{summary, sql, chart_spec_dict, new_messages}}` — chat_loop is DB-free; router (plan 03-04) renders `_final_card.html` itself.
  - **D-CHAT-12 truncation:** `_truncate_thought` caps at `_THOUGHT_TRUNCATE_CAP=140` chars at last whitespace, U+2026 ellipsis suffix.
  - **D-CHAT-13 pill renderers:** `_render_thought` / `_render_tool_call_pill` / `_render_tool_result_pill` delegate to plan 03-04 templates via `Jinja2Blocks` templates instance.
  - **RESEARCH Pitfall 7:** `_extract_tool_content_from_result` branches on `ToolReturnPart` (`.content`) vs `RetryPromptPart` (`.model_response()`).
  - **RESEARCH Anti-pattern:** `asyncio.CancelledError` raised, never swallowed.
- Modified `app_v2/main.py` (5-line diff): added `app.state.chat_turns = {}` and `app.state.chat_sessions = {}` on lifespan, sibling to existing `app.state.agent_registry = {}` precedent.

## Task Commits

Each task was committed atomically:

1. **Task 1: chat_session registry — per-turn cancel + per-session history** — `9c83dd7` (feat)
2. **Task 2: chat_loop.stream_chat_turn — SSE generator + 4 stop boundaries** — `f336d91` (feat)
3. **Task 3: document chat registries on app.state lifespan** — `56d0d65` (feat)

## Files Created/Modified

### Created
- `app/core/agent/chat_session.py` (255 lines) — module exporting 11 names: `TurnState`, `SessionState`, `new_turn`, `get_cancel_event`, `get_pending_question`, `get_session_id_for_turn`, `cancel_turn`, `pop_turn`, `get_or_create_session`, `get_session_history`, `append_session_history`. Module-private `_TURNS` / `_SESSIONS` dicts guarded by `threading.Lock`; `_scrub_messages_inplace` private helper for D-CHAT-11.
- `app/core/agent/chat_loop.py` (411 lines) — module exporting `stream_chat_turn`, `HARD_REASONS`, `SOFT_REASONS`. Module-private helpers: `_event_to_payload`, `_render_thought`, `_render_tool_call_pill`, `_render_tool_result_pill`, `_render_error`, `_truncate_thought`, `_extract_tool_content`, `_extract_tool_content_from_result`, `_summarize_tool_result`. Body-copy table `_ERROR_BODY_BY_REASON` covering all 8 D-CHAT-04 reasons.

### Modified
- `app_v2/main.py` — added 2 init lines (`app.state.chat_turns = {}`, `app.state.chat_sessions = {}`) + 2 comment lines + 1 blank line inside the lifespan body, immediately after the existing `app.state.agent_registry = {}` precedent (line 51). Total diff: 5 insertions, 0 deletions, 0 modifications.

## Decisions Made

1. **`agent.run_stream_events` over `agent.iter` (Open Question 1 RESOLVED).** Public PydanticAI 1.86.0 API, signature-verified against `pydantic_ai/agent/abstract.py:946-1008`. Sufficient for D-CHAT-01 cooperative cancellation because the rejection-counter check fires on `FunctionToolResultEvent` boundaries — exactly where the cancel checkpoint sits. Avoids the unverified `CallToolsNode.stream` introspection path (RESEARCH A3 LOW-confidence).

2. **`AgentRunResult.new_messages()` extracted via `run_result.new_messages()`, not `getattr(ev, 'new_messages')`.** The plan template snippet `getattr(ev, "new_messages", lambda: [])()` would always return `[]` because `new_messages` is a method on `ev.result`, not on the `AgentRunResultEvent` itself. Verified by reading `pydantic_ai/run.py` `AgentRunResult` source — the method excludes replayed history (returns ONLY the messages produced by this run, exactly what the session-history append needs). **Auto-fixed (Rule 1 - Bug)** before commit.

3. **Per-session lock serializes `append_session_history` (Open Question 2 RESOLVED).** `_SESSION_LOCK` is uncontended in the single-tab common case (one browser, one in-flight turn at a time per the UI lockout in D-CHAT-14). The multi-tab race window is documented as ACCEPTED — worst outcome is interleaved messages, which is benign for the `[-12:]` slice (D-CHAT-15) because order across concurrent turns from the same browser does not affect downstream replay.

4. **WARNING-3 STRUCTURED final-payload contract.** `stream_chat_turn` yields `{event:'final', payload:{summary, sql, chart_spec_dict, new_messages}}` — NOT pre-rendered HTML. The router (plan 03-04) hydrates `_final_card.html` itself by re-running `PresentResult.sql` against `request.app.state.db` and constructing the Plotly chart server-side. This keeps `chat_loop.py` DB-free (zero `db.run_query` calls) and zero `plotly` constructions, aligning with threat model T-03-04-09 (chart_html constructed server-side under router control). The plan's `<context>` block flagged this as the WARNING-3 contract — honored verbatim.

5. **`asyncio.Event` over `threading.Event` (RESEARCH Pitfall 6).** Mixing `threading.Event` with asyncio leads to "event set but generator never wakes" bugs because the asyncio scheduler does not poll thread events. The cancel POST handler in plan 03-04 will be `async def` so it lives on the same loop as the SSE generator; `cancel_event.set()` is async-loop-safe.

6. **`_render_*` helpers delegate to plan 03-04 templates via Jinja2Blocks `templates` instance.** Templates `ask/_thought_event.html`, `ask/_tool_call_pill.html`, `ask/_tool_result_pill.html`, `ask/_error_card.html` do NOT exist yet — they ship in plan 03-04. Module import succeeds because `templates.get_template()` is called only at runtime by `stream_chat_turn`, not at module load. Unit tests of pure helpers (`_truncate_thought`, `HARD_REASONS`, `_ERROR_BODY_BY_REASON`) do not trigger template lookup.

7. **`_THOUGHT_TRUNCATE_CAP = 140` (researcher pick over D-CHAT-12 placeholder of 120).** UI-SPEC §C researcher recommendation reads cleanly at 13px italic with line-height 1.5 for the typical thought summary length seen in PydanticAI ThinkingPart deltas. The `_truncate_thought` helper finds the last whitespace at-or-before `cap`, falls back to a hard cut at `cap` if no good whitespace exists in the second half, then appends U+2026.

8. **`app.state.chat_turns` / `chat_sessions` are DOCUMENTATION hooks.** Source of truth is the module-level `_TURNS` / `_SESSIONS` dicts in `chat_session.py`. The router (plan 03-04) interacts ONLY via the chat_session helpers (`new_turn`, `get_cancel_event`, etc.) — it never reaches into `app.state.chat_turns` directly. Mirroring on `app.state` documents the lifecycle for any future test or admin endpoint that wants to enumerate live turns.

9. **DB adapter attribute is `app.state.db` (NOT `app.state.db_adapter`).** Pinned at `app_v2/main.py:56` and `:65`. Plan 03-04's `_hydrate_final_card` MUST read from `request.app.state.db`. Verified by re-reading the file before editing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed AgentRunResult.new_messages access path**
- **Found during:** Task 2 implementation (writing chat_loop.py).
- **Issue:** Plan template snippet says `new_messages = list(getattr(ev, "new_messages", lambda: [])() or [])` for the `AgentRunResultEvent` branch. This would always return `[]` because `new_messages` is a method on `ev.result` (which is `AgentRunResult`), NOT on the `AgentRunResultEvent` wrapper. Verified by reading `pydantic_ai/run.py` source.
- **Fix:** Changed to `new_messages = list(run_result.new_messages())` wrapped in defensive `try/except Exception` so a future API change cannot break the SSE flow.
- **Files modified:** `app/core/agent/chat_loop.py`
- **Commit:** `f336d91`

No other deviations — the rest of the plan executed exactly as written. All acceptance criteria for Task 1 (10 items), Task 2 (13 items including all 8 reason-string greps), and Task 3 (5 items) passed on first commit.

## Issues Encountered

None.

## User Setup Required

None — modules are purely additive code with no runtime effect until plan 03-04 wires the new SSE routes. Existing Ask page (v2.0 Phase 6 surface) continues rendering unchanged because nothing imports `chat_session` or `chat_loop` yet. No external service configuration required.

## Verification Performed

Each task ran its `<verify>` block plus the plan's `<verification>` block:

### Task 1 (chat_session.py)
```
.venv/bin/python -c "
import asyncio
from app.core.agent.chat_session import (
    new_turn, get_cancel_event, get_pending_question, cancel_turn, pop_turn,
    get_session_history, append_session_history, get_or_create_session,
)
session_id = 'test-session'
turn_id = new_turn(session_id, 'compare X across SM8850 and SM8650')
assert len(turn_id) == 32, turn_id
assert get_pending_question(turn_id) == 'compare X across SM8850 and SM8650'
ev = get_cancel_event(turn_id)
assert isinstance(ev, asyncio.Event), type(ev)
assert not ev.is_set()
cancel_turn(turn_id)
assert ev.is_set()
hist = get_session_history(session_id)
assert hist == []
pop_turn(turn_id)
print('OK')
"
```
→ `OK`. File 255 lines (≥100). All 11 `__all__` exports present. Substring greps pass: `state.messages[-limit:]`, `if active_llm_type == "openai"`, `def _scrub_messages_inplace`, `asyncio.Event`, `UserPromptPart` + `ToolReturnPart` + `ToolCallPart`, `limit: int = 12`.

### Task 2 (chat_loop.py)
```
.venv/bin/python -c "
from app.core.agent.chat_loop import (
    stream_chat_turn, HARD_REASONS, SOFT_REASONS,
    _truncate_thought, _ERROR_BODY_BY_REASON,
)
assert _truncate_thought('a' * 50, 140) == 'a' * 50
trunc = _truncate_thought('hello ' * 100, 140)
assert len(trunc) <= 141, len(trunc)
assert trunc.endswith('…')
assert 'still-rejected-after-5-attempts' in HARD_REASONS
assert 'stopped-by-user' in SOFT_REASONS
assert 'step-budget-exhausted' in SOFT_REASONS
assert 'timeout' in SOFT_REASONS
for r in {'llm-error','still-rejected-after-5-attempts','stream-dropped','agent-no-final-result','unconfigured','timeout','step-budget-exhausted','stopped-by-user'}:
    assert r in _ERROR_BODY_BY_REASON, r
print('OK')
"
```
→ `OK`. File 411 lines (≥150). All 8 D-CHAT-04 reason strings present (each ≥2 occurrences). `async def stream_chat_turn` ✓. `UsageLimits(tool_calls_limit=chat_max_steps)` ✓. `if cancel_event.is_set()` ✓. `rejection_counter >= rejection_cap` ✓. `rejection_cap: int = 5` ✓. `HARD_REASONS = frozenset(` and `SOFT_REASONS = frozenset(` ✓. `_THOUGHT_TRUNCATE_CAP = 140` ✓. `from app_v2.templates import templates` ✓. `except asyncio.CancelledError:` followed by `raise` (no swallow) ✓.

### Task 3 (app_v2/main.py)
```
.venv/bin/python -c "
from fastapi.testclient import TestClient
from app_v2.main import app
client = TestClient(app)
r = client.get('/')
assert r.status_code in (200, 302, 307), r.status_code
print('OK')
"
```
→ `OK`. `grep "app.state.chat_turns"` matches at line 54; `grep "app.state.chat_sessions"` matches at line 56. `git diff --stat` shows 5 insertions, 0 deletions, 0 modifications (acceptance bound: ≤6).

### Plan-level verification
```
pytest tests/agent/ tests/v2/ -x -q
```
→ **464 passed, 5 skipped, 5 warnings in 38.51s** — identical to plan 03-02's baseline. Zero regressions.

```
.venv/bin/python -c "
from app.core.agent.chat_session import new_turn, get_session_history, append_session_history
from app.core.agent.chat_loop import stream_chat_turn, HARD_REASONS, SOFT_REASONS
print('chat_session + chat_loop import cleanly')
"
```
→ `chat_session + chat_loop import cleanly`.

## Threat Surface Audit

Per the plan's `<threat_model>`:

- **T-03-03-01 (Spoofing / Information Disclosure, turn_id in URL):** mitigated. `turn_id = uuid.uuid4().hex` (32 hex chars, 128 bits of entropy — unguessable). Plan 03-04 will additionally verify `turn.session_id` matches the request's `pbm2_session` cookie (defense-in-depth — see plan 03-04 threat model).
- **T-03-03-02 (Information Disclosure, scrub skipped for Ollama):** ACCEPTED per D-CHAT-11. Ollama is local intranet — paths are not leaving the network. Privacy boundary, not security.
- **T-03-03-03 (Tampering, message_history mutation across concurrent turns):** mitigated. `_SESSION_LOCK` taken on every session-history write (`append_session_history`, `get_or_create_session`); uncontended in the single-tab common case. Multi-tab worst case is interleaved messages, benign for `[-12:]` slice.
- **T-03-03-04 (DoS, unbounded growth of `_SESSIONS`):** ACCEPTED. ~12 messages × ~20 turns × ~50 active users × ~5KB/message = ~60MB worst-case per process — within budget for intranet single-process deployment. TTL hardening deferred to future phase.
- **T-03-03-05 (Tampering, cancel_event set on wrong turn_id):** ACCEPTED. Each turn has its own `asyncio.Event`; setting one does not affect another. `_TURN_LOCK` protects the dict lookup itself. Already-completed turns simply ignore the flag (D-CHAT-01 — `cancel_turn` is no-op when turn is absent).
- **T-03-03-06 (Information Disclosure, `_log.debug` of LLM exception type name):** ACCEPTED. Only `type(exc).__name__` logged (e.g., `RuntimeError`, `TimeoutError`) — not the exception message itself, so DB rows / SQL fragments do not leak to logs. RESEARCH Anti-pattern banned per-event `_log.info`. Verified at `chat_loop.py` `_log.debug("chat-loop unexpected exception: %s", type(exc).__name__)`.
- **T-03-03-07 (Spoofing, UUID4 collision):** ACCEPTED. Probability ~1 in 2^122 per pair; not a real-world threat.

No new threat flags surfaced beyond the plan's pre-registered set. The plumbing modules introduce zero new network endpoints, zero auth paths, zero file access patterns, zero schema changes — they are pure async-control-flow + data-mutation glue.

## Next Phase Readiness

All Wave-2 contract surface for plan 03-04 (router rewrite) now in place:

- **Plan 03-04 router rewrite can now:**
  - Import `from app.core.agent.chat_session import new_turn, get_cancel_event, get_pending_question, get_session_id_for_turn, cancel_turn, pop_turn, get_or_create_session, get_session_history, append_session_history`.
  - Import `from app.core.agent.chat_loop import stream_chat_turn` and drive it inside an `EventSourceResponse(...)` generator.
  - Wrap `BackgroundTask(pop_turn, turn_id)` into `EventSourceResponse(..., background=...)` for cleanup (RESEARCH Pitfall 3).
  - On `event:'final'` payload, run `payload['sql']` against `request.app.state.db` and render `_final_card.html` itself with `table_html` + `chart_html` populated (WARNING-3 contract; T-03-04-09 alignment).
  - On `event:'error'` payload, append `payload['html']` to the SSE stream — `_error_card.html` is fully rendered server-side by `_render_error` already.
- **No runtime behavior change yet:** Ask page still renders the v2.0 Phase 6 surface. All existing tests green.

## Self-Check

Verified file existence and commit hashes:

- `app/core/agent/chat_session.py` → FOUND (255 lines)
- `app/core/agent/chat_loop.py` → FOUND (411 lines)
- `app_v2/main.py` (modified) → FOUND, contains `app.state.chat_turns = {}` at line 54 and `app.state.chat_sessions = {}` at line 56
- Commit `9c83dd7` (Task 1) → FOUND in git log
- Commit `f336d91` (Task 2) → FOUND in git log
- Commit `56d0d65` (Task 3) → FOUND in git log

## Self-Check: PASSED

---
*Phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on*
*Plan: 03*
*Completed: 2026-05-03*
