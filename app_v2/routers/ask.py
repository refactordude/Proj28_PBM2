"""Phase 3 D-CHAT-08: rewritten Ask router (multi-step agentic chat).

Routes:
  GET  /ask                       — chat shell (replaces v2.0 Phase 6 single-shot Q&A page)
  POST /ask/chat                  — start a new turn; returns user-message + SSE consumer fragment
  GET  /ask/stream/{turn_id}      — SSE stream (async def — REQUIRED for streaming)
  POST /ask/cancel/{turn_id}      — flip cancel_event (async def — pure registry mutation)

REMOVED in this plan (D-CHAT-09 atomic boundary):
  POST /ask/query    — Phase 6 one-shot Q&A handler
  POST /ask/confirm  — Phase 6 NL-05 two-turn confirmation handler

Phase 6 invariant ``test_no_async_def_in_phase6_router`` is REPLACED by a Phase 3
invariant (plan 05) that allows async only on the streaming + cancel routes and
forbids any synchronous PydanticAI runner call anywhere in this file.

Threat model alignments (per 03-04-PLAN.md):
  - T-03-04-01/02: ``GET /ask/stream`` and ``POST /ask/cancel`` check the
    ``pbm2_session`` cookie against ``chat_session.get_session_id_for_turn`` and
    return 403 on mismatch. ``turn_id`` itself is uuid4().hex (128-bit entropy).
  - T-03-04-04: every agent-supplied template variable uses Jinja's ``| e``
    autoescape filter (templates carry the contract; this router just renders).
  - T-03-04-09: the Plotly chart HTML is constructed server-side here from the
    typed ChartSpec — column names are validated against ``df.columns`` before
    plotting (silent downgrade to ``chart_type='none'`` when missing) so the
    ``| safe`` filter on ``chart_html`` in ``_final_card.html`` only ever
    receives router-produced markup.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Annotated, Any

import pandas as pd
import sqlalchemy as sa
from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from sse_starlette import EventSourceResponse, ServerSentEvent
from starlette.background import BackgroundTask

from app.adapters.llm.pydantic_model import build_pydantic_model
from app.core.agent.chat_agent import (
    ChartSpec,
    ChatAgentDeps,
    PresentResult,
    build_chat_agent,
)
from app.core.agent.chat_loop import stream_chat_turn
from app.core.agent.chat_session import (
    append_session_history,
    cancel_turn,
    get_cancel_event,
    get_pending_question,
    get_session_history,
    get_session_id_for_turn,
    new_turn,
    pop_turn,
)
from app.services.sql_limiter import inject_limit
from app.services.sql_validator import validate_sql

from app_v2.services.llm_resolver import (
    resolve_active_backend_name,
    resolve_active_llm,
)
from app_v2.templates import templates

_log = logging.getLogger(__name__)

router = APIRouter()

# RESEARCH Gap 6 / Pitfall 8: pbm2_session cookie shape mirrors pbm2_llm.
_PBM2_SESSION_COOKIE = "pbm2_session"

# WR-04: known-local LLM backends (no path scrub needed — local inference,
# no cloud egress). Anything NOT in this set is treated as cloud and gets the
# D-CHAT-11 path-scrub policy applied (default-deny posture). Extend this set
# when a new local backend is introduced.
_LOCAL_LLM_TYPES = frozenset({"ollama"})


# --- Cookie helper --------------------------------------------------------


def _ensure_session_cookie(request: Request, response: Response) -> str:
    """Return the active ``pbm2_session`` value, setting the cookie when missing.

    RESEARCH Gap 6 / Pitfall 8: cookie shape mirrors ``pbm2_llm`` —
    ``HttpOnly=True``, ``SameSite=Lax``, ``Secure=False`` (intranet HTTP per
    project constraints). 1-year ``max_age`` so the same session is preserved
    across browser restarts.

    NOTE: FastAPI's ``Response`` parameter merges Set-Cookie headers into the
    final response only when the route returns a non-``Response`` object. Both
    /ask and /ask/chat return a ``TemplateResponse`` directly, so callers that
    need the cookie to actually reach the browser MUST also call
    ``_apply_session_cookie(template_response, sid)`` on the returned response.
    This helper still flips the parameter ``response`` for routes that DO use
    the merge path (and is harmless when they don't).
    """
    sid = request.cookies.get(_PBM2_SESSION_COOKIE)
    if sid:
        return sid
    sid = uuid.uuid4().hex
    response.set_cookie(
        _PBM2_SESSION_COOKIE,
        sid,
        max_age=31536000,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return sid


def _apply_session_cookie(response: Response, request: Request, sid: str) -> None:
    """Set ``pbm2_session`` on ``response`` only when the request did not carry it.

    Used by routes that return a ``TemplateResponse`` directly — FastAPI's
    parameter-Response merge does NOT apply in that case, so we set the cookie
    on the actual response object. Idempotent: skipped when the request already
    carried a ``pbm2_session`` value (no point re-issuing the same id).
    """
    if request.cookies.get(_PBM2_SESSION_COOKIE) == sid:
        return  # client already has it
    response.set_cookie(
        _PBM2_SESSION_COOKIE,
        sid,
        max_age=31536000,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


# --- Routes ---------------------------------------------------------------


@router.get("/ask", response_class=HTMLResponse)
def ask_page(request: Request, response: Response):
    """Chat shell. No starter chips (D-CHAT-10). LLM dropdown verbatim from Phase 6 (D-CHAT-11)."""
    settings = getattr(request.app.state, "settings", None)
    backend_name = resolve_active_backend_name(settings, request)
    active_llm = resolve_active_llm(settings, request)
    llms = list(getattr(settings, "llms", []) or []) if settings is not None else []
    sid = _ensure_session_cookie(request, response)

    tr = templates.TemplateResponse(
        request,
        "ask/index.html",
        {
            "active_tab": "ask",
            "page_title": "Ask",
            "backend_name": backend_name,
            "llm_cfg": active_llm,
            "llms": llms,
        },
    )
    _apply_session_cookie(tr, request, sid)
    return tr


@router.post("/ask/chat", response_class=HTMLResponse)
def ask_chat(
    request: Request,
    response: Response,
    question: Annotated[str, Form()] = "",
):
    """Start a new turn. Returns the user-message fragment + SSE consumer + OOB Stop swap.

    SYNC ``def`` — does not stream; only registers the turn and returns the
    initial HTML fragment. Phase 3 invariant (plan 05) allows ``async`` only on
    ``/ask/stream`` and ``/ask/cancel``.
    """
    sid = _ensure_session_cookie(request, response)
    q = (question or "").strip()
    turn_id = new_turn(sid, q)

    tr = templates.TemplateResponse(
        request,
        "ask/_user_message.html",
        {"turn_id": turn_id, "question": q},
    )
    _apply_session_cookie(tr, request, sid)
    return tr


@router.get("/ask/stream/{turn_id}")
async def ask_stream(turn_id: str, request: Request):
    """SSE endpoint. ASYNC ``def`` is REQUIRED here for the streaming response.

    Phase 6 invariant ``test_no_async_def_in_phase6_router`` is replaced in
    plan 05 by a narrowed Phase 3 invariant that allows async on
    ``/ask/stream`` and ``/ask/cancel`` only.
    """
    settings = getattr(request.app.state, "settings", None)

    # T-03-04-01: turn_id must belong to the requesting browser session.
    request_sid = request.cookies.get(_PBM2_SESSION_COOKIE) or ""
    try:
        owner_sid = get_session_id_for_turn(turn_id)
    except KeyError:
        return Response(status_code=404)
    if owner_sid != request_sid:
        return Response(status_code=403)

    llm_cfg = resolve_active_llm(settings, request)
    if llm_cfg is None:
        return EventSourceResponse(
            _unconfigured_event_generator(),
            background=BackgroundTask(pop_turn, turn_id),
        )

    db_adapter = getattr(request.app.state, "db", None)
    if db_adapter is None:
        return EventSourceResponse(
            _unconfigured_event_generator(),
            background=BackgroundTask(pop_turn, turn_id),
        )

    agent_cfg = getattr(getattr(settings, "app", None), "agent", None)
    if agent_cfg is None:
        return EventSourceResponse(
            _unconfigured_event_generator(),
            background=BackgroundTask(pop_turn, turn_id),
        )
    # WR-04: default-deny path-scrub policy. Any backend type that is NOT
    # explicitly known-local (`_LOCAL_LLM_TYPES`) is treated as cloud and gets
    # the D-CHAT-11 scrub applied. This protects against silent regression if a
    # future cloud backend (e.g. anthropic) is added without updating this gate.
    # The `active_llm_type` Literal admits only "openai" / "ollama"; we map any
    # non-local type to "openai" so the existing scrub_paths gate fires.
    raw_llm_type = getattr(llm_cfg, "type", "") or ""
    if raw_llm_type in _LOCAL_LLM_TYPES:
        active_llm_type = "ollama"
    else:
        if raw_llm_type and raw_llm_type != "openai":
            _log.warning(
                "unknown LLM type %r — applying cloud path-scrub policy "
                "(treating as openai for scrub purposes)",
                raw_llm_type,
            )
        active_llm_type = "openai"
    deps = ChatAgentDeps(
        db=db_adapter,
        agent_cfg=agent_cfg,
        active_llm_type=active_llm_type,
    )
    pydantic_ai_model = build_pydantic_model(llm_cfg)
    agent = build_chat_agent(pydantic_ai_model)

    cancel_event = get_cancel_event(turn_id)
    question = get_pending_question(turn_id)
    msg_history = get_session_history(owner_sid, limit=12)
    chat_max_steps = int(getattr(agent_cfg, "chat_max_steps", 12))

    async def event_generator():
        async for ev in stream_chat_turn(
            agent=agent,
            deps=deps,
            question=question,
            message_history=msg_history,
            cancel_event=cancel_event,
            chat_max_steps=chat_max_steps,
            rejection_cap=5,
        ):
            # WARNING-3 PINNED CONTRACT: chat_loop emits a STRUCTURED payload
            # for "final" events; this router renders ``_final_card.html``
            # itself with table_html + chart_html populated via
            # ``_hydrate_final_card`` (which queries app.state.db).
            # All other events arrive as pre-rendered HTML in ev["html"].
            if ev["event"] == "final":
                payload = ev["payload"]
                # WR-03: ``_hydrate_final_card`` runs sync ``pd.read_sql_query``
                # against the pymysql/SQLAlchemy stack. Dispatch to a thread so
                # the event loop is free to service other SSE streams + cancel
                # endpoints during the final SQL execution.
                html = await asyncio.to_thread(
                    _hydrate_final_card,
                    payload=payload,
                    deps=deps,
                    request=request,
                    owner_sid=owner_sid,
                    active_llm_type=active_llm_type,
                    original_question=question,
                )
                yield ServerSentEvent(event="final", data=html)
            else:
                yield ServerSentEvent(event=ev["event"], data=ev["html"])

    return EventSourceResponse(
        event_generator(),
        background=BackgroundTask(pop_turn, turn_id),
        ping=15,
    )


@router.post("/ask/cancel/{turn_id}")
async def ask_cancel(turn_id: str, request: Request) -> Response:
    """Flip the per-turn ``cancel_event``. Authenticated to the originating session.

    T-03-04-02: same session-ownership check as the SSE endpoint. ``async`` is
    acceptable here — the body is a pure registry mutation (no call into the
    legacy synchronous PydanticAI runner or ``run_nl_query``).
    """
    request_sid = request.cookies.get(_PBM2_SESSION_COOKIE) or ""
    try:
        owner_sid = get_session_id_for_turn(turn_id)
    except KeyError:
        return Response(status_code=404)
    if owner_sid != request_sid:
        return Response(status_code=403)
    cancel_turn(turn_id)
    return Response(status_code=204)


# --- Internal helpers -----------------------------------------------------


async def _unconfigured_event_generator():
    """Emit a single ``error`` event and close — used when no LLM/DB/agent_cfg is available."""
    html = templates.get_template("ask/_error_card.html").render(
        severity="hard",
        reason="unconfigured",
        heading="Something went wrong.",
        body="No LLM backend is configured.",
        detail="",
        original_question="",
    )
    yield ServerSentEvent(event="error", data=html)


class _GridVM:
    """Minimal view-model that satisfies ``browse/_grid.html``'s ``vm.df_wide`` /
    ``vm.index_col_name`` contract.

    The Browse macro iterates ``vm.df_wide.iterrows()`` and reads
    ``row[vm.index_col_name]`` — nothing else. We don't reuse
    ``BrowseViewModel`` because ``_final_card.html`` only needs the two fields
    the macro actually touches; this also avoids importing the heavyweight
    Browse view-model into the Ask router.
    """

    def __init__(self, df_wide: pd.DataFrame, index_col_name: str) -> None:
        self.df_wide = df_wide
        self.index_col_name = index_col_name


def _hydrate_final_card(
    *,
    payload: dict[str, Any],
    deps: ChatAgentDeps,
    request: Request,
    owner_sid: str,
    active_llm_type: str,
    original_question: str,
) -> str:
    """WARNING-3 PINNED CONTRACT: hydrate ``_final_card.html`` server-side.

    Receives the structured final payload ``{summary, sql, chart_spec_dict,
    new_messages}`` from ``chat_loop.stream_chat_turn`` (NOT pre-rendered
    HTML). The router OWNS the entire final-card render so chat_loop stays
    pure (no DB / no Plotly in the agent module).

    Steps:
      1. Re-run ``payload["sql"]`` through SAFE-02..06 (validate_sql +
         inject_limit) and execute via ``request.app.state.db.run_query``.
         On validator rejection or execution error, fall back to
         ``table_html=""`` / ``row_count=0`` and continue (the user still
         gets the summary).
      2. Build the table HTML using the existing Browse ``_grid.html`` macro
         (RESEARCH Gap 9).
      3. Reconstruct ``chart_spec`` from the dict and (per Open Question 3
         RESOLVED — silent downgrade) skip the chart when columns are
         missing or chart_type=='none'.
      4. Persist new_messages to the session history (D-CHAT-11 path scrub
         fires inside ``append_session_history`` when the active LLM is
         OpenAI).
      5. Render ``ask/_final_card.html`` and return its HTML.
    """
    summary = payload.get("summary", "") or ""
    sql = payload.get("sql", "") or ""
    chart_spec_dict = payload.get("chart_spec_dict") or {}
    new_messages = payload.get("new_messages") or []

    # Step 1 — execute the agent-supplied SQL through the SAFE-02..06 harness.
    df = pd.DataFrame()
    table_html = ""
    row_count = 0
    chart_html = ""
    if sql.strip():
        try:
            vr = validate_sql(sql, deps.agent_cfg.allowed_tables)
            if vr.ok:
                safe_sql = inject_limit(sql, deps.agent_cfg.row_cap)
                db_adapter = request.app.state.db
                # Use the adapter's engine when available so we can apply the
                # session-level READ ONLY + max_execution_time guards (matches
                # ``chat_agent._execute_and_wrap``); fall back to ``run_query``
                # for adapters without ``_get_engine``.
                engine_fn = getattr(db_adapter, "_get_engine", None)
                timeout_ms = int(deps.agent_cfg.timeout_s) * 1000
                try:
                    if engine_fn is None:
                        df = db_adapter.run_query(safe_sql)
                    else:
                        with engine_fn().connect() as conn:
                            try:
                                conn.execute(sa.text("SET SESSION TRANSACTION READ ONLY"))
                            except Exception:  # noqa: BLE001 — session pragma may be unsupported
                                pass
                            try:
                                conn.execute(
                                    sa.text(
                                        f"SET SESSION max_execution_time={timeout_ms}"
                                    )
                                )
                            except Exception:  # noqa: BLE001
                                pass
                            df = pd.read_sql_query(sa.text(safe_sql), conn)
                except Exception as exc:  # noqa: BLE001 — DB issue → render summary-only card
                    _log.warning(
                        "final-card SQL execution failed (%s); rendering summary-only card",
                        type(exc).__name__,
                    )
                    df = pd.DataFrame()
            else:
                _log.warning(
                    "final-card SQL rejected by validator: %s", vr.reason
                )
        except Exception as exc:  # noqa: BLE001
            _log.warning(
                "final-card SQL hydration failed (%s)", type(exc).__name__
            )
            df = pd.DataFrame()

    # Step 2 — Browse macro reuse for the table portion (RESEARCH Gap 9).
    if not df.empty:
        index_col_name = str(df.columns[0]) if len(df.columns) else ""
        vm = _GridVM(df_wide=df, index_col_name=index_col_name)
        try:
            table_html = templates.get_template("browse/_grid.html").render(vm=vm)
            row_count = int(len(df))
        except Exception as exc:  # noqa: BLE001 — defensive: never break the SSE stream on a render hiccup
            _log.warning("final-card table render failed (%s)", type(exc).__name__)
            table_html = ""
            row_count = 0

    # Step 3 — Plotly chart, silent downgrade per RESEARCH Open Question 3.
    chart_spec = ChartSpec(**chart_spec_dict) if chart_spec_dict else ChartSpec()
    if (
        chart_spec.chart_type != "none"
        and chart_spec.x_column
        and chart_spec.y_column
        and not df.empty
        and chart_spec.x_column in df.columns
        and chart_spec.y_column in df.columns
    ):
        try:
            chart_html = _build_plotly_chart_html(df, chart_spec)
        except Exception as exc:  # noqa: BLE001 — defensive
            _log.warning("final-card chart render failed (%s)", type(exc).__name__)
            chart_html = ""

    # Step 4 — persist new messages with D-CHAT-11 path scrub.
    if new_messages:
        try:
            append_session_history(
                owner_sid,
                new_messages,
                active_llm_type=active_llm_type,
            )
        except Exception as exc:  # noqa: BLE001
            _log.warning(
                "session-history append failed (%s)", type(exc).__name__
            )

    # Step 5 — render the final card.
    return templates.get_template("ask/_final_card.html").render(
        summary=summary,
        sql=sql,
        chart_spec=chart_spec,
        table_html=table_html,
        chart_html=chart_html,
        row_count=row_count,
        original_question=original_question,
    )


def _build_plotly_chart_html(df: pd.DataFrame, chart_spec: ChartSpec) -> str:
    """Construct the Plotly chart HTML server-side (T-03-04-09 mitigation).

    RESEARCH Pitfall 9: per-column numeric coercion before plotting.
    ``include_plotlyjs=False`` because the bundle is loaded once via
    ``_extra_head_`` block in ``ask/index.html``.
    """
    import plotly.graph_objects as go  # imported lazily to spare other pages

    x = df[chart_spec.x_column]
    y = pd.to_numeric(df[chart_spec.y_column], errors="coerce")

    chart_type = chart_spec.chart_type
    if chart_type == "bar":
        fig = go.Figure(data=[go.Bar(x=x, y=y)])
    elif chart_type == "line":
        fig = go.Figure(data=[go.Scatter(x=x, y=y, mode="lines+markers")])
    elif chart_type == "scatter":
        fig = go.Figure(data=[go.Scatter(x=x, y=y, mode="markers")])
    else:  # "none" — should not reach here per the gate above, but safeguard
        return ""

    fig.update_layout(
        margin=dict(l=24, r=24, t=12, b=24),
        height=320,
        xaxis_title=chart_spec.x_column,
        yaxis_title=chart_spec.y_column,
    )
    return fig.to_html(include_plotlyjs=False, full_html=False)
