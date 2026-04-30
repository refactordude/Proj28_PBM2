---
phase: 02-ui-shell-rewrite-browse-footer-joint-validation-layout-parit
type: context
created: 2026-05-01
status: locked
---

# Phase 2: UI Shell Rewrite + Browse Footer + Joint Validation Layout Parity + Pagination — Context

> **Captured directly from user's UI overhaul brief (2026-05-01)** — every decision below was supplied by the user and is locked. The UI researcher and planner must NOT re-ask these questions; they may only fill in *implementation* gaps (specific px values, token names, component structure) consistent with these decisions and Browse's existing design language.

<domain>
## Phase Boundary

**In scope (this phase):**

1. **Shell rewrite** (affects every page — base.html + tokens.css + app.css):
   - Top nav restructured: tabs left-aligned next to PBM2 logo (currently top-right).
   - Nav bar height increased — taller padding, more vertical breathing room.
   - Main content area becomes full-width edge-to-edge (remove `.shell { max-width: 1280px }` constraint and horizontal margins).
   - Typography scale established and applied consistently across all pages: logo > section heading > nav tabs > table headers (uppercase/muted) > body.
   - Font weights normalized: bold for headings, regular for body, medium for nav items.
   - Line-height and spacing balanced so nothing feels cramped or oversized.
   - Full-width sticky in-flow footer (white background) added at the bottom of every page. Sticks at viewport bottom while scrolling; in-flow (not `position: fixed`) so it gives the shell a rounded "card" shape.

2. **Browse page**:
   - Existing floating "N platforms × M parameters" count text moves into the new sticky footer (still the same content — label + two count badges).
   - Otherwise visual parity preserved (Browse is the design reference for everything else).

3. **Joint Validation page** (must match Browse's design system):
   - Merge filter-bar panel + grid panel into a SINGLE panel (currently two `.panel` elements; Browse uses one).
   - Filter row layout: horizontal (single row) — same control row pattern as Browse's "Platforms / Parameters / Swap axes".
   - Same dropdown button styling as Browse (continue using the `browse/_picker_popover.html` macro AS-IS — no macro fork).
   - "Clear all" right-aligned in the filter row (matching Browse convention; currently after the filter dropdowns at the right).
   - "6 entries" count caption: top-right of the panel header (matching Browse's "N platforms × M parameters" placement). Currently below the filter bar.
   - "Joint Validation" h1: same heading style/size/weight as Browse's "Browse" h1, AND inside the white panel (currently outside `.panel`, in `.page-head` block of `overview/index.html`).

4. **Pagination on Joint Validation listing**:
   - Page numbering (page numbers / next-prev controls) on the JV grid.
   - Default 15 entries per page.
   - Pagination control surfaces in the footer or the panel — researcher decides exact placement consistent with Browse's overall feel.
   - Filter / sort / page state must round-trip through the URL (same `HX-Push-Url` pattern as Browse / Phase 5 sort state).

**Out of scope (NOT this phase):**

- Browse page filter / control redesign — Browse is the design REFERENCE; do not re-style its filter row, panel header, or counts. Only Browse's count text moves to the new footer.
- Ask page redesign — Ask inherits the new shell (taller nav, left-aligned tabs, full-width, sticky footer, type scale) but its existing inner UI is preserved byte-stable.
- Joint Validation detail page (`/joint_validation/<id>`) layout redesign — inherits the shell only; properties table + iframe sandbox stay as-shipped in Phase 1.
- Pagination on Browse or Ask — JV-only.
- Server-side pagination of the JV view-model — keep the existing all-rows-in-one-call shape (the data set is small; pagination can be client-side or done by slicing in `build_joint_validation_grid_view_model`). Final call belongs to the planner; start with the simpler approach.
- Adding a footer to detail pages or partial fragments returned via HTMX — only the full-page shell needs the footer.
- Per-row date-range filtering, multi-select, or batch ops on JV — same exclusions carry over from Phase 1.
- Popover positioning rework — Phase 1 quick task 260430-wzg already shipped the CSS overflow:visible fix; once the JV filter is merged into a single panel like Browse, the popover boundary issue disappears as a side effect.
- Re-platforming the type system — keep `Inter Tight` (already loaded via tokens.css) and `JetBrains Mono` (already used in pivot table). Do NOT introduce new font families.

</domain>

<decisions>
## Implementation Decisions

> Decision IDs use a fresh `D-UI2-*` namespace so they do not collide with `D-OV-*` (v2.0 Phase 5) or `D-JV-*` (Phase 1).

### Shell Layout

- **D-UI2-01: Tabs move from top-right to top-LEFT.** The nav becomes `[PBM2 logo] [Joint Validation] [Browse] [Ask]` — all left-aligned, with the tabs immediately to the right of the logo. Right side of nav can remain empty or hold future secondary controls (out of scope to populate).
  - Why: User explicitly requested this layout in 2026-05-01 brief; signals "primary navigation" rather than "side menu".
  - How to apply: Restructure `app_v2/templates/base.html` nav container; existing `nav-pills` markup stays but `ms-auto` / right-alignment is removed.

- **D-UI2-02: Taller nav bar.** Increase vertical padding so nav has more breathing room. Exact px value is researcher's call; target visual weight similar to a "site-header" rather than a "thin toolbar".
  - Why: User said "feels more substantial".
  - How to apply: Adjust nav padding tokens in tokens.css and apply via a nav-bar class in app.css. Aim for ~16–20px vertical padding (researcher confirms).

- **D-UI2-03: Full-width content panel.** Remove `.shell { max-width: 1280px }` and the horizontal padding `24px` so content stretches edge-to-edge across the viewport. The panel inside the shell should match the header bar's width.
  - Why: User said "remove the horizontal margins / max-width constraint on the card so it stretches edge-to-edge".
  - How to apply: Edit `.shell` rule in app.css; reduce or remove its outer padding. Inner panels keep their own padding (`.panel-body { padding: 26px 32px }`).

- **D-UI2-04: Typography hierarchy locked.** Order from largest/heaviest to smallest/lightest:
  1. PBM2 logo (largest, brand weight)
  2. Section heading h1 ("Browse", "Joint Validation") — prominent, inside the white panel
  3. Nav tabs — medium weight, medium size, hover/active state preserved from current design
  4. Table headers — slightly smaller, uppercase or muted color
  5. Table cell content — readable but not oversized (current 13–15px range)
  - Font weights: bold for headings, regular for body, medium for nav items.
  - Line-height + letter-spacing balanced so nothing is cramped.
  - Why: User explicitly listed this hierarchy.
  - How to apply: Define a type-scale section in tokens.css (`--font-size-logo`, `--font-size-h1`, `--font-size-nav`, `--font-size-th`, `--font-size-body`); apply via app.css selectors. Researcher proposes exact px values; planner pins them in PLAN.md.

- **D-UI2-05: Sticky in-flow footer with rounded shell shape.** A full-width white footer bar sits at the bottom of every page. It is **sticky in-flow** (NOT `position: fixed`) — meaning it occupies space in normal flow at the page bottom but stays visible at the viewport bottom when content is shorter than the viewport. The shell takes a rounded-card silhouette: tall nav at top + full-width content + footer at bottom forms a cohesive container.
  - Why: User explicitly said "sticky in-flow footer which makes the shell round-shaped". User also clarified earlier that they did NOT want `position: fixed` (would need bottom padding on tables to avoid clipping last row).
  - How to apply: Footer wraps in a flex column on `body` or `.shell`, with `min-height: 100vh` and the footer pushed to `margin-top: auto`. CSS pattern is well-known ("sticky footer flex layout"). Researcher specifies exact selectors.
  - Footer content default: empty on detail pages and Ask page; carries the entity-count badges on Browse and Joint Validation.

### Browse Page

- **D-UI2-06: Browse count text moves into the sticky footer.** The current "X platforms × Y parameters" status text (currently a small, floating in-panel badge) moves into the footer. Same content (label + two badges), same styling cues (small text, badge components for the counts).
  - Why: User wants the footer to be useful, not empty. Browse is the test case for footer content.
  - How to apply: Remove the count widget from `templates/browse/index.html` (or its partial); render it inside the footer block (a new template fragment, e.g. `templates/_footer/browse_counts.html`). The HTMX OOB swap `count_oob` block in browse routes must continue to update the count after each filter change — the OOB target id moves from inside the panel to inside the footer.

### Joint Validation Page (Browse parity)

- **D-UI2-07: Merge filter-bar panel + grid panel into ONE panel.** JV currently has two `.panel` elements (the filter bar IS its own panel, then the grid is a separate panel). Restructure `templates/overview/index.html` so the filter row, count caption, and grid table all live inside a single `<div class="panel">` — matching Browse's `<div class="panel"><panel-header><filter-bar><grid-body></div>` shape.
  - Why: User observation 2026-05-01: "Joint Validation page seems like has two separate white area while Browse has only one." Visual mismatch with Browse, and side effect: popover bridges the gap between panels (visually messy).
  - How to apply: Restructure `templates/overview/index.html` to mirror `templates/browse/index.html`. The `overview-filter-bar panel` element loses its `panel` class — it becomes `.overview-filter-bar` only, nested inside the outer `.panel`. The existing `.panel:has(.overview-filter-bar) { overflow: visible }` rule then matches naturally (no self-match needed). The quick-task 260430-wzg self-match selector stays as harmless safety net (user kept it).

- **D-UI2-08: Filter row layout horizontal.** All six filter dropdowns (Status / Customer / AP Company / Device / Controller / Application) sit in a single horizontal row. Same arrangement as Browse's "Platforms / Parameters / Swap axes" controls.
  - Why: User explicitly: "Lay them out horizontally in a row". Currently each is on its own line because each `<div class="dropdown">` is a block element — needs flex/inline-flex on the form or filter-bar container.
  - How to apply: `.overview-filter-bar` gets `display: flex; gap: …; align-items: center`. The form inside also flex-rows. Wrap-on-narrow-viewport is acceptable (overflow x-axis would be worse). Researcher pins exact gap value.

- **D-UI2-09: Reuse Browse's picker macro byte-stable.** No macro fork. The dropdown button style, popover content, and all D-OV / D-JV behavior contracts (D-15b auto-commit, form-association, OOB badge swap) carry forward exactly.
  - Why: User said "Use the same dropdown button styling as Browse page". Macro was already shared; this confirms no divergence.
  - How to apply: `_filter_bar.html` keeps `from "browse/_picker_popover.html" import picker_popover`. Only the WRAPPER markup changes (.overview-filter-bar layout), not the macro calls.

- **D-UI2-10: "Clear all" right-aligned in the filter row.** Within the horizontal filter row, "Clear all" sits at the far right.
  - Why: Browse convention; user explicitly: "Place 'Clear all' on the right side of the filter row, matching Browse page convention".
  - How to apply: With `display: flex` on the filter bar, `Clear all` gets `margin-left: auto` (push to right). It already exists as the last child in `_filter_bar.html`; only positioning changes.

- **D-UI2-11: Entry count moves to panel header right-side.** "6 entries" appears in the top-right of the panel header (where Browse shows "2 platforms × 2 parameters"). Removed from its current place beneath the filter bar.
  - Why: Browse layout parity; user explicit.
  - How to apply: `templates/overview/index.html` panel-header gets a left zone (h1 "Joint Validation") and a right zone (count caption). The HTMX OOB target id `#overview-count` migrates to the new location; routes' `count_oob` block already emits an OOB swap fragment, so only the receiving target moves.

- **D-UI2-12: H1 inside the white panel, Browse-styled.** "Joint Validation" h1 moves from outside the panel (currently in `.page-head` div) to inside the panel header. Visual style matches Browse's "Browse" h1 — same size, same weight, same family. The `Pivot grid` tag next to Browse's h1 has no JV equivalent and is omitted.
  - Why: User explicit: "should be inside the white area as it does in Browse page".
  - How to apply: Remove the standalone `.page-head` block in `overview/index.html`; place `<h1 class="page-title">Joint Validation</h1>` inside the new panel-header. Use the same selector / utility classes as Browse's h1.

### Pagination (JV-only)

- **D-UI2-13: Pagination control on JV listing.** Visible page numbers (≤ ~7 with ellipsis on overflow), with prev/next arrows. Pagination control appears in the footer (preferred — co-locates with entry count) OR at the bottom of the panel — researcher picks based on visual fit.
  - Why: User explicit: "I want page numbering system for Joint Validation in case there are so many items."
  - How to apply: Render via Bootstrap 5's `<ul class="pagination">` component (already in vendored CSS — no new dependency). HTMX-swap the grid + count + pagination block on each page click via `hx-get="/?page=N"` with `HX-Push-Url`. Server slices the rows from `build_joint_validation_grid_view_model` based on `page` query param.

- **D-UI2-14: Default page size 15.** First page shows 15 entries; subsequent pages each 15. No user-facing page-size picker (out of scope; can be added later if needed).
  - Why: User explicit: "Default: show 15 items per each page."
  - How to apply: Constant `JV_PAGE_SIZE = 15` in `routers/overview.py` (or a small `pagination.py` shared service). Page slicing happens in the router (or grid-service helper) so view-model carries `rows` (current page only), `page`, `page_count`, `total_count`.

### Claude's Discretion

The following are NOT locked by the user and the researcher / planner may resolve them:
- Exact px values for nav padding (D-UI2-02), font sizes (D-UI2-04), gap values (D-UI2-08), and footer height — pinned by researcher's UI-SPEC.md and the planner's PLAN.md.
- Whether the pagination control belongs in the footer (D-UI2-13a) or at the bottom of the panel (D-UI2-13b). Researcher decides based on Browse's design rhythm.
- Whether server-side or client-side pagination — server-side keeps URL round-trip clean; client-side avoids HTTP roundtrips on small datasets. Planner picks; default to server-side to match the existing HTMX patterns.
- Whether the JV detail page (`/joint_validation/<id>`) gets a back-to-listing breadcrumb or stays as-is. Default: stays as-is (out of scope).
- Whether Ask page's count area participates in the footer pattern. Default: footer is empty on Ask (Ask has no entity count to surface).

</decisions>

<specifics>
## Specific References

The user's verbatim brief (2026-05-01), summarized below as the locked source of truth:

### Layout changes for overall UI

1. Restructure top navigation:
   - Tabs (Joint Validation / Browse / Ask) move from top-right to top-LEFT, immediately right of "PBM2" logo.
   - Increase nav bar height — taller padding, more vertical breathing room.

2. Make panel full-width:
   - Remove horizontal margins / max-width on the card so it stretches edge-to-edge, matching the header bar width.
   - Increase font size to match (covered by D-UI2-04 typography hierarchy).

3. Improve typography:
   - Visual hierarchy: logo largest, nav tabs medium, section headings prominent, table headers smaller and uppercase/muted, table cells readable but not oversized.
   - Consistent font weights: bold headings, regular body, medium nav items.
   - Adjust line-height and spacing — balanced and polished, nothing cramped or oversized.

### Browse page

1. Add a full-width white footer bar:
   - Current "4 platforms × 4 parameters" floating bottom-left text becomes the footer content.
   - Footer spans full width, solid white background, sticky in-flow.

### Joint Validation page (match Browse design system)

1. Filter controls layout:
   - Six dropdowns (Status, Customer, AP Company, Device, Controller, Application) horizontal in a single row.
   - Popover not weirdly clipped at the edge of its content area.
   - "Clear all" right-aligned in filter row.
   - Same dropdown button styling as Browse.

2. Entry count placement:
   - "6 entries" → top right (mirror Browse's "2 platforms × 2 parameters").

3. Page heading:
   - "Joint Validation" h1 — same style/size/weight as Browse's "Browse" h1.
   - H1 inside the white panel area (matches Browse).

4. Pagination:
   - Page numbering, default 15 items per page.

### Goal (verbatim)

> All pages should feel like part of the same application — same shell (full-width tall nav with left-aligned tabs, full-width content, full-width white footer), same control patterns, same typography, clean, well-proportioned typography throughout.

</specifics>

<canonical_refs>
## Canonical References

- **Browse page (`templates/browse/index.html` + `_filter_bar.html` + `_picker_popover.html`)** — design reference. Match its panel structure, filter row pattern, count placement, and dropdown button styling. Do NOT modify Browse's design beyond extracting the count text into the footer (D-UI2-06).
- **Phase 1 Plan 05 (`templates/overview/index.html`, `_filter_bar.html`)** — current JV layout that's being restructured. The filter-bar's `.panel` class is the structural mistake that gets undone in D-UI2-07.
- **Quick task 260430-wzg (`260430-wzg-SUMMARY.md`)** — CSS overflow:visible self-match selector for `.panel.overview-filter-bar`. User confirmed: keep as harmless safety net even after D-UI2-07 removes the structural need for it.
- **Existing `tokens.css`** — current type/color tokens (`--ink`, `--mute`, `--panel`, `--radius-panel: 22px`, etc.). Researcher should add type-scale tokens here (D-UI2-04) without churning existing names.
- **Existing `app.css`** — current `.shell`, `.panel`, `.panel-header`, `.panel-body`, `.browse-filter-bar`, `.overview-filter-bar`, `.pivot-table`, `.overview-table` rules. Researcher's UI-SPEC pins which selectors get edited vs newly introduced.
- **HTMX OOB swap patterns from Phase 4 / Phase 5** — `count_oob`, `picker_badges_oob`, `filter_badges_oob` blocks. The pagination block adds a new OOB block alongside these (D-UI2-13).
- **Bootstrap 5 vendored** (`static/vendor/bootstrap/bootstrap.min.css`) — `.pagination` component already available; no new dependency for D-UI2-13.

</canonical_refs>
