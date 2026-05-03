---
phase: 04-ui-foundation-helix-aligned-shell-primitives-build-reusable
type: context
created: 2026-05-03
status: locked
---

# Phase 4: UI Foundation — Helix-aligned shell & primitives — Context

> **Decisions captured 2026-05-03 from interactive discuss-phase.** Anchored visually to `/home/yh/Desktop/02_Projects/Proj27_PBM1_fork_bootstrap/Dashboard_v2.html` (React prototype). Stack stays **Jinja + HTMX**; brand stays **PBM2** (not Helix). Decisions below are locked; researcher and planner may resolve only the items explicitly listed under *Claude's Discretion*.

<domain>
## Phase Boundary

**In scope (this phase):**

1. **CSS primitives** — extend `app_v2/static/css/app.css` with rules for: `.topbar`, `.brand`, `.brand-mark`, `.av`, `.tabs`, `.tab`, `.tab .count`, `.ph` (header inside panel), `.hero` (1.3:1 grid + 72 px stat number + segmented bar + side-stats), `.kpi` (4-up and 5-up grid variants + sparkline slot), `.chip` / `.chips` / `.pill` / `.tiny-chip`, popover infrastructure (`.pop`, `.pop-wrap`, `.pop-head`, `.pop .qrow`, `.pop .grp`, `.pop .opt`, `.pop .dates`, `.pop .foot`), and a sticky-corner table class that pins both `<thead>` and the first column. Tokens already in `tokens.css` are reused; only add new tokens (e.g., `--cyan`, `--cyan-soft`) if a primitive actually uses them.

2. **Jinja partials in `app_v2/templates/_components/`**:
   - `_components/topbar.html` — macro
   - `_components/page_head.html` — macro
   - `_components/hero.html` — macro (takes `HeroSpec`)
   - `_components/kpi_card.html` — macro (one macro, takes count/variant arg for 4-up vs 5-up)
   - `_components/sparkline.html` — macro (server-rendered inline SVG)
   - `_components/date_range_popover.html` — macro
   - `_components/filters_popover.html` — macro (chip-group multi-category popover)
   - `_components/showcase.html` — section template (used only by `/_components`)
   - Pills / chips / tiny-chips ship as **CSS only** — no macro (Claude's Discretion)

3. **Pydantic view-model** — `HeroSpec` Pydantic v2 model (location pinned by planner) feeding `hero` macro: `label`, `big_number`, `big_number_unit`, `delta_text`, `segments=[(label, value, color), ...]`, `side_stats=[(k, v, tone), ...]`. Type-checked at the router boundary; mirrors the existing `OverviewGridViewModel` / `PageLink` pattern.

4. **Showcase route** — new `app_v2/routers/components.py` mounts `GET /_components`, rendering `_components/showcase.html` which exercises every primitive with realistic sample data, sectioned by primitive. Exists for the lifetime of the app (not dev-gated). Acts as the live design reference for downstream phases and as the locus for invariant tests.

5. **Migration of the existing PBM2 surfaces** to the new primitives:
   - `templates/base.html` — replace the current `<nav class="navbar navbar-expand-lg navbar-light bg-light border-bottom">` with the new `topbar` macro. The active tab is passed via `active_tab` (already threaded by routers).
   - Existing `.panel-header` usages migrate to the new `.ph` class. The previously shipped `.panel-header .panel-title` rule keeps the JV `<h1>` rendering at the same 18 px / 700 weight (D-UI2-12 honored).
   - **Browse filter row stays untouched** (D-UI2-09 byte-stability). `_picker_popover.html` is **not** ported to the chip-group `filters_popover.html`.
   - **Browse pivot table keeps its current sticky-thead-only behavior.** The new sticky-first-column class is shipped + showcased but not retrofitted to Browse.
   - JV listing inherits the new topbar + page-head + `.ph` naming; the rest of D-UI2-07..14 (single panel, horizontal flex filter row, h1 + count in `.ph`, panel-footer pagination) is preserved byte-stable.
   - Ask page inherits the new topbar; chat surface CSS shipped in Phase 03 is preserved.

6. **HTMX wiring for popovers** — new popovers use Bootstrap 5 dropdown anchoring (already vendored). Apply submits a form with hidden inputs; state round-trips via `HX-Push-Url` exactly like the existing Browse picker.

**Out of scope (NOT this phase):**

- Tab counts wired to live data on the new `.tabs` strip. Primitive supports the slot; no router emits `nav_counts` yet.
- Env pill, notification bell, real per-user avatar. The avatar slot renders a static "PM" placeholder.
- Browse filter row migration from `_picker_popover.html` to `filters_popover.html` — deferred to a later phase if/when a chip-group filter is desired on Browse.
- Sticky-first-column retrofit on the Browse pivot table — deferred (the class ships and is showcased; no Browse markup change).
- Plotly micro-charts or any JS-driven sparklines. Sparklines stay server-rendered inline SVG.
- New Helix tabs (Tech Reports, Platform BM). PBM2 tabs roster stays Joint Validation / Browse / Ask.
- Empty-state primitive. `app_v2/templates/browse/_empty_state.html` stays Browse-specific; generalization waits for a third consumer.
- New auth, identity, env-config surfaces.

</domain>

<decisions>
## Implementation Decisions

> Decision IDs use a fresh `D-UIF-*` namespace ("UI Foundation") so they don't collide with `D-OV-*` (v2.0 Phase 5), `D-JV-*` (post-v2.0 Phase 1), `D-UI2-*` (post-v2.0 Phase 2), or `D-CHAT-*` (post-v2.0 Phase 3).

### Adoption Boundary

- **D-UIF-01: Phase 4 ships primitives, a `/_components` showcase route, AND migrates the global shell + panel-header naming on every existing surface (Browse / JV / Ask).** Refinements: Browse filter row is **not** retrofitted (its `_picker_popover.html` stays byte-stable per D-UI2-09); Browse pivot keeps its current sticky-thead-only behavior. Migration covers what's structurally compatible without breaking shipped contracts.
  - Why: User chose "Primitives + migrate everything" then later narrowed two specific items (picker popover, sticky-first-column) out of the migration. Net is "global shell + panel-header naming migrate; per-surface filter rows and pivots stay".
  - How to apply: Touch `base.html` topbar, every page's `.panel-header` → `.ph`, every page-head block. Do not touch `_picker_popover.html`, the Browse filter row HTML, or the Browse pivot table HTML.

### Showcase

- **D-UIF-02: New `GET /_components` route renders every primitive with realistic sample data on a single sectioned page.** Always-on (not dev-gated). Sections: Topbar, Page-head, Hero (full + minimal), KPI 4-up, KPI 5-up, Pills/Chips/Tiny-chips, Date-range popover, Filters popover (chip groups), Sticky-corner table. Acts as the live design reference for downstream phases.
  - Why: User chose "Full /_components showcase route". Single locus for verification + Nyquist invariant tests; downstream phases pick the right primitive by viewing this page.
  - How to apply: New `app_v2/routers/components.py` mounted in `main.py`. Template `_components/showcase.html` includes each section. Sample data hard-coded inline or in a small fixtures module — must be representative enough to exercise every macro arg, including edge cases (sparkline with single-element data, hero with zero side_stats, popover with no chip groups).

### Popover Interaction Model

- **D-UIF-03: Both new popovers (date-range, filters) use the Bootstrap 5 dropdown pattern, mirroring `_picker_popover.html` semantics.** Apply submits a form with hidden inputs; state round-trips via `HX-Push-Url`. Click-outside dismisses; focus trap on open.
  - Why: User chose "Bootstrap dropdown, mirroring Browse picker". Maximum reuse of an already-tested pattern; zero new JS framework.
  - How to apply: Each popover is a `<div class="dropdown"><button class="dropdown-toggle">...</button><div class="dropdown-menu pop">...</div></div>`. The `.pop` rules from Dashboard_v2.html are ported as Phase-4 CSS. The existing `static/js/popover-search.js` may need a sibling helper (or extension) for chip-toggle behavior; researcher decides whether to extend or duplicate.

- **D-UIF-04: `_components/filters_popover.html` is the new chip-group multi-category popover** (Type / Status / OEM / UFS-eMMC etc., each as a row of chip toggles + a "Reset all" link). Distinct from `_picker_popover.html` (checkbox list, single attribute). Both primitives coexist.
  - Why: User chose "Ship filters_popover.html only; defer Browse migration to a follow-up". The chip-group pattern is what Helix uses; the checkbox-list pattern is what Browse already ships and tests pin byte-stable.
  - How to apply: `filters_popover.html` macro takes `groups=[FilterGroup(label, options=[FilterOption(label, value, on)], ...)]`. Renders Helix's `.grp` / `.opts` / `.opt` / `.opt.on` markup. NOT a fork of `_picker_popover.html` — it lives next to it.

- **D-UIF-05: `_picker_popover.html` is byte-stable per D-UI2-09.** No edits, no refactor, no rename. Browse and JV continue importing it AS-IS.
  - Why: D-UI2-09 was locked in Phase 02; Browse and JV invariant tests grep against picker markup. Breaking it forces a cascade of test rewrites that adds nothing this phase.
  - How to apply: Treat the file as read-only. If a chip-group filter row is wanted on Browse later, that's a new phase that explicitly migrates Browse off the checkbox picker.

### Topbar

- **D-UIF-06: Full Helix topbar shape — gradient brand-mark with letter "P" + "PBM2" wordmark + horizontal tab strip + static `.av` avatar slot showing "PM".** No env pill, no notification bell, no live tab count badges. Avatar is a placeholder; no auth coupling.
  - Why: User chose "Full Helix topbar". The gradient brand-mark + wordmark + tab strip is the visual signature of the Helix design language; the avatar slot is structurally needed so future per-user identity has a place to land. Bell + env pill require live signals that don't exist yet.
  - How to apply: `topbar` macro takes `active_tab` (already threaded). Renders `<div class="topbar"><div class="brand"><div class="brand-mark">P</div><span>PBM2</span></div><div class="tabs">...</div><div class="top-right"><div class="av">PM</div></div></div>`. Tab `<button>` form vs `<a>` form — researcher's call; default `<a href>` to preserve full-page navigation (matches existing base.html convention; no hx-boost per Phase 1 Pitfall 8).

- **D-UIF-07: Tabs roster stays Joint Validation / Browse / Ask.** No new tabs introduced this phase. The macro signature accepts a list of tabs so the showcase can demonstrate variants, but the live `base.html` uses the existing trio.
  - Why: Adding Tech Reports / Platform BM would imply features that don't exist yet; gates the topbar primitive on real downstream work rather than design-driven scope creep.
  - How to apply: Tab list lives in the macro call inside `base.html`; researcher pins exact label / icon / href triples consistent with the existing nav.

### Component Pattern

- **D-UIF-08: Stateful primitives ship as Jinja MACROS; static partials use `{% include %}`.** Macros: `topbar`, `page_head`, `hero`, `kpi_card`, `sparkline`, `date_range_popover`, `filters_popover`. Includes: `_components/showcase.html` (section template).
  - Why: Macros allow per-call customization (active_tab, hero spec, kpi data) which every stateful primitive needs. Includes are simpler for the showcase that doesn't need parameterization. Mix matches the existing `_picker_popover.html` convention (macro form).
  - How to apply: Each macro file exposes a single `{% macro name(...) %}` matching the filename. Keyword-only args where possible for forward compatibility. Default values for visual parameters so most call sites pass only data.

### Sparkline

- **D-UIF-09: KPI-card sparkline = server-rendered inline SVG via Jinja macro.** Macro signature: `sparkline(data: list[int|float], width=90, height=26, color="#3366ff")`. Pure-Jinja polyline algorithm builds `<svg><path d="..."/></svg>` — no JS, no extra dependency.
  - Why: User chose "Server-rendered inline SVG". Matches "no React" constraint; no JS surface; cacheable; works inside HTMX swaps without re-mounting.
  - How to apply: Macro normalizes data to viewBox using min/max + 4 px padding; emits two `<path>` elements (filled area at 12% opacity + line stroke). Edge cases: empty data → `<svg/>`; single point → degenerate horizontal line; constant data → mid-height flat line. Color defaults to `--accent`; planner exposes the CSS-var fallback so future restyles don't need template edits.

### Sticky-Corner Table

- **D-UIF-10: Phase 4 ships a `.pivot-sticky-corner` class (or similar — researcher names) that pins `<thead>` AND the first `<td>`/`<th>` column.** Top-left corner cell is double-pinned. Showcase demos it on a small pivot fixture. Browse pivot is **not** retrofitted; its existing sticky-thead-only behavior is preserved.
  - Why: User chose "Add sticky-first-column class; not applied to Browse yet". Ships the capability without changing visible Browse behavior; retrofit risk lives in a future phase that owns the Browse pivot pixel diff.
  - How to apply: CSS uses `position: sticky` + `z-index` ladder (top-left `z-index: 3`, thead and first column `z-index: 2`, body cells `z-index: 1`). Background colors must be explicit (sticky cells reveal cells underneath). Researcher pins exact class name and z-index values.

### Hero Data Contract

- **D-UIF-11: `HeroSpec` is a Pydantic v2 view-model passed to the `hero` macro.** Fields: `label: str`, `big_number: int | float | str`, `big_number_unit: str | None`, `delta_text: str | None`, `segments: list[HeroSegment]` (optional, drives the segmented bar), `side_stats: list[HeroSideStat]` (optional, drives the side panel). `HeroSegment(label, value, color)`, `HeroSideStat(key, value, tone: Literal["default","green","red"])`.
  - Why: User chose "Pydantic HeroSpec view-model". Type-checked at the router boundary; mirrors `OverviewGridViewModel`, `PageLink`, `ChartSpec` pattern; refactor-safe.
  - How to apply: Submodel location pinned by planner (likely `app/core/models/` or `app_v2/services/`). Macro signature: `{% macro hero(spec) %}` reading `spec.label`, `spec.big_number`, etc. Showcase passes a hand-constructed `HeroSpec` instance. Empty / minimal hero supported by leaving `segments` and `side_stats` as empty lists; macro handles gracefully.

### Claude's Discretion

The researcher and planner may resolve these without re-asking the user:

- **KPI variants:** ONE `kpi_card` macro takes a count/variant arg (e.g., `variant="4-up"|"5-up"`) or the variant is implied by container CSS class. Researcher picks.
- **Pills / chips / tiny-chips:** CSS-only. No Jinja macros. Documented via showcase usage. (User folded this into discretion.)
- **Empty-state primitive:** NOT shipped. Existing `browse/_empty_state.html` stays Browse-specific; generalize later when JV or showcase needs it. (User folded this into discretion.)
- **Topbar tabs roster default content** (Joint Validation / Browse / Ask). No new tabs this phase. (User folded this into discretion.)
- Exact px values for `.topbar` height, `.ph` padding, `.hero` grid gap, `.kpi` spark size, `.pop` width. Researcher pins via UI-SPEC.md (if generated) or PLAN.md.
- `HeroSpec` submodel file location (likely `app/core/models/hero.py` or co-located with showcase view-model).
- Whether `.ph` is a NEW class or an alias for `.panel-header`. Researcher decides; if alias, existing `.panel-header` rules stay and `.ph` selectors are added; if rename, existing rules are renamed and `.panel-header` callers are updated to use `.ph`.
- Tab `<button>` vs `<a>` form in the topbar — default `<a href>` to match existing base.html and Phase 1 Pitfall 8 (no hx-boost on tab nav).
- Whether `popover-search.js` is extended or a sibling JS helper is added for chip-toggle behavior.
- Sticky-corner class name (`.pivot-sticky-corner` vs `.table-sticky-corner` vs another).
- Sample data values for the showcase fixtures (must exercise every macro arg path; content can be lorem-ipsum-ish).
- New tokens — add `--cyan`, `--cyan-soft` and any additional surface tokens only if a primitive uses them. Don't bulk-import all Helix tokens.
- Whether the `Inter Tight` font already loaded covers the Helix weight range (400/500/600/700/800). It does (per Dashboard_v2.html line 9 the Helix prototype loads exactly that range from Google Fonts) — verify and document.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Visual reference (mandatory)
- `/home/yh/Desktop/02_Projects/Proj27_PBM1_fork_bootstrap/Dashboard_v2.html` — full Helix React prototype establishing every primitive (lines 11-345 = CSS rules; lines 357-1432 = component usage). Use line numbers to anchor any pixel/spacing/color decision.
  - Lines 11-21 — token table (colors, ink hierarchy, semantic palette)
  - Lines 31-47 — `.shell` + `.topbar` + `.brand` + `.brand-mark` + `.av` + `.icon-btn`
  - Lines 49-61 — `.tabs` + `.tab` + `.tab .count` + `.live`/`.pulse`
  - Lines 63-67 — `.page-head` + `.page-title` + `.page-sub` + `.page-actions`
  - Lines 69-80 — `.btn` + variants (`.sec`, `.white`, `.ghost`, `.sm`, `.on`)
  - Lines 82-103 — `.hero` + `.hero-bar` + `.hero .side`
  - Lines 105-114 — `.kpis` + `.kpis.five` + `.kpi` + `.spark`
  - Lines 116-128 — `.panel` + `.ph` + `.chips` + `.chip`
  - Lines 130-152 — `.pop` + `.pop-wrap` + `.pop-head` + `.qrow` + `.dates` + `.foot` + `.grp` + `.opts` + `.opt`
  - Lines 173-181 — `.st` (status pills) + `.list-foot`
  - Lines 183-219 — `.jvt` (sticky-corner table styling) + `.pill` + `.typ` + `.oemchip` + `.ufschip` + `.lnk` + `.ai-btn`
  - Lines 263-268 — `.tiny-chip` and tone variants
  - Lines 1136-1206 — `Wide-form matrix` Platform BM table demonstrating sticky-first-column + sticky-corner z-index ladder

### Phase predecessors (mandatory)
- `.planning/phases/02-ui-shell-rewrite-browse-footer-joint-validation-layout-parit/02-CONTEXT.md` — D-UI2-01..D-UI2-14 carried forward; especially **D-UI2-04** (type scale tokens — DO NOT churn), **D-UI2-05** (sticky-in-flow footer pattern; topbar lives above this), **D-UI2-09** (`_picker_popover.html` byte-stable — D-UIF-05 honors), **D-UI2-12** (JV `<h1>` styling rule pinned via `.panel-header .panel-title`).
- `.planning/phases/01-overview-tab-auto-discover-platforms-from-html-files/01-CONTEXT.md` — D-JV-01..D-JV-17. Most relevant: D-JV-01 (top-nav label "Joint Validation") — the new topbar macro must surface this label exactly.
- `.planning/phases/03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on/03-CONTEXT.md` — D-CHAT-01..D-CHAT-15. Most relevant: D-CHAT-04 (error vocabulary), D-CHAT-05 (Plotly server-rendered) — Ask page-head migration must not break Plotly extra_head + chat surface CSS.
- `.planning/PROJECT.md` — Constraints (FastAPI + Bootstrap + HTMX, no React) and the Phase 02 type-scale lock.

### Existing code to read before planning
- `app_v2/templates/base.html` — current navbar shape; the topbar migration target.
- `app_v2/static/css/tokens.css` — full token list; D-UI2-04 type scale already present.
- `app_v2/static/css/app.css` — current `.shell` (line 40), `.panel` family (lines 51-74), `.page-head` family (lines 43-46), `.browse-filter-bar` (line 150), `.overview-filter-bar` (line 247), `.pivot-table` family (lines 188-223), `.overview-table` family (lines 258-294), `.ai-btn` (lines 92-115), `.ai-chip` (lines 304-330), chat surface (lines 348-540).
- `app_v2/templates/browse/_picker_popover.html` — D-UI2-09 byte-stable contract. Read but DO NOT modify.
- `app_v2/templates/browse/index.html`, `_filter_bar.html`, `_grid.html`, `_empty_state.html`, `_warnings.html` — Browse panel shape; touch only `.panel-header` → `.ph` if researcher chooses rename path.
- `app_v2/templates/overview/index.html`, `_filter_bar.html`, `_grid.html`, `_pagination.html` — JV panel shape; same `.panel-header` → `.ph` consideration.
- `app_v2/templates/ask/index.html` and partials — Ask shell; topbar inheritance test surface.
- `app_v2/static/js/popover-search.js` — existing dropdown helper; decide extend vs duplicate for chip-toggle behavior.
- `app_v2/main.py` — router mount point for the new `routers/components.py`.

### Stack docs (no remote fetch needed; all vendored)
- Bootstrap 5 vendored at `app_v2/static/vendor/bootstrap/` — `.dropdown` / `.dropdown-menu` / `.dropdown-toggle` patterns for the new popovers.
- HTMX 2.0.10 vendored at `app_v2/static/vendor/htmx/` — `HX-Push-Url`, OOB swaps, `hx-vals` already used; popover Apply uses the same patterns.

### User memory (load-bearing)
- `~/.claude/projects/-home-yh-Desktop-02-Projects-Proj28-PBM2/memory/feedback_design_anchor.md` — "anchor v2.0 frontend grey areas to Dashboard_v2.html design language". Phase 4 IS this anchoring.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`tokens.css`** — `--bg`, `--panel`, `--ink`, `--ink-2`, `--mute`, `--dim`, `--line`, `--line-2`, `--accent`, `--accent-soft`, `--accent-ink`, `--green`, `--green-soft`, `--red`, `--red-soft`, `--amber`, `--amber-soft`, `--violet`, `--violet-soft`, `--radius-panel: 22px`, `--radius-card: 16px`, `--radius-btn: 10px`, `--radius-pill: 999px`, `--shadow-panel`, `--font-size-logo: 20px`, `--font-size-h1: 28px`, `--font-size-th: 12px`, `--font-size-body: 15px`. Phase 4 needs to add: `--cyan`, `--cyan-soft` IF any primitive uses them (Helix has them in lines 19-20 — likely needed by the chat or AI thread sidebar later, not Phase 4).
- **`app.css`** — already covers: body flex column + sticky-in-flow footer (D-UI2-05), `.panel` / `.panel-header` / `.panel-body` / `.panel-footer` (D-UI2-07..12), `.page-head` / `.page-title` / `.page-sub` / `.page-actions` (D-UI2-04), `.ai-btn` / `.ai-chip` / `.btn-stop` (Dashboard verbatim). Phase 4 adds the topbar/brand/tabs/hero/kpi/chip/pop/sticky-corner rules on top.
- **`_picker_popover.html`** — Bootstrap dropdown checkbox-list popover. D-UI2-09 byte-stable. **Do not edit.** New `filters_popover.html` is a sibling, not a fork.
- **Existing routers** — `browse.py`, `joint_validation.py`, `summary.py`, `ask.py`, `content.py`, `llm.py`. `nav_label_map` / `active_tab` threading is already standard.
- **Vendored fonts** — Inter Tight (400/500/600/700) + JetBrains Mono (400/500/600). Helix uses 800 for `.page-title` and `.brand-mark`; check if 800 is loaded; if not, researcher decides whether to drop to 700 or extend the font request.

### Established Patterns
- **HTMX OOB swaps** — `count_oob`, `picker_badges_oob`, `filter_badges_oob`, `pagination_oob` blocks. New popovers' Apply submits a form whose response includes OOB blocks for the affected page surfaces (entry count, badge state, etc).
- **`HX-Push-Url`** — used everywhere for filter/sort/page state. Popover Apply must call this.
- **No hx-boost on tab nav** — Phase 1 Pitfall 8. Topbar tabs stay `<a href>` for full-page nav.
- **Pydantic view-models for grids** — `OverviewGridViewModel`, `PageLink` already exist. New `HeroSpec` follows the same convention.
- **Macro convention** — `{% from "browse/_picker_popover.html" import picker_popover %}` then `{{ picker_popover(...) }}`. New macros follow the same import-and-call pattern.
- **Static asset registration** — `popover-search.js` loaded with defer AFTER bootstrap.bundle. Any new helper for chip-toggle behavior follows the same defer-after-bootstrap rule.

### Integration Points
- **`base.html` line 39-68** — current `<nav class="navbar...">` block is the single replacement site for the new topbar macro. Active tab logic (`{% if active_tab == 'overview' %}active{% endif %}`) preserved by passing `active_tab` to the macro.
- **`base.html` line 84-94** — sticky-in-flow footer (D-UI2-05). Topbar sits above this; primitives must respect the body flex layout (`min-height: 100vh; flex-direction: column`).
- **`main.py`** — register `routers.components.router` for `GET /_components`. Mount before any catch-all.
- **`.panel-header` callers** — every `index.html` under `templates/` that renders a panel header. Researcher decides alias-or-rename.
- **`overview/index.html`** — JV listing already uses `.panel-header` with h1 inside (D-UI2-12). Same migration path as Browse.
- **`ask/index.html`** — uses `.ph` already (per app.css line 1318 — actually that's Dashboard_v2.html). Verify ask currently uses Bootstrap-style header; if so, migrate to `.ph` macro.

</code_context>

<specifics>
## Specific Ideas

- **Anchor visually to `Dashboard_v2.html`** (sibling project at `/home/yh/Desktop/02_Projects/Proj27_PBM1_fork_bootstrap/Dashboard_v2.html`). Per memory: "pin v2.0 frontend grey areas to Dashboard_v2.html design language". Phase 4 IS this anchoring made systematic.
- **Brand stays PBM2.** The gradient brand-mark renders the letter **"P"** (not Helix's "H"). Wordmark stays "PBM2".
- **Avatar slot is static "PM" placeholder.** Two-letter initials in the gradient circle. No coupling to auth; no per-user identity. The slot exists so a future auth phase has an obvious place to wire identity in.
- **No env pill, no notification bell** in this phase. They appear in Helix but require live signals that don't exist in PBM2 yet.
- **Hero macro can render with zero side stats and zero segments.** Showcase demonstrates both full and minimal hero variants.
- **Sparkline edge cases** — empty list, single value, constant series — must all render gracefully (`<svg/>`, degenerate flat line) without breaking the macro contract.
- **`/_components` is always-on**, not behind a debug flag. It's a documented internal surface, useful at runtime for downstream phase work.

</specifics>

<deferred>
## Deferred Ideas

- **Live tab counts on the topbar** — needs a per-router `nav_counts` dict contract; out of scope this phase. Primitive supports the slot via `count` arg; the call site in `base.html` simply doesn't pass any counts in v1.
- **Env pill on topbar** — needs a real environment signal; out of scope.
- **Notification bell** — needs an alert source; out of scope.
- **Per-user identity / real avatar** — auth is deferred per D-04; static "PM" placeholder for now.
- **Sticky-first-column retrofit on Browse pivot** — class ships and is showcased; Browse pivot HTML is not changed. Future phase owns the visible Browse pixel diff.
- **Browse filter row migration to chip-group `filters_popover.html`** — `_picker_popover.html` stays byte-stable per D-UI2-09. A future phase that explicitly wants the chip-group filter on Browse can do the migration with proper test rewrites.
- **Empty-state primitive generalization** — `browse/_empty_state.html` stays Browse-specific. When JV or showcase or another consumer needs an empty state, a generic `_components/empty_state.html` is added then.
- **Tech Reports tab + Platform BM tab** — Helix shows both; PBM2 doesn't have these features. Topbar primitive macro takes a tabs list so adding them later is data-only, not markup.
- **Plotly micro-charts / richer micro-vis** — sparklines stay server-rendered inline SVG. If a future feature wants interactive minis, that phase picks the tech path.
- **KPI variant macro signature refinement** — if the planner finds the variant arg awkward, splitting into `kpi_card_4up` / `kpi_card_5up` is a minor follow-up.
- **`.ph` vs `.panel-header` final naming** — researcher picks alias-or-rename; either is reversible.

</deferred>

---

*Phase: 04-ui-foundation-helix-aligned-shell-primitives-build-reusable*
*Context gathered: 2026-05-03*
