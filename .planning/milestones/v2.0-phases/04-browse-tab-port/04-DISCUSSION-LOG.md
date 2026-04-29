# Phase 04: Browse Tab Port - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-26
**Phase:** 04-browse-tab-port
**Mode:** Interactive smart discuss (default mode, 1 question per turn, AskUserQuestion-driven)
**Areas discussed:** Surface scope, Filter UI, Filter trigger model, Export UX

---

## Surface scope

### Q1: Which v1.0 Browse surfaces should Phase 4 port to v2.0?

| Option | Description | Selected |
|--------|-------------|----------|
| Pivot only (Recommended) | Match BROWSE-V2-01..05 verbatim; smallest port; v1.0 remains for Detail/Chart users | ✓ |
| Pivot + Detail | Pivot + single-platform long-form sorted by InfoCategory ASC, Item ASC | |
| Pivot + Detail + Chart | Full v1.0 parity; Plotly must be vendored for intranet | |
| Pivot + Chart (no Detail) | Skip Detail; port Pivot + Chart; Detail absorbed by /platforms/{id} | |

**User's choice:** Pivot only
**Notes:** Smallest, surgical port. v1.0 Streamlit Browse remains available on port 8501 as the fallback for power users until v1.0 is sunset.

### Q2: For Detail/Chart deferral: how should I handle them?

| Option | Description | Selected |
|--------|-------------|----------|
| Defer both as future ideas (Recommended) | Note under Deferred Ideas; Plotly stays in requirements.txt (v1.0 still imports it); no req additions | ✓ |
| Drop Plotly from v2.0 entirely; mark Chart out-of-scope | Cleaner architectural signal but harder to revisit later | |
| Add as v3.0 candidate with explicit numbering (BROWSE-V2-F01/F02) | Preserves traceability when someone revisits | |

**User's choice:** Defer both as future ideas
**Notes:** No new Future Requirements added; Deferred Ideas captures the intent.

---

## Filter UI

### Q1: Where should the filter controls live on the Browse page?

| Option | Description | Selected |
|--------|-------------|----------|
| Top inline filter bar inside .panel (Recommended) | Single-row layout above grid; pivot grid gets full panel width below; matches Dashboard_v2.html JV-tab pattern | ✓ |
| Left rail (sidebar-style) panel | Two-column ~280px rail + main; closest to v1.0 mental model; tradeoff: pivot loses 280px width | |
| Offcanvas drawer (toggleable) | Filters in Bootstrap offcanvas; pivot 100% width; tradeoff: extra click + chip summary needed | |

**User's choice:** Top inline filter bar inside .panel
**Notes:** Initially asked the user to clarify before proceeding (no answer on first attempt); preview block was the same on retry, user proceeded with the recommended option.

### Q2: How should users pick platforms/parameters from long lists (100+ items)?

| Option | Description | Selected |
|--------|-------------|----------|
| Popover checklist with search (Recommended) | Bootstrap dropdown: search input + scrollable checklist + Apply/Clear footer; ~30 lines vanilla JS | ✓ |
| Typeahead-add-chip (Phase 2 Add pattern) | HTML5 datalist + chips below input; consistent with Phase 2; tradeoff: no bulk select | |
| Native <select multiple> | Zero JS; tradeoff: notoriously bad UX for 100+ items | |
| Choices.js (lightweight JS lib) | ~30KB gz; best UX; tradeoff: violates "no extra JS lib" principle from Phase 1 | |

**User's choice:** Popover checklist with search
**Notes:** Most familiar pattern (Notion/Linear/JIRA filter style). User accepted preview ASCII mockup directly.

### Q3: How should the search-input inside the popover filter the candidate list?

| Option | Description | Selected |
|--------|-------------|----------|
| Client-side substring filter on pre-rendered list (Recommended) | Server renders full list once; vanilla JS hides non-matching <li>; instant feel | ✓ |
| Server-side HTMX typeahead per keystroke | hx-post per keystroke with 250ms debounce; round-trip cost; thread pressure | |
| No search input — plain scrollable checklist | Simplest; fails the "100+ params unsearchable" pain | |

**User's choice:** Client-side substring filter on pre-rendered list
**Notes:** Acceptable HTML-shipping cost (~50KB for 500 items); zero round-trips per keystroke.

### Q4: Where do candidate platforms and parameters come from?

| Option | Description | Selected |
|--------|-------------|----------|
| Full DB catalog (v1.0 parity, Recommended) | All PLATFORM_IDs in ufs_data; all (InfoCategory, Item) combos | ✓ |
| Curated Overview only (Phase 2 list) | Tight tab coupling; breaks core value when Overview is empty | |
| Toggle: 'Curated only' vs 'All platforms' | Adds 1 piece of state; marginal benefit; can be added later | |

**User's choice:** Full DB catalog (v1.0 parity)
**Notes:** Browse must work even when Overview is empty (PROJECT.md core value).

---

## Filter trigger model

### Q1: When should the pivot grid re-fetch from the DB after a user changes a filter?

| Option | Description | Selected |
|--------|-------------|----------|
| Apply button inside each popover (Recommended) | Selections local until Apply; one re-fetch per Apply; swap-axes immediate (view transform) | ✓ |
| Change-triggered — every checkbox toggle re-queries | Phase 2 Overview pattern; tradeoff: 5 toggles = 5 DB queries; perceived flicker | |
| Hybrid — popover Apply, swap-axes immediate | Functionally identical to Apply-button option once stated explicitly | |

**User's choice:** Apply button inside each popover (with swap-axes triggering immediately)
**Notes:** Core perceived-performance decision: 200-row pivot queries × N toggles is unacceptable. Made explicit in CONTEXT.md D-14 / D-16.

### Q2: Top-level 'Clear all' affordance in the filter bar?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — small text link in the filter bar (Recommended) | Hidden when no filters set; resets BOTH pickers AND triggers a single grid swap | ✓ |
| No — per-popover Clear is sufficient | User must open each popover separately to reset | |
| Yes, plus a 'Reset to URL state' option | Two clear actions; complexity for shared-link workflows; premature | |

**User's choice:** Yes — small text link in the filter bar
**Notes:** Consistent with Phase 2 Overview filter D-17.

---

## Export UX

### Q1: How should the Excel/CSV export controls work in v2.0 Browse?

| Option | Description | Selected |
|--------|-------------|----------|
| Bootstrap modal mirroring v1.0 (Recommended) | Format radio + scope radio + filename input + Download button; reuses v1.0 _sanitize_filename | |
| Dropdown menu — 4 direct download links | Excel/CSV × wide/long; auto-default filename; 1-click | |
| Inline buttons — wide-only | Smallest UX surface; drops 'full long-form' export from v2.0 | |
| (Asked for clarification first) | User indicated they wanted to clarify before answering | |

**User's choice:** "Remove the excel/csv export feature for simplicity"
**Notes:** User rejected the question and asked for the entire export feature to be dropped. This converted the discussion from "which export UI?" to "should we have export at all?" — answered with explicit scope-removal.

### Q2: Confirm scope-out — drop BROWSE-V2-04 (Excel/CSV export) from v2.0 entirely?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — drop entirely; move to Out of Scope (Recommended) | BROWSE-V2-04 → Out of Scope; success criterion #3 deleted; no openpyxl/csv code in app_v2/ | ✓ |
| Yes — but defer to v3 (BROWSE-V2-F02) | Move to Future Requirements with new ID; preserves audit trail | |
| Keep export but just simplify the UI | Reverts the simplification request | |

**User's choice:** Drop entirely; move to Out of Scope
**Notes:** v1.0 Streamlit Browse remains the export surface until v1.0 sunset. Triggers required upstream edits to REQUIREMENTS.md, ROADMAP.md, PROJECT.md (captured in CONTEXT.md "Required upstream edits BEFORE planning starts" section).

---

## Claude's Discretion (areas not asked about)

- Bootstrap Icons selection (`bi-chevron-down`, `bi-arrow-left-right`, `bi-x` — replaceable)
- Popover dimensions (suggest 320–480px)
- Row-label truncation ellipsis behavior
- Search input debounce (50ms or zero)
- Empty-state copy update from v1.0 ("in the sidebar" → "above")
- HTMX swap animation timing (`swap:200ms`)
- `autocomplete="off"` on the search input
- Test layout under `tests/v2/` (mirrors Phase 2/3)

## Deferred Ideas

(See CONTEXT.md `<deferred>` section for the full list)

- Detail surface port; Chart surface port; Excel/CSV export under v2.0 shell
- Sticky-left first column on the wide grid
- Faceted filtering by Brand/SoC/Year on Platforms picker
- InfoCategory grouping in Parameters picker
- Saved filter presets, per-user filter cookie
- Keyboard shortcuts in popover, "Select all matching search" button
- Streaming long-form export, sort-by-column-header, aggregated views

---

*Generated: 2026-04-26*
