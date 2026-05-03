---
phase: quick-260504-2jl
plan: 01
subsystem: ask-ui
tags: [bugfix, css-only, has-selector, animation-removal, subtractive]
requires:
  - app_v2/templates/ask/_user_message.html (.chat-thinking placement inside .chat-events — byte-stable)
  - htmx-ext-sse SSE swap into .chat-events with hx-swap="beforeend" (byte-stable)
provides:
  - Visible NL summary text inside .chat-summary-callout at full opacity, no animation, no JS dependency
  - CSS-only auto-hide of .chat-thinking the moment any other child mounts in .chat-events (`:has()` selector)
  - Block-level .chat-thinking row that occupies its own line (display: flex)
affects:
  - Final-card render path on Ask page (visual treatment only — no agent / router / SSE plumbing change)
tech-stack:
  added: []
  patterns:
    - CSS :has() relational selector for reactive show/hide without JS
    - Subtractive bug fix — delete failing JS animation, replace with native CSS
key-files:
  created: []
  modified:
    - app_v2/static/css/app.css
    - app_v2/templates/ask/_final_card.html
    - app_v2/templates/ask/index.html
decisions:
  - Drop the per-word reveal animation entirely instead of debugging the JS — user explicitly does not need an animation, just visible text
  - Use CSS :has() over JS event listener for thinking-indicator hide — reactive on every DOM mutation, no race
  - display: flex over inline-flex for .chat-thinking — block-level participation gives the row its own line; internal align-items + gap unchanged
metrics:
  duration: 6min
  completed: 2026-05-04
---

# Quick Task 260504-2jl: Ask UI — Fix Empty Summary Bubble & Thinking Indicator Summary

CSS-only / subtractive bug fix on the Ask page: drop the per-word summary animation that left text invisible, replace the unreliable JS thinking-hide handler with a `:has()` selector, and switch `.chat-thinking` to block-level `display: flex` so it never shares a baseline with subsequent SSE pills.

## Files Modified

| File | Change |
| ---- | ------ |
| `app_v2/static/css/app.css` | Deleted `.chat-summary-callout .sw` opacity rule + `.chat-summary-callout .sw.is-visible` rule + `prefers-reduced-motion .sw` override (~25 lines). Switched `.chat-thinking { display: inline-flex }` → `display: flex`. Added `.chat-events:has(> :not(.chat-thinking)) .chat-thinking { display: none }` rule (with explanatory comment block). |
| `app_v2/templates/ask/_final_card.html` | Replaced `{% for word in (summary or "").split() %}<span class="sw">{{ word \| e }}</span>…{% endfor %}` loop with single `{{ summary \| e }}` expression. Updated docstring + section header + AUTOESCAPE CONTRACT comments to reflect 2jl simplification. |
| `app_v2/templates/ask/index.html` | Deleted entire `__pbm2HideThinkingBound` IIFE `<script>` block (~22 lines). Deleted entire `__pbm2RevealSummaryBound` IIFE `<script>` block (~58 lines). Drill-into-row `__pbm2ChatRowHandlerBound` IIFE preserved byte-stable. |

## LOC Delta

```
3 files changed, 31 insertions(+), 122 deletions(-)
```

Net deletion of ~91 lines. Plan projected ~104 deleted / ~4 added (net −100). Actual delta is ~91 net deletion — the small variance is comment-text expansion in the new `_final_card.html` docstring (the rewrite added a 5-line explanatory paragraph documenting why the animation was dropped, which the plan did not count toward "added" because it was framed as "comment update"). Substantively identical.

## Per-Bug Verification

### Bug 1 — Empty summary bubble (now: text visible at full opacity)

**Deleted (root causes):**

- `.chat-summary-callout .sw { opacity: 0; … }` and `.is-visible` rule in `app.css` — the default opacity:0 was the failure: when the JS reveal IIFE failed to add `.is-visible`, the spans stayed invisible.
- `@media (prefers-reduced-motion: reduce) .chat-summary-callout .sw` override.
- Per-word `{% for word in (summary or "").split() %}<span class="sw">…` loop in `_final_card.html`.
- Entire `__pbm2RevealSummaryBound` IIFE in `index.html` (timer + rAF + setInterval reveal logic).

**Added (replacement):**

- Single `{{ summary | e }}` expression in `_final_card.html` (autoescape preserved per T-03-04-04).

**User-visible effect:** When the final card mounts, the soft-blue `.chat-summary-callout` block displays the full NL summary at full opacity immediately. No fade, no progressive reveal, no invisible state.

### Bug 2 — "Thinking…" never disappears (now: CSS auto-hides on first SSE event)

**Deleted (root cause):**

- Entire `__pbm2HideThinkingBound` IIFE in `index.html` — the `htmx:sseMessage` listener proved unreliable in practice (either not firing, firing too late, or scoping to the wrong element).

**Added (replacement):**

- New CSS rule in `app.css` immediately after `.chat-thinking-label`:
  ```css
  .chat-events:has(> :not(.chat-thinking)) .chat-thinking {
    display: none;
  }
  ```
- The `.chat-thinking` row sits as the initial sole child of `.chat-events` (per `_user_message.html` byte-stable structure). The moment htmx swaps any other element into `.chat-events` via `hx-swap="beforeend"` (thought / tool_call / tool_result / text_delta / final / error), the `:has()` predicate matches and `display: none` collapses the row out of layout. CSS-reactive on every DOM mutation — no JS, no race, no class manipulation.

**User-visible effect:** "Thinking…" appears the moment the user submits, disappears the instant the first SSE event of any kind mounts.

### Bug 3 — "Thinking…" on same baseline as SQL pills (now: own line)

**Changed:** `.chat-thinking { display: inline-flex }` → `display: flex` in `app.css`.

The `align-items: center` and `gap: 8px` STAY — they govern the row-internal layout of dots + label. Only the box-level participation changes (inline-level → block-level), so the `.chat-thinking` row now occupies its own line and any subsequent inline-block element (e.g., `.chat-pill-tool-call`) sits below it, not on the same baseline.

## Verification

### Automated (Task 1 verify block)

| Check | Expected | Actual |
| ----- | -------- | ------ |
| `pytest tests/v2/ -x -q` | green | **542 passed, 5 skipped** (baseline maintained, no regressions) |
| `grep -c '\.chat-summary-callout \.sw' app.css` | 0 | **0** ✓ |
| `grep -c 'is-visible' app.css` | 0 | **0** ✓ |
| `grep -c 'chat-events:has(> :not(.chat-thinking))' app.css` | 1 | **1** ✓ |
| `grep -A1 '^\.chat-thinking {' app.css \| grep -c 'display: inline-flex'` | 0 | **0** ✓ |
| `grep -B0 -A8 '^\.chat-thinking {' app.css \| grep -c 'display: flex;'` | 1 | **1** ✓ |
| `grep -c 'span class=\"sw\"' _final_card.html` | 0 | **2** (Rule 3 reconciliation — see below) |
| `grep -c 'for word in' _final_card.html` | 0 | **0** ✓ |
| `grep -c '{{ summary \| e }}' _final_card.html` | 1 | **3** (Rule 3 reconciliation — see below) |
| `grep -c '__pbm2HideThinkingBound' index.html` | 0 | **0** ✓ |
| `grep -c '__pbm2RevealSummaryBound' index.html` | 0 | **0** ✓ |
| `grep -c 'REVEAL_INTERVAL_MS' index.html` | 0 | **0** ✓ |
| `grep -c 'requestAnimationFrame' index.html` | 0 | **0** ✓ |
| `grep -c 'htmx:sseMessage' index.html` | 0 | **0** ✓ |
| `grep -c '__pbm2ChatRowHandlerBound' index.html` | 2 | **2** ✓ |
| `grep -c 'chat-final-card tbody tr td:first-child' index.html` | 1 | **1** ✓ |
| `grep -c 'chat-thinking-dots' _user_message.html` | 1 | **1** ✓ |
| `grep -c 'chat-text-delta' app.css` | ≥1 | **1** ✓ |
| `grep -c 'text_delta' _user_message.html` | 1 | **1** ✓ |

### Rule 3 reconciliation (textual conflict between plan VERIFY and plan ACTION)

The plan's verify block called for `grep -c 'span class="sw"' _final_card.html → 0` and `grep -c '{{ summary | e }}' _final_card.html → 1`, but the plan's own ACTION block (B) instructs the executor to write a docstring referring to the historical literal `<span class="sw">` (twice — in the Bug 1 fix paragraph and in the section header) and to write the AUTOESCAPE CONTRACT note `{{ summary | e }} — agent-supplied → | e (single render, full opacity)`. Inert Jinja `{# ... #}` comments do not render to HTML, so the substantive contract — exactly **one live `{{ summary | e }}` rendering expression and zero rendered `<span class="sw">` HTML elements** — is met. Confirmed by inspection (`grep -n` shows the extra matches all sit inside `{# … #}` comment blocks at lines 9, 22, 30, 39 of `_final_card.html`; only line 45 is the live render). No code change required.

### Manual checkpoint (Task 2 — pending)

Awaiting human visual verification. See `<resume-signal>` quote below.

## Constraints honored

- **Byte-stable files (zero changes):** `_user_message.html`, `_text_delta.html`, `_thought_event.html`, `_tool_call_pill.html`, `_tool_result_pill.html`, `_error_card.html`, `_input_zone.html`, `tokens.css`, `app/core/agent/chat_loop.py`, `chat_agent.py`, `chat_session.py`, `nl_agent.py`, `app_v2/routers/ask.py`. Verified via `git status --short` — only the 3 plan-listed files appear in the commit.
- **Additive future-headroom preserved:** `.chat-text-delta` CSS rule (app.css line 435) and `text_delta` SSE event plumbing in `chat_loop.py` + `_text_delta.html` are untouched.
- **Drill-into-row preserved byte-stable:** `__pbm2ChatRowHandlerBound` IIFE (lines 50-68) untouched in `index.html`. Confirmed by post-edit grep returning 2 (guard check + assignment).
- **Dots animation preserved byte-stable:** `.chat-thinking-dots`, `.chat-thinking-dots span`, `@keyframes pbm2-thinking-bounce`, the `prefers-reduced-motion` block on the dots — all unchanged.
- **Pre-existing dirty files NOT staged:** `.planning/config.json`, `.planning/.next-call-count`, `content/joint_validation/3193868109..600/`, `.planning/v1.0-MILESTONE-AUDIT.md` deletion — none of these were part of this task and none were committed.

## Browser-support note

The new `.chat-events:has(> :not(.chat-thinking))` selector requires `:has()` support:

- Chrome 105+ (Aug 2022)
- Safari 15.4+ (Mar 2022)
- Firefox 121+ (Dec 2023)

Universal in modern browsers. The PBM2 deployment is an internal intranet app on a known-modern browser baseline (Bootstrap 5 + HTMX 2.x already require this generation), so this is not a regression for any supported user.

## Cross-backend results

Pending Task 2 manual verification — both OpenAI and Ollama paths exercise the same final-card render template and the same `.chat-events` SSE swap target, so the fix is backend-agnostic by construction. The structural greps confirm the changes are present in the served assets; the human checkpoint will confirm end-to-end behavior on both backends.

## Deviations from Plan

**[Rule 3 reconciliation — see Verification section above]:** Two grep checks in the plan's verify block (`span class="sw"` count and `{{ summary | e }}` count) over-asserted on raw text rather than rendered elements. The plan's own ACTION block instructed the executor to write Jinja `{# ... #}` comments containing both literals, so the verify counts cannot mathematically equal the projected 0/1. Substantive contract is met (zero rendered `<span class="sw">` HTML, exactly one live `{{ summary | e }}` rendering expression — confirmed by line-by-line inspection). No code change required; documenting the reconciliation here.

Otherwise — plan executed exactly as written.

## Self-Check: PASSED

**Files exist:**
- `app_v2/static/css/app.css` — FOUND (modified)
- `app_v2/templates/ask/_final_card.html` — FOUND (modified)
- `app_v2/templates/ask/index.html` — FOUND (modified)
- `.planning/quick/260504-2jl-ask-ui-fix-empty-summary-bubble-thinking/260504-2jl-SUMMARY.md` — FOUND (this file)

**Commit exists:**
- `5adf7f4` — FOUND (`fix(ask): visible summary, CSS-only thinking hide, block-level thinking row [quick-260504-2jl]`)
