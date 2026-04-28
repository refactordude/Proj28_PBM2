/* popover-search.js — Browse popover-checklist (D-09, D-10, D-14).
 *
 * D-15 (amended 2026-04-28) + D-15a — close-event taxonomy.
 *
 * The picker popover supports TWO close-completion paths:
 *
 *   (1) IMPLICIT APPLY — commit the current checkbox state.
 *       Triggered by: outside-click on the page; click on the OTHER
 *       picker's trigger button; click on the Swap-axes toggle / Clear-all
 *       link; Tab-away (focusout to a non-popover element); browser-tab
 *       blur; programmatic bootstrap.Dropdown.hide(). Distinguishing
 *       feature: hide.bs.dropdown fires WITHOUT dataset.cancelling=1.
 *       Implementation: programmatically click the popover's Apply
 *       button (popoverApplyBtn.click()) so the SAME HTMX wiring used
 *       by explicit Apply runs — gap-2 form-association
 *       (form="browse-filter-form") + gap-3 picker_badges_oob OOB swap
 *       both fire automatically. Hand-rolling a second hx-post here
 *       would create two divergent code paths; programmatic click
 *       eliminates that risk.
 *
 *   (2) EXPLICIT CANCEL — revert to data-original-selection.
 *       Triggered by: Escape key only. Distinguishing feature: a
 *       document-level keydown listener (capture phase) sets
 *       dataset.cancelling="1" BEFORE Bootstrap fires hide.bs.dropdown.
 *       onDropdownHide reads-and-deletes the flag and branches to the
 *       revert path. Bootstrap's hide.bs.dropdown event payload
 *       (e.clickEvent) is non-null on outside-click but null on BOTH
 *       Esc AND programmatic close — so e.clickEvent alone cannot
 *       distinguish those two; the keydown trick is the canonical
 *       workaround.
 *
 *   (3) NO-OP SHORT-CIRCUIT — close without committing OR reverting.
 *       Triggered when: popover closes (any path) AND the current
 *       sorted-checked-values array deep-equals data-original-selection.
 *       Skips the implicit-Apply HTMX request entirely (no DB
 *       round-trip on stray opens that didn't change state).
 *       Sets dataset.applied="1" to prevent the cancel branch from
 *       firing too — but does NOT click Apply.
 *
 * No visual cue distinguishes implicit-Apply from explicit-Apply
 * (D-15a explicit). The trigger badge update (picker_badges_oob,
 * gap-3) and the grid swap are the affordance.
 *
 * Refs: 04-CONTEXT.md D-09 (data-bs-auto-close="outside" precondition),
 *       D-14 (Apply contract — closes popover, updates badge, single
 *       hx-post grid swap), D-15 amended, D-15a close-event taxonomy.
 * Bootstrap docs: getbootstrap.com/docs/5.3/components/dropdowns#events
 */
(function () {
  "use strict";

  function onInput(e) {
    if (!e.target.matches('.popover-search-input')) return;
    var root = e.target.closest('.popover-search-root');
    if (!root) return;
    var q = e.target.value.toLowerCase();
    root.querySelectorAll('.popover-search-list > li').forEach(function (li) {
      var label = (li.dataset.label || '').toLowerCase();
      li.style.display = label.indexOf(q) !== -1 ? '' : 'none';
    });
  }

  function onCheckboxChange(e) {
    if (!e.target.matches('.popover-search-root input[type="checkbox"]')) return;
    var root = e.target.closest('.popover-search-root');
    if (!root) return;
    var count = root.querySelectorAll('input[type="checkbox"]:checked').length;
    var badge = root.querySelector('.popover-apply-count');
    if (badge) badge.textContent = count;
  }

  function onClearClick(e) {
    if (!e.target.matches('.popover-clear-btn')) return;
    var root = e.target.closest('.popover-search-root');
    if (!root) return;
    // D-15: Clear empties checkboxes ONLY; never fires HTMX. The user must
    // still click Apply (or trigger an implicit-Apply close path) to commit.
    root.querySelectorAll('input[type="checkbox"]').forEach(function (cb) {
      cb.checked = false;
      cb.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }

  function onDropdownShow(e) {
    var root = e.target.querySelector ? e.target.querySelector('.popover-search-root') : null;
    if (!root) return;
    // D-15: stash sorted current selection so close-without-Apply can
    // (a) detect no-op short-circuit (D-15a) and (b) revert on Esc.
    var checked = Array.prototype.slice.call(
      root.querySelectorAll('input[type="checkbox"]:checked')
    ).map(function (cb) { return cb.value; });
    // Stash AS-CHECKED. The deep-equality check sorts both sides at
    // comparison time so the order of toggling doesn't fool it.
    root.dataset.originalSelection = JSON.stringify(checked);
    // D-09: focus search input. show.bs.dropdown fires before visible — defer.
    setTimeout(function () {
      var input = root.querySelector('.popover-search-input');
      if (input) input.focus();
    }, 0);
  }

  // D-15a no-op short-circuit support: deep-equal the current checked
  // values against the stashed originalSelection (both sorted at
  // comparison time so order of toggling doesn't matter).
  function _selectionsEqual(currentArr, originalJsonStr) {
    var original;
    try { original = JSON.parse(originalJsonStr || '[]'); }
    catch (err) { return false; }
    if (!Object.prototype.toString.call(original) === '[object Array]') return false;
    if (!original || typeof original.length !== 'number') return false;
    if (currentArr.length !== original.length) return false;
    var a = currentArr.slice().sort();
    var b = original.slice().sort();
    for (var i = 0; i < a.length; i++) {
      if (a[i] !== b[i]) return false;
    }
    return true;
  }

  // D-15a explicit-cancel detection — set dataset.cancelling="1" on Esc
  // BEFORE Bootstrap's hide.bs.dropdown fires. Capture phase is required
  // because Bootstrap may stop propagation on its own keydown listener.
  function onKeydown(e) {
    if (e.key !== 'Escape') return;
    // Bootstrap closes the OPEN dropdown nearest to the focused element.
    // In our markup, .dropdown-menu IS .popover-search-root (line 43 of
    // _picker_popover.html sets both classes on the same element). Find
    // the currently-open one — there is at most one open at a time
    // because Bootstrap closes others on outside-click.
    var openMenu = document.querySelector('.dropdown-menu.show.popover-search-root');
    if (openMenu) openMenu.dataset.cancelling = '1';
  }

  function onDropdownHide(e) {
    var root = e.target.querySelector ? e.target.querySelector('.popover-search-root') : null;
    if (!root) return;

    // (i) Explicit Apply already ran — onApplyClick set dataset.applied=1.
    // The HTMX request is firing; do not double-process. Clear the flag
    // for the next open cycle and exit.
    if (root.dataset.applied === '1') {
      delete root.dataset.applied;
      delete root.dataset.cancelling;  // defensive: ignore any stray Esc-flag
      return;
    }

    // (ii) D-15a EXPLICIT CANCEL — Esc was pressed; revert from stash.
    if (root.dataset.cancelling === '1') {
      delete root.dataset.cancelling;
      var original = JSON.parse(root.dataset.originalSelection || '[]');
      var set = {};
      for (var i = 0; i < original.length; i++) set[original[i]] = true;
      root.querySelectorAll('input[type="checkbox"]').forEach(function (cb) {
        cb.checked = !!set[cb.value];
      });
      var badge = root.querySelector('.popover-apply-count');
      if (badge) badge.textContent = original.length;
      return;
    }

    // (iii) D-15a NO-OP SHORT-CIRCUIT — selection unchanged. Skip the
    // implicit-Apply HTMX request. Set dataset.applied=1 so any
    // straggling cancel-handler logic short-circuits too.
    var current = Array.prototype.slice.call(
      root.querySelectorAll('input[type="checkbox"]:checked')
    ).map(function (cb) { return cb.value; });
    if (_selectionsEqual(current, root.dataset.originalSelection)) {
      root.dataset.applied = '1';
      // Marker — branch (i) on the NEXT close cycle clears it.
      return;
    }

    // (iv) D-15a IMPLICIT APPLY — click the Apply button programmatically.
    // The click triggers onApplyClick (sets dataset.applied=1) AND HTMX's
    // hx-post=/browse/grid AND the existing hx-on:click=...hide() (no-op
    // since dropdown is already closing). Bootstrap.Dropdown.hide() is
    // idempotent so the inline hide() call is safe even mid-hide-cycle.
    // This path inherits gap-2 (form="browse-filter-form" auto-include)
    // and gap-3 (picker_badges_oob OOB swap on response).
    var applyBtn = root.querySelector('.popover-apply-btn');
    if (applyBtn) applyBtn.click();
  }

  function onApplyClick(e) {
    if (!e.target.matches('.popover-apply-btn, .popover-apply-btn *')) return;
    var root = e.target.closest('.popover-search-root');
    if (root) root.dataset.applied = '1';
    // HTMX fires from hx-post on the button; Bootstrap dropdown closes via hx-on:click.
  }

  document.addEventListener('input',  onInput,            true);
  document.addEventListener('change', onCheckboxChange,   true);
  document.addEventListener('click',  onClearClick,       true);
  document.addEventListener('click',  onApplyClick,       true);
  document.addEventListener('keydown', onKeydown,         true);  // D-15a — must be capture-phase to set dataset.cancelling before Bootstrap's own listeners
  document.addEventListener('show.bs.dropdown',   onDropdownShow);
  document.addEventListener('hidden.bs.dropdown', onDropdownHide);
})();
