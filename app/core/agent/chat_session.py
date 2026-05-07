"""Phase 3 chat-session registry — per-turn cancel events + per-session message history.

Per D-CHAT-01 (asyncio.Event-based cooperative cancel), D-CHAT-11 ("both" path-scrub
policy: tool args + tool results), D-CHAT-15 (sliding window of last 12 ModelMessage
entries = 6 user/agent pairs).

This module is the in-memory glue between the SSE route handlers (plan 03-04) and
the chat-loop generator (chat_loop.stream_chat_turn). It owns two single-process
registries:

  - _TURNS: dict[turn_id, TurnState] — per-turn cancel_event + pending_question.
    Lives from POST /ask/chat to end of GET /ask/stream/{turn_id}; popped via
    BackgroundTask after the SSE response completes.

  - _SESSIONS: dict[session_id, SessionState] — per-browser-session message_history.
    Lives for the process lifetime. Each new turn slices the last 12 entries
    via get_session_history(...) and replays via PydanticAI message_history kwarg;
    after the turn, append_session_history(...) extends with agent_run.new_messages().

The dicts are protected by threading.Lock (single-process intranet — no Redis
required per project constraints). asyncio.Event is the cancellation primitive
(NOT threading.Event — RESEARCH Pitfall 6: mixing threading.Event with asyncio
leads to "event set but generator never wakes" bugs).

D-CHAT-11 path-scrub policy "both": when active_llm_type=='openai',
append_session_history applies scrub_paths to UserPromptPart, ToolReturnPart,
and ToolCallPart args before they enter the message store, so the next turn's
message_history replay does not leak filesystem paths to the cloud LLM.
"""
from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass, field
from typing import Literal

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from app.services.path_scrubber import scrub_paths


# --- Dataclasses ----------------------------------------------------------


@dataclass
class TurnState:
    """Per-turn state — lives from POST /ask/chat to end of GET /ask/stream."""

    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    pending_question: str = ""
    session_id: str = ""


@dataclass
class SessionState:
    """Per-browser-session state — lives for the process lifetime."""

    messages: list[ModelMessage] = field(default_factory=list)


# --- Module-level registries ---------------------------------------------
# Single-process intranet deployment, so threading.Lock is sufficient; no Redis.
# RESEARCH Pattern 4 — these are the canonical store; app.state.chat_turns /
# chat_sessions on app_v2/main.py are documentation hooks only.

_TURN_LOCK = threading.Lock()
_TURNS: dict[str, TurnState] = {}

# WR-02 mitigation: bound `_TURNS` growth when the SSE stream is never opened.
# `pop_turn` only fires from the SSE BackgroundTask, so a POST /ask/chat that
# never gets a paired GET /ask/stream (tab close mid-submit, network drop,
# scanner traffic) leaks the entry. Cap the dict at `_TURN_SOFT_CAP` and evict
# the oldest entries (insertion order — Py3.7+ dicts are ordered) on overflow.
# Sized so that even worst-case orphan-rate burst is bounded; normal operation
# keeps the dict tiny because pop_turn fires within seconds of stream close.
_TURN_SOFT_CAP = 500

_SESSION_LOCK = threading.Lock()
_SESSIONS: dict[str, SessionState] = {}


# --- Turn lifecycle helpers -----------------------------------------------


def new_turn(session_id: str, question: str) -> str:
    """Create a new turn entry; return its turn_id (32-hex).

    Called from POST /ask/chat (plan 03-04). The returned turn_id is what the
    HTMX fragment renders into `sse-connect="/ask/stream/{turn_id}"` so the
    browser opens the SSE stream against this turn.

    WR-02: when ``len(_TURNS) >= _TURN_SOFT_CAP`` we evict the oldest entry
    (insertion order). This bounds the dict in pathological no-stream-attached
    cases without breaking the normal POST /ask/chat → GET /ask/stream pairing.
    """
    turn_id = uuid.uuid4().hex
    with _TURN_LOCK:
        if len(_TURNS) >= _TURN_SOFT_CAP:
            # Evict oldest by insertion order. Eviction is intentionally silent —
            # this is best-effort cleanup for orphaned (stream-never-opened)
            # turns; in normal operation pop_turn fires from the SSE
            # BackgroundTask before the cap is approached.
            _TURNS.pop(next(iter(_TURNS)), None)
        _TURNS[turn_id] = TurnState(pending_question=question, session_id=session_id)
    return turn_id


def get_cancel_event(turn_id: str) -> asyncio.Event:
    """Return the per-turn asyncio.Event the chat-loop checks between tool calls.

    The chat-loop (chat_loop.stream_chat_turn) checks `cancel_event.is_set()`
    between FunctionToolResultEvent boundaries — the D-CHAT-01 cooperative
    cancellation invariant. Raises KeyError if the turn does not exist.
    """
    with _TURN_LOCK:
        return _TURNS[turn_id].cancel_event


def get_pending_question(turn_id: str) -> str:
    """Return the question string the user submitted with this turn.

    The SSE route (plan 03-04) reads this so it can pass `question` into
    stream_chat_turn without the browser needing to round-trip the same string
    through the URL.
    """
    with _TURN_LOCK:
        return _TURNS[turn_id].pending_question


def get_session_id_for_turn(turn_id: str) -> str:
    """Return the session_id this turn was registered under.

    The SSE route uses this to fetch the message_history and to know which
    session to append the run's new_messages back to.
    """
    with _TURN_LOCK:
        return _TURNS[turn_id].session_id


def cancel_turn(turn_id: str) -> None:
    """D-CHAT-01 — flip the per-turn cancel_event.

    Called from POST /ask/cancel/{turn_id}. The chat-loop checks the event
    between tool calls and emits a final 'stopped-by-user' error frame on
    the next checkpoint. No-op if the turn id is unknown (already-completed
    turns simply ignore the flag — T-03-03-05).
    """
    with _TURN_LOCK:
        if turn_id in _TURNS:
            _TURNS[turn_id].cancel_event.set()


def pop_turn(turn_id: str) -> None:
    """Cleanup helper — passed as BackgroundTask to EventSourceResponse.

    Starlette runs the BackgroundTask AFTER the response body finishes
    streaming (RESEARCH Pitfall 3). The pop is idempotent — popping an
    already-removed turn is a no-op.
    """
    with _TURN_LOCK:
        _TURNS.pop(turn_id, None)


# --- Session lifecycle helpers -------------------------------------------


def get_or_create_session(session_id: str) -> SessionState:
    """Return the SessionState for this browser session (creating if absent).

    Called by get_session_history and append_session_history; also exposed
    publicly so any future admin/test endpoint can introspect a session's
    message store without re-implementing the lock dance.
    """
    with _SESSION_LOCK:
        if session_id not in _SESSIONS:
            _SESSIONS[session_id] = SessionState()
        return _SESSIONS[session_id]


def get_session_history(session_id: str, limit: int = 12) -> list[ModelMessage]:
    """Return the last ``limit`` ModelMessage entries (D-CHAT-15 sliding window),
    re-anchored to the nearest UserPromptPart boundary.

    Default limit=12 = 6 user/agent pairs (one user ModelRequest + one agent
    ModelResponse per turn typically).

    The LLM context is what gets truncated; the user-visible transcript shows
    everything (rendered by the SSE event swap engine in plan 03-04).

    OPENAI BOUNDARY FIX: a naive ``state.messages[-limit:]`` can land mid-turn
    on a ``ModelRequest`` whose first part is a ``ToolReturnPart`` (tool reply)
    without the preceding ``ModelResponse`` containing the matching
    ``ToolCallPart``. OpenAI's chat-completions API rejects this with:
       400 — "messages with role 'tool' must be a response to a preceeding
       message with 'tool_calls'."
    To prevent that, we walk forward from the slice start until we find a
    ``ModelRequest`` that contains a ``UserPromptPart`` (a fresh user-initiated
    exchange) and slice from there. If no such anchor exists in the window,
    start with an empty history — the agent loses context but doesn't error.
    """
    from pydantic_ai.messages import ModelRequest, UserPromptPart

    state = get_or_create_session(session_id)
    window = list(state.messages[-limit:])

    for idx, msg in enumerate(window):
        if isinstance(msg, ModelRequest) and any(
            isinstance(part, UserPromptPart) for part in msg.parts
        ):
            return window[idx:]

    return []


def append_session_history(
    session_id: str,
    new_messages: list[ModelMessage],
    *,
    active_llm_type: Literal["openai", "ollama"],
) -> None:
    """Append agent_run.new_messages() to the session store.

    D-CHAT-11 "both" policy: when active_llm_type=='openai', scrub ALL strings
    in UserPromptPart, ToolReturnPart, and ToolCallPart args before they enter
    history (so the next turn's message_history replay does not leak
    filesystem paths to the cloud LLM).

    Per Open Question 2 (resolved 2026-05-03): the append is serialized via
    _SESSION_LOCK so concurrent multi-tab writes from the same browser do
    not race. Worst-case multi-tab outcome is interleaved messages, which is
    benign for the [-12:] slice — order across concurrent turns from the same
    browser does not affect downstream replay.
    """
    if active_llm_type == "openai":
        _scrub_messages_inplace(new_messages)
    with _SESSION_LOCK:
        state = _SESSIONS.setdefault(session_id, SessionState())
        state.messages.extend(new_messages)


def clear_session_history(session_id: str) -> None:
    """Drop all messages for ``session_id`` so the next turn starts fresh.

    Backs the POST /ask/clear endpoint (Clear button next to Ask). Idempotent:
    clearing a session that has no messages — or no SessionState yet — is a no-op.
    Acquires _SESSION_LOCK so a concurrent append from another tab can't race.
    """
    with _SESSION_LOCK:
        state = _SESSIONS.get(session_id)
        if state is not None:
            state.messages.clear()


def _scrub_messages_inplace(messages: list[ModelMessage]) -> None:
    """Walk messages and apply scrub_paths to all string content (D-CHAT-11).

    Mutates in place. The walk visits:

      - ModelRequest.parts[*]
        - UserPromptPart.content (str) — the question + replayed user prompts
        - ToolReturnPart.content (str) — the tool result text (run_sql etc.)
      - ModelResponse.parts[*]
        - ToolCallPart.args (dict[str, Any]) — string-valued args only

    All other part types and non-string content are left untouched.

    Per RESEARCH Gap 7 / D-CHAT-11 "both" — same shape verified against
    PydanticAI 1.86.0's ModelMessage taxonomy.
    """
    for m in messages:
        if isinstance(m, ModelRequest):
            for p in m.parts:
                if isinstance(p, UserPromptPart) and isinstance(p.content, str):
                    p.content = scrub_paths(p.content)
                elif isinstance(p, ToolReturnPart) and isinstance(p.content, str):
                    p.content = scrub_paths(p.content)
        elif isinstance(m, ModelResponse):
            for p in m.parts:
                if isinstance(p, ToolCallPart) and isinstance(p.args, dict):
                    p.args = {
                        k: (scrub_paths(v) if isinstance(v, str) else v)
                        for k, v in p.args.items()
                    }


__all__ = [
    "TurnState",
    "SessionState",
    "new_turn",
    "get_cancel_event",
    "get_pending_question",
    "get_session_id_for_turn",
    "cancel_turn",
    "pop_turn",
    "get_or_create_session",
    "get_session_history",
    "append_session_history",
    "clear_session_history",
]
