---
created: 2026-05-07T15:11:01.627Z
title: Enforce configured LLM model — drop hardcoded fallbacks + decide on app.agent.model
area: llm
files:
  - app/adapters/llm/pydantic_model.py:43
  - app/adapters/llm/pydantic_model.py:48
  - app_v2/services/summary_service.py:146
  - app_v2/services/summary_service.py:247-248
  - app_v2/routers/ask.py:254
  - app/core/agent/config.py
  - config/settings.yaml:30
---

## Problem

Deployment target is corporate OpenAI-compatible endpoint serving `gpt-oss-120b`
only — never real OpenAI. Today's code has dormant fallbacks that would silently
substitute a different model if `cfg.model` were ever blank, plus one
already-broken setting:

1. **Dormant fallbacks** (`cfg.model or "<literal>"`) — fire only when settings.yaml
   omits `model`, but on a corporate endpoint a literal like `"gpt-4o-mini"` would
   produce a confusing 4xx instead of a clean config error.
2. **Dead config:** `app.agent.model` (config/settings.yaml:30) is **never read by
   any production code** (verified 2026-05-08 via grep across `app/` and `app_v2/`
   for `agent_cfg.model` / `agent.model` — zero hits). The `AgentConfig` field
   exists with the documented contract "empty string means inherit from
   LLMConfig.model", but `app_v2/routers/ask.py:254` calls
   `build_pydantic_model(llm_cfg)` directly and ignores `agent_cfg.model`.

**PREREQ before changing code: smoke-test tool calling on the corporate endpoint.**
PydanticAI's chat agent (`build_chat_agent` + `@agent.tool` for `run_sql`) sends
`tools=[...]` on `/v1/chat/completions` and parses `tool_calls` back. gpt-oss-120b
natively supports tool calling (harmony format) and vLLM/SGLang/TGI all expose it
through the OpenAI-compatible shape — but corporate proxies sometimes:

- silently strip the `tools` parameter,
- return tool args inside `content` as plain text,
- emit `tool_calls[].function.arguments` as a raw string instead of structured JSON.

Any of those breaks PydanticAI's loop without an obvious error. A 30-second curl
against the corporate `/v1/chat/completions` with a minimal `tools` payload tells
you whether the rest of this todo is worth doing.

## Solution

**Phase 0 — smoke test (blocking):**

Run a minimal request against the corporate endpoint:

```bash
curl -sS "$ENDPOINT/v1/chat/completions" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [{"role":"user","content":"What is 2+2? Use the calc tool."}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "calc",
        "description": "Evaluate an arithmetic expression",
        "parameters": {
          "type": "object",
          "properties": {"expr": {"type": "string"}},
          "required": ["expr"]
        }
      }
    }],
    "tool_choice": "auto"
  }' | jq '.choices[0].message'
```

Verify the response has `tool_calls[0].function.{name,arguments}` populated and
`arguments` parses as JSON. If broken, do NOT proceed with the enforcement
change — the chat agent will silently fail; investigate proxy/server
configuration first.

**Phase 1 — enforce (only after smoke test passes):**

1. `app/adapters/llm/pydantic_model.py:43` — drop `or "gpt-4o-mini"`:
   ```python
   return OpenAIChatModel(cfg.model, provider=provider)
   ```
2. `app/adapters/llm/pydantic_model.py:48` — drop `or "qwen2.5:7b"`:
   ```python
   return OllamaModel(cfg.model, provider=provider)
   ```
3. `app_v2/services/summary_service.py:146` — drop the type-conditional fallback:
   ```python
   model = cfg.model
   ```
4. `app_v2/services/summary_service.py:247-248` — drop same fallback in
   `SummaryResult.llm_model`:
   ```python
   llm_model=cfg.model,
   ```
5. **Fail-fast:** at the top of `build_pydantic_model` and
   `_call_llm_with_text`, raise `ValueError("LLMConfig.model is required ...")`
   when `cfg.model` is empty — clean config error vs confusing 4xx from the
   corporate endpoint.

**Phase 2 — decide on `app.agent.model` (pick one, don't leave dead config):**

- **(a) Wire it up:** in `app_v2/routers/ask.py:254`, if
  `agent_cfg.model` is non-empty, build a derived `LLMConfig` (or pass model
  override into `build_pydantic_model`) so the agent uses the override. Keeps
  the documented contract; useful if the agent ever needs a different model
  than summaries (e.g. accuracy escalation per AGENT-09).
- **(b) Delete it:** remove `model` from `AgentConfig`
  (`app/core/agent/config.py`) and from `config/settings.yaml:30`. With one
  corporate model, there's no need for an agent-specific override and dead
  config is worse than no config.

Recommendation: **(b) delete**, unless there's a near-term reason to escalate
the agent to a different corporate model than the summary service uses.

**Phase 3 — tests:**

- Update tests that pass empty `cfg.model` to either set a real model or assert
  the new `ValueError`.
- Add a regression test: `LLMConfig(type="openai", model="")` → `ValueError`
  from `build_pydantic_model`.
