---
phase: 04-ui-foundation-helix-aligned-shell-primitives-build-reusable
plan: 04
subsystem: ui
tags: [jinja, htmx, fastapi, bootstrap5, helix, showcase]

requires:
  - phase: 04-01
    provides: Helix primitive CSS classes (.topbar, .ph, .kpi, .hero, .pop, .table-sticky-corner, .btn-helix, .chip, .tiny-chip)
  - phase: 04-02
    provides: 7 Jinja macros + HeroSpec/FilterGroup Pydantic v2 models + chip-toggle.js
  - phase: 04-03
    provides: Atomic shell swap (base.html topbar) + chip-toggle.js loaded after Bootstrap
provides:
  - GET /_components always-on showcase route (D-UIF-02)
  - showcase.html exercising every primitive: topbar (inherited), page-head, hero (full + minimal), KPI 4-up + 5-up, sparkline edge cases, all chip variants, both popovers, sticky-corner table
  - test_phase04_uif_invariants.py — pins NEW class names + key dimensions; forward-compatible with Wave 5 .ph consolidation
  - test_phase04_uif_components.py — renders /_components, asserts every primitive (includes BLOCKER 2 hyphen-safe assertion: name="ufs_emmc" present, name="ufs-emmc" absent)
  - test_phase04_uif_hero_spec.py — Pydantic v2 unit tests on HeroSpec including sparkline edge cases (empty/single/constant data, NaN-free)
affects: ["Phase 04-05", "downstream phases consuming /_components for design reference"]

tech-stack:
  added: []
  patterns:
    - "Always-on showcase route (no feature flag) — design system stays canonical and testable"
    - "Forward-compatible invariant tests — assert D-UI2-12 declarations under either selector to survive Wave 5 consolidation"

key-files:
  created:
    - app_v2/routers/components.py
    - app_v2/templates/_components/showcase.html
    - tests/v2/test_phase04_uif_invariants.py
    - tests/v2/test_phase04_uif_components.py
    - tests/v2/test_phase04_uif_hero_spec.py
  modified:
    - app_v2/main.py

key-decisions:
  - "GET /_components mounted always-on per D-UIF-02 — no feature flag, no env gate"
  - "Router registration follows main.py:189-197 load-order convention (root last); not alphabetical"
  - "Test names use test_phase04_uif_*.py prefix to avoid collision with v2.0 milestone's test_phase04_*.py"
  - "Showcase exercises FilterGroup(label='UFS-eMMC') explicitly to validate D-UIF-04 hyphen-replacement code path"

patterns-established:
  - "Server-rendered SVG sparkline with explicit edge-case handling (empty/single/constant/NaN-free) — D-UIF-09"
  - "Showcase as living design contract — `/_components` is the canonical reference for downstream phases"

requirements-completed: ["D-UIF-02", "D-UIF-03", "D-UIF-04", "D-UIF-06", "D-UIF-07", "D-UIF-08", "D-UIF-09", "D-UIF-10", "D-UIF-11"]

duration: ~30min (estimated; spread over a usage-limit boundary)
completed: 2026-05-03
---

# Phase 04: Wave 4 — Showcase Route + Invariant Tests

**Mounted always-on `/_components` showcase route exercising every Helix primitive, plus 50 invariant tests pinning class names, dimensions, sparkline edge cases, and the BLOCKER 2 hyphen-safe filter-group assertion.**

## Performance

- **Duration:** ~30 min (split across a usage-limit boundary; resumed inline)
- **Started:** 2026-05-03T08:08Z
- **Completed:** 2026-05-03T (after limit reset)
- **Tasks:** 2 of 2 complete
- **Files modified:** 1; **Files created:** 5

## Accomplishments

- `GET /_components` returns 200 with showcase markup exercising topbar (inherited), page-head, hero (full + minimal), KPI 4-up + 5-up grids with sparklines, every chip / pill / tiny-chip variant, date-range popover, filters popover (chip groups including UFS-eMMC), sticky-corner table.
- 50 new tests pass; full v2 suite at 541 passed / 5 skipped / 0 failures (no regression from the 491 baseline post-Wave 3).
- Invariant tests are forward-compatible with Wave 5 consolidation: `.ph` rule check accepts D-UI2-12 declarations under either `.panel-header .panel-title` (pre-Wave-5) OR `.ph .panel-title` (post-Wave-5).

## Task Commits

1. **Task 1: Mount /_components route + showcase template** — `ee7a80b` (feat)
2. **Task 2: Three Phase 04 UIF invariant test files** — `80fae92` (test)

_Plan metadata commit pending (this SUMMARY)._

## Files Created/Modified

- `app_v2/routers/components.py` — always-on showcase router
- `app_v2/templates/_components/showcase.html` — renders every primitive with realistic sample data
- `app_v2/main.py` — `from app_v2.routers import components` + `app.include_router(components.router)` per load-order convention
- `tests/v2/test_phase04_uif_invariants.py` — 273 lines pinning class names + dimensions
- `tests/v2/test_phase04_uif_components.py` — 249 lines rendering showcase + asserting all primitives
- `tests/v2/test_phase04_uif_hero_spec.py` — 141 lines Pydantic v2 model unit tests + sparkline edge-case assertions

## Notes

- Wave 4 hit a usage-limit boundary mid-execution. Task 1 (route + showcase) committed before the limit; Task 2 (test files) was completed inline by the orchestrator after the limit reset, with full v2 test suite re-run to confirm no regression.
- D-UIF-04 hyphen-safe assertion landed: showcase renders `name="ufs_emmc"` (underscore form) and never `name="ufs-emmc"` (hyphen form).
- Wave 5 (atomic `.panel-header` → `.ph` migration) is the only remaining wave for Phase 04.
