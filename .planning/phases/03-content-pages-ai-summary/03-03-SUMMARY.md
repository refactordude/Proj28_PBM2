---
phase: 03-content-pages-ai-summary
plan: 03
subsystem: ai-summary
tags: [llm, summary, ttlcache, openai-sdk, htmx, error-classification, prompt-injection-defense, fastapi, tdd]

# Dependency graph
requires:
  - phase: 03-content-pages-ai-summary
    plan: 01
    provides: app_v2/services/llm_resolver.py::resolve_active_llm + resolve_active_backend_name; app_v2/static/css/app.css::ai-btn + .panel + .markdown-content
  - phase: 03-content-pages-ai-summary
    plan: 02
    provides: app_v2/services/content_store.py::read_content + get_content_mtime_ns; app_v2/routers/platforms.py::CONTENT_DIR; #summary-{pid} swap target pre-seeded in _entity_row.html and detail.html
provides:
  - app_v2/data/summary_prompt.py::SYSTEM_PROMPT + USER_PROMPT_TEMPLATE — D-20 verbatim with `<notes>` prompt-injection wrapper
  - app_v2/services/summary_service.py — TTLCache(maxsize=128, ttl=3600) + threading.Lock + _build_client + _classify_error + get_or_generate_summary
  - app_v2/routers/summary.py — POST /platforms/{pid}/summary (ALWAYS 200; never 5xx)
  - app_v2/templates/summary/_success.html — success fragment (panel mini-card + metadata footer + Regenerate)
  - app_v2/templates/summary/_error.html — amber alert + Retry
  - tests/v2/test_summary_service.py — 23 unit tests (cache hit/miss, mtime invalidation, TTL expiry, regenerate, error classification, build_client, lock-not-held)
  - tests/v2/test_summary_routes.py — 14 route tests (success, cache hit, regenerate, 4 error fragments, missing content, no LLM, 3 path-traversal, backend metadata, always-200 invariant)
affects: [03-04-overview-rewire-and-e2e]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Module-level TTLCache + threading.Lock paired (Pitfall 11) — lock held ONLY around dict get/set; LLM call runs OUTSIDE the lock so concurrent requests don't serialize on a slow Ollama cold-start
    - Pitfall-13 cache-key sharpening — hashkey(pid, mtime_ns, llm_name, llm_model) uses st_mtime_ns (integer) NOT st_mtime (float), avoiding stale-summary risk on filesystems that round mtime to whole seconds
    - openai SDK with custom base_url for dual-backend support — no litellm, no separate Ollama SDK; one `_build_client(cfg)` factory dispatches Ollama (`base_url=…/v1`, api_key="ollama", 60s timeout) or OpenAI (api_key from cfg or env, 30s timeout) on cfg.type
    - 7-string error vocabulary (UI-SPEC §8c) + 8th "LLM not configured" — _classify_error maps every openai 2.x / httpx exception to a fixed user-readable string; raw exception text NEVER reaches the client; route `_log.warning`s the original
    - "ALWAYS 200" route contract — every failure path returns the amber-warning fragment via templates.TemplateResponse; the route never raises HTTPException, never returns 5xx; the HTMX swap lands inline in #summary-{pid}, never escalating to the global #htmx-error-container
    - Regenerate write-back (D-18) — X-Regenerate: true header bypasses cache lookup but stores the new value under the same key, so a subsequent normal click hits the new value
    - APITimeoutError ordered BEFORE APIConnectionError in classifier — APITimeoutError is a subclass of APIConnectionError in openai 2.x; reversing the order would misclassify every timeout as a connect error
    - Pitfall-14 _Timer__timer test idiom — patches the cachetools v7 name-mangled inner timer callable so TTL expiry tests don't need wall-clock sleep

key-files:
  created:
    - app_v2/data/summary_prompt.py
    - app_v2/services/summary_service.py
    - app_v2/routers/summary.py
    - app_v2/templates/summary/_success.html
    - app_v2/templates/summary/_error.html
    - tests/v2/test_summary_service.py
    - tests/v2/test_summary_routes.py
  modified:
    - app_v2/main.py

key-decisions:
  - "ALWAYS 200 contract: route never raises HTTPException and never returns 5xx. Every error class flows to summary/_error.html with a classified reason. Acceptance criterion enforces via grep `! status_code=5` and `! raise HTTPException`."
  - "8th vocabulary entry 'LLM not configured — set one in Settings' for empty settings.llms case (when llm_resolver.resolve_active_llm returns None). UI-SPEC §8c's seven entries all assume a backend exists; this 8th entry is the natural extension."
  - "Cache key uses mtime_ns (Pitfall 13) — get_content_mtime_ns returns Path.stat().st_mtime_ns (integer nanoseconds). Test asserts NO float component in the cache-key tuple."
  - "Lock NOT held during LLM call (Pitfall 11) — explicit smoke test acquires the lock from a chat.completions.create side_effect and asserts non-blocking acquire succeeds. If the outer code held the lock the test would deadlock or the assertion would fail."
  - "Pitfall-18 deviation (RESEARCH.md Q3): NO Ollama warmup ping in lifespan; rely on summary_service _build_client's 60s read timeout. Comment in summary_service AND main.py makes the deviation auditable."
  - "Single shared llm_resolver module (Plan 03-01 Q2 RESOLVED): summary.py imports resolve_active_llm + resolve_active_backend_name; no inline _resolve_active_llm or _backend_display_name helpers. Eliminates 3-way duplication previously slated for overview.py / platforms.py / summary.py."
  - "Path-traversal hardening (D-22): FastAPI Path(pattern=^[A-Za-z0-9_\\-]{1,128}$) at HTTP entry returns 404 (URL-encoded slashes reshape Starlette routing) or 422 (regex mismatch) BEFORE any LLM call. Parametrized test covers 3 attack strings; asserts 0 LLM calls and empty content_dir post-attack."
  - "Renderer pipeline reuse: LLM-generated markdown text passed through render_markdown() (the same MarkdownIt('js-default') singleton from content_store) — defense against an LLM output containing `<script>` is the SAME XSS defense as user-authored markdown. T-03-03-04 mitigation."

patterns-established:
  - "Pattern: TTLCache + threading.Lock paired, lock NOT held during slow IO call. The lock guards only dict.get / dict[key] = result; the LLM/network call is outside the lock so concurrent requests with the same key may both fetch (acceptable; bounded by cache size × TTL)."
  - "Pattern: classified-error vocabulary as the LLM/UI boundary. _classify_error(exc, backend_name) returns one of N fixed user-facing strings; raw exception text NEVER crosses the boundary; the server logs the original via _log.warning. Reusable for any future LLM-backed feature."
  - "Pattern: ALWAYS-200 routes for HTMX inline error fragments. Routes whose error swap target is a per-row slot (NOT the global #htmx-error-container) MUST return 200 with the error fragment, never raise HTTPException. The 4xx/5xx path triggers the global error handler — wrong place for inline UX errors."
  - "Pattern: cache-key precision sharpening (Pitfall 13). When using filesystem mtime as a cache-invalidation signal, prefer st_mtime_ns (int) over st_mtime (float). Same-second edits on lossy filesystems would otherwise miss the invalidation."

requirements-completed: [SUMMARY-02, SUMMARY-03, SUMMARY-04, SUMMARY-05, SUMMARY-06, SUMMARY-07]

# Metrics
duration: 23min
completed: 2026-04-25
---

# Phase 03 Plan 03: Summary Route + Service + Templates Summary

**TDD-built AI Summary feature: TTLCache + Lock + openai SDK single-shot + 7-string error vocabulary, with the route ALWAYS returning 200 (UI-SPEC mandate). Cache key sharpened to mtime_ns (Pitfall 13). Lock held only around dict get/set — LLM call runs outside the lock. Shared llm_resolver eliminates 3-way duplication. 37 new tests passing (23 service + 14 route); full v2 suite 207 passing, 0 failed.**

## Performance

- **Duration:** ~23 min
- **Started:** 2026-04-25T22:55Z (Task 1 RED commit `14480b0`)
- **Completed:** 2026-04-25T23:18Z (Task 2 GREEN commit `85821a8`)
- **Tasks:** 2 (both auto, both TDD)
- **Commit boundaries:** 5 — RED + GREEN + templates + RED + GREEN
- **Files created:** 7
- **Files modified:** 1 (`app_v2/main.py` — single `include_router(summary.router)` line + reorder comment)

## summary_service Public API

| Symbol                           | Purpose                                                                                                                                                                                                                          |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SummaryResult`                  | Frozen dataclass: `text`, `llm_name`, `llm_model`, `generated_at` (UTC tz-aware datetime). Used by templates for the metadata footer.                                                                                            |
| `LLMNotConfiguredError`          | Raised when `settings.llms` is empty. Currently the route handles this via `resolve_active_llm` returning `None` and short-circuiting; the exception class is exported for future explicit-raise paths (e.g., a CLI front-end). |
| `get_or_generate_summary(...)`   | `(pid, cfg, content_dir, *, regenerate=False) → SummaryResult`. Cached single-shot. Reads content_mtime_ns + content; cache key = `hashkey(pid, mtime_ns, cfg.name, cfg.model)`. Lock guards only dict access.                  |
| `_classify_error(exc, backend)`  | Maps openai 2.x / httpx exceptions to one of 7 fixed strings (UI-SPEC §8c). Order matters: APITimeoutError BEFORE APIConnectionError because the former is a subclass of the latter in openai 2.x.                              |
| `_build_client(cfg)`             | OpenAI client factory. Ollama: `base_url=…/v1`, `api_key="ollama"`, 60s timeout. OpenAI: `api_key` from cfg or `OPENAI_API_KEY` env, 30s timeout. Pitfall 18 deviation comment.                                                  |
| `clear_summary_cache()`          | Test helper: clears the module-level TTLCache under the lock.                                                                                                                                                                    |

## Cache Key Construction (Pitfall 13)

```python
key = hashkey(platform_id, mtime_ns, cfg.name, cfg.model)
```

- `platform_id` — string (regex-validated at HTTP entry).
- `mtime_ns` — **integer nanoseconds** from `Path.stat().st_mtime_ns`. **NOT** `st_mtime` (float seconds). On filesystems that round mtime to whole seconds, two edits within the same second would otherwise share a cache entry and the second user would see the stale summary.
- `cfg.name` — partitions cache by LLM backend identity (so switching from `ollama-default` to `my-openai` is a fresh cache entry).
- `cfg.model` — partitions cache by exact model (e.g., `llama3.1` vs `llama3.2`).

`cachetools.keys.hashkey` returns a tuple-like object that hashes components individually (no `str()` stringification — T-03-03-07 mitigation, not a vulnerability for this 4-tuple but the principle holds for future extensions).

## Error Vocabulary

The user-facing reason string is one of these — raw exception text NEVER reaches the client. `_classify_error` checks isinstance in this order:

| Trigger                                                              | Reason string                                            |
| -------------------------------------------------------------------- | -------------------------------------------------------- |
| `APITimeoutError`, `httpx.ReadTimeout`, `httpx.WriteTimeout`         | `LLM took too long to respond`                           |
| `APIConnectionError`, `httpx.ConnectError`, `httpx.ConnectTimeout`   | `Cannot reach the LLM backend ({backend_name})`          |
| `AuthenticationError`                                                | `LLM authentication failed — check API key in Settings` |
| `RateLimitError`                                                     | `LLM is rate-limited — try again in a moment`           |
| `APIStatusError` with `status_code >= 500`                           | `LLM backend returned an error (HTTP {status})`         |
| `FileNotFoundError`                                                  | `Content page no longer exists`                          |
| any other exception                                                  | `Unexpected error — see server logs`                    |
| (route-level) empty `settings.llms`                                  | `LLM not configured — set one in Settings`              |

The 8th entry is added by `summary.py` directly (not in `_classify_error`) because the empty-LLM case is detected via `resolve_active_llm` returning `None`, before any exception path is reached.

**Order rationale:** `APITimeoutError` MUST be checked before `APIConnectionError` — in openai 2.x the former subclasses the latter, so reversing the order would misclassify every timeout as a connect error. The classifier explicitly documents this with a comment.

## Lock-Not-Held-During-LLM-Call (Pitfall 11)

```python
# 1) Lookup under lock
if not regenerate:
    with _summary_lock:
        cached = _summary_cache.get(key)
    if cached is not None:
        return cached

# 2) LLM call OUTSIDE the lock
text = _call_llm_single_shot(content, cfg)
result = SummaryResult(...)

# 3) Write back under the lock
with _summary_lock:
    _summary_cache[key] = result
```

If the lock were held during step 2, every concurrent request hitting a cache miss would serialize behind a single slow Ollama cold-start (≥several seconds). Holding the lock only around the dict access means:

- Two concurrent requests with the same key may both call the LLM. Acceptable: the cache is bounded (128 entries × 1hr TTL).
- The cache write is atomic (the dict[] assignment is the only mutation under the lock).
- TTL expiry behavior is unchanged.

The invariant is enforced by an explicit smoke test (`test_lock_not_held_during_llm_call`) that tries a non-blocking acquire from inside the chat.completions.create side_effect and asserts True.

## Route's "Always 200" Contract

```python
@router.post("/{platform_id}/summary", response_class=HTMLResponse)
def get_summary_route(...):
    settings = getattr(request.app.state, "settings", None)
    cfg = resolve_active_llm(settings)
    backend_name = resolve_active_backend_name(settings)
    if cfg is None:
        return _render_error(request, platform_id, "LLM not configured — set one in Settings")

    regenerate = (x_regenerate or "").lower() == "true"
    try:
        result = summary_service.get_or_generate_summary(...)
    except FileNotFoundError:
        return _render_error(request, platform_id, "Content page no longer exists")
    except Exception as exc:  # noqa: BLE001 — classified to user-readable string
        reason = summary_service._classify_error(exc, backend_name)
        _log.warning("Summary failed for %s (%s): %s", platform_id, type(exc).__name__, exc)
        return _render_error(request, platform_id, reason)

    age_s = max(0, int((datetime.now(timezone.utc) - result.generated_at).total_seconds()))
    summary_html = render_markdown(result.text)
    return templates.TemplateResponse(request, "summary/_success.html", {...})
```

**Why this matters for HTMX:** the per-row summary slot uses `hx-swap="innerHTML"` targeting `#summary-{pid}`. A 5xx response would invoke the global `htmx-error-handler.js` which targets `#htmx-error-container` (top of the page). The error fragment would land in the wrong place, and the user would see a generic alert instead of an inline retry button. Returning 200 with the error fragment keeps the failure visible WHERE the user clicked.

The contract is enforced by acceptance criteria (`! grep -q 'status_code=5' app_v2/routers/summary.py` and `! grep -q 'raise HTTPException'`) AND by an explicit `test_post_summary_never_returns_5xx_on_any_exception` test that injects an unclassified `ValueError` and asserts 200.

## Backend Resolution

`summary.py` imports `resolve_active_llm` + `resolve_active_backend_name` from the shared `app_v2.services.llm_resolver` (Plan 03-01). Resolution order (RESEARCH.md Q2):

1. `settings.llms` entry whose `name == settings.app.default_llm`
2. `settings.llms[0]` if any LLMs configured
3. `None` (route returns "LLM not configured" error fragment)

`resolve_active_backend_name` returns `'OpenAI'` (when `cfg.type == 'openai'`) or `'Ollama'` (D-19 default for any other type — including missing/None).

The resolver is duck-typed: it accepts ANY object with a `.llms` attribute, so tests can monkeypatch `app.state.settings` with a minimal Pydantic `Settings` instance. Both helpers are defensive — they `try / except: return None / 'Ollama'` and never raise.

## Test Count Delta

| Test file                          | Before  | After   | Delta |
| ---------------------------------- | ------- | ------- | ----- |
| tests/v2/test_summary_service.py   | 0       | 23      | +23   |
| tests/v2/test_summary_routes.py    | 0       | 14      | +14   |
| **tests/v2/ total**                | **170** | **207** | **+37** |
| **Full project**                   | **353** | **390** | **+37** |

Test breakdown:

- **23 service tests:** cache hit/miss, mtime invalidation (D-25), regenerate write-back (D-18), SummaryResult metadata, mtime_ns key (Pitfall 13), FileNotFoundError, TTL expiry (Pitfall 14 _Timer__timer pattern), 7 error-classification cases (one per vocabulary entry + APITimeoutError + APIConnectionError pairs), 4 build_client cases (Ollama with/without endpoint, OpenAI api_key behaviors), lock-not-held smoke test, clear_summary_cache helper.
- **14 route tests:** success fragment with metadata, markdown rendering, cache hit on second call, X-Regenerate bypass + write-back, 3 error-fragment cases (connect / timeout / auth), missing content → 'Content page no longer exists', empty settings.llms → 'LLM not configured', 3 parametrized path-traversal cases, backend metadata thread-through, ALWAYS-200 invariant on unclassified exception.

## Task Commits

1. **Task 1 RED:** `14480b0` test(03-03): add summary_prompt module + failing tests for summary_service (TDD RED)
2. **Task 1 GREEN:** `cc68ce3` feat(03-03): add summary_service (TTLCache + openai SDK + classify_error)
3. **Templates:** `186b2c2` feat(03-03): add summary templates (success + error fragments)
4. **Task 2 RED:** `4345bbd` test(03-03): add failing tests for summary route (TDD RED)
5. **Task 2 GREEN:** `85821a8` feat(03-03): add summary route (POST /platforms/{pid}/summary — always 200)

## Decisions Made

- **8th vocabulary entry "LLM not configured — set one in Settings"** — UI-SPEC §8c's seven entries all assume a backend exists; the empty-`settings.llms` case needs its own copy. Adopted as a route-level pre-check (before `_classify_error` is even reached) so the resolver's `None` return is the gate.
- **Lock NOT held during LLM call** — Pitfall 11 rationale. Trades exact-once-per-key for not serializing on slow IO. Two concurrent identical requests may both call the LLM (acceptable: 128-entry × 1hr TTL bounds spend per T-03-03-05 acceptance).
- **mtime_ns over mtime** — Pitfall 13 sharpening. Sub-second edits on filesystems that round mtime would otherwise miss cache invalidation. `get_content_mtime_ns` is the dedicated reader; tests assert no float in the key tuple.
- **APITimeoutError BEFORE APIConnectionError in classifier** — inheritance order in openai 2.x. Reversing would misclassify every timeout. Comment in `_classify_error` documents the constraint.
- **No `from pathlib import Path` in summary.py** — `summary.py` only uses FastAPI's `Path` (path-parameter validation) and reaches pathlib paths transitively via `platforms_router.CONTENT_DIR`. Importing both `Path` symbols would shadow `pathlib.Path` (the second import wins). Module docstring documents the choice; acceptance criterion enforces.
- **Render LLM markdown via the same `render_markdown()` from content_store** — T-03-03-04 (LLM-generated XSS) mitigation. `MarkdownIt('js-default')` is a singleton; LLM output is treated as untrusted markdown like user-authored content.
- **`backend_name` threaded through to template context** — even though the success template doesn't currently use it, the context key is present for the future "Summarizing… (using {backend})" disclosure UX (already pre-rendered by Plan 03-02 in the htmx-indicator).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Acceptance-criteria grep `class="alert alert-warning"` was over-strict**

- **Found during:** Final acceptance-criteria pass.
- **Issue:** The plan's acceptance criterion `grep -q 'class="alert alert-warning"' app_v2/templates/summary/_error.html` looks for a literal closing-quote string. The UI-SPEC §8c verbatim template (which the plan also prescribed) sets `class="alert alert-warning d-flex justify-content-between align-items-center mt-2"` — the closing quote is far from `alert-warning`. The literal grep fails on a correct template.
- **Fix:** No code change. The `class="alert alert-warning` substring matches; the security-relevant CSS class is present; UI-SPEC §8c is faithfully followed. The over-strict acceptance pattern is documented as a Rule-1 plan bug. The substring grep `class="alert alert-warning` was used to confirm the property.
- **Verification:** `grep -q 'class="alert alert-warning' app_v2/templates/summary/_error.html` exits 0; rendered route response in `test_post_summary_returns_error_fragment_on_connect_error` contains `class="alert alert-warning` AND `Cannot reach the LLM backend` AND `Retry`.
- **Files modified:** None.
- **Committed in:** N/A (no code change required).

---

**Total deviations:** 1 plan bug (over-strict acceptance grep) — no code change, security property still verified.
**Impact on plan:** Plan acceptance criteria still met (the substring grep confirms the security-relevant CSS class is present, and the route tests assert the same property at runtime).

## Issues Encountered

- None. TDD RED→GREEN cycles converged on the first try for both Task 1 and Task 2.
- The pre-existing summary_service implementation (Task 1 commits `14480b0` / `cc68ce3` / `186b2c2`) was already complete on disk when this session resumed; only Task 2 (route + main.py wiring + route tests) needed new commits.

## User Setup Required

None — no external service configuration. The summary route works without a real LLM backend (returns the "LLM not configured" error fragment when settings.llms is empty); a real Ollama or OpenAI backend produces the success fragment.

For the operator wanting end-to-end manual smoke: configure an Ollama URL in `config/settings.yaml` (`llms: - name: ollama-default, type: ollama, model: llama3.1, endpoint: http://localhost:11434`), start Ollama (`ollama serve` + `ollama pull llama3.1`), then `curl -s -X POST http://localhost:8000/platforms/Samsung_S22Ultra_SM8450/summary` should return either the success card or the amber alert (never 5xx).

## Integration Contract for Plan 03-04 (Overview Rewire + E2E)

Plan 03-04 will:

1. **Cross-process race test (D-24)** imports `app_v2.services.content_store` directly (not summary_service) — the race is on the file-write atomic invariant, not the summary cache. Plan 03-03's contract is that the cache key uses `mtime_ns` so a successful concurrent write produces a fresh cache entry on the next read.
2. **Overview list endpoint integration:** the per-row `#summary-{pid}` slot is already wired by Plan 03-02; Plan 03-03 just supplies the 200/200 response that swaps into it. Plan 03-04 may add filter-driven HTMX rerender tests that include the summary slot.
3. **No further modification to summary_service.py / summary.py is anticipated by Plan 03-04.**

## Next Phase Readiness

**Plan 03-04 (overview rewire + E2E) — READY**

- All Phase 03 routes are wired; Plan 03-04 can write end-to-end tests against the production routes.
- The cross-process race test (D-24) targets `content_store.save_content` directly; the summary cache invalidation contract is verified by `test_summary_cache_invalidates_on_mtime_change` (Plan 03-03).

No blockers or concerns.

## Threat Flags

None — no new security-relevant surface introduced beyond the threat-modeled paths in `<threat_model>` (T-03-03-01..10). Specifically:

- LLM output rendered via existing `render_markdown` (same XSS defense as content pages — T-03-03-04 mitigation reused).
- Cache key built with `hashkey` (T-03-03-07 mitigation in place).
- API key never traverses the error-classification surface (T-03-03-03 mitigation: `_build_client` raises `RuntimeError("OpenAI API key not configured")` which the route catches and classifies to "Unexpected error — see server logs"; the API key value itself never enters `_classify_error`).
- All paths for `platform_id` are gated by the regex pattern at HTTP entry (T-03-03-10 mitigation reused from Plan 03-02).

## Self-Check: PASSED

Verified all created files exist:
- FOUND: app_v2/data/summary_prompt.py
- FOUND: app_v2/services/summary_service.py
- FOUND: app_v2/routers/summary.py
- FOUND: app_v2/templates/summary/_success.html
- FOUND: app_v2/templates/summary/_error.html
- FOUND: tests/v2/test_summary_service.py
- FOUND: tests/v2/test_summary_routes.py

Verified all 5 task commits in git log:
- FOUND: 14480b0 test(03-03): RED summary_service
- FOUND: cc68ce3 feat(03-03): summary_service GREEN
- FOUND: 186b2c2 feat(03-03): summary templates
- FOUND: 4345bbd test(03-03): RED summary route
- FOUND: 85821a8 feat(03-03): summary route GREEN

Verified test target met:
- 23 service tests passing (≥18 required) — PASS
- 14 route tests passing (≥10 required) — PASS
- 207 v2 tests passing, 0 failed — PASS
- 390 full-project tests passing, 0 failed — PASS

Verified acceptance criteria (key items):
- summary.py: no `async def` (INFRA-05) — PASS
- summary.py: no `status_code=5` (UI-SPEC mandate) — PASS
- summary.py: no `raise HTTPException` — PASS
- summary.py: no `from pathlib import Path` (Blocker 2) — PASS
- summary.py: imports from `app_v2.services.llm_resolver` (Warning 4) — PASS
- summary.py: no inline `_resolve_active_llm` / `_backend_display_name` (Warning 4) — PASS
- summary_service.py: `Pitfall 18` + `DEVIATION from RESEARCH.md Q3` documented — PASS
- summary_service.py: `TTLCache(maxsize=128, ttl=3600)` + `_summary_lock = threading.Lock()` (D-17) — PASS
- summary_service.py: `hashkey(platform_id, mtime_ns` (Pitfall 13) — PASS
- summary_service.py: `stream=False` (D-21) — PASS
- summary_service.py: lock NOT held during LLM call (verified by smoke test) — PASS
- main.py: `include_router(summary.router)` ordered platforms→summary→root — PASS

---
*Phase: 03-content-pages-ai-summary*
*Plan: 03*
*Completed: 2026-04-25*
