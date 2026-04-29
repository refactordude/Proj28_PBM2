---
phase: 06-ask-tab-port
plan: 02
subsystem: api
tags: [fastapi, htmx, jinja2, cookie, llm-resolver, starter-prompts, picker-macro]

requires:
  - phase: 03-content-pages-ai-summary
    provides: llm_resolver.py with resolve_active_llm + resolve_active_backend_name
  - phase: 04-browse-tab-port
    provides: _picker_popover.html macro with form_id/hx_post/hx_target kwargs

provides:
  - resolve_active_llm(settings, request=None) reads pbm2_llm cookie with D-15 validation
  - resolve_active_backend_name(settings, request=None) honors cookie precedence (D-17)
  - app_v2/services/starter_prompts.py::load_starter_prompts() with YAML fallback chain
  - _picker_popover.html disable_auto_commit=False kwarg suppresses hx-* on <ul> when True

affects:
  - 06-03-PLAN (ask router — calls resolve_active_llm(settings, request) and load_starter_prompts())
  - 06-04-PLAN (confirm panel template — calls picker_popover(..., disable_auto_commit=True))
  - 06-05-PLAN (cookie-path tests for the extended resolver)

tech-stack:
  added: []
  patterns:
    - "Cookie-aware LLM resolution: request=None default preserves backward compat; request threading gives cookie precedence with closed-set validation (D-15)"
    - "Service-module port: v1.0 Streamlit page helpers extracted into framework-agnostic app_v2/services/ before the source file is deleted (Pitfall 5 defense)"
    - "Macro kwarg for opt-out: disable_auto_commit=False preserves byte-stability for default callers while enabling confirmation panel to suppress expensive auto-submit"

key-files:
  created:
    - app_v2/services/starter_prompts.py
  modified:
    - app_v2/services/llm_resolver.py
    - app_v2/routers/overview.py
    - app_v2/routers/platforms.py
    - app_v2/routers/summary.py
    - app_v2/templates/browse/_picker_popover.html

key-decisions:
  - "Cookie validation uses closed-set check: cookie value MUST be in {l.name for l in settings.llms}; any other value (missing, empty, tampered, stale-config) silently falls through to settings.app.default_llm. No signing needed (intranet, two backends). (D-15)"
  - "request=None default makes the extension purely additive — all Phase 1-5 callers continue to work unchanged; the 4 router call sites now pass request so AI Summary picks up the cookie too (D-17)"
  - "load_starter_prompts() module-scope imports (hoisted from function-scope per RESEARCH.md Pattern 6); no lru_cache (called only by GET /ask, YAML < 1KB, would mask live-edit of config file)"
  - "disable_auto_commit=False default on picker_popover: Phase 4/5 callers are byte-stable; confirmation panel (Plan 06-04) passes True to prevent one-agent-run-per-checkbox-toggle (RESEARCH.md Pitfall 3)"

requirements-completed:
  - ASK-V2-05
  - ASK-V2-08

duration: 25min
completed: 2026-04-29
---

# Phase 6 Plan 02: Foundation — llm_resolver cookie extension + starter_prompts service + picker macro disable_auto_commit

**Cookie-aware llm_resolver with pbm2_llm validation, YAML-fallback starter_prompts service, and picker macro opt-out kwarg unlocking Plans 06-03 and 06-04**

## Performance

- **Duration:** 25 min
- **Started:** 2026-04-29T00:00:00Z
- **Completed:** 2026-04-29T00:25:00Z
- **Tasks:** 3
- **Files modified:** 6 (1 new)

## Accomplishments

- Extended `resolve_active_llm` and `resolve_active_backend_name` with `request=None` and `pbm2_llm` cookie precedence; D-15 closed-set validation prevents cookie tampering
- Created `app_v2/services/starter_prompts.py` as a framework-agnostic port of v1.0's loader (avoids importing the Streamlit/nest_asyncio-contaminated source); sanity check confirmed "OK 8 entries"
- Added `disable_auto_commit=False` kwarg to `_picker_popover.html` macro; Phase 4 + Phase 5 invariants still pass; Browse + Overview route tests byte-stable

## Task Commits

1. **Task 1: Extend llm_resolver + thread request through 4 callers** — `ba59c87` (feat)
2. **Task 2: Create app_v2/services/starter_prompts.py** — `5f02e64` (feat)
3. **Task 3: Add disable_auto_commit kwarg to _picker_popover.html** — `7f68acf` (feat)

## Caller Updates (4 one-line changes)

| File | Line | Before | After |
|------|------|--------|-------|
| `app_v2/routers/overview.py` | 237 | `resolve_active_backend_name(getattr(request.app.state, "settings", None))` | `resolve_active_backend_name(getattr(request.app.state, "settings", None), request)` |
| `app_v2/routers/platforms.py` | 74 | `resolve_active_backend_name(settings)` | `resolve_active_backend_name(settings, request)` |
| `app_v2/routers/summary.py` | 124 | `resolve_active_llm(settings)` | `resolve_active_llm(settings, request)` |
| `app_v2/routers/summary.py` | 125 | `resolve_active_backend_name(settings)` | `resolve_active_backend_name(settings, request)` |

## Macro Signature Delta

```diff
-{% macro picker_popover(name, label, options, selected, form_id="browse-filter-form", hx_post="/browse/grid", hx_target="#browse-grid") %}
+{% macro picker_popover(name, label, options, selected, form_id="browse-filter-form", hx_post="/browse/grid", hx_target="#browse-grid", disable_auto_commit=False) %}
```

Conditional `{% if not disable_auto_commit %}` block wraps all 5 `hx-*` attrs on the `<ul>` (lines 82-87 of the updated template). Default `False` renders identically to the pre-Plan-06-02 macro.

## Verification Results

- `resolve_active_llm(settings, request)` — 1 match in llm_resolver.py
- `resolve_active_backend_name(settings, request)` — 1 match in llm_resolver.py
- `"pbm2_llm"` — 2 occurrences in llm_resolver.py (cookie read + docstring)
- `valid_names` — 2 occurrences in llm_resolver.py (set comprehension + variable usage)
- All 4 router call sites thread `request` — confirmed
- `test_llm_resolver.py` — 8 passed (backward compat preserved)
- `starter_prompts.py` sanity import — OK 8 entries
- `test_phase04_invariants.py::test_picker_popover_uses_d15b_auto_commit_pattern` — PASSED
- `test_phase05_invariants.py::test_picker_popover_macro_is_shared_not_forked` — PASSED
- `test_browse_routes.py` + `test_overview_routes.py` — 38 passed
- Full pre-Phase-6 v2 suite — **301 passed, 1 skipped** (identical to baseline)

## Files Created/Modified

- `app_v2/services/llm_resolver.py` — extended both functions with `request=None` + `pbm2_llm` cookie branch; module docstring updated with Phase 6 D-17 extension note
- `app_v2/services/starter_prompts.py` — NEW: YAML fallback loader ported from v1.0; no streamlit/nest_asyncio; 59 lines including module docstring
- `app_v2/templates/browse/_picker_popover.html` — macro signature + conditional hx-* emission + comment block update
- `app_v2/routers/overview.py` — 1-line caller update (line 237)
- `app_v2/routers/platforms.py` — 1-line caller update (line 74)
- `app_v2/routers/summary.py` — 2-line caller update (lines 124-125)

## Decisions Made

- Cookie validation is closed-set only (no signing) per D-15: `cookie_val in valid_names` is the full defense for this intranet app with two pre-configured backends
- `getattr(request, "cookies", None) or {}` with `hasattr(cookies, "get")` guard makes the resolver robust against non-Starlette request objects in tests
- Module-scope imports in `starter_prompts.py` (not function-scope as in v1.0) because the Streamlit page reason for function-scope imports (avoid top-level side-effects in a module Streamlit re-imports) doesn't apply to a FastAPI service module
- `disable_auto_commit` default is `False` (not `True`) to ensure all existing Phase 4/5 callers remain byte-stable without any template changes

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## New Artifacts Available to Plan 06-03 / 06-04

| Artifact | Consumer | API |
|----------|----------|-----|
| `resolve_active_llm(settings, request)` | Plan 06-03 ask router | Cookie-aware backend config |
| `resolve_active_backend_name(settings, request)` | Plan 06-03 ask router | Cookie-aware label string |
| `load_starter_prompts()` | Plan 06-03 GET /ask | Returns 8 chip entries from YAML |
| `picker_popover(..., disable_auto_commit=True)` | Plan 06-04 confirm panel | Suppresses auto-submit on checkbox toggle |

## Next Phase Readiness

- Plan 06-03 (routes: GET /ask, POST /ask/query, POST /ask/confirm, POST /settings/llm) can now call `resolve_active_llm(settings, request)` and `load_starter_prompts()` against verified APIs
- Plan 06-04 (templates: confirm panel) can call `picker_popover(..., disable_auto_commit=True)` to prevent expensive per-checkbox agent runs
- Plan 06-05 (tests) can add cookie-path tests to `test_llm_resolver.py` — the new `request=None` path is backward-compatible but needs cookie-present test coverage

---
*Phase: 06-ask-tab-port*
*Completed: 2026-04-29*
