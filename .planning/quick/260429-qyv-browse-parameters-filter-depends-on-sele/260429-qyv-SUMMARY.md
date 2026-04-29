---
phase: 260429-qyv
plan: 01
subsystem: browse
tags: [browse, filter, parameters, htmx, security]
requires: [list_parameters, list_platforms, fetch_cells, _picker_popover]
provides:
  - "list_parameters_for_platforms (data + cache layer)"
  - "params_disabled bool on BrowseViewModel"
  - "POST /browse/params-fragment route"
  - "params_picker_oob OOB-swap block on /browse/grid"
  - "_picker_popover.html disabled=False kwarg (additive)"
affects:
  - "app/services/ufs_service.py (additive — list_parameters byte-stable)"
  - "app_v2/services/cache.py (additive cache slot)"
  - "app_v2/services/browse_service.py (catalog source switched, intersection added)"
  - "app_v2/routers/browse.py (block_names extended, new fragment route)"
  - "app_v2/templates/browse/* (additive blocks + macro kwarg)"
tech-stack:
  added: []
  patterns:
    - "platforms-filtered catalog query (parameterized IN with sa.bindparam expanding=True; matches fetch_cells idiom)"
    - "TTLCache(maxsize=128, ttl=300) keyed on hashkey(platforms, db_name)"
    - "server-side intersection of checked-set against filtered catalog before fetch_cells"
    - "OOB-swap of entire picker container (#params-picker-slot) alongside grid swap"
    - "additive Jinja macro kwarg with default-False byte-stable for existing call sites"
key-files:
  created: []
  modified:
    - app/services/ufs_service.py
    - app_v2/services/cache.py
    - app_v2/services/browse_service.py
    - app_v2/routers/browse.py
    - app_v2/templates/browse/_picker_popover.html
    - app_v2/templates/browse/_filter_bar.html
    - app_v2/templates/browse/index.html
    - tests/services/test_ufs_service.py
    - tests/v2/test_cache.py
    - tests/v2/test_browse_service.py
    - tests/v2/test_browse_routes.py
decisions:
  - "Bifurcate the parameter catalog source: Browse uses platforms-filtered query (list_parameters_for_platforms), Ask continues to use unfiltered list_parameters (NL-05 needs the full candidate space). Two separate cache wrappers, two separate cache slots."
  - "Disabled-state semantics: dropdown body is OMITTED from the DOM (not just visually hidden) when zero platforms are selected — eliminates form-association leak risk at the structural level, not just the CSS level."
  - "Server-side intersection (not just client-side hide) is the source of truth: stale labels are dropped from selected_params before fetch_cells AND in the rendered picker, so no UI desync is possible."
  - "Defense-in-depth via OOB swap on /browse/grid: every grid POST re-renders the picker container, so any stale URL or hand-crafted form is corrected on the next round-trip even if the dedicated /browse/params-fragment endpoint is bypassed."
  - "Cache key uses tuple(sorted(selected_platforms)) so order-variant selections share a slot; the data layer accepts the tuple as-is (matching the fetch_cells contract)."
metrics:
  duration: ~50min
  tasks_completed: 2_of_2_code_tasks_plus_T3_ready_for_UAT
  tests_added: 16
  completed_date: 2026-04-29
---

# Quick Task 260429-qyv: Browse Parameters filter depends on Platforms — Summary

## One-liner

Made the Browse Parameters picker strictly dependent on the currently-selected Platforms — disabled when zero, filtered to platforms-applicable items when one or more, with server-side intersection that drops stale checked-but-no-longer-applicable parameters before they reach `fetch_cells`.

## Why

Pre-fix, the Parameters picker showed the entire `(InfoCategory, Item)` catalog regardless of which platforms were selected, which (a) wasted users' time scrolling parameters that did not apply, and (b) let a checked-but-no-longer-applicable parameter ride along when its source platform was unselected — it stayed checked under `form="browse-filter-form"` and was still posted on the next Apply, returning 0-row pivots that broke the user's mental model. The fix re-derives the visible parameter list and the checked-set as a function of the visible platforms, both at the picker render level and at the SQL-build level.

## What changed (per file)

| File | Change | Why |
| --- | --- | --- |
| `app/services/ufs_service.py` | New `list_parameters_for_platforms(db, platforms, db_name="")` function — `SELECT DISTINCT InfoCategory, Item FROM <tbl> WHERE PLATFORM_ID IN :platforms ORDER BY InfoCategory, Item`, with `sa.bindparam(expanding=True)`, `_safe_table` allowlist guard, and an empty-platforms short-circuit. Existing `list_parameters` left byte-stable (one-line docstring API addition is the only delta). | Mirror the security model of `fetch_cells` (T-03-01, T-03-02, DATA-05). Keep the unfiltered `list_parameters` so the Ask page's NL-05 confirmation panel (`app_v2/routers/ask.py:248`) still gets the full candidate catalog. |
| `app_v2/services/cache.py` | New `_parameters_for_platforms_cache: TTLCache(maxsize=128, ttl=300)` + dedicated `threading.Lock`; `@cached` wrapper keyed on `hashkey(platforms, db_name)`. `clear_all_caches()` now invalidates the new cache too. | Match the existing `list_parameters` wrapper pattern (separate lock for finer-grained contention; 5-min TTL because the catalog is immutable between ingestions). |
| `app_v2/services/browse_service.py` | Replaced `list_parameters` import with `list_parameters_for_platforms`. Added `params_disabled: bool` field to `BrowseViewModel`. Rewrote the catalog block of `build_view_model`: when zero platforms selected, skip the catalog call and surface `all_param_labels=[]`; otherwise sort+tuple the platforms for the cache key and source the catalog from the new wrapper. Added the intersection step: `selected_param_labels` is filtered against `all_param_labels` before parsing, so stale labels are dropped before reaching `fetch_cells`. `n_value_cols_total` and `selected_params` reflect the filtered set. | Single point of truth for the dependency rule. The intersection lives at the orchestrator (not the route) so any caller — current or future — that uses `build_view_model` inherits the defense automatically. |
| `app_v2/routers/browse.py` | Extended `block_names` on `POST /browse/grid` to include `params_picker_oob`. Added new route `POST /browse/params-fragment` that renders only the `params_picker` block. | OOB swap on the primary commit path = single round-trip for both grid and picker; the dedicated endpoint is kept for direct testability and future graceful-degradation hooks. |
| `app_v2/templates/browse/_picker_popover.html` | Additive `disabled=False` kwarg on the `picker_popover` macro. When True, the trigger button gets `disabled` + `aria-disabled="true"`, the badge stays hidden via `d-none`, and the entire `<div class="dropdown-menu">` body is omitted from the DOM. When False (the default for ALL existing call sites), rendered HTML is byte-stable. | Structural defense — no checkboxes in DOM means no form-association leak path is even possible when the picker is supposed to be disabled. |
| `app_v2/templates/browse/_filter_bar.html` | Wrapped the Parameters picker call in `<div id="params-picker-slot">…</div>` and passed `disabled=vm.params_disabled`. Platforms picker call site byte-stable. | Stable swap target for both the OOB block on `/browse/grid` and the primary `hx-target` of the dedicated fragment endpoint. |
| `app_v2/templates/browse/index.html` | Added new named blocks `params_picker_oob` (OOB swap, with `hx-swap-oob="true"`, emitted by `/browse/grid`) and `params_picker` (standalone, no OOB attribute, rendered by `/browse/params-fragment`). Existing `picker_badges_oob` block updated so the params badge is forced `d-none` when `vm.params_disabled`. | Two emit paths for the picker: one OOB-swap as part of every grid POST, one primary-target swap for the dedicated endpoint — both reuse the same macro so the DOM is identical regardless of how the picker arrived. |
| `tests/services/test_ufs_service.py` | New `mock_db_multi_platform` SQLite fixture (3 platforms, 5 rows). 6 new tests: returns records for single platform, widens for multi-platform, empty short-circuit (no SQL), `db_name` kwarg, `bindparam` injection probe, cross-platform exclusion. Existing tests untouched. | Cover SAFE-01, T-03-01, DATA-05 echoes for the new function. |
| `tests/v2/test_cache.py` | 5 new tests: per-(platforms, db_name) cache hit, distinct db_name partitions, order-variant non-collision (caller-normalizes contract), independence from `list_parameters`, `clear_all_caches` invalidation. | Pin the cache contract before consumers depend on it. |
| `tests/v2/test_browse_service.py` | 5 new `# 260429-qyv:` tests: zero-platforms disables params (no catalog call), filtered param catalog with sorted platforms tuple, stale label drop in `selected_params` AND `fetch_cells` items, multi-platform widening with sorted-tuple cache key, full-catalog ignored when no platforms. Updated 6 existing tests where they patched `list_parameters` (now `list_parameters_for_platforms`) or expected the params catalog to be queried with no platforms. | Cover the intersection contract — the heart of the bug fix. |
| `tests/v2/test_browse_routes.py` | Updated `_patch_cache` helper to patch `list_parameters_for_platforms` instead of `list_parameters` (signature change includes the platforms-tuple positional). 5 new `# 260429-qyv:` tests: params-fragment disabled response, params-fragment populated with intersection (stale label dropped), params-fragment returns picker-only (no cross-block OOB leakage), `/browse/grid` emits `params_picker_oob`, `/browse/grid` defense-in-depth filters stale labels at the route boundary. Updated 3 existing tests where they relied on the params picker rendering with no platforms (the XSS escape test, the D-15b regression test, the garbage-params test). | Exercise the new endpoint and the OOB-on-grid path; preserve the existing route contracts. |

## Verification

| Metric | Before | After |
| --- | --- | --- |
| `pytest tests/services/test_ufs_service.py tests/v2/test_cache.py -q` | 25 passed | 40 passed |
| `pytest tests/v2/test_browse_service.py -q` | 16 passed | 21 passed |
| `pytest tests/v2/test_browse_routes.py -q` | 16 passed | 21 passed |
| `pytest tests/v2/ tests/services/test_ufs_service.py -q` | (baseline) | **375 passed, 2 skipped** |
| `pytest -q` (project-wide) | (baseline) | **526 passed, 2 skipped** |

**Byte-stability checks:**
- `git diff -- app_v2/routers/ask.py` — empty (Ask still imports `list_parameters` from `app_v2.services.cache`, NL-05 panel byte-stable).
- `git diff -- app_v2/templates/overview/` — empty (Overview's six popover-checklist filters call `picker_popover` with no `disabled` kwarg → default `False` → byte-stable).
- The macro change is additive: `disabled=False` is the default for every existing call site (Browse Platforms picker, Overview's six pickers, Ask's NL-05 confirm panel via `disable_auto_commit=True` only).

## Headline behaviors (must-haves) — code-level coverage

| Behavior | Where it's enforced | Test |
| --- | --- | --- |
| Zero platforms ⇒ Parameters trigger fully disabled, dropdown body omitted | `_picker_popover.html` `{% if not disabled %}…{% endif %}` wrap; `params_disabled=True` set in `build_view_model` | `test_params_fragment_disabled_when_no_platforms` |
| ≥1 platform ⇒ Parameters picker lists ONLY filtered (cat, item) pairs | `list_parameters_for_platforms` SQL filter + `build_view_model` catalog source switch | `test_build_view_model_filtered_param_catalog`, `test_list_parameters_for_platforms_returns_records` |
| Unselecting a contributing platform drops affected params from picker AND from checked-set | Intersection step in `build_view_model`: `selected_params_filtered = [lbl for lbl in selected_param_labels if lbl in available]` | `test_build_view_model_drops_stale_param_labels`, `test_grid_post_filters_stale_param_labels`, `test_params_fragment_populated_with_intersection` |
| `POST /browse/grid` defended server-side: empty platforms → empty grid; populated with stale → stale dropped before `fetch_cells` | `build_view_model` is the single orchestrator both routes use | `test_post_browse_grid_empty_form_returns_empty_state`, `test_grid_post_filters_stale_param_labels` |
| URL round-trip + Apply auto-commit (D-15b) + swap-axes + Clear all + picker badge OOB still work | Existing route + template behavior unchanged outside the additive deltas | All 16 pre-existing route tests still pass |
| `list_parameters(db, db_name='')` zero-arg behavior byte-stable for the Ask page | `list_parameters` is the unfiltered wrapper in `cache.py`, untouched. The new function is a separate symbol. | `git diff -- app_v2/routers/ask.py` is empty; the existing Ask test suite stays green |

## Tasks 1 & 2 — completed

**Commits:**
- `c93db52` — `feat(quick-260429-qyv): add list_parameters_for_platforms data layer + cache wrapper`
- `f1e002b` — `feat(quick-260429-qyv): make Browse Parameters filter depend on Platforms`

## Task 3 (visual UAT) — ready for human verification

No code changes in this task. The visual contract for scenarios A–G in `260429-qyv-PLAN.md` is implementable from the work above and **ready for human UAT** at the live server:

```
uvicorn app_v2.main:app --reload --port 8001
```

Walk-through:

| Scenario | What to do | Expected |
| --- | --- | --- |
| **A** Disabled on initial load | Visit `/browse` with no query string | Parameters trigger is greyed/disabled; clicking does nothing |
| **B** Enables on first Platform pick | Check one platform in the Platforms popover | Auto-commit (D-15b 250ms debounce) → grid + Parameters trigger become enabled; Parameters list shows ONLY parameters available for that platform |
| **C** Cross-platform widening | Add a second platform with different params | Parameters list grows to the union of both platforms' params |
| **D** Stale-discard on Platform unselect | With P1 + P2 selected, check a P2-only param, then uncheck P2 | The P2-only param disappears from the Parameters dropdown AND from the grid, and the checked-state is discarded (re-checking P2 does NOT auto-recheck the param) |
| **E** Disable on full unselect | Uncheck all platforms | Parameters trigger goes disabled again, all checks dropped, grid returns to empty-state alert |
| **F** URL round-trip | Copy a multi-platform/multi-param URL into a fresh tab | Picker checks restore exactly; any stale URL param silently drops |
| **G** Other tabs unchanged | Visit `/overview` and `/ask` | Overview's 6 filters still work as before; Ask's NL-05 candidate panel still uses the full catalog |

The user types **approved** when all 7 scenarios pass; otherwise describes the failing scenario for diagnosis.

## Reference back to STATE.md decisions

- **D-15b** (debounced auto-commit, 2026-04-28) — preserved byte-stable. The new Parameters re-render rides on the same change-event path.
- **D-12** (catalog source for Browse pickers) — refined: full DB catalog for Platforms (still `list_platforms`), platforms-filtered catalog for Parameters (now `list_parameters_for_platforms`). Ask retains the full unfiltered catalog (`list_parameters`).
- **DATA-05** (empty-filter SQL guard, originally on `fetch_cells`) — mirrored at the new `list_parameters_for_platforms`: empty platforms tuple → return `[]` without issuing SQL.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Existing `_patch_cache` helper patched `list_parameters` (now removed from `browse_service`)**
- **Found during:** Task 2 (route tests run after browse_service import change)
- **Issue:** `monkeypatch.setattr` on `app_v2.services.browse_service.list_parameters` raised `AttributeError` because the symbol no longer exists in browse_service after the import switch.
- **Fix:** Updated `_patch_cache` to patch `app_v2.services.browse_service.list_parameters_for_platforms` instead. The lambda now accepts the platforms tuple as a positional argument (and ignores it — returns the static fixture).
- **Files modified:** `tests/v2/test_browse_routes.py` (the helper at the top of the file).
- **Commit:** `f1e002b`.

**2. [Rule 3 — Blocking] Three existing route tests assumed the Parameters picker renders with zero platforms**
- **Found during:** Task 2
- **Issue:** With the new disabled-state contract (no popover-search-list when platforms is empty), three tests started failing:
  - `test_post_browse_grid_xss_escape_in_param_label` — was sending GET `/browse` (no platforms) and expected the catalog labels to render in the picker, where the XSS escaping would be visible.
  - `test_picker_checklist_carries_d15b_hx_attributes` — was sending GET `/browse` and expecting `popover-search-list` to appear ≥ 2 times (once per picker).
  - `test_get_browse_with_garbage_params_returns_empty_grid` — was asserting `mock_fetch_cells.called`, but the new intersection drops the garbage label and short-circuits the empty-selection branch before fetch_cells runs.
- **Fix:** First two tests now use `?platforms=P1` so both pickers render their bodies. Third test relaxed: under the new contract, fetch_cells either is NOT called or is called with empty filter tuples — both prove the garbage label never reached SQL. The assertion now accepts both outcomes.
- **Files modified:** `tests/v2/test_browse_routes.py`.
- **Commit:** `f1e002b`.

**3. [Rule 3 — Blocking] Six existing browse_service tests patched `list_parameters` (no longer imported by browse_service)**
- **Found during:** Task 2
- **Issue:** Same root cause as Item 1 — `mocker.patch.object(browse_service, "list_parameters", ...)` raised `AttributeError`.
- **Fix:** Updated each test to patch `list_parameters_for_platforms` instead. For tests that exercise the populated branch (need fetch_cells reached), the mock now returns the labels that match what the test expects to flow through to SQL — otherwise the new intersection step would drop them. `test_build_view_model_col_capped_signal` and `test_build_view_model_index_col_swap` now mock `list_parameters_for_platforms` with the full set of expected labels (35 and 1, respectively); `test_all_param_labels_sorted_by_combined_label` now passes a non-empty `selected_platforms` so the catalog is queried at all.
- **Files modified:** `tests/v2/test_browse_service.py`.
- **Commit:** `f1e002b`.

**4. [Rule 3 — Blocking] First version of `test_params_fragment_populated_with_intersection` did not mock fetch_cells**
- **Found during:** Task 2 (running new route tests)
- **Issue:** The new `POST /browse/params-fragment` route reuses `build_view_model`, which calls `fetch_cells` when selection is non-empty. The test's `MockDB` does not implement `_get_engine`, so the real cache-layer `fetch_cells` raised `AttributeError` when traversing through to ufs_service. The route's response only renders the `params_picker` block — the fetch_cells result is functionally wasted but the call still runs.
- **Fix:** Added a benign `fetch=lambda …: (df, False)` mock to the `_patch_cache` call in the new test, matching the idiom used by every other route test that exercises the populated branch.
- **Files modified:** `tests/v2/test_browse_routes.py`.
- **Commit:** `f1e002b`.

**5. [Rule 3 — Blocking] First version of `test_params_fragment_only_returns_picker_block` asserted absence of `id="picker-params-badge"`**
- **Found during:** Task 2
- **Issue:** The Parameters picker macro renders its OWN trigger-button badge with `id="picker-params-badge"` — that's the in-trigger count display, not an OOB-swap span. The assertion incorrectly conflated the macro's intrinsic badge with the OOB block from `picker_badges_oob`.
- **Fix:** Replaced the assertion with `assert "hx-swap-oob" not in body` — this correctly distinguishes "the params-fragment must be the primary swap target" from "no OOB-swap attributes are emitted by this fragment."
- **Files modified:** `tests/v2/test_browse_routes.py`.
- **Commit:** `f1e002b`.

### Tooling notes

- **`ruff check`** — the plan asks for ruff to be run; the active venv (`.venv/bin/python`) does not have ruff installed (no `ruff` module, no `.venv/bin/ruff` binary). The new code follows the existing project style (4-space indents, double-quoted strings, type annotations matching surrounding code, alphabetic imports within groups). No syntax issues; all tests pass via `.venv/bin/python -m pytest`.

## Self-Check: PASSED

- [x] `app/services/ufs_service.py` modified — `list_parameters_for_platforms` defined; `list_parameters` byte-stable except for one-line Public API addition.
- [x] `app_v2/services/cache.py` modified — `_parameters_for_platforms_cache` + lock + wrapper + `clear_all_caches` extension.
- [x] `app_v2/services/browse_service.py` modified — `params_disabled` field, intersection step, catalog source switched.
- [x] `app_v2/routers/browse.py` modified — `block_names` extended, `POST /browse/params-fragment` route added.
- [x] `app_v2/templates/browse/_picker_popover.html` modified — `disabled=False` kwarg + disabled-trigger + body-omission branch.
- [x] `app_v2/templates/browse/_filter_bar.html` modified — `<div id="params-picker-slot">` wrapper.
- [x] `app_v2/templates/browse/index.html` modified — `params_picker_oob` + `params_picker` blocks.
- [x] `tests/services/test_ufs_service.py` modified — 6 new tests added; existing tests untouched.
- [x] `tests/v2/test_cache.py` modified — 5 new tests added; existing tests untouched.
- [x] `tests/v2/test_browse_service.py` modified — 5 new tests + 6 updated tests.
- [x] `tests/v2/test_browse_routes.py` modified — `_patch_cache` updated, 3 existing tests updated, 5 new tests added.
- [x] Commit `c93db52` exists in `git log`.
- [x] Commit `f1e002b` exists in `git log`.
- [x] `pytest tests/v2/ tests/services/test_ufs_service.py -q` → 375 passed, 2 skipped.
- [x] `pytest -q` (project-wide) → 526 passed, 2 skipped.
- [x] `git diff -- app_v2/routers/ask.py` is empty (Ask byte-stable).
- [x] `git diff -- app_v2/templates/overview/` is empty (Overview byte-stable).
- [x] No stubs introduced — all rendered values are real data flowing through `build_view_model` → cache → ufs_service.
- [x] No new threat surface introduced beyond the parameterized SQL pattern already used by `fetch_cells` (same `_safe_table` allowlist, same `sa.bindparam(expanding=True)` binding).
