---
status: diagnosed
trigger: "gap-2: Apply button does not swap pivot grid; only Swap-axes triggers render"
created: 2026-04-27T14:00:00Z
updated: 2026-04-27T14:30:00Z
---

## Current Focus

hypothesis: Apply button POST sends empty platforms/params because hx-include CSS selector finds zero inputs (checkboxes are not DOM descendants of the empty form). Swap-axes works because its triggering element has form="browse-filter-form", so HTMX auto-includes form.elements (which DOES include form-associated inputs) for the non-GET request.
test: static code analysis of HTMX source (htmx.min.js dn() function) + template structure
expecting: confirmed — root cause is mismatched hx-include strategy between Apply and Swap-axes
next_action: return ROOT CAUSE FOUND (goal: find_root_cause_only)

## Symptoms

expected: |
  Selecting platforms+parameters in the pickers and clicking Apply triggers a
  POST /browse/grid carrying the checked items; the grid swaps in-place;
  HX-Push-Url updates the URL bar to /browse?platforms=...&params=...; the
  Swap-axes toggle re-renders the grid with axes flipped; Clear-all empties
  both pickers and shows the empty-state alert.

actual: |
  After ticking platforms+parameters and clicking Apply, the grid region keeps
  showing the empty-state alert. Clicking Swap-axes subsequently DOES correctly
  render the pivot grid with the previously-selected filters.

errors: "Select platforms and parameters above to build the pivot grid." (empty-state alert shown when it should show data)

reproduction: |
  1. python scripts/seed_demo_db.py
  2. .venv/bin/uvicorn app_v2.main:app --port 8000
  3. Open http://localhost:8000/browse, DevTools Network open
  4. Tick 2-3 platforms, tick 2-3 parameters
  5. Click Apply — grid keeps showing empty-state
  6. Click Swap-axes — grid now shows correct pivot data

started: observed on first UAT run 2026-04-27

## Eliminated

- hypothesis: build_view_model / pivot logic is broken
  evidence: Swap-axes calls the same build_view_model path and it works; the pivot code is not at fault.
  timestamp: 2026-04-27T14:10:00Z

- hypothesis: POST /browse/grid route handler returns wrong fragment
  evidence: When platforms/params ARE received correctly (Swap-axes path), the route returns the correct grid. The handler itself is correct.
  timestamp: 2026-04-27T14:10:00Z

- hypothesis: hx-target or hx-swap is wrong on Apply button
  evidence: hx-target="#browse-grid" and hx-swap="innerHTML swap:200ms" are present and correct on the Apply button. The problem is what goes INTO the POST body, not where the response lands.
  timestamp: 2026-04-27T14:15:00Z

## Evidence

- timestamp: 2026-04-27T14:05:00Z
  checked: app_v2/templates/browse/_picker_popover.html line 81
  found: Apply button uses hx-include="#browse-filter-form input:checked"
  implication: This is a CSS descendant selector — finds inputs that are DOM children of #browse-filter-form. The form is an empty element (no DOM children); the checkboxes are DOM children of .dropdown-menu elements, not of the form.

- timestamp: 2026-04-27T14:07:00Z
  checked: app_v2/templates/browse/index.html lines 42-45 + _picker_popover.html lines 57-62
  found: |
    <form id="browse-filter-form" autocomplete="off" class="visually-hidden" aria-hidden="true"></form>
    (empty form, DOM-sibling of the filter bar)
    checkboxes: <input type="checkbox" name="platforms" form="browse-filter-form" ...>
    (form= attribute associates them with the form, but they are NOT DOM descendants)
  implication: |
    CSS selector "#browse-filter-form input:checked" resolves via document.querySelectorAll()
    to the descendant combinator — finds ZERO checkboxes because the form has no DOM children.
    The form= attribute establishes form association for submission purposes only; it does NOT
    create a DOM ancestor relationship.

- timestamp: 2026-04-27T14:12:00Z
  checked: app_v2/templates/browse/_filter_bar.html lines 33-45
  found: |
    Swap-axes checkbox:
      <input type="checkbox" id="browse-swap-axes" name="swap" value="1"
             form="browse-filter-form"
             hx-post="/browse/grid"
             hx-include="#browse-filter-form input[name='platforms']:checked,
                          #browse-filter-form input[name='params']:checked,
                          #browse-swap-axes:checked"
             hx-trigger="change">
  implication: |
    The Swap-axes checkbox ITSELF has form="browse-filter-form". The HTMX source (dn() function
    in htmx.min.js) for non-GET requests calls Nt(triggeringElement) = element.form, which
    resolves to the form element via the form= DOM property. It then calls fn() on that form
    element. fn() checks instanceof HTMLFormElement and iterates form.elements — which DOES
    include all form-associated inputs (including those with form="browse-filter-form").
    This is how Swap-axes successfully submits the checked platform/param checkboxes.

- timestamp: 2026-04-27T14:18:00Z
  checked: app_v2/static/vendor/htmx/htmx.min.js — function dn() (getInputValues)
  found: |
    function dn(e, t) {
      ...
      if(t !== "get") { fn(n, o, i, Nt(e), l) }  // Nt(e) = e.form || closest("form")
      fn(n, r, i, e, l);
      ...
      const u = ve(e, "hx-include");
      ie(u, function(e) {
        fn(n, r, i, ue(e), l);  // process the resolved element
        if(!h(e, "form")) {
          ie(p(e).querySelectorAll(ot), function(e) { fn(n, r, i, e, l) });
        }
      });
      ...
    }
    And fn():
    if(e instanceof HTMLFormElement) {
      ie(e.elements, function(e) {...}); // form.elements RESPECTS form= attribute
      new FormData(e).forEach(...)
    }
  implication: |
    The triggering element's associated form (via .form DOM property) is auto-included for
    non-GET requests. The Apply button (<button type="button">) has no form= attribute and
    no ancestor <form> element in its DOM tree, so Nt(Apply) = null → no form auto-included.
    The Swap-axes checkbox has form="browse-filter-form", so Nt(Swap) = form#browse-filter-form
    → form.elements iterates ALL form-associated inputs → checked platforms/params are included.

- timestamp: 2026-04-27T14:22:00Z
  checked: app_v2/services/browse_service.py lines 111-127 (build_view_model)
  found: |
    is_empty = (not selected_platforms) or (not selected_param_labels)
    if is_empty or db is None:
        return BrowseViewModel(..., is_empty_selection=True, ...)
  implication: |
    When Apply POST arrives with no platforms/params (empty body), is_empty=True and the
    service correctly returns empty-state. This confirms the bug is upstream in the HTMX
    form serialization layer, not in the service logic.

- timestamp: 2026-04-27T14:25:00Z
  checked: popover-search.js onDropdownHide (lines 51-64)
  found: |
    onDropdownHide checks root.dataset.applied === '1' to decide whether to restore.
    onApplyClick sets root.dataset.applied = '1' before HTMX fires.
    So the checkbox state IS preserved (not restored) after Apply click.
  implication: |
    The checkboxes remain checked after Apply click. This is why Swap-axes, fired second,
    finds the checkboxes still checked. But the HTMX mechanism for Swap-axes (not Apply) is
    what actually captures them — via form.elements through the form= attribute on the
    triggering checkbox.

## Resolution

root_cause: |
  The Apply button in _picker_popover.html (line 79-86) is a <button type="button"> with no
  form= attribute and no ancestor <form> element in its DOM tree. Its hx-include uses the
  CSS selector "#browse-filter-form input:checked", which is a descendant combinator evaluated
  via document.querySelectorAll(). Because the checkboxes are DOM children of .dropdown-menu
  elements (not DOM children of #browse-filter-form), this selector returns ZERO elements.

  In contrast, the Swap-axes checkbox has form="browse-filter-form". HTMX's dn() function
  (getInputValues) for non-GET requests calls Nt(triggeringElement) = element.form, which
  resolves to the form element via the HTML form ownership property. fn() then processes the
  form element and, detecting instanceof HTMLFormElement, iterates form.elements — which the
  browser DOM populates with ALL form-associated controls including those linked via the form=
  attribute. This gives Swap-axes access to all checked platform/param checkboxes.

  The fix direction: give the Apply button a way to iterate form.elements rather than the
  descendant-selector path. Options:
  1. Add form="browse-filter-form" to the Apply button — HTMX will then auto-include the
     form's associated controls for the non-GET request (same path as Swap-axes).
  2. Change hx-include to "#browse-filter-form" (select the form element itself) — HTMX's
     fn() then processes it as HTMLFormElement and iterates form.elements.
  Both options correctly capture the form-associated checkboxes without requiring them to be
  DOM descendants of the form.

fix: |
  [pending diagnosis — owned by gap-closure planner]

verification: |
  [pending]

files_changed: []
