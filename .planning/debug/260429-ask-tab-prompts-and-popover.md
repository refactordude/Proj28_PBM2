---
status: awaiting_human_verify
trigger: "Investigate two bugs in the Ask tab: (1) example prompts do nothing when clicked, (2) Confirm parameters dropdown is clipped"
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:10:00Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: BOTH root causes confirmed. Fixing now.
  Bug #1: _starter_chips.html onclick only sets value + focus; missing requestSubmit() call to auto-run the form.
  Bug #2: _confirm_panel.html .panel container has overflow:hidden (Phase 03 default); CSS rule at app.css:112 only covers .browse-filter-bar and .overview-filter-bar; no selector covers the ask confirm panel picker dropdown.
test: code review complete — reading confirmed both mechanisms
expecting: applying fixes then verifying
next_action: edit _starter_chips.html onclick + extend CSS :has() selector

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected:
  1. Clicking a prompt chip under "Try asking" should populate the prompt and submit the question (auto-run).
  2. The "Confirm parameters" dropdown should fully render and not be clipped by its parent panel/card.

actual:
  1. Clicking a "Try asking" prompt does nothing — no UI feedback, no question runs.
  2. The "Confirm parameters" dropdown/popover is visually clipped off (cut at the panel edge).

errors: none reported visually
reproduction:
  1. Navigate to Ask tab
  2. Click any "Try asking" prompt chip → nothing happens
  3. Open "Confirm parameters" dropdown → clipped by surrounding card/panel

started: v2.0 shell; Browse-tab equivalent clipping fixed in commit c9f9bcd on 2026-04-29

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-29T00:01Z
  checked: app_v2/templates/ask/_starter_chips.html line 25
  found: onclick handler is `var t=document.getElementById('ask-q');t.value={{ prompt.question | tojson }};t.focus();` — sets value and focuses but never calls requestSubmit() or dispatchEvent('submit')
  implication: Bug #1 confirmed. The click fills the textarea but nothing triggers the form POST. No other JS wiring exists for chips (grep found no htmx.trigger/dispatchEvent/auto-submit anywhere near this file).

- timestamp: 2026-04-29T00:01Z
  checked: app_v2/templates/ask/_starter_chips.html design comment lines 8-10
  found: Comment says "clicking a chip fills the textarea but does NOT auto-submit" — the spec comment itself reflects the wrong behavior. The objective requires auto-run.
  implication: The spec comment was written to match the (wrong) implementation. The fix is to add requestSubmit() to the onclick AND update the comment.

- timestamp: 2026-04-29T00:02Z
  checked: app_v2/templates/ask/_confirm_panel.html — panel wrapper structure
  found: Line 28: `<div class="panel" style="border-left: 3px solid var(--violet, #7a5af8);">` — a bare .panel with no filter-bar class. The picker_popover macro renders a Bootstrap .dropdown-menu inside this panel.
  implication: .panel { overflow: hidden } (app.css §3 line 21) clips the dropdown. The :has() exception at app.css:112 covers only .browse-filter-bar and .overview-filter-bar — the ask confirm panel has neither.

- timestamp: 2026-04-29T00:02Z
  checked: app_v2/static/css/app.css line 112
  found: `.panel:has(.browse-filter-bar), .panel:has(.overview-filter-bar) { overflow: visible; }` — Ask confirm panel not covered.
  implication: Bug #2 confirmed. Pattern from prior fix (commit c9f9bcd) needs to be extended to cover the ask confirm panel. The cleanest selector is `.panel:has(#ask-confirm-form)` — the form id is stable and unique.

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: |
  Bug #1: _starter_chips.html onclick only set textarea value + focus but never
  called form.requestSubmit(). The design-comment even said "does NOT auto-submit",
  so the wrong behavior was intentional per a stale spec. The objective requires
  auto-run on chip click.

  Bug #2: The .panel wrapper in _confirm_panel.html has overflow:hidden (Phase 03
  default). The CSS :has() overflow-visible exception (app.css line 112, added in
  commit c9f9bcd) only covered .browse-filter-bar and .overview-filter-bar panels.
  The ask confirm panel carries neither class, so its Bootstrap .dropdown-menu was
  clipped at the panel edge. Fix extends the :has() rule to also match
  .panel:has(#ask-confirm-form).

fix: |
  1. app_v2/templates/ask/_starter_chips.html: added
     `document.getElementById('ask-query-form').requestSubmit();`
     at the end of the chip button onclick handler; updated design comment.
  2. app_v2/static/css/app.css: extended overflow-visible :has() compound
     selector to include `.panel:has(#ask-confirm-form)` on its own line.

verification: self-verified via code review; awaiting human confirmation in browser
files_changed:
  - app_v2/templates/ask/_starter_chips.html
  - app_v2/static/css/app.css
