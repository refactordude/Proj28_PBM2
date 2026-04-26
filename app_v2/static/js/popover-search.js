/* popover-search.js — Browse popover-checklist (D-10, D-14, D-15) */
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
    // D-15: Clear empties checkboxes ONLY; never fires HTMX.
    root.querySelectorAll('input[type="checkbox"]').forEach(function (cb) {
      cb.checked = false;
      cb.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }

  function onDropdownShow(e) {
    var root = e.target.querySelector ? e.target.querySelector('.popover-search-root') : null;
    if (!root) return;
    // D-15: stash so close-without-Apply can restore.
    var checked = Array.prototype.slice.call(
      root.querySelectorAll('input[type="checkbox"]:checked')
    ).map(function (cb) { return cb.value; });
    root.dataset.originalSelection = JSON.stringify(checked);
    // D-09: focus search input. show.bs.dropdown fires before visible — defer.
    setTimeout(function () {
      var input = root.querySelector('.popover-search-input');
      if (input) input.focus();
    }, 0);
  }

  function onDropdownHide(e) {
    var root = e.target.querySelector ? e.target.querySelector('.popover-search-root') : null;
    if (!root) return;
    if (root.dataset.applied === '1') { delete root.dataset.applied; return; }
    // D-15: restore original selection on close-without-Apply.
    var original = JSON.parse(root.dataset.originalSelection || '[]');
    var set = {};
    for (var i = 0; i < original.length; i++) set[original[i]] = true;
    root.querySelectorAll('input[type="checkbox"]').forEach(function (cb) {
      cb.checked = !!set[cb.value];
    });
    var badge = root.querySelector('.popover-apply-count');
    if (badge) badge.textContent = original.length;
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
  document.addEventListener('show.bs.dropdown',   onDropdownShow);
  document.addEventListener('hidden.bs.dropdown', onDropdownHide);
})();
