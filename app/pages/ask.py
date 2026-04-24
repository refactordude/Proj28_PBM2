"""Ask page — Phase 2 NL agent UI (NL-01..04, NL-10).

nest_asyncio.apply() MUST be the first executable statement (Pitfall 6).
"""
from __future__ import annotations

# --- nest_asyncio MUST be first — Pitfall 6 ---
import nest_asyncio
nest_asyncio.apply()

import uuid
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from app.adapters.llm.pydantic_model import build_pydantic_model
from app.core.agent.config import AgentConfig
from app.core.agent.nl_agent import (
    AgentDeps,
    AgentRunFailure,
    ClarificationNeeded,
    SQLResult,
    build_agent,
    run_agent,
)
from app.core.config import find_llm, load_settings


_HISTORY_CAP = 50
_DEFAULTS: dict[str, Any] = {
    "ask.question": "",
    "ask.history": [],
    "ask.openai_warning_dismissed": False,
    "ask.confirmed_params": [],
    "ask.pending_params": [],
    "ask.last_sql": "",
    "ask.last_df": None,
    "ask.last_summary": "",
    "ask.last_abort": None,           # AgentRunFailure | None — populated by run, cleared by next successful run
    "ask.history_truncated": False,
}


@st.cache_resource
def get_nl_agent(llm_name: str):
    """Build + cache a PydanticAI Agent per backend (Pitfall 3)."""
    if not llm_name:
        return None
    settings = load_settings()
    cfg = find_llm(settings, llm_name)
    if cfg is None:
        return None
    model = build_pydantic_model(cfg)
    return build_agent(model)


def _init_session_state() -> None:
    for k, v in _DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _render_banners() -> None:
    """Top-of-page banner zone. At most one banner; priority abort > sensitivity."""
    abort: AgentRunFailure | None = st.session_state.get("ask.last_abort")
    if abort is not None:
        if abort.reason == "step-cap":
            st.error("Agent stopped: reached the 5-step limit. Try rephrasing your question with more specific parameters.")
        elif abort.reason == "timeout":
            st.error("Agent stopped: query timed out after 30 seconds. Try a more targeted question or switch to a faster model.")
        else:  # llm-error fallback
            st.error(f"Something went wrong. Try rephrasing your question. ({abort.detail.split(':')[0] or 'Error'})")
        with st.expander("Partial output", expanded=False):
            if abort.last_sql:
                st.subheader("Last tool call")
                st.code(abort.last_sql, language="sql")
        return  # skip sensitivity warning when abort is active

    active_llm = st.session_state.get("active_llm", "")
    settings = load_settings()
    active_cfg = find_llm(settings, active_llm)
    is_openai = bool(active_cfg and active_cfg.type == "openai")
    if is_openai and not st.session_state.get("ask.openai_warning_dismissed"):
        st.warning(
            "You're about to send UFS parameter data to OpenAI's servers. "
            "Switch to Ollama in the sidebar for local processing."
        )
        if st.button("Dismiss", type="secondary", key="ask.dismiss_warning"):
            st.session_state["ask.openai_warning_dismissed"] = True
            st.rerun()


def _render_history() -> None:
    """Collapsed history expander above the question input (D-19)."""
    history = st.session_state.get("ask.history", [])
    with st.expander(f"History ({len(history)})", expanded=False):
        if not history:
            st.caption("Your recent questions appear here.")
            return
        for entry in reversed(history):
            col_q, col_ts = st.columns([5, 1])
            with col_q:
                q = entry["question"]
                label = (q[:80] + "...") if len(q) > 80 else q
                if entry["status"] == "failed":
                    label = label + " ✗"
                if st.button(label, key=f"history_{entry['id']}", type="secondary"):
                    st.session_state["ask.question"] = entry["question"]
                    st.rerun()
            with col_ts:
                st.caption(entry["timestamp"])
        if st.session_state.get("ask.history_truncated"):
            st.caption("History truncated to 50 most recent questions.")


def _append_history(question: str, sql: str, row_count: int, status: str) -> None:
    entry = {
        "id": uuid.uuid4().hex,
        "question": question,
        "sql": sql,
        "row_count": row_count,
        "status": status,
        "timestamp": datetime.now().strftime("%H:%M"),
    }
    hist: list = st.session_state.setdefault("ask.history", [])
    hist.append(entry)
    if len(hist) > _HISTORY_CAP:
        del hist[: len(hist) - _HISTORY_CAP]
        st.session_state["ask.history_truncated"] = True


def _render_question_input() -> str:
    return st.text_area(
        "Your question",
        value=st.session_state.get("ask.question", ""),
        placeholder="e.g. What is the WriteProt status for all LUNs on platform X?",
        height=80,
        key="ask.question",
    )


def _render_starter_gallery() -> None:
    """Gallery rendered only when no history yet. (Plan 02-06 wires the YAML loader.)

    This plan is the UI scaffold; it renders from a stubbed list. Plan 02-06 replaces
    the stub with a load_starter_prompts() call.
    """
    if st.session_state.get("ask.history"):
        return
    st.subheader("Try asking...")
    stub_prompts = [
        {"label": "WriteProt status by platform",
         "question": "What is the WriteProt status for all LUNs on each platform?"},
        {"label": "Compare bkops across platforms",
         "question": "Compare background operations settings across all platforms."},
    ]
    cols = st.columns(4)
    for i, prompt in enumerate(stub_prompts[:8]):
        with cols[i % 4]:
            if st.button(prompt["label"], key=f"starter_{i}", type="secondary"):
                st.session_state["ask.question"] = prompt["question"]
                st.rerun()


def _render_answer_zone() -> None:
    last_df = st.session_state.get("ask.last_df")
    if last_df is None:
        return

    cfg_row_cap = 200  # AgentConfig.row_cap default — refined when agent runs
    if len(last_df) >= cfg_row_cap:
        st.warning(f"Result capped at {cfg_row_cap} rows. Refine your question to see all data.")

    st.dataframe(
        last_df,
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"{len(last_df)} rows returned.")

    summary = st.session_state.get("ask.last_summary", "")
    if summary:
        st.write(summary)

    sql = st.session_state.get("ask.last_sql", "")
    if sql:
        with st.expander("Generated SQL", expanded=False):
            st.code(sql, language="sql")
            if st.button("Regenerate", type="secondary", key="ask.regenerate"):
                _run_agent_flow(st.session_state.get("ask.question", ""))


def _run_agent_flow(question: str) -> None:
    """Single-shot agent run — NL-05 confirmation flow is wired in Plan 02-05.

    On ClarificationNeeded, this plan stores the proposed params in
    ask.pending_params and shows a stub message. Plan 02-05 replaces the stub
    with the actual multiselect + Run Query flow.
    """
    if not question.strip():
        return
    active_llm = st.session_state.get("active_llm", "")
    if not active_llm:
        st.error("No LLM backend selected. Pick one in the sidebar.")
        return
    active_db = st.session_state.get("active_db", "")
    from streamlit_app import get_db_adapter  # avoid circular import at module load
    db = get_db_adapter(active_db)
    if db is None:
        st.warning("No active database. Configure one in Settings.")
        return

    settings = load_settings()
    llm_cfg = find_llm(settings, active_llm)
    if llm_cfg is None:
        st.error("Selected LLM not found in settings.")
        return

    agent = get_nl_agent(active_llm)
    if agent is None:
        st.error("Could not build agent.")
        return

    deps = AgentDeps(
        db=db,
        agent_cfg=settings.app.agent,
        active_llm_type="openai" if llm_cfg.type == "openai" else "ollama",
    )

    with st.spinner("Thinking..."):
        output = run_agent(agent, question, deps)

    if isinstance(output, AgentRunFailure):
        st.session_state["ask.last_abort"] = output
        st.session_state["ask.last_df"] = None
        st.session_state["ask.last_summary"] = ""
        st.session_state["ask.last_sql"] = output.last_sql
        _append_history(question, output.last_sql, 0, "failed")
        return

    st.session_state["ask.last_abort"] = None

    if isinstance(output, ClarificationNeeded):
        # Plan 02-05 replaces this branch with the multiselect flow.
        st.session_state["ask.pending_params"] = output.candidate_params
        st.info(f"[Plan 02-05 placeholder] {output.message}")
        return

    # SQLResult — execute it via the same tool path by re-running.
    # In practice PydanticAI's tool call already executed the SQL; the agent's
    # result.output.query is the SQL and result.output.explanation is the summary.
    # We need the actual DataFrame for the table — fetch it now from the DB using
    # the validated query. Use the same validator+limiter+executor chain.
    from app.core.agent.nl_agent import _execute_read_only  # internal reuse
    from app.services.sql_limiter import inject_limit
    from app.services.sql_validator import validate_sql

    cfg = settings.app.agent
    vr = validate_sql(output.query, cfg.allowed_tables)
    if not vr.ok:
        st.error(f"Generated SQL was rejected: {vr.reason}")
        _append_history(question, output.query, 0, "failed")
        return
    safe_sql = inject_limit(output.query, cfg.row_cap)
    try:
        # Run the query and capture as DataFrame for display (separate from the tool-call
        # text the agent already saw). This is intentional duplication — the agent's view
        # is text-for-LLM; the user's view is a DataFrame.
        import sqlalchemy as sa
        if hasattr(db, "_get_engine"):
            with db._get_engine().connect() as conn:
                try:
                    conn.execute(sa.text("SET SESSION TRANSACTION READ ONLY"))
                except Exception:
                    pass
                df = pd.read_sql_query(sa.text(safe_sql), conn)
        else:
            df = db.run_query(safe_sql)
    except Exception as exc:
        st.error(f"SQL execution failed. ({type(exc).__name__})")
        _append_history(question, safe_sql, 0, "failed")
        return

    st.session_state["ask.last_sql"] = safe_sql
    st.session_state["ask.last_df"] = df
    st.session_state["ask.last_summary"] = output.explanation
    _append_history(question, safe_sql, len(df), "ok")


def render() -> None:
    _init_session_state()
    _render_banners()
    st.title("Ask")
    _render_history()
    question = _render_question_input()

    # Submit on explicit "Run" press — for this plan we use a default button.
    # (Plan 02-05 replaces this with the param-confirmation "Run Query" button.)
    if st.button("Run", type="primary", key="ask.run"):
        _run_agent_flow(question)

    _render_answer_zone()
    _render_starter_gallery()


render()
