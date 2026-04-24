# Project Research Summary

**Project:** PBM2
**Domain:** Streamlit intranet EAV-MySQL browser + NL-to-SQL agent (UFS platform parameters)
**Researched:** 2026-04-23
**Confidence:** HIGH

## Executive Summary

PBM2 is a read-only internal data tool solving three equal user pain points: users cannot discover which parameters exist (Discovery), cannot read long-form EAV rows (EAV confusion), and cannot write SQL (SQL barrier). The validated build strategy is to solve Discovery and EAV confusion first through a fast ad-hoc browsing UI — platform picker, parameter catalog tree, wide-form pivot grid, and export — and then layer NL-to-SQL on top once that foundation is solid. The existing scaffolding (Pydantic settings, DB/LLM adapter skeletons, auth YAML) is sound and should not be redesigned; the only missing pieces are the NL agent framework (add PydanticAI), the service layer (add ufs_service.py + result_normalizer.py), and the page files.

The recommended approach is a four-phase build: foundation/auth wiring first, then the browsing layer (the v1 must-work feature), then the NL agent layer, then polish. The Result field is the hardest domain problem — it is free-form text that can be hex, decimal, CSV, compound packed values, shell error output, or the string "None". Normalization must be lazy and per-query; any global coercion will silently lose data. The dual-LLM backend (OpenAI cloud + Ollama local, user-switchable at runtime) is a firm user requirement and is straightforwardly implemented using the openai SDK base_url parameter pointed at Ollama\'s OpenAI-compatible endpoint — no additional routing library is needed.

The primary risks are: (1) memory blow-up if the full 100k-row table is pulled before filtering — every query must push WHERE clauses to MySQL before pandas pivots; (2) the wide pivot becoming unusable with 100+ columns — default to single-category view; (3) Ollama tool-calling unreliability with smaller models — requires a JSON extraction fallback and a tested model list; and (4) prompt injection via stored Result values reaching the LLM context — rows must be wrapped in <db_data> delimiters with explicit framing instructions. All four risks have clear, well-documented mitigations.

---

## Key Findings

### Recommended Stack

The existing requirements.txt is correct and complete except for one addition: pydantic-ai>=1.0,<2.0 (the NL agent framework). No core library should be swapped. The only architectural decisions that were deferred and now have clear answers are: PydanticAI for the agent, st.dataframe with column_config for the pivot grid (not AgGrid), the openai SDK directly for both backends (not litellm), and sqlalchemy>=2.0,<2.1 (pin away from the 2.1 beta). Version pins to use: Streamlit 1.56.0, SQLAlchemy 2.0.49, pandas 3.0.2, PydanticAI 1.86.0, streamlit-authenticator 0.4.2.

**Core technologies:**
- **Streamlit 1.56.0**: UI framework — st.dataframe + column_config covers all pivot grid needs natively; st.navigation + st.Page for multi-page auth-gated routing
- **SQLAlchemy 2.0.x Core** (not ORM): DB engine and connection pool — pool_pre_ping=True + pool_recycle=3600 are mandatory for MySQL on an intranet (prevents "server gone away" errors); pin to <2.1 (2.1 is beta)
- **pandas 3.0.2**: Client-side pivot, normalization, export — pd.read_sql_query(sa.text(...), conn) is the correct pandas 3.x / SQLAlchemy 2.x idiom; older pd.read_sql with text SQL is deprecated
- **PydanticAI 1.86.0**: NL-to-SQL agent — API-stable V1; first-class single-table SQL generation example in official docs; structured Success | InvalidRequest output; native OpenAI + Ollama support; minimal dependency surface vs LangChain
- **openai SDK 1.78.x**: LLM client for BOTH backends — OpenAI(base_url="http://localhost:11434/v1", api_key="ollama") handles Ollama; base_url must include /v1 or calls 404
- **Pydantic v2 + python-dotenv + PyYAML**: Already in scaffolding; settings load chain is .env -> settings.yaml -> Pydantic Settings -> @st.cache_resource
- **pytest + AppTest**: Testing — Streamlit\'s native headless AppTest runs in CI without a browser; use pytest-mock to patch get_engine() and LLM calls

**What NOT to use:** LangChain (50+ transitive deps, full-schema reflection on every call, hard to gate allowed_tables), litellm (50MB for two providers that share the same wire protocol), streamlit-aggrid (solo-maintained JS component), SQLAlchemy ORM (single read-only table, no models needed), full 100k-row table loads, st.cache_resource for DataFrames.

### Expected Features

The three pain points map to three feature clusters that must all ship in v1. Solving only one is not enough.

**Must have (table stakes) — v1 launch blockers:**
- Platform multi-select picker with typeahead — users cannot start without this (EAV)
- Parameter catalog with InfoCategory tree + typeahead search — resolves Discovery at root
- Wide-form pivot grid: platforms x parameters, sortable, column-hide (EAV)
- Single-platform detail view grouped by InfoCategory (EAV)
- Result normalization to a single missing sentinel (pd.NA) — prevents misleading display
- Row count display ("showing N of M platforms") — confirms filter is working
- Loading / empty / error states with plain-English messages — required for internal adoption
- Excel and CSV export — analysts will not use the tool without this
- Sticky filters via st.session_state — without this, every widget interaction resets work
- NL question input + LLM model switcher (OpenAI/Ollama sidebar) — the SQL barrier feature
- Show generated SQL in collapsed expander — required for user trust
- Regenerate button — required for stochastic LLM output tolerance
- Session query history — required for iterative question refinement
- LLM plain-text summary alongside result table
- LLM parameter proposal step (question -> proposed params -> confirm -> SQL) — resolves Discovery for NL users
- Agent safety guardrails wired and visible (readonly, row cap=200, timeout=30s)
- Starter-prompt gallery (6-10 curated questions, YAML-backed) — blank-slate onboarding
- Shareable URL via st.query_params — enables Slack handoffs of filter state

**Should have (differentiators) — add in v1.x after first user feedback:**
- Heatmap / conditional formatting for numeric parameters — outlier detection at a glance
- Editable generated SQL (power-user escape hatch, hidden in expander, secondary to NL input)
- "Why this query?" explanation panel — builds trust in NL results
- LUN sub-header grouping in pivot (N_fieldname items displayed as "LUN field [0-7]")
- DME _local/_peer split display

**Defer (v2+) — trigger-based, do not build without user signal:**
- Platform comparison presets — trigger: users repeatedly re-selecting the same cohort
- Saved parameter sets — trigger: users describing "my regular view"
- Cross-session query history — requires server-side persistence, new architectural dependency
- "Similar platforms" suggestion — requires similarity computation over pivot matrix
- Confidence/quality indicator for NL results — requires reliable LLM self-evaluation signal

**Anti-features (never add without deliberate reversal of documented decision):**
- Free-form SQL editor as first-class feature — defeats the SQL barrier the app exists to remove
- Admin data ingestion / write UI — DB is read-only by contract
- Per-user SSO / RBAC — shared-credential intranet is the explicit v1 choice
- Global Result type coercion on load — same Item is legitimately different types across platforms

### Architecture Approach

The architecture is a four-layer stack: UI pages -> service layer (ufs_service.py) -> adapters (DB/LLM) -> external services (MySQL, OpenAI/Ollama). Pages never touch adapters directly. The service layer handles query building, pivot, and normalization. The agent runner sits inside app/core/agent/ alongside AgentConfig and dispatches to typed tools in agent/tools.py, which are thin wrappers over ufs_service functions. The SQLAlchemy engine is a @st.cache_resource singleton shared across sessions; query results are @st.cache_data(ttl=300) per call signature. Runtime user preferences (active LLM name, active DB name, query history) live in st.session_state — never in @st.cache_resource.

**Major components:**
1. **streamlit_app.py** — Auth guard (streamlit-authenticator), st.navigation page router, shared sidebar (LLM/DB selector, connection status)
2. **app/pages/browse.py** — Platform picker, parameter catalog tree, wide-form pivot grid, charts, export; calls only ufs_service functions
3. **app/services/ufs_service.py + result_normalizer.py** — Domain logic: parameterized SQL builder, pivot engine, 5-stage normalization pipeline (missing -> error strings -> LUN prefix -> DME split -> lazy type coercion)
4. **app/core/agent/runner.py + tools.py** — ReAct loop (max_steps=5, timeout=30s, row_cap=200), 5 typed tools (list_platforms, list_parameters, search_parameters, fetch_cells, run_readonly_sql)
5. **app/adapters/db/ + app/adapters/llm/** — Existing skeleton; MySQLAdapter wraps SQLAlchemy engine; OpenAIAdapter/OllamaAdapter use openai.OpenAI(base_url=...) pattern
6. **app/pages/nl_query.py** — NL input box, parameter proposal confirmation step, agent result display, streaming summary, history entry
7. **app/pages/settings.py** — DB/LLM connection CRUD; shown before browsing so users can configure before first use

**Critical ordering constraint:** result_normalizer.py must have a stable API and unit tests before ufs_service.py is written. The normalization API is the domain\'s hardest problem — the free-form Result field — and the pivot correctness depends entirely on it.

### Critical Pitfalls

1. **Memory blow-up on full-table pivot** (BLOCKER, Phase 1) — Always push WHERE PLATFORM_ID IN (...) and WHERE Item IN (...) to MySQL before fetching. Never load the full 100k-row table into pandas. Apply the same 200-row cap to browse queries as to agent queries.

2. **Global Result type coercion corrupts heterogeneous data** (BLOCKER, Phase 1) — The same Item is legitimately hex on one platform and decimal on another. Use a ResultClassifier enum (HEX | DECIMAL | CSV | BLOB | COMPOUND | ERROR | MISSING); coerce lazily and only for the specific Item in scope when charting. Define MISSING_SENTINELS = {None, "None", "", "N/A", "null", "NULL"} and an is_missing(val) utility; use pd.NA (not np.nan) as the display sentinel.

3. **EAV cell duplication silently corrupts pivot output** (BLOCKER, Phase 1) — The schema has no UNIQUE constraint. Always run df.duplicated(subset=["PLATFORM_ID", "InfoCategory", "Item"]).sum() before pivot and log/surface the count. Use aggfunc="first" consciously. Include a test fixture with deliberate duplicates.

4. **Wide pivot grid becomes unusable at 100+ columns** (SERIOUS, Phase 1 UI) — Default to single-InfoCategory view; require explicit user action to expand to multi-category. Cap displayed columns at ~30 with a visible warning. Keep PLATFORM_ID as the DataFrame index for the frozen-column effect.

5. **Streamlit full-script rerun executes expensive DB queries on every widget interaction** (BLOCKER, Phase 1) — Wrap all DB queries in @st.cache_data(ttl=300) with immutable argument types (tuples, not lists). Gate LLM calls behind an explicit st.form submit button. Use @st.cache_resource for the engine, @st.cache_data for DataFrames.

6. **Prompt injection via stored Result values** (SERIOUS, Phase 2) — Wrap all DB row data in <db_data>...</db_data> delimiters in the LLM context with a system-prompt instruction that content inside the tag is raw data, not instructions. Mitigated additionally by row_cap=200 and sqlparse SELECT-only validation.

7. **Ollama tool-calling unreliability with smaller models** (SERIOUS, Phase 2) — Implement a JSON extraction fallback in the Ollama adapter (try json.loads, then regex first-JSON-block, then surface as plain text). Only document tested models (Llama 3.1+, Qwen 2.5+, Mistral Nemo). Set OLLAMA_KEEP_ALIVE=-1 to avoid 10-30s cold-start stalls.

8. **Data sensitivity / PII leakage to OpenAI** (SERIOUS, Phase 2) — Default the LLM backend to Ollama; require explicit user action to switch to OpenAI. Show a prominent data-sensitivity warning when OpenAI is selected. Implement a configurable pii_filter that scrubs filesystem paths (/sys/, /proc/) before they enter the LLM context.

---

## Implications for Roadmap

### Phase 1: Foundation + Browsing

**Rationale:** Ad-hoc browsing is the stated primary value; the NL layer must not block it. The service layer and normalizer must be built and tested before the pivot grid UI. Auth credentials must be correct before any shared deployment. This phase delivers a fully working product even if the NL layer is never added.

**Delivers:** A working read-only data browser — platform picker, parameter catalog tree, wide-form pivot grid, single-platform detail view, normalization, export, auth, settings UI, starter-prompt gallery (as a browsing entry point), shareable URL.

**Features addressed:** All table-stakes browsing features + auth/deployment prerequisites from FEATURES.md. All P1 browsing items.

**Pitfalls to prevent:** Memory blow-up (SQL filters before pivot), global type coercion (build normalizer first and test it), EAV cell duplication (duplicate-aware test fixture), wide pivot unusability (single-category default, 30-column cap), Streamlit rerun cost (cache_data on all DB queries), demo auth credentials (auth.yaml in .gitignore, startup assertion on weak cookie.key), "None" string truthy (is_missing unit test), LUN prefix in catalog (group N_fieldname items).

**Research flag:** Standard patterns — well-documented Streamlit + pandas + SQLAlchemy. The domain-specific work (result_normalizer.py) is fully specified in PROJECT.md and ARCHITECTURE.md. No deeper research phase needed.

### Phase 2: NL Agent Layer

**Rationale:** The browsing layer must be solid before the agent is layered on top. The agent tools are all wrappers over ufs_service functions that already exist from Phase 1. NL can fail gracefully without breaking the browse UI.

**Delivers:** Full NL-to-SQL capability across all three query shapes (lookup-one-platform, compare-across-platforms, filter-platforms-by-value). Parameter proposal step, plain-text LLM summary, session history, agent safety guardrails wired and visible.

**Features addressed:** All P1 NL layer features from FEATURES.md — NL question input, LLM model switcher, show SQL, regenerate, session history, parameter proposal step, LLM summary, agent safety guardrails.

**Stack used:** PydanticAI 1.86.0, openai SDK dual-backend wiring, sqlparse for SELECT-only validation + LIMIT injection, httpx async for Ollama streaming.

**Pitfalls to prevent:** Prompt injection (db_data wrapper), LIKE full-table scan (SQL validation layer), LLM hallucinated Item names (parameter disambiguation step with exact DB values), Ollama JSON inconsistency (extraction fallback), Ollama cold-start (OLLAMA_KEEP_ALIVE, streaming, 120s timeout), agent infinite loop (max_steps=5 hard counter, tool deduplication), OpenAI PII leakage (Ollama as default, warning, pii_filter), session state contamination (cache_resource only for stateless infrastructure).

**Research flag:** Needs deeper attention during planning. The PydanticAI agent tool contract, the parameter disambiguation flow (two-step: propose -> confirm -> SQL), and the Ollama adapter fallback chain are the three pieces most likely to require iteration. A /gsd-research-phase is recommended before planning NL agent milestones.

### Phase 3: Polish + v1.x Differentiators

**Rationale:** Once both layers are working and in use, targeted enhancements address gaps from real usage. No new dependencies — all build on Phase 1 and 2 foundations.

**Delivers:** Heatmap/conditional formatting for numeric parameters, editable generated SQL (secondary hidden feature), "Why this query?" explanation panel, LUN sub-header grouping in pivot, DME _local/_peer split display, history page, UX polish from user feedback.

**Features addressed:** All P2 items from FEATURES.md feature prioritization matrix.

**Watch out:** Editable SQL must remain a secondary hidden feature — it must not become a first-class interface. Heatmap must handle non-numeric columns gracefully.

**Research flag:** Standard patterns. No additional research needed.

### Phase 4: v2+ Features (deferred, trigger-based)

**Rationale:** Defer until v1 is validated and specific user requests emerge. Each feature has a documented trigger in FEATURES.md.

**Delivers (when triggered):** Platform comparison presets, saved parameter sets, cross-session query history (requires server-side persistence design decision), similar platforms suggestion, deep-link to named preset, confidence/quality indicator for NL results.

**Research flag:** Cross-session query history will need a research phase when scoped — the server-side persistence decision (SQLite vs new DB table vs key-value store) is not trivial for a Streamlit intranet app.

### Phase Ordering Rationale

- **Normalizer before service before UI:** result_normalizer.py must have a stable API and pass unit tests before ufs_service.py is written. This is the single hardest domain problem and the pivot depends entirely on it.
- **Settings page in Phase 1, not Phase 3:** Users need to configure DB and LLM endpoints before browsing. It is a Phase 1 prerequisite.
- **Auth rotation in Phase 1:** demo credentials must be resolved before any shared team deployment. It is a deployment precondition, not a polish item.
- **LUN catalog grouping spans phases:** The catalog display fix (group N_fieldname items) belongs in Phase 1; the agent schema encoding for LUN-scoped queries belongs in Phase 2.
- **Browse before NL:** The agent tools are wrappers over service functions. Building the agent before the service is proven creates fragile dependencies. The user\'s stated priority is browsing first.

### Research Flags

**Needs research during planning:**
- **Phase 2 (NL Agent):** PydanticAI agent tool contract for single-table EAV pattern; parameter proposal step UX flow; Ollama adapter JSON fallback implementation. Recommend /gsd-research-phase before planning NL agent milestones.
- **Phase 4 (cross-session history, if triggered):** Server-side persistence design decision.

**Standard patterns (skip research):**
- **Phase 1 (Browsing):** Well-documented Streamlit + pandas + SQLAlchemy patterns verified in research.
- **Phase 3 (Polish):** Heatmap, editable SQL, history page all follow well-documented patterns.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified via PyPI and official docs; existing scaffolding validated as sound; no speculative recommendations |
| Features | HIGH (browsing) / MEDIUM (NL UX) | Streamlit native capabilities verified against official docs; NL-to-SQL UX from multiple production deployments; EAV pivot UX from community practice |
| Architecture | HIGH | Scaffolding read directly; Streamlit and SQLAlchemy patterns verified against official docs; component boundaries derived from existing code structure |
| Pitfalls | HIGH (Streamlit/pandas) / MEDIUM (Ollama reliability) | Streamlit/pandas mechanics are documented and reproducible; Ollama tool-calling data from community sources |

**Overall confidence:** HIGH

### Gaps to Address

- **Ollama model compatibility list:** Llama 3.1+, Qwen 2.5+, Mistral Nemo identified as verified, but the actual models available on the team\'s Ollama instance must be confirmed before Phase 2 planning.
- **PydanticAI agent loop wiring with existing AgentConfig:** The integration of max_steps, timeout_s, and row_cap enforcement inside the @agent.tool decorator should be prototyped early in Phase 2 before the full NL page is built.
- **MySQL index status on ufs_data:** Whether a composite index on (PLATFORM_ID, InfoCategory, Item) already exists should be verified at Phase 2 start. Without it, the SQL validation layer must always inject MAX_EXECUTION_TIME hints.
- **PLATFORM_ID count in production:** If count exceeds ~500, the platform picker needs a grouped/brand-filtered design from Phase 1. Check against the real DB before Phase 1 UI work begins.

---

## Sources

### Primary (HIGH confidence)
- Streamlit 1.56.0 official docs — st.dataframe column_config, st.navigation, AppTest, caching semantics: https://docs.streamlit.io
- SQLAlchemy 2.0.49 release page; 2.1 beta confirmed: https://pypi.org/project/SQLAlchemy/ and https://www.sqlalchemy.org/blog/2026/04/16/sqlalchemy-2.1.0b2-released/
- pandas 3.0.2 release page and what\'s new: https://pypi.org/project/pandas/
- PydanticAI 1.86.0 — V1 API-stable, SQL generation example: https://pypi.org/project/pydantic-ai/ and https://pydantic.dev/docs/ai/examples/data-analytics/sql-gen/
- Ollama OpenAI compatibility — base_url /v1 requirement: https://docs.ollama.com/api/openai-compatibility
- streamlit-authenticator 0.4.2: https://pypi.org/project/streamlit-authenticator/
- DuckDB + Streamlit caching pattern: https://duckdb.org/2025/03/28/using-duckdb-in-streamlit

### Secondary (MEDIUM confidence)
- NL2SQL system design guide 2025: https://medium.com/@adityamahakali/nl2sql-system-design-guide-2025-c517a00ae34d
- Ollama tool calling reliability: https://deepwiki.com/ollama/ollama/7.2-tool-calling-and-function-execution
- Ollama model unloading / OLLAMA_KEEP_ALIVE: https://github.com/ollama/ollama/issues/13552
- EAV model and pivot reporting patterns: https://softwarepatternslexicon.com/102/6/15/
- Pandas pivot duplicate index issue: https://github.com/pandas-dev/pandas/issues/63314
- Streamlit session state isolation: https://discuss.streamlit.io/t/session-state-shared-between-different-users/44432

### Tertiary (LOW confidence — needs validation)
- LLM prompt injection via stored DB data: https://www.keysight.com/blogs/en/tech/nwvs/2025/07/31/db-query-based-prompt-injection
- NL-to-SQL hallucination reduction: https://medium.com/wrenai/reducing-hallucinations-in-text-to-sql-building-trust-and-accuracy-in-data-access-176ac636e208
- LLM agent infinite loop failure modes: https://www.agentpatterns.tech/en/failures/infinite-loop

---
*Research completed: 2026-04-23*
*Ready for roadmap: yes*
