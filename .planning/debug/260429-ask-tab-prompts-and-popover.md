---
status: fixing
trigger: "Investigate two bugs in the Ask tab: (1) example prompts do nothing when clicked, (2) Confirm parameters dropdown is clipped"
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T01:30:00Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: BOTH root causes re-confirmed after fresh full investigation from scratch.
  Bug #1 (REAL): _starter_chips.html onclick uses {{ prompt.question | tojson }} which
    renders double-quoted JSON strings ("...") inside a double-quoted HTML attribute.
    The embedded double-quote immediately terminates the onclick attribute. The
    JS onclick handler is malformed HTML — the browser parses it as a broken
    attribute and the JS inside never executes. requestSubmit() was added in the
    prior fix but it is dead code because the onclick is invalid HTML.
  Bug #2 (NEW): The CSS :has(#ask-confirm-form) fix was added but the problem
    persists. Given that the Browse :has(.browse-filter-bar) fix DOES work and
    the syntax is identical, the clipping source must be more reliable to fix
    via data-bs-boundary="viewport" on the dropdown toggle inside the picker
    macro — this instructs Popper.js to use the viewport as the clipping
    boundary, bypassing all overflow:hidden ancestors entirely.
test: live app rendered HTML confirmed via curl — onclick attribute terminates mid-string.
expecting: Fix #1: use data-question attribute + data-form attribute; JS reads from those.
           Fix #2: add data-bs-boundary="viewport" to picker toggle button.
next_action: apply both fixes now

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

- hypothesis: Bug #1 was simply a missing requestSubmit() call (prior session diagnosis)
  evidence: requestSubmit() was added in prior commit fafcf53 but user confirmed chip
            clicks STILL do nothing. Live HTML dump via curl reveals the onclick
            attribute uses {{ prompt.question | tojson }} which emits a double-quoted
            JSON string inside a double-quoted HTML attribute. The embedded " terminates
            the onclick="" attribute at the = sign, making the entire handler invalid.
            The requestSubmit() call that was added is never reached — the JS is not
            even syntactically valid HTML in this context.
  timestamp: 2026-04-29T01:15Z

- hypothesis: Bug #2 fixed by CSS :has(#ask-confirm-form) override (prior session)
  evidence: User confirmed dropdown still clipped after commit fafcf53. CSS :has()
            fix IS in the file (verified at app.css line 115). The fix may be
            defeated by browser cache or by Popper.js computing overflow from a
            different ancestor. The more robust fix bypasses CSS entirely by
            instructing Popper via data-bs-boundary="viewport" on the toggle button.
  timestamp: 2026-04-29T01:20Z

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-29T00:01Z
  checked: app_v2/templates/ask/_starter_chips.html line 25 (prior session)
  found: onclick handler fills textarea and focuses; requestSubmit() was missing
  implication: Prior fix was diagnosed as missing requestSubmit().

- timestamp: 2026-04-29T00:02Z
  checked: app_v2/static/css/app.css line 112 (prior session)
  found: :has() rule covered only .browse-filter-bar / .overview-filter-bar panels
  implication: Prior fix extended rule to include .panel:has(#ask-confirm-form).

- timestamp: 2026-04-29T01:10Z
  checked: live rendered HTML from GET /ask via curl
  found: |
    Chip button onclick rendered as:
      onclick="var t=document.getElementById('ask-q');t.value="What is the WriteProt status for all LUNs on platform X?";t.focus();document.getElementById('ask-query-form').requestSubmit();"
    The value= is followed by a double-quote (from tojson), which the HTML parser
    interprets as the END of the onclick="" attribute. The JS assigned to onclick
    becomes: `var t=document.getElementById('ask-q');t.value=` which is
    syntactically incomplete JavaScript. The button renders with a broken onclick.
    The click event fires but the handler is a no-op / throws a parse error.
  implication: This is the REAL root cause of Bug #1. The prior hypothesis
    (missing requestSubmit) was a secondary symptom of a different fix; the
    fundamental issue is tojson + double-quoted HTML attribute = HTML injection.

- timestamp: 2026-04-29T01:20Z
  checked: HTMX 2.0.10 source + Bootstrap 5.3.8 Dropdown internals
  found: |
    - HTMX listens for 'submit' event on form; requestSubmit() does fire submit
      events in modern browsers → HTMX interception IS correct once onclick works.
    - Bootstrap Dropdown uses Popper.js with boundary:"clippingParents" by default.
      Popper walks ancestors checking getComputedStyle(el).overflow for auto|scroll|
      overlay|hidden via Ze() function. CSS :has(#ask-confirm-form) overrides panel
      overflow but if browser cache or specificity issue defeats it, Popper still clips.
    - data-bs-boundary is read from data attributes via getDataAttributes() by Bootstrap.
      Setting data-bs-boundary="viewport" makes Popper use viewport as clip boundary,
      bypassing ALL overflow:hidden ancestors regardless of CSS state.
  implication: Bug #2's definitive fix is data-bs-boundary="viewport" on the toggle,
    NOT an additional CSS override. The CSS :has fix can remain as defense-in-depth.

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: |
  Bug #1 (CONFIRMED): The chip button onclick attribute is set with double quotes
  (`onclick="..."`). Inside the handler, the prompt text is inserted via
  `{{ prompt.question | tojson }}`. Jinja2's tojson filter produces a JSON string
  enclosed in double quotes (e.g., `"What is the WriteProt status..."`). These
  embedded double quotes terminate the HTML onclick attribute immediately after
  `t.value=`, producing invalid HTML. The browser parses a broken onclick handler
  that stops mid-expression. The click does nothing. requestSubmit() is present
  in the template source but never reached because the JS string assignment before
  it is HTML-broken.

  Bug #2 (CONFIRMED): The .panel { overflow: hidden } ancestor clips the Bootstrap
  dropdown-menu. CSS :has(#ask-confirm-form) override was added but user confirms
  it doesn't help. Root cause is that Popper.js detects overflow:hidden ancestors
  via computed style at runtime. The reliable fix is to add data-bs-boundary="viewport"
  to the dropdown toggle so Popper uses the viewport as its clipping constraint
  rather than scrolling ancestors.

fix: |
  Bug #1: Replace tojson-in-onclick approach with data-question attribute.
    The chip button carries data-question="{{ prompt.question | e }}" (HTML-escaped
    text — safe for attribute context). The onclick reads
    document.getElementById('ask-q').value = this.dataset.question;
    This avoids putting a JS string literal inside an HTML attribute entirely.
    requestSubmit() call remains at end of onclick.

  Bug #2: Add data-bs-boundary="viewport" to the dropdown toggle button in
    _picker_popover.html. This instructs Bootstrap/Popper to use the viewport
    as the clipping boundary instead of scrollable ancestors, bypassing the
    overflow:hidden .panel regardless of computed CSS state.

verification: pending — applying fixes now
files_changed:
  - app_v2/templates/ask/_starter_chips.html
  - app_v2/templates/browse/_picker_popover.html
