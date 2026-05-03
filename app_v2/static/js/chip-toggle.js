/* Phase 4 — UI Foundation: chip-toggle helper (D-UIF-04, sibling of popover-search.js).
 *
 * Click on `.pop .opt` toggles the `.on` class on the chip and syncs
 * the value of an associated hidden <input>. Does NOT submit the form;
 * the popover's Apply button is responsible for submission.
 *
 * Loaded with `defer` AFTER bootstrap.bundle.min.js in base.html
 * (Wave 3), mirroring the popover-search.js loading pattern.
 *
 * Pitfall 8 (RESEARCH.md): popover-search.js already uses document-level
 * click delegation. Both listeners coexist via PRECISE selectors:
 *   - popover-search.js binds inside `.popover-search-root` (the
 *     existing checkbox-list popover; D-UI2-09 byte-stable).
 *   - chip-toggle.js binds on `.pop .opt` and skips clicks that fall
 *     inside `.popover-search-root` (defense-in-depth: the existing
 *     popover does NOT use .opt markup, but the early-return makes
 *     the boundary explicit and audit-friendly).
 *
 * The associated hidden <input> is located by either:
 *   1. A child of the .opt button (rare — when the input is nested
 *      inside the button for tight DOM coupling).
 *   2. A sibling within the same `.opts` group with attribute
 *      `data-opt="<chip value>"` (the convention used by
 *      filters_popover.html).
 */
(function () {
  "use strict";

  function onChipClick(e) {
    var opt = e.target.closest('.pop .opt');
    if (!opt) return;
    // D-UI2-09 byte-stable: skip clicks inside the existing
    // checkbox-list popover-search-root. The chip-toggle popover
    // uses .pop without .popover-search-root.
    if (opt.closest('.popover-search-root')) return;

    e.preventDefault();
    opt.classList.toggle('on');

    var isOn = opt.classList.contains('on');
    // D-UIF-04 chip-value-as-payload: when ON, write the chip's data-value
    // into the hidden input (so the form submission carries the actual
    // category value); when OFF, clear the input. This diverges from
    // RESEARCH §Pitfall 8 sketch (which used '1') so that multi-option
    // groups submit a meaningful value per option, not a generic flag.
    var chipValue = opt.dataset.value || '';

    // Try nested input first; fall back to data-opt sibling lookup.
    var hidden = opt.querySelector('input[type=hidden]');
    if (!hidden && opt.parentElement) {
      hidden = opt.parentElement.querySelector(
        'input[type=hidden][data-opt="' + chipValue + '"]'
      );
    }
    if (hidden) {
      hidden.value = isOn ? chipValue : '';
    }
  }

  document.addEventListener('click', onChipClick, true);
})();
