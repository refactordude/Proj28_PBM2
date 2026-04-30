---
phase: 01-overview-tab-auto-discover-platforms-from-html-files
type: research
created: 2026-04-30
domain: HTML-scraped joint-validation listing on FastAPI/Bootstrap/HTMX (Confluence-export ingestion + iframe sandbox + AI summary reuse)
confidence: HIGH
---

# Phase 1: Overview Tab — Auto-discover Joint Validations from HTML Files — Research

**Researched:** 2026-04-30
**Domain:** HTML scraping (BeautifulSoup4) + Starlette StaticFiles + iframe sandbox + reuse of v2.0 Phase 5 grid/filter/sort scaffolding + AI Summary route adaptation.
**Confidence:** **HIGH** for stack, patterns, security boundaries, file mapping, and view-model shape (verified against installed `.venv` + on-disk Phase 5 sources). MEDIUM-HIGH for iframe sandbox attribute set (verified against MDN/web.dev current guidance, but exact Confluence-export-HTML shape is inferred — no real sample available). LOW only for "what does Confluence Cloud 2026 emit when you click Export → HTML" because the user has no sample on disk.

---

## Summary

This phase is a **scoped rewrite, not greenfield**. The Overview tab's data source switches from `config/overview.yaml` + `content/platforms/*.md` frontmatter → globbed `content/joint_validation/<numeric_id>/index.html` parsed with BeautifulSoup4. Every other moving part — sortable Bootstrap table, six picker-popover filters, URL round-trip with `HX-Push-Url`, mtime-keyed memoization, AI Summary modal, OOB count + filter-badge swaps, jinja2-fragments `block_names=[...]` rendering, `picker_popover` macro, `popover-search.js` D-15b debounce — is byte-identical reuse from Phase 5. The new code surface is small (3 services + 1 router + 2 templates + 1 fixture), the deletion surface is large (4 services + 3 templates + 5 tests + 1 yaml + 1 route).

The four risk concentrations the planner needs to allocate verification budget against:

1. **BS4 selector fragility on Confluence's two table shapes** — `<th><strong>Field</strong></th><td>value</td>` is the documented Page-Properties output, but exports also produce `<p><strong>Field</strong>: value</p>` rows AND occasionally wrap labels inside `<a>` (anchor links to glossary). Selector must walk to the structural sibling cell, not just the textual next sibling.
2. **iframe sandbox + same-origin trade-off** — `sandbox="allow-same-origin"` (no `allow-scripts`) is the correct posture for embedding Confluence-exported HTML: inline styles render, scripts are blocked, and the parent page can navigate the iframe. Adding `allow-scripts` alongside `allow-same-origin` is the single most-warned-against combination in MDN/web.dev because it lets the framed document remove the sandbox attribute.
3. **Path traversal at the static mount boundary** — `app.mount("/static/joint_validation", StaticFiles(directory="content/joint_validation"))` is safe in Starlette 1.0 (the CVE-2023-29159 `commonprefix`→`commonpath` fix shipped in 0.27, and we run 1.0). But the safe minimal config requires explicit `html=False`, `follow_symlink=False`, and the `^\d+$` directory-name guard at the application layer — these are belt-and-suspenders that the planner must script as acceptance grep.
4. **mtime cache on copy-tree drop pattern** — D-JV-09's "drop folder" workflow means `cp -r` writes files in arbitrary order; a request that arrives mid-copy could parse a partially-written `index.html`. The mtime-keyed memo correctly invalidates after the copy completes (next mtime tick), but the *first* read after a partial drop may still cache a malformed parse. Acceptable per D-JV-05 (missing fields → blank), but worth noting.

**Primary recommendation:** Treat this phase as **assembly + targeted parser invention**. Reuse Phase 5's grid_service / overview_filter / picker_popover / popover-search.js / `_build_overview_url` / OOB block conventions byte-stable. Invent only what is genuinely new: (a) the `joint_validation_parser.py` module wrapping BS4 with two locator strategies + Korean-aware label matching, (b) the `joint_validation_store.py` module replacing yaml with directory glob + mtime-keyed memo, (c) the `joint_validation/detail.html` template with the iframe sandbox shell, and (d) the StaticFiles mount call in `main.py`. Everything else is mechanical translation of `OverviewRow` → `JointValidationRow` and `platform_id` → `confluence_page_id`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

> Copied verbatim from `.planning/phases/01-overview-tab-auto-discover-platforms-from-html-files/01-CONTEXT.md` — these are LOCKED. Do not relitigate.

### Locked Decisions (D-JV-01 .. D-JV-17)

**Source & discovery:**
- **D-JV-01** — Tab scope: REPLACE Overview's Platform list with Joint Validation list. Top-nav URL stays `/overview`; visible label changes from "Overview" to **"Joint Validation"**. Browse + Ask tabs untouched.
- **D-JV-02** — Source of truth: `content/joint_validation/<numeric_id>/index.html`. Discovery is `glob('content/joint_validation/*/index.html')`. Directory name MUST be lowercase-underscore `joint_validation/` (NOT `Joint Validation/`, NOT `joint-validation/`). Reason: matches Python module-naming convention; avoids URL-encoding spaces in static-mount path.
- **D-JV-03** — Folder name validation: `^\d+$` (digits only) AND must contain a readable `index.html`. Anything else (`_drafts`, `README`, `.DS_Store`, partial folders) silently skipped. This is also the path-traversal backstop for the static mount.
- **D-JV-04** — Metadata extraction: parse `<strong>Field</strong>` rows directly from `index.html` with BeautifulSoup4 (new dependency). 13 fields: `title` (first `<h1>`), `status`, `customer`, `model_name`, `ap_company`, `ap_model`, `device`, `controller`, `application`, `assignee` (from `<strong>담당자</strong>` Korean label), `start`, `end`, `link` (`<a href>` inside the cell adjacent to `<strong>Report Link</strong>`). First match wins on duplicate labels. Locator strategy is Claude's discretion; needs to handle BOTH `<th><strong>…</strong></th><td>value</td>` AND `<p><strong>…</strong>: value</p>`.
- **D-JV-05** — Missing field → blank cell `""` (NOT em-dash `—`). DELIBERATE departure from Phase 5 D-OV-09. Title fallback when `<h1>` missing: render `confluence_page_id` so the row stays clickable.

**Cleanup:**
- **D-JV-06** — DELETE: `config/overview.yaml`, `app_v2/services/overview_store.py`, `overview_filter.py`, `overview_grid_service.py`, `templates/overview/_filter_bar.html`, `_grid.html`, `index.html` (full rewrite, not rename), `OverviewEntity` / `DuplicateEntityError`, all v2.0 tests for deleted units. KEEP: `content/platforms/*.md`, `content_store.py`, `routers/platforms.py`, `/platforms/<PID>` detail/edit/preview routes.
- **D-JV-07** — DELETE `POST /overview/add`. No "Add Joint Validation" affordance — drop-folder workflow only.

**Behavior:**
- **D-JV-08** — Cache: mtime-keyed in-process memo per `index.html`, keyed by `(confluence_page_id, mtime_ns)`. Bounded to `len(found_pages)`. Glob NOT cached (re-glob every request).
- **D-JV-09** — Onboarding: drop-folder workflow only. No in-app form, no Refresh button, no Confluence import wizard.
- **D-JV-10** — Default sort: `start desc`, tiebreaker `confluence_page_id ASC`. Empty/blank/malformed `start` sorts to END regardless of asc/desc. Sort cycles asc → desc → asc on header click. Date columns parse `YYYY-MM-DD` for sort but render the original string.
- **D-JV-11** — Six popover-checklist filters (same set as Phase 5): `status`, `customer`, `ap_company`, `device`, `controller`, `application`. Reuse `picker_popover` macro AS-IS. D-15b auto-commit + 250ms debounce + form-association + OOB filter-badge swap all carry forward. 12 sortable columns (the 13 fields minus `link`); Action column NOT sortable; Title IS sortable.

**URL & routing:**
- **D-JV-12** — Routes: `GET /` and `GET /overview` listing stays. `POST /overview/grid` returns blocks `["grid", "count_oob", "filter_badges_oob"]` with `HX-Push-Url` to canonical `/overview?...`. NEW: `GET /joint_validation/<numeric_id>` detail page — properties table + `<iframe sandbox="allow-same-origin">` with `src=/static/joint_validation/<id>/index.html`.
- **D-JV-13** — Static mount: `app.mount("/static/joint_validation", StaticFiles(directory="content/joint_validation"), name="joint_validation_static")` in `app_v2/main.py`.
- **D-JV-14** — URL state shape (unchanged from D-OV-13): `/overview?status=A&status=B&customer=X&ap_company=Y&device=Z&controller=W&application=V&sort=start&order=desc`. Repeated keys for multi-value filters; `sort` and `order` single-valued.

**UI:**
- **D-JV-15** — Row actions: TWO buttons (Report Link + AI Summary). Bootstrap `btn-sm`. (1) Report Link: opens `link` in new tab `target="_blank" rel="noopener noreferrer"`; URL sanitizer drops `javascript:` / `data:` / `vbscript:` / `file:` / `about:`; promotes bare domains to `https://`. Disabled when `link` empty. (2) AI Summary: same modal pattern as Phase 5 D-OV-15. Title cell IS the link to detail page (no separate View button).
- **D-JV-16** — AI Summary input pre-processing: `<script>`, `<style>`, `<img>` decomposed; `BeautifulSoup.get_text(separator='\n')`; collapse blank lines. `nl_service.max_context_tokens=30000` (actually `AgentConfig.max_context_tokens` per code review) is the final clamp. Reuse Phase 3 `summary_service` pattern (TTLCache + Lock + always-200) with the prompt re-worded for "Joint Validation page".
- **D-JV-17** — Empty state: render chrome + filter bar + popovers (disabled — no values to filter on); single full-width `<tbody>` row with helper text "**No Joint Validations yet.** Drop a Confluence export at `content/joint_validation/<page_id>/index.html`"; count caption "0 entries".

### Claude's Discretion
- BeautifulSoup4 selector strategy (locator function shape — `find_parent('tr')` vs. `find_next_sibling('td')` etc.).
- Date parsing fallback (treat malformed/missing as blank for sort; render raw string in cell).
- AI Summary prompt copy (carry concise, structured tone from Platform AI Summary).
- Sample HTML fixture for tests (user has no real sample to provide).
- Top-nav label color/icon (Bootstrap defaults).

### Deferred Ideas (OUT OF SCOPE)
- In-app Confluence import (URL paste → fetch HTML → save).
- Date-range filter on Start / End.
- Filter on Title / Model Name / Assignee.
- Bulk-select / batch operations.
- Repurposing `config/overview.yaml` as a pin/hide override.
- Manual 'Refresh' button.
- Live Confluence API metadata fetch.
- Removing `content/platforms/*.md` or `/platforms/<PID>` detail page (Browse + Ask still need PLATFORM_IDs).
</user_constraints>

---

## Project Constraints (from CLAUDE.md)

> Extracted directly from project CLAUDE.md — same authority as locked decisions; planner must verify compliance.

| Directive | Source line | Implication for this phase |
|---|---|---|
| **Stack pinned**: FastAPI + Bootstrap 5 + HTMX + Jinja2 + jinja2-fragments + SQLAlchemy + pandas + Pydantic v2 + python-dotenv (v2.0 milestone shipped 2026-04-29 tag `v2.0`) | "Constraints" line 1 | DO NOT add Streamlit, LangChain, AgGrid, Vanna, LiteLLM, or React. Phase 1 is a v2.0-stack-only addition. New deps allowed: `beautifulsoup4`, optionally `lxml`. |
| **Read-only DB; ufs_data only** | "Constraints", "Single-table EAV MySQL (`ufs_data`), read-only" | Joint Validation is OFF the DB entirely — no SQLAlchemy in this phase's new code. No `PLATFORM_ID` lookups, no `ufs_data` joins. |
| **Sync `def` routes (FastAPI threadpool dispatch — INFRA-05)** | CONTEXT.md `<code_context>` line 251 | New router and the static mount must NOT use `async def` for the route handlers. BS4 parsing is CPU-bound and stays out of the event loop because of the sync-def + threadpool. (StaticFiles itself is async-ASGI, but the mount API is unaffected.) |
| **GSD Workflow Enforcement** | "GSD Workflow Enforcement" | Edits go through `/gsd-execute-phase` after planning. The research phase produces this file; the planner produces PLANs; execution then edits the codebase. |
| **NEVER hand-roll PLATFORM_ID parsing** (project convention) | "Naming conventions inside `Item`" | Joint Validation IDs are independent of `PLATFORM_ID`; no parser overlap. Existing `app_v2/data/platform_parser.py` is NOT reused for this phase. |
| **XSS defense via Jinja2 explicit-escape `\| e`** | Existing templates audit-grep: "the autoescape-bypass filter and inline scripts are banned by acceptance grep" (in `_grid.html`, `index.html`) | New templates (`joint_validation/detail.html`, rewritten `overview/*.html`) MUST use `\| e` explicit-escape on every dynamic value. The `\| safe` filter is restricted; the only legitimate use in this phase is `summary_html \| safe` from the AI Summary success template (LLM markdown output → `MarkdownIt('js-default')` → safe HTML). |
| **`yaml.safe_load` only; `yaml.load` is banned by Phase 5 invariant test** | `tests/v2/test_phase05_invariants.py::test_content_store_uses_yaml_safe_load_only` | Not relevant to this phase (no YAML in new code) but the invariant test must continue to pass — i.e., DO NOT introduce `yaml.load` to satisfy any "load Confluence export metadata" temptation. |
| **All NL invocations route through `app/core/agent/nl_service.run_nl_query`** | Phase 6 D-20 carry-forward | AI Summary path uses `summary_service`, which uses the OpenAI SDK directly — does NOT pass through `nl_service`. The `max_context_tokens=30000` clamp lives on `AgentConfig`, not `nl_service`. CONTEXT.md D-JV-16 says "the existing `nl_service.max_context_tokens=30000` cap is the final clamp" — verify with planner whether this is meant to (a) be enforced by re-using `AgentConfig.max_context_tokens` as a constant in summary_service input pre-processing, or (b) is shorthand for "OpenAI SDK's `max_tokens` parameter caps output". My read: it's the AGENT context cap, not the summary route cap; the summary route already has `cfg.max_tokens` for output. The planner should confirm whether D-JV-16 means we add a 30k-token *input* truncation, since the existing summary_service does NOT truncate input. **[ASSUMED]** — input truncation is a new step the planner must call out. |

---

<phase_requirements>
## Phase Requirements

> No REQUIREMENTS.md row exists for Phase 1 (the project is between milestones; ROADMAP.md says "TBD"). Per the orchestrator's instruction, must-haves are derived directly from CONTEXT.md decisions D-JV-01..17. The planner SHOULD copy this table into PLANs as the requirement-trace surface (each PLAN's must_haves should reference these IDs).

| ID | Description | Research Support |
|---|---|---|
| JV-01 | Tab content is REPLACED: Overview shows Joint Validation rows; nav label flips to "Joint Validation"; URL `/overview` unchanged. | §"Phase 5 Reuse Map" identifies `templates/base.html` line 38-43 as the nav-label edit point; `routers/overview.py` GET `/` + GET `/overview` route bodies stay (only context dict changes). |
| JV-02 | Discovery glob: `content/joint_validation/*/index.html`; directory name regex `^\d+$`; non-matching folders silently skipped. | §"Don't Hand-Roll" — use `pathlib.Path.glob('joint_validation/*/index.html')` + `re.match(r'^\d+$', dir.name)`. Re-glob on every request (D-JV-08); typical < 1ms for ~100 dirs on local SSD. |
| JV-03 | Parse 13 fields per `index.html` with BeautifulSoup4: title (first `<h1>`) + 12 strong-label rows including Korean `담당자`. First match wins on duplicate labels. Missing fields → blank `""`. | §"BS4 Selector Strategy" gives the recommended locator; §"Korean Label Handling" confirms BS4 4.14.x is UTF-8-clean. |
| JV-04 | Mtime-keyed in-process memo per `index.html`, keyed by `(confluence_page_id, mtime_ns)`. Bounded to `len(found_pages)`. Glob NOT cached. | §"Mtime Cache" — pattern is byte-identical to Phase 5 `read_frontmatter` cache; same module-level dict, same invalidation semantics. |
| JV-05 | Six popover-checklist filters (status, customer, ap_company, device, controller, application). Reuse `picker_popover` macro AS-IS with `form_id='overview-filter-form'`, `hx_post='/overview/grid'`, `hx_target='#overview-grid'`. | §"Phase 5 Reuse Map" confirms macro signature accepts these as kwargs (`browse/_picker_popover.html` line 50). |
| JV-06 | 12 sortable columns (all data fields except `link`); default `start desc` tiebreaker `confluence_page_id ASC`; empties to END regardless of order; date columns parse YYYY-MM-DD for sort, render raw. | §"Phase 5 Reuse Map" — `_sort_rows` two-pass stable sort in `overview_grid_service.py` lines 213-276 is reused verbatim (rename platform_id → confluence_page_id). |
| JV-07 | URL round-trip: query keys `status[]`, `customer[]`, `ap_company[]`, `device[]`, `controller[]`, `application[]`, `sort`, `order`; canonical URL pushed via `HX-Push-Url`. | §"Phase 5 Reuse Map" — `_build_overview_url` in `routers/overview.py` lines 155-181 reused verbatim. |
| JV-08 | `POST /overview/grid` returns block_names=`["grid", "count_oob", "filter_badges_oob"]`; HX-Push-Url to canonical `/overview?...`. | §"Phase 5 Reuse Map" — exact pattern in `routers/overview.py` line 353. |
| JV-09 | Detail page `GET /joint_validation/<numeric_id>` — properties table + `<iframe sandbox="allow-same-origin">` with `src=/static/joint_validation/<id>/index.html`. | §"iframe Sandbox" — locked attribute set is `sandbox="allow-same-origin"` (no `allow-scripts`); inline styles render natively without script permission. |
| JV-10 | Static mount `app.mount("/static/joint_validation", StaticFiles(directory="content/joint_validation"), name="joint_validation_static")` in `app_v2/main.py` lifespan-time setup. | §"FastAPI StaticFiles Path-Traversal Defense" — Starlette 1.0.0 (installed) post-CVE-2023-29159; safe minimal config = `html=False, follow_symlink=False` (defaults); rely on `os.path.commonpath` + `realpath` + `^\d+$` app-layer guard. |
| JV-11 | AI Summary route reuses Phase 3 `summary_service.py` pattern (TTLCache + Lock + always-200). Pre-process: BS4 decompose `<script>`, `<style>`, `<img>`; `get_text(separator='\n')`; collapse blank lines. | §"AI Summary Reuse" — `summary_service` accepts a content string; new shim function `get_or_generate_jv_summary(confluence_page_id, cfg, jv_dir)` adapts the input source. |
| JV-12 | Two row buttons: Report Link (URL-sanitized; opens `target="_blank" rel="noopener noreferrer"`); AI Summary (modal, Phase 5 D-OV-15 pattern). Title cell is link to detail page. | §"Phase 5 Reuse Map" — Link button pattern at `templates/overview/_grid.html` lines 74-93; AI Summary button lines 94-107; modal in `index.html` lines 160-194. |
| JV-13 | Empty state: render chrome + disabled filter popovers + single full-width helper-text row + "0 entries" caption. | §"Phase 5 Reuse Map" — Phase 5 has the empty-state pattern at `_grid.html` lines 116-128; new copy diverges per D-JV-17. Picker disabled state already exists in macro (`disabled=True` kwarg, line 50). |
| JV-14 | DELETE `config/overview.yaml`, `overview_store.py`, `overview_filter.py`, `overview_grid_service.py`, three `templates/overview/*.html`, `OverviewEntity`, `DuplicateEntityError`, `POST /overview/add`, related v2.0 tests. KEEP `content/platforms/*.md`, `content_store.py`, `routers/platforms.py`, `/platforms/<PID>` routes. | §"Cleanup Targets" enumerates exact paths. The Phase 5 invariant test at `tests/v2/test_phase05_invariants.py` will need rewriting under a Phase 1 namespace. |
| JV-15 | Add dependency: `beautifulsoup4>=4.12,<5.0` to `requirements.txt`. Optional: `lxml>=5.0,<7.0` for parser backend speed/tolerance. | §"Standard Stack" — version verification confirms 4.14.3 is current stable (released 2025-11-30); 4.12 lower bound matches Phase 5 pin-style. |
</phase_requirements>

---

## Standard Stack

### Core (new dependencies for this phase)

| Library | Recommended pin | Verified version | Purpose | Why standard |
|---|---|---|---|---|
| **beautifulsoup4** | `>=4.12,<5.0` | 4.14.3 (released 2025-11-30) [VERIFIED: PyPI 2026-04-30] | HTML parser for the 13-field extraction (D-JV-04). | The locked library per CONTEXT.md. BS4 has been the de-facto Python HTML scraper since 2012; it's the *only* mature option that handles malformed HTML AND has a stable, ergonomic API for tag/sibling navigation. lxml-only would be faster but more brittle on Confluence's occasionally-broken markup; html5lib alone would be too slow. BS4 *uses* one of these as the backend — that's the right separation. |
| **lxml** *(optional but recommended)* | `>=5.0,<7.0` | 6.1.0 (released 2026-04-17) [VERIFIED: PyPI 2026-04-30] | Backend parser for BS4. | BS4-with-lxml is 2-10x faster than BS4-with-html.parser AND has better error recovery for broken HTML [CITED: lxml.de/elementsoup.html]. The downside is a C-extension wheel (manylinux wheels exist for Linux x86_64 / aarch64; install is single-step on the project's Linux 6.17 / Python 3.13 environment). For an internal tool with ~100 files re-parsed only on mtime change, the speed delta is small in absolute terms (sub-millisecond per file) but the malformed-HTML resilience pays off when Confluence emits unclosed tags. **Recommendation: include lxml as a hard dep, not optional** — failing back to `html.parser` at runtime if lxml is missing creates two parsing-behavior regimes that tests can't easily cover. |
| **No** new framework / new ORM / new HTTP client | — | — | — | All other libraries needed (FastAPI 0.136.1, Pydantic 2.13.3, Starlette 1.0.0, Jinja2-fragments, cachetools, openai SDK) are already in `requirements.txt` from v2.0 — verified via `.venv` introspection [VERIFIED]. |

### Supporting (already installed; no new install)

| Library | Pinned version | Purpose | Use case |
|---|---|---|---|
| FastAPI | 0.136.1 [VERIFIED: .venv] | Routing | New `joint_validation` router (or extend `overview.py`); `app.mount(...)` for static. |
| Starlette | 1.0.0 [VERIFIED: .venv] | StaticFiles, TemplateResponse | `StaticFiles(directory=..., html=False, follow_symlink=False)`. |
| Pydantic v2 | 2.13.3 [VERIFIED: .venv] | View-model | `JointValidationRow` + `JointValidationGridViewModel` BaseModels. |
| jinja2-fragments | (installed; lacks `__version__`) [VERIFIED: .venv import-only] | Block-name fragment rendering | `templates.TemplateResponse(request, "overview/index.html", ctx, block_names=["grid", "count_oob", "filter_badges_oob"])`. |
| cachetools | 7.0+ | TTLCache | `summary_service` already uses it; reuse. |
| openai | 1.50+ | OpenAI + Ollama LLM client | `summary_service._build_client` already wires both via `base_url` switch. |
| markdown-it-py | 3.0+ | Markdown→HTML | LLM summary output uses `render_markdown` (`MarkdownIt('js-default')`) — XSS-safe. |
| pytest | 9.0.3 [VERIFIED: .venv] | Test runner | Existing `tests/v2/conftest.py`; new test files follow that layout. |
| FastAPI TestClient | (installed) [VERIFIED: .venv] | Route integration tests | Pattern: `tests/v2/test_overview_routes.py`. |

### Alternatives Considered (and rejected)

| Instead of | Could use | Tradeoff (why we don't) |
|---|---|---|
| BeautifulSoup4 | lxml directly with `lxml.html.fromstring` + XPath | XPath is more terse but less forgiving on malformed HTML; BS4's `find_all`/`find_next_sibling` API is what the implementer reaches for first. Locked by CONTEXT.md anyway. |
| BeautifulSoup4 | parsel / Scrapy selectors | Adds Scrapy's transitive deps for one-off parsing. No benefit. |
| BeautifulSoup4 | regex on the raw HTML | Would-be appealingly small but the `<th><strong>Field</strong></th><td>value</td>` pattern has too many whitespace / nested-tag variations. `[ASSUMED]` regex would limp on the second-shape `<p><strong>…</strong>: …</p>` fallback. Don't hand-roll. |
| html.parser (stdlib) backend | lxml backend | html.parser ships with Python (no install) but is slower and more strict — common Confluence quirks (unclosed `<br>`, stray `&` in attributes) trip it. Recommendation: ship `lxml` as a real dep. |
| New `joint_validation` router file | Extend `overview.py` | The implementer's call. Recommendation: NEW router file (`app_v2/routers/joint_validation.py`) for the `GET /joint_validation/<id>` detail route, register in `main.py` AFTER `overview` (URL ordering doesn't conflict but logical grouping helps); leave `GET /` + `GET /overview` + `POST /overview/grid` in `routers/overview.py` (URL stays `/overview`). |
| New `JointValidationRow` Pydantic model | Reuse `OverviewRow` and rename | The field set is mostly the same but `confluence_page_id` replaces `platform_id`, `link` semantics differ slightly (Confluence emits real `<a href>`, not raw frontmatter strings), and the `has_content` field is no longer relevant (every JV has `index.html` or it wouldn't be in the list). Cleaner to define a new model than to soft-mutate the old one. |

**Installation (single line in `requirements.txt`):**
```
beautifulsoup4>=4.12,<5.0
lxml>=5.0,<7.0
```

**Version verification done in research session:**
- `beautifulsoup4` 4.14.3 (released 2025-11-30) — current stable per PyPI [VERIFIED: pypi.org/pypi/beautifulsoup4/json on 2026-04-30].
- `lxml` 6.1.0 (released 2026-04-17) — current stable per PyPI; 6.1.0 includes a security fix for XXE in `iterparse()` (`resolve_entities='internal'` is now the default), which is irrelevant to BS4-driven parsing but reassures supply-chain hygiene [VERIFIED: pypi.org/pypi/lxml/json on 2026-04-30].

---

## Architecture Patterns

### Recommended Project Structure

```
app_v2/
├── main.py                                    # ADD: app.mount("/static/joint_validation", ...)
├── routers/
│   ├── overview.py                            # MODIFY: replace _resolve_curated_pids() etc.
│   │                                          #         with discover_joint_validations() call;
│   │                                          #         delete add_platform/_entity_dict/legacy ctx
│   └── joint_validation.py                    # NEW: GET /joint_validation/<numeric_id> detail
├── services/
│   ├── joint_validation_store.py              # NEW: glob+validate+memo
│   ├── joint_validation_parser.py             # NEW: BS4 13-field extraction
│   ├── joint_validation_grid_service.py       # NEW: view-model builder (filter/sort/count)
│   ├── joint_validation_summary.py            # NEW or shim in summary.py: AI summary adapter
│   │                                          #     (calls existing summary_service primitives
│   │                                          #      with parsed JV text instead of markdown)
│   ├── overview_store.py                      # DELETE
│   ├── overview_filter.py                     # DELETE
│   ├── overview_grid_service.py               # DELETE (after pattern copy)
│   └── summary_service.py                     # KEEP (extend slightly OR add adapter — see Q8)
├── templates/
│   ├── base.html                              # MODIFY: nav label "Overview" → "Joint Validation"
│   ├── overview/
│   │   ├── index.html                         # FULL REWRITE
│   │   ├── _grid.html                         # FULL REWRITE
│   │   └── _filter_bar.html                   # FULL REWRITE (filter set unchanged in shape)
│   └── joint_validation/                      # NEW directory
│       └── detail.html                        # NEW: properties table + iframe sandbox
├── data/                                      # No change here for this phase
└── ...

content/
├── platforms/                                 # KEEP (Browse + Ask consume from here)
└── joint_validation/                          # NEW directory; root for the static mount
    └── 3193868109/                            # Example folder; user-supplied
        ├── index.html
        └── attachments/                       # Confluence-emitted assets

config/
└── overview.yaml                              # DELETE

tests/v2/
├── test_overview_store.py                     # DELETE
├── test_overview_filter.py                    # DELETE
├── test_overview_grid_service.py              # DELETE
├── test_overview_routes.py                    # REWRITE (joint-validation listing)
├── test_phase05_invariants.py                 # REWRITE/REPLACE as test_phase01_invariants.py
├── test_joint_validation_parser.py            # NEW
├── test_joint_validation_store.py             # NEW
├── test_joint_validation_grid_service.py      # NEW
├── test_joint_validation_routes.py            # NEW (replaces test_overview_routes.py)
├── test_joint_validation_invariants.py        # NEW (this phase's grep-policy guards)
└── fixtures/
    └── joint_validation_sample.html           # NEW (representative Confluence export)
```

### Pattern 1: BS4 Selector — `<th><strong>Field</strong></th><td>value</td>` (primary shape)

**What:** Confluence's Page Properties macro emits a 2-column table where each row is `<tr><th><strong>Label</strong></th><td>Value</td></tr>`. The `<strong>` element is the textual key.

**When to use:** Every row labelled with one of the 13 strong-label fields.

**Locator strategy (recommended — STRUCTURAL siblings, not text siblings):**

```python
# Source: BS4 4.14.3 official docs (find_parent / find_next_sibling)
# https://www.crummy.com/software/BeautifulSoup/bs4/doc/
def _extract_label_value(soup: BeautifulSoup, label: str) -> str:
    """Return the trimmed text of the cell adjacent to <strong>label</strong>.

    Strategy:
      1. Find the FIRST <strong> whose stripped text equals `label`.
         (string=label is too strict — Confluence sometimes wraps with
          surrounding whitespace; use a callable predicate.)
      2. Walk up to the structural parent <th> or <td> (Page Properties
         macro shape) OR <p> (fallback shape).
      3. From that parent, find the next-sibling cell:
         - If parent is <th>: same-row <td>  → use parent.find_next_sibling('td')
         - If parent is <td>: same-row next <td> (label and value share row)
         - If parent is <p>: text after the <strong> within the same <p>
                              (split on the first ':' or just use the strong's
                               .next_sibling text up to the next tag).
      4. Return value.get_text(strip=True) for cells; return '' if no cell.

    Edge cases handled:
      - Nested <strong> inside <a>: strong might be inside <a><strong>Label</strong></a>;
        walk up until you find <th>/<td>/<p>.
      - Trailing whitespace in label text: strip and compare case-sensitive
        (preserve Korean 담당자 byte-equality).
      - Multiple <strong> rows with the same label: first match wins (D-JV-04 contract).
      - Empty value cell (<td></td>): returns '' — surfaced as blank per D-JV-05.
    """
    strong = soup.find(
        'strong',
        string=lambda s: s is not None and s.strip() == label,
    )
    if strong is None:
        return ''
    # Walk up to the structural row-cell.
    cell = strong.find_parent(['th', 'td', 'p'])
    if cell is None:
        return ''
    if cell.name in ('th', 'td'):
        # Page Properties macro: th/td are siblings inside <tr>.
        sibling = cell.find_next_sibling(['td', 'th'])
        if sibling is None:
            return ''
        return sibling.get_text(strip=True)
    # cell.name == 'p' — fallback shape: <p><strong>Label</strong>: value</p>.
    # Get the text of the <p>, strip the label prefix.
    full = cell.get_text(strip=True)
    if full.startswith(label):
        rest = full[len(label):].lstrip()
        # Strip a leading ':' if present.
        if rest.startswith(':'):
            rest = rest[1:].lstrip()
        return rest
    # Defensive — return what we can.
    return full
```

**Why this and not alternatives:**

| Alternative | Why rejected |
|---|---|
| `strong.find_next('td')` | Walks past structural boundaries — could match a `<td>` from the NEXT row if the current row's value cell is missing. Returns the wrong value silently. |
| `strong.next_sibling` | Returns text-or-tag immediately after `<strong>`; for the th/td shape there IS no next sibling inside `<th>` (the `<td>` is in the parent `<tr>`'s next sibling). Returns the empty string. |
| `strong.parent.find_next_sibling('td')` | Works for the th/td shape but breaks for the `<p>` fallback (parent is `<p>`, no sibling `<td>`). Use the cell-name branch shown above. |
| `soup.select(f'th:has(strong:-soup-contains("{label}")) + td')` | CSS-selector elegance, but `:has()` and `:-soup-contains()` are BS4 4.10+ extensions that depend on the parser backend — `html.parser` rejects pseudo-selectors silently. Only safe with lxml backend. Do not lock the implementation to a backend feature when the imperative version works on both. |

[VERIFIED: against installed BS4 source — `find_parent` accepts a list of tag names; `find_next_sibling(['td', 'th'])` accepts the same. Same on 4.14.3.]

### Pattern 2: BS4 Selector — `<p><strong>Field</strong>: value</p>` (fallback shape)

Confluence sometimes (especially in older pages or in pages where Page Properties wasn't used) emits inline label-value pairs in paragraphs. The same `_extract_label_value` function above handles this via the `cell.name == 'p'` branch.

### Pattern 3: BS4 Selector — `<h1>` for title (D-JV-04)

```python
def _extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.find('h1')
    return h1.get_text(strip=True) if h1 else ''
```

Title fallback (when h1 missing) lives in the SERVICE layer (`joint_validation_grid_service`), not the parser — same pattern as Phase 5 D-OV-09 title fallback (`title = h1_text or confluence_page_id`).

### Pattern 4: BS4 link extraction for Report Link (D-JV-04)

```python
def _extract_link(soup: BeautifulSoup) -> str:
    """Extract first <a href=...> inside the <td> adjacent to <strong>Report Link</strong>.

    Strategy: locate the value cell as in _extract_label_value, then find the
    first <a> inside it. Return href attribute (raw — sanitization happens at
    the service layer via _sanitize_link, ported from Phase 5 D-OV-16).
    """
    strong = soup.find('strong', string=lambda s: s and s.strip() == 'Report Link')
    if strong is None:
        return ''
    parent = strong.find_parent(['th', 'td', 'p'])
    if parent is None:
        return ''
    sibling = parent.find_next_sibling(['td', 'th']) if parent.name in ('th', 'td') else parent
    if sibling is None:
        return ''
    a = sibling.find('a', href=True)
    return a['href'].strip() if a else ''
```

### Pattern 5: AI Summary text pre-processing (D-JV-16)

```python
# Source: BS4 official docs decompose() example
def _strip_to_text(html_bytes: bytes) -> str:
    """Reduce a Confluence-export HTML to plain text suitable for an LLM prompt.

    Decomposes <script>, <style>, <img> so their inner text/attributes never
    reach get_text(). The <img src="data:..."> base64 payload is the specific
    bloat the user flagged — decompose() removes the tag entirely (including
    attributes), so even attribute serialization can't leak base64 into the
    prompt.
    """
    soup = BeautifulSoup(html_bytes, 'lxml')
    for tag in soup(['script', 'style', 'img']):
        tag.decompose()
    text = soup.get_text(separator='\n')
    # Collapse runs of >=2 blank lines to a single blank line.
    lines = [ln.rstrip() for ln in text.splitlines()]
    out: list[str] = []
    prev_blank = False
    for ln in lines:
        is_blank = not ln.strip()
        if is_blank and prev_blank:
            continue
        out.append(ln)
        prev_blank = is_blank
    return '\n'.join(out).strip()
```

### Pattern 6: Phase 5 reuse — `_sort_rows`, `_validate_sort`, `_normalize_filters`, `_sanitize_link`, `_parse_iso_date`, `_build_overview_url`

These six pure functions in `app_v2/services/overview_grid_service.py` (lines 130-276) and `routers/overview.py` (lines 155-181) carry forward verbatim. Copy/paste with rename `platform_id` → `confluence_page_id` is the simplest correct path. Don't try to import the old service before deleting it; copy the function bodies into the new `joint_validation_grid_service.py` and delete the old service in the same plan.

### Anti-Patterns to Avoid

- **Caching the directory glob.** D-JV-08 explicitly says re-glob on every request; avoid the temptation to memoize because "globs are slow." On local SSD with ~100 numeric subdirs, `Path.glob('joint_validation/*/index.html')` is sub-millisecond [ASSUMED — based on Phase 3 RESEARCH.md mtime-cache discussion; not benchmarked here]. Caching would defeat D-JV-09 (drop-folder workflow).
- **Async parser code.** BS4 is CPU-bound. Sync `def` everywhere (INFRA-05). FastAPI dispatches to threadpool.
- **Reading `index.html` as a string before BS4.** Open in binary mode and let BS4 detect encoding from `<meta charset>` AND BOM AND content-sniffing. Confluence emits UTF-8 in 2026 (verified default for Cloud and Data Center 10.x [CITED: Atlassian Confluence Data Center 10.2 docs]), but reading as bytes preserves full Unicode for the Korean `담당자` label match. `Path.read_bytes()` → `BeautifulSoup(bytes, 'lxml')` is the right pipe.
- **Inline `<script>` inside the iframe-loaded HTML.** Even with `sandbox="allow-same-origin"` and no `allow-scripts`, scripts in the imported HTML do NOT execute (the sandbox blocks them). But Confluence sometimes inlines small `<script>` tags for code-block syntax highlighters; the sandbox handles it. **Don't add `allow-scripts` to "make highlighting work"** — that's the most-warned-against combination per MDN [CITED: developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe].
- **Replacing the `picker_popover` macro signature.** The macro already has `form_id`, `hx_post`, `hx_target`, `disable_auto_commit`, `disabled` kwargs (added in Phase 5 / 260429-qyv). Reuse AS-IS. Modifying the macro to specialize for JV would break Browse and Ask.
- **Hand-rolling URL sanitization.** `_sanitize_link` exists in Phase 5 `overview_grid_service.py` lines 130-159. Copy verbatim into the new service. Don't invent a new sanitizer.
- **A separate "Refresh" button or background task.** The mtime-keyed memo + re-glob covers it. The user explicitly deferred the Refresh button in DISCUSSION-LOG.md.

---

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| HTML parsing | Regex-driven `<strong>…</strong>` matcher | `beautifulsoup4` (with `lxml` backend) | Confluence emits inconsistent whitespace, nested `<strong><a>`, `<br>` self-closing variations, and occasionally entity-encoded labels. BS4 absorbs all of these. |
| URL sanitizer | New `_sanitize_link` for JV | Copy Phase 5's `overview_grid_service._sanitize_link` verbatim | D-JV-15 explicitly says "URL sanitizer drops dangerous schemes (`javascript:`, `data:`, `vbscript:`, `file:`, `about:`); promotes bare domains to `https://`. (port D-OV-16 verbatim)". |
| Date parsing | Custom `YYYY-MM-DD` regex | `datetime.date.fromisoformat()` | Pure stdlib; matches D-JV-10's "extract `YYYY-MM-DD`". On parse failure return None and treat as blank-for-sort (Phase 5 `_parse_iso_date`). |
| Mtime cache | New TTL store | Module-level `dict[(id, mtime_ns), ParsedRow]` | Phase 5 `read_frontmatter` cache pattern; bounded by directory size; implicit invalidation. Don't add `cachetools.TTLCache` here (different semantics — TTL would expire valid entries unnecessarily; mtime is the authoritative invalidation signal). |
| AI Summary cache | New summary cache | Reuse `summary_service._summary_cache` (existing TTLCache(128, 3600)) — extend the cache key to include `confluence_page_id` and `mtime_ns` instead of `platform_id` | The TTL semantics are appropriate for summaries (LLM output is non-deterministic; caching for 1h is fine). |
| Static file serving | A custom `GET /static/joint_validation/{path:path}` route | `app.mount("/static/joint_validation", StaticFiles(directory="content/joint_validation"), name="joint_validation_static")` | StaticFiles handles `Last-Modified`, `If-Modified-Since`, `Range`, `ETag`, MIME detection, path normalization, and the post-CVE-2023-29159 `commonpath` traversal defense. Re-implementing any of those is busywork that creates security holes. |
| Path-traversal defense for the mount | A re-implementation of `realpath` + `relative_to` checks inside the mount | Use Starlette 1.0's defaults (`html=False`, `follow_symlink=False`) PLUS the `^\d+$` directory-name regex ENFORCED by `joint_validation_store.discover()` and an acceptance grep test | StaticFiles already enforces the boundary. The `^\d+$` regex is a defense-in-depth against any future `_drafts/` folder accidentally exposing draft content. |
| URL composer | Build query strings manually | `urllib.parse.urlencode(pairs, quote_via=urllib.parse.quote)` | Phase 5 D-OV-13 / Phase 4 D-32 / Pitfall 6 — `quote_via=quote` ensures spaces encode as `%20` not `+`. Reuse `_build_overview_url` from `routers/overview.py` lines 155-181. |
| OpenAI/Ollama dual-backend client | Adding LiteLLM or per-backend SDKs | `openai.OpenAI(api_key=..., base_url=...)` (OpenAI direct OR Ollama via `/v1`) — exactly as `summary_service._build_client` already does | Confirmed in CLAUDE.md tech-stack section: "litellm — 50MB for 2-provider use case". |
| LLM prompt template | Rebuild from scratch | Carry tone + structure from `app_v2/data/summary_prompt.py` (`SYSTEM_PROMPT` + `USER_PROMPT_TEMPLATE` with `<notes>` injection mitigation) — re-word for "Joint Validation page" | T-03-03 prompt-injection mitigation already justified there; same threat model applies. |

**Key insight:** This phase has only TWO genuinely new pieces of code that don't have a verbatim Phase 5 / Phase 3 counterpart: (1) the BS4 parser (`joint_validation_parser.py`), and (2) the iframe sandbox + StaticFiles mount + properties table (`joint_validation/detail.html` + `main.py` mount line). Everything else is mechanical reuse.

---

## Phase 5 Reuse Map (Concrete File:Line Pointers)

> The most operationally-useful section for the planner. Each row tells the planner "open X file at Y line, copy Z pattern, rename to JV equivalent."

| Pattern | Source file:line | New file (this phase) | Modification |
|---|---|---|---|
| `picker_popover` Jinja macro | `app_v2/templates/browse/_picker_popover.html` lines 50-135 | (no copy — IMPORT AS-IS) | Reused unchanged. |
| `popover-search.js` (D-15b 250ms debounce) | `app_v2/static/js/popover-search.js` whole file | (no copy — REUSE AS-IS) | Reused unchanged. |
| Overview filter bar layout | `app_v2/templates/overview/_filter_bar.html` whole file | `app_v2/templates/overview/_filter_bar.html` | Full rewrite, but the structure (6 picker_popover invocations + Clear-all link) is byte-identical; only the `vm.filter_options[...]` keys stay the same, `selected_filters.get(...)` keys stay the same. |
| Sortable column header `sortable_th` macro | `app_v2/templates/overview/index.html` lines 103-123 | `app_v2/templates/overview/index.html` (rewrite) | Copy verbatim; change column list to JV's 12 sortable fields. |
| `_grid.html` row template | `app_v2/templates/overview/_grid.html` lines 1-130 | `app_v2/templates/overview/_grid.html` (rewrite) | Restructure: drop the `maybe()` em-dash macro (D-JV-05 says blank `""`); change Title cell `href` from `/platforms/{pid}` to `/joint_validation/{id}`; AI Summary button `hx-post` from `/platforms/{pid}/summary` to `/joint_validation/{id}/summary`; Link button uses `row.link` (already sanitized service-side). |
| AI Summary modal | `app_v2/templates/overview/index.html` lines 160-194 | `app_v2/templates/overview/index.html` (rewrite) | Copy verbatim. The modal-body innerHTML target id `summary-modal-body` and the show.bs.modal placeholder-reset script stay the same. |
| OOB count caption | `app_v2/templates/overview/index.html` lines 200-204 (`{% block count_oob %}`) | `app_v2/templates/overview/index.html` (rewrite) | Copy; change "platform" / "platforms" wording to "Joint Validation" / "Joint Validations" or "entry"/"entries" (CONTEXT.md D-JV-17 says "0 entries"). |
| OOB filter badges | `app_v2/templates/overview/index.html` lines 215-221 (`{% block filter_badges_oob %}`) | `app_v2/templates/overview/index.html` (rewrite) | Copy verbatim; iterates `active_filter_counts.items()` over the same 6 keys. |
| `OverviewGridViewModel` Pydantic model | `app_v2/services/overview_grid_service.py` lines 79-122 | `app_v2/services/joint_validation_grid_service.py` | Rename: `OverviewRow` → `JointValidationRow`; `platform_id` → `confluence_page_id` (typed `str` constrained to `^\d+$`); drop `has_content` and `has_content_map` (every JV has `index.html` or it's filtered out); add no new fields. |
| `_sort_rows` two-pass stable sort | `app_v2/services/overview_grid_service.py` lines 213-276 | `app_v2/services/joint_validation_grid_service.py` | Copy verbatim; rename `platform_id` to `confluence_page_id`. |
| `_sanitize_link` URL sanitizer | `app_v2/services/overview_grid_service.py` lines 130-159 | `app_v2/services/joint_validation_grid_service.py` | Copy verbatim. |
| `_parse_iso_date` | `app_v2/services/overview_grid_service.py` lines 162-172 | `app_v2/services/joint_validation_grid_service.py` | Copy verbatim. |
| `_validate_sort` | `app_v2/services/overview_grid_service.py` lines 175-189 | `app_v2/services/joint_validation_grid_service.py` | Copy; update SORTABLE_COLUMNS to JV's 12 fields. |
| `_normalize_filters` | `app_v2/services/overview_grid_service.py` lines 192-210 | `app_v2/services/joint_validation_grid_service.py` | Copy verbatim. |
| `build_overview_grid_view_model` orchestrator | `app_v2/services/overview_grid_service.py` lines 284-389 | `app_v2/services/joint_validation_grid_service.py` (rename to `build_joint_validation_grid_view_model`) | Replace `for pid in curated_pids: fm = read_frontmatter(pid, content_dir)` with `for jv_dir in discover_joint_validations(jv_root): row_data = parse_index_html(jv_dir / 'index.html')` — i.e., swap the data-source loop, keep the filter/sort/options machinery. |
| `_build_overview_url` URL composer | `app_v2/routers/overview.py` lines 155-181 | `app_v2/routers/overview.py` (modify in place) | Copy verbatim — same query keys, same canonical URL `/overview?...`. |
| `_parse_filter_dict` | `app_v2/routers/overview.py` lines 131-152 | `app_v2/routers/overview.py` (keep) | Reused verbatim. Same 6 keys. |
| GET `/` + GET `/overview` route | `app_v2/routers/overview.py` lines 184-253 | `app_v2/routers/overview.py` (modify) | Delete `_resolve_curated_pids()`, `_entity_dict()`, `_build_overview_context()`, `add_platform()` route. Delete the legacy-context block (lines 229-243). Replace `build_overview_grid_view_model` import with `build_joint_validation_grid_view_model`. |
| POST `/overview/grid` route | `app_v2/routers/overview.py` lines 306-359 | `app_v2/routers/overview.py` (modify) | Same shape; only the service-call signature changes. `block_names=["grid", "count_oob", "filter_badges_oob"]` stays. `HX-Push-Url` via `_build_overview_url(...)` stays. |
| `summary_service.py` TTLCache + Lock + always-200 | `app_v2/services/summary_service.py` whole file | `app_v2/services/summary_service.py` (extend OR add `joint_validation_summary.py` shim) | The cleanest path: ADD a new function `get_or_generate_jv_summary(confluence_page_id, cfg, jv_dir)` that reads `index.html`, runs the `_strip_to_text` pre-processor (D-JV-16), then calls a refactored `_call_llm_with_text(text, cfg)` extracted from `_call_llm_single_shot`. Reuse the same `_summary_cache`, `_summary_lock`, `_classify_error`, `_build_client`. New cache key includes `mtime_ns` (already does for platforms). Alternative: keep summary_service unchanged and add a thin shim in `joint_validation_summary.py` that prepares text and calls a public `summary_service.summarize_text(text, cfg, cache_key) -> SummaryResult`. **Recommendation: refactor for the shim approach** — it isolates this phase's LLM-input formatting and avoids touching the Phase 3 entry point function for content-page summaries (which the `/platforms/<PID>` flow still needs). |
| AI Summary route success/error templates | `app_v2/templates/summary/_success.html` + `_error.html` | (REUSE AS-IS) | Both templates take `target_id`, `platform_id`, etc. Change is minor: parameterize `platform_id` → an `entity_id` of either kind, OR add `joint_validation_id` alongside. **Simpler: rename the template variables to a generic `entity_id` and `entity_kind` ('platform' / 'joint_validation') so both flows share the partials.** |
| Backend-name resolver | `app_v2/services/llm_resolver.py` whole file | (REUSE AS-IS) | The `pbm2_llm` cookie + Ask-page LLM dropdown drive this; both Ask AND the new JV summary flow inherit the active backend automatically. |
| Sync-`def` route discipline | All `app_v2/routers/*.py` | New `joint_validation` router | Same convention. Tests rely on it for thread-safe pytest-mock patches. |

**Drift between Phase 5 D-OV-* and on-disk shape (worth flagging):**

- D-OV-15 originally said the AI Summary surface was inline; UAT-time refactor moved it to a global modal with `summary-modal-body` as the swap target — Phase 1 inherits the modal pattern. [VERIFIED: `templates/overview/index.html` lines 160-194.]
- D-OV-13 query-key list is verified accurate against `routers/overview.py` line 170: `("status", "customer", "ap_company", "device", "controller", "application")`. Same set carries forward.
- D-OV-16 URL sanitizer scheme list at `overview_grid_service.py` line 54: `("javascript:", "data:", "vbscript:", "file:", "about:")` — exact match for D-JV-15. [VERIFIED.]
- The legacy "Add platform" form in `templates/overview/index.html` lines 49-67 + the `add_platform` route in `routers/overview.py` lines 256-303 are both DELETIONS for D-JV-07.

---

## Pydantic v2 View-Model Shape

Concrete sketch the planner can drop into `app_v2/services/joint_validation_grid_service.py`:

```python
# Source: ported from app_v2/services/overview_grid_service.py:79-122
from typing import Literal
from pydantic import BaseModel, Field

class JointValidationRow(BaseModel):
    """One row in the Joint Validation pivot grid.

    Departures from OverviewRow:
    - confluence_page_id replaces platform_id (digits-only).
    - All optional fields default to '' (empty string), not None — D-JV-05.
    - has_content / has_content_map dropped (every JV has index.html).
    - link is the raw <a href> from <strong>Report Link</strong> cell,
      sanitized to None / 'http(s)://...' by _sanitize_link before the row
      is constructed.
    """
    confluence_page_id: str = Field(..., pattern=r'^\d+$')
    title: str = ''       # h1 text or confluence_page_id fallback
    status: str = ''
    customer: str = ''
    model_name: str = ''
    ap_company: str = ''
    ap_model: str = ''
    device: str = ''
    controller: str = ''
    application: str = ''
    assignee: str = ''    # 담당자
    start: str = ''       # YYYY-MM-DD or raw string
    end: str = ''         # YYYY-MM-DD or raw string
    link: str | None = None  # sanitized; None means disabled-state Link button


class JointValidationGridViewModel(BaseModel):
    rows: list[JointValidationRow]
    filter_options: dict[str, list[str]]      # keys = FILTERABLE_COLUMNS (6)
    active_filter_counts: dict[str, int]      # keys = FILTERABLE_COLUMNS
    sort_col: str
    sort_order: Literal['asc', 'desc']
    total_count: int                          # equals len(rows) — useful for "0 entries"


# Module constants
ALL_METADATA_KEYS: tuple[str, ...] = (
    'title', 'status', 'customer', 'model_name', 'ap_company', 'ap_model',
    'device', 'controller', 'application', 'assignee', 'start', 'end',
)
SORTABLE_COLUMNS: tuple[str, ...] = ALL_METADATA_KEYS  # 12 sortable
FILTERABLE_COLUMNS: tuple[str, ...] = (
    'status', 'customer', 'ap_company', 'device', 'controller', 'application',
)
DATE_COLUMNS: tuple[str, ...] = ('start', 'end')
DEFAULT_SORT_COL: str = 'start'
DEFAULT_SORT_ORDER: Literal['asc', 'desc'] = 'desc'
```

**Per Q7 of the orchestrator's prompt**: `applied_filters` SHOULD stay as `dict[str, list[str]]` (matching Phase 5's `selected_filters` shape used in `_filter_bar.html`). The template references `selected_filters.get('status', [])` etc. in `picker_popover` calls, so collapsing to a flat dict keeps the existing macro signature byte-stable.

---

## Mtime Cache (Pitfalls and Resolution)

**Cache key:** `(confluence_page_id, mtime_ns)` — same shape as Phase 5's `_FRONTMATTER_CACHE`.

**Pitfall (a) — filesystem mtime resolution:** `os.stat().st_mtime_ns` is integer nanoseconds, BUT the actual resolution depends on the filesystem:

| Filesystem | Effective mtime resolution | Risk |
|---|---|---|
| ext4 (Linux, default) | nanosecond | None for this workload. |
| NFS | seconds (typical) | Two writes within the same wall-clock second → same mtime → stale cache after the second write. |
| FAT32 / exFAT | 2 seconds | Same as NFS. |
| Windows host volume mounted into a Linux container (e.g., WSL2 `/mnt/c/...`) | seconds (DrvFs) | Same as NFS. |
| btrfs / xfs | nanosecond | None. |

**Mitigation:** None needed for the project's stated deployment (Linux 6.17 native ext4 on the intranet host, single-uvicorn-process — `STATE.md` and `PROJECT.md` confirm). If the deployment ever moves to a host volume mount, the cache will be slightly stale after rapid sequential edits; the practical impact is zero because Confluence exports are dropped infrequently (drop-folder workflow, D-JV-09).

**Pitfall (b) — atomic-rename / `cp -r` patterns:** When the user runs `cp -r drop/3193868109/ content/joint_validation/`, files are written one-by-one. A request that arrives between the directory creation and the `index.html` write would see "no index.html" and skip the row (D-JV-03 contract — the regex+`is_file()` check covers this). A request that arrives after `index.html` is written but before `attachments/` is fully copied would parse `index.html` correctly but the iframe would 404 some attachments (acceptable; user re-renders detail page after copy completes).

**Mitigation:** None at the application layer. The discovery contract (D-JV-03) silently skips folders without a readable `index.html`. Document this in user-facing onboarding copy.

**Pitfall (c) — clock skew during a `cp -r`:** The destination filesystem stamps each file with `time.time()` at write completion; if the user's system clock jumps backward during the copy (NTP correction on a long-uptime server is the classic case), file mtimes can go backward. Cache key `(id, mtime_ns)` is just an opaque key — different value → cache miss → re-parse. No correctness issue, only efficiency.

**Pitfall (d) — unbounded cache growth:** The cache is keyed by `(confluence_page_id, mtime_ns)`. If the same JV is edited 1000 times, the cache holds 1000 entries for that page (one per historical mtime). For a single-uvicorn-process intranet tool with infrequent drops, the practical memory cost is negligible (< 1KB per entry, < 1MB for thousands of entries). **Do not add an LRU cap unless cache size becomes an observable problem** — the simpler dict is easier to test and reason about, matching Phase 5 D-OV-12 precedent.

---

## iframe Sandbox + Same-Origin Static Content (D-JV-12)

**Locked attribute:** `sandbox="allow-same-origin"` (no `allow-scripts`).

**What this allows:**
- Inline `<style>` and `style="..."` attributes render fully [VERIFIED: MDN — sandbox blocks scripting, navigation, plugins, popups, but CSS rendering is NOT a sandbox-restricted capability].
- The iframe's document is treated as same-origin with the parent — this lets the parent page (`detail.html`) read the iframe's title, scroll position, etc., but NOT execute scripts inside it (allow-scripts is what enables scripting).
- Image, font, video, and audio loading from the same origin works (Confluence-exported `attachments/...` resolve relative to the iframe `src`).
- Form rendering displays but submission is blocked unless `allow-forms` is added.
- Navigation inside the iframe via `<a href>` is blocked unless `allow-top-navigation` (top-level) or `allow-popups` (new tab) is added — and we DO want some control here.

**The `<a target="_top">` question for external Confluence links:** Confluence pages frequently contain `<a href="https://confluence.example.com/...">` cross-references. With pure `sandbox="allow-same-origin"`, clicking these does nothing (blocked).

**Recommendation for the planner:**
- **Default attribute set:** `sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"`.
  - `allow-popups`: lets `<a target="_blank">` open external links in a new tab.
  - `allow-popups-to-escape-sandbox`: the new tab is NOT sandboxed (otherwise it inherits the iframe's sandbox and Confluence's home page won't render).
  - **DO NOT** add `allow-scripts` — combining `allow-scripts` with `allow-same-origin` lets the framed document remove the sandbox attribute, defeating the security boundary entirely [CITED: developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe — "When the embedded document has the same origin as the embedding page, it is strongly discouraged to use both allow-scripts and allow-same-origin"].
  - **DO NOT** add `allow-top-navigation` — would let a malicious export navigate the parent page away.
  - **DO NOT** add `allow-forms` unless the user explicitly wants Confluence forms to submit (not in scope this phase).

**The `target="_top"` requirement for in-iframe links:** If the user wants an in-iframe `<a>` to navigate the iframe itself (rather than open a new tab), the default behavior already does that — no sandbox flag needed. No additional handling required.

**Browser compatibility (2026):** Sandbox attribute is universally supported (Chrome 4+, Firefox 17+, Safari 5+, Edge 12+) [CITED: caniuse.com — sandbox attribute, ~98% global support 2026]. `allow-popups-to-escape-sandbox` requires Chrome 53+ / Firefox 79+ / Safari 16.4+; for an internal intranet tool with a known browser baseline this is uniformly safe.

**Rendering Confluence's inline `<script>` for syntax highlighting:** Confluence's HTML export occasionally inlines a tiny `<script>` for collapsible-section toggles or syntax highlighters. With no `allow-scripts`, these scripts do not run; the affected content (collapsible sections) renders in its un-toggled state. **This is acceptable** — D-JV-09 says the iframe shows the page "as exported"; users who need full interactivity can click the Report Link to open the live Confluence page.

**`Content-Security-Policy` + `frame-ancestors` consideration:** Not required this phase. The iframe lives on the SAME origin as the parent (we serve the static content from `/static/joint_validation/...`), so no CORS or CSP `frame-ancestors` directive is needed. **DO NOT add a custom CSP** — interacts poorly with the existing FastAPI shell which has none.

---

## FastAPI StaticFiles Path-Traversal Defense (D-JV-13)

**Verified Starlette 1.0.0 source** [VERIFIED: `.venv/lib/python3.13/site-packages/starlette/staticfiles.py`]:

The lookup function uses:
```python
if self.follow_symlink:
    full_path = os.path.abspath(joined_path)
else:
    full_path = os.path.realpath(joined_path)  # resolves symlinks
if os.path.commonpath([full_path, directory]) != str(directory):
    continue  # outside the static directory; reject
```

**This is the post-CVE-2023-29159 fix (commonpath, not commonprefix)** — Starlette 0.27+ ships it; we run 1.0.0. [VERIFIED: GHSA-v5gw-mw7f-84px advisory.]

**Default settings already-safe** (no override needed):
- `html: bool = False` — does NOT auto-serve `index.html` for directory URLs unless explicitly enabled. **For this phase: SET `html=False` EXPLICITLY** in the mount call as documentation, even though it's the default.
- `follow_symlink: bool = False` — does NOT follow symlinks out of the directory. **Keep default**: `os.path.realpath` resolves symlinks AND the `commonpath` check rejects them if they escape.
- `check_dir: bool = True` — raises at startup if the directory doesn't exist. **Keep default; the lifespan-time `content_dir.mkdir(parents=True, exist_ok=True)` pattern in `main.py` (already in use for `content/platforms`) ensures `content/joint_validation/` exists before mount.**

**Safe minimal mount call:**
```python
# app_v2/main.py — after the existing app.mount("/static", ...) call:
app.mount(
    "/static/joint_validation",
    StaticFiles(
        directory="content/joint_validation",
        html=False,
        follow_symlink=False,
    ),
    name="joint_validation_static",
)
```

**The `^\d+$` directory-name regex (D-JV-03)** is enforced at the application layer — `joint_validation_store.discover()` filters the glob result. StaticFiles itself does NOT enforce a directory-name format; a request to `/static/joint_validation/_drafts/sensitive.html` would succeed if `_drafts/sensitive.html` existed inside `content/joint_validation/`. **Mitigation:** the planner must include an acceptance-grep test that any folder under `content/joint_validation/` whose name does NOT match `^\d+$` is excluded from listings AND that the empty-state copy does not surface them. The static mount itself does not need a regex — the threat model is "what's exposed", and the directory only contains numeric subdirectories per the drop-folder workflow (D-JV-09). **Recommended: add a `pytest` test that drops a `_drafts/` folder with a marker file into a tmp `content/joint_validation/`, makes a `GET /overview` request, and asserts the marker is not in the rendered HTML.**

**Known pitfalls:**
- **DO NOT** set `html=True` — would auto-serve `index.html` for the bare `/static/joint_validation/<id>/` URL, but D-JV-12 already says `iframe src` includes the explicit `/index.html`. `html=True` adds `404.html` redirect logic that's irrelevant and could confuse the iframe.
- **DO NOT** set `follow_symlink=True` — would let a symlink inside `content/joint_validation/<id>/` point to `/etc/passwd`. Default `False` blocks this.
- **DO NOT** mount the directory with `check_dir=False` — silent missing-directory failures. Default `True` raises a startup error if `content/joint_validation/` doesn't exist; the lifespan's `mkdir(exist_ok=True)` handles cold-start.

**No known CVEs as of 2026-04-30** for the `os.path.commonpath` + `realpath` + default-False combo. CVE-2023-29159 is fully patched in 0.27+; we run 1.0.0.

---

## AI Summary Route Shape (D-JV-16)

**Confirmation against on-disk Phase 3 code** [VERIFIED: `app_v2/services/summary_service.py`, `routers/summary.py`, `data/summary_prompt.py`]:

| Element | Phase 3 location | What changes for JV |
|---|---|---|
| TTLCache | `summary_service.py:80` `_summary_cache: TTLCache(maxsize=128, ttl=3600)` | Reuse same cache module-global. |
| Lock | `summary_service.py:81` `_summary_lock = threading.Lock()` | Reuse. |
| Cache key | `summary_service.py:201` `hashkey(platform_id, mtime_ns, cfg.name, cfg.model)` | Add a kind discriminator: `hashkey('jv', confluence_page_id, mtime_ns, cfg.name, cfg.model)` so JV and platform summaries don't collide on the same numeric id (`Samsung_S22Ultra_SM8450` vs `3193868109` won't collide as strings, but defense in depth is cheap). |
| Client builder | `summary_service.py:84` `_build_client(cfg)` | Reuse — handles both OpenAI and Ollama via `base_url=<endpoint>/v1`. |
| LLM call | `summary_service.py:118` `_call_llm_single_shot(content, cfg)` | Refactor: extract the `chat.completions.create` call into a backend-agnostic helper that takes `(content_text, cfg, system_prompt, user_prompt_template)`. Then both content-page and JV summaries call it with their own prompts. |
| Error classifier | `summary_service.py:144` `_classify_error(exc, backend_name)` | Reuse verbatim — same 7-string vocabulary. |
| Always-200 contract | `routers/summary.py:113` `get_summary_route` | Mirror in new JV summary route: never raises, always 200, error fragment is `summary/_error.html` with classified `reason`. |
| Pre-processing | (none for content pages — markdown is already plain) | NEW for JV: D-JV-16 — BS4 decompose `<script>`, `<style>`, `<img>`; `get_text(separator='\n')`; collapse blank lines. Lives in `joint_validation_summary._strip_to_text(html_bytes)` (Pattern 5 above). |
| Token clamp | (none — relies on cfg.max_tokens for output) | D-JV-16 says "the existing `nl_service.max_context_tokens=30000` cap is the final clamp". Verified: this constant is `app.core.agent.config.AgentConfig.max_context_tokens` (default 30_000). **[ASSUMED]** the planner needs to add an INPUT truncation step in `_strip_to_text` (e.g., `text[:30_000 * 4]` as a token-character heuristic) OR pass the value through to `cfg.max_tokens` via a config-load pull. The discuss-phase did not lock this; recommend the planner ASK before locking. |
| Prompt template | `app_v2/data/summary_prompt.py` | NEW: `app_v2/data/jv_summary_prompt.py` with re-worded `SYSTEM_PROMPT` ("You summarize Joint Validation pages…") and `USER_PROMPT_TEMPLATE` (wrap content in `<jv_page>...</jv_page>` instead of `<notes>...</notes>` — same anti-injection structural defense). |

**Public surface for the new JV summary route:**

```python
# app_v2/services/joint_validation_summary.py — NEW
def get_or_generate_jv_summary(
    confluence_page_id: str,        # ^\d+$
    cfg: LLMConfig,
    jv_root: Path,                  # content/joint_validation
    *,
    regenerate: bool = False,
) -> SummaryResult:
    """Reads index.html, strips noise, calls LLM with cached result."""
    index_html = jv_root / confluence_page_id / "index.html"
    mtime_ns = index_html.stat().st_mtime_ns  # raises FileNotFoundError → caller catches → 200 + error fragment
    html_bytes = index_html.read_bytes()
    text = _strip_to_text(html_bytes)         # Pattern 5
    # Optionally clamp text to ~30000 tokens worth of chars (4 chars/token heuristic)
    if len(text) > 120_000:                    # ~30k tokens — see [ASSUMED] above
        text = text[:120_000]
    return _summarize_text_cached(
        cache_key=hashkey('jv', confluence_page_id, mtime_ns, cfg.name, cfg.model),
        text=text,
        cfg=cfg,
        regenerate=regenerate,
        system_prompt=JV_SYSTEM_PROMPT,
        user_prompt_template=JV_USER_PROMPT_TEMPLATE,
    )

# app_v2/routers/joint_validation.py — NEW
@router.post("/joint_validation/{confluence_page_id}/summary", response_class=HTMLResponse)
def get_jv_summary_route(
    request: Request,
    confluence_page_id: Annotated[str, Path(pattern=r"^\d+$", min_length=1, max_length=32)],
    x_regenerate: Annotated[str | None, Header()] = None,
    hx_target: Annotated[str | None, Header()] = None,
):
    # Mirror routers/summary.py:113 byte-stable; only the service call swaps.
    ...
```

**Confirmation that route URL `/joint_validation/<id>/summary` doesn't collide:** The static mount is at `/static/joint_validation/<id>/...` (different prefix). The detail page is at `/joint_validation/<id>` (no `/summary` suffix). No collision. The planner can safely register both routes under the same `prefix="/joint_validation"` router.

---

## Korean Label Handling (담당자)

**BS4 4.14.x is UTF-8-clean** when reading bytes [VERIFIED: BS4 docs `BeautifulSoup(bytes_or_handle, parser)` does encoding-detection from `<meta charset>`, BOM, and content-sniffing via `cchardet`/`chardet` if installed, falling back to UTF-8].

**Strategy:**
1. Open the file with `Path.read_bytes()` — preserves all bytes including BOM and any high-Unicode label characters.
2. Pass bytes to BS4: `BeautifulSoup(html_bytes, 'lxml')` — BS4 auto-detects encoding.
3. Match labels with `string=lambda s: s and s.strip() == '담당자'` — Python 3 strings are Unicode-native; the literal `'담당자'` is the codepoint sequence U+B2F4 U+B2F9 U+C790. **NEVER** ASCII-fold or `.encode('ascii', errors='ignore')` the label or the text-to-match.
4. Source files for the parser MUST declare `# -*- coding: utf-8 -*-` (or rely on Python 3's UTF-8 source default — Python 3.13 is UTF-8 by default for source files [VERIFIED]).
5. **Acceptance test:** parse a fixture with `<strong>담당자</strong></th><td>홍길동</td>`, assert `row.assignee == '홍길동'`. The test file itself must be saved as UTF-8 (verify via `file --mime-encoding fixture.html` returns `utf-8`).

**Encoding-detection fallback:** If `chardet`/`cchardet` are not installed (BS4 falls back to its `EncodingDetector` heuristic, which is less reliable for CJK), Confluence-exported HTML usually carries `<meta charset="UTF-8">` so detection is deterministic. The project doesn't currently install chardet [VERIFIED: not in requirements.txt]; recommend NOT adding it as a hard dep — BS4's built-in detector + `<meta charset>` is sufficient.

---

## Test Fixture Shape (Claude's Discretion + Q9)

A minimal-but-complete fixture exercising all locked extraction rules. Save as `tests/v2/fixtures/joint_validation_sample.html` (UTF-8, no BOM):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Joint Validation - 3193868109</title>
  <style>/* Confluence inline styles, decomposed by AI Summary pre-process */</style>
</head>
<body>
  <h1>Samsung S22 Ultra UFS 3.1 Joint Validation</h1>
  <table class="confluenceTable">
    <tbody>
      <tr><th><strong>Status</strong></th><td>In Progress</td></tr>
      <tr><th><strong>Customer</strong></th><td>Samsung</td></tr>
      <tr><th><strong>Model Name</strong></th><td>S22Ultra</td></tr>
      <tr><th><strong>AP Company</strong></th><td>Qualcomm</td></tr>
      <tr><th><strong>AP Model</strong></th><td>SM8450</td></tr>
      <tr><th><strong>Device</strong></th><td>UFS 3.1</td></tr>
      <tr><th><strong>Controller</strong></th><td>FW v2.3</td></tr>
      <tr><th><strong>Application</strong></th><td>Smartphone</td></tr>
      <tr><th><strong>담당자</strong></th><td>홍길동</td></tr>
      <tr><th><strong>Start</strong></th><td>2026-03-15</td></tr>
      <tr><th><strong>End</strong></th><td>2026-06-30</td></tr>
      <tr><th><strong>Report Link</strong></th><td><a href="https://confluence.example.com/pages/3193868109">Confluence Report</a></td></tr>
    </tbody>
  </table>
  <p>Test body paragraph.</p>
  <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAYAAABccqhmAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAB[REPEAT FOR ~1KB BASE64 BLOB]"
       alt="Inline base64 image to verify D-JV-16 decompose">
  <h2>Notes</h2>
  <p>Some narrative notes that the AI Summary should pick up.</p>
</body>
</html>
```

**A second, minimal fixture testing the FALLBACK shape and ONE missing field** (`tests/v2/fixtures/joint_validation_fallback_sample.html`):

```html
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>JV 4242</title></head>
<body>
  <h1>Sparse Fixture</h1>
  <p><strong>Customer</strong>: TestCustomer</p>
  <p><strong>Model Name</strong>: TestModel</p>
  <!-- Status field deliberately omitted to verify D-JV-05 blank fallback -->
  <p><strong>담당자</strong>: 김철수</p>
  <p><strong>Start</strong>: 2026-04-01</p>
</body>
</html>
```

**Coverage matrix:**

| Fixture | Locked rules covered |
|---|---|
| `joint_validation_sample.html` (page_id 3193868109) | All 13 fields, primary `<th><strong>…</strong></th><td>…</td>` shape, Korean assignee, base64 image (D-JV-16 verification target) |
| `joint_validation_fallback_sample.html` (page_id 4242) | `<p><strong>…</strong>: …</p>` fallback shape, missing `Status` field → blank, Korean assignee variant |

The user's note about `confluence_page_id=3193868109` is incorporated as the primary fixture's directory name in tests.

---

## Test Framework Parity (Q10)

[VERIFIED: directory listing of `tests/v2/`]

**Existing layout:**
- `tests/v2/conftest.py` — registers the `slow` marker only; no shared fixtures
- `tests/v2/test_*_routes.py` — FastAPI TestClient pattern (e.g., `test_overview_routes.py:23` `from fastapi.testclient import TestClient`)
- `tests/v2/test_*_service.py` — pure service unit tests with `tmp_path` injection
- `tests/v2/test_phaseN_invariants.py` — grep-based policy guards (e.g., `test_phase05_invariants.py`)

**No shared HTMLParser fixture exists.** This phase introduces the first BS4-driven test surface; recommend adding a `tests/v2/conftest.py` fixture:

```python
@pytest.fixture
def jv_sample_html():
    """Read the canonical sample fixture as bytes."""
    fixture_path = Path(__file__).parent / "fixtures" / "joint_validation_sample.html"
    return fixture_path.read_bytes()
```

Alternatively, scope the fixture to `tests/v2/test_joint_validation_parser.py` only (it's the only consumer).

**FastAPI TestClient idiom for the JV routes:** Mirror `test_overview_routes.py:23-50` — `TestClient(app)`, monkeypatch the JV root directory to `tmp_path`, write fixture HTML files into `tmp_path/<numeric_id>/index.html`.

**Static mount tests:** TestClient handles `app.mount(...)` natively — `client.get('/static/joint_validation/3193868109/index.html')` resolves through the mount transparently. Path traversal tests: `client.get('/static/joint_validation/../etc/passwd')` should return 404 (Starlette normalizes `..` away).

---

## Cleanup Targets (D-JV-06 + D-JV-07)

**Files to DELETE:**

| Path | Why |
|---|---|
| `config/overview.yaml` | Curated entity list — replaced by directory glob. |
| `app_v2/services/overview_store.py` | YAML CRUD — no longer needed. |
| `app_v2/services/overview_filter.py` | `has_content_file` was Platform-specific; JV always has `index.html` or it's filtered at discovery. |
| `app_v2/services/overview_grid_service.py` | Replaced by `joint_validation_grid_service.py` (after pattern copy). |
| `app_v2/templates/overview/index.html` | Full rewrite (NOT rename — D-JV-06 explicit). |
| `app_v2/templates/overview/_grid.html` | Full rewrite. |
| `app_v2/templates/overview/_filter_bar.html` | Full rewrite (filter set unchanged in shape). |
| `app_v2/services/overview_store.py::OverviewEntity` | Pydantic type — gone with the file. |
| `app_v2/services/overview_store.py::DuplicateEntityError` | Same. |
| `tests/v2/test_overview_store.py` | Tests for deleted module. |
| `tests/v2/test_overview_grid_service.py` | Tests for deleted module. |
| `tests/v2/test_overview_filter.py` | Tests for deleted module. |
| `tests/v2/test_overview_routes.py` | Will be REWRITTEN as `test_joint_validation_routes.py` — content fully replaced. |
| `tests/v2/test_phase05_invariants.py` | Some assertions still hold (e.g., yaml.safe_load); others are obsolete (e.g., D-OV-04 forbidden routes). Recommend keeping the file under a new name `test_phase01_invariants.py` with this phase's policy guards (D-JV-* equivalents). |
| Route `POST /overview/add` in `routers/overview.py:256-303` | D-JV-07 — Joint Validation drop-folder workflow has no add affordance. |

**Files to KEEP UNCHANGED:**

| Path | Why |
|---|---|
| `content/platforms/*.md` | Browse + Ask still consume PLATFORM_IDs from `ufs_data`. |
| `app_v2/services/content_store.py` | Backs `/platforms/<PID>` markdown CRUD. |
| `app_v2/routers/platforms.py` | `/platforms/<PID>` detail/edit/preview routes. |
| `app_v2/routers/summary.py` | Existing AI Summary route for content pages — unchanged. |
| `app_v2/services/summary_service.py` | Reused (with optional refactor to extract `_call_llm_single_shot` into a shared helper). |
| `app_v2/services/llm_resolver.py` | `pbm2_llm` cookie + Ask-page LLM dropdown — unchanged. |
| `app_v2/static/js/popover-search.js` | D-15b — unchanged. |
| `app_v2/templates/browse/_picker_popover.html` | Reused AS-IS. |
| `app_v2/templates/summary/_success.html`, `_error.html` | Reused (consider parameterizing entity_id/entity_kind for cross-flow reuse). |

---

## Common Pitfalls

### Pitfall 1: BS4 `string=` predicate matching surrounding whitespace

**What goes wrong:** `soup.find('strong', string='Status')` returns None when the actual HTML is `<strong> Status </strong>` (Confluence sometimes adds surrounding whitespace) or `<strong>Status<br/></strong>` (entity-encoded line break inside the strong).

**Why it happens:** `string=` does an exact-match comparison against the tag's `.string` property (which is None for tags with multiple children).

**How to avoid:** Use `string=lambda s: s is not None and s.strip() == 'Status'`. This handles surrounding whitespace AND the case where `.string` is None for tags with mixed content (multi-child tags) — though for the latter the lambda still gets called with each NavigableString child.

**Warning signs:** Test fixtures pass but real Confluence exports return blank fields for some rows.

### Pitfall 2: First-match-wins violated by sort order

**What goes wrong:** D-JV-04 says "first match wins when a label appears more than once on the page". `soup.find('strong', ...)` returns the document-order first match, which IS what we want. But if the implementer uses `soup.find_all(...)` and picks `[-1]`, they get the LAST match instead. Subtle bug.

**How to avoid:** Use `find()` (singular), not `find_all()[0]`. Document the contract in the parser's docstring.

**Warning signs:** Two `<strong>Status</strong>` rows on a page (e.g., one in a properties table, one in a sub-section); the wrong value surfaces.

### Pitfall 3: Cache key collision between Phase 3 platform summaries and Phase 1 JV summaries

**What goes wrong:** Phase 3 cache key is `hashkey(platform_id, mtime_ns, llm_name, llm_model)`. If the implementer reuses this exact key shape for JV (replacing `platform_id` with `confluence_page_id`), there's no field to disambiguate "this is a JV summary" vs "this is a content-page summary". A `confluence_page_id="3193868109"` and a `platform_id="3193868109"` (unlikely but legal under the regex) would share a cache slot.

**How to avoid:** Add a string discriminator: `hashkey('jv', confluence_page_id, mtime_ns, llm_name, llm_model)` for JV, leaving `hashkey(platform_id, ...)` for platforms.

**Warning signs:** Same numeric id appears in both stores; cache returns the wrong summary.

### Pitfall 4: Iframe attribute order changing render

**What goes wrong:** None, actually — attribute order doesn't matter for the sandbox attribute. Listed here so the planner doesn't worry.

**How to avoid:** N/A.

### Pitfall 5: Mtime cache returning stale data after a `cp -p` (preserve mtime) drop

**What goes wrong:** `cp -p` preserves the source file's mtime. If a user updates a JV folder externally (edit, save) and then `cp -p`'s the new version into `content/joint_validation/`, the destination file's mtime equals the SOURCE's mtime — which might be OLDER than the cached `mtime_ns`. The cache hit returns stale parsed data; the new content is invisible until the user re-saves with mtime > cache key.

**How to avoid:** Document in user-facing onboarding: "Use `cp` (without `-p`) or just drag-and-drop to ensure the new file's mtime reflects the time of copy." Alternatively, key the cache on `(confluence_page_id, mtime_ns, file_size)` to differentiate same-mtime-different-content cases.

**Warning signs:** User reports "I updated the file but the page still shows old data."

### Pitfall 6: Sync `def` vs async `def` mismatch on the JV summary route

**What goes wrong:** Phase 6 added `async def` for some routes. If the JV summary route is `async def` while calling sync BS4 + sync `summary_service.get_or_generate_summary`, those calls block the event loop.

**How to avoid:** Match the existing project convention (INFRA-05 — sync `def` everywhere in v2.0). Verified by `tests/v2/test_phase05_invariants.py::test_no_async_def_in_overview_routes` pattern; this phase needs an equivalent invariant test.

**Warning signs:** Slow request handling under modest concurrency; `htmx-error-container` showing 500s under load.

### Pitfall 7: BS4 4.13+ deprecation of `findAll`/`findAllNext` camelCase aliases

**What goes wrong:** BS4 4.13+ deprecated camelCase method names (`findAll`, `findAllNext`, etc.) in favor of snake_case (`find_all`, `find_all_next`). Code that uses camelCase will warn now and break in 5.0.

**How to avoid:** Use snake_case exclusively. This is the BS4 docs-recommended idiom anyway.

**Warning signs:** `DeprecationWarning` in pytest output.

### Pitfall 8: jinja2-fragments `block_names=` requires the block's local macros to be defined INSIDE the block

**What goes wrong:** Phase 5 hit this — the `sortable_th` macro was originally defined at template-top; when `POST /overview/grid` rendered with `block_names=["grid", ...]`, the macro was not visible inside the isolated block. Phase 5 fixed it by defining the macro INSIDE `{% block grid %}` (line 103).

**How to avoid:** Mirror Phase 5's approach exactly — define `sortable_th` inside the `grid` block. Document in the template comment as Phase 5 did. The `maybe()` macro is gone for this phase (D-JV-05 says blank, not em-dash) so this only applies to `sortable_th`.

**Warning signs:** `POST /overview/grid` returns a fragment with `{{ sortable_th(...) }}` literally as text (Jinja2 silent macro miss).

### Pitfall 9: Leaking BS4 NavigableString objects to Pydantic

**What goes wrong:** `soup.find('h1').string` returns a `NavigableString` (a `str` subclass with a parent reference). Passing it to a Pydantic model field works at runtime but `str()` coercion or `.strip()` is needed to get a plain `str` for serialization stability and to drop the parent reference (otherwise the parsed BS4 tree is held alive by every JV row).

**How to avoid:** Always wrap returned values: `str(elem.get_text(strip=True))` or `elem.get_text(strip=True)` (already returns plain str).

**Warning signs:** Memory growth over time as old BS4 trees pin via NavigableString references; this is mostly cosmetic at our scale but worth flagging.

### Pitfall 10: Static mount path collision with the existing `/static` mount

**What goes wrong:** `app_v2/main.py:108` already does `app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")`. The new mount at `/static/joint_validation` is a child path. Starlette dispatches by exact-prefix match, longest-match-wins; the new mount must be added BEFORE the parent `/static` mount in router order, OR the parent `/static` will match `/static/joint_validation/...` requests first.

**How to avoid:** Add `app.mount("/static/joint_validation", ...)` BEFORE the existing `app.mount("/static", ...)` line (i.e., move the existing line down OR insert above it). Verify with a smoke test: `client.get('/static/joint_validation/3193868109/index.html')` returns the file content; `client.get('/static/css/app.css')` still returns the existing CSS.

**Warning signs:** Iframe `src` returns 404 for the JV `index.html`; `/static/css/app.css` still works.

[VERIFIED: Starlette routing.py — Starlette tries each route in registered order; for mounts, the first one whose path-prefix matches wins. Ordering matters.]

### Pitfall 11: AI Summary cache age display reading from the JV cache but route claims "fresh"

**What goes wrong:** Phase 3's `_success.html` template renders cached_age_s; if this phase reuses the success template but stores its cache in a separate dict, the age calculation must be done in the same function that returns the SummaryResult. (Pattern's already correct in summary_service; just don't accidentally reset `result.generated_at` in the JV path.)

**How to avoid:** Don't construct a new `SummaryResult` after a cache hit; return the cached object as-is.

**Warning signs:** Cache hit shows "(fresh)" instead of the cached age.

---

## Code Examples

### Example 1: Discovery (D-JV-02 + D-JV-03)

```python
# app_v2/services/joint_validation_store.py
# Source: pattern adapted from Phase 5 overview_store.py + filter regex idiom
from __future__ import annotations
import re
from pathlib import Path
from typing import Iterator

JV_ROOT: Path = Path("content/joint_validation")
PAGE_ID_PATTERN = re.compile(r"^\d+$")


def discover_joint_validations(jv_root: Path = JV_ROOT) -> Iterator[tuple[str, Path]]:
    """Yield (confluence_page_id, index_html_path) for each valid JV folder.

    A folder is valid iff:
      - Name matches ^\\d+$
      - Contains a readable index.html

    Anything else silently skipped (D-JV-03). Glob NOT cached (D-JV-08).
    """
    if not jv_root.exists():
        return
    for index_html in jv_root.glob("*/index.html"):
        page_id = index_html.parent.name
        if not PAGE_ID_PATTERN.match(page_id):
            continue
        if not index_html.is_file():
            continue
        yield page_id, index_html
```

### Example 2: Mtime memo (D-JV-08)

```python
# app_v2/services/joint_validation_store.py — continued
from app_v2.services.joint_validation_parser import parse_index_html, ParsedJV

_PARSE_CACHE: dict[tuple[str, int], ParsedJV] = {}


def get_parsed_jv(page_id: str, index_html: Path) -> ParsedJV:
    """Return parsed metadata; memoized by (page_id, mtime_ns).

    Mirror of Phase 5's read_frontmatter cache pattern (D-OV-12).
    """
    mtime_ns = index_html.stat().st_mtime_ns
    key = (page_id, mtime_ns)
    cached = _PARSE_CACHE.get(key)
    if cached is not None:
        return cached
    parsed = parse_index_html(index_html.read_bytes())
    _PARSE_CACHE[key] = parsed
    return parsed
```

### Example 3: Parser (D-JV-04)

```python
# app_v2/services/joint_validation_parser.py
# Source: BS4 4.14.3 official docs + locator strategy from Pattern 1 above
from __future__ import annotations
from dataclasses import dataclass, field
from bs4 import BeautifulSoup, Tag


@dataclass(frozen=True)
class ParsedJV:
    title: str = ''
    status: str = ''
    customer: str = ''
    model_name: str = ''
    ap_company: str = ''
    ap_model: str = ''
    device: str = ''
    controller: str = ''
    application: str = ''
    assignee: str = ''
    start: str = ''
    end: str = ''
    link: str = ''


_FIELD_LABELS: dict[str, str] = {
    'status': 'Status',
    'customer': 'Customer',
    'model_name': 'Model Name',
    'ap_company': 'AP Company',
    'ap_model': 'AP Model',
    'device': 'Device',
    'controller': 'Controller',
    'application': 'Application',
    'assignee': '담당자',  # Korean — UTF-8 byte sequence
    'start': 'Start',
    'end': 'End',
}


def _extract_label_value(soup: BeautifulSoup, label: str) -> str:
    strong = soup.find(
        'strong',
        string=lambda s: s is not None and s.strip() == label,
    )
    if strong is None:
        return ''
    cell = strong.find_parent(['th', 'td', 'p'])
    if cell is None:
        return ''
    if cell.name in ('th', 'td'):
        sibling = cell.find_next_sibling(['td', 'th'])
        if sibling is None:
            return ''
        return sibling.get_text(strip=True)
    # Fallback: <p><strong>Label</strong>: value</p>
    full = cell.get_text(strip=True)
    if full.startswith(label):
        rest = full[len(label):].lstrip()
        if rest.startswith(':'):
            rest = rest[1:].lstrip()
        return rest
    return full


def _extract_link(soup: BeautifulSoup) -> str:
    strong = soup.find('strong', string=lambda s: s and s.strip() == 'Report Link')
    if strong is None:
        return ''
    parent = strong.find_parent(['th', 'td', 'p'])
    if parent is None:
        return ''
    sibling = parent.find_next_sibling(['td', 'th']) if parent.name in ('th', 'td') else parent
    if sibling is None:
        return ''
    a = sibling.find('a', href=True)
    return a['href'].strip() if a else ''


def parse_index_html(html_bytes: bytes) -> ParsedJV:
    """Best-effort 13-field extraction. Missing/unparseable fields → ''."""
    try:
        soup = BeautifulSoup(html_bytes, 'lxml')
    except Exception:
        # lxml may be unavailable — fall back to html.parser; still works.
        soup = BeautifulSoup(html_bytes, 'html.parser')
    h1 = soup.find('h1')
    title = h1.get_text(strip=True) if h1 else ''
    return ParsedJV(
        title=title,
        status=_extract_label_value(soup, 'Status'),
        customer=_extract_label_value(soup, 'Customer'),
        model_name=_extract_label_value(soup, 'Model Name'),
        ap_company=_extract_label_value(soup, 'AP Company'),
        ap_model=_extract_label_value(soup, 'AP Model'),
        device=_extract_label_value(soup, 'Device'),
        controller=_extract_label_value(soup, 'Controller'),
        application=_extract_label_value(soup, 'Application'),
        assignee=_extract_label_value(soup, '담당자'),
        start=_extract_label_value(soup, 'Start'),
        end=_extract_label_value(soup, 'End'),
        link=_extract_link(soup),
    )
```

### Example 4: Iframe sandbox in detail.html

```html
{# app_v2/templates/joint_validation/detail.html #}
{% extends "base.html" %}
{% block content %}
<div class="shell">
  <div class="page-head mb-3">
    <h1 class="page-title">{{ jv.title or jv.confluence_page_id | e }}</h1>
    <small class="text-muted">Confluence Page ID: {{ jv.confluence_page_id | e }}</small>
  </div>

  {# Properties table #}
  <div class="panel mb-3">
    <div class="panel-body">
      <table class="table table-sm">
        <tbody>
          <tr><th>Status</th><td>{{ jv.status | e }}</td></tr>
          <tr><th>Customer</th><td>{{ jv.customer | e }}</td></tr>
          <tr><th>Model Name</th><td>{{ jv.model_name | e }}</td></tr>
          <tr><th>AP Company</th><td>{{ jv.ap_company | e }}</td></tr>
          <tr><th>AP Model</th><td>{{ jv.ap_model | e }}</td></tr>
          <tr><th>Device</th><td>{{ jv.device | e }}</td></tr>
          <tr><th>Controller</th><td>{{ jv.controller | e }}</td></tr>
          <tr><th>Application</th><td>{{ jv.application | e }}</td></tr>
          <tr><th>담당자</th><td>{{ jv.assignee | e }}</td></tr>
          <tr><th>Start</th><td>{{ jv.start | e }}</td></tr>
          <tr><th>End</th><td>{{ jv.end | e }}</td></tr>
          <tr><th>Report Link</th>
            <td>
              {% if jv.link %}
                <a href="{{ jv.link | e }}" target="_blank" rel="noopener noreferrer">
                  <i class="bi bi-link-45deg"></i> {{ jv.link | e }}
                </a>
              {% endif %}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  {# Iframe sandbox — inline styles render, scripts blocked, popups allowed for external links #}
  <div class="panel">
    <div class="panel-body p-0">
      <iframe
        src="/static/joint_validation/{{ jv.confluence_page_id | e }}/index.html"
        sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"
        style="width: 100%; height: 80vh; border: 0;"
        loading="lazy"
        title="Confluence export — {{ jv.title | e }}"></iframe>
    </div>
  </div>
</div>
{% endblock %}
```

### Example 5: Static mount in main.py

```python
# app_v2/main.py — add BEFORE the existing app.mount("/static", ...) line
app.mount(
    "/static/joint_validation",
    StaticFiles(
        directory="content/joint_validation",
        html=False,
        follow_symlink=False,
    ),
    name="joint_validation_static",
)

# Existing line — keep it AFTER the JV mount so longest-prefix wins.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Lifespan addition: mkdir content/joint_validation alongside content/platforms.
# Inside the existing lifespan() function:
jv_dir = Path("content/joint_validation")
try:
    jv_dir.mkdir(parents=True, exist_ok=True)
except OSError as exc:
    _log.warning("Failed to create content/joint_validation/: %s", exc)
```

---

## State of the Art

| Old approach | Current approach | When changed | Impact |
|---|---|---|---|
| Curated YAML (`config/overview.yaml` listing platforms) | Drop-folder discovery (`content/joint_validation/<id>/index.html`) | This phase (2026-04-30) | Onboarding shifts from in-app form → file drop. |
| `<select>` filter dropdowns (Phase 2) | `picker_popover` checklist popovers (Phase 5; reused here) | v2.0 Phase 5 (2026-04-28) | Multi-select with debounced auto-commit; no Apply button. |
| Em-dash sentinel `—` for missing fields (Phase 5 D-OV-09) | Blank string `""` for missing fields (D-JV-05) | This phase | Cleaner table cells per user preference. |
| Per-platform markdown content + frontmatter | Per-JV folder + raw HTML | This phase | No frontmatter parser; BS4 instead. |
| `pd.read_sql` deprecated text-SQL pattern | `pd.read_sql_query(sa.text(...))` (Browse + Ask) | v1.0 → maintained in v2.0 | Not relevant to this phase (no DB calls). |
| Streamlit shell | FastAPI + Bootstrap 5 + HTMX | v2.0 (2026-04-29) | Stack already locked; this phase is a v2.0-stack-only addition. |
| BS4 camelCase methods (`findAll`, etc.) | snake_case (`find_all`, etc.) | BS4 4.13 (2024-2025) | Use snake_case in new code. |
| Starlette `commonprefix` path-traversal check | `commonpath` (CVE-2023-29159 fix) | Starlette 0.27 (2023) | We run 1.0.0 — fully patched. |

**Deprecated / outdated patterns to avoid:**

- `findAll`, `findAllNext`, etc. — replaced by snake_case in BS4 4.13+; deprecation warnings now, removal in 5.0.
- `pd.read_sql(<text-string>, conn)` — deprecated in pandas 2.x (irrelevant here, but a project-wide convention).
- `lxml.iterparse(..., resolve_entities=True)` — XXE risk, lxml 6.1.0 changed default to `'internal'`; irrelevant for BS4 use but flagged for hygiene.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | The Confluence-export Page Properties macro emits `<table>...<tr><th><strong>Field</strong></th><td>value</td></tr></table>` shape in 2026 | §"BS4 Selector Strategy" Pattern 1 | Parser returns blank for primary shape; ALL JV rows get blanks. Fixture must come from a real export to verify. |
| A2 | The fallback shape `<p><strong>Field</strong>: value</p>` exists in real Confluence exports | §"BS4 Selector Strategy" Pattern 2 | Fallback never triggers (always primary shape). No regression risk; just unused code path. |
| A3 | `nl_service.max_context_tokens=30000` (CONTEXT.md D-JV-16) is shorthand for "the AgentConfig token cap" — the planner must decide whether to add a 30k-token input clamp to the JV summary text | §"AI Summary Reuse" + §"Project Constraints" | If interpreted incorrectly, large JV pages may overflow LLM context and cause API errors; if interpreted as no-op, we're fine. Recommend planner asks user. |
| A4 | Local SSD glob of ~100 numeric subdirs is sub-millisecond | §"Anti-Patterns" + §"Mtime Cache" | If real-world directory size grows to 10,000+ folders, glob cost becomes user-visible and we'd need to add glob caching (deferred per D-JV-08). Re-evaluate if discovery latency surfaces. |
| A5 | `lxml` has manylinux wheels for Python 3.13 on Linux x86_64 / aarch64 | §"Standard Stack" | Install fails on the deployment host; fall back to `html.parser` (which lxml-aware code already does at runtime per Pattern parser code Example 3). Low risk — `lxml` 6.1.0 wheels confirmed available on PyPI. |
| A6 | The user wants `target="_blank"` for external links inside the iframe (hence `allow-popups + allow-popups-to-escape-sandbox`) | §"iframe Sandbox" | If they wanted in-iframe navigation only, the sandbox is overspecified. Remove the `allow-popups*` flags if confirmed. |
| A7 | Confluence's HTML export is served as UTF-8 (or with a `<meta charset>` tag) | §"Korean Label Handling" | If a real export uses Shift-JIS / EUC-KR, BS4's encoding detection without `chardet` may guess wrong. Mitigation: declare a `chardet` dep if a fixture exhibits the issue. |
| A8 | The Phase 5 invariant test file should be REPLACED (not deleted outright) so similar policy guards continue protecting this phase's decisions | §"Cleanup Targets" | If the file is just deleted, future regressions slip. Recommend planner explicitly schedules `test_phase01_invariants.py` creation. |
| A9 | The summary route URL `POST /joint_validation/{id}/summary` does not collide with the detail page `GET /joint_validation/{id}` (different methods) | §"AI Summary Route Shape" | None — FastAPI dispatches by (method, path). Verified mentally against existing `POST /platforms/{id}/summary` + `GET /platforms/{id}` pattern. |

---

## Open Questions

1. **Should the JV summary text be input-truncated to ~30k tokens before being sent to the LLM?**
   - What we know: D-JV-16 says "the existing `nl_service.max_context_tokens=30000` cap is the final clamp". The constant lives on `app.core.agent.config.AgentConfig`, not `nl_service` itself. Phase 3's `summary_service` does not currently truncate input.
   - What's unclear: Is the clamp meant to (a) be applied as a ~120k character truncation on the stripped text, (b) flow through to `cfg.max_tokens` (which controls OUTPUT not input), or (c) be a documentation-only reference to the project's overall token budget?
   - Recommendation: planner asks user during plan-check; default to (a) if no answer (safest — avoids cloud OpenAI 400-too-many-tokens errors on long JV pages with large attachment lists).

2. **Should the `summary/_success.html` and `_error.html` templates be parameterized for cross-flow reuse, or duplicated under `joint_validation/`?**
   - What we know: Both templates currently take `platform_id`, `target_id`. The retry/regenerate buttons hardcode `/platforms/{platform_id}/summary` URLs.
   - What's unclear: Is the duplication cost (~50 lines × 2 files) more or less than the parameterization complexity (entity_id + entity_kind + url_prefix)?
   - Recommendation: parameterize the templates (rename `platform_id` → `entity_id`, add `summary_url` context variable). Single source of truth for the AI Summary card UI; no code duplication.

3. **Should the JV detail route live in `routers/joint_validation.py` or extend `routers/overview.py`?**
   - What we know: Phase 5 used `overview.py` for both listing and (legacy) add. Logically `/joint_validation/{id}` is a different surface area.
   - What's unclear: Is one-router-per-URL-prefix the project convention, or two-routers-per-domain?
   - Recommendation: NEW file `routers/joint_validation.py` for the detail + summary routes; keep `routers/overview.py` for the listing (URL `/overview` stays). Mirrors `routers/platforms.py` vs `routers/summary.py` separation.

4. **Should the `test_phase05_invariants.py` file be deleted, renamed, or kept for cross-version policy guards?**
   - What we know: Some assertions still hold (yaml.safe_load), some are obsolete (forbidden routes are different now).
   - Recommendation: REPLACE with `test_phase01_invariants.py` covering this phase's policy guards: no `yaml.load` (carries forward), no `add_platform` route (D-JV-07), no `OverviewEntity` symbol, BS4 used not regex, `^\d+$` regex enforced in store, sync `def` everywhere, no `\| safe` in JV templates, etc.

5. **Should the parser tolerate `<strong>` inside `<a>` (linkified labels)?**
   - What we know: Confluence sometimes wraps labels in glossary-link anchors: `<a href="..."><strong>Status</strong></a>`. The current locator (`find_parent(['th','td','p'])`) walks up past the `<a>` correctly. But if the value cell is the `<a>`'s parent (rare), behavior is undefined.
   - Recommendation: keep current locator. If a real Confluence export trips it, add a regression fixture and adjust.

---

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| Python 3.x | All app code | ✓ | 3.13.7 (.venv) [VERIFIED] | — |
| FastAPI | Routes, mounts | ✓ | 0.136.1 [VERIFIED] | — |
| Pydantic v2 | View-models | ✓ | 2.13.3 [VERIFIED] | — |
| Starlette | StaticFiles, TemplateResponse | ✓ | 1.0.0 [VERIFIED] | — |
| pytest | Tests | ✓ | 9.0.3 [VERIFIED] | — |
| FastAPI TestClient | Route tests | ✓ | (installed) [VERIFIED] | — |
| jinja2-fragments | block_names rendering | ✓ | (installed; no `__version__` attr) [VERIFIED] | — |
| openai | LLM client (Ollama + OpenAI) | ✓ | per requirements.txt `>=1.50` [VERIFIED via existing summary_service] | — |
| cachetools | TTLCache for summaries | ✓ | per requirements.txt `>=7.0,<8.0` [VERIFIED] | — |
| markdown-it-py | LLM output rendering | ✓ | per requirements.txt `[plugins]>=3.0` [VERIFIED] | — |
| **beautifulsoup4** | NEW for this phase | ✗ | (not yet installed) | None — required for D-JV-04. Planner adds to `requirements.txt`. |
| **lxml** | NEW for this phase (recommended) | ✗ | (not yet installed) | `html.parser` (stdlib) — slower but works. Parser code in Example 3 already falls back. |

**Missing dependencies with no fallback:**
- `beautifulsoup4` — required by every code path that touches `index.html`. **Planner MUST schedule a task that adds `beautifulsoup4>=4.12,<5.0` to `requirements.txt`** as the first task of the first plan.

**Missing dependencies with viable fallback:**
- `lxml` — viable fallback to `html.parser`. **Planner SHOULD add `lxml>=5.0,<7.0` regardless** to ensure consistent parsing behavior across dev and prod. Don't ship two parser regimes.

---

## Sources

### Primary (HIGH confidence — VERIFIED via tool or installed code)

- BS4 4.14.3 PyPI metadata — https://pypi.org/pypi/beautifulsoup4/json [VERIFIED 2026-04-30]
- lxml 6.1.0 PyPI metadata — https://pypi.org/pypi/lxml/json [VERIFIED 2026-04-30]
- Starlette 1.0.0 source — `.venv/lib/python3.13/site-packages/starlette/staticfiles.py` (post-CVE-2023-29159 `commonpath` + `realpath` + default-False symlink/html) [VERIFIED]
- FastAPI 0.136.1, Pydantic 2.13.3, Starlette 1.0.0, pytest 9.0.3 — `.venv/bin/python3 -c 'import X; print(X.__version__)'` [VERIFIED]
- Phase 5 source files — read in research session [VERIFIED]:
  - `app_v2/services/overview_grid_service.py` (390 lines)
  - `app_v2/templates/overview/index.html` (224 lines)
  - `app_v2/templates/overview/_grid.html` (130 lines)
  - `app_v2/templates/overview/_filter_bar.html` (87 lines)
  - `app_v2/templates/browse/_picker_popover.html` (135 lines)
  - `app_v2/static/js/popover-search.js` (head)
  - `app_v2/routers/overview.py` (370 lines)
  - `app_v2/services/summary_service.py` (233 lines)
  - `app_v2/services/llm_resolver.py` (90 lines)
  - `app_v2/services/content_store.py` (285 lines)
  - `app_v2/data/summary_prompt.py` (31 lines)
  - `app_v2/main.py` (183 lines)
  - `app_v2/templates/base.html` (78 lines)
  - `tests/v2/test_overview_routes.py` (head)
  - `tests/v2/test_phase05_invariants.py` (head)
- Phase 1 CONTEXT.md + DISCUSSION-LOG.md — `.planning/phases/01-overview-tab-auto-discover-platforms-from-html-files/01-CONTEXT.md` [VERIFIED]
- CLAUDE.md — `/home/yh/Desktop/02_Projects/Proj28_PBM2/CLAUDE.md` [VERIFIED]
- `.planning/PROJECT.md`, `.planning/STATE.md`, `.planning/ROADMAP.md` [VERIFIED]
- `.planning/config.json` (`nyquist_validation: false`) [VERIFIED]

### Secondary (MEDIUM confidence — official docs)

- Beautiful Soup 4.14.3 documentation — https://www.crummy.com/software/BeautifulSoup/bs4/doc/ [CITED]
- lxml ElementSoup parser comparison — https://lxml.de/elementsoup.html [CITED]
- MDN `<iframe>` element + sandbox attribute — https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe [CITED]
- web.dev "Play safely in sandboxed IFrames" — https://web.dev/articles/sandboxed-iframes [CITED]
- caniuse "iframe sandbox allow-same-origin" — https://caniuse.com/mdn-html_elements_iframe_sandbox_allow-same-origin [CITED]
- GHSA CVE-2023-29159 (Starlette path traversal) — https://github.com/Kludex/starlette/security/advisories/GHSA-v5gw-mw7f-84px [CITED]
- Atlassian Confluence Data Center 10.2 Page Properties Macro — https://confluence.atlassian.com/doc/page-properties-macro-184550024.html [CITED]
- Confluence HTML Export space tree — https://support.atlassian.com/confluence/kb/how-to-get-the-page-tree-structure-in-an-html-export/ [CITED]

### Tertiary (LOW — flagged for validation)

- (none — all critical claims verified through Primary or Secondary sources.)

---

## Metadata

**Confidence breakdown:**
- Standard stack — HIGH (versions verified via PyPI + .venv).
- Architecture / Phase 5 reuse map — HIGH (file:line pointers verified by reading on-disk files).
- BS4 selector strategy — HIGH (idiom is BS4-canonical; matches official docs).
- iframe sandbox attribute set — HIGH (recommendation matches MDN/web.dev current guidance).
- StaticFiles path-traversal defense — HIGH (Starlette 1.0.0 source read directly; post-CVE-2023-29159).
- Mtime cache pitfalls — HIGH (mirrors Phase 5 D-OV-12 verified pattern).
- Confluence-export HTML shape — MEDIUM (Atlassian docs confirm the macro structure exists; exact byte-shape only verifiable with a real export).
- AI Summary route shape — HIGH (existing summary_service.py source read; refactor path is mechanical).
- Test fixtures — HIGH for shape; MEDIUM for "matches what user will drop" (no real sample available).
- Common pitfalls — HIGH (documented from both Phase 3/5 RESEARCH.md and on-disk source).

**Research date:** 2026-04-30
**Valid until:** 2026-05-30 (30 days; stack is mature, BS4 / lxml / Starlette release cadences are slow).

---

*Research conducted by gsd-researcher; consumed by gsd-planner for plan generation.*
