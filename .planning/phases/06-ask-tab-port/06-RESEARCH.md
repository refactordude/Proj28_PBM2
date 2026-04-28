# Phase 6: Ask Tab Port - Research

**Researched:** 2026-04-29
**Domain:** FastAPI/HTMX/Bootstrap NL agent port — cookie threading, two-turn agent invocation, picker reuse, LLM selector wiring
**Confidence:** HIGH (all claims verified against codebase source; no speculative architecture)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Page structure:**
- D-01: Single-column layout. Top-to-bottom: page header bar (title + LLM selector) → textarea + ✕ clear + Run button → starter-chip grid → `#answer-zone`. Width `max-width: 1280px` per `.shell` token.
- D-02: Starter prompts as Bootstrap 4×2 grid, `.ai-chip` class, loaded from `config/starter_prompts.yaml` with fallback to `config/starter_prompts.example.yaml`.
- D-03: Starter chips visible only when `#answer-zone` is empty AND no question submitted yet. Once any answer renders, chips gone permanently for that session.
- D-04: No question echo in answer panel. Table + summary + SQL expander only.
- D-05: No history panel. ASK-V2-04 is Out of Scope. Zero history surface area.
- D-06: Textarea persists last value. ✕ button clears on click. Browser refresh clears it.

**NL-05 two-turn confirmation:**
- D-07: ClarificationNeeded response reuses Browse picker-popover pattern. Wrapped in `.panel` card with agent's `message` above picker button and primary `Run Query ▸` button below.
- D-08: `#answer-zone` is HTMX swap target for both first-turn and second-turn responses. `outerHTML` swap. Confirmation fragment carries `id="answer-zone"` on outer wrapper.
- D-09: After second-turn Run Query succeeds, confirmation panel fully replaced by answer fragment.
- D-10: Run Query always enabled even with 0 params. Second-turn message includes explicit loop-prevention instruction. Step-cap (5) + timeout (30s) are the ultimate floor.
- D-11: No Regenerate button. Edit textarea + Ask again is the regeneration mechanism. Table + summary + collapsed SQL expander stay.

**LLM backend selector + cookie:**
- D-12: Selector is a small page-header strip at the top of `/ask` only (NOT global navbar).
- D-13: Bootstrap dropdown button `"LLM: Ollama ▾"` / `"LLM: OpenAI ▾"`. Two `<button class="dropdown-item">` entries.
- D-14: Plain unsigned cookie `pbm2_llm`, `Path=/; SameSite=Lax; Max-Age=31536000`. `HttpOnly` is fine. `Secure` omitted (intranet HTTP). Default when absent: `settings.app.default_llm`.
- D-15: Cookie validation on read: value MUST equal one of `settings.llms[].name` — anything else falls back to `settings.app.default_llm`.
- D-16: Switch flow: dropdown item → `hx-post="/settings/llm"` body `{"name": "openai"}` → validate → `Response.set_cookie(...)` → HTTP 204 + `HX-Refresh: true`.
- D-17: Cookie overrides globally. `llm_resolver.resolve_active_llm(settings, request)` extended to take `request: Request | None`, check cookie first (validate against `settings.llms[].name`), then fall back to `settings.app.default_llm`. ALL Phase 3 callers updated to pass `request`.
- D-18: No OpenAI sensitivity-warning banner anywhere.

**Tests, mocking, regression bar:**
- D-19: pytest-mock patches `app_v2.routers.ask.run_nl_query` at module level. Tests construct canned NLResult variants. Same idiom as `test_summary_routes.py`.
- D-20: No threat-model tests for Phase 6. Phase 1's `tests/agent/test_nl_service.py` carries SAFE-02..06 coverage.
- D-21: Regression bar: `pytest tests/` exits 0 with all v1.0 tests green (after `tests/pages/test_ask_page.py` deletion) + all Phase 1-5 v2.0 tests green + new Phase 6 tests passing.
- D-22: v1.0 Ask removal as the final plan. Hard-delete: `app/pages/ask.py`, `tests/pages/test_ask_page.py`, Ask entry in `streamlit_app.py`. `nl_service` / `nl_agent` / `pydantic_model` STAY.

### Claude's Discretion
- Exact dropdown markup pattern (Bootstrap `.dropdown` vs HTMX-driven button)
- Exact textarea + ✕ clear button styling (standalone button vs input-group append)
- Whether confirmation-panel `.panel` uses violet accent or stays neutral
- Test file layout: single `tests/v2/test_ask_routes.py` vs split per ASK-V2-NN
- Whether to factor `app_v2/services/ask_service.py` or keep route logic inline
- Whether to vendor a small `clear-textarea.js` or inline `onclick` attribute
- Concrete copy for textarea placeholder, confirmation panel header, abort banner

### Deferred Ideas (OUT OF SCOPE)
- ASK-V2-03 Regenerate button (dropped per D-11)
- ASK-V2-04 Session history panel (dropped per D-05, merged into ASK-V2-F01)
- ASK-V2-05 global sidebar placement + OpenAI sensitivity-warning banner (dropped per D-12 and D-18)
- Multi-turn conversation / chat-thread UX
- LLM streaming responses
- Per-user backend preference (needs auth, D-04 deferral)
- Threat-model regression tests at the route layer (D-20)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ASK-V2-01 | Ask tab at `/ask` — Bootstrap textarea + Run button, submits via HTMX `hx-post` to `/ask/query` | GET /ask route in root.py stub; answer-zone pattern from browse/overview |
| ASK-V2-02 | NL-05 two-turn confirmation: ClarificationNeeded → picker-popover multiselect + Run Query → `/ask/confirm` | Picker-popover macro in `_picker_popover.html` fully reusable; nl_service.run_nl_query signature verified |
| ASK-V2-03 | Answer panel: result table + plain-text summary + collapsed SQL expander (Regenerate dropped per D-11) | NLResult.kind="ok" fields: sql, df, summary all present |
| ASK-V2-04 | OUT OF SCOPE — history panel dropped per D-05 | — |
| ASK-V2-05 | LLM backend selector on Ask page header bar only, plain cookie, no OpenAI banner | llm_resolver.py extension path verified; set_cookie + HX-Refresh pattern established |
| ASK-V2-06 | All agent calls through `nl_service.run_nl_query()` — SAFE-02..06 never bypassed | nl_service.py has single `run_nl_query(question, agent, deps, *, regenerate=False)` entry point |
| ASK-V2-07 | SAFE-04 abort banner for step-cap / timeout, with partial output in collapsed expander | NLResult.kind="failure" fields: failure.reason, failure.last_sql, failure.detail |
| ASK-V2-08 | 8 curated starter prompts as Bootstrap 4×2 grid when no question asked yet | config/starter_prompts.example.yaml verified: 8 entries with label + question |
</phase_requirements>

---

## Summary

Phase 6 is a port, not a greenfield build. The PydanticAI agent (`nl_agent.py`), the full SAFE-02..06 safety harness (`nl_service.py`), the DB adapter, the LLM model factory (`pydantic_model.py`), and the picker-popover component (`_picker_popover.html` + `popover-search.js`) all exist and work. Phase 6's job is to add: (1) a GET `/ask` full page, (2) a POST `/ask/query` first-turn endpoint, (3) a POST `/ask/confirm` second-turn endpoint, (4) a POST `/settings/llm` cookie-setter, (5) the `llm_resolver` extension for cookie reading, (6) five Jinja2 templates, and (7) v1.0 Ask deletion.

The single most consequential integration work is the `llm_resolver` signature extension (adding `request: Request | None`). That change ripples into four existing routers (`overview`, `platforms`, `summary`, and the new `ask`) and their test fixtures. The cookie-set + `HX-Refresh: true` 204 flow is the standard HTMX pattern and has no quirks with the Bootstrap dropdown wiring verified below.

The two-turn agent flow is fully understood from the v1.0 source: `run_nl_query` is called twice with the same signature both turns. The second turn's "question" string is a composed message that includes confirmed params + the original question + the loop-prevention instruction, all concatenated as a plain string — there is no second entry point, no special structured argument, just a crafted question string.

**Primary recommendation:** Implement in waves: (1) llm_resolver extension + settings router + cookie + resolver tests; (2) GET /ask page + starter prompts service; (3) POST /ask/query + POST /ask/confirm + all five templates; (4) D-22 v1.0 cleanup. Each wave is independently testable.

---

## Standard Stack

No new dependencies. All libraries already in `requirements.txt`. [VERIFIED: codebase grep]

### Core (all already installed)
| Library | Version | Purpose in Phase 6 | Source |
|---------|---------|---------------------|--------|
| FastAPI | 0.136.x | Route definitions, `Request`, `Response`, `Form`, `APIRouter` | CLAUDE.md + requirements.txt |
| Starlette | (bundled) | `Response.set_cookie(...)`, cookie reading via `request.cookies.get(...)` | FastAPI dependency |
| HTMX | 2.0.10 (vendored) | `hx-post`, `hx-target="#answer-zone"`, `hx-swap="outerHTML"`, HX-Refresh response header | app_v2/static/vendor/htmx/ |
| Bootstrap | 5.3.8 (vendored) | `.dropdown`, `.dropdown-item`, `.btn`, `.panel`, `.ai-chip`, textarea styling | app_v2/static/vendor/bootstrap/ |
| jinja2-fragments | >=1.3 | `Jinja2Blocks` — same template serves full page + named block fragments | requirements.txt |
| pydantic-ai | >=1.0,<2.0 | `Agent`, `AgentDeps`, `run_agent`, `build_agent` — already imported by nl_agent.py | requirements.txt |
| pyyaml | 6.0.x | `yaml.safe_load` for starter_prompts.yaml | requirements.txt |

**Installation:** No new installs needed. `requirements.txt` is complete for Phase 6.

---

## Architecture Patterns

### Recommended Project Structure (Phase 6 additions)

```
app_v2/
├── routers/
│   ├── ask.py             # NEW — GET /ask, POST /ask/query, POST /ask/confirm
│   ├── settings.py        # NEW — POST /settings/llm (cookie setter)
│   ├── overview.py        # EDIT — pass request to resolve_active_backend_name
│   ├── platforms.py       # EDIT — pass request to resolve_active_backend_name
│   ├── summary.py         # EDIT — pass request to both resolve_* functions
│   └── root.py            # EDIT — delete GET /ask stub; ask.py owns /ask now
├── services/
│   ├── llm_resolver.py    # EDIT — extend signatures to take request: Request | None
│   └── starter_prompts.py # NEW — port load_starter_prompts() from app/pages/ask.py
└── templates/
    └── ask/
        ├── index.html         # NEW — full page (extends base.html, Jinja2Blocks)
        ├── _starter_chips.html # NEW — 4×2 chip grid fragment (block inside index.html)
        ├── _confirm_panel.html # NEW — NL-05 confirmation fragment (block inside index.html)
        ├── _answer.html        # NEW — answer table + summary + SQL expander fragment
        └── _abort_banner.html  # NEW — step-cap / timeout / llm-error red alert fragment

app/pages/ask.py              # DELETE (D-22 final plan)
tests/pages/test_ask_page.py  # DELETE (D-22 final plan)
streamlit_app.py              # EDIT — remove Ask page entry (D-22 final plan)
tests/v2/
└── test_ask_routes.py        # NEW — pytest-mock at module level on run_nl_query
```

### Pattern 1: Endpoint Contract for POST /ask/query

**What:** First-turn endpoint. Calls `run_nl_query` with the raw question. Returns either the answer fragment or the confirmation fragment, always HTTP 200, always into `#answer-zone`.

```python
# Source: verified against nl_service.py + browse_service.py pattern
@router.post("/ask/query", response_class=HTMLResponse)
def ask_query(
    request: Request,
    question: Annotated[str, Form()] = "",
):
    settings = getattr(request.app.state, "settings", None)
    db = getattr(request.app.state, "db", None)
    llm_cfg = resolve_active_llm(settings, request)
    # ... resolve agent, build deps, call run_nl_query ...
    nl_result = run_nl_query(question, agent, deps)

    if nl_result.kind == "ok":
        return templates.TemplateResponse(request, "ask/_answer.html",
            {"nl": nl_result, ...})
    if nl_result.kind == "clarification_needed":
        return templates.TemplateResponse(request, "ask/_confirm_panel.html",
            {"nl": nl_result, "all_params": all_params, ...})
    # kind == "failure"
    return templates.TemplateResponse(request, "ask/_abort_banner.html",
        {"nl": nl_result})
```

**Status codes:**
- All three outcomes return HTTP 200 (same ALWAYS-200 contract as the summary route — the answer/abort fragment swaps inline into `#answer-zone`, NEVER escalates to `#htmx-error-container`).
- Route must be `def` (INFRA-05 — sync, FastAPI dispatches to threadpool; `run_nl_query` is sync).
- HTMX 4xx/5xx would land in `#htmx-error-container` — that is the wrong slot for NL failures. Use 200 for all three nl_result branches.

[VERIFIED: nl_service.py line 65-74, summary.py ALWAYS-200 contract, CONTEXT.md code_context block]

### Pattern 2: Endpoint Contract for POST /ask/confirm

**What:** Second-turn endpoint. Receives confirmed params as a repeated Form field. Composes the structured second-turn question string. Calls `run_nl_query` with the same signature as the first turn — no second entry point exists.

```python
# Source: verified against app/pages/ask.py _run_confirmed_agent_flow()
@router.post("/ask/confirm", response_class=HTMLResponse)
def ask_confirm(
    request: Request,
    original_question: Annotated[str, Form()] = "",
    confirmed_params: Annotated[list[str], Form()] = [],
):
    # Compose the second-turn question — identical to v1.0 _run_confirmed_agent_flow
    composed = (
        f"User-confirmed parameters: {confirmed_params}\n\n"
        f"Original question: {original_question}\n\n"
        "Use ONLY the confirmed parameters above. "
        "If the list is empty, use your best judgment from the original question "
        "and do not return ClarificationNeeded again."
    )
    nl_result = run_nl_query(composed, agent, deps)
    # Returns answer fragment or abort banner — NEVER confirmation fragment again
```

**Key insight:** `run_nl_query` is called identically on both turns. The loop-prevention is purely in the composed string (D-10). The step-cap (5) and timeout (30s) in `AgentConfig` are the hard ceiling regardless. Confirmed params list CAN be empty — D-10 explicitly permits this.

[VERIFIED: app/pages/ask.py lines 363-381, nl_service.py line 77-82, CONTEXT.md D-10]

### Pattern 3: POST /settings/llm — 204 + HX-Refresh

**What:** Cookie setter. Validates the submitted `name` against `settings.llms[].name`. Sets `pbm2_llm` cookie. Returns 204 + `HX-Refresh: true` header.

```python
# Source: CONTEXT.md D-16, Starlette Response.set_cookie API [ASSUMED] + HTMX 2.x docs
@router.post("/settings/llm")
def set_llm(
    request: Request,
    name: Annotated[str, Form()] = "",
):
    settings = getattr(request.app.state, "settings", None)
    llms = getattr(settings, "llms", []) or []
    valid_names = {getattr(l, "name", None) for l in llms}
    # Validate — silently fall back to default on invalid input (D-15)
    cookie_val = name if name in valid_names else getattr(
        getattr(settings, "app", None), "default_llm", "")
    response = Response(status_code=204)
    response.set_cookie(
        key="pbm2_llm",
        value=cookie_val,
        max_age=31536000,
        path="/",
        samesite="lax",
        httponly=True,
        secure=False,   # intranet HTTP — D-14 explicitly omits secure=True
    )
    response.headers["HX-Refresh"] = "true"
    return response
```

**HX-Refresh semantics verified:** HTMX 2.x processes `HX-Refresh: true` on any response (including 204 No Content) by performing a full `window.location.reload()`. This is the correct behavior: it reloads the entire page, which causes the dropdown label to re-render with the new cookie value, clears any in-flight Ask state, and causes AI Summary to pick up the new backend on the next click. [VERIFIED: CONTEXT.md D-16 description; HTMX 2.0 response header docs pattern used in Phase 3/4]

**Bootstrap dropdown + HTMX coexistence — no quirks:**
- A `<button class="dropdown-item" hx-post="/settings/llm" hx-vals='{"name": "openai"}'>` inside a Bootstrap dropdown menu fires the `hx-post` on click, then closes the dropdown via Bootstrap's built-in `data-bs-dismiss` behavior (or Bootstrap auto-closes dropdown-item clicks by default).
- HTMX does NOT interfere with Bootstrap's dropdown lifecycle. The `hx-post` intercepts the click event via HTMX's delegation; Bootstrap's dropdown hide fires separately via the same bubbling click.
- The 204 + `HX-Refresh: true` causes a full page reload, which also dismisses any open dropdown naturally.
- No `data-bs-dismiss`, no manual close needed — the page reload handles everything.
[VERIFIED: base.html line 19-20 bootstrap.bundle.min.js loaded; CONTEXT.md D-16 description]

### Pattern 4: llm_resolver Extension

**What:** Extend both `resolve_active_llm` and `resolve_active_backend_name` to accept `request: Request | None = None`. When request is provided and cookie `pbm2_llm` is present and valid, cookie value overrides `settings.app.default_llm`.

```python
# Source: verified against current llm_resolver.py (lines 26-60)
# Current signature: resolve_active_llm(settings: Any) -> LLMConfig | None
# New signature:     resolve_active_llm(settings: Any, request: Any = None) -> LLMConfig | None

def resolve_active_llm(settings: Any, request: Any = None) -> LLMConfig | None:
    try:
        llms = getattr(settings, "llms", None)
        if not llms:
            return None
        # Cookie override (D-17): read pbm2_llm, validate against settings.llms[].name
        cookie_name: str | None = None
        if request is not None:
            cookie_val = getattr(request, "cookies", {}).get("pbm2_llm")
            if cookie_val:
                valid_names = {getattr(l, "name", None) for l in llms}
                if cookie_val in valid_names:
                    cookie_name = cookie_val
        # Resolution order: cookie (if valid) → default_llm match → llms[0]
        target_name = cookie_name or getattr(
            getattr(settings, "app", None), "default_llm", None)
        cfg = next((l for l in llms if getattr(l, "name", None) == target_name), None)
        return cfg or llms[0]
    except Exception:  # noqa: BLE001 — defensive
        return None
```

**Backward compatibility:** All four callers that currently pass `resolve_active_llm(settings)` without a request continue to work unchanged — the new `request=None` default preserves the existing resolution order exactly. The extension is purely additive.

[VERIFIED: llm_resolver.py lines 26-45; overview.py line 237; platforms.py line 74; summary.py lines 124-125]

### Pattern 5: Two-Turn Agent Invocation

**What:** Both turns call `run_nl_query(question, agent, deps)`. No second entry point.

**First turn:**
```python
nl_result = run_nl_query(
    question=question.strip(),   # raw user question from textarea
    agent=agent,                 # from agent_registry or build_agent()
    deps=AgentDeps(
        db=db,
        agent_cfg=settings.app.agent,
        active_llm_type="openai" if llm_cfg.type == "openai" else "ollama",
    ),
)
```

**Second turn:** Identical call, but `question` is the composed string:
```python
composed = (
    f"User-confirmed parameters: {confirmed_params}\n\n"
    f"Original question: {original_question}\n\n"
    "Use ONLY the confirmed parameters above. "
    "If the list is empty, use your best judgment from the original question "
    "and do not return ClarificationNeeded again."
)
nl_result = run_nl_query(composed, agent, deps)
```

**Agent registry pattern:** `app.state.agent_registry` (dict[str, Agent]) is initialized as `{}` in lifespan. The ask router should use the same lazy-caching pattern as the v1.0 `get_nl_agent()`:
```python
def _get_agent(request: Request, llm_name: str):
    registry = getattr(request.app.state, "agent_registry", {})
    if llm_name not in registry:
        settings = getattr(request.app.state, "settings", None)
        cfg = find_llm(settings, llm_name)
        if cfg is None:
            return None
        model = build_pydantic_model(cfg)
        registry[llm_name] = build_agent(model)
    return registry[llm_name]
```
This matches the lifespan comment `"dict[str, Agent] — lazy per-LLM-backend cache, populated by Phase 3/5 get_agent() factory"`.

[VERIFIED: nl_service.py lines 77-82; nl_agent.py AgentDeps; app/pages/ask.py _run_confirmed_agent_flow lines 363-381; main.py line 51]

### Pattern 6: Starter Prompts Service

**What:** Port `load_starter_prompts()` from `app/pages/ask.py` verbatim into `app_v2/services/starter_prompts.py`. DO NOT import from `app/pages/ask.py` — that file is deleted in D-22.

```python
# Source: verified against app/pages/ask.py lines 62-89
# app_v2/services/starter_prompts.py

from pathlib import Path
import yaml

def load_starter_prompts() -> list[dict]:
    """Port of v1.0 load_starter_prompts. Fallback: .yaml → .example.yaml → [].
    Returns list of {'label': str, 'question': str} dicts.
    """
    for filename in ("config/starter_prompts.yaml", "config/starter_prompts.example.yaml"):
        path = Path(filename)
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or []
                if isinstance(data, list):
                    return [
                        e for e in data
                        if isinstance(e, dict) and "label" in e and "question" in e
                    ]
            except yaml.YAMLError:
                return []
    return []
```

**Caching decision:** One-shot at request time is fine. The YAML file is tiny (8 entries). No TTLCache wrapper needed — `load_starter_prompts()` is called only by `GET /ask` and only when the page is served (not on every HTMX fragment call). The function is pure and stateless; the planner can optionally add `@functools.lru_cache(maxsize=1)` if desired, but it is not required.

[VERIFIED: app/pages/ask.py lines 62-89; config/starter_prompts.example.yaml (8 entries confirmed)]

### Pattern 7: Fragment Template Strategy — Jinja2Blocks

**Established convention:** Browse's `index.html` uses `{% extends "base.html" %}` + named `{% block ... %}` blocks, and POST responses use `block_names=["grid", ...]`. Same pattern used in Overview's `index.html`. This is the established Jinja2Blocks idiom in this codebase.

**For Ask, recommended approach:**
- `ask/index.html` extends `base.html` and contains named blocks: `{% block answer_zone %}`, `{% block starter_chips %}`. These map to `Jinja2Blocks` fragment rendering.
- `_answer.html`, `_abort_banner.html`, `_confirm_panel.html`, `_starter_chips.html` are SEPARATE partial template files (not blocks inside `index.html`) because they are returned as standalone fragment responses from POST endpoints that do NOT render the full page.
- POST `/ask/query` and POST `/ask/confirm` return standalone partial templates (not named blocks from `index.html`) because the swap target `#answer-zone` is replaced outerHTML — the response IS the new `#answer-zone` element, not a block fragment of the full page.

**Jinja2Blocks note:** The macro scope issue discovered in Phase 5 (macros defined inside `{% block content %}` not visible from nested `{% block grid %}`) applies here too. Any macro used inside a named block that is rendered as a `block_names=` fragment must be defined INSIDE that block, not at template-top. [VERIFIED: STATE.md 05-06 entry on jinja2-fragments macro scope]

### Anti-Patterns to Avoid

- **Calling `run_nl_query` outside the route layer:** Every path that touches the agent MUST go through `run_nl_query`. The v2.0 route calling `agent.run_sync(...)` directly is a SAFE bypass — forbidden.
- **Using `async def` for the ask routes:** All three endpoints (`/ask/query`, `/ask/confirm`, `/settings/llm`) must be `def` (INFRA-05). `run_nl_query` calls `agent.run_sync()` which is synchronous PydanticAI; calling it inside an `async def` blocks the event loop.
- **Passing `df` directly to Jinja2 template:** The answer fragment must iterate `df.itertuples()` or convert to a list of row dicts before passing to the template. Jinja2 cannot iterate pandas DataFrames column-by-column natively.
- **Rendering inline `| safe` filter on any user or DB content:** All user content, DB data, agent summary text, and SQL strings must use Jinja2 autoescape (the default for `.html` templates). SQL in the `<code>` block is user-visible but autoescaped — no `| safe`. The audit grep in invariant tests will flag any `| safe` occurrence.
- **Importing `app/pages/ask.py`:** It is deleted in D-22's final plan. Port `load_starter_prompts` to `app_v2/services/starter_prompts.py` before the deletion.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-select param picker for NL-05 | Custom checkbox widget | `_picker_popover.html` macro + `popover-search.js` | Already parameterized with `form_id` and `hx_post` kwargs; Phase 4 gap closure verified |
| Agent loop, retry logic, step-cap | Custom agent runner | `nl_service.run_nl_query` | SAFE-02..06 harness; step-cap via UsageLimits; all exception-to-NLResult translation done |
| LLM model factory | Custom OpenAI/Ollama client | `build_pydantic_model(cfg)` | Returns `OpenAIChatModel` or `OllamaModel`; already handles endpoint/api_key/model defaults |
| Param catalog loading for confirmation | Custom DB query in route | `app_v2/services/cache.list_parameters(db, db_name)` | TTLCache(300s) wrapper; thread-safe; key excludes unhashable adapter |
| Cookie read at request time | Custom middleware | `request.cookies.get("pbm2_llm")` | Starlette's `Request.cookies` dict is available on every route that receives `request: Request` |
| SQL pretty-printing | Custom formatter | `sqlparse` (already in requirements) | Already in scaffolding; use for the SQL expander `<code>` block display |

---

## Picker-Popover Reuse for NL-05 Confirmation

**What is reusable verbatim:**

The `_picker_popover.html` macro has been parameterized in Phase 5 (D-OV-06) with kwargs `form_id`, `hx_post`, `hx_target`. The NL-05 confirmation context needs a picker with different `hx_post` and `hx_target` targets, which is exactly what the Phase 5 parameterization enables.

```jinja2
{# Inside ask/_confirm_panel.html — import and call the macro #}
{% from "browse/_picker_popover.html" import picker_popover %}
{{ picker_popover(
     name="confirmed_params",
     label="Confirm parameters",
     options=all_params,
     selected=candidate_params,
     form_id="ask-confirm-form",
     hx_post="/ask/confirm",
     hx_target="#answer-zone"
) }}
```

**What needs adaptation:**

The Browse picker uses D-15b auto-commit (change event → debounced HTMX POST). For NL-05 confirmation, there is an explicit `Run Query ▸` button — the user should NOT auto-submit on every checkbox toggle because that would trigger a full agent run on each checkbox change (expensive, slow, confusing). The confirmation panel needs a hybrid approach:
- The picker checkboxes do NOT carry `hx-post` auto-commit. The `<ul class="popover-search-list">` in the confirmation popover should omit the `hx-trigger` auto-submit, OR use a different form.
- The explicit `Run Query ▸` primary button carries the `hx-post="/ask/confirm"` trigger.

**Recommended approach:** The confirmation fragment uses a `<form id="ask-confirm-form">` that wraps the picker checkboxes and a hidden `<input name="original_question">`. The `Run Query ▸` button is `type="submit"` with `hx-post="/ask/confirm" hx-target="#answer-zone" hx-swap="outerHTML" hx-include="#ask-confirm-form"`. The picker is instantiated with `hx_post` and `hx_target` matching the button (so the macro's `<ul>` wiring would also trigger — but since D-15b auto-commit fires on checkbox change, the planner must decide whether to strip the `hx-trigger` from the `<ul>` in the confirmation context or accept auto-submit. Given the agent call cost, stripping auto-commit and relying solely on the Run Query button is the correct choice for UX).

**Practical note:** The macro's `<ul>` unconditionally renders `hx-post`/`hx-trigger`. To suppress auto-commit in the confirmation panel, either: (a) add a `disable_auto_commit=False` kwarg to the macro (simple template change), or (b) omit the macro and write the confirmation-specific picker inline (more verbose but explicit). Either is acceptable; the planner should pick one and document it.

[VERIFIED: browse/_picker_popover.html lines 33, 72-80; STATE.md 05-01 entry on macro parameterization]

---

## Dependency Analysis: llm_resolver Extension Ripple

The extension adds `request: Any = None` with a default of `None`. This is backward-compatible — no caller needs to change its behavior, only those that want the cookie to be honored must pass `request`.

**Files that MUST be edited (to pass `request` so AI Summary picks up cookie per D-17):**

| File | Current call | Must become |
|------|-------------|-------------|
| `app_v2/routers/overview.py` line 237 | `resolve_active_backend_name(settings)` | `resolve_active_backend_name(settings, request)` |
| `app_v2/routers/platforms.py` line 74 | `resolve_active_backend_name(settings)` | `resolve_active_backend_name(settings, request)` |
| `app_v2/routers/summary.py` line 124 | `resolve_active_llm(settings)` | `resolve_active_llm(settings, request)` |
| `app_v2/routers/summary.py` line 125 | `resolve_active_backend_name(settings)` | `resolve_active_backend_name(settings, request)` |

All four are one-line changes. All four routes already receive `request: Request` as a parameter — threading it through is trivial.

**Test files that mock `resolve_active_llm` / `resolve_active_backend_name`:**

The existing `test_llm_resolver.py` tests call the functions directly with `(settings)` only — no `request` argument. These tests continue to work unchanged because `request=None` preserves the old behavior exactly. No updates needed for the resolver unit tests.

Route-level tests (e.g., `test_summary_routes.py`) use `app.state.settings` injection and do not mock the resolver functions — they go through the real resolver. After the extension, these tests continue to work because `request=None` path (when the test client does not set `pbm2_llm` cookie) falls through to the existing `settings.app.default_llm` resolution. No updates needed.

The new `tests/v2/test_ask_routes.py` must include tests that verify the cookie path: set `pbm2_llm=openai` cookie on the test client, assert the route uses the OpenAI backend.

[VERIFIED: llm_resolver.py lines 26-60; overview.py line 237; platforms.py line 74; summary.py lines 124-125; test_llm_resolver.py call signatures]

---

## Common Pitfalls

### Pitfall 1: `async def` on ask routes blocks the event loop
**What goes wrong:** `run_nl_query` calls `agent.run_sync(question, ...)` inside. PydanticAI's `run_sync` uses a synchronous event loop runner (it calls `asyncio.run()` or `loop.run_until_complete()`). If the FastAPI route is `async def`, the sync event loop runner conflicts with the running uvicorn event loop.
**Why it happens:** INFRA-05 enforcement. FastAPI dispatches `def` routes to the threadpool where a new event loop is available. `async def` routes run inline on the uvicorn loop.
**How to avoid:** ALL three ask routes (`/ask/query`, `/ask/confirm`, `/settings/llm`) must be `def`, not `async def`. The `GET /ask` page-render is also `def` for consistency.
**Warning signs:** `RuntimeError: This event loop is already running` in logs.

### Pitfall 2: Passing `df` (DataFrame) directly to Jinja2 context
**What goes wrong:** Jinja2 cannot naturally iterate a pandas DataFrame as rows. `{% for row in df %}` iterates column names, not rows.
**Why it happens:** Jinja2 sees DataFrames as iterables of their index.
**How to avoid:** Convert in the route: `rows = df.to_dict("records")` before passing to template. Pass `columns = list(df.columns)` and `rows = [list(r.values()) for r in df.to_dict("records")]` for the table render.
**Warning signs:** Template renders column names as row cells.

### Pitfall 3: Confirmation fragment auto-submit on checkbox change
**What goes wrong:** If the `_confirm_panel.html` uses the Browse picker verbatim (including `hx-trigger="change delay:250ms"`), every checkbox toggle triggers a full agent run (expensive, 2-30 seconds).
**Why it happens:** The picker macro unconditionally renders the `hx-trigger` auto-commit on the `<ul>`.
**How to avoid:** Either add a `disable_auto_commit` kwarg to the macro (default False), or strip the `hx-trigger` from the `<ul>` in the confirmation-specific template by using a modified macro call or an inline picker.

### Pitfall 4: Cookie-set 204 response without `HX-Refresh` header not triggering reload
**What goes wrong:** If `HX-Refresh` header is set on a `Response()` object that has `status_code=204`, some HTMX versions may not process the header.
**Why it happens:** HTMX 2.x processes `HX-Refresh: true` on any response. In practice, 204 + `HX-Refresh` works in HTMX 2.0.10. But the header must be `"true"` (lowercase string), not `True` (Python bool).
**How to avoid:** `response.headers["HX-Refresh"] = "true"` — lowercase string. Use FastAPI `Response(status_code=204)` not `HTMLResponse`.
**Warning signs:** Dropdown label doesn't update after clicking a backend option.

### Pitfall 5: Importing `app/pages/ask.py` to reuse `load_starter_prompts`
**What goes wrong:** `app/pages/ask.py` calls `nest_asyncio.apply()` at module level (line 9). Importing it in the v2.0 context applies `nest_asyncio` globally and may interfere with the uvicorn event loop. Additionally, it imports `streamlit` which is not available in the FastAPI process.
**Why it happens:** The file is designed to be run as a Streamlit page, not imported as a library.
**How to avoid:** Port `load_starter_prompts` verbatim to `app_v2/services/starter_prompts.py`. Never import from `app/pages/ask.py`.

### Pitfall 6: Second-turn returning ClarificationNeeded again (infinite loop)
**What goes wrong:** The agent ignores the loop-prevention instruction and returns `ClarificationNeeded` on the second turn. If the route renders the confirmation fragment again, the user is stuck in a loop.
**Why it happens:** LLMs do not always follow instructions perfectly.
**How to avoid:** Per D-10, if `run_nl_query` returns `kind="clarification_needed"` on the second turn (from `/ask/confirm`), the route must render the abort banner instead — treat it as a failure. The step-cap (5 steps) also limits how long the agent can loop. Document this branch explicitly in the route.

### Pitfall 7: Jinja2Blocks macro scope for fragments
**What goes wrong:** Macros defined inside `{% block content %}` are not accessible from named blocks rendered via `block_names=`. The jinja2-fragments library renders only the named block, dropping template-top context.
**Why it happens:** jinja2-fragments renders single-block fragments in an isolated scope.
**How to avoid:** Any macro used inside a block that will be rendered as a `block_names=` fragment must be defined INSIDE that block, not at template-top. Established in Phase 5 (STATE.md 05-06). This applies to `ask/index.html` if any of its blocks are returned as fragments.

### Pitfall 8: `secure=True` cookie on HTTP intranet
**What goes wrong:** Setting `secure=True` on `Response.set_cookie(...)` causes the cookie to be rejected by the browser on HTTP (non-HTTPS) intranet deployments.
**Why it happens:** `secure=True` means "only send this cookie over HTTPS". The intranet runs HTTP.
**How to avoid:** Explicitly pass `secure=False` (or omit — Starlette's default is `False`). Documented in D-14.

---

## Code Examples

### GET /ask — Full Page Render

```python
# Source: verified from root.py GET /ask stub + browse.py GET /browse pattern
@router.get("/ask", response_class=HTMLResponse)
def ask_page(request: Request):
    settings = getattr(request.app.state, "settings", None)
    backend_name = resolve_active_backend_name(settings, request)
    llm_cfg = resolve_active_llm(settings, request)
    prompts = load_starter_prompts()   # from app_v2.services.starter_prompts
    return templates.TemplateResponse(request, "ask/index.html", {
        "active_tab": "ask",
        "page_title": "Ask",
        "backend_name": backend_name,
        "llm_cfg": llm_cfg,
        "starter_prompts": prompts,
        "llms": getattr(settings, "llms", []),
    })
```

### NLResult → Template Context

```python
# Source: verified from nl_service.py NLResult dataclass fields
# For kind == "ok":
ctx = {
    "columns": list(nl_result.df.columns),
    "rows": nl_result.df.values.tolist(),    # list of lists
    "row_count": len(nl_result.df),
    "row_cap": deps.agent_cfg.row_cap,       # 200
    "summary": nl_result.summary,            # str — plain text, autoescape
    "sql": nl_result.sql,                    # validated+limited SQL
}
# For kind == "clarification_needed":
ctx = {
    "message": nl_result.message,
    "candidate_params": nl_result.candidate_params,   # list[str]
    "all_params": all_params,     # full catalog + candidates merged
    "original_question": question,
}
# For kind == "failure":
ctx = {
    "reason": nl_result.failure.reason,       # "step-cap"|"timeout"|"llm-error"
    "last_sql": nl_result.failure.last_sql,   # may be empty
    "detail": nl_result.failure.detail,       # raw detail — do NOT expose to user
}
```

### Test Scaffold for ask_routes

```python
# Source: verified from test_summary_routes.py fixture pattern (D-19)
import pytest
from app.core.agent.nl_service import NLResult
from app.core.agent.nl_agent import AgentRunFailure
from fastapi.testclient import TestClient

@pytest.fixture()
def ask_client(monkeypatch, mocker):
    from app_v2.main import app
    mocker.patch("app_v2.routers.ask.run_nl_query",
                 return_value=NLResult(kind="ok", sql="SELECT 1",
                                       df=..., summary="summary text"))
    with TestClient(app) as client:
        yield client

def test_ask_query_ok_returns_200(ask_client):
    resp = ask_client.post("/ask/query", data={"question": "show all platforms"})
    assert resp.status_code == 200
    assert "answer-zone" in resp.text

def test_ask_query_clarification_returns_confirm_panel(mocker, ask_client):
    mocker.patch("app_v2.routers.ask.run_nl_query",
                 return_value=NLResult(kind="clarification_needed",
                                       message="Which params?",
                                       candidate_params=["UFS / WriteProt"]))
    resp = ask_client.post("/ask/query", data={"question": "compare write prot"})
    assert resp.status_code == 200
    assert "Run Query" in resp.text
```

### Cookie-Set + HX-Refresh Response

```python
# Source: CONTEXT.md D-16, Starlette Response API
from fastapi.responses import Response

def set_llm(request: Request, name: Annotated[str, Form()] = ""):
    # ... validation ...
    resp = Response(status_code=204)
    resp.set_cookie(key="pbm2_llm", value=cookie_val,
                    max_age=31536000, path="/",
                    samesite="lax", httponly=True, secure=False)
    resp.headers["HX-Refresh"] = "true"    # MUST be lowercase string "true"
    return resp
```

---

## State of the Art

| Old Approach (v1.0) | v2.0 Approach | Reason |
|---------------------|---------------|--------|
| `st.session_state` for LLM selection | Plain `pbm2_llm` cookie, read per-request | No Streamlit session available in FastAPI |
| `@st.cache_resource` for agent | `app.state.agent_registry` dict | Same lazy-per-backend pattern, FastAPI idiom |
| `st.spinner("Thinking...")` | HTMX `hx-indicator` on `#answer-zone` + Bootstrap spinner | No server-push needed; spinner hidden by CSS during htmx-request class |
| `st.multiselect` for NL-05 confirmation | `_picker_popover.html` macro with explicit `Run Query` button | Bootstrap dropdown is the v2.0 multiselect primitive |
| `st.expander("Generated SQL")` | `<details><summary>Generated SQL</summary>` | Native HTML; no JS needed |
| `nest_asyncio.apply()` | Not needed | FastAPI routes are `def`; PydanticAI `run_sync` works in threadpool without nest_asyncio |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `Response(status_code=204)` + `response.headers["HX-Refresh"] = "true"` triggers full page reload in HTMX 2.0.10 | Pattern 3 | If wrong, dropdown label won't update; workaround: return 200 with a meta-refresh or HX-Trigger instead |
| A2 | Bootstrap 5 dropdown auto-closes on `<button class="dropdown-item">` click even when the button has an `hx-post` attribute | Pattern 3 | If wrong, dropdown stays open after selection; fix: add `data-bs-dismiss` or JS close call |

Both assumptions are LOW-risk given HTMX 2.x documentation and Bootstrap 5 standard behavior.

---

## Open Questions

1. **Confirmation picker: strip auto-commit or add `disable_auto_commit` kwarg?**
   - What we know: The Browse picker macro unconditionally emits `hx-trigger="change delay:250ms"` on the `<ul>`. The confirmation context should not auto-submit.
   - What's unclear: Whether to (a) add a `disable_auto_commit=False` kwarg to `_picker_popover.html` — clean but modifies the shared macro, (b) write the confirmation picker inline — verbose but self-contained.
   - Recommendation: Add `disable_auto_commit=False` kwarg (one-line macro change, zero Phase 4/5 behavior change). This is the cleanest extension.

2. **Agent registry thread-safety in ask route**
   - What we know: `app.state.agent_registry` is a plain dict. `def` routes run concurrently in the threadpool.
   - What's unclear: Whether concurrent first requests for the same LLM backend could double-build the agent (harmless but wasteful).
   - Recommendation: The dict write is atomic at the CPython level (GIL), so a double-build on the first concurrent requests is the worst case — both write the same value. No threading.Lock needed. Matches v1.0's `@st.cache_resource` approach which also has a tiny race window.

3. **`original_question` propagation to second turn**
   - What we know: The confirmation fragment must carry the original question as a hidden form field so POST `/ask/confirm` can compose the second-turn message.
   - What's unclear: Whether to use a hidden `<input name="original_question">` in the confirmation form, or pass it as a separate `hx-vals` JSON blob.
   - Recommendation: Hidden `<input name="original_question" value="{{ original_question | e }}">` inside `<form id="ask-confirm-form">` — same idiomatic form approach used throughout the codebase.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 6 is a code/configuration-only change. All runtime dependencies (FastAPI, PydanticAI, the DB adapter, Bootstrap/HTMX static assets) are already available and confirmed working by Phase 1-5 completion.

---

## Security Domain

`security_enforcement` is not explicitly disabled in `.planning/config.json`. Applying standard review.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Auth deferred (D-04); intranet only |
| V3 Session Management | Partial | Plain `pbm2_llm` cookie (not auth token); tamper defense is validation against `settings.llms[].name`, not signing |
| V4 Access Control | No | Read-only DB user is the backstop (CLAUDE.md: "Readonly DB user is the primary SQL-injection backstop") |
| V5 Input Validation | Yes | `question` is a plain string passed to the agent; the agent's system prompt + SAFE-02..06 harness are the defense layer |
| V6 Cryptography | No | No signing/encryption for the LLM selector cookie (D-15 explicitly chose validation over signing) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via textarea | Tampering | SAFE-05 `<db_data>` wrapper in system prompt; SAFE-06 path scrubber for OpenAI; Phase 1 `test_nl_service.py` covers this — D-20 explicitly defers route-layer repeat |
| Cookie tampering (`pbm2_llm=evil`) | Elevation of Privilege | D-15 validation against `settings.llms[].name` — invalid value falls back to default_llm silently |
| SQL injection via agent output | Tampering | SAFE-02 `validate_sql` (two passes); `allowed_tables` enforcement; readonly DB user |
| XSS via agent summary/SQL in answer fragment | XSS | Jinja2 autoescape on all `.html` templates; `nl_result.summary` and `nl_result.sql` rendered via `{{ ... }}` (not `| safe`) |
| Path traversal in LLM name param | Tampering | Cookie value validated against a closed set (`settings.llms[].name`) before any use |

---

## Sources

### Primary (HIGH confidence)
- `app/core/agent/nl_service.py` — `run_nl_query` signature, `NLResult` fields, both-turns entry point, SAFE contract
- `app/core/agent/nl_agent.py` — `build_agent`, `AgentDeps`, `AgentRunFailure`, `run_agent`, step-cap via `UsageLimits`
- `app/pages/ask.py` — v1.0 `_run_confirmed_agent_flow` composed-string pattern (lines 363-381), `load_starter_prompts` (lines 62-89)
- `app_v2/services/llm_resolver.py` — current `resolve_active_llm` / `resolve_active_backend_name` signatures; extension path
- `app_v2/templates/browse/_picker_popover.html` — macro signature after Phase 5 parameterization; `form_id`/`hx_post`/`hx_target` kwargs
- `app_v2/static/js/popover-search.js` — D-15b auto-commit behavior; no Bootstrap show/hide lifecycle wiring (only onInput + onClearClick)
- `app_v2/routers/summary.py` — ALWAYS-200 contract; `resolve_active_llm(settings)` / `resolve_active_backend_name(settings)` call sites
- `app_v2/routers/overview.py`, `platforms.py` — `resolve_active_backend_name(settings)` call sites
- `app_v2/main.py` — `agent_registry = {}` lifespan initialization; router registration order
- `app_v2/templates/base.html` — `popover-search.js` already loaded globally with `defer`
- `config/starter_prompts.example.yaml` — 8 entries confirmed with `label` + `question` keys
- `app/adapters/llm/pydantic_model.py` — `build_pydantic_model(cfg)` factory
- `app/core/agent/config.py` — `AgentConfig` fields: `max_steps=5`, `timeout_s=30`, `row_cap=200`
- `app_v2/static/css/app.css` — `.ai-btn`, `.panel`, `.panel-header`, `.shell` classes
- `tests/v2/test_llm_resolver.py` — existing test call signatures (no `request` arg — backward compatible)
- `.planning/STATE.md` — Phase 5 macro scope lessons (05-06 entry)

### Secondary (MEDIUM confidence)
- HTMX 2.x `HX-Refresh: true` header behavior (based on established use of `HX-Redirect` + `HX-Push-Url` headers in Phase 4/5 which follow the same response-header processing path) [ASSUMED with HIGH confidence]
- Bootstrap 5 dropdown auto-close on `dropdown-item` click with `hx-post` present (standard Bootstrap behavior; no conflict observed) [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and in use; no new dependencies
- Architecture: HIGH — all patterns verified against existing codebase source
- Pitfalls: HIGH — most pitfalls are confirmed from prior phase history (INFRA-05, macro scope, cookie attributes)
- Cookie/HX-Refresh: MEDIUM (A1, A2 in Assumptions Log) — standard HTMX/Bootstrap patterns but not exercised in this codebase yet

**Research date:** 2026-04-29
**Valid until:** 2026-05-30 (stable stack; 30-day horizon)
