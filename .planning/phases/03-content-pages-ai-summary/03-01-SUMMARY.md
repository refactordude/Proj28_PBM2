---
phase: 03-content-pages-ai-summary
plan: 01
subsystem: infra
tags: [atomic-write, css-tokens, lifespan, llm-resolver, refactor, fastapi, htmx, dashboard-design-system]

# Dependency graph
requires:
  - phase: 02-overview-tab-and-filters
    provides: app_v2/services/overview_store._atomic_write (refactored to delegate); app_v2/templates/base.html stylesheet block; app_v2/main.py lifespan handler
provides:
  - app_v2/data/atomic_write.py::atomic_write_bytes — POSIX-atomic file write helper (D-30); single source of truth for overview YAML and content markdown
  - app_v2/services/llm_resolver.py::resolve_active_llm + resolve_active_backend_name — eliminates 3-way duplicated _resolve_* helpers (Q2 RESOLVED)
  - app_v2/static/css/tokens.css — Dashboard CSS custom properties (--violet, --accent, --radius-panel, --shadow-panel, etc.)
  - app_v2/static/css/app.css — component classes (.shell, .panel, .ai-btn, .markdown-content, .nav-pills overrides, .btn-white, .btn-sec, .page-title)
  - content/platforms/.gitkeep — directory survives git clone; rest of content/ gitignored
  - app_v2/main.py lifespan mkdir for content/platforms/ + Pitfall-18 deviation comment
  - tests/v2/test_atomic_write.py — 7 unit tests
  - tests/v2/test_llm_resolver.py — 8 unit tests
  - tests/v2/test_main.py::test_lifespan_creates_content_platforms_directory — lifespan mkdir regression test
affects: [03-02-content-routes, 03-03-summary-route, 03-04-overview-rewire-and-e2e]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Centralized POSIX-atomic write helper (tempfile.mkstemp in same dir → fsync → os.replace → chmod) with mode preservation
    - Duck-typed Settings resolver (defensive getattr fallbacks; never raises)
    - CSS token layer split (tokens.css declares var(--*), app.css consumes them; load order enforced in base.html)
    - Lifespan-time directory bootstrap with OSError tolerance (app starts even if mkdir fails so the operator sees a clearer error from the actual write attempt later)
    - Pitfall-18 deviation comment as auditable in-code rationale

key-files:
  created:
    - app_v2/data/atomic_write.py
    - app_v2/services/llm_resolver.py
    - app_v2/static/css/tokens.css
    - app_v2/static/css/app.css
    - content/platforms/.gitkeep
    - tests/v2/test_atomic_write.py
    - tests/v2/test_llm_resolver.py
  modified:
    - app_v2/services/overview_store.py
    - app_v2/templates/base.html
    - app_v2/main.py
    - tests/v2/test_main.py
    - .gitignore

key-decisions:
  - "atomic_write_bytes accepts default_mode (0o644 default; overview_store passes 0o666 to preserve umask-applied 0o644 on new YAML files). Helper handles existing-mode preservation AND new-file umask calculation in one place."
  - "Pitfall-18 deviation: NO Ollama warmup ping in lifespan. Rely on summary_service's 60s read timeout (plan 03-03). Lifespan must start cleanly even if Ollama is unreachable; first-request cold start is acceptable for an internal tool with low concurrency. Comment placed in main.py to make the deviation auditable."
  - "Gitignore pattern fix: a bare 'content/' rule short-circuits descent into the directory, so '!content/platforms/.gitkeep' alone never matches. Added '!content/' + '!content/platforms/' re-includes plus 'content/platforms/*' wildcard so the .gitkeep negation actually applies. All other files inside content/ remain ignored."
  - "llm_resolver duck-typed: accepts ANY object with .llms (defensive getattr); tests can pass minimal stand-ins. Returns None / 'Ollama' on any malformed input — never raises from the resolver."

patterns-established:
  - "Pattern: shared atomic-write helper with default_mode parameter — callers choose 0o644 (content) or 0o666 (yaml) and the helper does the umask math + existing-mode preservation."
  - "Pattern: CSS tokens.css before app.css in base.html (var(--*) declared before use); UI-SPEC verbatim CSS rules pulled into a single layered file pair."
  - "Pattern: services-layer resolver for app.state.settings lookups — eliminates router-to-router import cycles AND copy-paste of _resolve_* helpers."

requirements-completed: [CONTENT-01]

# Metrics
duration: 10min
completed: 2026-04-25
---

# Phase 03 Plan 01: Wave-0 Shared Infrastructure Summary

**atomic_write_bytes helper extracted (overview_store now delegates), Dashboard tokens.css + app.css wired into base.html, lifespan mkdir + gitignore for content/platforms/, and llm_resolver shared module — three duplications eliminated, zero regressions across 306 tests.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-25T13:44:43Z (first task commit)
- **Completed:** 2026-04-25T13:52:30Z (last task commit)
- **Tasks:** 4 (all auto, two with TDD)
- **Files modified:** 11 created/modified across `app_v2/`, `tests/v2/`, `.gitignore`, `content/`

## Accomplishments

- **atomic_write_bytes shared helper** (D-30, CONTENT-06) — POSIX-atomic write idiom (tempfile.mkstemp in same dir → write → fsync → os.replace → chmod) extracted from overview_store into `app_v2/data/atomic_write.py`. Phase 02 overview_store now delegates (~12-line `_atomic_write` body, down from 46). Phase 03 `content_store` (plan 03-02) will import the same helper — no copy-paste.
- **llm_resolver shared module** (RESEARCH Q2 RESOLVED) — `resolve_active_llm` + `resolve_active_backend_name` in `app_v2/services/llm_resolver.py`. Eliminates the 3-way duplication that would otherwise appear in plans 03-02 (overview/platforms) and 03-03 (summary). Duck-typed Settings, never raises.
- **Dashboard CSS token layer** — `tokens.css` (verbatim from UI-SPEC §Design System: --bg, --ink, --accent #3366ff, --violet #7a5af8, --radius-panel 22px, --shadow-panel) + `app.css` (.shell, .page-head, .page-title, .btn-white, .panel/.panel-body/.panel-header, .nav-pills overrides, .btn-sec, .ai-btn full rule, .markdown-content). Wired into `base.html` with tokens before app (var(--*) declared before consumption).
- **content/platforms/ infrastructure** — lifespan mkdir (D-27) with OSError tolerance + Pitfall-18 deviation comment (no Ollama warmup; rely on read-timeout in 03-03). `.gitignore` ignores `content/` while keeping `content/platforms/.gitkeep` tracked.
- **Test count:** 290 → 306 passing across full project (107 → 123 in `tests/v2/`). Zero regressions; 16 new tests covering the helpers and lifespan.

## Task Commits

1. **Task 1 RED:** `085564e` test(03-01): failing tests for atomic_write_bytes
2. **Task 1 GREEN:** `42fed84` feat(03-01): atomic_write_bytes helper (D-30)
3. **Task 1 REFACTOR:** `8c3ba12` refactor(03-01): overview_store delegates to atomic_write_bytes
4. **Task 2:** `7e2e23c` feat(03-01): tokens.css + app.css wired in base.html
5. **Task 3:** `09a720e` feat(03-01): lifespan content/platforms/ + .gitignore (D-27, D-28)
6. **Task 4 RED:** `baf254b` test(03-01): failing tests for llm_resolver
7. **Task 4 GREEN:** `4b80bda` feat(03-01): llm_resolver shared helpers (Q2 RESOLVED)

## Files Created/Modified

### Created
- `app_v2/data/atomic_write.py` — `atomic_write_bytes(target, payload, *, default_mode=0o644) -> None`. ~70 lines. Preserves existing target mode; default_mode & ~umask for new files; tempfile cleanup on any exception.
- `app_v2/services/llm_resolver.py` — `resolve_active_llm(settings) -> LLMConfig | None`, `resolve_active_backend_name(settings) -> str`. Duck-typed; defensive getattr fallbacks; returns None / 'Ollama' on malformed input.
- `app_v2/static/css/tokens.css` — 41 lines, CSS custom properties verbatim from UI-SPEC §Design System, Inter Tight + JetBrains Mono font-family.
- `app_v2/static/css/app.css` — 84 lines, component classes (`.shell`, `.page-head`, `.page-title`, `.page-sub`, `.page-actions`, `.btn-white`, `.panel`, `.panel-body`, `.panel-header`, `.nav-pills .nav-link`/`.active`, `.btn-sec`, `.ai-btn` + `:hover`/`:focus-visible`/`:disabled`/`.htmx-request`/`.regen`/`.ai-btn-md`, `.markdown-content` h1-h3/p/code/pre/ul/ol/blockquote).
- `content/platforms/.gitkeep` — empty marker, tracked.
- `tests/v2/test_atomic_write.py` — 7 tests (basic write, parent mkdir, mode preservation, default_mode + umask, fsync error cleanup, replace error cleanup, 100 KB roundtrip, overview_store regression guard).
- `tests/v2/test_llm_resolver.py` — 8 tests (default_llm match, fallback to first, None on empty, None on missing-attr object, OpenAI label, Ollama label, default 'Ollama' when no LLM, unknown-type fallback to 'Ollama').

### Modified
- `app_v2/services/overview_store.py` — body of `_atomic_write` shrunk from ~46 to ~12 lines. Dropped module-private `os` / `stat` / `tempfile` imports (helper owns them now). Public API unchanged.
- `app_v2/templates/base.html` — added 2 `<link rel="stylesheet">` lines after vendored Bootstrap and before HTMX `<script>`. tokens.css loads BEFORE app.css.
- `app_v2/main.py` — lifespan mkdir for `content/platforms/` (OSError tolerated + logged) + Pitfall-18 deviation comment.
- `tests/v2/test_main.py` — added `test_lifespan_creates_content_platforms_directory` (chdir to tmp_path, asserts mkdir landed there).
- `.gitignore` — added `content/` ignore + traversal rescue rules + `content/platforms/.gitkeep` negation.

## Integration Contracts for Plans 03-02 / 03-03

**Plan 03-02 (content routes + content_store):**
```python
from app_v2.data.atomic_write import atomic_write_bytes
from app_v2.services.llm_resolver import resolve_active_backend_name
```
content_store should call `atomic_write_bytes(target, markdown.encode("utf-8"), default_mode=0o644)`. Routers should replace any inline `_resolve_backend_name` helpers with the imported function.

**Plan 03-03 (summary route + summary_service):**
```python
from app_v2.services.llm_resolver import resolve_active_llm, resolve_active_backend_name
```
Replaces the duplicated inline `_resolve_active_llm` + `_backend_display_name` helpers in summary.py. Summary template's loading text "Summarizing… (using {backend})" should use `resolve_active_backend_name(request.app.state.settings)`.

**Stylesheets:** Every Phase 03 template (`platform/detail.html`, `platform/edit.html`, `summary/card.html`, refreshed `_entity_row.html`) consumes `.panel`, `.ai-btn`, `.markdown-content`, etc. — already loaded globally via base.html.

## Decisions Made

- **default_mode parameter on atomic_write_bytes** — callers choose 0o644 (content markdown) or 0o666 (overview YAML, preserving prior umask-applied 0o644 result). Centralizes the existing-mode preservation + umask-aware new-file mode in ONE place.
- **No Ollama warmup ping in lifespan (Pitfall-18 deviation)** — the app starts cleanly even when Ollama is unreachable; first-request cold start is acceptable for an internal-tool deployment. Read-timeout (60s) in 03-03 summary_service is the sole mitigation. Comment in main.py makes the deviation auditable.
- **Gitignore rescue rules for content/ + .gitkeep** — Rule 1 fix to make the plan's two prescribed lines actually work. The bare `content/` rule alone short-circuits descent so the negation never applies; added `!content/`, `!content/platforms/`, and `content/platforms/*` so the negation on `.gitkeep` is reachable while everything else inside `content/` remains ignored.
- **llm_resolver returns 'Ollama' on unknown type** — D-19 default; future-proofs against new LLM types being added to the Literal without breaking the templates' loading text.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Gitignore pattern would not actually track .gitkeep**
- **Found during:** Task 3 (lifespan + .gitignore + .gitkeep)
- **Issue:** The plan prescribed exactly `content/` followed by `!content/platforms/.gitkeep`. Git's behavior is to short-circuit descent into a directory matched by an ignore rule, so the negation on a file deep inside that directory never gets a chance to apply. `git check-ignore -v content/platforms/.gitkeep` reported the ignore rule (line 9) was matching the .gitkeep — confirming the file would NOT be tracked.
- **Fix:** Kept the plan's two prescribed lines (`content/` + `!content/platforms/.gitkeep`) so the grep acceptance criteria still pass, but added two re-include rules (`!content/`, `!content/platforms/`) and a wildcard (`content/platforms/*`) between them. Now `git check-ignore` confirms the negation rule for .gitkeep wins, while all other files inside `content/platforms/` remain ignored. Added an inline comment in `.gitignore` explaining the four-line pattern.
- **Files modified:** `.gitignore`
- **Verification:** `git add content/platforms/.gitkeep && git ls-files content/` returns exactly `content/platforms/.gitkeep`. `git check-ignore -v content/platforms/.gitkeep` matches `.gitignore:18:!content/platforms/.gitkeep` (negation wins). Created a throwaway file `content/platforms/_test_should_be_ignored.md` and confirmed `git check-ignore -v` matched the wildcard ignore rule.
- **Committed in:** `09a720e` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in plan's gitignore pattern)
**Impact on plan:** Plan acceptance criteria still met (the two prescribed grep lines still pass); the additional traversal rules are necessary for the .gitkeep to actually be tracked. No scope creep.

## Issues Encountered

- None beyond the gitignore pattern bug (handled as Rule 1 above). All TDD RED→GREEN cycles converged on first try.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Plan 03-02 (content routes + content_store) — READY**
- atomic_write_bytes helper available for `content_store.write_content`.
- llm_resolver.resolve_active_backend_name available for the entity-row's "AI Summary" button enable-state and the detail page's button.
- `content/platforms/` directory guaranteed to exist at startup.
- Dashboard CSS classes (.shell, .panel, .ai-btn, .markdown-content, .btn-white, .btn-sec, .nav-pills overrides) loaded globally — templates can use them immediately.

**Plan 03-03 (summary route + summary_service) — READY**
- llm_resolver.resolve_active_llm available for `_build_client` factory.
- `.markdown-content` styling available for rendered summary text.
- `.ai-btn` + `.ai-btn.regen` available for Regenerate button.

**Plan 03-04 (overview rewire + E2E) — READY**
- All shared infrastructure in place; this plan just wires existing helpers into existing routers and adds the cross-process race test (D-24).

No blockers or concerns.

## Self-Check: PASSED

Verified all created files exist:
- FOUND: `app_v2/data/atomic_write.py`
- FOUND: `app_v2/services/llm_resolver.py`
- FOUND: `app_v2/static/css/tokens.css`
- FOUND: `app_v2/static/css/app.css`
- FOUND: `content/platforms/.gitkeep`
- FOUND: `tests/v2/test_atomic_write.py`
- FOUND: `tests/v2/test_llm_resolver.py`

Verified all 7 task commits in git log:
- FOUND: `085564e` test(03-01): failing tests for atomic_write_bytes
- FOUND: `42fed84` feat(03-01): atomic_write_bytes helper
- FOUND: `8c3ba12` refactor(03-01): overview_store delegates
- FOUND: `7e2e23c` feat(03-01): tokens.css + app.css
- FOUND: `09a720e` feat(03-01): lifespan + gitignore + .gitkeep
- FOUND: `baf254b` test(03-01): failing tests for llm_resolver
- FOUND: `4b80bda` feat(03-01): llm_resolver helpers

Verified test target met: 306 tests passing (290 baseline + 16 new), 0 failed.

---
*Phase: 03-content-pages-ai-summary*
*Plan: 01*
*Completed: 2026-04-25*
