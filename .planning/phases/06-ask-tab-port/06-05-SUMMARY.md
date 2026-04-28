---
phase: 06-ask-tab-port
plan: 05
subsystem: tests
tags: [pytest, fastapi, htmx, nl-agent, cookie, ask-tab, settings, invariants, mock]

requires:
  - phase: 06-ask-tab-port
    plan: 03
    provides: GET /ask, POST /ask/query, POST /ask/confirm, POST /settings/llm routes; app_v2.routers.ask.run_nl_query module-level import
  - phase: 06-ask-tab-port
    plan: 04
    provides: ask/index.html, _answer.html, _confirm_panel.html, _abort_banner.html, _starter_chips.html templates; id=answer-zone on fragment wrappers

provides:
  - tests/v2/test_ask_routes.py: 13 route-level TestClient tests for /ask, /ask/query, /ask/confirm
  - tests/v2/test_settings_routes.py: 5 TestClient tests for POST /settings/llm (D-14, D-15, D-16, Pitfall-4, Pitfall-8)
  - tests/v2/test_phase06_invariants.py: 9 source-level tests parametrized to 19 collected items (static-analysis guards)
  - tests/v2/test_llm_resolver.py: 2 cookie-precedence tests appended (D-15, D-17); 10 total, no regressions

affects:
  - 06-06-PLAN: regression bar set at 522 tests; test_v1_streamlit_ask_still_present_pre_06_06_deletion polarity flip required

tech-stack:
  added: []
  patterns:
    - "D-19 module-level patch: mocker.patch('app_v2.routers.ask.run_nl_query') at module level + fixture-level _build_deps + _get_agent sentinels so route reaches run_nl_query without real Agent/DB"
    - "httpx-0.28 repeated-key fix: _post_form_pairs helper using urllib.parse.urlencode + content= for confirmed_params multi-value form fields (mirrors 04-04 pattern)"
    - "Runtime-constructed forbidden literals: banned tokens built as string concatenation so test source does not contain the scanned substring (eliminates self-match false-positive)"
    - "Regex code-call discrimination: agent.run_sync guarded with (?<!`) prefix so docstring backtick prose does not trigger the invariant"

key-files:
  created:
    - tests/v2/test_ask_routes.py
    - tests/v2/test_settings_routes.py
    - tests/v2/test_phase06_invariants.py
  modified:
    - tests/v2/test_llm_resolver.py

decisions:
  - "_build_deps mocked in ask_client fixture (deviation from plan stub): plan showed only _get_agent + run_nl_query mocked, but Pydantic AgentDeps validation against SimpleNamespace db caused route to short-circuit at deps guard; _build_deps sentinel mock is the minimal fix (Rule-1)"
  - "agent.run_sync invariant uses regex (?<!`) backtick-prefix negative lookbehind: the module docstring mentions 'agent.run_sync(...)' in backtick prose; a naive string-contains check would have failed the invariant"

metrics:
  duration: ~9min
  completed: "2026-04-28T23:24:00Z"
  tasks: 2
  files: 4 (3 new + 1 modified)
  new_tests_collected: 39
  total_suite_after: 522
  total_suite_before: 300 (v2 only) / 483 (full)
---

# Phase 6 Plan 05: Ask + Settings Tests + Phase 6 Invariants Summary

**39 new tests proving Plans 06-03 + 06-04 route and template contracts; full suite 522 passed**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-04-28T23:14:43Z
- **Completed:** 2026-04-28T23:24:00Z
- **Tasks:** 2
- **Files modified:** 4 (3 new, 1 extended)

## Accomplishments

### Task 1: test_ask_routes.py + test_settings_routes.py + test_llm_resolver.py cookie tests

**`tests/v2/test_ask_routes.py`** (13 tests, 250+ lines):

| Test | Coverage |
|------|----------|
| `test_get_ask_returns_200_with_html` | ASK-V2-01: page render, id=answer-zone, textarea, Run button |
| `test_get_ask_dropdown_lists_all_configured_llms` | ASK-V2-05: both LLM names in dropdown |
| `test_post_ask_query_ok_returns_answer_fragment` | NLResult.ok: table + summary + Generated SQL |
| `test_post_ask_query_clarification_returns_confirm_panel` | NLResult.clarification_needed: message + hidden original_question + Run Query |
| `test_post_ask_query_failure_step_cap_returns_abort_banner` | reason=step-cap verbatim v1.0 copy |
| `test_post_ask_query_failure_timeout_returns_abort_banner` | reason=timeout verbatim v1.0 copy |
| `test_post_ask_query_no_llm_configured_returns_abort_banner` | resolve_active_llm=None path |
| `test_post_ask_confirm_composes_loop_prevention_message` | D-10: confirmed_params + original_question + loop-prevention sentence |
| `test_post_ask_confirm_with_empty_confirmed_params_still_runs` | D-10: empty list path; "If the list is empty" |
| `test_post_ask_confirm_second_turn_clarification_is_suppressed` | Pitfall 6: second ClarificationNeeded → abort banner |
| `test_post_ask_confirm_failure_returns_abort_banner` | Standard failure on second turn |
| `test_post_ask_query_honors_pbm2_llm_cookie` | D-17: valid cookie → openai-prod backend |
| `test_post_ask_query_falls_back_when_cookie_invalid` | D-15: tampered cookie → ollama-local default |

**`tests/v2/test_settings_routes.py`** (5 tests):

| Test | Coverage |
|------|----------|
| `test_post_settings_llm_valid_name_sets_cookie` | D-16/Pitfall-4: 204 + HX-Refresh: true + pbm2_llm cookie |
| `test_post_settings_llm_cookie_attributes` | D-14: Path=/, SameSite=Lax, Max-Age=31536000, HttpOnly |
| `test_post_settings_llm_invalid_name_falls_back_to_default` | D-15: evil-tampered → default silently |
| `test_post_settings_llm_empty_name_falls_back_to_default` | D-15: empty → default |
| `test_post_settings_llm_route_is_sync_def` | INFRA-05/Pitfall-1: not a coroutine |

**`tests/v2/test_llm_resolver.py`** (2 new tests appended):
- `test_resolve_active_llm_cookie_overrides_default`: D-17 valid cookie → named LLM returned
- `test_resolve_active_llm_invalid_cookie_falls_back_silently`: D-15 tampered cookie → default_llm

### Task 2: test_phase06_invariants.py (9 source-level tests / 19 collected items)

| Test (collected) | Decision | Guard |
|------------------|----------|-------|
| `test_no_async_def_in_phase6_router[ask.py]` | INFRA-05 | `^async def` absent in ask.py |
| `test_no_async_def_in_phase6_router[settings.py]` | INFRA-05 | `^async def` absent in settings.py |
| `test_no_safe_filter_in_ask_templates[index.html]` | XSS | `| safe` absent |
| `test_no_safe_filter_in_ask_templates[_starter_chips.html]` | XSS | `| safe` absent |
| `test_no_safe_filter_in_ask_templates[_confirm_panel.html]` | XSS | `| safe` absent |
| `test_no_safe_filter_in_ask_templates[_answer.html]` | XSS | `| safe` absent |
| `test_no_safe_filter_in_ask_templates[_abort_banner.html]` | XSS | `| safe` absent |
| `test_fragment_outer_wrapper_has_answer_zone_id[_confirm_panel.html]` | D-08 | `id="answer-zone"` present |
| `test_fragment_outer_wrapper_has_answer_zone_id[_answer.html]` | D-08 | `id="answer-zone"` present |
| `test_fragment_outer_wrapper_has_answer_zone_id[_abort_banner.html]` | D-08 | `id="answer-zone"` present |
| `test_no_regenerate_button_in_ask_templates` | D-11 | "Regenerate" absent in all ask templates |
| `test_no_openai_sensitivity_banner_in_ask_templates` | D-18 | OpenAI banner copy absent |
| `test_ask_router_uses_nl_service_run_nl_query_only` | ASK-V2-06 | no `agent.run_sync(` code call + module-level import present |
| `test_no_banned_libraries_imported_in_phase6[langchain]` | CLAUDE.md | banned import absent |
| `test_no_banned_libraries_imported_in_phase6[litellm]` | CLAUDE.md | banned import absent |
| `test_no_banned_libraries_imported_in_phase6[vanna]` | CLAUDE.md | banned import absent |
| `test_no_banned_libraries_imported_in_phase6[llama_index]` | CLAUDE.md | banned import absent |
| `test_settings_router_cookie_attrs_match_d14` | D-14/Pitfall-8 | pbm2_llm, max_age, path, samesite, httponly, secure=False |
| `test_v1_streamlit_ask_still_present_pre_06_06_deletion` | D-22 | app/pages/ask.py EXISTS (polarity flip in 06-06) |

## D-19 Mocking Pattern Used

```python
# Fixture-level (ask_client):
mocker.patch("app_v2.routers.ask._get_agent", return_value=_sentinel)
mocker.patch("app_v2.routers.ask._build_deps", return_value=_sentinel)
mocker.patch("app_v2.routers.ask.run_nl_query", return_value=NLResult(kind="ok", ...))

# Per-test override (when testing specific NLResult branches):
mocker.patch("app_v2.routers.ask.run_nl_query", return_value=NLResult(kind="failure", ...))
```

The patch path `"app_v2.routers.ask.run_nl_query"` is the module-level import established in Plan 06-03 (D-19 contract). `_build_deps` is also patched because Pydantic's `AgentDeps` model requires a real `DBAdapter` instance — the sentinel short-circuits validation so the route handler reaches `run_nl_query` without real DB/Agent setup.

## Polarity-Flip Handoff to Plan 06-06

`test_v1_streamlit_ask_still_present_pre_06_06_deletion` currently asserts:
```python
assert v1_ask.exists(), "v1.0 Streamlit Ask page should still exist until Plan 06-06"
```

**Plan 06-06 MUST flip this to `assert not v1_ask.exists()` after deleting `app/pages/ask.py`.** The test file to edit is `tests/v2/test_phase06_invariants.py`, line ~185.

## New Green Test Count

- **Before Plan 06-05:** 300 v2 tests, 483 full-suite tests
- **After Plan 06-05:** 339 v2 tests (+39), **522 full-suite tests** (+39)
- Plan 06-06 will record **522** as the pre-deletion baseline, then subtract the v1.0 ask test count after deletion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added `_build_deps` mock to ask_client fixture**
- **Found during:** Task 1 — first test run, 6 tests failing with "No LLM backend configured"
- **Issue:** Plan showed only `_get_agent` + `run_nl_query` mocked. `_build_deps` constructs a Pydantic `AgentDeps` model requiring `db: DBAdapter` — a SimpleNamespace duck-type fails Pydantic validation, so the route's `if agent is None or deps is None` guard triggered and short-circuited to `_render_unconfigured`.
- **Fix:** Added `mocker.patch("app_v2.routers.ask._build_deps", return_value=_sentinel)` to the fixture. The sentinel value is non-None so the guard passes; the deps object is never actually used since `run_nl_query` is also mocked.
- **Files modified:** `tests/v2/test_ask_routes.py`
- **Commit:** 6e8c065

**2. [Rule 1 - Bug] `agent.run_sync` invariant uses backtick-prefix negative lookbehind**
- **Found during:** Task 2 design (pre-emptive check before writing)
- **Issue:** `ask.py` module docstring mentions `` `agent.run_sync(...)` `` in backtick-quoted prose at line 4. A naive `assert forbidden not in src` would have failed this invariant immediately.
- **Fix:** Used `re.compile(r"(?<!`)\bagent\.run_sync\s*\(")` to match only code-call patterns (not backtick-wrapped documentation references).
- **Files modified:** `tests/v2/test_phase06_invariants.py`
- **Commit:** a94f4e7

**3. [Rule 1 - Bug] Used `_post_form_pairs` for `confirmed_params` multi-value encoding**
- **Found during:** Task 1 test run — `test_post_ask_confirm_composes_loop_prevention_message` failing because `confirmed_params` arrived as `[]` instead of `['UFS · LUNCount']`
- **Issue:** httpx 0.28 dropped list-of-tuples support on `data=` (documented in STATE.md 04-04). The `confirmed_params` field requires repeated form keys.
- **Fix:** Added `_post_form_pairs` helper using `urllib.parse.urlencode` + `content=` pattern; used it in the multi-value test.
- **Files modified:** `tests/v2/test_ask_routes.py`
- **Commit:** 6e8c065

## Task Commits

1. **Task 1: test_ask_routes.py + test_settings_routes.py + llm_resolver cookies** — `6e8c065` (test)
2. **Task 2: test_phase06_invariants.py** — `a94f4e7` (test)

## Self-Check

All checks before writing this SUMMARY:
- `tests/v2/test_ask_routes.py` exists — FOUND
- `tests/v2/test_settings_routes.py` exists — FOUND
- `tests/v2/test_phase06_invariants.py` exists — FOUND
- `tests/v2/test_llm_resolver.py` cookie tests present — FOUND
- Commit `6e8c065` exists — FOUND
- Commit `a94f4e7` exists — FOUND
- `pytest tests/v2/test_ask_routes.py -q` → 13 passed
- `pytest tests/v2/test_settings_routes.py -q` → 5 passed
- `pytest tests/v2/test_phase06_invariants.py -q` → 19 passed
- `pytest tests/v2/test_llm_resolver.py -q` → 10 passed (8 existing + 2 new)
- `pytest tests/ -q` → 522 passed, 2 skipped, 0 failed

## Self-Check: PASSED
