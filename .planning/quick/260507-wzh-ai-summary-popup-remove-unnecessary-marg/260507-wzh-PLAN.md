---
task: 260507-wzh
type: quick
description: AI Summary popup — remove dead space above h1 heading
files_modified:
  - app_v2/static/css/app.css
---

<objective>
Remove the unnecessary marginal space above the h1 heading at the top of the AI Summary popup (Bootstrap modal `#summary-modal`).

**Root cause identified:** `app_v2/static/css/app.css` line 132 sets `margin-top: 1.5em` on `.markdown-content h1`. When the AI Summary's markdown response starts with a `# Title` (which it typically does — see `app_v2/data/summary_prompt.py` and `jv_summary_prompt.py`), pandoc/markdown renders it as the **first child** inside `<article class="markdown-content">` (see `app_v2/templates/summary/_success.html` line 18). With no element above it, the `1.5em` top margin (~36px) becomes pure dead space between the modal's `.modal-body` (Bootstrap default `padding: 1rem`) and the visible heading.

**Why it looks "reserved for nothing":** the gap is normally meant to space an h1 *away from preceding paragraphs* in long markdown bodies — but when h1 is first, the space serves no purpose.

Purpose: surgical CSS fix — zero out the top margin of the first child inside any `.markdown-content` container so headings sit flush with the parent's natural top padding.
Output: 1 modified file, 1 added CSS rule (~2 lines).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@./CLAUDE.md
@app_v2/static/css/app.css
@app_v2/templates/summary/_success.html
@app_v2/templates/overview/index.html
@app_v2/templates/platforms/detail.html

<interfaces>
Relevant existing CSS rules in `app_v2/static/css/app.css` (lines 130-140):

```css
/* §Markdown content rendering rules */
.markdown-content { max-width: 800px; margin: 0 auto; line-height: 1.6; }
.markdown-content h1 { font-size: 24px; font-weight: 700; line-height: 1.3; margin-top: 1.5em; margin-bottom: 0.5em; }
.markdown-content h2 { font-size: 20px; font-weight: 700; line-height: 1.3; margin-top: 1.4em; margin-bottom: 0.5em; }
.markdown-content h3 { font-size: 17px; font-weight: 600; line-height: 1.4; margin-top: 1.2em; margin-bottom: 0.4em; }
.markdown-content p { margin: 0 0 1em; }
```

Two callers of `.markdown-content`:

1. **AI Summary modal** (the bug location) — `app_v2/templates/summary/_success.html:18`:
   ```html
   <article class="markdown-content" style="max-width: 720px; line-height: 1.55;">
     {{ summary_html | safe }}
   </article>
   ```
   `summary_html` typically begins with `<h1>...</h1>` (the LLM's title line). NO element precedes it inside `.markdown-content`.

2. **Platforms detail page** — `app_v2/templates/platforms/detail.html`. Outer `h1.page-title` sits OUTSIDE `.markdown-content`. Inside `.markdown-content`, the rendered note may have an Obsidian-style `.properties-table` first (see `app.css` lines 142-148), and the markdown body's first element follows. In either layout, this fix's effect (zero top margin on the first child) is desired — there is no use case where we want dead space at the very top of a markdown container.

Modal structure (for context only — NOT modified): `app_v2/templates/overview/index.html:159-174` defines `#summary-modal` with standard Bootstrap `.modal-header` / `.modal-body` chrome. The `<h5 class="modal-title">AI Summary</h5>` sits in the header — that's the popup's own title (separate from the markdown h1 below it). The bug is the gap *inside* `.modal-body`, above the rendered markdown's h1.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add `.markdown-content > :first-child { margin-top: 0; }` rule to app.css</name>
  <files>app_v2/static/css/app.css</files>
  <action>
Open `app_v2/static/css/app.css`. Locate the markdown content rules block (line 130 starts with the `/* §Markdown content rendering rules */` comment).

Insert a new CSS rule **immediately after the existing `.markdown-content { ... }` rule on line 131** (i.e., before the `.markdown-content h1` rule on line 132):

```css
/* 260507-wzh — kill dead space above the first rendered child (typically h1 in
   AI Summary popups). The h1/h2/h3 top margins below are designed to space
   headings AWAY from preceding paragraphs; when a heading is the first child
   they collapse into a visible gap above the modal/panel content. */
.markdown-content > :first-child { margin-top: 0; }
```

**Why universal `:first-child` and not just `h1:first-child`:** the LLM may occasionally start its markdown with a `## H2` or a paragraph instead of `# H1`. The universal selector handles every variant for free; the only side effect on the platforms detail page is that the markdown body's first paragraph (or properties-table — though `.properties-table` already has `margin: 0 auto 1.5em`, no top margin to zero) sits flush with its container's top, which is the desired layout there too.

**Do NOT** modify the existing `.markdown-content h1`, `h2`, or `h3` rules — those margins are correct for the *non-first* case (heading after a paragraph). The new rule is additive and uses the child-combinator (`>`) to avoid affecting nested elements like `<li>` first children inside `<ul>`.

**Do NOT** touch the modal markup in `app_v2/templates/overview/index.html` or the partial in `app_v2/templates/summary/_success.html` — they're correct.
  </action>
  <verify>
    <automated>grep -n "first-child { margin-top: 0" app_v2/static/css/app.css</automated>
  </verify>
  <done>
- `app_v2/static/css/app.css` contains the new rule `.markdown-content > :first-child { margin-top: 0; }` (with the 260507-wzh trailing-comment marker).
- Existing `.markdown-content h1/h2/h3` rules byte-stable (verifiable with `grep -c "margin-top: 1.5em" app_v2/static/css/app.css` — still returns 1).
- Live-server smoke test: open AI Summary popup on any Platform row in `/overview` (or JV row); the h1 sits flush with the modal-body's natural top padding (no extra dead space). On `/platforms/{id}`, the rendered note's first element (paragraph or properties-table) is unchanged visually since `.properties-table` already had no top margin and the first markdown paragraph never had a top margin.
- Existing test suite remains green: `pytest tests/v2 -q` passes (no test asserts on `margin-top: 1.5em` literal — confirmed via `grep -rn "margin-top.*1.5em\|first-child" tests/v2/ | head` returning no relevant matches).
  </done>
</task>

</tasks>

<verification>
Manual browser check on dev server:
1. `uvicorn app_v2.main:app --reload`
2. Visit `/overview` → click AI Summary on any row → modal opens → h1 sits flush below the modal-header divider, no ~36px dead band above it.
3. Visit `/joint_validation` → click AI Summary on any JV row → same flush layout (the partial is reused per Phase 01 Plan 01-01 D-OV-01 generic parameterization).
4. Visit `/platforms/{any-id}` → the markdown body still renders correctly; properties-table (if present) and paragraphs still have correct vertical rhythm BELOW the first element.

Automated check: full v2 suite still passes.
```
pytest tests/v2 -q
```
</verification>

<success_criteria>
- AI Summary popup's h1 has no dead space above it (visual confirmation).
- `.markdown-content` is still used in 2 callers (modal partial + platforms detail) with NO template changes.
- Single CSS rule added; no other rules modified or deleted.
- All v2 tests pass.
- Surgical: 1 file, 1 rule, ~3 lines including comment.
</success_criteria>

<output>
After completion, create `.planning/quick/260507-wzh-ai-summary-popup-remove-unnecessary-marg/260507-wzh-SUMMARY.md` documenting:
- Root cause (CSS `.markdown-content h1` 1.5em top margin acting as dead space when h1 is first child)
- Fix (additive `:first-child` zero-margin rule)
- Files changed (1)
- Verification result
</output>
