# Milestones

## v1.0 MVP (Shipped: 2026-04-24)

**Phases completed:** 2 phases, 13 plans, 16 tasks

**Key accomplishments:**

- Streamlit entrypoint with st.navigation, shared sidebar (DB/LLM/health), corrected MySQLAdapter (pool_recycle=3600, pd.read_sql_query), and gitignore secrets exclusion
- 5-stage EAV Result-field normalization pipeline with 65-test pytest suite covering hex/decimal/CSV/compound classification, LUN prefix parsing, DME side detection, and lazy numeric coercion
- 4-function domain service layer with @st.cache_data TTL caching, parameterized IN-clause SQL, row capping, Result normalization, and aggfunc='first' pivot — backed by 10 pytest tests on a SQLite in-memory fixture
- Sidebar filters + Pivot tab with swap-axes, 30-col/200-row warnings, URL round-trip, and copy-link button — replacing Plan 01 placeholder with the app's primary UI surface
- Detail tab (BROWSE-05) and Chart tab (VIZ-01/VIZ-02) filling the Plan 05 stubs — with tab URL round-trip and sidebar Copy link
- Excel export (EXPORT-01) + CSV export (EXPORT-02) via a single st.dialog component wired into the Pivot tab's ctrl_export slot
- NL-07/NL-08 dual backend: PydanticAI-compatible OpenAI/Ollama factory, sidebar LLM radio activated; `nest-asyncio` added for Streamlit event-loop interop
- SAFE-02/03/04(timeout)/06 and NL-09: 4 TDD-built pure safety functions (sqlparse SELECT-only validator, LIMIT injector, path scrubber, Ollama JSON fallback) with 53 tests — later hardened with UNION + CTE + uppercase-path regression tests after code review
- NL-06/SAFE-04(step-cap)/SAFE-05: PydanticAI agent with `output_type=SQLResult|ClarificationNeeded`, single `run_sql` tool composing all safety primitives + `<db_data>` prompt-injection wrapper, 10-test TestModel/FunctionModel coverage
- NL-01/02/03/04/10: Ask page (st.navigation third slot) with question input, SQL expander + Regenerate, collapsed history panel, OpenAI data-sensitivity dismissible banner, SAFE-04 abort banner with distinct step-cap vs timeout copy
- NL-05: two-turn ClarificationNeeded flow — multiselect pre-checked with agent-proposed (InfoCategory, Item) candidates, "Run Query" re-invokes agent with confirmed params injected as second-turn structured message
- ONBD-01/02: gitignored `config/starter_prompts.yaml` (committed `.example.yaml`) with 8 curated UFS prompts covering lookup/compare/filter shapes, rendered as 4×2 gallery that hides after first successful run

### Code Review Hardening (post-execution)

- Phase 1: 1 critical (table-name allowlist) + 5 warnings (multi-DB cache key, DB error logging, `pd.isna` guard, filename traversal order, browse.tab URL sync) + 1 re-review-surfaced XSS (escape DB name in sidebar health indicator) — all fixed with regression tests
- Phase 2: 2 critical SQL validator bypasses (UNION smuggle, CTE smuggle) + 4 warnings (display-side timeout, Regenerate discarded confirmed params, case-insensitive path scrub, pymysql error leak to LLM) — all fixed with regression tests

### Deferred / Accepted Gaps

- FOUND-01 (login page) and FOUND-03 (cookie-key startup guard) deferred to a pre-deployment phase per CONTEXT D-04. FOUND-02 (gitignore auth.yaml) IS in scope and complete so the scaffold cannot leak demo credentials when auth is enabled later.
- 12 items pending live-browser / live-LLM human validation, persisted in `01-HUMAN-UAT.md` + `02-HUMAN-UAT.md` for later `/gsd-verify-work`.

### Stats

- Git range: `b30664a` → `fa00e3d` (87 commits across 2026-04-23 → 2026-04-24)
- LOC: 3080 (app/) + 1711 (tests/) Python
- Tests: 171 passing (75 Phase 1 + 96 Phase 2)
- Requirements: 47/49 satisfied, 2 deferred (accepted per D-04)

---
