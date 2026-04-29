---
phase: 06-ask-tab-port
plan: 03
subsystem: api
tags: [fastapi, htmx, nl-agent, cookie, ask-tab, settings, sync-def, always-200]

requires:
  - phase: 06-ask-tab-port
    plan: 02
    provides: resolve_active_llm(settings, request=None), load_starter_prompts(), picker disable_auto_commit kwarg

provides:
  - GET /ask full-page route (sync def, ask/index.html with backend_name + starter_prompts + llms context)
  - POST /ask/query first-turn NL endpoint (always-200, three-branch fragment dispatch)
  - POST /ask/confirm second-turn NL endpoint (loop-prevention, Pitfall 6 abort on second ClarificationNeeded)
  - POST /settings/llm cookie-setter (pbm2_llm, D-14 attrs, 204 + HX-Refresh: true)
  - ask + settings routers registered in main.py before root (defense-in-depth)
  - Phase 1 GET /ask stub removed from root.py (empty APIRouter shell retained)

affects:
  - 06-04-PLAN (templates: ask/index.html, _answer.html, _confirm_panel.html, _abort_banner.html)
  - 06-05-PLAN (tests: test_ask_routes.py, test_settings_routes.py consume these routes)

tech-stack:
  added: []
  patterns:
    - "ALWAYS-200 contract: all NL outcomes (ok/clarification_needed/failure) return HTTP 200; fragment swaps into #answer-zone; 4xx/5xx reserved for route errors only"
    - "sync def routes: run_nl_query calls agent.run_sync internally; async def would block uvicorn event loop (INFRA-05, Pitfall 1)"
    - "Module-level run_nl_query import: pytest-mock patches app_v2.routers.ask.run_nl_query at module level (D-19)"
    - "_get_agent lazy registry: app.state.agent_registry dict[str, Agent] populated on first call per backend (RESEARCH.md Pattern 5)"
    - "Pitfall 6 suppression: second-turn ClarificationNeeded treated as failure(reason=llm-error) to prevent infinite confirmation loop (D-10)"
    - "_df_to_template_ctx: DataFrame converted to columns+rows lists before TemplateResponse (Pitfall 2)"
    - "D-14 cookie: pbm2_llm, path=/, samesite=lax, max_age=31536000, httponly=True, secure=False (intranet HTTP)"
    - "D-16 HX-Refresh: response.headers['HX-Refresh'] = 'true' (lowercase string, Pitfall 4)"

key-files:
  created:
    - app_v2/routers/ask.py
    - app_v2/routers/settings.py
  modified:
    - app_v2/routers/root.py
    - app_v2/main.py
    - tests/v2/test_main.py
    - tests/v2/test_phase04_invariants.py

key-decisions:
  - "ALWAYS-200 contract for all three NL outcome branches — matches summary.py precedent; HTMX #htmx-error-container is for route errors only, not NL failures"
  - "Module-level run_nl_query import (not function-scope) so mocker.patch('app_v2.routers.ask.run_nl_query') works at test time (D-19)"
  - "D-15 cookie validation: closed-set check against {l.name for l in settings.llms}; fallback to default_llm silently (no 4xx)"
  - "Pitfall 6: second-turn ClarificationNeeded synthesizes AgentRunFailure(reason=llm-error) — user sees abort banner, never a second confirmation panel"
  - "Two tombstoned tests (Rule-1 auto-fix): test_get_ask_returns_200_with_phase_placeholder + test_no_browse_stub_in_root_router sanity assertion — both guard Phase 1 invariants intentionally changed by this plan"

requirements-completed:
  - ASK-V2-01
  - ASK-V2-02
  - ASK-V2-06
  - ASK-V2-07

duration: 5min
completed: 2026-04-28T23:01:52Z
---

# Phase 6 Plan 03: Ask + Settings Routers Summary

**Four sync def routes wired to run_nl_query — GET /ask, POST /ask/query, POST /ask/confirm, POST /settings/llm**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-28T22:56:28Z
- **Completed:** 2026-04-28T23:01:52Z
- **Tasks:** 2
- **Files modified:** 6 (2 new routers, 1 trimmed router, 1 updated main.py, 2 tombstoned tests)

## Accomplishments

### Task 1: app_v2/routers/ask.py + root.py trimming

Created `app_v2/routers/ask.py` (271 lines) with three sync `def` routes:

**GET /ask** — full-page render feeding `ask/index.html` with:
- `backend_name` from `resolve_active_backend_name(settings, request)` (cookie-aware)
- `llm_cfg` from `resolve_active_llm(settings, request)` (cookie-aware)
- `starter_prompts` from `load_starter_prompts()` (8 entries from YAML)
- `llms` list for the LLM selector dropdown

**POST /ask/query** — first-turn NL endpoint (ALWAYS-200):
- Resolves active LLM via cookie-aware resolver
- Lazy-builds PydanticAI agent via `_get_agent` from `app.state.agent_registry`
- Calls `run_nl_query(question.strip(), agent, deps)` — never bypasses SAFE harness
- Branches: `ok` → `_answer.html`, `clarification_needed` → `_confirm_panel.html`, `failure` → `_abort_banner.html`

**POST /ask/confirm** — second-turn NL endpoint (ALWAYS-200):
- Composes the loop-prevention message verbatim per RESEARCH.md Pattern 2 / D-10:
  `"Use ONLY the confirmed parameters above. If the list is empty, use your best judgment from the original question and do not return ClarificationNeeded again."`
- Calls `run_nl_query(composed, agent, deps)` — identical call signature to first turn
- Pitfall 6 guard: if agent returns `ClarificationNeeded` again, synthesizes `AgentRunFailure(reason="llm-error")` and renders abort banner — user never sees a second confirmation loop

Trimmed `root.py` to empty `APIRouter()` shell — Phase 1 GET /ask stub removed. Module kept (main.py still imports it).

### Task 2: app_v2/routers/settings.py + main.py registration

Created `app_v2/routers/settings.py` (65 lines):

**POST /settings/llm** — cookie setter (sync `def`, HTTP 204 + HX-Refresh):
- D-15 validation: `name in {getattr(l, "name", None) for l in llms}` — invalid value falls to `default_llm`
- D-14 cookie attrs: `key="pbm2_llm"`, `max_age=31536000`, `path="/"`, `samesite="lax"`, `httponly=True`, `secure=False`
- D-16 response: `Response(status_code=204)` + `response.headers["HX-Refresh"] = "true"` (lowercase Pitfall 4)

Updated `main.py` router registration block — `ask` + `settings_router` inserted BEFORE `root` (defense-in-depth precedent from Phase 4 browse-before-root).

## HTTP Shape Summary

| Route | Method | Fragment / Response | Status |
|-------|--------|---------------------|--------|
| /ask | GET | ask/index.html (full page) | 200 |
| /ask/query | POST | ask/_answer.html OR ask/_confirm_panel.html OR ask/_abort_banner.html | 200 |
| /ask/confirm | POST | ask/_answer.html OR ask/_abort_banner.html (NEVER _confirm_panel.html) | 200 |
| /settings/llm | POST | Empty body, set-cookie, HX-Refresh | 204 |

## Agent Registry Pattern

```python
def _get_agent(request: Request, llm_name: str):
    registry = getattr(request.app.state, "agent_registry", None)
    if llm_name in registry:
        return registry[llm_name]  # cache hit
    cfg = find_llm(settings, llm_name)
    model = build_pydantic_model(cfg)
    agent = build_agent(model)
    registry[llm_name] = agent   # lazy populate
    return agent
```

Matches v1.0 `@st.cache_resource get_nl_agent()` pattern. CPython GIL makes dict writes atomic — no threading.Lock needed for intranet ~10-user load.

## Loop-Prevention Message (D-10 verbatim)

```python
composed = (
    f"User-confirmed parameters: {confirmed_params}\n\n"
    f"Original question: {original_question}\n\n"
    "Use ONLY the confirmed parameters above. "
    "If the list is empty, use your best judgment from the original question "
    "and do not return ClarificationNeeded again."
)
```

## Pitfall 6 Mechanism

In `_run_second_turn`, if `run_nl_query` returns `kind="clarification_needed"` on the second call:

```python
synth = NLResult(
    kind="failure",
    failure=AgentRunFailure(
        reason="llm-error",
        last_sql="",
        detail="Agent requested clarification a second time; aborting to prevent loop.",
    ),
)
_log.warning("Second-turn ClarificationNeeded suppressed (D-10 / Pitfall 6)")
return _render_failure_kind(request, synth)
```

User sees the abort banner. Step-cap (5) + timeout (30s) inside `run_nl_query` are the hard ceiling regardless.

## Router Registration Ordering

```
overview → platforms → summary → browse → ask → settings_router → root
```

`ask` and `settings_router` registered BEFORE `root` (now an empty shell). Even if a future commit accidentally re-adds a `/ask` stub to `root.py`, the real `ask` router still wins via first-match FastAPI routing.

## Final grep Counts (ALWAYS-200 + sync def + cookie attrs)

```
grep -cE "^async def" app_v2/routers/ask.py      → 0  (sync def contract)
grep -cE "^async def" app_v2/routers/settings.py  → 0  (sync def contract)
grep -c '"ask/_abort_banner.html"' ask.py          → 2  (unconfigured + failure branches)
grep -cE 'secure=True' settings.py                 → 0  (intranet HTTP — D-14)
grep -cE '"HX-Refresh"\] = "true"' settings.py    → 1  (lowercase Pitfall 4)
```

## Task Commits

1. **Task 1: ask.py + root.py trim** — `59a4964` (feat)
2. **Task 2: settings.py + main.py + test tombstones** — `dc23b7d` (feat)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Tombstoned two tests that guarded Phase 1 stub invariants**
- **Found during:** Task 2 verification (post-implementation test run)
- **Issue:** `test_get_ask_returns_200_with_phase_placeholder` asserted Phase 1 "Coming in Phase 5" placeholder text in `/ask` response. `test_no_browse_stub_in_root_router` had a "sanity" assertion that `def ask_page` must remain in `root.py`. Both invariants are intentionally broken by this plan.
- **Fix:** Tombstoned both with `@pytest.mark.skip` carrying Phase 6 reason + pointer to Plan 06-04/06-05. `test_no_browse_stub_in_root_router` assertion inverted to enforce the new Phase 6 contract (ask stub MUST be absent from root.py).
- **Files modified:** `tests/v2/test_main.py`, `tests/v2/test_phase04_invariants.py`
- **Commit:** `dc23b7d`

## Next Phase Readiness

- Plan 06-04 (templates) receives 4 route contracts to satisfy:
  - `ask/index.html` — full page with `active_tab`, `backend_name`, `llm_cfg`, `starter_prompts`, `llms` context
  - `ask/_answer.html` — outer wrapper `id="answer-zone"`, `columns`, `rows`, `row_count`, `summary`, `sql`
  - `ask/_confirm_panel.html` — outer wrapper `id="answer-zone"`, `message`, `candidate_params`, `all_params`, `original_question`
  - `ask/_abort_banner.html` — outer wrapper `id="answer-zone"`, `reason`, `last_sql`, `detail`
- Plan 06-05 (tests) patches `app_v2.routers.ask.run_nl_query` at module level (D-19 contract in place)

---
*Phase: 06-ask-tab-port*
*Completed: 2026-04-28T23:01:52Z*
