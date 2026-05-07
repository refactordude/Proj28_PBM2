---
phase: quick-260507-vys
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app_v2/static/css/app.css
autonomous: true
requirements:
  - "Each tool_call / tool_result pill renders on its own line in the Ask transcript"
  - "Closed pills retain chip aesthetic (rounded, content-sized)"
  - "Expanded ([open]) pills still render as full-width readable cards"
  - "Streaming summary (.chat-text-delta) still flows as one paragraph below pills"
  - "No regression to .chat-thought, .chat-final-card, .chat-summary-callout"

must_haves:
  truths:
    - "Each closed .chat-pill-tool-call appears on its own line"
    - "Each closed .chat-pill-tool-result-ok / .chat-pill-tool-result-rejected appears on its own line"
    - "Closed pills are still sized to their content (not stretched to full container width)"
    - "Expanded ([open]) pills render as full-width cards (unchanged from current open-state appearance)"
    - "Final summary <span class='chat-text-delta'> chunks still concatenate inline as a flowing paragraph"
  artifacts:
    - path: "app_v2/static/css/app.css"
      provides: ".chat-pill-tool-call / .chat-pill-tool-result-* closed-state block layout + [open] width:auto"
      contains: "display: block"
  key_links:
    - from: ".chat-pill-tool-call (closed)"
      to: "block-level layout"
      via: "display: block; width: fit-content"
      pattern: "\\.chat-pill-tool-call \\{[^}]*display: block"
    - from: ".chat-pill-tool-result-ok, .chat-pill-tool-result-rejected (closed)"
      to: "block-level layout"
      via: "display: block; width: fit-content"
      pattern: "display: block;\\s*\\n\\s*width: fit-content"
    - from: ".chat-pill-tool-call[open]"
      to: "full-width card"
      via: "width: auto override"
      pattern: "\\[open\\][^}]*width: auto"
---

<objective>
Stack tool-call and tool-result pills vertically in the Ask transcript so each pill takes its own line, while keeping the chip aesthetic (rounded, content-sized) and preserving the existing expanded-card [open] state.

Purpose: The transcript currently reads as a horizontal jumble of pills (`▸ inspect_schema({}) ▸ inspect_schema ok ▸ get_distinct_values(...) ...`). Stacking them vertically makes the agent's tool sequence readable as a step-by-step log.

Output: 4 CSS edits in `app_v2/static/css/app.css` (no template changes, no JS, no HTML).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@app_v2/static/css/app.css
@app_v2/templates/ask/_thought_event.html
@app_v2/templates/ask/_tool_call_pill.html
@app_v2/templates/ask/_tool_result_pill.html
@app_v2/templates/ask/_text_delta.html
@app_v2/templates/ask/_user_message.html

<interfaces>
<!-- The 4 CSS rule blocks this task touches (current state, lines 580-636 of app.css). -->
<!-- The closed-state rules currently use display: inline-block; the [open] rules already use display: block. -->
<!-- The fix: closed → display: block + width: fit-content; [open] → add width: auto. -->

Closed-state tool-call pill (line 581-592):
```css
.chat-pill-tool-call {
  display: inline-block;          /* ← change to: display: block; width: fit-content; */
  padding: 6px 12px;
  margin: 6px 0;
  background: var(--violet-soft);
  color: var(--violet);
  border-radius: var(--radius-pill);
  font-size: 13px;
  font-weight: 500;
  font-family: "JetBrains Mono", ui-monospace, monospace;
  letter-spacing: 0;
}
```

Open-state tool-call pill (line 595-600):
```css
.chat-pill-tool-call[open] {
  display: block;                  /* ← keep; ADD: width: auto; */
  border-radius: var(--radius-card);
  background: #f7f4ff;
  padding: 12px 16px;
}
```

Closed-state tool-result pills (line 614-622):
```css
.chat-pill-tool-result-ok,
.chat-pill-tool-result-rejected {
  display: inline-block;           /* ← change to: display: block; width: fit-content; */
  padding: 6px 12px;
  margin: 6px 0;
  border-radius: var(--radius-pill);
  font-size: 13px;
  font-weight: 500;
}
```

Open-state tool-result pills (line 629-634):
```css
.chat-pill-tool-result-ok[open],
.chat-pill-tool-result-rejected[open] {
  display: block;                  /* ← keep; ADD: width: auto; */
  border-radius: var(--radius-card);
  padding: 12px 16px;
}
```

Untouched (out of scope):
- `.chat-thought` — `<details>` element, already block-level by default
- `.chat-text-delta` — `<span>`, MUST stay inline so the streaming summary flows as one paragraph
- `.chat-final-card`, `.chat-summary-callout` — final answer surfaces, unaffected
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Stack chat pills vertically (CSS-only)</name>
  <files>app_v2/static/css/app.css</files>
  <action>
Apply 4 surgical edits to `app_v2/static/css/app.css`. Use the Edit tool for each — do NOT use sed.

EDIT 1 — `.chat-pill-tool-call` closed-state rule (~line 582):
Change the single line `display: inline-block;` inside the `.chat-pill-tool-call { ... }` block (the one whose next properties are `padding: 6px 12px; margin: 6px 0; background: var(--violet-soft);`) to two lines:
```
  display: block;
  width: fit-content;
```
Why: `display: block` forces a line break (each pill on its own row); `width: fit-content` keeps the chip aesthetic — the pill stays sized to its text content instead of stretching to full container width.

EDIT 2 — `.chat-pill-tool-call[open]` rule (~line 595-600):
Inside the `.chat-pill-tool-call[open] { ... }` block, immediately after the `display: block;` line, add a new line:
```
  width: auto;
```
Why: when expanded into a card, the pill must fill the available width again — without this override, `width: fit-content` from EDIT 1 would still apply (since `[open]` only re-declares display, not width) and the expanded card would awkwardly hug its content.

EDIT 3 — `.chat-pill-tool-result-ok, .chat-pill-tool-result-rejected` closed-state rule (~line 614-622):
Change the single line `display: inline-block;` inside the `.chat-pill-tool-result-ok, .chat-pill-tool-result-rejected { ... }` shared block to two lines:
```
  display: block;
  width: fit-content;
```
Same rationale as EDIT 1, applied to both green (ok) and red (rejected) result pills.

EDIT 4 — `.chat-pill-tool-result-ok[open], .chat-pill-tool-result-rejected[open]` rule (~line 629-634):
Inside the shared `[open]` block, immediately after the `display: block;` line, add:
```
  width: auto;
```
Same rationale as EDIT 2.

Constraints (DO NOT touch):
- `.chat-thought` rules (lines ~559-578) — already block-level via `<details>` default
- `.chat-text-delta` (lines ~550-556) — MUST remain inline (span) so streaming summary flows as a paragraph
- `.chat-final-card`, `.chat-summary-callout` — final answer surfaces, out of scope
- `.chat-result-preview` table styles — out of scope
- All other properties (padding, margin, background, color, border-radius, font-*) on the four edited rules — leave byte-stable

Per project D-CHAT-13: pill aesthetic (violet for tool_call, green for ok-result, red for rejected) is contractual; only the `display` / `width` axes change.
  </action>
  <verify>
    <automated>
# 1. Closed-state pills are now block-level (4 expected matches: 1 tool-call closed + 1 shared result closed = 2 rules,
#    each with display: block + width: fit-content = 2 lines × 2 rules = 4 line matches across the file region)
grep -c -E "(display: block|width: fit-content);" app_v2/static/css/app.css

# 2. Both [open] rules now have width: auto override (2 expected matches)
grep -c "width: auto;" app_v2/static/css/app.css

# 3. Both inline-block declarations on chat pills are gone (0 expected matches)
grep -E "\.chat-pill-tool-(call|result-(ok|rejected))[^{]*\{[^}]*inline-block" app_v2/static/css/app.css | wc -l

# 4. .chat-text-delta is untouched and stays inline-eligible (no display rule, default = inline span; 0 matches expected)
grep -A 5 "^\.chat-text-delta {" app_v2/static/css/app.css | grep -c "display:"

# 5. v2 test suite still green (no UI test asserts on display:inline-block of pills, but run as a regression net)
pytest tests/v2/ -x -q 2>&1 | tail -5
    </automated>
  </verify>
  <done>
- `.chat-pill-tool-call` closed rule has `display: block; width: fit-content;` (no `inline-block`)
- `.chat-pill-tool-call[open]` rule has `width: auto;` line right after `display: block;`
- `.chat-pill-tool-result-ok, .chat-pill-tool-result-rejected` closed rule has `display: block; width: fit-content;`
- `.chat-pill-tool-result-ok[open], .chat-pill-tool-result-rejected[open]` rule has `width: auto;`
- `grep -c "inline-block" app_v2/static/css/app.css` for chat-pill-* selectors returns 0
- v2 test suite passes (regression check; CSS change should not break any backend/template test)
- Visual outcome (manual sanity check, not blocking): in `/ask`, after submitting a multi-tool question, each `▸ tool_name(...)` pill and each `▸ result` pill renders on its own line; clicking any pill still expands it to a full-width card; final summary text still reads as one flowing paragraph below the pills
  </done>
</task>

</tasks>

<verification>
- All 4 CSS edits land in a single commit on the `ui-improvement` branch
- `pytest tests/v2/ -q` passes (baseline + regression)
- `grep -E "\.chat-pill-tool-(call|result)[^{]*\{[^}]*inline-block" app_v2/static/css/app.css` returns no matches
- Manual /ask smoke (optional, not blocking): pills stack vertically; expanded card still readable; summary paragraph still flows
</verification>

<success_criteria>
- Each tool-call / tool-result pill takes its own line in the chat transcript (closed state)
- Closed pills retain chip width (sized to content, not full container)
- Expanded ([open]) pills retain the existing readable card width (full container)
- `.chat-text-delta` summary still flows as one paragraph (untouched)
- `.chat-thought` still renders as italic block (untouched)
- v2 test suite stays green
</success_criteria>

<output>
After completion, create `.planning/quick/260507-vys-in-ask-page-each-thought-process-message/260507-vys-SUMMARY.md`
</output>
