# Roadmap: PBM2

## Overview

PBM2 ships in two phases that respect the core value ordering: browsing must work before NL. Phase 1 delivers a fully standalone product — auth, settings, data service, and browse UI — so non-SQL users can find, compare, and export UFS platform data without writing a line of SQL. Phase 2 layers the NL agent on top of that solid foundation, adding natural-language query, LLM summary, session history, and the full safety harness for cloud LLM use. Each phase delivers a coherent, testable capability; Phase 2 is never a prerequisite for Phase 1's value.

## Phases

**Phase Numbering:**
- Integer phases (1, 2): Planned milestone work
- Decimal phases (1.1, etc.): Urgent insertions if needed

- [x] **Phase 1: Foundation + Browsing** - Deployable read-only data browser: auth, settings, data service, pivot grid, charts, export (completed 2026-04-23)
- [ ] **Phase 2: NL Agent Layer** - Natural-language query on top of the Phase 1 service layer, with full safety harness

## Phase Details

### Phase 1: Foundation + Browsing
**Goal**: Users can securely browse, filter, visualize, and export UFS parameter data without writing SQL — and the app is safely deployable to the team intranet
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, FOUND-06, FOUND-07, FOUND-08, DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, BROWSE-01, BROWSE-02, BROWSE-03, BROWSE-04, BROWSE-05, BROWSE-06, BROWSE-07, BROWSE-08, BROWSE-09, VIZ-01, VIZ-02, EXPORT-01, EXPORT-02, SETUP-01, SETUP-02, SETUP-03, SAFE-01
**Success Criteria** (what must be TRUE):
  1. App runs on the team intranet without authentication (auth deferred to a pre-deployment phase per CONTEXT D-04). `config/auth.yaml` and `.env` are gitignored so the scaffold does not leak demo credentials when auth is turned on later.
  2. User can configure DB and LLM connection entries from the Settings page, test each connection, and see a pass/fail result — before touching any data browser
  3. User can select one or more platforms and one or more parameters, view the result as a sortable wide-form pivot grid (platforms x parameters), and see a row-count indicator confirming how many platforms and parameters are displayed
  4. User can chart any numeric parameter column as a bar, line, or scatter Plotly chart, and download the current result as an Excel or CSV file
  5. User's filter selections persist across widget interactions, and the filter state can be copied as a shareable URL that reproduces the same view for a teammate
**Plans**: TBD
**UI hint**: yes

### Phase 2: NL Agent Layer
**Goal**: Users can ask natural-language questions about the database and receive a result table plus a plain-text LLM summary, with the full agent safety harness active and visible
**Depends on**: Phase 1
**Requirements**: NL-01, NL-02, NL-03, NL-04, NL-05, NL-06, NL-07, NL-08, NL-09, NL-10, SAFE-02, SAFE-03, SAFE-04, SAFE-05, SAFE-06, ONBD-01, ONBD-02
**Success Criteria** (what must be TRUE):
  1. User types a natural-language question, the agent proposes candidate parameters from the real DB for confirmation, and then returns a result table and a plain-text LLM summary
  2. User can see the LLM-generated SQL in a collapsed expander, click Regenerate to re-run with a fresh LLM call, and see their session question history in a history panel
  3. User can switch between Ollama (default) and OpenAI backends from the sidebar; switching to OpenAI shows a data-sensitivity warning before the first request of the session
  4. The agent correctly handles all three core question shapes (lookup-one-platform, compare-across-platforms, filter-platforms-by-value) and aborts cleanly with a user-visible message if the step cap or timeout is exceeded
  5. User sees a starter-prompt gallery of 6-10 curated questions; clicking a prompt fills the NL input and is immediately runnable
**Plans**: 6 plans
**Plan list**:
- [ ] 02-01-PLAN.md — Deps install (nest-asyncio) + build_pydantic_model factory + sidebar radio activation (NL-07, NL-08)
- [ ] 02-02-PLAN.md — Pure-function safety primitives: validate_sql, inject_limit, scrub_paths, extract_json (SAFE-02, SAFE-03, SAFE-04 timeout, SAFE-06, NL-09)
- [ ] 02-03-PLAN.md — PydanticAI Agent core: types, run_sql tool, run_agent runner (NL-06, SAFE-04 step-cap, SAFE-05)
- [ ] 02-04-PLAN.md — Ask page: title, history, question input, answer zone, sensitivity warning, abort banner, gallery scaffold (NL-01, NL-02, NL-03, NL-04, NL-10)
- [ ] 02-05-PLAN.md — NL-05 param confirmation multiselect + Run Query second-turn flow (NL-05)
- [ ] 02-06-PLAN.md — Starter prompt gallery YAML loader + 8 curated prompts (ONBD-01, ONBD-02)
**Needs research**: yes
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation + Browsing | 7/7 | Complete   | 2026-04-23 |
| 2. NL Agent Layer | 0/6 | Not started | - |
