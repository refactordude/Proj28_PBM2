# Feature Research

**Domain:** Streamlit intranet data-browsing + NL-to-SQL tool over a single-table EAV MySQL database
**Researched:** 2026-04-23
**Confidence:** HIGH (Streamlit native capabilities verified against official docs); MEDIUM (NL-to-SQL UX patterns from multiple credible production deployments); MEDIUM (EAV pivot UX from community practice, no single authoritative source)

---

## Pain Point Key

Every feature below is tagged with which of the three founding pain points it addresses:

| Tag | Pain Point |
|-----|------------|
| D | Discovery — users don't know which parameter to look for |
| E | EAV — long-form rows are unreadable; users expect wide form |
| S | SQL — non-technical users cannot write pivot SQL at all |
| I | Infrastructure — invisible scaffolding, not user-facing pain |

---

## Feature Landscape

### Table Stakes (Users Expect These)

Missing any of these makes the product feel broken or unprofessional, even for an internal tool.

#### Browsing & Grid Layer

| Feature | Why Expected | Complexity | Pain Point | Notes |
|---------|--------------|------------|------------|-------|
| Platform multi-select picker | Any data tool has a "what are you looking at?" selector | LOW | E | `st.multiselect` over distinct `PLATFORM_ID` values; partial-match typeahead critical because names are long (`Brand_Model_SoCID`) |
| Parameter picker with category grouping | Users must choose columns; InfoCategory tree prevents a flat 100+ item list from being unusable | MEDIUM | D | Render as two-level: category → item; support multi-select within categories |
| Wide-form pivot grid (platforms × parameters) | Users think in wide form, data lives in long form; the translation must happen invisibly | MEDIUM | E | `pandas.pivot_table(aggfunc="first")` client-side; use `st.dataframe` with column config; handle duplicate `(PLATFORM_ID, InfoCategory, Item)` rows silently |
| Single-platform detail view (long → grouped by InfoCategory) | Side-by-side with pivot; when user wants depth on one device | LOW | E | Grouped by category; collapsible sections or tabs per category |
| Sortable pivot grid | Every table in every tool is sortable; absence reads as broken | LOW | E | `st.dataframe` native header-click sort |
| Column hiding (hide parameters) | Wide tables with 100+ columns are unreadable without this | LOW | D/E | `st.dataframe` column visibility menu is native in Streamlit >= 1.40; also expose programmatic `column_order` |
| Row count display | "Showing 14 of 47 platforms" confirms filter is working | LOW | I | Always show filtered vs total counts above the grid |
| Result normalization / missing value sentinel | Raw `None`, `"None"`, empty string, `Permission denied`, `cat: /sys/...` all mean "not measured"; showing them raw misleads users | MEDIUM | E | Normalize to a single display value (e.g., `—`) before rendering; do this per-query, lazily, not globally on load |
| Loading spinner / skeleton state | Any DB call takes time; blank screen with no feedback is alarming | LOW | I | `st.spinner` around all DB fetches and LLM calls |
| Empty state messaging | If filter yields zero rows, say so explicitly with a suggested next step | LOW | I | "No platforms matched your filters. Try widening the platform or parameter selection." |
| Error surface | DB connection failures, LLM timeouts, bad query — each needs a visible user-friendly error, not a Python traceback | LOW | I | `st.error` with plain-English message; log traceback server-side only |
| Excel / CSV export | Any data tool used by analysts is expected to feed Excel | LOW | E/S | `openpyxl` already in requirements; offer both formats on the pivot result and on the NL result |

#### NL Query Layer

| Feature | Why Expected | Complexity | Pain Point | Notes |
|---------|--------------|------------|------------|-------|
| Natural-language question input box | The entire point of the NL layer; absence means it doesn't exist | LOW | S | `st.text_area` or `st.chat_input`; placeholder text should show an example query |
| Show generated SQL (collapsed by default) | Without this, users cannot verify or debug LLM output; breaks trust | LOW | S | `st.expander("View generated SQL")` wrapping a `st.code` block; collapsed by default to reduce clutter |
| Regenerate button | LLM output is stochastic; users expect one retry before blaming themselves | LOW | S | Re-runs the same question with temperature bump or alternate prompt; does not require editing SQL |
| Query history (current session) | Users iterate on questions; needing to retype the last 5 tries is frustrating | LOW | S | `st.session_state` list; display as clickable chips or a selectbox above the input |
| LLM model switcher (OpenAI / Ollama) | Already a user-decided feature; absence means it wasn't wired up | LOW | I | Sidebar `st.radio` or `st.selectbox`; toggles `LLMConfig` at runtime per session state |
| Plain-text LLM summary alongside results | Data table alone answers "what" but not "what does this mean"; summary closes the gap | MEDIUM | S | Separate LLM call after SQL runs; capped token output; shown in `st.info` or `st.markdown` block below the result table |
| Agent safety guardrails visible | "Read-only query, max 200 rows" notice builds trust that the tool won't mutate data | LOW | I | One-line disclaimer in sidebar or footer; not a modal, just text |

#### Sharing & Navigation

| Feature | Why Expected | Complexity | Pain Point | Notes |
|---------|--------------|------------|------------|-------|
| Shareable URL for current view | Intranet tools live and die by Slack-paste links; without this, every handoff requires re-explaining the filter state | MEDIUM | I | `st.query_params` (Streamlit >= 1.30) supports read/write; known issue: params clear on page refresh in some versions — use session state as fallback, write params on every rerun; encode platform IDs + selected params in URL |
| Sticky filters (persist on rerun) | Streamlit reruns on every widget interaction; filters resetting mid-session destroys usability | LOW | I | `st.session_state` initialization guard (`if "platforms" not in st.session_state: ...`); all filter widgets initialized from session state |

---

### Differentiators (Competitive Advantage)

These are what make PBM2 feel purpose-built for UFS platform analysis rather than a generic query tool.

#### EAV-Specific Browsing

| Feature | Value Proposition | Complexity | Phase | Pain Point | Notes |
|---------|-------------------|------------|-------|------------|-------|
| Browsable parameter catalog (InfoCategory tree sidebar) | Solves the "I don't know what parameter to look for" problem at the root; no other generic tool provides domain-aware navigation | MEDIUM | v1 | D | Render InfoCategory → Item as collapsible tree; clicking an item adds it to the active parameter set; show item count per category |
| Typeahead search over InfoCategory + Item names | Users know a keyword ("write", "speed", "health") but not the exact parameter name | LOW | v1 | D | `st.text_input` with live filter against a cached distinct-values list; highlights matches in catalog |
| Starter-prompt gallery | Bridges the blank-slate problem; non-technical users don't know what to ask first | MEDIUM | v1 | D/S | Curated 6-10 question cards (e.g., "Compare write speed across all Samsung platforms", "Which platforms have health descriptor warnings?"); click-to-run or click-to-edit; stored as YAML config so team can update without code changes |
| LLM-suggests relevant parameters from vague question (parameter proposal step) | Before running SQL, agent shows candidate parameters so user can confirm scope; reduces hallucinated pivots | HIGH | v1 | D/S | Two-step flow: question → proposed parameters → user confirms → SQL runs; uses schema + value-sample context; prevents the LLM from silently choosing wrong InfoCategory |
| Heatmap / conditional formatting view for numeric wide-form results | When comparing 20+ platforms on a numeric parameter (e.g., write speed), color gradient makes outliers instant to spot | MEDIUM | v1 | E | Plotly `imshow` or pandas Styler background gradient; only activates for numeric-coercible columns; toggle switch, not default |
| Platform comparison presets | Power users repeatedly compare the same cohort (e.g., "all Qualcomm SM8550 platforms"); saving this prevents re-selecting 15 items each session | MEDIUM | v2 | E | Stored in `st.session_state` + optional YAML config; named presets displayed as one-click chips above the platform picker |
| Saved parameter sets (named column selections) | Analysts have recurring views ("always show health + write perf params"); named sets prevent re-building every session | MEDIUM | v2 | D | Similar to saved views in BI tools; stored per-session initially, YAML-persisted in v2 |
| "Similar platforms" suggestion | After viewing one platform, surface 2-3 platforms that share the same SoC family or have similar parameter profiles | HIGH | v2 | D/E | Requires similarity computation over pivot matrix; meaningful only after core pivot is solid |
| Deep-link to specific pivot view (platform + parameter set encoded in URL) | Enables Slack handoffs of exact analysis states | MEDIUM | v2 | I | Extends the table-stakes URL-sharing feature with named presets encoded in params |

#### NL Layer Differentiators

| Feature | Value Proposition | Complexity | Phase | Pain Point | Notes |
|---------|-------------------|------------|-------|------------|-------|
| Editable generated SQL (power-user escape hatch) | Technical users can fix a near-correct query rather than restarting; increases trust and reduces friction for edge cases | MEDIUM | v1.x | S | `st.text_area` seeded with generated SQL; "Run edited SQL" button; runs through same readonly/row-cap safety layer; do NOT expose this as the primary interface — it must stay secondary to NL input to preserve the SQL barrier for non-SQL users |
| "Why this query?" explanation | Increases trust; users understand what the agent interpreted their question to mean | MEDIUM | v1.x | S | Second LLM call: "Explain in plain English what this SQL is doing and how it maps to the user's question"; shown in expander alongside the SQL |
| Confidence / quality indicator | Surfaces when the LLM is uncertain so users know to double-check | HIGH | v2 | S | Requires self-evaluation prompt or log-probability analysis; LOW confidence for v1; display only if a reliable signal exists |
| Cross-session query history | Persisted query log so team can see what colleagues have asked; reduces duplicate work | HIGH | v2 | S | Requires server-side persistence (SQLite or a new table); out of scope for v1 which is session-only |

---

### Anti-Features (Deliberately Excluded)

These must be documented to prevent well-meaning scope creep from re-adding them.

| Anti-Feature | Why It Gets Requested | Why It Is Harmful Here | What to Do Instead | Scope Note |
|--------------|----------------------|------------------------|-------------------|-----------|
| Free-form SQL editor as a first-class feature | Technical users want direct SQL access | Re-introduces exactly the SQL barrier the app exists to remove; creates two workflows that diverge; non-SQL users feel the "real" interface is being hidden from them | Provide editable-SQL as a hidden expander, secondary to NL, only visible after a query runs | Explicit out of scope for primary UX |
| Admin data ingestion / Excel upload UI | PMs want to "fix" or "add" data they see is wrong | DB is read-only by contract; introducing a write path changes the security model and operational ownership | Direct data corrections to the upstream system that owns `ufs_data` | Explicit PROJECT.md out of scope |
| Per-user auth / SSO / role-based access | Larger team growth will eventually need this | Shared-credential intranet is the user's explicit v1 choice; SSO adds auth infrastructure complexity that isn't justified yet | Keep `streamlit-authenticator` with shared creds; revisit if team grows or data sensitivity increases | Explicit PROJECT.md out of scope |
| Public internet deployment / OAuth hardening | Demo requests from partners | Changes threat model entirely; requires proper secrets management, rate limiting, multi-tenant isolation | Keep behind company VPN/intranet; share screenshots or exports for external communication | Explicit PROJECT.md out of scope |
| Multi-table / cross-DB joins | Analysts may want to correlate UFS data with other systems | The EAV schema is the entire product scope; cross-table joins require schema discovery, join planning, and ambiguity resolution that is a different product | Build PBM2 well for the one table it owns; cross-system correlation belongs in a BI layer | Explicit PROJECT.md out of scope |
| Global Result type coercion on load | Cleaner data is appealing | Same `Item` is legitimately hex on one platform and decimal on another; global coercion destroys that distinction | Keep coercion lazy and per-query; the display layer decides how to render each value column | Explicit PROJECT.md architectural decision |
| Infinite scroll / server-side pagination of the pivot grid | Feels like better UX for large tables | EAV pivot requires the full result set to be pivoted client-side before display; incremental streaming doesn't compose with `pandas.pivot_table`; row cap (200) makes this moot | Enforce the agent row cap (200 rows) and add platform/parameter pre-filters so result sets fit in memory before pivoting | Architectural constraint |
| Real-time auto-refresh / live data | Dashboards often have this | `ufs_data` is populated in batch by an upstream pipeline, not a stream; auto-refresh adds complexity and unnecessary DB load for no user value | Show data freshness timestamp ("Data as of: [last row ingestion timestamp]") instead | Not a data-source capability |

---

## EAV Pivot UX Patterns: What Works, What Fails

This section is specific to the long-form EAV → wide-form pivot transformation that is PBM2's core rendering challenge.

### Patterns That Work

**Pre-filter before pivot, not after.** With 100k+ rows and 100+ parameters, pivoting the full table then filtering is slow and produces unreadable matrices. Always filter platforms AND parameters in SQL, return a narrow result set, then pivot. The platform picker + parameter picker together act as the required pre-filter gate.

**`aggfunc="first"` with visible duplicate warning.** The schema has no UNIQUE constraint on `(PLATFORM_ID, InfoCategory, Item)`. Using `first` is correct and safe, but a row-count annotation ("3 duplicate cells collapsed") prevents users from thinking data is missing.

**LUN-scoped parameter display.** `lun_info`, `lun_unit_descriptor`, `lun_unit_block` items have `N_` prefixes (e.g., `0_WriteProt`, `1_WriteProt`). In the wide pivot, group these under a collapsible "LUN N" sub-header or use a two-level column index; flat display produces visually overwhelming repeat columns.

**DME `_local` / `_peer` split.** Some `Result` values pack both as `local=...,peer=...`. Parse and display as two sub-columns rather than raw packed string. Defer to v1.x — raw display is acceptable for v1.

**Heatmap for numeric parameters.** When comparing a numeric metric (e.g., max write speed) across 20+ platforms, color gradient encoding spots outliers in under one second. Text-only comparison across 20 rows requires line-by-line reading. Activate only when column is numeric-coercible; show raw value in cell, color as background.

**Sort pivot by a specific column.** "Show me all platforms sorted by write speed descending" is the most common ad-hoc comparison. Streamlit native `st.dataframe` supports header-click sort — ensure this is preserved.

**Column width management.** UFS `Result` values can be long (whitespace-delimited number blobs); default column widths make the grid unreadable. Use `column_config` to set a reasonable `max_column_width` and enable cell wrap or truncation with tooltip.

**Category tabs / section headers.** When viewing a single platform's full profile, grouping by InfoCategory (using `st.tabs` or `st.expander`) makes the 100+ parameter list navigable. Flat alphabetical display is unusable.

### Patterns That Fail

**Pivoting without pre-filters.** If a user selects no parameters, the pivot produces a matrix with 100+ columns. At 100 platforms × 100 parameters = 10,000 cells, `st.dataframe` renders slowly and the result is unreadable. Enforce a minimum parameter selection (at least 1) or at least warn and cap columns.

**Showing raw `None`/`"None"`/empty strings as distinct values.** Users interpret `None` (Python object), `"None"` (string), `NULL` (SQL), and `""` (empty string) differently but they all mean "not measured here." Mixing them in the pivot makes it look like the DB has data inconsistencies. Normalize to a single `—` display sentinel.

**Attempting frozen/pinned columns with native `st.dataframe`.** Native Streamlit does not support pinning a `PLATFORM_ID` column while scrolling horizontally through 100 parameters. Without this, the platform identity is lost when scrolling right. Mitigation: keep `PLATFORM_ID` as the DataFrame index (which Streamlit renders frozen in the index position) and rely on platform count being small enough that users can still navigate. If this proves insufficient, `streamlit-aggrid` supports true column pinning.

**Alphabetical flat parameter list.** 100+ parameters listed alphabetically offers no semantic grouping. Users searching for "write performance" have no clustering signal. Always group by InfoCategory.

**Rendering the full `ufs_data` table without filters.** 100k+ rows cannot be pivot-displayed in a browser. Always require at least platform selection or parameter selection before query runs; never allow the "show everything" query through the UI.

**Displaying error strings (`cat: /sys/...`) as values in heatmap.** Non-numeric values silently break color encoding. Always filter or null-out error strings before numeric coercion; mixed columns should fall back to text display, not crash.

---

## Feature Dependencies

```
Platform Picker
    └──requires──> DB connection + distinct PLATFORM_ID query
                       └──requires──> SQLAlchemy adapter (already scaffolded)

Parameter Picker (InfoCategory tree)
    └──requires──> DB connection + distinct InfoCategory/Item query
    └──enhances──> Wide-Form Pivot Grid (controls which columns appear)

Wide-Form Pivot Grid
    └──requires──> Platform Picker (at least one platform selected)
    └──requires──> Parameter Picker (at least one parameter selected)
    └──requires──> Result Normalization (missing sentinel)
    └──enhances──> Heatmap View (conditional formatting over pivot data)
    └──enhances──> Excel/CSV Export (exports the pivot output)

Typeahead Search Bar
    └──requires──> Cached distinct InfoCategory + Item list
    └──enhances──> Parameter Picker (filters the tree)

Starter Prompt Gallery
    └──enhances──> NL Question Input (pre-fills the text area)
    └──enhances──> Parameter Picker (can pre-select params for browsing questions)

NL Question Input
    └──requires──> LLM adapter (OpenAI or Ollama)
    └──requires──> DB connection
    └──enhances──> Wide-Form Pivot Grid (NL result feeds back into grid view)

LLM Parameter Proposal Step
    └──requires──> NL Question Input
    └──requires──> Cached schema context (InfoCategory + Item list)
    └──enhances──> Parameter Picker (confirms proposed params before SQL runs)

Show Generated SQL
    └──requires──> NL Question Input (something must generate SQL first)

Editable Generated SQL
    └──requires──> Show Generated SQL
    └──conflicts──> "NL is the primary interface" principle (must stay secondary)

Query History (session)
    └──requires──> NL Question Input
    └──requires──> st.session_state persistence

Shareable URL
    └──requires──> st.query_params (Streamlit >= 1.30, already met by requirements.txt >= 1.40)
    └──enhances──> Platform Picker (encodes selected platforms)
    └──enhances──> Parameter Picker (encodes selected params)

LLM Plain-Text Summary
    └──requires──> NL Question Input + result table
    └──requires──> LLM adapter

Heatmap View
    └──requires──> Wide-Form Pivot Grid
    └──requires──> Numeric-coercible column detection

Platform Comparison Presets (v2)
    └──requires──> Platform Picker
    └──enhances──> Shareable URL (can encode preset name)

Saved Parameter Sets (v2)
    └──requires──> Parameter Picker

Cross-session Query History (v2)
    └──requires──> Server-side persistence (new dependency, not yet scaffolded)
    └──conflicts──> Single-user session model assumed in v1
```

---

## MVP Definition

### Launch With (v1)

Core browsing must work without the NL layer. NL layer must be usable but is allowed to fail gracefully.

**Browsing (non-negotiable):**
- [ ] Platform picker with typeahead — without this, users cannot start
- [ ] Parameter catalog (InfoCategory tree) + typeahead search — resolves Discovery pain
- [ ] Wide-form pivot grid with sort + column hide — resolves EAV pain
- [ ] Single-platform detail view grouped by InfoCategory — resolves EAV pain
- [ ] Result normalization (missing sentinel) — prevents misleading display
- [ ] Row count display — confirms filter is working
- [ ] Loading + empty + error states — basic polish required for internal adoption
- [ ] Excel / CSV export — analysts will not use the tool without this
- [ ] Sticky filters (session state) — without this, every widget interaction resets work

**NL Layer (must work for the three query shapes):**
- [ ] NL question input — the feature exists
- [ ] LLM model switcher (OpenAI/Ollama sidebar) — already scaffolded; must be wired
- [ ] Show generated SQL (collapsed expander) — required for trust
- [ ] Regenerate button — required for stochastic LLM tolerance
- [ ] Session query history — required for iteration
- [ ] LLM plain-text summary — direct value-add alongside results
- [ ] LLM parameter proposal step (question → proposed params → confirm → SQL) — resolves Discovery pain for NL users; also prevents silent wrong-parameter queries
- [ ] Agent safety guardrails (readonly, row cap, timeout) — already in config; must be wired and visible

**Sharing:**
- [ ] Starter-prompt gallery (6-10 curated questions, YAML-backed) — resolves blank-slate onboarding problem
- [ ] Shareable URL via `st.query_params` — enables Slack handoffs

### Add After Validation (v1.x)

Add these once v1 is in use and users report the specific gap.

- [ ] Editable generated SQL — add when technical users report NL not being precise enough; keep as secondary hidden feature
- [ ] "Why this query?" explanation — add when users express distrust of NL results
- [ ] Heatmap / conditional formatting — add when users ask "can I see the outliers faster?"
- [ ] DME `_local`/`_peer` split display — add when users complain about packed value readability
- [ ] LUN sub-header grouping in pivot — add when users report column list confusion for LUN-heavy comparisons

### Future Consideration (v2+)

Defer until v1 is validated and these specific user requests emerge.

- [ ] Platform comparison presets — trigger: users repeatedly re-selecting the same cohort
- [ ] Saved parameter sets — trigger: users describing "my regular view" verbally
- [ ] Cross-session query history — trigger: team coordination need, requires server-side persistence design
- [ ] "Similar platforms" suggestion — trigger: users asking "what else is like this?"; requires similarity computation
- [ ] Deep-link to named preset — trigger: URL sharing becomes complex enough to need named states
- [ ] Confidence / quality indicator for NL results — trigger: users wanting to know when to trust vs verify; requires reliable LLM self-evaluation signal

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Pain Point |
|---------|------------|---------------------|----------|------------|
| Platform picker + typeahead | HIGH | LOW | P1 | E |
| Parameter catalog (InfoCategory tree) | HIGH | MEDIUM | P1 | D |
| Wide-form pivot grid | HIGH | MEDIUM | P1 | E |
| Result normalization | HIGH | MEDIUM | P1 | E |
| Loading / empty / error states | HIGH | LOW | P1 | I |
| Excel/CSV export | HIGH | LOW | P1 | E/S |
| Sticky filters (session state) | HIGH | LOW | P1 | I |
| NL question input | HIGH | LOW | P1 | S |
| Show generated SQL | HIGH | LOW | P1 | S |
| Regenerate button | HIGH | LOW | P1 | S |
| Session query history | MEDIUM | LOW | P1 | S |
| LLM model switcher | MEDIUM | LOW | P1 | I |
| Starter-prompt gallery | HIGH | MEDIUM | P1 | D/S |
| LLM parameter proposal step | HIGH | HIGH | P1 | D/S |
| LLM plain-text summary | MEDIUM | MEDIUM | P1 | S |
| Shareable URL | MEDIUM | MEDIUM | P1 | I |
| Single-platform detail view | MEDIUM | LOW | P1 | E |
| Row count display | MEDIUM | LOW | P1 | I |
| Agent safety guardrails (visible) | MEDIUM | LOW | P1 | I |
| Heatmap / conditional formatting | HIGH | MEDIUM | P2 | E |
| Editable generated SQL | MEDIUM | MEDIUM | P2 | S |
| "Why this query?" explanation | MEDIUM | MEDIUM | P2 | S |
| LUN sub-header grouping | MEDIUM | MEDIUM | P2 | E |
| Platform comparison presets | MEDIUM | MEDIUM | P3 | E |
| Saved parameter sets | MEDIUM | MEDIUM | P3 | D |
| Cross-session query history | LOW | HIGH | P3 | S |
| "Similar platforms" suggestion | LOW | HIGH | P3 | D/E |
| Confidence indicator | LOW | HIGH | P3 | S |

---

## Pain Point — Feature Mapping Summary

### Discovery (D): Users don't know which parameter corresponds to their question

Primary resolution: Parameter catalog with InfoCategory tree + typeahead search
Supporting: Starter-prompt gallery, LLM parameter proposal step
Secondary: "Similar platforms" (v2), Saved parameter sets (v2)

### EAV Confusion (E): Long-form rows are unreadable; users expect wide form

Primary resolution: Wide-form pivot grid (the core rendering primitive)
Supporting: Result normalization, column hiding, single-platform detail view, heatmap
Secondary: Platform comparison presets (v2), LUN sub-header grouping (v1.x)

### SQL Barrier (S): Non-technical users cannot write SQL at all

Primary resolution: NL question input + agent safety (removes the barrier)
Supporting: Show generated SQL, regenerate, session history, LLM summary, starter prompts
Secondary: Editable SQL (v1.x — for technical users who want precision without full SQL), "Why this query?" (v1.x)

---

## Sources

- Streamlit official docs, `st.dataframe` column configuration API: https://docs.streamlit.io/develop/api-reference/data/st.dataframe
- Streamlit `st.query_params` documentation and known issues (2025): https://docs.streamlit.io/develop/api-reference/caching-and-state/st.query_params
- EAV model and pivot reporting patterns: https://softwarepatternslexicon.com/102/6/15/
- NL2SQL system design and transparency patterns (2025): https://medium.com/@adityamahakali/nl2sql-system-design-guide-2025-c517a00ae34d
- Complex data table UX design (Stephanie Walter): https://stephaniewalter.design/blog/essential-resources-design-complex-data-tables/
- Filter UX patterns (Pencil & Paper): https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-filtering
- streamlit-aggrid for frozen column support: https://github.com/PablocFonseca/streamlit-aggrid
- Production NL-to-SQL trust and transparency (Uber QueryGPT): https://www.uber.com/us/en/blog/query-gpt/
- TailorSQL query workload patterns (VLDB 2025): https://arxiv.org/html/2505.23039v1

---

*Feature research for: PBM2 — Streamlit intranet EAV data browsing + NL-to-SQL tool*
*Researched: 2026-04-23*
