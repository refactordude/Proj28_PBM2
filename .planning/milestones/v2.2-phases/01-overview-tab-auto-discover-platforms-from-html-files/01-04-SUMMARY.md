---
phase: 01-overview-tab-auto-discover-platforms-from-html-files
plan: 04
subsystem: api
tags: [fastapi, htmx, staticfiles, routers, joint-validation, ai-summary, refactor]

# Dependency graph
requires:
  - phase: 01-overview-tab-auto-discover-platforms-from-html-files/01-01
    provides: summary/_success.html + _error.html parameterized with entity_id + summary_url
  - phase: 01-overview-tab-auto-discover-platforms-from-html-files/01-02
    provides: build_joint_validation_grid_view_model + JV_ROOT + JointValidationRow + _sanitize_link + get_parsed_jv
  - phase: 01-overview-tab-auto-discover-platforms-from-html-files/01-03
    provides: get_or_generate_jv_summary returning a BARE SummaryResult (text/llm_name/llm_model/generated_at)
provides:
  - app_v2/main.py — StaticFiles mount /static/joint_validation BEFORE /static; lifespan mkdir content/joint_validation/; joint_validation router registered
  - app_v2/routers/overview.py — rewritten GET / + GET /overview + POST /overview/grid for Joint Validation; legacy POST /overview/add deleted; legacy curated-Platform helpers deleted
  - app_v2/routers/joint_validation.py — GET /joint_validation/{id} detail route + POST /joint_validation/{id}/summary AI Summary route (always-200)
affects: [01-05-PLAN.md, 01-06-PLAN.md]

# Tech tracking
tech-stack:
  added: []  # No new deps; all from earlier plans
  patterns:
    - "StaticFiles mount registration order matters — child mount /static/joint_validation registered BEFORE parent /static so longest-prefix wins (Pitfall 10)"
    - "HX-Push-Url must be set on the constructed TemplateResponse — FastAPI's parameter-Response merge does NOT apply when the route returns its own Response object"
    - "Path(pattern=r'^\\d+$') at the FastAPI parameter layer is the first-line path-traversal defense — non-numeric IDs return 422 before any filesystem touch"
    - "Always-200 contract for AI Summary route — never raises; cfg-None branch BEFORE try/except; exceptions classified to user-readable strings via summary_service._classify_error"
    - "Backward-compat alias key (platform_id alongside entity_id + summary_url) keeps the parameterized template render-stable across both /platforms and /joint_validation surfaces"
    - "Transitional context aliases (active_filter_counts + all_platform_ids=[]) bridge the JV vm to the still-Platform-shaped Phase 5 templates so GET /overview returns 200 in the wave-3 interim state — Plan 05 deletes the aliases"

key-files:
  created:
    - app_v2/routers/joint_validation.py
  modified:
    - app_v2/main.py
    - app_v2/routers/overview.py
    - tests/v2/test_main.py
    - tests/v2/test_summary_routes.py
    - tests/v2/test_summary_integration.py
    - tests/v2/test_content_routes.py

key-decisions:
  - "Drop the unused PAGE_ID_PATTERN + discover_joint_validations imports from routers/joint_validation.py — the route uses an inline regex Path(pattern=...) and the listing-side discovery lives in overview.py only"
  - "Set HX-Push-Url on the constructed TemplateResponse, NOT via an injected `Response` parameter — the latter has no effect when the handler returns its own response. Mirrors Phase 5 routers/overview.py:349-358"
  - "Pass active_filter_counts + all_platform_ids=[] as transitional aliases on the JV listing context so the still-Phase-5-shaped templates render to 200 — Plan 05 rewrites the templates and removes the bridge"
  - "Skip three legacy test_content_routes.py tests (test_overview_row_ai_button_*, test_overview_has_global_summary_modal) instead of refactoring them — they test deleted POST /overview/add and the curated-Platform row markup; Plan 06 ships JV-shaped equivalents"
  - "Update test_summary_routes.py + test_summary_integration.py + test_content_routes.py fixtures to drop the overview_mod.CONTENT_DIR + overview_mod.list_platforms monkeypatches that referenced deleted attributes — the platforms-side detail/summary tests under those fixtures only need platforms_mod.CONTENT_DIR"

patterns-established:
  - "Mount-before-/static idiom for child static-prefix mounts — documented in main.py with a Pitfall 10 reference"
  - "Always-200 AI Summary route as a copy-stable shape across /platforms and /joint_validation (cfg-None branch, X-Regenerate canonical parsing, render_markdown(result.text) in the router, age_s computed from result.generated_at) — both routers now follow byte-stable lines for the LLM call shell"

requirements-completed: [D-JV-01, D-JV-07, D-JV-09, D-JV-12, D-JV-13, D-JV-14, D-JV-15, D-JV-16]

# Metrics
duration: 19min
completed: 2026-04-30
---

# Phase 01 Plan 04: Wire data layer to HTTP routes — JV listing + detail + AI Summary

**Routers/main.py rewired for Joint Validation: `/static/joint_validation` mount + lifespan mkdir, `/overview` listing now reads `build_joint_validation_grid_view_model(JV_ROOT, ...)` (deletes POST /overview/add and curated-Platform helpers per D-JV-07 + D-JV-09), and a new `routers/joint_validation.py` module exposes `GET /joint_validation/{id}` (detail) + `POST /joint_validation/{id}/summary` (AI Summary always-200) — three atomic commits, 109 tests green across the touched modules; the 5 plan-tolerated test files (test_overview_*, test_phase05_invariants) remain broken and will be deleted in Plan 06.**

## Performance

- **Duration:** ~19 min
- **Started:** 2026-04-30T11:36:32Z
- **Completed:** 2026-04-30T11:55:41Z
- **Tasks:** 3
- **Files created:** 1 (routers/joint_validation.py — 226 LOC)
- **Files modified:** 6 (main.py +27 / -0; routers/overview.py rewritten 370 → 210 LOC; 4 test fixture cleanups)

## Accomplishments

- **Task 1 — main.py wiring (D-JV-13).** Added the StaticFiles mount for `/static/joint_validation` BEFORE the existing `/static` mount (Pitfall 10 — Starlette dispatches mounts by registration order; longest-prefix-first is NOT automatic). `html=False` and `follow_symlink=False` set explicitly even though they're defaults — documents the safe minimal config. Added `jv_dir = Path("content/joint_validation")` mkdir inside the existing lifespan body so the StaticFiles mount has a guaranteed directory at startup AND the drop-folder workflow (D-JV-09) works on cold start. Registered the new `joint_validation` router between `summary` and `browse` so the JV detail + summary routes are reachable.
- **Task 2 — overview.py rewrite (D-JV-01, D-JV-07, D-JV-09, D-JV-12, D-JV-14).** GET `/` + GET `/overview` now build a `JointValidationGridViewModel` from `JV_ROOT`; POST `/overview/grid` returns the same three OOB blocks (`grid`, `count_oob`, `filter_badges_oob`) and pushes a canonical `/overview?status=...&customer=...&...&sort=...&order=...` URL via `HX-Push-Url`. Deleted the legacy POST `/overview/add` route along with `_resolve_curated_pids`, `_entity_dict`, `_build_overview_context`, and the `OverviewEntity` / `DuplicateEntityError` imports. KEPT `_parse_filter_dict` and `_build_overview_url` verbatim — JV-agnostic with the same 6 query keys. Sync `def` preserved (INFRA-05).
- **Task 3 — routers/joint_validation.py (D-JV-12, D-JV-15, D-JV-16).** `GET /joint_validation/{confluence_page_id}` returns 404 when `index.html` is missing (HTTPException, regular non-summary route convention); on hit it builds a `JointValidationRow` (with `_sanitize_link` applied so dangerous schemes can't reach the row) and renders `joint_validation/detail.html` (template ships in Plan 05). `POST /joint_validation/{confluence_page_id}/summary` is the always-200 AI Summary route, mirroring `routers/summary.py:113-180` byte-stable except for the service call name and entity prefix:
  - canonical helpers (`resolve_active_llm` + `resolve_active_backend_name`)
  - `cfg is None` early-return BEFORE `try/except` with the canonical reason `"LLM not configured — set one in Settings"`
  - canonical X-Regenerate parsing (`(x_regenerate or "").lower() == "true"`)
  - canonical templates import (`from app_v2.templates import templates`)
  - canonical `render_markdown` import (`from app_v2.services.content_store import render_markdown`)
  - canonical bare-SummaryResult shape — router computes `summary_html = render_markdown(result.text)` and `age_s = max(0, int((datetime.now(timezone.utc) - result.generated_at).total_seconds()))`
- **Tests stayed green: 109 passed across the four direct-impact suites** (test_main + test_summary_routes + test_summary_service + test_summary_integration + the 4 new JV suites). The wider plan-tolerated suite (with the 5 documented `--ignore` files) shows **331 passed / 5 skipped** with zero regressions outside the 5 known-broken legacy files that Plan 06 deletes.

## Task Commits

Each task was committed atomically:

1. **Task 1 — Mount + lifespan + router register** — `56d8327` (feat)
2. **Task 2 — Rewrite overview router for JV listing** — `45e520b` (feat)
3. **Task 3 — Add routers/joint_validation.py + test fixture cleanups** — `1581900` (feat)

## Files Created / Modified

- **Created:** `app_v2/routers/joint_validation.py` (226 LOC). Two routes (detail + summary). Imports the canonical templates singleton, the BARE-SummaryResult-returning service, and `render_markdown` from `content_store`. Sync `def`. Always-200 contract with `_render_error_fragment` helper.
- **Modified:** `app_v2/main.py` (+27 LOC). Three additions: lifespan mkdir for `content/joint_validation/`, StaticFiles mount before `/static`, joint_validation router registered between summary and browse.
- **Modified:** `app_v2/routers/overview.py` (370 → 210 LOC, net −160). Imports trimmed (no more `OverviewEntity` / `DuplicateEntityError` / `add_overview` / `load_overview` / `read_yaml_entities` / `OverviewGridViewModel` / `build_overview_grid_view_model` / `read_frontmatter` / `CONTENT_DIR_DEFAULT` / `overview_filter` / `parse_platform_id` / `get_year` / `list_platforms` / `resolve_active_backend_name` / `Depends` / `Path as _Path` / `DBAdapter`). Routes consolidated to: `GET /` + `GET /overview` (JV listing) + `POST /overview/grid` (JV fragment swap with HX-Push-Url). Legacy POST `/overview/add` route + `_resolve_curated_pids` + `_entity_dict` + `_build_overview_context` helpers gone.
- **Modified:** `tests/v2/test_main.py` — `crashing_client` fixture re-targets monkey-patch from the deleted `_build_overview_context` to `build_joint_validation_grid_view_model` so the catch-all 500-handler assertions still exercise the GET /overview path.
- **Modified:** `tests/v2/test_summary_routes.py` + `tests/v2/test_summary_integration.py` — drop monkeypatches against `overview_mod.CONTENT_DIR` and `overview_mod.list_platforms` (deleted attributes); the platforms-side summary route under test reads `platforms_mod.CONTENT_DIR`.
- **Modified:** `tests/v2/test_content_routes.py` — same fixture cleanup, plus three tests skipped (`test_overview_row_ai_button_disabled_when_no_content`, `test_overview_row_ai_button_enabled_when_content_exists`, `test_overview_has_global_summary_modal`) — they test the deleted POST `/overview/add` affordance + curated-Platform row markup; Plan 06 ships the JV-shaped equivalents.

## Route List Snapshot

After this plan, the relevant routes registered on `app`:

| Method | Path                                              | Owner module                                         | Purpose                                          |
| ------ | ------------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------ |
| GET    | `/`                                               | `app_v2/routers/overview.py`                         | Joint Validation listing (alias of `/overview`)  |
| GET    | `/overview`                                       | `app_v2/routers/overview.py`                         | Joint Validation listing                         |
| POST   | `/overview/grid`                                  | `app_v2/routers/overview.py`                         | HTMX fragment swap (3 OOB blocks, HX-Push-Url)   |
| GET    | `/joint_validation/{confluence_page_id}`          | `app_v2/routers/joint_validation.py` (NEW)           | Detail page (properties + iframe sandbox)        |
| POST   | `/joint_validation/{confluence_page_id}/summary`  | `app_v2/routers/joint_validation.py` (NEW)           | AI Summary always-200                            |
| (mount)| `/static/joint_validation`                        | `app_v2/main.py` (NEW StaticFiles mount)             | Serves Confluence-exported HTML for the iframe   |

Removed by this plan:

| Method | Path                  | Was in module                  | Reason                                                                     |
| ------ | --------------------- | ------------------------------ | -------------------------------------------------------------------------- |
| POST   | `/overview/add`       | `app_v2/routers/overview.py`   | D-JV-07 + D-JV-09 — drop-folder workflow only; no in-app form              |

## Block Resolution Confirmation

The plan's `<output>` section asks the SUMMARY to confirm the planning-round blocking concerns are resolved:

- **BLOCK-01 (D-JV-09 in requirements):** Resolved at plan-frontmatter level — `requirements: [D-JV-01, D-JV-07, D-JV-09, D-JV-12, D-JV-13, D-JV-14, D-JV-15, D-JV-16]` is the requirement set marked complete by this plan; D-JV-09 (drop-folder workflow / no-add-form) is honored by the deletion of POST `/overview/add` and by the re-glob-every-request behavior baked into the GET handlers.
- **BLOCK-04 (SummaryResult shape):** Resolved. `routers/joint_validation.py` constructs the success-template context from `result.text` (markdown → `summary_html`), `result.llm_name`, `result.llm_model`, and `result.generated_at` (→ `cached_age_s`). The phantom fields `result.summary_html` / `result.backend_name` / `result.cached_age_s` are NOT referenced (acceptance grep returns zero matches).
- **BLOCK-05 (resolve_active_llm):** Resolved. The router calls `resolve_active_llm(settings, request)` and `resolve_active_backend_name(settings, request)` — the canonical names. The wrong name `resolve_llm_config` returns zero grep matches.
- **BLOCK-06 (X-Regenerate parsing):** Resolved. `regenerate = (x_regenerate or "").lower() == "true"` — only the literal string `"true"` triggers regenerate. The wrong shape `regenerate = x_regenerate is not None` returns zero grep matches.
- **BLOCK-07 (templates import):** Resolved. The router imports `from app_v2.templates import templates` directly — every other router in the project uses this exact path. The fragile `from app_v2.routers.overview import templates` returns zero grep matches.
- **WARN-01 (cfg is None branch):** Resolved. `if cfg is None:` is present BEFORE the `try/except` and returns the canonical reason string `"LLM not configured — set one in Settings"` — byte-equal to `routers/summary.py:135`.

## Decisions Made

- **Drop unused imports `PAGE_ID_PATTERN` + `discover_joint_validations`** from `routers/joint_validation.py`. The plan's action template listed them in the import block, but the router uses an inline `Path(pattern=r"^\d+$")` regex (defense-in-depth at the FastAPI parameter layer) and never calls `discover_joint_validations` (the listing-side glob lives in `overview.py` only). Removing them keeps the import surface honest.
- **Set `HX-Push-Url` on the constructed `TemplateResponse`** (`response.headers["HX-Push-Url"] = ...`) instead of via an injected `Response` parameter. The injected `Response` mechanism only works when FastAPI is constructing the response itself (e.g., when the handler returns a dict / model and FastAPI builds the JSONResponse). When the handler returns its own response object, the returned object's headers are authoritative — the injected-Response merge does not apply. Verified empirically: with the parameter approach the header was missing from the wire-level response. Mirrors Phase 5's pattern at `routers/overview.py:349-358`.
- **Pass `active_filter_counts` + `all_platform_ids=[]` transitional aliases** on the JV listing context. The Phase 5 templates still expect these top-level keys (`_filter_bar.html:74` references `active_filter_counts.values() | sum`; `index.html:62` references `all_platform_ids` for the legacy "Add platform" datalist). The aliases keep GET /overview returning 200 in the wave-3 interim state. Plan 05 rewrites the templates to read `vm.active_filter_counts` directly and removes the legacy form, at which point the bridge becomes dead context (harmless; deletable in a follow-up cleanup).
- **Skip three legacy `test_content_routes.py` tests** instead of refactoring them. The tests exercise the deleted POST `/overview/add` affordance and the curated-Platform row markup. Their behavioral target is gone-by-design (D-JV-07 + D-JV-09); the JV-shaped equivalents will ship in Plan 06. A `pytest.mark.skip` with a reason that names Plan 04 + Plan 05 + Plan 06 is the cleanest way to keep test discovery clean without losing the historical context.
- **Update `tests/v2/test_summary_routes.py` + `test_summary_integration.py` + `test_content_routes.py` fixtures** to drop the monkeypatches against `overview_mod.CONTENT_DIR` and `overview_mod.list_platforms`. Both attributes are deleted in Task 2; the platforms-side summary route under those fixtures only needs `platforms_mod.CONTENT_DIR` (still present). The fixture-only edit keeps the tests' intent intact.

## Deviations from Plan

### Rule 3 — Auto-fix blocking: Pydantic Form() / default_factory incompatibility

**Found during:** Task 2 first verify run.

**Issue:** The plan's action template specified `Form(default_factory=list)] = []` for the POST handler form parameters. Pydantic v2.13.x + FastAPI 0.136.x reject this combination ("cannot specify both default and default_factory"). The exact same lesson is documented inline in the pre-existing GET handler (lines 188-193 of the original Phase 5 file). Reused that comment near the rewritten POST handler.

**Fix:** Use `Form()] = []` (literal default only) — matches the pre-Phase-5 router idiom; empty omitted form key still resolves to `[]`. No semantic change.

**Files modified:** `app_v2/routers/overview.py` (POST handler signature).

**Commit:** `45e520b`.

### Rule 3 — Auto-fix blocking: HX-Push-Url not propagating via injected Response

**Found during:** Task 2 second verify run.

**Issue:** First implementation followed the plan's action template literally with `def post_overview_grid(request, response: Response, ...): ...; response.headers["HX-Push-Url"] = url; return templates.TemplateResponse(...)`. The header was MISSING from the wire-level response — FastAPI's parameter-Response merge does not apply when the route returns its own Response object. The returned object's headers are authoritative.

**Fix:** Capture `response = templates.TemplateResponse(...)`, then `response.headers["HX-Push-Url"] = ...`, then `return response`. Mirrors Phase 5's pattern at `routers/overview.py:349-358`. Removed the unused `Response` import.

**Files modified:** `app_v2/routers/overview.py`.

**Commit:** `45e520b`.

### Rule 3 — Auto-fix blocking: Phase 5 templates require legacy top-level context keys

**Found during:** Task 2 first end-to-end TestClient verify.

**Issue:** The plan's action template specified `ctx = {"vm": vm, "selected_filters": filters, "active_tab": "overview"}` — three keys only. The still-Phase-5-shaped templates need `active_filter_counts` (top-level) for `_filter_bar.html:74` and `_grid.html:116`, plus `all_platform_ids` for `index.html:62` (legacy "Add platform" datalist). With only the three keys, GET /overview returned 500 (Jinja2 UndefinedError).

**Fix:** Add `active_filter_counts=vm.active_filter_counts` (mirror the dict on the vm at the top level) and `all_platform_ids=[]` (legacy form datalist; the form still renders but the datalist is empty and submitting it 404s — which is the desired post-D-JV-07 behavior). Documented as transitional aliases that Plan 05 deletes when it rewrites the templates.

**Files modified:** `app_v2/routers/overview.py`.

**Commit:** `45e520b`.

### Rule 3 — Auto-fix blocking: Test fixtures referenced deleted overview attributes

**Found during:** Task 3 broader regression run.

**Issue:** `tests/v2/test_main.py::crashing_client`, `tests/v2/test_summary_routes.py::isolated_summary`, `tests/v2/test_summary_integration.py::integrated_app`, and `tests/v2/test_content_routes.py::isolated_content` all monkeypatched `overview_mod.CONTENT_DIR` (and the latter two also `overview_mod.list_platforms`). Task 2's deletions removed both attributes — fixture setup raised `AttributeError`, blocking 23 tests.

**Fix:**
- `test_main.py::crashing_client` — re-targets the monkey-patch to `build_joint_validation_grid_view_model` (the new GET /overview entry point) so the catch-all 500-handler assertions still exercise the GET /overview path. Two assertions still pass.
- `test_summary_routes.py::isolated_summary` + `test_summary_integration.py::integrated_app` + `test_content_routes.py::isolated_content` — drop the `overview_mod.CONTENT_DIR` + `overview_mod.list_platforms` monkeypatches entirely. The platforms-side summary route under those fixtures only needs `platforms_mod.CONTENT_DIR` (still patched).

**Files modified:** `tests/v2/test_main.py`, `tests/v2/test_summary_routes.py`, `tests/v2/test_summary_integration.py`, `tests/v2/test_content_routes.py`.

**Commits:** `45e520b` (test_main.py), `1581900` (others).

### Rule 3 — Auto-fix blocking: Three legacy tests assert against deleted POST /overview/add behavior

**Found during:** Task 3 broader regression run.

**Issue:** `tests/v2/test_content_routes.py::test_overview_row_ai_button_disabled_when_no_content`, `test_overview_row_ai_button_enabled_when_content_exists`, and `test_overview_has_global_summary_modal` all start with `client.post("/overview/add", data={"platform_id": _PID})` and `assert add_r.status_code == 200`. POST /overview/add now returns 404 (deleted by D-JV-07 + D-JV-09).

**Fix:** Add `@pytest.mark.skip(reason=…)` markers naming Plan 04 + Plan 05 + Plan 06 (skip-with-context). The functionality is gone-by-design; Plan 06 will ship JV-shaped replacement tests against `JointValidationRow` markup.

**Files modified:** `tests/v2/test_content_routes.py`.

**Commit:** `1581900`.

### Minor — Acceptance criteria grep against multi-line mount call

**Found during:** Task 1 acceptance criteria run.

**Issue:** The AC `grep -F 'app.mount("/static/joint_validation"' app_v2/main.py` requires both `app.mount(` and `"/static/joint_validation"` on the same line. The chosen layout splits them across lines (kwargs-per-line for readability):

```python
app.mount(
    "/static/joint_validation",
    StaticFiles(...),
    name="joint_validation_static",
)
```

This is the same indentation style the project already uses for the other mount call (single-line) — but the JV mount uses multiple kwargs that benefit from line breaks.

**Resolution:** No code change. The other related ACs (`name="joint_validation_static"`, `directory="content/joint_validation"`, `html=False`, `follow_symlink=False`, `app.include_router(joint_validation.router)`) all pass and assert the same intent. The mount-order AC `grep -n 'app.mount' app_v2/main.py` confirms the JV mount appears on line 122, the parent /static mount on line 133 — JV-first as required by Pitfall 10. Substantive contract verified by the live TestClient run that hits the mount.

**Total deviations:** 5 Rule-3 auto-fixes (3 unblocking the route, 2 unblocking tests); 1 documented AC-format inconsistency that did not require code change. Zero Rule-4 escalations.

## Issues Encountered

None — all five Rule-3 fixes resolved cleanly. The 5 plan-tolerated test files (`test_overview_routes.py`, `test_overview_store.py`, `test_overview_grid_service.py`, `test_overview_filter.py`, `test_phase05_invariants.py`) remain broken as expected per the plan's verification block; Plan 06 deletes them.

## User Setup Required

None — no external service configuration required. The drop-folder workflow (D-JV-09) is the user-facing onboarding flow but it does not block route execution; an empty `content/joint_validation/` is rendered with the JV grid scaffolding (no rows; the empty-state message lives in the Plan 05 template rewrite).

## Verification Results

- **Acceptance-criteria greps for Task 1 (main.py):** mount call present, name + directory + html=False + follow_symlink=False kwargs all present, joint_validation router import + include_router calls both present, jv_dir mkdir present, mount order JV (line 122) BEFORE /static (line 133).
- **Acceptance-criteria greps for Task 2 (overview.py):** JV grid service + JV_ROOT imports present, `build_joint_validation_grid_view_model` called 3× (GET + POST + comment), `block_names=["grid", "count_oob", "filter_badges_oob"]` present, all "should be 0" greps return 0 (`def add_platform`, `@router.post("/overview/add"`, `_resolve_curated_pids`, `_entity_dict`, `_build_overview_context`, `OverviewEntity`, `build_overview_grid_view_model`, `async def`).
- **Acceptance-criteria greps for Task 3 (joint_validation.py):** file exists, APIRouter prefix correct, both routes present with correct decorators + path-arg regex, all canonical helper imports present, all "should be 0" greps return 0 (`resolve_llm_config`, `from app_v2.routers.overview import templates`, `regenerate = x_regenerate is not None`, `app_v2.utils.markdown_render`, `result.summary_html`, `result.backend_name`, `result.cached_age_s`, `model_copy`, `async def`), all template + context keys present (entity_id, summary_url, llm_name, llm_model, summary_html via render_markdown, cfg-None branch with canonical reason).
- **TestClient smoke checks:**
  - `GET /` → 200
  - `GET /overview` → 200
  - `POST /overview/grid` → 200, `HX-Push-Url: /overview?status=A&sort=start&order=desc`
  - `POST /overview/add` → 404 (route gone)
  - `GET /joint_validation/abc` → 422 (Path regex rejects non-numeric)
  - `GET /joint_validation/9999999999` → 404 (HTTPException — no index.html)
  - `POST /joint_validation/abc/summary` → 422
  - `POST /joint_validation/9999999999/summary` → 200 (always-200 contract; cfg-None or FileNotFoundError branch)
- **Direct-impact pytest runs:**
  - `pytest tests/v2/test_main.py -q` → **18 passed, 2 skipped in 11.66s**
  - `pytest tests/v2/test_main.py tests/v2/test_summary_routes.py tests/v2/test_summary_service.py tests/v2/test_summary_integration.py -q` → **68 passed, 2 skipped in 13.37s**
  - `pytest tests/v2/test_summary_routes.py tests/v2/test_summary_service.py tests/v2/test_summary_integration.py tests/v2/test_main.py tests/v2/test_joint_validation_summary.py tests/v2/test_joint_validation_parser.py tests/v2/test_joint_validation_store.py tests/v2/test_joint_validation_grid_service.py -q` → **109 passed, 2 skipped in 15.01s**
- **Wider regression run (with the 5 plan-tolerated `--ignore` files):** `pytest tests/v2/ -q --ignore=tests/v2/test_overview_routes.py --ignore=tests/v2/test_overview_store.py --ignore=tests/v2/test_overview_grid_service.py --ignore=tests/v2/test_overview_filter.py --ignore=tests/v2/test_phase05_invariants.py` → **331 passed, 5 skipped, 4 warnings in 23.99s** (zero regressions outside the 5 known-broken legacy files Plan 06 deletes).

## Next Phase Readiness

**Plan 05 unblocked.** Templates can be rewritten against the published JV context contracts:

- `overview/index.html` + `_grid.html` + `_filter_bar.html` consume `vm: JointValidationGridViewModel` (rows, filter_options, active_filter_counts, sort_col, sort_order, total_count) + `selected_filters` + `active_tab`. Plan 05 can drop the transitional `active_filter_counts` and `all_platform_ids` top-level aliases once the templates read from the vm directly and the legacy "Add platform" form is removed.
- `joint_validation/detail.html` (NEW) consumes `jv: JointValidationRow` + `active_tab`. The iframe `src` is constructed against `/static/joint_validation/<id>/index.html` (the new mount).
- The summary route mirrors `/platforms/{pid}/summary` byte-stable except for the entity prefix; Plan 05 templates trigger it via `hx-post="/joint_validation/{{ row.confluence_page_id | e }}/summary"` with `hx-target="#summary-modal-body"`, reusing the global Bootstrap modal pattern from D-OV-15.

**Plan 06 unblocked.** All replacement test cases can target the JV routes:

- `GET /overview` returns 200 with the JV grid (no Platform-curated artifacts visible) once Plan 05 templates ship.
- `POST /overview/grid` returns the three OOB blocks + canonical HX-Push-Url.
- `POST /overview/add` returns 404 (route gone — D-JV-07 + D-JV-09).
- `GET /joint_validation/{numeric}` returns 200 with properties table + iframe pointing at `/static/joint_validation/{id}/index.html`.
- `GET /joint_validation/{non-numeric}` returns 422 (FastAPI Path regex rejection).
- `GET /static/joint_validation/../etc/passwd` returns 404 (Starlette path normalization — VERIFIED at the StaticFiles boundary).
- `POST /joint_validation/{id}/summary` always returns 200 with `hx-post="/joint_validation/{id}/summary"` in the rendered fragment.
- Plan 06 also deletes the 5 broken legacy test files and replaces them with JV-shaped equivalents (`test_joint_validation_routes.py`, `test_joint_validation_invariants.py`).

---
*Phase: 01-overview-tab-auto-discover-platforms-from-html-files*
*Completed: 2026-04-30*

## Self-Check: PASSED

- File `app_v2/routers/joint_validation.py` exists (created, 220 LOC) ✓
- File `app_v2/main.py` modified (mount + lifespan + router register) ✓
- File `app_v2/routers/overview.py` modified (rewritten 370 → 210 LOC) ✓
- File `tests/v2/test_main.py` modified (crashing_client fixture re-targeted) ✓
- File `tests/v2/test_summary_routes.py` modified (fixture cleanup) ✓
- File `tests/v2/test_summary_integration.py` modified (fixture cleanup) ✓
- File `tests/v2/test_content_routes.py` modified (fixture cleanup + 3 test skips) ✓
- Commit `56d8327` (Task 1 — Mount + lifespan + router register) exists ✓
- Commit `45e520b` (Task 2 — Rewrite overview router for JV) exists ✓
- Commit `1581900` (Task 3 — Add joint_validation router + test fixture cleanups) exists ✓
- 109 tests pass across the four direct-impact suites + the new JV suites ✓
- Wider regression suite (5 known-broken files ignored): 331 passed, 5 skipped, zero regressions ✓
