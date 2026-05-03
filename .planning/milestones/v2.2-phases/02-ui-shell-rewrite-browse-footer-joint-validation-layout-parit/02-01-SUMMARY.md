---
phase: 02-ui-shell-rewrite-browse-footer-joint-validation-layout-parit
plan: "01"
subsystem: ui-shell
tags: [css, tokens, layout, footer, tdd, bootstrap5]
requires: []
provides: [ui-shell-tokens, shell-full-width, site-footer-slot, navbar-padding]
affects: [app_v2/templates/base.html, app_v2/static/css/tokens.css, app_v2/static/css/app.css]
tech-stack:
  added: []
  patterns: [flex-column-sticky-footer, css-custom-properties-type-scale, tdd-grep-invariants]
key-files:
  created:
    - tests/v2/test_phase02_invariants.py
  modified:
    - app_v2/static/css/tokens.css
    - app_v2/static/css/app.css
    - app_v2/templates/base.html
decisions:
  - "D-UI2-04: 4 type-scale tokens added to tokens.css root block (--font-size-logo: 20px, --font-size-h1: 28px, --font-size-th: 12px, --font-size-body: 15px); --font-size-nav intentionally absent"
  - "D-UI2-03: .shell rule reduced to padding: 0 — max-width: 1280px and margin: 0 auto removed"
  - "D-UI2-02: .navbar rule in app.css §0 sets padding-top: 16px / padding-bottom: 16px"
  - "D-UI2-05: body flex-column + main.container-fluid flex:1 0 auto + .site-footer flex-shrink:0 implements sticky-in-flow footer"
  - "D-UI2-12: .panel-header .panel-title at 18px/700 mirrors Browse .panel-header b rule for JV heading visual parity"
  - "test_site_footer_rule uses regex rule-selector search to avoid false-match on comment text"
metrics:
  duration: "8min"
  completed: "2026-05-01"
  tasks: 3
  files: 4
---

# Phase 02 Plan 01: UI Shell Rewrite — Tokens, CSS, Footer Slot Summary

**One-liner:** Global shell rewritten with flex-column sticky-in-flow footer, 4 type-scale tokens, full-width `.shell`, taller nav (16px padding), and `.site-footer` block slot wired into base.html.

---

## What Was Built

Three discrete changes lock the visual contract from 02-UI-SPEC.md into the shell layer before any page-level restructuring begins:

1. **tokens.css** — 4 type-scale custom properties appended inside `:root {}` after the Shadow block. `--font-size-logo: 20px`, `--font-size-h1: 28px`, `--font-size-th: 12px`, `--font-size-body: 15px`. No `--font-size-nav` (nav tabs share body size at 700 weight). All 28 existing tokens preserved untouched.

2. **app.css** — Three edits:
   - §0 prepended: `body { display: flex; flex-direction: column; min-height: 100vh; }` + `main.container-fluid { flex: 1 0 auto; }` + `.site-footer { flex-shrink: 0; background: var(--panel); border-top: 1px solid var(--line); min-height: 48px; padding: 0 32px; display: flex; align-items: center; gap: 16px; }` + `.navbar { padding-top: 16px; padding-bottom: 16px; }`
   - §1: `.shell` reduced from `max-width: 1280px; margin: 0 auto; padding: 18px 24px 56px` to `padding: 0`
   - §3: `.panel-header .panel-title { font-size: 18px; font-weight: 700; letter-spacing: -.015em; margin: 0; line-height: 1.2; }` added
   - 260430-wzg `.panel.overview-filter-bar { overflow: visible }` preserved byte-stable

3. **base.html** — Single insertion before `</body>`: `<footer class="site-footer" id="site-footer">{% block footer %}{% endblock footer %}</footer>`

4. **test_phase02_invariants.py** — 15-test invariant suite (grep-style + TestClient) enforcing all 5 decisions. TDD RED commit made before implementation.

---

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 863dcaa | test | Add failing tests for phase 02 UI shell invariants (RED) |
| 50251b1 | feat | Add type-scale tokens to tokens.css (D-UI2-04) |
| e91f885 | feat | Add shell-rewrite CSS rules to app.css (D-UI2-02, D-UI2-03, D-UI2-05) |
| c09f42f | feat | Wire footer block into base.html (D-UI2-05) |

---

## Verification Results

- All 15 invariant tests in `tests/v2/test_phase02_invariants.py` pass.
- Full suite: **376 passed, 5 skipped, 0 failures** — zero regressions against the 506-test v2.0 baseline (5 skipped tests are pre-existing from Phase 1 plan 04).
- `grep -c 'max-width: 1280px' app_v2/static/css/app.css` → 0
- `grep -E '\.shell \{' app_v2/static/css/app.css` → `.shell { padding: 0; }`
- `grep -c '<footer class="site-footer"' app_v2/templates/base.html` → 1
- `grep -c '{% block footer %}' app_v2/templates/base.html` → 1
- `grep -c '\.panel\.overview-filter-bar' app_v2/static/css/app.css` → 2 (preserved)

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_site_footer_rule: regex selector search instead of string find**
- **Found during:** Task 2 GREEN verification
- **Issue:** `src.find(".site-footer")` hit the CSS comment text ("site-footer" in comment about D-UI2-05) before finding the actual `.site-footer {` rule selector. The extracted block ended at the first `}` which was inside the `body {}` block, not the `.site-footer {}` block — causing false negative on `flex-shrink: 0` assertion.
- **Fix:** Updated `test_site_footer_rule` to use `re.compile(r"\.site-footer\s*\{", re.MULTILINE).search(src)` to locate the CSS selector rule start, not the comment mention.
- **Files modified:** `tests/v2/test_phase02_invariants.py`
- **Commit:** e91f885

**2. [Rule 1 - Bug] tokens.css comment contained `--font-size-nav` substring**
- **Found during:** Task 1 GREEN verification
- **Issue:** The plan-specified comment text `"--font-size-nav intentionally not declared"` contained the literal string `--font-size-nav`, which caused `test_tokens_no_font_size_nav` to fail (test asserts the token name is absent from the entire file).
- **Fix:** Reworded comment to `"no separate nav token (UI-SPEC §Typography)"` — preserves the design intent without embedding the prohibited token name.
- **Files modified:** `app_v2/static/css/tokens.css`
- **Commit:** 50251b1

---

## Known Stubs

None — this plan creates no data-bearing UI content. The `{% block footer %}{% endblock footer %}` slot in base.html renders empty on pages that don't override it (detail pages, Ask); this is the intended design per D-UI2-05 ("48px white stripe at page bottom giving the rounded-card shell silhouette").

---

## Threat Surface Scan

No new trust boundaries introduced. Changes are:
- Static CSS files (served by StaticFiles, no user input)
- base.html footer slot default is empty string (no user data rendered)

Matches the T-02-01-01..04 entries in the plan's threat model. No unregistered threat surface.

---

## Self-Check: PASSED

Files exist:
- `app_v2/static/css/tokens.css` — FOUND
- `app_v2/static/css/app.css` — FOUND
- `app_v2/templates/base.html` — FOUND
- `tests/v2/test_phase02_invariants.py` — FOUND

Commits exist:
- 863dcaa — FOUND
- 50251b1 — FOUND
- e91f885 — FOUND
- c09f42f — FOUND
