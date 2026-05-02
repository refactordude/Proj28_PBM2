---
phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
fixed_at: 2026-05-03T00:00:00Z
review_path: .planning/phases/03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on/03-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-05-03
**Source review:** `.planning/phases/03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on/03-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (Critical: 0, Warning: 4)
- Fixed: 4
- Skipped: 0
- Test baseline: 477 passing, 5 skipped, 0 failures (pre and post fixes — no regressions)

## Fixed Issues

### WR-01: chat_agent SAFE-harness silently drops execution-error logging

**Files modified:** `app/core/agent/chat_agent.py`
**Commit:** b4ed33c
**Applied fix:** Added `import logging` + module-level `_log = logging.getLogger(__name__)` and inserted `_log.warning("chat-agent run_sql execution error: %s: %s", type(exc).__name__, exc)` inside the broad `except Exception as exc` in `_execute_and_wrap`. Restores the observability parity with `nl_agent.run_sql` (nl_agent.py:179) so operators see server-side stack traces when DB errors fire from agent-issued SQL.

### WR-02: Turn-registry leaks when SSE stream is never opened

**Files modified:** `app/core/agent/chat_session.py`
**Commit:** a404467
**Applied fix:** Added `_TURN_SOFT_CAP = 500` module constant and an LRU-style eviction inside `new_turn`: when `len(_TURNS) >= _TURN_SOFT_CAP`, evict the oldest entry by insertion order before inserting the new turn. Bounds dict growth in pathological cases (POST /ask/chat with no paired GET /ask/stream — tab close mid-submit, network drop, scanner traffic) without affecting normal POST → SSE pairing where `pop_turn` fires from the SSE BackgroundTask within seconds.

This is the simpler alternative the reviewer explicitly listed ("Or, simpler: keep an LRU cap in `_TURNS`"). It is preferred over the delayed-pop async-task approach because:
1. `ask_chat` is sync `def` (Phase 3 invariant `test_ask_router_async_def_only_on_streaming_routes` requires this); scheduling an asyncio task from a sync handler is awkward.
2. No long-lived `asyncio.sleep(600)` slots tied up per turn.
3. Bounded growth is the actual goal — the cap directly enforces it.

### WR-03: Synchronous DB I/O on event-loop thread inside SSE generator

**Files modified:** `app_v2/routers/ask.py`
**Commit:** c5b4c9a
**Applied fix:** Added `import asyncio` and wrapped the `_hydrate_final_card` call inside `event_generator` with `await asyncio.to_thread(_hydrate_final_card, ...)`. The function still runs sync `pd.read_sql_query(sa.text(safe_sql), conn)` against the existing pymysql/SQLAlchemy stack, but it now runs on a thread-pool executor so other concurrent SSE streams + cancel endpoints make progress during the final SQL execution. Aligns with the orchestrator's preferred fix (no broader async-DB refactor needed).

### WR-04: Silent coercion of unknown LLM type to "ollama" disables path scrub

**Files modified:** `app_v2/routers/ask.py`
**Commit:** e9ca63b
**Applied fix:** Replaced the silent `"openai" if type == "openai" else "ollama"` coercion with an explicit allow-list check: `_LOCAL_LLM_TYPES = frozenset({"ollama"})` is the only set of types that map to `active_llm_type = "ollama"` (path scrub disabled). Anything else — including unknown future cloud backends like `anthropic` — falls through to `active_llm_type = "openai"` so the D-CHAT-11 scrub fires. Unknown types (anything that is neither "ollama" nor "openai") additionally emit `_log.warning("unknown LLM type %r ...")` so operators see when a misconfigured or new backend triggers the default-deny path. Default-deny posture aligns with the threat model: a path leak is worse than a misclassified local backend running an unnecessary scrub.

---

_Fixed: 2026-05-03_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
