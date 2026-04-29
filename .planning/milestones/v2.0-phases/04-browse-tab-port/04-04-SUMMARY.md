---
phase: 04-browse-tab-port
plan: 04
subsystem: tests
tags: [browse, integration-tests, invariants, regression-guards, xss, sqli, htmx, hx-push-url, security]

# Dependency graph
requires:
  - phase: 04-browse-tab-port (plan 04-02)
    provides: BrowseViewModel orchestrator + sync def routes + HX-Push-Url canonical URL composition + module constants PARAM_LABEL_SEP / ROW_CAP / COL_CAP
  - phase: 04-browse-tab-port (plan 04-03)
    provides: browse template tree (index.html, _filter_bar.html, _picker_popover.html, _grid.html, _warnings.html, _empty_state.html) + popover-search.js + Phase 04 CSS additions
provides:
  - tests/v2/test_browse_routes.py — 12 end-to-end TestClient integration tests for GET /browse + POST /browse/grid covering URL round-trip, empty state, cap warnings, XSS escape, SQLi safety via parameterized binds, swap-axes index column, garbage-label drop with REAL fetch_cells.call_args introspection (Issue 2 fix verified)
  - tests/v2/test_phase04_invariants.py — 13 codebase static-analysis tests guarding D-03 / D-13 / D-19 / D-22 / D-34 / Plan 04-02 router-ordering / XSS-safe-filter-absent
affects: [phase-5-ask, future-regressions]

# Tech tracking
tech-stack:
  added: []   # No new dependencies — reused fastapi.testclient, pytest, pandas, urllib.parse
  patterns:
    - "Form encoding helper _post_form_pairs(client, url, pairs) — manually url-encodes the body and posts via content= with explicit Content-Type, working around httpx 0.28's drop of list-of-tuples support on data="
    - "_patch_cache(monkeypatch, *, platforms=None, params=None, fetch=None) — patches at the browse_service call-site (the import binding), NOT at app_v2.services.cache, because browse_service does `from app_v2.services.cache import ...` which copies the names into its own namespace (Pitfall 11 of the test reliability discussion)"
    - "MockDB / MockConfig fixture pattern — replaces app.state.db AFTER lifespan ran, mirrors Phase 03 isolated_summary"
    - "Recording-mock pattern for fetch_cells (MagicMock with return_value) — captures call_args.args / call_args.kwargs to introspect what flowed through the orchestrator into the SQL bind layer (real assertion, not tautological)"
    - "Static-analysis grep guards — `^\\s*(import|from)\\s+<lib>\\b` anchored regex for Python imports; substring scan for /browse/export route paths and `| safe` Jinja filter; raw character checks for v1.0 slash separator string literals (constructed at runtime to avoid self-match on the test file itself)"

key-files:
  created:
    - tests/v2/test_browse_routes.py (438 lines, 12 tests)
    - tests/v2/test_phase04_invariants.py (211 lines, 13 tests)
  modified:
    - app_v2/services/browse_service.py (rephrased two docstrings to remove literal v1.0 slash separator bytes — Rule-1 acceptance compliance, behavior unchanged)

key-decisions:
  - "Form encoding via urlencode + content= — httpx 0.28 raises TypeError on `data=` with list-of-tuples; helper `_post_form_pairs` encapsulates the workaround so every test that needs repeated form keys (multiple platforms, multiple params) goes through one consistent idiom"
  - "Patch at the call-site (`app_v2.services.browse_service.list_platforms`) NOT at the cache module — `from ... import ...` binds names into the consuming module's namespace; patching the source module would not redirect existing references in browse_service"
  - "Two-part SQLi/XSS test — POST verifies `fetch_cells` receives the literal injection string as a tuple element (no SQL interpolation); GET verifies the same string is HTML-escaped wherever echoed in the picker (XSS defense). The picker checkbox `value=` attr is the actual attack surface; the POST grid fragment doesn't render the picker, so a single test covering both planes is needed."
  - "Garbage-params test (Issue 2 mitigation verification) uses MagicMock + introspection of call_args, NOT a tautological string-comparison assertion. Asserts `items_passed in (None, (), [], frozenset())` and same for `infocategories_passed`. Proves `_parse_param_label` returned None for the malformed label and the comprehension filtered it out BEFORE `fetch_cells` was called — the actual contract Plan 04-02 promised."
  - "Static-analysis tests construct forbidden literals at runtime (`'\"' + ' / ' + '\"'`) so the test file itself does not contain the bytes that the test scans for — eliminates self-match risk. Same approach used for `/browse/export` and `| safe` substrings."

patterns-established:
  - "Browse route TestClient fixture pattern — opens TestClient, replaces app.state.db AFTER the context-manager enter, yields, restores None on teardown. Mirrors `tests/v2/test_summary_routes.py::isolated_summary` from Phase 03."
  - "Recording-mock-with-introspection pattern for service-layer behavior verification — when a contract says 'X is filtered before reaching Y', use MagicMock + call_args to assert the actual tuple shape passed to Y, not just that the response renders. Generalizes to any future test of orchestration filters (e.g. NL agent param sanitization in Phase 5)."
  - "Form encoding helper for repeated keys — applies to any future tests of FastAPI routes that consume `Annotated[list[str], Form()]` parameters. Helpers ARE worth their weight when they encapsulate a library-version workaround (httpx 0.28 deprecation)."

requirements-completed: [BROWSE-V2-01, BROWSE-V2-02, BROWSE-V2-03, BROWSE-V2-05]

# Metrics
duration: 14m
completed: 2026-04-26
---

# Phase 4 Plan 04: Integration Tests + Invariant Guards Summary

**12 end-to-end TestClient tests + 13 static-analysis invariant guards. All 25 new tests pass. Phase 1-3 regression suite still green (245 → 270 passed, 1 skipped). v1.0 test suite untouched (183 passed). Issue 2 fix from plan-checker verified — garbage-params test introspects `fetch_cells.call_args` and asserts the malformed label was DROPPED before SQL bind; no tautological assertion remains.**

## Performance

- **Duration:** ~14 min (866 seconds wall clock)
- **Started:** 2026-04-26T13:53:19Z
- **Completed:** 2026-04-26T14:07:45Z
- **Tasks:** 2
- **Files created:** 2 (test_browse_routes.py, test_phase04_invariants.py)
- **Files modified:** 1 (app_v2/services/browse_service.py — docstring rephrase only, no behavior change)

## Accomplishments

- **`tests/v2/test_browse_routes.py` (12 tests, all green)** — covers every Phase 4 success criterion from ROADMAP: filter + sticky-header layout (rendered table assertion), caps mirror v1.0 (D-24 verbatim copy assertions), URL round-trip (BROWSE-V2-05). Plus XSS defense (T-04-03-02), SQLi defense via parameterized binds (T-04-02-01), swap-axes view transform (D-16), garbage-label drop (T-04-02-02 with REAL introspection).
- **`tests/v2/test_phase04_invariants.py` (13 tests, all green)** — guards D-03 (no plotly), D-19 (no openpyxl, no csv, no /browse/export), D-22 (no export_dialog), D-34 (no async def in browse routes), D-13 (middle-dot separator only — v1.0 slash separator literal absent), Plan 04-02 wiring (browse stub gone from root.py; browse router registered before root in main.py), XSS regression (no `| safe` in browse templates), and belt-and-suspenders template scan for plotly/openpyxl/export_dialog tokens.
- **Issue 2 fix from plan-checker — VERIFIED.** The garbage-params test no longer uses the tautological `or "&lt;" not in "garbage_no_separator"` assertion. It introspects `mock_fetch_cells.call_args.args` and `.kwargs`, then asserts both the items tuple (positional arg 3) and infocategories tuple (positional arg 2) are empty when the URL carries a label without the ` · ` separator. This proves `_parse_param_label` actually filtered the malformed label out BEFORE it could be bound into the SQL.
- **httpx 0.28 form-encoding workaround** — wrote a tiny helper `_post_form_pairs(client, url, pairs)` that uses `urllib.parse.urlencode` + `client.post(url, content=body, headers={"Content-Type": "application/x-www-form-urlencoded"})`. httpx 0.28 dropped support for `data=[(...)]` (raises TypeError); this is the supported escape hatch.
- **Two-plane XSS/SQLi defense test** — the test exercises BOTH planes: POST verifies the injection string flows to `fetch_cells` as a literal tuple element (proving the SQLi mitigation); GET verifies the same string is HTML-escaped in the picker checkbox `value="..."` attribute (proving the XSS mitigation). Single test covers both attack surfaces of the same input.

## Final Test Counts

| Suite | Count | Status |
|------|-------|-------|
| `tests/v2/test_browse_routes.py` | 12 | all green |
| `tests/v2/test_phase04_invariants.py` | 13 | all green |
| `tests/v2/test_browse_service.py` (Plan 04-02) | 16 | all green |
| Full v2 suite (`tests/v2`) | 270 passed, 1 skipped | green |
| v1.0 suite (`tests/`, ignoring v2) | 183 | green |

The 1 skipped test is the Plan 04-02 tombstone for the old Phase 1 `/browse` placeholder (`test_get_browse_returns_200_with_phase_placeholder`).

## Confirmation: Exact HX-Push-Url emission

Runtime smoke verified the route emits the exact URL the test asserts:

```
$ python3 -c "from app_v2.services.browse_service import _build_browse_url; print(repr(_build_browse_url(['A', 'B'], ['cat · item'], True)))"
'/browse?platforms=A&platforms=B&params=cat%20%C2%B7%20item&swap=1'
```

The test assertion `assert push == "/browse?platforms=A&platforms=B&params=cat%20%C2%B7%20item&swap=1"` matches the route's actual emission byte-for-byte. Pitfall 6 (cosmetic %20 vs +) is verified end-to-end.

## Confirmation: garbage-params test introspects fetch_cells args (Issue 2 fix)

```
$ grep -n "items_passed" tests/v2/test_browse_routes.py
404:    if "items" in call_kwargs:
405:        items_passed = call_kwargs["items"]
408:        items_passed = None
409:    assert items_passed in (None, (), [], frozenset()), (
410:        f"garbage label leaked into items: {items_passed!r}"

$ grep -F '"&lt;" not in "garbage_no_separator"' tests/v2/test_browse_routes.py
(no output — tautological literal is GONE)
```

The recording mock pattern is in place; the test asserts on `mock_fetch_cells.call_args` directly. The previous-style assertion comparing two constants is removed.

## Confirmation: v1.0 tests untouched

```
$ .venv/bin/pytest tests/ -q --ignore=tests/v2
183 passed in 44.11s
```

No v1.0 regressions. Phase 4 is a parallel deployment; the v1.0 suite running in `app/` was not modified by any of the plans 04-01..04-04.

## Task Commits

| Task | Description | Hash |
|------|-------------|------|
| 1 | End-to-end TestClient integration tests for browse routes | `96a32d4` |
| 2 | Codebase invariant guards (Phase 04 static-analysis) | `50ff69b` |

**Plan metadata commit:** _pending — final commit covers SUMMARY + STATE + ROADMAP progress + REQUIREMENTS marks_

## Decisions Made

- **Form encoding helper instead of inline `data=` everywhere** — httpx 0.28 raises `TypeError: sequence item 0: expected a bytes-like object, tuple found` on `data=[(...)]`. The helper `_post_form_pairs(client, url, pairs)` keeps every test's call site short and the workaround documented in one place. Future tests for routes consuming `Annotated[list[str], Form()]` will reuse this helper verbatim.
- **Patch at `app_v2.services.browse_service.list_platforms` (the call-site name), NOT at `app_v2.services.cache.list_platforms`** — `browse_service` does `from app_v2.services.cache import list_platforms`, which binds the name into `browse_service`'s namespace. Patching the cache module rebinds `app_v2.services.cache.list_platforms` but does not redirect `browse_service`'s already-imported reference. The Phase 1-3 fixtures (e.g. `tests/v2/test_overview_routes.py:39`) use the same call-site-patching idiom — adopted verbatim.
- **Static-analysis tests construct forbidden literals at runtime** — patterns like `'"' + ' / ' + '"'` and `"/browse/" + "export"` and `"| " + "safe"` ensure the test file ITSELF does not contain the substring it scans for under `app_v2/`. Eliminates the self-match false-positive risk that would otherwise force ugly carve-out logic.
- **Two-plane XSS/SQLi test** — the SQLi attack surface is the SQL bind layer (POST flows through `fetch_cells`); the XSS attack surface is the picker checkbox echo (GET renders the popover). One test exercises both planes against the same injection string `' OR 1=1 --` to keep the relationship clear: parameterized SQL prevents interpolation, autoescape prevents script smuggling, both must hold simultaneously.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] httpx 0.28 dropped list-of-tuples support on `data=`**
- **Found during:** Task 1, first test execution after writing
- **Issue:** Tests using `client.post(url, data=[(...)])` raised `TypeError: sequence item 0: expected a bytes-like object, tuple found` because httpx 0.28's form encoder no longer accepts list-of-tuples (the warning message was visible in the failed test output: "Use 'content=<...>' to upload raw bytes/text content").
- **Fix:** Added the `_post_form_pairs(client, url, pairs)` helper that uses `urllib.parse.urlencode` + `content=body` + explicit `Content-Type: application/x-www-form-urlencoded` header. All 6 tests that send repeated form keys (POST /browse/grid with multiple platforms or params) now go through the helper.
- **Files modified:** `tests/v2/test_browse_routes.py`
- **Verification:** All 12 tests pass; the helper is documented in the module docstring with the rationale.
- **Committed in:** `96a32d4` (Task 1 commit, included in initial implementation)

**2. [Rule 1 - Bug] SQL injection test premise was wrong — POST grid fragment never echoes the platforms picker**
- **Found during:** Task 1 acceptance test run
- **Issue:** The plan-body sketch asserted that the injection string would be HTML-escaped in the POST `/browse/grid` response. But POST returns ONLY the named blocks (`grid`, `count_oob`, `warnings_oob`) — the picker checkboxes are NOT in those blocks. The injection string never appears in the POST response at all (which is the correct behavior; the route is a fragment endpoint). The "echoed in the response" assertion can never pass for the POST plane.
- **Fix:** Split the test into two parts: (a) POST verifies `fetch_cells` receives the injection string as a literal tuple element (the SQLi defense plane); (b) GET `/browse?platforms=<injection>` verifies the string is HTML-escaped in the picker checkbox `value=` attribute (the XSS defense plane). Both planes share the same injection input so the relationship is explicit. Catalog mock is updated so the GET render emits the injection string (otherwise the picker would not include it as a candidate).
- **Files modified:** `tests/v2/test_browse_routes.py`
- **Verification:** Both planes verified independently. POST: `assert captured["platforms"] == (injection,)`. GET: `assert "&#39; OR 1=1 --" in r_get.text`.
- **Committed in:** `96a32d4` (Task 1 commit, included in initial implementation)

**3. [Rule 1 - Bug] Acceptance grep flagged the literal `"&lt;" not in "garbage_no_separator"` inside a documentation comment**
- **Found during:** Task 1 final acceptance audit
- **Issue:** The garbage-params test docstring documented the Issue 2 fix by quoting the OLD broken assertion (`"&lt;" not in "garbage_no_separator"`) so future readers would understand what changed. The acceptance criterion `! grep -F '"&lt;" not in "garbage_no_separator"' tests/v2/test_browse_routes.py` flagged this docstring as a violation.
- **Fix:** Rephrased the docstring to describe the issue in prose ("compared a constant escaped string to a constant raw string — always True regardless of route behavior") instead of quoting the literal old assertion. Same pattern as Plan 04-02 deviation 3 and Plan 04-03 deviation 3 — strict acceptance grep collides with documentation prose.
- **Files modified:** `tests/v2/test_browse_routes.py`
- **Verification:** `grep -F '"&lt;" not in "garbage_no_separator"' tests/v2/test_browse_routes.py` → no output. Test still passes (docstring is the only thing that changed).
- **Committed in:** `96a32d4` (Task 1 commit, included in initial implementation)

**4. [Rule 1 - Bug] Acceptance test for D-13 separator flagged docstrings in `app_v2/services/browse_service.py`**
- **Found during:** Task 2 first test execution
- **Issue:** The `test_param_label_separator_is_middle_dot_not_slash` invariant scans `app_v2/services/browse_service.py` for the literal `' / '` and `" / "` byte sequences (catching v1.0 slash separator usage). Two docstrings in `browse_service.py` quoted the v1.0 separator while warning against it ("NEVER ' / ' — that is v1.0 (Pitfall 3)" and "NEVER use partition(' / ') here"). The strict acceptance grep does not distinguish docstrings from string literals.
- **Fix:** Rephrased the two docstring warnings to use prose ("the v1.0 slash separator") instead of the literal byte sequence. Same pattern as Plan 04-02 deviation 3 and Plan 04-03 deviation 3 (acceptance-grep-induced documentation rephrasing). Behavior of `_parse_param_label` is unchanged — the only edits are inside docstrings.
- **Files modified:** `app_v2/services/browse_service.py` (lines 10, 71-72 — docstring text only)
- **Verification:** `grep -c "' / '" app_v2/services/browse_service.py` → 0; `grep -c '" / "' app_v2/services/browse_service.py` → 0. All 13 invariant tests pass. All 16 Plan 04-02 browse_service unit tests still pass (no behavior regression).
- **Committed in:** `50ff69b` (Task 2 commit, included alongside the new invariant test file)

---

**Total deviations:** 4 (1 Rule-3 environmental blocker, 3 Rule-1 acceptance-compliance fixes — 2 in test file docstrings/structure, 1 in service docstrings).
**Impact on plan:** Zero scope creep. Zero new dependencies. Zero behavior changes in production code (the `browse_service.py` edits are docstring text only). All four deviations are forced by environmental reality (httpx 0.28 API change) or by the plan's own strict acceptance grep criteria. Pattern matches Plan 04-02 / 04-03 deviations.

## Issues Encountered

None blocking — both tasks executed cleanly. Each task's verification block ran before commit. The two Rule-1 fixes inside Task 1 (`_post_form_pairs` workaround + SQLi test split) were implemented inline during the TDD GREEN phase before the first commit; the 13 invariant tests in Task 2 ran green on first execution after the `browse_service.py` docstring rephrase.

## Note on httpx 0.28 form-encoding deprecation

The first test run failed with the warning `DeprecationWarning: Use 'content=<...>' to upload raw bytes/text content.` accompanying a `TypeError`. This is an upstream behavior change in httpx 0.28 (December 2024 release) that propagated into Starlette's TestClient. The fix (`urlencode` + `content=` + explicit Content-Type) is the supported escape hatch and is documented in the test module docstring + the `_post_form_pairs` helper docstring. Future test authors writing FastAPI route tests with multiple `Annotated[list[str], Form()]` parameters should reuse this helper.

## User Setup Required

None — no external service configuration, no env vars, no manual steps.

## Phase 4 Readiness Statement

**Ready for `/gsd-verify-phase 4` and `/gsd-uat-phase 4`.**

All four Phase 4 plans are complete:
- 04-01: scope lock + REQUIREMENTS/ROADMAP/PROJECT trim — `7c4f44d`+ history
- 04-02: BrowseViewModel orchestrator + sync def routes + HX-Push-Url — `8fcf143` / `e8b488e` / `67f02fe` / `3474d51`
- 04-03: 6 templates + popover-search.js + Phase 04 CSS — `d1932eb` / `04e6179` / `f4207c0` / `2784ced`
- 04-04: 12 integration tests + 13 invariant guards — `96a32d4` / `50ff69b`

All ROADMAP success criteria are covered by at least one integration test:
1. **Filter swap + sticky-header layout** — `test_post_browse_grid_swap_axes_changes_index_col` + `test_post_browse_grid_returns_fragment_not_full_page` (table HTML asserted).
2. **Caps mirror v1.0 (verbatim D-24 copy)** — `test_post_browse_grid_row_cap_warning` + `test_post_browse_grid_col_cap_warning` (both copy strings asserted byte-for-byte).
3. **URL round-trip (BROWSE-V2-05)** — `test_get_browse_pre_checks_pickers_from_url` + `test_get_browse_renders_grid_when_url_has_full_state` + `test_post_browse_grid_sets_hx_push_url_header` (full GET → render → POST → HX-Push-Url cycle).

All 13 codebase invariants enforced — any future commit that re-introduces plotly/openpyxl/csv/export_dialog/async-def-in-browse/v1.0-slash-separator/`| safe`-in-browse-templates will fail CI.

## Threat Flags

None — no new attack surface introduced by tests; tests verify mitigations on existing surface. The static-analysis guards lock in those mitigations against future regression. All threats from Plans 04-02 / 04-03 (T-04-02-01..05, T-04-03-01..08) remain mitigated and are now also pinned by automated regression tests.

## Self-Check: PASSED

- `tests/v2/test_browse_routes.py` — FOUND
- `tests/v2/test_phase04_invariants.py` — FOUND
- `.planning/phases/04-browse-tab-port/04-04-SUMMARY.md` — being written now
- Commit `96a32d4` (Task 1 — browse routes integration tests) — FOUND in `git log --oneline`
- Commit `50ff69b` (Task 2 — Phase 04 codebase invariants) — FOUND in `git log --oneline`

---
*Phase: 04-browse-tab-port*
*Completed: 2026-04-26*
