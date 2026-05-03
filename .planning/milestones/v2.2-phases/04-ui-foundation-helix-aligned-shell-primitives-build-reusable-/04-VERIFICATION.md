---
phase: 04-ui-foundation-helix-aligned-shell-primitives-build-reusable
verified: 2026-05-03T11:30:00Z
status: human_needed
score: 11/11 must-haves verified (locked-decision contract)
overrides_applied: 0
human_verification:
  - test: "Visit http://localhost:8000/_components in a browser"
    expected: "Topbar (P brand-mark + PBM2 wordmark + 3 unselected tabs + PM avatar) at the top; every primitive section renders (Topbar, Page-head, Hero full + minimal, KPI 4-up, KPI 5-up, Sparklines, Pills/Chips/Tiny-chips, Date-range popover, Filters popover, Sticky-corner table). No console errors. Inter Tight font visible (not system fallback). Hero number renders at 72 px weight 800. KPI sparklines visible inline. Sticky-corner table: top-left corner stays pinned when scrolling both axes."
    why_human: "Visual rendering, font weight 800, sparkline visibility, scroll behavior on sticky-corner table cannot be verified programmatically — these are visual/interactive contracts."
  - test: "Open the date-range popover on /_components"
    expected: "Click 'Date range' → popover opens via Bootstrap dropdown; start/end date inputs editable; Reset clears values; Apply submits the (visible) form. NO 7d/14d/30d/60d quick-day chip row (WR-03 deliberately removed dead UI; ROADMAP literal mentions these chips, but the post-execution WR-03 fix removed them because no JS handler ever read data-quick-days)."
    why_human: "Confirms WR-03 fix is desired/acceptable: ROADMAP goal text mentions '7/14/30/60d quick chips' but the implementation deliberately omits them per WR-03. User decision needed: accept WR-03 deviation, or re-add a working quick-day handler."
  - test: "Open the filters popover on /_components and click chips"
    expected: "Chips toggle on/off (visual change to .opt.on); hidden inputs sync via chip-toggle.js (WR-04 fix: when chip OFF, the hidden input's `disabled` attribute is set so the form does not submit a stale empty value). Apply Filters submits the form. Reset Filters clears chips."
    why_human: "WR-04 disabled-input-on-OFF behavior was flagged for human verification by the code-fixer. Confirm chip toggle + form-data integrity in real browser submission flow."
  - test: "Smoke test live routes after the topbar swap"
    expected: "GET /, /browse, /ask, /joint_validation/<existing-id> all render the new Helix topbar; existing layouts visually byte-stable (the .ph rule preserved 18px 26px padding to avoid 2-px-per-axis drift)."
    why_human: "Visual byte-stability of shipped surfaces vs pre-Wave-5 layout cannot be tested programmatically; confirms the consolidation choice in Wave 5 (preserve 18 px 26 px over the speculative 16 px 24 px) actually prevents perceptible drift."
  - test: "Confirm Google Fonts CDN is reachable from the deployment network"
    expected: "fonts.googleapis.com loads; .page-title (28 px) and .brand-mark (gradient circle with letter P) render with Inter Tight at the requested weights. If blocked by intranet egress, fonts silently fall back to system UI fonts and weight 800 degrades to ~700 — visible but not functionally broken."
    why_human: "Pitfall 1 / Open Assumption A1 from RESEARCH: outbound DNS to fonts.googleapis.com is environment-dependent. Plan 04-01 documented a vendored woff2 fallback as a future quick-task if smoke testing reveals a block."
---

# Phase 04: UI Foundation — Helix-aligned shell & primitives — Verification Report

**Phase Goal:** Build reusable Jinja partials and CSS for the visual system anchored to `Dashboard_v2.html`. Topbar (brand + tab strip + avatar), page-head, hero (1.3:1 grid + 72 px stat number + segmented bar + side-stats), KPI cards (4-up + 5-up with sparkline), panel + `.ph` header, status pills / chips / tiny-chips, date-range popover, filters popover (multi-select chip groups), sticky-corner table styling. Stack: Jinja + HTMX (no React). Brand stays PBM2.

**Verified:** 2026-05-03T11:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (locked-decision contract D-UIF-01..D-UIF-11)

| #  | Truth (D-UIF) | Status | Evidence |
| -- | ------------- | ------ | -------- |
| 1  | **D-UIF-01:** Browse / JV listing / overview / Ask / JV detail render with `class="ph"` (not `class="panel-header"`); Phase 02 invariants pinning the literal `panel-header` are atomically rewritten; CSS rule for `.ph .panel-title` exists with D-UI2-12 declarations preserved | VERIFIED | `grep -c 'panel-header' …{browse,overview,ask,joint_validation/detail}/index.html` = 0 in all four; `class="ph"` present in each; `.ph .panel-title { font-size: 18px; font-weight: 700; … margin: 0; … }` at app.css; `test_panel_title_rule`, `test_overview_index_count_in_panel_header`, `test_overview_index_filter_bar_inside_panel` rewritten to assert on `.ph` |
| 2  | **D-UIF-02:** `GET /_components` route mounted always-on (no feature flag) | VERIFIED | `app_v2/routers/components.py` exists; `app.include_router(components.router)` in main.py; no env/debug/feature-flag gating around the route; HTTP 200 returned in TestClient call |
| 3  | **D-UIF-03:** Both popovers (date-range + filters) use the Bootstrap 5 dropdown mechanism | VERIFIED | Both macros render `<div class="dropdown pop-wrap">` + `<div class="dropdown-menu pop">` with `data-bs-toggle="dropdown"` + `data-bs-auto-close="outside"`; showcase response contains 2 of each |
| 4  | **D-UIF-04:** filters_popover renders chip-group rows with hyphen-safe `name="ufs_emmc"` (not `ufs-emmc`); chip-toggle.js syncs hidden inputs | VERIFIED | Showcase output contains `name="ufs_emmc"`; absent `name="ufs-emmc"`; `class="grp"` and `class="opt on"` markup present; chip-toggle.js exists with `closest('.pop .opt')` + `popover-search-root` boundary check |
| 5  | **D-UIF-05:** `_components/_picker_popover.html` and `popover-search.js` byte-stable | VERIFIED | `git diff --quiet HEAD -- app_v2/templates/browse/_picker_popover.html` exits 0; same for `app_v2/static/js/popover-search.js`; same for `tokens.css` (D-UI2-04) |
| 6  | **D-UIF-06:** Helix topbar shape (brand + tabs + avatar) replaces legacy navbar in base.html | VERIFIED | base.html: `{% from "_components/topbar.html" import topbar %}` + `{{ topbar(active_tab=active_tab|default("")) }}`; legacy `<nav class="navbar`, `navbar-brand`, `nav nav-tabs` all absent; `.navbar { padding: 16px 0 }` rule removed from app.css; live routes render `class="topbar"` + `class="brand-mark">P<` + `>PBM2<` + `>PM<` |
| 7  | **D-UIF-07:** Tabs roster includes JV / Browse / Ask | VERIFIED | topbar.html contains exactly three `<a class="tab" href>` entries (`/`, `/browse`, `/ask`); labels `Joint Validation`, `Browse`, `Ask`; `aria-selected="true"` applied conditionally |
| 8  | **D-UIF-08:** Macro-per-file under `_components/` | VERIFIED | All 7 macro files: each contains exactly one `{% macro <name> %}` block; macro name matches filename (topbar, page_head, hero, kpi_card, sparkline, date_range_popover, filters_popover) |
| 9  | **D-UIF-09:** Sparkline server-rendered SVG with NaN-free edge cases | VERIFIED | Macro renders `<svg>` for empty/None/single/constant/multi data with no `NaN` substrings; namespace() pattern accumulates path strings; constant data falls back to mid-height flat line; showcase 5-up grid and standalone section exercise empty + single + constant edge cases |
| 10 | **D-UIF-10:** `.table-sticky-corner` rule + showcase exercise | VERIFIED | app.css: `.table-sticky-corner-wrap`, `.table-sticky-corner`, `thead th:first-child { z-index: 3 }`, `tbody td:first-child { position: sticky; z-index: 1 }`; showcase renders 4×5 sample pivot table with the class |
| 11 | **D-UIF-11:** `HeroSpec` Pydantic v2 model exists and is unit-tested | VERIFIED | `app_v2/services/hero_spec.py` exports HeroSpec, HeroSegment, HeroSideStat with Pydantic v2 + Field(default_factory=list); `tests/v2/test_phase04_uif_hero_spec.py` covers minimal/full/Literal-tone/required-field/per-instance-list semantics |

**Score:** 11 / 11 locked-decision contracts verified.

### Required Artifacts (Three-level + Data-flow check)

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `app_v2/static/css/app.css` | Helix primitive rules + `.ph` family rewrite + `.navbar` rule deletion | VERIFIED | `.topbar`, `.brand-mark`, `.av`, `.tabs`, `.tab[aria-selected="true"]`, `.ph` (×1, padding 18px 26px), `.ph .panel-title` (×1 + ×2 in comments), `.chip.on`, `.hero .num`, `.kpis.five`, `.kpi .spark`, `.pop`, `.pop .opt.on`, `.tiny-chip.ok`, `.table-sticky-corner thead th:first-child` (z-index: 3), `.btn-helix` all present; `.panel-header` selectors absent; `.navbar { … }` absent |
| `app_v2/templates/base.html` | Google Fonts <link> + topbar macro import + chip-toggle.js script | VERIFIED | 2× `fonts.googleapis.com`, 1× `Inter+Tight:wght@400;500;600;700;800`, 1× `JetBrains+Mono:wght@400;500;600`; topbar import + invocation; `chip-toggle.js` script present after `popover-search.js`; `<nav class="navbar` absent; footer block + htmx-error-container preserved |
| `app_v2/templates/_components/{topbar,page_head,hero,kpi_card,sparkline,date_range_popover,filters_popover}.html` | One macro per file, filename = macro | VERIFIED | All 7 files exist, each with exactly one `{% macro %}` matching filename |
| `app_v2/templates/_components/showcase.html` | Section page exercising every primitive | VERIFIED | 214 lines; renders Topbar (inherited via base.html), Page-head, Hero full + minimal, KPI 4-up + 5-up, standalone Sparklines (with empty + constant edge cases), Pills/Chips/Tiny-chips, Date-range popover, Filters popover (Status / OEM / UFS-eMMC), Sticky-corner table; all sections appear in HTTP response |
| `app_v2/services/hero_spec.py` | HeroSpec/HeroSegment/HeroSideStat Pydantic v2 | VERIFIED | All three exported; Literal["default","green","red"] tone; Field(default_factory=list); imports work |
| `app_v2/services/filter_spec.py` | FilterGroup/FilterOption Pydantic v2 | VERIFIED | Both exported; default `on=False`; default empty options list |
| `app_v2/static/js/chip-toggle.js` | Sibling helper for `.pop .opt` chip toggle + form-data integrity | VERIFIED | 111 lines; document-level click delegation with capture phase; `closest('.pop .opt')`; `popover-search-root` boundary check (Pitfall 8); WR-04: `hidden.disabled = true/false` based on isOn so form submission excludes OFF chips; Reset handler also flips disabled |
| `app_v2/routers/components.py` | GET /_components route + showcase context | VERIFIED | router exists; mounted in main.py (sequenced before root); active_tab="showcase" passed; HeroSpec / FilterGroup fixtures inline |
| `tests/v2/test_phase04_uif_invariants.py` | Static-source invariants for Wave 1 + Wave 3 | VERIFIED | 273 lines; 19 tests pass; covers .ph rule shape, fonts link order, base.html topbar, chip-toggle.js sibling, _picker_popover byte-stable, macro-per-file convention |
| `tests/v2/test_phase04_uif_components.py` | Route + macro behavior tests | VERIFIED | 257 lines; 19 tests pass; route 200; section labels; hero variants; KPI grids; sparkline edge-case rendering; popover dropdown markup; filters_popover hyphen-safe `ufs_emmc` (positive) + `ufs-emmc` (negative); sticky-corner table; regressions on /, /browse, /ask |
| `tests/v2/test_phase04_uif_hero_spec.py` | Pydantic unit tests | VERIFIED | 152 lines; 13 tests pass; HeroSpec required/optional/coercion/Literal/per-instance lists; FilterGroup/FilterOption defaults |

### Key Link Verification

| From | To | Via | Status |
| ---- | -- | --- | ------ |
| `base.html <head>` | Google Fonts CDN | `<link rel="stylesheet">` before tokens.css | WIRED — fonts link at smaller line number than tokens.css link |
| `base.html` | `_components/topbar.html` | `{% from %} import topbar` + `{{ topbar(active_tab=...) }}` | WIRED — invocation present, all 3 routes render `class="topbar"` |
| `base.html` | `chip-toggle.js` | `<script src=… defer>` after `bootstrap.bundle.min.js` | WIRED — script tag present, source order verified |
| `routers/components.py` | `_components/showcase.html` | `templates.TemplateResponse(... "_components/showcase.html" ...)` | WIRED — TestClient returns 200 with all 10 sections in body |
| `routers/components.py` | HeroSpec / FilterGroup | `from app_v2.services.{hero_spec,filter_spec} import …` | WIRED — `Active validations` + `Total platforms` rendered in HTML; `name="ufs_emmc"` rendered |
| `_components/kpi_card.html` | `_components/sparkline.html` | `{% from %} import sparkline` | WIRED — showcase response contains 12 `<svg` elements (4-up + 5-up + 5 standalone, minus those without spark_data) |
| `_components/filters_popover.html` | `static/js/chip-toggle.js` | hidden inputs `data-opt=` + `.pop .opt` selector | WIRED — chip-toggle.js binds via document-level click delegation |
| `app.css .ph .panel-title` | overview/JV detail `<h1 class="panel-title">` | descendant selector | WIRED — selector exists; both surfaces render the literal `<h1 class="panel-title">` inside `<div class="ph">` |
| `app_v2/main.py` | `routers/components.py` | `from app_v2.routers import components; app.include_router(components.router)` | WIRED — GET /_components returns 200 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| showcase.html → hero(spec=hero_full) | `hero_full` | `routers/components.py` constructs HeroSpec inline | Yes — labels, segments, side_stats reach DOM | FLOWING |
| showcase.html → kpi_card(spark_data=…) | `kpi_4up`/`kpi_5up` | inline list-of-dicts in router | Yes — values, deltas, sparkline SVGs render | FLOWING |
| showcase.html → filters_popover(groups=filter_groups) | `filter_groups` | inline FilterGroup list in router | Yes — Status/OEM/UFS-eMMC chips render with `on` state propagated | FLOWING |
| topbar macro inside base.html | `active_tab` | router context (overview/browse/ask routes) | Yes — `aria-selected="true"` lands on the right tab on /, /browse, /ask; absent on /_components | FLOWING |
| sparkline macro | `data` list | KPI fixtures inline | Yes — non-NaN paths emitted across empty/single/constant/multi inputs | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full v2 test suite green | `.venv/bin/python -m pytest tests/v2/ -q` | 542 passed, 5 skipped, 0 failures | PASS |
| Phase 04 UIF tests green | `pytest tests/v2/test_phase04_uif_*.py -q` | 51 passed | PASS |
| Phase 02 invariants + main tests green | `pytest tests/v2/test_phase02_invariants.py tests/v2/test_main.py -q` | 73 passed, 2 skipped | PASS |
| GET /_components | TestClient call → 200 with 10 primitive sections in body | All sections present; `class="topbar"` inherited; no `aria-selected="true"` on any tab (showcase) | PASS |
| GET /, /browse, /ask | TestClient calls → 200 with `class="topbar"` and `class="ph"` (where applicable), no `class="panel-header"` | All three pass | PASS |
| Hyphen-safe filters_popover | Showcase response check | `name="ufs_emmc"` present; `name="ufs-emmc"` absent | PASS |
| Sparkline edge cases | Direct macro render via Jinja Environment | empty / None / single / constant all yield `<svg>` with no `NaN` | PASS |
| Byte-stable refs | `git diff --quiet HEAD --` on _picker_popover, popover-search.js, tokens.css | All exit 0 | PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
| ----------- | -------------- | ----------- | ------ | -------- |
| D-UIF-01 | 04-01, 04-03, 04-04, 04-05 | LOCKED rename path: panel-header → .ph atomic, on every existing surface | SATISFIED | All four target templates carry `class="ph"`; CSS rules rewritten; Phase 02 invariant tests rewritten with belt-and-suspenders negative assertions |
| D-UIF-02 | 04-04 | GET /_components always-on, every primitive section, no feature flag | SATISFIED | Route returns 200; no env/debug gate; all 10 sections render |
| D-UIF-03 | 04-02, 04-04 | Both popovers use Bootstrap 5 dropdown anchoring | SATISFIED | Both `.dropdown.pop-wrap` + `.dropdown-menu.pop` + `data-bs-auto-close="outside"` |
| D-UIF-04 | 04-02, 04-04 | filters_popover chip-group, hyphen-safe group_name, chip-toggle.js | SATISFIED | `name="ufs_emmc"` confirmed; chip-toggle.js sibling exists |
| D-UIF-05 | 04-02, 04-03, 04-04, 04-05 | `_picker_popover.html` byte-stable | SATISFIED | `git diff --quiet HEAD --` exits 0 |
| D-UIF-06 | 04-01, 04-02, 04-03, 04-04 | Full Helix topbar shape (brand-mark "P" + "PBM2" + tabs + "PM" avatar) | SATISFIED | Live routes render the exact markup; `.navbar` rule + legacy nav-tabs ul gone |
| D-UIF-07 | 04-01, 04-02, 04-03, 04-04 | Tabs roster: JV / Browse / Ask | SATISFIED | Exactly three tabs in topbar.html; labels confirmed |
| D-UIF-08 | 04-02, 04-04 | One macro per file under `_components/` | SATISFIED | All 7 macro files satisfy the convention |
| D-UIF-09 | 04-01, 04-02, 04-04 | Sparkline server-rendered SVG, NaN-free edges | SATISFIED | Edge cases verified by direct macro render and unit tests |
| D-UIF-10 | 04-01, 04-04 | `.table-sticky-corner` class with z-index ladder + showcase exercise | SATISFIED | CSS rule + showcase 4×5 sample table rendered |
| D-UIF-11 | 04-02, 04-04 | HeroSpec Pydantic v2 + unit tests | SATISFIED | hero_spec.py exists; test_phase04_uif_hero_spec.py exercises required/optional/Literal/per-instance |

All 11 LOCKED requirement IDs are traceable to a plan AND demonstrably present in the implementation.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none flagged) | — | — | — | Implementation is consistent: no TODO/FIXME placeholders, no return-null stubs, no console.log-only handlers in any artifact created by Phase 04. The only marker comments found are intentional documentation comments (e.g., chip-toggle.js boundary documentation, app.css Phase 04 banner). |

### Goal-Text vs Implementation Divergence (Informational)

The ROADMAP goal text says: "date-range popover (7/14/30/60d quick chips + start/end inputs + reset/apply)". The implementation deliberately removed the quick-day chips per the **WR-03** post-execution fix (commit `112f2d8`):

> The quick-range chip row (data-quick-days="7|14|30|...") was removed in WR-03: no JS read the attribute, so the chips were dead UI that misled users into thinking clicks would populate the date inputs. Re-add when a quick-range handler ships.

This is a deliberate scoping choice (avoid shipping dead UI), tracked in tests (`test_phase04_uif_components.py` asserts `class="qrow" not in body` and `data-quick-days= not in body`). Listed in `human_verification` so the user can confirm acceptance — the alternative is to re-add the chips behind a working quick-range handler in a follow-up.

### Human Verification Required

See `human_verification` block in the frontmatter. Five items, summarized:

1. **Visual /_components smoke** — every primitive renders correctly in a browser; Inter Tight @ 800 visible; sticky-corner scrolling works.
2. **Date-range popover** — confirm WR-03 (no quick-day chips) is the desired ship state.
3. **Filters popover + chip-toggle** — confirm WR-04 disabled-input-on-OFF flow in real browser submission.
4. **Live routes after topbar swap** — confirm `.ph { padding: 18px 26px }` consolidation prevents perceptible drift on Browse / JV / Ask vs pre-Wave-5 layout.
5. **Google Fonts CDN reachability** — Pitfall 1 / A1: confirm `fonts.googleapis.com` is reachable from the deployment intranet (vendored woff2 fallback documented as a follow-up if blocked).

### Gaps Summary

No blocking gaps. All 11 LOCKED D-UIF-XX contracts are satisfied; all 542 tests pass; all routes return 200; D-UIF-05 byte-stable refs unchanged. The single goal-text-vs-implementation divergence (WR-03 quick-day chip removal) is a documented, tested deviation captured in `human_verification` for user acceptance.

---

_Verified: 2026-05-03T11:30:00Z_
_Verifier: Claude (gsd-verifier)_
