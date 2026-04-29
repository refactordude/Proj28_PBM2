# Phase 6: Ask Tab Port - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 06-ask-tab-port
**Areas discussed:** Page layout, Two-turn confirmation widget, LLM backend selector + cookie, Test scope + threat model

---

## Page Layout

### Layout shape

| Option | Description | Selected |
|--------|-------------|----------|
| Single column (v1.0 spec) | One column. History as collapsed `<details>` above textarea. Starter prompts as `.ai-chip` strip below textarea. Answer in a `.panel`. Simplest to port; matches v1.0 mental model. | ✓ |
| Faithful Dashboard 2-col | 300px `.ai-side` history sidebar + `.ai-main` answer area with `.ai-msgs`, `.ai-suggest` chips, `.ai-input` bottom bar. Visually closest to Dashboard. | |
| Adaptive (1-col empty, 2-col after) | Single column on first load; 2-col emerges after first question. Most polished UX but doubles template complexity. | |

**User's choice:** Single column (v1.0 spec)
**Notes:** Recommended option. User accepted the preview verbatim.

### Starter prompts placement & styling

| Option | Description | Selected |
|--------|-------------|----------|
| Bootstrap 4×2 grid w/ `.ai-chip` styling | Honor ASK-V2-08 grid spec literally; style each cell with the Dashboard `.ai-chip` class. | ✓ |
| Pure `.ai-chip` flex-wrap strip | Dashboard `.ai-suggest` flow; ignores 4×2 grid spec. | |
| Bootstrap 4×2 grid w/ `btn-outline-secondary` | Strict v1.0 port; no Dashboard chip styling. | |

**User's choice:** Bootstrap 4×2 grid w/ `.ai-chip` styling
**Notes:** Recommended option. Honors ASK-V2-08 while pinning to Dashboard's `.ai-chip` token.

### Starter prompts position

| Option | Description | Selected |
|--------|-------------|----------|
| Below textarea, above answer slot | Textarea = primary CTA on top; chips below as helper. | ✓ |
| Above textarea (suggestion-first) | Chips appear first as onboarding, then input. | |

**User's choice:** Below textarea, above answer slot
**Notes:** Recommended option, matches selected preview.

### Question echo in answer panel

| Option | Description | Selected |
|--------|-------------|----------|
| Echo question as `.msg user`, then `.msg ai` with results | Two stacked Dashboard chat bubbles. | |
| Skip echo — show table + summary directly | Result panel only. Question already in textarea. | ✓ |

**User's choice:** Skip echo — show table + summary directly
**Notes:** v1.0-faithful; saves vertical space.

### History panel

| Option | Description | Selected |
|--------|-------------|----------|
| Collapsed `<details>` above textarea, closed by default | Per ASK-V2-04 spec verbatim. | |
| Collapsed `<details>` above textarea, opens after first Q | Auto-opens after first question. | |
| **No history** (user free-text) | Drop history entirely from Phase 6. | ✓ |

**User's choice:** No history (user typed "no need for history")
**Notes:** ASK-V2-04 moves to Out of Scope. This is a meaningful spec deviation.

### Textarea persistence after query

| Option | Description | Selected |
|--------|-------------|----------|
| Persist last question in textarea until cleared | Browser refresh clears it; no cookie persistence. | |
| Clear textarea after each successful query | Empty textarea after answer renders. | |
| Persist + clear button next to textarea | Persist by default, with explicit ✕ to clear. | ✓ |

**User's choice:** Persist + small clear (✕) button next to textarea
**Notes:** Most explicit and discoverable.

---

## Two-turn Confirmation Widget

### Multiselect rendering

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse Browse picker-popover (D-15b) | Auto-commit, search filter, scrollable list, Apply/Clear. Reuses `popover-search.js`. | ✓ |
| Inline Bootstrap checkbox list with text-filter | Always-visible scrollable panel; simpler markup but more vertical space. | |
| Removable pill cards w/ autocomplete add (Dashboard `.ai-card-grid`) | Each candidate as a `.ai-src` card with ✕; novel UX. | |

**User's choice:** Reuse Browse picker-popover
**Notes:** Recommended option. Behaviorally consistent with Browse — user already knows the widget.

### HTMX swap target

| Option | Description | Selected |
|--------|-------------|----------|
| Replace `#answer-zone` with confirmation panel | Same swap target for both confirmation and final answer. | ✓ |
| Append confirmation below textarea, leave answer slot empty | Two DOM regions to manage. | |

**User's choice:** Replace `#answer-zone`
**Notes:** Recommended option. Symmetric, single-region NL state.

### After Run Query success

| Option | Description | Selected |
|--------|-------------|----------|
| Collapse — swap entire confirm panel out for answer | Cleanest. | ✓ |
| Persist as small collapsed summary above answer | "Ran with 8 of 12 params — Re-confirm" affordance. | |

**User's choice:** Collapse
**Notes:** Recommended option.

### 0 params on Run Query

| Option | Description | Selected |
|--------|-------------|----------|
| Disable Run Query until ≥1 selected | Inline hint, prevent nonsensical query. | |
| Allow 0 params — let agent decide | Trust agent; loop risk mitigated by step-cap. | ✓ |
| Allow 0 params — fall back to all original proposals | Forgive accidental clears, silently override. | |

**User's choice:** Allow 0 params — let agent decide
**Notes:** Deviation from v1.0 silent no-op. Loop-prevention added via defensive second-turn prompt instruction.

### Regenerate button

| Option | Description | Selected |
|--------|-------------|----------|
| Re-run with same question + same confirmed params | Per ASK-V2-03 spec verbatim, with `X-Regenerate` header. | |
| Re-run with same question, skip confirmation step | Forces single-shot mode. | |
| Adaptive — follows original path | Bookkeeping required. | |
| **No Regenerate button** (user free-text) | Editing textarea + Ask is the regeneration mechanism. | ✓ |

**User's choice:** No Regenerate button (user typed "no need for regeneration, but editing previous message is enough")
**Notes:** ASK-V2-03 partial deviation. Table/summary/SQL expander stay; only the Regenerate button is dropped.

---

## LLM Backend Selector + Cookie

### Selector placement

| Option | Description | Selected |
|--------|-------------|----------|
| Right-aligned dropdown in nav, after tabs | Global, per ASK-V2-05. | |
| Native `<select>` in nav, after tabs | Plain Bootstrap form-select. | |
| Selector only on Ask page | Drop "global" from spec. | ✓ |

**User's choice:** Selector only on Ask page (drop "global" from spec)
**Notes:** Partial deviation from ASK-V2-05.

### Cookie strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Plain unsigned cookie | Server validates against `settings.llms[].name` on read. | ✓ |
| Signed cookie via `itsdangerous` | Tamper-resistant; requires secret-management. | |
| Starlette `SessionMiddleware` | Heavier; meant for multi-key session state. | |

**User's choice:** Plain unsigned cookie
**Notes:** Recommended option. Validation against `settings.llms[].name` is the entire defense.

### Switch flow

| Option | Description | Selected |
|--------|-------------|----------|
| `hx-post /settings/llm`; 204 + Set-Cookie + `HX-Refresh: true` | Full page refresh; idempotent. | ✓ |
| `hx-post /settings/llm`; OOB swaps for nav + alert + dropdown | No reload, smoother but complex template plumbing. | |
| Plain form POST with full page reload | No HTMX. | |

**User's choice:** `hx-post` + 204 + Set-Cookie + `HX-Refresh: true`
**Notes:** Recommended option.

### OpenAI sensitivity banner

| Option | Description | Selected |
|--------|-------------|----------|
| Banner inside Ask page main area, dismiss = session cookie | Per ASK-V2-05 spec verbatim. | |
| Banner globally below navbar on every page when OpenAI active | Spec deviation. | |
| Toast-style notification on switch only | One-time. | |
| **No banner** (user free-text) | No alert anywhere. | ✓ |

**User's choice:** No banner (user typed "no need")
**Notes:** ASK-V2-05 banner half fully dropped.

### Cookie scope of effect (follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| Cookie overrides globally — Ask & AI Summary both use it | Update `llm_resolver` to read cookie first. | ✓ |
| Cookie only affects Ask routes | Two sources of truth. | |
| Cookie overrides + YAML knob to disable override | Redundant unless knob is wanted. | |

**User's choice:** Cookie overrides globally
**Notes:** Recommended option. Single source of truth across all v2.0 LLM-using features.

### Selector copy/style

| Option | Description | Selected |
|--------|-------------|----------|
| Header bar on Ask, label `LLM: Ollama▾` / `LLM: OpenAI▾` | Compact dropdown. | ✓ |
| Toggle pill group: `[Ollama] [OpenAI]` | Segmented btn-group. | |
| Plain `<select>`, label `Backend:` prefix | Native select. | |

**User's choice:** Header bar with `LLM: Ollama▾` / `LLM: OpenAI▾`
**Notes:** Recommended option.

---

## Test Scope + Threat Model

### Mocking strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Mock `nl_service.run_nl_query` at module level | Canned `NLResult` variants; doesn't touch agent or DB. | ✓ |
| Mock the PydanticAI Agent + DB adapter | Closer to integration; duplicative with Phase 1 tests. | |
| Hit a real agent against a fixture DB | Highest fidelity; slowest, flakiest. | |

**User's choice:** Mock `nl_service.run_nl_query` at module level
**Notes:** Recommended option. Same idiom as Phase 3 SUMMARY tests.

### Threat model items

**User's choice:** SKIP — no Phase 6 threat-model tests
**Notes:** User typed "skip threat model test". Inherits Phase 1's `nl_service` SAFE-02..06 coverage. The route layer is a thin shell over `run_nl_query`, so re-testing the harness from `/ask/query` would be redundant.

(Options not shown — user explicitly skipped this question.)

### Regression bar

| Option | Description | Selected |
|--------|-------------|----------|
| All v1.0 tests stay green; all prior v2.0 tests stay green; new v2.0 Ask tests added | Same standard as Phases 1–5. | ✓ |
| Same + integration test that hits a real Ollama if available | Extra layer; defer. | |

**User's choice:** All v1.0 tests + all prior v2.0 tests + new Phase 6 tests
**Notes:** Recommended option. Note: v1.0 test count drops by `tests/pages/test_ask_page.py`'s test count after D-22 cleanup.

### v1.0 Ask page disposition

| Option | Description | Selected |
|--------|-------------|----------|
| Stays in place (parallel operation) | Consistent with Phase 1 contract. | |
| Remove v1.0 Ask page once v2.0 ships | Hard deletion. | ✓ |

**User's choice:** Remove v1.0 Ask page once v2.0 ships
**Notes:** Phase-1 parallel-operation contract is overridden for the v1.0 Ask page only.

### v1.0 Ask removal scope

| Option | Description | Selected |
|--------|-------------|----------|
| Delete `app/pages/ask.py` + remove from `streamlit_app.py` nav + delete `tests/pages/test_ask_page.py` | Hard removal. | ✓ |
| Keep `app/pages/ask.py` with deprecation banner | Soft removal. | |
| Keep both pages live in parallel | Reverse course. | |

**User's choice:** Hard removal
**Notes:** Recommended option.

### Where the deletion happens

| Option | Description | Selected |
|--------|-------------|----------|
| Inside Phase 6, as the final plan | One commit, one place to review. | ✓ |
| Separate Phase 7 "v1.0 Ask removal" added to roadmap | Cleaner phase boundaries; workflow overhead. | |

**User's choice:** Inside Phase 6, as the final plan
**Notes:** Recommended option.

---

## Claude's Discretion

Areas where the user explicitly deferred to Claude or where the planner has flexibility:
- Exact dropdown markup (Bootstrap `.dropdown` vs HTMX-driven button)
- Exact textarea + ✕ clear button styling
- Whether the confirmation panel uses violet accent (consistent with `.ai-btn`) or stays neutral
- Test file layout (single `tests/v2/test_ask_routes.py` vs split per requirement)
- Whether to factor an `app_v2/services/ask_service.py` or keep route logic inline
- Whether to vendor a small `clear-textarea.js` helper or use inline `onclick`
- Concrete copy strings (defer to v1.0 02-UI-SPEC.md copywriting contract — port verbatim)

## Deferred Ideas

### Spec changes to apply during planning
- ASK-V2-03 → drop Regenerate clause
- ASK-V2-04 → move to Out of Scope (or merge into ASK-V2-F01)
- ASK-V2-05 → drop global-sidebar placement and OpenAI banner

### Out of Phase 6 scope
- Multi-turn conversation / chat-thread UX
- LLM streaming responses
- Per-user backend preference (needs auth)
- Threat-model regression tests at the route layer
