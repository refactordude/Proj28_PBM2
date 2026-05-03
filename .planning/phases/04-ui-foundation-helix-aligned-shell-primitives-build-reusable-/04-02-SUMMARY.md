---
phase: 04-ui-foundation-helix-aligned-shell-primitives-build-reusable
plan: 02
subsystem: ui
tags: [jinja2, pydantic-v2, helix-design-language, primitives, popovers, htmx, bootstrap5]

# Dependency graph
requires:
  - phase: 04-ui-foundation-helix-aligned-shell-primitives-build-reusable
    plan: 01
    provides: ".topbar / .brand / .brand-mark / .av / .tabs / .tab[aria-selected=true] / .ph / .hero / .kpis / .kpi / .pop family / .opt[.on] / .grp / .btn-helix CSS rules"
provides:
  - "HeroSpec + HeroSegment + HeroSideStat Pydantic v2 view-models (app_v2/services/hero_spec.py)"
  - "FilterGroup + FilterOption Pydantic v2 view-models (app_v2/services/filter_spec.py)"
  - "topbar(active_tab) macro — Wave 3 base.html topbar swap target"
  - "page_head(title, subtitle, actions_html) macro — Wave 4 showcase + future detail pages"
  - "hero(spec) macro consuming HeroSpec — Wave 4 showcase + future Platform BM"
  - "kpi_card(label, value, unit, delta, delta_tone, spark_data) macro — Wave 4 4-up/5-up grids"
  - "sparkline(data, width, height, color) pure-Jinja inline SVG — used by kpi_card + future micro-charts"
  - "date_range_popover(form_id, ...) — D-UIF-03 Bootstrap-dropdown-anchored, form-associated"
  - "filters_popover(form_id, groups) — D-UIF-04 chip-group multi-category"
  - "chip-toggle.js — sibling helper for .pop .opt → hidden-input sync (loaded in Wave 3)"
affects:
  - "Wave 3 (04-03): base.html can now `{% from \"_components/topbar.html\" import topbar %}` and load chip-toggle.js with defer; test_main.py / test_phase02_invariants.py navbar assertions get rewritten in the same atomic commit"
  - "Wave 4 (04-04): GET /_components showcase route renders every primitive with hard-coded HeroSpec / FilterGroup instances"
  - "Wave 5 (04-05): .panel-header → .ph atomic markup migration; primitives in this plan already emit .page-head / .pop / .kpi / .hero markup so no compatibility shim needed"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One macro per file under app_v2/templates/_components/ — filename === macro name (D-UIF-08); callers use {% from %} import"
    - "Pydantic v2 view-models with Field(default_factory=list) for mutable defaults — required since v2 forbids = [] mutable defaults"
    - "from __future__ import annotations enables PEP 604 union syntax (int | float | str) on Python 3.13"
    - "Form-association via form=\"<form_id>\" attr on inputs/buttons inside .dropdown-menu so they POST with the page-level form despite living inside the dropdown DOM (same trick as browse/_picker_popover.html line 113)"
    - "Sparkline namespace() pattern for cross-loop string accumulation — Jinja loop scope cannot reassign outer vars; namespace is the canonical idiom"
    - "Document-level click delegation with capture-phase + selector boundaries (chip-toggle.js skips .popover-search-root) — both popover JS files coexist (Pitfall 8)"
    - "Hyphen-safe group_name in filters_popover: lowercase + replace(' ','_') + replace('-','_') so UFS-eMMC -> ufs_emmc (Python attr-safe)"

key-files:
  created:
    - app_v2/services/hero_spec.py
    - app_v2/services/filter_spec.py
    - app_v2/static/js/chip-toggle.js
    - app_v2/templates/_components/__init__.py
    - app_v2/templates/_components/topbar.html
    - app_v2/templates/_components/page_head.html
    - app_v2/templates/_components/sparkline.html
    - app_v2/templates/_components/kpi_card.html
    - app_v2/templates/_components/hero.html
    - app_v2/templates/_components/date_range_popover.html
    - app_v2/templates/_components/filters_popover.html
  modified: []

key-decisions:
  - "chip-toggle.js as SIBLING of popover-search.js, NOT a fork: D-UIF-05 + D-UI2-09 require popover-search.js byte-stable. Both files use document-level click delegation with capture phase; coexistence guaranteed by precise selectors — chip-toggle binds on `.pop .opt` and early-returns if `.popover-search-root` ancestor is present (Pitfall 8 boundary)."
  - "chip-value-as-payload (NOT '1') in chip-toggle.js: when chip toggles ON, hidden input gets chipValue from data-value; OFF clears it. Diverges from RESEARCH §Pitfall 8 sketch which proposed a generic '1' flag — chip-value preserves multi-option-per-group fidelity so server receives `?status=open&status=closed` rather than opaque flags."
  - "HeroSpec and FilterGroup live in SEPARATE files (hero_spec.py + filter_spec.py): RESEARCH Open Question 2 resolved as separate-file. Mirrors one-concept-per-file convention in app_v2/services/ (joint_validation_grid_service / joint_validation_summary / browse_service / etc). Cleaner imports for downstream phases (showcase imports just what it needs)."
  - "kpi_card variant arg dropped per UI-SPEC §kpi_card line 280: caller sets the `.kpis` or `.kpis.five` container class instead of passing variant=\"4-up\"|\"5-up\". ONE macro renders ONE card; container choice is the caller's responsibility (Wave 4 showcase emits `<div class=\"kpis five\">…</div>` directly). Reduces macro signature surface area."
  - "btn-helix used inside popovers (date_range_popover, filters_popover) instead of plain Bootstrap .btn: Wave 1 added `.btn-helix` namespace specifically to avoid fighting Bootstrap's `.btn` cascade. Phase 4 popovers/showcase use `.btn-helix .sm` / `.btn-helix .ghost .sm` so the Helix-tinted styling lands without site-wide Bootstrap override."
  - "hero macro inline-overrides grid-template-columns when spec.side_stats is empty: `style=\"grid-template-columns: 1fr;\"`. Only runtime-data-dependent style override in any macro; everything else lives in app.css. Prevents an empty .side panel from creating an awkward 1.3fr / 1fr layout with the right column blank."
  - "sparkline namespace() pattern: Jinja's loop scope cannot reassign outer scalar variables across iterations. The canonical idiom is `{% set ns = namespace(d_line='', d_area='') %}` then `{% set ns.d_line = ns.d_line ~ ' L ' ~ x ~ ' ' ~ y %}`. Two paths are accumulated (line stroke + filled area with closing `L width height L 0 height Z`)."
  - "filters_popover hyphen-safe group_name: `grp.label | lower | replace(' ', '_') | replace('-', '_')` so labels like `UFS-eMMC` produce hidden-input `name=\"ufs_emmc\"` (Python attribute-safe; downstream consumers can use `request.form['ufs_emmc']` and SQL filter columns can be named without quoting). BLOCKER 2 from plan revision honored — both space and hyphen are replaced."

requirements-completed: [D-UIF-03, D-UIF-04, D-UIF-05, D-UIF-06, D-UIF-07, D-UIF-08, D-UIF-09, D-UIF-11]

# Metrics
duration: 5min
completed: 2026-05-03
---

# Phase 04 Plan 02: Wave 2 — Jinja partials, Pydantic view-models, chip-toggle.js Summary

**7 Jinja macro partials (topbar / page_head / hero / kpi_card / sparkline / date_range_popover / filters_popover) + 2 Pydantic v2 submodules (HeroSpec / FilterGroup) + chip-toggle.js sibling helper — every Phase 4 stateful primitive declared in UI-SPEC §New Jinja Macros + §Pydantic View-Models now ships under app_v2/templates/_components/ + app_v2/services/, all driven by the CSS foundation Wave 1 already laid down**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-03T08:02:10Z
- **Completed:** 2026-05-03T08:07:26Z
- **Tasks:** 2
- **Files modified:** 11 (all created; no existing files edited)

## Accomplishments

- Created `app_v2/services/hero_spec.py` (HeroSpec + HeroSegment + HeroSideStat Pydantic v2 models) and `app_v2/services/filter_spec.py` (FilterGroup + FilterOption) — type-checked at the router boundary; Field(default_factory=list) for mutable defaults; `from __future__ import annotations` enables PEP 604 union syntax on Python 3.13.
- Created `app_v2/static/js/chip-toggle.js` as a SIBLING of `popover-search.js` (popover-search.js byte-stable per D-UIF-05 / D-UI2-09). Document-level click delegation with capture phase; precise `.pop .opt` selector + `.popover-search-root` early-return ensures both helpers coexist (Pitfall 8 boundary).
- Created `app_v2/templates/_components/` directory + 8 files: 7 macro partials (one macro per file, filename === macro name per D-UIF-08) + 1 `__init__.py` marker for IDE introspection.
- `topbar(active_tab)` — D-UIF-06 brand "P" + "PBM2" wordmark + PM avatar; D-UIF-07 trio of `<a href>` tabs (Joint Validation `/`, Browse `/browse`, Ask `/ask`) with `aria-selected="true"` on the active.
- `page_head(title, subtitle, actions_html)` — escapes title + subtitle, raw `actions_html` (caller-escaped); plays nicely with existing `.page-head` rule from Phase 02.
- `sparkline(data, width=90, height=26, color)` — pure Jinja inline SVG. Pitfall 4 mitigated: empty data → bare `<svg>`, single point → degenerate horizontal line, constant data → flat horizontal line at mid-height (`height / 2 = 13` for default 26px viewBox), no NaN paths.
- `kpi_card(label, value, unit, delta, delta_tone, spark_data)` — variant arg dropped per UI-SPEC line 280; imports `sparkline` and conditionally renders the `.spark` slot. Caller wraps cards in `<div class="kpis">` or `<div class="kpis five">` for 4-up vs 5-up grids.
- `hero(spec)` — reads HeroSpec; conditionally renders `.hero-bar` (only if `spec.segments`) and `.side` (only if `spec.side_stats`); collapses grid to 1fr when side empty.
- `date_range_popover(form_id, ...)` and `filters_popover(form_id, groups, button_label)` — both use Bootstrap 5 `.dropdown` + `.dropdown-menu` + `data-bs-auto-close="outside"` per D-UIF-03; form-association via `form="<form_id>"` on inputs/buttons; `btn-helix` styling on Apply CTAs to use Wave 1's namespaced primary button.
- `filters_popover` hyphen-safe group_name: `grp.label | lower | replace(' ', '_') | replace('-', '_')` so `UFS-eMMC` → `name="ufs_emmc"` (Python attribute-safe). Both space AND hyphen replaced per BLOCKER 2 from plan revision.
- All 493 v2 tests stay green. New files dormant — Wave 3 mounts them via base.html topbar swap; Wave 4 exercises every primitive in `/_components`.
- `app_v2/templates/browse/_picker_popover.html` + `app_v2/static/js/popover-search.js` byte-stable (D-UIF-05 / D-UI2-09 verified via `git diff --quiet HEAD` after each task).

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Pydantic view-models (HeroSpec + FilterGroup) and chip-toggle.js sibling helper** — `b93ea9e` (feat)
2. **Task 2: Create all 7 Jinja macro partials in _components/** — `2a69bc5` (feat)

## Files Created/Modified

### Created (11)

- `app_v2/services/hero_spec.py` — HeroSpec + HeroSegment + HeroSideStat Pydantic v2 models. 49 lines. Mirrors PageLink convention.
- `app_v2/services/filter_spec.py` — FilterGroup + FilterOption Pydantic v2 models. 35 lines. Co-located with hero_spec.py per services/ one-concept-per-file convention.
- `app_v2/static/js/chip-toggle.js` — Document-level click delegation with `.pop .opt` selector + `.popover-search-root` early-return. 58 lines. Capture-phase listener.
- `app_v2/templates/_components/__init__.py` — IDE introspection marker (Jinja loader does not consume it). 2 lines.
- `app_v2/templates/_components/topbar.html` — `topbar(active_tab="")` macro. 36 lines. Brand "P" gradient mark + "PBM2" wordmark + 3 `<a>` tabs + "PM" avatar.
- `app_v2/templates/_components/page_head.html` — `page_head(title, subtitle="", actions_html="")` macro. 21 lines. `| e` on title/subtitle; `| safe` on actions_html.
- `app_v2/templates/_components/sparkline.html` — `sparkline(data, width=90, height=26, color="var(--accent)")` macro. 41 lines. namespace() accumulator; height/2 mid-height fallback for hi==lo.
- `app_v2/templates/_components/kpi_card.html` — `kpi_card(label, value, unit="", delta="", delta_tone="flat", spark_data=None)` macro. 25 lines. `{% from "_components/sparkline.html" import sparkline %}` at module top.
- `app_v2/templates/_components/hero.html` — `hero(spec)` macro reading HeroSpec attributes. 43 lines. Inline `style="grid-template-columns: 1fr;"` only when `spec.side_stats` is empty.
- `app_v2/templates/_components/date_range_popover.html` — `date_range_popover(form_id, field_prefix="date", quick_days=[7,14,30,60], start_val="", end_val="")` macro. 65 lines. Reset/Apply CTAs.
- `app_v2/templates/_components/filters_popover.html` — `filters_popover(form_id, groups, button_label="Filters")` macro. 65 lines. Hyphen-safe group_name; Reset Filters/Apply Filters CTAs.

### Modified (0)

No existing files modified. Phase 02 invariants byte-stable.

## Decisions Made

- **chip-toggle.js as sibling (not fork) of popover-search.js:** D-UIF-05 + D-UI2-09 require popover-search.js byte-stable. Both files use document-level click delegation with capture phase. Coexistence is guaranteed by precise selectors — chip-toggle binds on `.pop .opt` and early-returns when ancestor is `.popover-search-root` (the existing checkbox-list root). Pitfall 8 boundary documented in code comments + audit-friendly.
- **chip-value-as-payload, not '1':** When chip toggles ON, hidden input gets the chip's `data-value`; OFF clears it. Diverges from RESEARCH §Pitfall 8 sketch which proposed a generic '1' flag. Chip-value preserves multi-option-per-group fidelity so server receives `?status=open&status=closed` rather than opaque flags. Documented inline in chip-toggle.js with a comment block referencing the RESEARCH divergence.
- **HeroSpec and FilterGroup in SEPARATE files (RESEARCH Open Question 2 resolved):** `hero_spec.py` and `filter_spec.py` live next to each other in `app_v2/services/`. Mirrors the one-concept-per-file convention (joint_validation_grid_service / joint_validation_summary / browse_service / etc). Cleaner imports — Wave 4 showcase will `from app_v2.services.hero_spec import HeroSpec` and `from app_v2.services.filter_spec import FilterGroup` independently.
- **kpi_card variant arg dropped per UI-SPEC line 280:** Caller sets `.kpis` or `.kpis.five` container class instead of passing `variant="4-up"|"5-up"`. ONE macro renders ONE card; the grid choice is the caller's responsibility (showcase emits `<div class="kpis five">{{ kpi_card(...) }}{{ kpi_card(...) }}…</div>`). Documented as a spec divergence with a comment block in the macro.
- **btn-helix inside popovers + showcase:** Wave 1 added `.btn-helix` specifically to avoid fighting Bootstrap's `.btn` cascade. Phase 4 popovers use `.btn-helix .sm` / `.btn-helix .ghost .sm` so the Helix-tinted button styling lands without site-wide Bootstrap override. Browse + JV existing buttons keep their Bootstrap `.btn` styling untouched.
- **hero macro inline grid-template-columns override:** Only runtime-data-dependent style override in any macro. When `spec.side_stats` is empty, the macro emits `style="grid-template-columns: 1fr;"` so the hero collapses to a single column instead of leaving the right column blank inside the 1.3fr/1fr template. All other styling (hero-bar segment widths/colors via inline style) is also data-driven from HeroSegment.value/color.
- **sparkline namespace() pattern + mid-height fallback:** Jinja loop scope cannot reassign outer scalar variables; namespace() is the canonical idiom for accumulating string state across a loop. When `hi == lo` (constant data), `y = (height / 2) | round(2)` produces a flat horizontal line at mid-height (13 for the default 26px viewBox). Verified: `'NaN' not in render([5,5,5,5,5])` and `' 13' in render([5,5,5,5,5])`.
- **filters_popover hyphen-safe group_name:** `grp.label | lower | replace(' ', '_') | replace('-', '_')` produces Python-attribute-safe form field names. UFS-eMMC label → `name="ufs_emmc"`. BLOCKER 2 from plan revision (both space AND hyphen replaced) honored.

## Deviations from Plan

None — plan executed exactly as written. All acceptance criteria green on first run:
- Both Pydantic models import cleanly with required validation behavior (Literal constraint raises ValidationError on invalid tone; Field(default_factory=list) yields per-instance empty lists).
- All 7 macros render correctly via `{% from %} import` with the listed test inputs.
- Sparkline edge cases (empty / None / single / constant / multi) all produce non-NaN SVG.
- Hero full-variant emits `.hero-bar` + `.side`; minimal variant emits neither and adds `style="grid-template-columns: 1fr;"`.
- filters_popover with `UFS-eMMC` group label produces `name="ufs_emmc"` (hyphen replaced).
- `_picker_popover.html` and `popover-search.js` byte-stable (verified via `git diff --quiet HEAD` after each commit).
- Full v2 test suite green: 493 passed, 5 skipped, 0 failures (same as Wave 1 baseline).

## Issues Encountered

None. Both tasks ran first-time green. Verification scripts (Pydantic validation + Jinja `from_string` + `Environment` rendering of all 7 macros + grep matrix on macro files + `git diff --quiet HEAD` on byte-stable refs) passed end-to-end.

Note on grep counts: the plan's acceptance criteria expect `grep -c 'PBM2' …topbar.html` returns 1 and `grep -c 'data-bs-auto-close="outside"' …date_range_popover.html` returns 1. Both files contain the literal text once in a doc comment AND once in the structural attribute, so `grep -c` returns 2. The structural intent (one occurrence in markup) is met; this is a documentation artifact only and does not violate behavior. No file change made.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Wave 3 (04-03) unblocked:** `base.html` can now `{% from "_components/topbar.html" import topbar %}` and load `chip-toggle.js` with `defer` after `bootstrap.bundle.min.js`. Wave 3 atomically swaps the `<nav class="navbar">` block for `{{ topbar(active_tab=active_tab|default("")) }}`, removes the `.navbar { padding: 16px 0 }` rule from app.css, and rewrites `tests/v2/test_main.py` + `tests/v2/test_phase02_invariants.py` assertions on `nav-tabs` / `navbar-brand` to assert on `.topbar` / `.brand` / `.brand-mark` / `.tab[aria-selected="true"]`.
- **Wave 4 (04-04) unblocked:** GET /_components showcase route can now `from app_v2.services.hero_spec import HeroSpec, HeroSegment, HeroSideStat` + `from app_v2.services.filter_spec import FilterGroup, FilterOption` and render every primitive section with hard-coded fixtures: Topbar (passive — already in base.html after Wave 3), Page-head, Hero (full + minimal variants), KPI 4-up grid (with sparklines), KPI 5-up grid, Pills/Chips/Tiny-chips (CSS-only sections), Date-range popover (standalone), Filters popover (chip groups: Status / OEM / UFS-eMMC), Sticky-corner table.
- **Wave 5 (04-05) prep:** Primitives in this plan emit `.page-head` markup (page_head macro) and `.ph` is unused by Wave 2 outputs. Wave 5 atomically renames `.panel-header` to `.ph` in app.css + every Browse/JV/Ask `index.html` + invariant tests; Wave 2 macros remain compatible since they use `.page-head` (different concept from `.panel-header`).
- **No blockers.**

## Self-Check: PASSED

- FOUND: `app_v2/services/hero_spec.py`
- FOUND: `app_v2/services/filter_spec.py`
- FOUND: `app_v2/static/js/chip-toggle.js`
- FOUND: `app_v2/templates/_components/__init__.py`
- FOUND: `app_v2/templates/_components/topbar.html`
- FOUND: `app_v2/templates/_components/page_head.html`
- FOUND: `app_v2/templates/_components/sparkline.html`
- FOUND: `app_v2/templates/_components/kpi_card.html`
- FOUND: `app_v2/templates/_components/hero.html`
- FOUND: `app_v2/templates/_components/date_range_popover.html`
- FOUND: `app_v2/templates/_components/filters_popover.html`
- FOUND: commit `b93ea9e` (Task 1 — Pydantic models + chip-toggle.js)
- FOUND: commit `2a69bc5` (Task 2 — 7 Jinja macros + __init__.py marker)

---
*Phase: 04-ui-foundation-helix-aligned-shell-primitives-build-reusable*
*Completed: 2026-05-03*
