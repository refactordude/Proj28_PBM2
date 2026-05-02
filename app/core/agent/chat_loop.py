"""Phase 3 chat-loop generator — drives PydanticAI agent.run_stream_events.

Per D-CHAT-01 (cancel between tool result events), D-CHAT-02 (rejection cap=5),
D-CHAT-03 (UsageLimits.tool_calls_limit=chat_max_steps), D-CHAT-04 (terminal
error classification into 8 reasons mapped to hard/soft severity), D-CHAT-12
(140-char truncation), D-CHAT-13 (pill renderers), D-CHAT-15 (message_history
slicing happens in chat_session, replayed here via run_stream_events kwarg).

The single public export is `stream_chat_turn` — an async generator yielding
``{"event": <type>, "html": <fragment> | "payload": <dict>}`` dicts that the
SSE route (plan 03-04) wraps into ServerSentEvent frames.

Layered semantics on top of PydanticAI:
  - cancel_event.is_set() between tool result events  -> emit error 'stopped-by-user' (D-CHAT-01)
  - rejection_counter reaches rejection_cap           -> emit error 'still-rejected-after-5-attempts' (D-CHAT-02)
  - UsageLimitExceeded (chat_max_steps)               -> emit error 'step-budget-exhausted' (D-CHAT-03)
  - timeout / LLM 5xx / connection drop               -> emit error 'timeout' or 'llm-error' (D-CHAT-04)
  - PresentResult delivered                           -> emit 'final' STRUCTURED payload (D-CHAT-05)

WARNING-3 contract: the final SSE frame carries a STRUCTURED payload (summary,
sql, chart_spec_dict, new_messages) — NOT pre-rendered HTML. The router
(plan 03-04) hydrates _final_card.html itself by re-running PresentResult.sql
against app.state.db and constructing the Plotly chart server-side. This keeps
chat_loop pure (no DB access in the agent module) and aligns with threat model
T-03-04-09 (chart_html constructed under router control).

Open Question 4 (RESOLVED): UsageLimitExceeded is caught only when raised
BEFORE the final event is emitted; once `final_emitted=True`, the generator
has already terminated cleanly and any subsequent UsageLimitExceeded is moot.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Callable

import sqlparse
from pydantic_ai import Agent
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import (
    AgentStreamEvent,
    FinalResultEvent,  # noqa: F401 — reserved for future per-event introspection
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelMessage,
    PartDeltaEvent,  # noqa: F401 — reserved for future per-event introspection
    PartEndEvent,  # noqa: F401 — reserved for future per-event introspection
    PartStartEvent,
    RetryPromptPart,
    TextPart,  # noqa: F401 — reserved for future per-event introspection
    ThinkingPart,
    ToolCallPart,  # noqa: F401 — used by isinstance checks in PartStartEvent payload
    ToolReturnPart,
)
from pydantic_ai.run import AgentRunResultEvent
from pydantic_ai.usage import UsageLimits

from app.core.agent.chat_agent import ChartSpec, ChatAgentDeps, PresentResult
from app_v2.templates import templates

_log = logging.getLogger(__name__)

# D-CHAT-12: thought-summary truncation cap (UI-SPEC §C — researcher pick: 140 chars)
_THOUGHT_TRUNCATE_CAP = 140

# D-CHAT-04 reason vocabulary — exhaustive list of error reasons; the
# template _error_card.html (plan 04) maps each to severity + heading + body copy.
HARD_REASONS = frozenset(
    {
        "llm-error",
        "still-rejected-after-5-attempts",
        "stream-dropped",
        "agent-no-final-result",
        "unconfigured",
    }
)
SOFT_REASONS = frozenset({"timeout", "step-budget-exhausted", "stopped-by-user"})


# --- Public entry point ---------------------------------------------------


async def stream_chat_turn(
    *,
    agent: Agent,
    deps: ChatAgentDeps,
    question: str,
    message_history: list[ModelMessage],
    cancel_event: asyncio.Event,
    chat_max_steps: int,
    rejection_cap: int = 5,
    on_run_complete: Callable[[list[ModelMessage]], None] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield {event, html | payload} dicts for each AgentStreamEvent the agent emits.

    See module docstring for the full layered-semantics list.

    Args:
        agent: The PydanticAI Agent built by chat_agent.build_chat_agent.
        deps: ChatAgentDeps carrying the DBAdapter + active_llm_type for path scrub.
        question: The user prompt for this turn (D-CHAT-08).
        message_history: Pre-sliced last-12 ModelMessages from chat_session
            (D-CHAT-15 sliding window already applied by caller).
        cancel_event: Per-turn asyncio.Event from chat_session.get_cancel_event;
            checked between FunctionToolResultEvent boundaries (D-CHAT-01).
        chat_max_steps: Per-turn budget (D-CHAT-03) wired into
            UsageLimits(tool_calls_limit=...).
        rejection_cap: Consecutive REJECTED: tool results before abort (D-CHAT-02).
        on_run_complete: Optional callback receiving the run's new_messages so the
            router can call append_session_history (with path scrub when
            active_llm_type=='openai', per D-CHAT-11). The final SSE frame's payload
            also carries `new_messages` so the router can persist them inline; this
            hook remains for backward-compat with tests that don't drive the SSE.

    Uses agent.run_stream_events (RESEARCH Gap 1 / Open Question 1 RESOLVED) — the
    simpler API; the rejection-counter check fires on FunctionToolResultEvent
    boundaries which is also where the D-CHAT-01 cancel checkpoint sits.
    """
    rejection_counter = 0
    final_emitted = False
    new_messages: list[ModelMessage] = []
    usage_limits = UsageLimits(tool_calls_limit=chat_max_steps)

    try:
        # agent.run_stream_events returns AsyncIterator[AgentStreamEvent | AgentRunResultEvent]
        async for ev in agent.run_stream_events(
            question,
            deps=deps,
            message_history=message_history,
            usage_limits=usage_limits,
        ):
            # AgentRunResultEvent is the terminal payload carrying agent_run.result.
            # AgentRunResult.new_messages() returns ONLY this turn's messages
            # (replayed history excluded — verified in pydantic_ai/run.py).
            #
            # IMPORTANT: ``isinstance(ev, AgentRunResultEvent)`` is the correct
            # discriminator here. ``hasattr(ev, "result")`` would ALSO match
            # ``FunctionToolResultEvent`` (which carries a ``result``
            # ToolReturnPart attribute), wrongly classifying every tool result
            # as the terminal frame.
            if isinstance(ev, AgentRunResultEvent):
                run_result = ev.result
                try:
                    new_messages = list(run_result.new_messages())
                except Exception:  # noqa: BLE001 — defensive; new_messages should not raise
                    new_messages = []
                output = getattr(run_result, "output", None)
                if isinstance(output, PresentResult):
                    # WARNING-3 contract: chat_loop emits STRUCTURED final payload (JSON dict),
                    # NOT pre-rendered HTML. The router (plan 03-04) hydrates the final card by
                    # running PresentResult.sql against app.state.db and rendering _final_card.html
                    # itself with table_html + chart_html populated. Aligned with threat model
                    # T-03-04-09 (chart_html constructed server-side under router control).
                    final_payload = {
                        "summary": output.summary,
                        "sql": output.sql,
                        "chart_spec_dict": output.chart_spec.model_dump(),
                        "new_messages": new_messages,  # router uses for append_session_history
                    }
                    yield {"event": "final", "payload": final_payload}
                    final_emitted = True
                else:
                    yield {"event": "error", "html": _render_error("agent-no-final-result")}
                    final_emitted = True
                break

            payload = _event_to_payload(ev)
            if payload is not None:
                yield payload

            # D-CHAT-02: track REJECTED: prefix on tool results
            if isinstance(ev, FunctionToolResultEvent):
                content = _extract_tool_content(ev)
                if content.startswith("REJECTED:"):
                    rejection_counter += 1
                    if rejection_counter >= rejection_cap:
                        yield {
                            "event": "error",
                            "html": _render_error("still-rejected-after-5-attempts"),
                        }
                        final_emitted = True
                        return  # exit generator (not break — there's no remaining work)
                else:
                    rejection_counter = 0  # reset on non-rejection result

                # D-CHAT-01: cooperative cancel checkpoint between tool calls
                if cancel_event.is_set():
                    yield {"event": "error", "html": _render_error("stopped-by-user")}
                    final_emitted = True
                    return

    except UsageLimitExceeded:
        yield {"event": "error", "html": _render_error("step-budget-exhausted")}
        final_emitted = True
    except asyncio.CancelledError:
        # Browser closed the SSE connection — let it propagate so BackgroundTask cleanup runs
        # (RESEARCH Anti-pattern: don't catch CancelledError and continue).
        raise
    except Exception as exc:  # noqa: BLE001 — terminal classification mirrors run_agent
        msg = str(exc).lower()
        if "timeout" in msg or "max_execution_time" in msg or "deadline" in msg:
            yield {"event": "error", "html": _render_error("timeout")}
        else:
            _log.debug("chat-loop unexpected exception: %s", type(exc).__name__)
            yield {
                "event": "error",
                "html": _render_error("llm-error", detail=type(exc).__name__),
            }
        final_emitted = True

    # If we exited the run cleanly but never emitted a final/error frame, emit a fallback.
    if not final_emitted:
        yield {"event": "error", "html": _render_error("agent-no-final-result")}

    # Hand new_messages to the router callback (router applies path scrub + appends to session).
    if on_run_complete is not None and new_messages:
        on_run_complete(new_messages)


# --- Event-to-payload classifier -----------------------------------------


def _event_to_payload(ev: AgentStreamEvent) -> dict[str, Any] | None:
    """Map a PydanticAI AgentStreamEvent to {event, html} or None to skip.

    UI-SPEC §C: thoughts render as <details> with truncated summary (140 chars).
    UI-SPEC §D/§E: tool_call/tool_result render as compact pills with click-to-expand.

    PartDeltaEvent, PartEndEvent, FinalResultEvent: skipped in Phase 3 default
    (output_type=PresentResult forces structured output, so streaming TextPart
    deltas would be partial JSON the user does not need to see).
    """
    if isinstance(ev, PartStartEvent):
        if isinstance(ev.part, ThinkingPart):
            return {
                "event": "thought",
                "html": _render_thought(ev.part.content),
            }
        # TextPart starts mean the agent is preparing the structured output —
        # skipped per output_type=PresentResult (no plain text in chat output).
        return None

    if isinstance(ev, FunctionToolCallEvent):
        tool_name = ev.part.tool_name
        args = ev.part.args
        return {
            "event": "tool_call",
            "html": _render_tool_call_pill(tool_name, args),
        }

    if isinstance(ev, FunctionToolResultEvent):
        return {
            "event": "tool_result",
            "html": _render_tool_result_pill(ev.result),
        }

    return None


# --- Rendering helpers ----------------------------------------------------
# Delegate to plan 03-04 templates via the Jinja2Blocks `templates` instance.
# These helpers are only invoked at runtime by stream_chat_turn; unit tests of
# this module's pure helpers (_truncate_thought, HARD_REASONS, etc.) do not
# trigger them, so the absence of the templates does not break import.


def _render_thought(content: str) -> str:
    truncated = _truncate_thought(content, _THOUGHT_TRUNCATE_CAP)
    return templates.get_template("ask/_thought_event.html").render(
        truncated=truncated,
        full_content=content,
    )


def _render_tool_call_pill(tool_name: str, args: Any) -> str:
    if tool_name == "run_sql" and isinstance(args, dict) and "sql" in args:
        sql = args["sql"]
        pretty_args = sqlparse.format(sql, reindent=True, keyword_case="upper")
        # UI-SPEC Copywriting: ▸ run_sql("SELECT ... FROM ufs_data LIMIT 50"), ~80 chars
        args_summary = sql.replace("\n", " ").strip()[:80]
    else:
        pretty_args = (
            json.dumps(args, indent=2, ensure_ascii=False, default=str) if args else ""
        )
        if isinstance(args, dict):
            args_summary = ", ".join(f"{k}={v!r}" for k, v in args.items())[:80]
        else:
            args_summary = str(args)[:80]
    return templates.get_template("ask/_tool_call_pill.html").render(
        tool_name=tool_name,
        args_summary=args_summary,
        pretty_args=pretty_args,
    )


def _render_tool_result_pill(result: Any) -> str:
    """result is ToolReturnPart | RetryPromptPart (RESEARCH Pitfall 7)."""
    content = _extract_tool_content_from_result(result)
    rejected = content.startswith("REJECTED:")
    summary_text, full_reason, preview_columns, preview_rows = _summarize_tool_result(
        result, content, rejected
    )
    return templates.get_template("ask/_tool_result_pill.html").render(
        rejected=rejected,
        summary_text=summary_text,
        full_reason=full_reason,
        preview_columns=preview_columns,
        preview_rows=preview_rows,
    )


# WARNING-3 contract: NO _render_final_card helper in this module.
# The router (plan 03-04) owns the final-card render entirely so chat_loop stays
# pure (no DB access, no Plotly construction). chat_loop emits a structured
# final payload {summary, sql, chart_spec_dict, new_messages}; the router runs
# the sql via app.state.db, builds the Plotly chart, and renders _final_card.html
# with table_html + chart_html populated. Aligned with threat model T-03-04-09.


def _render_error(reason: str, *, detail: str = "") -> str:
    severity = "hard" if reason in HARD_REASONS else "soft"
    heading = "Something went wrong." if severity == "hard" else "This turn was stopped."
    body = _ERROR_BODY_BY_REASON.get(reason, "An unexpected error occurred.")
    return templates.get_template("ask/_error_card.html").render(
        severity=severity,
        reason=reason,
        heading=heading,
        body=body,
        detail=detail,
        original_question="",  # router-side wrapper may inject this if it has the question
    )


# Body copy locked in UI-SPEC Copywriting Contract — keep verbatim
_ERROR_BODY_BY_REASON: dict[str, str] = {
    "llm-error": "The LLM service returned an error.",
    "still-rejected-after-5-attempts": "The model rewrote the query 5 times and was still rejected.",
    "stream-dropped": "The connection to the agent was lost.",
    "agent-no-final-result": "The agent stopped without producing a final answer.",
    "unconfigured": "No LLM backend is configured.",
    "timeout": "The agent took longer than the configured timeout. Try a more specific question.",
    "step-budget-exhausted": "The agent reached its step budget without finishing. Try breaking the question into smaller parts.",
    "stopped-by-user": "You stopped this turn.",
}


# --- Truncation + tool-content extraction helpers (RESEARCH Pitfall 7) ----


def _truncate_thought(content: str, cap: int) -> str:
    """UI-SPEC §C: truncate at the last whitespace before char `cap`, append U+2026."""
    text = content.strip()
    if len(text) <= cap:
        return text
    # Find last whitespace at or before `cap`; fall back to hard cut at `cap`.
    cut = text.rfind(" ", 0, cap)
    if cut < cap // 2:  # no good whitespace — hard cut
        cut = cap
    return text[:cut].rstrip() + "…"


def _extract_tool_content(ev: FunctionToolResultEvent) -> str:
    """RESEARCH Pitfall 7: ToolReturnPart vs RetryPromptPart."""
    return _extract_tool_content_from_result(ev.result)


def _extract_tool_content_from_result(result: Any) -> str:
    if isinstance(result, ToolReturnPart):
        return str(result.content)
    if isinstance(result, RetryPromptPart):
        try:
            return result.model_response()
        except Exception:  # noqa: BLE001 — defensive
            return str(result)
    return str(result)


def _summarize_tool_result(
    result: Any, content: str, rejected: bool
) -> tuple[str, str, list, list]:
    """Build summary_text, full_reason, preview_columns, preview_rows for the pill.

    UI-SPEC Copywriting Contract templates:
      - REJECTED: "▸ REJECTED: {first_line_of_reason}"
      - success (run_sql/sample_rows/count_rows): "▸ returned {N} rows"
      - other tools: "▸ {tool_name} ok"
    """
    if rejected:
        full_reason = content[len("REJECTED:"):].strip()
        first_line = full_reason.split("\n", 1)[0]
        return f"▸ REJECTED: {first_line}", full_reason, [], []

    tool_name = getattr(result, "tool_name", None) or ""
    # Detect tabular tool results by <db_data>...</db_data> wrapper (SAFE-05)
    if "<db_data>" in content and "</db_data>" in content:
        body = content.split("<db_data>", 1)[1].split("</db_data>", 1)[0].strip()
        lines = [
            ln
            for ln in body.split("\n")
            if ln.strip() and ln.strip() != "(no rows returned)"
        ]
        if not lines:
            return f"▸ {tool_name or 'tool'} returned 0 rows", "", [], []
        # First line is header (pipe-delimited per _execute_and_wrap)
        header = [c.strip() for c in lines[0].split(" | ")]
        preview_rows = [
            [c.strip() for c in ln.split(" | ")]
            for ln in lines[1 : 1 + 10]  # first 10 rows max per UI-SPEC §E
        ]
        n_rows = max(len(lines) - 1, 0)  # subtract header line
        return f"▸ returned {n_rows} rows", "", header, preview_rows

    # Non-tabular tool (e.g., inspect_schema) — short summary string
    return f"▸ {tool_name or 'tool'} ok", content, [], []


__all__ = ["stream_chat_turn", "HARD_REASONS", "SOFT_REASONS"]
