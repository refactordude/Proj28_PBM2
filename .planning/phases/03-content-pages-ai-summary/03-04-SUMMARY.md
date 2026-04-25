---
phase: 03-content-pages-ai-summary
plan: 04
subsystem: testing
tags: [integration, cross-process, race-test, multiprocessing, fork, ttlcache, regression-guard, invariants, tdd, htmx, fastapi]

# Dependency graph
requires:
  - phase: 03-content-pages-ai-summary
    plan: 01
    provides: app_v2/data/atomic_write.py::atomic_write_bytes (D-30 single source of truth verified by invariant guard); pytest 'slow' marker registration target
  - phase: 03-content-pages-ai-summary
    plan: 02
    provides: app_v2/services/content_store.py::save_content/read_content/get_content_mtime_ns (cross-process race subject + integration test seam); app_v2/routers/platforms.py POST /platforms/{pid} save route (end-to-end save→summary chain entry)
  - phase: 03-content-pages-ai-summary
    plan: 03
    provides: app_v2/services/summary_service.py::get_or_generate_summary + _summary_cache + clear_summary_cache (integration + concurrency test surface); app_v2/routers/summary.py POST /platforms/{pid}/summary (always-200 contract under test)
provides:
  - tests/v2/test_content_store_race.py — D-24 verbatim cross-process save race + ThreadPool single-process race (2 tests)
  - tests/v2/test_summary_integration.py — 7 end-to-end TestClient integration tests (save→summary chain, cache hit, X-Regenerate write-back, mtime invalidation, ConnectError fragment, missing-content fragment, concurrent same-key thread test)
  - tests/v2/test_phase03_invariants.py — 8 invariant guards (12 cases incl. parametrize) covering INFRA-05, Pitfall 1, UI-SPEC always-200, banned libs, D-21 stream=False, D-17 TTLCache dimensions, Pitfall 13 mtime_ns, D-30 atomic_write_bytes single-source-of-truth
  - tests/v2/conftest.py — registers `slow` pytest marker (silences PytestUnknownMarkWarning + enables `-m 'not slow'` opt-out)
affects: [04-browse-tab-port, 05-ask-tab-port]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Cross-process race test via multiprocessing.get_context("fork") with module-top-level worker (A5 picklability constraint)
    - End-to-end TestClient integration pattern with mocked _build_client only (D-23 — no transport-layer mocking)
    - Per-call MagicMock response queue for testing cache invalidation chains (mock_client.chat.completions.create.side_effect = list-iterator function)
    - Codebase-level static-analysis grep guards as automated CI policy enforcement (replaces manual code-review checklist for locked decisions)
    - Word-boundary regex (`\bword\b`) in invariant grep tests to avoid false-positives on docstring phrases

key-files:
  created:
    - tests/v2/test_content_store_race.py
    - tests/v2/test_summary_integration.py
    - tests/v2/test_phase03_invariants.py
    - tests/v2/conftest.py
  modified: []

key-decisions:
  - "Cross-process race test (D-24) uses fork-only POSIX semantics — module-top-level worker function (A5) for picklability; @pytest.mark.slow + @pytest.mark.skipif(sys.platform == 'win32') guards keep Windows CI green while Linux/macOS CI runs the real fork test."
  - "tests/v2/conftest.py registers the `slow` marker locally (no project-level pyproject.toml [tool.pytest.ini_options] section was created) so the addinivalue_line registration is scoped to the directory under test."
  - "Per-call response queue in test_summary_after_content_edit_invalidates_cache uses a closure with index list (idx[0] += 1) instead of `type(r)()` cloning — MagicMock instances are not callable as types; the closure pattern is the canonical pytest-mock idiom for stateful side_effects."
  - "test_summary_route_never_returns_5xx uses `\\braise\\s+HTTPException\\b` (word-boundary) so the docstring phrase 'NEVER raises HTTPException' (which contains 'raises HTTPException', no `raise ` token) cannot trigger a false-positive."
  - "test_no_banned_libraries_imported_in_app_v2 anchors `^\\s*(import|from)\\s+<lib>` so docstring/comment occurrences cannot trip the guard — only actual import statements at line start (with optional indent) are checked."
  - "Integration fixture replaces app.state.settings = Settings(...) AFTER `with TestClient(app)` lifespan ran — mirrors the proven pattern from test_summary_routes.py::isolated_summary instead of mutating sub-attributes of the existing pydantic model."

patterns-established:
  - "Pattern: cross-process race test via fork with module-top-level worker. Required by D-24 user override; Plan 03-04 is the canonical example. Future phases adding cross-process invariants follow the same skeleton (ctx = mp.get_context('fork'); ctx.Process(target=_module_level_worker, args=...); join with timeout; assert exitcode == 0; assert post-conditions on the shared filesystem state)."
  - "Pattern: codebase-level invariant guards as test files. Locked decisions (D-numbers, pitfalls, contract mandates) get a grep-style test in tests/v2/test_phase03_invariants.py. CI fails any future PR that violates the pinned decision before review."
  - "Pattern: integration tests sit alongside unit tests but use the FULL FastAPI app via TestClient with only the LLM client mocked. Differs from route-unit-tests (which mock the service module's call surface) by exercising the real route → service → content_store seam."

requirements-completed: [CONTENT-06, SUMMARY-05]

# Metrics
duration: 7min
completed: 2026-04-25
---

# Phase 03 Plan 04: Cross-Process Race + Integration + Invariants Summary

**D-24 cross-process race test (multiprocessing.fork + module-top-level worker, 3 explicit assertions) + 7 end-to-end integration tests via TestClient (full save→summary chain with mocked LLM only) + 8 invariant guards (12 cases via parametrize) covering INFRA-05, Pitfall 1, UI-SPEC always-200, 4 banned libraries, D-17/D-21/D-30, and Pitfall 13. Test count 207 → 228 (v2) / 390 → 411 (full project), 0 failures, all locked decisions now backed by automated CI guards.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-04-25T21:06:21Z
- **Completed:** 2026-04-25T21:13:37Z
- **Tasks:** 3 (all auto, no TDD — final-wave verification plan)
- **Commit boundaries:** 3 (one per task)
- **Files created:** 4 (3 test files + 1 conftest.py)
- **Files modified:** 0

## Accomplishments

- **D-24 cross-process race test** — verbatim user-mandated test using `multiprocessing.get_context("fork")` with 2 workers writing different payloads (3000-byte 'A' vs 'B') to the same target. Module-top-level `_save_in_worker` (A5 picklability). Three explicit assertions verified on the local Linux box: (1) file content equals one of the two payloads in full (no hybrid); (2) no leftover `.{pid}.md.*.tmp` tempfile in content_dir; (3) file mode is exactly 0o644. `@pytest.mark.slow` + skip-on-win32. Single-process ThreadPool counterpart (8 threads × 4 workers) catches exception/cleanup leaks within one Python interpreter.
- **End-to-end summary integration tests** (7 tests via TestClient) — exercise the full route → service → content_store → mocked LLM seam. Covers: (1) save→summary chain with bullets + ollama metadata footer; (2) cache hit on second call (1 LLM invocation total); (3) X-Regenerate header bypasses lookup but writes back (D-18 — 2 LLM calls across 3 requests); (4) mtime_ns changes on save invalidate the cache (per-call response queue distinguishes resp 1 vs resp 2); (5) httpx.ConnectError → 200 + amber alert (UI-SPEC contract); (6) missing content file → 200 + "Content page no longer exists"; (7) 8-thread ThreadPoolExecutor concurrent same-key call → all 8 SummaryResults returned, `_summary_cache` contains exactly 1 entry post-run (Pitfall 11 — lock guards dict access only).
- **Phase 03 invariant guards** — 8 unique test functions (12 cases via parametrize) enforce locked decisions as automated CI policy:
  - `test_no_async_def_in_phase03_routers` (parametrize: platforms.py, summary.py) — INFRA-05.
  - `test_no_default_markdownit_constructor_in_app_v2` — Pitfall 1; rejects any `MarkdownIt(...)` whose first arg ≠ `'js-default'`/`"js-default"`.
  - `test_summary_route_never_returns_5xx` — UI-SPEC contract; greps for `status_code\s*=\s*5\d\d` AND `\braise\s+HTTPException\b` (word-boundary avoids docstring false-positive).
  - `test_no_banned_libraries_imported_in_app_v2` (parametrize: langchain, litellm, vanna, llama_index) — CLAUDE.md "What NOT to Use" enforcement.
  - `test_summary_service_uses_stream_false` — D-21 single-shot guard.
  - `test_summary_ttlcache_uses_locked_dimensions` — D-17 verbatim guard.
  - `test_summary_cache_key_uses_mtime_ns` — Pitfall 13 sharpening guard.
  - `test_atomic_write_bytes_is_single_source_of_truth` — D-30; asserts def lives ONLY in `app_v2/data/atomic_write.py` AND that `overview_store` + `content_store` both import (don't reimplement).
- **Pytest `slow` marker registered** in `tests/v2/conftest.py` so the cross-process test does not emit `PytestUnknownMarkWarning` and CI can opt out via `-m 'not slow'` if needed.
- **Test count:** 207 → 228 v2 tests (+21); 390 → 411 full-project tests (+21); 0 regressions, 0 failures.

## Task Commits

1. **Task 1:** `a0c64b4` test(03-04): add D-24 cross-process race test + ThreadPool race
2. **Task 2:** `46037b6` test(03-04): add end-to-end summary integration + concurrent thread tests
3. **Task 3:** `4bec1e2` test(03-04): add Phase 03 codebase invariant guards

## Files Created/Modified

### Created

- `tests/v2/test_content_store_race.py` (130 lines) — `_save_in_worker` module-top-level + `test_cross_process_save_race` (slow + skip-win32) + `test_thread_pool_save_race_no_corruption`.
- `tests/v2/test_summary_integration.py` (≈300 lines) — `integrated_app` fixture + 7 tests covering save→summary, cache hit, X-Regenerate, mtime invalidation, ConnectError fragment, missing-content fragment, concurrent same-key threads.
- `tests/v2/test_phase03_invariants.py` (≈230 lines) — 8 guard functions, 12 cases via parametrize.
- `tests/v2/conftest.py` (20 lines) — `pytest_configure` registers `slow` marker.

### Modified

None — Plan 03-04 only adds tests; no production code changes.

## D-24 Race Test Details

**Worker:**
```python
def _save_in_worker(content_dir_str: str, pid: str, payload: str) -> None:
    from app_v2.services.content_store import save_content
    save_content(pid, payload, content_dir=Path(content_dir_str))
```

**Driver (verbatim from RESEARCH.md A5):**
```python
ctx = multiprocessing.get_context("fork")
p1 = ctx.Process(target=_save_in_worker, args=(str(content_dir), pid, payload_a))
p2 = ctx.Process(target=_save_in_worker, args=(str(content_dir), pid, payload_b))
p1.start(); p2.start()
p1.join(timeout=10); p2.join(timeout=10)
```

**Assertions:**

| # | Property | Code |
|---|----------|------|
| 1 | hybrid-content rejection | `assert final in (payload_a, payload_b)` |
| 2 | no leftover tempfile | `assert leftovers == []` (filtered by prefix `.{pid}.md.` + suffix `.tmp`) |
| 3 | file mode is 0o644 | `assert stat.S_IMODE(target.stat().st_mode) == 0o644` |

**Verified on Linux:** test passes on this Linux 6.17 box; both worker exit codes are 0; final content equals one of the two payloads in full (no hybrid bytes detected); no leaked tempfile; chmod-applied 0o644 mode preserved.

## Integration Test Surface

| Test | Asserts | LLM call count |
|------|---------|----------------|
| `test_save_then_summary_renders_success_card` | success card + bullets + `ollama-default · llama3.1` metadata | 1 |
| `test_summary_cache_hit_returns_same_text_no_extra_llm_call` | second call hits cache | 1 |
| `test_summary_regenerate_header_bypasses_cache` | X-Regenerate bypasses lookup AND writes back | 2 (call 1 + bypass; call 3 hits refreshed cache) |
| `test_summary_after_content_edit_invalidates_cache` | mtime_ns changes → cache miss | 2 (resp 1 + resp 2) |
| `test_summary_returns_error_fragment_on_llm_failure` | ConnectError → 200 + amber alert + Retry button | 1 (raises) |
| `test_summary_returns_error_fragment_when_content_missing` | FileNotFoundError → 200 + "Content page no longer exists" | 0 |
| `test_concurrent_summary_same_key_no_cache_corruption` | 8 threads → 8 results, cache size == 1 | ≤ 8 (acceptable per Pitfall 11; lock guards dict only) |

## Invariant Guard Catalog

| Guard | Pattern Greppd For | Files Scanned | Locked Decision |
|-------|---------------------|---------------|------------------|
| no async def in routers | `^\s*async\s+def\s+` | platforms.py, summary.py | INFRA-05 |
| no default `MarkdownIt(` | `MarkdownIt\s*\(([^)]*)` first arg ≠ `'js-default'`/`"js-default"` | every `.py` under `app_v2/` | Pitfall 1 (XSS) |
| no 5xx in summary route | `status_code\s*=\s*5\d\d` AND `\braise\s+HTTPException\b` | summary.py | UI-SPEC §8c |
| no banned libs (langchain, litellm, vanna, llama_index) | `^\s*(import\|from)\s+<lib>\b` | every `.py` under `app_v2/` | CLAUDE.md "What NOT to Use" |
| `stream=False` only | literal `stream=False` present + `stream=True` absent | summary_service.py | D-21 (SUMMARY-04 single-shot) |
| TTLCache dimensions | literal `TTLCache(maxsize=128, ttl=3600)` | summary_service.py | D-17 verbatim |
| cache key uses mtime_ns | literal `mtime_ns` | summary_service.py | Pitfall 13 |
| atomic_write_bytes single source | `^def\s+atomic_write_bytes\s*\(` appears in EXACTLY one file (`app_v2/data/atomic_write.py`); both `overview_store` + `content_store` import via `from app_v2.data.atomic_write import atomic_write_bytes` | every `.py` under `app_v2/` | D-30 |

## Phase 03 Closure: Decision-to-Test Traceability

Every D-XX from `03-CONTEXT.md` and every SUMMARY-XX/CONTENT-XX from REQUIREMENTS.md is now backed by ≥1 passing test:

| Decision | Backing Test(s) | Plan |
|----------|-----------------|------|
| D-04 path-traversal regex | `test_path_traversal_rejected_before_filesystem` (15 cases) | 03-02 |
| D-08 MarkdownIt('js-default') XSS defense | `test_post_preview_xss_safe` + `test_no_default_markdownit_constructor_in_app_v2` | 03-02 + 03-04 |
| D-10 client-side Cancel | `test_post_edit_returns_panel_with_cancel_html` | 03-02 |
| D-13 button enable/disable | `test_overview_row_ai_button_enabled_when_content_exists` + `test_overview_row_ai_button_disabled_when_no_content` | 03-02 |
| D-17 TTLCache(128, 3600) | `test_summary_ttlcache_uses_locked_dimensions` | 03-04 |
| D-18 Regenerate write-back | `test_summary_regenerate_header_bypasses_cache` | 03-04 |
| D-19 backend-name resolution | `test_resolve_active_backend_name_*` | 03-01 |
| D-20 prompt with `<notes>` wrapper | `test_summary_prompt_module_*` | 03-03 |
| D-21 stream=False | `test_summary_service_uses_stream_false` | 03-04 |
| D-22 path-traversal coverage (3 strings × routes) | `test_path_traversal_rejected_*` | 03-02 + 03-03 |
| D-23 LLM client mocking | every `_build_client` mocker.patch.object call | 03-03 + 03-04 |
| D-24 cross-process race | `test_cross_process_save_race` | 03-04 |
| D-25 TTLCache + mtime invalidation | `test_summary_cache_invalidates_on_mtime_change` + `test_summary_after_content_edit_invalidates_cache` | 03-03 + 03-04 |
| D-26 threat-model items | one test per T-03-XX-NN (see plan threat_models) | 03-01..04 |
| D-27 lifespan content/platforms/ mkdir | `test_lifespan_creates_content_platforms_directory` | 03-01 |
| D-30 atomic_write_bytes single source | `test_atomic_write_bytes_is_single_source_of_truth` | 03-04 |
| D-31 64KB content size cap | `test_post_save_oversize_returns_422` | 03-02 |
| INFRA-05 (no async def) | `test_no_async_def_in_phase03_routers` | 03-04 |
| Pitfall 11 (lock not held during LLM) | `test_lock_not_held_during_llm_call` + `test_concurrent_summary_same_key_no_cache_corruption` | 03-03 + 03-04 |
| Pitfall 13 (mtime_ns precision) | `test_summary_cache_key_uses_mtime_ns` | 03-04 |
| Pitfall 14 (_Timer__timer patch) | `test_summary_ttl_expiry_via_timer_patch` | 03-03 |
| UI-SPEC always-200 | `test_summary_route_never_returns_5xx` (static guard) + `test_post_summary_never_returns_5xx_on_any_exception` (runtime) | 03-03 + 03-04 |
| CLAUDE.md banned libs | `test_no_banned_libraries_imported_in_app_v2` (parametrized × 4) | 03-04 |

## Decisions Made

- **`tests/v2/conftest.py` is the registration site for the `slow` marker** — chosen over creating a project-level `pyproject.toml [tool.pytest.ini_options]` section because the project has no existing pytest config file and a directory-scoped conftest avoids introducing a new top-level config artifact. CI can still opt out via `pytest tests/v2/ -m "not slow"` because conftest's `addinivalue_line` registration is fully equivalent to a `markers = [...]` pyproject entry.
- **Word-boundary regex for `raise HTTPException`** — the summary.py docstring contains the phrase "NEVER raises HTTPException" (which has the substring `raises HTTPException` but no literal `raise ` token). Using `\braise\s+HTTPException\b` ensures the static guard catches actual `raise HTTPException(...)` statements while ignoring docstring text.
- **Per-call response queue uses a closure** — instead of the plan's `type(r)()` pattern (which doesn't work because MagicMock is not type-callable), the test uses `idx = [0]` + a closure that returns `responses[idx[0]]` and advances. This is the canonical pytest-mock idiom for stateful side_effects.
- **Integration fixture replaces `app.state.settings = Settings(...)` after lifespan ran** — mirrors the proven pattern from `test_summary_routes.py::isolated_summary`. Avoids the in-place mutation pattern (`client.app.state.settings.llms = [...]`) the plan suggested, because constructing a fresh Settings instance is unambiguous and cannot fail validation under future Pydantic constraints.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan's per-call response builder used `type(r)()` cloning which is not valid for MagicMock instances**

- **Found during:** Task 2 (writing `test_summary_after_content_edit_invalidates_cache`).
- **Issue:** The plan's example code did `fake = type(r)()` to construct a per-call MagicMock-shaped response. `r` is a MagicMock instance whose `type()` is `MagicMock`, but instantiating it with no args returns a fresh MagicMock that lacks the `.choices` shape expected by `_call_llm_single_shot` — assigning `.choices = [type("C", (), {"message": ...})()]` would technically work but the nested `type(...)` calls produce non-attribute objects that fail the `.choices[0].message.content` access.
- **Fix:** Replaced with the canonical `_build_chat_response(mocker, text)` helper that builds a proper MagicMock with a `choices[0].message.content` shape (same idiom used in `test_summary_routes.py::_make_mock_client`). The closure-based queue (`idx = [0]; idx[0] += 1`) drives the per-call response.
- **Files modified:** Only the test file as written (no source files affected; the bug was in the plan's template, not the implementation).
- **Verification:** `test_summary_after_content_edit_invalidates_cache` passes; resp 1 and resp 2 are correctly distinguishable in the rendered HTML.
- **Committed in:** `46037b6` (Task 2 commit).

**2. [Rule 1 - Bug] Plan's `integrated_app` fixture mutated `client.app.state.settings.llms` in-place — fragile against Pydantic v2 model immutability semantics**

- **Found during:** Task 2 (fixture design).
- **Issue:** The plan suggested `client.app.state.settings.llms = [LLMConfig(...)]` after `with TestClient(app)`. Pydantic v2 models default to `model_config["frozen"] = False`, so the mutation works today, but the existing proven pattern in `test_summary_routes.py::isolated_summary` instead replaces `app.state.settings = Settings(...)` entirely. Using the proven pattern eliminates the dependency on field-level mutability and is robust against future schema tightening.
- **Fix:** Replaced the plan's in-place mutation with `app.state.settings = Settings(databases=[], llms=[LLMConfig(...)], app=AppConfig(default_llm="ollama-default"))`. Mirrors the proven pattern; same observable behavior; no test changes needed downstream.
- **Files modified:** `tests/v2/test_summary_integration.py` only.
- **Verification:** All 7 integration tests pass on first try with the corrected fixture.
- **Committed in:** `46037b6` (Task 2 commit).

---

**Total deviations:** 2 auto-fixed (both Rule 1 — plan-template bugs in test code that the plan author hadn't run). No production source files affected; plan acceptance criteria all met; D-24 verbatim assertions intact.

## Issues Encountered

- None beyond the two test-template bugs above. The cross-process race test (D-24) passed on the first run with the local Linux 6.17 ext4 filesystem; both worker processes exited cleanly within the 10s join timeout; no hybrid bytes were observed across multiple runs.
- A `DeprecationWarning: This process is multi-threaded, use of fork() may lead to deadlocks in the child` is emitted by Python 3.13 when the cross-process race test runs alongside other threaded tests in the same session. The test still passes deterministically (the parent does not hold any locks the child needs after fork), but the warning is intrinsic to Python 3.14+'s phase-out of fork as the default start method on Linux. Not fixed here — would require either spawning a fresh subprocess (defeating the point of `fork`) or skipping the test on 3.13+ (which would break D-24 on the team's actual deployment Python).

## User Setup Required

None — no external service configuration. The race test runs locally with no DB or LLM dependencies; integration tests use mocked LLM via `mocker.patch.object(summary_service, "_build_client", ...)`.

## Phase 03 Closure

All four plans of Phase 03 are now complete:

- 03-01: shared infrastructure (atomic_write_bytes, llm_resolver, tokens.css/app.css, lifespan mkdir).
- 03-02: content CRUD (content_store, platforms.py routes, 4 templates, overview-row .ai-btn wiring).
- 03-03: summary route + service (TTLCache + Lock + openai SDK + 7-string error vocab + always-200 contract).
- 03-04: cross-process race + integration + invariants (this plan).

**Test totals (Phase 03):**

| Wave | Test count delta | Cumulative v2 | Cumulative full project |
|------|------------------|---------------|--------------------------|
| Plan 03-01 baseline | +16 | 123 | 306 |
| Plan 03-02 | +47 | 170 | 353 |
| Plan 03-03 | +37 | 207 | 390 |
| Plan 03-04 | +21 | 228 | 411 |

## Next Phase Readiness

**Phase 04 (Browse Tab Port) — READY**

- No shared modules consumed from Phase 03's content/summary surface; the only Phase 03 imports a Phase 04 task might use are the `.panel` / `.markdown-content` / `.btn-white` / `.btn-sec` CSS classes from Plan 03-01's `tokens.css` + `app.css`, which are reusable for the Browse pivot table styling and any inline help text.
- The `slow` marker registered in `tests/v2/conftest.py` is available for any Phase 04+ test that needs cross-process or multi-second behavior (e.g., a 100k-row pivot performance test could use `@pytest.mark.slow` to opt out of the fast CI lane).
- The codebase invariant guard pattern (Plan 03-04 Task 3) is reusable: Phase 04 should add new guards to `tests/v2/test_phase03_invariants.py` (or a renamed `test_phase04_invariants.py`) for any locked decisions in `04-CONTEXT.md`.
- D-30's atomic_write_bytes is the single source of truth for any future atomic-write callers (Phase 04 Browse export to disk, if added; Phase 05 Ask conversation history persistence, if added).

No blockers or concerns.

## Threat Flags

None — Plan 03-04 only adds tests; no new security-relevant surface introduced. The cross-process race test exercises an existing surface (atomic_write_bytes / save_content) and confirms the threat-modeled behavior (T-03-04-01..02) holds under fork-spawned concurrency.

## Self-Check: PASSED

Verified all created files exist:
- FOUND: tests/v2/test_content_store_race.py
- FOUND: tests/v2/test_summary_integration.py
- FOUND: tests/v2/test_phase03_invariants.py
- FOUND: tests/v2/conftest.py

Verified all 3 task commits in git log:
- FOUND: a0c64b4 test(03-04): add D-24 cross-process race test + ThreadPool race
- FOUND: 46037b6 test(03-04): add end-to-end summary integration + concurrent thread tests
- FOUND: 4bec1e2 test(03-04): add Phase 03 codebase invariant guards

Verified test target met:
- 2 race tests passing — PASS
- 7 integration tests passing — PASS
- 12 invariant cases (8 unique × parametrize) passing — PASS
- 228 v2 tests passing (≥207 baseline + 21 new) — PASS
- 411 full-project tests passing (≥390 baseline + 21 new) — PASS
- 0 failures, 0 regressions — PASS

Verified acceptance criteria (key items):
- D-24 cross-process race exists at module top-level with the verbatim 3 assertions — PASS
- @pytest.mark.slow + skip-on-win32 guards present (single-line decorator form) — PASS
- ThreadPool counterpart asserts no exception + no leftover tempfile + no hybrid content — PASS
- 7 integration tests cover the full chain via TestClient with only LLM mocked — PASS
- 12 invariant cases enforce all 8 locked decisions (INFRA-05, Pitfall 1, UI-SPEC always-200, banned libs × 4, D-21, D-17, Pitfall 13, D-30) — PASS

---
*Phase: 03-content-pages-ai-summary*
*Plan: 04*
*Completed: 2026-04-25*
