---
phase: "02-nl-agent-layer"
plan: "04"
subsystem: ask-page-ui
tags: [streamlit, ask-page, NL-01, NL-02, NL-03, NL-04, NL-10, human-verify]
dependency_graph:
  requires: [02-03]
  provides:
    - app/pages/ask.py (Ask page render function — banner zone, title, history, question, answer, gallery)
    - streamlit_app.py Ask navigation entry (between Browse and Settings)
    - tests/pages/test_ask_page.py (6 AppTest smoke tests)
  affects:
    - app/pages/ask.py (Plan 02-05 injects param-confirmation row, replaces "Run" button)
    - app/pages/ask.py (Plan 02-06 replaces stub gallery with YAML-loaded prompts)
tech_stack:
  added:
    - nest_asyncio (applied at module top to fix Pitfall 6)
  patterns:
    - "@st.cache_resource def get_nl_agent(llm_name) — agent cached per backend"
    - "ask.* session state namespace with _DEFAULTS dict initialized once per render"
    - "AppTest.from_file with default_timeout=60 for pydantic_ai cold-start (~15s)"
    - "SETTINGS_PATH env var fixture pattern for AppTest sensitivity warning tests"
key_files:
  created:
    - app/pages/ask.py
    - tests/pages/__init__.py
    - tests/pages/test_ask_page.py
  modified:
    - streamlit_app.py
decisions:
  - "AppTest default_timeout=60 required — pydantic_ai import adds ~12-15s cold-start"
  - "SETTINGS_PATH env var used as test fixture for sensitivity warning tests — monkeypatching the imported module has no effect on AppTest's isolated script execution context"
  - "from_string approach for warning tests rejected — duplicate widget key error when from_string re-calls render functions on a module already imported by the AppTest runner"
  - "ask.py calls get_db_adapter via lazy import (inside _run_agent_flow) to avoid circular import at module load"
metrics:
  duration: "18 minutes"
  completed_date: "2026-04-24"
  tasks_completed: 2
  files_changed: 4
requirements_satisfied: [NL-01, NL-02, NL-03, NL-04, NL-10]

needs_human_verify:
  - step: "Click 'Ask' in nav — confirm between Browse and Settings"
  - step: "Empty state shows 'History (0)' expander, question text area, 'Try asking...' gallery with 2 stub buttons"
  - step: "Sidebar: select Ollama — no warning banner; select OpenAI — warning appears with exact copy 'You're about to send UFS parameter data to OpenAI's servers. Switch to Ollama in the sidebar for local processing.'"
  - step: "Click 'Dismiss' — warning disappears; refresh browser — warning returns"
  - step: "Type a question and click 'Run' — spinner 'Thinking...', then result table + row-count caption + st.write summary + collapsed 'Generated SQL' expander"
  - step: "Click 'Regenerate' in the SQL expander — answer reloads"
  - step: "Click history entry — question is refilled in the text area"
  - step: "If agent returns ClarificationNeeded — '[Plan 02-05 placeholder]' info message (expected intermediate state)"
---

# Phase 2 Plan 04: Ask Page Scaffold Summary

**One-liner:** Ask page scaffold with NL-10 OpenAI sensitivity warning, SAFE-04 abort banner, History expander (LRU cap 50), starter gallery (2 stub prompts), and single-shot run_agent flow wired end-to-end.

## What Was Built

### app/pages/ask.py (308 lines)

Full Ask page render function meeting all must_haves from the plan:

**Session state:** 10 keys in `ask.*` namespace initialized once via `_DEFAULTS` dict. `_HISTORY_CAP = 50` with LRU drop on overflow.

**Banner zone (`_render_banners`):**
- Priority 1 (SAFE-04): `st.error(...)` with exact D-22 step-cap and timeout copy variants; collapsed "Partial output" expander showing last SQL
- Priority 2 (NL-10): `st.warning(...)` with exact D-25 copy when OpenAI is active and not dismissed; "Dismiss" secondary button sets `ask.openai_warning_dismissed = True`
- Banner priority enforced: abort present → skip sensitivity warning

**History panel (`_render_history`):** Collapsed `History ({N})` expander above question input; reversed order; 5:1 column split for question label vs timestamp; failed entries get ` ✗` Unicode suffix; truncation caption at bottom when cap hit.

**Question input (`_render_question_input`):** `st.text_area` with `key="ask.question"` and exact UI-SPEC placeholder.

**Answer zone (`_render_answer_zone`):** `st.dataframe` + row-count `st.caption` + `st.write(summary)` + collapsed "Generated SQL" expander with `st.code` and "Regenerate" secondary button.

**Agent flow (`_run_agent_flow`):**
- Guards: empty question, no LLM, no DB, LLM config not found, agent build failed
- `AgentRunFailure` path: sets `ask.last_abort`, appends failed history entry
- `ClarificationNeeded` path: stores `ask.pending_params`, shows `[Plan 02-05 placeholder]` info — seam for Plan 02-05
- `SQLResult` path: re-validates + re-limits the SQL, fetches DataFrame via `_execute_read_only` (falls back to `db.run_query`), stores `ask.last_df/sql/summary`, appends ok history entry

**Starter gallery (`_render_starter_gallery`):** 2 stub prompts in 4-column grid; hidden once `ask.history` has any entry.

**`get_nl_agent(llm_name)` `@st.cache_resource`:** Builds + caches PydanticAI Agent per LLM backend name. Returns None on missing config.

### streamlit_app.py

Navigation updated (D-17 ordering):
```python
st.Page("app/pages/browse.py",   title="Browse",   ..., default=True),
st.Page("app/pages/ask.py",      title="Ask",      icon=":material/chat:"),
st.Page("app/pages/settings.py", title="Settings", ...),
```
The `# Phase 2 — uncomment when NL agent is wired` comment + `nl_agent.py` placeholder removed.

### tests/pages/test_ask_page.py (6 tests, all passing)

| Test | What it verifies |
|------|-----------------|
| `test_ask_page_module_imports_without_error` | ask.py runs in AppTest without raising |
| `test_ask_page_shows_title` | `st.title("Ask")` present |
| `test_ask_page_shows_starter_gallery_on_empty_history` | "Try asking..." subheader when history empty |
| `test_ask_page_shows_history_panel_with_zero_count` | "History (0)" expander label on empty state |
| `test_ask_page_sensitivity_warning_shown_when_openai_active` | NL-10 warning text appears for openai LLM |
| `test_ask_page_no_sensitivity_warning_when_ollama` | No warning for ollama LLM |

**All 6 pass in ~19s** (pydantic_ai cold-start ~15s per AppTest process isolation).

## Known Intermediate States

1. **ClarificationNeeded branch is a stub:** When the agent returns `ClarificationNeeded`, the page shows `st.info("[Plan 02-05 placeholder] {message}")` and stores `ask.pending_params`. Plan 02-05 replaces this with the `st.multiselect` + "Run Query" confirmation row.

2. **"Run" button is scaffolding:** The `st.button("Run", type="primary", key="ask.run")` in `render()` is a plan-internal placeholder. Plan 02-05 removes it and introduces the param-confirmation flow's "Run Query" button as the primary CTA.

3. **Starter gallery uses 2 stub prompts:** `_render_starter_gallery()` has a hardcoded 2-item list. Plan 02-06 replaces it with `load_starter_prompts()` reading `config/starter_prompts.yaml` and rendering all 8 prompts.

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| `stub_prompts` (2-item list) | app/pages/ask.py | ~142 | Intentional scaffold — Plan 02-06 wires YAML loader |
| `[Plan 02-05 placeholder]` info | app/pages/ask.py | ~193 | Intentional — Plan 02-05 implements confirmation flow |
| `cfg_row_cap = 200` hardcoded | app/pages/ask.py | ~153 | Uses AgentConfig default; refined when agent runs with actual cfg |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] AppTest default_timeout increased from 10s to 60s**
- **Found during:** Task 2 test execution
- **Issue:** ask.py's import of `pydantic_ai` and `nest_asyncio` at module level adds ~12-15s to every AppTest cold start. Plan specified `default_timeout=10` which caused all from_file tests to time out.
- **Fix:** All `AppTest.from_file` calls use `default_timeout=60`.
- **Files modified:** `tests/pages/test_ask_page.py`

**2. [Rule 1 - Bug] Sensitivity warning test approach changed from monkeypatch to SETTINGS_PATH fixture**
- **Found during:** Task 2 test execution
- **Issue:** Plan specified `monkeypatch.setattr(ask_mod, "load_settings", fake_load_settings)`. AppTest runs ask.py in an isolated execution context — patching the already-imported module object does not affect the script's `load_settings` call inside AppTest. The warning never appeared in test assertions.
- **Fix:** Tests create a temporary YAML file with the desired LLM config and set `SETTINGS_PATH` env var before the AppTest run. The `load_settings()` call inside the script then reads from the fixture file. The `from_string` with inline patching was also tried but caused `StreamlitDuplicateElementKey` because the already-loaded ask.py module ran `render()` at import time.
- **Files modified:** `tests/pages/test_ask_page.py`

## Threat Surface Scan

All T-02-04-01 through T-02-04-07 mitigations verified:
- T-02-04-01: Ollama is default (sidebar `default_idx` selects first ollama entry); NL-10 warning fires on first openai use per session
- T-02-04-02: `ask.openai_warning_dismissed` is session-scoped only (in `_DEFAULTS`, not persisted to YAML)
- T-02-04-03: `st.write(summary)` and `st.code(sql)` — no `unsafe_allow_html=True` anywhere in ask.py
- T-02-04-04: `get_nl_agent` cached on `llm_name` — backend switch produces different cache entry
- T-02-04-05: `_HISTORY_CAP = 50` with LRU drop enforced in `_append_history`
- T-02-04-06: Accepted — intranet only; Streamlit has no native CSRF token support
- T-02-04-07: Accepted — agent is stateless between runs

No new network endpoints, auth paths, or file access patterns introduced beyond the plan's threat model.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 600c3f9 | feat | Ask page scaffold — banner zone, history, gallery, agent flow |
| f873700 | feat | Activate Ask page in st.navigation + AppTest smoke tests |

## Self-Check: PASSED
