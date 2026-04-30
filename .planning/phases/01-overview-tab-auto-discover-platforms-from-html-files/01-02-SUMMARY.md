---
phase: 01-overview-tab-auto-discover-platforms-from-html-files
plan: 02
subsystem: api
tags: [beautifulsoup4, lxml, pydantic-v2, fastapi, html-parsing, mtime-cache, view-model]

# Dependency graph
requires:
  - phase: 01-overview-tab-auto-discover-platforms-from-html-files/01-01
    provides: beautifulsoup4>=4.12 + lxml>=5.0 installed in .venv (importable)
provides:
  - app_v2/services/joint_validation_parser.py — BS4 13-field extractor (parse_index_html, ParsedJV); handles Page Properties macro AND <p><strong>...</strong>: ...</p> shapes; Korean 담당자 byte-equal
  - app_v2/services/joint_validation_store.py — discovery glob (^\d+$ folders + readable index.html) + mtime-keyed parse cache (clear_parse_cache helper)
  - app_v2/services/joint_validation_grid_service.py — JointValidationGridViewModel builder (filter, 12-col sort, count); _sanitize_link is verbatim port of D-OV-16
affects: [01-03-PLAN.md, 01-04-PLAN.md, 01-05-PLAN.md, 01-06-PLAN.md]

# Tech tracking
tech-stack:
  added: []  # No new deps; uses bs4+lxml pinned in plan 01-01
  patterns:
    - "BS4 string-predicate locator: lambda s: s.strip() == label (handles whitespace; first match wins)"
    - "find_parent([th, td, p]) walk-up to support both Page Properties macro AND <p>-fallback shapes in one pass"
    - "Mtime-keyed in-process memo (page_id, mtime_ns); glob NOT memoized so newly-dropped folders appear immediately"
    - "Pydantic v2 view-model + ALL_METADATA_KEYS constant (12 sortable columns) reused as the shape contract"
    - "D-JV-05 — blank '' default for missing fields (not Phase 5's '—' em-dash sentinel)"
    - "_sanitize_link verbatim port from D-OV-16 — Plan 06 invariant grep will confirm 5-scheme tuple is byte-equal"

key-files:
  created:
    - app_v2/services/joint_validation_parser.py
    - app_v2/services/joint_validation_store.py
    - app_v2/services/joint_validation_grid_service.py
    - tests/v2/fixtures/joint_validation_sample.html
    - tests/v2/fixtures/joint_validation_fallback_sample.html
    - tests/v2/test_joint_validation_parser.py
    - tests/v2/test_joint_validation_store.py
    - tests/v2/test_joint_validation_grid_service.py
  modified: []

key-decisions:
  - "Use Pydantic v2 BaseModel for ParsedJV (rather than @dataclass) for stack consistency with Phase 5's OverviewRow/OverviewGridViewModel"
  - "Wrap every BS4 get_text() result in str() so NavigableString never leaks to Pydantic (Pitfall 9)"
  - "Glob is NOT cached; only the parsed-metadata dict is memoized — preserves D-JV-09 drop-folder UX"
  - "Local import of joint_validation_store inside build_joint_validation_grid_view_model to keep import-time graph clean"
  - "JointValidationRow.link is sanitized at the SERVICE layer (parser returns raw href); D-JV-15 ports D-OV-16 verbatim"

patterns-established:
  - "Auto-discover-from-disk pattern: discover_joint_validations() globs */index.html, gates folder names through ^\\d+$ regex, requires index.html to be a regular file (not directory). Three-tier validation in one pass."
  - "Mtime-keyed parse cache pattern carried from Phase 5 D-OV-12 (content_store._FRONTMATTER_CACHE) — bounded by directory size, invalidated implicitly via file touch, explicit clear_parse_cache() helper for tests"
  - "Two-pass stable sort with empties always to END regardless of asc/desc — verbatim from overview_grid_service.py:213-276 with type rename (OverviewRow → JointValidationRow) and tiebreaker rename (platform_id → confluence_page_id)"

requirements-completed: [D-JV-02, D-JV-03, D-JV-04, D-JV-05, D-JV-08, D-JV-09, D-JV-10, D-JV-11, D-JV-14]

# Metrics
duration: 6min
completed: 2026-04-30
---

# Phase 01 Plan 02: BS4 13-field JV parser + discovery glob + mtime cache + grid view-model

**Three-module data-extraction core for the Joint Validation tab: BS4 parser handling both Page Properties macro and `<p><strong>Field</strong>: value</p>` shapes (10 tests), mtime-keyed discovery store (8 tests), and 12-column-sort + 6-filter grid view-model builder (12 tests) — 30 tests green; downstream Plans 03/04/05 unblocked.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-04-30T08:49:20Z
- **Completed:** 2026-04-30T08:55:43Z
- **Tasks:** 3 (TDD: RED + GREEN per task)
- **Files created:** 8 (3 services, 2 fixtures, 3 test files)

## Accomplishments

- **Parser (Task 1)** — `parse_index_html(html_bytes) -> ParsedJV` extracts the 13 fields (h1 title + 12 strong-label rows) from BOTH the primary `<th><strong>Field</strong></th><td>value</td>` shape AND the fallback `<p><strong>Field</strong>: value</p>` shape in one pass. First match wins on duplicate labels. Missing fields default to `""` (D-JV-05). Korean `담당자` byte-equal matched. Every cell text wrapped in `str(...)` so `NavigableString` cannot leak into Pydantic (Pitfall 9). Defensive `lxml` → `html.parser` fallback if the lxml wheel ever fails.
- **Store (Task 2)** — `discover_joint_validations(jv_root)` globs `*/index.html`, gates folder names through `^\d+$`, requires `index.html` to be a regular file (`is_file()`) — three-tier validation in one pass. Anything else silently skipped (D-JV-03 — also serves as path-traversal backstop). `get_parsed_jv(page_id, idx)` memoizes by `(page_id, mtime_ns)`; sibling pages survive a single-page invalidation. `clear_parse_cache()` test helper exposed. Glob is NOT cached → newly-dropped folders appear on next request (D-JV-09).
- **Grid service (Task 3)** — `build_joint_validation_grid_view_model(jv_root, filters, sort_col, sort_order) -> JointValidationGridViewModel` returns: 6 filter_options (computed from full row set, not the filtered subset), 12-column sort with default `start desc` + `confluence_page_id` ASC tiebreaker (stable for both orders), blank starts always to END, link sanitized via `_sanitize_link` (verbatim port of D-OV-16 — drops `javascript:`/`data:`/`vbscript:`/`file:`/`about:`, promotes bare domain to `https://`). Title falls back to `confluence_page_id` when `<h1>` missing (D-JV-05).
- **30 new tests green; 364 Phase 5 tests still pass — zero regressions.**

## Task Commits

Each task was committed atomically (TDD RED → GREEN):

1. **Task 1 RED — Failing parser tests + 2 fixtures** — `81a4633` (test)
2. **Task 1 GREEN — BS4 13-field JV parser** — `5ee9b52` (feat)
3. **Task 2 RED — Failing store tests** — `138b435` (test)
4. **Task 2 GREEN — Discovery glob + mtime cache** — `bd8dde5` (feat)
5. **Task 3 RED — Failing grid service tests** — `5679023` (test)
6. **Task 3 GREEN — Grid view-model builder** — `8c4219b` (feat)

_TDD note: each task ran the full RED → GREEN cycle. No REFACTOR commits were needed — the GREEN implementations were minimal-but-complete on first pass; the helpers in Task 3 are byte-equal copies of Phase 5 code and required no cleanup._

## Files Created/Modified

- `app_v2/services/joint_validation_parser.py` — `ParsedJV` Pydantic v2 model + `parse_index_html` + `_extract_label_value` + `_extract_link` (134 lines, 13 string fields, lxml/html.parser fallback)
- `app_v2/services/joint_validation_store.py` — `discover_joint_validations` glob + `get_parsed_jv` mtime cache + `clear_parse_cache` (70 lines, `JV_ROOT` + `PAGE_ID_PATTERN` + `_PARSE_CACHE` constants)
- `app_v2/services/joint_validation_grid_service.py` — `JointValidationRow` + `JointValidationGridViewModel` + `build_joint_validation_grid_view_model` + 5 verbatim-ported helpers (377 lines; `_sanitize_link`, `_parse_iso_date`, `_validate_sort`, `_normalize_filters`, `_sort_rows`)
- `tests/v2/fixtures/joint_validation_sample.html` — primary-shape fixture, page_id 3193868109, all 12 metadata rows + h1 + base64 image (UTF-8, no BOM)
- `tests/v2/fixtures/joint_validation_fallback_sample.html` — `<p><strong>Field</strong>: value</p>` shape with deliberately-omitted Status (UTF-8, no BOM)
- `tests/v2/test_joint_validation_parser.py` — 10 tests (primary shape, fallback shape, missing h1, Korean byte-equal, first-match-wins, empty cells, link href, label-in-anchor, whitespace strip, NavigableString leak guard)
- `tests/v2/test_joint_validation_store.py` — 8 tests (numeric-only discovery, missing root, dir-disguised-as-index skip, mtime cache hit/miss, sibling cache survival, clear helper, regex rejection)
- `tests/v2/test_joint_validation_grid_service.py` — 12 tests (view-model shape, default sort + tiebreaker, blank-start-to-END both directions, status filter, filter-options-from-full-set, link sanitizer drops/promotes, title fallback, active filter counts, invalid sort_col fallback, empty root, link-None-default)

## Decisions Made

- **Pydantic v2 BaseModel for ParsedJV (not @dataclass)** — stack consistency with Phase 5's `OverviewRow`/`OverviewGridViewModel`. Same lazy-validation cost; downstream consumers (Plans 04/05) get the same `.model_dump()` story.
- **`str(...)` wrapper on every BS4 text return** — Pitfall 9. `bs4.NavigableString` is a `str` subclass but carries a parent reference; if it leaks into Pydantic and gets pickled/serialized, the entire BS4 tree comes along. Wrapping at extraction time costs ~zero; debugging a leaked tree later is expensive.
- **Glob NOT memoized; only parse cache memoized** — D-JV-09 / D-JV-08. The drop-folder workflow requires a fresh glob each request. Glob on local SSD with ~100 dirs is sub-millisecond per RESEARCH.md; caching it would defeat the contract.
- **Local import of `joint_validation_store` inside `build_joint_validation_grid_view_model`** — Keeps import-time graph linear (parser ← store ← grid). The grid service is the only consumer of the store, and `_sanitize_link` is independent of the store, so this only affects the orchestrator function. Costless deferred import.
- **`JointValidationRow.link: str | None = None`, NOT `""`** — `None` signals "no usable link" so the template renders the Report Link button in its disabled state (D-JV-15). Other fields stay `""` per D-JV-05; only `link` is `None` because it has a special "absent" semantic that drives a UI affordance.

## Deviations from Plan

None — plan executed exactly as written. RESEARCH.md Patterns 1–6 followed verbatim (string-predicate locator, find_parent walk-up, str-wrap on get_text, mtime-keyed cache, glob NOT cached, two-pass stable sort).

The plan's `<action>` blocks were treated as load-bearing reference implementations and copied byte-equal except where the docstring/comment language was tightened (cited verbatim source line ranges from `overview_grid_service.py` so Plan 06's invariant tests can grep for the citation per D-JV-15).

**Total deviations:** 0 auto-fixed (no Rules 1–3 fixes); 0 architectural decisions (no Rule 4 escalations).
**Impact on plan:** None — Plans 03/04/05/06 are unblocked exactly as the plan intended.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Verification Results

- `.venv/bin/pytest tests/v2/test_joint_validation_parser.py -q` → **10 passed in 0.82s**
- `.venv/bin/pytest tests/v2/test_joint_validation_store.py -q` → **8 passed in 0.83s**
- `.venv/bin/pytest tests/v2/test_joint_validation_grid_service.py -q` → **12 passed in 0.90s**
- Combined: `.venv/bin/pytest tests/v2/test_joint_validation_parser.py tests/v2/test_joint_validation_store.py tests/v2/test_joint_validation_grid_service.py -q` → **30 passed in 1.06s**
- `.venv/bin/python -c 'from app_v2.services.joint_validation_grid_service import build_joint_validation_grid_view_model; print("OK")'` → exit 0 (`OK`)
- Phase 5 regression check: `.venv/bin/pytest tests/v2/ -q --ignore=tests/v2/test_joint_validation_parser.py --ignore=tests/v2/test_joint_validation_store.py --ignore=tests/v2/test_joint_validation_grid_service.py` → **364 passed, 2 skipped, 4 warnings in 25.07s** (zero regressions)
- Acceptance-criteria greps all pass: `string=lambda s:` count = 2; `find_parent([` count = 2; Korean `담당자` literal preserved; `PAGE_ID_PATTERN re.compile(r"^\d+$")` present; `glob("*/index.html")` literal present; `_PARSE_CACHE: dict` present; `is_file()` guard present; `FILTERABLE_COLUMNS tuple[str` present; 6-filter literal tuple present; 5-scheme literal tuple present (`"javascript:", "data:", "vbscript:", "file:", "about:"`); `class JointValidationRow` count = 1; `class JointValidationGridViewModel` count = 1; `def build_joint_validation_grid_view_model` count = 1; no em-dash defaults in row model.

## Next Phase Readiness

**Plan 03 unblocked:** can build the JV summary shim against the BS4-parsed HTML returned by `parse_index_html` (or invoke `get_parsed_jv` directly).

**Plan 04 unblocked:** can wire `GET /overview` + `POST /overview/grid` against `build_joint_validation_grid_view_model(JV_ROOT, filters, sort_col, sort_order)` — the view-model shape is final.

**Plan 05 unblocked:** can rewrite the `overview/index.html` + `_grid.html` + `_filter_bar.html` templates against `JointValidationGridViewModel` (rows, filter_options, active_filter_counts, sort_col, sort_order, total_count). The 6-FILTERABLE_COLUMNS contract and 12-SORTABLE_COLUMNS contract are both pinned by tests.

**Plan 06 unblocked:** the `_DANGEROUS_LINK_SCHEMES` 5-tuple is byte-equal to D-OV-16 — invariant grep will pass.

---
*Phase: 01-overview-tab-auto-discover-platforms-from-html-files*
*Completed: 2026-04-30*

## Self-Check: PASSED

- File `app_v2/services/joint_validation_parser.py` exists ✓
- File `app_v2/services/joint_validation_store.py` exists ✓
- File `app_v2/services/joint_validation_grid_service.py` exists ✓
- File `tests/v2/fixtures/joint_validation_sample.html` exists ✓
- File `tests/v2/fixtures/joint_validation_fallback_sample.html` exists ✓
- File `tests/v2/test_joint_validation_parser.py` exists ✓
- File `tests/v2/test_joint_validation_store.py` exists ✓
- File `tests/v2/test_joint_validation_grid_service.py` exists ✓
- Commit `81a4633` (Task 1 RED — parser tests + fixtures) exists ✓
- Commit `5ee9b52` (Task 1 GREEN — BS4 parser) exists ✓
- Commit `138b435` (Task 2 RED — store tests) exists ✓
- Commit `bd8dde5` (Task 2 GREEN — discovery + cache) exists ✓
- Commit `5679023` (Task 3 RED — grid service tests) exists ✓
- Commit `8c4219b` (Task 3 GREEN — grid view-model) exists ✓
- Combined plan-02 test count: 30 passed (10 parser + 8 store + 12 grid)
- Phase 5 regression: 364 passed, 2 skipped — zero regressions
