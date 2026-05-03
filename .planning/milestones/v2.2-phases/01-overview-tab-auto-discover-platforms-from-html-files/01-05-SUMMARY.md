---
phase: 01-overview-tab-auto-discover-platforms-from-html-files
plan: 05
subsystem: ui
tags: [jinja2, htmx, bootstrap5, iframe-sandbox, joint-validation, template-rewrite]

# Dependency graph
requires:
  - phase: 01-overview-tab-auto-discover-platforms-from-html-files/01-02
    provides: JointValidationGridViewModel shape (rows, filter_options, active_filter_counts, sort_col, sort_order, total_count) — what the rewritten templates iterate
  - phase: 01-overview-tab-auto-discover-platforms-from-html-files/01-04
    provides: router context dict (vm, selected_filters, active_tab, transitional active_filter_counts + all_platform_ids aliases) + GET /joint_validation/{id} route
provides:
  - app_v2/templates/base.html — top-nav label "Joint Validation" (URL "/" unchanged)
  - app_v2/templates/overview/index.html — JV listing shell with 3 OOB blocks (grid, count_oob, filter_badges_oob), sortable_th macro INSIDE grid block (Pitfall 8), AI Summary modal targeting #summary-modal-body
  - app_v2/templates/overview/_grid.html — 12 sortable headers + Action column with Report Link + AI Summary buttons, blank "" defaults (D-JV-05), empty state copy verbatim per D-JV-17
  - app_v2/templates/overview/_filter_bar.html — 6 picker_popover invocations with form_id="overview-filter-form" + Clear-all link (D-JV-11)
  - app_v2/templates/joint_validation/detail.html (NEW) — properties table + <iframe sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"> referencing /static/joint_validation/{id}/index.html
affects: [01-06-PLAN.md]

# Tech tracking
tech-stack:
  added: []  # No new deps; all from earlier plans
  patterns:
    - "Pitfall 8 — sortable_th macro defined INSIDE {% block grid %} so jinja2-fragments block_names=['grid', ...] rendering retains macro visibility"
    - "Locked iframe sandbox 3-flag string: allow-same-origin allow-popups allow-popups-to-escape-sandbox (NO script-execution flag, NO allow-top-navigation, NO allow-forms)"
    - "Defense-in-depth | e on every dynamic value (autoescape is also on by default for .html templates) — every JV template grep returns zero | safe filters"
    - "D-JV-05 blank '' defaults — NO em-dash sentinel anywhere in JV templates (deliberate departure from Phase 5 D-OV-09)"
    - "D-JV-17 empty-state copy rendered verbatim with colspan='13' to span all 13 columns; helper text path content/joint_validation/<page_id>/index.html escaped via &lt;...&gt;"

key-files:
  created:
    - app_v2/templates/joint_validation/detail.html
  modified:
    - app_v2/templates/base.html
    - app_v2/templates/overview/index.html
    - app_v2/templates/overview/_grid.html
    - app_v2/templates/overview/_filter_bar.html
    - tests/v2/test_main.py

key-decisions:
  - "Rephrase sandbox-warning comment to avoid the literal 'allow-scripts' token — acceptance criterion enforces 'grep -F allow-scripts' returns 0; the comment now says 'script-execution flag' instead, conveying identical safety intent without tripping the strict literal grep"
  - "Auto-fix two test_main.py assertions that referenced the literal 'Overview' nav label — direct consequence of Plan 05 Task 1's D-JV-01 rename; assertions now check 'Joint Validation' while preserving the structural intent (3 tabs + active class on the JV nav-link)"
  - "Re-use of summary/_success.html + _error.html partials parameterized in Plan 01 — the AI Summary button on each JV row hx-posts /joint_validation/{id}/summary which renders into #summary-modal-body using entity_id + summary_url placeholders set up in Plan 01 Task 2"
  - "Picker_popover macro reused AS-IS — the 'disabled' kwarg added in 260429-qyv was already present, so WARN-03 verification passed without modification (grep -F 'disabled' app_v2/templates/browse/_picker_popover.html returns 9 matches)"

patterns-established:
  - "JV templates render against vm:JointValidationGridViewModel + jv:JointValidationRow; selected_filters is the filter-side dict; active_tab='overview' threads through base.html nav-link active class"
  - "Iframe sandbox literal locked at template-render time (not router-time) so security review can grep one literal string across the codebase to verify the contract — Plan 06's invariant test will pin this byte-stable"
  - "Title cell IS the link to /joint_validation/<id> (no separate View button) — D-JV-15 — Action column hosts only Report Link + AI Summary buttons"

requirements-completed: [D-JV-01, D-JV-05, D-JV-10, D-JV-11, D-JV-12, D-JV-13, D-JV-15, D-JV-17]

# Metrics
duration: 7min
completed: 2026-04-30
---

# Phase 01 Plan 05: Rewrite overview templates + add joint_validation/detail.html

**Five templates rewired for Joint Validation: nav-label flipped (D-JV-01), three overview/ templates fully rewritten (12 sortable column headers, 6 popover-checklist filters, AI Summary modal), and a new joint_validation/detail.html with the locked 3-flag iframe sandbox attribute. Three atomic commits, 109 tests green across the direct-impact suites + 331 passed in the wider regression run; zero regressions.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-04-30T12:00:55Z
- **Completed:** 2026-04-30T12:08:02Z
- **Tasks:** 3
- **Files created:** 1 (joint_validation/detail.html — 65 LOC)
- **Files modified:** 5 (base.html nav label flip; index.html 226 → 93 LOC; _grid.html 130 → 92 LOC; _filter_bar.html 86 → 97 LOC; tests/v2/test_main.py — 2 assertions auto-fixed)

## Accomplishments

- **Task 1 — Nav label + filter bar (D-JV-01, D-JV-11).** `app_v2/templates/base.html` top-nav label "Overview" → "Joint Validation"; URL `/` and `active_tab == 'overview'` comparison preserved verbatim. `app_v2/templates/overview/_filter_bar.html` rewritten as 6 `picker_popover(...)` invocations (status, customer, ap_company, device, controller, application) with `form_id="overview-filter-form"`, all hx-target=#overview-grid, all `disabled=(vm.total_count == 0 and (vm.filter_options[col] | length) == 0)` — D-JV-17 empty-state pattern. `picker_popover` macro reused AS-IS (the `disabled=False` default kwarg added in 260429-qyv was already present, so WARN-03 verification passed without modification). Clear-all link emits `hx-get="/overview"` to reset filters + sort to defaults.
- **Task 2 — index.html + _grid.html (D-JV-05, D-JV-10, D-JV-15, D-JV-17).** `overview/index.html` now hosts 3 OOB blocks (`grid`, `count_oob`, `filter_badges_oob`) at the top level of the content block so `block_names=["grid", "count_oob", "filter_badges_oob"]` rendering picks them up cleanly. The `sortable_th` macro is defined INSIDE the `{% block grid %}` body (Pitfall 8 — block-local macro visibility for jinja2-fragments). The AI Summary modal at `#summary-modal` with body slot `#summary-modal-body` carries the Phase 5 D-OV-15 `show.bs.modal` placeholder-reset pattern verbatim. `overview/_grid.html` renders 12 `sortable_th(...)` calls in `<thead>` + a non-sortable Action column header; the data row has 13 `<td>` cells (12 fields + Action); empty-state row uses `colspan="13"` with verbatim D-JV-17 copy "**No Joint Validations yet.** Drop a Confluence export at `content/joint_validation/<page_id>/index.html`". Title cell IS the link to `/joint_validation/<id>` (no separate View button). Report Link button: when `row.link` is truthy, an `<a target="_blank" rel="noopener noreferrer">`; otherwise a `<button disabled>` placeholder. AI Summary button: `hx-post="/joint_validation/{id}/summary"` → `#summary-modal-body` with `data-bs-toggle="modal"`. Every dynamic value `| e`-escaped; zero `| safe` filters.
- **Task 3 — joint_validation/detail.html (D-JV-12, D-JV-13).** New template at `app_v2/templates/joint_validation/detail.html` with: page-head (jv.title + Confluence Page ID), 12-row Obsidian-style properties table (Status..End + Report Link), and `<iframe sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox">` pointing at `/static/joint_validation/{{ jv.confluence_page_id | e }}/index.html`. The literal sandbox attribute value is exactly the 3-flag string, byte-stable; NO script-execution flag, NO allow-top-navigation, NO allow-forms. Korean `담당자` row preserved verbatim (UTF-8 throughout). Every dynamic value `| e`-escaped (including the `iframe src` value as defense-in-depth even though `confluence_page_id` is regex-pinned at the route layer). Zero `| safe` filters.

## Task Commits

Each task was committed atomically:

1. **Task 1 — Flip nav label + rewrite _filter_bar.html** — `b31b7c1` (feat)
2. **Task 2 — Rewrite overview/index.html + _grid.html for JV grid** — `52bddfc` (feat)
3. **Task 3 — Add joint_validation/detail.html (properties + iframe sandbox)** — `55ae228` (feat)

## Files Created / Modified

- **Created:** `app_v2/templates/joint_validation/detail.html` (65 LOC). Properties table + iframe sandbox detail page. Path-arg `{{ jv.confluence_page_id | e }}` flows into the iframe src; the regex `^\d+$` pin lives at the route layer (Plan 04 Task 3).
- **Modified:** `app_v2/templates/base.html` — single edit on the Overview nav-link visible label text.
- **Modified:** `app_v2/templates/overview/index.html` (226 → 93 LOC, net −133). Phase 5 Platform-curated chrome (Add platform form, datalist, Curated platforms tag, panel-header) gone; replaced with `<h1>Joint Validation</h1>` + `{% include "overview/_filter_bar.html" %}` + 3 OOB blocks.
- **Modified:** `app_v2/templates/overview/_grid.html` (130 → 92 LOC, net −38). Em-dash `maybe()` macro removed (D-JV-05); `has_content` references gone; `platform_id` references gone; the 12 sortable headers are now defined in `index.html`'s `block grid` and called from `_grid.html`; the empty-state branch uses the JV-specific copy.
- **Modified:** `app_v2/templates/overview/_filter_bar.html` (86 → 97 LOC, net +11). Six `picker_popover(...)` invocations expanded with kwargs-on-individual-lines (the `disabled=...` empty-state expression makes one-line invocations unreadable).
- **Modified:** `tests/v2/test_main.py` — 2 assertions in `test_get_root_contains_three_tab_labels` and `test_get_root_marks_overview_active` updated from "Overview" → "Joint Validation" (Rule 3 auto-fix: D-JV-01 nav-label rename caused these to fail; the structural intent is preserved).

## Decisions Made

- **Rephrase sandbox-warning comment to avoid the literal `allow-scripts` token.** The plan's acceptance criterion enforces `grep -F 'allow-scripts' app_v2/templates/joint_validation/detail.html` returns 0 matches. The first draft's comment said "do NOT add allow-scripts — combining allow-scripts with allow-same-origin lets the framed document remove the sandbox attr" which trips the literal grep twice. Replaced both occurrences with "script-execution flag" — same safety intent, no token leak.
- **Reuse picker_popover AS-IS without modification.** WARN-03 in the plan flagged that if the `disabled` kwarg were missing from `app_v2/templates/browse/_picker_popover.html` then the 6 `disabled=...` invocations would silently no-op. Verified at task-1 start: `grep -F 'disabled' app_v2/templates/browse/_picker_popover.html` returns 9 matches; the macro signature already has `disabled=False` as a default kwarg (added in quick task 260429-qyv). No macro modification needed.
- **Auto-fix tests/v2/test_main.py instead of leaving it broken for Plan 06.** The plan does not enumerate `test_main.py` as one of the 5 plan-tolerated legacy files; the failing assertions (`test_get_root_contains_three_tab_labels` + `test_get_root_marks_overview_active`) were a *direct* consequence of Plan 05 Task 1's D-JV-01 nav-label rename. Per Rule 3 (auto-fix blocking caused by THIS plan's task), updated the literal "Overview" → "Joint Validation" while preserving the structural intent (3 tab labels + active class on the JV/overview nav-link). Test count delta: 0 (same 2 tests, just updated assertions).

## Deviations from Plan

### Rule 3 — Auto-fix blocking: 'allow-scripts' word in safety-comment trips the strict literal grep AC

**Found during:** Task 3 first acceptance grep run.

**Issue:** The plan's `<action>` block for Task 3 included a sandbox-safety comment that wrote `do NOT add allow-scripts — combining allow-scripts with allow-same-origin lets the framed document remove the sandbox attr (MDN warns explicitly against this).` Two occurrences of the literal token `allow-scripts`. The plan's acceptance criterion is `grep -F 'allow-scripts' app_v2/templates/joint_validation/detail.html` returns no matches. Strictly applied, the AC fails.

**Fix:** Rephrased both occurrences in the comment to use "script-execution flag" instead of the literal token. The safety intent is preserved verbatim (the comment still warns against combining the script-execution flag with `allow-same-origin`); only the literal token is gone.

**Files modified:** `app_v2/templates/joint_validation/detail.html`.

**Commit:** `55ae228` (Task 3 commit — included in initial Write of the file).

### Rule 3 — Auto-fix blocking: test_main.py asserts on the literal 'Overview' nav label

**Found during:** Task 3 final regression run.

**Issue:** `tests/v2/test_main.py::test_get_root_contains_three_tab_labels` asserts `assert "Overview" in r.text`, and `test_get_root_marks_overview_active` searches for `"Overview"` inside the nav section to verify the active-class window. Plan 05 Task 1 renamed the nav-link visible label from "Overview" to "Joint Validation" per D-JV-01; both tests now fail. The plan does NOT list `test_main.py` among the 5 plan-tolerated legacy files (`test_overview_routes.py`, `test_overview_store.py`, `test_overview_grid_service.py`, `test_overview_filter.py`, `test_phase05_invariants.py`) — those are Plan 06's deletion targets.

**Fix:** Updated both assertions to check `"Joint Validation"` instead of `"Overview"`. The structural intent is preserved: `test_get_root_contains_three_tab_labels` still verifies all 3 nav labels are present; `test_get_root_marks_overview_active` still verifies the active class is on the first tab's nav-link (only the search-key string changed). Comments added explaining the D-JV-01 rename + that `active_tab == 'overview'` comparison is unchanged.

**Files modified:** `tests/v2/test_main.py`.

**Commit:** `55ae228` (folded into Task 3 commit alongside detail.html).

### Minor — Acceptance grep on `target="_blank"` and `rel="noopener noreferrer"` produced false zeros under shell quoting

**Found during:** Task 3 first acceptance grep run.

**Issue:** The acceptance criterion `grep -F 'target="_blank"' app_v2/templates/joint_validation/detail.html` produced 0 matches when run inside an `echo '...'` chain, but a Python-based byte-equal substring count returned 2 matches (one in the iframe-attr precedence comment example + one on the actual `<a>` tag). The shell-quoting was the issue, not the file content.

**Resolution:** No code change. Verified the file content directly with a `python -c "...content.count('target=\"_blank\"')"` helper which confirmed 2 matches for `target="_blank"` (the iframe `<iframe>` does not have it; the link anchor and an aria-label reference for an open report do). The substantive contract (Report Link target attr + rel attr + iframe sandbox attr literal + Korean assignee row) is verified by the live TestClient render which shows all four strings in the rendered HTML.

**Total deviations:** 2 Rule-3 auto-fixes (sandbox-comment rephrasing + test_main.py assertion update); 1 documented shell-quoting AC inconsistency that did not require code change. Zero Rule-4 escalations.

**Impact on plan:** None — substantive contract intact; the locked sandbox attribute literal is byte-stable in the rendered HTML; all 5 success criteria pass; Plan 06 unblocked.

## Issues Encountered

None — both Rule-3 fixes resolved cleanly.

## User Setup Required

None — no external service configuration required. The drop-folder workflow (D-JV-09) is the user-facing onboarding flow but it does not block route execution; an empty `content/joint_validation/` is rendered with the JV grid scaffolding (now showing the verbatim D-JV-17 empty-state message).

## Verification Results

- **Jinja2 compile (all 5 templates):** `.venv/bin/python -c "import jinja2; e = jinja2.Environment(loader=jinja2.FileSystemLoader('app_v2/templates'), autoescape=True); [e.get_template(t) for t in ['base.html', 'overview/index.html', 'overview/_grid.html', 'overview/_filter_bar.html', 'joint_validation/detail.html']]; print('OK')"` → exit 0 (`OK`)
- **TestClient end-to-end smoke:**
  - `GET /` → 200; "Joint Validation" present in body; "No Joint Validations yet." present when JV root is empty; `summary-modal-body` slot present.
  - `GET /` (with one fixture JV folder) → 200; `<a href="/joint_validation/3193868109"` present in body.
  - `GET /joint_validation/3193868109` (with fixture) → 200; literal sandbox attribute `sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"` present; iframe src `/static/joint_validation/3193868109/index.html` present; Korean `<th>담당자</th>` row present.
  - `GET /joint_validation/9999999999` → 404 (HTTPException — no index.html on disk).
  - `GET /joint_validation/abc` → 422 (FastAPI Path regex rejects non-numeric).
- **Acceptance-criteria greps (all pass):**
  - Task 1: nav label flipped (1× match new label, 0× match old label); `active_tab == 'overview'` count unchanged (2); `picker_popover(` count = 6; `name="..."` for each of 6 filter columns = 1 each; `form_id="overview-filter-form"` count = 6; `has_content` = 0; em-dash = 0; `disabled` in macro = 9.
  - Task 2: `{% block grid %}`, `{% block count_oob %}`, `{% block filter_badges_oob %}` each = 1 in index.html; `macro sortable_th` count = 1 INSIDE the grid block (awk-bracketed); `sortable_th(` count in _grid.html = 12; literal `"title", "Title"` + `"담당자"` + `colspan="13"` + `No Joint Validations yet.` + `content/joint_validation/&lt;page_id&gt;/index.html` + `/joint_validation/{{ row.confluence_page_id` + `target="_blank"` + `rel="noopener noreferrer"` + `hx-post="/joint_validation/` + `hx-target="#summary-modal-body"` + `data-bs-toggle="modal"` all present; em-dash + `has_content` + `platform_id` = 0; `| e` count = 17; `| safe` = 0 in both index.html and _grid.html.
  - Task 3: sandbox literal = 1; `allow-scripts` + `allow-top-navigation` + `allow-forms` = 0; iframe src jinja substring = 1; `/index.html` = 1; `<iframe` = 1; `target="_blank"` = 2 (Python-verified); `rel="noopener noreferrer"` = 1; `<th>담당자</th>` = 1; em-dash = 0; `| safe` = 0; `| e` = 17.
- **Direct-impact pytest runs:**
  - `pytest tests/v2/test_main.py tests/v2/test_joint_validation_*.py tests/v2/test_summary_*.py -q` → **109 passed, 2 skipped in 14.41s**
- **Wider regression run (with the 5 plan-tolerated --ignore files):** `pytest tests/v2/ -q --ignore=tests/v2/test_overview_routes.py --ignore=tests/v2/test_overview_store.py --ignore=tests/v2/test_overview_grid_service.py --ignore=tests/v2/test_overview_filter.py --ignore=tests/v2/test_phase05_invariants.py` → **331 passed, 5 skipped, 4 warnings in 23.43s** (zero regressions outside the 5 known-broken legacy files Plan 06 deletes).

## Output Block Confirmations

The plan's `<output>` block asks the SUMMARY to confirm:

- **5 template files modified (1 nav flip, 3 full rewrites, 1 new):** Confirmed —
  1. `app_v2/templates/base.html` — nav label flipped (D-JV-01); 1-token edit
  2. `app_v2/templates/overview/_filter_bar.html` — full rewrite (D-JV-11)
  3. `app_v2/templates/overview/index.html` — full rewrite (D-JV-15, D-JV-17)
  4. `app_v2/templates/overview/_grid.html` — full rewrite (D-JV-05, D-JV-10, D-JV-15)
  5. `app_v2/templates/joint_validation/detail.html` — NEW (D-JV-12, D-JV-13)
- **LOC delta per file:**
  - `base.html` — 77 lines (unchanged total LOC; one-token edit on the nav-link visible label)
  - `overview/_filter_bar.html` — 97 lines (was 86, +11 — kwargs-on-individual-lines for the `disabled=...` expression)
  - `overview/index.html` — 93 lines (was 226, −133 — Platform chrome gone)
  - `overview/_grid.html` — 92 lines (was 130, −38 — `maybe()` macro + `has_content` references gone)
  - `joint_validation/detail.html` — 65 lines (NEW)
- **`| safe` count is 0 across all JV templates:** Confirmed. `grep -c '| safe' app_v2/templates/joint_validation/detail.html app_v2/templates/overview/_grid.html app_v2/templates/overview/index.html app_v2/templates/overview/_filter_bar.html` returns 0 for every file.
- **Iframe sandbox attribute is exactly the locked 3-flag string:** Confirmed. `grep -F 'sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"' app_v2/templates/joint_validation/detail.html` returns 1 match. `grep -F 'allow-scripts'`, `grep -F 'allow-top-navigation'`, `grep -F 'allow-forms'` all return 0 matches.

## Next Phase Readiness

**Plan 06 unblocked.** All replacement test cases can target the JV templates as wave-3 work is now complete:

- `GET /overview` returns 200 with the JV grid (no Platform-curated artifacts visible) — already verified by TestClient smoke; Plan 06 promotes this to a permanent test in `test_joint_validation_routes.py` / `test_joint_validation_invariants.py`.
- `GET /joint_validation/{numeric}` returns 200 with the locked sandbox attribute literal in body — already verified by TestClient smoke.
- The 5 legacy test files (`test_overview_routes.py`, `test_overview_store.py`, `test_overview_grid_service.py`, `test_overview_filter.py`, `test_phase05_invariants.py`) are the final deletion targets for Plan 06.
- The transitional context aliases (`active_filter_counts` + `all_platform_ids=[]`) on the JV listing context are now dead context — the rewritten templates read from `vm.active_filter_counts` directly. Plan 06 (or a follow-up cleanup) can delete the bridge from `app_v2/routers/overview.py`.
- Invariant grep tests (Plan 06): the locked sandbox literal, the 5-scheme `_DANGEROUS_LINK_SCHEMES` tuple, and the verbatim D-JV-17 empty-state copy can all be byte-pinned across the codebase.

---
*Phase: 01-overview-tab-auto-discover-platforms-from-html-files*
*Completed: 2026-04-30*

## Self-Check: PASSED

- File `app_v2/templates/base.html` exists, top-nav label "Joint Validation" present ✓
- File `app_v2/templates/overview/_filter_bar.html` exists, 6 picker_popover invocations + form_id="overview-filter-form" ✓
- File `app_v2/templates/overview/index.html` exists, 3 OOB blocks + sortable_th macro INSIDE grid block ✓
- File `app_v2/templates/overview/_grid.html` exists, 12 sortable headers + Action column + verbatim D-JV-17 empty state ✓
- File `app_v2/templates/joint_validation/detail.html` exists, locked 3-flag sandbox literal ✓
- File `tests/v2/test_main.py` modified, 2 assertions auto-fixed for D-JV-01 nav-label rename ✓
- File `.planning/phases/01-overview-tab-auto-discover-platforms-from-html-files/01-05-SUMMARY.md` exists ✓
- Commit `b31b7c1` (Task 1 — Flip nav label + rewrite _filter_bar.html) exists ✓
- Commit `52bddfc` (Task 2 — Rewrite overview/index.html + _grid.html) exists ✓
- Commit `55ae228` (Task 3 — Add joint_validation/detail.html) exists ✓
- All 5 templates compile under Jinja2 ✓
- 109 tests pass across direct-impact suites; 331 pass in wider regression run; zero regressions ✓
- TestClient end-to-end smoke: GET / → 200, GET /joint_validation/{id} → 200 with locked sandbox literal ✓
