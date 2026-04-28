/* popover-search.js — Browse popover-checklist (D-09, D-10, D-15b).
 *
 * D-15b (gap-5 closure 2026-04-28) — auto-commit on each checkbox change with
 * 250ms client-side debounce. The <ul class="popover-search-list"> in
 * _picker_popover.html carries hx-post / hx-target / hx-swap / hx-trigger=
 * "change changed delay:250ms"; bubbling change events from inner checkboxes
 * fire a single debounced POST. There is NO Apply button — D-14, D-15, D-15a
 * are superseded.
 *
 * This script handles only the two surfaces HTMX cannot:
 *   (1) onInput  — client-side substring filter on the search box (D-10).
 *   (2) onClearClick — popover Clear button unchecks all in this picker.
 *       The dispatched bubbling 'change' events are picked up by HTMX's
 *       hx-trigger on the <ul>, so a single debounced commit fires.
 *
 * Bootstrap dropdown lifecycle events (show/hide) are no longer wired —
 * with auto-commit there is no commit/cancel distinction; all close paths
 * are equivalent (just close the popover). data-bs-auto-close="outside"
 * (D-09) keeps the popover open across multiple toggles for ergonomics.
 *
 * Refs: 04-CONTEXT.md D-09, D-10, D-15b. The form-association from gap-2
 * (form="browse-filter-form" on each checkbox) and the trigger-badge OOB
 * swap from gap-3 (picker_badges_oob in index.html) continue to work
 * unchanged — HTMX's auto-include of form-associated inputs handles the
 * payload; the route's block_names list emits the badge OOB fragment on
 * every response.
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

  function onClearClick(e) {
    if (!e.target.matches('.popover-clear-btn')) return;
    var root = e.target.closest('.popover-search-root');
    if (!root) return;
    // D-15b: uncheck all in this picker. Each dispatched 'change' event
    // bubbles to the <ul class="popover-search-list">, where HTMX's
    // hx-trigger="change changed delay:250ms" debounces them into a
    // single POST /browse/grid that commits the empty selection for
    // this picker (other picker's selection preserved via form-association).
    root.querySelectorAll('input[type="checkbox"]').forEach(function (cb) {
      if (cb.checked) {
        cb.checked = false;
        cb.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });
  }

  document.addEventListener('input', onInput,      true);
  document.addEventListener('click', onClearClick, true);
})();
