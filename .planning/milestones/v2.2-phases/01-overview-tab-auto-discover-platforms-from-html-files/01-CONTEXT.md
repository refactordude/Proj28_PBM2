---
phase: 01-overview-tab-auto-discover-platforms-from-html-files
type: context
created: 2026-04-30
status: locked
---

# Phase 1: Overview Tab — Auto-discover Joint Validations from HTML Files — Context

> **Naming clarification:** the roadmap title says "Auto-discover Platforms from HTML Files" but the entity in scope is **Joint Validation** — a new domain object that is *not* mapped to `PLATFORM_ID` / `ufs_data`. Joint Validation has its own identifier (Confluence page ID), its own metadata (parsed from each `index.html`), and its own listing surface. The Overview tab is being **replaced** to show Joint Validations instead of Platforms.

<domain>
## Phase Boundary

**In scope (this phase):**
- Replace what the Overview tab shows: Platforms → Joint Validations.
- New source of truth: glob `content/joint_validation/<numeric_id>/index.html` (one folder per Joint Validation; folder name is the Confluence page ID).
- Parse 13 fields directly from each `index.html` (title from `<h1>` + 12 fields from `<strong>Field</strong>` rows).
- Reuse the v2.0 Phase 5 grid + filter + sort infrastructure (popover-checklist filters, sticky-top Bootstrap table, URL round-trip, mtime-keyed cache pattern).
- New detail page `GET /joint_validation/<id>` that renders parsed metadata as a properties table on top + the original `index.html` body in an `<iframe sandbox>` below.
- Static-mount `content/joint_validation/` so the iframe can resolve `/static/joint_validation/<id>/index.html`.
- AI Summary feature carries forward (modal pattern from D-OV-15) but its input is now the parsed text of `index.html`.
- Delete all Platform-curated Overview machinery: `config/overview.yaml`, `app_v2/services/overview_store.py`, the Platform metadata flow on Overview, `POST /overview/add`.

**Out of scope (NOT this phase):**
- Editing Joint Validations from the UI (they are exported from Confluence; the app is read-only here).
- Confluence API integration / in-app import flow (drop-folder workflow only — see D-JV-09).
- Removing or modifying Browse / Ask tabs — both still consume `PLATFORM_ID` from `ufs_data`.
- Removing `content/platforms/*.md` or the `/platforms/<PID>` detail/edit pages — Browse rows still link there.
- Keeping the legacy "Add platform" form anywhere in the app.
- Date-range filtering on Start / End (sort only; same precedent as D-OV-07).
- Filter on Title / Model Name / Assignee (sort-only — same precedent as Phase 5).
- Multi-select / batch operations.

</domain>

<decisions>
## Implementation Decisions

> Decision IDs use a fresh `D-JV-*` namespace (Joint Validation) so they do not collide with Phase 5's `D-OV-*` namespace, which remains valid for the Platform-side artifacts that are NOT being removed (`/platforms/<PID>` detail page, `content/platforms/*.md`, content_store.py frontmatter reader).

### Source & discovery

#### D-JV-01 — Tab scope: replace Overview's Platform list with Joint Validation list

The Overview tab content is wholesale replaced. Top-nav URL stays `/overview`; the visible tab label changes from "Overview" to **"Joint Validation"**. The tab no longer shows curated platforms; it shows auto-discovered Joint Validation folders. Browse and Ask tabs are untouched.

#### D-JV-02 — Source of truth: `content/joint_validation/<numeric_id>/index.html`

Discovery is a directory glob: `content/joint_validation/*/index.html`. Each match is one Joint Validation row.

The directory name **must** be the lowercase-underscore form `joint_validation/` (NOT `Joint Validation/` with a space, NOT `joint-validation/` with a hyphen). Reason: matches the Python module-naming convention already used in `app_v2/` (browse_service, content_store, …) and avoids URL-encoding spaces in the static-mount path.

#### D-JV-03 — Folder name validation: numeric only (`^\d+$`)

A folder under `content/joint_validation/` is a valid Joint Validation **iff** its name matches `^\d+$` (digits only) AND it contains a readable `index.html`. Anything else (`_drafts`, `README`, `.DS_Store`, `assets`, partial folder without `index.html`) is silently skipped — no warning, no surfaced error. This is also the path-traversal backstop for the static mount.

#### D-JV-04 — Metadata extraction: parse `<strong>Field</strong>` rows directly from `index.html`

No sidecar metadata file. No frontmatter. No Confluence API. The HTML is parsed in-process with **BeautifulSoup4** (new dependency). For each Joint Validation row, extract these fields:

| Field | Source rule |
|---|---|
| `title` | First `<h1>` tag, text content verbatim |
| `status` | Cell adjacent to a `<strong>Status</strong>` label |
| `customer` | Cell adjacent to a `<strong>Customer</strong>` label |
| `model_name` | Cell adjacent to a `<strong>Model Name</strong>` label |
| `ap_company` | Cell adjacent to a `<strong>AP Company</strong>` label |
| `ap_model` | Cell adjacent to a `<strong>AP Model</strong>` label |
| `device` | Cell adjacent to a `<strong>Device</strong>` label |
| `controller` | Cell adjacent to a `<strong>Controller</strong>` label |
| `application` | Cell adjacent to a `<strong>Application</strong>` label |
| `assignee` | Cell adjacent to a `<strong>담당자</strong>` label (Korean key — UTF-8 throughout) |
| `start` | Cell adjacent to `<strong>Start</strong>`; extract `YYYY-MM-DD` |
| `end` | Cell adjacent to `<strong>End</strong>`; extract `YYYY-MM-DD` |
| `link` | `<a href="…">` inside the cell adjacent to `<strong>Report Link</strong>` |

Locator strategy: find the `<strong>` element, walk to its nearest sibling `<td>` (Confluence "Page Properties" macro emits `<th><strong>Field</strong></th><td>value</td>`); fall back to the next-sibling cell of the parent if the immediate sibling is empty. **First match wins** when a label appears more than once on the page.

#### D-JV-05 — Missing field → blank cell (NOT em-dash)

If a `<strong>Field</strong>` row is absent or its value cell is empty, render the column as an empty string `""` in the grid. This is a **deliberate departure** from Phase 5 D-OV-09's `—` em-dash sentinel. Rationale: the Joint Validation metadata is parsed from semi-structured HTML; the user wants visually clean cells rather than sentinel noise.

Title fallback when `<h1>` is missing: render the `confluence_page_id` (e.g., `3193868109`) so the row is still clickable to the detail page.

### Cleanup of Platform-curated Overview machinery

#### D-JV-06 — Delete the Platform-curated yaml + supporting code

The following are **deleted** in this phase:

- `config/overview.yaml` (the curated entity list)
- `app_v2/services/overview_store.py` (load/add/remove against the yaml)
- `app_v2/services/overview_filter.py` (`has_content_file` helper — Platform-md-specific; superseded by Joint Validation discovery)
- `app_v2/services/overview_grid_service.py` (Platform-frontmatter view-model; replaced by a new Joint-Validation-aware service — see D-JV-12)
- `app_v2/templates/overview/_filter_bar.html`, `_grid.html`, `index.html` — fully rewritten (NOT renamed) for Joint Validation columns and rows
- The `OverviewEntity` / `DuplicateEntityError` Pydantic types
- All v2.0 tests for the deleted units (e.g., `tests/v2/test_overview_store.py`, `tests/v2/test_overview_grid_service.py`, `tests/v2/test_overview_filter.py`); the test_overview_routes.py / test_phase05_invariants.py will be rewritten or replaced with Joint Validation equivalents.

These are **kept** unchanged:

- `content/platforms/*.md` — Browse + Ask still consume `PLATFORM_ID` from `ufs_data`; the per-platform markdown still backs `/platforms/<PID>` detail/edit pages.
- `app_v2/services/content_store.py` — still needed for `/platforms/<PID>` markdown CRUD.
- `app_v2/routers/platforms.py` and `/platforms/<PID>` detail/edit/preview routes.

#### D-JV-07 — Delete `POST /overview/add`

The Platform-curated Add form is removed. There is no analogous "Add Joint Validation" affordance — Joint Validations appear by dropping a folder under `content/joint_validation/`. See D-JV-09.

### Behavior

#### D-JV-08 — Cache: mtime-keyed in-process memo per `index.html`

Mirror the Phase 5 D-OV-12 pattern. A module-level dict keyed by `(confluence_page_id, mtime_ns)` caches the parsed metadata. A change to the HTML file changes the mtime → cache miss → re-parse. Bounded to `len(found_pages)`. Per-process; single uvicorn process is the deployment baseline.

The directory glob itself is NOT cached — re-glob on every request so newly-dropped folders appear immediately. Glob cost on local SSD with ~100 dirs is sub-millisecond.

#### D-JV-09 — Onboarding: drop-folder workflow only

A new Joint Validation appears by copying a folder structured `content/joint_validation/<numeric_id>/index.html` (plus any image/asset files referenced inside) into the repo. The next `GET /overview` re-globs and shows it. No in-app form, no Refresh button, no Confluence import wizard.

#### D-JV-10 — Default sort: `start desc`, tiebreaker `confluence_page_id ASC`

Matches the Phase 5 D-OV-07 contract verbatim. Empty/blank/malformed `start` values sort to the END regardless of asc/desc (so blank-date rows do not pollute the top of the default view). Sort cycles asc → desc → asc on header click; no "unsorted" state. Default first-click on an unsorted column = asc. Date columns parse `YYYY-MM-DD` into a sortable form but render the original string back to the cell.

#### D-JV-11 — Six popover-checklist filters (same set as Phase 5)

Filter columns: `status`, `customer`, `ap_company`, `device`, `controller`, `application`. Reuse the Phase 4 `picker_popover` macro AS-IS (already parameterized with `form_id` since v2.0 Phase 5). D-15b auto-commit + 250ms debounce + form-association + OOB filter-badge swap all carry forward.

Sortable columns include all 12 data fields (the 11 above + `model_name` + `ap_model` + `assignee` + `start` + `end`). The Action column (Report Link, AI Summary buttons) is NOT sortable. Title is sortable.

### URL & routing

#### D-JV-12 — Routes: `GET/POST /overview` listing stays; new `GET /joint_validation/<id>` detail

- `GET /overview` (and `GET /`) — full page, hydrates from `?status=…&customer=…&sort=start&order=desc` per the unchanged D-OV-13 URL shape.
- `POST /overview/grid` — fragment swap; returns blocks `["grid", "count_oob", "filter_badges_oob"]`. `HX-Push-Url` set to canonical `/overview?...`.
- `GET /joint_validation/<numeric_id>` — new detail page. Renders parsed metadata as a properties table + `<iframe sandbox="allow-same-origin">` whose `src` is `/static/joint_validation/<id>/index.html`.

The existing `/overview/add`, `/overview/filter`, `/overview/filter/reset`, `/overview/<pid>` (DELETE) routes stay deleted (Phase 5 already removed the latter three; this phase removes the first).

#### D-JV-13 — Static mount for the Confluence body

Add `app.mount("/static/joint_validation", StaticFiles(directory="content/joint_validation"), name="joint_validation_static")` in `app_v2/main.py`. Serves the `index.html` and any sibling assets (images, CSS, JS exported by Confluence) so the detail-page iframe can resolve them. The `^\d+$` directory-name guard (D-JV-03) plus FastAPI StaticFiles' built-in path normalization is the path-traversal backstop.

#### D-JV-14 — URL state shape (unchanged from D-OV-13)

`/overview?status=A&status=B&customer=X&ap_company=Y&device=Z&controller=W&application=V&sort=start&order=desc` — repeated keys for multi-value filters; FastAPI parses to `list[str]` via `Query(default_factory=list)`. `sort` and `order` are single-valued.

### UI

#### D-JV-15 — Row actions: two buttons (Report Link + AI Summary)

The Action column has exactly **two** buttons per row, matching the Phase 5 v2.0 button shape (Bootstrap `btn-sm` with icon):

1. **Report Link** — opens the parsed `link` value in a new tab (`target="_blank" rel="noopener noreferrer"`); URL sanitizer drops dangerous schemes (`javascript:`, `data:`, `vbscript:`, `file:`, `about:`) and promotes bare domains to `https://` (port D-OV-16 verbatim). Disabled when `link` is empty.
2. **AI Summary** — same modal popup pattern as Phase 5 D-OV-15. Opens a Bootstrap modal; HTMX-fetches a summary from the LLM; renders into the modal body.

The row's title cell is itself a link to `/joint_validation/<id>` (no separate "View" button).

#### D-JV-16 — AI Summary input pre-processing

Before sending the page content to the LLM, the parser removes nodes that bloat context and add no value:

1. Decompose all `<script>`, `<style>`, and `<img>` tags (the user explicitly flagged inline base64 image `src` attributes as a token-blow-up risk).
2. Call `BeautifulSoup.get_text(separator='\n')` to extract human-readable text.
3. Collapse runs of blank lines.
4. The existing `nl_service.max_context_tokens=30000` cap is the final clamp; no separate truncation logic.

The summary route reuses Phase 3's `summary_service.py` pattern (TTLCache + Lock + always-200 contract), with the prompt text adjusted for "Joint Validation page" instead of "platform notes".

#### D-JV-17 — Empty state

When `content/joint_validation/` does not exist OR contains zero folders matching `^\d+$/index.html`:

- Render the table chrome + filter bar normally.
- Filter popovers are rendered but disabled (no values to filter on).
- The `<tbody>` contains a single full-width row with the helper text:
  > **No Joint Validations yet.** Drop a Confluence export at `content/joint_validation/<page_id>/index.html`.
- The count caption reads "0 entries".

### Claude's Discretion

- **HTML parser implementation:** BeautifulSoup4 is the locked library. The exact selector strategy for `<strong>Field</strong>` row → value cell (e.g., `find_parent('tr')` + `find('td')` vs. `find_next_sibling('td')`) is left to the implementer; needs to handle both `<th><strong>Field</strong></th><td>value</td>` and `<p><strong>Field</strong>: value</p>` layouts gracefully.
- **Date parsing:** `datetime.date.fromisoformat()` is sufficient; on parse failure, treat as blank/missing for sort purposes but render the raw string in the cell.
- **AI Summary prompt copy:** wording is Claude's discretion. Carry tone from the Platform AI Summary prompt (concise, structured, no marketing language).
- **Sample HTML fixture for tests:** the user does not have a sample file to provide — the implementer creates a representative fixture (`tests/v2/fixtures/joint_validation_sample.html`) that exercises the locked extraction rules + at least one missing-field case + one image with a long base64 `src` to verify pre-processing.
- **Top-nav label color/icon:** Bootstrap defaults; `.nav-link` styling unchanged. Label is the literal string "Joint Validation".

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & project-level
- `.planning/ROADMAP.md` — Phase 1 entry (under "Next Milestone")
- `.planning/PROJECT.md` — v2.0 stack constraints; Active requirements; current Overview definition (being replaced)
- `.planning/STATE.md` — current project state (no active milestone; v2.0 shipped)

### Phase 5 (v2.0) — baseline being replaced; patterns being reused
- `.planning/milestones/v2.0-phases/05-overview-redesign/05-CONTEXT.md` — D-OV-01..D-OV-16 (filter, sort, URL, cache, sentinel patterns)
- `.planning/milestones/v2.0-phases/05-overview-redesign/05-VERIFICATION.md` — Phase 5 verification baseline
- `.planning/milestones/v2.0-phases/04-browse-tab-port/` — picker_popover macro origin + D-15b debounce contract
- `.planning/milestones/v2.0-phases/03-content-pages-ai-summary/` — AI Summary modal + summary_service.py pattern (Phase 3)

### Code being modified or referenced
- `app_v2/main.py` — needs new StaticFiles mount for `/static/joint_validation`
- `app_v2/routers/overview.py` — Platform-curated routes deleted; Joint Validation routes added
- `app_v2/templates/overview/index.html` — full rewrite (column headers, action buttons)
- `app_v2/templates/overview/_grid.html` — full rewrite
- `app_v2/templates/overview/_filter_bar.html` — full rewrite (filter set unchanged in shape; data source different)
- `app_v2/templates/browse/_picker_popover.html` — reused AS-IS (already parameterized for cross-tab use)
- `app_v2/static/js/popover-search.js` — reused AS-IS (D-15b)
- `app_v2/services/overview_grid_service.py` — replaced by `joint_validation_grid_service.py` (read for pattern, then delete)
- `app_v2/services/overview_store.py` — deleted (read for the load/atomic-write pattern, even though disk yaml is gone)
- `app_v2/services/overview_filter.py` — deleted
- `app_v2/services/summary_service.py` — pattern reference for the new Joint Validation summary route
- `app_v2/services/cache.py` — TTLCache pattern reference
- `app_v2/templates/platforms/detail.html` — pattern reference for the new `joint_validation/detail.html`

### New code to add
- `app_v2/services/joint_validation_store.py` — globs `content/joint_validation/*/index.html`, validates `^\d+$` folder names, returns parsed-metadata view-models with mtime-keyed cache
- `app_v2/services/joint_validation_parser.py` — BeautifulSoup4 extraction of the 13 fields per D-JV-04
- `app_v2/services/joint_validation_grid_service.py` — view-model builder (filters, sort, count) — replaces overview_grid_service.py
- `app_v2/routers/joint_validation.py` — new `GET /joint_validation/<id>` detail route (or co-locate in overview.py — implementer's call)
- `app_v2/templates/joint_validation/detail.html` — properties table + iframe sandbox
- `app_v2/templates/overview/_summary_modal.html` — if not already factored from Phase 5; AI Summary modal
- `tests/v2/test_joint_validation_parser.py`, `tests/v2/test_joint_validation_grid_service.py`, `tests/v2/test_joint_validation_routes.py`, `tests/v2/test_joint_validation_invariants.py`
- `tests/v2/fixtures/joint_validation_sample.html` — representative HTML fixture (see Claude's Discretion)

### New dependency
- `requirements.txt` — add `beautifulsoup4>=4.12` (and optionally `lxml>=5.0` as the parser backend; `html.parser` works without it but is slower and stricter)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`browse/_picker_popover.html` macro** — accepts `form_id` parameter (added in v2.0 Phase 5). Phase 1 calls it with `form_id="overview-filter-form"`; macro definition unchanged.
- **`popover-search.js`** — D-15b auto-commit (250ms debounce) + form-association + checkbox-state sync. Reused unchanged.
- **`summary_service.py` pattern** — TTLCache + asyncio.Lock + openai SDK single-shot; the new Joint Validation summary route follows the same shape.
- **AI Summary modal markup** (Phase 5 D-OV-15) — Bootstrap modal with `hx-target` pointing to a slot inside the modal body; reused with the route URL swapped.
- **URL sanitizer** for the Report Link button (Phase 5 D-OV-16) — drops `javascript:` / `data:` / `vbscript:` / `file:` / `about:` schemes; promotes bare domains to `https://`. Reused verbatim.
- **OOB filter-badge swap** (Phase 4 gap-3 / Phase 5 `filter_badges_oob` block) — reused for the six picker triggers.
- **`HX-Push-Url` canonical-URL composition** (Phase 4 D-32 / Phase 5 `_build_overview_url`) — reused with the same query-key set (status, customer, ap_company, device, controller, application, sort, order).

### Established Patterns
- **All routes are sync `def`** — FastAPI dispatches to threadpool (INFRA-05); BeautifulSoup parsing is CPU-bound and stays out of the event loop without extra ceremony.
- **Cache keyed by mtime_ns** — same idiom as Phase 5 D-OV-12; in-process dict, bounded to known set size, invalidation is implicit via mtime.
- **Block-based template rendering** with `block_names=[...]` — Phase 4/5 idiom for HTMX fragment swaps; reused for `POST /overview/grid`.
- **Pydantic view-models** for service-to-template handoff — `OverviewGridViewModel` shape is the template; rename to `JointValidationGridViewModel` with new column shape.
- **Path validation BEFORE filesystem touch** — D-JV-03 `^\d+$` regex applied as the first gate in any function that path-joins `content/joint_validation/<id>/...`.

### Integration Points
- **`app_v2/main.py`** — add a second `app.mount(...)` call for `/static/joint_validation`; lifespan unchanged.
- **`app_v2/routers/__init__.py`** — register the new joint_validation router (if a separate router file is used) or extend the overview router.
- **`app_v2/templates/base.html`** — top-nav label change (`Overview` → `Joint Validation`); URL stays `/overview`.
- **`app_v2/services/llm_resolver.py`** — reused unchanged for AI Summary backend resolution; the existing `pbm2_llm` cookie + Ask-page LLM dropdown drive both Ask AND Joint Validation AI Summary.

</code_context>

<specifics>
## Specific Ideas

- The user named the new domain object **Joint Validation** explicitly to differentiate it from Platform; the term must appear verbatim in the nav label, page heading, and any error/empty-state copy.
- The `<strong>담당자</strong>` row is in **Korean** — the parser must use UTF-8 throughout and not fold the label to ASCII. Match the literal `담당자` byte sequence in the `<strong>` text.
- The user provided no real sample of `index.html`; only a description of the locator pattern. The implementer must build a representative fixture (see Claude's Discretion) and treat the parser as best-effort: fields that fail to extract render blank.
- **Image src bloat is a real concern**, not a hypothetical: Confluence exports occasionally inline images as base64 data URIs that can be hundreds of KB each. The pre-processor in D-JV-16 explicitly decomposes `<img>` (not just strips tags around them) so the `src` attribute never reaches `get_text()` output even via attribute serialization.
- The single sample `confluence_page_id` mentioned by the user is `3193868109`. Useful as a fixture name in tests.
- Default sort `start desc` is the same default as Phase 5 — preserves muscle memory for users coming from the v2.0 Overview.

</specifics>

<deferred>
## Deferred Ideas

- **In-app Confluence import** (URL paste → app fetches HTML → saves to `content/joint_validation/<id>/`): out of scope for this phase. Adds network/auth/error-UX complexity and is its own phase if and when needed.
- **Date-range filter on Start / End**: deferred (sort only is sufficient for the curated set size). Matches Phase 5's same deferral.
- **Filter on Title / Model Name / Assignee**: deferred (sort only). Matches Phase 5's same deferral.
- **Bulk-select / batch operations**: not requested.
- **Keep `config/overview.yaml` as a 'pin/hide' override layer**: presented as an option; user chose the simpler "delete all of it" path. Can be revisited in a future phase if curation needs re-emerge.
- **'Refresh' button** to manually invalidate the parse cache: unnecessary because the cache is mtime-keyed; deferred (would only matter if mtime updates lag the file write, which is not a typical concern on local FS).
- **Confluence API integration / live metadata fetch**: deferred — would replace D-JV-04's HTML-scrape approach. Trade-off: less brittle parsing but adds Confluence reachability + auth as runtime dependencies.
- **Removing `content/platforms/*.md` and `/platforms/<PID>` detail page**: explicitly out of scope. Browse + Ask still need PLATFORM_IDs from `ufs_data`; the per-platform markdown still backs an in-app detail/edit surface that is unaffected by this phase.

</deferred>

---

*Phase: 01-overview-tab-auto-discover-platforms-from-html-files*
*Context gathered: 2026-04-30 via interactive discuss-phase. Replaces Platform-curated Overview with Joint Validation auto-discovery.*
