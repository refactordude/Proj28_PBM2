---
phase: 04-browse-tab-port
plan: 02
subsystem: api
tags: [browse, fastapi, service, view-model, url-roundtrip, pivot, htmx, hx-push-url, ttlcache, sync-def]

# Dependency graph
requires:
  - phase: 01-foundation-shell
    provides: app_v2/services/cache.py TTLCache wrappers (list_platforms, list_parameters, fetch_cells); pivot_to_wide_core alias on app/services/ufs_service.py; templates Jinja2Blocks instance; INFRA-05 sync-def-only convention
  - phase: 02-overview-tab-filters
    provides: get_db helper pattern (request.app.state.db); _resolve_db_name idiom (db.config.name); block_names fragment-render pattern via Jinja2Blocks
  - phase: 04-browse-tab-port (plan 04-01)
    provides: Phase 4 scope locked to 4 reqs (BROWSE-V2-04 export removed); REQUIREMENTS/ROADMAP/PROJECT internally consistent
provides:
  - app_v2/services/browse_service.py — BrowseViewModel dataclass + build_view_model orchestrator + _parse_param_label + _build_browse_url + PARAM_LABEL_SEP/ROW_CAP/COL_CAP constants
  - app_v2/routers/browse.py — sync def GET /browse + POST /browse/grid with HX-Push-Url canonical URL composition
  - Phase 1 GET /browse stub deleted from routers/root.py (browse router now owns /browse exclusively)
  - app_v2/main.py wires browse router BEFORE root (defense-in-depth ordering)
affects: [04-03, 04-04, phase-5-ask]

# Tech tracking
tech-stack:
  added: []   # No new dependencies — reused fastapi, pydantic, jinja2_fragments, cachetools, pandas
  patterns:
    - "Pattern 1 (RESEARCH.md): single orchestration function powers BOTH GET and POST — build_view_model is consumed identically by both routes; only the render mode (full page vs block_names fragment) differs"
    - "Pattern 6: block_names fragment rendering on POST returns ONLY [grid, count_oob, warnings_oob] — the persistent shell receives OOB swaps without re-rendering the filter bar"
    - "HX-Push-Url response header overrides the hx-push-url attribute (Pitfall 2) — canonical /browse?... URL pushed to history instead of /browse/grid"
    - "Pure-service pattern (no FastAPI imports inside services/) carried from Phase 2 overview_filter — service modules are framework-agnostic and unit-testable without TestClient"
    - "Pattern: middle-dot ' · ' (U+00B7) parameter-label separator — distinct from v1.0 ' / ' (Pitfall 3); module constant PARAM_LABEL_SEP single source of truth"
    - "Pattern: garbage-label silent drop (T-04-02-02 mitigation) — _parse_param_label returns None for malformed input, comprehension filters before SQL bind, never injects empty strings"

key-files:
  created:
    - app_v2/services/browse_service.py
    - app_v2/routers/browse.py
    - tests/v2/test_browse_service.py
  modified:
    - app_v2/main.py (browse router registration BEFORE root)
    - app_v2/routers/root.py (Phase 1 /browse stub deleted; /ask preserved)
    - tests/v2/test_main.py (Phase 1 /browse placeholder test skipped — tombstone with pointer to 04-03/04-04)

key-decisions:
  - "PARAM_LABEL_SEP=' · ' (UTF-8 bytes b' \\xc2\\xb7 ') as the SINGLE source of truth for InfoCategory/Item label format (D-13). Never copy v1.0's ' / ' separator (Pitfall 3)."
  - "ROW_CAP=200 / COL_CAP=30 (D-23) defined as module-level constants in browse_service.py — not hardcoded in routes. Single source of truth for v1.0 cap parity."
  - "build_view_model accepts db=None gracefully (returns fully-empty BrowseViewModel) — Phase 1 lifespan contract permits db=None when no databases are configured. No 500 on the /browse landing in that scenario."
  - "GET handler uses Query(default_factory=list) WITHOUT a literal '= []' default — Pydantic 2.13.x rejects the both-defaults form. POST handler keeps Form() with '= []' (Form supports the literal-default form)."
  - "Empty-selection short-circuit happens AFTER catalog calls (list_platforms / list_parameters) — popovers must always have the full candidate list available; only fetch_cells (the SQL hit) is gated."
  - "Browse router registered BEFORE root in main.py — defense-in-depth so an accidental /browse stub re-add to root.py cannot shadow the real router."

patterns-established:
  - "View-model dataclass per tab — BrowseViewModel mirrors Phase 02's overview-context-builder shape but typed as a frozen-ish dataclass (mutable for now; could be frozen=True if Pydantic v2 dataclasses prove desirable)"
  - "Service module is framework-agnostic (no fastapi/starlette imports) — testable without TestClient via pytest-mock at the call site (mocker.patch.object(browse_service, ...))"
  - "Router wires both GET and POST through the SAME orchestrator with identical signatures — block_names is the only render-time difference"
  - "Phase 1 stub-test tombstone pattern: when a Phase X plan replaces a Phase 1 placeholder route, mark the stub-specific test @pytest.mark.skip with a reason pointing at the future plan that supplies the real templates/integration tests"

requirements-completed: [BROWSE-V2-01, BROWSE-V2-03, BROWSE-V2-05]

# Metrics
duration: 12m
completed: 2026-04-26
---

# Phase 4 Plan 02: Browse Service + Router Summary

**Pure-Python BrowseViewModel orchestrator + sync def GET /browse + POST /browse/grid with HX-Push-Url canonical-URL composition. Replaces the Phase 1 /browse placeholder; templates ship in Plan 04-03.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-26T13:18:00Z
- **Completed:** 2026-04-26T13:30:00Z
- **Tasks:** 3
- **Files created:** 3 (browse_service.py, browse.py, test_browse_service.py)
- **Files modified:** 3 (main.py, root.py, test_main.py)

## Accomplishments

- `BrowseViewModel` dataclass (13 fields) is the single source of truth consumed by both Browse routes — full-page render and HTMX fragment render are byte-identical above the Jinja2 layer.
- `build_view_model` enforces `ROW_CAP=200`/`COL_CAP=30` (D-23) by delegating to existing TTLCache wrappers (`fetch_cells` from `app_v2/services/cache.py`) and the existing pure pivot (`pivot_to_wide_core`). No new SQL, no new pandas logic.
- Empty-selection short-circuit verified by mock: when `selected_platforms=[]` OR `selected_param_labels=[]`, `fetch_cells` is NEVER called. Catalog calls (`list_platforms` / `list_parameters`) ALWAYS run so popovers can render the full lists.
- Garbage-label defense (T-04-02-02): `_parse_param_label` returns None for any label without ` · `, the walrus comprehension drops them silently, and `fetch_cells` receives only well-formed `(InfoCategory, Item)` tuples — empty strings can never reach the SQL bind parameters.
- POST `/browse/grid` sets `HX-Push-Url` response header to the canonical `/browse?...` URL composed via `_build_browse_url(..., quote_via=urllib.parse.quote)` (Pitfall 6 — `%20` for spaces, NOT `+`).
- Phase 1 `/browse` stub removed from `routers/root.py`; browse router registered in `main.py` BEFORE `root` (defense-in-depth ordering).
- 16 unit tests in `tests/v2/test_browse_service.py` cover: middle-dot separator (3 tests), constants/dataclass shape (1 test), empty-selection short-circuit (2 tests), `fetch_cells` argument shape (1 test), cap signaling (3 tests, including index-col swap), all-param-label sort order (1 test), garbage-label defense (1 test), URL round-trip (3 tests), bonus dataclass introspection (1 test).

## Task Commits

Each task was committed atomically:

1. **Task 1 RED — failing tests for browse_service** — `8fcf143` (test)
2. **Task 1 GREEN — browse_service orchestrator + view-model** — `e8b488e` (feat)
3. **Task 2 — browse router (GET /browse + POST /browse/grid)** — `67f02fe` (feat)
4. **Task 3 — wire browse router; remove Phase 1 /browse stub** — `3474d51` (chore)

**Plan metadata:** _pending — final commit covers SUMMARY + STATE + ROADMAP progress + REQUIREMENTS marks_

## Files Created/Modified

- **`app_v2/services/browse_service.py` (created, 192 lines)** — BrowseViewModel dataclass; `build_view_model(db, db_name, selected_platforms, selected_param_labels, swap_axes) -> BrowseViewModel`; `_parse_param_label(label) -> tuple|None`; `_build_browse_url(platforms, params, swap) -> str`; constants `PARAM_LABEL_SEP=' · '`, `ROW_CAP=200`, `COL_CAP=30`. NO FastAPI/Starlette imports — pure orchestration.
- **`app_v2/routers/browse.py` (created, 128 lines)** — `get_db` helper, `_resolve_db_name` helper, `browse_page` (GET /browse, sync def, full-page render), `browse_grid` (POST /browse/grid, sync def, fragment render with `block_names=["grid", "count_oob", "warnings_oob"]` and `HX-Push-Url` response header).
- **`tests/v2/test_browse_service.py` (created, 378 lines)** — 16 tests, all green; uses `pytest-mock` `mocker.patch.object(browse_service, ...)` at the call site (NOT at the cache module — verified Pitfall 11 of test reliability).
- **`app_v2/main.py` (modified)** — added `from app_v2.routers import browse` import + `app.include_router(browse.router)` BEFORE `root.router` (lines 137-155).
- **`app_v2/routers/root.py` (modified)** — deleted Phase 1 `browse_page` function (lines 17-24 in the pre-edit version); preserved `ask_page` for Phase 5; updated module docstring to reflect `/ask`-only scope.
- **`tests/v2/test_main.py` (modified)** — applied `@pytest.mark.skip` to `test_get_browse_returns_200_with_phase_placeholder` with a reason pointing at Plan 04-03 / 04-04 (where templates and integration tests land).

## BrowseViewModel Final Field List

13 fields, exactly as sketched in RESEARCH.md Pattern 1 — no deviations:

| Field | Type | Purpose |
|------|------|---------|
| `df_wide` | `pd.DataFrame` | Pivoted wide-form data (empty when `is_empty_selection=True`) |
| `row_capped` | `bool` | True when `fetch_cells` truncated >200 rows |
| `col_capped` | `bool` | True when `pivot_to_wide_core` truncated >30 value cols |
| `n_value_cols_total` | `int` | Requested label count — N for "Showing first 30 of {N} parameters" |
| `n_rows` | `int` | Rows actually shown |
| `n_cols` | `int` | Value-cols actually shown (≤ COL_CAP) |
| `swap_axes` | `bool` | Echoed for UI toggle state |
| `selected_platforms` | `list[str]` | Echo for popover pre-check |
| `selected_params` | `list[str]` | Echo for popover pre-check (combined labels) |
| `all_platforms` | `list[str]` | Full DB catalog (popover candidates) |
| `all_param_labels` | `list[str]` | Full DB catalog, alphabetically by combined label |
| `is_empty_selection` | `bool` | Drives empty-state template branch |
| `index_col_name` | `str` | "PLATFORM_ID" (default) or "Item" (swap_axes) |

## Confirmation: PARAM_LABEL_SEP byte sequence

```
$ python3 -c "import re; s=open('app_v2/services/browse_service.py').read(); m=re.search(r'PARAM_LABEL_SEP\s*=\s*\"[^\"]*\"', s); print('bytes:', m.group().encode('utf-8'))"
bytes: b'PARAM_LABEL_SEP = " \xc2\xb7 "'
```

The constant is exactly `" \xc2\xb7 "` (UTF-8 — middle dot U+00B7 wrapped by ASCII spaces). The literal `" / "` (v1.0 separator) appears nowhere in `browse_service.py` (verified `grep -c '" / "' app_v2/services/browse_service.py` → 0).

## Confirmation: NO async def in browse.py

```
$ grep -cE "^\s*async\s+def" app_v2/routers/browse.py
0
$ grep -cE "^\s*def\s+browse_page\b" app_v2/routers/browse.py
1
$ grep -cE "^\s*def\s+browse_grid\b" app_v2/routers/browse.py
1
```

Both routes are sync `def` per INFRA-05 + D-34. SQLAlchemy is sync; FastAPI dispatches `def` to the threadpool.

## Wiring sequence in main.py

Final include order (lines 145-155):

```python
from app_v2.routers import overview   # owns GET /
from app_v2.routers import platforms  # owns /platforms/*
from app_v2.routers import summary    # owns POST /platforms/{pid}/summary
from app_v2.routers import browse     # owns /browse + /browse/grid (Phase 04)
from app_v2.routers import root       # owns /ask (Phase 5 stub)

app.include_router(overview.router)
app.include_router(platforms.router)
app.include_router(summary.router)
app.include_router(browse.router)     # BEFORE root (defense-in-depth)
app.include_router(root.router)
```

`browse` BEFORE `root` per the plan's rationale: even if a future commit accidentally re-adds a `/browse` stub to `root.py`, the real browse router still wins.

## Test count and edge cases discovered during TDD

**Final test count:** 16 (plan asked for ≥15). All passing.

The tests exercised one edge case the plan-body sketch didn't explicitly call out:
- **Test 7 (`test_build_view_model_fetch_cells_args`)** asserts that platforms are passed in INPUT order (not sorted) to `fetch_cells`, while `infocategories` and `items` ARE sorted (de-duplicated set → sorted tuple). This matches the plan's natural-language behavior but is worth pinning down with a test because it crystallizes the contract: `selected_platforms` flows through verbatim to `tuple(...)`, while parsed `(cat, item)` tuples flow through `sorted({...})`.

The walrus operator `(p := _parse_param_label(lbl))` in the comprehension is supported by Python 3.13 (project venv); no compatibility concerns.

## Decisions Made

- **Pydantic v2 + FastAPI 0.136.x signature constraint** (deviation Rule 3 below) — `Query(default_factory=list)` and a literal `= []` default cannot coexist on the same parameter; chose `default_factory` only for GET. POST `Form()` keeps the literal `= []` form (Pydantic accepts that pattern for `Form`). The plan's acceptance regex still passes (it grep-checks the canonical idiom, which is met).
- **`db is None` graceful handling** — instead of hard-erroring when lifespan failed to build an adapter, `build_view_model` returns the fully-empty BrowseViewModel. Phase 1 smoke-test contract permits no-database startup; the route stays responsive in that scenario.
- **Catalog calls always run, even on empty selection** — popovers need `all_platforms` and `all_param_labels` to render, regardless of selection state. The empty-selection short-circuit gates only `fetch_cells` (the SQL hit). Catalog calls are TTLCache-backed (300s TTL) so the cost is negligible after first hit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pydantic v2 + FastAPI 0.136.x reject `Query(default_factory=list)` + `= []` together**
- **Found during:** Task 2 (smoke test `python -c "from app_v2.routers.browse import router"`)
- **Issue:** `TypeError: cannot specify both default and default_factory` raised at import time. The plan body's exact code mirrored from RESEARCH.md uses both forms (see plan body line 439-440). Pydantic 2.13.3 + FastAPI 0.136.1 reject this combination at module load.
- **Fix:** Removed the literal `= []` defaults from the GET parameter signature; kept ONLY `Query(default_factory=list)`. Empty-omitted query keys still resolve to `[]` (NOT None) — verified by smoke test. POST `Form()` is unaffected and keeps its literal `= []` defaults (Pydantic accepts that form for Form fields).
- **Files modified:** `app_v2/routers/browse.py`
- **Verification:** `python -c "from app_v2.routers.browse import router; print([(r.path, sorted(r.methods)) for r in router.routes])"` → `[('/browse', ['GET']), ('/browse/grid', ['POST'])]` (success). Plan acceptance regex `Annotated\[list\[str\], Query(default_factory=list)\]` still passes (grep returns 2 — both `platforms` and `params`).
- **Committed in:** `67f02fe` (Task 2 commit)

**2. [Rule 3 - Blocking] Phase 1 stub test asserts copy that no longer exists**
- **Found during:** Task 3 acceptance criterion #6 (`pytest tests/v2/test_main.py ... -x -q`)
- **Issue:** `test_get_browse_returns_200_with_phase_placeholder` asserts `"Coming in Phase 4"` is in the response body. After deleting the Phase 1 stub from `routers/root.py`, the new browse router renders `browse/index.html` which doesn't exist until Plan 04-03. Test fails with `jinja2.exceptions.TemplateNotFound: 'browse/index.html'`.
- **Fix:** Marked the test `@pytest.mark.skip(reason=...)` with a tombstone pointing at Plan 04-03 (template) and Plan 04-04 (integration tests). The test stays in the file as documentation of the deleted stub but does not run. Alternative considered: outright delete — rejected because the tombstone preserves traceability.
- **Files modified:** `tests/v2/test_main.py`
- **Verification:** `pytest tests/v2/test_main.py ... -x -q` → 83 passed, 1 skipped (the tombstone).
- **Committed in:** `3474d51` (Task 3 commit)

**3. [Rule 1 - Bug] Comment/docstring strings violated grep acceptance**
- **Found during:** Task 1 acceptance criterion `grep -c '" / "' app_v2/services/browse_service.py` → expected 0
- **Issue:** A comment "NEVER \" / \" (v1.0 separator)" contained the literal `" / "` byte sequence the acceptance grep flags. Strict regex acceptance forced removal of the literal even from documentation.
- **Fix:** Rephrased the comment to "NEVER the v1.0 slash separator" — meaning preserved, no literal `" / "` bytes.
- **Files modified:** `app_v2/services/browse_service.py`
- **Verification:** `grep -c '" / "' app_v2/services/browse_service.py` → 0.
- **Committed in:** `e8b488e` (Task 1 commit, included in initial implementation)

**4. [Rule 1 - Bug] Router docstring contained literal `/browse/clear`**
- **Found during:** Task 2 acceptance criterion `grep -c '/browse/clear' app_v2/routers/browse.py` → expected 0
- **Issue:** The `browse_grid` docstring described "no separate /browse/clear route exists" — meaningful prose but the literal substring violated the strict grep that prevents an accidental future addition of that route.
- **Fix:** Rephrased to "no separate clear endpoint exists per CONTEXT.md decision D-18" — meaning preserved, no literal `/browse/clear` bytes.
- **Files modified:** `app_v2/routers/browse.py`
- **Verification:** `grep -c '/browse/clear' app_v2/routers/browse.py` → 0.
- **Committed in:** `67f02fe` (Task 2 commit, included in initial implementation)

---

**Total deviations:** 4 auto-fixed (2 Rule-3 blocking, 2 Rule-1 grep-acceptance compliance bugs).
**Impact on plan:** Two Rule-3 fixes were forced by environmental reality (Pydantic v2 signature constraint; Phase 1 test must accept Phase 4 takeover). Two Rule-1 fixes were forced by the plan's own strict grep acceptance criteria (the documentation prose collided with the literal-string guards). All four fixes preserve the plan's intent verbatim. Zero scope creep — no new features, no new dependencies.

## Issues Encountered

None — three tasks executed cleanly. Each task's verification block ran before commit.

## Note on Template Rendering

**HTML rendering will fail until Plan 04-03 creates the templates** — this is expected and documented in the plan's `<output>` block. The router is wired correctly; an actual HTTP `GET /browse` request lands at the new browse router, calls `build_view_model`, then attempts to render `browse/index.html` which doesn't exist yet → 500 via the global exception handler. Plan 04-03 ships:
- `app_v2/templates/browse/index.html` (full page + named blocks)
- `app_v2/templates/browse/_filter_bar.html`, `_picker_popover.html`, `_grid.html`, `_empty_state.html`, `_cap_warnings.html`
- `app_v2/static/js/popover-search.js`

After Plan 04-03 lands, Plan 04-04 will add full-stack integration tests (TestClient → GET /browse with full query string → assert pre-rendered grid HTML).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Plan 04-03** can begin immediately — the router is wired and the view model is the single source of truth for template context. Templates only need to consume the BrowseViewModel fields documented above.
- **Plan 04-04** integration tests can rely on:
  - Both `/browse` and `/browse/grid` routes present in `app.routes`
  - `HX-Push-Url` header set on POST responses
  - Empty-selection short-circuit returns BrowseViewModel without DB call (mock-friendly)
  - Garbage-label defense — passing `?params=garbage` produces empty grid, not 500

## Threat Flags

None — no new attack surface beyond what the plan's threat register (`<threat_model>`) already enumerates. The Browse routes consume parameterized SQL via `fetch_cells_core` (T-04-02-01 mitigated by `sa.bindparam(expanding=True)` upstream), gracefully drop garbage labels (T-04-02-02 mitigated by `_parse_param_label` returning None), are bounded by the 200-row SQL `LIMIT` (T-04-02-03 — DoS bound), surface 500s via the existing INFRA-02 exception handler with no schema/SQL leaks (T-04-02-04 — already mitigated globally), and use `quote_via=urllib.parse.quote` for `HX-Push-Url` cosmetics (T-04-02-05 mitigated by Pitfall 6 fix).

## Self-Check: PASSED

- `app_v2/services/browse_service.py` — FOUND
- `app_v2/routers/browse.py` — FOUND
- `tests/v2/test_browse_service.py` — FOUND
- `.planning/phases/04-browse-tab-port/04-02-SUMMARY.md` — FOUND
- Commit `8fcf143` (Task 1 RED — failing tests) — FOUND in `git log --oneline --all`
- Commit `e8b488e` (Task 1 GREEN — browse_service implementation) — FOUND in `git log --oneline --all`
- Commit `67f02fe` (Task 2 — browse router) — FOUND in `git log --oneline --all`
- Commit `3474d51` (Task 3 — wire router + delete stub) — FOUND in `git log --oneline --all`

---
*Phase: 04-browse-tab-port*
*Completed: 2026-04-26*
