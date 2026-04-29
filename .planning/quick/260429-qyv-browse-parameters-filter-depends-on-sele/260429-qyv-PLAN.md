---
phase: 260429-qyv
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/ufs_service.py
  - app_v2/services/cache.py
  - app_v2/services/browse_service.py
  - app_v2/routers/browse.py
  - app_v2/templates/browse/_picker_popover.html
  - app_v2/templates/browse/_filter_bar.html
  - app_v2/templates/browse/index.html
  - tests/services/test_ufs_service.py
  - tests/v2/test_browse_service.py
  - tests/v2/test_browse_routes.py
autonomous: false
requirements:
  - QUICK-260429-qyv
must_haves:
  truths:
    - "When zero Platforms are selected, the Parameters picker trigger is fully disabled — clicking it does not open the dropdown, the trigger reads as disabled to assistive tech, and no checkbox is interactable"
    - "When at least one Platform is selected, the Parameters picker lists ONLY parameters (`InfoCategory · Item` labels) that have at least one row in `ufs_data` matching the currently-selected Platforms"
    - "Unselecting a Platform that contributed parameters causes those parameters to disappear from the Parameters picker AND drops them from the checked-set, so they cannot leak into the next Apply / grid render"
    - "POST /browse/grid is defended server-side: a request with zero platforms returns the empty-state grid regardless of any params= form fields, and a request with platforms+params filters out any param labels that are not available for the current platforms before calling fetch_cells"
    - "Existing v2.0 Browse behavior is preserved: URL round-trip (?platforms=&params=&swap=1), Apply auto-commit (D-15b), swap-axes toggle, Clear all, picker count badges, and the shareable URL all work exactly as before — only the param-availability rules change"
    - "Existing `list_parameters(db, db_name='')` zero-arg behavior is byte-stable for callers that need the full catalog (Ask page `_confirm_panel.html` build at app_v2/routers/ask.py:248) — the new platforms-filtered query is a separate function, not a breaking signature change"
  artifacts:
    - path: "app/services/ufs_service.py"
      provides: "New `list_parameters_for_platforms(db, platforms, db_name='') -> list[dict]` function that returns sorted distinct (InfoCategory, Item) rows whose PLATFORM_ID is in the supplied tuple — using sa.bindparam(expanding=True), the same SAFE-01 / T-03-01 mitigations as fetch_cells"
      contains: "def list_parameters_for_platforms"
    - path: "app_v2/services/cache.py"
      provides: "TTLCache wrapper `list_parameters_for_platforms(db, platforms, db_name='')` keyed on `hashkey(platforms, db_name)`, ttl=300s, paired with its own threading.Lock — same caching contract as list_parameters"
      contains: "list_parameters_for_platforms"
    - path: "app_v2/services/browse_service.py"
      provides: "Updated `build_view_model` that derives the filtered param catalog from selected_platforms, intersects selected_param_labels with the filtered catalog (drops stale labels), and exposes `params_disabled: bool` (True iff selected_platforms is empty) on the BrowseViewModel"
      contains: "params_disabled"
    - path: "app_v2/routers/browse.py"
      provides: "New `POST /browse/params-fragment` route that re-renders the Parameters picker block (named block `params_picker` in index.html) when the Platforms picker changes — returns the disabled-state fragment when platforms is empty"
      contains: "/browse/params-fragment"
    - path: "app_v2/templates/browse/_picker_popover.html"
      provides: "Macro extended with optional `disabled=False` arg — when True, the trigger button gets `disabled` attr + `aria-disabled='true'`, the dropdown body is omitted (so no checkboxes can be interacted with), and the badge stays hidden"
      contains: "disabled"
    - path: "app_v2/templates/browse/_filter_bar.html"
      provides: "Platforms picker `<ul>` fires `hx-post='/browse/params-fragment'` on change with `hx-target='#params-picker-slot'`; Parameters picker is wrapped in `<div id='params-picker-slot'>` and rendered via the new `params_picker` block in index.html with `disabled=vm.params_disabled`"
      contains: "/browse/params-fragment"
  key_links:
    - from: "_filter_bar.html (Platforms picker <ul>)"
      to: "/browse/params-fragment"
      via: "hx-post on the platforms picker <ul> (same change-event source as the existing /browse/grid wiring)"
      pattern: "hx-post=\"/browse/params-fragment\""
    - from: "POST /browse/params-fragment"
      to: "app_v2/templates/browse/index.html named block `params_picker`"
      via: "TemplateResponse with block_names=['params_picker']"
      pattern: "block_names=\\[.*params_picker.*\\]"
    - from: "build_view_model"
      to: "list_parameters_for_platforms"
      via: "platform-filtered catalog query (cached) + label intersection"
      pattern: "list_parameters_for_platforms"
    - from: "POST /browse/grid (defense-in-depth)"
      to: "build_view_model"
      via: "build_view_model intersects selected_param_labels against the platform-filtered catalog before calling fetch_cells"
      pattern: "selected_param_labels.*all_param_labels"
---

<objective>
On the Browse tab, make the Parameters filter strictly dependent on the current Platforms selection: only show parameters that exist for the selected platforms, disable the picker entirely when zero platforms are selected, and re-derive both the visible options AND the checked-set on every Platforms change so stale checked-but-invisible parameters cannot leak into a query.

Purpose: Today the Parameters picker shows the full `(InfoCategory, Item)` catalog regardless of which platforms are selected — which both wastes the user's time scrolling parameters that don't apply, AND lets a checked-but-no-longer-applicable parameter ride along when a platform is unselected (it stays checked under `form="browse-filter-form"` and is still posted on the next Apply). This breaks the user's mental model: the visible parameter list should always be a function of the visible platforms.

Output:
- New data-layer function `list_parameters_for_platforms(db, platforms, db_name='')` (parameterized SQL, allowlist-guarded table name) + matching cache wrapper (TTLCache, threading.Lock, partitioned by `hashkey(platforms, db_name)`).
- `build_view_model` extended to source the filtered catalog, intersect the checked-set against it, and expose `params_disabled: bool`.
- Existing `_picker_popover` macro extended (additive `disabled=False` arg, byte-stable when False).
- New `POST /browse/params-fragment` HTMX endpoint that re-renders just the Parameters picker block; Platforms picker `<ul>` fires it on change.
- POST `/browse/grid` continues to work, now with build_view_model's server-side param-intersection as defense-in-depth so a hand-crafted POST with stale params + platforms still cannot leak invalid labels into fetch_cells.
- Tests: 1 new ufs_service test (filter behavior, parameterized SQL, sort, allowlist), 4 new browse_service tests (disabled state, intersection, cross-platform widening, full-catalog ignored), 2 new route tests (params-fragment endpoint disabled response + populated response).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/PROJECT.md
@./CLAUDE.md
@app/services/ufs_service.py
@app_v2/services/cache.py
@app_v2/services/browse_service.py
@app_v2/routers/browse.py
@app_v2/routers/ask.py
@app_v2/templates/browse/index.html
@app_v2/templates/browse/_filter_bar.html
@app_v2/templates/browse/_picker_popover.html
@tests/v2/test_browse_service.py
@tests/v2/test_browse_routes.py

<interfaces>
<!-- Critical existing contracts the executor must preserve byte-stable for
     non-Browse code paths. These are extracted from the codebase for direct
     use — do NOT re-explore. -->

<!-- 1) `list_parameters` is the FULL-catalog query. The Ask page calls it
     with no platform filter to build the NL-05 confirmation panel candidate
     list. The new behavior MUST be a separate function — do NOT change the
     signature or semantics of list_parameters. -->

From app/services/ufs_service.py:
```python
def list_parameters(db: DBAdapter, db_name: str = "") -> list[dict]:
    """Return sorted distinct (InfoCategory, Item) rows."""
    tbl = _safe_table(_TABLE)
    with db._get_engine().connect() as conn:
        df = pd.read_sql_query(
            sa.text(
                f"SELECT DISTINCT InfoCategory, Item FROM {tbl} "
                "ORDER BY InfoCategory, Item"
            ),
            conn,
        )
    return df.to_dict("records")
```

From app_v2/routers/ask.py (line 248 — DO NOT BREAK):
```python
rows = list_parameters(db, db_name="")  # full catalog, NL-05 candidates
```

<!-- 2) The fetch_cells SQL pattern is the template for the new platforms-filtered
     parameters query: parameterized IN-list via sa.bindparam(expanding=True),
     allowlist-guarded table name via _safe_table(_TABLE), no f-string user
     interpolation. The new function MUST follow this pattern. -->

From app/services/ufs_service.py (fetch_cells):
```python
sql = sa.text(
    f"SELECT ... FROM {tbl} WHERE PLATFORM_ID IN :platforms ..."
).bindparams(sa.bindparam("platforms", expanding=True))
params = {"platforms": list(platforms), ...}
```

<!-- 3) Cache wrapper pattern (cachetools @cached + dedicated lock + key lambda
     that excludes the unhashable adapter, partitioned by db_name). The new
     wrapper MUST follow this pattern exactly. -->

From app_v2/services/cache.py:
```python
_parameters_cache: TTLCache = TTLCache(maxsize=64, ttl=300)
_parameters_lock = threading.Lock()

@cached(
    cache=_parameters_cache,
    lock=_parameters_lock,
    key=lambda db, db_name="": hashkey(db_name),
)
def list_parameters(db: DBAdapter, db_name: str = "") -> list[dict]:
    return _list_parameters_uncached(db, db_name)
```

<!-- 4) BrowseViewModel — the dataclass returned by build_view_model. Adding a
     new bool field `params_disabled` is the minimal change. Templates read
     vm.<field> via Jinja attribute access, so adding a field is non-breaking
     for callers that don't reference it. -->

From app_v2/services/browse_service.py:
```python
@dataclass
class BrowseViewModel:
    df_wide: pd.DataFrame
    row_capped: bool
    col_capped: bool
    n_value_cols_total: int
    n_rows: int
    n_cols: int
    swap_axes: bool
    selected_platforms: list[str]
    selected_params: list[str]
    all_platforms: list[str]
    all_param_labels: list[str]    # <-- this is the list the popover renders
    is_empty_selection: bool
    index_col_name: str
```

<!-- 5) PARAM_LABEL_SEP and the platforms-empty short-circuit in
     build_view_model are unchanged in spirit; the new behavior layers on top. -->

From app_v2/services/browse_service.py:
```python
PARAM_LABEL_SEP = " · "  # D-13: middle dot U+00B7. Pitfall 3 — never " / "
```

<!-- 6) The picker_popover macro's existing optional kwargs pattern
     (`disable_auto_commit=False`) is the precedent for adding `disabled=False`
     additively. -->

From app_v2/templates/browse/_picker_popover.html:
```jinja
{% macro picker_popover(name, label, options, selected,
                       form_id="browse-filter-form",
                       hx_post="/browse/grid",
                       hx_target="#browse-grid",
                       disable_auto_commit=False) %}
```

<!-- 7) The named-block + block_names=[...] pattern is how routes render
     fragment-only responses. Existing precedent: POST /browse/grid renders
     block_names=["grid", "count_oob", "warnings_oob", "picker_badges_oob"]. -->

From app_v2/routers/browse.py (browse_grid):
```python
response = templates.TemplateResponse(
    request, "browse/index.html", ctx,
    block_names=["grid", "count_oob", "warnings_oob", "picker_badges_oob"],
)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Data layer — `list_parameters_for_platforms` in ufs_service + cache wrapper</name>
  <files>
app/services/ufs_service.py
app_v2/services/cache.py
tests/services/test_ufs_service.py
tests/v2/test_cache.py
  </files>
  <behavior>
- Test (ufs_service): `list_parameters_for_platforms(mock_db, ("P1",))` issues a SELECT DISTINCT InfoCategory, Item FROM `<allowed_table>` WHERE PLATFORM_ID IN :platforms ORDER BY InfoCategory, Item, with `:platforms` bound via expanding=True. Returns `list[dict]` shape identical to `list_parameters` (e.g. `[{"InfoCategory": "attribute", "Item": "vendor_id"}, ...]`).
- Test (ufs_service): zero-platforms input — `list_parameters_for_platforms(mock_db, ())` returns `[]` WITHOUT issuing SQL (DATA-05 echo / matches fetch_cells empty-platforms guard).
- Test (ufs_service): table allowlist is enforced — `_safe_table(_TABLE)` is invoked, so a tampered `_TABLE` would raise ValueError before SQL emission (covered by reusing the existing allowlist guard, no new test fixture required — just assert the guard is called).
- Test (cache): `list_parameters_for_platforms(db, platforms, db_name)` is cached per `hashkey(platforms, db_name)` — calling twice with the same `(platforms, db_name)` invokes the underlying ufs_service function only once; calling with a different platforms tuple invokes it again.
- Test (cache): the platforms argument is normalized to a hashable tuple before keying — passing `("P1", "P2")` and `("P2", "P1")` should NOT collide on the cache key (sort-on-call is the caller's responsibility, not the cache's; this matches existing fetch_cells behavior). The wrapper rejects list inputs by relying on the caller to pass a tuple, exactly like `fetch_cells`.
  </behavior>
  <action>
Step 1 — Add `list_parameters_for_platforms` to `app/services/ufs_service.py`:

Append a new function AFTER the existing `list_parameters` definition (and BEFORE the `# Cell query` divider), modeled byte-for-byte on `list_parameters` + the platforms-filter pattern from `fetch_cells`:

```python
def list_parameters_for_platforms(
    db: DBAdapter,
    platforms: tuple[str, ...],
    db_name: str = "",
) -> list[dict]:
    """Return sorted distinct (InfoCategory, Item) rows that exist for ANY of
    the given PLATFORM_IDs.

    DATA-05 guard: empty platforms tuple returns [] without issuing SQL —
    mirrors fetch_cells behavior. The Browse Parameters picker depends on this
    so a "zero platforms selected" state never reaches the DB.

    Security (T-03-01, T-03-02): same allowlist + parameterized-IN pattern as
    fetch_cells. _safe_table() validates the table name; sa.bindparam(...,
    expanding=True) binds the platforms list — no f-string interpolation of
    user-controlled values.
    """
    if not platforms:
        return []
    tbl = _safe_table(_TABLE)
    sql = sa.text(
        f"SELECT DISTINCT InfoCategory, Item FROM {tbl} "
        "WHERE PLATFORM_ID IN :platforms "
        "ORDER BY InfoCategory, Item"
    ).bindparams(sa.bindparam("platforms", expanding=True))
    with db._get_engine().connect() as conn:
        df = pd.read_sql_query(sql, conn, params={"platforms": list(platforms)})
    return df.to_dict("records")
```

Update the module docstring's `Public API` section to include the new function (single line addition; do NOT touch any other line of the docstring):

```
  list_parameters_for_platforms(db, platforms, db_name="") -> list[dict]
```

DO NOT change `list_parameters` — the Ask page (app_v2/routers/ask.py:248) calls it for the full NL-05 candidate catalog.

Step 2 — Add cache wrapper to `app_v2/services/cache.py`:

Import the new function alongside the existing imports from ufs_service:

```python
from app.services.ufs_service import (
    fetch_cells as _fetch_cells_uncached,
    list_parameters as _list_parameters_uncached,
    list_parameters_for_platforms as _list_parameters_for_platforms_uncached,
    list_platforms as _list_platforms_uncached,
)
```

Add a dedicated TTLCache + lock + decorated wrapper, modeled on the existing `list_parameters` wrapper but keyed on `(platforms, db_name)`:

```python
_parameters_for_platforms_cache: TTLCache = TTLCache(maxsize=128, ttl=300)
_parameters_for_platforms_lock = threading.Lock()


@cached(
    cache=_parameters_for_platforms_cache,
    lock=_parameters_for_platforms_lock,
    key=lambda db, platforms, db_name="": hashkey(platforms, db_name),
)
def list_parameters_for_platforms(
    db: DBAdapter,
    platforms: Tuple[str, ...],
    db_name: str = "",
) -> list[dict]:
    """Return sorted distinct (InfoCategory, Item) rows for the given platforms (cached per (platforms, db_name))."""
    return _list_parameters_for_platforms_uncached(db, platforms, db_name)
```

Extend `clear_all_caches()` to include the new cache:

```python
for cache, lock in (
    (_platforms_cache, _platforms_lock),
    (_parameters_cache, _parameters_lock),
    (_parameters_for_platforms_cache, _parameters_for_platforms_lock),  # <-- add
    (_cells_cache, _cells_lock),
):
    with lock:
        cache.clear()
```

Update the module docstring's TTL rationale block to mention the new cache (one bullet, mirror the existing `list_parameters` bullet language).

Step 3 — Tests:

In `tests/services/test_ufs_service.py`, add tests in the `# list_parameters` region (or a fresh `# list_parameters_for_platforms` divider near it):
- `test_list_parameters_for_platforms_returns_records(mock_db)`: configures `mock_db._get_engine().connect()` (or whatever the existing fixture pattern is — copy verbatim from `test_list_parameters_returns_records`) to return a DataFrame with two rows; asserts the call returns the expected list-of-dicts.
- `test_list_parameters_for_platforms_empty_returns_empty(mock_db)`: passes `()` for platforms; asserts `result == []` AND that no `connect()` call was made (use `mock_db._get_engine().connect.assert_not_called()` or whatever idiom the existing tests use).
- `test_list_parameters_for_platforms_uses_bindparam(mocker, mock_db)`: spy on `pd.read_sql_query` (or the engine.connect path the existing tests already use) and assert that `params={"platforms": ["P1", "P2"]}` is passed and that the SQL text contains `IN :platforms` (NOT a literal-interpolated tuple).

In `tests/v2/test_cache.py`, add tests under a new `# list_parameters_for_platforms — cached per (platforms, db_name)` divider, mirroring the existing `list_parameters` test pattern:
- `test_list_parameters_for_platforms_caches_per_platforms_tuple()`: patches `_list_parameters_for_platforms_uncached`, calls the wrapper twice with the same `(("P1",), "db_a")` — asserts the underlying mock was called exactly once. Calls a third time with `(("P2",), "db_a")` — asserts the mock is now called twice (different cache key).
- `test_clear_all_caches_invalidates_parameters_for_platforms()`: warm the cache, call `clear_all_caches()`, then call again — asserts the underlying function is called twice (cache was cleared).

CRITICAL constraints for Task 1:
- DO NOT modify the signature, body, or docstring (beyond the one-line Public API addition) of `list_parameters` in ufs_service.py.
- DO NOT modify any existing test in `test_ufs_service.py` or `test_cache.py` — only add new tests.
- Preserve the import ordering of cache.py (alphabetic within each group is the existing convention — slot the new `list_parameters_for_platforms as _list_parameters_for_platforms_uncached` between `list_parameters` and `list_platforms`).
- The cache key is `hashkey(platforms, db_name)` — `platforms` MUST be a tuple at the call site. Document this in the wrapper docstring (it matches the existing `fetch_cells` contract).
- Run `ruff check app/services/ufs_service.py app_v2/services/cache.py` and resolve any violations introduced by the new code (don't touch unrelated existing violations).
  </action>
  <verify>
    <automated>pytest tests/services/test_ufs_service.py tests/v2/test_cache.py -q</automated>
  </verify>
  <done>
- `list_parameters_for_platforms` exists in `app/services/ufs_service.py`, returns `list[dict]`, uses `_safe_table` + `sa.bindparam(expanding=True)`, and short-circuits on empty platforms with `return []` BEFORE any DB call.
- Existing `list_parameters` in `ufs_service.py` is byte-stable (`git diff app/services/ufs_service.py` shows ONLY: the new function + the one-line Public API docstring addition).
- `app_v2/services/cache.py` has `list_parameters_for_platforms` wrapper with its own TTLCache (ttl=300, maxsize=128), its own threading.Lock, and a key lambda `lambda db, platforms, db_name="": hashkey(platforms, db_name)`. `clear_all_caches()` invalidates it.
- All new tests pass; the full `tests/services/test_ufs_service.py` and `tests/v2/test_cache.py` suites remain green (no regressions).
- `ruff check app/services/ufs_service.py app_v2/services/cache.py` reports no new violations.
- `git diff -- app_v2/routers/ask.py` is empty (Ask still uses unchanged `list_parameters`).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Service / route / template wiring — filtered catalog, intersection, disabled state, HTMX endpoint</name>
  <files>
app_v2/services/browse_service.py
app_v2/routers/browse.py
app_v2/templates/browse/_picker_popover.html
app_v2/templates/browse/_filter_bar.html
app_v2/templates/browse/index.html
tests/v2/test_browse_service.py
tests/v2/test_browse_routes.py
  </files>
  <behavior>
- Test (browse_service): `build_view_model(db, db_name, selected_platforms=[], selected_param_labels=[], swap_axes=False)` returns a vm with `params_disabled=True`, `all_param_labels=[]` (ignore the unfiltered catalog when no platforms), `selected_params=[]`, `is_empty_selection=True`. `list_parameters_for_platforms` is NOT called (zero-platforms short-circuit). `fetch_cells` is NOT called.
- Test (browse_service): with `selected_platforms=["P1"]` and `selected_param_labels=[]`, the vm has `params_disabled=False`, `all_param_labels=` the result of `list_parameters_for_platforms(db, ("P1",), db_name)` formatted via PARAM_LABEL_SEP and sorted, `selected_params=[]`, `is_empty_selection=True` (still empty because params is empty). `fetch_cells` not called.
- Test (browse_service) — INTERSECTION (the heart of this task): with `selected_platforms=["P1"]`, `selected_param_labels=["attribute · vendor_id", "flags · stale_label"]`, and `list_parameters_for_platforms` mocked to return ONLY `[{"InfoCategory": "attribute", "Item": "vendor_id"}]` — the vm has `selected_params=["attribute · vendor_id"]` (the stale `"flags · stale_label"` was DROPPED from the checked-set because it's not in the filtered catalog). `fetch_cells` is called with categories=("attribute",), items=("vendor_id",) — NOT including "stale_label".
- Test (browse_service): with `selected_platforms=["P1", "P2"]` (multi-platform widening), `list_parameters_for_platforms` is called once with the TUPLE `("P1", "P2")` (sort + tuple-cast at the call site for stable cache key; matches fetch_cells idiom). Returned param labels are the union from both platforms, surfaced as `all_param_labels`.
- Test (route): `POST /browse/params-fragment` with no `platforms` form field → response body contains the disabled Parameters trigger (matches `disabled` attr) AND does NOT contain a `<ul class="popover-search-list">` for the params picker (no checkboxes rendered — they cannot be ticked).
- Test (route): `POST /browse/params-fragment` with `platforms=P1` and `params=attribute · vendor_id, flags · stale_label`, with `list_parameters_for_platforms` mocked to return only the `attribute · vendor_id` row → response contains the `attribute · vendor_id` checkbox checked AND does NOT contain the `flags · stale_label` checkbox at all (intersection drops it).
- Test (route, defense-in-depth): `POST /browse/grid` with `platforms=` empty + `params=attribute · vendor_id` → response is the empty-state grid (existing behavior, byte-stable). `POST /browse/grid` with `platforms=P1` + `params=attribute · vendor_id, flags · stale_label` (the second is stale) — `fetch_cells` is invoked with items=("vendor_id",) only (the stale label is filtered out by build_view_model's intersection step). The existing /browse/grid tests must remain green.
  </behavior>
  <action>
Step 1 — Update `app_v2/services/browse_service.py`:

Add `params_disabled: bool` to the BrowseViewModel dataclass (place it next to `is_empty_selection` for thematic locality):

```python
@dataclass
class BrowseViewModel:
    ...
    is_empty_selection: bool
    params_disabled: bool         # NEW: True iff selected_platforms is empty
    index_col_name: str
```

Update the imports — replace the existing `from app_v2.services.cache import fetch_cells, list_parameters, list_platforms` with:

```python
from app_v2.services.cache import (
    fetch_cells,
    list_parameters_for_platforms,
    list_platforms,
)
```

Note: `list_parameters` (the full-catalog wrapper) is REMOVED from this module's imports — Browse no longer needs the unfiltered catalog. Ask still imports it directly from cache.py (untouched).

Rewrite the catalog block of `build_view_model`. Replace the current catalog-fetch block:

```python
if db is None:
    all_platforms: list[str] = []
    all_param_labels: list[str] = []
else:
    all_platforms = list(list_platforms(db, db_name=db_name))
    all_params_raw = list(list_parameters(db, db_name=db_name))
    all_param_labels = sorted(
        f"{p['InfoCategory']}{PARAM_LABEL_SEP}{p['Item']}"
        for p in all_params_raw
    )
```

with:

```python
params_disabled = not selected_platforms
if db is None:
    all_platforms: list[str] = []
    all_param_labels: list[str] = []
elif params_disabled:
    # Zero platforms selected → Parameters picker is disabled. We do NOT
    # query list_parameters_for_platforms with an empty tuple (the data-layer
    # short-circuit returns [] anyway, but skipping the call avoids cache
    # churn and makes the contract explicit at the orchestrator level).
    all_platforms = list(list_platforms(db, db_name=db_name))
    all_param_labels = []
else:
    all_platforms = list(list_platforms(db, db_name=db_name))
    # Sort + tuple-cast for stable cache key (matches fetch_cells idiom).
    platforms_key = tuple(sorted(selected_platforms))
    all_params_raw = list(
        list_parameters_for_platforms(db, platforms_key, db_name=db_name)
    )
    all_param_labels = sorted(
        f"{p['InfoCategory']}{PARAM_LABEL_SEP}{p['Item']}"
        for p in all_params_raw
    )

# CRITICAL — re-derive the checked-set on every call. Any param label that
# is no longer in the filtered catalog is dropped from selected_params, so
# stale "checked but invisible" parameters cannot leak into fetch_cells.
# Order is preserved by iterating selected_param_labels (user's original
# selection order) rather than the catalog.
available = set(all_param_labels)
selected_params_filtered = [
    lbl for lbl in selected_param_labels if lbl in available
]
```

Then update every `BrowseViewModel(...)` construction in `build_view_model` to:
- pass `params_disabled=params_disabled`,
- replace `selected_params=list(selected_param_labels)` with `selected_params=selected_params_filtered` (BOTH the empty-selection branch AND the populated branch — the intersection is the source of truth for downstream code).

Update the `is_empty` computation immediately following the catalog block to use the FILTERED selected_params, so a vm whose checked-set was wiped by the intersection is treated as empty:

```python
is_empty = (not selected_platforms) or (not selected_params_filtered)
```

Update the `parsed = [...]` comprehension in the populated branch to iterate `selected_params_filtered` (NOT the raw `selected_param_labels`) — this is the key defense-in-depth that prevents stale labels from reaching `fetch_cells`:

```python
parsed = [
    p for lbl in selected_params_filtered if (p := _parse_param_label(lbl))
]
```

Step 2 — Update `app_v2/templates/browse/_picker_popover.html`:

Add an additive `disabled=False` kwarg to the macro signature:

```jinja
{% macro picker_popover(name, label, options, selected,
                       form_id="browse-filter-form",
                       hx_post="/browse/grid",
                       hx_target="#browse-grid",
                       disable_auto_commit=False,
                       disabled=False) %}
```

Update the trigger button to support disabled state. Replace the existing trigger button block with:

```jinja
<button class="btn btn-outline-secondary btn-sm dropdown-toggle"
        type="button"
        id="picker-{{ name }}-trigger"
        {% if not disabled %}data-bs-toggle="dropdown"
        data-bs-auto-close="outside"{% endif %}
        {% if disabled %}disabled aria-disabled="true"{% endif %}
        aria-expanded="false"
        aria-label="Select {{ label | lower }}{% if disabled %} (disabled — select a platform first){% elif selected %} ({{ selected | length }} selected){% endif %}">
  {{ label }} <span id="picker-{{ name }}-badge" class="badge bg-secondary ms-1{% if not selected or disabled %} d-none{% endif %}" aria-live="polite">{{ selected | length }}</span> <i class="bi bi-chevron-down ms-1"></i>
</button>
```

Wrap the entire `<div class="dropdown-menu p-0 popover-search-root">…</div>` body block in `{% if not disabled %}…{% endif %}` so when disabled, NO checkbox is in the DOM and form-association cannot leak any checked state. (When disabled, the trigger has no `data-bs-toggle="dropdown"`, so even if a stray checkbox existed it could not be reached.)

Document the new kwarg at the top of the macro docstring comment block:

```
- `disabled=True` (NEW for quick task 260429-qyv): renders the trigger as
  Bootstrap-disabled (the `disabled` attr on the <button> AND aria-disabled),
  omits the dropdown body entirely (no checkboxes in DOM), and forces the
  badge to d-none. Used by the Parameters picker when zero Platforms are
  selected — the user cannot interact with parameters until at least one
  platform is chosen. The Parameters fragment is re-rendered via
  POST /browse/params-fragment on every Platforms change.
```

Step 3 — Update `app_v2/templates/browse/_filter_bar.html`:

(a) Wire the Platforms picker to fire the params-fragment refresh in addition to the existing /browse/grid wiring. Both fire on the SAME change — HTMX supports multiple hx-* on one element via different targets, but since the macro hard-codes a single `hx-post`/`hx-target`, the cleanest extension is via `hx-trigger`-bound additional request using `htmx.ajax` from a custom event handler is overkill. Instead, the simplest robust approach is to leverage HTMX's "trigger on the same change a second hx-post via hx-on" — BUT the cleanest architectural choice (chosen here) is:

The platforms picker `<ul>`'s existing change-event ALREADY fires `POST /browse/grid`. The grid response already returns OOB swaps for `picker-platforms-badge` and `picker-params-badge`. We extend `POST /browse/grid` to ALSO emit an OOB-swap for the entire Parameters picker block (the picker swap is keyed on a stable container id `id="params-picker-slot"`). This way, ONE request handles BOTH the grid update AND the parameters re-render — no extra endpoint hit, no double round-trip.

Refactor as follows:

In `_filter_bar.html`, wrap the Parameters picker call site in a stable container, and KEEP the existing Platforms picker call site unchanged:

```jinja
{# Platforms picker — full DB catalog source (D-12). #}
{{ picker_popover("platforms", "Platforms", vm.all_platforms, vm.selected_platforms) }}

{# Parameters picker — FILTERED to currently-selected platforms.
   Wrapped in #params-picker-slot so the grid POST response can OOB-swap the
   entire picker on every Platforms change. When vm.params_disabled, the
   macro renders the disabled trigger and no dropdown body. #}
<div id="params-picker-slot">
  {{ picker_popover("params", "Parameters", vm.all_param_labels, vm.selected_params, disabled=vm.params_disabled) }}
</div>
```

(b) The dedicated `POST /browse/params-fragment` endpoint is STILL needed for two reasons:
  1. Direct testability of the params-rendering logic in isolation (route test).
  2. Future graceful-degradation hook (e.g. if grid POST fails, the params picker can still be refreshed independently).

But to keep the same single-request UX, we DO NOT wire the platforms picker to it from the filter bar. Instead, the existing /browse/grid POST does the work via a new OOB swap (Step 5 below).

If during implementation you find that the grid POST's OOB swap of the ENTIRE picker conflicts with the open-popover state (e.g. swapping out the `<div>` while the popover is open is jarring), fall back to the dedicated endpoint approach: add `hx-on::after-request="htmx.ajax('POST', '/browse/params-fragment', {...})"` to the platforms `<ul>` instead. The route is implemented either way.

Step 4 — Update `app_v2/templates/browse/index.html`:

Add a new named block `params_picker_oob` for the OOB swap, plus a named block `params_picker` that the dedicated endpoint can render in isolation.

Inside the `{% block content %}` body, AFTER the existing OOB blocks (count_oob, warnings_oob, picker_badges_oob), add:

```jinja
{# OOB Parameters picker — emitted by POST /browse/grid alongside the grid
   swap so the Parameters picker re-renders whenever Platforms changes. The
   inner #params-picker-slot is the stable target; HTMX merges by id.
   Defense-in-depth: even if the platforms picker badge OOB above lands but
   this OOB is dropped, the next Apply still passes through build_view_model
   which intersects selected_params against the filtered catalog — no stale
   label can reach fetch_cells. (260429-qyv) #}
{% block params_picker_oob %}
  <div id="params-picker-slot" hx-swap-oob="true">
    {% from 'browse/_picker_popover.html' import picker_popover %}
    {{ picker_popover("params", "Parameters", vm.all_param_labels, vm.selected_params, disabled=vm.params_disabled) }}
  </div>
{% endblock params_picker_oob %}

{# Standalone Parameters picker block — used by POST /browse/params-fragment
   for direct refresh paths (test fixture + future graceful-degradation hook). #}
{% block params_picker %}
  {% from 'browse/_picker_popover.html' import picker_popover %}
  {{ picker_popover("params", "Parameters", vm.all_param_labels, vm.selected_params, disabled=vm.params_disabled) }}
{% endblock params_picker %}
```

Step 5 — Update `app_v2/routers/browse.py`:

Extend the `block_names` list in `browse_grid` to include `params_picker_oob`:

```python
block_names=["grid", "count_oob", "warnings_oob", "picker_badges_oob", "params_picker_oob"],
```

Add a new route `POST /browse/params-fragment` that returns ONLY the `params_picker` block:

```python
@router.post("/browse/params-fragment", response_class=HTMLResponse)
def browse_params_fragment(
    request: Request,
    platforms: Annotated[list[str], Form()] = [],
    params: Annotated[list[str], Form()] = [],
    db: DBAdapter | None = Depends(get_db),
):
    """Re-render ONLY the Parameters picker block (260429-qyv).

    Fired when the Platforms picker changes. When `platforms` is empty, the
    response is the disabled-state Parameters picker (no checkboxes in DOM).
    Otherwise the response is the picker populated with the parameters that
    exist for the selected platforms, with the previously-checked set
    intersected against the new available set (stale labels dropped).

    swap_axes is irrelevant for this fragment (the picker doesn't depend on
    it), so it is not accepted as a form field.
    """
    db_name = _resolve_db_name(db)
    vm = build_view_model(
        db,
        db_name,
        selected_platforms=platforms,
        selected_param_labels=params,
        swap_axes=False,
    )
    ctx = {"vm": vm}
    return templates.TemplateResponse(
        request,
        "browse/index.html",
        ctx,
        block_names=["params_picker"],
    )
```

Step 6 — Tests:

In `tests/v2/test_browse_service.py`, add tests under a new `# 260429-qyv: filtered parameters catalog + intersection` divider:

- `test_build_view_model_zero_platforms_disables_params(mocker)`: db=sentinel, mock list_platforms → ["P1","P2"], DO NOT mock list_parameters_for_platforms (assert it's not called). Call with selected_platforms=[]. Assert vm.params_disabled is True, vm.all_param_labels == [], vm.selected_params == []. Use `mocker.patch.object(browse_service, "list_parameters_for_platforms")` and assert `.assert_not_called()`.
- `test_build_view_model_filtered_param_catalog(mocker)`: mock list_platforms → ["P1","P2"], mock list_parameters_for_platforms → `[{"InfoCategory": "attribute", "Item": "vendor_id"}]`. Call with selected_platforms=["P1"], selected_param_labels=[]. Assert vm.params_disabled is False, vm.all_param_labels == ["attribute · vendor_id"], list_parameters_for_platforms was called with platforms=("P1",) (tuple, sorted).
- `test_build_view_model_drops_stale_param_labels(mocker)`: mock list_parameters_for_platforms → only `[{"InfoCategory": "attribute", "Item": "vendor_id"}]`. Call with selected_platforms=["P1"], selected_param_labels=["attribute · vendor_id", "flags · stale_label"]. Assert vm.selected_params == ["attribute · vendor_id"] (stale dropped); also patch fetch_cells and assert it was called with items=("vendor_id",) — NOT containing "stale_label".
- `test_build_view_model_multi_platform_widens_catalog(mocker)`: mock list_parameters_for_platforms to assert it's called with `("P1", "P2")` (sorted tuple) when selected_platforms=["P2","P1"] (input order is reversed; sort guarantees stable cache key).

In `tests/v2/test_browse_routes.py`, add tests under a new `# 260429-qyv: /browse/params-fragment + grid OOB params` divider. Use the existing TestClient fixture pattern (copy verbatim from existing tests in the file):

- `test_params_fragment_disabled_when_no_platforms(test_client, mocker)`: mock build_view_model OR the underlying cache layer to keep the test focused. POST /browse/params-fragment with empty form → response.status_code == 200, response body contains `disabled` (button attr) and `aria-disabled="true"`, and does NOT contain `popover-search-list` (no `<ul>` body — checkboxes are not in DOM).
- `test_params_fragment_populated_with_intersection(test_client, mocker)`: mock list_parameters_for_platforms → `[{"InfoCategory": "attribute", "Item": "vendor_id"}]`. POST /browse/params-fragment with `platforms=P1`, `params=attribute · vendor_id`, `params=flags · stale_label`. Assert response contains the `attribute · vendor_id` checkbox marked checked, does NOT contain `flags · stale_label` anywhere in the body.
- `test_grid_post_emits_params_picker_oob(test_client, mocker)`: POST /browse/grid with platforms=P1 + a valid param → response body contains the OOB params picker fragment (look for `id="params-picker-slot"` AND `hx-swap-oob="true"` together).
- (Defense-in-depth) `test_grid_post_filters_stale_param_labels(test_client, mocker)`: POST /browse/grid with platforms=P1, params=attribute · vendor_id, params=flags · stale_label, list_parameters_for_platforms mocked to return only the vendor_id row. Spy on `fetch_cells` and assert items=("vendor_id",). The existing /browse/grid tests for empty-platform short-circuit MUST still pass byte-stable — DO NOT alter those.

CRITICAL constraints for Task 2:
- The new `params_disabled` field is the ONLY field added to BrowseViewModel. Order it just before `index_col_name` (last positional dataclass field before index_col_name). Consumers that construct BrowseViewModel via keyword args (the function itself, all tests) are unaffected.
- DO NOT change PARAM_LABEL_SEP or _parse_param_label.
- DO NOT remove the existing OOB blocks (count_oob, warnings_oob, picker_badges_oob) — just add `params_picker_oob` and `params_picker` after them.
- The `_filter_bar.html` change is ADDITIVE: wrap the existing Parameters picker call in `<div id="params-picker-slot">…</div>` AND pass `disabled=vm.params_disabled`. The Platforms picker call site is byte-stable.
- The `_picker_popover.html` macro change is ADDITIVE: when `disabled=False` (the default for ALL existing call sites — Browse Platforms, Browse Parameters in the populated branch, Overview's 6 pickers in `app_v2/templates/overview/_filter_bar.html`, and Ask's confirm panel `_confirm_panel.html`), the rendered HTML is BYTE-STABLE with the pre-change output. Verify by: (a) running existing `tests/v2/test_browse_routes.py` and `tests/v2/test_overview_*.py` and `tests/v2/test_ask_*.py` and confirming all pass; (b) `git diff` of the macro shows only additions inside `{% if disabled %}/{% if not disabled %}` guards.
- Run `ruff check app_v2/services/browse_service.py app_v2/routers/browse.py` after changes; resolve any new violations.
- Run `pytest tests/v2/ -q` after Task 2 — the full v2 test suite (which is currently 506 tests passing per STATE.md) MUST stay green; only the new tests are added.
  </action>
  <verify>
    <automated>pytest tests/v2/test_browse_service.py tests/v2/test_browse_routes.py -q && pytest tests/v2/ -q</automated>
  </verify>
  <done>
- BrowseViewModel has a new `params_disabled: bool` field, populated correctly: True when selected_platforms is empty, False otherwise.
- `build_view_model` calls `list_parameters_for_platforms` (NOT the unfiltered `list_parameters`) when platforms is non-empty; calls neither when platforms is empty (just returns disabled vm with empty param catalog).
- `build_view_model` filters `selected_param_labels` to `selected_params_filtered` (intersection with the filtered catalog) BEFORE constructing the vm AND BEFORE calling `fetch_cells`. Stale labels never reach the data layer.
- `_picker_popover.html` macro has `disabled=False` kwarg; when True, the trigger button has `disabled` and `aria-disabled="true"`, the dropdown body is omitted entirely, and the badge has `d-none`.
- `_filter_bar.html` wraps the Parameters picker in `<div id="params-picker-slot">…</div>` and passes `disabled=vm.params_disabled`.
- `index.html` exposes new named blocks `params_picker_oob` (OOB swap fragment for /browse/grid responses) and `params_picker` (standalone block for /browse/params-fragment responses).
- `POST /browse/params-fragment` route exists, accepts `platforms` + `params` form fields, returns the `params_picker` block — disabled when platforms empty, populated + intersected when platforms non-empty.
- `POST /browse/grid`'s `block_names` list now includes `params_picker_oob`, so every grid POST also re-renders the Parameters picker with the current intersection.
- All new tests pass; full `pytest tests/v2/ -q` is green (≥ pre-change passing count + new tests added).
- Existing Overview, Ask, and other `_picker_popover` callers are byte-stable in rendered output (regression suite confirms).
- `ruff check` reports no new violations.
- `git diff -- app_v2/routers/ask.py` is empty.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Visual UAT — Parameters filter follows Platforms selection</name>
  <files>(no code changes — verification of Tasks 1 and 2)</files>
  <action>
Pause for human visual verification of the end-to-end behavior on the live server. No code changes in this task. The user runs the v2.0 app locally and walks through the four scenarios in <how-to-verify>. The user types "approved" if all four pass, or describes the failing scenario.
  </action>
  <how-to-verify>
1. Start the v2.0 app locally:
   ```
   uvicorn app_v2.main:app --reload --port 8001
   ```
2. Open http://localhost:8001/browse in a browser.

3. **Scenario A — Disabled state on initial load:**
   - With zero platforms selected (the default landing state on /browse with no query string), the Parameters trigger button should be visibly disabled (greyed out per Bootstrap's disabled style on `.btn-outline-secondary`), AND clicking it should do NOTHING — no dropdown opens, no checklist appears.
   - Hover tooltip / aria-label should communicate the disabled reason ("Select a platform first" or equivalent).

4. **Scenario B — Enabling on first Platform pick:**
   - Click the **Platforms** trigger, check ONE platform (say `P1`), and let the popover auto-commit (D-15b 250ms debounce).
   - Expected: the grid re-renders (count caption updates), AND the Parameters trigger becomes enabled (no longer greyed out).
   - Click the now-enabled Parameters trigger and confirm: the dropdown lists ONLY parameters that have rows in `ufs_data` for `P1` — NOT the full catalog. This may be a much shorter list than before the fix.

5. **Scenario C — Cross-platform widening:**
   - With `P1` selected, ALSO check a second platform `P2` (different SoC, ideally one that has parameters `P1` does not).
   - Expected: the Parameters dropdown grows to include parameters from both `P1` and `P2` (the union). No parameter from a third unselected platform leaks in.

6. **Scenario D — Stale-checked discard on Platform unselect (the headline bug fix):**
   - With `P1` + `P2` both selected, open Parameters and check a parameter that exists ONLY for `P2` (e.g. one that does NOT appear when only `P1` is selected — pick by domain knowledge or by toggling and observing).
   - Click Apply / let auto-commit fire — confirm the grid includes that parameter's column for `P2`.
   - Now go back to Platforms and UNCHECK `P2`.
   - Expected:
     a. The Parameters dropdown immediately re-renders, and the parameter that only existed for `P2` is GONE from the list (not shown unchecked, not shown greyed — entirely absent).
     b. The grid re-renders WITHOUT that parameter's column — proving the stale checked-set was discarded server-side, not just hidden in the DOM.
     c. The Parameters trigger badge count updates to reflect only the still-valid checked items.
   - Re-check `P2`: the previously-checked parameter does NOT auto-recheck (this is correct — the checked-state was discarded, not merely hidden).

7. **Scenario E — Disable on full unselect:**
   - From the previous state, uncheck ALL platforms (the picker should now show 0 selected).
   - Expected: the Parameters trigger becomes disabled again, ALL its previous checks are dropped, and the grid returns to the empty-state alert ("Select platforms and parameters above to build the pivot grid.").

8. **Scenario F — URL round-trip regression:**
   - With a multi-platform + multi-param selection active, copy the address-bar URL (it should be `/browse?platforms=…&params=…`).
   - Open that URL in a fresh tab.
   - Expected: the picker checks restore exactly as before (this exercises the URL → form → server intersection path; if a stale param somehow was in the URL, it should also be silently dropped — not error out).

9. **Scenario G — Other tabs unchanged (regression):**
   - Visit /overview — all 6 popover-checklist filters work exactly as before (they should, since the macro change is additive on a default `disabled=False` arg).
   - Visit /ask — open the NL flow, confirm the NL-05 confirmation panel's parameters list still uses the FULL catalog (Ask is unaffected by the platforms-filtered query).

Type **approved** when all 7 scenarios pass. Otherwise describe which scenario fails and what you observed; we will diagnose.
  </how-to-verify>
  <verify>
    <automated>MISSING — visual UAT cannot be automated; human confirmation via "approved" resume signal is the only acceptance gate.</automated>
  </verify>
  <done>
- User has typed "approved" after walking through scenarios A–G.
- All four primary scenarios (A: disabled state; B: enabling; C: widening; D: stale-discard) behave per <how-to-verify>.
- Regression scenarios (F: URL round-trip; G: Overview + Ask byte-stable) confirmed unchanged.
  </done>
  <resume-signal>Type "approved" or describe issues</resume-signal>
</task>

</tasks>

<verification>
- `pytest tests/services/test_ufs_service.py tests/v2/ -q` is fully green (existing 506+ tests stay green; new tests added in this plan all pass).
- `ruff check app/services/ufs_service.py app_v2/services/cache.py app_v2/services/browse_service.py app_v2/routers/browse.py` reports no new violations.
- `git diff` is confined to the files listed in `files_modified` (frontmatter). In particular:
  - `git diff -- app_v2/routers/ask.py` is empty (Ask page byte-stable).
  - `git diff -- app/services/ufs_service.py` shows only the new function + the one-line Public API docstring addition (existing `list_parameters` byte-stable).
  - `git diff -- app_v2/templates/browse/_picker_popover.html` shows only additive `disabled=False` kwarg branches (rendered HTML byte-stable when disabled is False).
- The four headline behaviors from the user request (filtered list, disabled state, stale-discard on unselect, server-side enforcement) are all observable via the route tests AND human UAT.
- `git diff -- app_v2/templates/overview/` is empty (Overview's reuse of the picker macro is unaffected by the additive kwarg).
</verification>

<success_criteria>
- Parameters picker is fully disabled (button + missing dropdown body) whenever zero platforms are selected; the user cannot interact with it.
- When platforms are selected, the Parameters picker shows ONLY parameters that exist in `ufs_data` for the union of those platforms — backed by a cached, parameterized SQL query.
- When a platform is unselected, parameters that existed only for it disappear from the picker AND are dropped from the checked-set; the next grid render reflects the trimmed set.
- POST /browse/grid is the single round-trip that updates BOTH the grid AND the Parameters picker (via OOB swap of `#params-picker-slot`); a separate POST /browse/params-fragment endpoint exists for direct fragment refreshes / future graceful-degradation paths.
- Defense-in-depth: even a hand-crafted POST with stale params + valid platforms cannot leak invalid labels into `fetch_cells` — `build_view_model` intersects against the filtered catalog server-side.
- Existing Browse, Overview, and Ask behavior is byte-stable for all paths that don't touch the Parameters picker dependency rule (URL round-trip, Apply auto-commit, swap-axes, Clear all, NL-05 candidate panel, Overview 6 pickers).
- Full `pytest tests/v2/ -q` plus `pytest tests/services/test_ufs_service.py -q` remain green; new tests cover: data-layer filter + cache, build_view_model intersection + disabled state, route-level disabled fragment, route-level intersection fragment, grid POST OOB params re-render, grid POST stale-label filtering.
- User approves the visual UAT covering all 7 scenarios.
</success_criteria>

<output>
After completion, create `.planning/quick/260429-qyv-browse-parameters-filter-depends-on-sele/260429-qyv-SUMMARY.md` documenting:
- Final diff summary for each file in `files_modified` (one line per file: what changed, why).
- Confirmation that `list_parameters` (full catalog) is byte-stable and the Ask page is unaffected.
- Confirmation that the Overview tab's 6 popover-checklist filters are byte-stable (additive macro kwarg only).
- The exact new endpoint signature `POST /browse/params-fragment` and the rationale for keeping it alongside the OOB-swap-on-grid-post primary path.
- New test count (delta) and final `pytest tests/v2/ -q` summary line.
- Human UAT outcome (which scenarios passed; any issues raised and resolved).
- Reference back to STATE.md decisions touched: D-15b (debounced auto-commit), D-12 (catalog source — now bifurcated: full catalog for Ask, platforms-filtered for Browse), DATA-05 (empty-filter SQL guard, mirrored at the new function).
</output>
