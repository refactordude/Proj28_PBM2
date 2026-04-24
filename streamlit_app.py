"""PBM2 — Streamlit entrypoint.

Loads .env, builds shared navigation (Browse + Settings), renders the shared sidebar
(DB selector, LLM selector inert, connection health indicator), and routes to the
active page via st.navigation.

Auth (streamlit-authenticator) is deferred to a pre-deployment phase per D-04.
"""
from __future__ import annotations

import html
import time
from typing import Any

from dotenv import load_dotenv

# Load .env before any code that reads env vars (OPENAI_API_KEY, SETTINGS_PATH, etc.)
load_dotenv()

import streamlit as st

from app.adapters.db.registry import build_adapter
from app.core.config import DatabaseConfig, Settings, load_settings

# ---------------------------------------------------------------------------
# Page config — must be the first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PBM2",
    page_icon=":material/table_chart:",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Cached DB adapter factory
# ---------------------------------------------------------------------------
@st.cache_resource
def get_db_adapter(db_name: str) -> Any:
    """Return a cached DBAdapter for the named database.

    Keyed by db_name so each distinct DB gets its own singleton engine.
    Returns None if the database name is empty or not found in settings.
    """
    if not db_name:
        return None
    settings = load_settings()
    from app.core.config import find_database

    cfg = find_database(settings, db_name)
    if cfg is None:
        return None
    return build_adapter(cfg)


# ---------------------------------------------------------------------------
# Health-check helper with 60-second TTL
# ---------------------------------------------------------------------------
_HEALTH_TTL = 60  # seconds


def _get_health(db_name: str) -> tuple[str, str]:
    """Return (status, message) for the named DB, re-checking at most once per 60s.

    status is one of: "pass", "fail", "untested"
    Does NOT expose config values in the message — only the adapter's curated string.
    """
    if not db_name:
        return "untested", "No database selected"

    cache_key = f"_db_health_{db_name}"
    ts_key = f"_db_health_ts_{db_name}"

    now = time.time()
    last_ts: float = st.session_state.get(ts_key, 0.0)

    if now - last_ts < _HEALTH_TTL:
        # Use cached result
        return st.session_state.get(cache_key, ("untested", "Not yet tested"))

    # Run a real test
    try:
        adapter = get_db_adapter(db_name)
        if adapter is None:
            result = ("fail", "Database not found in settings")
        else:
            ok, msg = adapter.test_connection()
            result = ("pass", msg) if ok else ("fail", msg)
    except Exception as exc:
        # Never surface raw config; surface only a safe summary
        result = ("fail", f"Connection error: {type(exc).__name__}")

    st.session_state[cache_key] = result
    st.session_state[ts_key] = now
    return result


# ---------------------------------------------------------------------------
# Shared sidebar
# ---------------------------------------------------------------------------
def render_sidebar(settings: Settings) -> None:
    """Render the entrypoint-level sidebar widgets (D-03, D-05).

    Only top-level selectors belong here. Platform/parameter multiselects
    are rendered inside browse.py to avoid re-render on tab switch (Pitfall 7).
    """
    st.sidebar.title("PBM2")

    # --- DB selector ---
    if len(settings.databases) > 1:
        st.sidebar.selectbox(
            "Database",
            options=[d.name for d in settings.databases],
            key="active_db",
        )
    elif len(settings.databases) == 1:
        st.session_state["active_db"] = settings.databases[0].name
        st.sidebar.caption(f"DB: {settings.databases[0].name}")
    else:
        st.session_state["active_db"] = ""
        st.sidebar.warning("No database configured. Add one in Settings.")

    # --- Connection health indicator ---
    active_db: str = st.session_state.get("active_db", "")
    status, msg = _get_health(active_db)

    if status == "pass":
        dot_color = "#2ca02c"
    elif status == "fail":
        dot_color = "#d62728"
    else:
        dot_color = "#aaaaaa"

    # Escape user-editable db name — Settings YAML is writable by anyone with intranet
    # access and would otherwise execute <script> payloads injected as a db name.
    safe_label = html.escape(active_db) if active_db else "No DB"
    st.sidebar.markdown(
        f'<span style="color:{dot_color};">●</span> {safe_label}',
        unsafe_allow_html=True,
    )

    # --- LLM selector (active in Phase 2, NL-07) ---
    if settings.llms:
        llm_names = [ll.name for ll in settings.llms]
        # Default to the first Ollama entry (NL-10 default Ollama); fall back to index 0
        default_idx = next(
            (i for i, ll in enumerate(settings.llms) if ll.type == "ollama"), 0
        )
        st.sidebar.radio(
            "LLM Backend",
            options=llm_names,
            index=default_idx,
            key="active_llm",
        )
    else:
        if "active_llm" not in st.session_state:
            st.session_state["active_llm"] = ""

    # Divider — Browse page appends its own widgets below this line
    st.sidebar.divider()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    settings = load_settings()

    render_sidebar(settings)

    pg = st.navigation(
        [
            st.Page(
                "app/pages/browse.py",
                title="Browse",
                icon=":material/table_chart:",
                default=True,
            ),
            st.Page("app/pages/ask.py", title="Ask", icon=":material/chat:"),
            st.Page(
                "app/pages/settings.py",
                title="Settings",
                icon=":material/settings:",
            ),
        ]
    )
    pg.run()


if __name__ == "__main__":
    main()
else:
    # When Streamlit imports this module as a page, run main() automatically.
    main()
