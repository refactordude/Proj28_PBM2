# Phase 4: UI Foundation — Helix-aligned shell & primitives - Research

**Researched:** 2026-05-03
**Domain:** UI primitives layer for FastAPI + Jinja2 + Bootstrap 5 + HTMX (no React, no JS framework)
**Confidence:** HIGH (full visual reference + existing codebase fully readable; CONTEXT.md and UI-SPEC.md fully locked)

## Summary

Phase 4 ports the visual signature of `/home/yh/Desktop/02_Projects/Proj27_PBM1_fork_bootstrap/Dashboard_v2.html` (a React/inline-CSS prototype, 1438 lines, all CSS in `<style>` lines 11–345) into the existing PBM2 stack — **Jinja2 macros + a single-file `app.css` extension + zero new JS framework**. The phase is overwhelmingly a CSS + Jinja-macro authoring exercise; the only new Python is one router (`routers/components.py` for `GET /_components`), one Pydantic file (`HeroSpec` + helpers), and one tiny inline-SVG sparkline algorithm in a Jinja macro.

The ecosystem's verdict is unambiguous: for a pure visual port with HTMX as the interaction primitive, **inline SVG (server-rendered) and `position: sticky` (CSS-only) eliminate the entire client-JS surface for sparklines and sticky-corner tables**. Bootstrap 5.3.8's `dropdown` component is the correct host for both new popovers — it is already vendored, already validated by the byte-stable `_picker_popover.html` (D-UI2-09 / D-UIF-05), and supports custom-width `.dropdown-menu` content with arbitrary children + `data-bs-auto-close="outside"`. The only fresh JS needed is a ~30-line `chip-toggle.js` sibling for the chip-on-click → hidden-input sync inside `filters_popover.html`.

**Primary recommendation:** Treat this as a **CSS port of Dashboard_v2.html lines 11–268 + 1155–1206**, gated by two existing-codebase constraints the UI-SPEC has not fully resolved: (1) **The UI-SPEC's "migrate every `panel-header` → `ph`" instruction (line 411–413) directly contradicts UI-SPEC line 242 ("`.ph` is a NEW class, NOT a rename") AND breaks Phase 02 invariant tests that pin the literal string `class="panel-header"` byte-stably (`tests/v2/test_phase02_invariants.py` lines 286, 406, 622, 663) — the planner MUST resolve this contradiction by adopting the alias-not-rename path (ship `.ph` as a NEW class with identical rules; existing `.panel-header` HTML stays byte-stable; macros emit `.ph` only on new surfaces) before any task touches templates.** (2) **Tests pin `nav nav-tabs` and `navbar-brand` strings (`tests/v2/test_main.py` lines 32, 145, 196, 209) as the topbar markup** — replacing the topbar with a non-`navbar` Helix shape requires the planner to coordinate test rewrites in the same wave as the markup change.

## User Constraints (from CONTEXT.md)

### Locked Decisions

(verbatim from `04-CONTEXT.md` §Implementation Decisions; namespace `D-UIF-*`)

- **D-UIF-01:** Phase 4 ships primitives, a `/_components` showcase route, AND migrates the global shell + panel-header naming on every existing surface (Browse / JV / Ask). Refinements: Browse filter row is **not** retrofitted (its `_picker_popover.html` stays byte-stable per D-UI2-09); Browse pivot keeps its current sticky-thead-only behavior. Migration covers what's structurally compatible without breaking shipped contracts.
- **D-UIF-02:** New `GET /_components` route renders every primitive with realistic sample data on a single sectioned page. Always-on (not dev-gated). Sections: Topbar, Page-head, Hero (full + minimal), KPI 4-up, KPI 5-up, Pills/Chips/Tiny-chips, Date-range popover, Filters popover (chip groups), Sticky-corner table.
- **D-UIF-03:** Both new popovers (date-range, filters) use the Bootstrap 5 dropdown pattern, mirroring `_picker_popover.html` semantics. Apply submits a form with hidden inputs; state round-trips via `HX-Push-Url`. Click-outside dismisses; focus trap on open.
- **D-UIF-04:** `_components/filters_popover.html` is the new chip-group multi-category popover. Distinct from `_picker_popover.html` (checkbox list, single attribute). Both primitives coexist.
- **D-UIF-05:** `_picker_popover.html` is byte-stable per D-UI2-09. No edits, no refactor, no rename. Browse and JV continue importing it AS-IS.
- **D-UIF-06:** Full Helix topbar shape — gradient brand-mark with letter "P" + "PBM2" wordmark + horizontal tab strip + static `.av` avatar slot showing "PM". No env pill, no notification bell, no live tab count badges.
- **D-UIF-07:** Tabs roster stays Joint Validation / Browse / Ask. No new tabs introduced this phase.
- **D-UIF-08:** Stateful primitives ship as Jinja MACROS; static partials use `{% include %}`. Macros: `topbar`, `page_head`, `hero`, `kpi_card`, `sparkline`, `date_range_popover`, `filters_popover`. Includes: `_components/showcase.html`.
- **D-UIF-09:** KPI-card sparkline = server-rendered inline SVG via Jinja macro. Macro signature: `sparkline(data: list[int|float], width=90, height=26, color="#3366ff")`.
- **D-UIF-10:** Phase 4 ships a `.pivot-sticky-corner` (or similar) class that pins `<thead>` AND the first column. Showcase demos it; Browse pivot is NOT retrofitted.
- **D-UIF-11:** `HeroSpec` is a Pydantic v2 view-model passed to the `hero` macro. Fields: `label`, `big_number`, `big_number_unit`, `delta_text`, `segments: list[HeroSegment]`, `side_stats: list[HeroSideStat]`.

### Claude's Discretion

(verbatim items the researcher/planner may resolve without re-asking; researcher's resolutions noted inline below)

- KPI variants: ONE `kpi_card` macro with `variant` arg. **(Resolved by UI-SPEC: variant arg sets caller's container class `.kpis` or `.kpis.five`; macro renders one `.kpi` card.)**
- Pills / chips / tiny-chips: CSS-only.
- Empty-state primitive: NOT shipped this phase.
- Topbar tabs roster default content (Joint Validation / Browse / Ask).
- Exact px values for `.topbar` height, `.ph` padding, `.hero` grid gap, `.kpi` spark size, `.pop` width. **(Resolved by UI-SPEC §Spacing, §Typography, §Component Inventory — Dashboard verbatim with mod-4 normalization.)**
- `HeroSpec` submodel file location. **(UI-SPEC pins `app_v2/services/hero_spec.py`.)**
- Whether `.ph` is a NEW class or an alias for `.panel-header`. **(UI-SPEC §Component Inventory line 242 states explicitly: "`.ph` is a NEW class, NOT a rename." Researcher AGREES — this is the only path that preserves D-UI2-12 + Phase 02 invariants. See §Migration Strategy below for the contradiction with UI-SPEC §Migration that must be resolved.)**
- Tab `<button>` vs `<a>` form in topbar — **default `<a href>`** to match existing base.html and Phase 1 Pitfall 8 (no hx-boost on tab nav).
- Whether `popover-search.js` is extended or a sibling JS helper is added. **(UI-SPEC §JS pins sibling `chip-toggle.js`. Researcher AGREES — D-UI2-09 byte-stable.)**
- Sticky-corner class name. **(UI-SPEC pins `.table-sticky-corner`.)**
- Sample data values for showcase fixtures (must exercise every macro arg).
- New tokens: add `--cyan` / `--cyan-soft` ONLY if a primitive uses them. **(Researcher: Phase 4 primitives do NOT use cyan; tokens already in `tokens.css` cover everything per §UI-SPEC §Color "No new color tokens needed.")**
- Whether `Inter Tight` already covers Helix weight range (400/500/600/700/800). **(Researcher confirms NOT loaded — `base.html` has zero Google Fonts link tag; current rendering relies on system fallback for weight 800. UI-SPEC §Font Loading Fix mandates adding the link tag in `<head>` before tokens.css. See §Pitfall 1.)**

### Deferred Ideas (OUT OF SCOPE)

- Live tab counts on the topbar.
- Env pill, notification bell, real per-user avatar.
- Sticky-first-column retrofit on Browse pivot.
- Browse filter row migration to chip-group `filters_popover.html`.
- Empty-state primitive generalization.
- Tech Reports tab + Platform BM tab.
- Plotly micro-charts / interactive sparklines.
- KPI variant macro signature refinement.

## Phase Requirements

(No formal `REQ-*` IDs were locked for this phase; the contract is stated as `D-UIF-01..D-UIF-11` decisions + UI-SPEC component inventory. The planner uses these as requirement IDs.)

| ID | Description | Research Support |
|----|-------------|------------------|
| D-UIF-01 | Migrate global shell + panel-header naming on every existing surface | §Migration Strategy (alias-not-rename path resolves the UI-SPEC contradiction) |
| D-UIF-02 | `GET /_components` showcase route, always-on | §Showcase Route + existing FastAPI router pattern |
| D-UIF-03 | Bootstrap 5 dropdown for both new popovers | §Bootstrap dropdown for popovers (custom width + arbitrary content verified) |
| D-UIF-04 | `filters_popover.html` chip-group sibling | §Filters popover macro |
| D-UIF-05 | `_picker_popover.html` byte-stable | §Don't Hand-Roll (popover-search.js untouched; chip-toggle.js is sibling) |
| D-UIF-06 | Full Helix topbar with brand-mark "P" + wordmark "PBM2" + tabs + avatar "PM" | §Topbar (macro signature; Bootstrap navbar fully replaced — see §Pitfall 2 test surface) |
| D-UIF-07 | Tabs roster: Joint Validation / Browse / Ask | §Topbar tabs list (existing nav_label_map preserved) |
| D-UIF-08 | Macros for stateful primitives; includes for static | §Jinja2 partial composition |
| D-UIF-09 | Server-rendered inline SVG sparkline | §Sparkline algorithm + edge cases |
| D-UIF-10 | `.table-sticky-corner` class (showcase only) | §Sticky-corner table — pure CSS via `position: sticky` z-index ladder |
| D-UIF-11 | `HeroSpec` Pydantic v2 view-model | §HeroSpec + sibling submodels |

## Project Constraints (from CLAUDE.md)

The following directives are extracted from `./CLAUDE.md` and are LAW for the planner:

| Directive | Source | Application to Phase 4 |
|-----------|--------|----------------------|
| Tech stack: FastAPI + Bootstrap 5 + HTMX + Jinja2 + jinja2-fragments + Pydantic v2 | CLAUDE.md §Constraints | All primitives are Jinja macros; no React; no client-side framework |
| Read-only DB; no writes | CLAUDE.md §Constraints | N/A (Phase 4 is UI primitives only — no DB code) |
| GSD workflow enforcement: don't edit outside a GSD command | CLAUDE.md §GSD Workflow | Plan tasks invoked via `/gsd-execute-phase`; Wave 0 = test infra |
| `Avoid using cat/head/tail/sed/awk/echo` | CLAUDE.md tool guidance | Planner uses Read/Edit/Write tools, not bash text-mangling |
| Project skills directory empty | CLAUDE.md §Project Skills | No skill rules to load |
| Profile not configured | CLAUDE.md §Developer Profile | No profile-specific style overrides |

**Implication:** Plans MUST use Edit/Write tools for `app.css` extensions and template authoring. The new `routers/components.py` follows the existing FastAPI APIRouter pattern (see `app_v2/routers/joint_validation.py`, `summary.py`). The `HeroSpec` Pydantic v2 model mirrors the established `JointValidationGridViewModel` / `PageLink` pattern in `app_v2/services/joint_validation_grid_service.py`.

## Standard Stack

### Core (already vendored / installed — Phase 4 adds NOTHING new at the runtime-dependency layer)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Bootstrap 5 | **5.3.8** (`app_v2/static/vendor/bootstrap/VERSIONS.txt`, downloaded 2026-04-24) | Dropdown component, utility classes (d-flex, ms-auto, etc.) | Already the v2.0-locked UI primitive; v5.3 dropdown is mature, click-outside dismiss + focus management built-in |
| Bootstrap Icons | **1.13.1** | `bi-*` icons inside topbar / page-head / table buttons | Already vendored; Helix prototype uses inline SVG for icons but `bi-*` is the existing PBM2 idiom — no need to switch |
| HTMX | **2.0.10** (`app_v2/static/vendor/htmx/VERSIONS.txt`) | Form-submit + OOB swaps for popovers; `HX-Push-Url` round-trip | Already wired via base.html with `defer`; popover Apply form-submits piggy-back on this |
| jinja2 + jinja2-fragments | (existing project pin) | Macro definitions + block-level rendering for OOB | Existing convention — every Phase 02 partial uses `{% from "x" import macro %}{{ macro(...) }}` |
| Pydantic v2 | (existing project pin) | `HeroSpec`, `HeroSegment`, `HeroSideStat`, `FilterGroup`, `FilterOption` models | Mirrors `JointValidationGridViewModel`, `PageLink`, `ChartSpec` already in services |
| FastAPI APIRouter | (existing) | New `routers/components.py` for `GET /_components` | Pattern verified in `app_v2/main.py` lines 207–213 — `app.include_router(components.router)` registered before `root.router` (the catch-all-ish surface) |

### Supporting (NEW client-side asset)

| File | Purpose | When to Use |
|------|---------|-------------|
| `app_v2/static/js/chip-toggle.js` (NEW, ~30 LOC) | Click-to-toggle `.pop .opt.on` class + sync to a hidden `<input>` in the parent form. NOT a fork of `popover-search.js` (D-UIF-05 / D-UI2-09 byte-stable). | Loaded after `bootstrap.bundle.min.js` with `defer` in `base.html`, mirrors the existing pattern for `popover-search.js` |
| `app_v2/services/hero_spec.py` (NEW) | Pydantic v2 `HeroSpec`, `HeroSegment`, `HeroSideStat` | Imported by `routers/components.py` for showcase + by any future router that wants to render a hero |
| `app_v2/services/filter_spec.py` (NEW) — OR co-located in `hero_spec.py` (researcher's call: separate file is cleaner; planner picks) | Pydantic v2 `FilterGroup`, `FilterOption` | Imported by future routers that drive `filters_popover.html` |
| `app_v2/routers/components.py` (NEW) | `GET /_components` rendering `_components/showcase.html` | Mounted in `main.py` BEFORE `root.router` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Server-rendered inline SVG sparkline | Chart.js / sparkline.js / d3-tiny | Adds a JS asset and a per-call mount cost; HTMX swap re-mounts charts on every grid swap — verified pain point in Phase 03's Plotly path. Inline SVG renders deterministically and survives HTMX outerHTML swaps with zero re-init work. **Verdict: locked by D-UIF-09; researcher concurs.** |
| Bootstrap 5 dropdown for popover | Bootstrap 5 popover (`bsPopover`) | Bootstrap's `popover` component is for tooltip-style content with `data-bs-content` + `data-bs-html=true`; rendering a 300px form with chip groups inside a popover requires fighting the trigger/positioning model. The existing `_picker_popover.html` proves dropdown is the right primitive. **Verdict: locked by D-UIF-03.** |
| Single `.ph` selector replacing `.panel-header` | Keep `.panel-header` AS-IS, add `.ph` as alias with identical rules | UI-SPEC §Component Inventory line 242 already declares `.ph` is NEW (not a rename) — but UI-SPEC §Migration line 411–413 contradicts this. Phase 02 invariants pin literal `class="panel-header"`. **Verdict: alias path. See §Migration Strategy below.** |
| Topbar as Bootstrap `<nav class="navbar">` | Topbar as bare `<div class="topbar">` (Helix shape) | Helix topbar is a single rounded white pill — fundamentally different visual treatment than Bootstrap navbar. The existing `.navbar { padding: 16px 0 }` rule (D-UI2-02) is the only Bootstrap navbar customization; replacing the markup means deleting that rule and updating `tests/v2/test_phase02_invariants.py::test_navbar_padding_override` + `tests/v2/test_main.py::test_*nav-tabs*`. **Verdict: replace; tests update in the same wave. See §Pitfall 2.** |
| Macros emitting `<a>` tabs | `<button>` tabs that POST | Phase 1 Pitfall 8 explicitly forbids `hx-boost` on tab nav; full-page navigation is the contract. **Verdict: `<a href>` per Discretion + Phase 1 Pitfall 8.** |

**Installation:** None. Phase 4 adds zero runtime dependencies.

**Version verification:**
- Bootstrap `5.3.8` confirmed via `app_v2/static/vendor/bootstrap/VERSIONS.txt`. `[VERIFIED: vendor manifest]`
- HTMX `2.0.10` confirmed via `app_v2/static/vendor/htmx/VERSIONS.txt`. `[VERIFIED: vendor manifest]`
- HTMX SSE extension `2.2.4` (Phase 03; not used in Phase 4 but confirms vendor pattern). `[VERIFIED: vendor manifest]`
- Inter Tight via Google Fonts: `family=Inter+Tight:wght@400;500;600;700;800` — verified against `Dashboard_v2.html` line 9. `[CITED: Dashboard_v2.html line 9]`
- JetBrains Mono via Google Fonts: `family=JetBrains+Mono:wght@400;500;600`. `[CITED: Dashboard_v2.html line 9]`

## Architecture Patterns

### Recommended File Layout

```
app_v2/
├── routers/
│   └── components.py                    # NEW: GET /_components → showcase.html
├── services/
│   └── hero_spec.py                     # NEW: HeroSpec, HeroSegment, HeroSideStat
│                                        #      (and optionally FilterGroup, FilterOption
│                                        #       if planner picks co-location over filter_spec.py)
├── static/
│   ├── css/
│   │   ├── tokens.css                   # UNCHANGED (or expanded with --cyan only IF used)
│   │   └── app.css                      # EXTENDED with all Helix primitives (~270 new lines)
│   └── js/
│       └── chip-toggle.js               # NEW: ~30 LOC; loaded AFTER bootstrap.bundle.min.js
└── templates/
    ├── base.html                        # MODIFIED: <head> gains Google Fonts link;
    │                                    #          <nav class="navbar"> swapped for {{ topbar(...) }};
    │                                    #          tests update in lockstep
    └── _components/                     # NEW directory
        ├── topbar.html                  # macro: topbar(active_tab="")
        ├── page_head.html               # macro: page_head(title, subtitle="", actions_html="")
        ├── hero.html                    # macro: hero(spec)  — spec is HeroSpec
        ├── kpi_card.html                # macro: kpi_card(label, value, unit="", delta="",
        │                                #                 delta_tone="flat", spark_data=None)
        ├── sparkline.html               # macro: sparkline(data, width=90, height=26,
        │                                #                  color="var(--accent)")
        ├── date_range_popover.html      # macro: date_range_popover(form_id, field_prefix="date",
        │                                #         quick_days=[7,14,30,60], start_val="", end_val="")
        ├── filters_popover.html         # macro: filters_popover(form_id, groups,
        │                                #         button_label="Filters")
        └── showcase.html                # included by GET /_components — exercises every primitive
```

### Pattern 1: Jinja macro file = single export named after the file

**What:** Every primitive lives in its own file with one `{% macro <filename>(...) %}` block. Callers do `{% from "_components/topbar.html" import topbar %}` then `{{ topbar(active_tab="overview") }}`.

**When to use:** All stateful primitives (D-UIF-08).

**Example (verbatim from existing `_picker_popover.html`):**
```jinja
{# app_v2/templates/_components/topbar.html #}
{% macro topbar(active_tab="") %}
<div class="topbar">
  <div class="brand">
    <div class="brand-mark">P</div>
    <span>PBM2</span>
  </div>
  <div class="tabs">
    <a class="tab" href="/" {% if active_tab == "overview" %}aria-selected="true"{% endif %}>
      <i class="bi bi-list-ul"></i> Joint Validation
    </a>
    <a class="tab" href="/browse" {% if active_tab == "browse" %}aria-selected="true"{% endif %}>
      <i class="bi bi-table"></i> Browse
    </a>
    <a class="tab" href="/ask" {% if active_tab == "ask" %}aria-selected="true"{% endif %}>
      <i class="bi bi-chat-dots"></i> Ask
    </a>
  </div>
  <div class="top-right">
    <div class="av">PM</div>
  </div>
</div>
{% endmacro %}
```
Source: `app_v2/templates/browse/_picker_popover.html` macro pattern + Dashboard_v2.html lines 31–47, 50–56. `[CITED: Dashboard_v2.html lines 31-56]`

### Pattern 2: jinja2-fragments + macros — define macros INSIDE blocks if the block is rendered alone

**What:** When a router uses `block_names=["grid", ...]` to render only a fragment for HTMX, macros defined OUTSIDE the rendered block are invisible. The Browse and JV templates already encode this:
```jinja
{% block grid %}
  {% macro sortable_th(col, label) %}...{% endmacro %}   {# defined INSIDE block #}
  ...
{% endblock %}
```

**When to use:** Phase 4 macros are imported from `_components/` files via `{% from ... import ... %}`, NOT defined inline — so this pitfall does NOT bite the new primitives directly. BUT: `routers/components.py` should render the **full template** (no `block_names` filter); the showcase is a single full-page render.

**Source:** `app_v2/templates/overview/index.html` lines 50–71 (Phase 01 Pitfall 8). `[VERIFIED: codebase grep]`

### Pattern 3: Pydantic v2 view-model passed to macro

**What:** `hero(spec)` receives a `HeroSpec` instance; macro reads `spec.label`, `spec.big_number`, etc. Mirrors `OverviewGridViewModel` + `PageLink` pattern.

**Example (mirrors existing `JointValidationGridViewModel` in `app_v2/services/joint_validation_grid_service.py` lines 106–137):**
```python
# app_v2/services/hero_spec.py
from typing import Literal
from pydantic import BaseModel, Field

class HeroSegment(BaseModel):
    label: str
    value: float       # percentage 0–100
    color: str         # CSS color string e.g. "#3366ff" or "var(--accent)"

class HeroSideStat(BaseModel):
    key: str
    value: str
    tone: Literal["default", "green", "red"] = "default"

class HeroSpec(BaseModel):
    label: str
    big_number: int | float | str
    big_number_unit: str | None = None
    delta_text: str | None = None
    segments: list[HeroSegment] = Field(default_factory=list)
    side_stats: list[HeroSideStat] = Field(default_factory=list)
```
Source: UI-SPEC §Pydantic View-Models lines 326–366 + `[VERIFIED: app_v2/services/joint_validation_grid_service.py lines 106-137]`

### Pattern 4: Bootstrap 5 dropdown for arbitrary popover content

**What:** A 300px white panel with form inputs lives inside `<div class="dropdown-menu pop">…</div>`. The trigger is `<button class="btn dropdown-toggle">`, dropdown semantics (open/close, click-outside-to-dismiss, focus management) come from Bootstrap; visual styling comes from Phase 4 CSS (`.pop`, `.pop-head`, etc.). Set `data-bs-auto-close="outside"` on the trigger to keep it open during interaction. Set `min-width` and `width` on the `.dropdown-menu.pop` element to override Bootstrap's default 10rem.

**When to use:** Both `date_range_popover.html` and `filters_popover.html` (D-UIF-03).

**Example skeleton:**
```jinja
<div class="dropdown pop-wrap">
  <button class="btn btn-white dropdown-toggle"
          type="button"
          data-bs-toggle="dropdown"
          data-bs-auto-close="outside"
          aria-expanded="false">
    {{ button_label | e }}
  </button>
  <div class="dropdown-menu pop" style="width:300px;">
    {# .pop-head, .qrow / .grp / .opts, .foot ... #}
  </div>
</div>
```
Source: `app_v2/templates/browse/_picker_popover.html` lines 51–134 + Dashboard_v2.html lines 130–152. `[VERIFIED: codebase grep]` `[CITED: Bootstrap docs https://getbootstrap.com/docs/5.3/components/dropdowns/]`

### Pattern 5: HTMX form submit from popover Apply

**What:** Apply button = `<button type="submit" form="some-form-id" class="btn sm">`. The form lives outside the popover; the button uses `form=` attribute to associate (same trick as `_picker_popover.html` line 113 `form="{{ form_id }}"`). The form has `hx-post` / `hx-target` / `hx-push-url` already set; submit fires HTMX. Server response includes OOB swap blocks for any badges that need refresh.

**When to use:** Apply submit in date-range and filters popovers (D-UIF-03).

**Source:** `app_v2/templates/browse/_picker_popover.html` form-association pattern + `app_v2/routers/browse.py` `block_names` OOB pattern. `[VERIFIED: codebase grep]`

### Anti-Patterns to Avoid

- **Inline `<style>` in macros.** Phase 03 Plotly chart_html embeds inline styles unavoidably (3rd-party library); Phase 4 macros must put all styling in `app.css`. Reasoning: invariant tests grep `app.css` for rule presence; inline styles can't be invariant-tested.
- **Macro defined outside block, rendered as a fragment via `block_names=[...]`.** Macros become invisible (Phase 01 Pitfall 8). Phase 4 macros are imported via `{% from %}` so this is mostly avoided, but the showcase route should render the full template (no `block_names`).
- **`hx-boost` on tabs.** Phase 1 Pitfall 8. Tab nav is full-page navigation by contract.
- **Editing `popover-search.js` to add chip-toggle behavior.** Violates D-UI2-09 + D-UIF-05 byte-stable contract on `_picker_popover.html`'s JS sibling.
- **Renaming `panel-header` → `ph` across all callers.** Breaks Phase 02 invariant tests and the D-UI2-12 `.panel-header .panel-title` rule. See §Migration Strategy.
- **Loading 4.5MB Plotly globally.** Phase 03 RESEARCH Pitfall 5 — Plotly is loaded ONLY on `/ask` via `{% block extra_head %}`. Phase 4 doesn't add Plotly; sparklines are inline SVG.
- **Bootstrap navbar shape preserved with `.topbar` styling layered on top.** The `.navbar` rule + Bootstrap's navbar CSS will fight Helix's flat-pill shape. Replace markup wholesale; delete `.navbar { padding: 16px 0 }`; update tests in lockstep.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dropdown open/close + click-outside dismiss | Custom JS event handlers | Bootstrap 5 `data-bs-toggle="dropdown" data-bs-auto-close="outside"` | Bootstrap handles focus trap, ESC-to-close, click-outside, ARIA — battle-tested by `_picker_popover.html`. `[VERIFIED: app_v2/templates/browse/_picker_popover.html line 56-57]` |
| Sticky-corner table behavior | JavaScript scroll listeners that toggle `position: fixed` | Pure CSS `position: sticky` + z-index ladder | Browser-native, GPU-accelerated, no JS overhead, survives HTMX swaps. Dashboard_v2.html lines 1155–1177 demonstrates the exact z-index ladder. `[CITED: Dashboard_v2.html lines 1155-1177]` |
| Sparkline rendering | Adding sparkline.js / Chart.js / d3-tiny | Server-rendered inline SVG `<svg><path d="..."/></svg>` (Jinja macro) | One-time render; HTMX swaps preserve it; no JS asset cost; no per-mount initialization. D-UIF-09 locks this. |
| Form association of popover inputs | Wrapping the popover inside a `<form>` | `<input form="form-id">` attribute on inputs that live outside the form's DOM tree | Browser DOM API; HTMX auto-includes form-associated controls via `getInputValues()` (proven in `_picker_popover.html`'s gap-2 closure 2026-04-27). `[VERIFIED: app_v2/templates/browse/_picker_popover.html line 113]` |
| Markdown → HTML rendering for showcase text | DIY string templating | Plain Jinja templating; markdown is overkill for static showcase copy | Showcase content is hard-coded headings + sample chips; no markdown source. |
| Date input widget | jQuery datepicker / flatpickr / luxon | Native `<input type="date">` | Browser-native; mobile-friendly; no asset cost; UI-SPEC §New Jinja Macros pins `<input type="date">` per Dashboard_v2.html line 144. `[CITED: Dashboard_v2.html line 144]` |
| Avatar / brand-mark gradient | SVG asset + CDN | Inline `linear-gradient(135deg, #3366ff, #5e7cff)` in CSS rule | Dashboard_v2.html lines 35–36 + 46. Single CSS rule. Zero asset weight. |
| Sample data fixtures | YAML / JSON fixture file | Hard-code Python dicts inside `routers/components.py` | UI-SPEC §New Jinja Macros §showcase.html line 322: "All sample data hard-coded inline". Showcase is a one-off; fixtures add indirection. |

**Key insight:** Phase 4 is a **pure CSS-and-Jinja port**. Every "would I need a JS lib for this?" question lands on `no` because (a) `position: sticky` handles the only complex layout primitive, (b) Bootstrap dropdown handles the only stateful UI behavior, (c) inline SVG handles the only data-vis primitive, and (d) Jinja macros + Pydantic models handle parameterization. The 30-line `chip-toggle.js` is the entirety of NEW client-side code.

## Migration Strategy (load-bearing — resolves the UI-SPEC contradiction)

> **THE PLANNER MUST READ THIS BEFORE WRITING ANY TEMPLATE EDIT.**

UI-SPEC contains two statements that contradict each other:
- **§Component Inventory line 242** (researcher's pinned discretion): *"`.ph` is a NEW class, NOT a rename. The existing `.panel-header` rules stay untouched … New primitives emit `.ph`; existing callers are MIGRATED from `.panel-header` to `.ph` …"*
- **§Migration: Existing Surfaces line 411–413**: *"Migrate to `class=\"ph\"`. … Template tests that grep for `panel-header` must be updated."*

The first half of line 242 (".ph is NEW, NOT a rename, existing rules stay") preserves the D-UI2-12 `.panel-header .panel-title { font-size: 18px; ... }` rule. The second half of line 242 plus line 411–413 says to rewrite all callers AND update the tests, which **invalidates Phase 02 invariants** that pin `<div class="panel-header"` byte-stably:

| Test | File | Line | Asserts |
|------|------|------|---------|
| `test_browse_panel_header_byte_stable` | `tests/v2/test_phase02_invariants.py` | 403–409 | `<b>Browse</b>` AND `<span class="tag">Pivot grid</span>` inside browse `panel-header` |
| `test_count_oob_inside_panel_header` | `tests/v2/test_phase02_invariants.py` | 617–646 | `<span id="overview-count"` appears AFTER `<div class="panel-header"` literal |
| `test_filter_bar_after_panel_header` | `tests/v2/test_phase02_invariants.py` | 669–679 | filter-bar include after `<div class="panel-header"` literal |
| `test_no_count_in_panel_footer` | `tests/v2/test_phase02_invariants.py` | 842–847 | exactly 2 occurrences of count span — receiver in panel-header + emitter |
| `test_panel_title_rule` | `tests/v2/test_phase02_invariants.py` | 178–195 | `.panel-header .panel-title { font-size: 18px; font-weight: 700; margin: 0; }` exists in `app.css` |

**The planner's resolution (RESEARCHER'S RECOMMENDATION):**

1. **Add `.ph` as a NEW class in `app.css` with rules verbatim from Dashboard_v2.html lines 118–121** (with normalized 16px 24px padding per UI-SPEC §Spacing). Keep all existing `.panel-header` rules untouched (they continue to apply to existing surfaces).

2. **NEW partials emit `<div class="ph">…</div>`** (e.g., the new `_components/page_head.html`'s side panel headers used in showcase, the showcase sections themselves).

3. **EXISTING `<div class="panel-header">` markup in `browse/index.html`, `overview/index.html`, `joint_validation/detail.html`, `ask/index.html`, `platforms/_edit_panel.html` STAYS AS-IS.** No rename. No edits. This preserves all Phase 02 invariants and D-UI2-12 byte-stably.

4. **The visual outcome is identical** — both `.ph` and `.panel-header` render at the same padding / flex / border (the rules can be authored to be byte-equivalent).

5. **Optional follow-up phase** (post-Phase 4): if the planner deems the dual-class duplication ugly, a future migration phase can do the controlled rename with proper test rewrites. NOT this phase.

This resolution is consistent with D-UIF-05 (`_picker_popover.html` byte-stable) — both decisions exist because Phase 02 made deliberate byte-stability locks, and Phase 4 should not be the phase that breaks them.

**Tests that DO need to update for D-UIF-06 (topbar replacement)** — these are the unavoidable test edits, since the topbar markup itself is being replaced:

| Test | File | Line | What to update |
|------|------|------|----------------|
| `test_navbar_padding_override` | `tests/v2/test_phase02_invariants.py` | 154–174 | DELETE — `.navbar { padding: 16px 0 }` rule is removed when navbar is replaced |
| `test_*nav-tabs*` | `tests/v2/test_main.py` | 31–61, 124–146, 196–209 | UPDATE — assert on `class="topbar"` + `class="tabs"` + `class="tab"` instead; aria-selected="true" instead of `active` class |
| `test_*navbar-brand*` | `tests/v2/test_main.py` | 145, 196, 209 | UPDATE — assert on `class="brand"` + `class="brand-mark"` instead |

These updates are scoped, byte-localized, and the planner should plan them as part of the topbar replacement task — NOT as a separate test-rewrite task. The tests are checking "shell renders as expected"; they need to ride with the shell change.

## Common Pitfalls

### Pitfall 1: `.page-title` font-weight 800 silently degrades to 700 (or worse)

**What goes wrong:** `app.css` line 44 already declares `.page-title { font-weight: 800 }`. `tokens.css` line 42 declares the font-family stack as `"Inter Tight", system-ui, ...`. **`base.html` has zero `<link>` to Google Fonts.** System fallback fonts (Segoe UI on Windows, system-ui on Linux/Mac) typically max out at weight 700 — so weight 800 silently rounds down or blacks the glyph.

**Why it happens:** The Helix prototype loads Inter Tight via `<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700;800...">`. PBM2 inherited the `font-family` declaration but not the `<link>`.

**How to avoid:** UI-SPEC §Font Loading Fix is correct. ADD this to `base.html` `<head>` BEFORE `<link href="…tokens.css">`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
```
**Caveat:** PBM2 is intranet-deployed (`.planning/PROJECT.md` Constraints). If outbound access to fonts.googleapis.com is unreliable, plan a vendored-font fallback (download woff2 files into `app_v2/static/vendor/fonts/`, swap `<link>` for a local `@font-face`). Researcher recommends: **try Google Fonts first** (Helix prototype uses CDN; intranet usually allows fonts.googleapis.com), but the planner should add a brief test that confirms the link is present and document the vendored-fallback path in PLAN comments.

**Warning signs:** Compare `.page-title` rendering before vs after the link is added. Title visibly thickens at weight 800 with Inter Tight loaded; falls back to ~700-equivalent system rendering without it.

`[VERIFIED: codebase grep — no Google Fonts link in base.html]` `[CITED: Dashboard_v2.html line 9]`

### Pitfall 2: Replacing `<nav class="navbar">` cascades into 5+ test failures

**What goes wrong:** `tests/v2/test_main.py` asserts `assert "nav nav-tabs" in r.text` (line 32), `assert "navbar-brand" not in body` (lines 145, 196), and `assert "navbar-brand" in body` (line 209). `tests/v2/test_phase02_invariants.py::test_navbar_padding_override` asserts the `.navbar { padding-top: 16px }` rule.

**Why it happens:** The Helix topbar is fundamentally different markup — `<div class="topbar">`, no `nav-tabs`, no `navbar-brand`. The replacement is correct per D-UIF-06 but breaks 5+ test assertions.

**How to avoid:** Plan the topbar swap as a SINGLE atomic task that:
1. Edits `base.html` to swap `<nav class="navbar...">…</nav>` for `{% from "_components/topbar.html" import topbar %}{{ topbar(active_tab=active_tab|default("")) }}`
2. Removes the `.navbar { padding: 16px 0 }` rule from `app.css`
3. Updates `tests/v2/test_main.py` assertions to check for the NEW topbar markers (`class="topbar"`, `class="brand"`, `class="brand-mark"`, `class="tab"` + `aria-selected="true"`)
4. Removes (or rewrites) `tests/v2/test_phase02_invariants.py::test_navbar_padding_override`

The `test_main.py` tests for HTMX 404 / 500 fragments asserting `navbar-brand not in body` (lines 145, 196) should update to assert `class="topbar" not in body` — the contract being verified is "fragment responses are not full pages", which still holds.

**Warning signs:** Test failures in `test_main.py` after the topbar swap. If the planner sees these AND has not updated assertions, the swap is half-done.

`[VERIFIED: tests/v2/test_main.py lines 31, 145, 196, 209]` `[VERIFIED: tests/v2/test_phase02_invariants.py line 154-174]`

### Pitfall 3: Bootstrap `.dropdown-menu` 10rem default min-width clips the 300px Helix popover

**What goes wrong:** Bootstrap 5 dropdowns default to `min-width: 10rem` (160px). Helix `.pop` is 300px. If `.pop` rules are authored without an explicit width / min-width override, Bootstrap's defaults can cause the popover to render at 160px and visibly cut off the chip-group rows.

**Why it happens:** Bootstrap's `--bs-dropdown-min-width: 10rem` cascades into `.dropdown-menu`. Helix CSS uses `.pop { width: 300px }` directly without the `.dropdown-menu` wrapper.

**How to avoid:** Author the CSS so `.dropdown-menu.pop { width: 300px; min-width: 300px; padding: 14px; ...}` — the `.pop` selector also targets when applied as a child of `.dropdown-menu`. Verify by visiting `/_components` and inspecting the rendered popover; width should match Dashboard_v2.html line 132 (`width: 300px`).

**Warning signs:** Popover renders narrower than expected; chip groups wrap at unexpected widths.

`[CITED: Bootstrap docs https://getbootstrap.com/docs/5.3/components/dropdowns/]` `[CITED: Dashboard_v2.html line 132]`

### Pitfall 4: Sparkline algorithm degenerate cases (constant data, single point, empty list)

**What goes wrong:** Naive sparkline algorithms compute `y = (val - min) / (max - min) * height` — when `max == min` (constant data) or `len(data) == 0` or `len(data) == 1`, this divides by zero or produces a single point with no path.

**Why it happens:** Real KPI data routinely flatlines (zero growth), is single-point (just-introduced metric), or empty (no data yet).

**How to avoid:** D-UIF-09 + UI-SPEC §sparkline.html lines 287–292 explicitly enumerate the three edge cases and the required output for each:
- `data` is empty / None → emit `<svg width="{width}" height="{height}"/>` with no paths
- `data` has exactly 1 element → emit a degenerate horizontal line at mid-height
- All elements equal → flat line at mid-height (`max - min == 0` ⇒ default y = height/2)

**Algorithm sketch (Jinja-friendly):**
```jinja
{% macro sparkline(data, width=90, height=26, color="var(--accent)") %}
  {%- if not data -%}
    <svg width="{{ width }}" height="{{ height }}" aria-hidden="true"/>
  {%- else -%}
    {%- set lo = data | min -%}
    {%- set hi = data | max -%}
    {%- set rng = (hi - lo) if hi != lo else 1 -%}
    {%- set pad = 2 -%}
    {%- set inner_h = height - 2 * pad -%}
    {%- set step = (width / (data|length - 1)) if data|length > 1 else 0 -%}
    {%- set points = [] -%}
    {%- for v in data -%}
      {%- set x = (loop.index0 * step) | round(2) -%}
      {%- set y = (pad + inner_h * (1 - ((v - lo) / rng))) | round(2) if hi != lo else (height / 2) -%}
      {%- set _ = points.append([x, y]) -%}
    {%- endfor -%}
    <svg width="{{ width }}" height="{{ height }}" viewBox="0 0 {{ width }} {{ height }}" aria-hidden="true">
      <path d="M{% for p in points %}{{ p[0] }} {{ p[1] }}{% if not loop.last %} L {% endif %}{% endfor %} L {{ width }} {{ height }} L 0 {{ height }} Z"
            fill="{{ color }}" opacity="0.12"/>
      <path d="M{% for p in points %}{{ p[0] }} {{ p[1] }}{% if not loop.last %} L {% endif %}{% endfor %}"
            fill="none" stroke="{{ color }}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  {%- endif -%}
{% endmacro %}
```
Note: Jinja's default lacks `min`/`max` filters in some older versions; verify `min` and `max` are registered (Jinja 3.x ships them). Alternative: pass `lo`/`hi` precomputed in the router/showcase and accept them as macro args.

**Warning signs:** Sparkline render fails silently (empty SVG) on constant data; or path becomes `M 0 NaN L 90 NaN`.

`[CITED: UI-SPEC lines 287-292]` `[VERIFIED: Jinja 3.x has min/max filters per https://jinja.palletsprojects.com/en/3.x/templates/#min]`

### Pitfall 5: Sticky-corner table z-index ladder cells leak background through scroll

**What goes wrong:** `position: sticky` on table cells without explicit `background-color` allows underlying scrolled content to bleed through the sticky cells.

**Why it happens:** Table cells are `transparent` by default; sticky-positioning doesn't change that.

**How to avoid:** Dashboard_v2.html lines 1155–1177 demonstrates the explicit z-index + background pattern:
```css
.table-sticky-corner thead th        { position: sticky; top: 0;      z-index: 2; background: #fafbfc; }
.table-sticky-corner thead th:first-child { left: 0; top: 0;          z-index: 3; background: #fafbfc; }  /* corner */
.table-sticky-corner tbody td:first-child { position: sticky; left: 0; z-index: 1; background: #fff; }   /* first column */
```
Two pieces are critical: (1) explicit `background:` on every sticky cell (no `transparent` fallback) and (2) the corner cell needs `z-index: 3` to draw OVER both the thead row and the first-column. Body cells stay at default z-index (auto, behind the sticky cells).

**Warning signs:** Visible "ghost" text or color bleeding through the sticky thead during scroll. Open DevTools, inspect a sticky `<th>`, confirm computed `background-color` is non-transparent.

`[CITED: Dashboard_v2.html lines 1155-1177]`

### Pitfall 6: jinja2-fragments `block_names=[...]` does NOT include `{% from %}` imports inside skipped blocks

**What goes wrong:** When `routers/components.py` does `templates.TemplateResponse("_components/showcase.html", ...)` (a normal full render), `{% from "_components/topbar.html" import topbar %}` works fine. But if a future router renders `_components/showcase.html` with `block_names=["section_kpi"]`, and the import statement is at the top of the template (outside any block), the macro might be invisible inside `section_kpi` — the same Phase 01 Pitfall 8 pattern. **Phase 4 showcase is rendered as a full template by `GET /_components`**, so this pitfall doesn't bite directly. But document it for future maintainers.

**How to avoid:** Always render the showcase as a full template; do NOT use `block_names` filter on the showcase route.

**Warning signs:** N/A this phase — but future phases that try to fragment-render the showcase will hit it.

`[VERIFIED: app_v2/templates/overview/index.html lines 50-71]`

### Pitfall 7: Bootstrap dropdown re-initialization after HTMX swap

**What goes wrong:** When HTMX replaces a region containing a Bootstrap dropdown trigger via `hx-swap="outerHTML"`, the `data-bs-toggle="dropdown"` attribute on the new element is detected by Bootstrap's MutationObserver IF Bootstrap is loaded with the bundle (which includes Popper). Without the bundle, dropdowns initialized via `new bootstrap.Dropdown(el)` go stale.

**Why it happens:** PBM2 vendors `bootstrap.bundle.min.js` (verified via `app_v2/static/vendor/bootstrap/`). The bundle includes Popper and auto-detects new `data-bs-toggle="dropdown"` elements via event delegation, NOT MutationObserver — so newly-swapped triggers Just Work because clicks on `data-bs-toggle="dropdown"` are handled at the document level.

**How to avoid:** Ensure `bootstrap.bundle.min.js` (NOT `bootstrap.min.js`) is the loaded variant. `[VERIFIED: app_v2/templates/base.html line 21 — uses bootstrap.bundle.min.js]`. New popovers added by HTMX swaps will work without manual re-init.

**Warning signs:** Dropdown trigger rendered after HTMX swap doesn't open on click. If observed: confirm `bootstrap.bundle.min.js` is loaded, not `bootstrap.min.js`.

`[VERIFIED: app_v2/templates/base.html line 21]`

### Pitfall 8: `chip-toggle.js` global click delegation conflicts with `popover-search.js`

**What goes wrong:** `popover-search.js` already uses `document.addEventListener('click', onClearClick, true)` (capture phase) for `.popover-clear-btn`. If `chip-toggle.js` also registers a global click listener for `.pop .opt`, both listeners fire on every click; selectors must be precise.

**Why it happens:** Both files use document-level event delegation as a deliberate pattern (works for HTMX-swapped content).

**How to avoid:** Use precise selectors. `chip-toggle.js` matches ONLY `e.target.closest('.pop .opt')`, with an early return if `e.target.closest('.popover-search-root')` matches (the existing search popover, where `.opt` does not appear). Document the boundary in code comments.

**Sketch:**
```javascript
// app_v2/static/js/chip-toggle.js
(function () {
  "use strict";
  function onChipClick(e) {
    var opt = e.target.closest('.pop .opt');
    if (!opt) return;
    // Skip clicks inside the existing checkbox-list popover-search-root
    // (D-UI2-09 byte-stable). The chip-toggle popover uses .pop without that root.
    if (opt.closest('.popover-search-root')) return;
    e.preventDefault();
    opt.classList.toggle('on');
    var hidden = opt.querySelector('input[type=hidden]')
              || opt.parentElement.querySelector('input[type=hidden][data-opt="' + opt.dataset.value + '"]');
    if (hidden) hidden.value = opt.classList.contains('on') ? '1' : '';
  }
  document.addEventListener('click', onChipClick, true);
})();
```

**Warning signs:** Clicking a chip clears the search popover or vice-versa.

`[VERIFIED: app_v2/static/js/popover-search.js lines 28-61]`

## Code Examples

### Bootstrap dropdown wrapping arbitrary popover content (date-range)

```jinja
{# app_v2/templates/_components/date_range_popover.html #}
{% macro date_range_popover(form_id, field_prefix="date", quick_days=[7,14,30,60], start_val="", end_val="") %}
<div class="dropdown pop-wrap">
  <button class="btn btn-white btn-sm dropdown-toggle"
          type="button"
          data-bs-toggle="dropdown"
          data-bs-auto-close="outside"
          aria-expanded="false">
    Date range
  </button>
  <div class="dropdown-menu pop" style="width:300px;">
    <div class="pop-head">
      <span>Date range</span>
      <a href="#" data-action="reset">Reset</a>
    </div>
    <div class="qrow" role="group" aria-label="Quick ranges">
      {% for d in quick_days %}
        <button type="button"
                class="{% if (end_val and (end_val|length > 0)) %}{% endif %}"
                data-quick-days="{{ d }}">
          {{ d }}d
        </button>
      {% endfor %}
    </div>
    <div class="dates">
      <div>
        <label for="{{ form_id }}-{{ field_prefix }}-start">Start</label>
        <input type="date" id="{{ form_id }}-{{ field_prefix }}-start"
               name="{{ field_prefix }}_start" value="{{ start_val | e }}"
               form="{{ form_id }}">
      </div>
      <div>
        <label for="{{ form_id }}-{{ field_prefix }}-end">End</label>
        <input type="date" id="{{ form_id }}-{{ field_prefix }}-end"
               name="{{ field_prefix }}_end" value="{{ end_val | e }}"
               form="{{ form_id }}">
      </div>
    </div>
    <div class="foot">
      <button type="button" class="btn ghost btn-sm" data-action="reset">Reset</button>
      <button type="submit" form="{{ form_id }}" class="btn sm">Apply</button>
    </div>
  </div>
</div>
{% endmacro %}
```
Source pattern: `app_v2/templates/browse/_picker_popover.html` + Dashboard_v2.html lines 130–146. `[CITED: Dashboard_v2.html lines 130-146]`

### Filters popover (chip-group) — emits hidden inputs for form-association

```jinja
{# app_v2/templates/_components/filters_popover.html #}
{% macro filters_popover(form_id, groups, button_label="Filters") %}
<div class="dropdown pop-wrap">
  <button class="btn btn-white btn-sm dropdown-toggle"
          type="button"
          data-bs-toggle="dropdown"
          data-bs-auto-close="outside"
          aria-expanded="false">
    {{ button_label | e }}
  </button>
  <div class="dropdown-menu pop" style="width:300px;">
    <div class="pop-head">
      <span>Filters</span>
      <a href="#" data-action="reset">Reset Filters</a>
    </div>
    {% for grp in groups %}
      <div class="grp">
        <div class="grp-l">{{ grp.label | e }}</div>
        <div class="opts">
          {% for opt in grp.options %}
            <button type="button"
                    class="opt {% if opt.on %}on{% endif %}"
                    data-value="{{ opt.value | e }}">
              {{ opt.label | e }}
            </button>
            <input type="hidden"
                   name="{{ grp.label | lower | replace(' ', '_') }}"
                   value="{% if opt.on %}{{ opt.value | e }}{% endif %}"
                   data-opt="{{ opt.value | e }}"
                   form="{{ form_id }}">
          {% endfor %}
        </div>
      </div>
    {% endfor %}
    <div class="foot">
      <button type="button" class="btn ghost btn-sm" data-action="reset">Reset</button>
      <button type="submit" form="{{ form_id }}" class="btn sm">Apply Filters</button>
    </div>
  </div>
</div>
{% endmacro %}
```
Source: UI-SPEC §Component Inventory + Dashboard_v2.html lines 147–152. `[CITED: Dashboard_v2.html lines 147-152]`

### Sticky-corner table CSS

```css
/* app.css — append */
.table-sticky-corner {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.table-sticky-corner thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #fafbfc;
  text-align: left;
  padding: 10px 14px;
  font-size: 11px;
  color: var(--mute);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .04em;
  border-bottom: 1px solid var(--line);
  white-space: nowrap;
}
.table-sticky-corner thead th:first-child {
  left: 0;
  z-index: 3;                    /* corner — above thead AND first column */
}
.table-sticky-corner tbody td:first-child {
  position: sticky;
  left: 0;
  z-index: 1;
  background: #fff;
  border-right: 1px solid var(--line);
}
.table-sticky-corner tbody td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
}
```
Source: Dashboard_v2.html lines 1155–1177 (verbatim z-index ladder). The wrapping container needs `overflow: auto; max-height: 560px` (or similar) — Dashboard_v2.html line 1151. `[CITED: Dashboard_v2.html lines 1151-1177]`

### Showcase route

```python
# app_v2/routers/components.py
"""Phase 4 — UI Foundation: GET /_components showcase route (D-UIF-02).

Renders every Phase 4 primitive with realistic sample data. Always-on (NOT
dev-gated). Acts as the live design reference for downstream phases and as
the locus for invariant tests. Sample data is hard-coded inline per
UI-SPEC §showcase.html.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app_v2.services.hero_spec import HeroSpec, HeroSegment, HeroSideStat
from app_v2.templates import templates

router = APIRouter()


@router.get("/_components", response_class=HTMLResponse)
def components_showcase(request: Request) -> HTMLResponse:
    """Render the components showcase page."""
    hero_full = HeroSpec(
        label="Active validations",
        big_number=128,
        big_number_unit="open",
        delta_text="+12 this week",
        segments=[
            HeroSegment(label="Pending", value=44, color="var(--accent)"),
            HeroSegment(label="In progress", value=36, color="var(--green)"),
            HeroSegment(label="Blocked", value=20, color="var(--red)"),
        ],
        side_stats=[
            HeroSideStat(key="Avg cycle time", value="4d 2h", tone="default"),
            HeroSideStat(key="Overdue", value="7", tone="red"),
            HeroSideStat(key="Closed this week", value="22", tone="green"),
        ],
    )
    hero_minimal = HeroSpec(
        label="Total platforms",
        big_number=42,
        big_number_unit=None,
        delta_text=None,
        segments=[],
        side_stats=[],
    )
    kpi_data = [
        {"label": "Open", "value": 128, "unit": "", "delta": "+12", "delta_tone": "up", "spark_data": [10, 14, 18, 22, 30, 28, 36]},
        {"label": "Closed", "value": 218, "unit": "", "delta": "+22", "delta_tone": "ok", "spark_data": [12, 18, 16, 24, 28, 32, 38]},
        {"label": "Overdue", "value": 7, "unit": "", "delta": "−3", "delta_tone": "down", "spark_data": [9, 8, 11, 12, 10, 8, 7]},
        {"label": "Avg cycle", "value": "4d 2h", "unit": "", "delta": "flat", "delta_tone": "flat", "spark_data": None},
    ]
    return templates.TemplateResponse(
        request,
        "_components/showcase.html",
        {
            "request": request,
            "active_tab": "showcase",
            "hero_full": hero_full,
            "hero_minimal": hero_minimal,
            "kpi_data": kpi_data,
            # Date range + filters sample data inline in the template.
        },
    )
```
Mounted in `main.py` BEFORE `root.router`:
```python
from app_v2.routers import components
# ... after the other include_router() calls ...
app.include_router(components.router)
app.include_router(root.router)  # catch-all goes LAST
```

`[VERIFIED: app_v2/routers/joint_validation.py pattern]` `[VERIFIED: app_v2/main.py lines 207-214]`

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bootstrap navbar with `.nav-tabs` | Custom `.topbar` + `.tabs` shape | Phase 4 (this) | Topbar visually distinct; matches Helix; tests update inline |
| `.panel-header` everywhere | `.ph` for new surfaces; `.panel-header` byte-stable on existing | Phase 4 (this) | Dual-class period; no callers change; future phase consolidates |
| Plotly micro-charts in tables | Inline SVG sparklines | Phase 4 (this) | Zero JS cost; HTMX-safe; deterministic render |
| JS-driven sticky-column tables | Pure CSS `position: sticky` z-index ladder | Phase 4 (this; class shipped, not retrofitted to Browse) | Zero JS; survives any swap |
| `_picker_popover.html` for both pickers and chip-group filters | `_picker_popover.html` (checkbox list) + `filters_popover.html` (chip group) — siblings | Phase 4 (this) | Both primitives coexist; D-UI2-09 byte-stable |
| System-fallback fonts | Inter Tight via Google Fonts CDN | Phase 4 (this) | `.page-title` weight 800 actually renders weight 800 |

**Deprecated/outdated:** None — no Phase 4 decision deprecates an existing pattern. The closest is the topbar markup (the old `.navbar` markup is replaced, not "deprecated" — replaced wholesale).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Intranet deployment can reach `fonts.googleapis.com` | Pitfall 1 | Page renders with system-fallback fonts; `.page-title` weight 800 silently wrong. Mitigation: document the vendored-font fallback path in PLAN. |
| A2 | Phase 02 invariant tests are the only ones pinning `class="panel-header"` | Migration Strategy | If other tests pin it, the alias-not-rename path still works (existing markup unchanged); just more tests survive. NO downside risk. |
| A3 | Bootstrap 5.3.8's `.dropdown-menu` accepts arbitrary `width` style override without breaking the Popper positioning | Pitfall 3 | Popover may misalign or clip on narrow viewports. Validation: visit `/_components` after CSS lands; verify popover anchors correctly. |
| A4 | Jinja's `min` and `max` filters are registered in the project's Jinja2 version | Pitfall 4 | Sparkline macro raises a runtime error. Mitigation: pass `lo`/`hi` as macro args computed in the router, OR use `data | sort | first` / `data | sort | last`. |
| A5 | Existing `bootstrap.bundle.min.js` (not vanilla `bootstrap.min.js`) handles document-level click delegation for newly-swapped `data-bs-toggle="dropdown"` triggers | Pitfall 7 | Newly-swapped popovers don't open on click. **Verified** via the existing `_picker_popover.html` working under HTMX OOB swaps in Phase 02. Risk: LOW. |

**The planner / discuss-phase should re-confirm A1 explicitly with the user before building** — intranet font reachability is a deployment-environment fact, not a code fact, and the user is the only authority on it.

## Open Questions

1. **Will fonts.googleapis.com be reachable from the intranet target deployment?**
   - What we know: PBM2 is intranet-deployed (PROJECT.md). Helix prototype was built with the assumption of CDN access.
   - What's unclear: Whether the target intranet permits outbound HTTPS to `fonts.googleapis.com` and `fonts.gstatic.com`.
   - Recommendation: Plan adds the CDN link first. If a smoke test fails (font weight 800 still falls back), a follow-up task adds vendored woff2 fonts under `app_v2/static/vendor/fonts/` + an `@font-face` override in `tokens.css`. This is a cheap, reversible fallback path.

2. **Where does `FilterGroup` / `FilterOption` live — sibling file `filter_spec.py` or inline in `hero_spec.py`?**
   - What we know: UI-SPEC says "or inline in showcase". `HeroSpec` is in `hero_spec.py`.
   - What's unclear: Single-file co-location vs. clean separation.
   - Recommendation: `app_v2/services/filter_spec.py` (separate file). Cleaner imports for downstream phases; mirrors the established one-concept-per-file convention in `services/`.

3. **Does the showcase page need its own active_tab key, or should it render with no tab active?**
   - What we know: UI-SPEC §Showcase Route says `active_tab="showcase"` — the topbar then renders no tab as active because no tab matches `"showcase"`.
   - What's unclear: Nothing — this is a clean resolution.
   - Recommendation: Use `active_tab="showcase"`. The `topbar` macro emits `aria-selected="true"` only when the tab id matches; "showcase" matches none of overview/browse/ask, so all tabs render in their default unselected state. This is correct.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Node.js | gsd-tools.cjs init | ✓ | v24.11.1 | — |
| Python 3 | FastAPI runtime | ✓ | 3.13.7 | — |
| Bootstrap 5 | Dropdown component, utilities | ✓ (vendored) | 5.3.8 | — |
| HTMX | Form submit, OOB swaps | ✓ (vendored) | 2.0.10 | — |
| Bootstrap Icons | `bi-*` icons | ✓ (vendored) | 1.13.1 | — |
| Inter Tight font | `.page-title` weight 800, `.brand-mark` weight 800 | **✗** (NOT loaded) | n/a | Use vendored woff2 + `@font-face` if Google Fonts CDN is unreachable |
| JetBrains Mono font | `.mono` class | ✗ (NOT loaded) | n/a | Same fallback as above |
| jinja2 + jinja2-fragments | Template rendering | ✓ (existing pin) | per requirements.txt | — |
| Pydantic v2 | View-model | ✓ (existing pin) | per requirements.txt | — |
| FastAPI | Router | ✓ (existing pin) | per requirements.txt | — |

**Missing dependencies with no fallback:** None. Both fonts are missing-with-fallback (planner adds Google Fonts link; vendor as backup if CDN blocked).

**Missing dependencies with fallback:**
- Inter Tight + JetBrains Mono fonts: primary fix is Google Fonts CDN link in `base.html` (UI-SPEC §Font Loading Fix); vendored woff2 + `@font-face` is the intranet-fallback path.

## Validation Architecture

> `.planning/config.json` was not found, so default-enabled per the spec: include this section.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing project pin) + FastAPI `TestClient` |
| Config file | `pyproject.toml` / `setup.cfg` (existing — verified by presence of `tests/v2/conftest.py`) |
| Quick run command | `pytest tests/v2/test_phase04_invariants.py -x -q` |
| Full suite command | `pytest tests/v2/ -q` |

`[VERIFIED: tests/v2/conftest.py exists; tests/v2/test_phase02_invariants.py is the established invariant pattern]`

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| D-UIF-01 | Browse / JV `panel-header` markup byte-stable (alias-not-rename path) | invariant | `pytest tests/v2/test_phase02_invariants.py -x` | ✅ existing |
| D-UIF-02 | `GET /_components` returns 200 with all sections present | route | `pytest tests/v2/test_phase04_components.py::test_showcase_renders -x` | ❌ Wave 0 |
| D-UIF-02 | Showcase exercises every macro arg path (full hero + minimal hero, KPI 4-up + 5-up, all chip variants, popovers, sticky table) | invariant | `pytest tests/v2/test_phase04_components.py::test_showcase_sections -x` | ❌ Wave 0 |
| D-UIF-03 | Both new popovers use `class="dropdown-menu pop"` + `data-bs-auto-close="outside"` | invariant | `pytest tests/v2/test_phase04_components.py::test_popovers_use_bootstrap_dropdown -x` | ❌ Wave 0 |
| D-UIF-04 | `filters_popover.html` macro emits `.grp` / `.grp-l` / `.opts` / `.opt` markup | invariant | `pytest tests/v2/test_phase04_components.py::test_filters_popover_chip_markup -x` | ❌ Wave 0 |
| D-UIF-05 | `_picker_popover.html` byte-stable (no edits) | invariant | `pytest tests/v2/test_phase04_components.py::test_picker_popover_byte_stable -x` | ❌ Wave 0 |
| D-UIF-06 | `base.html` topbar contains `class="topbar"`, `class="brand"`, `class="brand-mark"` with letter "P", `class="av"` with "PM" | invariant | `pytest tests/v2/test_main.py::test_topbar_helix_shape -x` | ❌ Wave 0 (replaces existing nav-tabs assertions) |
| D-UIF-06 | No `class="navbar"` and no `class="navbar-brand"` in `base.html` | invariant | `pytest tests/v2/test_main.py::test_no_legacy_navbar -x` | ❌ Wave 0 |
| D-UIF-07 | Topbar renders 3 tabs: Joint Validation / Browse / Ask with correct `href` | invariant | `pytest tests/v2/test_main.py::test_topbar_tabs_roster -x` | ❌ Wave 0 |
| D-UIF-08 | Each `_components/*.html` macro file exports a single `{% macro %}` with the filename | invariant | `pytest tests/v2/test_phase04_components.py::test_macro_per_file -x` | ❌ Wave 0 |
| D-UIF-09 | `sparkline()` handles empty / single / constant data without crash | unit | `pytest tests/v2/test_phase04_components.py::test_sparkline_edge_cases -x` | ❌ Wave 0 |
| D-UIF-10 | `app.css` contains `.table-sticky-corner` rule with `position: sticky` and `z-index: 3` for corner | invariant | `pytest tests/v2/test_phase04_components.py::test_sticky_corner_css -x` | ❌ Wave 0 |
| D-UIF-11 | `HeroSpec` Pydantic model: required fields validate; defaults work; `tone` Literal accepts only allowed values | unit | `pytest tests/v2/test_phase04_hero_spec.py -x` | ❌ Wave 0 |
| Pitfall 1 | `base.html` `<head>` contains the Inter Tight Google Fonts link | invariant | `pytest tests/v2/test_phase04_components.py::test_google_fonts_link_present -x` | ❌ Wave 0 |
| Pitfall 8 | `chip-toggle.js` exists and is a sibling (popover-search.js unchanged) | invariant | `pytest tests/v2/test_phase04_components.py::test_chip_toggle_js_sibling -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/v2/test_phase04_invariants.py tests/v2/test_phase04_components.py tests/v2/test_phase04_hero_spec.py -x -q` (~5–8 sec)
- **Per wave merge:** `pytest tests/v2/ -q` (full suite — ~30 sec on 442+ tests)
- **Phase gate:** Full suite green; manual visual check against `Dashboard_v2.html` at `/_components`; UAT items recorded in HUMAN-UAT.md

### Wave 0 Gaps

- [ ] `tests/v2/test_phase04_components.py` — covers D-UIF-02, D-UIF-03, D-UIF-04, D-UIF-05, D-UIF-08, D-UIF-09, D-UIF-10, Pitfall 1, Pitfall 8 (single test file with one class per primitive)
- [ ] `tests/v2/test_phase04_hero_spec.py` — covers D-UIF-11 (Pydantic model unit tests)
- [ ] `tests/v2/test_phase04_invariants.py` — covers the static `app.css` rule presence (mirrors `test_phase02_invariants.py` pattern)
- [ ] Update `tests/v2/test_main.py` — replace `nav-tabs` / `navbar-brand` assertions with topbar-shape assertions (D-UIF-06, D-UIF-07)
- [ ] Update `tests/v2/test_phase02_invariants.py::test_navbar_padding_override` — DELETE (the `.navbar` rule is removed when navbar is replaced)

## Sources

### Primary (HIGH confidence — verified in this session)

- **`/home/yh/Desktop/02_Projects/Proj27_PBM1_fork_bootstrap/Dashboard_v2.html` (1438 lines)** — visual reference; CSS lines 11–345; component usage lines 357–1432; sticky-corner table lines 1136–1206. Read directly. `[VERIFIED]`
- **`app_v2/static/css/tokens.css`** — full token list confirmed; `--font-size-h1 = 28px`, `--font-size-body = 15px` already present. `[VERIFIED]`
- **`app_v2/static/css/app.css`** — confirmed `.page-title` weight 800 already in use; `.panel-header` family rules present; `.ai-btn` / `.ai-chip` / `.chat-*` classes present. `[VERIFIED]`
- **`app_v2/templates/base.html`** — confirmed NO Google Fonts link; `bootstrap.bundle.min.js` loaded with `defer`. `[VERIFIED]`
- **`app_v2/templates/browse/_picker_popover.html`** — Bootstrap dropdown + `data-bs-auto-close="outside"` + form-association pattern. `[VERIFIED]`
- **`app_v2/static/js/popover-search.js`** — document-level click delegation pattern. `[VERIFIED]`
- **`app_v2/services/joint_validation_grid_service.py`** lines 106–137 — `PageLink` Pydantic submodel pattern. `[VERIFIED]`
- **`app_v2/main.py`** lines 207–214 — router registration order. `[VERIFIED]`
- **`app_v2/static/vendor/bootstrap/VERSIONS.txt`** — Bootstrap 5.3.8 confirmed. `[VERIFIED]`
- **`app_v2/static/vendor/htmx/VERSIONS.txt`** — HTMX 2.0.10 confirmed. `[VERIFIED]`
- **`tests/v2/test_phase02_invariants.py`** lines 154–195, 286, 286, 403–409, 617–646, 669–679, 842–847 — Phase 02 invariants pinning `class="panel-header"`, `.panel-header .panel-title` rule, `.navbar` padding rule. `[VERIFIED]`
- **`tests/v2/test_main.py`** lines 31–61, 124–146, 196–209 — assertions on `nav nav-tabs` and `navbar-brand` strings. `[VERIFIED]`

### Secondary (MEDIUM confidence — official docs cross-referenced)

- **Bootstrap 5.3 dropdowns** — https://getbootstrap.com/docs/5.3/components/dropdowns/ — `data-bs-auto-close="outside"`, custom width via `.dropdown-menu` width override, arbitrary content support. `[CITED]`
- **Jinja2 builtin filters** — https://jinja.palletsprojects.com/en/3.x/templates/#min — `min` and `max` filters available since Jinja 2.x. `[CITED]`
- **MDN `position: sticky`** — sticky-positioning model + z-index for nested sticky cells. `[CITED — well-documented browser behavior]`

### Tertiary (LOW confidence — flagged for validation)

- **fonts.googleapis.com reachability from intranet** — assumption A1; needs explicit user confirmation in discuss-phase or live-server smoke test.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dependency is already vendored or locked in existing requirements; no new runtime deps.
- Architecture (macros, Pydantic models, file layout): HIGH — mirrors existing patterns 1:1.
- Pitfalls: HIGH — Pitfalls 1, 2, 5, 7 are codebase-grep-verified; Pitfalls 3, 4, 6, 8 are reasoning from documented Bootstrap / Jinja behavior.
- Migration strategy resolution (alias-not-rename for `.ph`): HIGH — only path consistent with all locked decisions (D-UIF-01, D-UIF-05, D-UI2-09, D-UI2-12) and existing invariants.

**Research date:** 2026-05-03
**Valid until:** 2026-06-02 (30 days — Phase 4 is a stable visual port; the visual reference, vendored libraries, and existing codebase are all stable; revisit only if new tests land in `tests/v2/` that pin additional shell markup).
