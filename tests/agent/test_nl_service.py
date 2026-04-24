"""Tests for the framework-agnostic nl_service orchestrator (INFRA-07)."""
from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock

import pandas as pd
import pytest
import sqlalchemy as sa
from pydantic_ai.exceptions import UsageLimitExceeded

from app.adapters.db.base import DBAdapter
from app.core.agent.config import AgentConfig
from app.core.agent.nl_agent import (
    AgentDeps,
    AgentRunFailure,
    ClarificationNeeded,
    SQLResult,
)
from app.core.agent.nl_service import NLResult, run_nl_query
from app.core.config import DatabaseConfig


# ---------------------------------------------------------------------------
# Minimal concrete DBAdapter for tests (cannot pass MagicMock — Pydantic is_instance)
# ---------------------------------------------------------------------------


class _StubDB(DBAdapter):
    """Minimal concrete DBAdapter for tests — no real DB access needed."""

    def __init__(self):
        super().__init__(DatabaseConfig(name="stub", type="mysql"))
        self._engine_mock = MagicMock()

    def _get_engine(self):
        return self._engine_mock

    def test_connection(self) -> tuple[bool, str]:
        return True, "ok"

    def list_tables(self) -> list[str]:
        return ["ufs_data"]

    def get_schema(self, tables=None) -> dict:
        return {}

    def run_query(self, sql: str) -> pd.DataFrame:
        return pd.DataFrame()


class _FakeRunResult:
    def __init__(self, output):
        self.output = output


class _FakeAgent:
    """Stand-in for pydantic_ai.Agent — only run_sync is exercised."""

    def __init__(self, *, raise_exc=None, output=None):
        self._raise = raise_exc
        self._output = output

    def run_sync(self, question, deps, usage_limits):
        if self._raise is not None:
            raise self._raise
        return _FakeRunResult(self._output)


def _make_deps(db, *, active_llm_type="ollama"):
    return AgentDeps(
        db=db,
        agent_cfg=AgentConfig(
            allowed_tables=["ufs_data"],
            row_cap=200,
            timeout_s=30,
            max_steps=5,
            model="",
        ),
        active_llm_type=active_llm_type,
    )


def test_step_cap_returns_failure():
    """Test 1 — UsageLimitExceeded -> NLResult(kind='failure', reason='step-cap')."""
    agent = _FakeAgent(raise_exc=UsageLimitExceeded("step cap"))
    deps = _make_deps(_StubDB())
    result = run_nl_query("Q", agent, deps)
    assert result.kind == "failure"
    assert result.failure.reason == "step-cap"


def test_clarification_branch():
    """Test 2 — ClarificationNeeded -> NLResult(kind='clarification_needed')."""
    output = ClarificationNeeded(
        message="Which param do you mean?",
        candidate_params=["InfoCategory / Item1", "InfoCategory / Item2"],
    )
    agent = _FakeAgent(output=output)
    deps = _make_deps(_StubDB())
    result = run_nl_query("Q", agent, deps)
    assert result.kind == "clarification_needed"
    assert result.message == "Which param do you mean?"
    assert result.candidate_params == ["InfoCategory / Item1", "InfoCategory / Item2"]


def test_ok_branch_fetches_dataframe(monkeypatch):
    """Test 3 — SQLResult -> NLResult(kind='ok') with LIMIT injected DataFrame."""
    fake_df = pd.DataFrame({"PLATFORM_ID": ["P1"], "Result": ["ok"]})

    db = _StubDB()
    conn_mock = MagicMock()
    db._engine_mock.connect.return_value.__enter__.return_value = conn_mock

    # Patch pd.read_sql_query to bypass real DB
    import app.core.agent.nl_service as mod

    monkeypatch.setattr(mod.pd, "read_sql_query", lambda sql, conn: fake_df)

    sql = "SELECT PLATFORM_ID, Result FROM ufs_data WHERE PLATFORM_ID = 'P1'"
    output = SQLResult(query=sql, explanation="One row for P1.")
    agent = _FakeAgent(output=output)
    deps = _make_deps(db)

    result = run_nl_query("Q", agent, deps)
    assert result.kind == "ok"
    assert "LIMIT" in result.sql.upper()  # inject_limit applied
    assert result.df.equals(fake_df)
    assert result.summary == "One row for P1."


def test_ok_branch_rejected_by_validator():
    """Test 4 — SQLResult with disallowed table -> NLResult(kind='failure', reason='llm-error')."""
    bad = SQLResult(query="SELECT * FROM mysql.user", explanation="bad")
    agent = _FakeAgent(output=bad)
    deps = _make_deps(_StubDB())

    result = run_nl_query("Q", agent, deps)
    assert result.kind == "failure"
    assert result.failure.reason == "llm-error"
    assert "rejected" in result.failure.detail.lower()


def test_nl_service_importable_without_streamlit():
    """Test 5 — nl_service importable in subprocess with no Streamlit session."""
    r = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.core.agent.nl_service import NLResult, run_nl_query; print('ok')",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd="/home/yh/Desktop/02_Projects/Proj28_PBM2",
    )
    assert r.returncode == 0, (
        f"returncode={r.returncode}\nstdout={r.stdout}\nstderr={r.stderr}"
    )
    assert "ok" in r.stdout


def test_nl_result_candidate_params_not_shared():
    """Test 6 — NLResult.candidate_params default_factory: separate instances don't share list."""
    a = NLResult(kind="clarification_needed", message="x")
    b = NLResult(kind="clarification_needed", message="y")
    a.candidate_params.append("X")
    assert b.candidate_params == [], (
        "candidate_params must use default_factory=list, not a mutable default"
    )
