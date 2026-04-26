---
phase: 04-browse-tab-port
reviewed: 2026-04-26T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - app_v2/main.py
  - app_v2/routers/browse.py
  - app_v2/routers/root.py
  - app_v2/services/browse_service.py
  - app_v2/static/css/app.css
  - app_v2/static/js/popover-search.js
  - app_v2/templates/base.html
  - app_v2/templates/browse/_empty_state.html
  - app_v2/templates/browse/_filter_bar.html
  - app_v2/templates/browse/_grid.html
  - app_v2/templates/browse/_picker_popover.html
  - app_v2/templates/browse/_warnings.html
  - app_v2/templates/browse/index.html
  - tests/v2/test_browse_routes.py
  - tests/v2/test_browse_service.py
  - tests/v2/test_main.py
  - tests/v2/test_phase04_invariants.py
findings:
  critical: 0
  warning: 5
  info: 6
  total: 11
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-04-26
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

The Phase 4 Browse Tab Port is well-architected and security-aware. Notable strengths:

- SQL injection defense is correct in depth — service layer never builds SQL strings; parameterized binds happen in `fetch_cells_core` upstream; garbage labels are dropped via `_parse_param_label` before reaching SQL.
- XSS defense uses `| e` filter explicitly in addition to Jinja2 autoescape (belt-and-suspenders). Invariant test guards against `| safe` regression.
- HTMX OOB swap pattern, fragment vs full-page rendering, and `HX-Push-Url` round-trip are all correctly implemented and tested.
- Test coverage is thorough — invariant tests guard locked decisions (D-13 separator, D-19 export removal, D-34 sync def).

The findings below are concentrated around (a) two HTMX `hx-include` selectors that target descendants of an empty form (likely broken in browser even though tests pass because they bypass HTMX), (b) a Clear-all UX gap that resets server state without re-rendering the picker checkboxes, and (c) a few minor consistency / type-hint / test-assertion issues. No critical security or correctness bugs were found.

## Warnings

### WR-01: hx-include selectors target descendants of an empty form — likely broken under HTMX

**File:** `app_v2/templates/browse/_filter_bar.html:41` and `app_v2/templates/browse/_picker_popover.html:81`
**Issue:**
The empty form `<form id="browse-filter-form"></form>` (`index.html:42`) contains no DOM children. The picker checkboxes use the HTML `form="browse-filter-form"` attribute to *form-associate* but they are NOT DOM descendants of that form (they live inside `.dropdown-menu` elements in `.browse-filter-bar`).

The selectors used are descendant combinators:

- `_filter_bar.html:41`: `hx-include="#browse-filter-form input[name='platforms']:checked, #browse-filter-form input[name='params']:checked, #browse-swap-axes:checked"`
- `_picker_popover.html:81`: `hx-include="#browse-filter-form input:checked"`

A descendant combinator like `#browse-filter-form input` resolves via `document.querySelectorAll(...)`, which only matches DOM descendants — not form-associated controls reached via the `form=` attribute. HTMX's `hx-include` is a plain CSS selector list; it has no special handling that promotes descendant selectors into form-association lookups (HTMX only uses native FormData semantics when the *selector itself matches the form element*, e.g. `hx-include="#browse-filter-form"` or `hx-include="form"`).

If this analysis is correct, both the Swap-axes toggle and every popover Apply button would POST `platforms=[]` / `params=[]` regardless of the user's selection — falling into the empty-state branch on every action. The Phase 4 integration tests (`test_browse_routes.py`) do **not** catch this because they bypass HTMX entirely and POST form data manually via `_post_form_pairs`.

The accompanying comment "Pitfall 4 of 04-RESEARCH.md" suggests the author believed `form=` attribute association would resolve through descendant CSS selectors; this is not how CSS selectors work.

**Fix:**
Either change the selectors to target the form itself (so HTMX uses native FormData with form-association), or use an attribute selector that matches the `form=` attribute directly:

```html
<!-- Option A: target the form element itself -->
hx-include="#browse-filter-form"

<!-- Option B: select by form-association attribute (works regardless of DOM nesting) -->
hx-include="input[form='browse-filter-form'][name='platforms']:checked, input[form='browse-filter-form'][name='params']:checked, #browse-swap-axes"
```

Option B is closer to the existing intent (per-name filtering for the swap toggle) and is provably correct under any CSS selector engine. Add a Playwright/AppTest-style browser test that exercises a real HTMX click cycle to lock in the fix.

---

### WR-02: Clear-all does not reset picker checkbox state in the DOM

**File:** `app_v2/templates/browse/_filter_bar.html:54-64`
**Issue:**
The Clear-all link POSTs to `/browse/grid` with `hx-vals='{}'` and `hx-target="#browse-grid"`. The server returns the `grid`/`count_oob`/`warnings_oob` blocks only — the filter bar (including the checkboxes inside the dropdown menus) is **not** re-rendered. As a result, after Clear-all:

- The grid switches to empty-state (correct).
- The grid count caption clears (correct).
- But the popover checkboxes remain visually checked, and `popover-search.js` still has the previous `data-original-selection` stash.

If the user immediately re-opens a popover or hits Apply, the still-checked boxes will be re-submitted, undoing the clear. This is a real UX bug, not just cosmetic.

**Fix:**
Clear the popover checkboxes client-side when Clear-all fires. Two practical options:

```html
<!-- Option A: dispatch a custom event from Clear-all and have popover-search.js
     unselect all checkboxes on receipt -->
<a id="clear-all-link"
   hx-post="/browse/grid"
   hx-vals='{}'
   hx-target="#browse-grid"
   hx-on:click="document.querySelectorAll('input[form=browse-filter-form]').forEach(cb => cb.checked = false); document.getElementById('browse-swap-axes').checked = false;"
   ...>

<!-- Option B: also OOB-swap the filter bar from the server response. Requires
     adding a {% block filter_bar %} OOB block in index.html and including it
     in block_names for /browse/grid. -->
```

Option A is the smaller change. Option B keeps the server as the source of truth (preferred long-term).

---

### WR-03: Mutable default arguments on POST /browse/grid

**File:** `app_v2/routers/browse.py:92-94`
**Issue:**
The POST handler uses bare mutable defaults:

```python
platforms: Annotated[list[str], Form()] = [],
params: Annotated[list[str], Form()] = [],
swap: Annotated[str, Form()] = "",
```

This is inconsistent with the GET handler at lines 62-64, which deliberately uses `Query(default_factory=list)` and includes a long comment explaining that "Pydantic v2 (2.13.x) + FastAPI 0.136.x reject the combination of `Query(default_factory=list)` AND a parameter default `= []`". The same Pydantic/FastAPI rules apply to `Form()`. Today FastAPI tolerates mutable defaults in this position by replacing them per-request, but the convention noted in the GET docstring exists precisely to avoid this footgun. Future Pydantic versions may begin warning or erroring here, matching the Query-side behavior.

**Fix:**
Mirror the GET handler's pattern:

```python
@router.post("/browse/grid", response_class=HTMLResponse)
def browse_grid(
    request: Request,
    platforms: Annotated[list[str], Form(default_factory=list)],
    params: Annotated[list[str], Form(default_factory=list)],
    swap: Annotated[str, Form()] = "",
    db: DBAdapter | None = Depends(get_db),
):
```

---

### WR-04: Tautological assertion in XSS test masks real failures

**File:** `tests/v2/test_browse_routes.py:340`
**Issue:**

```python
assert "<script>" not in r_get.text or r_get.text.count("<script>") == 0
```

The two clauses are logically equivalent: `"<script>" not in s` is true exactly when `s.count("<script>") == 0`. The `or` between them makes the assertion trivially `True` — it cannot fail even if the response contains ten `<script>` tags. A test that cannot fail is worse than no test, because it gives false confidence.

**Fix:**
Drop the tautology:

```python
assert "<script>" not in r_get.text, "Injection string should not produce literal <script> in response"
```

If the intent was to allow `<script>` only when escaped (e.g. `&lt;script&gt;`), express that explicitly:

```python
# Reject ONLY unescaped <script>; the escaped form is fine.
import re
assert not re.search(r"<script\b[^>]*>", r_get.text, re.I), "Unescaped <script> tag found"
```

---

### WR-05: 500-page handler can themselves raise (template lookup not in try/except)

**File:** `app_v2/main.py:130-134`
**Issue:**
The catch-all `unhandled_exception_handler` calls `templates.TemplateResponse(request, "500.html", ...)`. If template rendering itself raises (missing template, broken Jinja syntax in a base block, etc.), the exception propagates back into Starlette's middleware stack and the user sees a default uncaught traceback instead of a clean 500 page. For the same reason `http_exception_handler` (lines 111-127) is exposed.

This is a low-likelihood failure (the templates ship with the app), but a misconfigured intranet deploy that loses `app_v2/templates/500.html` would surface a worse error than the default `{"detail": "..."}` JSON response.

**Fix:**
Wrap the TemplateResponse calls and fall back to a static HTML string if rendering fails:

```python
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    _log.exception("Unhandled exception on %s: %s", request.url.path, exc)
    try:
        return templates.TemplateResponse(
            request, "500.html",
            {"detail": f"{type(exc).__name__}: Internal server error"},
            status_code=500,
        )
    except Exception:  # noqa: BLE001 — last-resort renderer
        _log.exception("500.html template render failed")
        return HTMLResponse(
            "<h1>HTTP 500</h1><p>Internal server error.</p>",
            status_code=500,
        )
```

Apply the same wrapping pattern to `http_exception_handler` for the 404 / 500 branches.

## Info

### IN-01: `db` parameter is untyped in `build_view_model`

**File:** `app_v2/services/browse_service.py:79`
**Issue:**
The `db` positional parameter has no type annotation while every other parameter and the return type are annotated. Call sites pass `DBAdapter | None`. Mypy / IDEs lose the contract.

**Fix:**
```python
def build_view_model(
    db: "DBAdapter | None",
    db_name: str,
    selected_platforms: list[str],
    selected_param_labels: list[str],
    swap_axes: bool,
) -> BrowseViewModel:
```

(Add `from app.adapters.db.base import DBAdapter` under a `TYPE_CHECKING` guard to avoid a runtime import — service layer is supposed to be pure-Python with no FastAPI/Starlette imports per the module docstring; a pure typing-only import is consistent with that rule.)

---

### IN-02: `urlencode` slicing in test relies on undocumented format detail

**File:** `tests/v2/test_browse_routes.py:332`
**Issue:**
```python
r_get = client.get(f"/browse?platforms={urlencode([('x', injection)])[2:]}")
```
This builds `x=...&...` and slices off the first two characters (`x=`) to get the encoded value. It's correct for a single tuple but extremely fragile — any changes to the `urlencode` contract (extra leading characters, multi-pair input) would silently produce invalid URLs. Reviewers reading the test have to mentally re-derive what `[2:]` means.

**Fix:**
```python
from urllib.parse import quote
r_get = client.get(f"/browse?platforms={quote(injection, safe='')}")
```
`quote` is purpose-built for percent-encoding a single value.

---

### IN-03: `block_names` output may include duplicate `<span id="grid-count">` if both `grid` block and `count_oob` block are emitted in the same response

**File:** `app_v2/templates/browse/index.html:33-36, 73-77`
**Issue:**
The `count_oob` block emits a `<span id="grid-count" hx-swap-oob="true">`. The full-page `content` block also contains a `<span id="grid-count">` inside `.panel-header`. For POST /browse/grid the route asks for `block_names=["grid", "count_oob", "warnings_oob"]` — the `grid` block is rendered from inside the `content` block (which itself contains the in-flow `#grid-count`), but `jinja2_fragments` block rendering should isolate to the named blocks only.

If `jinja2_fragments` ever changes its block resolution to include parent context fragments, two `<span id="grid-count">` could end up in the same response and HTMX OOB resolution would be undefined. There's no problem today, but a regression test asserting "POST /browse/grid response contains exactly one `<span id=\"grid-count\">`" would lock it in.

**Fix:**
Add to `test_browse_routes.py`:
```python
assert r.text.count('id="grid-count"') == 1, (
    "POST /browse/grid response must emit exactly one #grid-count "
    "(the OOB swap target); two would create ambiguous OOB resolution."
)
```

---

### IN-04: `popover-search.js` JSON.parse can throw on malformed dataset

**File:** `app_v2/static/js/popover-search.js:56`
**Issue:**
```javascript
var original = JSON.parse(root.dataset.originalSelection || '[]');
```
If `root.dataset.originalSelection` was somehow corrupted (e.g. another script wrote a non-JSON value), the parse throws and `onDropdownHide` aborts mid-restore. The `||` only guards against the empty-string case, not malformed JSON.

**Fix:**
```javascript
var original = [];
try {
  original = JSON.parse(root.dataset.originalSelection || '[]');
} catch (_e) {
  original = [];
}
```

This is defense-in-depth — the property is only ever written by this same module today, but the guard costs nothing.

---

### IN-05: `picker_popover` membership test is O(n × m)

**File:** `app_v2/templates/browse/_picker_popover.html:62`
**Issue:**
```jinja
{% if opt in selected %}checked{% endif %}
```
For a catalog of N options and M selected, this is O(N×M). With ~100k+ rows in `ufs_data` the catalog is bounded by distinct platforms/parameters (likely << 100k), but Phase 4 already plans to render the full catalog in pickers.

**Fix:**
Pass the selected set into the macro pre-converted:
```jinja
{% set selected_set = selected | as_set %}  {# or: selected | tojson | ... #}
{% for opt in options %}
  ...{% if opt in selected_set %}checked{% endif %}
```
or do the conversion in `build_view_model` (BrowseViewModel.selected_platforms_set, etc.). Out-of-scope-for-v1 if catalogs stay small (< 1k).

---

### IN-06: Stale "(Task 3) of this plan" reference in module docstring

**File:** `app_v2/routers/browse.py:5-7`
**Issue:**
The module docstring references "(Task 3)" of an old plan revision. Plan 04-02 is the current locked plan; Task numbers may not align after future refactors. Cross-document references are maintenance debt.

**Fix:**
Replace plan-task references with stable invariants:
```python
"""Browse tab routes — pivot grid + URL round-trip (Phase 4).

Owns: GET /browse, POST /browse/grid.

The Phase 1 GET /browse stub in routers/root.py was removed when this router
was added — main.py registers `browse` BEFORE `root` so even if a future commit
accidentally re-introduces a /browse stub in root.py the real browse router
still wins (defense-in-depth).
"""
```

---

_Reviewed: 2026-04-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
