"""Ask tab routes — NL agent UI under FastAPI/HTMX (Phase 6, ASK-V2-01..03, -06, -07).

Three sync `def` routes — never `async def` because `run_nl_query` calls
``agent.run_sync(...)`` internally and async-def routes would block the
uvicorn event loop (RESEARCH.md Pitfall 1; INFRA-05).

ALWAYS-200 contract (mirrors summary.py): every NL outcome (ok /
clarification_needed / failure) returns HTTP 200 with the matching fragment
template. The fragment swaps inline into ``#answer-zone`` via the caller's
HTMX hx-target; it NEVER escalates to the global ``#htmx-error-container``.
4xx/5xx are reserved for actual route errors (validation, server bugs).

Module-level imports (D-19): ``run_nl_query`` is imported at module top so
``mocker.patch("app_v2.routers.ask.run_nl_query")`` works at test time —
the same idiom as ``test_summary_routes.py``.

Cookie-aware backend resolution (D-15, D-17): both ``resolve_active_llm`` and
``resolve_active_backend_name`` are called with ``(settings, request)`` so
the ``pbm2_llm`` cookie set by ``POST /settings/llm`` (Plan 06-03) flows
through to NL agent + AI Summary as a single source of truth.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from app.adapters.llm.pydantic_model import build_pydantic_model
from app.core.agent.nl_agent import AgentDeps, build_agent
from app.core.agent.nl_service import NLResult, run_nl_query
from app.core.config import find_llm

from app_v2.services.cache import list_parameters
from app_v2.services.llm_resolver import (
    resolve_active_backend_name,
    resolve_active_llm,
)
from app_v2.services.starter_prompts import load_starter_prompts
from app_v2.templates import templates

_log = logging.getLogger(__name__)

router = APIRouter()


# --- Helpers ---------------------------------------------------------------

def _get_agent(request: Request, llm_name: str):
    """Return a cached PydanticAI Agent for ``llm_name`` from app.state.agent_registry.

    Lazy-builds on first request per backend. Matches the v1.0
    ``get_nl_agent`` `@st.cache_resource` pattern (RESEARCH.md Pattern 5).
    Returns None if ``llm_name`` is empty or not in settings.llms.
    """
    if not llm_name:
        return None
    registry = getattr(request.app.state, "agent_registry", None)
    if registry is None:
        return None
    if llm_name in registry:
        return registry[llm_name]
    settings = getattr(request.app.state, "settings", None)
    cfg = find_llm(settings, llm_name) if settings is not None else None
    if cfg is None:
        return None
    model = build_pydantic_model(cfg)
    agent = build_agent(model)
    registry[llm_name] = agent
    return agent


def _df_to_template_ctx(df) -> tuple[list[str], list[list]]:
    """Convert a pandas DataFrame into Jinja2-friendly columns + rows.

    Pitfall 2: Jinja2 cannot iterate a DataFrame as rows. Convert here so the
    template iterates plain Python lists.
    """
    if df is None:
        return [], []
    columns = [str(c) for c in df.columns]
    rows = [list(r) for r in df.itertuples(index=False, name=None)]
    return columns, rows


# --- Routes ----------------------------------------------------------------

@router.get("/ask", response_class=HTMLResponse)
def ask_page(request: Request):
    """Render the full Ask page (ASK-V2-01).

    Context fed to ``ask/index.html``:
        - active_tab="ask", page_title="Ask"
        - backend_name: "Ollama" or "OpenAI" (D-13 dropdown label)
        - llm_cfg: active LLMConfig (may be None — template degrades gracefully)
        - starter_prompts: list of {label, question} (ASK-V2-08; Plan 06-04 chip grid)
        - llms: settings.llms (drives the dropdown menu items, D-13)
    """
    settings = getattr(request.app.state, "settings", None)
    backend_name = resolve_active_backend_name(settings, request)
    llm_cfg = resolve_active_llm(settings, request)
    prompts = load_starter_prompts()
    llms = list(getattr(settings, "llms", []) or [])
    return templates.TemplateResponse(
        request,
        "ask/index.html",
        {
            "active_tab": "ask",
            "page_title": "Ask",
            "backend_name": backend_name,
            "llm_cfg": llm_cfg,
            "starter_prompts": prompts,
            "llms": llms,
        },
    )


@router.post("/ask/query", response_class=HTMLResponse)
def ask_query(
    request: Request,
    question: Annotated[str, Form()] = "",
):
    """First-turn NL endpoint (ASK-V2-01, ASK-V2-02, ASK-V2-06, ASK-V2-07).

    Returns one of three fragments — ALWAYS HTTP 200:
      - ask/_answer.html       (kind="ok"): table + summary + SQL expander
      - ask/_confirm_panel.html (kind="clarification_needed"): NL-05 picker + Run Query
      - ask/_abort_banner.html (kind="failure"): step-cap / timeout / llm-error
    """
    return _run_first_turn(request, question)


@router.post("/ask/confirm", response_class=HTMLResponse)
def ask_confirm(
    request: Request,
    original_question: Annotated[str, Form()] = "",
    confirmed_params: Annotated[list[str], Form()] = [],
):
    """Second-turn NL endpoint (ASK-V2-02, ASK-V2-06, ASK-V2-07; D-10).

    Composes the second-turn message verbatim per RESEARCH.md Pattern 2 and
    calls ``run_nl_query`` again. Returns ``_answer.html`` on success or
    ``_abort_banner.html`` on failure. If the agent returns
    ``ClarificationNeeded`` AGAIN (LLM ignored the loop-prevention
    instruction — Pitfall 6), the route treats it as a failure with
    reason="llm-error" so the user sees an explicit abort instead of an
    infinite confirmation loop.

    D-10: ``confirmed_params`` may be EMPTY — the loop-prevention message
    instructs the agent to use its best judgment from the original question
    in that case. Step-cap (5) and timeout (30s) are the ultimate floor.
    """
    composed = (
        f"User-confirmed parameters: {confirmed_params}\n\n"
        f"Original question: {original_question}\n\n"
        "Use ONLY the confirmed parameters above. "
        "If the list is empty, use your best judgment from the original question "
        "and do not return ClarificationNeeded again."
    )
    return _run_second_turn(request, composed, original_question)


# --- Internal turn handlers ------------------------------------------------

def _build_deps(request: Request, llm_cfg) -> AgentDeps | None:
    """Construct AgentDeps from app.state — None if any required piece is missing."""
    settings = getattr(request.app.state, "settings", None)
    db = getattr(request.app.state, "db", None)
    if settings is None or db is None or llm_cfg is None:
        return None
    agent_cfg = getattr(getattr(settings, "app", None), "agent", None)
    if agent_cfg is None:
        return None
    active_llm_type = "openai" if getattr(llm_cfg, "type", "") == "openai" else "ollama"
    try:
        return AgentDeps(db=db, agent_cfg=agent_cfg, active_llm_type=active_llm_type)
    except Exception:  # noqa: BLE001 — defensive: AgentDeps validation never crashes the route
        return None


def _render_unconfigured(request: Request) -> HTMLResponse:
    """No LLM configured — render the abort banner with reason='unconfigured'.

    WR-01 fix: the dedicated ``unconfigured`` template branch renders a single
    actionable message ("No LLM backend configured. Open Settings ...") instead
    of the generic catch-all ("Something went wrong. (...) Try rephrasing your
    question."), which awkwardly told users to rephrase a question that has
    nothing to do with the underlying configuration problem.
    """
    return templates.TemplateResponse(
        request,
        "ask/_abort_banner.html",
        {
            "reason": "unconfigured",
            "last_sql": "",
            "detail": "",
        },
        status_code=200,
    )


def _render_failure_kind(request: Request, nl_result: NLResult) -> HTMLResponse:
    """Render ask/_abort_banner.html from an NLResult.kind=='failure' result."""
    failure = nl_result.failure
    return templates.TemplateResponse(
        request,
        "ask/_abort_banner.html",
        {
            "reason": getattr(failure, "reason", "llm-error"),
            "last_sql": getattr(failure, "last_sql", ""),
            "detail": getattr(failure, "detail", ""),
        },
        status_code=200,
    )


def _render_ok(request: Request, nl_result: NLResult) -> HTMLResponse:
    """Render ask/_answer.html from an NLResult.kind=='ok' result."""
    columns, rows = _df_to_template_ctx(nl_result.df)
    return templates.TemplateResponse(
        request,
        "ask/_answer.html",
        {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "summary": nl_result.summary,
            "sql": nl_result.sql,
        },
        status_code=200,
    )


def _render_confirmation(request: Request, nl_result: NLResult, original_question: str) -> HTMLResponse:
    """Render ask/_confirm_panel.html — NL-05 (D-07).

    Builds the merged param catalog (full DB catalog ∪ agent's candidates)
    so the user can both keep the proposals and add more. Falls back to
    candidates-only when the DB is unavailable (graceful degradation —
    matches v1.0 behavior at app/pages/ask.py:336-339).
    """
    db = getattr(request.app.state, "db", None)
    candidates = list(nl_result.candidate_params)
    full_catalog: list[str] = []
    if db is not None:
        try:
            rows = list_parameters(db, db_name="")
            full_catalog = [
                f"{r['InfoCategory']} · {r['Item']}"  # Phase 4 PARAM_LABEL_SEP=' · ' (UTF-8 bytes b' \xc2\xb7 ')
                for r in rows
            ]
        except Exception:  # noqa: BLE001 — graceful degradation
            full_catalog = []
    all_params = sorted(set(full_catalog) | set(candidates))
    return templates.TemplateResponse(
        request,
        "ask/_confirm_panel.html",
        {
            "message": nl_result.message,
            "candidate_params": candidates,
            "all_params": all_params,
            "original_question": original_question,
        },
        status_code=200,
    )


def _run_first_turn(request: Request, question: str) -> HTMLResponse:
    """Common first-turn dispatch — invoked by POST /ask/query."""
    settings = getattr(request.app.state, "settings", None)
    llm_cfg = resolve_active_llm(settings, request)
    if llm_cfg is None:
        return _render_unconfigured(request)
    agent = _get_agent(request, getattr(llm_cfg, "name", ""))
    deps = _build_deps(request, llm_cfg)
    if agent is None or deps is None:
        return _render_unconfigured(request)
    nl_result: NLResult = run_nl_query(question.strip(), agent, deps)
    if nl_result.kind == "ok":
        return _render_ok(request, nl_result)
    if nl_result.kind == "clarification_needed":
        return _render_confirmation(request, nl_result, original_question=question)
    # kind == "failure"
    return _render_failure_kind(request, nl_result)


def _run_second_turn(request: Request, composed: str, original_question: str) -> HTMLResponse:
    """Common second-turn dispatch — invoked by POST /ask/confirm.

    Pitfall 6: if the agent ignores the loop-prevention instruction and
    returns ``ClarificationNeeded`` again, render the abort banner instead
    of the confirmation panel. The user is NEVER shown a second
    confirmation prompt — they must edit the textarea and re-Ask.
    """
    settings = getattr(request.app.state, "settings", None)
    llm_cfg = resolve_active_llm(settings, request)
    if llm_cfg is None:
        return _render_unconfigured(request)
    agent = _get_agent(request, getattr(llm_cfg, "name", ""))
    deps = _build_deps(request, llm_cfg)
    if agent is None or deps is None:
        return _render_unconfigured(request)
    nl_result: NLResult = run_nl_query(composed, agent, deps)
    if nl_result.kind == "ok":
        return _render_ok(request, nl_result)
    if nl_result.kind == "clarification_needed":
        # Pitfall 6 — treat as failure (loop prevention). Synthesize a failure
        # NLResult for _render_failure_kind.
        from app.core.agent.nl_agent import AgentRunFailure  # local import — no top-level couple
        synth = NLResult(
            kind="failure",
            failure=AgentRunFailure(
                reason="llm-error",
                last_sql="",
                detail="Agent requested clarification a second time; aborting to prevent loop.",
            ),
        )
        _log.warning("Second-turn ClarificationNeeded suppressed (D-10 / Pitfall 6)")
        return _render_failure_kind(request, synth)
    # kind == "failure"
    return _render_failure_kind(request, nl_result)
