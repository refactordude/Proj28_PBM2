---
phase: "02-nl-agent-layer"
plan: "05"
subsystem: ask-page-ui
tags: [streamlit, ask-page, NL-05, multiselect, param-confirmation, human-verify]
dependency_graph:
  requires: [02-04]
  provides:
    - app/pages/ask.py (NL-05 param-confirmation flow — ClarificationNeeded branch activated)
    - tests/pages/test_ask_page.py (4 new AppTest tests for NL-05; 10 total)
  affects:
    - app/pages/ask.py (Plan 02-06 may extend gallery prompts; NL-05 flow is complete)
tech_stack:
  added: []
  patterns:
    - "Page-local _get_db_adapter (@st.cache_resource) to avoid importing streamlit_app (mirrors browse.py pattern)"
    - "Graceful DB degradation in _render_param_confirmation: multiselect renders with pending params only when DB unavailable"
    - "Second-turn prompt composition: structured user message injecting confirmed params + original question"
    - "ClarificationNeeded loop guard: clear pending_params before second call + 'Do not ask for more clarification' in prompt"
key_files:
  created: []
  modified:
    - app/pages/ask.py
    - tests/pages/test_ask_page.py
decisions:
  - "Page-local _get_db_adapter added to ask.py (mirrors browse.py) — importing streamlit_app triggers st.Page() validation which crashes AppTest when ask.py runs with pending_params set"
  - "Graceful degradation in _render_param_confirmation: DB unavailable -> full_catalog=[], options=set(pending) — multiselect still renders so user can uncheck agent proposals"
  - "Second-turn prompt composition: 'User-confirmed parameters: {list}\n\nOriginal question: {q}\n\nUse ONLY the confirmed parameters above. Do not ask for more clarification.' — stateless single-message injection (Open Question 3 resolution)"
  - "ClarificationNeeded loop guard: pending_params cleared BEFORE _run_agent_flow call; 'do not ask for more clarification' appended to composed prompt (T-02-05-04 mitigation)"
  - "AppTest tests 3 & 4 use active_db='' to trigger graceful-degradation path — no real DB needed; monkeypatching approach from plan rejected for same reason as Plan 02-04 (AppTest isolated context)"
metrics:
  duration: "6 minutes"
  completed_date: "2026-04-24"
  tasks_completed: 2
  files_changed: 2
requirements_satisfied: [NL-05]

needs_human_verify:
  - step: "Navigate to Ask page — confirm 'Ask' primary button (not 'Run') is visible on empty state"
  - step: "Type a vague question (e.g. 'Show me write protection info') and click 'Ask'"
  - step: "Verify spinner 'Thinking...' appears then a multiselect labeled 'Parameters to include' renders pre-checked with agent candidates"
  - step: "Verify caption 'Agent proposed N parameters. Uncheck to remove, search to add.' appears below multiselect"
  - step: "Open the dropdown — verify it contains the full parameter catalog (search for an arbitrary InfoCategory from Browse)"
  - step: "Uncheck one item, type to add another — multiselect responds"
  - step: "Click 'Run Query' — spinner 'Thinking...' then answer zone renders with result table, summary, 'Generated SQL' expander"
  - step: "After successful run — multiselect is gone; page returns to first-turn mode (Ask button visible)"
  - step: "Regression: ask a crisp question — goes direct-execute, no confirmation row, answer renders immediately"
  - step: "Regression: history panel lists both questions with timestamps"
---

# Phase 2 Plan 05: NL-05 Param Confirmation Two-Turn Flow Summary

**One-liner:** NL-05 two-stage param-confirmation flow: ClarificationNeeded branch renders a pre-checked multiselect + "Run Query" button; second-turn injects confirmed params as a structured prompt with loop-guard.

## What Was Built

### app/pages/ask.py (changes from Plan 02-04)

**New helpers added above `_DEFAULTS`:**

- `_format_param_label(info_category, item) -> str` — canonical `"InfoCategory / Item"` label matching Browse page (D-21 separator `" / "`)
- `_full_param_catalog(db, db_name) -> list[str]` — queries `list_parameters` and maps to label strings

**New `_get_db_adapter` (`@st.cache_resource`):**

Added page-local adapter factory (mirrors `browse.py` pattern) to replace the `from streamlit_app import get_db_adapter` lazy import. This eliminates the AppTest crash caused by `streamlit_app.py` calling `st.Page()` at import time when `pending_params` is non-empty.

**`_DEFAULTS` extended:**

Added `"ask.pending_message": ""` so the agent's clarification message is stored and displayed above the multiselect.

**`_render_agent_flow` ClarificationNeeded branch (was placeholder, now real):**

```python
if isinstance(output, ClarificationNeeded):
    st.session_state["ask.pending_params"] = list(output.candidate_params)
    st.session_state["ask.pending_message"] = output.message
    st.session_state["ask.confirmed_params"] = []
    return
```

**`_render_param_confirmation()` — new function:**

- Reads `pending_params` from session state; returns immediately if empty
- Calls `_get_db_adapter(active_db)` for the full catalog; if DB unavailable, degrades gracefully (uses empty catalog — multiselect still renders with pending params as options)
- `options = sorted(set(full_catalog) | set(pending))` — hallucinated candidates remain selectable per T-02-05-02
- Displays `output.message` via `st.write()` before the multiselect
- `st.multiselect("Parameters to include", options=options, default=pending, placeholder="Search to add more parameters...")` — exact UI-SPEC D-21 copy
- `st.caption("Agent proposed {N} parameters. Uncheck to remove, search to add.")` — exact A-11 copy
- `st.button("Run Query", type="primary")` — single accent-colored CTA per UI-SPEC color contract

**`_run_confirmed_agent_flow()` — new function:**

Composes the second-turn prompt:
```
User-confirmed parameters: {confirmed}

Original question: {question}

Use ONLY the confirmed parameters above. Do not ask for more clarification.
```
Clears `pending_params` and `pending_message` **before** calling `_run_agent_flow()` — T-02-05-04 loop guard.

**`render()` — "Ask" / "Run Query" branch:**

```python
if st.session_state.get("ask.pending_params"):
    _render_param_confirmation()
else:
    if st.button("Ask", type="primary", key="ask.first_turn"):
        ...
```

Single primary CTA at any time: "Ask" (pre-confirmation) or "Run Query" (during confirmation). The plan-internal "Run" button from Plan 02-04 is replaced.

### tests/pages/test_ask_page.py (4 new tests)

| Test | What it verifies |
|------|-----------------|
| `test_param_confirmation_multiselect_renders_when_pending` | Multiselect labeled "Parameters to include" renders; caption says "Agent proposed 2 parameters" |
| `test_no_confirmation_row_when_pending_empty` | No confirmation multiselect when pending_params=[] |
| `test_first_turn_ask_button_shown_when_no_pending` | "Ask" button present; "Run Query" absent when no pending |
| `test_run_query_button_shown_only_when_pending` | "Run Query" button present when pending_params has entries |

All 10 tests pass (6 Plan 02-04 + 4 Plan 02-05).

## Open Question 3 Resolution

Plan 02-03 RESEARCH deferred: "How to inject confirmed params into the second-turn agent call — multi-turn message history vs structured user message?"

**Chosen approach:** Stateless structured user message. The composed prompt embeds the confirmed list + original question + explicit instruction "Do not ask for more clarification." This avoids multi-turn state management, keeps the agent cache-safe, and works with both OpenAI and Ollama backends.

## ClarificationNeeded Loop Safeguard

Two-layer defense against infinite `ClarificationNeeded` → multiselect → `ClarificationNeeded` loops (T-02-05-04):

1. `ask.pending_params` is cleared before the second `_run_agent_flow` call — if the agent somehow returns `ClarificationNeeded` again, `render()` will show the "Ask" button (not the multiselect), breaking the loop
2. The composed prompt ends with "Use ONLY the confirmed parameters above. Do not ask for more clarification." — explicit LLM instruction to proceed to SQL

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Replaced `from streamlit_app import get_db_adapter` with page-local `_get_db_adapter`**
- **Found during:** Task 2 test execution
- **Issue:** `_render_param_confirmation` used `from streamlit_app import get_db_adapter` (same lazy-import pattern as `_run_agent_flow`). When AppTest ran ask.py with `pending_params` non-empty, the import executed `streamlit_app.py` at module level, which calls `main()` → `st.Page("app/pages/browse.py")` → `StreamlitAPIException: Unable to create Page. The file 'browse.py' could not be found.` (AppTest CWD differs from project root in page-file context)
- **Fix:** Added `@st.cache_resource def _get_db_adapter(db_name)` to ask.py (mirrors the same pattern in browse.py). Replaced all two occurrences of `from streamlit_app import get_db_adapter` with `_get_db_adapter(active_db)`. The page-local factory imports only `build_adapter` and `find_database` — no Streamlit navigation calls.
- **Files modified:** `app/pages/ask.py`
- **Commit:** ebe5f0e

**2. [Rule 2 - Missing critical functionality] Graceful degradation when DB unavailable in `_render_param_confirmation`**
- **Found during:** Task 2 test design
- **Issue:** Plan's original `_render_param_confirmation` showed `st.warning("No active database...")` and returned when `db is None` — the multiselect never rendered, making the confirmation flow completely broken in no-DB scenarios (and untestable without a real DB)
- **Fix:** When `db is None`, `full_catalog = []` so `options = sorted(set(pending))` — the multiselect still renders with only the agent-proposed params. User can still uncheck proposals; they just can't add from the full catalog. This is correct per T-02-05-02 (hallucinated candidates remain selectable).
- **Files modified:** `app/pages/ask.py`
- **Commit:** ebe5f0e

**3. [Rule 1 - Bug] AppTest test approach changed from monkeypatch to active_db="" degradation path**
- **Found during:** Task 2 test design
- **Issue:** Plan specified `monkeypatch.setattr(ask_mod, "_full_param_catalog", ...)` and `monkeypatch.setattr(streamlit_app, "get_db_adapter", ...)`. AppTest runs ask.py in an isolated script context; patching already-imported module objects has no effect (same limitation documented in Plan 02-04). Additionally, `streamlit_app` can no longer be imported in the test process due to deviation 1 fix.
- **Fix:** Tests 3 & 4 set `active_db=""` which makes `_get_db_adapter("")` return None, triggering the graceful-degradation path. This is consistent with how Plan 02-04 tests use SETTINGS_PATH instead of monkeypatch.
- **Files modified:** `tests/pages/test_ask_page.py`
- **Commit:** ebe5f0e

## Note for Plan 02-06

Plan 02-06 (completed before 02-05 per STATE.md) replaced the 2-stub gallery with the 8-prompt YAML loader. Plan 02-05 is the last plan with behavioral changes to ask.py in Phase 2. The NL-05 placeholder documented in Plan 02-04 is now fully resolved.

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| `cfg_row_cap = 200` hardcoded | app/pages/ask.py | ~227 | Uses AgentConfig default; Plan 02-05 does not change agent config wiring |

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns beyond the plan's threat model.

All T-02-05-01 through T-02-05-05 mitigations verified:
- T-02-05-01: Confirmed params go into structured user message; system prompt's CRITICAL SECURITY INSTRUCTION (SAFE-05) treats all DB-origin data as untrusted
- T-02-05-02: `options = sorted(set(full_catalog) | set(pending))` — hallucinated labels remain selectable; user is the final gate
- T-02-05-03: Accepted — same catalog access as Browse page
- T-02-05-04: Two-layer loop guard (clear pending before call + "Do not ask for more clarification" in prompt)
- T-02-05-05: `pending_params` cleared before second `_run_agent_flow` call; success path writes `last_df/sql/summary`

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| bde89cc | feat | NL-05 param confirmation multiselect + Run Query flow |
| ebe5f0e | feat | page-local _get_db_adapter + NL-05 AppTest coverage |

## Self-Check: PASSED

- app/pages/ask.py: FOUND
- tests/pages/test_ask_page.py: FOUND
- .planning/phases/02-nl-agent-layer/02-05-SUMMARY.md: FOUND
- commit bde89cc: FOUND
- commit ebe5f0e: FOUND
- st.multiselect in ask.py: PASS
- Run Query in ask.py: PASS
- Plan 02-05 placeholder absent: PASS
- test_param_confirmation_multiselect_renders_when_pending: FOUND
- test_run_query_button_shown_only_when_pending: FOUND
