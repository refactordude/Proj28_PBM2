"""Phase 6 codebase invariants — static-analysis grep guards.

Same idiom as test_phase04_invariants.py / test_phase05_invariants.py:
each test grep-asserts a contract over Phase 6 source files. Failures here
mean a future commit silently broke a locked Phase 6 decision.

Forbidden literals are constructed at runtime via string concatenation so
this test file's source does not contain the substring it scans for under
app_v2/ (eliminates self-match false-positive risk; same defense as Phase 4
and Phase 5 invariants).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ASK_ROUTER = REPO / "app_v2" / "routers" / "ask.py"
SETTINGS_ROUTER = REPO / "app_v2" / "routers" / "settings.py"
ASK_TEMPLATES_DIR = REPO / "app_v2" / "templates" / "ask"
APP_V2_ROOT = REPO / "app_v2"


# ---- INFRA-05 / Pitfall 1 — sync def routes only ------------------------

@pytest.mark.parametrize("router_path", [ASK_ROUTER, SETTINGS_ROUTER], ids=lambda p: p.name)
def test_no_async_def_in_phase6_router(router_path):
    """INFRA-05: every route function in ask.py + settings.py is `def`, never `async def`.

    `run_nl_query` calls `agent.run_sync()` internally (PydanticAI sync runner);
    invoking it inside `async def` would deadlock the uvicorn event loop
    (Pitfall 1).
    """
    src = router_path.read_text()
    forbidden = "async" + " " + "def"  # constructed at runtime — see test header
    matches = re.findall(r"^" + forbidden + r"\b", src, flags=re.MULTILINE)
    assert matches == [], f"{router_path.name} has async def routes; INFRA-05 + Pitfall 1 forbid this"


# ---- XSS defense — Jinja2 templates must not bypass autoescape ----------

@pytest.mark.parametrize(
    "template_name",
    ["index.html", "_starter_chips.html", "_confirm_panel.html", "_answer.html", "_abort_banner.html"],
)
def test_no_safe_filter_in_ask_templates(template_name):
    """No `| safe` filter in any Phase 6 Ask template (XSS defense).

    Agent-generated content (summary, sql, failure.detail) and user content
    (question, confirmed_params) flow through these templates. Any `| safe`
    on user/agent input is a guaranteed XSS vector.
    """
    template = ASK_TEMPLATES_DIR / template_name
    src = template.read_text()
    forbidden = "|" + " " + "safe"  # constructed at runtime
    assert forbidden not in src, f"ask/{template_name} contains '{forbidden}'; remove the filter"


# ---- D-08 — every fragment template carries id="answer-zone" ------------

@pytest.mark.parametrize(
    "template_name",
    ["_confirm_panel.html", "_answer.html", "_abort_banner.html"],
)
def test_fragment_outer_wrapper_has_answer_zone_id(template_name):
    """D-08: each #answer-zone-replacing fragment carries id="answer-zone" on its outer wrapper.

    Without this, hx-swap="outerHTML" would replace the fragment with a
    no-id <div>, and subsequent swaps would have no target.
    """
    template = ASK_TEMPLATES_DIR / template_name
    src = template.read_text()
    assert 'id="answer-zone"' in src, \
        f'ask/{template_name} missing id="answer-zone" on outer wrapper'


# ---- D-11 — no Regenerate button anywhere in ask/ -----------------------

def test_no_regenerate_button_in_ask_templates():
    """D-11: regeneration is via 'edit textarea + Run again', not a button.

    The original ASK-V2-03 spec had a Regenerate button; Phase 6 dropped it.
    """
    forbidden = "Regen" + "erate"  # constructed at runtime
    for template in ASK_TEMPLATES_DIR.glob("*.html"):
        src = template.read_text()
        assert forbidden not in src, \
            f"ask/{template.name} contains '{forbidden}' — D-11 forbids it"


# ---- D-18 — no OpenAI sensitivity-warning banner anywhere ---------------

def test_no_openai_sensitivity_banner_in_ask_templates():
    """D-18: no warning banner about sending data to OpenAI's servers.

    The original ASK-V2-05 spec had a dismissible alert banner; Phase 6
    dropped it. The visible LLM dropdown label is the affordance.
    """
    # The exact v1.0 copy, constructed at runtime
    forbidden = "send" + " UFS parameter data to " + "OpenAI"
    for template in ASK_TEMPLATES_DIR.glob("*.html"):
        src = template.read_text()
        assert forbidden not in src, \
            f"ask/{template.name} contains the OpenAI banner copy — D-18 forbids it"


# ---- ASK-V2-06 — every NL invocation goes through run_nl_query ----------

def test_ask_router_uses_nl_service_run_nl_query_only():
    """ASK-V2-06: the route layer must call `run_nl_query`, never `agent.run_sync` directly.

    Bypassing run_nl_query skips the post-agent SAFE-02 second pass +
    READ ONLY session + LIMIT re-injection. The harness MUST be the only
    path.

    The forbidden literal `agent.run_sync` is matched only as actual Python
    code (preceded by a non-backtick, non-whitespace token context). The
    module docstring mentions the term in backtick-quoted prose — that is
    an acceptable documentation reference, not a code call. We check for
    the code-call pattern: an identifier followed immediately by `.run_sync(`.
    """
    src = ASK_ROUTER.read_text()
    # Code-level call pattern: identifier.run_sync( — NOT preceded by backtick
    # The docstring wraps it as `agent.run_sync(...)` in backtick prose;
    # actual code would be: <identifier>.run_sync( without the backtick
    forbidden_code = re.compile(r"(?<!`)\bagent\." + "run_sync" + r"\s*\(")
    assert not forbidden_code.search(src), \
        "app_v2/routers/ask.py contains agent.run_sync() code call — ASK-V2-06 forbids bypassing nl_service"
    # Positive assertion: the run_nl_query import is at module level (D-19 mocking precondition)
    assert re.search(
        r"^from app\.core\.agent\.nl_service import .*run_nl_query", src, flags=re.MULTILINE
    ), "app_v2/routers/ask.py must import run_nl_query at module level (D-19)"


# ---- Banned libraries (CLAUDE.md 'What NOT to Use') --------------------

@pytest.mark.parametrize(
    "library",
    ["langchain", "litellm", "vanna", "llama_index"],
)
def test_no_banned_libraries_imported_in_phase6(library):
    """CLAUDE.md: never import langchain / litellm / vanna / llama_index.

    Same audit as Phase 3 invariants — extended to Phase 6 files.
    """
    pat = re.compile(r"^\s*(import|from)\s+" + library + r"\b", flags=re.MULTILINE)
    targets = [
        ASK_ROUTER,
        SETTINGS_ROUTER,
        APP_V2_ROOT / "services" / "starter_prompts.py",
    ]
    for target in targets:
        if not target.exists():
            continue
        src = target.read_text()
        assert not pat.search(src), \
            f"{target} imports banned library {library!r}"


# ---- D-14 — cookie attrs (no Secure) -----------------------------------

def test_settings_router_cookie_attrs_match_d14():
    """D-14: pbm2_llm cookie set with Path=/, SameSite=Lax, Max-Age=31536000,
    HttpOnly=True; NO Secure (intranet HTTP — Pitfall 8)."""
    src = SETTINGS_ROUTER.read_text()
    assert 'key="pbm2_llm"' in src
    assert "max_age=31536000" in src
    assert 'path="/"' in src
    assert 'samesite="lax"' in src
    assert "httponly=True" in src
    # Secure MUST be explicitly False (Pitfall 8) — search for the literal
    assert "secure=False" in src
    # No accidental secure=True
    assert "secure=True" not in src


# ---- D-22 readiness — v1.0 Streamlit Ask still present at this stage ----

def test_v1_streamlit_ask_deleted_per_d22():
    """D-22: the v1.0 Streamlit Ask UI was hard-deleted in Plan 06-06.

    Polarity-flipped from `test_v1_streamlit_ask_still_present_pre_06_06_deletion`
    (Plan 06-05 placeholder). After Plan 06-06, the v1.0 Ask page MUST NOT
    exist on disk; v2.0 owns the Ask URL outright.

    Files that MUST stay (D-22 #5 — framework-agnostic v2.0 consumers):
      - app/core/agent/nl_service.py
      - app/core/agent/nl_agent.py
      - app/adapters/llm/pydantic_model.py
    These are positively asserted to ensure deletion didn't overreach.
    """
    v1_ask = REPO / "app" / "pages" / "ask.py"
    assert not v1_ask.exists(), "D-22: app/pages/ask.py must be deleted in Plan 06-06"

    v1_test = REPO / "tests" / "pages" / "test_ask_page.py"
    assert not v1_test.exists(), "D-22: tests/pages/test_ask_page.py must be deleted"

    # streamlit_app.py was deleted in quick task 260429-kn7 (v1.0 sunset)
    assert not (REPO / "streamlit_app.py").exists(), \
        "streamlit_app.py must not exist after v1.0 Streamlit sunset (quick task 260429-kn7)"

    # D-22 #5 — framework-agnostic preserves
    nl_service = REPO / "app" / "core" / "agent" / "nl_service.py"
    nl_agent = REPO / "app" / "core" / "agent" / "nl_agent.py"
    pydantic_model = REPO / "app" / "adapters" / "llm" / "pydantic_model.py"
    assert nl_service.exists(), "D-22 #5: nl_service.py MUST be preserved (v2.0 consumer)"
    assert nl_agent.exists(), "D-22 #5: nl_agent.py MUST be preserved (v2.0 consumer)"
    assert pydantic_model.exists(), "D-22 #5: pydantic_model.py MUST be preserved (v2.0 consumer)"
