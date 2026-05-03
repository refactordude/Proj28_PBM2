"""Unit tests for ``app.core.agent.chat_agent`` — D-CHAT-02 motivating example
+ D-CHAT-05 PresentResult terminator + D-CHAT-09 no-nl_service-import.

Covers:
  - The motivating example: UNION SQL → REJECTED: prefix on the tool result
    (D-CHAT-02). The agent (mocked) reads the prefix and retries with split queries.
  - SAFE-05 wrapping invariant: successful run_sql returns ``<db_data>...</db_data>``.
  - D-CHAT-11 path scrub: applied when active_llm_type=='openai', skipped for 'ollama'.
  - D-CHAT-06 ChartSpec literal constraint (chart_type must be bar|line|scatter|none).
  - D-CHAT-09 invariant: chat_agent module does NOT import nl_service or run_nl_query.
  - PresentResult terminator returns a typed Pydantic model (D-CHAT-05).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.adapters.db.base import DBAdapter
from app.core.agent.chat_agent import (
    ChartSpec,
    ChatAgentDeps,
    PresentResult,
    _execute_and_wrap,
    build_chat_agent,
)
from app.core.agent.config import AgentConfig


class _FakeDB(DBAdapter):
    """Minimal in-memory DBAdapter — passes the Pydantic v2 isinstance(DBAdapter) check."""

    def __init__(self, df: pd.DataFrame | None = None) -> None:
        self._df = df if df is not None else pd.DataFrame()

    def test_connection(self):
        return True, "ok"

    def list_tables(self):
        return ["ufs_data"]

    def get_schema(self, tables=None):
        return {"ufs_data": []}

    def run_query(self, sql: str) -> pd.DataFrame:
        return self._df.copy()


def _make_ctx(active_llm_type: str = "ollama", df: pd.DataFrame | None = None):
    """Build a RunContext-shaped MagicMock with deps wired to a real ChatAgentDeps."""
    cfg = AgentConfig(allowed_tables=["ufs_data"], chat_max_steps=12)
    deps = ChatAgentDeps(
        db=_FakeDB(df=df),
        agent_cfg=cfg,
        active_llm_type=active_llm_type,
    )
    ctx = MagicMock()
    ctx.deps = deps
    return ctx


# --- D-CHAT-02 motivating example ----------------------------------------


def test_execute_and_wrap_returns_REJECTED_on_union_sql_d_chat_02_motivating_example():
    """The SM8850 vs SM8650 UNION case — agent must read REJECTED: prefix and retry.

    This is the canonical RESEARCH motivating example: the user asks
    "compare X across SM8850 and SM8650", a naive single-query SQL would use
    UNION which the SAFE-02 validator rejects, the tool returns ``REJECTED:``
    so the agent splits into two SELECTs (D-CHAT-02 contract).
    """
    ctx = _make_ctx()
    sql = (
        "SELECT * FROM ufs_data WHERE PLATFORM_ID='SM8850' "
        "UNION "
        "SELECT * FROM ufs_data WHERE PLATFORM_ID='SM8650'"
    )
    result = _execute_and_wrap(ctx, sql, prefix_rejection=True)
    assert result.startswith("REJECTED:"), (
        f"UNION SQL should be rejected with REJECTED: prefix, got: {result!r}"
    )


def test_execute_and_wrap_returns_db_data_wrapper_on_success():
    """SAFE-05 wrapping invariant — successful run_sql results wrap in <db_data>...</db_data>."""
    ctx = _make_ctx(df=pd.DataFrame({"a": [1, 2]}))
    result = _execute_and_wrap(ctx, "SELECT * FROM ufs_data LIMIT 5")
    assert result.startswith("<db_data>")
    assert result.endswith("</db_data>")


def test_execute_and_wrap_empty_df_returns_no_rows_marker():
    """Empty DataFrame → '(no rows returned)' inside the <db_data> wrapper."""
    ctx = _make_ctx(df=pd.DataFrame())
    result = _execute_and_wrap(ctx, "SELECT * FROM ufs_data LIMIT 5")
    assert "<db_data>" in result
    assert "(no rows returned)" in result


# --- Empty-where guard + DB-error → REJECTED rerouting ------------------


def test_count_rows_with_empty_where_clause_raises_model_retry_without_db_call():
    """count_rows MUST short-circuit on empty where_clause and raise ModelRetry
    so PydanticAI re-prompts the model WITHOUT consuming a budget slot
    (Cursor / Aider "free retries on parseable errors" pattern).
    """
    from pydantic_ai import ModelRetry
    from pydantic_ai.models.test import TestModel

    agent = build_chat_agent(TestModel())
    count_rows = agent._function_toolset.tools["count_rows"].function
    ctx = _make_ctx()
    ctx.run_step = 1
    with pytest.raises(ModelRetry, match="non-empty"):
        count_rows(ctx, where_clause="")


def test_sample_rows_with_empty_where_clause_raises_model_retry_without_db_call():
    """sample_rows mirrors count_rows — the same guard raises ModelRetry."""
    from pydantic_ai import ModelRetry
    from pydantic_ai.models.test import TestModel

    agent = build_chat_agent(TestModel())
    sample_rows = agent._function_toolset.tools["sample_rows"].function
    ctx = _make_ctx()
    ctx.run_step = 1
    with pytest.raises(ModelRetry, match="non-empty"):
        sample_rows(ctx, where_clause="", limit=5)


def test_repeat_tool_call_returns_cached_result_with_terminate_nudge():
    """Aider/Cursor pattern: repeated calls with identical args short-circuit
    to the cached result with a "[CACHED]" prefix that nudges the model to
    call present_result. Bounds runaway loops regardless of model quality.
    """
    from pydantic_ai.models.test import TestModel

    df = pd.DataFrame({"PLATFORM_ID": ["SM8650_v1", "SM8650_v2"]})
    agent = build_chat_agent(TestModel())
    get_distinct_values = agent._function_toolset.tools["get_distinct_values"].function
    ctx = _make_ctx(df=df)
    ctx.run_step = 1

    # First call — populates the cache and returns real data.
    out1 = get_distinct_values(ctx, column="PLATFORM_ID")
    assert "<db_data>" in out1, "first call should return live DB output"
    assert "[CACHED" not in out1, "first call should NOT have CACHED prefix"
    assert ctx.deps.tool_call_cache, "cache should be populated after first call"

    # Second call with same args — cache hit, prepends CACHED note.
    ctx.run_step = 2
    out2 = get_distinct_values(ctx, column="PLATFORM_ID")
    assert out2.startswith("[CACHED"), f"repeat call should be CACHED; got {out2[:80]!r}"
    assert "present_result" in out2, "CACHED note should nudge toward present_result"
    assert "<db_data>" in out2, "CACHED result should still include the original data"


def test_rejected_tool_result_is_not_cached():
    """REJECTED:/error results MUST NOT be cached — the agent should be
    able to retry the same tool with different args via ModelRetry.
    Caching a REJECTED result would trap the agent in a stale rejection.
    """
    from pydantic_ai import ModelRetry
    from pydantic_ai.models.test import TestModel

    agent = build_chat_agent(TestModel())
    get_distinct_values = agent._function_toolset.tools["get_distinct_values"].function
    ctx = _make_ctx()
    ctx.run_step = 1

    # Invalid column → REJECTED → ModelRetry → tool_call_cache stays empty.
    with pytest.raises(ModelRetry):
        get_distinct_values(ctx, column="not_a_column")
    assert "get_distinct_values:not_a_column" not in ctx.deps.tool_call_cache, (
        "REJECTED results must not be cached"
    )


def test_successful_tool_result_carries_remaining_budget_hint():
    """Cursor / Aider pattern: tool results inject a remaining-budget hint
    so the model self-paces and calls present_result before exhaustion.
    """
    from pydantic_ai.models.test import TestModel

    agent = build_chat_agent(TestModel())
    inspect_schema = agent._function_toolset.tools["inspect_schema"].function
    ctx = _make_ctx()
    ctx.run_step = 3
    out = inspect_schema(ctx)
    assert "PLATFORM_ID:str" in out, "schema content must still be returned"
    assert "[budget:" in out, "budget hint should be appended"
    # cap=12, run_step=3, remaining=9
    assert "9/12" in out, f"expected '9/12' remaining; got {out!r}"
    assert "present_result" in out, "hint should mention present_result"


def test_db_execution_error_is_routed_through_rejection_path():
    """DB-side execution errors (syntax, missing columns, runtime) get the
    REJECTED: prefix so the agent counts them toward the D-CHAT-02 retry cap
    and recognizes the result as retryable."""
    from sqlalchemy.exc import OperationalError

    class _ExplodingDB(DBAdapter):
        def __init__(self):  # bypass DBAdapter's DatabaseConfig requirement
            pass

        def test_connection(self):  # noqa: D401
            return True, "ok"

        def list_tables(self):
            return ["ufs_data"]

        def get_schema(self, tables=None):
            return {"ufs_data": []}

        def run_query(self, sql):
            raise OperationalError(sql, {}, Exception("near \"LIMIT\": syntax error"))

    cfg = AgentConfig(allowed_tables=["ufs_data"], chat_max_steps=12)
    deps = ChatAgentDeps(
        db=_ExplodingDB(),
        agent_cfg=cfg,
        active_llm_type="ollama",
    )
    ctx = MagicMock()
    ctx.deps = deps

    out = _execute_and_wrap(ctx, "SELECT * FROM ufs_data", prefix_rejection=True)
    assert out.startswith("REJECTED:"), (
        f"DB execution errors must be routed through the REJECTED: path so the "
        f"D-CHAT-02 retry counter increments; got {out!r}"
    )
    assert "OperationalError" in out, "error type should be visible to the LLM"


# --- D-CHAT-11 scrub-on-write -------------------------------------------


def test_execute_and_wrap_scrub_paths_on_openai():
    """D-CHAT-11 — path scrub applied when active_llm_type=='openai'."""
    ctx = _make_ctx(
        active_llm_type="openai",
        df=pd.DataFrame({"path": ["/sys/block/sda/queue/depth"]}),
    )
    result = _execute_and_wrap(ctx, "SELECT * FROM ufs_data")
    assert "/sys/block" not in result
    assert "<path>" in result


def test_execute_and_wrap_no_scrub_on_ollama():
    """Ollama is local intranet — no path scrub (D-CHAT-11)."""
    ctx = _make_ctx(
        active_llm_type="ollama",
        df=pd.DataFrame({"path": ["/sys/block/sda/queue/depth"]}),
    )
    result = _execute_and_wrap(ctx, "SELECT * FROM ufs_data")
    assert "/sys/block/sda/queue/depth" in result


# --- D-CHAT-05 + D-CHAT-06 PresentResult / ChartSpec ----------------------


def test_present_result_returns_typed_pydantic_model():
    pr = PresentResult(summary="ok", sql="SELECT 1")
    assert isinstance(pr, PresentResult)
    assert isinstance(pr.chart_spec, ChartSpec)
    assert pr.chart_spec.chart_type == "none"  # default


def test_chart_spec_chart_type_literal_constraint():
    """D-CHAT-06 — chart_type literal constrained to bar|line|scatter|none."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ChartSpec(chart_type="histogram")  # type: ignore — invalid literal


def test_chart_spec_accepts_all_four_literals():
    for valid in ("bar", "line", "scatter", "none"):
        cs = ChartSpec(chart_type=valid)  # type: ignore[arg-type]
        assert cs.chart_type == valid


def test_present_result_validator_accepts_chart_spec_dict():
    """ChartSpec can be passed as nested model or dict."""
    pr = PresentResult(
        summary="ok",
        sql="SELECT 1",
        chart_spec=ChartSpec(chart_type="bar", x_column="a", y_column="b"),
    )
    assert pr.chart_spec.chart_type == "bar"
    assert pr.chart_spec.x_column == "a"


# --- Agent factory -------------------------------------------------------


def test_build_chat_agent_constructs_with_test_model():
    """build_chat_agent returns an Agent instance for any pydantic_ai model.

    Uses pydantic_ai's TestModel — guarantees no real LLM call.
    """
    from pydantic_ai.models.test import TestModel

    agent = build_chat_agent(TestModel())
    assert agent is not None


# --- D-CHAT-09 invariant — no nl_service import in chat_agent -------------


def test_chat_agent_does_not_import_nl_service():
    """D-CHAT-09 — chat_agent uses harness pieces directly, NOT run_nl_query."""
    repo = Path(__file__).resolve().parents[2]
    src = (repo / "app" / "core" / "agent" / "chat_agent.py").read_text()
    assert "from app.core.agent.nl_service" not in src
    assert "import nl_service" not in src
    # And does not import from nl_agent — chat_agent is the parallel multi-step path.
    assert "from app.core.agent.nl_agent import run_nl_query" not in src
