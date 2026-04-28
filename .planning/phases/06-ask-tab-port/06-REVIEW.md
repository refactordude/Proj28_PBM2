---
phase: 06-ask-tab-port
reviewed: 2026-04-29T00:00:00Z
depth: standard
iteration: 2
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
  warning: 0
  info: 6
  total: 6
status: clean
---

# Phase 6: Code Review Report (Iteration 2)

**Reviewed:** 2026-04-29
**Depth:** standard
**Iteration:** 2 (re-review after `--auto` fixes for WR-01, WR-02)
**Files Reviewed:** 23
**Status:** clean (no Critical or Warning findings)

## Summary

Iteration 2 confirms the WR-01 and WR-02 fixes from
`06-REVIEW-FIX.md` (commits `1995e89` and `f06fb88`) landed correctly, do not
regress any of the ten Phase 6 focus areas, and do not introduce any new
Critical or Warning issues. Regression bar holds: `pytest tests/v2/ -q` =
339 passed / 2 skipped — identical to the iteration-1 baseline.

### WR-01 fix re-verification (commit `1995e89`)

- `_render_unconfigured` (`ask.py:182-200`) now passes `reason="unconfigured"`
  with empty `detail=""`. The new `{% elif reason == "unconfigured" %}` branch
  in `_abort_banner.html:39-40` renders a single-sentence actionable line:
  *"No LLM backend configured. Open Settings and select a backend, then try
  again."*
- Existing test `test_post_ask_query_no_llm_configured_returns_abort_banner`
  asserts on the substring `"No LLM backend configured"` — still passes (the
  literal lives in the new dedicated branch).
- Cookie/route flow is **untouched**: `resolve_active_llm`, `set_llm`, and
  the `pbm2_llm` cookie attributes (`Path=/`, `SameSite=Lax`, `Max-Age=31536000`,
  `HttpOnly=True`, `Secure=False`) are byte-stable. `test_phase06_invariants
  ::test_settings_router_cookie_attrs_match_d14` and
  `test_settings_routes::*` continue to pass.
- The fragment outer wrapper still carries `id="answer-zone"` (verified by
  `test_fragment_outer_wrapper_has_answer_zone_id`); swap idempotence is
  preserved.
- Copy is autoescaped and contains no dynamic interpolation (no XSS surface).

### WR-02 fix re-verification (commit `f06fb88`)

- Second-turn `ClarificationNeeded` branch in `_run_second_turn`
  (`ask.py:307-328`) now calls `templates.TemplateResponse` directly with
  `reason="loop-aborted"`, bypassing the synthesized
  `NLResult(kind="failure", failure=AgentRunFailure(...))` round-trip from
  iteration 1.
- The `from app.core.agent.nl_agent import AgentRunFailure` local import is
  **removed**, eliminating IN-01 along this code path (top-level coupling
  via `AgentDeps`/`build_agent` already exists; the local import was
  redundant).
- New `{% elif reason == "loop-aborted" %}` branch in
  `_abort_banner.html:41-42` renders user-actionable copy: *"The model could
  not narrow your question even with explicit parameters (clarification a
  second time was suppressed). Edit the question above to be more specific
  — mention platform IDs, parameter names, or a value range — and try
  again."*
- Sync `def` is preserved on `_run_second_turn` (it is a helper called from
  the sync `ask_confirm` route handler, not a route itself; both stay sync).
  `test_no_async_def_in_phase6_router` continues to pass.
- The `_log.warning("Second-turn ClarificationNeeded suppressed ...")` call
  is preserved at the entry of the suppression branch — observability for
  Pitfall 6 trips remains intact.
- Module-level `run_nl_query` import (`ask.py:32`) is preserved — D-19
  mocking precondition holds.
- `AgentRunFailure.reason` Literal (`step-cap` | `timeout` | `llm-error`)
  is intentionally **not widened**. The summary in `06-REVIEW-FIX.md`
  correctly justifies this: `loop-aborted` is a v2 presentation concern
  (route layer), not an agent-output concern (domain layer). This is a
  correct architectural decision and matches the layering in
  `nl_service.py`.
- Existing test `test_post_ask_confirm_second_turn_clarification_is_suppressed`
  passes because its assertion accepts either `"Something went wrong"` OR
  `"clarification a second time"`, and the new copy contains the latter
  literal.
- Outer-wrapper `id="answer-zone"` preserved on the response; swap
  idempotence intact.

### Ten focus-area re-sweep (no regressions)

1. **Sync def routes only** — `ask_page`, `ask_query`, `ask_confirm`,
   `set_llm` are all `def`. `test_no_async_def_in_phase6_router` green.
2. **Cookie attrs (D-14)** — `settings.py` unchanged; invariant test green.
3. **Swap idempotence (D-08)** — both new template branches live inside
   the existing `<div id="answer-zone">`; outer wrapper unchanged. Invariant
   test `test_fragment_outer_wrapper_has_answer_zone_id` green.
4. **XSS** — no `| safe` filter anywhere in `templates/ask/`. New branch copy
   is static text with no Jinja interpolation. Invariant test
   `test_no_safe_filter_in_ask_templates` green.
5. **Module-level `run_nl_query` import** — `ask.py:32` unchanged. Invariant
   `test_ask_router_uses_nl_service_run_nl_query_only` green.
6. **Loop prevention** — second-turn `ClarificationNeeded` still produces an
   abort banner (alert-danger, no `Run Query` button). Test
   `test_post_ask_confirm_second_turn_clarification_is_suppressed` green.
7. **DataFrame conversion (Pitfall 2)** — `_df_to_template_ctx` and call
   sites unchanged.
8. **Picker macro reuse (D-07 / Pitfall 3)** — `_confirm_panel.html` still
   passes `disable_auto_commit=True`; macro behavior in
   `_picker_popover.html:82-87` byte-stable. Phase 4 test
   `test_picker_popover_uses_d15b_auto_commit_pattern` green.
9. **Banned imports** — none. The fix actually **removes** a local import
   (`AgentRunFailure` from `nl_agent`), reducing the import surface.
   Invariant `test_no_banned_libraries_imported_in_phase6` green.
10. **Verbatim copy port** — the v1.0-derived strings (textarea placeholder,
    step-cap copy, timeout copy, "Generated SQL", "Partial output", "Try
    asking...", "Parameters to include", "Run Query ▸", "{N} rows
    returned.") are untouched by the fixes. The new `unconfigured` and
    `loop-aborted` copy is NEW v2.0 UX text, not a port — verbatim contract
    is unaffected.

### What changed vs iteration 1 finding set

- **WR-01: closed.** The dedicated `unconfigured` branch eliminates the
  awkward "Something went wrong. (...) Try rephrasing your question."
  wrapper for this state.
- **WR-02: closed.** The dedicated `loop-aborted` branch eliminates the
  same wrapper for the loop-prevention state and adds explicit recovery
  guidance.
- **IN-01: partially resolved as a side effect of WR-02.** The local
  `from app.core.agent.nl_agent import AgentRunFailure` import inside
  `_run_second_turn` is removed because the synthesized failure NLResult
  is no longer needed. The remaining recommendation in IN-01 (consolidate
  the top-level import line) is moot — there is no longer any local
  `AgentRunFailure` import anywhere in the file.
- **IN-02, IN-03, IN-04, IN-05: unchanged from iteration 1** (out of scope
  per `fix_scope=critical_warning`; carried forward below renumbered).

The single new informational item below (IN-06) is a minor code-quality
observation about the iteration-2 fix itself — not a bug, not a
regression, and consciously left for future cleanup.

## Info

### IN-01: Composed second-turn message uses Python list `repr()` (brittle coupling) [carried forward]

**File:** `app_v2/routers/ask.py:155`

**Issue:** Unchanged from iteration 1. The composed prompt does
`f"User-confirmed parameters: {confirmed_params}\n\n"`. Python f-strings
with a list use `repr()`, which produces `['UFS · LUNCount']`. The agent
must parse this Python literal. If a future refactor changes
`confirmed_params` to a tuple, set, or frozenset, the rendered
representation changes and the agent's prompt-time interpretation may
shift. The matching test
(`test_post_ask_confirm_composes_loop_prevention_message`) asserts on the
literal `"User-confirmed parameters: ['UFS · LUNCount']"` so the format is
locked at test level — but the test won't catch a tuple/set substitution.

**Fix:** Use an explicit serialization to make the contract intentional:

```python
import json

confirmed_repr = json.dumps(list(confirmed_params))  # always JSON-array
composed = (
    f"User-confirmed parameters: {confirmed_repr}\n\n"
    f"Original question: {original_question}\n\n"
    "Use ONLY the confirmed parameters above. "
    "If the list is empty, use your best judgment from the original question "
    "and do not return ClarificationNeeded again."
)
```

JSON-array form is also more familiar to LLMs as a structured-data
representation.

### IN-02: `_get_agent` mutates `app.state.agent_registry` without a lock (benign threadpool race) [carried forward]

**File:** `app_v2/routers/ask.py:50-71`

**Issue:** Unchanged from iteration 1. FastAPI dispatches sync `def` routes
to a threadpool, so two concurrent requests for the same `llm_name` can
both pass the `if llm_name in registry` guard, both run
`build_pydantic_model` + `build_agent`, and both write to
`registry[llm_name]`. The race is benign — the build is idempotent and the
second write just overwrites the first — but it does mean an extra LLM
client may be constructed under load. For a low-concurrency intranet tool
this is acceptable.

**Fix (optional, low priority):** add a `threading.Lock` with double-checked
locking, OR add a comment to `_get_agent` stating that the duplicate-build
race is acceptable and why.

### IN-03: `valid_names` set in `set_llm` may include `None` if any LLMConfig lacks `name` [carried forward]

**File:** `app_v2/routers/settings.py:52`

**Issue:** Unchanged from iteration 1.
`valid_names = {getattr(l, "name", None) for l in llms}`. If any
`LLMConfig` is malformed and missing `name`, the set contains `None`. In
practice this is benign because no submitted form value will equal
`None`; this is purely a code-cleanliness concern.

**Fix:**
```python
valid_names = {n for n in (getattr(l, "name", None) for l in llms) if n}
```

### IN-04: `confirmed_params: list[str] = []` mutable default in `ask_confirm` [carried forward]

**File:** `app_v2/routers/ask.py:138`

**Issue:** Unchanged from iteration 1. Standard Python style would flag
`= []` as a mutable default argument. The project's established v2.0 idiom
(see `app_v2/routers/overview.py:309-314`) intentionally uses `= []` for
FastAPI `Form()` parameters because FastAPI special-cases `Form` to
evaluate defaults per-request rather than reusing the same list object. So
this is NOT a real bug, but it is a divergence from PEP 8 / Pyflakes /
Ruff B006 expectations that future readers may flag.

**Fix (optional, project-preference dependent):** Either add `# noqa: B006`
annotations on the affected lines or document the project pattern in
`CLAUDE.md` `## Conventions`.

### IN-05: Identical `templates.TemplateResponse(...)` pattern repeated three times in `ask.py` (DRY)

**File:** `app_v2/routers/ask.py:182-200, 203-215, 318-328`

**Issue:** Surfaced by the iteration-2 fix. Three internal helpers/branches
now build the same shape:

```python
templates.TemplateResponse(
    request,
    "ask/_abort_banner.html",
    {"reason": ..., "last_sql": ..., "detail": ...},
    status_code=200,
)
```

— `_render_unconfigured` (reason `"unconfigured"`),
`_render_failure_kind` (reason from NLResult.failure), and the inline
loop-aborted branch in `_run_second_turn` (reason `"loop-aborted"`). The
three sites are correct and tests cover them, but a small
`_render_abort_banner(request, reason, last_sql="", detail="")` helper
would consolidate the construction in one place and make a future fourth
abort reason a one-line addition. This is a code-organization
improvement, not a bug.

**Fix (optional):**
```python
def _render_abort_banner(
    request: Request,
    reason: str,
    last_sql: str = "",
    detail: str = "",
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "ask/_abort_banner.html",
        {"reason": reason, "last_sql": last_sql, "detail": detail},
        status_code=200,
    )

def _render_unconfigured(request: Request) -> HTMLResponse:
    return _render_abort_banner(request, "unconfigured")

def _render_failure_kind(request: Request, nl_result: NLResult) -> HTMLResponse:
    failure = nl_result.failure
    return _render_abort_banner(
        request,
        getattr(failure, "reason", "llm-error"),
        getattr(failure, "last_sql", ""),
        getattr(failure, "detail", ""),
    )

# In _run_second_turn:
return _render_abort_banner(request, "loop-aborted")
```

### IN-06: New "loop-aborted" template copy duplicates information already conveyed by surrounding UI

**File:** `app_v2/templates/ask/_abort_banner.html:42`

**Issue:** Surfaced by the iteration-2 fix. The new copy reads: *"...
(clarification a second time was suppressed). Edit the question above ..."*
The parenthetical "clarification a second time was suppressed" is a
mid-tier internal description that helps the existing test
(`test_post_ask_confirm_second_turn_clarification_is_suppressed`)
substring-match but reads slightly like a log line to end users. The
sentence still parses cleanly without it. This is a copy/UX nit, not a
bug.

**Fix (optional):** Trim the parenthetical and rely on the rest of the
sentence:

```jinja
{% elif reason == "loop-aborted" %}
  The model could not narrow your question even with explicit parameters.
  Edit the question above to be more specific — mention platform IDs,
  parameter names, or a value range — and try again.
```

If the trim is applied, update
`test_post_ask_confirm_second_turn_clarification_is_suppressed` to assert
on a copy fragment that survives (e.g., `"could not narrow your question"`).

---

_Reviewed: 2026-04-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 2 (post-fix re-review)_
