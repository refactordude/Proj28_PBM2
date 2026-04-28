---
phase: 06-ask-tab-port
reviewed: 2026-04-29T00:00:00Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - app_v2/main.py
  - app_v2/routers/ask.py
  - app_v2/routers/overview.py
  - app_v2/routers/platforms.py
  - app_v2/routers/root.py
  - app_v2/routers/settings.py
  - app_v2/routers/summary.py
  - app_v2/services/llm_resolver.py
  - app_v2/services/starter_prompts.py
  - app_v2/static/css/app.css
  - app_v2/templates/ask/_abort_banner.html
  - app_v2/templates/ask/_answer.html
  - app_v2/templates/ask/_confirm_panel.html
  - app_v2/templates/ask/_starter_chips.html
  - app_v2/templates/ask/index.html
  - app_v2/templates/browse/_picker_popover.html
  - streamlit_app.py
  - tests/v2/test_ask_routes.py
  - tests/v2/test_llm_resolver.py
  - tests/v2/test_main.py
  - tests/v2/test_phase04_invariants.py
  - tests/v2/test_phase06_invariants.py
  - tests/v2/test_settings_routes.py
findings:
  critical: 0
  warning: 2
  info: 5
  total: 7
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-04-29
**Depth:** standard
**Files Reviewed:** 23
**Status:** issues_found

## Summary

Phase 6 ports the v1.0 Streamlit Ask page to FastAPI/HTMX/Bootstrap with high
fidelity to the locked decisions. The ten focus areas all pass:

- All Ask + Settings routes are sync `def` (verified by `test_phase06_invariants.test_no_async_def_in_phase6_router` and inspection of every `@router.<verb>` decorator). `agent.run_sync()` will not block the event loop.
- Cookie attributes for `pbm2_llm` are correct: `Path=/`, `SameSite=Lax`, `HttpOnly=True`, `Max-Age=31536000`, no `Secure` flag (intranet HTTP). Validation against `settings.llms[].name` happens **before** `set_cookie`; invalid input silently falls back to `settings.app.default_llm` per D-15.
- `_confirm_panel.html`, `_answer.html`, and `_abort_banner.html` each carry `id="answer-zone"` on the outermost wrapper; `_starter_chips.html` correctly does NOT (chips live outside the swap region by design).
- All dynamic outputs in Ask templates use Jinja2 explicit-escape (`| e`) or `| tojson` for the chip-fill JS string. No `| safe` filter anywhere in `templates/ask/`. Starlette's `Jinja2Templates` defaults `autoescape=select_autoescape()` so `.html` files autoescape implicitly; the explicit filters are belt-and-suspenders.
- `run_nl_query` is imported at module level in `ask.py` (line 32), enabling `mocker.patch("app_v2.routers.ask.run_nl_query")` per D-19. `test_post_ask_query_*` tests confirm the patch works.
- `_run_second_turn` (line 281) detects a second-turn `ClarificationNeeded` and synthesizes a failure NLResult with reason `"llm-error"` instead of re-rendering the picker — D-10 / Pitfall 6 satisfied. `test_post_ask_confirm_second_turn_clarification_is_suppressed` covers this.
- `_df_to_template_ctx` (line 74) converts the NLResult DataFrame to plain Python `columns: list[str]` + `rows: list[list]` before reaching Jinja — Pitfall 2 satisfied.
- `_confirm_panel.html` invokes `picker_popover(..., disable_auto_commit=True)` (line 60) and the macro suppresses `hx-post`/`hx-target`/`hx-swap`/`hx-include`/`hx-trigger` on the `<ul>` when this kwarg is truthy (lines 82-87 in `_picker_popover.html`).
- No banned imports detected: `langchain`, `litellm`, `vanna`, `llama_index`, `streamlit-aggrid`, `plotly`, `openpyxl`, `csv` — none appear under `app_v2/` (the existing Phase 04/05 invariants and the new `test_no_banned_libraries_imported_in_phase6` cover this).
- v1.0 Ask page artifacts are deleted: `app/pages/ask.py` and `tests/pages/test_ask_page.py` no longer exist on disk; `streamlit_app.py` does not reference them; `app/core/agent/nl_service.py`, `nl_agent.py`, and `app/adapters/llm/pydantic_model.py` are preserved per D-22 #5.
- Verbatim copy port verified: textarea placeholder `"e.g. What is the WriteProt status for all LUNs on platform X?"` (index.html:91), step-cap copy `"reached the 5-step limit"` and `"more specific parameters"` (_abort_banner.html:36), timeout copy `"timed out after 30 seconds"` and `"more targeted question or switch to a faster model"` (_abort_banner.html:38), `"Generated SQL"` (_answer.html:73), `"Partial output"` (_abort_banner.html:48), `"Try asking..."` (_starter_chips.html:19), `"Parameters to include"` (_confirm_panel.html:47), `"Run Query ▸"` (_confirm_panel.html:72), and `"{N} rows returned."` (_answer.html:59).

The two warnings below are UX/copy quality concerns surfaced by the unconfigured-LLM path and the second-turn loop-prevention path; both are non-blocking but worth a fix-forward. Five info-level items capture style nits, brittle coupling, and a benign threadpool race.

## Warnings

### WR-01: Unconfigured-LLM error message is awkwardly wrapped by the generic abort-banner template

**File:** `app_v2/routers/ask.py:182-193` (and template `app_v2/templates/ask/_abort_banner.html:33-42`)

**Issue:** `_render_unconfigured` builds an `_abort_banner.html` context with `reason="llm-error"` and `detail="No LLM backend configured — set one in Settings."` Because the template only special-cases `reason in {"step-cap", "timeout"}`, every other reason falls through to:

```
Something went wrong. (No LLM backend configured — set one in Settings.) Try rephrasing your question.
```

This concatenates an actionable config message with two unrelated sentences ("Something went wrong"; "Try rephrasing your question"), telling the user to rephrase a question that has nothing to do with the underlying problem (no LLM configured). The user-facing UX is misleading.

**Fix:** Either add a fourth `reason` branch in `_abort_banner.html`, or short-circuit to a dedicated template / inline alert:

```python
def _render_unconfigured(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "ask/_abort_banner.html",
        {
            "reason": "unconfigured",  # add a 4th branch in the template
            "last_sql": "",
            "detail": "",
        },
        status_code=200,
    )
```

```jinja
{# _abort_banner.html — add before the {% else %} #}
{% elif reason == "unconfigured" %}
  No LLM backend configured. Open Settings and select a backend, then try again.
{% else %}
  ...
```

Alternatively, reuse the summary-route pattern (`summary/_error.html` carries a single `reason` string rendered as-is) — that template avoids the awkward "Something went wrong. (...) Try rephrasing" wrapper.

### WR-02: Second-turn ClarificationNeeded suppression yields generic "Something went wrong" copy with no recovery hint

**File:** `app_v2/routers/ask.py:300-313`

**Issue:** When the agent ignores the loop-prevention instruction and returns `ClarificationNeeded` a second time, `_run_second_turn` synthesizes a failure with `reason="llm-error"` and `detail="Agent requested clarification a second time; aborting to prevent loop."` The generic abort-banner copy then renders:

```
Something went wrong. (Agent requested clarification a second time; aborting to prevent loop.) Try rephrasing your question.
```

The user is told to "rephrase" but the system has just dropped their confirmed parameter selections. Without an explicit hint that the textarea is now the recovery path AND that their picker selections were discarded, the user may think their click did nothing. The test (`test_post_ask_confirm_second_turn_clarification_is_suppressed`) only asserts the abort banner appears — it does not verify the copy clearly explains what to do next.

**Fix:** Either add a dedicated `reason="loop-aborted"` branch in `_abort_banner.html` with copy like:

```
The model could not narrow your question even with explicit parameters. Edit the question above to be more specific (mention platform IDs, parameter names, or a specific value range) and try again.
```

…or change the synthesized `detail` so the leak-through into the generic branch reads more usefully on its own. The current `detail` reads more like an internal log line than a user message.

## Info

### IN-01: Local re-import of `AgentRunFailure` inside `_run_second_turn` is inconsistent

**File:** `app_v2/routers/ask.py:303`

**Issue:** The function does `from app.core.agent.nl_agent import AgentRunFailure` as a local import with comment `# local import — no top-level couple`. But `AgentDeps` from the same module is already imported at the top of the file (line 31), so the "no top-level couple" rationale does not hold — there is already a top-level coupling to `nl_agent`. The local import adds a minor function-call overhead per second-turn ClarificationNeeded path and inconsistency for future readers.

**Fix:**
```python
# At top of file, alongside line 31:
from app.core.agent.nl_agent import AgentDeps, AgentRunFailure, build_agent

# Remove the local import on line 303.
```

### IN-02: Composed second-turn message uses Python list `repr()` (brittle coupling)

**File:** `app_v2/routers/ask.py:155`

**Issue:** The composed prompt does `f"User-confirmed parameters: {confirmed_params}\n\n"`. Python f-strings with a list use `repr()`, which produces `['UFS · LUNCount']`. The agent must parse this Python literal. If a future refactor changes `confirmed_params` to a tuple, set, or frozenset, the rendered representation changes (`('UFS · LUNCount',)`, `{'UFS · LUNCount'}`) and the agent's prompt-time interpretation may shift. The matching test (`test_post_ask_confirm_composes_loop_prevention_message`) asserts on the literal `"User-confirmed parameters: ['UFS · LUNCount']"` so the format is locked at test level — but the test won't catch a tuple/set substitution.

**Fix:** Use an explicit serialization to make the contract intentional:

```python
import json

confirmed_repr = json.dumps(list(confirmed_params))  # always JSON-array format
composed = (
    f"User-confirmed parameters: {confirmed_repr}\n\n"
    f"Original question: {original_question}\n\n"
    "Use ONLY the confirmed parameters above. "
    "If the list is empty, use your best judgment from the original question "
    "and do not return ClarificationNeeded again."
)
```

JSON-array form is also more familiar to LLMs as a structured-data representation.

### IN-03: `_get_agent` mutates `app.state.agent_registry` without a lock (benign threadpool race)

**File:** `app_v2/routers/ask.py:50-71`

**Issue:** FastAPI dispatches sync `def` routes to a threadpool, so two concurrent requests for the same `llm_name` can both pass the `if llm_name in registry` guard, both run `build_pydantic_model` + `build_agent`, and both write to `registry[llm_name]`. The race is benign — the build is idempotent and the second write just overwrites the first — but it does mean an extra LLM client may be constructed under load. For a low-concurrency intranet tool this is acceptable. Documenting it (or guarding with `threading.Lock`) makes the assumption auditable.

**Fix (optional, low priority):**
```python
import threading

_registry_lock = threading.Lock()

def _get_agent(request: Request, llm_name: str):
    if not llm_name:
        return None
    registry = getattr(request.app.state, "agent_registry", None)
    if registry is None:
        return None
    if llm_name in registry:
        return registry[llm_name]
    with _registry_lock:
        if llm_name in registry:  # double-checked locking
            return registry[llm_name]
        settings = getattr(request.app.state, "settings", None)
        cfg = find_llm(settings, llm_name) if settings is not None else None
        if cfg is None:
            return None
        agent = build_agent(build_pydantic_model(cfg))
        registry[llm_name] = agent
        return agent
```

Or simply add a comment to `_get_agent` stating that the duplicate-build race is acceptable and why.

### IN-04: `valid_names` set in `set_llm` may include `None` if any LLMConfig lacks `name`

**File:** `app_v2/routers/settings.py:52`

**Issue:** `valid_names = {getattr(l, "name", None) for l in llms}`. If any `LLMConfig` is malformed and missing `name`, the set contains `None`. A request with an empty form value (`name=""`) wouldn't match because `""` is not `None`, so it is fine in practice. But more importantly: if a tampered cookie or form value sent literally the string `"None"`, it still wouldn't match — correct behavior. This is purely a code-cleanliness concern.

**Fix:**
```python
valid_names = {n for n in (getattr(l, "name", None) for l in llms) if n}
```

This drops `None` and empty strings from the set, making the equality check intent explicit.

### IN-05: `confirmed_params: list[str] = []` mutable default in `ask_confirm`

**File:** `app_v2/routers/ask.py:138`

**Issue:** Standard Python style would flag `= []` as a mutable default argument. The project's established v2.0 idiom (see `app_v2/routers/overview.py:309-314` and the comment at lines 191-193) intentionally uses `= []` for FastAPI `Form()` parameters because FastAPI special-cases `Form` to evaluate defaults per-request rather than reusing the same list object. So this is NOT a real bug — but it is a divergence from PEP 8 / Pyflakes / Ruff B006 expectations that future readers may flag.

**Fix (optional, project-preference dependent):** Either add `# noqa: B006` annotations on the affected lines or document the project pattern in `CLAUDE.md` `## Conventions`. Current behavior is correct; the concern is purely lint-level.

---

_Reviewed: 2026-04-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
