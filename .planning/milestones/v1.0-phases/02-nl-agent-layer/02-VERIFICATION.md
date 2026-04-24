---
phase: 02-nl-agent-layer
verified: 2026-04-24T02:00:00Z
status: human_needed
score: 17/17 must-haves verified (automated)
overrides_applied: 0
human_verification:
  - test: "Ask page happy path — NL question direct-execute"
    expected: "User types a question, agent runs, result table + plain-text summary + collapsed 'Generated SQL' expander appear; Regenerate reloads the answer; history panel shows the entry with timestamp"
    why_human: "Requires a live Ollama or OpenAI backend; AppTest cannot run a real LLM call"
  - test: "NL-05 two-stage param-confirmation flow"
    expected: "Vague question triggers ClarificationNeeded; multiselect labeled 'Parameters to include' appears pre-checked with agent candidates; caption says 'Agent proposed N parameters. Uncheck to remove, search to add.'; clicking 'Run Query' re-invokes agent with confirmed params and renders answer zone"
    why_human: "Requires live LLM returning ClarificationNeeded; second-turn re-run depends on real LLM"
  - test: "OpenAI sensitivity warning and dismiss"
    expected: "Switching to OpenAI in sidebar shows exact warning copy; clicking 'Dismiss' hides it; browser refresh restores it"
    why_human: "Session-state dismiss behavior requires real browser interaction; AppTest cannot simulate cookie/session refresh cycle"
  - test: "Backend switch takes effect on next query"
    expected: "Changing sidebar radio from Ollama to OpenAI changes the LLM used on next 'Ask' click; no cross-session state bleed"
    why_human: "Requires running two successive queries with different sidebar states in a real browser session"
  - test: "Step-cap abort banner and partial output"
    expected: "When agent exceeds 5 steps, page shows red error 'Agent stopped: reached the 5-step limit...' and a collapsed 'Partial output' expander"
    why_human: "Forcing UsageLimitExceeded requires a model that consistently exceeds max_steps; not reliably inducible with a test fixture in isolation"
  - test: "Starter gallery: click a prompt pre-fills input"
    expected: "Clicking any of the 8 gallery buttons fills the question text area with the prompt's question text; gallery disappears after first successful run"
    why_human: "st.rerun() flow after button click requires real Streamlit rendering context; AppTest button interaction does not test the rerun behavior end-to-end"
---

# Phase 2: NL Agent Layer — Verification Report

**Phase Goal:** Users can ask NL questions of ufs_data, receive result table + plain-text summary, with full agent safety harness active and visible.
**Verified:** 2026-04-24T02:00:00Z
**Status:** human_needed — all automated checks pass; 6 items require live LLM backend testing
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | User types NL question, agent proposes candidate params, returns result table + LLM summary | VERIFIED (automated) | `ask.py` wires `run_agent` → `SQLResult.explanation` via `st.write`; `st.dataframe` renders `last_df`; NL-05 `_render_param_confirmation` + `_run_confirmed_agent_flow` are present and wired |
| 2 | User sees LLM-generated SQL in collapsed expander; Regenerate re-runs; history panel tracks session | VERIFIED (automated) | `st.expander("Generated SQL")` + `st.code` + `Regenerate` button in `_render_answer_zone`; `_HISTORY_CAP=50` with `_append_history`; `_render_history` shows `History ({N})` expander |
| 3 | User can switch Ollama (default) / OpenAI; OpenAI shows data-sensitivity warning | VERIFIED (automated) | `streamlit_app.py` uses `st.sidebar.radio` with `default_idx` pointing to first ollama entry; `_render_banners` renders exact NL-10 warning copy; `ask.openai_warning_dismissed` session-scoped |
| 4 | Agent handles 3 question shapes; step-cap and timeout abort cleanly with user-visible message | VERIFIED (automated) | System prompt contains lookup-one-platform / compare-across-platforms / filter-platforms-by-value; `UsageLimits(tool_calls_limit=max_steps)` in `run_agent`; `AgentRunFailure` catches `UsageLimitExceeded` + timeout → exact D-22 copy in `_render_banners` |
| 5 | Starter gallery of 6-10 curated prompts; clicking pre-fills input | VERIFIED (automated) | `config/starter_prompts.example.yaml` has 8 entries; `load_starter_prompts()` fallback chain; `_render_starter_gallery` calls it; gallery capped at `prompts[:8]` |

**Score:** 5/5 truths verified (automated portions)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `requirements.txt` | `nest-asyncio>=1.6` added | VERIFIED | Line 13: `nest-asyncio>=1.6`; `pydantic-ai>=1.0,<2.0` on line 9 |
| `app/adapters/llm/pydantic_model.py` | `build_pydantic_model` factory | VERIFIED | 54 lines; exports `build_pydantic_model`; returns `OpenAIChatModel`/`OllamaModel`; raises `ValueError` for unsupported types |
| `app/services/sql_validator.py` | `validate_sql` + `ValidationResult` (SAFE-02) | VERIFIED | 140 lines; UNION/INTERSECT/EXCEPT rejection (CR-01 fix); CTE rejection (CR-02 fix); comment rejection; table allowlist check |
| `app/services/sql_limiter.py` | `inject_limit` idempotent (SAFE-03) | VERIFIED | 45 lines; regex `\bLIMIT\s+(\d+)\b` IGNORECASE; idempotent confirmed by tests |
| `app/services/path_scrubber.py` | `scrub_paths` (SAFE-06) | VERIFIED | 26 lines; `re.IGNORECASE` flag present (WR-03 fix); replaces `/sys/`, `/proc/`, `/dev/` paths |
| `app/services/ollama_fallback.py` | `extract_json` 3-stage chain (NL-09) | VERIFIED | 68 lines; json.loads → fence-strip → regex `{.*}` DOTALL → None |
| `app/core/agent/nl_agent.py` | Agent factory + run_sql tool + run_agent (NL-06, SAFE-04, SAFE-05) | VERIFIED | 216 lines; `output_type=SQLResult\|ClarificationNeeded`; single `run_sql` tool; SAFE-05 `<db_data>` wrapper; SAFE-04 `UsageLimits`; WR-04 fix: only `type(exc).__name__` returned to LLM |
| `app/pages/ask.py` | Ask page with full NL-01..05 + NL-10 UI | VERIFIED | 433 lines; `nest_asyncio.apply()` first; `@st.cache_resource get_nl_agent`; `ask.*` session state namespace; NL-05 multiselect wired; stub_prompts removed; `load_starter_prompts()` wired |
| `streamlit_app.py` | Ask page in nav; sidebar radio active | VERIFIED | Line 179: `st.Page("app/pages/ask.py", title="Ask")`; `st.sidebar.radio` with `key="active_llm"`; Phase 2 hint caption removed |
| `config/starter_prompts.example.yaml` | 8 curated prompts (ONBD-01) | VERIFIED | 8 entries; 3 lookup + 3 compare + 2 filter; all labels ≤40 chars |
| `.gitignore` | `config/starter_prompts.yaml` gitignored (ONBD-02) | VERIFIED | 1 match for `config/starter_prompts.yaml` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `streamlit_app.py render_sidebar` | `st.session_state['active_llm']` | `key='active_llm'` on `st.sidebar.radio` | WIRED | Line 153: `key="active_llm"` confirmed |
| `build_pydantic_model` | `OpenAIChatModel` / `OllamaModel` | cfg.type dispatch | WIRED | Lines 38-48 confirm both branches |
| `nl_agent.py run_sql tool` | `validate_sql` | explicit import | WIRED | Line 168: `vr = validate_sql(sql, cfg.allowed_tables)` |
| `nl_agent.py run_sql tool` | `inject_limit` | explicit import | WIRED | Line 172: `safe_sql = inject_limit(sql, cfg.row_cap)` |
| `nl_agent.py run_sql tool` | `scrub_paths` (OpenAI only) | conditional call | WIRED | Lines 182-183: `if ctx.deps.active_llm_type == "openai": rows_text = scrub_paths(rows_text)` |
| `nl_agent.py run_agent` | `UsageLimits(tool_calls_limit=...)` | passed to `agent.run_sync` | WIRED | Line 204: `usage_limits = UsageLimits(tool_calls_limit=deps.agent_cfg.max_steps)` |
| `ask.py get_nl_agent` | `build_pydantic_model` | `@st.cache_resource` wrapper | WIRED | Lines 109-119: `model = build_pydantic_model(cfg); return build_agent(model)` |
| `ask.py` | `nl_agent.build_agent / run_agent` | import | WIRED | Lines 20-27: explicit import from `app.core.agent.nl_agent` |
| `streamlit_app.py` | `app/pages/ask.py` | `st.Page` in `st.navigation` | WIRED | Line 179 confirmed |
| `ask.py _render_starter_gallery` | `load_starter_prompts()` | direct call | WIRED | Line 211: `prompts = load_starter_prompts()` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `ask.py _render_answer_zone` | `ask.last_df` | `_run_agent_flow` → `pd.read_sql_query` via DB | Yes — fetched from DB after SQLResult returned | FLOWING |
| `ask.py _render_answer_zone` | `ask.last_summary` | `output.explanation` from LLM-returned `SQLResult` | Yes — LLM-generated summary string | FLOWING |
| `ask.py _render_answer_zone` | `ask.last_sql` | `inject_limit(output.query, ...)` | Yes — validated + limited SQL from LLM | FLOWING |
| `ask.py _render_starter_gallery` | `prompts` | `load_starter_prompts()` → YAML file | Yes — reads `config/starter_prompts.example.yaml` (8 entries) | FLOWING |
| `ask.py _render_param_confirmation` | `pending_params` | `ClarificationNeeded.candidate_params` from LLM | Yes (when LLM returns ClarificationNeeded) | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `validate_sql` accepts valid SELECT | `validate_sql('SELECT * FROM ufs_data', ['ufs_data']).ok` | `True` | PASS |
| `validate_sql` rejects UNION (CR-01) | `validate_sql('SELECT 1 FROM ufs_data UNION SELECT 1 FROM admin', [...]).ok` | `False` | PASS |
| `validate_sql` rejects CTE (CR-02) | `validate_sql('WITH t AS (SELECT * FROM other) SELECT * FROM ufs_data', [...]).ok` | `False` | PASS |
| `scrub_paths` handles uppercase (WR-03) | `scrub_paths('/SYS/BLOCK/sda')` | `'<path>'` | PASS |
| `inject_limit` idempotent | `inject_limit('SELECT * FROM x', 200)` | `'SELECT * FROM x LIMIT 200'` | PASS |
| `inject_limit` clamps above cap | `inject_limit('SELECT * FROM x LIMIT 500', 200)` | `'SELECT * FROM x LIMIT 200'` | PASS |
| Full test suite (171 tests) | `.venv/bin/python -m pytest tests/ -q` | `171 passed, 1 warning` | PASS |
| Phase 2 test subset (96 tests) | pytest on all Phase 2 test files | `96 passed` | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| NL-01 | 02-04 | NL question → result table + LLM summary | SATISFIED | `_run_agent_flow` → `st.dataframe` + `st.write(summary)` |
| NL-02 | 02-04 | SQL in collapsed expander on every NL result | SATISFIED | `st.expander("Generated SQL")` + `st.code(sql)` in `_render_answer_zone` |
| NL-03 | 02-04 | Regenerate re-runs with fresh LLM call | SATISFIED | `Regenerate` button dispatches to `_run_confirmed_agent_flow` or `_run_agent_flow` (WR-02 fix applied) |
| NL-04 | 02-04 | Session question history panel | SATISFIED | `_render_history`, `_append_history`, `_HISTORY_CAP=50` |
| NL-05 | 02-05 | Agent proposes params for user confirmation before SQL | SATISFIED | `_render_param_confirmation` + `st.multiselect` + "Run Query" + `_run_confirmed_agent_flow` |
| NL-06 | 02-03 | Handles 3 question shapes | SATISFIED | System prompt has all 3 shapes; `run_sql` tool executes them |
| NL-07 | 02-01 | Sidebar LLM backend switch | SATISFIED | `st.sidebar.radio` with `key="active_llm"`; default Ollama |
| NL-08 | 02-01 | Both backends use openai SDK | SATISFIED | `build_pydantic_model` uses `OpenAIChatModel`/`OllamaModel` via `openai` SDK |
| NL-09 | 02-02 | Ollama JSON fallback chain | SATISFIED | `extract_json` in `ollama_fallback.py`: 3-stage chain |
| NL-10 | 02-04 | Default Ollama; OpenAI shows sensitivity warning | SATISFIED | `default_idx` selects first ollama in sidebar; `_render_banners` shows warning with exact copy |
| SAFE-02 | 02-02 | SQL validator — single SELECT + allowlist | SATISFIED | `validate_sql` with CR-01 + CR-02 fixes; 18+ tests |
| SAFE-03 | 02-02 | LIMIT injection/clamping | SATISFIED | `inject_limit` idempotent; 11 tests |
| SAFE-04 | 02-03 | Step cap + timeout abort | SATISFIED | `UsageLimits(tool_calls_limit=max_steps)`; `SET SESSION max_execution_time`; `AgentRunFailure` sentinels |
| SAFE-05 | 02-03 | `<db_data>` wrapper + system prompt instruction | SATISFIED | `run_sql` returns `f"<db_data>\n{rows_text}\n</db_data>"`; CRITICAL SECURITY INSTRUCTION in system prompt |
| SAFE-06 | 02-02 | Path scrubbing for OpenAI only | SATISFIED | `scrub_paths` called conditionally when `active_llm_type == "openai"`; `re.IGNORECASE` fix applied |
| ONBD-01 | 02-06 | Starter gallery of 6-10 prompts | SATISFIED | 8-entry YAML; gallery renders up to 8 buttons |
| ONBD-02 | 02-06 | Prompts editable via YAML, no code change | SATISFIED | `load_starter_prompts` fallback chain; `test_user_yaml_overrides_example` confirms |

**All 17 Phase 2 requirements: SATISFIED**

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `ask.py:228` | `cfg_row_cap = 200` hardcoded magic number | Info (IN-01) | Warning message says "200 rows" even if settings override `row_cap`; not a functional blocker |
| `ask.py:133,135` | Hardcoded "5-step limit" and "30 seconds" in abort banner copy | Info (IN-01 extension) | Does not reflect `settings.app.agent.max_steps` / `timeout_s` if overridden; not a functional blocker |
| `nl_agent.py:208` | `AgentRunFailure.last_sql` never populated on step-cap or llm-error | Info (IN-04) | "Partial output" expander opens but shows nothing on step-cap; documented limitation |

None of the above are blockers. All critical (CR-01, CR-02) and warning (WR-01..04) findings from the code review have been fixed and verified.

---

### Review Fixes Confirmed

| Finding | Fix Applied | Verified |
|---------|-------------|---------|
| CR-01: UNION/INTERSECT/EXCEPT bypass | Blanket keyword rejection added before table check | CONFIRMED — `validate_sql('SELECT 1 FROM ufs_data UNION SELECT 1 FROM admin', ...)` returns `ok=False` |
| CR-02: CTE bypass | `T.Keyword.CTE` rejection added | CONFIRMED — `validate_sql('WITH t AS (...) SELECT * FROM ufs_data', ...)` returns `ok=False` |
| WR-01: Display-side missing timeout | `SET SESSION max_execution_time={timeout_ms}` added to ask.py SQLResult execution block | CONFIRMED — lines 331-340 |
| WR-02: Regenerate ignores confirmed params | Regenerate now dispatches `_run_confirmed_agent_flow()` when `confirmed_params` is non-empty | CONFIRMED — lines 247-251 |
| WR-03: Path scrubber case-sensitive | `re.IGNORECASE` added to `_PATH_PATTERN` | CONFIRMED — `scrub_paths('/SYS/BLOCK/sda') == '<path>'` |
| WR-04: exc details sent to LLM | Only `type(exc).__name__` returned; full detail logged server-side | CONFIRMED — line 180: `return f"SQL execution error: {type(exc).__name__}"` |

---

### Human Verification Required

#### 1. Ask Page Happy Path (NL-01, NL-02, NL-03, NL-04)

**Test:** Run `.venv/bin/streamlit run streamlit_app.py`. Click "Ask" in nav. Type "What is the WriteProt status for all platforms?" or similar. Click "Ask".
**Expected:** Spinner "Thinking...", then result `st.dataframe`, row-count caption, `st.write` plain-text summary, collapsed "Generated SQL" expander. Click expander — SQL starts with SELECT and has LIMIT. Click "Regenerate" — answer reloads. Click history entry — question refills.
**Why human:** Requires a live Ollama or OpenAI backend with a connected `ufs_data` database.

#### 2. NL-05 Param Confirmation Two-Turn Flow

**Test:** Type a vague question (e.g. "Show me write protection settings"). Click "Ask".
**Expected:** Spinner, then `st.multiselect("Parameters to include")` with agent candidates pre-checked. Caption: "Agent proposed N parameters. Uncheck to remove, search to add." "Run Query" primary button visible. Click "Run Query" — second spinner, then answer zone renders with table + summary.
**Why human:** Requires LLM returning `ClarificationNeeded`; second-turn re-run depends on real LLM.

#### 3. OpenAI Sensitivity Warning (NL-10)

**Test:** Switch sidebar radio to an OpenAI-type backend. Navigate to Ask page.
**Expected:** Yellow `st.warning` with exact text "You're about to send UFS parameter data to OpenAI's servers. Switch to Ollama in the sidebar for local processing." Click "Dismiss" — warning disappears. Refresh browser — warning returns.
**Why human:** Session dismiss behavior requires browser refresh; AppTest cannot simulate cookie/session cycle.

#### 4. Backend Switch Takes Effect

**Test:** Run one question with Ollama selected, then switch to OpenAI (or vice versa) and run a second question.
**Expected:** Different LLM backend handles the second query; no cross-session state bleed.
**Why human:** Requires two successive queries with different sidebar states.

#### 5. Step-Cap Abort Banner (SAFE-04)

**Test:** Configure `max_steps: 1` in settings (or use a model that always asks for clarification) to force `UsageLimitExceeded`.
**Expected:** Red `st.error("Agent stopped: reached the 5-step limit. Try rephrasing your question with more specific parameters.")` appears. Collapsed "Partial output" expander below.
**Why human:** Forcing step-cap in a controlled way requires either a specially configured model or settings override.

#### 6. Starter Gallery Prompt Pre-Fill (ONBD-01)

**Test:** Navigate to Ask page on fresh session (no history). Click any starter gallery button.
**Expected:** Button click fills the question text area with the prompt's question text; gallery remains visible until "Ask" is submitted. After first successful run, gallery disappears.
**Why human:** `st.rerun()` triggered by button click needs real Streamlit rendering; AppTest button-click does not test the full rerun → gallery-hide cycle.

---

### Gaps Summary

No automated gaps found. All 17 requirements are satisfied by code that exists, is substantive, is wired, and has data flowing through it. All code review critical and warning findings (CR-01, CR-02, WR-01 through WR-04) are confirmed fixed by the 02-REVIEW-FIX.md report and verified against the actual source.

The 6 human verification items above are standard Streamlit UI behaviors that require a live LLM backend and real browser session — they are not regressions or gaps, they are the expected end-to-end validation gate for any Streamlit NL-agent page.

Cross-phase regression: Full test suite runs 171 tests (Phase 1 + Phase 2) — 171 passed.

---

_Verified: 2026-04-24T02:00:00Z_
_Verifier: Claude (gsd-verifier)_
