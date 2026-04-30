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

## 260430-browse-pivot-empty-row-labels — Browse pivot row-label column renders em-dash instead of values
- **Date:** 2026-04-30
- **Error patterns:** browse, pivot, row label, em-dash, dash, empty td, td:empty, ::after, PLATFORM_ID, Item, index column, missing values, empty string, external DB, demo SQLite, pivot_to_wide, is_missing, dropna
- **Root cause:** Empty `<td>` row-label cells get an em-dash via the CSS rule `.pivot-table td:empty::after { content: "\2014" }` (intended for missing value cells but matches index-column cells too). The Jinja template's defensive check `... is not none else ""` does not catch empty-string PLATFORM_ID/Item values, which pass through `| string | e` as `""` and produce empty `<td>`. External DBs store empty/whitespace PLATFORM_IDs that the in-repo demo SQLite seed doesn't have, so the bug only surfaces in production. The user's initial guess (`reset_index(drop=True)` in pivot_to_wide) was wrong — line 269 already calls `wide.reset_index()` without `drop=True`; the column exists, its values are just empty.
- **Fix:** In `app/services/ufs_service.py::pivot_to_wide`, filter rows where the index-column value is "missing" per the canonical `is_missing()` contract from `result_normalizer.py` (covers None, "", whitespace-only, and the documented MISSING_SENTINELS) BEFORE calling pivot_table. Logs a WARNING with dropped count. Symmetric for both swap_axes orientations. When all rows are missing, returns an empty wide DataFrame with `[index_col]` shape so the template renders an empty `<tbody>` rather than one row of em-dashes. Mirrors the pre-existing `list_platforms` `.dropna()` discipline so empty platforms are filtered uniformly across the picker AND the grid.
- **Files changed:** app/services/ufs_service.py, tests/services/test_ufs_service.py
---

