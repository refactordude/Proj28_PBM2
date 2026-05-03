"""Phase 3 invariants — replace narrowed Phase 6 invariants for the chat surface.

Each test maps to a specific D-CHAT-* decision it guards:

  - test_ask_router_async_def_only_on_streaming_routes  — D-CHAT-08 + RESEARCH Pitfall 1
  - test_nl05_templates_deleted                         — D-CHAT-09 atomic deletion
  - test_starter_chips_not_included_in_index            — D-CHAT-10 starter-chips removal
  - test_llm_dropdown_preserved_in_index                — D-CHAT-11 LLM-dropdown preservation
  - test_no_safe_filter_on_agent_strings_in_chat_partials — XSS regression (T-03-04-04)
  - test_final_card_safe_filter_only_on_router_rendered_html — narrowed | safe whitelist
  - test_plotly_only_loaded_on_ask_page                 — T-03-04-07 / RESEARCH Pitfall 5
  - test_no_banned_libraries_imported_in_chat_modules   — CLAUDE.md banned libs guard
  - test_chat_loop_emits_all_8_d_chat_04_reasons        — D-CHAT-04 vocabulary

Phase 6 invariants superseded by this file (deleted atomically in plan 03-04
Task 1 per D-CHAT-09 — see deferred-items.md):

  - test_no_async_def_in_phase6_router       → narrowed: async OK on streaming routes
  - test_no_safe_filter_in_ask_templates     → updated parametrize list (new partials)
  - test_fragment_outer_wrapper_has_answer_zone_id → obsolete (no #answer-zone in Phase 3)
  - test_ask_router_uses_nl_service_run_nl_query_only → obsolete (chat_agent direct)
  - test_no_banned_libraries_imported_in_phase6 → broadened to chat module set

Decision traceability: RESEARCH Gap 13 — Phase 6 invariants superseded by Phase 3
narrowed equivalents. D-CHAT-09 atomic-cleanup contract — file removal happened
atomically with template + route deletion in plan 03-04 Task 1.
"""
from __future__ import annotations

import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


# -----------------------------------------------------------------------
# D-CHAT-08 — async def narrowing in app_v2/routers/ask.py
# -----------------------------------------------------------------------


def test_ask_router_async_def_only_on_streaming_routes():
    """Phase 3 narrows the Phase 6 sync-only rule (RESEARCH Pitfall 1):

    - /ask/stream/{turn_id} MUST be async def (SSE generator).
    - /ask/cancel/{turn_id} MAY be async def (no run_sync inside).
    - GET /ask + POST /ask/chat are sync def (no streaming).
    - run_sync MUST NOT be called anywhere in this file (forbids any
      synchronous PydanticAI runner call that would bypass the streaming
      harness — D-CHAT-03 / D-CHAT-04 stop-boundary classification depends
      on the streaming path).
    """
    src = (REPO / "app_v2" / "routers" / "ask.py").read_text()
    forbidden_run_sync = re.compile(r"\b\w+\.run_sync\s*\(")
    assert not forbidden_run_sync.search(src), (
        "ask.py contains agent.run_sync() — Phase 3 forbids bypassing the streaming harness"
    )
    assert "async def ask_stream" in src, "Phase 3 requires async def for /ask/stream"


# -----------------------------------------------------------------------
# D-CHAT-09 — NL-05 confirmation templates deleted atomically
# -----------------------------------------------------------------------


def test_nl05_templates_deleted():
    """D-CHAT-09 atomic deletion of the 3 NL-05 confirmation templates."""
    for name in ("_confirm_panel.html", "_abort_banner.html", "_answer.html"):
        path = REPO / "app_v2" / "templates" / "ask" / name
        assert not path.exists(), (
            f"{name} should have been deleted in Phase 3 (D-CHAT-09)"
        )


# -----------------------------------------------------------------------
# D-CHAT-10 — starter chips removed from the chat shell
# -----------------------------------------------------------------------


def test_starter_chips_not_included_in_index():
    """D-CHAT-10 — starter chips include is removed from the rewritten index.html."""
    src = (REPO / "app_v2" / "templates" / "ask" / "index.html").read_text()
    assert "_starter_chips.html" not in src, (
        "templates/ask/index.html still includes _starter_chips.html — D-CHAT-10 violated"
    )


# -----------------------------------------------------------------------
# D-CHAT-11 — LLM dropdown HTML carries verbatim from Phase 6
# -----------------------------------------------------------------------


def test_llm_dropdown_preserved_in_index():
    """D-CHAT-11 — LLM dropdown HTML carries verbatim from Phase 6.

    Trigger label, dropdown class, hx-post target — all unchanged.
    """
    src = (REPO / "app_v2" / "templates" / "ask" / "index.html").read_text()
    assert "LLM:" in src
    assert 'class="dropdown ms-auto"' in src
    assert 'hx-post="/settings/llm"' in src


# -----------------------------------------------------------------------
# T-03-04-04 — no | safe filter on agent-supplied strings in chat partials
# -----------------------------------------------------------------------


def test_no_safe_filter_on_agent_strings_in_chat_partials():
    """Phase 6 ``test_no_safe_filter_in_ask_templates`` updated to the new partial set.

    Every agent-supplied template variable in these partials uses Jinja's
    autoescape (| e). The | safe filter is forbidden because the variables
    are agent-supplied strings (XSS risk).

    Strips Jinja comments (``{# ... #}``) before checking — comment text
    like "NO | safe" inside an explanatory header is not a real filter
    usage and must not trigger the rule.

    _final_card.html is checked separately by
    ``test_final_card_safe_filter_only_on_router_rendered_html`` — its
    | safe usage is whitelisted to ``table_html`` and ``chart_html``
    (router-pre-rendered markup).
    """
    forbidden_partials = [
        "_thought_event.html",
        "_tool_call_pill.html",
        "_tool_result_pill.html",
        "_error_card.html",
        "_input_zone.html",
        "_user_message.html",
    ]
    needle = "| " + "safe"  # split to avoid self-match in this test file
    # Strip Jinja {# … #} comments so explanatory header copy "NO | safe" does
    # not false-trigger. Multi-line comments are common in these files.
    comment_re = re.compile(r"\{#.*?#\}", re.DOTALL)
    for partial in forbidden_partials:
        path = REPO / "app_v2" / "templates" / "ask" / partial
        assert path.exists(), f"{partial} missing on disk"
        src = path.read_text()
        stripped = comment_re.sub("", src)
        assert needle not in stripped, (
            f"{partial} uses `{needle}` filter outside a Jinja comment "
            f"— agent-supplied strings must use autoescape"
        )


def test_final_card_safe_filter_only_on_router_rendered_html():
    """_final_card.html may use ``| safe`` ONLY on ``table_html`` / ``chart_html``.

    Both variables are router-pre-rendered (Browse macro / Plotly figure HTML)
    so the autoescape exemption is intentional and limited.
    """
    src = (REPO / "app_v2" / "templates" / "ask" / "_final_card.html").read_text()
    needle = "| " + "safe"  # split to avoid self-match in this test file
    safe_lines = [ln for ln in src.split("\n") if needle in ln]
    assert safe_lines, (
        "_final_card.html should use | safe on table_html / chart_html — none found"
    )
    for ln in safe_lines:
        assert ("table_html" in ln) or ("chart_html" in ln), (
            f"_final_card.html line '{ln.strip()}' uses | safe on a non-whitelisted variable"
        )


# -----------------------------------------------------------------------
# T-03-04-07 — Plotly bundle only loaded on /ask page
# -----------------------------------------------------------------------


def test_plotly_only_loaded_on_ask_page():
    """T-03-04-07 — Plotly bundle loads only on /ask page (RESEARCH Pitfall 5).

    Browse / Joint Validation / Settings inherit base.html with empty
    extra_head — they MUST NOT reference plotly.min.js anywhere.
    """
    ask_index = (REPO / "app_v2" / "templates" / "ask" / "index.html").read_text()
    assert "vendor/plotly/plotly.min.js" in ask_index, (
        "ask/index.html should load the vendored Plotly bundle in extra_head"
    )
    other_pages = (
        "browse/index.html",
        "joint_validation/index.html",
        "joint_validation/detail.html",
        "settings/index.html",
        "base.html",
    )
    for page in other_pages:
        path = REPO / "app_v2" / "templates" / page
        if path.exists():
            assert "plotly.min.js" not in path.read_text(), (
                f"{page} imports Plotly — Phase 3 limits Plotly to /ask only"
            )


# -----------------------------------------------------------------------
# htmx-ext-sse must load AFTER htmx core (defer-order bug — see commit
# fixing /ask/stream never being opened by the browser)
# -----------------------------------------------------------------------


def test_htmx_ext_sse_loads_after_htmx_core_in_rendered_ask_page():
    """htmx-ext-sse.js MUST load AFTER htmx.min.js on the /ask page.

    Both are loaded with ``defer``, which means scripts execute in document
    order at parse time. If htmx-ext-sse runs before htmx core, the
    extension's ``htmx.defineExtension('sse', ...)`` call hits an undefined
    ``htmx`` global, registration fails silently, and every fragment with
    ``hx-ext="sse"`` swapped in afterwards is ignored — the browser never
    opens the EventSource against ``/ask/stream/{turn_id}`` so the chat
    appears completely dead even though the server-side POST /ask/chat
    succeeded.

    This test asserts the document order of the two ``<script src=...>``
    tags. It does NOT spin up a browser — the order alone is sufficient
    given both tags use the ``defer`` attribute.
    """
    from fastapi.testclient import TestClient

    from app_v2.main import app

    with TestClient(app) as client:
        html = client.get("/ask").text

    pattern = re.compile(
        r'<script\s+src="[^"]*vendor/htmx/(htmx-ext-sse|htmx)\.(?:min\.)?js"',
    )
    order = [m.group(1) for m in pattern.finditer(html)]
    assert "htmx" in order, "htmx.min.js should be referenced on /ask"
    assert "htmx-ext-sse" in order, "htmx-ext-sse.js should be referenced on /ask"
    assert order.index("htmx") < order.index("htmx-ext-sse"), (
        "htmx-ext-sse.js must load AFTER htmx.min.js on /ask — "
        "defer-order means an earlier script executes first; the extension "
        "needs htmx defined before its registration runs. Use the "
        "{% block scripts %} slot in base.html, not {% block extra_head %}."
    )


# -----------------------------------------------------------------------
# CLAUDE.md banned libs — chat module guard
# -----------------------------------------------------------------------


def test_no_banned_libraries_imported_in_chat_modules():
    """CLAUDE.md banned libs (langchain, litellm, vanna, llama_index).

    Broadens the Phase 6 ``test_no_banned_libraries_imported_in_phase6`` rule
    to the 4 new chat module paths (router + 3 agent modules).
    """
    chat_files = [
        REPO / "app_v2" / "routers" / "ask.py",
        REPO / "app" / "core" / "agent" / "chat_agent.py",
        REPO / "app" / "core" / "agent" / "chat_loop.py",
        REPO / "app" / "core" / "agent" / "chat_session.py",
    ]
    banned = ("langchain", "litellm", "vanna", "llama_index")
    for path in chat_files:
        assert path.exists(), f"chat module missing: {path}"
        src = path.read_text()
        for lib in banned:
            assert f"import {lib}" not in src, f"{path.name} imports banned {lib}"
            assert f"from {lib}" not in src, f"{path.name} imports from banned {lib}"


# -----------------------------------------------------------------------
# D-CHAT-04 — error reason vocabulary is exhaustive
# -----------------------------------------------------------------------


def test_chat_loop_emits_all_8_d_chat_04_reasons():
    """D-CHAT-04 — every error reason must be representable in chat_loop.

    The 8 reasons partition into HARD_REASONS (5) and SOFT_REASONS (3) with
    no overlap; every reason has body copy in _ERROR_BODY_BY_REASON.
    """
    from app.core.agent.chat_loop import (
        _ERROR_BODY_BY_REASON,
        HARD_REASONS,
        SOFT_REASONS,
    )

    expected = {
        "llm-error",
        "still-rejected-after-5-attempts",
        "stream-dropped",
        "agent-no-final-result",
        "unconfigured",
        "timeout",
        "step-budget-exhausted",
        "stopped-by-user",
    }
    assert expected <= set(_ERROR_BODY_BY_REASON.keys()), (
        "_ERROR_BODY_BY_REASON missing one or more D-CHAT-04 reasons"
    )
    assert HARD_REASONS | SOFT_REASONS == expected, (
        "HARD_REASONS | SOFT_REASONS must equal the full 8-reason set"
    )
    assert HARD_REASONS & SOFT_REASONS == set(), (
        "no D-CHAT-04 reason may appear in both HARD and SOFT partitions"
    )


# -----------------------------------------------------------------------
# D-CHAT-09 — Phase 6 invariants test file has been atomically deleted
# -----------------------------------------------------------------------


def test_phase06_invariants_file_remains_deleted():
    """D-CHAT-09 atomic-cleanup contract.

    ``tests/v2/test_phase06_invariants.py`` was deleted in plan 03-04 Task 1
    alongside the 3 NL-05 templates. This invariant guards against
    accidental re-creation by a future plan or quick task.
    """
    path = REPO / "tests" / "v2" / "test_phase06_invariants.py"
    assert not path.exists(), (
        "tests/v2/test_phase06_invariants.py was atomically deleted in plan 03-04 "
        "(D-CHAT-09); its assertions are superseded by this file."
    )
