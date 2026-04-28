---
phase: 05-overview-redesign
plan: 02
subsystem: service
tags: [content-store, frontmatter, yaml, parser, defensive, memoize, mtime-ns, tdd, d-ov-02, d-ov-12]

# Dependency graph
requires:
  - phase: 03-content-pages
    provides: content_store.py (read_content / save_content / get_content_mtime_ns / _safe_target / DEFAULT_CONTENT_DIR / MAX_CONTENT_BYTES) — Plan 05-02 appends without modifying any existing function
provides:
  - "read_frontmatter(platform_id, content_dir) -> dict[str, str] — defensive YAML frontmatter parser, never raises, returns {} on every error path, memoized by (platform_id, mtime_ns) per D-OV-12"
  - "_parse_frontmatter_text(text) -> dict[str, str] — pure-text parser helper (no I/O), reusable, exhaustive defensive contract"
  - "_FRONTMATTER_CACHE: dict[tuple[str, int], dict[str, str]] — module-level memoize cache, implicit invalidation via mtime_ns"
  - "tests/v2/test_content_store_frontmatter.py — 15 unit tests covering valid/12-PM-keys, defensive returns, Korean unicode, cache hit + miss-on-mtime-change, type coercion, cache key shape"
affects: [05-03-overview-grid-service, 05-04-routes, 05-05-templates, 05-06-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Defensive YAML parser: yaml.safe_load EXCLUSIVELY (never the unsafe full loader); every exception path returns {}; bare yaml.load token absent from source per acceptance grep — auditable defense against T-05-02-01 RCE"
    - "mtime_ns-keyed memoize: cache invalidates implicitly when file changes (no cache.clear() needed); reuses existing get_content_mtime_ns() so no second stat() call"
    - "Pure-text parser helper (_parse_frontmatter_text) separated from I/O wrapper (read_frontmatter) — testable without filesystem; unit-testable in isolation if a future caller wants in-memory parsing"
    - "Value coercion: str(v) for every non-None value (handles datetime.date, int, bool, float); None values DROPPED from result (caller can use `key in result` to test missing-vs-empty without coercing 'None' string to a value)"

key-files:
  created:
    - "tests/v2/test_content_store_frontmatter.py (15 tests, ~210 lines)"
  modified:
    - "app_v2/services/content_store.py (+118 lines appended — _FRONTMATTER_CACHE, _parse_frontmatter_text, read_frontmatter; existing 5 functions byte-stable)"

key-decisions:
  - "Plan acceptance grep `grep -cE \"\\byaml\\.load\\b\" returns 0` is intentionally strict — it bans the bare token even in comments. Initial implementation used the comment phrase 'yaml.load is unsafe', tripping the grep at line 133. Comment rephrased to '...the unsafe full loader is banned by acceptance grep' so the audit pattern stays clean. (Rule 3 — Blocking auto-fix; necessary for plan acceptance criterion to pass.)"
  - "Cache key is (platform_id, mtime_ns) — NOT (platform_id, content_dir, mtime_ns). Rationale: production has one CONTENT_DIR per process (module-level constant on platforms_router); tests use one tmp_path per test with autouse fixture clearing the cache. If a future feature ever needs multi-dir lookup in the same process, the cache key MUST be widened — Test 14 (structural) guards the current 2-tuple shape so any future widening is forced to update the test in lockstep."
  - "yaml.safe_load returns None for empty fences (`---\\n---\\n`) — handled in _parse_frontmatter_text via `not isinstance(data, dict): return {}` (catches both empty-fences AND non-mapping top-level like list/scalar in one branch). Single guard, two threats covered."
  - "Decision: catch `_yaml.YAMLError` AND a bare `Exception` as separate except clauses. YAMLError is the documented public exception; the bare Exception is defensive against any C-extension parser anomaly (libyaml binding bugs, encoding errors mid-parse). `noqa: BLE001` documents the intent — never raise on caller per D-OV-02."

patterns-established:
  - "Defensive parser pattern: pure-text helper (no I/O, exhaustive return-{}-on-error) + thin I/O wrapper (mtime check + cache + read + delegate to helper). Reusable for any future content-page extractor (e.g., a TOC scanner, a body-summary extractor)."
  - "mtime_ns memoize pattern: pair the existing get_content_mtime_ns() helper with a module-level dict[tuple[pid, mtime_ns], result]. No threading.Lock needed because the dict[get/set] is GIL-atomic for the single-key access pattern AND mtime_ns is monotonic per file (a stale cache entry can never be returned because the mtime_ns key wouldn't match)."
  - "Audit-grep-friendly comment hygiene: when a security contract is enforced via `grep -cE pattern returns 0`, even illustrative mentions of the banned pattern in source comments must avoid the bare token. Use rephrasing ('the unsafe full loader') or hyphenation ('yaml-load') instead. Establishes a Phase-5+ convention for any future grep-banned token."

requirements-completed: [OVERVIEW-V2-02]

# Metrics
duration: 8min
completed: 2026-04-28
---

# Phase 5 Plan 02: Frontmatter Parser Summary

**Added defensive `read_frontmatter(platform_id, content_dir) -> dict[str, str]` to `content_store.py` — yaml.safe_load only, never raises, memoized by `(platform_id, mtime_ns)` for O(1) re-reads on unchanged files. 15 unit tests cover valid 12-PM-key parse, every defensive return path, Korean unicode round-trip, cache hit + miss-on-mtime-change, and value type coercion.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-28T06:50:50Z
- **Completed:** 2026-04-28T06:58:49Z
- **Tasks:** 1 (TDD: RED → GREEN, no REFACTOR needed)
- **Files modified:** 2 (content_store.py +118 lines; new test_content_store_frontmatter.py)

## Accomplishments

- `read_frontmatter` lives on `app_v2.services.content_store` as a top-level export, callable as `from app_v2.services.content_store import read_frontmatter` — Plan 05-03's `overview_grid_service.build_overview_grid_view_model` can iterate curated PIDs and call this for every row's PM metadata in a tight loop without re-reading unchanged files.
- All 5 existing content_store functions (`render_markdown`, `_safe_target`, `read_content`, `save_content`, `delete_content`, `get_content_mtime_ns`) are byte-stable — 0 modifications; `grep -c 'def <name>('` for each returns exactly 1.
- 15 unit tests pass on first GREEN run (TDD RED phase confirmed via initial AttributeError on `_FRONTMATTER_CACHE`). Plan gate ≥14 → 15 collected; full v2 suite 290 passed (up from 275 baseline → +15 new tests, zero regressions).
- T-05-02-01 (YAML deserialization RCE) mitigated: `grep -cE '\byaml\.load\b' app_v2/services/content_store.py` returns 0; only `yaml.safe_load` ever called.
- T-05-02-02 (path traversal) mitigated: `read_frontmatter("../../etc/passwd", tmp_path)` returns `{}` via the existing `get_content_mtime_ns` → `_safe_target` → `Path.resolve().relative_to()` chain (defense in depth alongside FastAPI route regex).
- T-05-02-05 (cache stale-after-delete) mitigated: file deletion makes `get_content_mtime_ns` return `None`, short-circuiting BEFORE cache lookup → stale entry can never be returned.

## Task Commits

1. **Task 1: Add read_frontmatter to content_store.py with mtime_ns memoize + defensive YAML parse** — `ff30417` (feat) — combined RED+GREEN since the test file is new and all 15 tests passed on first GREEN run; no separate REFACTOR commit needed because the helper extraction (`_parse_frontmatter_text`) was part of the initial implementation, not a post-pass cleanup.

## Files Created/Modified

- `app_v2/services/content_store.py` — appended 118 lines after `get_content_mtime_ns`: import block, header docblock, `_FRONTMATTER_CACHE` declaration, `_parse_frontmatter_text` helper, `read_frontmatter` public function. No edits above the appended block.
- `tests/v2/test_content_store_frontmatter.py` — new file, 15 tests, ~210 lines. Mirrors `tests/v2/test_content_store.py::_write` fixture style. `autouse=True` `_clear_cache` fixture ensures every test starts and ends with an empty `_FRONTMATTER_CACHE` (test isolation).

## Test Roster (15)

| # | Test | Concern |
|---|------|---------|
| 1 | `test_read_frontmatter_returns_dict_for_valid_yaml` | Happy path: 12 PM keys present, all `isinstance(str)`, `assignee=홍길동`, body markdown excluded |
| 2 | `test_read_frontmatter_no_leading_fence_returns_empty` | File starts with `# Heading` (no `---\n`) → `{}` |
| 3 | `test_read_frontmatter_missing_closing_fence_returns_empty` | `---\ntitle: Foo\n` (no second `---`) → `{}` |
| 4 | `test_read_frontmatter_malformed_yaml_returns_empty` | `[unclosed bracket` → YAMLError caught → `{}` |
| 5 | `test_read_frontmatter_empty_fences_returns_empty` | `---\n---\n` → `safe_load("")` returns None → `{}` |
| 6 | `test_read_frontmatter_missing_file_returns_empty` | File doesn't exist; no FileNotFoundError → `{}` |
| 7 | `test_read_frontmatter_traversal_returns_empty` | `../../etc/passwd` → `_safe_target` ValueError → `{}` |
| 8 | `test_read_frontmatter_unicode_korean_roundtrip` | UTF-8 read + safe_load preserves 한글 byte-for-byte |
| 9 | `test_read_frontmatter_caches_on_first_call` | After call, `(P1, mtime_ns)` key present in `_FRONTMATTER_CACHE` |
| 9b | `test_read_frontmatter_does_not_reread_on_cache_hit` | `monkeypatch read_content` after prime → second call hits cache, count stays 0 |
| 10 | `test_read_frontmatter_invalidates_on_mtime_change` | `os.utime(target, ns=(_, +1s))` → second call returns NEW content |
| 11 | `test_read_frontmatter_coerces_date_to_str` | `start: 2026-04-01` (yaml → datetime.date) → `"2026-04-01"` (str) |
| 12 | `test_read_frontmatter_coerces_int_bool_drops_null` | `year: 2026` → `"2026"`; `active: true` → `"True"`; `flag: null` → key absent |
| 13 | `test_read_frontmatter_rejects_non_dict_yaml` | `- item1\n- item2` (yaml → list) → `{}` |
| 14 | `test_frontmatter_cache_key_is_pid_mtime_tuple` | Structural: every `_FRONTMATTER_CACHE` key is `(str, int)` 2-tuple |

## Decisions Made

- **Comment hygiene rephrase for audit-grep compliance** — the original implementation comment `# - Uses yaml.safe_load EXCLUSIVELY (T-05-02-01: yaml.load is unsafe)` tripped the plan's own acceptance criterion `grep -cE '\byaml\.load\b' returns 0` because the bare `yaml.load` token appears even inside a comment. Rephrased to `# - Uses yaml.safe_load EXCLUSIVELY (T-05-02-01: the unsafe full loader is banned by acceptance grep — see verification block in Plan 05-02)` so the contract holds end-to-end.
- **Two-tier exception catching in `_parse_frontmatter_text`** — explicit `except _yaml.YAMLError` (the documented exception class for public `safe_load` calls) followed by bare `except Exception: noqa: BLE001` (defense against any libyaml C-binding anomaly or encoding mid-parse error). Both branches return `{}` per D-OV-02.
- **Cache key is `(pid, mtime_ns)` — NOT `(pid, content_dir, mtime_ns)`** — production has one CONTENT_DIR per process (module-level constant on platforms router); tests use one `tmp_path` per test with autouse fixture clearing the cache between tests. If multi-dir support is ever added, Test 14 (structural assertion on key shape) will force the test update in lockstep with the implementation widening.
- **Helper extraction (`_parse_frontmatter_text`) was part of initial implementation** — separating pure-text parsing (no I/O) from the I/O wrapper makes the parser unit-testable in isolation if a future caller wants in-memory parsing (e.g., a CLI dump tool that reads from stdin). The plan's `<action>` block specified this structure; no post-implementation refactor needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan acceptance grep tripped on illustrative comment mentioning `yaml.load`**

- **Found during:** Task 1 verification (after GREEN tests passed but before commit) — running `grep -cE '\byaml\.load\b' app_v2/services/content_store.py` returned 1, not 0.
- **Issue:** The plan's `<action>` block dictated the exact docblock text `# - Uses yaml.safe_load EXCLUSIVELY (T-05-02-01: yaml.load is unsafe).` The plan's own acceptance criterion `grep -cE "\byaml\.load\b" app_v2/services/content_store.py returns 0` is intentionally strict — it bans the bare `yaml.load` token everywhere in the file, including comments (defense against grep-based audits and copy-paste regressions where a future contributor might accidentally use the unsafe loader). The `<action>` text and the `<acceptance_criteria>` were internally inconsistent.
- **Fix:** Rephrased the comment to `# - Uses yaml.safe_load EXCLUSIVELY (T-05-02-01: the unsafe full loader is\n#   banned by acceptance grep — see verification block in Plan 05-02).` The phrase "the unsafe full loader" preserves the contract documentation intent without using the banned bare token. The acceptance grep now returns 0.
- **Files modified:** `app_v2/services/content_store.py` (1 comment line rephrased to 2 lines)
- **Verification:** `grep -cE '\byaml\.load\b' app_v2/services/content_store.py` returns 0; `grep -q 'yaml.safe_load(' app_v2/services/content_store.py` succeeds; all 15 tests still pass (no behavior change — comment-only edit).
- **Committed in:** `ff30417` (combined Task 1 commit — fix landed before commit, not a separate cleanup)
- **Why this preserves the contract:** The intent of the comment was to document WHY safe_load is exclusive — that intent survives the rephrase ("the unsafe full loader" is unambiguous in context). The acceptance criterion's intent (grep-auditable ban on the unsafe API) is now physically enforced. Establishes a Phase-5+ comment-hygiene convention for any future token banned by audit grep.

---

**Total deviations:** 1 auto-fixed (Rule 3 — plan-internal contradiction between mandated docblock text and acceptance grep)
**Impact on plan:** Auto-fix necessary for Task 1 acceptance criterion to pass. Zero behavior change in production code (comment-only). Zero scope creep — the audit grep contract was respected, not weakened.

## Issues Encountered

- None beyond the documented Rule-3 deviation.

## Edge Cases Discovered During TDD

The original plan listed 14 tests; the implementation needed 15 because Test 9 has TWO distinct concerns:
- 9 (`test_read_frontmatter_caches_on_first_call`) — proves the cache KEY is populated
- 9b (`test_read_frontmatter_does_not_reread_on_cache_hit`) — proves the cache HIT short-circuits before `read_content`

These are independent invariants — a cache could be populated but still be re-read (e.g., a buggy implementation that always falls through to `read_content` and overwrites the cache entry every call). Splitting to two tests catches both bugs separately. The plan's `<behavior>` Test 9 description allowed either approach (`Alternatively: introspect _FRONTMATTER_CACHE directly OR monkeypatch read_content`); implementing both is strictly stronger.

YAML spec corner cases NOT explicitly in the original test list but DEFAULTED-handled by the implementation:
- `~` for null — `yaml.safe_load('key: ~')` returns `{'key': None}` → key dropped per Test 12 contract (None values dropped). Not separately tested because the existing `null` literal test (Test 12) covers the same code path; YAML treats `~` and `null` and `Null` and `NULL` identically.
- Anchor / alias references (`&anchor` / `*anchor`) — `safe_load` resolves them naturally; would just produce duplicate-value strings. Not malicious because alias expansion in `safe_load` is bounded by the 64KB content size cap (T-05-02-03 disposition: accept).
- Block scalars (`|` / `>`) — would produce multi-line string values; `str(v)` on a string is identity. Not separately tested but would round-trip correctly.

These are documented for future maintainers — no action needed in this plan.

## Cache Key & Invalidation (Test 10 cited)

- **Cache key:** `(platform_id: str, mtime_ns: int)` — 2-tuple, structurally enforced by Test 14.
- **Invalidation:** implicit via `mtime_ns` change. Test 10 proves this end-to-end:
  1. Write file with `title: Old`, call `read_frontmatter` → caches `("P1", mtime1) → {"title": "Old"}`.
  2. Re-write file with `title: New`, then `os.utime(target, ns=(_, mtime1 + 1_000_000_000))` to bump mtime by exactly 1 second (deterministic across filesystems regardless of FS mtime resolution — ext4, NTFS, APFS all support ns precision; even on FAT32-rounded systems +1s is far above the resolution).
  3. Second call to `read_frontmatter` looks up `("P1", mtime2)` — cache miss because `mtime2 != mtime1` — re-reads file, caches new entry, returns `{"title": "New"}`.
- **Stale entries after file delete:** when a file is deleted, `get_content_mtime_ns` returns `None` and `read_frontmatter` returns `{}` BEFORE consulting the cache (line `if mtime_ns is None: return {}` is BEFORE the cache lookup). The stale cache entry remains in memory but is never returned. Memory leak is bounded by `len(curated_pids) ≤ ~100` entries — accept (T-05-02-05 disposition).

## Plan 05-03 Dependency Note

Plan 05-03 (`overview_grid_service.build_overview_grid_view_model`) will call `read_frontmatter(pid, content_dir)` once per curated PID on every `GET /overview` and `POST /overview/grid` request. With `< ~100` curated PIDs, the first request triggers up to ~100 file reads + YAML parses; subsequent requests on unchanged files are O(1) per row (dict lookup). Cache hit ratio is expected to approach 100% under typical browsing (filter / sort changes don't invalidate the cache because the underlying files don't change). The cache invalidates implicitly when a user edits a content page via Phase 3's `POST /platforms/<pid>/content` (which calls `save_content` → atomic write → mtime advances). No explicit cache-clear hook is needed in the content-write path.

## Next Phase Readiness

- **Plan 05-03** (overview_grid_service) — DIRECT consumer of `read_frontmatter`. Ready to import: `from app_v2.services.content_store import read_frontmatter`. Iterate curated PIDs, call once per row, populate `OverviewRow` from the returned dict (with `—` em-dash for missing keys per D-OV-09).
- **Plan 05-04** (routes) — indirect consumer via 05-03 service. No direct import.
- **Plan 05-05** (templates) — indirect consumer via 05-03 view model. The picker_popover macro from Plan 05-01 is already parameterized (form_id, hx_post, hx_target) and ready for `_filter_bar.html`'s 6-popover invocation.
- **Plan 05-06** (invariants) — will likely add a static-analysis test asserting `read_frontmatter` uses `yaml.safe_load` exclusively (the in-file grep is already clean; a Phase-5 invariant test would lift this to a CI-enforced contract).

---
*Phase: 05-overview-redesign*
*Completed: 2026-04-28*

## Self-Check: PASSED

Verified files exist:
- FOUND: app_v2/services/content_store.py (modified — `read_frontmatter`, `_parse_frontmatter_text`, `_FRONTMATTER_CACHE` present; existing 5 functions byte-stable)
- FOUND: tests/v2/test_content_store_frontmatter.py (new — 15 tests collected and passing)

Verified commits exist:
- FOUND: ff30417 (Task 1: feat(05-02): add read_frontmatter to content_store with mtime_ns memoize (D-OV-02, D-OV-12))

Verified contracts:
- FOUND: `from app_v2.services.content_store import read_frontmatter` succeeds (`importable OK`)
- FOUND: `grep -q 'yaml.safe_load(' app_v2/services/content_store.py` succeeds
- FOUND: `grep -cE '\byaml\.load\b' app_v2/services/content_store.py` returns 0
- FOUND: `grep -q '_FRONTMATTER_CACHE: dict\[tuple\[str, int\], dict\[str, str\]\]' app_v2/services/content_store.py` succeeds
- FOUND: 15/15 tests pass in `tests/v2/test_content_store_frontmatter.py`
- FOUND: 65/65 Phase 1-4 regression tests pass (test_content_store + test_content_routes + test_content_store_race + test_summary_routes)
- FOUND: 290 passed / 1 skipped in full v2 suite (up from 275/1 baseline → +15 new tests, zero regressions)
