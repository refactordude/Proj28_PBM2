"""Phase 03 codebase invariants — regression guards on locked decisions.

These tests grep the source for forbidden patterns and assert their absence.
They are NOT functional tests; they are policy enforcement.

Each test maps to a specific D-number or pitfall it guards:

- INFRA-05: no async def in DB-touching / Phase 03 routes (extended to all
  Phase 03 routers; sync def + threadpool dispatch is the pinned model).
- Pitfall 1: ``MarkdownIt('js-default')`` ONLY — never the default constructor
  (which would enable raw HTML passthrough → XSS).
- UI-SPEC summary-error contract: summary route MUST always return 200 (the
  amber-warning fragment swaps inline; a 5xx would escalate to the global
  ``#htmx-error-container``).
- CLAUDE.md: no langchain / litellm / vanna / llama_index imports anywhere
  in app_v2/ (openai SDK with ``base_url`` is the dual-backend abstraction).
- D-21 + SUMMARY-04: single-shot only (``stream=False``).
- D-17: ``TTLCache(maxsize=128, ttl=3600)`` verbatim.
- Pitfall 13: cache key uses ``mtime_ns`` (integer ns), not float ``st_mtime``.
- D-30: ``atomic_write_bytes`` is the single shared helper — defined in
  ``app_v2/data/atomic_write.py`` and consumed via import by both
  ``overview_store`` and ``content_store``.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_V2_ROOT = REPO_ROOT / "app_v2"


def _read(*parts: str) -> str:
    return (APP_V2_ROOT.joinpath(*parts)).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# INFRA-05: no async def in routers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "router_file",
    [
        "routers/platforms.py",
        "routers/summary.py",
    ],
)
def test_no_async_def_in_phase03_routers(router_file):
    """INFRA-05: every Phase 03 route MUST be ``def`` (sync), dispatched to threadpool."""
    src = _read(router_file)
    # Match `async def` at start of line (allowing leading whitespace) — this
    # finds function declarations only. Decorator ``@…`` lines never start with
    # ``async``; module docstrings that use the phrase ``async def`` would
    # trigger a false positive in theory, but the Phase 03 routers do not.
    offending = [
        line.rstrip()
        for line in src.splitlines()
        if re.match(r"^\s*async\s+def\s+", line)
    ]
    assert offending == [], (
        f"INFRA-05 violation in {router_file}: async def is forbidden in "
        f"Phase 03 routes.\nOffending lines: {offending}"
    )


# ---------------------------------------------------------------------------
# Pitfall 1: MarkdownIt('js-default') ONLY
# ---------------------------------------------------------------------------

def test_no_default_markdownit_constructor_in_app_v2():
    """Pitfall 1: ``MarkdownIt()`` default constructor is XSS-unsafe (html=True).

    Search ALL .py files under app_v2/ for ``MarkdownIt(`` and assert each call
    site uses ``'js-default'`` as the first arg.
    """
    violations = []
    for path in APP_V2_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            m = re.search(r"MarkdownIt\s*\(([^)]*)", line)
            if not m:
                continue
            args = m.group(1).strip()
            # Allowed forms: MarkdownIt("js-default") or MarkdownIt('js-default').
            if not (
                args.startswith('"js-default"') or args.startswith("'js-default'")
            ):
                violations.append(
                    f"{path.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}"
                )
    assert violations == [], (
        "Pitfall 1: MarkdownIt() default constructor is XSS-unsafe.\n"
        "Use MarkdownIt('js-default') instead. Violations:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# UI-SPEC: summary route never 5xx
# ---------------------------------------------------------------------------

def test_summary_route_never_returns_5xx():
    """UI-SPEC 'Note on summary error response': always 200 with error fragment."""
    src = _read("routers/summary.py")
    # Forbid status_code=5xx and any explicit HTTPException raise. The
    # docstring uses the phrase "NEVER raises HTTPException" (no literal
    # ``raise HTTPException`` token), so the strict regex below will not
    # false-positive.
    if re.search(r"status_code\s*=\s*5\d\d", src):
        pytest.fail(
            "summary route MUST NOT set 5xx status (UI-SPEC contract)"
        )
    if re.search(r"\braise\s+HTTPException\b", src):
        pytest.fail(
            "summary route MUST NOT raise HTTPException (returns error "
            "fragment instead)"
        )


# ---------------------------------------------------------------------------
# CLAUDE.md: no banned libraries
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("banned", ["langchain", "litellm", "vanna", "llama_index"])
def test_no_banned_libraries_imported_in_app_v2(banned):
    """CLAUDE.md: only openai SDK with ``base_url`` for both backends.

    No LangChain / litellm / Vanna / LlamaIndex — these libraries were
    explicitly rejected in the technology stack research (CLAUDE.md "What NOT
    to Use" table).
    """
    violations = []
    for path in APP_V2_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            # Match ``import X``, ``from X``, ``from X.y`` — at line start
            # (allowing indent). String / comment occurrences are excluded
            # because the pattern anchors to ``^\s*(import|from)``.
            if re.search(rf"^\s*(import|from)\s+{re.escape(banned)}\b", line):
                violations.append(
                    f"{path.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}"
                )
    assert violations == [], (
        f"CLAUDE.md violation: '{banned}' import found in app_v2/. "
        f"Use openai SDK with base_url instead. Violations:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# D-21: single-shot only (stream=False)
# ---------------------------------------------------------------------------

def test_summary_service_uses_stream_false():
    """D-21 + SUMMARY-04: summary call is single-shot (``stream=False``)."""
    src = _read("services/summary_service.py")
    assert "stream=False" in src, (
        "D-21: summary_service must call chat.completions.create with stream=False"
    )
    assert "stream=True" not in src, (
        "D-21: streaming is out of scope for Phase 03"
    )


# ---------------------------------------------------------------------------
# D-17: TTLCache(maxsize=128, ttl=3600) verbatim
# ---------------------------------------------------------------------------

def test_summary_ttlcache_uses_locked_dimensions():
    """D-17 verbatim: ``TTLCache(maxsize=128, ttl=3600)``.

    Sharper sizes need a CONTEXT.md update first — this guard makes silent
    drift impossible.
    """
    src = _read("services/summary_service.py")
    assert "TTLCache(maxsize=128, ttl=3600)" in src, (
        "D-17 specifies TTLCache(maxsize=128, ttl=3600) verbatim. "
        "If you need different dimensions, update 03-CONTEXT.md first."
    )


# ---------------------------------------------------------------------------
# Pitfall 13: cache key uses mtime_ns (int) not st_mtime (float)
# ---------------------------------------------------------------------------

def test_summary_cache_key_uses_mtime_ns():
    """Pitfall 13: integer-nanosecond mtime sharpens key vs float-seconds st_mtime."""
    src = _read("services/summary_service.py")
    assert "mtime_ns" in src, (
        "Pitfall 13: cache key must include st_mtime_ns (integer ns) for "
        "sub-second precision"
    )


# ---------------------------------------------------------------------------
# D-30: atomic_write_bytes is the single shared helper
# ---------------------------------------------------------------------------

def test_atomic_write_bytes_is_single_source_of_truth():
    """D-30: only ONE definition of ``atomic_write_bytes`` in the codebase.

    The helper lives in ``app_v2/data/atomic_write.py``; both
    ``overview_store`` and ``content_store`` import it (no copy-paste).
    """
    defs = []
    for path in APP_V2_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"^def\s+atomic_write_bytes\s*\(", text, re.MULTILINE):
            defs.append(str(path.relative_to(REPO_ROOT)))
    assert defs == ["app_v2/data/atomic_write.py"], (
        f"atomic_write_bytes must be defined ONLY in "
        f"app_v2/data/atomic_write.py; found in: {defs}"
    )

    # Also assert overview_store and content_store IMPORT it (don't reimplement).
    overview_src = _read("services/overview_store.py")
    content_src = _read("services/content_store.py")
    assert (
        "from app_v2.data.atomic_write import atomic_write_bytes" in overview_src
    ), (
        "overview_store must import atomic_write_bytes "
        "(D-30 single source of truth)"
    )
    assert (
        "from app_v2.data.atomic_write import atomic_write_bytes" in content_src
    ), (
        "content_store must import atomic_write_bytes "
        "(D-30 single source of truth)"
    )
