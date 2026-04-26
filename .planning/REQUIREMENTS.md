# Requirements: PBM2 v2.0 Bootstrap Shell

**Milestone version:** v2.0
**Scope:** Complete UI rewrite — move off Streamlit onto FastAPI + Bootstrap 5 + HTMX with a horizontal-tab shell, curated platform-entity overview, per-platform markdown content pages, in-place AI Summary, and full v1.0 Browse + Ask feature parity under the new shell.

**Parallel to v1.0:** v1.0 Streamlit code stays in place under `app/` and `streamlit_app.py`. v2.0 lives in `app_v2/` at repo root. Framework-agnostic v1.0 modules (`result_normalizer`, `sql_validator`, `sql_limiter`, `path_scrubber`, `build_pydantic_model`, config models) are REUSED by import.

**Auth still deferred** per v1.0's D-04 pattern — `config/auth.yaml` stays gitignored.

## v2.0 Requirements

### Infrastructure & Foundation

- [x] **INFRA-01**: App runs via `uvicorn app_v2.main:app --host 0.0.0.0 --port 8000` on the team intranet; returns HTML at `/`, `/browse`, `/ask`, `/platforms/<id>`. No auth gate in v2.0.
- [x] **INFRA-02**: `base.html` provides a Bootstrap 5 shell with horizontal top-nav tabs (Overview / Browse / Ask), global `htmx:beforeSwap` JavaScript handler that renders HTMX 4xx/5xx responses into a dedicated error container (not silently dropped), and Bootstrap-styled 404/500 pages.
- [x] **INFRA-03**: `app_v2/lifespan` (FastAPI `@asynccontextmanager`) initializes `app.state.db` (MySQLAdapter), `app.state.settings` (Pydantic Settings), and `app.state.agent_registry = {}` for lazy per-backend NL-agent caching.
- [x] **INFRA-04**: Bootstrap 5.3.8 + HTMX 2.0.10 + bootstrap-icons 1.13.1 are vendored into `app_v2/static/vendor/` (not CDN-dependent) so the app runs on intranet without outbound internet access. Base template references local paths.
- [x] **INFRA-05**: All DB-touching routes are `def` (synchronous), not `async def`, so FastAPI dispatches them to the threadpool and sync SQLAlchemy does not block the event loop.
- [x] **INFRA-06**: **Pre-work gate — ufs_service refactor.** `app/services/ufs_service.py` is refactored so `list_platforms`, `list_parameters`, `fetch_cells`, and `pivot_to_wide` each have a pure `_core()` variant callable WITHOUT Streamlit context. The existing `@st.cache_data` wrappers delegate to the `_core()` functions so v1.0 API stays unchanged. All 171 v1.0 tests must still pass after refactor.
- [x] **INFRA-07**: **Pre-work gate — nl_service extraction.** SAFE-02..06 harness (sqlparse validator, LIMIT injector, path scrubber, step-cap enforcement, `<db_data>` wrapper) currently lives in `app/pages/ask.py`. Extract into `app/core/agent/nl_service.py` with a single `run_nl_query(question, agent, deps) -> NLResult` entrypoint. v1.0 `ask.py` is refactored to call `nl_service` instead of inlining the harness. All v1.0 NL tests must still pass.
- [x] **INFRA-08**: `app_v2/services/cache.py` provides `cachetools.TTLCache` + `threading.Lock()` wrappers for all `_core()` functions exposed by the refactored `ufs_service`. Cache keys exclude unhashable objects (adapter) — use `db_name: str` only.
- [x] **INFRA-09**: Shared `requirements.txt` is extended with v2.0 deps (`fastapi>=0.136,<0.137`, `uvicorn[standard]>=0.32`, `jinja2>=3.1`, `jinja2-fragments>=1.3`, `python-multipart`, `markdown-it-py[plugins]>=3.0`, `cachetools>=7.0,<8.0`, `pydantic-settings>=2.14`). Existing Streamlit deps are retained.

### Overview Tab

- [x] **OVERVIEW-01**: User can open the Overview tab at `/` (default) or `/?tab=overview`. Tab state reflects in URL via `hx-push-url`.
- [x] **OVERVIEW-02**: Overview page renders a list of curated platform entities. Each entity row shows: title (PLATFORM_ID), Brand badge, SoC badge, Year badge (when known), link to the platform's content page, "AI Summary" button, Remove (×) button.
- [x] **OVERVIEW-03**: User can add a platform to the curated list via a typeahead input (datalist or lightweight combobox) populated from PLATFORM_IDs available in `ufs_data`. HTMX `hx-trigger="keyup changed delay:250ms"` debounce on search; `hx-post` to add.
- [x] **OVERVIEW-04**: User can remove a platform from the curated list via the Remove (×) button; HTMX `hx-delete` + `hx-swap="delete"` on the entity row. Confirmation via browser `confirm()` or `hx-confirm`.
- [x] **OVERVIEW-05**: Curated list persists to `config/overview.yaml` (gitignored; `config/overview.example.yaml` committed as a template with 0–3 sample entries).
- [x] **OVERVIEW-06**: Overview page shows an empty state when the curated list is empty — explicit "Add your first platform" affordance pointing at the typeahead input.

### Overview Filters

- [x] **FILTER-01**: Overview page shows faceted filter controls: Brand (select with unique values parsed from curated `PLATFORM_IDs`), SoC (select), Year (select populated from SoC→year lookup table; excludes entries where year is `None`), "Has content page" toggle (checkbox).
- [x] **FILTER-02**: Changing any filter triggers an HTMX swap of the entity list only (not full page). `hx-include="[data-filter]"` pattern to aggregate all filter inputs into a single request; `change` trigger for selects, `change` for checkbox.
- [x] **FILTER-03**: Active filter badge shows the count of currently-active filters. "Clear all" link resets all filters and triggers a fresh list swap.
- [x] **FILTER-04**: `PLATFORM_ID` parser splits on `_` with `maxsplit=2` to yield `(brand, model, soc_raw)`. A `SoC→year` lookup table (shipped in `app_v2/data/soc_year.py`) maps known SoCs to release years; unknown SoCs return `year=None` and display "Unknown" in the Year badge. Entities with `year=None` are excluded from the Year filter dropdown options (they still appear in results if no Year filter is active).

### Content Pages

- [x] **CONTENT-01**: Each curated platform has an optional markdown content page at `content/platforms/<PLATFORM_ID>.md`. The `content/` directory is gitignored; `content/platforms/.gitkeep` is committed.
- [x] **CONTENT-02**: `PLATFORM_ID` path parameter is validated with a strict regex (`^[A-Za-z0-9_\-]{1,128}$`) via FastAPI `Path(..., pattern=...)`. Before any filesystem I/O, `pathlib.Path.resolve()` asserts the resolved path is inside the `content/platforms/` directory (defense in depth against path traversal).
- [x] **CONTENT-03**: Navigating to `/platforms/<id>` renders the content page. If the file exists, markdown is rendered safely via `MarkdownIt("js-default")` (HTML passthrough disabled) with the view toolbar showing Edit and Delete buttons. If the file does not exist, an empty-state page shows "No content yet — Add some" with a single "Add Content" button that opens the Edit view.
- [x] **CONTENT-04**: Edit view replaces the rendered content area via HTMX `hx-swap="outerHTML"` with a `<textarea>` pre-filled with the raw markdown (empty if new), a Write/Preview tab nav above it, Save and Cancel buttons below.
- [x] **CONTENT-05**: The Preview tab in edit view fetches the rendered HTML via HTMX `hx-post` to a `/platforms/<id>/preview` endpoint with debounce (`keyup changed delay:500ms`). Preview uses the same safe `MarkdownIt("js-default")` pipeline. Preview never writes to disk.
- [x] **CONTENT-06**: Save commits the edit to disk atomically: write to a tempfile in the same directory as the target, `fsync`, then `os.replace` — guarantees atomic update on POSIX. Uses `def` route so FastAPI dispatches to threadpool. Successful save swaps the editor back to the rendered view.
- [x] **CONTENT-07**: Cancel is client-side (swap back from the stored view fragment); does not hit the server. No dirty-check prompt — autosave is explicitly NOT implemented (anti-feature for shared-credential intranet).
- [x] **CONTENT-08**: Delete requires confirmation (`hx-confirm="Delete content page for {PLATFORM_ID}?"`). On confirm, deletes the file and swaps the view to the empty state. Delete is reversible only via editing history (no undo button; files are recreated by Add).

### AI Summary

- [x] **SUMMARY-01**: Each Overview entity row has an "AI Summary" button. Button is disabled (greyed + tooltip "No content page to summarize yet") when the platform has no content file. Button is enabled when a file exists.
- [x] **SUMMARY-02**: Clicking AI Summary triggers `hx-post` to `/platforms/<id>/summary`. The response fills a dedicated `<div id="summary-{id}">` via `hx-swap="innerHTML"` — the entity row itself is never replaced. Button uses `hx-disabled-elt="this"` during the request to prevent double-submit.
- [x] **SUMMARY-03**: Loading indicator: Bootstrap `spinner-border` with `htmx-indicator` class inside the summary div, hidden by default, shown during the request via HTMX's `htmx-request` parent class CSS.
- [x] **SUMMARY-04**: Summary is generated by a single-shot call to the active LLM backend (Ollama default, OpenAI if selected). Uses v1.0's `openai` SDK with `base_url` and `api_key` from the active `LLMConfig`. Prompt template lives in `app_v2/data/summary_prompt.py`: "Summarize the following platform notes in 2–3 concise bullets focusing on notable characteristics, quirks, or decisions. Do not add information not present in the notes." Content is wrapped in `<notes>...</notes>` tags; system prompt instructs the model to treat tag contents as untrusted text.
- [x] **SUMMARY-05**: Summary session cache: `cachetools.TTLCache(maxsize=128, ttl=3600)` keyed by `(platform_id, content_mtime, llm_name, llm_model)`. Subsequent clicks on the same entity return cached result instantly unless the content file's `mtime` changed.
- [x] **SUMMARY-06**: Regenerate button appears next to the rendered summary. Clicking bypasses the cache (via `hx-headers={"X-Regenerate": "true"}`) and forces a fresh LLM call.
- [x] **SUMMARY-07**: Error state: if the LLM call fails (network, auth, timeout), the summary div shows a Bootstrap alert ("Summary unavailable: {reason}. Try again or switch LLM backend in Settings.") with a Retry button. No silent failure.

### Browse Tab (Port)

- [x] **BROWSE-V2-01**: Browse tab at `/browse` re-implements v1.0's pivot grid (platform × parameter) under Bootstrap + HTMX. Filter selectors (platform multiselect, parameter multiselect, swap-axes toggle) are HTMX-swapped on change — no full page reload.
- [x] **BROWSE-V2-02**: Pivot grid uses Bootstrap's `table table-striped table-hover` with `<thead class="sticky-top">` for frozen header row. Every cell rendered as text (mirrors v1.0's TextColumn-only approach because EAV Results are heterogeneous).
- [x] **BROWSE-V2-03**: Row-count and column-count indicators, 30-column cap warning, 200-row cap warning — all mirror v1.0's BROWSE-04, BROWSE-06 behavior with exact copy preserved.
- [x] **BROWSE-V2-05**: Filter state round-trips via URL query params so links are shareable (`/browse?platforms=...&params=...&swap=1`).

### Ask Tab (Port)

- [ ] **ASK-V2-01**: Ask tab at `/ask` (or `/?tab=ask`) exposes the v1.0 PydanticAI NL agent under the new shell. Question input is a Bootstrap `<textarea>` with a "Run" button; submits via HTMX `hx-post` to `/ask/query`.
- [ ] **ASK-V2-02**: NL-05 two-turn confirmation flow: when the agent returns `ClarificationNeeded`, the response renders a multiselect of candidate `(InfoCategory, Item)` params (pre-checked with all proposals) and a "Run Query" button. HTMX form carries the user-confirmed params as hidden field values; `hx-post` to a follow-up endpoint re-invokes the agent with the confirmed params as a structured second-turn user message.
- [ ] **ASK-V2-03**: Answer panel renders: result table (via `<table>` with same TextColumn-only rule), plain-text LLM summary (escaped, displayed in a `<div>`), collapsed SQL expander using Bootstrap `<details>` with the validated/limited SQL inside a `<code>` block. Regenerate button above the summary re-invokes the agent with the same question + confirmed params via HTMX.
- [ ] **ASK-V2-04**: Session history panel (`<details>` above the question input) lists recent questions with status badges. Max 50 entries (LRU). Clicking a history row refills the question input. Session-only (no disk persistence in v2.0 — stored in a signed cookie or in `app.state.history` keyed by session cookie).
- [ ] **ASK-V2-05**: LLM backend selector lives in the global sidebar (top-right of the Bootstrap nav, a `<select>` with Ollama/OpenAI options). Backend preference is stored in a signed cookie; defaults to Ollama. Switching to OpenAI shows a dismissible Bootstrap alert banner ("You're about to send UFS parameter data to OpenAI's servers. Switch to Ollama in the sidebar for local processing.") on the Ask page; dismissed state is session-cookie-scoped (re-shows on browser refresh).
- [ ] **ASK-V2-06**: All agent calls route through `app/core/agent/nl_service.run_nl_query()` (from INFRA-07). Safety harness (SAFE-02..06) is never bypassed — any v2.0 route that touches NL runs through `nl_service`.
- [ ] **ASK-V2-07**: SAFE-04 abort banner: if the agent exceeds step-cap or timeout, a red Bootstrap alert shows with the exact copy from v1.0 UI-SPEC, and partial output (if any) is rendered in a collapsed `<details>` expander.
- [ ] **ASK-V2-08**: 8 curated starter prompts render as a Bootstrap 4×2 grid on the Ask page when no question has been asked yet. Prompts load from `config/starter_prompts.yaml` (same file as v1.0). Clicking a prompt fills the textarea; does NOT auto-submit.

## Future Requirements (Deferred to later milestones)

- [ ] **INFRA-F01**: Authentication (streamlit-authenticator equivalent for FastAPI — e.g. `fastapi-users` with session cookie + bcrypt); reinstates the v1.0 D-04 deferral. Required before team-wide rollout.
- [ ] **OVERVIEW-F01**: URL round-trip for filter state (`?tab=overview&brand=Samsung&year=2024`).
- [ ] **OVERVIEW-F02**: Drag-to-reorder entities; per-user favorites (requires auth).
- [ ] **CONTENT-F01**: Syntax highlighting for code blocks in rendered markdown (Pygments or Prism.js).
- [ ] **CONTENT-F02**: Conflict detection for concurrent edits (auth + last-modified-by tracking).
- [ ] **SUMMARY-F01**: User-configurable summary prompt template (Settings page entry).
- [ ] **ASK-V2-F01**: Persistent NL history across sessions (current scope: session-only).

## Out of Scope

- **SPA frontend (React/Vue/Svelte)** — HTMX satisfies the interactivity needs; no-build-step model keeps operational simplicity.
- **litellm** — same reasoning as v1.0; `openai` SDK with `base_url` covers both backends natively.
- **Excel/CSV export under v2.0 shell** — v1.0 Streamlit Browse remains the export surface until v1.0 sunset; v2.0 Browse is view-only by design choice (2026-04-26). v1.0's app/components/export_dialog.py is the reference implementation if/when this returns.
- **WYSIWYG markdown editor (TipTap / ProseMirror)** — textarea with Preview tab is sufficient; WYSIWYG editors introduce significant complexity for marginal UX gain on an internal tool.
- **Autosave on content pages** — explicit anti-feature per research: shared-credential intranet has no conflict detection; autosave makes it trivial to silently overwrite a colleague's work.
- **Async SQLAlchemy migration** — existing sync engine works; `def` FastAPI routes dispatch to threadpool; migration is risk without benefit.
- **Per-user curated lists** — shared-credential model; one shared curated list stored in `config/overview.yaml`. Per-user lists wait on auth.
- **Deleting v1.0 Streamlit code** — v1.0 stays in place alongside v2.0. Rollback path preserved; deployment nginx can route to either.
- **Replacing Plotly with another chart library** — Plotly carries over with `fig.to_html(full_html=False, include_plotlyjs="cdn")` for HTMX injection if Browse tab's Chart surface is ported (Chart surface itself may be deferred; roadmapper decides).

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 1 | Complete |
| INFRA-05 | Phase 1 | Complete |
| INFRA-06 | Phase 1 | Complete |
| INFRA-07 | Phase 1 | Complete |
| INFRA-08 | Phase 1 | Complete |
| INFRA-09 | Phase 1 | Complete |
| OVERVIEW-01 | Phase 2 | Complete |
| OVERVIEW-02 | Phase 2 | Complete |
| OVERVIEW-03 | Phase 2 | Complete |
| OVERVIEW-04 | Phase 2 | Complete |
| OVERVIEW-05 | Phase 2 | Complete |
| OVERVIEW-06 | Phase 2 | Complete |
| FILTER-01 | Phase 2 | Complete |
| FILTER-02 | Phase 2 | Complete |
| FILTER-03 | Phase 2 | Complete |
| FILTER-04 | Phase 2 | Complete |
| CONTENT-01 | Phase 3 | Complete |
| CONTENT-02 | Phase 3 | Complete |
| CONTENT-03 | Phase 3 | Complete |
| CONTENT-04 | Phase 3 | Complete |
| CONTENT-05 | Phase 3 | Complete |
| CONTENT-06 | Phase 3 | Complete |
| CONTENT-07 | Phase 3 | Complete |
| CONTENT-08 | Phase 3 | Complete |
| SUMMARY-01 | Phase 3 | Complete |
| SUMMARY-02 | Phase 3 | Complete |
| SUMMARY-03 | Phase 3 | Complete |
| SUMMARY-04 | Phase 3 | Complete |
| SUMMARY-05 | Phase 3 | Complete |
| SUMMARY-06 | Phase 3 | Complete |
| SUMMARY-07 | Phase 3 | Complete |
| BROWSE-V2-01 | Phase 4 | Complete |
| BROWSE-V2-02 | Phase 4 | Complete |
| BROWSE-V2-03 | Phase 4 | Complete |
| BROWSE-V2-05 | Phase 4 | Complete |
| ASK-V2-01 | Phase 5 | Pending |
| ASK-V2-02 | Phase 5 | Pending |
| ASK-V2-03 | Phase 5 | Pending |
| ASK-V2-04 | Phase 5 | Pending |
| ASK-V2-05 | Phase 5 | Pending |
| ASK-V2-06 | Phase 5 | Pending |
| ASK-V2-07 | Phase 5 | Pending |
| ASK-V2-08 | Phase 5 | Pending |

**Totals:**
- v2.0 Requirements: **45** (9 INFRA + 6 OVERVIEW + 4 FILTER + 8 CONTENT + 7 SUMMARY + 4 BROWSE-V2 + 8 ASK-V2)
- Deferred: 7
- Mapped to phases: 45 / 45 (Phase 1: 9, Phase 2: 10, Phase 3: 15, Phase 4: 4, Phase 5: 8)
