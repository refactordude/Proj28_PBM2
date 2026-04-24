---
phase: "02-nl-agent-layer"
plan: "01"
subsystem: "llm-adapter"
tags: [pydantic-ai, llm-adapter, sidebar, NL-07, NL-08, deps]
dependency_graph:
  requires: []
  provides: [build_pydantic_model, active_llm-session-state, nest-asyncio]
  affects: [streamlit_app.py, app/adapters/llm/pydantic_model.py, requirements.txt]
tech_stack:
  added: [pydantic-ai 1.86.0, openai 2.32.0, sqlparse 0.5.5, nest-asyncio 1.6.0]
  patterns: [PydanticAI OpenAIChatModel+OpenAIProvider, OllamaModel+OllamaProvider, st.sidebar.radio with default_idx]
key_files:
  created:
    - app/adapters/llm/pydantic_model.py
    - tests/adapters/__init__.py
    - tests/adapters/test_pydantic_model.py
  modified:
    - requirements.txt
    - streamlit_app.py
decisions:
  - "OpenAI SDK 2.x requires api_key at OpenAIProvider instantiation — unit tests use dummy key _DUMMY_KEY to satisfy SDK validation without network calls"
  - "st.navigation left untouched — ask.py nav entry deferred to Plan 02-04 per plan instruction to avoid FileNotFoundError at runtime"
  - "OllamaProvider with explicit base_url=f'{endpoint}/v1' per RESEARCH.md Pitfall 2 — parallel to legacy OllamaAdapter (not a replacement)"
metrics:
  duration: "7 minutes"
  completed_date: "2026-04-24"
  tasks_completed: 3
  files_changed: 5
requirements_satisfied: [NL-07, NL-08]
---

# Phase 2 Plan 01: NL Agent Layer Bootstrap Summary

**One-liner:** PydanticAI model factory (`build_pydantic_model`) + sidebar radio selector activation using `OpenAIChatModel`/`OllamaModel` with `gpt-4o-mini`/`qwen2.5:7b` defaults.

## What Was Built

### Task 1: nest-asyncio added and Phase 2 deps installed
- `nest-asyncio>=1.6` added to `requirements.txt` (only missing Phase 2 dependency)
- `pydantic-ai 1.86.0`, `openai 2.32.0`, `sqlparse 0.5.5`, `nest-asyncio 1.6.0` now importable from `.venv`
- `pydantic-ai`, `openai`, `sqlparse` were already pinned in `requirements.txt` but not installed

### Task 2: build_pydantic_model() factory (TDD)
`app/adapters/llm/pydantic_model.py` exports `build_pydantic_model(cfg: LLMConfig)`:

- **Supported types:** `"openai"` → `OpenAIChatModel` + `OpenAIProvider`; `"ollama"` → `OllamaModel` + `OllamaProvider`
- **Default model fallbacks:** `gpt-4o-mini` for openai, `qwen2.5:7b` for ollama
- **Default endpoint:** `None` for openai (uses `api.openai.com/v1`), `http://localhost:11434/v1` for ollama
- **Unsupported types:** raises `ValueError("Unsupported LLM type for PydanticAI agent: ...")` — covers `anthropic`, `vllm`, `custom` (T-02-01-03)
- **api_key:** passed to `OpenAIProvider` but never logged (T-02-01-01)
- **Parallel path:** does NOT replace legacy `OpenAIAdapter`/`OllamaAdapter` — those remain for Phase 1 `generate_sql`/`stream_text`

5 unit tests in `tests/adapters/test_pydantic_model.py` — all pass. Tests use dummy api_key (`sk-test-dummy-...`) to satisfy OpenAI SDK 2.x's key validation at provider construction time without making network calls.

### Task 3: Sidebar LLM radio selector activated
`streamlit_app.py` `render_sidebar()` changes:
- `st.sidebar.selectbox` → `st.sidebar.radio` with `key="active_llm"`
- Phase 2 hint caption removed: `"LLM backend selection takes effect in Phase 2 (Ask page)."` deleted
- `default_idx` defaults to first `ollama`-type entry (NL-10); falls back to index 0 if none
- `st.navigation` untouched — `ask.py` page registration deferred to Plan 02-04 (see Deviations)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] OpenAI SDK 2.x requires api_key at provider construction**
- **Found during:** Task 2 GREEN phase — all openai tests failed with `OpenAIError: The api_key client option must be set...`
- **Issue:** `OpenAIProvider(api_key=None, ...)` in `openai` SDK 2.x raises immediately if no `OPENAI_API_KEY` env var is set, unlike SDK 1.x which deferred the check to the first API call
- **Fix:** Updated tests to pass `api_key=_DUMMY_KEY` (`"sk-test-dummy-key-for-unit-tests-only"`) in all openai-type `LLMConfig` fixtures. The factory implementation is unchanged — it correctly passes `cfg.api_key or None` to the provider; the fix was purely in test fixtures.
- **Files modified:** `tests/adapters/test_pydantic_model.py`
- **Commit:** d6756f7

## Known Stubs

None — all functionality is fully wired. The `build_pydantic_model` factory returns real PydanticAI model objects. The sidebar radio writes to real session state. No placeholder values flow to UI rendering.

## Threat Flags

No new security-relevant surface introduced beyond what the plan's threat model covers:
- `build_pydantic_model` does not open network connections at construction time (connections are deferred to agent run)
- `api_key` from `LLMConfig` is passed to `OpenAIProvider` without logging (T-02-01-01 satisfied)
- Unsupported `cfg.type` raises `ValueError` immediately (T-02-01-03 satisfied)

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Task 1 | 72575bb | chore(02-01): add nest-asyncio>=1.6 and install Phase 2 deps |
| Task 2 RED | 92c278e | test(02-01): add failing tests for build_pydantic_model factory |
| Task 2 GREEN | d6756f7 | feat(02-01): add build_pydantic_model() PydanticAI model factory |
| Task 3 | 7ccb878 | feat(02-01): activate sidebar LLM radio selector (NL-07) |

## Self-Check: PASSED

All files exist, all 4 commits verified, all 5 tests pass, syntax check clean.
