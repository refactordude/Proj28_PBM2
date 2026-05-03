"""Unit tests for ``app.core.agent.chat_session`` — D-CHAT-11 + D-CHAT-15.

Covers:
  - new_turn / get_pending_question / get_session_id_for_turn / cancel_turn / pop_turn
    lifecycle (T-03-03-05 idempotency).
  - get_session_history sliding window (D-CHAT-15) — returns at most last 12
    ModelMessage entries.
  - append_session_history scrub-on-write policy (D-CHAT-11 "both") — applied
    when active_llm_type=='openai', skipped for 'ollama'.
  - _scrub_messages_inplace walks UserPromptPart, ToolReturnPart, ToolCallPart
    args (string-valued only).

All tests reset the module-level ``_TURNS`` / ``_SESSIONS`` registries before
AND after each test (T-03-05-01 mitigation).
"""
from __future__ import annotations

import pytest
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from app.core.agent.chat_session import (
    _SESSIONS,
    _TURNS,
    _scrub_messages_inplace,
    append_session_history,
    cancel_turn,
    get_cancel_event,
    get_or_create_session,
    get_pending_question,
    get_session_history,
    get_session_id_for_turn,
    new_turn,
    pop_turn,
)


@pytest.fixture(autouse=True)
def _reset_registries():
    _TURNS.clear()
    _SESSIONS.clear()
    yield
    _TURNS.clear()
    _SESSIONS.clear()


# --- Turn lifecycle (T-03-03-05) -------------------------------------------


def test_new_turn_creates_unique_id():
    a = new_turn("s1", "q1")
    b = new_turn("s1", "q2")
    assert a != b
    assert len(a) == 32  # uuid4().hex


def test_get_pending_question_returns_original():
    t = new_turn("s1", "compare X across SM8850 and SM8650")
    assert get_pending_question(t) == "compare X across SM8850 and SM8650"


def test_get_session_id_for_turn_returns_owner():
    t = new_turn("session_xyz", "q")
    assert get_session_id_for_turn(t) == "session_xyz"


def test_get_session_id_for_unknown_turn_raises_keyerror():
    with pytest.raises(KeyError):
        get_session_id_for_turn("not-a-real-turn")


def test_cancel_turn_sets_event():
    t = new_turn("s1", "q")
    ev = get_cancel_event(t)
    assert not ev.is_set()
    cancel_turn(t)
    assert ev.is_set()


def test_cancel_turn_on_unknown_id_is_noop():
    """T-03-03-05 — cancel after pop_turn (already-completed turn) must not raise."""
    cancel_turn("not-a-real-turn")  # no exception


def test_pop_turn_removes_entry_idempotently():
    t = new_turn("s1", "q")
    pop_turn(t)
    with pytest.raises(KeyError):
        get_session_id_for_turn(t)
    # Idempotent — popping again does not raise.
    pop_turn(t)


# --- D-CHAT-15 sliding window ----------------------------------------------


def test_session_history_sliding_window_d_chat_15():
    """D-CHAT-15 — get_session_history returns at most the last 12 messages."""
    sid = "s1"
    msgs = [
        ModelRequest(parts=[UserPromptPart(content=f"msg{i}")]) for i in range(20)
    ]
    append_session_history(sid, msgs, active_llm_type="ollama")
    hist = get_session_history(sid, limit=12)
    assert len(hist) == 12
    contents = [m.parts[0].content for m in hist]
    assert contents == [f"msg{i}" for i in range(8, 20)]


def test_session_history_default_limit_is_12():
    sid = "s1"
    msgs = [
        ModelRequest(parts=[UserPromptPart(content=f"msg{i}")]) for i in range(15)
    ]
    append_session_history(sid, msgs, active_llm_type="ollama")
    hist = get_session_history(sid)  # default limit
    assert len(hist) == 12


def test_session_history_reanchors_to_user_prompt_to_avoid_orphan_tool():
    """OPENAI BOUNDARY FIX — slicing [-limit:] can land mid-turn at an
    orphaned ToolReturnPart (a tool reply without its preceding assistant
    tool_calls message). OpenAI rejects that with:
      400 — "messages with role 'tool' must be a response to a preceeding
      message with 'tool_calls'."
    get_session_history walks the slice forward until it finds a
    ModelRequest containing a UserPromptPart and starts there.
    """
    from pydantic_ai.messages import (
        ModelResponse,
        TextPart,
        ToolCallPart,
        ToolReturnPart,
    )

    sid = "s_reanchor"
    # Build a 4-message conversation:
    #   0: ModelRequest [UserPromptPart "u0"]
    #   1: ModelResponse [ToolCallPart]
    #   2: ModelRequest [ToolReturnPart]                   ← orphan if sliced from here
    #   3: ModelRequest [UserPromptPart "u3"]              ← safe anchor
    msgs = [
        ModelRequest(parts=[UserPromptPart(content="u0")]),
        ModelResponse(parts=[ToolCallPart(tool_name="t", args={}, tool_call_id="c1")]),
        ModelRequest(parts=[ToolReturnPart(tool_name="t", content="r", tool_call_id="c1")]),
        ModelRequest(parts=[UserPromptPart(content="u3")]),
    ]
    append_session_history(sid, msgs, active_llm_type="ollama")

    # limit=2 would naively grab indices [2, 3] — leading with the orphan tool.
    # The re-anchor should drop the tool message and start at index 3.
    hist = get_session_history(sid, limit=2)
    assert len(hist) == 1, f"expected re-anchored slice of length 1; got {len(hist)}"
    assert isinstance(hist[0], ModelRequest)
    assert any(isinstance(p, UserPromptPart) for p in hist[0].parts)


def test_session_history_returns_empty_when_no_user_anchor_in_window():
    """If the slice window contains NO ModelRequest with a UserPromptPart,
    return an empty history rather than risk an OpenAI 400 on the next turn.
    The agent loses context but doesn't error.
    """
    from pydantic_ai.messages import (
        ModelResponse,
        ToolCallPart,
        ToolReturnPart,
    )

    sid = "s_no_anchor"
    msgs = [
        ModelRequest(parts=[UserPromptPart(content="u")]),
        ModelResponse(parts=[ToolCallPart(tool_name="t", args={}, tool_call_id="c1")]),
        ModelRequest(parts=[ToolReturnPart(tool_name="t", content="r", tool_call_id="c1")]),
        ModelResponse(parts=[ToolCallPart(tool_name="t", args={}, tool_call_id="c2")]),
        ModelRequest(parts=[ToolReturnPart(tool_name="t", content="r", tool_call_id="c2")]),
    ]
    append_session_history(sid, msgs, active_llm_type="ollama")

    # limit=3 grabs the last 3 (indices 2,3,4) — none is a UserPromptPart.
    hist = get_session_history(sid, limit=3)
    assert hist == [], f"expected empty history when no UserPromptPart in window; got {len(hist)} messages"


def test_session_history_short_returns_all():
    sid = "s1"
    msgs = [
        ModelRequest(parts=[UserPromptPart(content=f"msg{i}")]) for i in range(3)
    ]
    append_session_history(sid, msgs, active_llm_type="ollama")
    hist = get_session_history(sid)
    assert len(hist) == 3


def test_get_or_create_session_returns_same_state_on_repeat():
    a = get_or_create_session("s1")
    b = get_or_create_session("s1")
    assert a is b


# --- D-CHAT-11 scrub-on-write (OpenAI only) -------------------------------


def test_scrub_on_write_when_active_llm_is_openai():
    """D-CHAT-11 'both' policy — UserPromptPart / ToolReturnPart / ToolCallPart args scrubbed."""
    sid = "s1"
    msgs = [
        ModelRequest(
            parts=[
                UserPromptPart(content="check /sys/block/sda/queue/depth"),
                ToolReturnPart(
                    tool_name="run_sql",
                    content="<db_data>path: /proc/loadavg</db_data>",
                ),
            ]
        ),
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="run_sql",
                    args={"sql": "SELECT * FROM ufs_data WHERE Result LIKE '/dev/sda%'"},
                ),
            ]
        ),
    ]
    append_session_history(sid, msgs, active_llm_type="openai")
    hist = get_session_history(sid)
    # All path-shaped strings replaced with <path>
    user_text = hist[0].parts[0].content
    assert "/sys/block" not in user_text
    assert "<path>" in user_text

    tool_return_text = hist[0].parts[1].content
    assert "/proc/loadavg" not in tool_return_text
    assert "<path>" in tool_return_text

    tool_call_args = hist[1].parts[0].args
    assert "/dev/sda" not in tool_call_args["sql"]
    assert "<path>" in tool_call_args["sql"]


def test_no_scrub_when_active_llm_is_ollama():
    """Path scrub only fires for OpenAI — Ollama is local intranet (D-CHAT-11)."""
    sid = "s1"
    msgs = [ModelRequest(parts=[UserPromptPart(content="check /sys/block/sda")])]
    append_session_history(sid, msgs, active_llm_type="ollama")
    hist = get_session_history(sid)
    assert "/sys/block/sda" in hist[0].parts[0].content


def test_scrub_messages_inplace_visits_three_part_types():
    """_scrub_messages_inplace walks UserPromptPart, ToolReturnPart, ToolCallPart args."""
    msgs = [
        ModelRequest(
            parts=[
                UserPromptPart(content="user wrote /proc/version"),
                ToolReturnPart(tool_name="run_sql", content="result: /dev/null"),
            ]
        ),
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="run_sql",
                    args={"sql": "SELECT * /sys/block/sdb"},
                ),
            ]
        ),
    ]
    _scrub_messages_inplace(msgs)
    assert "<path>" in msgs[0].parts[0].content
    assert "/proc" not in msgs[0].parts[0].content
    assert "<path>" in msgs[0].parts[1].content
    assert "/dev/null" not in msgs[0].parts[1].content
    assert "<path>" in msgs[1].parts[0].args["sql"]
    assert "/sys" not in msgs[1].parts[0].args["sql"]


def test_scrub_skips_non_string_tool_call_args():
    """Non-string ToolCallPart args (e.g., numeric limit) pass through unchanged."""
    msgs = [
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="sample_rows",
                    args={"where_clause": "PLATFORM_ID='X'", "limit": 10},
                ),
            ]
        ),
    ]
    _scrub_messages_inplace(msgs)
    assert msgs[0].parts[0].args["limit"] == 10  # int unchanged


def test_append_history_extends_existing():
    """Sequential appends to same session accumulate."""
    sid = "s1"
    append_session_history(
        sid,
        [ModelRequest(parts=[UserPromptPart(content="first")])],
        active_llm_type="ollama",
    )
    append_session_history(
        sid,
        [ModelRequest(parts=[UserPromptPart(content="second")])],
        active_llm_type="ollama",
    )
    hist = get_session_history(sid)
    contents = [m.parts[0].content for m in hist]
    assert contents == ["first", "second"]
