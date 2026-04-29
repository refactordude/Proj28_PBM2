# Phase 04: Browse Tab Port - Context

**Gathered:** 2026-04-26
**Status:** Ready for planning
**Mode:** Interactive smart discuss (4 grey areas; export feature scope-removed mid-discussion)

<domain>
## Phase Boundary

Re-implement v1.0's pivot-grid browsing experience (platforms × parameters wide-form table, swap-axes, row/col caps, shareable URLs) under FastAPI + Bootstrap + HTMX in the v2.0 shell. Phase 4 delivers the Browse tab as a **view-only** surface — no Excel/CSV export in v2.0 (BROWSE-V2-04 scope-removed; see "Required upstream edits" below).

Delivers:
- GET `/browse` (and `/?tab=browse`) rendering the Browse tab content via Jinja2Blocks
- Top inline filter bar inside the Browse `.panel`: Platforms picker, Parameters picker, Swap-axes toggle, Clear-all link, count caption
- Popover-checklist multiselect widget (search input + scrollable checklist + Apply/Clear footer) used by both Platforms and Parameters pickers
- POST `/browse/grid` returning the pivot-grid fragment (bound by row-cap=200 and col-cap=30)
- Bootstrap `<table class="table table-striped table-hover">` with `<thead class="sticky-top">` for the pivot grid; every cell rendered as text
- Row-cap and column-cap warnings with **exact v1.0 copy**: "Result capped at 200 rows. Narrow your platform or parameter selection to see all data." and "Showing first 30 of {N} parameters. Narrow your selection to see all."
- URL query-param round-trip (`?platforms=…&params=…&swap=1`) so links are shareable; opening a URL directly renders the correctly-filtered grid (BROWSE-V2-05)

Scope OUT of Phase 4:
- **Excel/CSV export** — REMOVED entirely. BROWSE-V2-04 moves to REQUIREMENTS.md "Out of Scope" with reason "v1.0 Streamlit Browse remains the export surface until v1.0 sunset"
- **Detail surface** (single-platform long-form view from v1.0) — deferred
- **Chart surface** (Plotly bar/line/scatter from v1.0) — deferred
- Per-user filter persistence; saved filter presets — defer
- Brand/SoC/Year facets like Phase 2 Overview — Browse picks platforms by name, not by facet
- Schema-level filters (InfoCategory grouping in the Parameters picker UI) — keep flat alphabetical for now

</domain>

<decisions>
## Implementation Decisions

### Visual language pinned to Dashboard_v2.html (carried forward from Phase 3)

All UI uses tokens already wired into `app_v2/static/css/tokens.css` + `app_v2/static/css/app.css`. No further visual discussion:

- `.panel` for the Browse card container (white bg, border-radius 22px, padding 18-26px, soft shadow)
- `--bg #f3f4f6`, `--ink #171c24`, `--ink-2 #4a5361`, `--mute #8b93a0`, `--accent #3366ff`
- Inter Tight 15px base; **JetBrains Mono for the pivot-grid cell content** (mono numbers/hex align visually)
- Page shell max-width 1280px (Phase 1 base.html)

### Surface scope (Area 1)

- **D-01:** Phase 4 ports **only the Pivot grid**. Detail and Chart surfaces from v1.0 are NOT ported in this phase.
- **D-02:** v1.0 Streamlit Browse (3-tab Pivot/Detail/Chart) remains running on port 8501 as the fallback for users who need Detail or Chart. v2.0 lives in parallel on port 8000.
- **D-03:** Plotly stays in `requirements.txt` (v1.0 still imports it). v2.0 must NOT import Plotly anywhere under `app_v2/`. A Phase 4 codebase invariant test (grep guard, same pattern as Phase 03 banned-libraries test) enforces "no plotly import in app_v2/".

### Filter UI layout (Area 2.1)

- **D-04:** Filter controls live in a **top inline filter bar** inside the Browse `.panel`, above the pivot grid. Single-row layout: `[Platforms ▾ N] [Parameters ▾ N] [⇄ Swap axes] ............ [Clear all] [count caption]`. Pivot grid gets full panel width below the filter row.
- **D-05:** Filter bar uses `d-flex align-items-center gap-2 mb-3`. Picker trigger buttons use `btn btn-outline-secondary btn-sm` with caret icon (`bi-chevron-down`) and selection-count badge. The `[⇄ Swap axes]` toggle is a Bootstrap `btn-check`-styled toggle button (active/inactive variants).
- **D-06:** Count caption sits at the right end of the filter bar: text "{N} platforms × {K} parameters" using `text-muted small` styling. Mirrors v1.0 BROWSE-06 row-count indicator semantics.

### Multiselect widget (Area 2.2)

- **D-07:** Both Platforms and Parameters pickers use the **popover-checklist-with-search** pattern, NOT a typeahead-add-chip pattern, NOT a native `<select multiple>`, and NOT a JS lib (Choices.js, TomSelect). Pure Bootstrap dropdown + ~30 lines of vanilla JS for the search filter.
- **D-08:** Picker trigger button shows the current selection count as a badge: `[Platforms ▾ 3]`. Empty selection shows just `[Platforms ▾]` (no badge).
- **D-09:** Popover content (rendered server-side as a Bootstrap `.dropdown-menu` keyed `data-bs-toggle="dropdown"` with `data-bs-auto-close="outside"`):
  - **Header:** `<input type="search" class="form-control form-control-sm" placeholder="Search platforms…">` — focused on popover open
  - **Body:** scrollable `ul.list-unstyled` with each row = `<label class="dropdown-item d-flex"><input type="checkbox">{label}</label>`. `max-height: 320px; overflow-y: auto;`
  - **Footer:** sticky bottom bar with `[Clear]` (left) and `[Apply (N)]` (right, `btn-primary`)
- **D-10:** Search input is **client-side substring filter** (case-insensitive). Vanilla JS handler hides `<li>` rows where `data-label.toLowerCase().includes(query.toLowerCase())` is false. Zero round-trips per keystroke. Reusable `app_v2/static/js/popover-search.js` module attached to all `.popover-search` widgets via event delegation on the document.
- **D-11:** Server renders the FULL candidate list once when the page loads (not lazily on popover open). Cached via `cached_list_platforms(db, db_name=db_name)` (Phase 1 INFRA-08) and `cached_list_parameters(db, db_name=db_name)`. Acceptable up-front HTML cost: ~50KB for 500 platforms; instant interaction afterward.

### Filter source (Area 2.3)

- **D-12:** Both pickers draw from the **full DB catalog**, NOT the curated Overview list. Browse is for ad-hoc exploration (PROJECT.md core value); it must work even when Overview is empty or doesn't cover the platform a user wants to look at. Matches v1.0 behavior exactly.
- **D-13:** Parameter labels shown in the popover use the v1.0 combined-label format `"{InfoCategory} · {Item}"` sorted by InfoCategory ASC then Item ASC (carry from v1.0 UI-SPEC §178). Carry the same parsing rule when round-tripping selected labels through the URL.

### Filter trigger model (Area 3.1)

- **D-14:** ~~Selections inside a popover are **LOCAL until the user clicks `[Apply]`**...~~ **SUPERSEDED 2026-04-28 by D-15b** after gap-5 UAT replay. The 2-click Apply workflow was rejected by the user as friction; the original concern (5 toggles ≠ 5 queries) is now addressed by client-side debounce inside D-15b instead of by an explicit commit gesture. Original wording preserved here for audit only.
- **D-15:** ~~Popover-internal Clear button...~~ **SUPERSEDED 2026-04-28 by D-15b**. Clear button persists (clicking it unchecks all in this picker) but no longer has revert/cancel semantics — there is no longer a stashed "original selection" to revert to. The unchecked state IS the new selection; the debounced commit fires automatically.
- **D-15a:** ~~Close-event taxonomy...~~ **SUPERSEDED 2026-04-28 by D-15b**. With auto-commit per-toggle, all close paths are equivalent (just close the popover); there is no commit/cancel distinction to resolve. The implementation in commit `6b97921` and the taxonomy in commits `a9f6089`/`a2d6cb3` are reverted by gap-5 closure.
- **D-15b (NEW 2026-04-28):** **Auto-commit on each checkbox change with 250ms client-side debounce.**
  - Each `change` event on a picker checkbox bubbles to the `<ul class="popover-search-list">` checklist container, which carries `hx-post="/browse/grid" hx-target="#browse-grid" hx-swap="innerHTML swap:200ms" hx-trigger="change changed delay:250ms from:closest .popover-search-root"`.
  - HTMX's built-in `delay:250ms` trigger modifier handles the debounce — 5 quick toggles in < 250ms collapse to a single POST request. This addresses the original D-14 "5 toggles ≠ 5 queries" concern without needing an explicit commit gesture.
  - The Apply button is **REMOVED** from the popover footer. The Clear button stays (clicking it unchecks all in this picker, the bubbling change events fire the same debounced commit, the resulting empty-selection grid renders the empty-state alert if no other selections exist).
  - Top-level "Clear all" link (D-17) is unchanged.
  - Esc, outside-click, Tab-away all just close the popover — no commit/cancel distinction. The checkbox state at any moment IS the truth; the debounce commits it shortly after the last change regardless of how the popover closes.
  - `data-bs-auto-close="outside"` (D-09) stays so the popover remains open across multiple toggles for ergonomics (user can pick N items in a row).
  - Trigger button badge update path is **unchanged** — the `picker_badges_oob` OOB swap from gap-3 fires on every POST `/browse/grid` response, so the trigger badge updates server-side after the debounced request lands.
  - The form-association from gap-2 (`form="browse-filter-form"` on each checkbox) continues to work — HTMX auto-includes form-associated inputs of the triggering element via the FormData iteration in `getInputValues()`.
  - **Net code simplification:** popover-search.js shrinks by ~150 lines (the entire close-event taxonomy + dataset.applied/cancelling/originalSelection logic is removed). The contract is uniform across all close paths; HTMX's built-in `delay:` trigger is the only debouncer.
- **D-16:** Swap-axes toggle is a different beast: it's a **view transform of the already-fetched DataFrame**, not a re-query. Triggers immediately on click via `hx-post=/browse/grid` with `swap=1` flag — no Apply needed. The cached `_core` DataFrame is re-pivoted server-side with `swap_axes=True/False` and the table fragment swapped.

### Clear all (Area 3.2)

- **D-17:** Top-level **`Clear all` text link** in the filter bar, next to (or replacing) the count caption when count > 0. Hidden via `d-none` when no filters set. Click resets BOTH platforms and parameters AND triggers a single grid swap (empty grid + empty-state message).
- **D-18:** Clear-all is a single `hx-post=/browse/clear` (or `/browse/grid` with empty form), NOT two separate per-popover Clear actions.

### Export UX — REMOVED (Area 4)

- **D-19:** **Phase 4 ships no export feature.** No `[Export]` button, no `/browse/export/xlsx` route, no `/browse/export/csv` route, no openpyxl call in `app_v2/`. The `app_v2/templates/browse/` tree contains no export modal/dropdown templates.
- **D-20:** **BROWSE-V2-04 must be moved to REQUIREMENTS.md "Out of Scope"** before planning starts. Add reason row: "Excel/CSV export under v2.0 shell — v1.0 Streamlit Browse remains the export surface until v1.0 sunset; v2.0 Browse is view-only by design choice (2026-04-26 user decision)."
- **D-21:** **ROADMAP.md Phase 4 success criterion #3** ("User can download the current pivot grid as Excel (.xlsx) or CSV; the export reflects the active filter state and respects the row/col caps") **must be deleted**. Phase 4 success criteria become 3 (filter swap, caps, URL round-trip) instead of 4.
- **D-22:** `app/components/export_dialog.py` and `_sanitize_filename` in v1.0 are NOT touched, NOT copied, NOT imported. They remain available exclusively to v1.0 Streamlit code.

### Caps + warnings (carry from v1.0)

- **D-23:** Row cap = 200, column cap = 30 (matches v1.0 `fetch_cells` and `pivot_to_wide` defaults — NO change). Both caps are server-enforced; the route returns the capped DataFrame plus boolean flags `row_capped`/`col_capped`.
- **D-24:** Cap-warning copy is verbatim from v1.0 UI-SPEC:
  - Row-cap: `"Result capped at 200 rows. Narrow your platform or parameter selection to see all data."`
  - Col-cap: `"Showing first 30 of {N} parameters. Narrow your selection to see all."`
  - Rendered as a Bootstrap `alert alert-warning py-2 small` ABOVE the pivot grid (NOT inside the table).
- **D-25:** Empty-state copy must be updated for v2.0 (v1.0 said "in the sidebar" but v2.0 has no sidebar): `"Select platforms and parameters above to build the pivot grid."` Rendered as `alert alert-info` in the grid slot when the selection is empty.

### Pivot grid rendering (BROWSE-V2-02)

- **D-26:** `<table class="table table-striped table-hover table-sm">` (table-sm for density on a wide grid). `<thead>` uses `class="sticky-top bg-light"` so the header row stays visible on vertical scroll inside the panel.
- **D-27:** Every cell rendered as text via Jinja2 `| e` autoescape. NO column type config — mirrors v1.0's TextColumn-only approach because EAV `Result` values are heterogeneous (hex, decimal, CSV, error strings, etc.) and per-query lazy coercion is the wrong layer to render here. Cells use `font-family: var(--mono)` (JetBrains Mono) for visual alignment.
- **D-28:** Horizontal scroll behavior: the entire `.panel` body wraps the table in `<div class="table-responsive">`. With 30 cols × variable widths, horizontal scroll is expected on common monitor widths. **No sticky-left first column** in this phase — accept horizontal scroll for the index column too. (Sticky-left adds significant CSS complexity; deferred unless users request it.)
- **D-29:** `aggfunc="first"` for pivot duplicate handling — same as v1.0 `pivot_to_wide`. Re-uses `app/services/ufs_service.pivot_to_wide_core()` (Phase 1 INFRA-06 pure function).

### URL round-trip (BROWSE-V2-05)

- **D-30:** Query params: `platforms` and `params` use **repeated keys** (`?platforms=A&platforms=B`) rather than comma-separated, because (a) FastAPI parses repeated keys natively into `list[str]` via `Query(default=[])`, (b) PLATFORM_IDs and parameter labels can contain `_` and `·` but not commas (validated upstream), and (c) URL length under repeated-keys is fine for the 30-col cap (typical max URL ~2.5KB, well under 8KB browser limit).
- **D-31:** `swap` param is `"1"` if axes swapped, omitted otherwise — same convention as v1.0 BROWSE-09.
- **D-32:** `hx-push-url="true"` on the `/browse/grid` swap so the URL updates without a full page reload as filters change. Server-rendered initial GET reads the same query params and pre-checks the popover checkboxes accordingly.
- **D-33:** Param-label encoding in URL: pass the raw combined label (`"attribute · vendor_id"`); FastAPI/Starlette URL-encodes on the wire. Server splits on the literal `" · "` separator to recover `(InfoCategory, Item)` for the SQL filter. Defensive: round-trip integration test asserts a label survives full encoding cycle.

### Routes summary

| Method | Path | Purpose | Returns |
|--------|------|---------|---------|
| GET | `/browse` | Browse tab page (full HTML, with optional pre-filtered grid from query params) | Full HTML page via Jinja2Blocks (no `block_name`) |
| GET | `/?tab=browse` | Redirect/alias to `/browse` | 302 to `/browse` (preserve query params) |
| POST | `/browse/grid` | Grid fragment for filter changes / Apply / swap-axes | `<table>...</table>` + cap-warning fragment + count caption (OOB swap) |

(Two routes — was four before BROWSE-V2-04 was scope-removed.)

### Sync vs async

- **D-34:** All Browse routes use `def` (NOT `async def`) per INFRA-05. SQLAlchemy-touching functions (`fetch_cells_core`, `pivot_to_wide_core`) are sync; FastAPI dispatches `def` routes to the threadpool.

### Claude's Discretion

- Exact Bootstrap Icons (`bi-chevron-down`, `bi-arrow-left-right` for swap, `bi-x` for clear chips — all replaceable)
- Exact dropdown popover width (suggest min-width 320px, max-width 480px to accommodate long parameter labels)
- Whether the popover row labels truncate with ellipsis on overflow (recommend yes, with `title=` tooltip showing full label)
- Whether to show count "({N})" inside `[Apply (N)]` button vs just `[Apply]` (recommend with count for trust)
- Exact debounce on the search input (50ms recommended for client-side; can be zero)
- Whether to memorize the popover-internal selection draft across open/close cycles when the user navigates away without Apply (recommend: discard on close — simpler mental model)
- Exact copy for the "no platforms selected" / "no parameters selected" partial empty states (e.g., when user picks platforms but no parameters yet)
- HTMX swap animation timing (suggest `hx-swap="innerHTML swap:200ms"` for a subtle fade)
- Whether the search input has `autocomplete="off"` (recommend yes)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 4 contract
- `.planning/ROADMAP.md` — Phase 4 section (success criterion #3 needs deletion as part of D-20/D-21 cleanup)
- `.planning/REQUIREMENTS.md` — BROWSE-V2-01, BROWSE-V2-02, BROWSE-V2-03, BROWSE-V2-05 (BROWSE-V2-04 must be moved to "Out of Scope" before planning starts)
- `.planning/PROJECT.md` — "Browse carry-over (v2.0)" section under Active; Out of Scope row about Plotly carry; core-value priority "fast ad-hoc browsing"

### v1.0 source for the port (the authoritative behavior reference)
- `app/pages/browse.py` — v1.0 Browse page; pivot tab logic in `_render_pivot_tab()` (lines 212–326). Filters in `_render_sidebar()` (lines 134–207). URL helpers `_load_state_from_url()` / `_update_url_from_state()` (lines 54–110).
- `.planning/milestones/v1.0-phases/01-foundation-browsing/01-UI-SPEC.md` — §"Pivot Tab" (lines 177–199), §"Cap warnings" (lines 316–318), §"Empty/loading states" (lines 327–340), §"Shareable URL Contract" (lines 299–313). Empty-state copy must be UPDATED for v2.0 (no sidebar).

### Reusable v1.0 modules (import unchanged)
- `app/services/ufs_service.py` — `list_platforms_core`, `list_parameters_core`, `fetch_cells_core`, `pivot_to_wide_core` (Phase 1 INFRA-06 pure functions)
- `app/services/result_normalizer.py` — `normalize()`, `try_numeric()` (lazy per-query coercion). Browse currently does NOT call `try_numeric` because cells are rendered as text — but `normalize()` is applied inside `fetch_cells_core`.

### v2.0 Phase 1/2 patterns to follow
- `app_v2/services/cache.py` — TTLCache + threading.Lock pattern for `cached_list_platforms` / `cached_list_parameters` / `cached_fetch_cells` / `cached_pivot_to_wide`. Reuse the existing wrappers; if a `cached_fetch_cells`/`cached_pivot_to_wide` doesn't yet exist, add it via the same recipe.
- `app_v2/templates/__init__.py` — `templates = Jinja2Blocks(directory=...)` for fragment+page rendering from one template
- `app_v2/static/js/htmx-error-handler.js` — global 4xx/5xx swap handler (already wired in base.html)
- `app_v2/routers/overview.py` — Phase 2 reference for HTMX form submission, OOB swaps for badges, fragment vs full-page rendering pattern via `block_name=...`

### Visual language
- `/home/yh/Desktop/02_Projects/Proj27_PBM1_fork_bootstrap/Dashboard_v2.html` — Dashboard reference (Inter Tight, JetBrains Mono, `.panel` card pattern, color tokens, `.ai-btn` violet pill — though no AI affordances are used on the Browse page itself). Note: Dashboard_v2.html does NOT contain a wide-form pivot/data-grid pattern; the table styling for Browse is new territory under the established tokens.

### Pitfalls to consult
- `.planning/phases/03-content-pages-ai-summary/03-PITFALLS.md` (if exists) — patterns around HTMX OOB swaps, fragment rendering with `block_name`, sync def + threadpool concerns
- `.planning/phases/02-overview-tab-filters/02-PITFALLS.md` (if exists) — HTMX `hx-swap` ordering, `hx-include` form aggregation, OOB badge swaps

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable from prior phases
- `app/services/ufs_service.list_platforms_core(db, db_name)` — pure function returning `list[str]` of all PLATFORM_IDs in `ufs_data`. Phase 4 calls via `cached_list_platforms`.
- `app/services/ufs_service.list_parameters_core(db, db_name)` — pure function returning `list[tuple[InfoCategory, Item]]`. Phase 4 formats into combined labels.
- `app/services/ufs_service.fetch_cells_core(db, db_name, platforms, params, row_cap=200)` — pure function returning `(df_long, row_capped: bool)`.
- `app/services/ufs_service.pivot_to_wide_core(df_long, swap_axes=False, col_cap=30)` — pure function returning `(df_wide, col_capped: bool)`.
- `app_v2/services/cache.py` — `cached_list_platforms`, `cached_list_parameters` already exist (used by Phase 2). New wrappers needed: `cached_fetch_cells`, `cached_pivot_to_wide`.
- `app_v2/templates/__init__.py::templates` (Jinja2Blocks) — same engine. New templates under `app_v2/templates/browse/`.
- `app_v2/main.py` — register the new `browse` router; `app.state.db` and `app.state.settings` available via `request.app.state`.

### Established patterns (HTMX 2.0.10)
- `hx-target="#browse-grid"` + `hx-swap="innerHTML"` for grid swap
- `hx-trigger="click"` on Apply button inside popover; `hx-trigger="change"` on the swap-axes toggle
- `hx-include="[name='platforms'],[name='params'],[name='swap']"` to aggregate hidden form fields holding the current selection
- OOB swap pattern for the count caption: `<span id="grid-count" hx-swap-oob="true">{N} platforms × {K} parameters</span>` rendered inside the grid response body, lands in the persistent shell
- `hx-push-url="true"` on the grid swap to keep URL in sync with filters

### Dropdown auto-close behavior (Bootstrap 5)
- `data-bs-auto-close="outside"` keeps the popover open during checkbox interactions; only an outside-click closes it without Apply.
- Manual Bootstrap dropdown API can be used to close on Apply: `bootstrap.Dropdown.getInstance(triggerEl).hide()` from the Apply button's `hx-on:click` handler (after the HTMX request fires).

### Integration points
- `app_v2/routers/__init__.py` — register new `browse` router after `platforms` (Phase 3), before `root.py`
- `app_v2/main.py::include_router(browse.router)` ordering matters because `root.py` keeps `/browse` GET stub from Phase 1 — DELETE that stub when wiring the real `browse` router (Phase 4 owns `/browse`).
- `base.html` nav tab "Browse" already has `active_tab == 'browse'` styling logic (Phase 1) — Phase 4 templates set `{% set active_tab = "browse" %}`.
- `cached_list_platforms` / `cached_list_parameters` are TTLCache-backed (Phase 1 INFRA-08); calling them on every Browse GET is cheap.

### New Files (expected in plans)
- `app_v2/routers/browse.py` (GET /browse, POST /browse/grid)
- `app_v2/services/browse_service.py` (orchestration: parses filter form, calls cached_fetch_cells + cached_pivot_to_wide, returns view-model)
- `app_v2/templates/browse/index.html` (full page + fragment blocks)
- `app_v2/templates/browse/_filter_bar.html` (filter bar fragment)
- `app_v2/templates/browse/_picker_popover.html` (popover-checklist partial — reused for Platforms and Parameters via macro)
- `app_v2/templates/browse/_grid.html` (pivot table fragment)
- `app_v2/templates/browse/_empty_state.html`, `app_v2/templates/browse/_cap_warnings.html`
- `app_v2/static/js/popover-search.js` (~30 lines vanilla JS for client-side substring filter)
- `app_v2/services/cache.py` — extend with `cached_fetch_cells`, `cached_pivot_to_wide` (if not already present)
- `tests/v2/test_browse_routes.py` (route tests + URL round-trip)
- `tests/v2/test_browse_service.py` (filter parsing, view-model assembly)
- `tests/v2/test_popover_search.py` (JS unit tests via the AppTest pattern OR a Python test that asserts the rendered HTML structure of the popover; defer Playwright)

### Codebase invariant guards (Phase 03 pattern)
- Static-grep guard: assert `from app.components.export_dialog` does NOT appear under `app_v2/` (export feature is removed)
- Static-grep guard: assert `import plotly` / `from plotly` does NOT appear under `app_v2/` (Plotly stays out of v2.0)
- Static-grep guard (extension of Phase 03): assert no `async def` on Browse route handlers

</code_context>

<specifics>
## Specific Ideas

- **Popover-checklist pattern is the centerpiece UI decision.** Build it as a reusable Jinja macro `{% macro picker_popover(name, label, options, selected) %}` in `_picker_popover.html` — both Platforms and Parameters reuse it. Future phases (Ask tab parameter confirmation) can adopt the same widget if the pattern proves out.
- **Apply button is a hard requirement** — popover toggles do NOT trigger DB queries. This is the core perceived-performance decision: with 200-row pivot queries, change-triggered firing (5 toggles = 5 queries) is unacceptable. Make this explicit in test names ("test_popover_toggle_does_not_fetch", "test_apply_triggers_single_fetch").
- **No export = no openpyxl/csv code under app_v2/.** Codebase invariant test should assert no import. v1.0's `app/components/export_dialog.py` stays untouched; openpyxl stays in `requirements.txt` because v1.0 still uses it.
- **URL round-trip is testable with a single round-trip integration test:** GET `/browse?platforms=Samsung_S22Ultra_SM8450&params=attribute · vendor_id&swap=1` → 200 with the popover checkboxes pre-checked AND the grid pre-rendered with swap=1.
- **Empty-state copy MUST change from v1.0's "in the sidebar" to "above"** — caught by D-25; downstream agents must not blindly copy the v1.0 string.
- **Parameter-label sort order** is alphabetical by combined label `"{InfoCategory} · {Item}"` (not by InfoCategory ASC then Item ASC as separate keys). Test that `"attribute · zzz"` sorts before `"flags · aaa"`.
- **30-col / 200-row caps stay at the v1.0 numbers**, NOT relaxed under HTMX. The intuition that "HTMX can handle bigger" is wrong: row count drives DB load + render cost, not transport.
- **Phase 04 should pre-allocate codebase invariant guard tests** (extending Phase 03's static-analysis grep tradition) for: no plotly under app_v2/, no openpyxl under app_v2/, no `async def` on browse routes, no import of `app/components/export_dialog`.

</specifics>

<deferred>
## Deferred Ideas

- **Detail surface port** — single-platform long-form view from v1.0 Browse Detail tab. Defer; v1.0 Streamlit Browse remains fallback. Could be folded into the existing `/platforms/{id}` page (Phase 3) as a "Show parameters" section in a future phase, OR ported as `/browse/detail` if Detail-only workflow proves needed.
- **Chart surface port** — Plotly bar/line/scatter from v1.0 Browse Chart tab. Defer; v1.0 Streamlit Browse remains fallback. Plotly stays in requirements.txt for v1.0; if chart port revives, vendor `plotly.min.js` to `app_v2/static/vendor/plotly/` (intranet has no CDN) and use `fig.to_html(full_html=False, include_plotlyjs="/static/vendor/plotly/plotly.min.js")` for HTMX injection.
- **Excel/CSV export under v2.0 shell** — REMOVED from Phase 4 entirely (BROWSE-V2-04 scope-out). v1.0 Streamlit Browse remains the export surface. Re-add as a future requirement when v1.0 sunset is planned. v1.0's `app/components/export_dialog.py` is the reference implementation if/when this returns.
- **Sticky-left first-column** on the wide pivot grid — would help readability when horizontal scroll engages. Adds non-trivial CSS (`position: sticky` interactions with `table-responsive`). Defer until a user reports it as friction.
- **Faceted filtering by Brand/SoC/Year** (like Phase 2 Overview) on the Platforms picker — defer; raw PLATFORM_ID search is sufficient for ad-hoc browsing.
- **InfoCategory grouping in the Parameters picker** (collapsible groups vs flat list) — defer; flat alphabetical list is good enough for ~100+ items with client-side search.
- **Saved filter presets per user** — needs auth (still deferred per D-04). Defer.
- **Per-user filter persistence in cookie** — Phase 5 introduces LLM-backend cookie; Browse filter state could piggyback. Defer to v2.1.
- **Keyboard shortcuts** for popover navigation (arrow keys, Enter to toggle, Esc to close, Cmd/Ctrl+A to select all visible) — defer; mouse-and-search is the primary path.
- **"Select all matching search" button** inside the popover — when the search filter narrows to N items, a button to check all N at once. Useful for bulk operations. Defer until users ask.
- **Streaming long-form export (raw long DataFrame as ndjson)** — was a v1.0 power-user path; out of scope with all-of-export removed. Defer.
- **Visual chart preview in the picker** — reject (out of scope; we have no chart surface anyway).
- **Sort the grid by clicking column headers** — defer; v1.0 doesn't support it either, and the wide-form pivot doesn't have a natural sort semantics (the `Item` axis is unordered, the `PLATFORM_ID` axis is alphabetical).
- **Aggregated views** (e.g. "show only rows where any value differs across platforms") — defer; this is a different feature class.

</deferred>

---

## Required upstream edits BEFORE planning starts

These follow from the BROWSE-V2-04 scope-out (D-20, D-21). Planner should treat these as Plan 04-00 prerequisites OR call them out as a planning blocker:

1. `.planning/REQUIREMENTS.md` — Move BROWSE-V2-04 from "Browse Tab (Port)" Pending list to "Out of Scope" with reason: `"Excel/CSV export under v2.0 shell — v1.0 Streamlit Browse remains the export surface until v1.0 sunset; v2.0 Browse is view-only by design choice (2026-04-26)"`. Update the Traceability table to remove BROWSE-V2-04 → Phase 4 row and the totals (v2.0 Requirements: 46 → 45; Phase 4 mapped: 5 → 4).

2. `.planning/ROADMAP.md` — Phase 4 section: delete success criterion #3 (`"User can download the current pivot grid as Excel (.xlsx) or CSV..."`). Phase 4 success criteria become 3 items (filter swap + sticky header, caps mirror v1.0, URL round-trip). Update `**Requirements**: BROWSE-V2-01, BROWSE-V2-02, BROWSE-V2-03, BROWSE-V2-04, BROWSE-V2-05` → drop BROWSE-V2-04.

3. `.planning/PROJECT.md` — Under "Browse carry-over (v2.0)" Active section, the `[ ] Excel + CSV export` line moves to "Out of Scope" with reason. Add the rationale to "Key Decisions" table: `| Drop v2.0 Browse export to keep the port view-only | Simpler shell migration; v1.0 Streamlit Browse still serves the export workflow until v1.0 sunset | ⚠️ Revisit at v1.0 sunset planning |`.

---

*Phase: 04-browse-tab-port*
*Context gathered: 2026-04-26 via interactive smart discuss (4 grey areas; export feature scope-removed mid-discussion)*
*Amended 2026-04-28 via gap-4 discuss (D-15 close-policy contract change + D-15a close-event taxonomy added). Implementation in 04-07 surfaced a runtime bug (implicit-Apply not landing the grid swap) AND user-driven design pivot (remove Apply button entirely). D-14, D-15, D-15a all superseded by D-15b (auto-commit + 250ms debounce). gap-5 closes by overturning the contract; the 04-07 implementation is reverted via the gap-5 fix.*
