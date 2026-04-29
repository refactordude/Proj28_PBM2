---
phase: 03-content-pages-ai-summary
plan: 02
subsystem: content-crud
tags: [content-crud, htmx, markdown, path-traversal-defense, jinja2-blocks, tdd, fastapi, xss-defense]

# Dependency graph
requires:
  - phase: 03-content-pages-ai-summary
    plan: 01
    provides: app_v2/data/atomic_write.py::atomic_write_bytes; app_v2/services/llm_resolver.py::resolve_active_backend_name; app_v2/static/css/{tokens,app}.css; lifespan content/platforms/ mkdir
provides:
  - app_v2/services/content_store.py — read/save/delete/render markdown + _safe_target traversal defense + get_content_mtime_ns (Plan 03-03 cache key)
  - app_v2/routers/platforms.py — 5 def routes under /platforms (detail, edit, preview, save, delete) — INFRA-05 compliant
  - app_v2/templates/platforms/{detail,_content_area,_edit_panel,_preview_pane}.html — full CRUD UI surface
  - Wired Overview row .ai-btn (replaces Phase 02 disabled stub) + per-row summary slot for Plan 03-03 to swap into
  - tests/v2/test_content_store.py — 14 unit tests
  - tests/v2/test_content_routes.py — 33 route tests (incl. 15 path-traversal parametrized cases)
affects: [03-03-summary-route, 03-04-overview-rewire-and-e2e]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pure-function service module with content_dir injected (tests pass tmp_path; production defaults to content/platforms/)
    - Pathlib-alias pattern (`from pathlib import Path as _Path`) when fastapi.Path needs to coexist as a path-parameter validator
    - data-cancel-html stash via Jinja2 `| e` escape for D-10 client-side Cancel without server round-trip
    - HTMX outerHTML swap target #content-area shared by GET/save/delete (single fragment for 4 visual states)
    - Per-row summary slot wrapper (`<li id="summary-row-{pid}">`) reserved at Phase 02→03 boundary so Plan 03-03 just innerHTML-swaps the rendered summary

key-files:
  created:
    - app_v2/services/content_store.py
    - app_v2/routers/platforms.py
    - app_v2/templates/platforms/detail.html
    - app_v2/templates/platforms/_content_area.html
    - app_v2/templates/platforms/_edit_panel.html
    - app_v2/templates/platforms/_preview_pane.html
    - tests/v2/test_content_store.py
    - tests/v2/test_content_routes.py
  modified:
    - app_v2/main.py
    - app_v2/routers/overview.py
    - app_v2/templates/overview/_entity_row.html
    - tests/v2/test_overview_routes.py

key-decisions:
  - "content_store stays pure (content_dir param defaulted to DEFAULT_CONTENT_DIR); routes hold the single CONTENT_DIR module-level constant tests monkeypatch — keeps service layer reusable for any future caller (e.g., a CLI dump tool) with a different storage policy."
  - "Pathlib alias `from pathlib import Path as _Path` to avoid collision with `fastapi.Path` (mirrors overview.py:18 convention). CONTENT_DIR annotation references `_Path`, not the FastAPI class."
  - "data-cancel-html stash: edit_view renders _content_area.html into a string via templates.env.get_template().render(ctx) and injects it as a Jinja2 `| e` escaped attribute — no server round-trip on Cancel; T-03-02-04 (attribute injection) blocked by autoescape."
  - "Path traversal hardening at TWO layers: (1) FastAPI Path(pattern=^[A-Za-z0-9_\\-]{1,128}$) returns 422 BEFORE the route body runs; (2) content_store._safe_target re-asserts via Path.resolve()+relative_to() at the filesystem boundary. Tests parametrize 3 attack strings × 5 routes = 15 cases."
  - "Form(max_length=65536) enforced server-side; FastAPI returns 422 BEFORE atomic_write_bytes is invoked (T-03-02-05 — disk-fill DoS prevented)."
  - "Used hx-disabled-elt and the standalone `disabled` attribute together for the AI button — `disabled` blocks click natively when has_content=False; hx-disabled-elt is for the in-flight loading state when has_content=True."

requirements-completed: [CONTENT-02, CONTENT-03, CONTENT-04, CONTENT-05, CONTENT-06, CONTENT-07, CONTENT-08, SUMMARY-01]

# Metrics
duration: 17min
completed: 2026-04-25
---

# Phase 03 Plan 02: Content Routes + Templates + Overview Wiring Summary

**Full markdown CRUD surface delivered: 5 routes (GET/POST edit/POST preview/POST save/DELETE), 4 templates, content_store service, Overview row .ai-btn replacing Phase 02 stub. Path-traversal hardened at TWO layers (regex + relative_to), XSS-defended via MarkdownIt('js-default'), 64KB size cap enforced server-side, 47 new tests passing (14 content_store + 33 content_routes); full v2 suite 170 passing, full project 353 passing.**

## Performance

- **Duration:** ~17 min
- **Started:** 2026-04-25T13:58:14Z
- **Completed:** 2026-04-25T14:15:00Z (approximate)
- **Tasks:** 2 (Task 1 = content_store + tests; Task 2 = templates + router + overview wiring + tests)
- **Commit boundaries:** 7 (per plan <scope_note> contract)
- **Files created:** 8 (content_store.py, platforms.py, 4 templates, 2 test files)
- **Files modified:** 4 (main.py, overview.py, _entity_row.html, test_overview_routes.py)

## content_store API Surface

| Function | Purpose | Returns |
|----------|---------|---------|
| `render_markdown(text)` | Render markdown via `MarkdownIt('js-default')` (XSS-safe) | `str` (HTML) |
| `_safe_target(pid, content_dir)` | Resolve content_dir/<pid>.md; raise ValueError on traversal | `Path` |
| `read_content(pid, content_dir)` | UTF-8 file contents or None | `str | None` |
| `save_content(pid, payload, content_dir)` | Atomic write via `atomic_write_bytes` (default_mode=0o644) | `None` |
| `delete_content(pid, content_dir)` | Idempotent delete | `bool` (True=deleted, False=absent) |
| `get_content_mtime_ns(pid, content_dir)` | Integer-nanosecond mtime for Plan 03-03 cache key | `int | None` |

## Route Table

| Method | Path                            | Status | Returns                                                          |
| ------ | ------------------------------- | ------ | ---------------------------------------------------------------- |
| GET    | `/platforms/{pid}`              | 200    | full detail page (extends base.html); 422 on regex fail          |
| POST   | `/platforms/{pid}/edit`         | 200    | `_edit_panel.html` fragment (data-cancel-html stashed)           |
| POST   | `/platforms/{pid}/preview`      | 200    | `_preview_pane.html` fragment; 422 if content > 64KB             |
| POST   | `/platforms/{pid}` (save)       | 200    | `_content_area.html` rendered fragment; 422 if content > 64KB    |
| DELETE | `/platforms/{pid}/content`      | 200    | `_content_area.html` empty-state fragment (idempotent)           |

All 5 routes are `def` (not `async def`) — INFRA-05 compliant; FastAPI dispatches to threadpool. Every route validates `platform_id` via `Path(pattern=PLATFORM_ID_PATTERN, min_length=1, max_length=128)` BEFORE any filesystem call.

## Path-Traversal Defense Layers

**Layer 1 (HTTP routing):** `Path(pattern=r"^[A-Za-z0-9_\-]{1,128}$")` rejects traversal characters at FastAPI entry, returning 422. Starlette also returns 404 when URL-encoded slashes (`%2F`) reshape the route — both 404 and 422 are accepted by the parametrized traversal tests.

**Layer 2 (filesystem):** `content_store._safe_target` calls `(content_dir / f"{pid}.md").resolve().relative_to(content_dir.resolve())`. Any escape raises `ValueError`; `read_content` and `delete_content` swallow it (safe defaults: None / False); `save_content` re-raises (which would 500, but Layer 1 already blocks reachability).

**Test evidence:** `tests/v2/test_content_routes.py::test_path_traversal_rejected_before_filesystem` parametrizes 3 attack strings (`..%2F..%2Fetc%2Fpasswd`, `%2Fetc%2Fpasswd`, `foo%00bar`) × 5 HTTP routes = 15 cases; every case asserts `status_code in (404, 422)` AND `cd.iterdir() == []` (no file leaked into content dir).

## Overview Row Diff (Phase 02 → Phase 03)

| Aspect                             | Phase 02 (stub)                                                | Phase 03 (wired)                                                                  |
| ---------------------------------- | -------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Button class                       | `btn btn-outline-primary btn-sm ms-2`                          | `ai-btn ms-2` (Dashboard violet gradient from app.css)                            |
| Disabled                           | Always `disabled` (no Phase 03 yet)                            | `disabled` only when `entity.has_content == False` (D-13)                         |
| Tooltip copy                       | `"Content page must exist first (Phase 3)"`                    | `"Content page must exist first — open the platform to Add some"`                 |
| HTMX wiring                        | None                                                           | `hx-post="/platforms/{pid}/summary"` + `hx-target="#summary-{pid}"` + `hx-indicator` + `hx-disabled-elt` |
| Per-row summary slot               | Absent                                                         | `<li id="summary-row-{pid}">` containing `#summary-{pid}` + pre-seeded htmx-indicator spinner reading `"Summarizing… (using {backend_name})"` |
| `_entity_dict`                     | Returns `{platform_id, brand, soc_raw, year}`                  | + `has_content` (computed via `has_content_file(pid, CONTENT_DIR)`)               |

## Backend-Name Resolution Helper

Both `app_v2/routers/overview.py` and `app_v2/routers/platforms.py` call:

```python
from app_v2.services.llm_resolver import resolve_active_backend_name
backend_name = resolve_active_backend_name(getattr(request.app.state, "settings", None))
```

This is the Plan 03-01 single source of truth — neither router defines a local `_resolve_backend_name`. Returns `'OpenAI'` or `'Ollama'` (D-19 default 'Ollama' on missing/invalid settings). Plan 03-03 will import the same helper for the summary route's `_build_client` factory and the loading text.

## data-cancel-html Stash Mechanism

The Cancel button on the edit panel must restore the prior view client-side (D-10 — no server round-trip, no autosave, no dirty-check). Implementation:

1. Route `POST /platforms/{pid}/edit` builds `_detail_context(...)` for the platform.
2. Calls `templates.env.get_template("platforms/_content_area.html").render(ctx)` — this renders the rendered/empty-state HTML to a string.
3. Injects the string into the edit-panel context as `stashed_render_or_empty`.
4. `_edit_panel.html` puts it on `<div data-cancel-html="{{ stashed_render_or_empty | e }}">`.
5. Cancel button's inline handler reads `this.closest('#content-area').dataset.cancelHtml` and `outerHTML`-replaces the panel.

T-03-02-04 (attribute injection) blocked by Jinja2's `| e` autoescape filter — even if the rendered HTML contains `</div>` or `"`, the value is HTML-escaped on its way into the attribute.

## Test Count Delta

| Test file                       | Before  | After   | Delta |
| ------------------------------- | ------- | ------- | ----- |
| tests/v2/test_content_store.py  | 0       | 14      | +14   |
| tests/v2/test_content_routes.py | 0       | 33      | +33   |
| tests/v2/test_overview_routes.py| 18      | 18      | 0     |
| **tests/v2/ total**             | **123** | **170** | +47   |
| **Full project**                | **306** | **353** | +47   |

`test_content_routes.py` includes 15 parametrized path-traversal cases (3 strings × 5 routes) plus 18 happy-path / edge-case tests.

## Integration Contract for Plan 03-03 (Summary Route)

Plan 03-03 will:

1. **Validate** `platform_id` with the same regex `^[A-Za-z0-9_\-]{1,128}$` (POST /platforms/{platform_id}/summary).
2. **Read content** via `from app_v2.services.content_store import read_content, get_content_mtime_ns`.
3. **Cache key** uses `(platform_id, get_content_mtime_ns(...), llm_name, llm_model)` — Pitfall 13 (ns precision).
4. **Swap target** is the already-wired `#summary-{pid}` slot with pre-seeded `#summary-{pid}-spinner` htmx-indicator. Plan 03-02 created the per-row slot in `_entity_row.html` (Overview tab) AND the page-level slot in `platforms/detail.html`.
5. **Backend label** uses `from app_v2.services.llm_resolver import resolve_active_backend_name` (single source of truth — same as overview/platforms).
6. **Loading text** "Summarizing… (using {backend_name})" is rendered by Plan 03-02's pre-seeded spinner element; the route response just innerHTML-swaps the rendered summary card on top of it.

## Task Commits

1. **Task 1 RED:** `dc0561c` test(03-02): add failing tests for content_store (TDD RED)
2. **Task 1 GREEN:** `c36cb5b` feat(03-02): add content_store service
3. **Task 2 RED:** `f6edd63` test(03-02): add failing tests for content routes (TDD RED)
4. **Task 2 templates:** `d2b9dd0` feat(03-02): add platform templates
5. **Task 2 router:** `868b0e2` feat(03-02): add platforms router
6. **Task 2 overview wiring:** `cec87ec` feat(03-02): wire AI Summary on Overview row
7. **Task 2 main.py wiring:** `fcc046c` feat(03-02): include_router(platforms.router) in main.py

7 commit boundaries match the `<scope_note>` contract exactly.

## Decisions Made

- **content_store stays content_dir-injected (pure)** — routes hold the single CONTENT_DIR module-level constant tests monkeypatch. Service module is reusable for any future caller (CLI dump, Plan 03-03 summary) with a different storage policy.
- **Pathlib alias pattern** — `from pathlib import Path as _Path` mirrors `overview.py:18` so `fastapi.Path` (path-param validator) stays unaliased while module-level path-typed constants reference `_Path`. Acceptance criteria explicitly enforce this with `grep -q "CONTENT_DIR: _Path"`.
- **data-cancel-html stash via templates.env.get_template** — server-side render of the rendered/empty-state HTML into a string, injected through `| e` autoescape on its way into the attribute. Single source of truth for both visual states; no JavaScript template duplication.
- **Standalone `disabled` HTML attribute coexists with `hx-disabled-elt="this"`** — `disabled` blocks click natively when no content file exists (D-13); `hx-disabled-elt` is for the in-flight loading state during a real summary request (when the button IS enabled). The two attributes serve different purposes and are not mutually exclusive.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_safe_target("..", tmp_path)` test premise was wrong**
- **Found during:** Task 1 GREEN phase
- **Issue:** Plan's behavior text said `_safe_target("..", tmp_path)` raises ValueError. In practice, `f"{'..'}.md"` produces the perfectly valid filename `"..md"` inside `tmp_path` — `relative_to` succeeds, no ValueError.
- **Fix:** Changed test input to `"../../etc/passwd"` which produces `"../../etc/passwd.md"` after concatenation — that DOES escape `content_dir` on resolve(), and `relative_to` raises ValueError. Plan's documented attack vector preserved; test now matches implementation behavior.
- **Files modified:** `tests/v2/test_content_store.py` (only the failing test's input string)
- **Committed in:** `c36cb5b` (Task 1 GREEN — same commit as the implementation)

**2. [Rule 1 - Bug] Phase 02 stub assertion in `test_get_root_ai_summary_button_disabled` blocks Phase 03 wiring**
- **Found during:** Task 2 PHASE C (overview.py + entity_row update)
- **Issue:** Phase 02 test asserted the stub copy `"Content page must exist first (Phase 3)"`. Phase 03 plan explicitly replaces the stub with the wired .ai-btn carrying the new copy `"Content page must exist first — open the platform to Add some"`. Test fails.
- **Fix:** Updated assertion to the prefix `"Content page must exist first"` (still uniquely identifies the disabled tooltip; survives future copy tweaks). Updated docstring to reference D-13 and the Phase 03 wiring rationale.
- **Files modified:** `tests/v2/test_overview_routes.py` (only `test_get_root_ai_summary_button_disabled`)
- **Committed in:** `cec87ec` (Task 2 overview wiring commit)

**3. [Rule 1 - Bug] `test_post_preview_xss_safe` assertion too strict**
- **Found during:** Final test run after main.py wiring
- **Issue:** Test asserted `'onerror=x' not in r.text` but `js-default` escapes the angle brackets, producing `&lt;img onerror=x&gt;` — the literal substring `onerror=x` survives as inert text (not an executable attribute). This is XSS-safe but the assertion failed.
- **Fix:** Changed assertion to test for the executable form (`<img onerror`) absence AND the escaped form (`&lt;img onerror`) presence. Captures the actual security property: raw HTML cannot reach the DOM as a tag.
- **Files modified:** `tests/v2/test_content_routes.py`
- **Committed in:** `fcc046c` (Task 2 main.py wiring commit)

**4. [Rule 1 - Bug] `test_overview_row_ai_button_enabled_when_content_exists` substring collision with hx-disabled-elt**
- **Found during:** Final test run after main.py wiring
- **Issue:** Test searched the rendered button for the substring `"disabled"` — but `hx-disabled-elt="this"` (HTMX wiring for in-flight state) contains the substring "disabled". False positive.
- **Fix:** Changed assertion to target the tooltip copy `"Content page must exist first"` which only renders inside the disabled-attribute conditional. Specific to the disabled-state copy, not the HTMX wiring.
- **Files modified:** `tests/v2/test_content_routes.py`
- **Committed in:** `fcc046c` (Task 2 main.py wiring commit)

---

**Total deviations:** 4 auto-fixed (all Rule 1 — test-side assertion bugs). Implementation matches plan; no scope changes.

## Issues Encountered

None beyond the four test-assertion bugs above. The 7-commit-boundary contract held cleanly; templates and router landed in separate commits without intermediate-state breakage; the `add_platform` route still rendered correctly after `_entity_dict` gained `has_content` because the new field is keyed safely with `entity.has_content` in the template (Jinja2 returns Undefined which renders as empty when the conditional `{% if not entity.has_content %}` evaluates).

## User Setup Required

None — no external service configuration. The shared intranet content/platforms/ directory is created at lifespan startup (Plan 03-01).

## Next Phase Readiness

**Plan 03-03 (summary route + summary_service) — READY**
- `read_content(pid, CONTENT_DIR)` and `get_content_mtime_ns(pid, CONTENT_DIR)` available as the canonical content reader for the summary cache key.
- `#summary-{pid}` swap target already wired in BOTH `_entity_row.html` (Overview tab) AND `platforms/detail.html` (detail page) — Plan 03-03's POST /platforms/{pid}/summary just innerHTML-swaps a card.
- Pre-seeded `#summary-{pid}-spinner` htmx-indicator already renders `"Summarizing… (using {backend_name})"` when the request is in-flight.
- `resolve_active_backend_name` available — same import path Plan 03-02 uses.

**Plan 03-04 (overview rewire + E2E) — READY**
- All routes wired; Plan 03-04 can write the cross-process race test (D-24) directly against the production routes.

No blockers or concerns.

## Self-Check: PASSED

Verified all created files exist:
- FOUND: app_v2/services/content_store.py
- FOUND: app_v2/routers/platforms.py
- FOUND: app_v2/templates/platforms/detail.html
- FOUND: app_v2/templates/platforms/_content_area.html
- FOUND: app_v2/templates/platforms/_edit_panel.html
- FOUND: app_v2/templates/platforms/_preview_pane.html
- FOUND: tests/v2/test_content_store.py
- FOUND: tests/v2/test_content_routes.py

Verified all 7 task commits in git log:
- FOUND: dc0561c test(03-02): RED content_store
- FOUND: c36cb5b feat(03-02): content_store service
- FOUND: f6edd63 test(03-02): RED content routes
- FOUND: d2b9dd0 feat(03-02): platform templates
- FOUND: 868b0e2 feat(03-02): platforms router
- FOUND: cec87ec feat(03-02): wire AI Summary on Overview row
- FOUND: fcc046c feat(03-02): include_router(platforms.router) in main.py

Verified test target met: 170 v2 tests passing (123 baseline + 47 new), 0 failed.
Full project: 353 tests passing.

---
*Phase: 03-content-pages-ai-summary*
*Plan: 02*
*Completed: 2026-04-25*
