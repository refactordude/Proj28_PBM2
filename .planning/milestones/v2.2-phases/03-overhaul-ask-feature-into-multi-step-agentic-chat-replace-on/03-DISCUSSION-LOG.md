# Phase 3: Overhaul Ask feature into multi-step agentic chat — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-03
**Phase:** 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
**Areas discussed:** Stop & failure boundaries, present_result render shape, Routing & NL-05 migration, Chat transcript shape

---

## Stop & failure boundaries

### Q1: Stop-button cancellation semantics — what does pressing Stop actually do?

| Option | Description | Selected |
|--------|-------------|----------|
| Cooperative only (Recommended) | POST /ask/cancel/{turn_id} flips a cancel_event the agent loop checks BETWEEN tool calls. A long SQL statement runs to completion before the loop exits. Matches the existing AgentConfig.timeout_s safety net. Simple and ships cleanly with PydanticAI. | ✓ |
| Cooperative + mid-SQL kill | Cooperative between tools, PLUS a best-effort pymysql KILL QUERY against the active connection so a long-running SQL is interrupted on the DB side. Adds connection-tracking complexity and a second failure path. | |

**User's choice:** Cooperative only — recorded as D-CHAT-01.

### Q2: Guard-rejection retry cap — when the SQL guard returns REJECTED:... and the agent retries, how many rewrites do we allow before giving up on this turn?

| Option | Description | Selected |
|--------|-------------|----------|
| 3 retries, then surface error (Recommended) | Agent gets 3 chances to rewrite a rejected query before the turn aborts with a 'still rejected after 3 attempts' final event. Bounded token burn; matches Cursor/Defog defaults. | |
| Tied to overall step budget | No separate retry counter — rejections just consume from the total step budget. Simpler accounting, but one bad SQL can eat the whole turn. | |
| Looser — 5 retries | 5 chances before giving up. More forgiving for edge cases like the SM8850 vs SM8650 UNION example, at the cost of token burn. | ✓ |

**User's choice:** Looser — 5 retries — recorded as D-CHAT-02.

### Q3: Total per-turn step budget — how many tool calls can the agent make in one user turn before forced abort?

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse existing AgentConfig.max_steps (Recommended) | Today's max_steps setting already governs the v1.0 agent. Keep one knob; default value already chosen for this workload. Add a UI abort if exceeded with a 'reasoning budget exhausted' message. | |
| New agent_chat.max_steps with higher default | Multi-step chat needs more headroom than the v1.0 single-turn agent. Add a separate config key (e.g., 12) so the v1.0 budget stays tight while chat gets room to breathe. | ✓ |

**User's choice:** New agent_chat.max_steps with higher default — recorded as D-CHAT-03.

### Q4: Non-rejection failures — timeout, LLM 5xx, SSE stream drop. How do these surface in the chat?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline error event in transcript (Recommended) | Render a final 'error' event card in the chat (red/amber border per Dashboard_v2.html palette: --red, --amber). Reason + retry-this-question button. Conversation history is preserved; user can continue. | ✓ |
| Replace whole answer-zone with abort banner | Match v2.0 Phase 6's existing _abort_banner.html pattern — swap the whole zone with a banner. Simpler but discards the in-progress transcript on error. | |

**User's choice:** Inline error event in transcript — recorded as D-CHAT-04.

---

## present_result render shape

### Q1: What does the agent's final `present_result` event actually render?

| Option | Description | Selected |
|--------|-------------|----------|
| Table + LLM summary card (Recommended) | Top: short NL summary card (1–2 sentences — Dashboard_v2.html `.kpi`/`.callout` style with `--accent-soft` background). Below: pivot/wide-form table reusing Browse's `.pivot-table` styling. No chart by default. | (initial pick — superseded) |
| Table + summary + Plotly chart | Same as Recommended but also embed a Plotly chart when the agent decides numeric data warrants it (`chart_spec` in present_result schema). Reuses v1.0 Plotly path. Higher implementation cost. | ✓ (after clarification) |
| Table only | Strip down: just the result table, no NL summary, no chart. Fastest to ship, but loses the 'agentic chat' feel. | |

**User's choice (initial):** Table + summary + Plotly chart.
**Conflict:** Q2 picked "Defer chart to a follow-up phase" — contradicted Q1.
**Clarifier asked:** "You picked 'Table + summary + Plotly chart' AND 'Defer chart to a follow-up phase' — which do you actually want?"
- Resolved: **Table + summary + Plotly chart in Phase 3** — recorded as D-CHAT-05.

### Q2: When the agent emits a chart (if Plotly is in scope), who decides the chart type?

| Option | Description | Selected |
|--------|-------------|----------|
| Defer chart support to a follow-up phase (Recommended) | Lock present_result.chart_spec to None for this phase — ship table + summary only. | (initial pick — superseded by clarification above) |
| Agent chooses, user toggles | Agent fills `chart_spec` with a recommended chart type when numeric columns dominate; UI shows a small chart-type toggle (bar/line/scatter) the user can override post-hoc. | |
| User picks from a small toolbar | Agent never picks; result card has a mini toolbar (Bar / Line / Scatter / None). | |

**User's choice (initial):** Defer chart — but conflicted with Q1.
**Re-asked after clarification ("now that chart is in scope, who picks?"):**

| Option | Description | Selected |
|--------|-------------|----------|
| Agent picks, user toggles (Recommended) | Agent fills chart_type based on numeric-column heuristics. UI toggle for post-hoc override. | |
| User picks from a small toolbar | Agent never picks chart_type. | |
| Agent picks, no user override | Whatever the agent puts in chart_spec is what renders. Simpler UI. | ✓ |

**User's choice:** Agent picks, no user override — recorded as D-CHAT-06.

### Q3: Visual anchor — how closely should the result card mimic Dashboard_v2.html?

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse panel/ph + add result-specific tokens (Recommended) | Reuse existing `.panel`, `.panel-header`, `.panel-body` from app.css (already aligned to Dashboard_v2.html since Phase 02). Add chat-specific tokens for the message bubble + summary card using `--accent-soft`/`--green-soft`/`--red-soft`/`--amber-soft`. No new CSS framework. | ✓ |
| Pixel-port chat-specific styles from Dashboard_v2.html | Open Dashboard_v2.html, extract specific selectors and port them into the Ask chat surface. More fidelity, more CSS churn, more risk of drifting from Phase 02's tokens. | |

**User's choice:** Reuse panel/ph + add result-specific tokens — recorded as D-CHAT-07.

---

## Routing & NL-05 migration

### Q1: Where does the new agentic chat live route-wise?

| Option | Description | Selected |
|--------|-------------|----------|
| Replace /ask in place (Recommended) | The existing `/ask` route stays; the page rewrites under it. POST /ask/query is replaced by POST /ask/chat (start turn) + GET /ask/stream/{turn_id} (SSE) + POST /ask/cancel/{turn_id}. | ✓ |
| New /chat (or /ask/chat) page, keep /ask one-shot | Both flows coexist for a release: old one-shot Ask at /ask, new agentic chat at a new path. | |
| New /chat, delete /ask immediately | Clean break — ship `/chat`, retire `/ask`. | |

**User's choice:** Replace /ask in place — recorded as D-CHAT-08.

### Q2: What happens to the v2.0 Phase 6 NL-05 two-turn confirmation?

| Option | Description | Selected |
|--------|-------------|----------|
| Delete — agent's tools cover the same need (Recommended) | The new agent's `inspect_schema()` + `get_distinct_values()` tools let it discover candidate (InfoCategory, Item) params on its own without a hard-coded UI confirmation step. Delete `_confirm_panel.html`, `loop-aborted` branch, NL-05-specific code in nl_service. | ✓ |
| Keep — agent escalates ambiguity to a confirm panel | When the agent can't disambiguate via tools, it emits a special `clarification_needed` event that renders the existing `_confirm_panel.html`. | |
| Keep but rewire — confirm panel becomes a tool the agent calls | Add an `ask_user_to_pick(candidates)` agent tool that emits the picker UI; user's selection feeds back as a tool result. | |

**User's choice:** Delete — recorded as D-CHAT-09.

### Q3: What about the 8 starter chips and the LLM dropdown?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep both, adapt placement (Recommended) | LLM dropdown stays in the panel header (D-13..D-18 lock). Starter chips render on first page load before any chat history exists; once the user's first message appears in the transcript, chips are gone. | |
| Drop chips in chat shell | Chat shells usually don't have starter prompts — the empty state is just the input field. | ✓ |
| Chips become an empty-state hint card | When transcript is empty, show a Dashboard_v2.html-style hint panel with the chips inlined. | |

**User's choice:** Drop chips in chat shell — recorded as D-CHAT-10. LLM dropdown kept (D-CHAT-11).

---

## Chat transcript shape

### Q1: How do `thought` events render in the transcript?

| Option | Description | Selected |
|--------|-------------|----------|
| Collapsed by default, click to expand (Recommended) | Each thought renders as a one-line muted summary (truncated, italic, `--mute` color). User clicks to expand the full reasoning. | ✓ |
| Always fully visible | Every thought event renders in full — no truncation, no toggle. | |
| Hidden by default, single 'Show reasoning' toggle per turn | Thoughts are not in the DOM until the user clicks 'Show reasoning' on the answer. | |

**User's choice:** Collapsed by default, click to expand — recorded as D-CHAT-12.

### Q2: How do `tool_call` and `tool_result` events render?

| Option | Description | Selected |
|--------|-------------|----------|
| Compact pill + expandable detail (Recommended) | Pills with click-to-expand. tool_call on `--violet-soft`, tool_result on `--green-soft` (success) or `--red-soft` (REJECTED). | ✓ |
| Code-block style — always full | Each tool_call shows the full SQL (or args) in a JetBrains-Mono code block. Each tool_result shows a truncated table or REJECTED message in full. | |
| Pill-only, no expansion | Just `▸ run_sql ran (12 rows)` pills, no way to see the actual SQL/data. | |

**User's choice:** Compact pill + expandable detail — recorded as D-CHAT-13.

### Q3: Stop button — placement and copy?

| Option | Description | Selected |
|--------|-------------|----------|
| Sticky at bottom of transcript while agent works (Recommended) | While the agent is reasoning, the question input is disabled and a Stop button appears in its place: red text + outline (`--red`/`--red-soft`), copy 'Stop' (no icon needed). | ✓ |
| Floating button next to active turn | Stop button floats at the top-right of the in-progress turn's card. Persists with the transcript on scroll. | |
| Stop in the panel header | Stop button replaces the 'Run' button in the panel-header area while the agent is active. | |

**User's choice:** Sticky at bottom of transcript while agent works (input replacement) — recorded as D-CHAT-14.

### Q4: Multi-turn history — how many prior turns get replayed back to the agent via PydanticAI's `message_history=`?

| Option | Description | Selected |
|--------|-------------|----------|
| Last 6 turns, then truncate (Recommended) | Each new turn gets the last 6 user/agent message pairs as context. Anything older drops off. Bounds token cost. User-visible transcript still shows everything; only the LLM context is truncated. | ✓ |
| All turns in session | Full history is replayed. Conversation feels longest-memory, but a long session blows the context budget on later turns. | |
| Token-budget aware (sliding window by tokens, not turns) | Replay as many recent turns as fit within ~80% of `max_context_tokens`. | |

**User's choice:** Last 6 turns, then truncate — recorded as D-CHAT-15.

---

## Claude's Discretion

The following were not asked of the user; planner/researcher resolves consistent with the locks above and the v2.0 design tokens:

- Exact px values for pill backgrounds / corners, max-width of chat surface, font-sizes
- Truncation cap for thought summaries (placeholder: ~120 chars)
- Whether `count_rows` is a separate tool or folded into `run_sql` instructions
- SSE reconnection / browser-drop handling (default: emit final error event, no reconnect)
- Exact placement of LLM dropdown post-rewrite (default: panel-header `ms-auto` per Phase 6)
- Whether `agent_chat.max_steps` extends `AgentConfig` or lives on a new model
- Whether path scrub applies to tool args, results, or both (default: both)
- Plotly bundle loading strategy (default: Ask page only, not global)
- Test strategy for SSE endpoints (default: TestClient SSE iteration + assert event ordering)

---

## Deferred Ideas

Tracked in CONTEXT.md `<deferred>`:
- Saved-thread sidebar / named threads
- Mid-SQL `KILL QUERY` cancellation
- Chart-type override toolbar
- Token-budget-aware history sliding window
- SSE reconnection
- Browse / Joint Validation page changes
- Chart-type heuristic refinement
- Folded/reviewed todos (none surfaced — todo match-phase returned 0)
