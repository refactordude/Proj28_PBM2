# PBM2

## What This Is

PBM2 is an internal Streamlit website where a team of non-SQL users (PMs, analysts) can browse and query a large, EAV-form MySQL parameter database (`ufs_data`) that stores UFS subsystem profiles of Android platforms. The app lets users slice, pivot, filter, visualize, and export this long-form data — and ask natural-language questions on top — without ever writing SQL or reasoning about the schema themselves.

## Core Value

**Fast ad-hoc browsing of the parameter database.** Even if the NL layer fails, the UI must let a non-SQL user quickly find the platforms they care about, the parameters they care about, and see them in a wide-form grid they can read, compare, chart, and export. NL query rides on top of this and enhances it — it does not replace it.

## Current State

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

### Active

<!-- Pending decisions about what comes after v1.0. Populate at next milestone planning. -->

(None yet — v1.0 just shipped; start `/gsd-new-milestone` to scope v1.1)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- **Admin data ingestion / Excel upload UI** — "Someone else maintains the DB." The app is strictly a read client; no writes, no upserts, no file drops.
- **Per-user SSO (Google / Okta / AD)** — Intranet with shared team credentials via `streamlit-authenticator` is explicitly what the team wants for v1.
- **Public-internet deployment / auth hardening** — Runs on the company intranet only; strong auth is not a v1 requirement.
- **Multi-table / cross-table joins** — The entire domain is the single-table EAV `ufs_data`. Supporting arbitrary schemas is a different product.
- **Editing / correcting platform data from the UI** — DB is read-only by contract; any correction flow lives upstream in the system that populates `ufs_data`.
- **Training / fine-tuning an in-house LLM** — v1 relies on the LLM adapters already scaffolded (OpenAI cloud or Ollama local).

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

- **Tech stack**: Streamlit + SQLAlchemy (pymysql driver) + pandas + Pydantic v2 + python-dotenv — Why: scaffolding is already in place; no reason to diverge.
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
| Shared-credential intranet auth via existing `streamlit-authenticator` | Team is small, on internal network; proper SSO is not worth the complexity in v1 | ⚠️ Revisit — D-04 deferred auth to a pre-deployment phase. Must enable streamlit-authenticator + cookie-key guard before team-wide rollout |
| Name "PBM2" left unexpanded | Internal tool; acronym does not need to be marketable | ✓ Good |
| Discovery aids = all four: catalog + search + LLM suggest + starter prompts | User ranked discovery pain equal to EAV and SQL pain; partial solutions leave real users stuck | ✓ Good — all four shipped (catalog multiselect, typeahead, NL-05 agent suggest, starter gallery) |
| DB is strictly read-only in v1; no upload / write UI | "Someone else maintains the DB" — ingestion belongs upstream | ✓ Good — enforced at DB adapter (readonly user) + service layer (`SET SESSION TRANSACTION READ ONLY`) + SQL validator (SELECT-only) |
| `Result` normalization is lazy and per-query | Same `Item` legitimately has different encodings across platforms; global coercion would lose information | ✓ Good — `normalize()` applied only to the Result column per query; `try_numeric()` called per-column during chart render |
| Agent has exactly one tool (`run_sql`); no schema inspector | Minimizes agent attack surface; forces the agent to ask the user via NL-05 rather than introspect the schema | ✓ Good — validated in Phase 2 code review (UNION/CTE smuggle attempts caught by sqlparse validator) |
| NL-05 uses `st.multiselect` pre-checked with agent candidates; "Run Query" to execute | Preserves Browse-page mental model; user can add/remove candidates before committing | ✓ Good |
| Path scrub (`/sys/`, `/proc/`, `/dev/`) applied only when OpenAI backend active | Local Ollama sees raw data; cloud LLM gets scrubbed data — protects sensitive filesystem paths from leaving the intranet | ✓ Good — re-review caught case-insensitive miss (uppercase paths) and fixed |
| Phase 1 auth deferred to pre-deployment phase per D-04 | Team agreed to skip auth during core app build so the data-browsing value could be validated first; gitignore still in place so scaffold cannot leak demo creds | — Pending — revisit when preparing for team-wide rollout |

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
*Last updated: 2026-04-24 after v1.0 MVP milestone*
