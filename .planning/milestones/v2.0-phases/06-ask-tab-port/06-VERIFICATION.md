---
phase: 06-ask-tab-port
verified: 2026-04-29T09:15:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Load http://localhost:8000/ask in a browser; type a question and click Run"
    expected: "Result table with LLM summary and collapsed SQL block appear in #answer-zone via HTMX swap; no full page reload"
    why_human: "HTMX swap behavior and visual rendering require a running server with real LLM + DB connections"
  - test: "Trigger a ClarificationNeeded response from the agent (ask a vague question that mentions no specific parameters); modify the pre-checked picker and click 'Run Query ▸'"
    expected: "Confirmation panel appears with candidate params pre-checked; after clicking Run Query the confirmed params route to the second turn and return an answer fragment"
    why_human: "Two-turn flow requires a real LLM call to produce ClarificationNeeded; cannot mock this at the browser level"
  - test: "Click the 'LLM: Ollama ▾' dropdown and switch to OpenAI; refresh the page"
    expected: "Dropdown label updates to 'LLM: OpenAI ▾' after refresh; cookie pbm2_llm=openai-prod visible in DevTools; AI Summary on Overview also uses OpenAI"
    why_human: "Cookie persistence and cross-page effect require a running browser session"
  - test: "Click one of the 8 starter-prompt chips in the Ask page"
    expected: "Chip text fills the textarea but the form does NOT submit automatically"
    why_human: "onclick JS fill-without-submit behavior requires browser rendering"
  - test: "Submit a question that the agent exhausts (e.g. a very vague query that will hit 5 steps)"
    expected: "Red abort banner appears with exact copy: 'Agent stopped: reached the 5-step limit. Try rephrasing your question with more specific parameters.'"
    why_human: "Requires a live LLM + agent execution to trigger the step-cap path"
---

# Phase 6: Ask Tab Port — Verification Report

**Phase Goal:** Users can ask natural-language questions about the UFS database through the Ask tab, go through the two-turn parameter-confirmation flow, see results with the LLM summary and SQL expander, switch between Ollama and OpenAI backends, and rely on the full v1.0 safety harness — all under the new Bootstrap shell.
**Verified:** 2026-04-29T09:15:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | User can type a NL question, submit it, receive result table with LLM summary and collapsible SQL — OR parameter-confirmation when agent needs clarification | VERIFIED | `GET /ask` returns 200 with `ask/index.html`; `POST /ask/query` branches on `NLResult.kind` to `_answer.html` / `_confirm_panel.html` / `_abort_banner.html`; all routes are sync `def`; `run_nl_query` imported at module level; 13 route tests pass |
| 2 | Two-turn confirmation presents pre-checked candidate params; user can modify and click Run Query to execute with confirmed params; second-turn ClarificationNeeded → abort (loop prevention) | VERIFIED | `_confirm_panel.html` imports `picker_popover` with `disable_auto_commit=True`; `hx-post="/ask/confirm"` on Run Query button; hidden `original_question` input present; composed message includes "Use ONLY the confirmed parameters above" + loop-prevention sentence; Pitfall 6 suppression confirmed by `test_post_ask_confirm_second_turn_clarification_is_suppressed` passing |
| 3 | Ask page header shows "LLM: Ollama ▾" / "LLM: OpenAI ▾" dropdown; selected backend persists via `pbm2_llm` cookie; no global navbar selector; no OpenAI sensitivity-warning banner | VERIFIED | `POST /settings/llm` sets cookie with all D-14 attributes (`path=/`, `samesite=lax`, `max_age=31536000`, `httponly=True`, `secure=False`); returns 204 + `HX-Refresh: "true"`; `llm_resolver` reads and validates cookie against `settings.llms[].name`; `base.html` contains no LLM selector; 5 settings route tests + 2 cookie resolver tests pass |
| 4 | 8 curated starter prompts appear on initial page; clicking fills textarea without auto-submit | VERIFIED | `app_v2/services/starter_prompts.py` exists with fallback chain to `config/starter_prompts.example.yaml` (8 entries); `_starter_chips.html` iterates `starter_prompts[:8]` with `.ai-chip` class; onclick fills `#ask-q` textarea only (no `hx-post` or `submit()` in chips); `{% if starter_prompts %}` guard in index.html |
| 5 | Step-cap / timeout shows red abort banner with exact v1.0 copy; non-allowed table rejected before execution | VERIFIED | `_abort_banner.html` contains verbatim copy: "reached the 5-step limit. Try rephrasing your question with more specific parameters." and "query timed out after 30 seconds. Try a more targeted question or switch to a faster model."; `test_ask_router_uses_nl_service_run_nl_query_only` invariant confirms no `agent.run_sync` bypass; `run_nl_query` (which enforces SAFE-02..06 including allowed_tables) is the sole NL execution path |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app_v2/routers/ask.py` | GET /ask + POST /ask/query + POST /ask/confirm | VERIFIED | Exists, 320 lines, 3 sync routes, module-level `run_nl_query` import |
| `app_v2/routers/settings.py` | POST /settings/llm with D-14 cookie + 204 + HX-Refresh | VERIFIED | Exists, all cookie attrs present, `secure=False` explicit, `"HX-Refresh" = "true"` lowercase |
| `app_v2/services/llm_resolver.py` | Two-arg signatures with cookie precedence | VERIFIED | `resolve_active_llm(settings, request=None)` and `resolve_active_backend_name(settings, request=None)` with `pbm2_llm` cookie validation |
| `app_v2/services/starter_prompts.py` | YAML fallback loader porting v1.0 function | VERIFIED | Exists, no streamlit/nest_asyncio imports, returns 8 entries from example.yaml |
| `app_v2/templates/ask/index.html` | Full-page Ask layout (≥80 lines) | VERIFIED | 129 lines; extends base.html; has textarea, Run button, LLM dropdown, #answer-zone, starter_chips include |
| `app_v2/templates/ask/_starter_chips.html` | 4x2 chip grid | VERIFIED | 32 lines; "Try asking..." heading; `.ai-chip` buttons; onclick fills textarea only |
| `app_v2/templates/ask/_confirm_panel.html` | NL-05 confirmation with picker (≥30 lines) | VERIFIED | 79 lines; picker import with `disable_auto_commit=True`; hidden `original_question`; Run Query button; `id="answer-zone"` on outer wrapper |
| `app_v2/templates/ask/_answer.html` | Table + summary + SQL expander, no Regenerate (≥30 lines) | VERIFIED | 80 lines; `<details>` SQL expander; "Generated SQL" label; 0 occurrences of "Regenerate" |
| `app_v2/templates/ask/_abort_banner.html` | Red alert with v1.0 copy for 3 reasons (≥15 lines) | VERIFIED | 57 lines; `alert-danger`; step-cap verbatim copy; timeout verbatim copy; generic llm-error branch with `{{ detail \| e }}` |
| `app_v2/static/css/app.css` | Phase 6 appendix with `.ai-chip` | VERIFIED | `.ai-chip` rule with `border-radius: 999px`, `#f4f6f8`; Phase 6 marker comment; Phase 1-5 selectors preserved |
| `app_v2/templates/browse/_picker_popover.html` | `disable_auto_commit=False` kwarg | VERIFIED | Macro signature updated; `{% if not disable_auto_commit %}` wraps all 5 hx-* attributes |
| `tests/v2/test_ask_routes.py` | ≥12 tests, module-level mock (D-19) | VERIFIED | 13 test functions |
| `tests/v2/test_settings_routes.py` | ≥5 tests covering D-14/D-15/D-16 | VERIFIED | 5 test functions |
| `tests/v2/test_phase06_invariants.py` | ≥8 static guards, 19 collected items | VERIFIED | 9 test functions, 19 collected items, all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `ask/index.html` | `POST /ask/query` | `hx-post="/ask/query"` | WIRED | 1 match in template |
| `ask/index.html` | `POST /settings/llm` | `hx-post="/settings/llm"` | WIRED | 2 matches (one per dropdown item loop) |
| `ask/_confirm_panel.html` | `browse/_picker_popover.html` macro | `{% from ... import picker_popover %}` + `disable_auto_commit=True` | WIRED | 1 import, 3 occurrences of `disable_auto_commit=True` |
| `ask/_confirm_panel.html` | `POST /ask/confirm` | `hx-post="/ask/confirm"` | WIRED | 1 match on Run Query button |
| `app_v2/routers/ask.py` | `app.core.agent.nl_service.run_nl_query` | Module-level import (D-19) | WIRED | `from app.core.agent.nl_service import NLResult, run_nl_query` at line 32 |
| `app_v2/routers/ask.py` | `llm_resolver.resolve_active_llm(settings, request)` | Cookie-aware calls in `_run_first_turn` and `_run_second_turn` | WIRED | 3 call sites in ask.py, all two-arg |
| `app_v2/routers/settings.py` | `Response(204) + set_cookie + HX-Refresh` | D-16 Pitfall 4 lowercase string | WIRED | `"HX-Refresh" = "true"` confirmed |
| `app_v2/routers/overview.py` | `resolve_active_backend_name(settings, request)` | D-17 single source of truth | WIRED | Line 237 confirmed two-arg |
| `app_v2/routers/summary.py` | `resolve_active_llm(settings, request)` + `resolve_active_backend_name(settings, request)` | D-17 cookie applies to AI Summary | WIRED | Lines 124-125 confirmed two-arg |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| App boots with 4 new routes | `python3 -c "from app_v2.main import app; ..."` | `/ask`, `/ask/query`, `/ask/confirm`, `/settings/llm` in 20 routes | PASS |
| Full test suite green | `pytest tests/ -q --tb=no` | 506 passed, 2 skipped, 0 failed | PASS |
| v2 suite green | `pytest tests/v2/ -q --tb=no` | 339 passed, 2 skipped | PASS |
| Phase 6 invariants pass | `pytest tests/v2/test_phase06_invariants.py -v` | 19/19 passed | PASS |
| starter_prompts loads 8 entries | Python import sanity | `load_starter_prompts()` returns 8 entries (confirmed via yaml count) | PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| ASK-V2-01 | 06-03, 06-04, 06-05, 06-06 | Ask tab GET /ask + textarea + Run | SATISFIED | Route exists, index.html renders, 13 route tests cover page render |
| ASK-V2-02 | 06-03, 06-04, 06-05, 06-06 | Two-turn confirmation flow | SATISFIED | `_confirm_panel.html` with picker + hidden field + Run Query; `POST /ask/confirm` confirmed; loop suppression tested |
| ASK-V2-03 | 06-01, 06-04, 06-06 | Answer panel: table + summary + SQL expander, no Regenerate | SATISFIED | `_answer.html` has all three sections; 0 "Regenerate" occurrences; invariant test enforces D-11 |
| ASK-V2-04 | 06-01 | Session history panel | OUT OF SCOPE | Moved to ASK-V2-F01 per spec deviation D-05; traceability row updated; no implementation present |
| ASK-V2-05 | 06-02, 06-03, 06-04, 06-05, 06-06 | LLM backend selector (Ask-page only, cookie persistence, no banner) | SATISFIED | `POST /settings/llm` with D-14 attrs; dropdown in index.html only (not base.html); 5 settings tests pass |
| ASK-V2-06 | 06-03, 06-05, 06-06 | All NL calls through nl_service.run_nl_query | SATISFIED | Module-level import; no `agent.run_sync` call in ask.py; invariant test guards this |
| ASK-V2-07 | 06-04, 06-05, 06-06 | SAFE-04 abort banner with v1.0 copy | SATISFIED | `_abort_banner.html` with verbatim copy for step-cap + timeout; Partial output expander; route tests verify each reason |
| ASK-V2-08 | 06-02, 06-04, 06-05, 06-06 | 8 starter prompts, click fills without auto-submit | SATISFIED | `starter_prompts.py` loader; `_starter_chips.html` with onclick fill; no hx-post/submit in chips template |

### Anti-Patterns Found

| File | Pattern | Severity | Assessment |
|------|---------|----------|-----------|
| `app_v2/services/starter_prompts.py` line 9-10 | Contains "streamlit" and "nest_asyncio" strings | Info | Both are in the module docstring explaining WHY those imports are NOT present. Not actual imports. |
| `app_v2/routers/ask.py` line 4 | Contains "agent.run_sync" string | Info | In docstring explaining the reason sync def is required. Not an actual call. `test_ask_router_uses_nl_service_run_nl_query_only` invariant confirms no actual bypass. |
| `app_v2/templates/ask/_abort_banner.html` line 25 | Contains "sensitivity" | Info | In Jinja comment `{# D-18: No OpenAI sensitivity banner anywhere per user decision. #}`. Not rendered HTML. |

No blockers or substantive stubs found.

### Human Verification Required

The automated layer verified all route contracts, template structure, cookie attributes, test suite, and static invariants. Five behaviors require a running server with live LLM/DB connections:

**1. First-turn answer render**
- Test: Load `http://localhost:8000/ask`, type a question, click Run
- Expected: Result table with LLM summary and collapsed SQL block appear without full page reload
- Why human: HTMX swap and LLM response require running server + configured backends

**2. Two-turn confirmation flow (browser)**
- Test: Ask a vague parameter-related question; when the confirmation picker appears, modify checked params and click "Run Query ▸"
- Expected: Confirmed params sent to `/ask/confirm`; answer fragment replaces the picker
- Why human: ClarificationNeeded path requires a real LLM response; cannot trigger with static TestClient

**3. LLM backend cookie persistence**
- Test: Switch from "LLM: Ollama ▾" to "LLM: OpenAI ▾" using the Ask-page dropdown; refresh the page; then navigate to Overview and click AI Summary
- Expected: Dropdown remains "LLM: OpenAI ▾" after refresh; AI Summary also uses OpenAI; DevTools shows `pbm2_llm=openai-prod` cookie
- Why human: Cookie persistence requires browser session; cross-page effect requires live app

**4. Starter chip no-auto-submit**
- Test: Click any starter prompt chip on the Ask page
- Expected: Chip text fills the textarea; no network request fires; user must click Run manually
- Why human: onclick behavior requires browser rendering

**5. Abort banner with exact copy**
- Test: Submit a question that exhausts the step-cap (agent runs 5 steps without success)
- Expected: Red banner: "Agent stopped: reached the 5-step limit. Try rephrasing your question with more specific parameters."
- Why human: Requires live LLM execution to hit step-cap

### Gaps Summary

No functional gaps found. All 5 ROADMAP Success Criteria are implemented and tested.

**Documentation note (non-blocking):** ROADMAP.md still shows Phase 6 as `[ ]` (unchecked) with `5/6 plans, In Progress`, and STATE.md frontmatter counters show `completed_phases: 5, completed_plans: 29, percent: 97` instead of `6/30/100%`. These are planning artifact metadata fields that Plan 06-06 Task 2 was supposed to update but did not fully complete. The actual code, tests, and invariants are all correct and passing. This is a documentation-tracking discrepancy only — it does not affect the phase goal or any user-facing behavior.

The ROADMAP.md `Requirements:` line for Phase 6 also still lists ASK-V2-04 (the spec deviation moved it to Out of Scope), but REQUIREMENTS.md correctly reflects the out-of-scope status. This is a minor cross-document inconsistency with no functional impact.

---

_Verified: 2026-04-29T09:15:00Z_
_Verifier: Claude (gsd-verifier)_
