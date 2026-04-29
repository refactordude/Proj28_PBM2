# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## 260429-ask-tab-prompts-and-popover — Ask tab chips do nothing; Confirm parameters dropdown clipped
- **Date:** 2026-04-29
- **Error patterns:** onclick, tojson, double-quote, HTML attribute, chip, prompt, dropdown, clipped, popover, Popper, overflow hidden, starter chips, requestSubmit
- **Root cause:** (1) Chip onclick used `{{ prompt.question | tojson }}` inside a double-quoted HTML attribute; the tojson-emitted double-quotes terminated the attribute mid-expression, producing a broken handler the browser silently ignored. (2) Bootstrap Dropdown clipped by an overflow:hidden .panel ancestor; CSS :has() override was insufficient because Popper.js re-computes overflow from computed style at runtime.
- **Fix:** (1) Moved prompt text to `data-question="{{ prompt.question | e }}"` and read it via `this.dataset.question` in onclick — eliminates all quoting conflicts. (2) Added `data-bs-boundary="viewport"` to the dropdown toggle button, instructing Popper to use the viewport as clip boundary regardless of ancestor overflow state.
- **Files changed:** app_v2/templates/ask/_starter_chips.html, app_v2/templates/browse/_picker_popover.html
---

