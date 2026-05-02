---
phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
type: context
created: 2026-05-03
status: locked
---

# Phase 3: Overhaul Ask feature into multi-step agentic chat — Context

> **Captured 2026-05-03 from a `/gsd-discuss-phase` session that built on the pre-existing exploration note `.planning/notes/ask-chat-overhaul-decisions.md` (locked architectural decisions reached during a `/gsd-explore` session on the same date).** Decisions in `<decisions>` below are user-supplied and locked. Researcher and planner must NOT re-ask these questions; they may only fill in implementation gaps (specific px values, token names, exact import paths, retry-loop wiring, error-event payload schema) consistent with these locks and the v2.0 design language.

<domain>
## Phase Boundary

**In scope (this phase):**

1. **Replace the v2.0 Phase 6 one-shot Ask page with a multi-step PydanticAI tool-using agent loop.** Same route (`/ask`) — the page rewrites under it. The agent loop runs multiple SQL queries, inspects schema, samples distincts, reasons across tool results, and emits a structured final answer.

2. **Tool surface** (per `notes/ask-chat-overhaul-decisions.md`):
   - `run_sql(sql)` — wraps the existing `nl_service.run_nl_query` SQL guard. On rejection, returns a string starting with `REJECTED:` so the agent reads the reason and retries.
   - `inspect_schema()` — returns column list + types for `ufs_data`.
   - `get_distinct_values(column)` — tool-based distincts (no prompt-stuffing).
   - `sample_rows(where_clause, limit)` — quick capped peek.
   - `count_rows(where_clause)` — cheap pre-flight.
   - `present_result(dataframe_id, summary, chart_spec)` — forces a structured final answer (table + NL summary + chart hint) at end-of-turn.

3. **SSE streaming via sse-starlette** with structured event types: `thought` / `tool_call` / `tool_result` / `final` / `error`. Each frame is `event: <type>` + JSON payload. HTMX SSE extension (`hx-ext="sse"`, `sse-connect`, `sse-swap`) drives per-event Jinja partial swaps via jinja2-fragments.

4. **Ephemeral session-scoped chat history.** PydanticAI `message_history=` replays the last 6 user/agent message pairs into each new turn (D-CHAT-15). User-visible transcript shows everything; only the LLM context window is truncated. In-memory dict keyed by session/turn id (no database persistence).

5. **UI lockout + visible Stop button** while the agent is reasoning. Stop is cooperative-only — `POST /ask/cancel/{turn_id}` flips a `cancel_event` the agent loop checks between tool calls (D-CHAT-01).

6. **Guard-rejection retry loop.** When `run_sql` returns `REJECTED:`, the agent retries up to 5 times before the turn aborts with an inline error event (D-CHAT-02, D-CHAT-04).

7. **Final answer body**: NL summary card (top, accent-soft background) + pivot/wide-form table (Browse `.pivot-table` styling) + Plotly chart picked by the agent (D-CHAT-05, D-CHAT-06).

8. **Visual design** anchored to `Dashboard_v2.html` design language: reuse existing `.panel` / `.panel-header` / `.panel-body` (already aligned by Phase 02), plus new chat-specific tokens using the `--accent-soft` / `--green-soft` / `--red-soft` / `--amber-soft` / `--violet-soft` palette from Dashboard_v2.html (D-CHAT-07).

9. **Delete the v2.0 Phase 6 NL-05 two-turn confirmation** (`_confirm_panel.html`, `loop-aborted` abort branch, NL-05-specific nl_service code). The agent's `inspect_schema()` + `get_distinct_values()` tools cover the same need (D-CHAT-09).

10. **Drop starter chips** (`_starter_chips.html`) from the new chat shell — chat shells don't have starter prompts; the empty state is just the input field (D-CHAT-10). The file may stay on disk if referenced elsewhere; it is removed from the rewritten Ask page.

11. **Keep the LLM dropdown** in the panel header and the `pbm2_llm` cookie threading. Carry forward v2.0 Phase 6 D-12..D-18 unchanged (D-CHAT-11).

**Out of scope (NOT this phase):**

- **Saved-thread sidebar / named threads / Cursor-style auto-save** — explicit user choice in the exploration note. Future phase if it's actually wanted.
- **Mid-SQL `KILL QUERY` cancellation** — cooperative-only is the chosen model (D-CHAT-01). Adding pymysql `kill_query` is a future hardening phase.
- **Browse / Joint Validation / Settings page redesign** — Ask is the only page touched. The Phase 02 shell (taller nav, full-width content, sticky footer, type tokens) carries through; nothing else gets restyled.
- **Chart-type override toolbar** — the agent picks chart_type in `chart_spec` and the user has no override in this phase (D-CHAT-06). A future phase could add a toggle.
- **AI Summary feature changes** — `summary_service` and the AI Summary modal stay as-shipped. They share `pbm2_llm` cookie threading with Ask (already wired from v2.0 Phase 6) and need no changes.
- **Multi-table joins / cross-table tools** — agent stays scoped to `ufs_data` per `AgentConfig.allowed_tables`.
- **Schema migration / write paths** — DB remains read-only.
- **External bookmark migration / nav-label change** — `/ask` route stays; nav still says "Ask" (D-CHAT-08).

</domain>

<decisions>
## Implementation Decisions

> Decision IDs use a fresh `D-CHAT-*` namespace so they do not collide with `D-OV-*` (v2.0 Phase 5), `D-JV-*` (Phase 1), or `D-UI2-*` (Phase 02).

### Stop & Failure Boundaries

- **D-CHAT-01: Cooperative-only cancellation.** `POST /ask/cancel/{turn_id}` flips a `cancel_event` (in-process Event object stored in the session/turn map). The agent loop checks the event between tool calls; a tool call already in flight (e.g., a long SQL) runs to completion before the loop exits. No `pymysql.kill_query` in this phase.
  - Why: User picked the simpler model in 2026-05-03 discuss session. Avoids connection-tracking complexity and a second failure path. The existing `AgentConfig.timeout_s` + MySQL `max_execution_time` continue to act as the backstop for runaway SQL.
  - How to apply: Maintain an in-memory `dict[turn_id, threading.Event]` (or asyncio.Event since FastAPI routes are async-capable). The Stop button POSTs to `/ask/cancel/{turn_id}`; the route sets the event and returns 204. The agent loop wraps the per-step iteration in `if cancel_event.is_set(): break` and emits a final `event: error` SSE frame with reason "stopped-by-user".

- **D-CHAT-02: Guard-rejection retry cap = 5 rewrites per turn.** When `run_sql` returns a string starting with `REJECTED:`, the agent receives that as a tool result and is free to emit another `run_sql` call. After the 5th consecutive rejection on the same turn, the loop aborts with reason "still-rejected-after-5-attempts" (final error event).
  - Why: User picked 5 (looser than the recommended 3) in 2026-05-03 discuss session. Trades token burn for forgiveness on edge cases like the SM8850 vs SM8650 UNION example.
  - How to apply: Track a per-turn rejection counter in the agent loop wrapper (NOT in the tool itself, so non-rejection errors don't pollute the count). When the counter reaches 5, raise an internal "retry-cap-exceeded" exception caught by the SSE generator, which then emits the final error event.

- **D-CHAT-03: New `agent_chat.max_steps` config key, default ≥ 12.** A separate config knob from the v1.0 single-turn `AgentConfig.max_steps`. Add to `app/core/config.py` Pydantic settings under a new `AgentChatConfig` (or extend `AgentConfig` with a `chat_max_steps` field — planner picks the cleaner shape).
  - Why: User picked "new key with higher default" in 2026-05-03 discuss session. Multi-step chat needs more headroom than a v1.0 single-turn run; keeping the v1.0 budget tight while giving chat room to breathe avoids regressing v1.0 behavior.
  - How to apply: New field defaults to 12; configurable via existing settings.yaml plumbing. When the budget is exhausted, the loop emits a final error event with reason "step-budget-exhausted" (similar to Phase 6's `step-cap` abort branch but rendered inline per D-CHAT-04, not as a banner-replacement).

- **D-CHAT-04: Non-rejection failures (timeout, LLM 5xx, SSE stream drop, step-budget exhausted, retry-cap exceeded, stopped-by-user) render inline in the transcript as a final `error` event.** A single error-card Jinja partial (e.g., `templates/ask/_error_card.html`) is the receiving fragment for every error reason. Border + accent color comes from the Dashboard_v2.html palette: `--red` / `--red-soft` for hard failures (LLM error, retry-cap-exceeded, stream drop), `--amber` / `--amber-soft` for boundaries the user can mitigate (timeout, step-budget-exhausted, stopped-by-user). Card includes the reason + a "Retry this question" button that POSTs the same question to a new turn.
  - Why: User picked inline-in-transcript over Phase 6's whole-zone banner replacement in 2026-05-03 discuss session. Preserves in-progress transcript so the user can see where it failed.
  - How to apply: The SSE generator emits `event: error` + `{reason, message}` payload as the terminal event. Client-side `sse-swap="error"` appends the rendered `_error_card.html` fragment to the transcript and disables the SSE listener. Replaces Phase 6's `_abort_banner.html` for the new flow. The old `_abort_banner.html` is removed when NL-05 is deleted (D-CHAT-09).

### Final Answer (`present_result`) Body

- **D-CHAT-05: Final answer = NL summary card + pivot table + Plotly chart, in that vertical order, all in one card.** Top: 1–2 sentence NL summary on `--accent-soft` background (Dashboard_v2.html `.callout`-ish style). Middle: pivot/wide-form table reusing Browse's `.pivot-table` selectors verbatim — no styling fork. Bottom: Plotly chart rendered from `chart_spec`. Card lives inside `.panel-body` of the chat surface; one final card per turn.
  - Why: User picked the all-three combination in 2026-05-03 discuss session. Matches today's `_answer.html` output plus an explicit summary plus a chart, keeping the structured `present_result(dataframe_id, summary, chart_spec)` schema from the exploration note honest.
  - How to apply: New Jinja partial `templates/ask/_final_card.html` rendered by jinja2-fragments. Receives the `present_result` Pydantic model (dataframe ref, summary string, chart_spec). Reuses the Browse `_grid.html` macro for the table portion. Plotly bundle (`plotly>=5.22` already in v1.0 deps) loaded only on the Ask page.

- **D-CHAT-06: Agent picks `chart_spec.chart_type`; no user override in Phase 3.** The Pydantic schema for `present_result` includes `chart_spec: ChartSpec | None` where `ChartSpec` has `chart_type: Literal["bar", "line", "scatter", "none"]` and the columns to plot. Agent fills it based on numeric-column heuristics in its system prompt. UI renders whatever the agent chose; no toolbar, no toggle.
  - Why: User picked agent-decides-no-override in 2026-05-03 discuss session. Reinforces the "agentic" feel — the agent owns the answer shape end-to-end.
  - How to apply: Define `ChartSpec` in `app/core/agent/` (alongside the existing pydantic models). Agent system prompt instructs it to pick `chart_type="none"` when no numeric column is dominant. The chart-renderer fragment reads chart_type and emits the correct Plotly figure or skips chart rendering when `chart_type="none"`.

- **D-CHAT-07: Reuse `.panel` / `.panel-header` / `.panel-body` from app.css; add chat-specific tokens using the existing Dashboard_v2.html palette.** No new CSS framework, no pixel-port from Dashboard_v2.html. Chat-specific additions sit on top of the v2.0 Phase 02 token system: a thought-pill style using `--mute`, a tool_call pill using `--violet-soft`, a tool_result pill using `--green-soft` (success) or `--red-soft` (REJECTED), a summary card using `--accent-soft`, an error card using `--red-soft` / `--amber-soft` per D-CHAT-04.
  - Why: User picked reuse-and-extend over pixel-port in 2026-05-03 discuss session. Phase 02 already aligned panel structure to Dashboard_v2.html; this avoids drifting from Phase 02's tokens.
  - How to apply: New CSS rules added to `static/css/app.css` (or a new `chat.css` referenced only on the Ask page — planner picks). Tokens already exist in `tokens.css` from Phase 02 work; only new token names (e.g., `--chat-pill-thought`, `--chat-pill-tool`) need adding if any are introduced.

### Routing & NL-05 Migration

- **D-CHAT-08: Replace `/ask` in place. New route shape:**
  - `GET /ask` — unchanged route, page rewrites: chat shell with empty transcript (no starter chips, see D-CHAT-10) + question input form.
  - `POST /ask/chat` — kicks off a new turn. Body: `question` + optional CSRF/turn correlation. Response: `200` with the turn_id (HTMX swap inserts a "user message + agent-thinking placeholder" fragment into the transcript).
  - `GET /ask/stream/{turn_id}` — SSE endpoint. Iterates over `agent.run_stream(...)` and yields `thought` / `tool_call` / `tool_result` / `final` / `error` events.
  - `POST /ask/cancel/{turn_id}` — flips the cancel_event. Returns 204.
  - **Removed**: `POST /ask/query`, `POST /ask/confirm` (Phase 6 routes for the one-shot + NL-05 flow). The route layer's `nl_service.run_nl_query` import stays — it becomes a tool implementation called from the agent loop, not a route handler.
  - Why: User picked replace-in-place over a parallel `/chat` page in 2026-05-03 discuss session. Existing nav tab, page label, and bookmarks keep working; minimal migration friction.
  - How to apply: Rewrite `app_v2/routers/ask.py` end-to-end. Top-nav still says "Ask" (no nav-label flip). `app_v2/templates/ask/index.html` rewrites; the existing `id="answer-zone"` div becomes `id="chat-transcript"` (or similar) to match the new SSE event swap targets.

- **D-CHAT-09: Delete the NL-05 two-turn confirmation flow.** Removed in this phase:
  - `app_v2/templates/ask/_confirm_panel.html` (the picker-popover-based confirmation panel)
  - `app_v2/templates/ask/_abort_banner.html` (replaced by the inline `_error_card.html` per D-CHAT-04)
  - The `loop-aborted` abort branch and related copy in nl_service / nl_agent
  - The `POST /ask/confirm` route (per D-CHAT-08)
  - Any v2.0 Phase 6 tests that exercise the two-turn confirmation flow specifically (they get rewritten or deleted in this phase's plans)
  - **Preserved** because they're shared with non-Ask consumers: `nl_service.run_nl_query` (called by the agent's `run_sql` tool), `nl_agent.py` core agent factory, `pydantic_model.py` (used by AI Summary too), `starter_prompts.example.yaml` (no longer rendered on Ask but file may still ship as documentation).
  - Why: The new agent's `inspect_schema()` + `get_distinct_values()` tools cover the same disambiguation need without a hard-coded UI confirmation step. User picked delete in 2026-05-03 discuss session.
  - How to apply: Plan a dedicated cleanup task that removes templates + route handlers + matching tests in one commit so the working tree never has half-deleted artifacts.

- **D-CHAT-10: Drop starter chips on the new chat shell.** `_starter_chips.html` is no longer included in the Ask `index.html` template. The empty state is just the question input. If the file is referenced nowhere else after this phase, it gets deleted; otherwise it stays on disk unused (planner verifies via grep).
  - Why: User picked drop-on-chat-shell in 2026-05-03 discuss session. Chat shells don't have starter prompts; the input field is the empty state.
  - How to apply: Remove the `{% include "ask/_starter_chips.html" %}` block from `templates/ask/index.html`. Remove the `starter_prompts` context kwarg from the `GET /ask` handler when it's only fed to chips. Plan a grep to confirm no other consumers and delete the partial if orphaned.

- **D-CHAT-11: Keep the LLM dropdown + `pbm2_llm` cookie threading.** No change to v2.0 Phase 6 D-12..D-18 — the dropdown stays in the panel header, the `pbm2_llm` cookie still carries the active backend name, AI Summary continues to share the same backend choice. The dropdown + dropdown-item POST handlers ship verbatim into the rewritten `index.html` and `routers/ask.py`.
  - Why: User explicitly chose to keep both in 2026-05-03 discuss session. No reason to churn this surface.
  - How to apply: Lift the dropdown HTML block + the `POST /settings/llm` handler reference unchanged. Path scrub for OpenAI (per `app/core/agent/path_scrub.py` if it exists, or wherever it's currently wired) continues to apply against tool args + tool results when the active backend is OpenAI — researcher / planner confirms wiring.

### Chat Transcript Shape

- **D-CHAT-12: `thought` events render collapsed by default with click-to-expand.** Visual: one-line italic muted summary (truncated at, say, 120 chars; researcher picks exact cap). `--mute` text color, no background, small left-border in `--line-2`. User clicks to expand and see the full reasoning. The collapse state is per-event (each thought has its own toggle).
  - Why: User picked collapsed-by-default in 2026-05-03 discuss session. Keeps the transcript scannable on multi-step turns; full reasoning remains auditable.
  - How to apply: Each thought event renders a `<details>` block (HTML-native, no JS) with a `<summary>` containing the truncated text. Or a Bootstrap collapse if `<details>` styling is awkward — researcher picks. jinja2-fragments swaps the rendered fragment into the transcript on each `event: thought`.

- **D-CHAT-13: `tool_call` and `tool_result` events render as compact pills with click-to-expand.** Pills:
  - `tool_call`: `▸ run_sql("SELECT…")` on `--violet-soft` background, `--violet` ink. Click to expand → shows full args (SQL pretty-printed via sqlparse, or JSON for non-SQL tools) in a JetBrains-Mono code block.
  - `tool_result` (success): `▸ returned 12 rows` on `--green-soft` background, `--green` ink. Click to expand → shows a truncated table preview (first ~10 rows, capped).
  - `tool_result` (REJECTED): `▸ REJECTED: UNION not allowed` on `--red-soft`, `--red` ink. Click to expand → shows the full rejection message.
  - Why: User picked compact-pill-with-expansion in 2026-05-03 discuss session. Live-feel without flooding the screen.
  - How to apply: Two Jinja partials — `_tool_call_pill.html`, `_tool_result_pill.html` — both rendering `<details>` for the expand interaction. SSE event handler swaps each event's payload into the transcript as soon as it arrives.

- **D-CHAT-14: Stop button replaces the input area while the agent is working.** When a turn starts: the textarea + Run button are disabled / hidden; in their place renders a Stop button styled with `--red` outline + `--red` ink + `--red-soft` hover background, copy "Stop" (no icon needed). When the agent emits `event: final` or `event: error`: Stop disappears, the input + Run re-enable. Stop POSTs to `/ask/cancel/{turn_id}` (D-CHAT-01).
  - Why: User picked input-replacement over floating button or panel-header button in 2026-05-03 discuss session. Matches ChatGPT/Cursor pattern; no sticky-positioning CSS concern.
  - How to apply: Single template region (e.g., `templates/ask/_input_zone.html`) that renders either the input form (idle) or the Stop button (active). HTMX swaps this region on `POST /ask/chat` (active state) and on the SSE final/error events (idle state).

- **D-CHAT-15: `message_history=` replays the last 6 user/agent message pairs.** PydanticAI's `agent.run(message_history=...)` receives a sliding window of the most recent 6 turns from the in-memory session store. The user-visible transcript displays everything; only the LLM context window is truncated.
  - Why: User picked turn-based truncation (over all-history or token-based-window) in 2026-05-03 discuss session. Bounds token cost predictably; matches the existing `AgentConfig.max_context_tokens` budget without complex sliding-by-token logic.
  - How to apply: Session store keyed by browser session id stores `list[ModelMessage]`. On each new turn, slice `[-12:]` (6 user + 6 agent messages = 12 ModelMessage entries) and pass to `agent.run(message_history=…)`. Older messages stay in the user-visible transcript but aren't replayed to the LLM.

### Claude's Discretion

The following are NOT locked by the user and the researcher / planner may resolve them:

- **Exact px values, tokens, and selector names** — pill background corners, max-width of the chat surface inside the new full-width shell, font-size of the thought-pill summary. Researcher proposes; planner pins.
- **Truncation cap for thought summaries** (D-CHAT-12 placeholder: 120 chars). Researcher picks based on visual rhythm.
- **Whether `count_rows` is a separate tool or folded into the agent's `run_sql` instructions.** Default: keep as a separate tool per the exploration note's tool surface — feels cheap to wire and gives the agent a token-saving pre-flight option.
- **SSE reconnection / browser-drop handling.** Default: when the SSE stream drops mid-turn, the client emits a final `error` event with reason "stream-dropped" (D-CHAT-04). Reconnection is not in scope — the user retries the question. If the planner finds a clean reconnection pattern, that can be added; otherwise default ships.
- **Exact placement of the LLM dropdown post-rewrite** (panel header right-side vs panel-header far-right; both are valid given the new chat shell). Default: keep verbatim from current Phase 6 layout (panel-header `ms-auto` dropdown).
- **Whether the new `agent_chat.max_steps` lives on `AgentConfig` as a new field or on a new `AgentChatConfig` model.** Default: prefer extending `AgentConfig` to avoid a settings.yaml schema bump unless `AgentChatConfig` ends up with multiple distinct fields.
- **Whether path scrub applies to tool args, tool results, or both** when OpenAI is the active backend. Default: apply to BOTH (tool args before sending to OpenAI for the next turn's reasoning; tool results before they enter the chat history that gets replayed via `message_history=`).
- **Plotly bundle loading strategy.** Default: load the Plotly script tag only on the Ask page (not globally), so other pages aren't paying the cost. Researcher confirms.
- **Test strategy for SSE endpoints.** Default: streaming endpoints are tested by collecting events into a list (FastAPI's TestClient supports SSE iteration) and asserting on event types + ordering. Planner pins specific test fixtures.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pre-existing exploration & architecture decisions
- `.planning/notes/ask-chat-overhaul-decisions.md` — **READ FIRST.** Architectural decisions reached during the 2026-05-03 `/gsd-explore` session: motivating example (SM8850 vs SM8650), tool surface, stack alignment, and the four open questions resolved by this CONTEXT.md.

### v2.0 Phase 6 prior-art (Ask Tab Port)
- `.planning/milestones/v2.0-phases/06-ask-tab-port/06-CONTEXT.md` — Locked decisions D-12..D-18 for LLM dropdown + `pbm2_llm` cookie threading + path scrub policy. Carried forward unchanged per D-CHAT-11.
- `.planning/milestones/v2.0-phases/06-ask-tab-port/06-UI-SPEC.md` — Today's Ask page UI spec; the rewrite preserves the LLM dropdown and the panel-header layout, replaces everything inside `.panel-body`.
- `app_v2/templates/ask/index.html` — Current page; will be rewritten under the same route.
- `app_v2/templates/ask/_answer.html`, `app_v2/templates/ask/_confirm_panel.html`, `app_v2/templates/ask/_abort_banner.html`, `app_v2/templates/ask/_starter_chips.html` — Current Ask partials. `_confirm_panel.html`, `_abort_banner.html`, and the `_starter_chips.html` include are removed per D-CHAT-09 / D-CHAT-10. `_answer.html` is replaced by the new `_final_card.html` (D-CHAT-05).
- `app_v2/routers/ask.py` — Current route handlers. Rewritten end-to-end per D-CHAT-08.
- `app/core/agent/nl_service.py` — Single-locus NL invocation surface; becomes the implementation backing the agent's `run_sql` tool. Preserved.
- `app/core/agent/nl_agent.py` — Existing PydanticAI agent factory; extended to add tool decorators and the new agent-loop wrapper. Preserved.

### Phase 02 shell tokens (inherit unchanged)
- `app_v2/static/css/tokens.css` — Type scale (`--font-size-logo/h1/th/body`), color palette aligned to Dashboard_v2.html. Chat-specific token additions (D-CHAT-07) extend this file.
- `app_v2/static/css/app.css` — `.shell`, `.panel`, `.panel-header`, `.panel-body`, `.site-footer`. Chat-specific styles either extend `app.css` or live in a new `chat.css` (planner picks).
- `app_v2/templates/base.html` — Sticky in-flow footer block from Phase 02 (D-UI2-05). Ask page inherits without extending the footer block (Ask has no entity count to surface in the footer per Phase 02 D-UI2-05 default).

### Browse table / pivot styling (reused for the result card)
- `app_v2/templates/browse/_grid.html` + `app_v2/static/css/app.css` `.pivot-table` rules — Pivot-table styling reused verbatim inside `_final_card.html` per D-CHAT-05. Do NOT fork.

### Visual design anchor (sister project)
- `/home/yh/Desktop/02_Projects/Proj27_PBM1_fork_bootstrap/Dashboard_v2.html` — Source design language for the v2.0 token system already pulled into Phase 02. Chat surface reuses Phase 02's tokens; refer to the original Dashboard_v2.html only when adding new chat-specific tokens (D-CHAT-07) — specifically for the `--violet-soft`, `--green-soft`, `--red-soft`, `--amber-soft`, `--accent-soft` callout patterns.

### PydanticAI / SSE / HTMX docs
- https://ai.pydantic.dev/tools/ — `@agent.tool` patterns used by the new tool surface.
- https://ai.pydantic.dev/output/#streaming-structured-output — `agent.run_stream()` reference for the SSE generator.
- https://ai.pydantic.dev/message-history/ — `message_history=` semantics for D-CHAT-15.
- https://htmx.org/extensions/server-sent-events/ — `hx-ext="sse"`, `sse-connect`, `sse-swap` patterns.
- https://pypi.org/project/sse-starlette/ — `EventSourceResponse` for the streaming endpoint.

### Project rules
- `CLAUDE.md` — project-level constraints (read-only DB, lazy per-query type coercion, intranet deployment, dual OpenAI/Ollama LLM choice).
- `.planning/PROJECT.md` — Constraints + Key Decisions; honors security backstop (read-only DB user as primary SQL-injection guard) + path-scrub policy.
- `.planning/STATE.md` — current state pointer; updated at the end of this discuss session.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets
- **`nl_service.run_nl_query`** — single-locus NL invocation. Becomes the agent's `run_sql` tool implementation; the SQL guard rejection becomes the tool's `REJECTED:` return string (no rewriting needed at the tool boundary).
- **`nl_agent.py`** — existing PydanticAI agent factory. Extends with `@agent.tool` decorators for `inspect_schema`, `get_distinct_values`, `sample_rows`, `count_rows`, `present_result`, plus a thin agent-loop wrapper that yields events for the SSE generator.
- **Browse `_grid.html` + `.pivot-table` CSS** — reused verbatim inside `_final_card.html` (D-CHAT-05). No styling fork.
- **`pbm2_llm` cookie + `llm_resolver`** — already wired across Ask + AI Summary from v2.0 Phase 6. New chat shell threads through unchanged.
- **Path scrub helper** (location to be confirmed by researcher — likely `app/core/agent/path_scrub.py` or inline in `nl_service.py`) — applied against tool args + tool results when OpenAI is the active backend (Claude's Discretion: apply to BOTH).
- **Phase 02 sticky footer + full-width shell** — Ask page inherits without extending the footer block.
- **sqlparse** — already in v1.0 deps; reused to pretty-print SQL in tool_call expansion (D-CHAT-13).
- **plotly** — already in v1.0 deps (`plotly>=5.22`); reused for the chart in `_final_card.html` (D-CHAT-05).
- **jinja2-fragments** — already in v1.0 deps; per-event partial rendering for SSE swaps.

### Established patterns
- **Single `id="…"` swap-target region in `index.html`** — Phase 6 used `id="answer-zone"`. New chat shell uses a transcript region (e.g., `id="chat-transcript"`) plus a separate `id="input-zone"` per D-CHAT-14.
- **HTMX `hx-vals` + `hx-swap="none"` + 204+`HX-Refresh`** for the LLM dropdown (D-CHAT-11). Reused unchanged.
- **Pydantic models in `app/core/agent/`** — pattern for tool-output schemas. New `ChartSpec` and `PresentResult` models live alongside existing models.
- **Pytest + FastAPI TestClient + pytest-mock** — established test pattern for routers. SSE endpoints tested by iterating events from TestClient.

### Integration points
- **`app_v2/routers/ask.py`** — rewritten end-to-end (D-CHAT-08). Removes `POST /ask/query`, `POST /ask/confirm`. Adds `POST /ask/chat`, `GET /ask/stream/{turn_id}`, `POST /ask/cancel/{turn_id}`.
- **`app_v2/main.py`** — registers `sse-starlette` (the `EventSourceResponse` is per-route, no app-wide config needed) and verifies the existing `app.include_router(ask.router)` still mounts cleanly.
- **`requirements.txt`** — adds `sse-starlette` (small, single new dep). Everything else already pinned.
- **`app/core/config.py`** — adds `agent_chat.max_steps` (or extends `AgentConfig`) per D-CHAT-03.
- **`config/settings.example.yaml`** — documents the new `agent_chat.max_steps` knob with its default value.
- **`templates/ask/`** — directory restructured: removes `_answer.html`, `_confirm_panel.html`, `_abort_banner.html`, the `_starter_chips.html` include from `index.html`. Adds `_final_card.html`, `_thought_event.html` (or merged into the SSE swap fragment), `_tool_call_pill.html`, `_tool_result_pill.html`, `_error_card.html`, `_input_zone.html`.

</code_context>

<specifics>
## Specific Ideas

### Motivating user example (verbatim from `.planning/notes/ask-chat-overhaul-decisions.md`)

> "Right now even for a basic question like 'compare SM8850 vs SM8650', it plainly says 'Something went wrong. (SQL rejected: UNION / INTERSECT / EXCEPT are not allowed) Try rephrasing your question' and it's the end of story."

The new agent loop must solve this case automatically: when `run_sql("SELECT … UNION SELECT …")` returns `REJECTED: UNION / INTERSECT / EXCEPT are not allowed`, the agent reads the reason and emits two separate `run_sql("SELECT … WHERE PLATFORM_ID='SM8850'")` + `run_sql("SELECT … WHERE PLATFORM_ID='SM8650'")` calls, then merges results in `present_result`.

### Visual design anchor

Pin chat UI to **`/home/yh/Desktop/02_Projects/Proj27_PBM1_fork_bootstrap/Dashboard_v2.html`** design language (per user memory "Anchor design to visual reference"). Specific palette references for new chat-specific tokens (D-CHAT-07): `--accent-soft` for summary callouts, `--violet-soft` for tool_call pills, `--green-soft` for successful tool_result pills, `--red-soft` for REJECTED tool_result pills + hard error cards, `--amber-soft` for soft error cards (timeout, step-budget, stopped-by-user).

### "Stop" copy (D-CHAT-14)

Copy is just **"Stop"** — no icon. Red outline + red ink (`--red`), `--red-soft` hover background. Matches ChatGPT/Cursor convention.

### Truncation cap placeholder (D-CHAT-12)

Thought-summary collapsed view truncates at ~120 chars (researcher confirms exact value). Full text on expand.

</specifics>

<deferred>
## Deferred Ideas

These came up but are explicitly out of scope for Phase 3:

- **Saved-thread sidebar / named threads** — explicit user choice in the exploration note. Future phase.
- **Mid-SQL `KILL QUERY` cancellation** — D-CHAT-01 commits to cooperative-only. Hardening phase if v3 turns are slow enough that mid-tool cancel matters.
- **Chart-type override toolbar** — D-CHAT-06 commits to agent-decides-no-override. Future phase if users want to re-pick.
- **Token-budget-aware history sliding window** — D-CHAT-15 ships turn-based (last 6) truncation. Future phase if 6-turn replay overflows context for long answers.
- **SSE reconnection** — current ship: dropped stream emits a final `error` event. Future phase if drop frequency justifies a reconnect protocol.
- **Browse / Joint Validation page changes** — Ask is the only page touched in Phase 3.
- **Chart-type heuristic refinement** — agent gets a static instruction to pick chart_type. Future phase could add metric-based heuristics (cardinality, numeric ratio, etc.).
- **Folded todos** — none surfaced (todo match-phase returned 0 matches for Phase 3).
- **Reviewed Todos (not folded)** — none surfaced.

</deferred>

---

*Phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on*
*Context gathered: 2026-05-03 via /gsd-discuss-phase, building on the 2026-05-03 /gsd-explore architectural note at .planning/notes/ask-chat-overhaul-decisions.md*
