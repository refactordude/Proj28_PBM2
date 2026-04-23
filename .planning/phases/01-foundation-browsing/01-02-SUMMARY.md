---
phase: 01-foundation-browsing
plan: 02
subsystem: database
tags: [pandas, result-normalizer, eav, data-pipeline, pytest, tdd, normalization, hex, decimal, lun, dme]

# Dependency graph
requires: []
provides:
  - "result_normalizer module: 5-stage EAV Result field normalization pipeline with full pytest suite"
  - "ResultType enum: MISSING, ERROR, HEX, DECIMAL, CSV, WHITESPACE_BLOB, COMPOUND, IDENTIFIER"
  - "is_missing(): None/nan/pd.NA/sentinel/shell-error detection (DATA-01)"
  - "normalize(): stages 1-2 pipeline, pd.NA for all missing/error values (DATA-01)"
  - "classify(): 8-type heuristic classification without coercion (DATA-02)"
  - "split_lun_item(): LUN index 0..7 prefix parsing (DATA-03)"
  - "split_dme_suffix(): _local/_peer DME side detection (DATA-04)"
  - "unpack_dme_compound(): comma+equals compound value dict unpacking (DATA-04)"
  - "try_numeric(): on-demand hex/decimal coercion for chart path only (Stage 5)"
affects:
  - "01-03-ufs_service: imports result_normalizer for normalize() and classify() calls"
  - "app/pages/browse.py: uses try_numeric on chart path (VIZ-02)"

# Tech tracking
tech-stack:
  added: [pytest, pytest-mock, pandas 3.0.2 (venv)]
  patterns:
    - "pd.NA as the single missing sentinel — never np.nan or None after normalization"
    - "Anchored regexes (^...$) for HEX and DECIMAL classification (T-02-01 security)"
    - "Series.apply() for per-element normalization and coercion (lazy, per-query)"
    - "pd.isna() guard in is_missing() to handle pandas 3.x StringDtype nan representation"
    - "classify() checks ERROR before MISSING so shell-error strings return ERROR not MISSING"

key-files:
  created:
    - app/services/__init__.py
    - app/services/result_normalizer.py
    - tests/__init__.py
    - tests/services/__init__.py
    - tests/services/test_result_normalizer.py
  modified: []

key-decisions:
  - "classify() checks ERROR before is_missing() so shell-error strings (e.g. 'cat: /sys/foo') return ResultType.ERROR rather than ResultType.MISSING — both map to pd.NA in normalize(), but classify() preserves the distinction for callers that care"
  - "is_missing() calls pd.isna() first (in addition to val is None) to handle pandas 3.x StringDtype which stores None/pd.NA as float nan inside Series.apply() callbacks"
  - "try_numeric() returns object dtype Series (mixed int/float/pd.NA) — forced numeric dtype would reject pd.NA without explicit nullable Int64 conversion"
  - "MISSING_SENTINELS frozenset is case-sensitive and lists both variants explicitly (null/NULL, N/A/N/a) — no global lowercasing to avoid masking legitimate values"

patterns-established:
  - "TDD RED→GREEN: test file committed first (failing at collection), impl committed second (all pass)"
  - "pytest parametrize for sentinel set — reduces boilerplate while keeping each case visible"
  - "pd.isna() for NA-equality assertions in tests (not `is pd.NA`) — correct for Series element comparisons"

requirements-completed: [DATA-01, DATA-02, DATA-03, DATA-04]

# Metrics
duration: 5min
completed: 2026-04-23
---

# Phase 01 Plan 02: result_normalizer Summary

**5-stage EAV Result-field normalization pipeline with 65-test pytest suite covering hex/decimal/CSV/compound classification, LUN prefix parsing, DME side detection, and lazy numeric coercion**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-23T19:13:23Z
- **Completed:** 2026-04-23T19:18:00Z
- **Tasks:** 2 (TDD RED + GREEN)
- **Files modified:** 5

## Accomplishments

- 58 test functions (65 collected with parametrize expansion) cover every DATA-01..04 clause and Stage 5
- `result_normalizer.py` exports all 10 public symbols with full docstrings
- Handles pandas 3.x StringDtype edge case where `None`/`pd.NA` in Series becomes `float('nan')` inside `.apply()` callbacks
- Classify ordering: ERROR before MISSING preserves shell-error granularity while `normalize()` maps both to `pd.NA`

## Task Commits

1. **Task 1: Write failing pytest suite (RED)** — `b30664a` (test)
2. **Task 2: Implement result_normalizer to pass all tests (GREEN)** — `86211aa` (feat)

## Files Created/Modified

- `app/services/__init__.py` — Domain service layer package init
- `app/services/result_normalizer.py` — Full 5-stage normalization pipeline; 10 public exports
- `tests/__init__.py` — Test package init (empty)
- `tests/services/__init__.py` — Test sub-package init (empty)
- `tests/services/test_result_normalizer.py` — 58 test functions (65 collected); DATA-01..04 + Stage 5

## Public API Reference (stable — imported by Plan 03 ufs_service)

```python
from app.services.result_normalizer import (
    ResultType,           # Enum: MISSING ERROR HEX DECIMAL CSV WHITESPACE_BLOB COMPOUND IDENTIFIER
    MISSING_SENTINELS,    # frozenset: {None, "None", "", "N/A", "N/a", "null", "NULL"}
    SHELL_ERROR_PREFIXES, # tuple: ("cat: ", "Permission denied", "No such file")
    is_missing,           # (val: Any) -> bool
    normalize,            # (series: pd.Series) -> pd.Series  [stages 1-2; pd.NA for missing/error]
    classify,             # (val: Any) -> ResultType          [no coercion; DATA-02]
    split_lun_item,       # (item: str) -> tuple[int|None, str]  [DATA-03; 0..7 range]
    split_dme_suffix,     # (item: str) -> tuple[str, str|None]  [DATA-04; _local/_peer]
    unpack_dme_compound,  # (val: str) -> dict[str, str]         [DATA-04; key=val,...]
    try_numeric,          # (series: pd.Series) -> pd.Series  [stage 5; chart path only]
)
```

## Classification Heuristics (order matters)

| Priority | Type | Condition |
|----------|------|-----------|
| 1 | ERROR | string starts with `SHELL_ERROR_PREFIXES` element — checked BEFORE MISSING |
| 2 | MISSING | `is_missing(val)` is True (None, nan, pd.NA, empty, sentinel strings) |
| 3 | HEX | matches `^0[xX][0-9a-fA-F]+$` |
| 4 | DECIMAL | matches `^-?\d+(\.\d+)?([eE][-+]?\d+)?$` |
| 5 | COMPOUND | contains both `=` and `,` |
| 6 | CSV | contains `,` but not `=` |
| 7 | WHITESPACE_BLOB | contains `\n` OR (len > 40 AND `\s{2,}`) |
| 8 | IDENTIFIER | fallback |

## Decisions Made

- **classify() ERROR before MISSING:** Shell-error strings like `"cat: /sys/foo"` are classified as ERROR (not MISSING) to preserve semantic granularity for callers. `normalize()` maps both to `pd.NA` regardless. This ensures a UI can display "⚠ command failed" vs "— no data" differently if it ever needs to.
- **pandas 3.x nan guard in is_missing():** `pd.Series([None])` with default StringDtype produces `float('nan')` inside `.apply()` callbacks, not Python `None`. Added `pd.isna(val)` check (with TypeError/ValueError guard for array-like values) before the `isinstance(val, str)` branch.
- **try_numeric() returns object dtype:** Returning a homogeneous Int64/float64 dtype from `try_numeric()` would require explicit nullable dtype conversion and would reject pd.NA. Keeping object dtype lets the chart path call `pd.to_numeric(..., errors='coerce')` afterward for the specific Plotly use case.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] pandas 3.x StringDtype converts None/pd.NA to float nan in Series.apply()**
- **Found during:** Task 2 (GREEN phase, first pytest run)
- **Issue:** `test_normalize_converts_python_None_to_pd_NA` failed — `pd.Series([None, "0xFF"])` with pandas 3.x default StringDtype stores `None` as `float('nan')`, so `is_missing()` received `nan` (not `None`) and returned `False`; the cell came through as `'nan'` string instead of `pd.NA`
- **Fix:** Added `pd.isna(val)` guard at the top of `is_missing()`, with a `try/except (TypeError, ValueError)` to handle array-like values; the `val is None` check is preserved before it for the common case
- **Files modified:** `app/services/result_normalizer.py`
- **Verification:** All 65 tests pass after fix
- **Committed in:** `86211aa` (Task 2 commit)

**2. [Rule 1 - Bug] classify() returned MISSING for shell-error strings instead of ERROR**
- **Found during:** Task 2 (GREEN phase, second pytest run after fix 1)
- **Issue:** `test_classify_cat_shell_error_is_ERROR` failed — after fix 1 made `is_missing()` return True for shell errors (per plan spec), `classify()` hit the MISSING branch before the ERROR branch for strings like `"cat: /sys/foo"`
- **Fix:** Restructured `classify()` to check shell-error prefix BEFORE calling `is_missing()`: if val is a non-NA string starting with a SHELL_ERROR_PREFIXES element, return ERROR immediately; only then call `is_missing()` for the MISSING check
- **Files modified:** `app/services/result_normalizer.py`
- **Verification:** All 65 tests pass after fix
- **Committed in:** `86211aa` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — pandas 3.x compatibility + classify ordering)
**Impact on plan:** Both fixes required for correct behavior. No scope creep. The classify() fix resolves an inherent tension in the spec (is_missing includes shell errors, but classify must return ERROR not MISSING for them).

## Issues Encountered

- No virtual environment existed in the project; created `.venv` with `python3 -m venv` and installed `pandas` + `pytest` + `pytest-mock` to satisfy test infrastructure requirement. This is a normal project setup step, not a blocker.

## Known Stubs

None — all functions are fully implemented and tested.

## Threat Flags

No new threat surface introduced. Module is a pure-Python data transformation leaf with no network calls, file I/O, or external dependencies beyond pandas.

## Next Phase Readiness

- `app/services/result_normalizer.py` API is stable and fully tested — Plan 03 (`ufs_service`) can import from it immediately
- Test infrastructure (`.venv`, `tests/` package, `pytest`) is in place for Plan 03 TDD work
- `try_numeric()` is ready for the chart path in `browse.py` (VIZ-02)

---
*Phase: 01-foundation-browsing*
*Completed: 2026-04-23*
