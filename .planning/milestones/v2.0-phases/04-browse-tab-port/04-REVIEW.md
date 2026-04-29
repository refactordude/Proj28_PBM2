---
phase: 04-browse-tab-port
reviewed: 2026-04-28T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - app_v2/routers/browse.py
  - app_v2/services/browse_service.py
  - app_v2/static/js/popover-search.js
  - app_v2/templates/browse/_empty_state.html
  - app_v2/templates/browse/_filter_bar.html
  - app_v2/templates/browse/_grid.html
  - app_v2/templates/browse/_picker_popover.html
  - app_v2/templates/browse/_warnings.html
  - app_v2/templates/browse/index.html
  - tests/v2/test_browse_service.py
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-04-28T00:00:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Reviewed all 10 files in scope at standard depth, with extra attention to the gap-3
closure (Plan 04-06) changes in `_picker_popover.html`, `index.html`, and
`routers/browse.py` that introduce the `picker_badges_oob` OOB-swap fragment.

**Plan 04-06 verdict:** the gap-3 fix is correct and well-architected. The
always-emit-with-`d-none` pattern for OOB swap targets is the right call (a
conditional emit would re-introduce the original bug on non-empty -> empty
transitions), the new top-level Jinja block mirrors the established
`count_oob` pattern verbatim, and the regression tests cover both the populated
and the empty-selection paths. No issues found in the 04-06 diff itself.

The findings below are pre-existing latent issues in the broader Phase 4 code
that were either not addressed by 04-06 (and were out of scope for it) or are
small style/quality items. The most material item is **WR-01** (NaN cells
render as the string `"nan"` instead of being treated as empty by the CSS
`td:empty::after` em-dash pseudo-element) and **WR-02** (the swap-axes toggle
preserves the same defective `hx-include` CSS-descendant selector pattern that
caused gap-2 on the Apply button — currently masked by the `form=` attribute,
but a latent regression vector).

## Warnings

### WR-01: Pivot NaN cells render as literal `"nan"` text — CSS em-dash never engages

**File:** `app_v2/templates/browse/_grid.html:41-43`

**Issue:** Cells use the Jinja test `row[col] is not none` to decide between the
escaped value and the empty string:

```jinja2
<td>{{ row[col] | string | e if row[col] is not none else "" }}</td>
```

`pivot_to_wide_core` (in `app/services/ufs_service.py:266-272`) calls
`df_long.pivot_table(aggfunc="first")` with no `fill_value` and no post-`fillna`
step. For any sparse (PLATFORM_ID, Item) combination — common in EAV data where
not every platform reports every parameter — pandas inserts `float('nan')` into
the cell. In Jinja2, `nan is not none` is **True** (NaN is not the singleton
`None`), so the branch falls through to `nan | string | e`, which renders the
literal text `"nan"` in the grid.

The header comment block in `_grid.html:18-22` explicitly states the contract:

> None values render empty; the `.pivot-table td:empty::after` CSS pseudo-element
> injects an em-dash (per UI-SPEC §"Phase 04 additions").

That contract is breached for any sparse cell because `td:empty` only matches
truly empty `<td></td>` elements — a `<td>nan</td>` will never trigger the
pseudo-element. End users will see a grid with literal `nan` strings interspersed
between real values, with no em-dash placeholder.

**Fix:** Treat both `None` and pandas-style missing values as empty. Two
equivalent options:

```jinja2
{# Option A: add a NaN guard in the Jinja test #}
<td>{{ row[col] | string | e if row[col] is not none and row[col] == row[col] else "" }}</td>
```

(NaN is the only float for which `x == x` is False.)

```python
# Option B (preferred — single source of truth): fillna in pivot_to_wide_core
wide = df_long.pivot_table(...).where(lambda d: d.notna(), other=None)
# or
wide = wide.astype(object).where(wide.notna(), None)
```

Option B normalizes NaN -> None at the data boundary so every consumer (template,
CSV export, future Ask tab) sees the same shape. Add a regression test that
asserts a sparse cell renders as empty `<td></td>` (or with the em-dash via
the rendered CSS) and not as `<td>nan</td>`.

---

### WR-02: Swap-axes toggle uses the same broken `hx-include` selector pattern that caused gap-2 (latent regression)

**File:** `app_v2/templates/browse/_filter_bar.html:33-44`

**Issue:** The swap-axes checkbox carries:

```html
<input ... id="browse-swap-axes" name="swap" form="browse-filter-form"
       hx-post="/browse/grid"
       hx-include="#browse-filter-form input[name='platforms']:checked,
                   #browse-filter-form input[name='params']:checked,
                   #browse-swap-axes:checked"
       hx-target="#browse-grid" hx-trigger="change">
```

The `hx-include` selectors are CSS **descendant** selectors rooted at
`#browse-filter-form`. But `#browse-filter-form` is the empty `<form>` declared
inline at `index.html:42` (a sibling of `.browse-filter-bar`); the picker
checkboxes live inside Bootstrap dropdown menus that are **not** DOM descendants
of that form (they are descendants of `.browse-filter-bar` instead). The picker
checkboxes are only associated with the form via the HTML5 `form="browse-filter-form"`
attribute on each `<input type="checkbox">`.

This is the **exact** root cause of gap-2 on the Apply button (see `04-05-SUMMARY.md`
and `04-HUMAN-UAT.md` gap-2): a CSS-descendant selector returns 0 elements
because form-association is not the same as DOM-descendant. Plan 04-05 fixed the
Apply button by replacing the broken `hx-include` with `form="browse-filter-form"`
and relying on HTMX's `element.form` -> `form.elements` auto-include path.

Currently the swap-axes toggle works because it ALSO has `form="browse-filter-form"`
on line 38, which makes HTMX's auto-include path pick up the form-associated
checkboxes. The `hx-include` line is therefore dead (matches 0 elements) but
silently masked. If a future refactor drops the `form=` attribute thinking
`hx-include` covers it, swap-axes will silently break in the same way Apply did
in gap-2. The dead `hx-include` is also misleading documentation of intent for
future readers.

**Fix:** Drop the `hx-include` entirely; rely on `form="browse-filter-form"` +
HTMX's auto-include of `element.form` (the same fix shape as gap-2 on the Apply
button). Add an inline comment explaining the form-association contract so a
future maintainer does not re-introduce `hx-include`:

```html
{# Swap-axes toggle (D-16): immediate fire on change, NO Apply needed.
   Form-association via form="browse-filter-form" is the ONLY mechanism that
   includes the form-associated picker checkboxes in the POST body —
   hx-include CSS-descendant selectors do NOT match form-associated inputs
   that are not DOM descendants (gap-2 root cause; see 04-05-SUMMARY.md). #}
<input type="checkbox" id="browse-swap-axes" name="swap" value="1"
       form="browse-filter-form"
       {% if vm.swap_axes %}checked{% endif %}
       hx-post="/browse/grid"
       hx-target="#browse-grid"
       hx-swap="innerHTML swap:200ms"
       hx-trigger="change"
       aria-label="Swap axes (rows and columns)">
```

Add a regression test parallel to `test_apply_button_carries_form_attribute` that
asserts (a) `form="browse-filter-form"` is present on `#browse-swap-axes`, and
(b) the broken `hx-include="#browse-filter-form input..."` pattern is absent.

---

### WR-03: Trigger button `aria-label` becomes stale after OOB badge swap

**File:** `app_v2/templates/browse/_picker_popover.html:33-41`

**Issue:** The trigger button carries:

```html
<button ... id="picker-{{ name }}-trigger"
        aria-label="Select {{ label | lower }}{% if selected %} ({{ selected | length }} selected){% endif %}">
  {{ label }}
  <span id="picker-{{ name }}-badge" class="badge ...">{{ selected | length }}</span>
  ...
</button>
```

The badge `<span>` is now updated atomically via the new `picker_badges_oob`
OOB swap (Plan 04-06), which is correct. But the button's own `aria-label`
is **not** an OOB target — it is rendered once on GET and never refreshed.
After the user clicks Apply with a different selection count, the visible
badge updates ("3" -> "5") but the screen-reader-announced label remains
"Select platforms (3 selected)". Same drift can take the label from
"(3 selected)" all the way to no-suffix-at-all when Clear-all goes to 0,
without any audible change.

This is an accessibility regression specifically introduced by the partial-DOM
update pattern: the OOB-mergeable element (the badge) drifts from the
non-OOB element that documents it (the button label). The badge already has
`aria-live="polite"` (good — screen readers will announce the count), so
the button label is somewhat redundant; but the redundancy is now actively
wrong rather than belt-and-suspenders.

**Fix:** Two equivalent options. Preferred:

Option A — drop the `(N selected)` suffix from the button `aria-label` and
rely entirely on the badge's `aria-live="polite"` to announce changes:

```html
<button ...
        aria-label="Select {{ label | lower }}"
        aria-describedby="picker-{{ name }}-badge">
```

Option B — emit the button label itself as a third OOB target (more invasive;
requires the button to be re-rendered, not just the badge). Skip unless A is
unacceptable for some reason.

Add a regression test asserting that POST /browse/grid does NOT mutate the
button-level `aria-label` and that the label does not embed a stale count
suffix.

## Info

### IN-01: `db` parameter is untyped in `build_view_model` (loses static type guarantees)

**File:** `app_v2/services/browse_service.py:79`

**Issue:** The signature is:

```python
def build_view_model(
    db,
    db_name: str,
    selected_platforms: list[str],
    ...
```

The body branches on `if db is None:` (line 97) and otherwise calls
`list_platforms(db, db_name=db_name)` etc., so the function clearly accepts
`DBAdapter | None`. The router (`browse.py:32-38`) is correctly typed
(`def get_db(request: Request) -> DBAdapter | None`), but the service-layer
function loses the type annotation at the call site. mypy / ruff will not
catch a future caller passing the wrong shape (e.g., a `str` from a misplaced
refactor).

**Fix:** Annotate explicitly to match the router contract:

```python
from app.adapters.db.base import DBAdapter

def build_view_model(
    db: DBAdapter | None,
    db_name: str,
    ...
```

---

### IN-02: `Form()` defaults use `= []` mutable-default form rather than `default_factory`

**File:** `app_v2/routers/browse.py:92-94`

**Issue:** The POST handler uses:

```python
def browse_grid(
    request: Request,
    platforms: Annotated[list[str], Form()] = [],
    params: Annotated[list[str], Form()] = [],
    swap: Annotated[str, Form()] = "",
    ...
```

The GET handler at lines 62-63 uses the canonical Pydantic v2 idiom
`Annotated[list[str], Query(default_factory=list)]` and the inline comment
57-61 explicitly explains why mutable defaults are unsafe with Pydantic v2.
The POST handler then turns around and uses `= []`. This works in practice
because FastAPI's `Form()` dependency machinery instantiates a fresh list per
request rather than sharing the literal — but the inconsistency invites a
future maintainer to mis-port the pattern, and a static analyzer
(`ruff B006 mutable-argument-default`) will flag both lines.

**Fix:** Use the same `default_factory=list` form as the GET handler for
consistency and to silence ruff:

```python
platforms: Annotated[list[str], Form(default_factory=list)],
params: Annotated[list[str], Form(default_factory=list)],
swap: Annotated[str, Form()] = "",
```

---

### IN-03: `selected_platforms` is not de-duplicated, while `infocategories` and `items` are

**File:** `app_v2/services/browse_service.py:134-144`

**Issue:** When constructing the SQL filter tuples:

```python
infocategories = tuple(sorted({p[0] for p in parsed}))  # de-duped + sorted
items = tuple(sorted({p[1] for p in parsed}))            # de-duped + sorted
df_long, row_capped = fetch_cells(
    db,
    tuple(selected_platforms),  # NOT de-duped, NOT sorted
    infocategories,
    items,
    ...
)
```

A URL like `?platforms=A&platforms=A&params=cat%20%C2%B7%20i` will pass
`("A", "A")` to `fetch_cells`, which then becomes a duplicate IN-clause
binding (`PLATFORM_ID IN ('A', 'A')`) and — more importantly — produces
a DIFFERENT cache key from the canonical `("A",)` form, halving cache
effectiveness for any user who ends up with a duplicated query string.
Test 7 (`test_build_view_model_fetch_cells_args` at
`test_browse_service.py:142-157`) actually documents this: it passes
`["P2", "P1"]` and asserts the call receives `("P2", "P1")` unsorted.

This is not a security or correctness bug (SQL bind via `expanding=True`
handles duplicates safely), but it is a cache-stability and consistency
gap with the param tuples.

**Fix:** Apply the same dedup+sort to platforms:

```python
df_long, row_capped = fetch_cells(
    db,
    tuple(sorted(set(selected_platforms))),
    infocategories,
    items,
    row_cap=ROW_CAP,
    db_name=db_name,
)
```

Then update Test 7 to assert the sorted form. This also means the
URL round-trip `_build_browse_url` round-trips to a canonical (sorted) form
across cache reads, which is desirable for a shared-team intranet app.

If preserving user-visible URL order matters (it does not for D-30 — D-30
only specifies repeated keys, not order), keep the URL composition as-is
and only canonicalize for the SQL/cache layer.

---

### IN-04: `popover-search.js` reads `data-original-selection` JSON without try/catch

**File:** `app_v2/static/js/popover-search.js:55-57`

**Issue:** `onDropdownHide` reads:

```js
var original = JSON.parse(root.dataset.originalSelection || '[]');
```

The dataset is set by the same module on line 43, so under normal operation
the JSON is well-formed. But if any third party (a browser extension, a
future feature, a misbehaving HTMX swap that mutates the popover root) ever
writes a non-JSON string into `data-original-selection`, `JSON.parse` will
throw a `SyntaxError` and the dropdown-hide handler will abort
mid-restore — leaving the popover in a partially restored state. Not a real
bug today, but minor defense-in-depth.

**Fix:**

```js
var original = [];
try {
  original = JSON.parse(root.dataset.originalSelection || '[]');
} catch (_e) {
  original = [];
}
```

---

### IN-05: Browse page `<title>` is not differentiated; `vm.is_empty_selection` ternary repeats inside template

**File:** `app_v2/templates/browse/index.html:33-35, 73-77, 95-96`

**Issue:** The `if not vm.is_empty_selection` count expression is duplicated
verbatim in two places (the inline `#grid-count` span at line 33-35 and the
OOB block at line 74-76). Three tweaks worth doing in a small follow-up:

1. Hoist the count text into a Jinja variable at the top of the body block:

   ```jinja2
   {% set count_text = ('%d platforms × %d parameters' % (vm.n_rows, vm.n_cols)) if not vm.is_empty_selection else '' %}
   ```

   Then both `#grid-count` spans render `{{ count_text }}` — a single source
   of truth that prevents the two spans from drifting (e.g., one using
   `&times;` and the other using a different separator). Use the HTML entity
   `&times;` via `| safe` only after escaping the integer parts, or render the
   integers and use `&#215;` directly in the template for clarity.

2. The `<title>` is currently just "Browse" (set via `page_title` in the
   route context). Consider including the active selection count when present
   so multi-tab users can distinguish open Browse views — minor UX, low
   priority.

3. Consider a comment near the OOB block linking back to the in-place span
   so they stay in sync; currently the block comment at lines 83-93 only
   describes the OOB merge target, not its sibling.

These are stylistic; no behavioral bug.

---

_Reviewed: 2026-04-28T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
