# Roadmap: PBM2

## Milestones

- ✅ **v1.0 MVP** — Phases 1-2 (shipped 2026-04-24) — see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- ✅ **v2.0 Bootstrap Shell** — Phases 1-6 (shipped 2026-04-29) — see [milestones/v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md)
- 📋 **v2.1+** — TBD (run `/gsd-new-milestone` to define next milestone)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-2) — SHIPPED 2026-04-24</summary>

- [x] Phase 1: Foundation + Browsing (7/7 plans) — completed 2026-04-23
- [x] Phase 2: NL Agent Layer (6/6 plans) — completed 2026-04-24

Full archive: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
Requirements archive: [milestones/v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)
Audit: [milestones/v1.0-MILESTONE-AUDIT.md](milestones/v1.0-MILESTONE-AUDIT.md)

</details>

<details>
<summary>✅ v2.0 Bootstrap Shell (Phases 1-6) — SHIPPED 2026-04-29</summary>

- [x] Phase 1: Pre-work + Foundation (4/4 plans) — completed 2026-04-24
- [x] Phase 2: Overview Tab + Filters (3/3 plans) — completed 2026-04-25
- [x] Phase 3: Content Pages + AI Summary (4/4 plans) — completed 2026-04-26
- [x] Phase 4: Browse Tab Port (7/7 plans) — completed 2026-04-28
- [x] Phase 5: Overview Tab Redesign (6/6 plans) — completed 2026-04-28
- [x] Phase 6: Ask Tab Port (6/6 plans) — completed 2026-04-29

Full archive: [milestones/v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md)
Requirements archive: [milestones/v2.0-REQUIREMENTS.md](milestones/v2.0-REQUIREMENTS.md)
Audit: [milestones/v2.0-MILESTONE-AUDIT.md](milestones/v2.0-MILESTONE-AUDIT.md)

</details>

## Progress

| Milestone | Phases | Plans | Status | Shipped |
|-----------|--------|-------|--------|---------|
| v1.0 MVP | 2 | 13 | ✅ Shipped | 2026-04-24 |
| v2.0 Bootstrap Shell | 6 | 30 | ✅ Shipped | 2026-04-29 |

## Next Milestone

Run `/gsd-new-milestone` to plan the next iteration:
- Discovery: what user need / problem area to address next
- Research: explore relevant patterns + tech in scope
- Requirements: fresh REQUIREMENTS.md scoped to milestone
- Roadmap: fresh phase list under a new milestone heading

### Phase 1: Overview Tab: Auto-discover Platforms from HTML Files

**Goal:** Replace the Overview tab's curated-Platform listing with auto-discovered Joint Validation rows parsed from `content/joint_validation/<numeric_id>/index.html` (BeautifulSoup4); add `/joint_validation/<id>` detail page (properties table + iframe sandbox of the Confluence export); reuse the Phase 5 grid/filter/sort + AI Summary modal patterns; delete the Platform-curated yaml + supporting code paths (D-JV-01..D-JV-17 locked in 01-CONTEXT.md).
**Requirements**: D-JV-01, D-JV-02, D-JV-03, D-JV-04, D-JV-05, D-JV-06, D-JV-07, D-JV-08, D-JV-09, D-JV-10, D-JV-11, D-JV-12, D-JV-13, D-JV-14, D-JV-15, D-JV-16, D-JV-17
**Depends on:** v2.0 Phase 5 (Overview Redesign — patterns reused)
**Plans:** 6 plans

Plans:
- [x] 01-01-PLAN.md — Add beautifulsoup4+lxml deps; parameterize summary partials with entity_id+summary_url
- [x] 01-02-PLAN.md — BS4 parser + discovery store + grid_service view-model + tests + fixtures
- [x] 01-03-PLAN.md — JV summary shim (D-JV-16 _strip_to_text + JV prompt + cache discriminator); refactor summary_service helper
- [x] 01-04-PLAN.md — Rewrite routers/overview.py for JV listing; add routers/joint_validation.py (detail + summary); StaticFiles mount in main.py
- [x] 01-05-PLAN.md — Rewrite templates/overview/{index,_grid,_filter_bar}.html; add templates/joint_validation/detail.html; flip nav label
- [ ] 01-06-PLAN.md — Delete obsolete Phase 5 Platform-curated files (config/overview.yaml, overview_store.py, overview_filter.py, overview_grid_service.py + their tests + test_phase05_invariants.py + test_overview_routes.py); add test_joint_validation_routes.py + test_joint_validation_invariants.py
