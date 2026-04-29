/**
 * htmx-error-handler.js — INFRA-02
 *
 * By default HTMX silently discards responses with status >= 400. This handler
 * overrides that behavior: any 4xx/5xx response is swapped into
 * #htmx-error-container so validation errors and server errors are always
 * visible to users. See research/PITFALLS.md Pitfall 5.
 *
 * The handler attaches once at DOMContentLoaded — it survives subsequent HTMX
 * swaps because it is bound to document.body (the persistent shell), not to
 * any element that might be replaced.
 */
(function () {
  "use strict";

  function onBeforeSwap(evt) {
    var xhr = evt.detail && evt.detail.xhr;
    if (!xhr) return;
    if (xhr.status >= 400) {
      // Force HTMX to swap the response body despite the error status
      evt.detail.shouldSwap = true;
      evt.detail.isError = true;
      // Route the error response into the dedicated error container regardless
      // of the original hx-target. Prevents stale error text from lingering in
      // feature-specific targets (e.g. #overview-list) after the next success.
      // Guard against missing container (e.g. templates that don't extend base.html):
      // if null, HTMX falls back to the original hx-target — still visible, not silent.
      var errorContainer = document.getElementById("htmx-error-container");
      if (errorContainer) {
        evt.detail.target = errorContainer;
        // Force innerHTML swap regardless of the originating element's
        // hx-swap setting (typical forms use outerHTML, which would replace
        // the container itself and remove its id — a follow-up error swap
        // would then have nowhere to land). innerHTML places the fragment
        // INSIDE the container so its id survives across multiple errors.
        evt.detail.swapOverride = "innerHTML";
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      document.body.addEventListener("htmx:beforeSwap", onBeforeSwap);
    });
  } else {
    document.body.addEventListener("htmx:beforeSwap", onBeforeSwap);
  }
})();
