---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Bootstrap Shell
status: defining_requirements
stopped_at: Milestone v2.0 started — defining requirements
last_updated: "2026-04-25T00:00:00.000Z"
last_activity: 2026-04-25
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-25)

**Core value:** Fast ad-hoc browsing of the UFS parameter database — even if NL fails, the UI lets non-SQL users find platforms, compare parameters, chart, and export
**Current focus:** v2.0 Bootstrap Shell — defining requirements

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-25 — Milestone v2.0 Bootstrap Shell started

Progress: [░░░░░░░░░░] 0%

## Accumulated Context

### Decisions (v2.0 locked so far)

- Stack: FastAPI + Bootstrap 5 + HTMX + Jinja2 + markdown-it-py
- Scope: v2.0 is a parallel rewrite — v1.0 Streamlit code stays archived; v2.0 lives in a new directory (roadmapper decides path)
- Tabs (horizontal, top nav): Overview / Browse / Ask
- Entities on Overview = user-curated favorites (subset of PLATFORM_IDs), each with title + link + AI Summary button
- Filters: Brand / SoC / Year facets parsed from PLATFORM_ID + "has content page" toggle; all HTMX-swapped
- Content pages: markdown files at `content/platforms/<PLATFORM_ID>.md`, addable/editable/deletable via HTMX forms, rendered with markdown-it-py
- AI Summary: reuses v1.0 LLM adapter (single-shot completion on the content markdown), HTMX in-place swap, no navigation
- Browse tab: re-renders v1.0 pivot/swap-axes/caps/export under Bootstrap
- Ask tab: carries v1.0 NL agent (PydanticAI + dual OpenAI/Ollama + SAFE harness) forward under new UI
- Reuse: framework-agnostic v1.0 modules (result_normalizer, nl_agent, sql_validator/limiter/scrubber, build_pydantic_model, config models) imported, not copied
- Refactor: `ufs_service.py` `@st.cache_data` decorators swapped for framework-agnostic cache (likely cachetools.TTLCache) so it serves both apps
- Auth: still deferred per v1.0's D-04 pattern; `config/auth.yaml` stays gitignored

### Pending Todos

None yet — roadmap will populate phase-scoped todos.

### Blockers/Concerns

- Need to verify FastAPI + HTMX + Bootstrap 5 version pairing against 2026-04 stable releases (research will confirm)
- `app/services/ufs_service.py` Streamlit-coupled caching needs refactor before it can be shared between v1.0 and v2.0 — this is a v2.0 task (v1.0 stays untouched)
- Shared LLM adapter code is framework-agnostic but currently imported by v1.0 Streamlit pages — imports must stay backward-compatible

## Session Continuity

Last session: 2026-04-25T00:00:00.000Z
Stopped at: Milestone v2.0 started — requirements pending
Resume file: None
