# Phase 2: NL Agent Layer - Research

**Researched:** 2026-04-23
**Domain:** PydanticAI agent construction, SQL validation, LLM adapter wiring, Streamlit async
**Confidence:** HIGH (core PydanticAI API), MEDIUM (async/Streamlit interop — multiple approaches, pick one)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-17:** New "Ask" page as third `st.Page` — Browse (default) → Ask → Settings.
- **D-18:** Answer layout: question input → (NL-05 confirmation row) → result table via `st.dataframe` → plain-text LLM summary via `st.write` → collapsed SQL expander.
- **D-19:** History panel is collapsible `st.expander("History ({N})")` above the question input, off by default. Session-only. Clicking entry refills question and reruns.
- **D-20:** Regenerate button (NL-03) lives inside the SQL expander as a secondary button. Reuses last question + confirmed_params, fresh LLM call.
- **D-21:** NL-05 param confirmation via `st.multiselect` pre-checked with agent proposals. Same "InfoCategory / Item" label format as Browse.
- **D-22:** Agent failure (SAFE-04): `st.error("Agent stopped: {reason}")` banner + `st.expander("Partial output")` below. Failed history entry with `status: "failed"`.
- **D-23:** Ollama JSON fallback: silent `json.loads` → regex first-JSON-block → plain-text → give up. Raw output in `st.expander("LLM raw output")`. No user warning unless all fallbacks fail.
- **D-24:** Single PydanticAI `@agent.tool` `run_sql(sql)`. Enforces `allowed_tables=["ufs_data"]`, sqlparse SELECT-only validation (SAFE-02), LIMIT injection (SAFE-03), `SET SESSION TRANSACTION READ ONLY`, `timeout_s=30`. No other tools — agent uses NL-05 for param disambiguation.
- **D-25:** OpenAI sensitivity warning: `st.warning(...)` first time OpenAI used in session, dismissible. Exact copy locked in UI-SPEC.
- **D-26:** Path-scrub (SAFE-06): regex `/sys/.*`, `/proc/.*`, `/dev/.*` → `<path>` applied to `Result` column when `active_llm == "openai"`. Scrub happens inside `run_sql` after fetch, before wrapping in `<db_data>...</db_data>`.
- **D-27:** Starter prompts at `config/starter_prompts.yaml` (gitignored). Ship `config/starter_prompts.example.yaml`. 8 prompts covering lookup / compare / filter shapes. Click fills text_area; user still presses Enter to run.

### Claude's Discretion

- Exact PydanticAI model config (temperature=0.2, max_tokens 2000 for OpenAI, no cap for Ollama).
- `allowed_tables` enforcement mechanism — sqlparse AST walk vs simple regex.
- Starter prompt exact text — 8 UFS-specific prompts.
- Session-history truncation at 50 — LRU (drop oldest).
- Backend switch affordance — `st.sidebar.radio` (chosen in UI-SPEC, 2-option clarity).

### Deferred Ideas (OUT OF SCOPE)

- Multi-query planning, NL-V2-01 editable SQL, NL-V2-02 "Why this query?", cross-session history persistence, shareable NL URLs, LLM-generated chart suggestions, agent schema reflection as a tool.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NL-01 | NL question → result table + plain-text LLM summary | PydanticAI agent with `SQLResult` output_type |
| NL-02 | LLM-generated SQL in collapsed expander on every result | `result.output.query` exposed to UI |
| NL-03 | Regenerate button — fresh LLM call, same question + confirmed params | Session state `ask.confirmed_params` + re-call agent |
| NL-04 | Session history panel — session-only, clear on refresh | `ask.history` in session state, LRU 50 |
| NL-05 | Agent proposes candidate params, user confirms before SQL executes | `ClarificationNeeded` output type → multiselect UX |
| NL-06 | Correctly handles lookup / compare / filter question shapes | System prompt + schema context in agent message |
| NL-07 | User can switch LLM backend from sidebar | `active_llm` session state → rebuild agent on switch |
| NL-08 | Both backends use same openai SDK, differ only in base_url/api_key | `OpenAIChatModel` + `OpenAIProvider(base_url=...)` |
| NL-09 | Ollama JSON fallback chain so smaller models don't crash the agent | Pure-function fallback, unit-testable |
| NL-10 | Default backend Ollama; OpenAI shows one-time data-sensitivity warning | `ask.openai_warning_dismissed` session key |
| SAFE-02 | Agent SQL validated — single SELECT, allowed_tables only | sqlparse validator module |
| SAFE-03 | LIMIT injected if missing, clamped to row_cap | sqlparse LIMIT detector + string append |
| SAFE-04 | max_steps=5, timeout_s=30; exceed = clean abort with user message | `UsageLimits(tool_calls_limit=5)` + threading timeout |
| SAFE-05 | DB rows wrapped in `<db_data>...</db_data>` in LLM context | System prompt instruction + run_sql wrapping |
| SAFE-06 | /sys/ /proc/ /dev/ paths scrubbed before cloud LLM sees them | `re.sub` on Result column inside run_sql |
| ONBD-01 | Starter prompt gallery (6-10 prompts) on NL page | YAML file + 4-col `st.columns` gallery |
| ONBD-02 | Starter YAML editable without code change | Pure YAML, loaded at render time with PyYAML |
</phase_requirements>

---

## Summary

Phase 2 adds a PydanticAI `Agent` with one tool (`run_sql`) that turns NL questions into validated, LIMIT-capped, read-only SQL queries and returns structured output (`SQLResult | ClarificationNeeded`). The entire LLM abstraction layer (OpenAI + Ollama) is already stubbed in the codebase but needs to be rewired: the existing `OllamaAdapter` uses the raw Ollama REST API, not the `openai` SDK — Phase 2 must build a new PydanticAI-native model factory instead of adapting the old adapter. The sidebar LLM selector is already rendered but inert; activating it requires switching from `st.sidebar.selectbox` to `st.sidebar.radio` and writing the selected backend name to `st.session_state["active_llm"]`.

The key technical risk is Streamlit's async event loop conflict with PydanticAI's `agent.run_sync()`. The official recommendation is `nest_asyncio.apply()` — this must be called once at module import time in `app/pages/ask.py`. An alternative (running in a `ThreadPoolExecutor`) is more robust but adds complexity. `nest_asyncio` is the pragmatic first choice given the simple intranet deployment.

The SQL validator is a pure function (no I/O) and is fully unit-testable. The `allowed_tables` check via `sqlparse` token walk is more auditable than regex because it handles quoted identifiers and subquery table names correctly.

**Primary recommendation:** Build the agent core (`app/core/agent/nl_agent.py`) as a thin factory; keep all validation in `app/services/sql_validator.py` and `app/services/sql_limiter.py` as pure functions; wire the Ask page as `app/pages/ask.py`; extend `streamlit_app.py` sidebar for the live LLM radio selector.

---

## Standard Stack

### Core (all already in requirements.txt — NOT YET INSTALLED in venv)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| pydantic-ai | `>=1.0,<2.0` | NL agent framework | Not in venv yet — Wave 0 must install |
| openai | `>=1.50` | LLM client for both OpenAI and Ollama via `base_url` | Not in venv yet |
| sqlparse | `>=0.5` | SQL parsing, validation, pretty-print | Not in venv yet |
| nest-asyncio | `~1.6` | Patches event loop for Streamlit + PydanticAI | NOT in requirements.txt — must add |

`nest-asyncio` is the only new dependency. It is not in requirements.txt and must be added.

**Installation (Wave 0):**
```bash
pip install pydantic-ai>=1.0,<2.0 openai>=1.50 sqlparse>=0.5 nest-asyncio>=1.6
```

Add to `requirements.txt`:
```
nest-asyncio>=1.6
```

### Environment Availability

| Dependency | Available | Version | Action |
|------------|-----------|---------|--------|
| pydantic-ai | No (in requirements.txt, not installed) | — | Wave 0: `pip install` |
| openai SDK | No (in requirements.txt, not installed) | — | Wave 0: `pip install` |
| sqlparse | No (in requirements.txt, not installed) | — | Wave 0: `pip install` |
| nest-asyncio | No (not in requirements.txt) | — | Wave 0: add to requirements.txt and install |
| Ollama | ASSUMED present locally | — | User's intranet setup; not verifiable |
| MySQL (ufs_data) | ASSUMED present | — | Phase 1 assumed it worked |

---

## Architecture Patterns

### Recommended File Layout

```
app/
├── core/
│   └── agent/
│       ├── __init__.py        (exists, empty)
│       ├── config.py          (exists — AgentConfig)
│       └── nl_agent.py        (NEW — agent factory + result types)
├── services/
│   ├── sql_validator.py       (NEW — pure function: validate_sql())
│   ├── sql_limiter.py         (NEW — pure function: inject_limit())
│   └── path_scrubber.py       (NEW — pure function: scrub_paths())
├── pages/
│   └── ask.py                 (NEW — Ask page render function)
└── adapters/
    └── llm/
        └── pydantic_model.py  (NEW — build_pydantic_model() factory)
config/
├── starter_prompts.yaml          (NEW — gitignored, user editable)
└── starter_prompts.example.yaml  (NEW — committed template)
streamlit_app.py                  (MODIFIED — activate LLM radio, add Ask page)
tests/
├── agent/
│   ├── test_nl_agent.py       (NEW)
├── services/
│   ├── test_sql_validator.py  (NEW)
│   ├── test_sql_limiter.py    (NEW)
│   └── test_path_scrubber.py  (NEW)
└── pages/
    └── test_ask_page.py       (NEW — AppTest-based)
```

### Pattern 1: PydanticAI Agent Construction

**API parameter names (VERIFIED via pydantic.dev docs):**
- Constructor: `output_type` (NOT `result_type`)
- Run: `usage_limits=UsageLimits(tool_calls_limit=5)`
- Result accessor: `result.output`

```python
# Source: https://pydantic.dev/docs/ai/core-concepts/output/ (verified 2026-04-23)
from __future__ import annotations
from typing import Annotated
import asyncio
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from app.core.agent.config import AgentConfig
from app.adapters.db.base import DBAdapter


class SQLResult(BaseModel):
    query: str = Field(description="The SQL SELECT query to execute")
    explanation: str = Field(description="Plain-English summary of what this query does")


class ClarificationNeeded(BaseModel):
    message: str = Field(description="Question to ask the user for clarification")
    candidate_params: list[str] = Field(
        default_factory=list,
        description="Proposed InfoCategory/Item labels from the DB catalog"
    )


# Deps type bundles everything the tool needs at runtime
class AgentDeps(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    db: DBAdapter
    agent_cfg: AgentConfig
    active_llm_type: str  # "openai" | "ollama"


# Agent is a module-level singleton per backend (cached via @st.cache_resource)
def build_agent(model) -> Agent:
    agent: Agent[AgentDeps, SQLResult | ClarificationNeeded] = Agent(
        model,
        output_type=SQLResult | ClarificationNeeded,  # type: ignore[arg-type]
        deps_type=AgentDeps,
        model_settings={"temperature": 0.2},
        system_prompt=_SYSTEM_PROMPT,
    )

    @agent.tool
    def run_sql(ctx: RunContext[AgentDeps], sql: str) -> str:
        """Execute a validated SQL SELECT against ufs_data and return rows as text."""
        from app.services.sql_validator import validate_sql
        from app.services.sql_limiter import inject_limit
        from app.services.path_scrubber import scrub_paths

        cfg = ctx.deps.agent_cfg
        # SAFE-02: validate
        vr = validate_sql(sql, cfg.allowed_tables)
        if not vr.ok:
            return f"SQL rejected: {vr.reason}"
        # SAFE-03: inject LIMIT
        sql = inject_limit(sql, cfg.row_cap)
        # execute with read-only + timeout
        result_text = _execute_read_only(ctx.deps.db, sql, cfg.timeout_s)
        # SAFE-06: path scrub for cloud LLM
        if ctx.deps.active_llm_type == "openai":
            result_text = scrub_paths(result_text)
        # SAFE-05: delimit DB data
        return f"<db_data>{result_text}</db_data>"

    return agent
```

### Pattern 2: PydanticAI Model Factory (openai SDK dual base_url)

The key finding: PydanticAI 1.x uses `OpenAIChatModel` + `OpenAIProvider`, NOT the raw `openai.OpenAI()` client used by the legacy adapters. There is also a dedicated `OllamaModel` + `OllamaProvider`. [VERIFIED: pydantic.dev/docs/ai/models/openai/ and pydantic.dev/docs/ai/models/ollama/]

```python
# Source: https://pydantic.dev/docs/ai/models/openai/ (verified 2026-04-23)
# Source: https://pydantic.dev/docs/ai/models/ollama/ (verified 2026-04-23)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
from app.core.config import LLMConfig


def build_pydantic_model(cfg: LLMConfig):
    """Return a PydanticAI model object for the given LLMConfig."""
    if cfg.type == "openai":
        provider = OpenAIProvider(
            api_key=cfg.api_key or None,   # falls back to OPENAI_API_KEY env var
            base_url=cfg.endpoint or None, # None = default api.openai.com/v1
        )
        return OpenAIChatModel(cfg.model or "gpt-4o-mini", provider=provider)

    if cfg.type == "ollama":
        provider = OllamaProvider(
            base_url=(cfg.endpoint or "http://localhost:11434") + "/v1"
        )
        return OllamaModel(cfg.model or "qwen2.5:7b", provider=provider)

    raise ValueError(f"Unsupported LLM type for PydanticAI: {cfg.type}")
```

**NOTE on legacy adapters:** `app/adapters/llm/openai_adapter.py` and `ollama_adapter.py` remain untouched — they serve the Phase 1 `generate_sql` / `stream_text` interface. Phase 2 adds a parallel PydanticAI-native path. The old adapters are NOT used by the agent.

### Pattern 3: Agent Cache + Streamlit Async Fix

```python
# Source: https://pydantic.dev/docs/ai/overview/troubleshooting/ (verified 2026-04-23)
# nest_asyncio MUST be applied before any agent.run_sync() call.
# Call once at module load time in ask.py.
import nest_asyncio
nest_asyncio.apply()

import streamlit as st
from app.core.agent.nl_agent import build_agent, AgentDeps
from app.adapters.llm.pydantic_model import build_pydantic_model
from app.core.config import load_settings, find_llm


@st.cache_resource
def get_nl_agent(llm_name: str):
    """Build and cache a PydanticAI Agent per backend name.

    Keyed by llm_name so switching backends creates a new agent singleton.
    The agent itself is stateless; deps are injected at run time.
    """
    settings = load_settings()
    cfg = find_llm(settings, llm_name)
    if cfg is None:
        return None
    model = build_pydantic_model(cfg)
    return build_agent(model)
```

### Pattern 4: Agent Run in Streamlit

```python
from pydantic_ai.usage import UsageLimits
from pydantic_ai.exceptions import UsageLimitExceeded

with st.spinner("Thinking..."):
    try:
        result = agent.run_sync(
            user_question,
            deps=AgentDeps(db=db, agent_cfg=agent_cfg, active_llm_type=llm_type),
            usage_limits=UsageLimits(tool_calls_limit=agent_cfg.max_steps),
        )
        output = result.output   # SQLResult | ClarificationNeeded
    except UsageLimitExceeded:
        st.error("Agent stopped: reached the 5-step limit. ...")
    except TimeoutError:
        st.error("Agent stopped: query timed out after 30 seconds. ...")
```

**Timeout enforcement:** `UsageLimits(tool_calls_limit=5)` handles the step cap. Wall-clock timeout (30 s) is handled by `SET SESSION max_execution_time=30000` inside `_execute_read_only` (MySQL-side) rather than Python-side `signal.alarm` (which doesn't work in threads) or `asyncio.wait_for` (which requires native async). [VERIFIED: D-24 explicitly prefers MySQL-side timeout; confirmed by MySQL docs that max_execution_time applies to SELECT-only statements]

### Pattern 5: SQL Validator (SAFE-02)

```python
# app/services/sql_validator.py
# Source: sqlparse docs (sqlparse.readthedocs.io) + GitHub example extract_table_names.py
import sqlparse
import sqlparse.tokens as T
from pydantic import BaseModel


class ValidationResult(BaseModel):
    ok: bool
    reason: str = ""


def validate_sql(sql: str, allowed_tables: list[str]) -> ValidationResult:
    """Validate that sql is a single SELECT referencing only allowed_tables.

    Rejects:
    - Multi-statement input (count > 1 after sqlparse.split)
    - Non-SELECT statements (get_type() != 'SELECT')
    - SQL containing -- or /* comments (reject, don't strip)
    - Any table reference outside allowed_tables
    """
    # Multi-statement check
    statements = [s for s in sqlparse.parse(sql) if s.get_type() is not None]
    if len(statements) != 1:
        return ValidationResult(ok=False, reason="Only a single SELECT statement is allowed")

    stmt = statements[0]

    # Statement type check
    if stmt.get_type() != "SELECT":
        return ValidationResult(ok=False, reason=f"Only SELECT is allowed, got {stmt.get_type()}")

    # Comment check — reject immediately (don't attempt strip)
    for tok in stmt.flatten():
        if tok.ttype in (T.Comment.Single, T.Comment.Multiline):
            return ValidationResult(ok=False, reason="SQL comments are not allowed")

    # Table name extraction via FROM/JOIN walk
    tables = _extract_table_names(stmt)
    disallowed = tables - set(t.lower() for t in allowed_tables)
    if disallowed:
        return ValidationResult(ok=False, reason=f"Disallowed table(s): {disallowed}")

    return ValidationResult(ok=True)


def _extract_table_names(stmt) -> set[str]:
    """Walk token tree; collect identifier names after FROM and JOIN keywords."""
    from sqlparse.sql import Identifier, IdentifierList, Parenthesis

    tables: set[str] = set()
    from_seen = False

    def _walk(tokens):
        nonlocal from_seen
        for tok in tokens:
            if tok.ttype is T.Keyword and tok.normalized in ("FROM", "JOIN",
                    "INNER JOIN", "LEFT JOIN", "LEFT OUTER JOIN", "RIGHT JOIN"):
                from_seen = True
            elif from_seen:
                if isinstance(tok, Identifier):
                    tables.add(tok.get_real_name().lower())
                    from_seen = False
                elif isinstance(tok, IdentifierList):
                    for ident in tok.get_identifiers():
                        if isinstance(ident, Identifier):
                            tables.add(ident.get_real_name().lower())
                    from_seen = False
                elif isinstance(tok, Parenthesis):
                    _walk(tok.tokens)  # recurse into subqueries
                elif tok.ttype is T.Keyword:
                    from_seen = False
            if hasattr(tok, "tokens"):
                _walk(tok.tokens)

    _walk(stmt.tokens)
    return tables
```

### Pattern 6: LIMIT Injection (SAFE-03)

```python
# app/services/sql_limiter.py
# ASSUMED: regex-based detection is acceptable because the validator already
# confirmed the SQL is a single clean SELECT with no comments.
import re


def inject_limit(sql: str, row_cap: int) -> str:
    """Ensure sql has LIMIT <= row_cap.

    - If no LIMIT: append LIMIT {row_cap}
    - If LIMIT present with value > row_cap: replace with row_cap
    - If LIMIT present with value <= row_cap: leave unchanged
    """
    sql = sql.rstrip().rstrip(";")
    pattern = re.compile(r"\bLIMIT\s+(\d+)\b", re.IGNORECASE)
    match = pattern.search(sql)
    if match:
        existing = int(match.group(1))
        if existing > row_cap:
            sql = pattern.sub(f"LIMIT {row_cap}", sql)
        # else leave as-is
    else:
        sql = f"{sql} LIMIT {row_cap}"
    return sql
```

### Pattern 7: DB Execute with Read-Only + Timeout

```python
# Used inside run_sql tool — not in ufs_service (which takes structured filters)
import sqlalchemy as sa
from app.adapters.db.base import DBAdapter


def _execute_read_only(db: DBAdapter, sql: str, timeout_s: int) -> str:
    """Execute sql on a read-only session with MySQL-side timeout.

    Returns result rows as a pipe-delimited string for LLM context,
    truncated at row_cap (already injected by inject_limit).
    """
    timeout_ms = timeout_s * 1000
    with db._get_engine().connect() as conn:
        try:
            conn.execute(sa.text("SET SESSION TRANSACTION READ ONLY"))
        except Exception:
            pass  # Non-fatal: some MySQL configs don't support this
        try:
            conn.execute(sa.text(f"SET SESSION max_execution_time={timeout_ms}"))
        except Exception:
            pass  # Non-fatal: MySQL 5.7.8+ only
        import pandas as pd
        df = pd.read_sql_query(sa.text(sql), conn)

    # Format as text for LLM (compact table representation)
    if df.empty:
        return "(no rows returned)"
    header = " | ".join(str(c) for c in df.columns)
    rows = "\n".join(" | ".join(str(v) for v in row) for row in df.itertuples(index=False))
    return f"{header}\n{rows}"
```

**Why MySQL-side timeout over Python-side:** `signal.alarm` doesn't work in Streamlit's thread-pool workers (non-main thread). `asyncio.wait_for` requires async context. `SET SESSION max_execution_time` is enforced by MySQL itself and fires a clean `OperationalError` the Python code can catch. [CITED: dev.mysql.com/blog-archive/server-side-select-statement-timeouts/]

### Pattern 8: Path Scrubber (SAFE-06)

```python
# app/services/path_scrubber.py
import re

_PATH_PATTERN = re.compile(r"/(sys|proc|dev)/\S*")


def scrub_paths(text: str) -> str:
    """Replace /sys/*, /proc/*, /dev/* with <path> placeholder.

    Applied only when active LLM backend is OpenAI (D-26).
    The scrub is intentional — /dev/null and all /dev/* paths are replaced.
    """
    return _PATH_PATTERN.sub("<path>", text)
```

### Pattern 9: Ollama JSON Fallback (NL-09)

```python
# app/services/ollama_fallback.py — pure function, unit-testable
import json
import re
from typing import Any


def extract_json(raw: str) -> dict | None:
    """Fallback chain for Ollama models that emit imperfect JSON.

    Chain (D-23):
    1. json.loads(raw) — clean JSON
    2. Strip markdown code fences, retry
    3. re.search for first {...} block (DOTALL)
    4. Return None — give up
    """
    # Stage 1: clean JSON
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Stage 2: strip markdown fences
    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.DOTALL)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Stage 3: regex first JSON block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None  # all fallbacks failed
```

**Note:** PydanticAI's `OllamaModel` handles its own JSON parsing internally. The fallback chain above is for cases where the agent's result parsing fails and the raw LLM output needs to be shown in `st.expander("LLM raw output")` (D-23). The integration point is in the agent error handler, not inside PydanticAI itself.

### Pattern 10: Session State Keys (ask.* namespace)

```python
# Initialize at top of ask.py render() function
DEFAULTS = {
    "ask.question": "",
    "ask.history": [],           # list[dict] — question, sql, row_count, status, timestamp, id
    "ask.openai_warning_dismissed": False,
    "ask.confirmed_params": [],  # list[str] — "InfoCategory / Item" labels
    "ask.pending_params": [],    # proposed by agent (pre-confirmation)
    "ask.last_sql": "",
    "ask.last_df": None,         # DataFrame — NOT stored in history (avoid pickle overhead)
    "ask.last_summary": "",
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v
```

**History entry schema:**
```python
{
    "id": str,           # uuid4() for button key uniqueness
    "question": str,     # raw question text
    "sql": str,          # executed SQL (or partial)
    "row_count": int,    # 0 on failure
    "status": "ok" | "failed",
    "timestamp": str,    # "HH:MM" format
}
```
DataFrames are NOT stored in history — only `row_count`. The current result `ask.last_df` is a separate session state key.

### Pattern 11: Sidebar Activation

```python
# streamlit_app.py — render_sidebar() changes for Phase 2
# Change from: st.sidebar.selectbox("LLM Backend", ...)
# Change to:   st.sidebar.radio("LLM Backend", ...)
# Remove the Phase 2 hint caption

llm_names = [ll.name for ll in settings.llms]
if llm_names:
    # Default to Ollama (index of first "ollama"-type entry, or 0)
    default_idx = next(
        (i for i, ll in enumerate(settings.llms) if ll.type == "ollama"), 0
    )
    st.sidebar.radio(
        "LLM Backend",
        options=llm_names,
        index=default_idx,
        key="active_llm",
    )
    # Remove: st.sidebar.caption("LLM backend selection takes effect in Phase 2 (Ask page).")
```

### Pattern 12: Starter Prompt YAML

```yaml
# config/starter_prompts.example.yaml
# 8 prompts covering: 3x lookup-one-platform, 3x compare-across-platforms, 2x filter-by-value
- label: "WriteProt status by platform"
  question: "What is the WriteProt status for all LUNs on each platform?"
- label: "bkops across platforms"
  question: "Compare background operations (bkops_en) settings across all platforms."
- label: "LUN capacity for one platform"
  question: "Show all LUN capacities for platform X."
- label: "Platforms with purge disabled"
  question: "Which platforms have bkops purge disabled?"
- label: "ffu_features flags"
  question: "What are the ffu_features flags for each platform?"
- label: "Compare UFS version"
  question: "Compare the UFS specification version (spec_version) across all platforms."
- label: "Platforms with write protection on"
  question: "List all platforms where any LUN has write protection enabled."
- label: "eol_info fields"
  question: "Show eol_info fields for all platforms."
```

Loading pattern (no cache — file is tiny per D-27):
```python
def load_starter_prompts() -> list[dict]:
    import yaml
    from pathlib import Path
    path = Path("config/starter_prompts.yaml")
    if not path.exists():
        path = Path("config/starter_prompts.example.yaml")
    if not path.exists():
        return []
    with path.open() as f:
        return yaml.safe_load(f) or []
```

### Anti-Patterns to Avoid

- **Storing DataFrames in history list:** Causes large session state and potential pickle failures with pandas 3.x StringDtype. Store only `row_count`.
- **Creating agent on every Streamlit rerun:** The `Agent` object should be `@st.cache_resource` keyed on `llm_name`. Recreating per rerun is expensive and creates multiple event loop contexts.
- **Using old `OllamaAdapter._chat()` for the PydanticAI agent:** The old adapter calls the raw Ollama REST endpoint, not the OpenAI-compatible `/v1` endpoint. PydanticAI's `OllamaModel` expects the `/v1` path. They are parallel, not the same.
- **`signal.alarm` for timeout in Streamlit threads:** Only works in the main thread. Use `SET SESSION max_execution_time` instead.
- **Calling `asyncio.run()` inside Streamlit:** Raises `RuntimeError: This event loop is already running`. Use `agent.run_sync()` with `nest_asyncio.apply()`.
- **Injecting LIMIT before sqlparse validation:** Always validate first, then inject. The validator checks statement count and type on the original string.
- **f-string interpolation of `sql` into any larger string before executing:** `run_sql` receives the sql string from the LLM. It must go through sqlparse validation and then be passed as `sa.text(sql)` — never further interpolated.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM structured output (Union types) | Custom JSON parser + prompt engineering | PydanticAI `output_type=SQLResult \| ClarificationNeeded` | PydanticAI registers each union member as a separate tool, dramatically improving model reliability |
| Agent step cap | Manual counter in tool wrapper | `UsageLimits(tool_calls_limit=5)` passed to `run_sync()` | Framework raises `UsageLimitExceeded` cleanly; no counter state to maintain |
| SQL pretty-printing for display | Regex-based formatter | `sqlparse.format(sql, reindent=True, keyword_case="upper")` | Already in scaffolding dependency |
| Async-in-sync bridging for Streamlit | Thread pool + future polling | `nest_asyncio.apply()` + `agent.run_sync()` | One line; officially recommended by PydanticAI docs |
| DB row text formatting for LLM | DataFrame-to-HTML / JSON | Simple pipe-delimited header + rows | Compact, LLM-readable, avoids JSON nesting overhead against 30k token limit |

---

## Common Pitfalls

### Pitfall 1: `output_type` vs `result_type`
**What goes wrong:** Passing `result_type=...` to `Agent()` raises `TypeError: unexpected keyword argument`.
**Root cause:** PydanticAI 1.x uses `output_type`, not `result_type`. The old 0.x API used `result_type`.
**How to avoid:** Use `output_type=SQLResult | ClarificationNeeded` (verified from current docs).

### Pitfall 2: OllamaAdapter is NOT compatible with PydanticAI OllamaModel
**What goes wrong:** Attempting to reuse the Phase 1 `OllamaAdapter` for PydanticAI fails — the adapter calls `/api/chat` (raw Ollama protocol); PydanticAI's `OllamaModel` calls `/v1/chat/completions` (OpenAI-compatible).
**Root cause:** Two different Ollama API surfaces. The raw `/api/chat` endpoint exists alongside the OpenAI-compatible `/v1` endpoint on the same Ollama server.
**How to avoid:** Build a new `build_pydantic_model()` factory using `OllamaModel` + `OllamaProvider(base_url="http://localhost:11434/v1")`.

### Pitfall 3: Agent creation inside Streamlit script block (no cache)
**What goes wrong:** `Agent(model, ...)` is called every rerun, creating a new event loop context. With `nest_asyncio`, this causes "RuntimeError: Event loop is closed" on the second rerun.
**Root cause:** PydanticAI agents maintain internal async state. Creating one per rerun is unsafe.
**How to avoid:** Wrap `build_agent()` call in `@st.cache_resource` keyed on `llm_name`.

### Pitfall 4: Multi-statement SQL passes `get_type()` check
**What goes wrong:** `sqlparse.parse("SELECT 1; DROP TABLE ufs_data")[0].get_type()` returns `"SELECT"` — it only looks at the first statement. The `DROP TABLE` is in the second parsed statement.
**Root cause:** `sqlparse.parse()` returns a tuple of statements; `get_type()` on the first one doesn't see the second.
**How to avoid:** Check `len([s for s in sqlparse.parse(sql) if s.get_type() is not None]) == 1` before the type check.

### Pitfall 5: LIMIT injection double-applies on second Regenerate
**What goes wrong:** SQL already has `LIMIT 200`; inject_limit is called again and appends `LIMIT 200` again → `SELECT ... LIMIT 200 LIMIT 200`, which is a MySQL syntax error.
**Root cause:** Not checking for existing LIMIT.
**How to avoid:** Use the regex-based `inject_limit()` in Pattern 6 above — it detects and clamps existing LIMIT, never appends a second one.

### Pitfall 6: `nest_asyncio.apply()` must be called before first `import pydantic_ai`
**What goes wrong:** Calling `nest_asyncio.apply()` after PydanticAI has already set up its internal event loop may not patch all relevant parts.
**Root cause:** Import order matters with event loop patching.
**How to avoid:** Place `import nest_asyncio; nest_asyncio.apply()` as the FIRST two lines of `app/pages/ask.py`, before all other imports.

### Pitfall 7: UsageLimits must be passed to `run_sync()`, not to `Agent()`
**What goes wrong:** Passing `usage_limits=...` to `Agent()` constructor silently does nothing (or raises TypeError).
**Root cause:** `usage_limits` is a per-run parameter. [VERIFIED: pydantic-ai GitHub issue #1987]
**How to avoid:** Always pass `usage_limits=UsageLimits(tool_calls_limit=5)` to `agent.run_sync(...)`.

### Pitfall 8: `max_execution_time` is MySQL 5.7.8+ only
**What goes wrong:** On older MySQL or MariaDB, `SET SESSION max_execution_time=...` raises an exception.
**Root cause:** Feature was added in MySQL 5.7.8. MariaDB uses `max_statement_time` (different name).
**How to avoid:** Wrap both SET SESSION statements in try/except (same pattern as the existing SAFE-01 `SET SESSION TRANSACTION READ ONLY` in ufs_service.py).

### Pitfall 9: `ask.last_df` is None on page load (before first run)
**What goes wrong:** Answer zone renders unconditionally, pandas operations on `None` raise `AttributeError`.
**Root cause:** Session state key exists but holds `None` before first run.
**How to avoid:** Guard the answer zone render: `if st.session_state.get("ask.last_df") is not None:`.

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| `OllamaAdapter` using raw `/api/chat` | `OllamaModel` + `OllamaProvider(base_url=".../v1")` | Phase 2 adds PydanticAI-native path; old adapter is NOT replaced |
| `selectbox` for LLM selector (inert) | `st.sidebar.radio` (active, 2 options) | D-41 discretion in UI-SPEC |
| `result_type=` (PydanticAI 0.x) | `output_type=` (PydanticAI 1.x) | API-stable since Sep 2025 |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Ollama is available locally at `http://localhost:11434` for the team | Environment Availability | Ollama connection fails at first Ask page use; team must install Ollama |
| A2 | `OllamaProvider` accepts `base_url` with `/v1` suffix as shown | Pattern 2 | Build error or 404 on first agent call; fall back to `OpenAIChatModel(provider=OpenAIProvider(base_url="http://localhost:11434/v1"))` |
| A3 | `nest_asyncio.apply()` before first import resolves Streamlit + PydanticAI event loop conflict reliably | Pattern 3, Pattern 6 | RuntimeError on first agent run; fallback is ThreadPoolExecutor pattern |
| A4 | `SET SESSION max_execution_time=30000` is supported on the team's MySQL instance | Pattern 7 | Timeout enforcement silently disabled; queries may run >30s (non-fatal, wrapped in try/except) |
| A5 | The 8 starter prompt texts in Pattern 12 use real column/field names from ufs_data | Pattern 12 | Prompts work but return no results; need to adjust label names to match actual InfoCategory/Item values |

---

## Open Questions (RESOLVED)

1. **Ollama model name for starter prompt placeholder text**
   - What we know: `AgentConfig.model` defaults to `""` (inherits from LLMConfig); typical small models are `qwen2.5:7b` or `llama3.2:3b`
   - What's unclear: Which model the team has actually pulled to their Ollama instance
   - Recommendation: Use `cfg.model or "qwen2.5:7b"` as the default in `build_pydantic_model()`. Planner should add a note: "team must run `ollama pull qwen2.5:7b`".

2. **`OllamaProvider` vs `OpenAIProvider` for Ollama**
   - What we know: Both work for Ollama's `/v1` endpoint; `OllamaProvider` is the more semantically correct choice; `OpenAIProvider(base_url=".../v1")` is the fallback
   - What's unclear: Whether `OllamaProvider` handles the `OLLAMA_BASE_URL` env var automatically (documented as yes)
   - Recommendation: Use `OllamaProvider` with explicit `base_url` from `LLMConfig.endpoint`. Document the env var as a fallback in code comment.

3. **Agent result for NL-05 flow** — two-turn interaction
   - What we know: Agent returns `ClarificationNeeded(message, candidate_params)` on first run; user confirms params; second run uses confirmed params in the prompt
   - What's unclear: How to pass confirmed params back into the second agent run — via the user prompt text, or via `deps`?
   - Recommendation: Inject confirmed params as a structured user message: `f"User-confirmed parameters: {confirmed_params}\n\nOriginal question: {question}"`. This keeps the agent stateless and avoids multi-turn message history complexity.

4. **System prompt language**
   - What we know: The existing `SQL_SYSTEM_PROMPT` in `app/adapters/llm/base.py` is in Korean
   - What's unclear: Whether the PydanticAI agent system prompt should be Korean or English (English is more reliable for most LLMs)
   - Recommendation: Use English for the PydanticAI agent system prompt. The LLM produces better SQL with English instructions across both OpenAI and Ollama models. The summary response can be in either language.

---

## Environment Availability

| Dependency | Required By | Available | Version | Action |
|------------|-------------|-----------|---------|--------|
| pydantic-ai | NL agent | No (in requirements.txt) | — | Wave 0: `pip install pydantic-ai>=1.0,<2.0` |
| openai SDK | PydanticAI model | No (in requirements.txt) | — | Wave 0: `pip install openai>=1.50` |
| sqlparse | SQL validation | No (in requirements.txt) | — | Wave 0: `pip install sqlparse>=0.5` |
| plotly | Viz (Phase 1, same venv) | No (in requirements.txt) | — | Wave 0: install together |
| nest-asyncio | Streamlit async fix | No (NOT in requirements.txt) | — | Wave 0: add to requirements.txt + install |
| Ollama process | Ask page | ASSUMED | ASSUMED | Team must have `ollama serve` running |
| MySQL ufs_data | All DB queries | ASSUMED | ASSUMED | Inherited from Phase 1 assumption |

**Missing with no fallback (blocking):**
- `pydantic-ai`, `openai`, `sqlparse`, `nest-asyncio` — all must be installed before any Phase 2 code runs. Wave 0 plan must include `pip install -r requirements.txt`.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V4 Access Control | yes | `allowed_tables=["ufs_data"]` checked in validate_sql before every execution |
| V5 Input Validation | yes | sqlparse validator: statement type, single statement, no comments, table allowlist |
| V5 SQL Injection | yes | LLM-generated SQL is still untrusted input; validate_sql + read-only user is the double backstop |
| V6 Cryptography | no | No crypto in this phase |
| V2 Authentication | no | Phase 1 concern (streamlit-authenticator) |

### Threat Patterns

| Pattern | STRIDE | Mitigation |
|---------|--------|-----------|
| Prompt injection via `<db_data>` | Tampering | System prompt explicitly marks `<db_data>` as untrusted data, never instructions (SAFE-05) |
| LLM-generated multi-statement SQL | Tampering | sqlparse statement count check (SAFE-02) |
| LLM generates SQL with non-allowed table | Elevation of privilege | `allowed_tables` check via AST walk (SAFE-02) |
| LLM generates long-running query | DoS | `SET SESSION max_execution_time=30000` (SAFE-04) + `LIMIT` injection (SAFE-03) |
| DB data with /sys/ /proc/ paths sent to cloud | Information disclosure | `scrub_paths()` applied before LLM context (SAFE-06) |
| Read-only MySQL user | Tampering | Phase 1 SAFE-01 already enforced — primary backstop for all SQL injection |

---

## Sources

### Primary (HIGH confidence)
- [PydanticAI Agent docs](https://pydantic.dev/docs/ai/core-concepts/agent/) — `output_type`, `deps_type`, `run_sync()`, `UsageLimits`
- [PydanticAI Output docs](https://pydantic.dev/docs/ai/core-concepts/output/) — Union output_type, each member as separate tool, `result.output`
- [PydanticAI OpenAI model docs](https://pydantic.dev/docs/ai/models/openai/) — `OpenAIChatModel`, `OpenAIProvider(base_url=...)`
- [PydanticAI Ollama model docs](https://pydantic.dev/docs/ai/models/ollama/) — `OllamaModel`, `OllamaProvider`
- [PydanticAI Troubleshooting](https://pydantic.dev/docs/ai/overview/troubleshooting/) — `nest_asyncio.apply()` pattern for Streamlit/Jupyter
- [PydanticAI UsageLimits API](https://ai.pydantic.dev/api/usage/) — `tool_calls_limit`, `request_limit`, `UsageLimitExceeded`
- [GitHub issue #1987](https://github.com/pydantic/pydantic-ai/issues/1987) — `usage_limits` must be in `run_sync()`, not Agent constructor

### Secondary (MEDIUM confidence)
- [MySQL max_execution_time](https://dev.mysql.com/blog-archive/server-side-select-statement-timeouts/) — SELECT-only timeout, 5.7.8+ requirement
- [sqlparse GitHub extract_table_names example](https://github.com/andialbrecht/sqlparse/blob/master/examples/extract_table_names.py) — FROM/JOIN token walk pattern
- [Streamlit asyncio discussion](https://discuss.streamlit.io/t/got-that-asyncio-feeling-how-to-run-async-code-in-streamlit/89314) — ThreadPoolExecutor alternative to nest_asyncio

### Tertiary (LOW confidence — needs validation)
- OllamaProvider exact `base_url` suffix requirement (`/v1`) — inferred from Ollama docs, not directly tested
- `nest_asyncio.apply()` import order requirement — from community reports, not PydanticAI official docs

---

## Metadata

**Confidence breakdown:**
- PydanticAI agent API: HIGH — verified from official current pydantic.dev docs
- Async/Streamlit interop: MEDIUM — multiple community reports, one official pattern; not tested in this exact version combo
- sqlparse validator: MEDIUM — API verified, exact token-walk implementation is ASSUMED pattern
- MySQL timeout approach: MEDIUM — verified from MySQL docs, but MariaDB compatibility is ASSUMED

**Research date:** 2026-04-23
**Valid until:** 2026-05-23 (PydanticAI is fast-moving; re-verify if pydantic-ai version bumps past 1.86)
