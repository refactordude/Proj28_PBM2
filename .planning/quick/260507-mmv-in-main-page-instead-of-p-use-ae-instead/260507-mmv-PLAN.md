---
quick: 260507-mmv
type: execute
wave: 1
depends_on: []
files_modified:
  - app_v2/templates/_components/topbar.html
  - app_v2/templates/base.html
  - tests/v2/test_phase04_uif_components.py
  - tests/v2/test_main.py
autonomous: true
requirements: [QUICK-260507-mmv]

must_haves:
  truths:
    - "Topbar brand-mark renders 'AE' (not 'P')"
    - "Topbar wordmark renders 'Yhoon Dashboard' (not 'PBM2')"
    - "Topbar avatar renders 'YH' (not 'PM')"
    - "Joint Validation tab renders the bi-clipboard-check icon (not bi-list-ul)"
    - "Browser <title> reads 'Yhoon Dashboard — Yhoon Dashboard v2.0' on default pages (and the page_title-prefixed variant on others)"
    - "Full v2 test suite remains green after rebrand (existing assertions on legacy literals updated in lockstep)"
  artifacts:
    - path: "app_v2/templates/_components/topbar.html"
      provides: "Rebranded topbar macro (AE / Yhoon Dashboard / YH / clipboard-check JV icon) with comment block updated to match"
      contains: "class=\"brand-mark\">AE<"
    - path: "app_v2/templates/base.html"
      provides: "Browser-tab title using 'Yhoon Dashboard' wordmark and an updated topbar block comment"
      contains: "Yhoon Dashboard"
    - path: "tests/v2/test_phase04_uif_components.py"
      provides: "Showcase topbar assertions updated to new brand literals"
      contains: "class=\"brand-mark\">AE<"
    - path: "tests/v2/test_main.py"
      provides: "Root-page topbar assertion updated to new brand literal"
      contains: "class=\"brand-mark\">AE<"
  key_links:
    - from: "app_v2/templates/_components/topbar.html"
      to: "app_v2/templates/base.html"
      via: "{% from \"_components/topbar.html\" import topbar %} (base.html line 1)"
      pattern: "from \"_components/topbar.html\" import topbar"
    - from: "tests/v2/test_phase04_uif_components.py"
      to: "app_v2/templates/_components/topbar.html"
      via: "client.get(\"/_components\") response body assertions"
      pattern: "class=\"brand-mark\">AE<"
    - from: "tests/v2/test_main.py"
      to: "app_v2/templates/_components/topbar.html"
      via: "client.get(\"/\") response body assertion"
      pattern: "class=\"brand-mark\">AE<"
---

<objective>
Rebrand the v2 topbar shell: brand-mark "P" → "AE", wordmark "PBM2" → "Yhoon Dashboard", avatar "PM" → "YH", Joint Validation tab icon `bi-list-ul` → `bi-clipboard-check`. Browser-tab title also moves from "PBM2" to "Yhoon Dashboard" (keeping the ` v2.0` suffix). Update the two test files that pin the legacy literals so the suite stays green in the same commit. Update the topbar.html doc comment so it doesn't lie about rendered DOM; refresh the base.html block comment in lockstep.

Purpose: User wants the shipped v2.0 shell to read as "Yhoon Dashboard" rather than the project's internal "PBM2" codename, and wants a Joint-Validation-semantic icon on the JV tab.

Output: Single commit, four files modified, byte-precise edits, full v2 test suite green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@app_v2/templates/_components/topbar.html
@app_v2/templates/base.html
@tests/v2/test_phase04_uif_components.py
@tests/v2/test_main.py

<interfaces>
<!-- The topbar macro signature is unchanged by this rebrand. Documenting for the executor: -->
<!-- topbar(active_tab="") — emits .topbar containing .brand (.brand-mark + <span> wordmark), -->
<!-- .tabs (3x .tab anchors), .top-right (.av avatar). All three tabs and the macro signature -->
<!-- stay byte-identical except for the four content swaps + one icon class swap below. -->
</interfaces>

<rebrand_map>
<!-- The orchestrator already located every literal. Use this table verbatim — no re-grep needed. -->

| File | Line | Before                                          | After                                                |
|---|---|---|---|
| app_v2/templates/_components/topbar.html | 7  | `nav by contract). Brand-mark renders letter "P". Avatar slot` | `nav by contract). Brand-mark renders letters "AE". Avatar slot` |
| app_v2/templates/_components/topbar.html | 8  | `   shows static "PM" initials.`                | `   shows static "YH" initials.`                      |
| app_v2/templates/_components/topbar.html | 15 | `    <div class="brand-mark">P</div>`           | `    <div class="brand-mark">AE</div>`               |
| app_v2/templates/_components/topbar.html | 16 | `    <span>PBM2</span>`                         | `    <span>Yhoon Dashboard</span>`                   |
| app_v2/templates/_components/topbar.html | 21 | `      <i class="bi bi-list-ul"></i> Joint Validation` | `      <i class="bi bi-clipboard-check"></i> Joint Validation` |
| app_v2/templates/_components/topbar.html | 33 | `    <div class="av">PM</div>`                  | `    <div class="av">YH</div>`                       |
| app_v2/templates/base.html               | 7  | `  <title>{{ page_title \| default("PBM2") }} — PBM2 v2.0</title>` | `  <title>{{ page_title \| default("Yhoon Dashboard") }} — Yhoon Dashboard v2.0</title>` |
| app_v2/templates/base.html               | 54 | `     Replaces the legacy Bootstrap navbar markup. Brand "P" + wordmark` | `     Replaces the legacy Bootstrap navbar markup. Brand "AE" + wordmark` |
| app_v2/templates/base.html               | 55 | `     "PBM2" + tab strip (Joint Validation / Browse / Ask) + static "PM"` | `     "Yhoon Dashboard" + tab strip (Joint Validation / Browse / Ask) + static "YH"` |
| tests/v2/test_phase04_uif_components.py  | 37 | `    assert 'class="brand-mark">P<' in body`    | `    assert 'class="brand-mark">AE<' in body`        |
| tests/v2/test_phase04_uif_components.py  | 38 | `    assert ">PBM2<" in body`                   | `    assert ">Yhoon Dashboard<" in body`             |
| tests/v2/test_main.py                    | 36 | `    assert 'class="brand-mark">P<' in r.text`  | `    assert 'class="brand-mark">AE<' in r.text`      |
</rebrand_map>

<icon_choice>
The orchestrator picked `bi-clipboard-check` as the better Joint-Validation icon: a clipboard implies a review/checklist artefact and the embedded check implies validation passed — strongest semantic match for "Joint Validation" in Bootstrap Icons 1.13.1, which is already vendored (base.html line 11). Alternatives considered and rejected: `bi-shield-check` (security flavor), `bi-patch-check` (approval-of-a-thing, too narrow), `bi-list-check` (closer to original list-ul + check, viable second choice but loses the artefact metaphor).
</icon_choice>

<scope_guardrails>
- Do NOT edit any file outside the four listed in `files_modified`.
- Do NOT change any HTML other than the six topbar.html lines + one base.html `<title>` line + the base.html block-comment lines 54-55.
- Do NOT touch the `class="av"` styling, `.brand-mark` styling, or any CSS in app.css/tokens.css — this is a pure content-and-icon rebrand.
- The `.tabs` macro structure, `aria-selected="true"` logic, and href targets stay byte-identical.
- Do NOT mass-rename `PBM2` across the repo — `STATE.md`, decisions logs, milestone audits, and other docs intentionally retain "PBM2" as the codename. Only base.html's user-visible `<title>` and the topbar wordmark are user-facing.
</scope_guardrails>

<tasks>

<task type="auto">
  <name>Task 1: Rebrand topbar shell + update lockstep tests</name>
  <files>app_v2/templates/_components/topbar.html, app_v2/templates/base.html, tests/v2/test_phase04_uif_components.py, tests/v2/test_main.py</files>
  <action>
Apply the byte-precise edits in the `<rebrand_map>` table above using the Edit tool, file by file. Each edit is a single old_string → new_string swap. Preserve indentation and surrounding context exactly.

Concrete steps:

1. **app_v2/templates/_components/topbar.html** — six edits:
   - Comment block lines 7-8: `letter "P"` → `letters "AE"` and `static "PM" initials` → `static "YH" initials`.
   - Line 15: `<div class="brand-mark">P</div>` → `<div class="brand-mark">AE</div>`
   - Line 16: `<span>PBM2</span>` → `<span>Yhoon Dashboard</span>`
   - Line 21: `<i class="bi bi-list-ul"></i> Joint Validation` → `<i class="bi bi-clipboard-check"></i> Joint Validation`
   - Line 33: `<div class="av">PM</div>` → `<div class="av">YH</div>`

2. **app_v2/templates/base.html** — two edits:
   - Line 7 `<title>`: replace `{{ page_title | default("PBM2") }} — PBM2 v2.0` with `{{ page_title | default("Yhoon Dashboard") }} — Yhoon Dashboard v2.0`. Keep the ` v2.0` suffix.
   - Block comment lines 54-55 inside the `<body>`: rewrite `Brand "P" + wordmark "PBM2"` → `Brand "AE" + wordmark "Yhoon Dashboard"` and `static "PM" avatar` → `static "YH" avatar`. The comment must match the rendered DOM after this rebrand (per CLAUDE.md GSD constraints).

3. **tests/v2/test_phase04_uif_components.py** — two edits at lines 37-38:
   - `assert 'class="brand-mark">P<' in body` → `assert 'class="brand-mark">AE<' in body`
   - `assert ">PBM2<" in body` → `assert ">Yhoon Dashboard<" in body`

4. **tests/v2/test_main.py** — one edit at line 36:
   - `assert 'class="brand-mark">P<' in r.text` → `assert 'class="brand-mark">AE<' in r.text`

WHY all four files in one task: per `<constraints>`, the codebase must remain green at every commit boundary. If markup changes ship without test updates (or vice versa), the working tree is red — same atomicity rationale as the Phase 04 Wave 3 topbar swap (see STATE.md decision "Plan 04-03: Single-commit atomicity for Wave 3").

WHY a `<title>` change is in scope even though the user only said "main page": the user-facing wordmark consistency requires the browser tab to also read "Yhoon Dashboard" — keeping `PBM2` there would expose the codename to every page-load. The ` v2.0` suffix stays because it's milestone metadata, not branding.

WHY the comment-block edits are mandatory: CLAUDE.md GSD enforcement and the `<constraints>` block both require code comments to not lie about rendered DOM. The topbar.html docstring (lines 1-11) currently documents `"P"` / `"PM"` / `"PBM2"`, and base.html lines 53-56 documents `Brand "P" + wordmark "PBM2"` / `static "PM" avatar`. Both must be refreshed to match the new literals.

WHY `bi-clipboard-check`: see `<icon_choice>` block above — strongest JV semantic in the already-vendored Bootstrap Icons 1.13.1 set.
  </action>
  <verify>
    <automated>cd /home/yh/Desktop/02_Projects/Proj28_PBM2 &amp;&amp; python -m pytest tests/v2/test_main.py tests/v2/test_phase04_uif_components.py -x -q 2>&amp;1 | tail -40</automated>
  </verify>
  <done>
- `grep -F 'class="brand-mark">AE<' app_v2/templates/_components/topbar.html` matches exactly 1 line.
- `grep -F '<span>Yhoon Dashboard</span>' app_v2/templates/_components/topbar.html` matches exactly 1 line.
- `grep -F 'bi-clipboard-check' app_v2/templates/_components/topbar.html` matches exactly 1 line.
- `grep -F 'class="av">YH<' app_v2/templates/_components/topbar.html` matches exactly 1 line.
- `grep -cE '(>P<|>PBM2<|>PM<|bi-list-ul)' app_v2/templates/_components/topbar.html` returns 0.
- `grep -F 'Yhoon Dashboard — Yhoon Dashboard v2.0' app_v2/templates/base.html` matches exactly 1 line.
- `grep -F 'PBM2' app_v2/templates/base.html` returns 0 matches.
- `grep -cF '>PBM2<' tests/v2/test_phase04_uif_components.py tests/v2/test_main.py` returns 0.
- `grep -cF '>P<' tests/v2/test_main.py tests/v2/test_phase04_uif_components.py` returns 0 (the legacy `class="brand-mark">P<` literal is gone from both test files).
- The two pytest files pass: `pytest tests/v2/test_main.py tests/v2/test_phase04_uif_components.py -x` exits 0.
- Full v2 test suite still green: `pytest tests/v2/ -q` exits 0 (sanity sweep — only the four files in `files_modified` should have changed).
  </done>
</task>

</tasks>

<verification>
Run the full v2 suite:

```bash
cd /home/yh/Desktop/02_Projects/Proj28_PBM2
python -m pytest tests/v2/ -q 2>&1 | tail -20
```

Expected: All tests pass (no new failures, no skips beyond the existing module-level skips). Spot-check the rendered shell:

```bash
cd /home/yh/Desktop/02_Projects/Proj28_PBM2
python -c "
from fastapi.testclient import TestClient
from app_v2.main import app
with TestClient(app) as c:
    body = c.get('/').text
    assert 'class=\"brand-mark\">AE<' in body
    assert '<span>Yhoon Dashboard</span>' in body
    assert 'bi-clipboard-check' in body
    assert 'class=\"av\">YH<' in body
    print('OK: rebrand visible on GET /')
"
```
</verification>

<success_criteria>
- All four files modified per the `<rebrand_map>` (no other files touched).
- `pytest tests/v2/` exits 0.
- Browser tab title on every default page reads "Yhoon Dashboard — Yhoon Dashboard v2.0".
- Joint Validation tab icon is `bi-clipboard-check` (clipboard with embedded check).
- Topbar comment blocks in both topbar.html and base.html accurately describe the rendered DOM (no stale "P" / "PM" / "PBM2" references).
- Single git commit covers all four files (atomic rebrand + test sync, no half-state in working tree).
</success_criteria>

<output>
After completion, create `.planning/quick/260507-mmv-in-main-page-instead-of-p-use-ae-instead/260507-mmv-SUMMARY.md` describing:
- Files changed (4) with line-level diffs.
- The icon decision (`bi-clipboard-check` chosen, alternatives considered).
- Confirmation that the topbar/base.html comment blocks were refreshed in lockstep.
- Test results (counts before/after; should be identical except for the literal-string updates).
</output>
