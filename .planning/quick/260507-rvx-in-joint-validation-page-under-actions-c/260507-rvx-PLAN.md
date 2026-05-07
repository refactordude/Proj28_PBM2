---
phase: quick-260507-rvx
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app_v2/templates/overview/_grid.html
  - app_v2/static/css/app.css
autonomous: true
requirements:
  - QT-260507-rvx-01  # Strip leading icon glyphs from edm and AI buttons (컨플 has none)
  - QT-260507-rvx-02  # Equal-width edm / 컨플 / AI buttons
  - QT-260507-rvx-03  # Center the Actions column header and cells

must_haves:
  truths:
    - "The edm button renders only the text 'edm' (no <i class='bi bi-link-45deg'> glyph in front), in BOTH active and disabled branches"
    - "The AI button renders only the text 'AI' (no <i class='bi bi-magic'> glyph in front)"
    - "The 컨플 button text is unchanged (no icon was present, no change required)"
    - "The three Actions buttons (edm, 컨플, AI) render at the same visual width regardless of label length"
    - "The Actions column header <th> is center-aligned (not right-aligned)"
    - "The Actions column body <td> is center-aligned (not right-aligned), with the three buttons visually centered horizontally"
  artifacts:
    - path: "app_v2/templates/overview/_grid.html"
      provides: "JV grid table with cleaned-up Actions column (no leading icons, equal-width buttons, centered header+cells)"
      contains: "text-center"
    - path: "app_v2/static/css/app.css"
      provides: "CSS rule that gives the three Actions buttons a consistent min-width (e.g. .jv-action-btn { min-width: 56px; })"
      contains: ".jv-action-btn"
  key_links:
    - from: "app_v2/templates/overview/_grid.html"
      to: "app_v2/static/css/app.css"
      via: ".jv-action-btn class applied to all three button/anchor elements"
      pattern: "jv-action-btn"
---

<objective>
Three small UI tweaks to the Joint Validation grid's Actions column:
(1) strip the leading Bootstrap-Icon glyph from the edm and AI buttons (컨플 already has none),
(2) make the three Actions buttons (edm / 컨플 / AI) render at the same width regardless of label length, and
(3) change the Actions column header + body cells from right-aligned (`text-end`) to center-aligned (`text-center`).

Purpose: Tighter, more uniform Actions column. The user noted that the leading icons read as "emojis" / visual noise, the unequal button widths look jagged, and right-alignment hugs the right edge instead of sitting cleanly in the column.

Output: Edited `app_v2/templates/overview/_grid.html` (5 markup changes) + a new tiny CSS rule in `app_v2/static/css/app.css` for the equal-width class.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md

<scouting_findings>
Per the orchestrator's scouting hint, the JV "grid" template is NOT under
`app_v2/templates/joint_validation/` (that dir holds only `detail.html` for the
single-JV detail view). The Joint Validation tab list grid is rendered by
`app_v2/templates/overview/_grid.html` — a leftover path name from the v2.0
"Overview" → "Joint Validation" rename (D-JV-01). Verified by grep: only
`app_v2/templates/overview/_grid.html` contains BOTH `edm` and `컨플` button
markup.

CSS file: `app_v2/static/css/app.css` is the project's single stylesheet (per
Phase 04 UI Foundation; tokens.css holds CSS vars only). Add the new rule there.

The three buttons currently:
  - edm (lines 53-58 active branch, 60-65 disabled branch):
      `<i class="bi bi-link-45deg"></i> edm`  — width: small (3 chars + icon)
  - 컨플 (lines 73-78 active branch, 80-85 disabled branch):
      bare `컨플` text, no `<i>` element — width: smallest (2 CJK chars)
  - AI (lines 91-101 always-active button):
      `<i class="bi bi-magic"></i> AI`  — width: smallest (2 chars + icon)

Existing button class strings to preserve:
  - edm active:    `btn btn-sm btn-outline-secondary text-dark`
  - edm disabled:  `btn btn-sm btn-outline-secondary`
  - 컨플 active:    `btn btn-sm btn-outline-secondary text-dark ms-1`
  - 컨플 disabled:  `btn btn-sm btn-outline-secondary ms-1`
  - AI button:      `btn btn-sm btn-outline-primary ms-1`

Test pinning audit (grep tests/v2/):
  - 5 tests assert literal `"컨플" in body` — SAFE, we keep that text verbatim
  - NO tests assert `bi-link-45deg`, `bi-magic`, `text-end Actions`, or
    `class="text-end"` on the Actions <th> — safe to mutate
</scouting_findings>

<interfaces>
The Actions column's button DOM has no JavaScript or backend coupling beyond:
  - HTMX attrs on AI button: `hx-post="/joint_validation/{id}/summary"` etc.
    → these stay byte-stable
  - Bootstrap modal triggers on AI button: `data-bs-toggle="modal"`
    `data-bs-target="#summary-modal"` → stay byte-stable
  - HREFs on edm/컨플 active branches: `href="{{ row.link }}"` and
    `href="{{ conf_url ~ '/' ~ row.confluence_page_id }}"` → stay byte-stable

Adding a class (`jv-action-btn`) to existing `class="..."` strings does not
disturb any selector binding (no JS or test queries this class today).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Edit _grid.html — strip leading icons, add equal-width class to all three Actions buttons, center the Actions column</name>
  <files>app_v2/templates/overview/_grid.html</files>
  <action>
Open `app_v2/templates/overview/_grid.html` and make exactly these edits (line numbers approximate; match by string):

**Edit A (Actions header — line 21):**
Change:
  `<th class="text-end">Actions</th>`
to:
  `<th class="text-center">Actions</th>`

**Edit B (Actions cell — line 49):**
Change the row's Actions <td> opening tag:
  `<td class="text-end">`
to:
  `<td class="text-center">`

**Edit C (edm active anchor — lines 53-58):**
- Replace `class="btn btn-sm btn-outline-secondary text-dark"` with
  `class="btn btn-sm btn-outline-secondary text-dark jv-action-btn"`
- Replace the inner content `<i class="bi bi-link-45deg"></i> edm` with just `edm`
  (drop the `<i>` element AND the leading space; keep the surrounding indentation
  the same, mirroring the bare-text shape of the 컨플 button below).

**Edit D (edm disabled button — lines 60-65):**
- Replace `class="btn btn-sm btn-outline-secondary"` with
  `class="btn btn-sm btn-outline-secondary jv-action-btn"`
- Replace the inner content `<i class="bi bi-link-45deg"></i> edm` with just `edm`.

**Edit E (컨플 active anchor — lines 73-78):**
- Replace `class="btn btn-sm btn-outline-secondary text-dark ms-1"` with
  `class="btn btn-sm btn-outline-secondary text-dark ms-1 jv-action-btn"`
- Body text `컨플` is UNCHANGED (no icon was present).

**Edit F (컨플 disabled button — lines 80-85):**
- Replace `class="btn btn-sm btn-outline-secondary ms-1"` with
  `class="btn btn-sm btn-outline-secondary ms-1 jv-action-btn"`
- Body text `컨플` is UNCHANGED.

**Edit G (AI button — lines 91-101):**
- Replace `class="btn btn-sm btn-outline-primary ms-1"` with
  `class="btn btn-sm btn-outline-primary ms-1 jv-action-btn"`
- Replace the inner content `<i class="bi bi-magic"></i> AI` with just `AI`
  (drop the `<i>` element AND the leading space).

DO NOT touch any other attribute on these elements:
  - `href`, `target`, `rel`, `aria-label`, `disabled` — all preserved verbatim
  - HTMX attrs on AI button (`hx-post`, `hx-target`, `hx-swap`, `hx-headers`,
    `data-bs-toggle`, `data-bs-target`) — preserved verbatim
  - Surrounding Jinja `{% if %}/{% else %}/{% endif %}` and Jinja comments
    `{# ... #}` — preserved verbatim
  - The 9 `sortable_th(...)` calls above the Actions header — untouched
  - The empty-state `<td colspan="10" class="text-center text-muted py-4">`
    — untouched (this is the table-empty cell, unrelated)

Class-string ordering note: Bootstrap class order is non-semantic, so
`jv-action-btn` MAY be appended at the end of each class string (as specified
above). This keeps the diff minimal — single space + new token at end of each
string.
  </action>
  <verify>
    <automated>cd /home/yh/Desktop/02_Projects/Proj28_PBM2 &amp;&amp; \
      grep -c 'class="text-end"' app_v2/templates/overview/_grid.html | grep -q '^0$' &amp;&amp; \
      grep -c 'bi-link-45deg' app_v2/templates/overview/_grid.html | grep -q '^0$' &amp;&amp; \
      grep -c 'bi-magic' app_v2/templates/overview/_grid.html | grep -q '^0$' &amp;&amp; \
      grep -c 'jv-action-btn' app_v2/templates/overview/_grid.html | grep -q '^5$' &amp;&amp; \
      grep -q '&lt;th class="text-center"&gt;Actions&lt;/th&gt;' app_v2/templates/overview/_grid.html &amp;&amp; \
      grep -q '&lt;td class="text-center"&gt;' app_v2/templates/overview/_grid.html</automated>
  </verify>
  <done>
- Actions <th> uses `text-center` (not `text-end`)
- Actions <td> uses `text-center` (not `text-end`)
- Zero occurrences of `bi-link-45deg` and `bi-magic` remain in the file
- Exactly 5 occurrences of `jv-action-btn` (edm active + edm disabled + 컨플 active + 컨플 disabled + AI = 5)
- All Jinja conditionals, HTMX attrs, hrefs, and aria-labels intact
  </done>
</task>

<task type="auto">
  <name>Task 2: Add `.jv-action-btn` equal-width CSS rule to app.css</name>
  <files>app_v2/static/css/app.css</files>
  <action>
Append a small CSS block to `app_v2/static/css/app.css` (place at end of file, with a comment header for traceability):

```css
/* JV grid Actions column — quick task 260507-rvx.
   Three Actions buttons (edm / 컨플 / AI) all carry .jv-action-btn so they
   render at uniform width regardless of label glyph count. min-width sized to
   comfortably fit the widest of the three labels (컨플 — 2 CJK glyphs) at
   .btn-sm scale; text-align center keeps single-word labels visually centered
   inside the box. */
.jv-action-btn {
  min-width: 56px;
  text-align: center;
}
```

Sizing rationale:
- `.btn-sm` font-size is ~0.875rem (~14px); `edm` (3 ASCII) ≈ 28px text-width,
  `AI` (2 ASCII) ≈ 18px text-width, `컨플` (2 CJK at ~14px each) ≈ 28-30px.
  With Bootstrap's default `.btn-sm` `padding-x: 0.5rem` (8px each side),
  the natural button widths span roughly 34-46px. `min-width: 56px` gives all
  three a comfortable equal floor with a small visual breathing margin and
  zero clipping risk for either Latin or CJK glyphs.
- `text-align: center` is required because Bootstrap's `.btn` defaults to
  `text-align: center` already, but we set it explicitly for documentation
  and to be safe against any inherited-text-align surprises from the parent
  `<td class="text-center">`.

DO NOT touch any other CSS rule in the file. Do not modify tokens.css.
  </action>
  <verify>
    <automated>cd /home/yh/Desktop/02_Projects/Proj28_PBM2 &amp;&amp; \
      grep -q '\.jv-action-btn' app_v2/static/css/app.css &amp;&amp; \
      grep -q 'min-width: 56px' app_v2/static/css/app.css &amp;&amp; \
      python -m pytest tests/v2/ -x -q 2>&amp;1 | tail -5</automated>
  </verify>
  <done>
- `.jv-action-btn` rule exists in app.css with `min-width: 56px` and `text-align: center`
- Full v2 test suite (`tests/v2/`) still passes — no regressions from the
  template edits in Task 1 (the `컨플` literal is preserved, no other
  test-pinned strings touched)
  </done>
</task>

</tasks>

<verification>
Manual visual check after running the app (defer to user as a follow-up,
not blocking):
  1. Start app: `uvicorn app_v2.main:app --reload`
  2. Open http://localhost:8000/joint_validation
  3. Confirm Actions column header reads "Actions" centered above the buttons
     (not flush-right)
  4. Confirm each row's three buttons (edm / 컨플 / AI) sit centered in the
     cell and have visually identical width
  5. Confirm no leading icon/glyph appears in front of edm or AI labels
</verification>

<success_criteria>
- All Task 1 + Task 2 `<verify>` automated commands pass
- `grep -c 'class="text-end"' app_v2/templates/overview/_grid.html` returns `0`
- `grep -c 'jv-action-btn' app_v2/templates/overview/_grid.html` returns `5`
- `grep -c 'jv-action-btn' app_v2/static/css/app.css` returns `1` (the rule)
- `tests/v2/` suite green (no regressions)
</success_criteria>

<output>
After completion, create `.planning/quick/260507-rvx-in-joint-validation-page-under-actions-c/260507-rvx-SUMMARY.md`
documenting: 5 markup edits in `_grid.html`, 1 new CSS rule in `app.css`,
test count delta (should be 0 — pure UI tweak with no test changes), and
confirm the `컨플` literal preservation invariant held.
</output>
