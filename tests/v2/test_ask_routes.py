"""Phase 3 D-CHAT-08 router-level tests for the rewritten Ask surface.

Covers the 4 new routes (GET /ask, POST /ask/chat, GET /ask/stream/{turn_id},
POST /ask/cancel/{turn_id}) plus the deletion of the legacy Phase 6 routes
(POST /ask/query, POST /ask/confirm) per D-CHAT-09.

Mocking strategy:
  - ``build_chat_agent`` is patched at module level to return a fake agent whose
    ``run_stream_events`` is a controlled async generator (RESEARCH Gap 11).
  - ``request.app.state.db`` is set to a small ``_FakeDB(DBAdapter)`` subclass
    (Pydantic v2 strict-instance check on ChatAgentDeps.db requires a real
    DBAdapter — a MagicMock will not pass the validator).
  - ``request.app.state.settings.app.agent`` is a real ``AgentConfig`` instance
    (Pydantic v2 model_type validation on ``ChatAgentDeps.agent_cfg``).
  - No real LLM calls are made in any test in this file.

T-03-05-01 (test pollution): module-level ``_TURNS`` / ``_SESSIONS`` registries
are reset before AND after every test via the ``_reset_chat_registries``
autouse fixture.
"""
from __future__ import annotations

import re
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.adapters.db.base import DBAdapter
from app.core.agent.chat_agent import ChartSpec, PresentResult
from app.core.agent.chat_session import _SESSIONS, _TURNS
from app.core.agent.config import AgentConfig


class _FakeDB(DBAdapter):
    """Minimal in-memory DBAdapter subclass for router tests.

    Subclasses the abstract base so it passes Pydantic v2's
    ``isinstance(value, DBAdapter)`` check on ``ChatAgentDeps.db``.
    The ``run_query`` impl returns whatever DataFrame ``_df`` was set to
    (default empty); tests mutate ``_df`` to drive _hydrate_final_card.
    """

    def __init__(self, df: pd.DataFrame | None = None) -> None:
        # Skip the parent __init__ — we don't need a real DatabaseConfig.
        self._df = df if df is not None else pd.DataFrame()
        # Sentinel so router's getattr(self, '_get_engine', None) returns None
        # and falls back to the simpler run_query path.
        self._get_engine = None

    def test_connection(self) -> tuple[bool, str]:
        return True, "ok"

    def list_tables(self) -> list[str]:
        return ["ufs_data"]

    def get_schema(self, tables=None):
        return {"ufs_data": []}

    def run_query(self, sql: str) -> pd.DataFrame:
        return self._df.copy()


# --- Fixtures -------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_chat_registries():
    """T-03-05-01: clear the module-level chat registries before AND after every test."""
    _TURNS.clear()
    _SESSIONS.clear()
    yield
    _TURNS.clear()
    _SESSIONS.clear()


def _stub_settings():
    """Minimal settings stub honoring resolve_active_llm + resolve_active_backend_name.

    ``app.agent`` is a real ``AgentConfig`` instance so ChatAgentDeps's
    Pydantic v2 ``agent_cfg`` validator accepts it (model_type check).
    """
    return SimpleNamespace(
        app=SimpleNamespace(
            default_llm="ollama-local",
            agent=AgentConfig(
                allowed_tables=["ufs_data"],
                max_steps=5,
                chat_max_steps=12,
                timeout_s=30,
                row_cap=200,
            ),
        ),
        llms=[
            SimpleNamespace(name="ollama-local", type="ollama"),
            SimpleNamespace(name="openai-prod", type="openai"),
        ],
    )


@pytest.fixture
def client():
    """Plain TestClient with stub settings + fake DBAdapter injected after lifespan."""
    from app_v2.main import app

    with TestClient(app) as c:
        app.state.settings = _stub_settings()
        app.state.db = _FakeDB()
        yield c


# --- GET /ask -------------------------------------------------------------


def test_ask_page_renders_chat_shell_with_no_starter_chips(client):
    """D-CHAT-08 chat shell + D-CHAT-10 (no starter chips) + D-CHAT-11 (LLM dropdown)."""
    r = client.get("/ask")
    assert r.status_code == 200
    body = r.text
    # D-CHAT-10: starter chips include is gone from the shell.
    assert "_starter_chips.html" not in body
    # D-CHAT-08: chat shell IDs present.
    assert 'id="chat-transcript"' in body
    assert 'id="input-zone"' in body
    # D-CHAT-11: LLM dropdown trigger preserved.
    assert "LLM:" in body
    # Phase 3: vendored Plotly + htmx-ext-sse loaded only here (T-03-04-07).
    assert "vendor/plotly/plotly.min.js" in body
    assert "vendor/htmx/htmx-ext-sse.js" in body


def test_ask_page_sets_pbm2_session_cookie_on_first_visit(client):
    """RESEARCH Gap 6 / Pitfall 8 — pbm2_session cookie set on first GET /ask.

    Inspect the response Set-Cookie header rather than the TestClient cookie
    jar (the jar may not snapshot in time for the assertion in some
    httpx versions; the response header is the authoritative signal).
    """
    r = client.get("/ask")
    assert r.status_code == 200
    set_cookie_headers = r.headers.get("set-cookie", "")
    assert "pbm2_session=" in set_cookie_headers, (
        f"pbm2_session not in Set-Cookie header: {set_cookie_headers!r}"
    )
    # And the TestClient cookie jar should now carry it for subsequent requests.
    # (Cookies dict updates after iter_response; just check it was issued.)
    assert "HttpOnly" in set_cookie_headers
    assert "SameSite=lax" in set_cookie_headers.lower() or "samesite=lax" in set_cookie_headers.lower()


# --- POST /ask/chat -------------------------------------------------------


def test_post_ask_chat_returns_user_message_fragment_with_sse_consumer(client):
    """D-CHAT-08: POST /ask/chat returns the user-message + SSE consumer + OOB Stop swap."""
    r = client.post("/ask/chat", data={"question": "compare X across SM8850 and SM8650"})
    assert r.status_code == 200
    body = r.text
    # turn_id should be visible in sse-connect URL (uuid4().hex = 32 hex chars)
    assert re.search(r'sse-connect="/ask/stream/[0-9a-f]{32}"', body)
    # OOB swap to flip #input-zone to Stop state
    assert 'hx-swap-oob="true"' in body
    assert 'btn-stop' in body
    # Original question is rendered (autoescaped)
    assert "compare X across SM8850 and SM8650" in body


def test_post_ask_chat_with_empty_question_still_creates_turn(client):
    """The agent will produce an error event downstream; the route does not pre-validate."""
    r = client.post("/ask/chat", data={"question": "  "})
    assert r.status_code == 200
    # turn_id is still created even on whitespace-only question
    assert re.search(r'sse-connect="/ask/stream/[0-9a-f]{32}"', r.text)


# --- POST /ask/cancel/{turn_id} -------------------------------------------


def test_post_ask_cancel_with_foreign_session_returns_403(client):
    """T-03-04-02: cancel must be authenticated to the originating session."""
    r = client.post("/ask/chat", data={"question": "q"})
    turn_id = re.search(r'sse-connect="/ask/stream/([0-9a-f]+)"', r.text).group(1)
    # Session B (separate TestClient = separate cookie jar) tries to cancel.
    from app_v2.main import app
    other = TestClient(app)
    other.cookies.set("pbm2_session", "b" * 32)  # set a different, valid-looking session id
    cancel = other.post(f"/ask/cancel/{turn_id}")
    assert cancel.status_code == 403


def test_post_ask_cancel_with_unknown_turn_returns_404(client):
    """Unregistered turn_id (well-formed but never created) returns 404."""
    r = client.post("/ask/cancel/" + "0" * 32)
    assert r.status_code == 404


def test_post_ask_cancel_with_owning_session_returns_204(client):
    """Owner session cancels its own turn — returns 204 (no body)."""
    r = client.post("/ask/chat", data={"question": "q"})
    turn_id = re.search(r'sse-connect="/ask/stream/([0-9a-f]+)"', r.text).group(1)
    cancel = client.post(f"/ask/cancel/{turn_id}")
    assert cancel.status_code == 204


# --- GET /ask/stream/{turn_id} -------------------------------------------


def test_get_ask_stream_with_foreign_session_returns_403(client):
    """T-03-04-01: stream must be authenticated to the originating session."""
    r = client.post("/ask/chat", data={"question": "q"})
    turn_id = re.search(r'sse-connect="/ask/stream/([0-9a-f]+)"', r.text).group(1)
    from app_v2.main import app
    other = TestClient(app)
    other.cookies.set("pbm2_session", "b" * 32)
    stream = other.get(f"/ask/stream/{turn_id}")
    assert stream.status_code == 403


def test_get_ask_stream_with_unknown_turn_returns_404(client):
    """Unregistered turn_id returns 404 from the SSE endpoint as well."""
    stream = client.get("/ask/stream/" + "0" * 32)
    assert stream.status_code == 404


# --- Legacy Phase 6 route deletion (D-CHAT-09) ----------------------------


# --- Side-by-side comparison pivot ----------------------------------------


def test_maybe_pivot_eav_for_comparison_with_two_platforms_pivots_to_wide():
    """When the agent returns long-form EAV data spanning 2+ platforms, the
    router pivots to wide form so each PLATFORM_ID becomes a column and each
    "InfoCategory · Item" becomes a single row.
    """
    from app_v2.routers.ask import _maybe_pivot_eav_for_comparison

    df_long = pd.DataFrame(
        [
            ("SM8550_rev1", "VendorInfo", "ManufacturerName", "Samsung"),
            ("SM8550_rev1", "GeometryDescriptor", "RawDeviceCapacity", "256GB"),
            ("SM8650_v1", "VendorInfo", "ManufacturerName", "Micron"),
            ("SM8650_v1", "GeometryDescriptor", "RawDeviceCapacity", "1024GB"),
        ],
        columns=["PLATFORM_ID", "InfoCategory", "Item", "Result"],
    )

    df_wide, index_col = _maybe_pivot_eav_for_comparison(df_long)
    assert index_col == "Parameter"
    assert "Parameter" in df_wide.columns
    assert "SM8550_rev1" in df_wide.columns
    assert "SM8650_v1" in df_wide.columns
    # Two parameters → two rows after pivot.
    assert len(df_wide) == 2
    # Spot-check a value lands in the right cell.
    cap_row = df_wide[df_wide["Parameter"] == "GeometryDescriptor · RawDeviceCapacity"]
    assert cap_row["SM8550_rev1"].iloc[0] == "256GB"
    assert cap_row["SM8650_v1"].iloc[0] == "1024GB"


def test_maybe_pivot_eav_for_comparison_replaces_nan_with_empty_string_for_em_dash():
    """When one platform has a parameter the other doesn't, the pivot leaves
    NaN in the missing cell. The helper replaces NaN with empty string so
    the Browse macro renders ``"" | string | e`` → empty <td>, and the
    ``:empty::after { content: "—" }`` CSS rule fills with an em-dash.
    Without this, NaN would render as literal "nan" because
    ``float('nan') is not None`` is True.
    """
    from app_v2.routers.ask import _maybe_pivot_eav_for_comparison

    df_long = pd.DataFrame(
        [
            ("SM8550_rev1", "VendorInfo", "ManufacturerName", "Samsung"),
            ("SM8650_v1", "GeometryDescriptor", "RawDeviceCapacity", "1024GB"),
            # No GeometryDescriptor on SM8550, no VendorInfo on SM8650 →
            # both rows have NaN in one column post-pivot.
        ],
        columns=["PLATFORM_ID", "InfoCategory", "Item", "Result"],
    )

    df_wide, _ = _maybe_pivot_eav_for_comparison(df_long)
    # Find the cell that should be missing.
    capacity_row = df_wide[
        df_wide["Parameter"] == "GeometryDescriptor · RawDeviceCapacity"
    ]
    missing_cell = capacity_row["SM8550_rev1"].iloc[0]
    assert missing_cell == "", (
        f"missing pivot cell should be empty string (so the macro renders "
        f"empty <td> and CSS injects the em-dash); got {missing_cell!r}"
    )


def test_maybe_pivot_eav_for_comparison_with_one_platform_leaves_long_form():
    """Single-platform results pass through unchanged — already readable as
    a 4-column listing, no point pivoting to a single-column wide table.
    """
    from app_v2.routers.ask import _maybe_pivot_eav_for_comparison

    df_long = pd.DataFrame(
        [
            ("SM8550_rev1", "VendorInfo", "ManufacturerName", "Samsung"),
            ("SM8550_rev1", "GeometryDescriptor", "RawDeviceCapacity", "256GB"),
        ],
        columns=["PLATFORM_ID", "InfoCategory", "Item", "Result"],
    )

    df_render, index_col = _maybe_pivot_eav_for_comparison(df_long)
    assert index_col == "PLATFORM_ID"
    assert list(df_render.columns) == [
        "PLATFORM_ID",
        "InfoCategory",
        "Item",
        "Result",
    ], "single-platform result should not be pivoted"


def test_maybe_pivot_eav_for_comparison_non_eav_shape_passes_through():
    """Result without the 4 EAV columns (e.g., the agent ran an aggregate
    query like SELECT COUNT(*)) should render as-is without any pivot.
    """
    from app_v2.routers.ask import _maybe_pivot_eav_for_comparison

    df = pd.DataFrame({"cnt": [42]})
    df_render, index_col = _maybe_pivot_eav_for_comparison(df)
    assert index_col == "cnt"
    assert list(df_render.columns) == ["cnt"]


def test_post_ask_query_route_no_longer_exists(client):
    """D-CHAT-09: legacy one-shot /ask/query route deleted in plan 03-04."""
    r = client.post("/ask/query", data={"question": "q"})
    assert r.status_code in (404, 405)


def test_post_ask_confirm_route_no_longer_exists(client):
    """D-CHAT-09: legacy NL-05 /ask/confirm route deleted in plan 03-04."""
    r = client.post("/ask/confirm", data={"prompt_id": "x"})
    assert r.status_code in (404, 405)


# --- SSE event ordering + WARNING-3 final-card hydration ------------------


@patch("app_v2.routers.ask.build_pydantic_model", return_value=MagicMock(name="ai_model"))
@patch("app_v2.routers.ask.build_chat_agent")
def test_get_ask_stream_final_frame_contains_table_rows_when_sql_returns_rows(
    mock_build_agent, mock_build_model, client
):
    """WARNING-3 contract: when the agent emits PresentResult with sql that returns
    rows, the final SSE frame's rendered fragment contains a non-empty <tbody>.

    Verifies router-side _hydrate_final_card runs PresentResult.sql against
    app.state.db and renders _final_card.html with table_html populated.
    """
    from pydantic_ai.run import AgentRunResultEvent

    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})

    class _FakeRunResult:
        """Minimal AgentRunResult-like — chat_loop only reads .output + .new_messages()."""

        def __init__(self, output):
            self.output = output

        def new_messages(self):
            return []

    async def fake_stream(*a, **kw):
        # Yield only the terminal AgentRunResultEvent carrying a PresentResult.
        yield AgentRunResultEvent(
            result=_FakeRunResult(
                PresentResult(summary="ok", sql="SELECT * FROM ufs_data LIMIT 2")
            )
        )

    mock_agent = MagicMock()
    mock_agent.run_stream_events = fake_stream
    mock_build_agent.return_value = mock_agent

    # _FakeDB returns the given DataFrame from run_query so _hydrate_final_card
    # renders a populated <tbody>. Use a real DBAdapter subclass so the
    # ChatAgentDeps Pydantic v2 isinstance(DBAdapter) check passes.
    from app_v2.main import app as fastapi_app
    original_db = getattr(fastapi_app.state, "db", None)
    fastapi_app.state.db = _FakeDB(df)
    try:
        r = client.post("/ask/chat", data={"question": "q"})
        turn_id = re.search(r'sse-connect="/ask/stream/([0-9a-f]+)"', r.text).group(1)
        body = ""
        with client.stream("GET", f"/ask/stream/{turn_id}") as resp:
            assert resp.status_code == 200
            for line in resp.iter_lines():
                body += line + "\n"
                # The fake agent stream ends after one event, so once we see
                # </tbody> the rest of the response is just the SSE
                # close-of-stream sentinels — break out cleanly.
                if "</tbody>" in body and "event: final" in body:
                    break
        assert "event: final" in body, f"final SSE event not seen:\n{body[:500]}"
        assert "<tbody>" in body, f"final SSE frame missing <tbody>:\n{body[:2000]}"
        assert "</tbody>" in body, (
            f"final SSE frame missing </tbody>:\n{body[:2000]}"
        )
    finally:
        fastapi_app.state.db = original_db


@patch("app_v2.routers.ask.build_pydantic_model", return_value=MagicMock(name="ai_model"))
@patch("app_v2.routers.ask.build_chat_agent")
def test_get_ask_stream_emits_terminal_event_with_mocked_agent(
    mock_build_agent, mock_build_model, client
):
    """D-CHAT-08 + D-CHAT-04/05: SSE stream produces a terminal final or error event."""
    from pydantic_ai.run import AgentRunResultEvent

    class _FakeRunResult:
        def __init__(self):
            self.output = None  # forces 'agent-no-final-result' error path

        def new_messages(self):
            return []

    async def fake_stream(*a, **kw):
        yield AgentRunResultEvent(result=_FakeRunResult())

    mock_agent = MagicMock()
    mock_agent.run_stream_events = fake_stream
    mock_build_agent.return_value = mock_agent

    r = client.post("/ask/chat", data={"question": "q"})
    turn_id = re.search(r'sse-connect="/ask/stream/([0-9a-f]+)"', r.text).group(1)

    events = []
    with client.stream("GET", f"/ask/stream/{turn_id}") as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())
            if events and events[-1] in ("final", "error"):
                break

    assert events, "no SSE events received"
    assert events[-1] in ("final", "error")
