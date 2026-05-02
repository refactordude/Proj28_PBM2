---
phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
plan: 01
subsystem: infra
tags: [pydantic, sse-starlette, htmx, plotly, jinja2, agent-config]

# Dependency graph
requires:
  - phase: 02-ui-shell-rewrite
    provides: tokens.css palette + .panel/.panel-header/.panel-body component classes that the new chat surface (built in 03-04) extends
provides:
  - sse-starlette pinned in requirements.txt for streaming chat endpoint
  - AgentConfig.chat_max_steps field (default=12, ge=1, le=50) for the multi-step agent loop budget
  - documented chat_max_steps key in config/settings.example.yaml
  - {% block extra_head %}{% endblock %} placeholder in base.html for per-page asset injection
  - vendored htmx-ext-sse@2.2.4 (8.9KB) for HTMX SSE wiring
  - vendored plotly.js 2.35.2 (4.5MB) for Ask-page chart rendering
  - VERSIONS.txt manifests for both vendored bundles
affects: [03-02-chat-loop, 03-03-routes, 03-04-templates, 03-05-cleanup]

# Tech tracking
tech-stack:
  added:
    - sse-starlette>=3.3,<4.0 (explicit pin; was transitively present)
    - htmx-ext-sse@2.2.4 (vendored JS)
    - plotly.js 2.35.2 (vendored JS)
  patterns:
    - "Per-page asset injection via Jinja `extra_head` block — avoids global Plotly load (RESEARCH Pitfall 5)"
    - "VERSIONS.txt manifest format extended (append-not-overwrite) when adding new vendored bundles to an existing vendor dir"
    - "Extending AgentConfig with new field (chat_max_steps) over introducing AgentChatConfig submodel — avoids YAML schema bump"

key-files:
  created:
    - app_v2/static/vendor/htmx/htmx-ext-sse.js
    - app_v2/static/vendor/plotly/plotly.min.js
    - app_v2/static/vendor/plotly/VERSIONS.txt
  modified:
    - requirements.txt
    - app/core/agent/config.py
    - config/settings.example.yaml
    - app_v2/templates/base.html
    - app_v2/static/vendor/htmx/VERSIONS.txt

key-decisions:
  - "Extend AgentConfig with chat_max_steps:int field (research-recommended) instead of new AgentChatConfig submodel — avoids YAML schema bump (Gap 12)"
  - "Default chat_max_steps=12 per D-CHAT-03 — leaves headroom for inspect_schema → distincts → run_sql (REJECTED) → run_sql → run_sql → present_result (~6 calls)"
  - "Upper bound le=50 per RESEARCH Open Question 4 — DoS mitigation T-03-01-05"
  - "Plotly loaded only on /ask via per-page extra_head block — global load would inflict 4.5MB cost on Browse/JV/Settings (RESEARCH Pitfall 5)"
  - "extra_head block placed AFTER tokens.css/app.css and BEFORE htmx.min.js + bootstrap bundle — page-specific styles override globals; page-specific scripts can rely on htmx already deferred"
  - "VERSIONS.txt manifest append (not overwrite) — preserves existing htmx@2.0.10 audit record"

patterns-established:
  - "Vendor JS bundles via curl from CDN + VERSIONS.txt manifest with source URL + download date + pin reason"
  - "node --check on vendored bundles as syntactic-validity smoke test before commit"
  - "Per-page heavy asset loading via Jinja extra_head block (not global <head>)"

requirements-completed: [D-CHAT-03]

# Metrics
duration: ~10min
completed: 2026-05-02
---

# Phase 03 Plan 01: Chat Foundation Primitives Summary

**Foundation primitives for the multi-step Ask-chat overhaul: sse-starlette pin, AgentConfig.chat_max_steps (default=12), per-page extra_head Jinja block, and vendored htmx-ext-sse@2.2.4 + Plotly 2.35.2 bundles.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-02T18:04:33Z
- **Completed:** 2026-05-02T18:14:51Z
- **Tasks:** 2 / 2
- **Files modified:** 5
- **Files created:** 3
- **Tests:** 464 passed, 5 skipped (no regressions)

## Accomplishments

- Pinned sse-starlette explicitly in requirements.txt (was transitive only) so plan 03-02's `EventSourceResponse` import is contractual
- Added `AgentConfig.chat_max_steps` field (Pydantic `Field(default=12, ge=1, le=50)`) — the budget knob plan 03-02's `stream_chat_turn` will pass into PydanticAI `UsageLimits(tool_calls_limit=…)`
- Documented the new key in `config/settings.example.yaml` under `app.agent.chat_max_steps`
- Exposed `{% block extra_head %}{% endblock %}` slot in `base.html` between css imports and htmx defer tag, enabling per-page asset injection without disturbing global script ordering
- Vendored `htmx-ext-sse@2.2.4` (8,921 bytes) — HTMX 2.x core ships without SSE; required for the new chat surface
- Vendored Plotly 2.35.2 (4,558,696 bytes) — chart payload for `_final_card.html` (D-CHAT-05). Loaded only on `/ask` via `extra_head` to spare other pages
- Updated `app_v2/static/vendor/htmx/VERSIONS.txt` (append, not overwrite) and created new `app_v2/static/vendor/plotly/VERSIONS.txt` with full source-URL + download-date + pin-reason audit trail

## Task Commits

Each task was committed atomically:

1. **Task 1: sse-starlette pin + AgentConfig.chat_max_steps + settings.example.yaml documentation** — `6b7a019` (feat)
2. **Task 2: extra_head block + vendor htmx-ext-sse + Plotly bundles** — `8a54f99` (feat)

## Files Created/Modified

### Created
- `app_v2/static/vendor/htmx/htmx-ext-sse.js` — htmx-ext-sse@2.2.4 (8.9KB) — SSE wiring extension
- `app_v2/static/vendor/plotly/plotly.min.js` — plotly.js 2.35.2 (4.5MB) — chart bundle for /ask
- `app_v2/static/vendor/plotly/VERSIONS.txt` — Plotly manifest (source URL + date + pin reason)

### Modified
- `requirements.txt` — added explicit `sse-starlette>=3.3,<4.0` pin alongside `pydantic-ai`
- `app/core/agent/config.py` — added `chat_max_steps: int = Field(default=12, ge=1, le=50, description=...)` as last field on `AgentConfig`
- `config/settings.example.yaml` — documented `chat_max_steps: 12` under `app.agent` with inline rationale comment
- `app_v2/templates/base.html` — inserted `{% block extra_head %}{% endblock %}` between css imports and HTMX defer block
- `app_v2/static/vendor/htmx/VERSIONS.txt` — appended htmx-ext-sse@2.2.4 manifest block (preserved existing htmx@2.0.10 entry)

## Decisions Made

1. **Extend AgentConfig over new AgentChatConfig submodel.** Per RESEARCH Gap 12: a submodel would force a YAML schema bump (`app.agent_chat.max_steps`). Extending `AgentConfig` keeps all agent budgets under `app.agent.*` with no rearrangement; existing `settings.yaml` files keep working because Pydantic falls back to default when the key is absent.
2. **Place extra_head AFTER css imports, BEFORE htmx defer scripts.** This ordering means page-specific stylesheets can override `app.css` rules, and page-specific scripts can declare ordering relative to htmx (which already uses `defer`, so DOM order = parse order). Verified by inspecting the existing `<head>` block layout against the requirement that the new chat surface needs Plotly loaded ahead of any chart-render JS that runs on `htmx:afterSwap`.
3. **VERSIONS.txt append-not-overwrite.** The existing htmx@2.0.10 record is an audit anchor; replacing it would lose that history. Format mirrors the existing block verbatim (key:value lines with a `files:` list).
4. **node --check both bundles before committing.** Quick syntactic-validity check that catches a corrupted/half-downloaded curl payload without needing to spin up the full Starlette app.

## Deviations from Plan

None — plan executed exactly as written. All acceptance criteria from both tasks passed on first attempt; the existing 10 nl_agent tests + 18 v2 main tests + full v2/agent suite (464 passed, 5 skipped) showed no regressions.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. Vendored bundles are committed to the repo; the new `chat_max_steps` config key has a sensible default and does not require user override.

## Verification Performed

Both tasks ran their automated `<verify>` blocks plus the plan's `<verification>` block:

- `grep -E "^sse-starlette" requirements.txt` → `sse-starlette>=3.3,<4.0`
- `python -c "from app.core.agent.config import AgentConfig; assert AgentConfig().chat_max_steps == 12"` → OK
- Range validation: `chat_max_steps=0` → ValidationError (ge=1 enforced); `chat_max_steps=51` → ValidationError (le=50 enforced)
- `AgentConfig.model_fields.keys()` → `['model', 'max_steps', 'row_cap', 'timeout_s', 'allowed_tables', 'max_context_tokens', 'chat_max_steps']` — all 6 pre-existing fields preserved in original order
- `grep "block extra_head" app_v2/templates/base.html` → match at line 17
- `extra_head` confirmed inside `<head>` via Python regex slice
- `wc -c` on bundles: htmx-ext-sse=8921 bytes (>1000), plotly.min.js=4558696 bytes (>1000000)
- `node --check` passes on both bundles
- `grep -c "htmx: 2.0.10" .../VERSIONS.txt` → 1 (original record preserved)
- `pytest tests/v2/ tests/agent/ -x` → 464 passed, 5 skipped, no failures

## Threat Surface Audit

Per the plan's `<threat_model>`:

- **T-03-01-01 (Tampering, vendored JS):** mitigated — exact versions pinned in VERSIONS.txt manifests with source URL + license-vetting placeholder via UI-SPEC §Registry Safety reference.
- **T-03-01-03 (Plotly on every page):** mitigated by design — Plotly bundle is NOT loaded by base.html. It will be injected via `extra_head` only on `/ask` (in plan 03-04). Verified by `grep "plotly.min.js" app_v2/templates/` returning zero matches across all templates.
- **T-03-01-04 (chat_max_steps EoP):** accepted — Pydantic ge/le validators prevent out-of-range values; field is read-only at agent-loop time.
- **T-03-01-05 (DoS via cap=50):** mitigated — `UsageLimits(tool_calls_limit=…)` in plan 03-02 enforces the per-turn budget; combined with existing `timeout_s` and read-only DB user, max realistic damage is 50 SELECT queries per turn.

No new threat flags surfaced beyond the plan's pre-registered set.

## Next Phase Readiness

All foundation primitives in place for downstream Wave-1+ plans:

- **03-02 (chat_loop.py):** `from app.core.agent.config import AgentConfig` exposes `chat_max_steps`; `from sse_starlette import EventSourceResponse, ServerSentEvent` is contract-pinned.
- **03-04 (templates/ask/index.html rewrite):** can extend `{% block extra_head %}<script src="{{ url_for('static', path='vendor/plotly/plotly.min.js') }}" defer></script><script src="{{ url_for('static', path='vendor/htmx/htmx-ext-sse.js') }}" defer></script>{% endblock %}` to load Plotly + SSE extension only on `/ask`.
- **No runtime behavior change yet** — Ask page still renders the v2.0 Phase 6 surface (rewritten in plan 03-04). All existing tests green.

## Self-Check

Verified file existence and commit hashes:

- `app_v2/static/vendor/htmx/htmx-ext-sse.js` → FOUND (8921 bytes)
- `app_v2/static/vendor/plotly/plotly.min.js` → FOUND (4558696 bytes)
- `app_v2/static/vendor/plotly/VERSIONS.txt` → FOUND
- `app_v2/static/vendor/htmx/VERSIONS.txt` (modified) → FOUND, contains both htmx@2.0.10 + htmx-ext-sse@2.2.4 blocks
- `requirements.txt` (modified) → FOUND, contains `sse-starlette>=3.3,<4.0`
- `app/core/agent/config.py` (modified) → FOUND, contains `chat_max_steps`
- `config/settings.example.yaml` (modified) → FOUND, contains `chat_max_steps: 12`
- `app_v2/templates/base.html` (modified) → FOUND, contains `{% block extra_head %}{% endblock %}`
- Commit `6b7a019` (Task 1) → FOUND in git log
- Commit `8a54f99` (Task 2) → FOUND in git log

## Self-Check: PASSED

---
*Phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on*
*Plan: 01*
*Completed: 2026-05-02*
