"""Settings page — DB/LLM CRUD with per-row Test.

Decisions: D-09 (open access), D-10 (per-row sync Test), D-11 (masked inputs + plaintext
YAML persistence), D-12 (Save -> save_settings -> cache clears -> toast).
"""
from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Literal

import requests
import streamlit as st
from openai import OpenAI

from app.core.config import (
    AppConfig,
    DatabaseConfig,
    LLMConfig,
    Settings,
    load_settings,
    save_settings,
)
from app.adapters.db.registry import build_adapter as build_db_adapter
from app.adapters.llm.registry import build_adapter as build_llm_adapter  # unused in Phase 1 Test helper; retained for Phase 2


# ---------- LLM connection test helpers (D-10) ----------

def _test_llm_connection(cfg: LLMConfig) -> tuple[bool, str]:
    """Synchronous LLM ping. Returns (ok, message)."""
    if cfg.type == "openai":
        api_key = cfg.api_key or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return False, "No API key configured (set OPENAI_API_KEY env var or Settings api_key)"
        try:
            client = OpenAI(api_key=api_key, base_url=cfg.endpoint or None, timeout=5.0)
            client.models.list()
            return True, "OpenAI API reachable"
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"
    elif cfg.type == "ollama":
        endpoint = (cfg.endpoint or "http://localhost:11434").rstrip("/")
        try:
            r = requests.get(f"{endpoint}/api/tags", timeout=5)
            r.raise_for_status()
            return True, "Ollama is running"
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"
    else:
        return False, f"Test not implemented for type '{cfg.type}' in Phase 1"


# ---------- Session state helpers ----------

_STATE_KEY = "_settings_draft"  # In-memory edit buffer; only flushed to YAML on Save.

def _ensure_draft() -> Settings:
    """Load settings into session_state on first render; return the draft."""
    if _STATE_KEY not in st.session_state:
        st.session_state[_STATE_KEY] = deepcopy(load_settings())
    return st.session_state[_STATE_KEY]

def _persist_and_clear_caches(draft: Settings) -> tuple[bool, str]:
    """D-12: save_settings -> clear both caches -> return (ok, msg)."""
    try:
        save_settings(draft)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    st.cache_resource.clear()
    st.cache_data.clear()
    return True, "saved"

def _test_db_connection(cfg: DatabaseConfig) -> tuple[bool, str]:
    try:
        adapter = build_db_adapter(cfg)
        return adapter.test_connection()
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


# ---------- Per-entry renderers ----------

def _render_db_entry(draft: Settings, idx: int) -> None:
    cfg = draft.databases[idx]
    st.subheader(cfg.name or f"(new database #{idx + 1})")
    left, right = st.columns([3, 1])
    with left:
        cfg.name = st.text_input("Name", value=cfg.name, key=f"db_name_{idx}")
        cfg.type = st.selectbox(
            "Type",
            options=["mysql", "postgres", "mssql", "bigquery", "snowflake"],
            index=["mysql", "postgres", "mssql", "bigquery", "snowflake"].index(cfg.type),
            key=f"db_type_{idx}",
        )
        cfg.host = st.text_input("Host", value=cfg.host, key=f"db_host_{idx}")
        cfg.port = int(st.number_input("Port", value=cfg.port, min_value=1, max_value=65535, step=1, key=f"db_port_{idx}"))
        cfg.database = st.text_input("Database", value=cfg.database, key=f"db_database_{idx}")
        cfg.user = st.text_input("User", value=cfg.user, key=f"db_user_{idx}")
        cfg.password = st.text_input("Password", value=cfg.password, type="password", key=f"db_password_{idx}")  # D-11
        cfg.readonly = st.checkbox("Readonly session (SET SESSION TRANSACTION READ ONLY)", value=cfg.readonly, key=f"db_readonly_{idx}")
    with right:
        if st.button("Test", key=f"db_test_{idx}"):
            with st.spinner("Testing..."):
                ok, msg = _test_db_connection(cfg)
            st.session_state[f"db_test_result_{idx}"] = (ok, msg)
        result = st.session_state.get(f"db_test_result_{idx}")
        if result is not None:
            ok, msg = result
            if ok:
                st.success("Connected")
            else:
                st.error("Connection failed. See error detail below.")
                with st.expander("Error detail"):
                    st.code(msg)

    save_col, del_col = st.columns([1, 1])
    with save_col:
        if st.button("Save Connection", type="primary", key=f"db_save_{idx}"):
            ok, msg = _persist_and_clear_caches(draft)
            if ok:
                st.toast("Saved. Caches refreshed.")
            else:
                st.error(f"Could not save settings. Check file permissions on config/settings.yaml. ({msg})")
    with del_col:
        if st.button("Delete", type="secondary", key=f"db_delete_{idx}"):
            st.session_state[f"db_confirm_delete_{idx}"] = True
    if st.session_state.get(f"db_confirm_delete_{idx}"):
        _render_delete_dialog("db", idx, draft, cfg.name)
    st.divider()


def _render_llm_entry(draft: Settings, idx: int) -> None:
    cfg = draft.llms[idx]
    st.subheader(cfg.name or f"(new LLM #{idx + 1})")
    left, right = st.columns([3, 1])
    with left:
        cfg.name = st.text_input("Name", value=cfg.name, key=f"llm_name_{idx}")
        cfg.type = st.selectbox(
            "Type",
            options=["openai", "anthropic", "ollama", "vllm", "custom"],
            index=["openai", "anthropic", "ollama", "vllm", "custom"].index(cfg.type),
            key=f"llm_type_{idx}",
        )
        cfg.model = st.text_input("Model", value=cfg.model, key=f"llm_model_{idx}")
        cfg.endpoint = st.text_input("Endpoint", value=cfg.endpoint, key=f"llm_endpoint_{idx}")
        cfg.api_key = st.text_input("API Key", value=cfg.api_key, type="password", key=f"llm_api_key_{idx}")  # D-11
        cfg.temperature = float(st.number_input("Temperature", value=cfg.temperature, min_value=0.0, max_value=2.0, step=0.1, key=f"llm_temperature_{idx}"))
        cfg.max_tokens = int(st.number_input("Max Tokens", value=cfg.max_tokens, min_value=1, max_value=100000, step=1, key=f"llm_max_tokens_{idx}"))
        # Headers is an edge feature: render as JSON textarea
        headers_raw = st.text_area(
            "Headers (JSON)",
            value=json.dumps(cfg.headers),
            key=f"llm_headers_{idx}",
        )
        try:
            parsed_headers = json.loads(headers_raw)
            if isinstance(parsed_headers, dict):
                cfg.headers = parsed_headers
        except (json.JSONDecodeError, ValueError):
            st.error("Headers JSON is invalid; not saved")
    with right:
        if st.button("Test", key=f"llm_test_{idx}"):
            with st.spinner("Testing..."):
                ok, msg = _test_llm_connection(cfg)
            st.session_state[f"llm_test_result_{idx}"] = (ok, msg)
        result = st.session_state.get(f"llm_test_result_{idx}")
        if result is not None:
            ok, msg = result
            if ok:
                st.success("Connected")
            else:
                st.error("Connection failed. See error detail below.")
                with st.expander("Error detail"):
                    st.code(msg)

    save_col, del_col = st.columns([1, 1])
    with save_col:
        if st.button("Save Connection", type="primary", key=f"llm_save_{idx}"):
            ok, msg = _persist_and_clear_caches(draft)
            if ok:
                st.toast("Saved. Caches refreshed.")
            else:
                st.error(f"Could not save settings. Check file permissions on config/settings.yaml. ({msg})")
    with del_col:
        if st.button("Delete", type="secondary", key=f"llm_delete_{idx}"):
            st.session_state[f"llm_confirm_delete_{idx}"] = True
    if st.session_state.get(f"llm_confirm_delete_{idx}"):
        _render_delete_dialog("llm", idx, draft, cfg.name)
    st.divider()


def _render_delete_dialog(kind: Literal["db", "llm"], idx: int, draft: Settings, name: str) -> None:
    @st.dialog("Delete connection?")
    def _dialog():
        st.write(f"This will remove {name} from settings.yaml. This cannot be undone.")
        col_del, col_keep = st.columns(2)
        with col_del:
            if st.button("Delete", type="primary", key=f"{kind}_delete_confirm_{idx}"):
                if kind == "db":
                    draft.databases.pop(idx)
                else:
                    draft.llms.pop(idx)
                ok, msg = _persist_and_clear_caches(draft)
                st.session_state.pop(f"{kind}_confirm_delete_{idx}", None)
                if ok:
                    st.toast("Saved. Caches refreshed.")
                st.rerun()
        with col_keep:
            if st.button("Keep Connection", type="secondary", key=f"{kind}_delete_cancel_{idx}"):
                st.session_state.pop(f"{kind}_confirm_delete_{idx}", None)
                st.rerun()
    _dialog()


def _render_agent_config_readonly(agent_cfg) -> None:
    st.caption("Agent defaults (Phase 2)")
    st.text_input("Model override (blank = inherit from selected LLM)", value=agent_cfg.model or "", disabled=True, key="agent_model_ro")
    st.number_input("max_steps", value=agent_cfg.max_steps, disabled=True, key="agent_max_steps_ro")
    st.number_input("row_cap", value=agent_cfg.row_cap, disabled=True, key="agent_row_cap_ro")
    st.number_input("timeout_s", value=agent_cfg.timeout_s, disabled=True, key="agent_timeout_ro")
    st.text_input("allowed_tables", value=", ".join(agent_cfg.allowed_tables), disabled=True, key="agent_tables_ro")
    st.number_input("max_context_tokens", value=agent_cfg.max_context_tokens, disabled=True, key="agent_ctx_ro")


# ---------- Page entry ----------

st.title("Settings")
draft = _ensure_draft()

with st.expander("Database Connections", expanded=True):
    if not draft.databases:
        st.info("No connections configured. Add a database or LLM connection to get started.")
    for i in range(len(draft.databases)):
        _render_db_entry(draft, i)
    if st.button("+ Add Database", type="secondary", key="add_db"):
        draft.databases.append(DatabaseConfig(name=f"new_db_{len(draft.databases) + 1}"))
        st.rerun()

with st.expander("LLM Connections", expanded=True):
    if not draft.llms:
        st.info("No connections configured. Add a database or LLM connection to get started.")
    for i in range(len(draft.llms)):
        _render_llm_entry(draft, i)
    if st.button("+ Add LLM", type="secondary", key="add_llm"):
        draft.llms.append(LLMConfig(name=f"new_llm_{len(draft.llms) + 1}"))
        st.rerun()

# AgentConfig readonly (D-03 discretion; render at bottom of LLM section as per UI-SPEC)
_render_agent_config_readonly(draft.app.agent)
