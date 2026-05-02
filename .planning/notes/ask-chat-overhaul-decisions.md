---
title: Ask feature → agentic chat overhaul — architectural decisions
date: 2026-05-03
context: Pre-phase exploration for replacing one-shot Ask with multi-step PydanticAI agentic chat
source: /gsd-explore session
---

# Ask Feature → Agentic Chat Overhaul

This note captures the architectural decisions reached during a `/gsd-explore` session. It exists to give the phase planner full context so it doesn't have to rediscover the vision.

## Motivating user example

> "Right now even for a basic question like 'compare SM8850 vs SM8650', it plainly says 'Something went wrong. (SQL rejected: UNION / INTERSECT / EXCEPT are not allowed) Try rephrasing your question' and it's the end of story."

Today's Ask is a terminal Q&A: one LLM call → one SQL → if it fails, the user is stuck. The user wants it to feel like *chatting with an AI agent*, with visible reasoning and follow-up turns.

## Vision (decisions made)

| Decision | Choice | Why |
|---|---|---|
| **Primary capability gap** | Multi-step reasoning (agent runs multiple queries, inspects results, reasons across them) | User picked this over multi-turn memory, iterative refinement, and conversational tone — though all four come along for the ride. |
| **Guard-rail rejection handling** | Feed rejection back as a **tool-result error**, let the agent retry on its own — do NOT catch+rewrite client-side | Solves the SM8850 vs SM8650 UNION case automatically: the model sees `"REJECTED: UNION not allowed. Split into separate SELECTs and merge."` and emits two queries instead. Pattern used by Cursor agent loop and Defog. |
| **Streaming UX** | SSE with structured event types: `thought` / `tool_call` / `tool_result` / `final` | Reasoning is rendered live, so the user sees the agent thinking. PydanticAI's `agent.run_stream()` yields these natively. |
| **Persistence** | **Ephemeral, session-only.** No saved-thread sidebar (yet). | User explicitly chose this over named threads / Cursor-style auto-save. Keeps first cut shippable; sidebar is a follow-up if it's actually wanted. |
| **UI lockout** | Disable input + show visible **Stop button** while agent is reasoning. Stop POSTs to `/ask/cancel/{turn_id}`; server flips a `cancel_event` the agent loop checks between tool calls. | User explicitly asked: "during the reasoning process, I want it to show visually it's processing something so user cannot interact with it." |
| **Visual design anchor** | Pin chat UI to **Dashboard_v2.html** design language | Project-wide preference: anchor v2.0 frontend grey areas to Dashboard_v2.html; only ask about gaps. |

## Stack alignment (no new deps required for the core pattern)

Every primitive needed is already in the v2.0 stack or trivially addable:

| Need | Tool | Status |
|---|---|---|
| Agent loop | **PydanticAI** with `@agent.tool` | Already in deps (`pydantic-ai>=1.0,<2.0`) |
| Server-sent events | **sse-starlette** (`EventSourceResponse`) | New dep, small |
| Client-side SSE | **HTMX SSE extension** (`hx-ext="sse"`, `sse-connect`, `sse-swap`) | Already in stack |
| Per-event fragment rendering | **jinja2-fragments** | Already in deps |
| Conversation history | PydanticAI `ModelMessage` list, replay last N turns into `agent.run(message_history=...)` | Native — no new lib |
| Ephemeral session store | In-memory dict keyed by session/turn id (sufficient for ephemeral scope) | None |

## Tool surface for the agent

Beyond `run_sql`, expose:

- `inspect_schema()` → returns column list + types for `ufs_data`
- `get_distinct_values(column)` → tool-based discovery beats prompt-stuffing all distincts (5-10× token saving on wide EAV table)
- `sample_rows(where_clause, limit)` → quick peek, capped
- `count_rows(where_clause)` → cheap pre-flight before a heavy query
- `present_result(dataframe_id, summary, chart_spec)` → **forces** the final answer to be structured (df + chart hint + NL summary). Vanna and Dataherald both enforce this via Pydantic `result_type` unions.

The `run_sql` tool wraps the existing SQL guard. When the guard rejects, the tool returns a string starting with `REJECTED:` — the agent reads the reason and retries.

## Frontend pattern (FastAPI + HTMX, no React)

```html
<div hx-ext="sse"
     sse-connect="/ask/stream/{turn_id}"
     sse-swap="thought,tool_call,tool_result,final">
  <!-- jinja2-fragments swap a per-event-type partial as each event arrives -->
</div>
```

Each SSE frame is `event: <type>` + JSON payload. Server-side, the streaming endpoint iterates over `agent.run_stream(...)` and yields fragments rendered from per-event Jinja partials.

## What NOT to do

- ❌ Don't use LangChain/LangGraph — PydanticAI is already the chosen NL agent framework (per `.planning/PROJECT.md` and the v1.0 research carried into v2.0).
- ❌ Don't catch SQL guard rejections client-side and rewrite — let the model do it via tool feedback.
- ❌ Don't roll the full conversation history into one fat prompt — use `message_history=` so token budget stays bounded.
- ❌ Don't accumulate distinct values into the system prompt — expose them as a tool instead.
- ❌ Don't ship a saved-threads sidebar yet — explicitly out of scope per persistence decision.

## Open questions for the planner

1. **Stop-button cancellation semantics** — abort mid-SQL via pymysql `kill_query`, or only check `cancel_event` between tool calls? (Probably the latter for v1; SQL kill is harder.)
2. **Failure mode when guard rejects N times in a row** — bound the retry loop so the agent doesn't burn the whole token budget on rewrites.
3. **What does `present_result` actually render?** — table only, table + Plotly, table + summary card? Should match Dashboard_v2.html's result-display pattern.
4. **Is this a replacement of the current Ask page, or a new page?** — affects routing, auth integration, and migration path.

## Sources (from research pass during exploration)

- [PydanticAI Tools](https://ai.pydantic.dev/tools/)
- [PydanticAI Streaming](https://ai.pydantic.dev/output/#streaming-structured-output)
- [PydanticAI Message History](https://ai.pydantic.dev/message-history/)
- [HTMX SSE Extension](https://htmx.org/extensions/server-sent-events/)
- [sse-starlette PyPI](https://pypi.org/project/sse-starlette/)
- [Dataherald GitHub](https://github.com/Dataherald/dataherald)
- [Cursor Agent Blog](https://www.cursor.com/blog)
