---
phase: 05-overview-redesign
type: context
created: 2026-04-28
status: locked
---

# Phase 5: Overview Tab Redesign — Context

## Phase Boundary

**In scope (this phase):**
- Replace the Overview tab's `<ul class="list-group">` row layout with a Bootstrap **table** that mirrors the Phase 4 Browse pivot grid styling exactly (`<table class="table table-striped table-hover table-sm">` + `<thead class="sticky-top bg-light">`, sticky-bottom warnings if any, mono cell font).
- Source per-platform metadata from **YAML frontmatter** on each existing `content/platforms/<PLATFORM_ID>.md`. New frontmatter keys: `title`, `status`, `customer`, `model_name`, `ap_company`, `ap_model`, `device`, `controller`, `application`, `assignee`, `start`, `end`.
- Reuse the Phase 4 `_picker_popover.html` macro and `popover-search.js` module to provide six **multi-select popover-checklist filters**: Status, Customer, AP Company, Device, Controller, Application. Each filter follows the **D-15b auto-commit + 250ms debounce** contract that Phase 4 ships.
- **Sortable column headers** — clickable, default sort = `start` descending. URL round-trips `?sort=<col>&order=<asc|desc>` so the link is shareable (mirrors BROWSE-V2-05).
- Preserve the existing Phase 3 **AI Summary** in-place HTMX swap UX in the row's last cell. Stays in cell, no row-expand drawer.
- Remove the legacy brand / SoC / year / has_content `<select>` filters, the `_filter_alert.html` partial, and the per-row Remove (delete) button.

**Out of scope (NOT this phase):**
- Editing frontmatter through the Overview UI (frontmatter is authored on the existing per-platform content page form — no schema-validation UI in v2.0).
- Date-range filtering on Start / End (per user — sort only, no filter).
- Filter on Title / Model Name / 담당자 (per user — sort only, no filter).
- Search box for Title (out — sort only).
- Server-paginated rendering (curated list is < ~100 entries; client-side full table is fine).
- Bulk-select / batch operations (not requested).
- New Phase 6 (Ask Tab Port) work — Phase 6 stays as scoped before Phase 5 was inserted.

## Locked Decisions

> Numbering continues from Phase 4 (which ended at D-15b). Decision IDs use a fresh D-OV-* namespace to avoid collision and keep Overview decisions self-contained.

### D-OV-01 — Data source: YAML frontmatter on existing content pages

Per-platform PM metadata is sourced from **YAML frontmatter** on the existing `content/platforms/<PLATFORM_ID>.md` markdown files (already managed by `content_store.py`). NO new metadata table, NO separate JSON/YAML manifest, NO new directory.

Frontmatter shape (all keys optional — missing fields render as `—`):

```markdown
---
title: My Platform Project
status: in-progress
customer: Acme Corp
model_name: Foo Pro
ap_company: Samsung
ap_model: Exynos 1380
device: Phone
controller: ABC
application: Camera
assignee: 홍길동
start: 2026-04-01
end: 2026-12-31
---

# Body markdown here…
```

**Why:** content_store + atomic_write are already in place; no new persistence layer. The user already navigates to per-platform content pages — adding fields to that page is the lowest-friction path.

### D-OV-02 — Frontmatter parsing lives in `content_store.py`

Add `read_frontmatter(platform_id, content_dir) -> dict[str, str]` to `app_v2/services/content_store.py`. Returns an empty dict for missing file, missing frontmatter, malformed YAML, or any error. **Defensive:** never raises; logs warnings. Uses `pyyaml` (already in requirements). The function memoizes via mtime_ns key so repeated reads on the same content page are O(1) (mirrors `get_content_mtime_ns` pattern).

Frontmatter format: leading `---\n`, YAML body, closing `\n---\n` or `\n---` at end of frontmatter. Body markdown begins after the second `---` line. If no leading `---\n`, treat as zero frontmatter (full file is body).

### D-OV-03 — New service: `overview_grid_service.py`

Add `app_v2/services/overview_grid_service.py` with the orchestration function `build_overview_grid_view_model(curated_pids, content_dir, filters, sort) -> OverviewGridViewModel`. Pydantic model carries: `rows: list[OverviewRow]`, `filter_options: dict[str, list[str]]` (one list per filterable column, sorted alphabetically), `active_filter_counts: dict[str, int]`, `sort_col: str`, `sort_order: Literal["asc", "desc"]`, `has_content_map: dict[platform_id, bool]` (drives AI Summary disabled state).

Reuses Phase 4 patterns: filter list extraction (sorted unique values, `—` excluded), filter application (set membership), sort (stable, then by platform_id as tiebreaker).

### D-OV-04 — Routes: `/overview` (GET) + `/overview/grid` (POST)

Mirrors Phase 4's `GET /browse` + `POST /browse/grid` split:

- `GET /overview` — full page render (HTML doc), pre-populates filter selections + sort from URL query params, hands the `OverviewGridViewModel` to `overview/index.html`.
- `POST /overview/grid` — fragment swap. Body carries the picker checkbox values (form-associated with a hidden `<form id="overview-filter-form"></form>`) plus optional `sort` and `order`. Returns blocks: `["grid", "count_oob", "filter_badges_oob"]` — same OOB pattern as Phase 4. Sets `HX-Push-Url` to canonical `/overview?status=...&customer=...&sort=start&order=desc` so URL stays shareable.

Existing routes preserved: `POST /overview/add` (curated-list add) keeps working. `DELETE /overview/<pid>` is REMOVED (Remove button gone per user). Existing `POST /overview/filter` and `POST /overview/filter/reset` are REMOVED (replaced by `/overview/grid`).

### D-OV-05 — Templates

- `app_v2/templates/overview/index.html` — full rewrite. Page chrome: Add platform input row at top (unchanged); filter bar with 6 picker popovers + count caption; `<table class="table table-striped table-hover table-sm">` with sticky-top thead and sortable column headers. Block names: `grid`, `count_oob`, `filter_badges_oob`.
- `app_v2/templates/overview/_grid.html` — new partial. The fragment `POST /overview/grid` returns. Just the `<tbody>` + empty-state `<tr>`.
- `app_v2/templates/overview/_filter_bar.html` — new partial. Renders 6 picker popovers + count caption; reuses `from "browse/_picker_popover.html" import picker_popover` (CROSS-TEMPLATE IMPORT — the macro is already shared-friendly).
- `app_v2/templates/overview/_filter_alert.html` — DELETED (legacy filter dialog).
- `app_v2/templates/overview/_entity_row.html` — DELETED (replaced by table-row rendering inline in `_grid.html`).

### D-OV-06 — Reuse Phase 4 popover macro AS-IS, no fork

The `picker_popover` macro from `app_v2/templates/browse/_picker_popover.html` is DRY-imported into `_filter_bar.html` via `{% from "browse/_picker_popover.html" import picker_popover %}`. The macro signature `picker_popover(name, label, options, selected)` works unchanged. The macro's `<form id="browse-filter-form">` reference is **intentional** — Phase 5's hidden form is named `<form id="overview-filter-form">`, so the macro needs ONE small parameter addition: `form_id` defaulting to `"browse-filter-form"`. Phase 5 templates pass `form_id="overview-filter-form"`. Phase 4 callers continue without change because the default preserves their behavior.

This keeps both pages on one macro definition (single source of truth for D-15b auto-commit pattern, gap-2 form-association, gap-3 OOB swap targets, accessibility attrs).

### D-OV-07 — Sort UX: clickable column headers, asc → desc only

- All 12 data columns are sortable (Title, Status, Customer, Model Name, AP Company, AP Model, Device, Controller, Application, 담당자, Start, End). Button cells (Link, AI Summary) are NOT sortable.
- Click cycles: **asc → desc → asc** (no "unsorted" state — the table always has a defined order). Default first-click on an unsorted column = asc.
- Default page sort = `start` desc (latest on top).
- Active sort column header shows a small `<i class="bi bi-arrow-down-short">` (desc) or `<i class="bi bi-arrow-up-short">` (asc) glyph.
- Click triggers `hx-post=/overview/grid` carrying current filters + new sort/order. URL is HX-Push-Url'd.

Tiebreaker (when sort values are equal or both `—`): **platform_id ASC** for stability across renders.

### D-OV-08 — Date format & sort

`start` and `end` columns expect ISO 8601 dates (`YYYY-MM-DD`). Render as-is in the table. Empty / missing / malformed dates render as `—` and sort to the END regardless of asc/desc (so empty-date rows don't pollute the top of a default `start desc` sort).

Defensive: `read_frontmatter` returns the raw string; the service converts to `datetime.date` for sort but renders the original string in the table cell (so a frontmatter typo like `2026-04` shows as the user wrote it).

### D-OV-09 — `—` sentinel for missing values

Any missing / empty frontmatter field renders as the em-dash sentinel `—` (carries from v1.0 / Phase 4 missing-cell convention). Title falls back to PLATFORM_ID (NOT `—`) so the link cell remains useful.

### D-OV-10 — AI Summary cell unchanged from Phase 3

The AI Summary button stays in the row's last cell with the existing `hx-post=/platforms/<pid>/summary` + `hx-target=#summary-<pid>` + `hx-disabled-elt` + the per-row `<div id="summary-<pid>">` slot for response. The summary content swaps in below or beside the row — DEFAULT: a separate `<tr>` collapsed by default, inserted on first AI Summary trigger via OOB swap (mirrors Phase 3 layout).

`disabled` is set when the platform has no content page (existing D-13 from Phase 3 contract preserved). `has_content_map` from the view model drives this.

### D-OV-11 — Add platform input row preserved

The existing top-of-page `POST /overview/add` form (with PLATFORM_ID datalist typeahead) stays. After successful add, the page reloads (full GET /overview) so the new row appears in the table — simpler than synthesizing a one-row HTMX swap that then must populate frontmatter that may not exist yet.

### D-OV-12 — Performance: in-process memoize per content page mtime

Reading frontmatter on every GET /overview / POST /overview/grid would be N file reads per request (N = curated count, < ~100). To avoid re-parsing YAML on every keystroke debounce, `read_frontmatter` memoizes by `(platform_id, mtime_ns)`. Cache lives in-process; module-level dict; bounded to `len(curated_pids)`. Invalidation is implicit via mtime.

### D-OV-13 — URL state shape

`/overview?status=A&status=B&customer=X&ap_company=Y&device=Z&controller=W&application=V&sort=start&order=desc`

- Multi-value filter params use **repeated keys** (e.g., `?status=A&status=B`) — same as Phase 4's `platforms=A&platforms=B`. FastAPI parses repeated keys natively into `list[str]` via `Query(default=[])`.
- `sort` is a single column name; `order` is `asc` or `desc`. Unknown / invalid values → fall back to default (`start`/`desc`).

### D-OV-14 — Tests

- `tests/v2/test_content_store_frontmatter.py` (new) — frontmatter parser unit tests: malformed YAML, missing closing `---`, no leading `---`, valid frontmatter, empty values, unicode (담당자 = 한글).
- `tests/v2/test_overview_grid_service.py` (new) — service-layer tests: filter option extraction, multi-filter set-membership, sort behavior including date-empty-to-end + tiebreaker, no-curated-list edge case.
- `tests/v2/test_overview_routes.py` (UPDATED) — replace legacy `<select>` filter tests with new picker-popover + `/overview/grid` HTMX flow tests; URL round-trip; HX-Push-Url; OOB filter badges.
- `tests/v2/test_phase05_invariants.py` (new) — codebase invariants: no Plotly in `app_v2/`, no remove-button (`hx-delete=/overview/<pid>`) anywhere, the `picker_popover` macro is sourced from `browse/` and imported by `overview/`, the Browse pivot-grid table classes appear in the overview index.
- Existing `tests/v2/test_overview_filter.py` — DELETED (legacy `<select>` filters gone).
- Existing `tests/v2/test_overview_routes.py` legacy filter tests — DELETED.
- Phase 4 tests stay byte-stable (they don't touch overview).

## Specific user-locked answers (this discussion, 2026-04-28)

| Question | Answer |
|----------|--------|
| Data source for new fields? | **A** — YAML frontmatter on existing `content/platforms/<PLATFORM_ID>.md` |
| Which columns get filters? | Status, Customer, AP Company, Device, Controller, Application (6) |
| Date columns (Start / End)? | Sort only — no filter |
| 담당자 (assignee)? | No filter |
| AI Summary UX? | Stay in cell (existing Phase 3 in-place HTMX swap) |
| Sort? | Clickable column headers; default Start desc (latest on top) |
| Delete (Remove) button? | Remove — gone |
| Add platform input? | Keep |
| Title fallback when frontmatter missing? | PLATFORM_ID |
| Missing field sentinel? | `—` em-dash (matches Phase 4) |

## Cross-phase references

- D-15b (Phase 4): auto-commit + 250ms debounce — Overview filters reuse this contract verbatim.
- gap-2 (Phase 4): `form="overview-filter-form"` on each picker checkbox — Overview reuses the form-association mechanism with its own form id.
- gap-3 (Phase 4): picker_badges_oob OOB-swap pattern — Overview adds its own `filter_badges_oob` block emitting six trigger badge spans.
- Phase 3: `content_store.py` markdown read/write infrastructure + AI Summary route — both preserved unchanged; this phase ADDs `read_frontmatter` to content_store but doesn't modify existing behavior.

## Canonical refs

- `.planning/ROADMAP.md` Phase 5 section — goal + success criteria + requirement IDs
- `.planning/REQUIREMENTS.md` — OVERVIEW-V2-01..06
- `.planning/PROJECT.md` — Active milestone scope
- `app_v2/templates/browse/_picker_popover.html` — picker macro (must add `form_id` parameter for cross-phase reuse)
- `app_v2/static/js/popover-search.js` — D-15b implementation (Phase 5 reuses unchanged)
- `app_v2/services/content_store.py` — gets new `read_frontmatter` function
- `app_v2/services/browse_service.py` — pattern reference for `overview_grid_service.py`
- `app_v2/routers/browse.py` — pattern reference for the new GET / POST /overview/grid split
- `app_v2/templates/browse/index.html` — pattern reference for block_names + sticky table

## Required upstream edits BEFORE planning starts

These are documentation hygiene; planner should treat them as Plan 05-00 prerequisites OR call them out as a planning blocker:

1. ✅ `.planning/ROADMAP.md` — Phase 5 inserted, Phase 6 (Ask Tab Port) renumbered. Done 2026-04-28.
2. ✅ `.planning/REQUIREMENTS.md` — OVERVIEW-V2-01..06 added; ASK-V2-01..08 reassigned to Phase 6; Traceability table updated; v2.0 totals 45 → 51. Done 2026-04-28.
3. `.planning/PROJECT.md` — Add an "Overview redesign (v2.0)" subsection under Active Requirements (between current "Browse — v2.0" Validated block and "Ask carry-over (v2.0)" Active block). Planner OR Plan 05-01 owns this.

---

*Phase: 05-overview-redesign*
*Context locked: 2026-04-28 via interactive discuss after Phase 4 (Browse Tab Port) wrapped — user requested same filter pattern + table styling for the Overview tab with PM metadata fields.*
