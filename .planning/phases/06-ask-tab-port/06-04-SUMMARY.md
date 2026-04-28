---
phase: 06-ask-tab-port
plan: 04
subsystem: ui
tags: [jinja2, htmx, bootstrap, ask-tab, nl-agent, css, templates]

requires:
  - phase: 06-ask-tab-port
    plan: 02
    provides: picker_popover macro with disable_auto_commit kwarg; load_starter_prompts(); resolve_active_backend_name()
  - phase: 06-ask-tab-port
    plan: 03
    provides: GET /ask, POST /ask/query, POST /ask/confirm, POST /settings/llm routes; context dict shapes for all 4 templates

provides:
  - ask/index.html: full Ask page extending base.html with LLM dropdown (D-13), textarea+clear (D-06), starter-chip include (D-02/D-03), #answer-zone placeholder (D-08)
  - ask/_starter_chips.html: 4x2 Bootstrap grid of .ai-chip buttons that fill textarea without auto-submit (ASK-V2-08)
  - ask/_confirm_panel.html: NL-05 confirmation fragment (id=answer-zone); picker_popover with disable_auto_commit=True; hidden original_question; Run Query button (D-07/D-10)
  - ask/_answer.html: answer fragment (id=answer-zone); result table + LLM summary + collapsed Generated SQL expander; no extra action buttons (D-11)
  - ask/_abort_banner.html: abort fragment (id=answer-zone); verbatim v1.0 step-cap/timeout/llm-error copy; Partial output expander when last_sql set
  - app.css Phase 6 appendix: .ai-chip component class (rounded-pill, #f4f6f8 bg, accent hover) + 3 pseudo-states

affects:
  - 06-05-PLAN (tests: test_ask_routes.py consumes these templates via TestClient)
  - future-ask-tab: any visual change to Ask page starts here

tech-stack:
  added: []
  patterns:
    - "id=answer-zone on outermost wrapper of every answer-zone-replacing fragment (D-08 idempotent outerHTML swap pattern)"
    - "Jinja2 comment hygiene: avoid banned tokens (alert-warning, regenerate, | safe) even in comments — plan grep checks scan comments too"
    - "picker_popover macro with disable_auto_commit=True: confirmation panel checkbox toggles silent; Run Query is the sole commit trigger (Pitfall 3 / D-07)"
    - "Five verbatim copy strings from 02-UI-SPEC.md Copywriting Contract: placeholder, abort step-cap, abort timeout, Generated SQL, Try asking..."

key-files:
  created:
    - app_v2/templates/ask/index.html
    - app_v2/templates/ask/_starter_chips.html
    - app_v2/templates/ask/_confirm_panel.html
    - app_v2/templates/ask/_answer.html
    - app_v2/templates/ask/_abort_banner.html
  modified:
    - app_v2/static/css/app.css

key-decisions:
  - "D-08 enforcement: three answer-zone-replacing fragments each carry id=answer-zone on outermost wrapper so HTMX outerHTML swaps are idempotent regardless of which branch the route returns"
  - "D-11 compliance: _answer.html contains no action buttons; comment wording avoids the word 'regenerate' to satisfy grep-0 success criterion"
  - "D-18 compliance: no alert-warning class anywhere; comment wording avoids the literal token to satisfy grep-0 success criterion"
  - "Jinja2 comment hygiene convention: when a plan has grep-count-0 success criteria, the literal token must be absent from comments too — not just functional HTML"

requirements-completed:
  - ASK-V2-01
  - ASK-V2-02
  - ASK-V2-03
  - ASK-V2-05
  - ASK-V2-07
  - ASK-V2-08

duration: 15min
completed: 2026-04-29
---

# Phase 6 Plan 04: Ask Templates + CSS Appendix Summary

**Five Jinja2 templates building the full Ask UI surface (page / chips / confirm / answer / abort) plus .ai-chip CSS class, all wired to Plan 06-03's routes via HTMX outerHTML swaps into a single #answer-zone**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-29T00:10:00Z
- **Completed:** 2026-04-29T00:25:00Z
- **Tasks:** 2
- **Files modified:** 6 (5 new templates + 1 extended CSS file)

## Accomplishments

### Task 1: Five ask/ templates with verbatim copy ports

Created `app_v2/templates/ask/` directory and five Jinja2 templates:

**ask/index.html** (full page, extends base.html):
- Page header bar: `<h1>Ask</h1>` + Bootstrap `.dropdown` LLM selector (D-12/D-13)
- LLM dropdown items use `hx-post="/settings/llm"` with `hx-vals='{"name": "..."}'` and `hx-swap="none"` — 204 + HX-Refresh: true drives reload (D-16)
- Textarea with verbatim placeholder: `"e.g. What is the WriteProt status for all LUNs on platform X?"` (02-UI-SPEC.md Copywriting Contract)
- ✕ clear button with inline onclick (D-06 / CONTEXT.md Discretion)
- Run button (first-turn submit) wired to `hx-post="/ask/query"` with `hx-target="#answer-zone"` `hx-swap="outerHTML"`
- Starter chips include guarded by `{% if starter_prompts %}` (D-03)
- Empty `<div id="answer-zone">` swap target (D-08)

**ask/_starter_chips.html** (4×2 chip grid):
- Heading "Try asking..." — verbatim from 02-UI-SPEC.md Copywriting Contract
- Bootstrap `.row.g-2` with `.col-md-3.col-sm-6` columns
- Each `<button class="ai-chip">` with inline `onclick` that fills textarea without auto-submit (D-02/ASK-V2-08)
- `starter_prompts[:8]` slice — exactly 4×2 = 8 chips maximum
- NOT inside `#answer-zone` (lives in outer page scope)

**ask/_confirm_panel.html** (NL-05 confirmation fragment):
- Outermost `<div id="answer-zone">` (D-08)
- Imports and calls `picker_popover` macro from `browse/_picker_popover.html` with `disable_auto_commit=True` (D-07/Pitfall 3)
- Hidden `<input name="original_question">` for second-turn loop-prevention message (RESEARCH.md Open Question 3)
- Run Query ▸ button: `hx-post="/ask/confirm"` + `hx-include="#ask-confirm-form"` + `hx-target="#answer-zone"` `hx-swap="outerHTML"` (D-10)

**ask/_answer.html** (answer fragment):
- Outermost `<div id="answer-zone">` (D-08)
- Result table: Bootstrap `.table.table-striped.table-hover.table-sm` with sticky header; TextColumn-only (Pitfall 2 mitigation)
- Row count caption: `"{{ row_count }} rows returned."` — verbatim from 02-UI-SPEC.md Copywriting Contract
- LLM summary: plain `{{ summary | e }}` in a div (autoescaped, never `| safe`)
- Collapsed `<details>` with title "Generated SQL" — verbatim from 02-UI-SPEC.md Copywriting Contract
- No extra action buttons per D-11/ASK-V2-03 deviation

**ask/_abort_banner.html** (abort/error fragment):
- Outermost `<div id="answer-zone">` (D-08)
- Bootstrap `.alert.alert-danger`; three branches keyed on `reason`:
  - `step-cap`: "Agent stopped: reached the 5-step limit. Try rephrasing your question with more specific parameters." — verbatim
  - `timeout`: "Agent stopped: query timed out after 30 seconds. Try a more targeted question or switch to a faster model." — verbatim
  - else (`llm-error`): "Something went wrong." + autoescaped `detail`
- Partial output `<details>` expander (title "Partial output" verbatim) when `last_sql` non-empty

### Task 2: Phase 6 CSS appendix

Appended to `app_v2/static/css/app.css` (216 → 261 lines; additive only):

```css
.ai-chip { ... border-radius: 999px; background: #f4f6f8; ... }
.ai-chip:hover, .ai-chip:focus-visible { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
.ai-chip:active { background: #e3e7ec; }
```

Source: Dashboard_v2.html lines 337-339 simplified for Bootstrap `.col-md-3` column context. All Phase 1-5 CSS selectors (`.shell`, `.panel`, `.ai-btn`) preserved unchanged.

## Task Commits

1. **Task 1: Five ask/ templates** — `c32a479` (feat)
2. **Task 2: Phase 6 CSS appendix** — `1f98557` (feat)
3. **D-18 comment hygiene fix** — `db1b08e` (fix)

## Files Created/Modified

- `app_v2/templates/ask/index.html` — Full Ask page (D-01 layout, D-13 LLM dropdown, D-06 clear, D-08 answer-zone)
- `app_v2/templates/ask/_starter_chips.html` — 4×2 .ai-chip grid (ASK-V2-08, D-02/D-03)
- `app_v2/templates/ask/_confirm_panel.html` — NL-05 confirmation fragment (D-07, D-08, D-10)
- `app_v2/templates/ask/_answer.html` — Answer fragment: table + summary + SQL expander (ASK-V2-03 post-deviation, D-11)
- `app_v2/templates/ask/_abort_banner.html` — SAFE-04 abort fragment with verbatim v1.0 copy (ASK-V2-07)
- `app_v2/static/css/app.css` — Phase 6 appendix: .ai-chip component class + 3 pseudo-states

## Verbatim Copy Strings Ported (02-UI-SPEC.md)

| Element | Copy |
|---------|------|
| Textarea placeholder | `"e.g. What is the WriteProt status for all LUNs on platform X?"` |
| Starter chip heading | `"Try asking..."` |
| SQL expander title | `"Generated SQL"` |
| Abort — step cap | `"Agent stopped: reached the 5-step limit. Try rephrasing your question with more specific parameters."` |
| Abort — timeout | `"Agent stopped: query timed out after 30 seconds. Try a more targeted question or switch to a faster model."` |
| Partial output title | `"Partial output"` |
| Row-count caption | `"{N} rows returned."` |

## Picker Reuse Pattern

`_confirm_panel.html` imports the Phase 4 picker macro and calls it with `disable_auto_commit=True`:

```jinja2
{% from "browse/_picker_popover.html" import picker_popover %}
{{ picker_popover(
     name="confirmed_params",
     label="Confirm parameters",
     options=all_params,
     selected=candidate_params,
     form_id="ask-confirm-form",
     hx_post="/ask/confirm",
     hx_target="#answer-zone",
     disable_auto_commit=True
   ) }}
```

The `disable_auto_commit=True` flag suppresses all `hx-*` attributes on the inner `<ul>` (shipped in Plan 06-02) so checkbox toggles do NOT fire agent runs. The Run Query ▸ button below is the only commit trigger (Pitfall 3 / D-07/D-10).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed 'regenerate' word from _answer.html comments**
- **Found during:** Task 1 verification
- **Issue:** Plan success criterion `grep -ciE 'regenerate' app_v2/templates/ask/*.html returns 0` failed — the file's Jinja2 comments mentioned the word "Regenerate button" for documentation purposes
- **Fix:** Rewrote comment to describe D-11 without using the literal word "regenerate" (used "extra action buttons" and "resend mechanism" instead)
- **Files modified:** `app_v2/templates/ask/_answer.html`
- **Verification:** `grep -ciE 'regenerate' app_v2/templates/ask/_answer.html` returns 0

**2. [Rule 1 - Bug] Removed 'alert-warning' token from _abort_banner.html comment**
- **Found during:** Task 1 verification (D-18 check)
- **Issue:** Plan success criterion `grep -ciE 'alert-warning' app_v2/templates/ask/*.html returns 0` failed — the Jinja2 comment said "NO .alert-warning OpenAI sensitivity banner" which contained the literal token
- **Fix:** Rephrased comment to "No OpenAI sensitivity banner anywhere per user decision" avoiding the literal class name
- **Files modified:** `app_v2/templates/ask/_abort_banner.html`
- **Verification:** `grep -ciE 'alert-warning' app_v2/templates/ask/_abort_banner.html` returns 0
- **Committed in:** `db1b08e`

---

**Total deviations:** 2 auto-fixed (2 Rule 1 comment hygiene)
**Impact on plan:** Both fixes address plan grep-count-0 acceptance criteria; no behavior change in rendered HTML. Establishes Jinja2 comment hygiene convention: when a plan has grep-count-0 success criteria, avoid the literal token in comments too (mirrors Phase 05-02 `yaml.load` comment hygiene convention).

## Known Stubs

None — templates receive all required context from Plan 06-03's routes. The `starter_prompts` list is loaded from YAML by `load_starter_prompts()` (Plan 06-02). The `#answer-zone` empty `<div>` on initial page load is intentional (not a stub — it is the correct empty state before any question is asked).

## Self-Check

Verified before writing SUMMARY:
- All 5 templates exist and render under their respective context shapes (Jinja2 render test passed)
- Zero `| safe` filters anywhere in `app_v2/templates/ask/`
- Zero `regenerate` occurrences in any ask template
- Zero `alert-warning` / `data-sensitivity` / `sensitivity-warning` in any ask template
- Three answer-zone-replacing fragments each carry `id="answer-zone"` on outermost wrapper
- `_starter_chips.html` has zero `id="answer-zone"` occurrences
- `.ai-chip` rule present in `app_v2/static/css/app.css`
- All Phase 1-5 CSS selectors preserved (`.shell`, `.panel`, `.ai-btn`)
- Full v2 test suite: **300 passed, 2 skipped, 0 failed** (no regressions)

## Next Phase Readiness

- Plan 06-05 (tests) can now smoke-test all four Ask endpoints end-to-end using TestClient + template rendering (no more Jinja2 TemplateNotFound errors)
- Plan 06-06 (v1.0 cleanup / D-22): deletes `app/pages/ask.py` + `tests/pages/test_ask_page.py` + removes Ask page entry from `streamlit_app.py`
- The full Ask UI surface is complete — routes (06-03) + templates (06-04) are both in place; only tests (06-05) remain before Phase 6 is done

---
*Phase: 06-ask-tab-port*
*Completed: 2026-04-29*
