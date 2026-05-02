---
phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
reviewed: 2026-05-03T00:00:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - app/core/agent/chat_agent.py
  - app/core/agent/chat_session.py
  - app/core/agent/chat_loop.py
  - app/core/agent/config.py
  - app_v2/main.py
  - app_v2/routers/ask.py
  - app_v2/templates/base.html
  - app_v2/templates/ask/index.html
  - app_v2/templates/ask/_user_message.html
  - app_v2/templates/ask/_input_zone.html
  - app_v2/templates/ask/_thought_event.html
  - app_v2/templates/ask/_tool_call_pill.html
  - app_v2/templates/ask/_tool_result_pill.html
  - app_v2/templates/ask/_final_card.html
  - app_v2/templates/ask/_error_card.html
  - app_v2/static/css/app.css
  - tests/v2/test_ask_routes.py
  - tests/v2/test_phase03_chat_invariants.py
  - tests/v2/test_chat_loop.py
  - tests/v2/test_chat_session.py
  - tests/v2/test_chat_agent_tools.py
  - tests/v2/test_phase04_invariants.py
  - requirements.txt
  - config/settings.example.yaml
findings:
  critical: 0
  warning: 4
  info: 6
  total: 10
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-05-03
**Depth:** standard
**Files Reviewed:** 24
**Status:** issues_found

## Summary

Phase 3 implements the multi-step agentic chat overhaul: a parallel `chat_agent.py`
with 6 tools, a streaming `chat_loop.py` driving `agent.run_stream_events`, an
in-memory `chat_session.py` registry, and a rewritten Ask router with SSE +
session-ownership-gated stream / cancel endpoints. The implementation is
generally faithful to the design and threat models. Risk-area findings:

- **SQL guard regression (focus 1):** No drift detected. `_execute_and_wrap`
  applies SAFE-02 (validate_sql), SAFE-03 (inject_limit), SAFE-04 (SET SESSION
  TRANSACTION READ ONLY), SAFE-04b (max_execution_time), SAFE-06 (scrub_paths
  when openai), SAFE-05 (`<db_data>` wrapper) in the same order as
  `nl_agent.run_sql` + `_execute_read_only`. Rejection prefix changed to
  `REJECTED:` (intentional per D-CHAT-02). Single observable behavioural
  delta vs. nl_agent: chat_agent silently swallows exec exceptions
  (`_log.warning` removed) — see WR-01.
- **Session-cookie ownership (focus 2):** Both `/ask/stream/{turn_id}` and
  `/ask/cancel/{turn_id}` correctly compare `request_sid` to
  `get_session_id_for_turn(turn_id)` and return 403 on mismatch / 404 on
  unknown turn. Tests cover both negative paths. Pass.
- **Async/sync correctness (focus 3):** chat_loop is correctly async; cancel
  primitive is `asyncio.Event` (not `threading.Event`). No `agent.run_sync`
  anywhere in `app_v2/routers/ask.py`. Real concern: the SSE event_generator
  invokes `_hydrate_final_card` which performs synchronous `pd.read_sql_query`
  on the event-loop thread (WR-03).
- **Path scrub coverage (focus 4):** Both tool args (via
  `_scrub_messages_inplace` over `ToolCallPart.args` string-valued entries)
  AND tool results (via `_execute_and_wrap` `<db_data>` rows_text + via
  `ToolReturnPart.content` walked in append) are scrubbed when
  `active_llm_type == "openai"`. Pass — with one shape concern (IN-04: nested
  / non-string args bypass scrubber, brittle for future tools).
- **Jinja autoescape / XSS (focus 5):** All 5 chat partials use `| e` on
  every agent-supplied variable; `| safe` appears only on `table_html` /
  `chart_html` in `_final_card.html` (router-rendered, whitelisted by
  `test_final_card_safe_filter_only_on_router_rendered_html`). Pass.
- **Resource leaks (focus 6):** `_TURNS` entries are pop'd via
  `BackgroundTask(pop_turn, ...)` only on the SSE response path. POSTing
  `/ask/chat` and never opening the SSE stream leaks the turn entry forever
  (WR-02). `_SESSIONS` is documented as process-lifetime — flagged IN-02.
- **Test quality (focus 7):** Motivating example (SM8850 vs SM8650 UNION) is
  asserted; WARNING-3 final-payload structured contract is asserted; SSE
  ownership 403/404 are asserted. One assertion (table-rows test) checks tag
  presence rather than cell content — IN-05. Test cookie-isolation pattern
  has a subtle layout dependence — IN-06.
- **Banned-library compliance (focus 8):** No `langchain` / `litellm` /
  `vanna` / `llama_index` imports in any reviewed file. Pass.

No Critical findings. Four Warning findings (one observability regression,
two leak/blocking concerns, one silent-coercion risk) and six Info items.

## Warnings

### WR-01: chat_agent SAFE-harness silently drops execution-error logging

**File:** `app/core/agent/chat_agent.py:261-262`
**Issue:** `_execute_and_wrap` returns `f"SQL execution error: {type(exc).__name__}"` on
any DB exception but does NOT log the full exception detail server-side. The
parallel `nl_agent.run_sql` (the source of the verbatim port) explicitly logs
the full exception via `_log.warning("run_sql execution error: %s: %s",
type(exc).__name__, exc)` (nl_agent.py:179). Operationally, when the chat
agent's SQL fails (timeout, connection drop, pymysql error, schema mismatch),
the operator gets ZERO server-side signal — the agent sees `SQL execution
error: OperationalError` and may retry several times before hitting the
rejection cap, while the operator has no log line to debug from. This is an
observability regression vs. the legacy single-turn path.

**Fix:**
```python
# In app/core/agent/chat_agent.py near the top:
import logging
_log = logging.getLogger(__name__)

# In _execute_and_wrap, replace the bare except:
    except Exception as exc:
        _log.warning(
            "chat-agent run_sql execution error: %s: %s",
            type(exc).__name__,
            exc,
        )
        return f"SQL execution error: {type(exc).__name__}"
```

### WR-02: Turn-registry leaks when SSE stream is never opened

**File:** `app_v2/routers/ask.py:160-182`, `app/core/agent/chat_session.py:84-94`
**Issue:** `POST /ask/chat` calls `new_turn(sid, q)` which inserts into the
module-level `_TURNS` dict. The only cleanup path is `BackgroundTask(pop_turn,
turn_id)` registered on the SSE response in `ask_stream`. If the user submits
a question and the browser never opens `GET /ask/stream/{turn_id}` (tab close,
network drop after POST, an HTMX swap that never wires the SSE consumer, a
bot/scanner that fires the form), the entry remains in `_TURNS` for the
process lifetime. Each leaked entry is small (~few hundred bytes including
the `asyncio.Event`), but for a long-running process with intermittent
connectivity issues the dict grows unboundedly. Cancel-after-leak still works
(returns 204) which means the cancel_event is set on a turn no one is
listening to, masking that the leak even happened.

**Fix:** Either schedule a delayed cleanup on POST `/ask/chat` (TTL sweep) or
make the SSE handshake the registration step. Minimal mitigation:
```python
# In app_v2/routers/ask.py — register a one-shot timeout cleanup on POST.
import asyncio
from starlette.background import BackgroundTask

async def _delayed_pop(turn_id: str, delay: float = 600.0):
    """Clean up any turn whose SSE stream never connected within `delay` seconds."""
    await asyncio.sleep(delay)
    pop_turn(turn_id)

# In ask_chat:
turn_id = new_turn(sid, q)
# Schedule a 10-minute fallback cleanup; the SSE BackgroundTask will pop sooner
# when the stream completes normally (pop_turn is idempotent).
asyncio.get_event_loop().create_task(_delayed_pop(turn_id, 600.0))
```
Or, simpler: keep an LRU cap in `_TURNS` (e.g., trim oldest 100 when size >
500) inside `new_turn`.

### WR-03: Synchronous DB I/O on event-loop thread inside SSE generator

**File:** `app_v2/routers/ask.py:325-411` (`_hydrate_final_card`)
**Issue:** `_hydrate_final_card` is invoked from inside the `event_generator`
async function (line 255), which is the async iterable handed to
`EventSourceResponse`. The hydration runs `pd.read_sql_query(sa.text(safe_sql),
conn)` and `engine_fn().connect()` synchronously on the event-loop thread
(line 396). For the intranet's intended low-concurrency workload (CLAUDE.md
"low concurrency intranet tool") this is acceptable, but it blocks the loop
for the duration of the final SQL — preventing other SSE streams from making
progress and preventing the cancel endpoint's response from being scheduled
during that window. The `_execute_and_wrap` tool path doesn't have this issue
because PydanticAI dispatches sync `@agent.tool` functions to a threadpool.

**Fix:** Run the DB-bound portion of `_hydrate_final_card` in a threadpool:
```python
import asyncio

async def event_generator():
    async for ev in stream_chat_turn(...):
        if ev["event"] == "final":
            payload = ev["payload"]
            html = await asyncio.get_running_loop().run_in_executor(
                None,  # default ThreadPoolExecutor
                lambda: _hydrate_final_card(
                    payload=payload,
                    deps=deps,
                    request=request,
                    owner_sid=owner_sid,
                    active_llm_type=active_llm_type,
                    original_question=question,
                ),
            )
            yield ServerSentEvent(event="final", data=html)
        else:
            yield ServerSentEvent(event=ev["event"], data=ev["html"])
```

### WR-04: Silent coercion of unknown LLM `type` to "ollama" disables path scrub

**File:** `app_v2/routers/ask.py:224`
**Issue:** `active_llm_type = "openai" if getattr(llm_cfg, "type", "") == "openai" else "ollama"`
silently maps any non-`"openai"` string to `"ollama"`. The `LLMConfig.type`
field documented in CLAUDE.md research notes already lists `"anthropic"` as
"in the model for extensibility; just don't expose in the sidebar picker for
v1". If a future change exposes Anthropic (or any other cloud backend) and
forgets to update this branch, the path scrub policy (D-CHAT-11 "both") will
silently NOT fire and `/sys/*` / `/proc/*` / `/dev/*` paths will leak in the
prompt + replayed message_history to the cloud model. The correct
default-deny posture is: anything that is NOT explicitly `ollama` (or another
known-local backend) is treated as cloud and scrubbed.

**Fix:**
```python
# In app_v2/routers/ask.py:
_LOCAL_LLM_TYPES = frozenset({"ollama"})  # extend as new local backends are added
active_llm_type: Literal["openai", "ollama"] = (
    "ollama" if getattr(llm_cfg, "type", "") in _LOCAL_LLM_TYPES else "openai"
)
```
Then update `ChatAgentDeps.active_llm_type` Literal to admit the same two
canonical values (already does). The naming `active_llm_type` is now a
slight misnomer (it's actually a scrub-policy enum) — consider renaming to
`scrub_policy: Literal["scrub", "no_scrub"]` in a follow-up.

## Info

### IN-01: `app.state.chat_turns` / `app.state.chat_sessions` are dead

**File:** `app_v2/main.py:53-56`
**Issue:** Lifespan sets `app.state.chat_turns = {}` and
`app.state.chat_sessions = {}` but the actual registries live as
module-level dicts in `app/core/agent/chat_session.py:74-78`. The
chat_session module never reads `app.state`. The comment on chat_session.py
line 71 explicitly calls these "documentation hooks only" — but a future
contributor reading `main.py` lifespan first would reasonably assume
`app.state.chat_turns` is the registry and might write to it, silently
diverging from `_TURNS`.
**Fix:** Either delete the two `app.state.*` assignments and leave a single
comment in `lifespan` pointing at `chat_session._TURNS` / `_SESSIONS`, or
use `app.state` as the actual store and migrate chat_session to read it.
The first option is smaller and safer.

### IN-02: `_SESSIONS` has no eviction policy — unbounded growth

**File:** `app/core/agent/chat_session.py:77-78`, `156-167`
**Issue:** Module docstring says `_SESSIONS` "lives for the process lifetime"
— deliberate. But there is no LRU cap or TTL sweep, so a long-lived process
serving many distinct browser sessions accumulates `SessionState` entries
indefinitely. With the D-CHAT-15 sliding-window cap of 12 messages each,
each entry is bounded in size, but the dict itself is not. For an intranet
tool restarted nightly this is a non-issue; flagged in case the deployment
shifts to longer-lived processes.
**Fix:** Add a soft cap inside `get_or_create_session`:
```python
_SESSION_SOFT_CAP = 1000  # ~1000 distinct browser sessions before eviction
def get_or_create_session(session_id: str) -> SessionState:
    with _SESSION_LOCK:
        if session_id not in _SESSIONS:
            if len(_SESSIONS) >= _SESSION_SOFT_CAP:
                # Evict oldest by insertion order (Py3.7+ dicts are ordered)
                _SESSIONS.pop(next(iter(_SESSIONS)))
            _SESSIONS[session_id] = SessionState()
        return _SESSIONS[session_id]
```

### IN-03: `_get_engine` private-attr access duplicated between agent + router

**File:** `app/core/agent/chat_agent.py:246-260`, `app_v2/routers/ask.py:377-396`
**Issue:** Both call sites do `engine_fn = getattr(ctx.deps.db, "_get_engine",
None)` and reach into the adapter's underscore-prefixed accessor to apply
SET SESSION pragmas. This is a private-API leak that ties chat code to the
adapter's internal shape. If the adapter renames `_get_engine` to
`get_engine` (or a `Postgres` adapter omits it altogether), both sites
silently fall back to the unguarded `run_query` path with NO READ ONLY
session and NO statement timeout. The duplication also means a fix in one
place won't propagate to the other.
**Fix:** Promote the SAFE-harness `(READ ONLY + max_execution_time + read_sql_query)`
sequence to a method on `DBAdapter` (e.g. `run_query_safe(sql, timeout_s)`)
and have both `_execute_and_wrap` and `_hydrate_final_card` call that.
Single place to keep the harness.

### IN-04: `_scrub_messages_inplace` only scrubs string-valued ToolCallPart args

**File:** `app/core/agent/chat_session.py:236-240`
**Issue:** The dict-comprehension scrubs `args[k]` only when
`isinstance(v, str)`. Today's six tools all take `str | int` args, so this
is correct. If a future tool accepts `list[str]` or `dict[str, str]` (e.g.,
"filter columns" or "join hints"), path-shaped strings nested inside those
structures would NOT be scrubbed and would leak to OpenAI on the next
turn's `message_history` replay. The current shape is brittle to additive
changes and lacks a unit test asserting the contract.
**Fix:** Walk arg values recursively:
```python
def _scrub_value(v):
    if isinstance(v, str):
        return scrub_paths(v)
    if isinstance(v, list):
        return [_scrub_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _scrub_value(x) for k, x in v.items()}
    return v

# inside _scrub_messages_inplace:
p.args = {k: _scrub_value(v) for k, v in p.args.items()}
```

### IN-05: Final-card table-rows assertion only checks tag presence

**File:** `tests/v2/test_ask_routes.py:247-307`
**Issue:** `test_get_ask_stream_final_frame_contains_table_rows_when_sql_returns_rows`
asserts `"<tbody>" in body` and `"</tbody>" in body`. The Browse `_grid.html`
macro renders an empty `<tbody></tbody>` for empty DataFrames too, so this
assertion would PASS on a regression that returned an empty table while still
showing the structural tags. The test uses `pd.DataFrame({"a": [1, 2], "b":
["x", "y"]})` so the actual rendered tbody contains real rows; an assertion
on `<td>` content (or `body.count("<tr>") >= 3` to count thead + 2 data
rows) would catch a regression where the macro rendered headers only.
**Fix:**
```python
assert "<tbody>" in body
assert "</tbody>" in body
# Stronger: at least one data cell rendered (1 thead row + 2 data rows = 3 <tr>)
assert body.count("<tr>") >= 3, f"expected >=3 <tr> tags, got: {body.count('<tr>')}"
```

### IN-06: Foreign-session test relies on subtle TestClient lifespan ordering

**File:** `tests/v2/test_ask_routes.py:181-191`, `210-218`
**Issue:** Both `test_post_ask_cancel_with_foreign_session_returns_403` and
`test_get_ask_stream_with_foreign_session_returns_403` create a second
`TestClient(app)` inside the test body without a `with ... as` block. This
works because the fixture's outer `with TestClient(app) as c:` already ran
lifespan and set `app.state.settings` / `app.state.db`. If a future
contributor restructures the fixture to dispose state on teardown OR uses
a TestClient context manager on the inner `other = TestClient(app)`, the
second TestClient will re-run lifespan and clobber the stub
`app.state.settings`. The test would then fail with a confusing error rather
than the cleaner 403 assertion. Add an explicit comment or use a fresh
context-managed client that re-applies the stubs.
**Fix:** Document the dependency or extract the cookie-construction trick
into a helper:
```python
# Helper at module level:
def _make_other_session_client() -> TestClient:
    """Same app, fresh cookie jar — does NOT re-run lifespan."""
    other = TestClient(app)
    other.cookies.set("pbm2_session", "b" * 32)
    return other
```

---

_Reviewed: 2026-05-03_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
