# Feature Research — v2.0 Bootstrap Shell

**Domain:** FastAPI + Bootstrap 5 + HTMX intranet data browser (UX rewrite of v1.0 Streamlit)
**Researched:** 2026-04-23
**Confidence:** HIGH for HTMX mechanics (verified against htmx.org official docs); MEDIUM for UX conventions (multiple credible sources, no single authoritative standard); MEDIUM for PLATFORM_ID parsing (project-internal convention, no external authoritative source)

---

## Context: v1.0 Features Already Delivered

The following features are carried forward from v1.0 (archived Streamlit code) and re-implemented in v2.0 under the new shell. They are **not** research targets here — their behavior is locked:

- EAV pivot grid (platform × parameter), swap-axes, row/col caps, Excel/CSV export
- Long-form Detail view, Chart tab (Plotly), result normalization pipeline
- NL agent (PydanticAI, dual OpenAI/Ollama), safety harness (sqlparse, LIMIT injector, path scrub, step-cap, timeout, `<db_data>` wrapper), NL-05 two-turn confirmation
- Settings CRUD for DB/LLM connections, sidebar health indicator

All five sections below address only the **net-new v2.0 features**.

---

## Feature 1: Curated Entity List (Overview Tab — Add/Remove/Display)

### What the feature is

A user-maintained, ordered set of PLATFORM_IDs drawn from the live `ufs_data` database. Displayed as a list of entity rows in the Overview tab. Users build this list over time; it is their "watchlist" of platforms they care about. Each entity row shows: platform title, link to content page, "AI Summary" button (when content exists), and metadata badges.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Typeahead search to add a platform | PLATFORM_IDs are long opaque strings (`Samsung_S22Ultra_SM8450`); free-text search is the only usable entry point | MEDIUM | Server-side: `GET /api/platforms?q=` returns JSON list; frontend: Bootstrap 5 `<datalist>` or a lightweight JS combobox (Tom Select, ~5KB); `hx-trigger="keyup changed delay:250ms"` debounce pattern from htmx.org docs |
| Remove button on each entity row | Users need to prune stale platforms; absence makes the list grow unboundedly | LOW | `DELETE /overview/<platform_id>` with `hx-delete` + `hx-swap="outerHTML"` on the row element; immediate optimistic removal |
| Persist list to disk | Without persistence across server restarts the list resets; intranet team expects state to survive | LOW | JSON or YAML file: `content/overview.json` (list of PLATFORM_IDs in order); atomic write (write-temp + rename); no DB needed |
| Display entity count | "Showing 12 platforms" confirms the list is populated and filters are in effect | LOW | Badge in Overview tab header: `12 platforms` |
| Recently-added sort (default) | Users want the platform they just added to appear first, not lost at the bottom | LOW | Append-to-front on add; `content/overview.json` stores ordered list; no drag UI needed for v2.0 |
| Empty state when list is empty | First run, or after removing all platforms — blank screen reads as broken | LOW | Full-panel empty state: "No platforms added yet. Search above to add your first platform." + add affordance visible |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| "Has content page" badge on entity row | Tells user at a glance which platforms have enriched notes vs which are bare entries | LOW | Server-side: check `content/platforms/<PLATFORM_ID>.md` existence; render `<span class="badge bg-secondary">No notes</span>` vs `<span class="badge bg-success">Notes</span>` |
| Drag-to-reorder | Power users who curate a specific comparison order | HIGH | Requires SortableJS or htmx's hx-on + custom drag events; defer to v2.x — recently-added order covers most needs |

### Anti-Features

| Feature | Why Requested | Why Avoid | Alternative |
|---------|---------------|-----------|-------------|
| Pagination of the entity list | Feels like good practice for large lists | The list is user-curated; a team of 5-10 analysts will not add 100+ platforms; pagination adds navigation friction for no real benefit | Enforce a soft cap (warn at 50 platforms); no pagination needed |
| Per-user lists (separate watchlists per login) | Seems personalized | Auth is deferred to a later milestone; shared-credential intranet means a single shared list is the right model for now | One shared list; the team curates it together |
| Bulk import from CSV | Analysts want to mass-add all platforms | Defeats the "curated" intent; the list should be small and deliberately chosen | Add one at a time; if a use case for "all platforms" emerges, the Browse tab already shows all |

---

## Feature 2: In-Place AI Summary (HTMX Swap)

### What the feature is

A button on each entity row in the Overview tab that, on click, fires an HTMX POST to `/summary/<platform_id>`, the server calls the LLM (reusing v1.0's `openai` SDK + `LLMConfig`), and the returned summary HTML fragment is swapped in-place. No navigation. No page reload.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Button visible only when content file exists | Summarizing nothing is meaningless; a disabled/hidden button confuses users | LOW | Server-side: render button only when `content/platforms/<PLATFORM_ID>.md` exists; hide it entirely otherwise (do not show as disabled) |
| Loading indicator during LLM call | LLM calls take 2-10s; blank wait reads as broken | LOW | `hx-indicator="#summary-spinner-{id}"` with `<span id="summary-spinner-{id}" class="htmx-indicator spinner-border spinner-border-sm">` adjacent to button; Bootstrap's `spinner-border` class works natively with htmx-indicator opacity pattern |
| `hx-swap="innerHTML"` on a summary container | The row structure must stay intact; only the summary content area updates | LOW | Pattern: `<div id="summary-{id}">` as target; `hx-post="/summary/{id}"` + `hx-target="#summary-{id}"` + `hx-swap="innerHTML"`; button stays in the row; summary div below the button expands with content |
| Error state in the summary div | LLM timeout or unavailable; user must see actionable feedback | LOW | Server returns `<p class="text-danger">Summary failed. Check LLM connection in Settings.</p>` as the fragment; no full-page error |
| Disable button while loading | Prevent double-submission on slow LLM responses | LOW | `hx-disabled-elt="this"` attribute on the button (HTMX 1.9+ / 2.x); disables the element during the request |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Session-level summary cache with "Regenerate" button | LLM calls are slow and expensive; regenerating on every page visit is wasteful | MEDIUM | Server-side: store generated summary in a Python `dict` keyed by PLATFORM_ID for the lifetime of the FastAPI process (simple in-memory cache; not persisted); show `<small class="text-muted">Generated {N}s ago</small>` timestamp next to summary; add `<button hx-post="/summary/{id}?regen=1">Regenerate</button>` that bypasses cache |
| Summary length preset (Short / Detailed) | Different use cases: quick scan vs deep review | MEDIUM | Pass `?length=short|detailed` to the endpoint; short = 2 sentences, detailed = 5 bullets; renders as separate prompt variants; add only if team requests it |

### Anti-Features

| Feature | Why Requested | Why Avoid | Alternative |
|---------|---------------|-----------|-------------|
| Summary persisted to disk alongside content file | "Save the summary so it loads instantly" | Creates a stale-cache problem: if the content page is edited, the persisted summary is wrong; unclear invalidation rule | Use session-level in-memory cache (resets on server restart or regen click); explicitly tell users summaries are not saved |
| Auto-summarize on page load for all entities | "Load all summaries at once" | N parallel LLM calls on page load would make the Overview feel slow and spike costs; also hides the intentional "I want to read this now" action | Lazy on-demand only; user explicitly clicks per entity |
| Stream the summary token-by-token (SSE) | Looks impressive; feels responsive | HTMX + SSE requires `hx-ext="sse"` and a streaming endpoint; adds infrastructure complexity for a feature that works fine with a 5s blocking call for an intranet tool | Blocking call with spinner is sufficient; add SSE only if LLM latency consistently exceeds 10s |

---

## Feature 3: Markdown Content Page CRUD

### What the feature is

Each platform in the curated list can have a hand-authored markdown file at `content/platforms/<PLATFORM_ID>.md`. Users can add, edit, and delete these files from the browser via HTMX forms. The content is rendered with `markdown-it-py` (Python-side rendering, returns HTML).

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| View rendered content page | The whole point; markdown rendered as HTML via `markdown-it-py`; served at `/content/<platform_id>` | LOW | `GET /content/<platform_id>` reads the `.md` file, renders via `markdown_it.MarkdownIt().render(text)`, returns full-page Jinja2 template |
| Edit button → in-place textarea swap | Users need a path to correct or extend notes; absence means the feature is read-only (frustrating) | MEDIUM | Two modes on the content page: view mode (`<div id="content-view">`) and edit mode (`<div id="content-edit" style="display:none">`); clicking Edit does `hx-get="/content/{id}/edit"` + `hx-swap="outerHTML"` on the view container to replace with a `<textarea>` pre-filled with raw markdown |
| Explicit Save button (not autosave) | Autosave creates "what version am I seeing?" confusion for an intranet tool used by multiple people | LOW | `hx-post="/content/{id}"` with the textarea value as body; server writes file atomically; returns the rendered view fragment; `hx-swap="outerHTML"` replaces the edit form back to view mode |
| Cancel without saving | Users accidentally click Edit; Cancel must restore view without a save round-trip | LOW | Cancel button does `hx-get="/content/{id}/view"` + `hx-swap="outerHTML"` to swap back to the rendered view fragment; or purely client-side: swap the textarea div back to the pre-rendered view div (no server call); prefer client-side for instant feedback |
| Add content page from empty state | If no `.md` file exists, users need a way to create one | LOW | Empty state on the content page shows: "No notes for this platform. [Add notes]" button; clicking sends `hx-get="/content/{id}/edit"` which returns the textarea with an empty value; Save creates the file |
| Delete content page | Old notes should be removable | LOW | Delete button with Bootstrap confirm modal (`data-bs-toggle="modal"`); confirm sends `DELETE /content/{id}`; server deletes file; response swaps the content area to empty state |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Preview tab (Write / Preview toggle) | Lets user verify markdown renders correctly before saving; standard pattern from GitHub, GitLab editors | MEDIUM | Two-tab Bootstrap nav inside the edit form: "Write" (textarea) and "Preview"; Preview tab fires `hx-post="/content/preview"` with textarea value, returns rendered HTML fragment into preview pane; implemented with Bootstrap's `data-bs-toggle="tab"` + HTMX for preview fetch |
| Line count / word count display | Quick authoring feedback; helpful for keeping notes concise | LOW | Client-side JS `textarea.addEventListener("input", ...)` updating a `<small>` character count below the textarea; no server call needed |

### Anti-Features

| Feature | Why Requested | Why Avoid | Alternative |
|---------|---------------|-----------|-------------|
| Autosave on blur or timer | Modern editor feel | For a multi-user intranet tool, autosave can silently overwrite a colleague's edit with a partial draft; the shared-credential model amplifies this risk | Explicit Save button; show "Unsaved changes" text indicator when textarea has been modified (client-side dirty flag) |
| Rich WYSIWYG editor (TipTap, ProseMirror) | Friendlier for non-markdown users | Adds a heavy JS dependency (~400KB) for a feature used by 2-3 people on an intranet; plain markdown in a `<textarea>` is sufficient for analysts | Plain textarea + Preview tab; if WYSIWYG is needed later, add EasyMDE (Ionaru/easy-markdown-editor, ~60KB) |
| Conflict detection / last-write-wins warning | "Two users might edit at once" | Shared-credential intranet with a tiny team; concurrent edits are extremely unlikely; the complexity of OCC (optimistic concurrency control) with ETags is not justified | Explicit Save + "last write wins"; note in the UI copy that saves overwrite; revisit if team scales |
| Image upload inside content pages | Notes might need screenshots | Adds file-upload endpoint, storage path decisions, and markdown `![]()` link management; out of scope for v2.0 | Link to external images by URL; if local images needed, add a `/static/uploads/` path in a later milestone |

---

## Feature 4: Faceted Filters (Overview Tab — Brand / SoC / Year / Has Notes)

### What the feature is

A filter bar above the curated entity list. Filters are derived by parsing PLATFORM_IDs and checking content file existence. Filter changes trigger HTMX-swapped list updates without page reload. Active filters are visible as badges.

### PLATFORM_ID Parsing Strategy

The convention is `Brand_Model_SoCID` (e.g., `Samsung_S22Ultra_SM8450`). Parsing approach:

```python
def parse_platform_id(pid: str) -> dict:
    parts = pid.split("_", 2)  # max 3 parts
    brand = parts[0] if len(parts) >= 1 else "Unknown"
    model = parts[1] if len(parts) >= 2 else ""
    soc_raw = parts[2] if len(parts) >= 3 else ""
    # SoC: strip variant suffix (SM8450-AB → SM8450)
    soc = soc_raw.split("-")[0] if soc_raw else ""
    return {"brand": brand, "model": model, "soc": soc}
```

**Year derivation:** Do NOT attempt to derive year from the PLATFORM_ID itself — there is no year token in the convention. Year must come from a lookup table keyed by SoC prefix. Known mappings (from Wikipedia and PhoneDB research, MEDIUM confidence):

| SoC Prefix | Year |
|------------|------|
| SM8350 | 2021 |
| SM8450 | 2022 |
| SM8550 | 2022–2023 |
| SM8650 | 2023–2024 |
| Exynos 2100 | 2021 |
| Exynos 2200 | 2022 |
| Exynos 2400 | 2024 |

Implementation: embed a `SOC_YEAR_MAP: dict[str, int]` in the parser module. When a SoC prefix is not in the map, Year = `None` → display as "Unknown" in the filter and exclude from year-filtered results (do not crash). Do not expose year filter if all platforms have `year = None`.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Brand filter (multi-select) | "Show me Samsung platforms only" is the most common filter on a list of 20+ mixed-brand platforms | LOW | `<select multiple>` or Bootstrap checkboxes; `hx-get="/overview/list"` + `hx-include="[name='brand']"` + `hx-trigger="change"` + `hx-target="#entity-list"` + `hx-swap="innerHTML"` |
| SoC filter (multi-select) | "All SM8550 variants" is a frequent comparison use case | LOW | Same pattern as Brand filter; derived from parsed SoC prefix |
| "Has notes" toggle | Finding platforms with authored content pages is a distinct browsing mode | LOW | Boolean checkbox: `hx-get="/overview/list"` with `has_notes=1`; server checks file existence |
| Active filter count badge | "3 filters active" confirms filters are in effect without reading all dropdowns | LOW | Derive client-side from selected filter values: `<span id="filter-badge" class="badge bg-primary">3</span>`; update via small inline script on filter change, or via HTMX OOB swap from server response |
| "Clear all filters" link | Users want to reset without clicking each filter individually | LOW | `<a hx-get="/overview/list" hx-target="#entity-list" hx-swap="innerHTML" onclick="resetFilters()">Clear all</a>` + client-side JS to uncheck all filter inputs; URL should reflect cleared state |
| Zero-result empty state | After filtering, showing nothing with no feedback reads as broken | LOW | Server returns `<div class="text-muted py-5 text-center">No platforms match the current filters. <a href="#" hx-get="/overview/list?clear=1" ...>Clear filters</a></div>` as the list fragment |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Year filter (derived from SoC lookup table) | "Show 2023+ platforms only" is a useful recency filter for teams tracking newer chipsets | MEDIUM | Build SoC→year lookup table (see above); only show year filter if at least one platform has a known year |
| URL round-trip for shareable filter state | Analysts paste "here's the filtered view I'm looking at" links in Slack | MEDIUM | Canonical approach: `hx-push-url="true"` on each filter request so `GET /overview?brand=Samsung&soc=SM8550` is the deep-linked URL; on server render, read query params and pre-select filters accordingly; note that `hx-push-url` requires the full-page render path to also honor these params (HTMX docs: "you must be able to navigate to that URL and get a full page back") |
| Text search over entity names | "Find 'ultra'" without knowing exact brand/SoC | LOW | `<input hx-get="/overview/list" hx-trigger="keyup changed delay:300ms" hx-include="[data-filter]" hx-target="#entity-list" name="q" placeholder="Search platforms...">` — server-side `ILIKE '%q%'` on PLATFORM_ID |

### Anti-Features

| Feature | Why Requested | Why Avoid | Alternative |
|---------|---------------|-----------|-------------|
| Year filter from regex/heuristic on model name | "The model name says 'S22' so it's 2022" | Model names are not reliably year-encoded across brands (e.g., Xiaomi 13 is not 2013); this heuristic is wrong more often than right | Use SoC lookup table only; display "Year: Unknown" when SoC is not in the map |
| Instant filter on every keypress (no debounce) | Feels responsive | Triggers a server round-trip per keystroke on text search; with 20 platforms this is fine but the debounce pattern costs nothing and is the HTMX community standard | Use `hx-trigger="keyup changed delay:300ms"` for text; `change` (no delay) for select/checkbox filters |
| Faceted count annotations ("Samsung (8)") | Common in e-commerce | Requires counting after every filter change across all dimension combinations; expensive for a small list; adds visual clutter | Show total count in header badge; don't annotate per-option counts |

---

## Feature 5: Tab Navigation (Overview / Browse / Ask)

### What the feature is

Horizontal top-of-page tab bar replacing Streamlit's sidebar navigation. Three tabs: Overview (new), Browse (v1.0 pivot grid), Ask (v1.0 NL agent). Tab switches update the main content area and push a URL query parameter for deep linking.

### Recommended Pattern

**Use Bootstrap's built-in tab component for client-side appearance + HTMX for content loading.** Do not use pure HTMX tab simulation. The combination is the most maintainable approach for an intranet Bootstrap 5 app.

Architecture:
- Tab `<button>` elements carry both `data-bs-toggle="tab"` (Bootstrap state management) and `hx-get="/tabs/<name>"` + `hx-target="#tab-content"` (HTMX content fetch)
- On first click, HTMX loads the tab content and caches it in the DOM (prevent reload guard: `if(evt.detail.target.hasChildNodes()){ evt.preventDefault() }` per Marcus Obst's pattern)
- For URL deep linking: use `hx-push-url="/app?tab=overview"` (custom value, not `true`) so the URL reflects the active tab; server reads `?tab=` on full-page load and pre-renders the correct tab active

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Active tab highlighting | Any tab component does this; absence looks broken | LOW | Bootstrap `nav-link active` class; managed by Bootstrap's JS; no custom code needed |
| Tab content loaded once, cached in DOM | Switching to Browse and back to Overview must not re-run the pivot query | LOW | The hasChildNodes guard prevents HTMX re-request when tab has already been populated; revert to full reload only on explicit refresh trigger |
| URL reflects active tab (deep link) | Analysts share "go to the Ask tab" links in Slack | MEDIUM | `hx-push-url="/app?tab=<name>"` on each tab click; server reads `?tab=` param on initial full-page render to set the correct `active` class and pre-load content |
| Back button returns to previous tab | Standard browser navigation expectation | MEDIUM | HTMX `hx-push-url` + Bootstrap tab activation on `popstate` event (small JS listener: `window.addEventListener("popstate", ...)` reads URL and activates the corresponding tab); this requires ~10 lines of JS, which is acceptable |
| Keyboard navigation between tabs | Accessibility expectation | LOW | Bootstrap's built-in keyboard handling (arrow keys) works natively with `role="tablist"` pattern; no extra work needed |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Tab badge showing count (e.g., "Overview (12)") | Entity count visible without switching to the tab | LOW | Server renders tab button with count in `<span class="badge">12</span>`; update via HTMX OOB swap when overview list changes |

### Anti-Features

| Feature | Why Requested | Why Avoid | Alternative |
|---------|---------------|-----------|-------------|
| Client-side-only tab routing (hash-based `#overview`) | Simpler JS | Hash-based routing does not survive a full page refresh in FastAPI — the server receives a request for `/app#overview` where the `#overview` is not sent to the server; `?tab=` query param is the correct approach for server-rendered apps | Use `?tab=` query param with `hx-push-url` |
| Lazy-load each tab on every activation (no caching) | Ensures fresh data | Browse tab re-running the pivot query every time the user glances at another tab and back is jarring; the hasChildNodes guard is the right trade-off; explicit refresh button on Browse tab covers the "I need fresh data" case | Cache tab content in DOM; add explicit refresh icon on data-heavy tabs |

---

## Feature 6: Empty States

Each distinct empty condition requires its own state — not a generic "nothing here" message.

| Surface | Trigger | Table-Stakes Copy | Primary Action |
|---------|---------|-------------------|---------------|
| Overview list (no platforms added) | `content/overview.json` is empty or missing | "No platforms added yet. Search above to add your first platform." | Add platform search bar always visible at top |
| Overview list (after filters yield zero results) | Filters applied, no matches | "No platforms match the current filters." | "Clear filters" link that resets all filter inputs |
| Content page (no `.md` file) | File does not exist | "No notes for this platform yet." | "Add notes" button that opens the edit textarea |
| Summary area (button clicked, content missing) | Edge case: file deleted between page load and click | "Content page removed. Add notes first." | Return 404 fragment with copy above |
| Summary area (LLM error) | LLM call fails or times out | "Summary failed. Check LLM connection in Settings." | Link to Settings tab |
| Browse tab (no platforms selected) | No filter selection | "Select platforms and parameters in the sidebar to build the pivot grid." | (same as v1.0 Browse empty state — reuse exact copy) |
| Ask tab (no question submitted) | Initial state | Starter prompt gallery (same as v1.0) | 8-prompt grid |

---

## Feature 7: Entity Row Layout and Information Density

### Recommended layout: horizontal list row (not card grid)

Cards are appropriate for rich-media content (images, varied descriptions). Platform entities are uniform, text-only objects. A horizontal list row (`.list-group-item`) provides better information density for this use case:

```
[Brand badge] [PLATFORM_ID title]     [SoC badge] [Year badge] [Notes badge]     [Summary ▶] [Edit] [Remove]
```

**Column breakdown (Bootstrap `d-flex` row):**
- Left 60%: Platform name (styled as `<strong>`) + model sub-label in muted text
- Center 25%: Metadata badges (Brand, SoC, Year, Notes status)
- Right 15%: Action buttons (AI Summary, Edit/View notes, Remove)

### Badge design

Use Bootstrap's contextual badge colors for quick scanning:
- Brand: `badge bg-primary` (blue — identity)
- SoC: `badge bg-secondary` (grey — technical ID)
- Year: `badge bg-info text-dark` (teal — temporal)
- Has notes: `badge bg-success` / `badge bg-light text-muted border` — yes/no distinction is the most important signal; use color contrast
- AI summary cached: `badge bg-warning text-dark` — small "Cached" badge next to the summary text when the in-memory cache was used

### Entity row density: keep it scannable

- Maximum 3 lines per row: title line, metadata badge line, summary expansion (hidden by default)
- Summary text expands below the row (accordion-style) when the AI Summary button is clicked; it does NOT open a new page or modal
- Summary text is capped at 250 characters display (truncate with "..." + "Show more" toggle if longer)

---

## Feature Dependencies

```
Overview Tab
    └──requires──> Curated entity list (content/overview.json read/write)
    └──requires──> PLATFORM_ID parser (brand/soc/year extraction)
    └──requires──> FastAPI + Bootstrap 5 + HTMX shell (TAB-01)

Faceted Filters
    └──requires──> PLATFORM_ID parser
    └──requires──> Overview entity list loaded
    └──enhances──> Entity list display (swapped result on filter change)

AI Summary button
    └──requires──> Content page exists (content/platforms/<id>.md)
    └──requires──> LLM adapter (reused from v1.0 app/adapters/llm.py)
    └──requires──> Entity row rendered with summary container div

Content Page CRUD (Edit/Save/Delete)
    └──requires──> FastAPI file I/O (read/write content/platforms/<id>.md)
    └──requires──> markdown-it-py rendering endpoint
    └──enhances──> AI Summary (provides the markdown that Summary reads)
    └──enhances──> "Has notes" badge (file existence check)

Tab Navigation (Overview/Browse/Ask)
    └──requires──> Bootstrap 5 nav-tabs + HTMX hx-get per tab
    └──Browse tab requires──> v1.0 pivot grid ported to Jinja2/Bootstrap
    └──Ask tab requires──> v1.0 NL agent wired to FastAPI endpoint

URL Deep Link (tab + filter state)
    └──requires──> hx-push-url on tab clicks and filter changes
    └──requires──> Server reads ?tab=, ?brand=, ?soc= on full-page render

ufs_service.py refactor (st.cache_data → cachetools.TTLCache)
    └──required by──> Browse tab (pivot grid needs cached DB queries without Streamlit)
    └──required by──> PLATFORM_ID filter list (distinct platform IDs from DB)
```

---

## MVP Definition (v2.0 Milestone)

### Launch With

These are the features that make v2.0 coherent as a product. Without any one of them the rewrite is incomplete.

- [ ] Horizontal tab nav (Overview / Browse / Ask) with URL deep link — structural requirement; all other features live inside it
- [ ] Overview tab: add platform via typeahead, remove platform, persist to `content/overview.json` — core CRUD without which the tab is empty
- [ ] Entity row with metadata badges (Brand, SoC, Year, Notes status) — required for the list to be readable
- [ ] Faceted filters: Brand + SoC + "Has notes" toggle, HTMX-swapped — without filters the list is unusable above ~10 platforms
- [ ] Empty states for all five distinct surfaces (see Feature 6) — absence makes the app feel broken
- [ ] Content page CRUD: Add / Edit / Save / Delete via HTMX forms, markdown rendered server-side — enables the AI Summary button
- [ ] AI Summary button: HTMX POST → LLM call → in-place swap, with loading indicator and error state — the v2.0 differentiating feature
- [ ] Browse tab: pivot grid re-implemented in Bootstrap (port of v1.0, not redesign) — data value preserved
- [ ] Ask tab: NL agent under new shell (port of v1.0) — NL value preserved
- [ ] `ufs_service.py` refactor: `st.cache_data` → `cachetools.TTLCache` — prerequisite for Browse/Ask to work outside Streamlit

### Add After Validation (v2.x)

- [ ] Year filter (SoC lookup table) — add when team complains "I can't filter by year"
- [ ] Summary cache with regenerate button and timestamp — add when team reports re-clicking Summary and finding stale results
- [ ] Preview tab in content page editor — add when team reports writing broken markdown
- [ ] Drag-to-reorder entity list — add when team reports wanting a specific comparison order
- [ ] Text search over entity names — add when list grows beyond 20 platforms and filter combination is insufficient

### Future Consideration (v2.1+)

- [ ] Summary persistence to disk with invalidation on content edit — requires cache invalidation logic
- [ ] Rich WYSIWYG markdown editor (EasyMDE) — only if analysts resist plain textarea
- [ ] Per-tab "data freshness" indicator (last query time) — only if team reports stale-data confusion
- [ ] SSE streaming for AI Summary — only if LLM latency regularly exceeds 10 seconds

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Tab navigation shell (Overview/Browse/Ask) | HIGH | LOW | P1 |
| Add/remove platform (entity CRUD) | HIGH | LOW | P1 |
| Entity row with metadata badges | HIGH | LOW | P1 |
| Brand + SoC + "Has notes" filters (HTMX-swapped) | HIGH | MEDIUM | P1 |
| Empty states (all surfaces) | HIGH | LOW | P1 |
| Content page Add/Edit/Save/Delete | HIGH | MEDIUM | P1 |
| AI Summary button (HTMX in-place, loading indicator) | HIGH | MEDIUM | P1 |
| Browse tab pivot grid (Bootstrap port) | HIGH | MEDIUM | P1 |
| Ask tab NL agent (Bootstrap port) | HIGH | MEDIUM | P1 |
| ufs_service.py cachetools refactor | HIGH (blocker) | LOW | P1 |
| URL deep link for tab + filter state | MEDIUM | MEDIUM | P2 |
| Year filter (SoC lookup table) | MEDIUM | MEDIUM | P2 |
| Summary in-memory cache + regenerate button | MEDIUM | LOW | P2 |
| Content page preview tab | MEDIUM | LOW | P2 |
| Text search over entity names | MEDIUM | LOW | P2 |
| Drag-to-reorder entity list | LOW | HIGH | P3 |
| SSE streaming for AI Summary | LOW | HIGH | P3 |
| Rich WYSIWYG editor (EasyMDE) | LOW | MEDIUM | P3 |

---

## HTMX Pattern Reference (for executor)

All HTMX patterns below are verified against the official htmx.org documentation.

| Use Case | HTMX Attributes | Notes |
|----------|----------------|-------|
| Filter change → list refresh | `hx-get="/overview/list" hx-trigger="change" hx-include="[data-filter]" hx-target="#entity-list" hx-swap="innerHTML"` | `data-filter` attribute on all filter inputs for `hx-include` selection |
| Text search debounce | `hx-get="/overview/list" hx-trigger="keyup changed delay:300ms" hx-target="#entity-list" hx-swap="innerHTML"` | `changed` modifier prevents firing when value hasn't changed |
| AI Summary in-place swap | `hx-post="/summary/{id}" hx-target="#summary-{id}" hx-swap="innerHTML" hx-indicator="#spinner-{id}" hx-disabled-elt="this"` | Spinner sibling uses `class="htmx-indicator"` (opacity:0 by default) |
| Remove entity from list | `hx-delete="/overview/{id}" hx-target="closest .list-group-item" hx-swap="outerHTML swap:300ms"` | `swap:300ms` delay allows CSS fade-out before DOM removal |
| Content edit swap | `hx-get="/content/{id}/edit" hx-target="#content-view-{id}" hx-swap="outerHTML"` | Replaces entire view container with edit form |
| Tab content load | `hx-get="/tabs/overview" hx-target="#tab-content" hx-swap="innerHTML" hx-push-url="/app?tab=overview"` | Guard with `hasChildNodes` check to prevent reload |
| Deep link on full-page load | Server reads `request.query_params.get("tab", "overview")` and sets `active` class on the corresponding tab button and renders the correct content | FastAPI reads the `?tab=` param; no HTMX involved on initial load |

---

## Integration with v1.0 Reused Modules

| Module | Reuse Pattern | Changes Needed |
|--------|--------------|----------------|
| `app/adapters/llm.py` (LLM factory) | Import directly; call `build_client()` to get the `openai.OpenAI` instance | None — framework-agnostic |
| `app/adapters/db.py` (MySQLAdapter) | Import directly; call `run_query()` for Browse/Ask pivot queries | None — framework-agnostic |
| `app/core/config.py` (Pydantic Settings) | Import directly; `Settings.load()` reads the same `config/settings.yaml` | None — framework-agnostic |
| `app/core/result_normalizer.py` | Import directly; apply to pivot DataFrames as in v1.0 | None — pure Python function |
| `app/pages/nl_agent.py` (PydanticAI agent) | Import agent; wrap in FastAPI endpoint returning HTML fragment | None to agent logic; new FastAPI endpoint wrapper needed |
| `app/services/ufs_service.py` | Must refactor: replace `@st.cache_data` with `cachetools.TTLCache` | REQUIRED before v2.0 Browse/Ask tabs can work |

---

## Sources

- HTMX official docs — hx-indicator: https://htmx.org/attributes/hx-indicator/
- HTMX official docs — hx-swap: https://htmx.org/attributes/hx-swap/
- HTMX official docs — hx-push-url: https://htmx.org/attributes/hx-push-url/
- HTMX official docs — hx-trigger with debounce: https://htmx.org/docs/ (Trigger Modifiers section)
- Marcus Obst — Bootstrap 5 tabs with HTMX (hasChildNodes guard pattern): https://marcus-obst.de/blog/use-bootstrap-5x-tabs-with-htmx
- TestDriven.io — FastAPI + HTMX (HX-Request header detection, fragment patterns): https://testdriven.io/blog/fastapi-htmx/
- Shape of AI — AI summary UX patterns (trust, transparency, regenerate): https://www.shapeof.ai/patterns/summary
- NNGroup — Empty state design guidelines: https://www.nngroup.com/articles/empty-state-interface-design/
- Qualcomm SoC year lookup — SM8450/SM8550/SM8650 release years: https://en.wikipedia.org/wiki/List_of_Qualcomm_Snapdragon_systems_on_chips
- Pencil & Paper — Filter UX patterns: https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-filtering
- Smart Loading Patterns with HTMX (htmx-indicator usage): https://blog.openreplay.com/smart-loading-patterns-htmx/
- HTMX Progress Bar example (polling + HX-Trigger response header): https://htmx.org/examples/progress-bar/

---

*Feature research for: PBM2 v2.0 Bootstrap Shell — FastAPI + Bootstrap 5 + HTMX UX rewrite*
*Researched: 2026-04-23*
