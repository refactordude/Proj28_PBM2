# Phase 4: UI Foundation — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `04-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-05-03
**Phase:** 04-ui-foundation-helix-aligned-shell-primitives-build-reusable
**Areas discussed:** Adoption boundary, Showcase / demo page, Popover interaction model, Topbar visual richness, Picker reconciliation, Component pattern, Sparkline tech, Sticky-corner table scope, Hero data contract

---

## Gray-area selection (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| Adoption boundary | Primitives-only vs include migration | ✓ |
| Showcase / demo page | Where it lives + how thorough | ✓ |
| Popover interaction model | Bootstrap dropdown vs HTMX form vs details/summary | ✓ |
| Topbar visual richness | How much of the Helix topbar to adopt | ✓ |

**User picked:** all four.

---

## Adoption boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Primitives + showcase only | Existing pages untouched; downstream phases migrate | |
| Primitives + migrate global shell only | Topbar/page-head migrate; per-page panels stay | |
| Primitives + migrate everything | Topbar + page-head + Browse/JV/Ask panel headers all migrate | ✓ |
| CSS-only, no Jinja partials yet | Class system only; partials deferred | |

**User's choice:** Primitives + migrate everything.
**Notes:** Two later refinements narrowed migration: D-UIF-05 keeps `_picker_popover.html` byte-stable (Browse filter row not retrofitted), D-UIF-10 keeps Browse pivot's sticky-thead-only behavior (sticky-corner class shipped + showcased only). Net: global shell + page-head + `.panel-header → .ph` migrate everywhere; per-surface filter rows and pivots stay where shipped contracts already lock them.

---

## Showcase / demo page

| Option | Description | Selected |
|--------|-------------|----------|
| Full /_components showcase route | Every primitive with sample data on one sectioned page | ✓ |
| Showcase route, dev-only | Same content, dev/env-flag gated | |
| Static showcase page (HTML file under static/) | No router | |
| No showcase — retrofit pages serve as demo | Skip the route | |

**User's choice:** Full /_components showcase route.
**Notes:** Always-on, not dev-gated. Acts as live design reference for downstream phases and as the locus for invariant tests.

---

## Popover interaction model

| Option | Description | Selected |
|--------|-------------|----------|
| Bootstrap dropdown, mirroring Browse picker | Reuse already-tested pattern; HX-Push-Url round-trip | ✓ |
| HTMX-swap server form, no dropdown | New pattern; click-outside needs custom JS | |
| `<details>`/`<summary>` + form (no JS framework) | Pure HTML; loses floating-popover positioning | |
| Mixed — date-range Bootstrap dropdown, filters reuse `_picker_popover.html` | Smallest delta but creates pattern split | |

**User's choice:** Bootstrap dropdown, mirroring Browse picker.
**Notes:** Both new popovers (date-range, filters chip-group) follow this pattern. May extend or duplicate `popover-search.js` for chip-toggle behavior — researcher decides.

---

## Topbar visual richness

| Option | Description | Selected |
|--------|-------------|----------|
| Full Helix topbar | Brand-mark + wordmark + tabs + avatar slot | ✓ |
| Brand-mark + tabs only | No avatar/counts/env pill | |
| Restyle current navbar to .topbar/.tabs class names | Keep current shape; rename classes only | |
| Full topbar + tab counts wired to live data | Adds nav_counts dict contract on every router | |

**User's choice:** Full Helix topbar.
**Notes:** Brand-mark renders "P" (not Helix's "H"); wordmark "PBM2"; static "PM" avatar placeholder. NO env pill, NO notification bell, NO live tab counts in v1. Tabs roster stays Joint Validation / Browse / Ask.

---

## Continuation check #1

| Option | Description | Selected |
|--------|-------------|----------|
| More questions | Discuss the 5 open follow-ups | ✓ |
| I'm ready for context | Treat follow-ups as Claude's Discretion | |

**User's choice:** More questions.

---

## Picker-popover reconciliation

| Option | Description | Selected |
|--------|-------------|----------|
| Two distinct primitives, both shipped | `_picker_popover.html` byte-stable + new `filters_popover.html` chip-group | |
| Unify — retire `_picker_popover.html`, port everyone to chip groups | Breaks D-UI2-09 byte-stability | |
| Unify the other way — chip-group is a styling variant of `_picker_popover` | Macro signature grows | |
| Ship `filters_popover.html` only; defer Browse migration to a follow-up | Walks back part of "migrate everything" for Browse filter row | ✓ |

**User's choice:** Ship `filters_popover.html` only; defer Browse migration to a follow-up.
**Notes:** Locks D-UIF-04 (new chip-group primitive) and D-UIF-05 (`_picker_popover.html` byte-stable). Browse filter row visually unchanged after Phase 4.

---

## Component pattern (macros vs includes)

| Option | Description | Selected |
|--------|-------------|----------|
| Macros for stateful primitives, includes for static | Mixed convention matching existing `_picker_popover.html` | ✓ |
| Macros only — every primitive callable | Most consistent; verbose for static surfaces | |
| Includes only — every primitive a partial template | Fewer signatures; less reusable | |
| Hybrid — match `_picker_popover.html` convention exactly | Each partial is both macro + includable template | |

**User's choice:** Macros for stateful primitives, includes for static.
**Notes:** Stateful: topbar, page-head, hero, kpi_card, sparkline, popovers. Static: showcase sections.

---

## Sparkline rendering

| Option | Description | Selected |
|--------|-------------|----------|
| Server-rendered inline SVG via Jinja macro | Pure-Jinja polyline; no JS, no extra deps | ✓ |
| Plotly mini chart (already vendored) | Heavier; lazy-load on KPI-bearing pages | |
| Skip sparkline for v1 of the primitive | Defer until real consumer | |
| CSS-only stacked-bar fallback | Simpler but less expressive | |

**User's choice:** Server-rendered inline SVG via Jinja macro.
**Notes:** Macro signature `sparkline(data, width=90, height=26, color="#3366ff")`. Edge cases (empty / single point / constant) handled gracefully.

---

## Sticky-corner table scope

| Option | Description | Selected |
|--------|-------------|----------|
| Add sticky-first-column class; not applied to Browse yet | Class shipped + showcased; Browse pivot unchanged | ✓ |
| Add sticky-first-column AND retrofit Browse | Honors "migrate everything" literally; visible Browse change | |
| Package existing sticky-thead pattern only | No first-column pinning | |
| Sticky-thead + sticky-first-column + sticky-first-column-header | Full 4-way corner; harder to test | |

**User's choice:** Add sticky-first-column class; not applied to Browse yet.
**Notes:** Class ships with proper z-index ladder; Browse pivot keeps its current sticky-thead-only behavior. Retrofit deferred to a future phase.

---

## Hero data contract

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic HeroSpec view-model | Type-checked at router boundary; matches existing patterns | ✓ |
| Dict-positional macro args | Simpler signature; less type safety | |
| Optional / progressive args | Forgiving; harder to verify | |
| No hero primitive in v1 — ship CSS only | Defers data contract entirely | |

**User's choice:** Pydantic HeroSpec view-model.
**Notes:** `HeroSpec(label, big_number, big_number_unit, delta_text, segments=[HeroSegment(label,value,color)], side_stats=[HeroSideStat(key,value,tone)])`. Macro signature `{% macro hero(spec) %}`. Empty `segments` and `side_stats` supported.

---

## Continuation check #2

| Option | Description | Selected |
|--------|-------------|----------|
| Discuss — lock 4 smalls in one batch | KPI variants, pill macros, empty-state, tabs roster | |
| Fold into Claude's Discretion | Researcher proposes defaults consistent with Dashboard_v2.html | ✓ |
| I'm ready for context | Ship CONTEXT.md now | |

**User's choice:** Fold into Claude's Discretion.
**Notes:** Default leans recorded in CONTEXT.md → Claude's Discretion section.

---

## Claude's Discretion (folded items)

- KPI 4-up vs 5-up: ONE macro with count/variant arg
- Pills / chips / tiny-chips: CSS-only, no Jinja macros
- Empty-state primitive: NOT shipped (browse/_empty_state.html stays Browse-specific)
- Topbar tabs roster: Joint Validation / Browse / Ask only
- Exact px values, class naming (`.ph` vs `.panel-header` alias/rename), `HeroSpec` file location, sample data values for showcase, `popover-search.js` extend-vs-duplicate

## Deferred Ideas

- Live tab counts on topbar (needs `nav_counts` dict contract)
- Env pill / notification bell on topbar (need real signals)
- Per-user identity / real avatar (auth deferred per D-04)
- Sticky-first-column retrofit on Browse pivot
- Browse filter row migration to chip-group filters_popover
- Empty-state primitive generalization
- Tech Reports tab + Platform BM tab in topbar
- Plotly micro-charts as alternative sparkline tech
