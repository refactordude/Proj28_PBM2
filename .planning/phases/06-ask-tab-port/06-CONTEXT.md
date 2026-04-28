# Phase 6: Ask Tab Port - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning
**Mode:** Smart discuss (visual-anchored to Dashboard_v2.html, 4 grey areas resolved, 3 spec deviations recorded)

<domain>
## Phase Boundary

Port the v1.0 Streamlit Ask page (single Q→A NL agent with optional NL-05 two-turn confirmation) onto the FastAPI v2.0 / Bootstrap / HTMX shell. The PydanticAI agent and the SAFE-02..06 safety harness already live framework-agnostic in `app/core/agent/nl_service.run_nl_query` (Phase 1 INFRA-07) — Phase 6 adds the UX shell, HTMX wiring, route layer, and an Ask-page-scoped LLM backend selector.

Delivers:
- `GET /ask` — Ask page with textarea + Run + 4×2 starter-chip grid (when no question asked yet)
- `POST /ask/query` — first-turn endpoint; returns either an answer fragment OR an NL-05 confirmation fragment into `#answer-zone`
- `POST /ask/confirm` — second-turn endpoint; receives user-confirmed params, runs the agent again, returns answer fragment into `#answer-zone`
- `POST /settings/llm` — Ask-page LLM selector switch endpoint; sets `pbm2_llm` cookie, responds 204 + `HX-Refresh: true`
- `app_v2/routers/ask.py` and `app_v2/routers/settings.py` (new)
- `app_v2/templates/ask/{index.html, _starter_chips.html, _confirm_panel.html, _answer.html, _abort_banner.html}`
- `app_v2/services/llm_resolver.py` extension — read `pbm2_llm` cookie, validate against `settings.llms[].name`, fall back to `settings.app.default_llm`
- v1.0 cleanup as the **final plan** of this phase: hard-delete `app/pages/ask.py` + `tests/pages/test_ask_page.py` + remove the Ask page entry from `streamlit_app.py` nav. `nl_service` and `nl_agent` stay (now v2.0-only consumers)

Scope out:
- **History panel (ASK-V2-04 dropped — moved to Out of Scope)**. No `<details>` history above textarea, no LRU cookie/app.state, no history widget at all. v2.0 Ask is a strict single-shot tool: Q in, A out.
- **Regenerate button (ASK-V2-03 partial deviation)**. Editing the textarea and clicking Ask again is the regeneration mechanism. The result table, plain-text LLM summary, and collapsed SQL expander all remain per ASK-V2-03.
- **Global navbar placement of LLM selector + OpenAI sensitivity-warning banner (ASK-V2-05 partial deviation)**. The selector lives only on the Ask page (header bar). No standalone OpenAI warning banner anywhere.
- Threat-model regression tests for Phase 6 — inherit Phase 1's `nl_service` coverage; do not re-test prompt-injection / non-allowed-table / path-scrub at the route layer.
- Persistent NL history across sessions (ASK-V2-F01, already future).
- Authentication (D-04 deferral continues).

</domain>

<decisions>
## Implementation Decisions

### Page structure
- **D-01:** Single-column layout (Dashboard's 2-col `.ai-side` threads + `.ai-main` chat doesn't fit our single-shot Q→A model). Layout top-to-bottom: page header bar (title + LLM selector) → textarea + ✕ clear + Run button → starter-chip grid (when no Q yet) → `#answer-zone`. Width `max-width: 1280px` per Dashboard `.shell` token.
- **D-02:** Starter prompts render as a Bootstrap 4×2 grid styled with `.ai-chip` (Dashboard rounded-pill class — light grey bg `#f4f6f8`, accent on hover). Loaded from `config/starter_prompts.yaml` with fallback to `config/starter_prompts.example.yaml` (port the v1.0 `load_starter_prompts` idiom verbatim into a service module).
- **D-03:** Starter chips appear **below** the textarea (between Run button and `#answer-zone`). Visible only when `#answer-zone` is empty AND no question has been submitted yet. Once any answer renders, chips are gone — and they do **not** come back (single-session-life behavior matches v1.0 D-27 semantics).
- **D-04:** No question echo in the answer panel. The answer fragment shows table + summary + SQL expander only — the user's question stays in the textarea above. (Drops Dashboard's `.msg user` chat-bubble convention; not a fit for single-shot.)
- **D-05:** **No history panel.** ASK-V2-04 is moved to Out of Scope (or merged into ASK-V2-F01 "Persistent NL history across sessions"). Phase 6 ships zero history surface area: no widget, no cookie, no app.state list, no LRU.
- **D-06:** Textarea persists its last value across queries until the user manually clears it. A small Bootstrap-styled ✕ button sits adjacent (right-aligned over the textarea or in its toolbar) and clears the textarea on click. Browser refresh clears it (no cookie persistence for textarea).

### NL-05 two-turn confirmation
- **D-07:** When `nl_service.run_nl_query` returns `NLResult.kind="clarification_needed"`, the route renders a confirmation panel that **reuses the Browse picker-popover pattern** (Phase 4 D-15b auto-commit, search filter, Apply close, Clear restore). The popover is wrapped in a `.panel` card that shows the agent's `message` text above the picker button (label: `"Confirm parameters (N selected) ▾"`) and a primary `Run Query ▸` button below it.
- **D-08:** HTMX swap target is `#answer-zone` for **both** the first-turn response (which can be either an answer fragment or the confirmation fragment) and the second-turn response (always an answer fragment). Single DOM region for all NL state — symmetric and easy to reason about. `outerHTML` swap is fine; the confirmation fragment carries `id="answer-zone"` on its outer wrapper.
- **D-09:** After `Run Query` (second turn) succeeds, the confirmation panel is fully replaced by the answer fragment (the swap collapses it). If the user wants to re-tweak params, they must re-Ask — there is no inline "edit confirmation" affordance.
- **D-10:** `Run Query` is **always enabled** even when 0 params are selected (deviation from v1.0 `_run_confirmed_agent_flow` which silently no-ops). Server forwards the empty list to the agent in the second-turn structured message. **Loop-prevention mitigation:** the second-turn user message includes the explicit instruction `"Use ONLY the confirmed parameters above. If the list is empty, use your best judgment from the original question and do not return ClarificationNeeded again."` Backed by Phase 1's step-cap (5) and timeout (30s) as the ultimate floor — even if the agent ignores the instruction, the harness aborts.
- **D-11:** **No Regenerate button.** The user explicitly chose "edit textarea + Ask again" as the regeneration mechanism (ASK-V2-03 partial deviation). The result table, plain-text LLM summary, and collapsed SQL expander (`<details>` with the validated/limited SQL inside a `<code>` block) all stay per spec. Drop `cache_bypass`/`X-Regenerate` plumbing entirely for Phase 6.

### LLM backend selector + cookie (ASK-V2-05, partial)
- **D-12:** Selector placement: a small page-header strip at the top of `/ask` only (NOT the global `base.html` navbar). ASK-V2-05's "global sidebar (top-right of the Bootstrap nav)" is partially deviated — selector is Ask-scoped while still being a single source of truth.
- **D-13:** Selector is a Bootstrap dropdown button labeled `"LLM: Ollama ▾"` / `"LLM: OpenAI ▾"` (the active backend's display name baked into the label). Click reveals a dropdown menu with two `<button class="dropdown-item">` entries (Ollama / OpenAI). No OpenAI warning banner anywhere on the page (full deviation from the banner half of ASK-V2-05).
- **D-14:** Persistence: a plain (unsigned) cookie `pbm2_llm` with attributes `Path=/; SameSite=Lax; Max-Age=31536000`. `HttpOnly` is fine (no JS reads it). `Secure` is omitted (intranet HTTP). Default value when cookie absent: `settings.app.default_llm`.
- **D-15:** Cookie validation on read (mandatory): the value MUST equal one of `settings.llms[].name` — anything else falls back silently to `settings.app.default_llm`. This is the entire defense against tampering: even if a user crafts `pbm2_llm=evil`, the resolver returns the configured default. No signing needed.
- **D-16:** Switch flow: clicking a dropdown item triggers `hx-post="/settings/llm"` with form body `{"name": "openai"}`. The server validates the value, sets the cookie via `Response.set_cookie(...)`, and returns HTTP 204 with header `HX-Refresh: true`. HTMX then performs a full client-side page refresh — refreshing the dropdown label, any LLM-driven content (Ask answer / AI Summary cache state), and clearing in-flight Ask state cleanly.
- **D-17:** Cookie overrides globally — `llm_resolver.resolve_active_llm(settings, request)` is extended to take a `request` argument, check the cookie first (validate against `settings.llms[].name`), then fall back to `settings.app.default_llm`. **AI Summary on Overview also uses the cookie**: when the user picks OpenAI on Ask, the next AI Summary click on Overview also routes through OpenAI. Single source of truth for active backend.
- **D-18:** **No OpenAI sensitivity-warning banner.** ASK-V2-05's banner half is dropped (user explicit). Phase 6 ships no `.alert.alert-warning` for OpenAI usage anywhere. Users are expected to know what backend they picked from the selector label.

### Tests, mocking, regression bar
- **D-19:** Mocking strategy — `pytest-mock` patches `app_v2.routers.ask.run_nl_query` (or wherever `nl_service.run_nl_query` is imported into the route module) at module level. Tests construct canned `NLResult` variants (`ok` / `clarification_needed` / `failure(reason="step-cap"|"timeout"|"llm-error")`) and assert: route status code, swap target, fragment template name, fragment context values. Same idiom as Phase 3 `test_summary_routes.py`. Tests do NOT instantiate the PydanticAI agent or hit a DB.
- **D-20:** **No explicit threat-model tests** for Phase 6 (user explicit). Phase 1's `tests/agent/test_nl_service.py` already covers SAFE-02..06 (validate_sql, LIMIT injection, READ ONLY session, prompt-injection wrap, path-scrub). Phase 6 inherits that coverage; the route layer is a thin shell over `run_nl_query` and re-testing the harness from `/ask/query` would be redundant.
- **D-21:** Regression bar: `pytest tests/` exits 0 with all v1.0 tests still green (after `tests/pages/test_ask_page.py` is deleted in the final plan — STATE.md regression bar count drops by exactly that file's test count) + all Phase 1-5 v2.0 tests still green + new Phase 6 tests passing. Plan-level success criteria mirror this.
- **D-22:** **v1.0 Ask removal as the final plan of Phase 6.** Hard-delete: `app/pages/ask.py`, `tests/pages/test_ask_page.py`, the `st.Page("Ask", ...)` entry in `streamlit_app.py`. Any v1.0 Ask-only docs (e.g. `app/pages/__init__.py` re-exports) get cleaned up too. `app/core/agent/nl_service.py` and `nl_agent.py` STAY (they are v2.0-only consumers from this point). `config/starter_prompts.example.yaml` STAYS (used by v2.0).

### Claude's Discretion
- Exact dropdown markup pattern (Bootstrap `.dropdown` vs HTMX-driven button — pick whichever yields cleanest 204 + HX-Refresh flow)
- Exact textarea + ✕ clear button styling (standalone button vs input-group append)
- Whether the confirmation-panel `.panel` uses a violet accent (consistent with `.ai-btn` AI-color convention) or stays neutral
- Test file layout: single `tests/v2/test_ask_routes.py` vs split per ASK-V2-NN — pick whichever keeps a single test file under ~400 lines
- Whether to factor a `app_v2/services/ask_service.py` or keep route logic inline (route layer is thin since `nl_service` does the heavy lifting — inline is probably fine)
- Whether to vendor a small `clear-textarea.js` helper for the ✕ button or inline an `onclick` attribute (Phase 1 Pitfall says no module-level JS for trivial cases — inline `onclick="document.getElementById('ask-q').value=''"` is acceptable)
- Concrete copy for the textarea placeholder, the confirmation panel header, and the abort banner (defer to v1.0 02-UI-SPEC.md copywriting contract — port verbatim where applicable)

### Spec deviations — REQUIREMENTS.md must be updated during planning
| Requirement | Original spec | Phase 6 actual | Action |
|---|---|---|---|
| **ASK-V2-03** | Includes "Regenerate button above the summary re-invokes the agent..." | Regenerate button dropped; table+summary+SQL expander remain | Update ASK-V2-03 to remove Regenerate clause |
| **ASK-V2-04** | Session history panel, max 50, LRU, signed cookie or app.state | Fully out of scope — no history at all | Move ASK-V2-04 to Out of Scope (or merge into ASK-V2-F01) |
| **ASK-V2-05** | "global sidebar (top-right of the Bootstrap nav)" + dismissible OpenAI alert banner | Selector on Ask page header bar only; no OpenAI banner | Update ASK-V2-05 to remove the global-placement and banner clauses |

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (researcher, planner) MUST read these before planning or implementing.**

### v1.0 NL implementation being ported
- `app/pages/ask.py` — the v1.0 Streamlit Ask page (deleted in Phase 6's final plan, but it IS the source of truth for the port until then)
- `app/core/agent/nl_service.py` — framework-agnostic SAFE-02..06 orchestration, `run_nl_query` entry point, `NLResult` shape (Phase 1 INFRA-07)
- `app/core/agent/nl_agent.py` — `build_agent`, `SQLResult`, `ClarificationNeeded`, `AgentDeps`, `AgentRunFailure`, `run_agent`, the `run_sql` tool with `allowed_tables` enforcement
- `app/adapters/llm/pydantic_model.py` — `build_pydantic_model(cfg)` factory for OpenAI/Ollama
- `tests/pages/test_ask_page.py` — v1.0 Streamlit Ask tests (deleted in Phase 6's final plan)

### v1.0 NL design contract (port verbatim where applicable)
- `.planning/milestones/v1.0-phases/02-nl-agent-layer/02-CONTEXT.md` — D-17..D-27 (NL Page Layout, Param Confirmation, Safety, Sensitivity Warning, Starter Prompts) — note D-25 (OpenAI banner) and D-19 (history) are EXPLICITLY OVERRIDDEN by Phase 6 D-18 and D-05 respectively
- `.planning/milestones/v1.0-phases/02-nl-agent-layer/02-UI-SPEC.md` — Ask Page Contract (banner zone, full page layout, copywriting), Starter Prompt Gallery (§ Starter Prompt Gallery), Copywriting Contract (placeholder, button labels) — port the copy strings verbatim
- `.planning/milestones/v1.0-phases/02-nl-agent-layer/02-RESEARCH.md` — agent design rationale (only-one-tool, no schema inspector, two-turn flow justification)

### v2.0 phase context being built on
- `.planning/phases/01-pre-work-foundation/01-CONTEXT.md` — FastAPI/HTMX patterns, `TemplateResponse(request, name, ctx)` Starlette 1.0 signature, sync-def routes for DB calls, INFRA-06 + INFRA-07 contracts (the `nl_service` extraction this phase relies on)
- `.planning/phases/03-content-pages-ai-summary/03-CONTEXT.md` — Dashboard token pinning (`tokens.css`, `--violet`, `.ai-btn`, `.panel`), `llm_resolver` extraction (D-19), pytest-mock at module level (D-23), TTLCache + threading.Lock (carryover from Phase 2)
- `.planning/phases/04-browse-tab-port/04-CONTEXT.md` — picker-popover D-15b auto-commit pattern + `popover-search.js` (REUSED for NL-05 confirmation widget in this phase)
- `.planning/phases/03-content-pages-ai-summary/03-UI-SPEC.md` — `.ai-btn` styling reference, `.panel` empty-state pattern, `<details>` collapsed-section pattern

### Project-level
- `.planning/REQUIREMENTS.md` — ASK-V2-01..08 (with Phase 6 deviations to be applied during planning per the spec-deviations table above)
- `.planning/PROJECT.md` — Ask carry-over scope (lines 112-115), parallel-operation contract (overridden for the v1.0 Ask page only by D-22)
- `.planning/ROADMAP.md` — Phase 6 success criteria (the 5 enumerated criteria) — note SC#3 (OpenAI banner persistence/clearing) is OBSOLETE under D-18 and must be revised during planning to drop the banner-related sub-claims

### Visual reference
- `/home/yh/Desktop/02_Projects/Proj27_PBM1_fork_bootstrap/Dashboard_v2.html` — Ask AI tab design language. Specifically:
  - Lines 306-342 (CSS): `.ai-wrap`, `.ai-side`, `.ai-thread`, `.ai-main`, `.ai-msgs`, `.msg`, `.msg-citation`, `.ai-card-grid`, `.ai-src`, `.ai-actions`, `.ai-suggest`, `.ai-chip`, `.ai-input` — pinned visual tokens (we use `.ai-chip` + `.ai-input` selectively per D-02 and D-06; we do NOT adopt `.ai-side` / `.ai-main` 2-col structure per D-01)
  - Lines 1266-1395 (React): `TabAskAI` component — visual reference only; the multi-turn chat structure is NOT what we build

### Static assets (already shipped)
- `app_v2/static/js/popover-search.js` — picker-popover behavior (REUSED for D-07)
- `app_v2/static/css/tokens.css` — Dashboard CSS vars (`--violet`, `--accent-soft`, etc.)
- `app_v2/static/css/app.css` — `.ai-btn`, `.panel`, picker-popover styling (extend with `.ai-chip` if not yet present)
- `config/starter_prompts.example.yaml` — 8 starter prompts (committed; loaded by both v1.0 and v2.0 with the same fallback chain)

### Service layer (already shipped, may need extension)
- `app_v2/services/llm_resolver.py` — `resolve_active_llm(settings)` and `resolve_active_backend_name(settings)`. **Phase 6 extends signatures to take `request: Request | None` and read the `pbm2_llm` cookie before falling back to `settings.app.default_llm`.** All Phase 3 callers (overview, platforms, summary routes) must be updated to pass `request` so AI Summary picks up the cookie too.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets (import as-is)
- `app/core/agent/nl_service.run_nl_query(question, agent, deps, *, regenerate=False) -> NLResult`: the SINGLE entry point. Phase 6 routes import and call this; never bypass it.
- `app/core/agent/nl_agent.{build_agent, AgentDeps, AgentRunFailure, ClarificationNeeded, SQLResult, run_agent}`: agent factory + result types + step-cap-enforced `run_agent` wrapper.
- `app/adapters/llm/pydantic_model.build_pydantic_model(LLMConfig) -> Model`: returns `OpenAIChatModel` or `OllamaModel` based on `cfg.type`.
- `app/core/config.{Settings, LLMConfig, find_llm, load_settings}`: settings loader + lookup helpers — same pattern as Phase 3.
- `app_v2/services/llm_resolver.resolve_active_llm(settings, request=None)`: extend signature to read cookie first.
- `app_v2/static/js/popover-search.js` + `.picker-popover` class: NL-05 confirmation widget reuses this verbatim.
- v1.0 `app/pages/ask.py::load_starter_prompts()`: port the YAML fallback chain logic to a new `app_v2/services/starter_prompts.py` (or inline helper) — DO NOT import from `app/pages/ask.py` because that file is being deleted in this same phase.

### Established patterns (apply)
- Sync-def routes for DB calls (Phase 1; FastAPI threadpool dispatches `def` routes — `async def` would block the loop with sync SQLAlchemy)
- `templates.TemplateResponse(request, "ask/index.html", ctx)` — Starlette 1.0 first-arg-is-request signature
- `jinja2_fragments.fastapi.Jinja2Blocks` — same template file serves full page + named fragments via `block_name=`
- `pytest-mock` patches at module level (e.g., `mocker.patch("app_v2.routers.ask.run_nl_query")`)
- HTMX `hx-post` + `hx-target="#answer-zone"` + `hx-swap="outerHTML"`; the response fragment carries `id="answer-zone"` on its outer wrapper to keep the swap idempotent
- `htmx-error-handler.js` (Phase 1 INFRA-02) globally catches 4xx/5xx — Phase 6 routes can return 422 / 500 and the user-facing alert renders into `#htmx-error-container` automatically. The Ask abort banner (step-cap / timeout / llm-error) is rendered inside `#answer-zone`, not via `#htmx-error-container` (it's a normal 200 response with the failure fragment).

### Integration points (where Phase 6 connects)
- New routers: `app_v2/routers/ask.py`, `app_v2/routers/settings.py` — registered in `app_v2/main.py` lifespan/router-mount block
- New templates: `app_v2/templates/ask/{index.html, _starter_chips.html, _confirm_panel.html, _answer.html, _abort_banner.html}` (use `Jinja2Blocks` if any of these double as partial-target blocks within `index.html`)
- `app_v2/services/llm_resolver.py` — extend signature; update Phase 3 call sites (`app_v2/routers/{overview,platforms,summary}.py`) to thread `request` through. Watch for test breakage in `tests/v2/test_*_routes.py`.
- `streamlit_app.py` — drop the Ask page entry as part of D-22 (the final plan)
- `tests/pages/test_ask_page.py` — delete as part of D-22; STATE.md regression-bar test count drops accordingly
- `requirements.txt` — no new dependencies needed (Bootstrap dropdown ships with `bootstrap.bundle.min.js`; no `itsdangerous` because plain unsigned cookie per D-14)

### Deletion contract (D-22)
The final Phase 6 plan must:
1. Delete `app/pages/ask.py`
2. Delete `tests/pages/test_ask_page.py`
3. Edit `streamlit_app.py` to remove the Ask page entry from the `st.Page(...)` list
4. Run `pytest tests/` — record the new green-test count and update the regression bar in STATE.md
5. Verify `app/core/agent/nl_service.py` and `nl_agent.py` and `app/adapters/llm/pydantic_model.py` are still imported (by v2.0) — these MUST NOT be deleted

</code_context>

<specifics>
## Specific Ideas

- "no need for history" (user, on the history panel): drives D-05 (full ASK-V2-04 drop)
- "no need for regeneration, but editing previous message is enough" (user): drives D-11 (Regenerate button drop, ASK-V2-03 partial deviation)
- "skip threat model test" (user): drives D-20 (no Phase 6 threat-model regression tests; rely on Phase 1 coverage)
- "no need" on the OpenAI sensitivity banner (user): drives D-18 (no banner anywhere)
- v1.0 mental model preserved verbatim everywhere it can be: layout (D-01), starter chips (D-02), copy (port from 02-UI-SPEC.md)
- Dashboard `.ai-chip` is the ONE Dashboard chat-tab class we use; everything else (`.ai-side`, `.ai-main`, `.msg ai/user`, `.ai-card-grid`) is rejected for fit
- Cookie validation against `settings.llms[].name` is the cookie-tampering defense; no signing needed (intranet, low-stakes, only-2-pre-configured-backends)
- Cookie effect is GLOBAL across the app (Ask + AI Summary), even though the selector lives only on Ask — single source of truth (D-17)
- v1.0 Ask deletion happens INSIDE Phase 6 as the last plan, not in a separate cleanup phase (D-22)

</specifics>

<deferred>
## Deferred Ideas

### Spec changes to apply during planning (REQUIREMENTS.md updates)
- ASK-V2-03 → drop the Regenerate clause; keep table/summary/SQL expander
- ASK-V2-04 → move to Out of Scope (or merge into ASK-V2-F01 "Persistent NL history across sessions")
- ASK-V2-05 → drop the global-sidebar placement and the OpenAI dismissible-alert banner; selector becomes Ask-page-only

### Existing future requirements (no change)
- ASK-V2-F01 "Persistent NL history across sessions" — already deferred; ASK-V2-04 may merge into this

### Out of Phase 6 scope (notable mentions)
- Multi-turn conversation / chat-thread UX (Dashboard's `.ai-side` 2-col model) — would need a separate "Ask v3" milestone
- LLM streaming responses — not in v2.0 (single-shot per Phase 3 D-21 carryover)
- Per-user backend preference (vs shared cookie) — needs auth (D-04 deferral)
- Threat-model regression tests at the route layer — explicitly skipped per user; Phase 1 `nl_service` tests are the single locus

</deferred>

---

*Phase: 06-ask-tab-port*
*Context gathered: 2026-04-29*
