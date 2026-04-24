---
phase: 02-nl-agent-layer
plan: "02"
subsystem: agent-safety
tags: [sqlparse, security, SAFE-02, SAFE-03, SAFE-04, SAFE-06, NL-09, tdd]
requirements_addressed: [SAFE-02, SAFE-03, SAFE-06, NL-09]

dependency_graph:
  requires: []
  provides:
    - app.services.sql_validator.validate_sql
    - app.services.sql_validator.ValidationResult
    - app.services.sql_limiter.inject_limit
    - app.services.path_scrubber.scrub_paths
    - app.services.ollama_fallback.extract_json
  affects:
    - app/core/agent/nl_agent.py (Plan 02-03 composes all four primitives)

tech_stack:
  added: []
  patterns:
    - sqlparse AST token walk for table extraction (FROM/JOIN keyword traversal)
    - re.compile(IGNORECASE) for case-insensitive LIMIT detection
    - Multi-stage JSON fallback chain (json.loads → fence-strip → regex brace block)

key_files:
  created:
    - app/services/sql_validator.py
    - app/services/sql_limiter.py
    - app/services/path_scrubber.py
    - app/services/ollama_fallback.py
    - tests/services/test_sql_validator.py
    - tests/services/test_sql_limiter.py
    - tests/services/test_path_scrubber.py
    - tests/services/test_ollama_fallback.py
  modified: []

decisions:
  - "Subquery alias detection: Identifier whose first meaningful token is Parenthesis is a subquery alias — recurse into Parenthesis, skip alias name"
  - "inject_limit uses regex sub(count=1) to prevent double-replacement; idempotent by design (Pitfall 5)"
  - "extract_json returns None for JSON arrays — agent always outputs dict (SQLResult or ClarificationNeeded)"
  - "scrub_paths regex /(?:sys|proc|dev)/\\S* — \\S* matches non-whitespace, handles /dev/null and multi-segment paths"
  - "Pitfall 4 addressed: statement count check len(statements)==1 before get_type() — rejects SELECT;DROP even though first get_type() returns SELECT"

metrics:
  duration: "5 min"
  completed_date: "2026-04-24"
  tasks_completed: 4
  files_created: 8
  tests_total: 53
  tests_passed: 53
---

# Phase 02 Plan 02: Safety Primitives Summary

**One-liner:** Four pure-function safety primitives (sqlparse SELECT validator, idempotent LIMIT injector, /sys//proc//dev/ path scrubber, Ollama JSON fallback chain) implemented TDD with 53 passing tests.

## What Was Built

### Public API Contracts

```python
# app/services/sql_validator.py — SAFE-02
class ValidationResult(BaseModel):
    ok: bool
    reason: str = ""

def validate_sql(sql: str, allowed_tables: list[str]) -> ValidationResult: ...

# app/services/sql_limiter.py — SAFE-03
def inject_limit(sql: str, row_cap: int) -> str: ...

# app/services/path_scrubber.py — SAFE-06
def scrub_paths(text: str) -> str: ...

# app/services/ollama_fallback.py — NL-09
def extract_json(raw: str) -> dict | None: ...
```

### Module Details

**`sql_validator.py` (125 lines)**
- `ValidationResult`: Pydantic BaseModel with `ok: bool` and `reason: str = ""`
- `validate_sql`: Rejects if: statement count != 1 (Pitfall 4), type != SELECT, any comment token, any table outside `allowed_tables`
- `_extract_table_names`: Recursive AST walk via FROM/JOIN keywords; handles IdentifierList (comma-separated tables) and Parenthesis (subqueries); subquery aliases correctly excluded

**`sql_limiter.py` (45 lines)**
- `inject_limit`: Regex `\bLIMIT\s+(\d+)\b` with IGNORECASE; strips trailing semicolons and whitespace; clamps LIMIT > row_cap; leaves LIMIT <= row_cap unchanged; appends when absent
- Idempotent per Pitfall 5: `test_double_call_no_double_limit` and `test_triple_call_idempotent` verify no double-LIMIT

**`path_scrubber.py` (25 lines)**
- `scrub_paths`: Regex `/(?:sys|proc|dev)/\S*` replaces all `/sys/`, `/proc/`, `/dev/` substrings with `<path>`; handles multiple occurrences; `/usr/` and other paths pass through unchanged

**`ollama_fallback.py` (68 lines)**
- `extract_json`: 3-stage chain: (1) `json.loads(raw)`, (2) strip ```` ```json ``` ```` / ```` ``` ``` ```` fences + retry, (3) regex `\{.*\}` DOTALL + retry; returns `dict | None`; JSON arrays rejected (agent always outputs dict)

## Test Coverage

| File | Tests | Key Branches Covered |
|------|-------|----------------------|
| test_sql_validator.py | 18 | Simple SELECT, WHERE/ORDER/LIMIT, self-join, subquery, case-insensitive table, multi-statement (Pitfall 4), DROP/INSERT/UPDATE/DELETE, line comment, block comment, disallowed table, IdentifierList, empty, whitespace |
| test_sql_limiter.py | 11 | No LIMIT, trailing whitespace, semicolon strip, clamp above/below/at cap, lowercase, mixed-case, double-call (Pitfall 5), triple-call |
| test_path_scrubber.py | 11 | /sys/, /proc/, /dev/, /dev/null, multi-occurrence, /usr/ passthrough, plain text, empty string |
| test_ollama_fallback.py | 13 | Clean JSON, nested dict, ```json fence, plain fence, extra whitespace, prose-before, multiline embedded, plain-text fail, empty fail, array fail, malformed fail |
| **Total** | **53** | |

## Pitfall Mitigations Addressed

**Pitfall 4 (Multi-statement SQL passes get_type() check):**
- Addressed by: `len([s for s in sqlparse.parse(sql) if s.tokens and s.get_type() is not None]) != 1`
- Covered by: `test_two_selects` and `test_select_then_drop`

**Pitfall 5 (LIMIT injection double-applies on Regenerate):**
- Addressed by: `_LIMIT_RE.search()` + conditional sub — only replaces if existing > row_cap, otherwise returns unchanged
- Covered by: `test_double_call_no_double_limit` and `test_triple_call_idempotent`

## Dependency Direction

These four modules have NO imports from each other or from Plan 02-03. They are pure leaves:

```
Plan 02-03 (nl_agent.py run_sql tool)
    ├── app.services.sql_validator.validate_sql
    ├── app.services.sql_limiter.inject_limit
    ├── app.services.path_scrubber.scrub_paths
    └── app.services.ollama_fallback.extract_json
```

None of the four modules imports from Streamlit, SQLAlchemy, pandas, or any other I/O library. They are safe to test in isolation without any environment setup.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Subquery alias incorrectly added to disallowed tables**
- **Found during:** Task 1 GREEN phase — `test_subquery_select` failed
- **Issue:** `SELECT * FROM (SELECT Item, Result FROM ufs_data) AS sub` — the outer `Identifier` wrapping `(SELECT ...) AS sub` has `get_real_name()` returning `"sub"` (the alias), not a table name
- **Fix:** Before calling `get_real_name()`, check if the Identifier's first meaningful token is a `Parenthesis`. If so, recurse into the Parenthesis (walk the subquery) and skip adding the alias name
- **Files modified:** `app/services/sql_validator.py`
- **Commit:** 19d7349 (GREEN commit included the fix)

## Known Stubs

None — all four modules are complete implementations. No placeholder values or hardcoded empty returns.

## Threat Flags

No new network endpoints, auth paths, or trust boundaries introduced. All four modules are pure functions with no I/O.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 64e44a5 | test RED | add failing tests for validate_sql (SAFE-02) — 18 tests |
| 19d7349 | feat GREEN | implement validate_sql (SAFE-02) with subquery fix |
| b35bba9 | test RED | add failing tests for inject_limit (SAFE-03) — 11 tests |
| 3ef2e26 | feat GREEN | implement inject_limit (SAFE-03) idempotent |
| 7a6a270 | test RED | add failing tests for scrub_paths (SAFE-06) — 11 tests |
| 8fefa8f | feat GREEN | implement scrub_paths (SAFE-06) |
| 7cd31e7 | test RED | add failing tests for extract_json (NL-09) — 13 tests |
| fc40159 | feat GREEN | implement extract_json Ollama fallback chain (NL-09) |

## Self-Check: PASSED
