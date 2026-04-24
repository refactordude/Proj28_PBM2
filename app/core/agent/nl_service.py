"""Framework-agnostic SAFE-02..06 orchestration for the NL agent (INFRA-07).

This module is the SINGLE entry point that both v1.0 (app/pages/ask.py) and v2.0
(app_v2/routers/ask.py — Phase 5) call when running an NL query. Any route that
touches the agent MUST go through run_nl_query — bypassing it silently skips
the post-agent SQL re-validation and DataFrame fetch path.

Responsibility split with nl_agent.py:
  - nl_agent.run_sql TOOL (already implemented): SAFE-02 validate_sql, SAFE-03
    inject_limit, SAFE-06 scrub_paths (OpenAI), SAFE-05 <db_data> wrap. The tool
    returns TEXT rows to the LLM as context.
  - nl_service.run_nl_query (this module): SAFE-04 step-cap via run_agent +
    UsageLimits (already inside run_agent), post-agent SQLResult triage,
    re-validation of the emitted SQL, LIMIT re-injection, read-only session
    execution with MySQL max_execution_time, DataFrame fetch for UI display.
  - The tool's rows-text output is what the LLM sees; the UI needs a DataFrame.
    Those are intentionally separate code paths (see ask.py comment line ~312).

Why two validate_sql / inject_limit calls?
  - First call (inside the tool): protects the DB from bad SQL during reasoning.
  - Second call (here, post-agent): protects against the rare case where the
    agent's final output.query differs from what it passed to the tool. A belt-
    and-braces guarantee that the SQL the USER sees in the UI expander is the
    SAME safe SQL that was executed.

Not imported here (intentional):
  - `streamlit` — this module runs in any Python process
  - `fastapi` — this module stays framework-agnostic
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

import pandas as pd
import sqlalchemy as sa

from app.core.agent.nl_agent import (
    AgentDeps,
    AgentRunFailure,
    ClarificationNeeded,
    SQLResult,
    run_agent,
)
from app.services.sql_limiter import inject_limit
from app.services.sql_validator import validate_sql

_log = logging.getLogger(__name__)


@dataclass
class NLResult:
    """Discriminated result of a single NL query, consumed by the UI layer.

    Exactly one of the three outcome shapes is populated based on `kind`:
      - "ok": sql, df, summary are meaningful
      - "clarification_needed": message, candidate_params are meaningful
      - "failure": failure is meaningful

    The struct replaces the v1.0 pattern of ask.py inspecting output types with
    isinstance checks — callers now read nl_result.kind and branch on it.
    """

    kind: Literal["ok", "clarification_needed", "failure"]
    # kind == "ok"
    sql: str = ""
    df: Optional[pd.DataFrame] = None
    summary: str = ""
    # kind == "clarification_needed"
    message: str = ""
    candidate_params: list[str] = field(default_factory=list)
    # kind == "failure"
    failure: Optional[AgentRunFailure] = None


def run_nl_query(
    question: str,
    agent,  # pydantic_ai.Agent — type omitted to keep import surface narrow
    deps: AgentDeps,
    *,
    regenerate: bool = False,
) -> NLResult:
    """Run the agent, triage output, fetch result DataFrame for SQLResult cases.

    Args:
        question: Natural-language question from the user.
        agent: Built PydanticAI Agent (from nl_agent.build_agent).
        deps: AgentDeps bundle with db, agent_cfg, active_llm_type.
        regenerate: Reserved flag for ASK-V2-03 cache-bypass in Phase 5.
                    Currently unused; callers may pass True to signal intent
                    for forward-compatibility but behavior is identical.

    Returns:
        NLResult with exactly one populated outcome branch.

    SAFETY CONTRACT (must be preserved by all callers):
        - UsageLimitExceeded -> NLResult.kind="failure" with reason="step-cap"
        - Timeout (MySQL max_execution_time) -> reason="timeout"
        - Other agent exceptions -> reason="llm-error"
        - SQLResult with SQL that fails validate_sql -> reason="llm-error",
          NO DB execution occurs; detail prefixed with "SQL rejected:"
        - SQLResult that passes validation: LIMIT re-injected, executed in
          READ ONLY session with max_execution_time, DataFrame returned
    """
    _ = regenerate  # silence linter; reserved for Phase 5

    output = run_agent(agent, question, deps)

    # --- Failure branch (step-cap, timeout, llm-error — already classified by run_agent)
    if isinstance(output, AgentRunFailure):
        return NLResult(kind="failure", failure=output)

    # --- Clarification branch — agent wants the user to confirm params (NL-05)
    if isinstance(output, ClarificationNeeded):
        return NLResult(
            kind="clarification_needed",
            message=output.message,
            candidate_params=list(output.candidate_params),
        )

    # --- SQLResult branch: re-validate, re-limit, execute, return DataFrame
    assert isinstance(output, SQLResult)
    cfg = deps.agent_cfg

    # SAFE-02 second pass — defensive. The in-tool validator ran; this one catches
    # the rare case where the agent's final output.query differs from what it
    # passed to the tool (hallucination between tool call and output emission).
    vr = validate_sql(output.query, cfg.allowed_tables)
    if not vr.ok:
        _log.warning("SQLResult rejected post-agent: %s", vr.reason)
        return NLResult(
            kind="failure",
            failure=AgentRunFailure(
                reason="llm-error",
                last_sql=output.query,
                detail=f"SQL rejected: {vr.reason}",
            ),
        )

    # SAFE-03 re-inject (idempotent — inject_limit is safe to call on already-limited SQL)
    safe_sql = inject_limit(output.query, cfg.row_cap)

    # Execute with the SAME read-only + max_execution_time pattern as nl_agent._execute_read_only
    # but returning a DataFrame (not a text block for the LLM).
    timeout_ms = int(cfg.timeout_s) * 1000
    engine_fn = getattr(deps.db, "_get_engine", None)
    try:
        if engine_fn is None:
            df = deps.db.run_query(safe_sql)
        else:
            with engine_fn().connect() as conn:
                try:
                    conn.execute(sa.text("SET SESSION TRANSACTION READ ONLY"))
                except Exception:
                    pass  # SAFE-01 precedent — non-fatal
                try:
                    conn.execute(sa.text(f"SET SESSION max_execution_time={timeout_ms}"))
                except Exception:
                    pass  # Pitfall 8 — MySQL 5.7.8+ only
                df = pd.read_sql_query(sa.text(safe_sql), conn)
    except Exception as exc:
        msg = str(exc).lower()
        reason: Literal["step-cap", "timeout", "llm-error"] = "llm-error"
        if "timeout" in msg or "max_execution_time" in msg or "execution time" in msg:
            reason = "timeout"
        _log.warning("SQL execution failed post-agent: %s: %s", type(exc).__name__, exc)
        return NLResult(
            kind="failure",
            failure=AgentRunFailure(
                reason=reason,
                last_sql=safe_sql,
                detail=f"{type(exc).__name__}: {exc}",
            ),
        )

    return NLResult(
        kind="ok",
        sql=safe_sql,
        df=df,
        summary=output.explanation,
    )
