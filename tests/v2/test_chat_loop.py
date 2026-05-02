"""Unit tests for ``app.core.agent.chat_loop.stream_chat_turn`` — D-CHAT-01/02/03/04.

Drives the chat-loop generator with a fake ``Agent`` whose
``run_stream_events`` is a controlled async generator (RESEARCH Gap 11
fallback approach). No real LLM / DB calls.

Covered stop boundaries:
  - D-CHAT-01: cooperative cancel between FunctionToolResultEvent boundaries
               → final 'stopped-by-user' soft error.
  - D-CHAT-02: 5 consecutive REJECTED: tool results
               → final 'still-rejected-after-5-attempts' hard error.
  - D-CHAT-03: ``UsageLimitExceeded`` raised mid-loop
               → final 'step-budget-exhausted' soft error.
  - D-CHAT-04: unclassified exception
               → final 'llm-error' (or 'timeout' when message contains
               'timeout'/'max_execution_time'/'deadline') hard error.

Also covers the truncation cap helper (D-CHAT-12) and the partition
invariant ``HARD_REASONS | SOFT_REASONS == 8 reasons / no overlap``.
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from app.core.agent.chat_agent import ChatAgentDeps
from app.core.agent.chat_loop import (
    HARD_REASONS,
    SOFT_REASONS,
    _truncate_thought,
    stream_chat_turn,
)
from app.core.agent.config import AgentConfig


# pytest-anyio is provided by the `anyio` package's pytest plugin (no separate
# pytest-asyncio installation needed). Use @pytest.mark.anyio on async tests.


@pytest.fixture
def anyio_backend():
    """Constrain anyio's pytest plugin to the asyncio backend (matches chat_loop)."""
    return "asyncio"


def _make_deps() -> ChatAgentDeps:
    """Build a ChatAgentDeps with model_construct so we can pass a MagicMock for db.

    ``ChatAgentDeps.db`` is annotated as ``DBAdapter``; Pydantic v2 uses an
    ``isinstance`` check by default. ``model_construct`` skips validation,
    which is appropriate for unit tests of chat_loop where db is never read.
    """
    cfg = AgentConfig(allowed_tables=["ufs_data"], chat_max_steps=12)
    return ChatAgentDeps.model_construct(
        db=MagicMock(),
        agent_cfg=cfg,
        active_llm_type="ollama",
    )


# --- D-CHAT-12 thought truncation -----------------------------------------


def test_truncate_thought_under_cap_returns_input_unchanged():
    assert _truncate_thought("hello", 140) == "hello"


def test_truncate_thought_over_cap_appends_ellipsis():
    long = "word " * 50  # ~250 chars
    out = _truncate_thought(long, 140)
    assert len(out) <= 141  # 140 chars + 1 trailing U+2026
    assert out.endswith("…")


# --- D-CHAT-01 cooperative cancel ------------------------------------------


@pytest.mark.anyio
async def test_d_chat_01_cancel_event_set_emits_stopped_by_user():
    """Cancel flag flipped before the first tool result → 'stopped-by-user' soft error."""
    from pydantic_ai.messages import FunctionToolResultEvent, ToolReturnPart

    cancel_event = asyncio.Event()
    cancel_event.set()  # pre-set so cancel is detected on first tool result

    fake_agent = MagicMock()

    async def fake_stream(*a, **kw):
        # Yield one tool result with a non-rejection content; the loop
        # should detect cancel_event.is_set() on this checkpoint and bail.
        yield FunctionToolResultEvent(
            result=ToolReturnPart(
                tool_name="run_sql",
                content="<db_data>\nok\n</db_data>",
            )
        )

    fake_agent.run_stream_events = fake_stream

    events = []
    async for ev in stream_chat_turn(
        agent=fake_agent,
        deps=_make_deps(),
        question="q",
        message_history=[],
        cancel_event=cancel_event,
        chat_max_steps=12,
        rejection_cap=5,
    ):
        events.append(ev)

    error_events = [ev for ev in events if ev["event"] == "error"]
    assert error_events, f"no error event emitted; got: {events}"
    assert any("stopped-by-user" in ev["html"] for ev in error_events)


# --- D-CHAT-02 rejection cap ----------------------------------------------


@pytest.mark.anyio
async def test_d_chat_02_five_consecutive_rejections_emit_retry_cap_error():
    """5 REJECTED: tool results in a row → 'still-rejected-after-5-attempts' hard error."""
    from pydantic_ai.messages import FunctionToolResultEvent, ToolReturnPart

    cancel_event = asyncio.Event()
    fake_agent = MagicMock()

    async def fake_stream(*a, **kw):
        # Emit 6 rejections; the 5th should trip the cap and stop the loop.
        for _ in range(6):
            yield FunctionToolResultEvent(
                result=ToolReturnPart(
                    tool_name="run_sql",
                    content="REJECTED: UNION / INTERSECT / EXCEPT are not allowed",
                )
            )

    fake_agent.run_stream_events = fake_stream

    events = []
    async for ev in stream_chat_turn(
        agent=fake_agent,
        deps=_make_deps(),
        question="q",
        message_history=[],
        cancel_event=cancel_event,
        chat_max_steps=12,
        rejection_cap=5,
    ):
        events.append(ev)
        if ev["event"] == "error":
            break

    assert any(
        "still-rejected-after-5-attempts" in ev.get("html", "")
        for ev in events
        if ev["event"] == "error"
    ), f"retry-cap error not emitted; events: {events}"


@pytest.mark.anyio
async def test_d_chat_02_non_rejection_resets_counter():
    """A non-rejection tool result resets the rejection counter to zero."""
    from pydantic_ai.messages import FunctionToolResultEvent, ToolReturnPart

    cancel_event = asyncio.Event()
    fake_agent = MagicMock()

    async def fake_stream(*a, **kw):
        # 4 rejections then 1 success then 4 more rejections — cap is 5
        # consecutive, so this should NOT trip the cap.
        for _ in range(4):
            yield FunctionToolResultEvent(
                result=ToolReturnPart(tool_name="run_sql", content="REJECTED: bad")
            )
        yield FunctionToolResultEvent(
            result=ToolReturnPart(
                tool_name="run_sql", content="<db_data>\nok\n</db_data>"
            )
        )
        for _ in range(4):
            yield FunctionToolResultEvent(
                result=ToolReturnPart(tool_name="run_sql", content="REJECTED: bad")
            )

    fake_agent.run_stream_events = fake_stream

    events = []
    async for ev in stream_chat_turn(
        agent=fake_agent,
        deps=_make_deps(),
        question="q",
        message_history=[],
        cancel_event=cancel_event,
        chat_max_steps=12,
        rejection_cap=5,
    ):
        events.append(ev)

    error_events = [
        ev for ev in events
        if ev["event"] == "error" and "still-rejected-after-5-attempts" in ev["html"]
    ]
    assert not error_events, "rejection counter must reset on non-rejection result"


# --- D-CHAT-03 step-budget exhaustion --------------------------------------


@pytest.mark.anyio
async def test_d_chat_03_step_budget_exhausted_emits_correct_error():
    """``UsageLimitExceeded`` mid-loop → 'step-budget-exhausted' soft error."""
    from pydantic_ai.exceptions import UsageLimitExceeded

    cancel_event = asyncio.Event()
    fake_agent = MagicMock()

    async def fake_stream(*a, **kw):
        # Make this an async generator that raises before yielding.
        if False:  # pragma: no cover — make this a generator
            yield None
        raise UsageLimitExceeded("limit reached")

    fake_agent.run_stream_events = fake_stream

    events = []
    async for ev in stream_chat_turn(
        agent=fake_agent,
        deps=_make_deps(),
        question="q",
        message_history=[],
        cancel_event=cancel_event,
        chat_max_steps=2,
        rejection_cap=5,
    ):
        events.append(ev)

    assert any(
        "step-budget-exhausted" in ev.get("html", "")
        for ev in events
        if ev["event"] == "error"
    ), f"step-budget error not emitted; events: {events}"


# --- D-CHAT-04 unclassified exception classification ----------------------


@pytest.mark.anyio
async def test_d_chat_04_unexpected_exception_emits_llm_error():
    """An unclassified exception becomes a hard llm-error event."""
    cancel_event = asyncio.Event()
    fake_agent = MagicMock()

    async def fake_stream(*a, **kw):
        if False:  # pragma: no cover — make this a generator
            yield None
        raise RuntimeError("connection refused by openai")

    fake_agent.run_stream_events = fake_stream

    events = []
    async for ev in stream_chat_turn(
        agent=fake_agent,
        deps=_make_deps(),
        question="q",
        message_history=[],
        cancel_event=cancel_event,
        chat_max_steps=12,
        rejection_cap=5,
    ):
        events.append(ev)

    assert any(
        "llm-error" in ev.get("html", "")
        for ev in events
        if ev["event"] == "error"
    ), f"llm-error not emitted; events: {events}"


@pytest.mark.anyio
async def test_d_chat_04_timeout_message_emits_timeout_error():
    """Exception with 'timeout' / 'max_execution_time' / 'deadline' → timeout soft error."""
    cancel_event = asyncio.Event()
    fake_agent = MagicMock()

    async def fake_stream(*a, **kw):
        if False:  # pragma: no cover
            yield None
        raise RuntimeError("query exceeded max_execution_time")

    fake_agent.run_stream_events = fake_stream

    events = []
    async for ev in stream_chat_turn(
        agent=fake_agent,
        deps=_make_deps(),
        question="q",
        message_history=[],
        cancel_event=cancel_event,
        chat_max_steps=12,
        rejection_cap=5,
    ):
        events.append(ev)

    assert any(
        "timeout" in ev.get("html", "")
        for ev in events
        if ev["event"] == "error"
    )


# --- D-CHAT-04 vocabulary partition ----------------------------------------


def test_hard_soft_reason_partition_covers_all_8():
    """The 8 reasons partition cleanly into HARD_REASONS (5) and SOFT_REASONS (3)."""
    expected = {
        "llm-error",
        "still-rejected-after-5-attempts",
        "stream-dropped",
        "agent-no-final-result",
        "unconfigured",
        "timeout",
        "step-budget-exhausted",
        "stopped-by-user",
    }
    assert HARD_REASONS | SOFT_REASONS == expected
    assert HARD_REASONS & SOFT_REASONS == set()  # no reason in both


# --- D-CHAT-05 final payload shape -----------------------------------------


@pytest.mark.anyio
async def test_final_event_payload_has_all_4_keys():
    """WARNING-3 contract: terminal 'final' event carries structured payload."""
    from pydantic_ai.run import AgentRunResultEvent

    from app.core.agent.chat_agent import PresentResult

    cancel_event = asyncio.Event()
    fake_agent = MagicMock()

    class _FakeRunResult:
        """Minimal AgentRunResult-like object — chat_loop only reads .output + new_messages()."""

        def __init__(self, output):
            self.output = output

        def new_messages(self):
            return []

    async def fake_stream(*a, **kw):
        yield AgentRunResultEvent(
            result=_FakeRunResult(PresentResult(summary="ok", sql="SELECT 1 AS a"))
        )

    fake_agent.run_stream_events = fake_stream

    events = []
    async for ev in stream_chat_turn(
        agent=fake_agent,
        deps=_make_deps(),
        question="q",
        message_history=[],
        cancel_event=cancel_event,
        chat_max_steps=12,
        rejection_cap=5,
    ):
        events.append(ev)

    final_events = [ev for ev in events if ev["event"] == "final"]
    assert len(final_events) == 1, f"expected exactly 1 final event; got: {events}"
    payload = final_events[0]["payload"]
    # WARNING-3 four-key contract.
    assert set(payload.keys()) >= {"summary", "sql", "chart_spec_dict", "new_messages"}
    assert payload["summary"] == "ok"
    assert payload["sql"] == "SELECT 1 AS a"


@pytest.mark.anyio
async def test_terminal_event_with_non_present_result_emits_agent_no_final_result():
    """Terminal AgentRunResultEvent carrying non-PresentResult → 'agent-no-final-result' hard error."""
    from pydantic_ai.run import AgentRunResultEvent

    cancel_event = asyncio.Event()
    fake_agent = MagicMock()

    class _FakeRunResult:
        def __init__(self):
            self.output = None  # NOT a PresentResult

        def new_messages(self):
            return []

    async def fake_stream(*a, **kw):
        yield AgentRunResultEvent(result=_FakeRunResult())

    fake_agent.run_stream_events = fake_stream

    events = []
    async for ev in stream_chat_turn(
        agent=fake_agent,
        deps=_make_deps(),
        question="q",
        message_history=[],
        cancel_event=cancel_event,
        chat_max_steps=12,
        rejection_cap=5,
    ):
        events.append(ev)

    assert any(
        "agent-no-final-result" in ev.get("html", "")
        for ev in events
        if ev["event"] == "error"
    )
