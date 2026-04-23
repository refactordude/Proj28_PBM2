# Phase 1: Foundation + Browsing - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

A deployable read-only data browser. Users reach the app on the intranet URL, pick platforms and parameters, and view a wide-form pivot grid (with a toggleable axis), a single-platform detail view grouped by InfoCategory, and a numeric chart. They can export what they see as Excel or CSV, and an admin-style Settings page lets them configure DB and LLM connections with a live Test button. The DB is strictly read-only. The NL agent is **not** part of this phase; the LLM selector in the sidebar is wired to `st.session_state` but is inert until Phase 2.

Auth (streamlit-authenticator) is deferred out of this phase at the user's explicit request. The app runs open inside the intranet for Phase 1.

</domain>

<decisions>
## Implementation Decisions

### Navigation & Page Structure
- **D-01:** Phase 1 ships two `st.Page` surfaces: **Browse** (default landing) and **Settings**. No separate Home, Detail, or History page.
- **D-02:** The single-platform detail view lives as a **second tab** inside Browse, next to the Pivot tab. A third **Chart** tab is added (see D-13). Tabs share filter state.
- **D-03:** Every Phase 1 page shows a sidebar containing: **DB selector** (only visible if >1 DB is configured; otherwise shows the active DB name as read-only text), **LLM selector** (visible but inert — writes to `st.session_state['active_llm']`; nothing consumes it in Phase 1), **connection health indicator** next to the active DB. No data-freshness indicator — `ufs_data` has no ingestion timestamp column we can rely on, and the user accepts dropping this bullet.
- **D-04:** **Auth is skipped entirely in Phase 1.** FOUND-01 (login page), FOUND-02 (auth.yaml gitignore), and FOUND-03 (cookie-key startup guard) are deferred to a pre-deployment phase. `streamlit-authenticator` is not imported anywhere in Phase 1 code paths. **Exception:** `config/auth.yaml` remains gitignored in `.gitignore` regardless, so the scaffold doesn't accidentally ship demo creds when auth is turned on later. The LLM selector shows no data-sensitivity warning (that's a Phase 2 concern).

### Browse Page Layout
- **D-05:** Platform picker and parameter catalog both live in the **left sidebar**, below the DB/LLM selectors. Main panel is reserved for the Pivot / Detail / Chart tabs. Sidebar order: DB selector → LLM selector → divider → Platform multi-select → Parameter catalog → "Clear filters" button.
- **D-06:** The parameter catalog is rendered as a **single searchable two-level multiselect** (`st.multiselect`) where each option's label is formatted as `"InfoCategory / Item"`. Options are sorted by (InfoCategory ASC, Item ASC). Typeahead matches against the concatenated label — one widget, no expanders, no nested checkboxes.
- **D-07:** Pivot grid default orientation = **parameters as columns, platforms as rows** (`PLATFORM_ID` is the DataFrame index, which Streamlit renders frozen). A **"Swap axes" toggle** above the grid re-pivots to platforms-as-columns on demand. The 30-column cap (BROWSE-04) applies to whichever axis is currently the column axis.
- **D-08:** **LUN items are listed flat** in the catalog — `lun_info / 0_WriteProt`, `lun_info / 1_WriteProt`, ..., `lun_info / 7_WriteProt` appear as eight separate entries. No grouping, no "select all LUNs" roll-up, no per-LUN expander. BROWSE-02's phrase *"LUN-prefixed items grouped under their field name"* is deliberately narrowed: grouping is not required for Phase 1; flat is acceptable.

### Settings Page UX
- **D-09:** The Settings page is **fully editable by anyone who reaches the URL**. No role gate, no config flag, no passphrase. Consistent with the no-auth Phase 1 decision. Role/permission gating comes back with auth in a later phase.
- **D-10:** Each DB and LLM entry has its own **per-row "Test" button**. Test runs **synchronously** with `st.spinner`. Result is shown as an inline **pass/fail badge** (✅ / ❌) next to the Test button; failure reason is a tooltip or small expander below the badge. No auto-test on save.
- **D-11:** **Passwords and api_keys are stored plaintext in `config/settings.yaml`** (gitignored). In the Settings UI they are rendered as masked `st.text_input(type="password")` fields. This matches the existing `settings.example.yaml` scaffolding. No env-var references, no separate secrets file.
- **D-12:** On Save, the Settings page writes `settings.yaml` via `save_settings()` and then calls **`st.cache_resource.clear()` + `st.cache_data.clear()`**. A "Saved. Caches refreshed." toast appears. The next Browse interaction rebuilds the engine against the new config. No manual "Reload" button; no app restart required.

### Chart + Export
- **D-13:** Chart rendering lives as a **third tab** (Pivot / Detail / Chart) inside Browse. The Chart tab reads from the same filter state as Pivot.
- **D-14:** On the Chart tab, the user **explicitly picks** (a) the column to chart from a selectbox populated only with numeric-coercible columns, and (b) the chart type (bar / line / scatter radio). VIZ-02 is satisfied by filtering `pd.NA` and non-coercible cells out of the selected column before handing to Plotly. No auto-render, no small-multiples.
- **D-15:** Export captures the **currently-visible view** — post-sort, post-hide, post-axis-swap wide-form pivot from the Pivot tab; long-form `(InfoCategory, Item, Result)` rows from the Detail tab (only the selected platform). Charts are not exported (screenshot is user's responsibility).
- **D-16:** A **single "Export" button** above each tab opens an `st.dialog` with: **format selector** (xlsx / csv), **filename field** (default `pbm2_<tab>_<ISO-timestamp>`), and — only on the Pivot tab — a "Scope" radio with "Current view" (default, matches D-15) / "Raw long-form rows" (pre-pivot DataFrame for power users who want to re-analyze). Dialog "Download" button triggers the actual `st.download_button` flow.

### Folded Todos
None — no pending todos matched this phase.

### Claude's Discretion
- Exact color/typography of the pass/fail badge, loading spinner, empty-state illustrations.
- Debounce/throttle on typeahead in the parameter catalog multiselect.
- Error-message wording for BROWSE-07 empty/loading/error states.
- Filename sanitization rules for the export dialog.
- Precise layout of the Settings page form (single column vs two-column).
- How `AgentConfig` fields are surfaced in Settings — readonly display is enough for Phase 1, since the agent isn't running yet.
- Whether to seed `config/settings.yaml` from `settings.example.yaml` on first launch if it doesn't exist.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project vision & constraints
- `.planning/PROJECT.md` — Core Value (browsing-first), Constraints (tech stack, scale, security), Context (Result field heterogeneity, LUN/DME naming, PLATFORM_ID convention), Key Decisions (dual LLM backends, readonly DB, lazy per-query coercion)
- `.planning/ROADMAP.md` §Phase 1 — Phase goal, Requirements list, Success Criteria (the 5 things that must be TRUE)
- `CLAUDE.md` — Project summary, locked tech stack with verified versions (Streamlit 1.56.0, SQLAlchemy 2.0.49, pandas 3.0.2, PydanticAI 1.86.0, streamlit-authenticator 0.4.2), alternatives considered and rejected

### Phase 1 requirements (authoritative — every checkbox must be addressable by plans)
- `.planning/REQUIREMENTS.md` §Foundation — FOUND-01..08 (**note: FOUND-01/02/03 deferred per D-04**; FOUND-04..08 still in scope)
- `.planning/REQUIREMENTS.md` §Data Layer — DATA-01..07 (result_normalizer + ufs_service behavior, row-cap, duplicate handling)
- `.planning/REQUIREMENTS.md` §Browsing — BROWSE-01..09 (platform list, InfoCategory hierarchy, search, pivot grid, detail view, row counts, empty/loading states, sticky filters, shareable URL)
- `.planning/REQUIREMENTS.md` §Visualization — VIZ-01..02 (Plotly numeric charts, lazy numeric coercion)
- `.planning/REQUIREMENTS.md` §Export — EXPORT-01..02 (Excel via openpyxl, CSV)
- `.planning/REQUIREMENTS.md` §Settings — SETUP-01..03 (DB CRUD, LLM CRUD, Test connection)
- `.planning/REQUIREMENTS.md` §Safety — SAFE-01 (readonly MySQL user, `SET SESSION TRANSACTION READ ONLY` attempt)

### Architecture & stack research (implementation patterns)
- `.planning/research/SUMMARY.md` — Executive summary, recommended stack, MVP definition, phase implications
- `.planning/research/ARCHITECTURE.md` — Four-layer architecture (UI → Service → Adapter → External), component responsibilities, `st.cache_resource` engine singleton pattern, `st.cache_data(ttl=300)` query pattern, 5-stage normalization pipeline, error surfacing strategy, anti-patterns 1–4
- `.planning/research/STACK.md` — Version pins, installation guidance, scaffolding assessment
- `.planning/research/FEATURES.md` — EAV pivot UX patterns ("What Works / What Fails"), feature prioritization matrix, anti-features
- `.planning/research/PITFALLS.md` — Phase 1 blockers: memory blow-up (pre-filter before pivot), global type coercion, EAV duplicate rows, wide-pivot unusability at 100+ cols, Streamlit full-script rerun cost

### Existing scaffolding (code the plan must integrate with, not rewrite)
- `app/core/config.py` — `Settings`, `DatabaseConfig`, `LLMConfig`, `AppConfig`, `load_settings()`, `save_settings()`, `find_database()`, `find_llm()`
- `app/core/agent/config.py` — `AgentConfig` (imported but unused in Phase 1 UI; Settings page may display it read-only)
- `config/settings.example.yaml` — Canonical shape of `settings.yaml` (databases, llms, app defaults, agent defaults)
- `config/auth.yaml` — streamlit-authenticator credentials file (scaffolded; must stay gitignored even though Phase 1 doesn't import authenticator)
- `requirements.txt` — Dependency pins; note STACK.md recommends tightening `sqlalchemy>=2.0` → `sqlalchemy>=2.0,<2.1` and `pandas>=2.2` → `pandas>=3.0` (verify with planner)
- `.env.example` — `OPENAI_API_KEY`, `SETTINGS_PATH`, `AUTH_PATH`, `LOG_DIR`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`app/core/config.py`** — Fully usable as-is for Phase 1. Settings page builds forms against `DatabaseConfig` and `LLMConfig` Pydantic models; persistence via existing `save_settings()`. No schema changes needed.
- **`app/adapters/db/` + `app/adapters/llm/`** — Skeleton packages exist (empty `__init__.py`). Planner should flesh these out with `MySQLAdapter` (SQLAlchemy engine wrapper with `pool_pre_ping=True`, `pool_recycle=3600`, `SET SESSION TRANSACTION READ ONLY` attempt for SAFE-01) and stub `OpenAIAdapter`/`OllamaAdapter` classes (method signatures only — implementations are Phase 2).
- **`config/settings.example.yaml`** — First-run seed for `config/settings.yaml`. Decide: copy-on-first-launch, or require admin to fill in via Settings UI on empty state.

### Established Patterns
- **Pydantic v2 everywhere** — Settings, per-connection configs, AgentConfig all use `BaseModel` + `Field(default_factory=...)`. New service-layer types should follow the same pattern.
- **YAML round-trip via `yaml.safe_load` / `yaml.safe_dump`** — `load_settings` / `save_settings` already handle this. `allow_unicode=True, sort_keys=False` is the house style.
- **Korean comments in docstrings** — `config.py` uses Korean for module-level docstrings. New code may follow this convention or use English; the planner should preserve existing Korean comments when editing, not rewrite them.
- **Path resolution via `Path(__file__).resolve().parents[2]`** — The repo-root anchor pattern used in `config.py` for locating `config/settings.yaml`. Reuse for any other config/data file lookups.

### Integration Points
- **`streamlit_app.py` (new, at repo root)** — Entrypoint. Imports `load_settings()`, builds `st.navigation` with two pages, renders the shared sidebar widgets (DB/LLM/health), routes to Browse or Settings.
- **`app/pages/browse.py` (new)** — Calls `app/services/ufs_service.fetch_cells()`, `list_platforms()`, `list_parameters()`; renders Pivot/Detail/Chart tabs; owns the Export dialog.
- **`app/pages/settings.py` (new)** — Calls `load_settings()` on entry, writes via `save_settings()`, calls `test_connection()` per row; clears caches on save.
- **`app/services/ufs_service.py` (new)** — Thin domain service. Wraps the DB adapter, builds parameterized SQL, applies `result_normalizer`, pivots with `aggfunc="first"` and duplicate warning (DATA-06).
- **`app/services/result_normalizer.py` (new)** — The 5-stage pipeline (missing sentinel → error strings → LUN split → DME split → lazy numeric coercion). Must have a stable API and unit tests **before** `ufs_service.py` is written (critical dependency flagged in ARCHITECTURE.md).

</code_context>

<specifics>
## Specific Ideas

- **"Full sidebar with selectors + freshness"** — The user picked the fully-wired sidebar even though three of its pieces (LLM selector, data-freshness, logout) are inert or dropped in Phase 1. Rationale captured: Phase 1 pre-wires the shape so Phase 2 only has to add behavior, not layout.
- **Axis swap toggle** — User actively chose the "defer" option as an ACTIVE Phase 1 feature. The plan must include a "Swap axes" toggle above the pivot grid in Phase 1, not Phase 1.x. Implementation is cheap (`df.T`) but must be tested against the 30-column cap in both orientations.
- **Single Export dialog** — The user preferred the single-button dialog over two-button download widgets. This is a slightly heavier UI (requires `st.dialog`) but lets us consolidate format/filename/scope choices and add the "Raw long-form rows" escape hatch without cluttering the main view.
- **No freshness indicator** — Not because it's unimportant, but because there's no schema support yet. Revisit when upstream adds an ingestion timestamp column.

</specifics>

<deferred>
## Deferred Ideas

- **Authentication (FOUND-01, FOUND-03)** — User explicitly deferred auth for Phase 1. Track as a "pre-deployment" work item: before the app is shared beyond a single developer, re-enable streamlit-authenticator, rotate the demo cookie key, rotate the demo `admin/admin1234` credentials, add the FOUND-03 startup assertion. Note: FOUND-02 (gitignore) is **not** deferred — `config/auth.yaml` must be in `.gitignore` from Phase 1 onward so the scaffold doesn't leak demo creds when auth is enabled later.
- **Data-freshness indicator in sidebar** — Blocked on upstream adding an `updated_at` / `ingested_at` column (or a sidecar `last_sync` file). Add when source timestamp is available.
- **LUN sub-header grouping in pivot** — User chose flat for Phase 1. The BROWSE-V2-01 roadmap item (LUN `N_fieldname` displayed as collapsible sub-header in the pivot) stays v2. Same for BROWSE-V2-02 (DME `_local` / `_peer` split display).
- **LLM-related behavior** — No NL query, no data-sensitivity warning, no SQL expander, no regenerate, no session history, no starter-prompt gallery, no agent safety visible notice. All of this is Phase 2 (NL-01..10, SAFE-02..06, ONBD-01..02).
- **Heatmap / conditional formatting** — v1.x trigger-based feature. Not in Phase 1.
- **Editable generated SQL** — v1.x, hidden expander on NL page. Not in Phase 1.
- **History page** — Phase 2+ (session history belongs with NL).
- **Platform comparison presets, saved parameter sets, cross-session history, similar-platforms suggestion, confidence indicator** — All v2+; out of scope for Phase 1 and Phase 2.

### Reviewed Todos (not folded)
None — todo matcher returned zero matches for Phase 1.

</deferred>

---

*Phase: 01-foundation-browsing*
*Context gathered: 2026-04-23*
