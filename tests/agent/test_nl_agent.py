"""Unit tests for app.core.agent.nl_agent — NL-06, SAFE-04, SAFE-05 coverage.

All tests use PydanticAI TestModel / FunctionModel — no real API calls.
A SQLite in-memory database with a tiny ufs_data fixture stands in for MySQL.
"""
from __future__ import annotations

import pytest
import sqlalchemy as sa
import pandas as pd
from typing import Union

from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.usage import UsageLimits
from pydantic_ai.exceptions import UsageLimitExceeded

from app.adapters.db.base import DBAdapter
from app.core.agent.config import AgentConfig
from app.core.agent.nl_agent import (
    AgentDeps,
    AgentRunFailure,
    ClarificationNeeded,
    SQLResult,
    _execute_read_only,
    build_agent,
    run_agent,
)
from app.core.config import DatabaseConfig


# ---------------------------------------------------------------------------
# Fake DB adapter — SQLite in-memory with minimal ufs_data fixture
# ---------------------------------------------------------------------------

class _FakeDB(DBAdapter):
    """Minimal DBAdapter backed by SQLite in-memory for tests."""

    def __init__(self, engine: sa.Engine) -> None:
        super().__init__(DatabaseConfig(name="fake", type="mysql"))
        self._engine = engine

    def _get_engine(self) -> sa.Engine:
        return self._engine

    def test_connection(self) -> tuple[bool, str]:
        return True, "ok"

    def list_tables(self) -> list[str]:
        return ["ufs_data"]

    def get_schema(self, tables: list[str] | None = None) -> dict[str, list[dict]]:
        return {"ufs_data": []}

    def run_query(self, sql: str) -> pd.DataFrame:
        with self._engine.connect() as conn:
            return pd.read_sql_query(sa.text(sql), conn)


@pytest.fixture
def fake_db() -> _FakeDB:
    """Return a _FakeDB backed by a SQLite in-memory database with two fixture rows."""
    eng = sa.create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(sa.text(
            "CREATE TABLE ufs_data "
            "(PLATFORM_ID TEXT, InfoCategory TEXT, Item TEXT, Result TEXT)"
        ))
        conn.execute(sa.text(
            "INSERT INTO ufs_data VALUES "
            "('P1', 'storage', 'item1', '/sys/kernel/foo'), "
            "('P2', 'storage', 'item1', 'plain_value')"
        ))
    return _FakeDB(eng)


@pytest.fixture
def agent_cfg() -> AgentConfig:
    return AgentConfig(max_steps=5, row_cap=10, timeout_s=5, allowed_tables=["ufs_data"])


def _make_deps(
    fake_db: _FakeDB,
    agent_cfg: AgentConfig,
    llm_type: str = "ollama",
) -> AgentDeps:
    return AgentDeps(db=fake_db, agent_cfg=agent_cfg, active_llm_type=llm_type)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Test 1: agent has run_sql tool registered
# ---------------------------------------------------------------------------

def test_build_agent_registers_run_sql_tool(agent_cfg: AgentConfig) -> None:
    """build_agent() must register exactly one function tool named 'run_sql'."""
    agent = build_agent(TestModel())
    tool_names = list(agent._function_toolset.tools.keys())
    assert "run_sql" in tool_names, f"Expected 'run_sql' in tools; got {tool_names}"
    assert len(tool_names) == 1, f"Expected exactly 1 tool; got {tool_names}"


# ---------------------------------------------------------------------------
# Test 2: output_type introspection — both union members visible
# ---------------------------------------------------------------------------

def test_build_agent_has_union_output_type(agent_cfg: AgentConfig) -> None:
    """Agent must have SQLResult and ClarificationNeeded as output tool names."""
    agent = build_agent(TestModel())
    # Output tools are registered as 'final_result_SQLResult' / 'final_result_ClarificationNeeded'
    fs = agent._function_toolset
    # Access via output_schema.toolset (PydanticAI 1.86 internal structure)
    output_toolset = fs.output_schema.toolset
    output_tool_names = [t.name for t in output_toolset._tool_defs]
    assert any("SQLResult" in n for n in output_tool_names), (
        f"SQLResult not in output tools: {output_tool_names}"
    )
    assert any("ClarificationNeeded" in n for n in output_tool_names), (
        f"ClarificationNeeded not in output tools: {output_tool_names}"
    )


# ---------------------------------------------------------------------------
# Test 3: run_agent returns SQLResult when TestModel uses default output
# ---------------------------------------------------------------------------

def test_run_agent_returns_sql_result_for_lookup_question(
    fake_db: _FakeDB, agent_cfg: AgentConfig
) -> None:
    """TestModel default output returns the first union member (SQLResult)."""
    model = TestModel(custom_output_args={"query": "SELECT Result FROM ufs_data", "explanation": "test"})
    agent = build_agent(model)
    deps = _make_deps(fake_db, agent_cfg)
    result = run_agent(agent, "What is item1 on P1?", deps)
    assert isinstance(result, SQLResult), f"Expected SQLResult, got {type(result).__name__}: {result}"
    assert result.query.upper().startswith("SELECT")


# ---------------------------------------------------------------------------
# Test 4: run_agent returns ClarificationNeeded when scripted via FunctionModel
# ---------------------------------------------------------------------------

def test_run_agent_returns_clarification_needed_when_scripted(
    fake_db: _FakeDB, agent_cfg: AgentConfig
) -> None:
    """FunctionModel returning ClarificationNeeded output tool must produce ClarificationNeeded."""
    def fn(messages: list, info: AgentInfo) -> ModelResponse:
        tool_name = next(
            (t.name for t in info.output_tools if "ClarificationNeeded" in t.name),
            None,
        )
        assert tool_name, f"ClarificationNeeded tool not found in {[t.name for t in info.output_tools]}"
        return ModelResponse(parts=[ToolCallPart(
            tool_name,
            {"message": "Which parameter?", "candidate_params": ["storage / item1"]}
        )])

    agent = build_agent(FunctionModel(fn))
    deps = _make_deps(fake_db, agent_cfg)
    result = run_agent(agent, "Tell me about X?", deps)
    assert isinstance(result, ClarificationNeeded), f"Expected ClarificationNeeded, got {type(result).__name__}: {result}"
    assert result.candidate_params == ["storage / item1"]


# ---------------------------------------------------------------------------
# Test 5: run_agent catches UsageLimitExceeded and returns AgentRunFailure step-cap
# ---------------------------------------------------------------------------

def test_run_agent_catches_usage_limit_exceeded(
    fake_db: _FakeDB, agent_cfg: AgentConfig
) -> None:
    """FunctionModel that always calls run_sql must trigger SAFE-04 step-cap."""
    call_count = [0]

    def always_tool(messages: list, info: AgentInfo) -> ModelResponse:
        call_count[0] += 1
        fn_tools = info.function_tools
        if fn_tools:
            return ModelResponse(parts=[ToolCallPart(fn_tools[0].name, {"sql": "SELECT 1 FROM ufs_data"})])
        out_tool = next(t.name for t in info.output_tools if "SQLResult" in t.name)
        return ModelResponse(parts=[ToolCallPart(out_tool, {"query": "SELECT 1", "explanation": "x"})])

    agent = build_agent(FunctionModel(always_tool))
    # max_steps=1 so the second tool call attempt exceeds the limit
    cfg = AgentConfig(max_steps=1, row_cap=10, timeout_s=5, allowed_tables=["ufs_data"])
    deps = AgentDeps(db=fake_db, agent_cfg=cfg, active_llm_type="ollama")  # type: ignore[arg-type]
    result = run_agent(agent, "infinite loop question", deps)
    assert isinstance(result, AgentRunFailure), f"Expected AgentRunFailure, got {type(result).__name__}: {result}"
    assert result.reason == "step-cap", f"Expected reason='step-cap', got {result.reason!r}"


# ---------------------------------------------------------------------------
# Test 6: run_sql wraps results in <db_data>...</db_data> tags (SAFE-05)
# ---------------------------------------------------------------------------

def test_run_sql_wraps_result_in_db_data_tags(
    fake_db: _FakeDB, agent_cfg: AgentConfig
) -> None:
    """run_sql tool must wrap DB rows in <db_data>...</db_data> (SAFE-05)."""
    # Use FunctionModel to force a run_sql call with a known SQL
    sql_used = [""]

    def fn(messages: list, info: AgentInfo) -> ModelResponse:
        # First call: invoke run_sql tool
        fn_tools = info.function_tools
        if fn_tools and not any(
            hasattr(p, "tool_name") and p.tool_name in {t.name for t in fn_tools}
            for msg in messages
            for p in getattr(msg, "parts", [])
            if hasattr(p, "part_kind") and p.part_kind == "tool-return"
        ):
            sql = "SELECT PLATFORM_ID, Item, Result FROM ufs_data"
            sql_used[0] = sql
            return ModelResponse(parts=[ToolCallPart("run_sql", {"sql": sql})])
        # Second call: return SQLResult
        out_tool = next(t.name for t in info.output_tools if "SQLResult" in t.name)
        return ModelResponse(parts=[ToolCallPart(out_tool, {"query": sql_used[0], "explanation": "rows fetched"})])

    agent = build_agent(FunctionModel(fn))
    deps = _make_deps(fake_db, agent_cfg, llm_type="ollama")
    result = run_agent(agent, "show me data", deps)
    # We check the tool return by calling run_sql directly via the tool function
    # Extract the tool function from the agent
    run_sql_tool = agent._function_toolset.tools["run_sql"]
    from pydantic_ai import RunContext
    from pydantic_ai.usage import RunUsage
    ctx = RunContext(deps=deps, model=TestModel(), usage=RunUsage())
    tool_return = run_sql_tool.function(ctx, "SELECT PLATFORM_ID, Item, Result FROM ufs_data")
    assert tool_return.startswith("<db_data>"), f"Expected <db_data> prefix, got: {tool_return[:100]}"
    assert tool_return.rstrip().endswith("</db_data>"), f"Expected </db_data> suffix, got: {tool_return[-100:]}"
    assert "P1" in tool_return or "P2" in tool_return, "Expected rows in result"


# ---------------------------------------------------------------------------
# Test 7: run_sql rejects disallowed table
# ---------------------------------------------------------------------------

def test_run_sql_rejects_disallowed_table(
    fake_db: _FakeDB, agent_cfg: AgentConfig
) -> None:
    """run_sql tool must reject SQL referencing tables not in allowed_tables."""
    agent = build_agent(TestModel())
    deps = _make_deps(fake_db, agent_cfg)
    run_sql_tool = agent._function_toolset.tools["run_sql"]
    from pydantic_ai import RunContext
    from pydantic_ai.usage import RunUsage
    ctx = RunContext(deps=deps, model=TestModel(), usage=RunUsage())
    result = run_sql_tool.function(ctx, "SELECT * FROM other_table")
    assert result.startswith("SQL rejected:"), f"Expected 'SQL rejected:' prefix, got: {result[:100]}"


# ---------------------------------------------------------------------------
# Test 8: run_sql applies scrub_paths for openai, not for ollama
# ---------------------------------------------------------------------------

def test_run_sql_scrubs_paths_for_openai_only(
    fake_db: _FakeDB, agent_cfg: AgentConfig
) -> None:
    """scrub_paths must be applied only when active_llm_type='openai' (SAFE-06 / D-26).

    Fixture row P1 has Result='/sys/kernel/foo' — after scrub it becomes '<path>'.
    Fixture row P2 has Result='plain_value' — unchanged regardless.
    """
    agent = build_agent(TestModel())
    run_sql_tool = agent._function_toolset.tools["run_sql"]
    from pydantic_ai import RunContext
    from pydantic_ai.usage import RunUsage

    sql = "SELECT PLATFORM_ID, Result FROM ufs_data WHERE PLATFORM_ID = 'P1'"

    # OpenAI: /sys/kernel/foo should be replaced with <path>
    deps_openai = _make_deps(fake_db, agent_cfg, llm_type="openai")
    ctx_openai = RunContext(deps=deps_openai, model=TestModel(), usage=RunUsage())
    result_openai = run_sql_tool.function(ctx_openai, sql)
    assert "<path>" in result_openai, f"Expected <path> in OpenAI result: {result_openai}"
    assert "/sys/kernel/foo" not in result_openai, f"Path not scrubbed in OpenAI result: {result_openai}"

    # Ollama: /sys/kernel/foo must be preserved
    deps_ollama = _make_deps(fake_db, agent_cfg, llm_type="ollama")
    ctx_ollama = RunContext(deps=deps_ollama, model=TestModel(), usage=RunUsage())
    result_ollama = run_sql_tool.function(ctx_ollama, sql)
    assert "/sys/kernel/foo" in result_ollama, f"Path should be preserved in Ollama result: {result_ollama}"
    assert "<path>" not in result_ollama, f"Path should NOT be scrubbed in Ollama result: {result_ollama}"


# ---------------------------------------------------------------------------
# Test 9: run_agent translates generic exception to llm-error
# ---------------------------------------------------------------------------

def test_run_agent_translates_generic_error_to_llm_error(
    fake_db: _FakeDB, agent_cfg: AgentConfig
) -> None:
    """Any non-UsageLimitExceeded exception from agent.run_sync must become llm-error."""
    def fn_raises(messages: list, info: AgentInfo) -> ModelResponse:
        raise RuntimeError("simulated LLM error")

    agent = build_agent(FunctionModel(fn_raises))
    deps = _make_deps(fake_db, agent_cfg)
    result = run_agent(agent, "hello", deps)
    assert isinstance(result, AgentRunFailure), f"Expected AgentRunFailure, got {type(result).__name__}"
    assert result.reason == "llm-error", f"Expected reason='llm-error', got {result.reason!r}"
    assert "simulated LLM error" in result.detail


# ---------------------------------------------------------------------------
# Test 10: run_sql applies inject_limit (SAFE-03) to cap row count
# ---------------------------------------------------------------------------

def test_run_sql_injects_limit(fake_db: _FakeDB) -> None:
    """run_sql must inject LIMIT row_cap when SQL has no LIMIT clause."""
    # AgentConfig with row_cap=1 so only 1 row is returned from 2-row fixture
    cfg = AgentConfig(max_steps=5, row_cap=1, timeout_s=5, allowed_tables=["ufs_data"])
    agent = build_agent(TestModel())
    run_sql_tool = agent._function_toolset.tools["run_sql"]
    from pydantic_ai import RunContext
    from pydantic_ai.usage import RunUsage

    deps = AgentDeps(db=fake_db, agent_cfg=cfg, active_llm_type="ollama")  # type: ignore[arg-type]
    ctx = RunContext(deps=deps, model=TestModel(), usage=RunUsage())
    result = run_sql_tool.function(ctx, "SELECT PLATFORM_ID FROM ufs_data")
    # With row_cap=1, only 1 row should appear (P1 or P2, not both)
    lines = [line for line in result.split("\n") if line.strip() and not line.startswith("<")]
    # header + 1 data row at most (2 rows in fixture, cap=1)
    data_rows = [l for l in lines if "P1" in l or "P2" in l]
    assert len(data_rows) == 1, f"Expected 1 data row with row_cap=1, got {len(data_rows)}: {result}"
