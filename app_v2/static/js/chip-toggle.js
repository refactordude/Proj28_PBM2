/* Phase 4 — UI Foundation: chip-toggle helper (D-UIF-04, sibling of popover-search.js).
 *
 * Click on `.pop .opt` toggles the `.on` class on the chip and syncs
 * the associated hidden <input>'s submission state. Does NOT submit the
 * form; the popover's Apply button is responsible for submission.
 *
 * Click on `[data-action="reset"]` (typically the "Reset" link in
 * .pop-head and the ghost button in .foot) clears every `.opt.on`,
 * disables every hidden input, and zeroes every date input within the
 * enclosing `.pop`. (WR-02 fix.)
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
 *
 * OFF-state semantics (WR-04 fix): when a chip is OFF the associated
 * hidden input is `disabled` (so the browser excludes it from the form
 * submission) instead of having its value cleared to ''. The previous
 * "value = ''" approach silently dropped chips whose legitimate value
 * happened to be empty and was indistinguishable from "no chip ever
 * existed" on the server side. The form-decoder now sees presence vs
 * absence, not '' vs ''. FilterOption.value is also constrained to
 * non-empty in filter_spec.py as a belt-and-braces validation.
 */
(function () {
  "use strict";

  function findHiddenForChip(opt) {
    var chipValue = opt.dataset.value || '';
    // Try nested input first; fall back to data-opt sibling lookup.
    var hidden = opt.querySelector('input[type=hidden]');
    if (!hidden && opt.parentElement) {
      hidden = opt.parentElement.querySelector(
        'input[type=hidden][data-opt="' + chipValue + '"]'
      );
    }
    return hidden;
  }

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
    // into the hidden input and ENABLE submission. When OFF, DISABLE the
    // input so the browser excludes it from the form payload entirely
    // (WR-04 fix — robust against legitimate empty-string values, and
    // distinguishes "no chip selected" from "chip selected with empty
    // value" on the server).
    var chipValue = opt.dataset.value || '';
    var hidden = findHiddenForChip(opt);
    if (hidden) {
      if (isOn) {
        hidden.value = chipValue;
        hidden.disabled = false;
      } else {
        hidden.disabled = true;
      }
    }
  }

  function onResetClick(e) {
    var btn = e.target.closest('[data-action="reset"]');
    if (!btn) return;
    var pop = btn.closest('.pop');
    if (!pop) return;
    // Skip resets inside the existing checkbox-list popover-search-root
    // for the same reason onChipClick does (D-UI2-09 byte-stable).
    if (btn.closest('.popover-search-root')) return;

    e.preventDefault();
    pop.querySelectorAll('.opt.on').forEach(function (o) {
      o.classList.remove('on');
    });
    // WR-04 fix: disable hidden inputs (don't just clear values) so the
    // browser excludes them from submission, regardless of any legitimate
    // empty-string value a chip may carry.
    pop.querySelectorAll('input[type=hidden][data-opt]').forEach(function (i) {
      i.disabled = true;
    });
    pop.querySelectorAll('input[type=date]').forEach(function (i) {
      i.value = '';
    });
  }

  document.addEventListener('click', onChipClick, true);
  document.addEventListener('click', onResetClick, true);
})();
