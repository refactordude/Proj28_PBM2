# Requirements: PBM2

**Defined:** 2026-04-23
**Core Value:** Fast ad-hoc browsing of the parameter database. Even if the NL layer fails, the UI must let a non-SQL user quickly find the platforms they care about, the parameters they care about, and see them in a wide-form grid they can read, compare, chart, and export. NL rides on top.

## v1 Requirements

### Foundation

- [ ] **FOUND-01**: User signs in with shared team credentials via `streamlit-authenticator`; unauthenticated visitors see only the login page
- [x] **FOUND-02**: `config/auth.yaml` is excluded from git via `.gitignore`; only `config/auth.example.yaml` is tracked
- [ ] **FOUND-03**: App fails to start with a clear error message if the `streamlit-authenticator` cookie key is left at the demo value `change-this-secret-in-production`
- [x] **FOUND-04**: App loads DB and LLM configuration from `config/settings.yaml` (overridable via `SETTINGS_PATH`) and reads `OPENAI_API_KEY` from `.env` via `python-dotenv`
- [x] **FOUND-05**: App uses `st.navigation` + `st.Page` routing; page list is gated by authentication state
- [x] **FOUND-06**: The SQLAlchemy engine is a `@st.cache_resource` singleton with `pool_pre_ping=True` and `pool_recycle=3600`
- [x] **FOUND-07**: All DB query results are cached with `@st.cache_data(ttl=300)` keyed on immutable arguments (tuples, not lists)
- [x] **FOUND-08**: `requirements.txt` pins `sqlalchemy>=2.0,<2.1` and adds `pydantic-ai>=1.0,<2.0`

### Data Layer

- [x] **DATA-01**: The `result_normalizer` module maps `None`, empty string, `"None"`, `"null"`, `"N/A"`, and captured shell errors (`cat: …`, `Permission denied`, `No such file`) to a single `pd.NA` missing sentinel
- [x] **DATA-02**: The `result_normalizer` classifies any `Result` value into one of `{HEX, DECIMAL, CSV, WHITESPACE_BLOB, COMPOUND, IDENTIFIER, ERROR, MISSING}` without coercing the value — coercion happens lazily per-query
- [x] **DATA-03**: The `result_normalizer` can split LUN-prefixed `Item` values (`N_fieldname` for `N ∈ {0..7}`) into a LUN-index column and a field-name column on demand
- [x] **DATA-04**: The `result_normalizer` can split DME `_local`/`_peer` suffixes and unpack compound `local=...,peer=...` values on demand
- [x] **DATA-05**: `ufs_service` fetches rows with `WHERE PLATFORM_ID IN (...)` and/or `WHERE (InfoCategory, Item) IN (...)` applied server-side; the full `ufs_data` table is never loaded into pandas
- [x] **DATA-06**: `ufs_service.pivot_to_wide` produces a wide-form DataFrame with `aggfunc="first"` and logs a warning when duplicate `(PLATFORM_ID, InfoCategory, Item)` cells are detected
- [x] **DATA-07**: Every `ufs_service` query honors a 200-row cap (matching `AgentConfig.row_cap`) and surfaces the cap as a visible message when reached

### Browsing

- [x] **BROWSE-01**: User sees a list of all distinct `PLATFORM_ID` values and can multi-select platforms with type-ahead search
- [x] **BROWSE-02**: User sees `InfoCategory → Item` as a browsable hierarchy (sidebar or tree), with LUN-prefixed items grouped under their field name
- [x] **BROWSE-03**: User can search parameters by substring across both `InfoCategory` and `Item` via a type-ahead search bar
- [x] **BROWSE-04**: User sees a wide-form pivot grid (platforms × parameters), sortable by any column; the grid defaults to a single `InfoCategory` and caps displayed columns at ~30 with a visible warning when exceeded
- [x] **BROWSE-05**: User can open a single-platform detail view that lists `(InfoCategory, Item, Result)` rows grouped by `InfoCategory`
- [x] **BROWSE-06**: User sees a row-count indicator ("showing N of M platforms / K of L parameters") on every result view
- [x] **BROWSE-07**: User sees plain-English loading, empty, and error states for every query
- [x] **BROWSE-08**: User's filter selections persist across widget interactions via `st.session_state`
- [x] **BROWSE-09**: User can copy a shareable URL that reproduces the current filter state via `st.query_params`

### Visualization

- [x] **VIZ-01**: User can render a bar / line / scatter chart (Plotly) from any numeric column in the pivot grid or detail view
- [x] **VIZ-02**: Chart rendering uses lazy per-query numeric coercion and silently skips cells that are `pd.NA` or not coercible to a number

### Export

- [x] **EXPORT-01**: User can download the current pivot grid or detail view as an Excel (`.xlsx`) file via `openpyxl`
- [x] **EXPORT-02**: User can download the current pivot grid or detail view as a CSV file

### NL Agent

- [ ] **NL-01**: User types a natural-language question and receives both a result table and a plain-text LLM summary
- [ ] **NL-02**: User sees the LLM-generated SQL in a collapsed expander on every NL result
- [ ] **NL-03**: User can click **Regenerate** to re-run the same NL question with a fresh LLM call
- [ ] **NL-04**: User's NL questions and answers are preserved for the session in a history panel
- [ ] **NL-05**: Before running a query, the agent proposes candidate `(InfoCategory, Item)` parameters drawn from the actual DB and asks the user to confirm or adjust before SQL is executed
- [ ] **NL-06**: The agent correctly handles the three core question shapes: lookup-one-platform, compare-across-platforms, filter-platforms-by-value
- [x] **NL-07**: User can switch the LLM backend between OpenAI and Ollama from the sidebar; the choice takes effect on the next NL query
- [x] **NL-08**: Both OpenAI and Ollama backends use the same `openai` Python SDK client, differing only in `base_url` and `api_key`
- [x] **NL-09**: Ollama backend has a JSON extraction fallback (`json.loads` → regex first-JSON-block → plain text) so smaller models that emit imperfect tool-call JSON do not crash the agent
- [ ] **NL-10**: Default LLM backend is Ollama; selecting OpenAI displays a one-time data-sensitivity warning before the first request of the session

### Safety

- [x] **SAFE-01**: DB connection uses a read-only MySQL user; every session attempts `SET SESSION TRANSACTION READ ONLY` (non-fatal if unsupported)
- [x] **SAFE-02**: Agent-generated SQL is validated with `sqlparse` — only a single `SELECT` statement referencing a table in `allowed_tables` is executed; INSERT / UPDATE / DELETE / DROP / CALL / multi-statement queries are rejected
- [x] **SAFE-03**: Agent-generated SQL has a `LIMIT` injected if one is missing (cap = `AgentConfig.row_cap`)
- [ ] **SAFE-04**: Agent loop enforces `max_steps=5` as a hard step counter and `timeout_s=30` as a wall-clock timeout; exceeding either aborts cleanly with a user-visible message
- [ ] **SAFE-05**: DB rows passed into the LLM context are wrapped in `<db_data>...</db_data>` delimiters with an explicit system-prompt instruction that content inside the tag is raw data, never instructions
- [x] **SAFE-06**: `Result` values containing filesystem paths (`/sys/`, `/proc/`, `/dev/`) are scrubbed to a placeholder before being sent to any cloud LLM

### Settings

- [x] **SETUP-01**: Admin can create, read, update, and delete database connection entries from the Settings page; entries are persisted to `config/settings.yaml`
- [x] **SETUP-02**: Admin can create, read, update, and delete LLM connection entries from the Settings page; entries are persisted to `config/settings.yaml`
- [x] **SETUP-03**: Admin can test a database or LLM connection from the Settings page and see a pass/fail indicator

### Onboarding

- [ ] **ONBD-01**: User sees a gallery of 6–10 curated starter prompts (backed by a YAML file) on the NL page; clicking a prompt fills the question input
- [ ] **ONBD-02**: The starter-prompt YAML is editable by anyone with filesystem access — adding or removing a prompt requires no code change

## v2 Requirements

Deferred to a future release. Tracked but not in the current roadmap.

### Visualization

- **VIZ-V2-01**: Heatmap / conditional formatting for numeric parameters across the pivot grid

### NL Agent

- **NL-V2-01**: Editable generated SQL as a power-user escape hatch (hidden in an expander, secondary to NL input)
- **NL-V2-02**: "Why this query?" explanation panel that walks through how the LLM interpreted the question

### Browsing

- **BROWSE-V2-01**: LUN sub-header grouping in the pivot grid (`N_fieldname` items shown as "field [0–7]")
- **BROWSE-V2-02**: DME `_local` / `_peer` split display as paired columns

### v2+ (deferred, trigger-based)

- Platform comparison presets — trigger: users repeatedly re-selecting the same cohort
- Saved parameter sets — trigger: users describing "my regular view"
- Cross-session query history — requires server-side persistence
- "Similar platforms" suggestion — requires similarity computation over the pivot matrix
- Confidence / quality indicator for NL results — requires reliable LLM self-evaluation

## Out of Scope

| Feature | Reason |
|---------|--------|
| Admin data ingestion / Excel upload / DB write path | Someone else maintains `ufs_data`; v1 is strictly a read client |
| Per-user SSO (Google / Okta / AD) | Intranet + shared-credential auth is the explicit v1 choice |
| Public-internet deployment / auth hardening | Intranet-only; strong auth is not a v1 requirement |
| Multi-table / cross-table joins | The entire domain is the single-table EAV `ufs_data` |
| Editing / correcting platform data from the UI | DB is read-only by contract; corrections belong upstream |
| Training / fine-tuning an in-house LLM | v1 relies on OpenAI + Ollama adapters already scaffolded |
| Free-form SQL editor as a first-class feature | Reintroduces the SQL barrier the app exists to remove (editable SQL is allowed only as a hidden v2 expander) |
| Global `Result` type coercion on load | Same `Item` is legitimately hex on one platform and decimal on another — global coercion destroys information |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Pending |
| FOUND-02 | Phase 1 | Complete |
| FOUND-03 | Phase 1 | Pending |
| FOUND-04 | Phase 1 | Complete |
| FOUND-05 | Phase 1 | Complete |
| FOUND-06 | Phase 1 | Complete |
| FOUND-07 | Phase 1 | Complete |
| FOUND-08 | Phase 1 | Complete |
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DATA-03 | Phase 1 | Complete |
| DATA-04 | Phase 1 | Complete |
| DATA-05 | Phase 1 | Complete |
| DATA-06 | Phase 1 | Complete |
| DATA-07 | Phase 1 | Complete |
| BROWSE-01 | Phase 1 | Complete |
| BROWSE-02 | Phase 1 | Complete |
| BROWSE-03 | Phase 1 | Complete |
| BROWSE-04 | Phase 1 | Complete |
| BROWSE-05 | Phase 1 | Complete |
| BROWSE-06 | Phase 1 | Complete |
| BROWSE-07 | Phase 1 | Complete |
| BROWSE-08 | Phase 1 | Complete |
| BROWSE-09 | Phase 1 | Complete |
| VIZ-01 | Phase 1 | Complete |
| VIZ-02 | Phase 1 | Complete |
| EXPORT-01 | Phase 1 | Complete |
| EXPORT-02 | Phase 1 | Complete |
| NL-01 | Phase 2 | Pending |
| NL-02 | Phase 2 | Pending |
| NL-03 | Phase 2 | Pending |
| NL-04 | Phase 2 | Pending |
| NL-05 | Phase 2 | Pending |
| NL-06 | Phase 2 | Pending |
| NL-07 | Phase 2 | Complete |
| NL-08 | Phase 2 | Complete |
| NL-09 | Phase 2 | Complete |
| NL-10 | Phase 2 | Pending |
| SAFE-01 | Phase 1 | Complete |
| SAFE-02 | Phase 2 | Complete |
| SAFE-03 | Phase 2 | Complete |
| SAFE-04 | Phase 2 | Pending |
| SAFE-05 | Phase 2 | Pending |
| SAFE-06 | Phase 2 | Complete |
| SETUP-01 | Phase 1 | Complete |
| SETUP-02 | Phase 1 | Complete |
| SETUP-03 | Phase 1 | Complete |
| ONBD-01 | Phase 2 | Pending |
| ONBD-02 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 49 total (note: traceability table contains 49 rows; original count of 48 was a pre-fill estimate)
- Phase 1: 32 requirements (FOUND-01..08, DATA-01..07, BROWSE-01..09, VIZ-01..02, EXPORT-01..02, SETUP-01..03, SAFE-01)
- Phase 2: 17 requirements (NL-01..10, SAFE-02..06, ONBD-01..02)
- Mapped to phases: 49 / 49
- Unmapped: 0

---
*Requirements defined: 2026-04-23*
*Last updated: 2026-04-23 after roadmap creation — traceability filled in*
