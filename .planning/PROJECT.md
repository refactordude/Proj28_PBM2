# PBM2

## What This Is

PBM2 is an internal FastAPI + Bootstrap 5 + HTMX website where a team of non-SQL users (PMs, analysts) can browse and query a large, EAV-form MySQL parameter database (`ufs_data`) that stores UFS subsystem profiles of Android platforms. The app lets users slice, pivot, filter, visualize, and export this long-form data — and ask natural-language questions on top — without ever writing SQL or reasoning about the schema themselves.

## Core Value

**Fast ad-hoc browsing of the parameter database.** Even if the NL layer fails, the UI must let a non-SQL user quickly find the platforms they care about, the parameters they care about, and see them in a wide-form grid they can read, compare, chart, and export. NL query rides on top of this and enhances it — it does not replace it.

## Current Milestone: TBD

No formal milestone scoped yet. Phase 1 (Joint Validation auto-discovery, 2026-04-30) shipped as a post-v2.0 phase against the standalone D-JV-01..D-JV-17 requirement set locked in `phases/01-.../01-CONTEXT.md`. Run `/gsd-new-milestone` to formalize v2.1+ when more work is queued.

## Previous State

**v2.0 Bootstrap Shell shipped 2026-04-29** (tag `v2.0`). 6 phases, 30 plans, 65 tasks, 506 tests passing. Complete UX rewrite from Streamlit to FastAPI + Bootstrap 5 + HTMX with horizontal-tab shell:
- **Phase 1 (Foundation):** FastAPI/Bootstrap/HTMX scaffolding; `nl_service` extraction (INFRA-07); `cache.py` TTLCache wrappers; vendored static assets
- **Phase 2 (Overview + Filters):** Curated platform watchlist with HTMX-swapped Brand/SoC/Year filters
- **Phase 3 (Content + AI Summary):** Per-platform markdown CRUD with path-traversal hardening + XSS defense; AI Summary feature with TTLCache + always-200 contract
- **Phase 4 (Browse Tab Port):** Pivot grid ported to Bootstrap; popover-search.js; `HX-Push-Url` URL round-trip
- **Phase 5 (Overview Redesign):** Sortable Bootstrap table + 6 popover-checklist multi-filters; AI Summary modal (D-OV-15); Link button (D-OV-16)
- **Phase 6 (Ask Tab Port):** NL agent ported under FastAPI/HTMX; NL-05 two-turn confirmation; Ask-page-only LLM dropdown with `pbm2_llm` cookie threading; v1.0 Streamlit Ask deleted (D-22)

Full archive: [milestones/v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md), [milestones/v2.0-REQUIREMENTS.md](milestones/v2.0-REQUIREMENTS.md), [milestones/v2.0-MILESTONE-AUDIT.md](milestones/v2.0-MILESTONE-AUDIT.md), [milestones/v2.0-DECISIONS-LOG.md](milestones/v2.0-DECISIONS-LOG.md).

**v1.0 MVP shipped 2026-04-24.** Both planned phases delivered in a single autonomous run (`/gsd-autonomous`):

- **Phase 1 (Foundation + Browsing):** Streamlit app with navigation (Browse + Settings), DB/LLM connection CRUD in Settings, full Browse page with Pivot/Detail/Chart tabs, sidebar filters, shareable URL round-trip, Excel/CSV export. MySQLAdapter with correct pooling and read-only enforcement. EAV Result normalization pipeline (65 tests).
- **Phase 2 (NL Agent Layer):** Ask page with PydanticAI-backed natural-language-to-SQL agent, safety harness (sqlparse SELECT-only validator with UNION/CTE guards, LIMIT injector, path scrubber, `<db_data>` prompt-injection wrapper, step-cap, timeout), dual OpenAI/Ollama backends via `openai` SDK with different `base_url`, NL-05 two-turn parameter confirmation flow, OpenAI data-sensitivity warning, 8-prompt starter gallery.
- **Stats:** 3080 LOC app/ + 1711 LOC tests/, 171 passing pytest cases, 87 commits across 2 days.
- **Known deferrals:** FOUND-01 (login) and FOUND-03 (cookie-key startup guard) deferred to a pre-deployment phase per locked decision D-04. `config/auth.yaml` remains gitignored so demo credentials cannot leak when auth is enabled later.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

#### Browsing & Discovery — v1.0
- ✓ Browsable parameter catalog (InfoCategory / Item multiselect with typeahead) — v1.0
- ✓ Type-ahead search over `InfoCategory / Item` combined labels — v1.0
- ✓ Platform picker (multi-select over `PLATFORM_ID`) — v1.0
- ✓ Parameter picker (multi-select, sorted InfoCategory ASC then Item ASC) — v1.0
- ✓ Starter-prompt gallery (8 curated UFS prompts; editable via YAML) — v1.0

#### Data Display — v1.0
- ✓ Wide-form pivot grid with `aggfunc="first"`, swap-axes toggle, 30-column cap — v1.0
- ✓ Long-form Detail tab for single-platform deep dive, sorted — v1.0
- ✓ Result normalization pipeline (missing sentinels, shell errors, LUN split, DME split, lazy numeric coercion) — v1.0
- ✓ Plotly charts for numeric parameters (bar / line / scatter) with per-column numeric detection — v1.0
- ✓ Excel (openpyxl) and CSV (single utf-8-sig BOM) export via unified dialog — v1.0

#### Natural-Language Layer — v1.0
- ✓ NL question input handling all 3 core shapes (lookup / compare / filter) — v1.0
- ✓ Agent proposes candidate `(InfoCategory, Item)` params from the real DB before executing SQL (NL-05 two-turn flow) — v1.0
- ✓ Plain-text LLM-synthesized summary alongside result table — v1.0
- ✓ Sidebar radio switches OpenAI ↔ Ollama at runtime (default Ollama per D-25) — v1.0
- ✓ Safety harness: readonly DB user, `allowed_tables=["ufs_data"]`, sqlparse validator, LIMIT injection, step-cap, wall-clock timeout via MySQL `max_execution_time`, path scrub for OpenAI, `<db_data>` prompt-injection wrapper — v1.0

#### Platform — v1.0
- ✓ Settings UI for DB and LLM connection CRUD with per-row Test button — v1.0
- ⏳ Streamlit intranet deployment — v1.0 scaffolding complete (auth deferred to pre-deployment phase per D-04; `streamlit-authenticator` and cookie-key guard still to be enabled before team-wide rollout)

#### Browse — v2.0
- ✓ Wide-form pivot grid (platform × parameter) re-rendered in Bootstrap tables — v2.0 (Phase 4)
- ✓ Same filter / swap-axes / row-cap / col-cap behavior as v1.0; HTMX in-place swap, sticky header, shareable URLs (HX-Push-Url round-trip); Apply form-association + picker badge OOB-swap restored after gap closure (Plans 04-05, 04-06) — v2.0 (Phase 4). Export remains on v1.0 Streamlit per D-19..D-22.

#### Ask — v2.0
- ✓ Ask tab at `/ask` ports the v1.0 PydanticAI NL agent under the FastAPI/HTMX shell with sync `def` routes (GET /ask, POST /ask/query, POST /ask/confirm); module-level `run_nl_query` import for pytest-mock; all 3 fragments (`_answer.html`, `_confirm_panel.html`, `_abort_banner.html`) carry `id="answer-zone"` for idempotent HTMX outerHTML swaps — v2.0 (Phase 6)
- ✓ NL-05 two-turn confirmation flow reuses `_picker_popover.html` with `disable_auto_commit=True` so the Run Query button is the only commit trigger; second-turn `ClarificationNeeded` synthesizes a `loop-aborted` abort banner per D-10 — v2.0 (Phase 6)
- ✓ Ask-page-only LLM dropdown (Bootstrap; "LLM: Ollama ▾" / "LLM: OpenAI ▾"); `pbm2_llm` plain unsigned cookie validated against `settings.llms[].name` (closed-set defense, no signing); 204 + `HX-Refresh: true` → window.reload; cookie threading through `llm_resolver` makes Ask + AI Summary share a single backend choice (D-12, D-14, D-15, D-16, D-17, D-18 — global navbar selector and OpenAI sensitivity banner explicitly dropped) — v2.0 (Phase 6)
- ✓ 8 curated starter chips (4×2 `.ai-chip` grid); chips fill textarea via inline onclick without auto-submit; chips hide once an answer renders (D-02, D-03) — v2.0 (Phase 6)
- ✓ Abort banner with five reason branches (step-cap, timeout, llm-error, unconfigured, loop-aborted); copy ported verbatim from v1.0 02-UI-SPEC.md — v2.0 (Phase 6)
- ✓ All NL invocations route through `app/core/agent/nl_service.run_nl_query` (Phase 1 INFRA-07); SAFE-02..06 inherited; route-layer threat-model regression tests intentionally NOT added (D-20 — Phase 1's `tests/agent/test_nl_service.py` is the single locus) — v2.0 (Phase 6)
- ✓ v1.0 Streamlit Ask page deleted per D-22: `app/pages/ask.py`, `tests/pages/test_ask_page.py`, `tests/pages/test_starter_prompts.py`, and the `st.Page("Ask",...)` nav entry removed; `nl_service.py` / `nl_agent.py` / `pydantic_model.py` / `starter_prompts.example.yaml` preserved as v2.0 consumers — v2.0 (Phase 6)

#### Overview redesign — v2.0
- ✓ Sortable Bootstrap pivot table mirroring Phase 4 Browse styling; per-platform PM metadata (Title, Status, Customer, Model Name, AP Company, AP Model, Device, Controller, Application, 담당자, Start, End) sourced from YAML frontmatter on `content/platforms/<PLATFORM_ID>.md` — em-dash sentinel for missing fields; Title falls back to PLATFORM_ID — v2.0 (Phase 5)
- ✓ Six popover-checklist multi-filters (Status / Customer / AP Company / Device / Controller / Application) reusing Phase 4's `_picker_popover.html` macro with D-15b auto-commit + 250ms debounce; sort state survives URL round-trip — v2.0 (Phase 5)
- ✓ Actions column unifies View + AI ✨ buttons with identical Bootstrap shape; AI Summary surface evolved during UAT to a global Bootstrap modal popup (D-OV-15 supersedes D-OV-10 inline-slot rendering) — v2.0 (Phase 5)
- ✓ External `link:` frontmatter key surfaces as a per-row Link button (target="_blank" rel="noopener noreferrer"); URL sanitizer drops dangerous schemes (javascript:/data:/vbscript:/file:/about:) and promotes bare domains to https://; disabled state when missing (D-OV-16) — v2.0 (Phase 5)
- ✓ Detail page renders frontmatter as an Obsidian-style properties table above the markdown body (fix(05.1)) — v2.0 (Phase 5)

#### Joint Validation auto-discovery — post-v2.0
- ✓ Overview tab listing replaced: rows now auto-discovered from `content/joint_validation/<numeric_id>/index.html` (BeautifulSoup4 + lxml) with mtime-keyed cache and per-request glob — D-JV-01..D-JV-04, D-JV-08, D-JV-09 (Phase 1)
- ✓ 13-field properties parser (selector-based, `<small>` fallback) drives both grid view-model and detail page; Korean `담당자` field preserved — D-JV-04, D-JV-10, D-JV-11 (Phase 1)
- ✓ `/joint_validation/<confluence_page_id>` detail page (properties table + iframe sandbox of the original Confluence export served from `/static/joint_validation/...`); iframe sandbox attribute byte-pinned by invariant test — D-JV-05, D-JV-12, D-JV-13 (Phase 1)
- ✓ AI Summary route reuses Phase 3 `summary_service` plumbing via shared `_call_llm_with_text` helper; cache key namespaced as `("jv", confluence_page_id, mtime_ns, …)` — D-JV-15, D-JV-16 (Phase 1)
- ✓ Phase 5 Platform-curated machinery removed: `config/overview.yaml`, `overview_store.py`, `overview_filter.py`, `overview_grid_service.py`, `POST /overview/add` and tests — D-JV-06, D-JV-07 (Phase 1)
- ✓ Top-nav label flipped from "Overview" to "Joint Validation" — D-JV-01 (Phase 1)
- ✓ Final v2 suite: 360 passed / 5 skipped (30 net new tests, zero regressions)

#### UI shell rewrite + JV layout parity + pagination — post-v2.0
- ✓ Global UI shell rewritten — taller nav (16px padding, left-aligned tabs), full-width content (`.shell { padding: 0 }`), 4 type-scale tokens (`--font-size-logo/h1/th/body`), `body { display:flex; flex-direction:column; min-height:100vh }` sticky-in-flow layout, `.site-footer` block slot wired in `base.html` — D-UI2-01..D-UI2-05 (Phase 02)
- ✓ Browse "N platforms × M parameters" count caption migrated from `.panel-header` into `{% block footer %}`; OOB swap byte-stable — D-UI2-06 (Phase 02)
- ✓ Joint Validation listing restructured to single-panel Browse-mirror layout: one outer `.panel` carries `.panel-header` (h1 + count via `ms-auto`), inner horizontal flex filter row replaces the structurally-mistaken second panel; picker macro byte-stable — D-UI2-07..D-UI2-12 (Phase 02)
- ✓ Joint Validation pagination — `JV_PAGE_SIZE=15`, server-side row slicing, `PageLink` Pydantic submodel + ellipsis algorithm, `_pagination.html` partial rendered in footer + `pagination_oob` block, two-layer page validation (`Query/Form(ge=1, le=10_000)` + service clamp), `HX-Push-Url` round-trip omitting default page=1, hidden `page` input + `sortable_th` reset to page 1 on filter/sort change — D-UI2-13, D-UI2-14 (Phase 02)
- ✓ Final v2 suite: 442 passed / 5 skipped (39 net new tests, zero regressions from Phase 1's 360-test baseline)

### Active

<!-- v2.0 Bootstrap Shell — rewrite UI onto FastAPI + Bootstrap + HTMX. -->

#### Platform (v2.0)
- [ ] FastAPI app with Bootstrap 5 + HTMX shell — v1.0 Streamlit code removed in quick task 260429-kn7
- [ ] Horizontal top-nav tabs: Overview / Browse / Ask
- [ ] Intranet deployment target unchanged; auth still deferred (re-enable in a later milestone)

<!-- Overview (v2.0) curated-Platform watchlist superseded by Joint Validation auto-discovery (Phase 1, 2026-04-30). The "add/remove a platform" flow and Brand/SoC/Year filters are intentionally retired per D-JV-06 / D-JV-07 — see Validated → "Joint Validation auto-discovery — post-v2.0". -->

#### Content pages (v2.0)
- [ ] Per-platform markdown content pages at `content/platforms/<PLATFORM_ID>.md`
- [ ] Content page can be added, edited, deleted via HTMX forms
- [ ] Empty state when no content file exists — explicit Edit/Add affordance
- [ ] Markdown rendered with markdown-it-py (or similar)

#### AI Summary (v2.0)
- [ ] Button on each overview entity calls the LLM (reusing v1.0's openai SDK + backend radio) to summarize the content page markdown
- [ ] Summary swapped in-place via HTMX — no navigation
- [ ] Button disabled / hidden when no content file exists

<!-- Overview redesign (v2.0) — moved to Validated under "Overview redesign — v2.0" after Phase 5 completion (2026-04-29 UAT approved). -->


<!-- Ask carry-over (v2.0) — moved to Validated under "Ask — v2.0" after Phase 6 completion (2026-04-29). -->

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- **Admin data ingestion / Excel upload UI** — "Someone else maintains the DB." The app is strictly a read client; no writes, no upserts, no file drops.
- **Per-user SSO (Google / Okta / AD)** — Intranet with shared team credentials via `streamlit-authenticator` is explicitly what the team wants for v1.
- **Public-internet deployment / auth hardening** — Runs on the company intranet only; strong auth is not a v1 requirement.
- **Multi-table / cross-table joins** — The entire domain is the single-table EAV `ufs_data`. Supporting arbitrary schemas is a different product.
- **Editing / correcting platform data from the UI** — DB is read-only by contract; any correction flow lives upstream in the system that populates `ufs_data`.
- **Training / fine-tuning an in-house LLM** — v1 relies on the LLM adapters already scaffolded (OpenAI cloud or Ollama local).
- **v2.0 Browse Excel/CSV export** — v2.0 Browse is view-only by design choice (2026-04-26 user decision). The v1.0 export_dialog component was removed in quick task 260429-kn7 along with the rest of the Streamlit shell; export resurrection (if needed) will design a v2.0-native flow rather than restoring Streamlit.

## Context

**Domain:** The database (`ufs_data`) is a single-table EAV/long-form MySQL store of UFS (Universal Flash Storage) subsystem measurements for Android smartphone platforms. One row per `(PLATFORM_ID, InfoCategory, Item, Result)` tuple. Rows are typically pivoted client-side into a wide-form platforms × parameters matrix; MySQL itself does not support dynamic pivot. The schema is intentionally domain-agnostic — anything expressible as `(who, what-group, what-field, value)` fits — but today only UFS data lives in it. See the user-provided spec for the full column semantics and the InfoCategory catalog (`attribute`, `flags`, `device_descriptor`, `geometry_descriptor`, `health-descriptor`, `string_descriptor`, `lun_info`, `lun_unit_descriptor`, `lun_unit_block`, `dme`, `cpu`, `f2fs`, `mount`, `hibernParam`, `qcom_info`, `kernel`, `power`, `validation`, `ufsfeature`).

**The `Result` field is the hard part.** It is free-form `TEXT` populated by whatever probing tool captured the measurement. Expect raw hex (`0x01`), decimals, CSV lists (`mp,wm,og,jp`), identifier strings (`SAMSUNG`), compound packed values (`local=0x011101,peer=0x00010`), whitespace-delimited number blobs (`300000 576000 768000 …`), missing markers (`"None"` / empty / SQL `NULL`), and captured error output (`cat: /sys/...: No such file or directory`, `Permission denied`). Type coercion must be lazy and per-query — the same `Item` can be hex on one platform and decimal on another.

**Uniqueness:** `(PLATFORM_ID, InfoCategory, Item)` logically identifies one cell, but there is no `UNIQUE` constraint. Code must tolerate duplicates (e.g., `aggfunc="first"` when pivoting).

**`PLATFORM_ID` convention:** `Brand_Model_SoCID` (e.g., `Samsung_S22Ultra_SM8450`). Treat as an opaque string; partial identifiers are ambiguous across variants.

**User frustration that triggered this:**
1. **Discovery** — 100+ `InfoCategory` × `Item` combos; users don't know which parameter corresponds to their question.
2. **EAV confusion** — long-form rows are unreadable; people think natively in wide-form (platforms × parameters).
3. **SQL barrier** — non-technical users can't write SQL at all; technical users lose time writing pivot code from scratch for every ad-hoc question.

All three contribute equally, so solving only one is not enough.

**Existing scaffolding in the repo:**
- `app/core/config.py` — Pydantic `Settings` with `DatabaseConfig` (mysql/postgres/mssql/bigquery/snowflake, `readonly` flag), `LLMConfig` (openai/anthropic/ollama/vllm/custom), `AgentConfig` (`max_steps`, `row_cap=200`, `timeout_s=30`, `allowed_tables`, `max_context_tokens=30000`).
- `app/adapters/` — skeleton packages for DB and LLM adapters.
- `config/auth.yaml` — streamlit-authenticator credentials file (demo `admin` / `admin1234`).
- `config/settings.example.yaml` — example with `ufs_data` as the allowed table and both OpenAI and Ollama LLMs defined.
- `requirements.txt` — `streamlit>=1.40`, `streamlit-authenticator>=0.3.3`, `sqlalchemy>=2.0`, `pymysql>=1.1`, `pandas>=2.2`, `openpyxl>=3.1`, `pyyaml>=6.0`, `pydantic>=2.7`, `sqlparse>=0.5`, `openai>=1.50`, `httpx>=0.27`, `requests>=2.32`, `plotly>=5.22`, `altair>=5.3`, `python-dotenv>=1.0`, `bcrypt>=4.2`.
- `.env.example` — `OPENAI_API_KEY`, `SETTINGS_PATH`, `AUTH_PATH`, `LOG_DIR`.

**Naming conventions inside `Item` (must be honored by any parser):**
- LUN-scoped categories (`lun_info`, `lun_unit_descriptor`, `lun_unit_block`) prefix `N_` where `N ∈ {0..7}`; split with `Item.split("_", 1)`.
- DME items suffix `_local` or `_peer`. A single `Result` may occasionally pack both as `local=...,peer=...`.

## Constraints

- **Tech stack**: FastAPI + Bootstrap 5 + HTMX + Jinja2 + jinja2-fragments + SQLAlchemy (pymysql driver) + pandas + Pydantic v2 + python-dotenv — Why: v2.0 milestone shipped this stack 2026-04-29 (tag v2.0); v1.0 Streamlit shell sunset in quick task 260429-kn7.
- **Data**: Single-table EAV MySQL (`ufs_data`), read-only — Why: Real deployment; write path is owned by another system.
- **Scale**: ~100k+ rows across many platforms — Why: User flagged "too large"; a full dump must be pre-filtered before it hits the LLM, a chart, or an export.
- **Deployment**: Company intranet, shared team creds — Why: User selected this explicitly; no public-internet exposure is planned.
- **LLM choice**: OpenAI (cloud) + Ollama (local), user-switchable at runtime — Why: Lets users pick cloud for quality vs local for data-sensitivity situationally.
- **Result heterogeneity**: Type coercion is lazy and per-query, never global — Why: Same `Item` legitimately appears hex on one platform and decimal on another.
- **Security**: Readonly DB user is the primary SQL-injection backstop for the NL agent — Why: Even if the LLM generates harmful SQL, the DB can't execute writes.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Ad-hoc browsing is the v1 must-work feature; NL is secondary | User explicitly chose "Fast ad-hoc browsing" over "NL → correct answer" when forced to pick one — UI must stand on its own | ✓ Good — v1.0 Browse is complete and independently valuable; NL layered on top |
| Dual LLM backends (OpenAI + Ollama), user-selectable at runtime | Scaffolding already supports it; lets team pick per-question based on data sensitivity and quality needs | ✓ Good — both backends reachable via same `openai` SDK path (PydanticAI abstracts it) |
| Shared-credential intranet auth via existing `streamlit-authenticator` | Team is small, on internal network; proper SSO is not worth the complexity in v1 | ⚠️ Revisit — D-04 deferred auth to a pre-deployment phase. streamlit-authenticator + auth.yaml removed in 260429-kn7 (v1.0 sunset); fresh credential strategy to be picked when auth is re-enabled |
| Name "PBM2" left unexpanded | Internal tool; acronym does not need to be marketable | ✓ Good |
| Discovery aids = all four: catalog + search + LLM suggest + starter prompts | User ranked discovery pain equal to EAV and SQL pain; partial solutions leave real users stuck | ✓ Good — all four shipped (catalog multiselect, typeahead, NL-05 agent suggest, starter gallery) |
| DB is strictly read-only in v1; no upload / write UI | "Someone else maintains the DB" — ingestion belongs upstream | ✓ Good — enforced at DB adapter (readonly user) + service layer (`SET SESSION TRANSACTION READ ONLY`) + SQL validator (SELECT-only) |
| `Result` normalization is lazy and per-query | Same `Item` legitimately has different encodings across platforms; global coercion would lose information | ✓ Good — `normalize()` applied only to the Result column per query; `try_numeric()` called per-column during chart render |
| Agent has exactly one tool (`run_sql`); no schema inspector | Minimizes agent attack surface; forces the agent to ask the user via NL-05 rather than introspect the schema | ✓ Good — validated in Phase 2 code review (UNION/CTE smuggle attempts caught by sqlparse validator) |
| NL-05 uses `st.multiselect` pre-checked with agent candidates; "Run Query" to execute | Preserves Browse-page mental model; user can add/remove candidates before committing | ✓ Good |
| Path scrub (`/sys/`, `/proc/`, `/dev/`) applied only when OpenAI backend active | Local Ollama sees raw data; cloud LLM gets scrubbed data — protects sensitive filesystem paths from leaving the intranet | ✓ Good — re-review caught case-insensitive miss (uppercase paths) and fixed |
| Phase 1 auth deferred to pre-deployment phase per D-04 | Team agreed to skip auth during core app build so the data-browsing value could be validated first; gitignore still in place so scaffold cannot leak demo creds | — Pending — revisit when preparing for team-wide rollout |
| Drop v2.0 Browse export to keep the port view-only | Simpler shell migration; v1.0 Streamlit Browse still serves the export workflow until v1.0 sunset | ✓ Resolved — v1.0 export_dialog removed in 260429-kn7. Future export work (if any) is v2.0-native. |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-01 after Phase 02 (UI shell rewrite + Browse footer + JV layout parity + pagination) verified passed (14/14 must-haves). Locked decisions D-UI2-01..D-UI2-14 honored; picker macro byte-stable per D-UI2-09. v2 suite: 442 passed / 5 skipped.*
