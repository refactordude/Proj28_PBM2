---
phase: 01-overview-tab-auto-discover-platforms-from-html-files
plan: 01
subsystem: infra
tags: [beautifulsoup4, lxml, jinja2, htmx, fastapi, ai-summary, partial-reuse]

# Dependency graph
requires:
  - phase: v2.0-phase-3-content-and-ai-summary
    provides: AI Summary partials (_success.html, _error.html), POST /platforms/{pid}/summary route, summary_service classification + cache
provides:
  - beautifulsoup4 + lxml installed in .venv (importable from any app_v2 module)
  - summary/_success.html and summary/_error.html parameterized with entity_id + summary_url (generic; reusable by JV summary route)
  - app_v2/routers/summary.py passes new variables alongside legacy platform_id (backward-compat)
  - Regression-pin tests that lock the on-the-wire output of /platforms/{pid}/summary against future template forks
affects: [01-02-PLAN.md, 01-03-PLAN.md, 01-04-PLAN.md, 01-05-PLAN.md]

# Tech tracking
tech-stack:
  added: [beautifulsoup4>=4.12,<5.0 (4.14.3), lxml>=5.0,<7.0 (6.1.0)]
  patterns:
    - "Generic AI Summary partial (entity_id + summary_url) — one template, multiple routes"
    - "Backward-compat key in TemplateResponse context (keep platform_id alongside entity_id)"
    - "Regression-pin tests assert literal hx-post / hx-indicator strings to detect template forks"

key-files:
  created: []
  modified:
    - requirements.txt
    - app_v2/templates/summary/_success.html
    - app_v2/templates/summary/_error.html
    - app_v2/routers/summary.py
    - tests/v2/test_summary_routes.py

key-decisions:
  - "Pin BS4+lxml at lower-bound + major-cap (matches project pin style; no exact pins)"
  - "Keep platform_id key in TemplateResponse context for backward-compat in addition to entity_id"
  - "Regression-pin tests written BEFORE refactor (TDD pattern: tests pass against old code AND must keep passing post-refactor)"

patterns-established:
  - "Generic-partial pattern: AI Summary templates accept entity_id + summary_url so /platforms/{pid}/summary and future /joint_validation/{cid}/summary share one template"

requirements-completed: [D-JV-04, D-JV-15, D-JV-16]

# Metrics
duration: 5min
completed: 2026-04-30
---

# Phase 01 Plan 01: BeautifulSoup4/lxml install + AI Summary partial parameterization

**BS4 4.14.3 + lxml 6.1.0 added to requirements.txt; summary/_success.html + _error.html rebound from hardcoded platform_id to generic entity_id + summary_url so Plan 04's /joint_validation/{cid}/summary route can reuse the same partials with no fork.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-30T08:40:26Z
- **Completed:** 2026-04-30T08:45:43Z
- **Tasks:** 2
- **Files modified:** 5 (requirements.txt, 2 templates, 1 router, 1 test file)

## Accomplishments

- BeautifulSoup4 4.14.3 + lxml 6.1.0 installed in `.venv` (`import bs4, lxml` succeeds; `BeautifulSoup("<p>hi</p>", "lxml").p.text == "hi"` confirmed). Unblocks Plan 02 (HTML parser) + Plan 03 (JV summary shim).
- `app_v2/templates/summary/_success.html` rebound: `hx-post`, `hx-target`, `hx-indicator`, `aria-label` now read `entity_id` / `summary_url` instead of literal `platform_id` / `/platforms/{pid}/summary`.
- `app_v2/templates/summary/_error.html` rebound identically (retry button).
- `app_v2/routers/summary.py` `_render_error` and `get_summary_route` `TemplateResponse` calls now pass `entity_id=platform_id` and `summary_url=f"/platforms/{platform_id}/summary"` alongside the legacy `platform_id` key (kept for backward compat).
- Added 3 regression-pin tests in `tests/v2/test_summary_routes.py` that assert the on-the-wire output (literal `hx-post="/platforms/{pid}/summary"` and `hx-indicator="#summary-{pid}-spinner"`) — locks the contract against future template forks.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add beautifulsoup4 + lxml to requirements.txt** — `3874b3f` (chore)
2. **Task 2 RED — Pin generic-partial regression contract** — `213884f` (test)
3. **Task 2 GREEN — Parameterize summary partials with entity_id + summary_url** — `6996839` (refactor)

_TDD note: Task 2 was a regression-safe refactor. The "RED" tests pin the externally-observable behavior; they passed against the original `platform_id`-only templates AND must keep passing post-refactor. No separate REFACTOR commit was needed (no further cleanup)._

## Files Created/Modified

- `requirements.txt` — added `beautifulsoup4>=4.12,<5.0` and `lxml>=5.0,<7.0` (lower-bound + major-cap, matching existing pin style)
- `app_v2/templates/summary/_success.html` — `platform_id` → `entity_id`; literal `/platforms/{pid}/summary` → `{{ summary_url | e }}`; updated docstring
- `app_v2/templates/summary/_error.html` — same parameterization; updated docstring
- `app_v2/routers/summary.py` — both `TemplateResponse` calls now pass `entity_id` + `summary_url` alongside `platform_id`
- `tests/v2/test_summary_routes.py` — added `test_post_summary_success_renders_summary_url_in_hx_post`, `test_post_summary_success_renders_entity_id_in_hx_indicator`, `test_post_summary_error_retry_uses_summary_url`

## Decisions Made

- **Keep `platform_id` key in TemplateResponse context** (alongside the new `entity_id`/`summary_url`): no other template fragment references `platform_id` today, but keeping it costs nothing and protects against any consumer that does. Removing it later is trivial.
- **Use `lower-bound + major-cap` for BS4 + lxml** (`>=4.12,<5.0` and `>=5.0,<7.0`): matches the project's existing pin style (e.g., `pandas>=3.0`, `streamlit>=1.40,<2.0`); no exact pins.
- **Regression-pin tests written first (TDD-style)**: the refactor is observably-equivalent on the platform route, so tests pin the wire output and must keep passing. Three new tests added in `test_summary_routes.py`. The earlier tests (47 in the three target files; 364 across `tests/v2/`) provide additional safety net.

## Deviations from Plan

### Minor — Acceptance criteria grep count discrepancy (no functional impact)

The plan's Task 2 acceptance criteria expected `grep -c '{{ entity_id' app_v2/templates/summary/_success.html` to return at least 4, with the breakdown "(hx-post via summary_url, hx-target fallback, hx-indicator, aria-label)". This is internally inconsistent because the plan's `<action>` step explicitly directs the hx-target rewrite to `'summary-' ~ entity_id` (entity_id is NOT the immediately-following token after `{{`), and the hx-post uses `summary_url`. With the action exactly applied, the literal `{{ entity_id` substring appears 2 times in `_success.html` and 1 time in `_error.html` — covering hx-indicator + aria-label (success) and hx-indicator (error).

**Resolution:** Honored the explicit `<action>` step (which is the load-bearing instruction). Substantive contract is enforced by the new regression-pin tests (rendered HTML contains the expected `hx-post` / `hx-indicator` / retry strings) and full v2 suite (364 passed). No code change made.

**Total deviations:** 0 auto-fixed (no Rules 1–3 fixes); 1 documented plan-AC inconsistency that did not require code change.
**Impact on plan:** None — all behavior tests pass; refactor is regression-safe; downstream plans (02, 03, 04, 05) unblocked exactly as the plan intended.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Verification Results

- `.venv/bin/python -c 'import bs4, lxml'` → exit 0 (`bs4: 4.14.3 lxml: 6.1.0`)
- `.venv/bin/pytest tests/v2/test_summary_routes.py tests/v2/test_summary_service.py tests/v2/test_summary_integration.py -q` → **47 passed in 12.82s**
- `.venv/bin/pytest tests/v2/ -q` (full Phase 5 suite + this plan's tests) → **364 passed, 2 skipped, 4 warnings in 24.36s**
- `git diff requirements.txt app_v2/templates/summary/ app_v2/routers/summary.py` → only deliberate additions (no incidental changes)

## Next Phase Readiness

**Plan 02 unblocked:** can `from bs4 import BeautifulSoup` for HTML parsing.
**Plan 03 unblocked:** can build the JV summary shim against bs4-parsed HTML.
**Plans 04 + 05 unblocked:** can pass `entity_id=confluence_page_id` and `summary_url=f"/joint_validation/{cid}/summary"` to the same `_success.html` / `_error.html` partials.

---
*Phase: 01-overview-tab-auto-discover-platforms-from-html-files*
*Completed: 2026-04-30*

## Self-Check: PASSED

- File `requirements.txt` exists and contains `beautifulsoup4>=4.12,<5.0` + `lxml>=5.0,<7.0` ✓
- File `app_v2/templates/summary/_success.html` exists, references `entity_id` and `summary_url` ✓
- File `app_v2/templates/summary/_error.html` exists, references `entity_id` and `summary_url` ✓
- File `app_v2/routers/summary.py` exists, passes `entity_id` + `summary_url` in both TemplateResponse calls ✓
- File `tests/v2/test_summary_routes.py` exists, contains 3 new regression-pin tests ✓
- Commit `3874b3f` (Task 1) exists ✓
- Commit `213884f` (Task 2 RED — regression pin tests) exists ✓
- Commit `6996839` (Task 2 GREEN — refactor) exists ✓
