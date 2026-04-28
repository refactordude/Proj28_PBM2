"""Route-level tests for app_v2/routers/ask.py (Phase 6, ASK-V2-01..03,-06,-07).

D-19 mocking strategy: patch `app_v2.routers.ask.run_nl_query` at module
level (matches test_summary_routes.py idiom). Tests construct canned
NLResult variants and assert route status code, swap target, fragment
template name, and selected fragment context values. NEVER instantiate the
PydanticAI agent or hit a DB.

D-20: no threat-model tests here — Phase 1 tests/agent/test_nl_service.py
covers SAFE-02..06.
"""
from __future__ import annotations

import urllib.parse
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.agent.nl_agent import AgentRunFailure
from app.core.agent.nl_service import NLResult


def _post_form_pairs(client, url: str, pairs: list[tuple[str, str]]):
    """POST a URL with repeated-key form fields using the httpx 0.28-safe pattern.

    httpx 0.28 dropped list-of-tuples support on ``data=`` (raises TypeError).
    This helper mirrors the workaround documented in STATE.md 04-04 and used in
    ``tests/v2/test_browse_routes.py``: encode pairs manually with
    ``urllib.parse.urlencode`` (quote_via=quote preserves %20 spaces) and pass
    the body as ``content=`` with an explicit Content-Type header.
    """
    body = urllib.parse.urlencode(pairs, quote_via=urllib.parse.quote)
    return client.post(
        url,
        content=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def _stub_settings():
    return SimpleNamespace(
        app=SimpleNamespace(
            default_llm="ollama-local",
            agent=SimpleNamespace(
                allowed_tables=("ufs_data",),
                max_steps=5,
                timeout_s=30,
                row_cap=200,
            ),
        ),
        llms=[
            SimpleNamespace(name="ollama-local", type="ollama"),
            SimpleNamespace(name="openai-prod", type="openai"),
        ],
    )


@pytest.fixture()
def ask_client(mocker):
    """Yield a TestClient with run_nl_query + agent + deps mocked (D-19).

    Three patches applied at module level:
      - _get_agent     : returns a sentinel object (avoids real PydanticAI agent build)
      - _build_deps    : returns a sentinel object (avoids Pydantic AgentDeps validation
                         against a real DBAdapter; the deps value is never used because
                         run_nl_query is also mocked)
      - run_nl_query   : returns a canned NLResult (default kind="ok")

    This is the minimal set required so every route handler reaches the
    run_nl_query call without short-circuiting at agent/deps guards.
    """
    from app_v2.main import app

    # Sentinel returned by both helpers — route code only checks `is None`
    _sentinel = object()

    mocker.patch("app_v2.routers.ask._get_agent", return_value=_sentinel)
    mocker.patch("app_v2.routers.ask._build_deps", return_value=_sentinel)
    # Default mock: kind="ok"
    mocker.patch(
        "app_v2.routers.ask.run_nl_query",
        return_value=NLResult(
            kind="ok",
            sql="SELECT PLATFORM_ID FROM ufs_data LIMIT 200",
            df=pd.DataFrame({"PLATFORM_ID": ["A", "B"]}),
            summary="Two platforms.",
        ),
    )
    with TestClient(app) as client:
        # Inject AFTER lifespan ran — mirror of test_summary_routes.py isolated fixture
        app.state.settings = _stub_settings()
        app.state.db = SimpleNamespace(  # only used by _render_confirmation (list_parameters fallback)
            run_query=lambda *a, **k: pd.DataFrame(),
            _get_engine=None,
        )
        app.state.agent_registry = {}
        yield client


# --- GET /ask -------------------------------------------------------------

def test_get_ask_returns_200_with_html(ask_client, mocker):
    """ASK-V2-01: GET /ask renders the page."""
    # The default mock for _get_agent is fine; ask_page does NOT call run_nl_query
    mocker.patch(
        "app_v2.routers.ask.load_starter_prompts",
        return_value=[{"label": f"L{i}", "question": f"Q{i}"} for i in range(8)],
    )
    resp = ask_client.get("/ask")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    body = resp.text
    assert 'id="answer-zone"' in body
    assert 'id="ask-q"' in body
    assert 'hx-post="/ask/query"' in body
    assert "Try asking..." in body
    assert "LLM:" in body  # dropdown trigger label


def test_get_ask_dropdown_lists_all_configured_llms(ask_client, mocker):
    """ASK-V2-05: every settings.llms[] entry appears as a dropdown-item."""
    mocker.patch("app_v2.routers.ask.load_starter_prompts", return_value=[])
    resp = ask_client.get("/ask")
    assert resp.status_code == 200
    body = resp.text
    assert 'hx-post="/settings/llm"' in body
    # Both names appear in the dropdown
    assert "ollama-local" in body
    assert "openai-prod" in body


# --- POST /ask/query ------------------------------------------------------

def test_post_ask_query_ok_returns_answer_fragment(ask_client):
    """NLResult.kind='ok' -> ask/_answer.html with table + summary + SQL expander."""
    resp = ask_client.post("/ask/query", data={"question": "show all platforms"})
    assert resp.status_code == 200
    body = resp.text
    assert 'id="answer-zone"' in body
    assert "PLATFORM_ID" in body  # column header from the mocked DataFrame
    assert "Two platforms." in body  # summary
    assert "Generated SQL" in body
    assert "SELECT PLATFORM_ID FROM ufs_data" in body


def test_post_ask_query_clarification_returns_confirm_panel(ask_client, mocker):
    """NLResult.kind='clarification_needed' -> ask/_confirm_panel.html."""
    mocker.patch(
        "app_v2.routers.ask.run_nl_query",
        return_value=NLResult(
            kind="clarification_needed",
            message="Which params?",
            candidate_params=["UFS · WriteProt", "UFS · LUNCount"],
        ),
    )
    resp = ask_client.post("/ask/query", data={"question": "compare write prot"})
    assert resp.status_code == 200
    body = resp.text
    assert 'id="answer-zone"' in body
    assert "Which params?" in body
    assert 'name="original_question"' in body
    # original_question is propagated as the hidden input value (autoescaped)
    assert "compare write prot" in body
    assert "Run Query" in body


def test_post_ask_query_failure_step_cap_returns_abort_banner(ask_client, mocker):
    """NLResult.kind='failure', reason='step-cap' -> exact v1.0 copy."""
    mocker.patch(
        "app_v2.routers.ask.run_nl_query",
        return_value=NLResult(
            kind="failure",
            failure=AgentRunFailure(reason="step-cap", last_sql="SELECT 1", detail="UsageLimitExceeded"),
        ),
    )
    resp = ask_client.post("/ask/query", data={"question": "vague question"})
    assert resp.status_code == 200
    body = resp.text
    assert 'id="answer-zone"' in body
    assert "alert-danger" in body
    assert "reached the 5-step limit" in body
    assert "more specific parameters" in body


def test_post_ask_query_failure_timeout_returns_abort_banner(ask_client, mocker):
    """NLResult.kind='failure', reason='timeout' -> exact v1.0 copy."""
    mocker.patch(
        "app_v2.routers.ask.run_nl_query",
        return_value=NLResult(
            kind="failure",
            failure=AgentRunFailure(reason="timeout", last_sql="SELECT 1", detail="MaxExecutionTime"),
        ),
    )
    resp = ask_client.post("/ask/query", data={"question": "huge question"})
    assert resp.status_code == 200
    body = resp.text
    assert "timed out after 30 seconds" in body
    assert "more targeted question or switch to a faster model" in body


def test_post_ask_query_no_llm_configured_returns_abort_banner(ask_client, mocker):
    """When resolve_active_llm returns None, the route renders the abort banner."""
    mocker.patch("app_v2.routers.ask.resolve_active_llm", return_value=None)
    resp = ask_client.post("/ask/query", data={"question": "anything"})
    assert resp.status_code == 200
    body = resp.text
    assert "alert-danger" in body
    assert "No LLM backend configured" in body


# --- POST /ask/confirm ---------------------------------------------------

def test_post_ask_confirm_composes_loop_prevention_message(ask_client, mocker):
    """D-10: composed message includes the loop-prevention sentence verbatim.

    Uses _post_form_pairs (httpx 0.28 workaround from STATE.md 04-04) so that
    repeated-key form fields (confirmed_params appearing twice) are encoded
    correctly without triggering the httpx TypeError.
    """
    spy = mocker.patch(
        "app_v2.routers.ask.run_nl_query",
        return_value=NLResult(kind="ok", sql="SELECT 1", df=pd.DataFrame({"x": [1]}), summary="ok"),
    )
    resp = _post_form_pairs(
        ask_client,
        "/ask/confirm",
        [("original_question", "compare X"), ("confirmed_params", "UFS · LUNCount")],
    )
    assert resp.status_code == 200
    # First positional arg of run_nl_query is the composed question string
    composed = spy.call_args.args[0]
    assert "User-confirmed parameters: ['UFS · LUNCount']" in composed
    assert "Original question: compare X" in composed
    assert "Use ONLY the confirmed parameters above" in composed
    assert "do not return ClarificationNeeded again" in composed


def test_post_ask_confirm_with_empty_confirmed_params_still_runs(ask_client, mocker):
    """D-10: Run Query with 0 selected params is permitted (loop-prevention sentence handles it)."""
    spy = mocker.patch(
        "app_v2.routers.ask.run_nl_query",
        return_value=NLResult(kind="ok", sql="SELECT 1", df=pd.DataFrame({"x": [1]}), summary="ok"),
    )
    resp = ask_client.post("/ask/confirm", data={"original_question": "x"})
    assert resp.status_code == 200
    composed = spy.call_args.args[0]
    assert "User-confirmed parameters: []" in composed
    assert "If the list is empty" in composed


def test_post_ask_confirm_second_turn_clarification_is_suppressed(ask_client, mocker):
    """Pitfall 6: second-turn ClarificationNeeded -> abort banner, NOT another picker."""
    mocker.patch(
        "app_v2.routers.ask.run_nl_query",
        return_value=NLResult(
            kind="clarification_needed",
            message="still unclear",
            candidate_params=["X · Y"],
        ),
    )
    resp = ask_client.post(
        "/ask/confirm",
        data=[("original_question", "x"), ("confirmed_params", "A · B")],
    )
    assert resp.status_code == 200
    body = resp.text
    # Must be the abort banner, NOT the confirm panel
    assert "alert-danger" in body
    assert "Run Query" not in body  # no second confirm prompt
    assert "Something went wrong" in body or "clarification a second time" in body


def test_post_ask_confirm_failure_returns_abort_banner(ask_client, mocker):
    """Standard failure path on second turn = abort banner."""
    mocker.patch(
        "app_v2.routers.ask.run_nl_query",
        return_value=NLResult(
            kind="failure",
            failure=AgentRunFailure(reason="llm-error", last_sql="", detail="bad"),
        ),
    )
    resp = ask_client.post(
        "/ask/confirm",
        data=[("original_question", "x"), ("confirmed_params", "A · B")],
    )
    assert resp.status_code == 200
    assert "alert-danger" in resp.text


# --- Cookie-aware backend resolution -------------------------------------

def test_post_ask_query_honors_pbm2_llm_cookie(ask_client, mocker):
    """D-17: when pbm2_llm cookie is set to a valid llm name, the route resolves to that backend."""
    spy = mocker.patch("app_v2.routers.ask._get_agent", return_value=object())
    ask_client.cookies.set("pbm2_llm", "openai-prod")
    resp = ask_client.post("/ask/query", data={"question": "x"})
    assert resp.status_code == 200
    # _get_agent receives the cookie-resolved llm_name, not the default
    called_llm_name = spy.call_args.args[1]
    assert called_llm_name == "openai-prod"


def test_post_ask_query_falls_back_when_cookie_invalid(ask_client, mocker):
    """D-15: invalid cookie value silently falls back to settings.app.default_llm."""
    spy = mocker.patch("app_v2.routers.ask._get_agent", return_value=object())
    ask_client.cookies.set("pbm2_llm", "evil-tampered-value")
    resp = ask_client.post("/ask/query", data={"question": "x"})
    assert resp.status_code == 200
    called_llm_name = spy.call_args.args[1]
    assert called_llm_name == "ollama-local"  # the default
