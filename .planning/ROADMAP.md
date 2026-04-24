# Roadmap: PBM2

## Milestones

- ✅ **v1.0 MVP** — Phases 1-2 (shipped 2026-04-24) — see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- 🔄 **v2.0 Bootstrap Shell** — Phases 1-5 (active)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-2) — SHIPPED 2026-04-24</summary>

- [x] Phase 1: Foundation + Browsing (7/7 plans) — completed 2026-04-23
- [x] Phase 2: NL Agent Layer (6/6 plans) — completed 2026-04-24

Full archive: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
Requirements archive: [milestones/v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)
Audit: [milestones/v1.0-MILESTONE-AUDIT.md](milestones/v1.0-MILESTONE-AUDIT.md)

</details>

### v2.0 Bootstrap Shell — Active

- [ ] **Phase 1: Pre-work + Foundation** - v1.0 refactors (ufs_service, nl_service) + FastAPI shell, static vendor, cache layer, deps
- [ ] **Phase 2: Overview Tab + Filters** - Curated platform list, add/remove, HTMX-swapped faceted filters
- [ ] **Phase 3: Content Pages + AI Summary** - Per-platform markdown CRUD, safe rendering, in-place LLM summary
- [ ] **Phase 4: Browse Tab Port** - Pivot grid, swap-axes, row/col caps, Excel/CSV export under Bootstrap
- [ ] **Phase 5: Ask Tab Port** - NL agent, two-turn confirmation, history, LLM backend selector, safety harness

## Phase Details

### Phase 1: Pre-work + Foundation
**Goal**: The FastAPI v2.0 app starts cleanly alongside v1.0 Streamlit, serves the Bootstrap shell at `/`, and shares v1.0 service code without Streamlit coupling. All 171 v1.0 tests still pass. No visible UI features — only the structural plumbing every subsequent phase depends on.
**Depends on**: Nothing (first phase of v2.0)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, INFRA-07, INFRA-08, INFRA-09
**Success Criteria** (what must be TRUE):
  1. `uvicorn app_v2.main:app` starts without error; `GET /` returns HTTP 200 with Bootstrap nav and the three tabs (Overview / Browse / Ask) visible
  2. `pytest` still passes all 171 v1.0 tests after the ufs_service and nl_service refactors — no regressions
  3. `python -c "import app.services.ufs_service"` in a plain Python process (no Streamlit server running) raises no exception
  4. Bootstrap 5, HTMX, and Bootstrap Icons are served from `/static/vendor/` (not CDN-dependent); the page renders correctly with network access blocked
  5. A validation error on any HTMX form (4xx/5xx response) shows a visible error message in the page — not silently discarded
**Plans**: 4 plans
- [x] 01-01-PLAN.md — Dependencies + ufs_service _core extraction (INFRA-06, INFRA-09)
- [x] 01-02-PLAN.md — nl_service extraction from ask.py (INFRA-07)
- [x] 01-03-PLAN.md — FastAPI shell + vendored static assets + base template (INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05)
- [ ] 01-04-PLAN.md — app_v2/services/cache.py TTLCache wrappers (INFRA-08)

### Phase 2: Overview Tab + Filters
**Goal**: Users can build and maintain a curated watchlist of platforms from the live database, filter it by Brand/SoC/Year and content status, and see each platform with its metadata badges — all without a full page reload.
**Depends on**: Phase 1
**Requirements**: OVERVIEW-01, OVERVIEW-02, OVERVIEW-03, OVERVIEW-04, OVERVIEW-05, OVERVIEW-06, FILTER-01, FILTER-02, FILTER-03, FILTER-04
**Success Criteria** (what must be TRUE):
  1. User can type a partial platform name in the typeahead input and select a platform to add it to the curated list; the list updates in-place without a page reload
  2. User can remove a platform via the × button; after confirmation the row disappears from the list without a page reload; the list persists after browser refresh
  3. User can filter the list by Brand, SoC, or Year (or any combination); matching entities display and non-matching entities disappear without leaving the page; "Clear all" restores the full list
  4. When the curated list is empty (first run or all removed), an explicit "Add your first platform" prompt appears — not a blank area
  5. The active-filter badge shows the count of applied filters; the entity list reflects filters immediately on dropdown change
**Plans**: TBD
**UI hint**: yes

### Phase 3: Content Pages + AI Summary
**Goal**: Each curated platform can have a markdown content page that users can add, edit, preview, and delete through the web UI. When a content page exists, a single-click AI Summary button fetches a concise LLM-generated summary in-place, with caching and graceful error handling.
**Depends on**: Phase 1, Phase 2
**Requirements**: CONTENT-01, CONTENT-02, CONTENT-03, CONTENT-04, CONTENT-05, CONTENT-06, CONTENT-07, CONTENT-08, SUMMARY-01, SUMMARY-02, SUMMARY-03, SUMMARY-04, SUMMARY-05, SUMMARY-06, SUMMARY-07
**Success Criteria** (what must be TRUE):
  1. Navigating to `/platforms/<id>` shows the rendered markdown when a content file exists, or an explicit "Add Content" button when it does not
  2. A user can edit a platform's markdown, preview it (without saving), save it, and cancel — all without leaving the platform page or performing a full page reload; the saved content persists after browser refresh
  3. Deleting a content page (after browser confirmation) returns the page to the empty state; no `.md` file remains on disk
  4. The AI Summary button on an Overview entity is enabled only when a content file exists; clicking it swaps a concise summary in-place within 30 seconds; the loading spinner is visible during the request
  5. If the LLM call fails, a Bootstrap alert with the failure reason and a Retry button appears in the summary area — never a blank or a spinner that never resolves
  6. A second click on AI Summary (before content has changed) returns the cached result instantly; the Regenerate button bypasses the cache and triggers a fresh LLM call
**Plans**: TBD
**UI hint**: yes

### Phase 4: Browse Tab Port
**Goal**: Users can access the full v1.0 pivot-grid experience (platform × parameter wide-form table, swap-axes, row/col caps, export) under the new Bootstrap shell via the Browse tab — with shareable URLs and no full page reload on filter changes.
**Depends on**: Phase 1
**Requirements**: BROWSE-V2-01, BROWSE-V2-02, BROWSE-V2-03, BROWSE-V2-04, BROWSE-V2-05
**Success Criteria** (what must be TRUE):
  1. User can select platforms and parameters, and the pivot grid updates in the Browse tab without a full page reload; the sticky header remains visible while scrolling
  2. The 30-column cap warning and 200-row cap warning appear when the respective limits are reached — matching v1.0 behavior exactly
  3. User can download the current pivot grid as Excel (.xlsx) or CSV; the export reflects the active filter state and respects the row/col caps
  4. A Browse URL with query params (e.g. `?platforms=...&params=...&swap=1`) renders the correct filtered pivot grid when opened directly — the link is shareable
**Plans**: TBD
**UI hint**: yes

### Phase 5: Ask Tab Port
**Goal**: Users can ask natural-language questions about the UFS database through the Ask tab, go through the two-turn parameter-confirmation flow, see results with the LLM summary and SQL expander, switch between Ollama and OpenAI backends, and rely on the full v1.0 safety harness — all under the new Bootstrap shell.
**Depends on**: Phase 1, Phase 3
**Requirements**: ASK-V2-01, ASK-V2-02, ASK-V2-03, ASK-V2-04, ASK-V2-05, ASK-V2-06, ASK-V2-07, ASK-V2-08
**Success Criteria** (what must be TRUE):
  1. User can type a natural-language question, submit it, and receive a result table with an LLM summary and a collapsible SQL block — or a parameter-confirmation step when the agent needs clarification
  2. The two-turn confirmation flow presents pre-checked candidate parameters; user can modify the selection and click "Run Query" to execute with the confirmed params; the correct SQL runs against the DB
  3. Switching the backend selector to OpenAI shows the data-sensitivity alert banner; the selected backend persists across page refreshes (cookie); switching back to Ollama clears the banner
  4. The 8 curated starter prompts appear when no question has been asked; clicking one fills the textarea but does not auto-submit
  5. A question that would exceed the step-cap or timeout shows the red abort banner with the exact v1.0 copy; a question designed to SELECT from a non-allowed table (e.g. `mysql.user`) is rejected before execution
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Pre-work + Foundation | v2.0 | 2/4 | In Progress|  |
| 2. Overview Tab + Filters | v2.0 | 0/? | Not started | - |
| 3. Content Pages + AI Summary | v2.0 | 0/? | Not started | - |
| 4. Browse Tab Port | v2.0 | 0/? | Not started | - |
| 5. Ask Tab Port | v2.0 | 0/? | Not started | - |
