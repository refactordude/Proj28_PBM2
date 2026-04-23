# PBM2

## What This Is

PBM2 is an internal Streamlit website where a team of non-SQL users (PMs, analysts) can browse and query a large, EAV-form MySQL parameter database (`ufs_data`) that stores UFS subsystem profiles of Android platforms. The app lets users slice, pivot, filter, visualize, and export this long-form data — and ask natural-language questions on top — without ever writing SQL or reasoning about the schema themselves.

## Core Value

**Fast ad-hoc browsing of the parameter database.** Even if the NL layer fails, the UI must let a non-SQL user quickly find the platforms they care about, the parameters they care about, and see them in a wide-form grid they can read, compare, chart, and export. NL query rides on top of this and enhances it — it does not replace it.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. -->

#### Browsing & Discovery

- [ ] Browsable parameter catalog (InfoCategory → Item tree/sidebar)
- [ ] Type-ahead search bar over `InfoCategory` and `Item` names
- [ ] Platform picker (filter by one or many `PLATFORM_ID` values)
- [ ] Parameter picker (multi-select; category + item)
- [ ] Starter-prompt / saved-question gallery that users can click to run or modify

#### Data Display

- [ ] Wide-form pivot grid: platforms × parameters (`aggfunc="first"`), sortable, scrollable
- [ ] Long-form browsable view for a single platform (grouped by `InfoCategory`)
- [ ] Result normalization: coerce `None` / `"None"` / empty / `"cat: ..."` / `"Permission denied"` to a single missing sentinel before display
- [ ] Charts for numeric parameters (Plotly or Altair) — bar / line / scatter as appropriate
- [ ] Excel and CSV export of any visible result table

#### Natural-Language Layer

- [ ] NL question input that answers the three core shapes: lookup-one-platform, compare-across-platforms, filter-platforms-by-value
- [ ] Agent proposes candidate parameters from a vague question before running SQL
- [ ] Plain-text LLM-synthesized summary alongside the returned data table / chart
- [ ] LLM adapter supports OpenAI and Ollama, switchable at runtime from the sidebar
- [ ] Agent safety: `readonly` DB user, `allowed_tables: ["ufs_data"]`, row cap, step cap, timeout — all honored

#### Platform

- [ ] Streamlit intranet deployment, shared team credentials via `streamlit-authenticator`
- [ ] Settings UI (or at minimum config file flow) for database connections and LLM endpoints — consistent with existing `config/settings.example.yaml`

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
| Ad-hoc browsing is the v1 must-work feature; NL is secondary | User explicitly chose "Fast ad-hoc browsing" over "NL → correct answer" when forced to pick one — UI must stand on its own | — Pending |
| Dual LLM backends (OpenAI + Ollama), user-selectable at runtime | Scaffolding already supports it; lets team pick per-question based on data sensitivity and quality needs | — Pending |
| Shared-credential intranet auth via existing `streamlit-authenticator` | Team is small, on internal network; proper SSO is not worth the complexity in v1 | — Pending |
| Name "PBM2" left unexpanded | Internal tool; acronym does not need to be marketable | — Pending |
| Discovery aids = all four: catalog + search + LLM suggest + starter prompts | User ranked discovery pain equal to EAV and SQL pain; partial solutions leave real users stuck | — Pending |
| DB is strictly read-only in v1; no upload / write UI | "Someone else maintains the DB" — ingestion belongs upstream | — Pending |
| `Result` normalization is lazy and per-query | Same `Item` legitimately has different encodings across platforms; global coercion would lose information | — Pending |

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
*Last updated: 2026-04-23 after initialization*
