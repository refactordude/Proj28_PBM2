// app_v2/static/js/popover-search.js
//
// Picker popover client logic.
//
// D-08 / D-15 (amended) / D-15a (Phase 04, plan 04-07): close-event taxonomy.
//   The picker popover is a native <div popover>. It can close via four paths:
//
//     1. Explicit-Apply  → user clicks the [Apply] button.
//     2. Implicit-Apply  → user clicks outside the popover (light-dismiss).
//                          We programmatically click [Apply] on close.
//     3. Esc-Cancel      → user presses Escape. We mark the popover with
//                          dataset.cancelling = "1" before the browser closes
//                          it; on close we revert checkboxes to the snapshot
//                          taken at open and skip Apply.
//     4. No-op           → close (any path) when the current selection equals
//                          the snapshot taken at open. Skip Apply entirely.
//
//   Visual contract (D-08): no UI cue distinguishes implicit-Apply from
//   explicit-Apply. The grid + picker_badges_oob swap is the affordance.
//
//   Anchor: data-original-selection on the popover stores the JSON-encoded
//   selection at open time. Comparison is order-independent (sorted).

(function () {
  "use strict";

  /**
   * Read all currently checked checkbox values inside a popover, sorted.
   * Returns a JSON string for stable comparison.
   */
  function snapshotSelection(popover) {
    const checked = popover.querySelectorAll(
      'input[type="checkbox"][name="filter_value"]:checked'
    );
    const values = Array.from(checked, (cb) => cb.value);
    values.sort();
    return JSON.stringify(values);
  }

  /**
   * Restore checkbox state from a JSON snapshot string.
   * Used by Esc-Cancel to revert any in-popover changes the user made.
   */
  function restoreSelection(popover, snapshotJson) {
    let snapshot;
    try {
      snapshot = JSON.parse(snapshotJson);
    } catch (e) {
      return;
    }
    if (!Array.isArray(snapshot)) {
      return;
    }
    const wanted = new Set(snapshot);
    const all = popover.querySelectorAll(
      'input[type="checkbox"][name="filter_value"]'
    );
    all.forEach((cb) => {
      cb.checked = wanted.has(cb.value);
    });
  }

  /**
   * Wire up search filter, Esc-cancel listener, and toggle handler for one
   * popover. Idempotent: skips popovers already wired (data-popover-wired="1").
   */
  function wirePopover(popover) {
    if (popover.dataset.popoverWired === "1") {
      return;
    }
    popover.dataset.popoverWired = "1";

    // ---- search filter (existing behavior) -------------------------------
    const searchInput = popover.querySelector(".picker-search-input");
    const itemsContainer = popover.querySelector(".picker-items");
    if (searchInput && itemsContainer) {
      searchInput.addEventListener("input", function (ev) {
        const q = (ev.target.value || "").trim().toLowerCase();
        const labels = itemsContainer.querySelectorAll("label.picker-item");
        labels.forEach((label) => {
          const text = (label.textContent || "").toLowerCase();
          if (!q || text.indexOf(q) !== -1) {
            label.style.display = "";
          } else {
            label.style.display = "none";
          }
        });
      });
    }

    // ---- Esc-cancel: capture-phase keydown -------------------------------
    //
    // We use the capture phase so we observe the Escape press before the
    // browser dispatches the popover light-dismiss close. Setting
    // dataset.cancelling here is read by the toggle("closed") handler below
    // to differentiate Esc-Cancel from outside-click implicit-Apply.
    popover.addEventListener(
      "keydown",
      function (ev) {
        if (ev.key === "Escape") {
          popover.dataset.cancelling = "1";
        }
      },
      true // useCapture
    );

    // ---- toggle handler: snapshot on open, dispatch on close -------------
    popover.addEventListener("toggle", function (ev) {
      if (ev.newState === "open") {
        // Snapshot selection at open. Clear any stale cancelling flag.
        popover.dataset.originalSelection = snapshotSelection(popover);
        delete popover.dataset.cancelling;
        return;
      }

      if (ev.newState !== "closed") {
        return;
      }

      // ---- close path ---------------------------------------------------
      const original = popover.dataset.originalSelection;
      const cancelling = popover.dataset.cancelling === "1";

      // Always clear the cancelling flag for the next open cycle.
      delete popover.dataset.cancelling;

      if (cancelling) {
        // Esc-Cancel: revert checkbox state and skip Apply.
        if (typeof original === "string") {
          restoreSelection(popover, original);
        }
        return;
      }

      // No snapshot recorded (defensive): cannot determine if changed; skip.
      if (typeof original !== "string") {
        return;
      }

      const current = snapshotSelection(popover);
      if (current === original) {
        // No-op: selection unchanged → do not submit.
        return;
      }

      // Implicit-Apply: programmatically click the popover's Apply button.
      // The Apply button carries form="browse-filter-form" (gap-2 fix), so
      // its click submits the parent form via HTMX exactly like explicit-Apply.
      const applyBtn = popover.querySelector(".picker-apply");
      if (applyBtn) {
        applyBtn.click();
      }
    });
  }

  /**
   * Find every picker popover in the document and wire it.
   * Safe to call repeatedly; wiring is idempotent.
   */
  function wireAll(root) {
    const scope = root || document;
    const popovers = scope.querySelectorAll(".picker-popover[popover]");
    popovers.forEach(wirePopover);
  }

  // Initial wire on first load.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      wireAll(document);
    });
  } else {
    wireAll(document);
  }

  // Re-wire after HTMX swaps (the picker popover lives inside #filter-bar
  // which gets replaced when the filter bar is re-rendered).
  document.body.addEventListener("htmx:afterSwap", function (ev) {
    wireAll(ev.target || document);
  });
})();
