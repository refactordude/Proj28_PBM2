# Phase 2: Overview Tab + Filters - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous, batch tables, all 3 grey areas accepted)

<domain>
## Phase Boundary

Users can build and maintain a curated watchlist of platforms from the live `ufs_data` database, filter it by Brand / SoC / Year / has-content, and see each platform with its metadata badges — all without a full page reload. Overview tab is the FIRST user-facing surface of v2.0.

Delivers:
- GET /overview (and GET /?tab=overview) rendering the Overview tab content via Jinja2Blocks
- Curated list storage at `config/overview.yaml` (gitignored; `.example.yaml` committed)
- Add entity endpoint: HTMX POST /overview/add
- Remove entity endpoint: HTMX DELETE /overview/{platform_id}
- Filter endpoint: HTMX POST /overview/filter returning the entity-list fragment
- PLATFORM_ID parser + SoC→year lookup table in `app_v2/data/soc_year.py`
- Empty state when curated list is empty

Scope out:
- Content pages (platform detail page) — Phase 3
- AI Summary button actual behavior — Phase 3 (button is rendered but clicking does nothing in Phase 2, or it's disabled)
- Browse / Ask tabs — still stub placeholders from Phase 1
- URL round-trip for filter state — deferred to OVERVIEW-F01
- Drag-to-reorder — deferred to OVERVIEW-F02

</domain>

<decisions>
## Implementation Decisions

### Entity row layout & empty state (Area 1)
- **D-01:** Entity row uses Bootstrap `list-group list-group-flush` with `list-group-item d-flex align-items-center` per row. Dense — approximately 60px tall each.
- **D-02:** Layout within a row (left-to-right): PLATFORM_ID title (bold, `fs-5`), Brand badge, SoC badge, Year badge (when known), spacer (`me-auto`), link icon (→ `/platforms/<id>`), "AI Summary" button, "×" Remove button.
- **D-03:** Badges are `badge rounded-pill` styles: Brand=`bg-primary`, SoC=`bg-info`, Year=`bg-secondary` when unknown, `bg-success` when known. Link uses `bi-arrow-right-circle` icon in Bootstrap Icons.
- **D-04:** Buttons on the right: "AI Summary" is `btn btn-outline-primary btn-sm` with `bi-stars` icon + text label "AI Summary". "×" Remove is `btn btn-outline-danger btn-sm` icon-only (`bi-x`), with `aria-label="Remove {PLATFORM_ID}"` and `hx-confirm="Remove {PLATFORM_ID} from your overview?"`.
- **D-05:** Empty state when curated list is empty: Bootstrap alert (`alert alert-info text-center`) placed where the list would go, saying "No platforms in your overview yet. Use the search above to add your first one." with `bi-arrow-up-circle` icon pointing at the typeahead input.
- **D-06:** AI Summary button in Phase 2 is **disabled with tooltip** "Content page must exist first (Phase 3)" — button renders but does nothing. Full wiring lands in Phase 3 (SUMMARY-01..07).

### Typeahead + Add flow (Area 2)
- **D-07:** Typeahead uses HTML5 `<datalist>` bound to `<input type="text" list="platforms-datalist">`. The `<datalist>` is populated at page load from `list_parameters` … **correction: from the cached ufs_service `list_platforms_core` output** (the full `PLATFORM_ID` set, not filtered by curated list). No JS combobox library — zero runtime JS cost.
- **D-08:** Add flow UI: top of the Overview content area, above the collapsible filter block. Inline form:
  - `<label>` "Add platform to overview"
  - full-width `<input list="platforms-datalist">` with placeholder "Start typing a PLATFORM_ID…"
  - right-aligned `<button type="submit" class="btn btn-primary">Add</button>`
- **D-09:** Submit behavior: form uses `hx-post="/overview/add"`, `hx-target="#overview-list"`, `hx-swap="afterbegin"`. Response is the rendered HTML fragment of ONE new entity row. Input field cleared via `hx-on::after-request="this.reset()"`.
- **D-10:** Duplicate handling: if the submitted `PLATFORM_ID` already exists in `config/overview.yaml`, the POST returns HTTP 409 with a Bootstrap alert fragment ("Already in your overview: {PLATFORM_ID}") which HTMX swaps into `#htmx-error-container` via the existing beforeSwap handler. The curated list is unchanged.
- **D-11:** Invalid `PLATFORM_ID` handling: if the submitted value is not present in `list_platforms_core` results (user typed a platform that doesn't exist in the DB), POST returns HTTP 404 with a Bootstrap alert "Unknown platform: {PLATFORM_ID}. Choose from the dropdown." The datalist already constrains most users but free-form typing is possible.

### Filter UX & persistence (Area 3)
- **D-12:** Filter controls live in a collapsible `<details>` block immediately above `#overview-list` and below the Add row. The `<summary>` reads "Filters" with a badge showing active-filter count when > 0.
- **D-13:** Filter block open-by-default on first visit; collapsed/expanded state stored in `localStorage` (client-side only, session-agnostic). This is the ONLY client-side persistence in Phase 2.
- **D-14:** The `<details>` body contains a single row `row g-2`:
  - Brand `<select class="form-select form-select-sm" data-filter>` with options: All brands + unique brands from curated list
  - SoC `<select class="form-select form-select-sm" data-filter>` with options: All SoCs + unique SoCs from curated list
  - Year `<select class="form-select form-select-sm" data-filter>` with options: All years + unique years from curated list (excluding entries where year=None)
  - "Has content" `<input type="checkbox" class="form-check-input" data-filter>` + label — three-state semantically (unchecked=show all, checked=show only with-content; v2.0 has no "only without-content" state)
- **D-15:** Trigger: `hx-trigger="change"` on every filter input. The FORM (wrapping all filters) has `hx-include="[data-filter]"`, `hx-post="/overview/filter"`, `hx-target="#overview-list"`, `hx-swap="innerHTML"`. Single request per change. No debounce (these are select/checkbox, not text inputs).
- **D-16:** Active-filter count: server-computed (counts how many of the 4 inputs are not at their default value). Returned as a small HTMX OOB swap into `#filter-count-badge` alongside the entity list fragment.
- **D-17:** "Clear all" link to the right of the summary, visible only when count > 0. Click: `hx-post="/overview/filter/reset"` which resets all filter inputs client-side (via OOB swap or a tiny JS handler) AND triggers a fresh list swap.
- **D-18:** NO persistence across browser refresh. Filters reset to "All / unchecked" on full page load. Documented as acceptable simplification for Phase 2; URL round-trip is deferred to a future milestone (OVERVIEW-F01).

### PLATFORM_ID parsing & Year lookup (FILTER-04 implementation)
- **D-19:** Parser module at `app_v2/data/platform_parser.py`:
  - `parse_platform_id(pid: str) -> tuple[str, str, str]` returns `(brand, model, soc_raw)` via `pid.split("_", 2)`. If fewer than 3 parts, unparseable parts are empty strings (defensive).
- **D-20:** Year lookup at `app_v2/data/soc_year.py`:
  - `SOC_YEAR: dict[str, int | None]` mapping known SoC prefixes to release year. Example entries: `"SM8450": 2022, "SM8550": 2023, "SM8650": 2024, "MT6985": 2023, "Exynos2200": 2022, …`
  - `get_year(soc_raw: str) -> int | None` — O(1) lookup; returns None for unknown.
  - Initial table has ~12 known SoCs covering the most common Samsung/Qualcomm/MediaTek/Exynos releases. Users can extend the table directly (Python dict, no config file yet).
- **D-21:** When `get_year` returns None, the entity's Year badge shows "Unknown" and is styled as `bg-secondary`. Unknown-year entities are STILL included in filter results when the Year filter is unset; they are EXCLUDED only when the user selects a specific year.

### Storage & routes
- **D-22:** `config/overview.yaml` schema:
  ```yaml
  entities:
    - platform_id: Samsung_S22Ultra_SM8450
      added_at: 2026-04-25T10:30:00Z
    - platform_id: Pixel8_GoogleTensor_GS301
      added_at: 2026-04-25T11:00:00Z
  ```
  Order = insertion order (append-to-front semantics on add). Remove deletes by platform_id.
- **D-23:** `.example.yaml` committed with 0 sample entries (empty `entities: []`); the live file is gitignored per v1.0 pattern.
- **D-24:** Service module at `app_v2/services/overview_store.py`:
  - `load_overview() -> list[OverviewEntity]` — reads YAML, returns list sorted newest-first (by added_at desc).
  - `add_overview(platform_id: str)` — atomic write via tempfile + os.replace; raises `DuplicateEntityError` on conflict.
  - `remove_overview(platform_id: str) -> bool` — returns True if removed, False if not found; atomic write.
- **D-25:** Routes live in `app_v2/routers/overview.py`:
  - `GET /overview` (and `/?tab=overview`) → render Overview tab with full base layout (via Jinja2Blocks `block_name=None`)
  - `POST /overview/add` → `hx-post` returns either 200 with ONE entity row fragment OR 409/404 with Bootstrap alert fragment
  - `DELETE /overview/{platform_id:path}` → 200 with empty body (HTMX swaps to `delete` = removes the element); `platform_id` validated by `Path(..., pattern=r'^[A-Za-z0-9_\-]{1,128}$')`
  - `POST /overview/filter` → 200 with entity-list fragment (via Jinja2Blocks `block_name="entity_list"`) + OOB swap for filter-count-badge
  - `POST /overview/filter/reset` → 200 empty entity list (server computes "no filters" = full list) + OOB swap badge to 0
- **D-26:** All 5 routes use `def` (sync), NOT `async def` — per INFRA-05.

### Claude's Discretion
- Exact Bootstrap Icons (bi-arrow-right-circle, bi-stars, bi-x chosen; replaceable if better options exist)
- Exact badge colors within Bootstrap's palette
- Whether to add `autocomplete="off"` on the typeahead input (recommend yes to avoid browser autofill fighting datalist)
- Exact phrasing of HTML page title (`<title>PBM2 — Overview</title>` recommended)
- Whether to prefetch `list_platforms_core` on app startup in lifespan (recommend no — first request is fine; 200+ platforms loads in ~50ms)
- Whether the filter block should have a subtle background color to separate it visually — Claude's call

</decisions>

<code_context>
## Existing Code Insights

### Reusable from Phase 1
- `app_v2/services/cache.py`: `cached_list_platforms(db, db_name=db_name)` returns the full `list[str]` of PLATFORM_IDs from `ufs_data`. Use for datalist population AND add-validation.
- `app_v2/templates/__init__.py`: `templates = Jinja2Blocks(directory=...)`. Import for all Overview routes. Use `templates.TemplateResponse(request, "overview/...", context, block_name=...)` for fragments.
- `app_v2/main.py`: `app.state.db`, `app.state.settings` available via `request.app.state`. Use `Depends(get_db)` DI pattern from Phase 1.
- `app_v2/static/js/htmx-error-handler.js`: already wired for 4xx/5xx errors. Phase 2 just emits Bootstrap alert fragments with status codes — handler picks them up automatically.
- `app/services/ufs_service.list_platforms_core(db, db_name)`: pure function for datalist options (cached via `cached_list_platforms`).

### Established Patterns
- HTMX targeting: `hx-target` by ID (e.g., `#overview-list`) preferred over CSS class targeting.
- Template partials via Jinja2Blocks `{% block entity_list %}…{% endblock %}` in `overview/index.html`. Full-page render returns the whole template; fragment render returns just the block.
- File atomicity: `os.replace(tmp, final)` pattern for YAML writes (same as v1.0 `save_settings`).
- Test layout: `tests/v2/test_overview.py` for Overview routes, `tests/v2/test_overview_store.py` for storage, `tests/v2/test_platform_parser.py` for PLATFORM_ID parsing.

### Integration Points
- Overview routes consume `cached_list_platforms` from cache.py — must pass `db_name` explicitly (per Phase 1 WR-01 style fix).
- Filter dropdown options are server-computed from the CURRENT curated list (not the full DB catalog), so they only show brands/SoCs/years actually in use.
- The base.html nav tab "Overview" gets `active` class via the current route (already wired in Phase 1 root.py; Phase 2 overview routes extend base.html with `{% set active_tab = "overview" %}`).

### New Files (expected in plans)
- `app_v2/routers/overview.py`
- `app_v2/services/overview_store.py`
- `app_v2/data/__init__.py`
- `app_v2/data/platform_parser.py`
- `app_v2/data/soc_year.py`
- `app_v2/templates/overview/index.html` (full page + fragment blocks)
- `app_v2/templates/overview/_entity_row.html` (single row partial, included by index.html)
- `app_v2/templates/overview/_filter_alert.html` (409/404 alert fragment)
- `config/overview.example.yaml`
- `.gitignore` update for `config/overview.yaml`
- `tests/v2/test_overview.py`
- `tests/v2/test_overview_store.py`
- `tests/v2/test_platform_parser.py`
- `tests/v2/test_soc_year.py`

</code_context>

<specifics>
## Specific Ideas

- Jinja2Blocks pattern for fragment rendering:
  ```python
  # Full page
  return templates.TemplateResponse(request, "overview/index.html", ctx)
  # Fragment only
  return templates.TemplateResponse(request, "overview/index.html", ctx, block_name="entity_list")
  ```
- OOB swap for filter badge: include `<span id="filter-count-badge" hx-swap-oob="true" class="badge bg-primary">{{ count }}</span>` inside the `entity_list` block response. HTMX picks it up automatically.
- Add duplicate returns 409 not 400 per REST convention (conflict with existing resource).
- `aria-label` on every icon-only button for a11y — Remove buttons especially.
- For the Year filter dropdown, sort years descending (newest first) so users see most-recent entries at top.
- If `config/overview.yaml` is missing or malformed at startup, lifespan should create an empty one rather than crashing (defensive; corrupted YAML → log warning, return empty list).

</specifics>

<deferred>
## Deferred Ideas

- **URL round-trip for filter state** (OVERVIEW-F01) — `?brand=Samsung&soc=SM8650` shareable links. Defer — HTMX has `hx-push-url` but syncing filter inputs back from URL on page load is non-trivial. Revisit in a polish milestone.
- **Drag-to-reorder entities** (OVERVIEW-F02) — requires JS lib or HTML5 drag-drop; complex for Phase 2. Defer.
- **Per-user curated lists** — requires auth (still deferred per D-04 v1.0 pattern). Defer.
- **Filter by content-page title or content body text** — would require grep over markdown files, N+1 I/O. Defer.
- **Faceted filter counts ("Samsung (8)")** — per research FEATURES.md this is explicitly anti-feature for small lists. Keep deferred.
- **Prefetch typeahead from full DB catalog (>500 platforms)** — if the DB grows >500 platforms, datalist performance may degrade. Defer and measure.
- **"Pin to top" for entities** — v3 feature. Defer.
- **Persistent filter state in session cookie** — Phase 3 introduces LLM-backend cookie; filter cookies could piggyback. Defer to v2.1.

</deferred>

---

*Phase: 02-overview-tab-filters*
*Context gathered: 2026-04-25 via smart discuss (autonomous, 3 grey areas accepted verbatim)*
