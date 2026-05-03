---
phase: 01-overview-tab-auto-discover-platforms-from-html-files
verified: 2026-04-30T22:00:00Z
status: passed
score: 17/17 must-haves verified
overrides_applied: 0
---

# Phase 1: Overview Tab — Auto-discover Joint Validations Verification Report

**Phase Goal:** Replace the Overview tab's curated-Platform listing with auto-discovered Joint Validation rows parsed from `content/joint_validation/<numeric_id>/index.html` (BeautifulSoup4); add `/joint_validation/<id>` detail page (properties table + iframe sandbox of the Confluence export); reuse the Phase 5 grid/filter/sort + AI Summary modal patterns; delete the Platform-curated yaml + supporting code paths (D-JV-01..D-JV-17 locked in 01-CONTEXT.md).

**Verified:** 2026-04-30T22:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

ROADMAP.md does not declare success_criteria for this phase. Truths derived from goal + 17 D-JV-XX decisions in 01-CONTEXT.md and merged with PLAN must_haves across all 6 plans.

| #  | Truth (D-JV decision)                                                                                          | Status      | Evidence                                                                                                                                                                                                  |
| -- | -------------------------------------------------------------------------------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | D-JV-01: Top-nav label "Joint Validation"; URL `/` preserved                                                   | VERIFIED    | `app_v2/templates/base.html` line 38 contains `<i class="bi bi-list-ul"></i> Joint Validation`; live `GET /` returns 200 and "Overview</a>" no longer present                                              |
| 2  | D-JV-02: Source = `content/joint_validation/<numeric_id>/index.html` glob                                      | VERIFIED    | `joint_validation_store.py` exports `JV_ROOT = Path("content/joint_validation")` + `glob("*/index.html")` in `discover_joint_validations`                                                                |
| 3  | D-JV-03: Folder name `^\d+$` validation; non-numeric silently skipped                                          | VERIFIED    | `PAGE_ID_PATTERN = re.compile(r"^\d+$")` enforced in store + `Path(pattern=r"^\d+$", min_length=1, max_length=32)` at router; live `/joint_validation/abc` returns 422                                    |
| 4  | D-JV-04: BS4 extracts 13 fields incl. Korean `담당자` byte-equal                                                | VERIFIED    | `joint_validation_parser.py` contains literal `"담당자"` 4× incl. assignee mapping; 10/10 parser tests pass; primary + fallback fixture shapes both extract 13 fields                                       |
| 5  | D-JV-05: Missing field → blank `""` (NOT em-dash); title falls back to confluence_page_id                       | VERIFIED    | `JointValidationRow` defaults all fields `= ""`; invariant test 6 enforces zero `= "—"`; `_grid.html` zero `"—"` matches; service applies `parsed.title or page_id`                                       |
| 6  | D-JV-06: Platform-curated yaml + code paths deleted                                                            | VERIFIED    | `config/overview.yaml`, `overview_store.py`, `overview_filter.py`, `overview_grid_service.py` all confirmed absent; `grep -rn` returns zero references                                                    |
| 7  | D-JV-07: `POST /overview/add` deleted                                                                          | VERIFIED    | Live `POST /overview/add` returns 404; `grep -c 'add_platform\|@router.post("/overview/add"'` returns 0 in `overview.py`                                                                                  |
| 8  | D-JV-08: Mtime-keyed in-process parse cache                                                                    | VERIFIED    | `_PARSE_CACHE: dict[tuple[str, int], ParsedJV]` keyed by `(page_id, mtime_ns)`; 8/8 store tests pass incl. mtime invalidation + sibling cache survival                                                    |
| 9  | D-JV-09: Drop-folder workflow only (no add form anywhere)                                                      | VERIFIED    | `POST /overview/add` 404 (truth 7); glob NOT cached → re-globbed every request; comment in `discover_joint_validations` documents this                                                                    |
| 10 | D-JV-10: Default sort `start desc`, tiebreaker `confluence_page_id ASC`; blank starts to END both directions   | VERIFIED    | `DEFAULT_SORT_COL = "start"`, `DEFAULT_SORT_ORDER = "desc"`; grid_service tests `test_default_sort_start_desc_tiebreaker_page_id_asc` + `test_blank_start_sorts_to_end_regardless_of_order` pass          |
| 11 | D-JV-11: 6 popover-checklist filters (status, customer, ap_company, device, controller, application)          | VERIFIED    | `_filter_bar.html` contains 6 `picker_popover(` invocations; `FILTERABLE_COLUMNS = ("status", "customer", "ap_company", "device", "controller", "application")`; invariant test 15 enforces             |
| 12 | D-JV-12: GET /overview listing + GET /joint_validation/<id> detail (properties + iframe)                       | VERIFIED    | Live `GET /overview` returns 200; `GET /joint_validation/<numeric>` returns 200 with properties table + `<iframe src="/static/joint_validation/<id>/index.html">`; route_test 7 passes                  |
| 13 | D-JV-13: StaticFiles mount `/static/joint_validation` registered before `/static`; html=False; follow_symlink=False | VERIFIED | `main.py` line 122 mounts JV (line 133 mounts `/static`); `directory="content/joint_validation"`, `html=False`, `follow_symlink=False`, `name="joint_validation_static"` all present                  |
| 14 | D-JV-14: URL state shape (status/customer/ap_company/device/controller/application/sort/order)                | VERIFIED    | `_parse_filter_dict` + `_build_overview_url` preserved verbatim from Phase 5; route_test 5 verifies HX-Push-Url contains canonical query string                                                            |
| 15 | D-JV-15: Two row buttons (Report Link + AI Summary); URL sanitizer drops dangerous schemes                     | VERIFIED    | `_grid.html` contains both buttons + Report Link `target="_blank" rel="noopener noreferrer"`; `_sanitize_link` 5-scheme tuple `("javascript:", "data:", "vbscript:", "file:", "about:")` invariant-tested |
| 16 | D-JV-16: AI Summary input pre-processing decomposes `<script>`, `<style>`, `<img>`                             | VERIFIED    | `joint_validation_summary._strip_to_text` calls `soup(["script", "style", "img"])` + `decompose()`; cache key `hashkey("jv", ...)`; 11/11 JV summary tests pass                                           |
| 17 | D-JV-17: Empty state copy verbatim                                                                             | VERIFIED    | `_grid.html` contains `"No Joint Validations yet."` + `colspan="13"` + `content/joint_validation/&lt;page_id&gt;/index.html`; route_test 14 enforces                                                      |

**Score:** 17/17 truths verified

### Required Artifacts

Three-level verification (exists, substantive, wired) for every Plan-listed artifact.

| Artifact                                                    | Expected                                                              | Status     | Details                                                                                                       |
| ----------------------------------------------------------- | --------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------- |
| `requirements.txt`                                          | `beautifulsoup4>=4.12,<5.0` + `lxml>=5.0,<7.0`                        | VERIFIED   | Both lines present at expected pin syntax                                                                     |
| `app_v2/templates/summary/_success.html`                    | `entity_id` + `summary_url` parameterization                          | VERIFIED   | Contains `entity_id` 7×, `summary_url` 5×                                                                     |
| `app_v2/templates/summary/_error.html`                      | Same parameterization                                                  | VERIFIED   | Contains `entity_id` 4×, `summary_url` 2×                                                                     |
| `app_v2/routers/summary.py`                                 | TemplateResponse passes `entity_id` + `summary_url`                   | VERIFIED   | Both context keys present in both render call sites                                                           |
| `app_v2/services/joint_validation_parser.py`                | `parse_index_html`, `ParsedJV`, `_extract_label_value`, `_extract_link` | VERIFIED  | All 4 exports present; lxml→html.parser fallback; Korean literal preserved                                    |
| `app_v2/services/joint_validation_store.py`                 | `discover_joint_validations`, `get_parsed_jv`, `JV_ROOT`, `PAGE_ID_PATTERN` | VERIFIED | All exports present; mtime cache + glob discovery                                                              |
| `app_v2/services/joint_validation_grid_service.py`          | View-model builder + helpers                                          | VERIFIED   | `JointValidationRow`, `JointValidationGridViewModel`, `build_joint_validation_grid_view_model`, 6-FILTERABLE + 12-SORTABLE constants |
| `app_v2/services/joint_validation_summary.py`               | `get_or_generate_jv_summary`, `_strip_to_text`                        | VERIFIED   | Both exports present; `hashkey("jv", ...)` discriminator; D-JV-16 decompose                                   |
| `app_v2/data/jv_summary_prompt.py`                          | `JV_SYSTEM_PROMPT` + `JV_USER_PROMPT_TEMPLATE` (`{markdown_content}` placeholder) | VERIFIED | Both exports + `<jv_page>` anti-injection wrap                                                                 |
| `app_v2/services/summary_service.py`                        | `_call_llm_with_text` extracted; `_call_llm_single_shot` delegates    | VERIFIED   | Helper present; delegation single-line; tests 50/50 pass                                                       |
| `app_v2/main.py`                                            | StaticFiles mount + lifespan mkdir + router register                  | VERIFIED   | JV mount line 122 (before `/static` line 133); `jv_dir` mkdir; `app.include_router(joint_validation.router)` |
| `app_v2/routers/overview.py`                                | Rewritten for JV listing; legacy helpers deleted                       | VERIFIED   | Imports JV grid service; legacy symbols all 0 grep matches; sync def only                                     |
| `app_v2/routers/joint_validation.py`                        | Detail + summary routes                                                | VERIFIED   | Both routes present; sync def only; canonical helpers used; X-Regenerate parsing canonical                    |
| `app_v2/templates/base.html`                                | Top-nav label "Joint Validation"                                       | VERIFIED   | Label present; old "Overview</a>" gone                                                                         |
| `app_v2/templates/overview/index.html`                      | 3 OOB blocks; sortable_th macro INSIDE grid block                     | VERIFIED   | `block grid` + `block count_oob` + `block filter_badges_oob`; macro defined inside grid block (Pitfall 8)     |
| `app_v2/templates/overview/_grid.html`                      | 12 sortable headers + Action column + verbatim D-JV-17 empty state    | VERIFIED   | 12 `sortable_th(` calls; `colspan="13"`; verbatim empty-state copy                                             |
| `app_v2/templates/overview/_filter_bar.html`                | 6 picker_popover invocations + form_id                                | VERIFIED   | 6 invocations + `form_id="overview-filter-form"` 6×; reuses macro from `browse/_picker_popover.html`          |
| `app_v2/templates/joint_validation/detail.html`             | Properties table + locked iframe sandbox                              | VERIFIED   | Sandbox literal exact; NO `allow-scripts`/`allow-top-navigation`/`allow-forms`; Korean 담당자 row present       |
| `tests/v2/fixtures/joint_validation_sample.html`            | Primary-shape fixture                                                  | VERIFIED   | UTF-8, contains `<strong>담당자</strong>` byte-equal                                                            |
| `tests/v2/fixtures/joint_validation_fallback_sample.html`   | `<p><strong>Field</strong>: value</p>` shape                          | VERIFIED   | UTF-8, fallback shape covers blank-status case                                                                 |
| `tests/v2/test_joint_validation_routes.py`                  | 15 end-to-end TestClient tests                                        | VERIFIED   | 15 tests; all pass                                                                                             |
| `tests/v2/test_joint_validation_invariants.py`              | 15 grep-based source-level guards                                     | VERIFIED   | 15 tests; all pass; ran in 0.20s                                                                               |
| `tests/v2/test_joint_validation_parser.py`                  | 10 parser tests                                                        | VERIFIED   | 10 tests pass                                                                                                  |
| `tests/v2/test_joint_validation_store.py`                   | 8 store tests                                                          | VERIFIED   | 8 tests pass                                                                                                   |
| `tests/v2/test_joint_validation_grid_service.py`            | 12 grid tests                                                          | VERIFIED   | 12 tests pass                                                                                                  |
| `tests/v2/test_joint_validation_summary.py`                 | 11 summary tests                                                       | VERIFIED   | 11 tests pass                                                                                                  |
| Deletions: `config/overview.yaml`, `overview_store.py`, `overview_filter.py`, `overview_grid_service.py`, 4 legacy tests | All 8 files absent | VERIFIED  | `ls` confirms each path missing; `test_overview_filter.py` was already absent at plan start                  |

### Key Link Verification

| From                                                         | To                                                              | Via                                                          | Status | Details                                                                  |
| ------------------------------------------------------------ | --------------------------------------------------------------- | ------------------------------------------------------------ | ------ | ------------------------------------------------------------------------ |
| `app_v2/routers/summary.py`                                  | `summary/_success.html` & `_error.html`                         | TemplateResponse context with `entity_id` + `summary_url`    | WIRED  | Both context keys present at both call sites                             |
| `app_v2/services/joint_validation_store.py`                  | `app_v2/services/joint_validation_parser.py`                    | `from … import parse_index_html, ParsedJV`                   | WIRED  | Direct top-level import                                                   |
| `app_v2/services/joint_validation_grid_service.py`           | `app_v2/services/joint_validation_store.py`                     | local import inside `build_joint_validation_grid_view_model` | WIRED  | `discover_joint_validations` + `get_parsed_jv` imported and called       |
| `app_v2/services/joint_validation_summary.py`                | `app_v2/services/summary_service.py`                            | `from … import _call_llm_with_text, _summary_cache, _summary_lock, SummaryResult` | WIRED | All needed symbols imported                                              |
| `app_v2/services/joint_validation_summary.py`                | `app_v2/data/jv_summary_prompt.py`                              | `from … import JV_SYSTEM_PROMPT, JV_USER_PROMPT_TEMPLATE`    | WIRED  | Both prompts imported and passed to `_call_llm_with_text`                |
| `app_v2/main.py`                                             | `/static/joint_validation` static mount                         | `app.mount("/static/joint_validation", StaticFiles(...))`    | WIRED  | Mount registered line 122 (BEFORE `/static`); html=False, follow_symlink=False |
| `app_v2/routers/overview.py`                                 | `app_v2.services.joint_validation_grid_service`                 | import + call `build_joint_validation_grid_view_model`       | WIRED  | Called 2× (GET / and POST /overview/grid)                                |
| `app_v2/routers/joint_validation.py`                         | `app_v2.services.joint_validation_summary`                      | import + call `get_or_generate_jv_summary`                   | WIRED  | Called in summary route                                                   |
| `app_v2/routers/joint_validation.py`                         | `app_v2/templates/joint_validation/detail.html`                 | `templates.TemplateResponse`                                 | WIRED  | Detail route renders this template                                       |
| `app_v2/templates/overview/index.html`                       | `app_v2/templates/overview/_grid.html`                          | Jinja `{% include "overview/_grid.html" %}`                  | WIRED  | Inside `{% block grid %}`                                                 |
| `app_v2/templates/overview/index.html`                       | `app_v2/templates/overview/_filter_bar.html`                    | `{% include "overview/_filter_bar.html" %}`                  | WIRED  | At top of content shell                                                  |
| `app_v2/templates/overview/_filter_bar.html`                 | `app_v2/templates/browse/_picker_popover.html`                  | `{% from … import picker_popover %}` + 6 macro calls         | WIRED  | Macro reused unchanged                                                   |
| `app_v2/templates/overview/_grid.html`                       | `/joint_validation/{confluence_page_id}/summary`                | `hx-post` attribute on AI Summary button                     | WIRED  | Present with `hx-target="#summary-modal-body"`                            |
| `app_v2/templates/joint_validation/detail.html`              | `/static/joint_validation/{confluence_page_id}/index.html`      | `<iframe src=…>`                                             | WIRED  | Present with locked sandbox attribute                                    |

### Data-Flow Trace (Level 4)

Live verification with a real JV folder dropped into `content/joint_validation/`.

| Artifact                                          | Data Variable                          | Source                                                              | Produces Real Data | Status   |
| ------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------- | ------------------ | -------- |
| `templates/overview/_grid.html`                   | `vm.rows[]` (per-row cell render)      | `build_joint_validation_grid_view_model` → `discover_joint_validations` → `get_parsed_jv` | Yes (real BS4 parse) | FLOWING |
| `templates/joint_validation/detail.html`          | `jv` (JointValidationRow)              | `get_parsed_jv(page_id, index_html)` in `routers/joint_validation.py` detail route | Yes              | FLOWING |
| `<iframe src=…>` static mount                     | `index.html` bytes                     | StaticFiles handler reads `content/joint_validation/<id>/index.html` | Yes (sample file body served verbatim) | FLOWING |
| `templates/summary/_success.html`                 | `summary_html`                         | `render_markdown(result.text)` in router (after `_call_llm_with_text`) | Yes (when LLM configured; route_test_13 mocks the LLM and verifies render path) | FLOWING |
| `templates/overview/_grid.html` empty-state branch | `vm.rows` length zero                  | empty `JV_ROOT`                                                     | Verbatim D-JV-17 copy renders | FLOWING |

Live data-flow verified: a fixture-dropped folder produced "Acme" customer, "In Progress" status, "Live Verification Sample" title, and `/joint_validation/<id>` link in the listing HTML; the detail page rendered the same metadata + iframe pointing at the static-served file.

### Behavioral Spot-Checks

| Behavior                                                | Command                                                                        | Result | Status |
| ------------------------------------------------------- | ------------------------------------------------------------------------------ | ------ | ------ |
| Module imports cleanly                                  | `python -c "from app_v2.main import app"`                                      | OK     | PASS   |
| Full pytest suite                                       | `pytest tests/v2/ -q`                                                          | 360 passed, 5 skipped, 4 warnings | PASS |
| `GET /` → 200                                           | TestClient                                                                     | 200    | PASS   |
| `GET /overview` → 200                                   | TestClient                                                                     | 200    | PASS   |
| `POST /overview/grid` → 200                             | TestClient with `sort=start, order=desc`                                       | 200    | PASS   |
| `POST /overview/add` → 404                              | TestClient                                                                     | 404    | PASS   |
| `GET /joint_validation/abc` → 422                       | TestClient                                                                     | 422    | PASS   |
| `GET /joint_validation/9999` → 404                      | TestClient                                                                     | 404    | PASS   |
| `GET /static/joint_validation/../etc/passwd` → 404      | TestClient                                                                     | 404    | PASS   |
| `GET /browse` regression                                | TestClient                                                                     | 200    | PASS   |
| `GET /ask` regression                                   | TestClient                                                                     | 200    | PASS   |
| Live JV folder appears in listing                       | drop folder → GET /overview → assert "Acme" + title link                       | All present | PASS |
| Live JV detail renders properties + iframe + sandbox    | GET /joint_validation/<id> → assert sandbox literal + iframe src + Korean row | All present | PASS |
| Static mount serves index.html                          | GET /static/joint_validation/<id>/index.html → assert body bytes               | Bytes match | PASS |
| JV invariants policy guards                             | `pytest tests/v2/test_joint_validation_invariants.py`                          | 15/15 pass | PASS |
| JV route coverage                                       | `pytest tests/v2/test_joint_validation_routes.py`                              | 15/15 pass | PASS |

### Requirements Coverage

All 17 requirement IDs declared in PLAN frontmatter cross-referenced against `01-CONTEXT.md` (the canonical D-JV-XX decisions document; no separate `REQUIREMENTS.md` exists for this phase).

| Requirement | Source Plan(s)        | Description                                                       | Status     | Evidence                                              |
| ----------- | --------------------- | ----------------------------------------------------------------- | ---------- | ----------------------------------------------------- |
| D-JV-01     | 04, 05, 06            | Overview tab → Joint Validation label                             | SATISFIED  | Truths 1, 11, 17                                      |
| D-JV-02     | 02                    | Source = `content/joint_validation/<id>/index.html`               | SATISFIED  | Truth 2                                               |
| D-JV-03     | 02                    | `^\d+$` folder regex                                              | SATISFIED  | Truth 3                                               |
| D-JV-04     | 01, 02                | BS4 13-field extraction                                           | SATISFIED  | Truth 4                                               |
| D-JV-05     | 02, 05                | Blank `""` for missing fields                                     | SATISFIED  | Truth 5                                               |
| D-JV-06     | 06                    | Delete Platform-curated yaml + code                               | SATISFIED  | Truth 6 (8 deletions confirmed)                       |
| D-JV-07     | 04, 06                | Delete `POST /overview/add`                                        | SATISFIED  | Truth 7                                               |
| D-JV-08     | 02                    | Mtime-keyed in-process cache                                       | SATISFIED  | Truth 8                                               |
| D-JV-09     | 02, 04                | Drop-folder workflow only                                         | SATISFIED  | Truth 9                                               |
| D-JV-10     | 02                    | Default sort start desc + tiebreaker                              | SATISFIED  | Truth 10                                              |
| D-JV-11     | 02, 05                | 6 popover-checklist filters                                       | SATISFIED  | Truth 11                                              |
| D-JV-12     | 04, 05, 06            | Routes: listing + detail                                          | SATISFIED  | Truth 12                                              |
| D-JV-13     | 04, 05, 06            | StaticFiles mount + lifespan mkdir                                | SATISFIED  | Truth 13                                              |
| D-JV-14     | 02, 04                | URL state shape                                                   | SATISFIED  | Truth 14                                              |
| D-JV-15     | 01, 04, 05, 06        | Two row buttons + URL sanitizer                                   | SATISFIED  | Truth 15                                              |
| D-JV-16     | 01, 03, 04            | AI Summary input pre-processing                                   | SATISFIED  | Truth 16                                              |
| D-JV-17     | 05, 06                | Empty state copy verbatim                                         | SATISFIED  | Truth 17                                              |

**Orphaned requirements:** None — every D-JV-XX in the phase scope appears in at least one plan's `requirements:` field. Union coverage spans D-JV-01 through D-JV-17 with no gaps.

### Anti-Patterns Found

Files modified by this phase scanned for stub patterns; only documentation/comment occurrences flagged informationally.

| File                                                  | Line   | Pattern                                                       | Severity | Impact                                                                                                                  |
| ----------------------------------------------------- | ------ | ------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------- |
| `app_v2/services/joint_validation_summary.py`         | 65-68  | `try BeautifulSoup(html, "lxml") except Exception: html.parser` | Info     | Defensive fallback on a hard dep; same pattern duplicated in parser (IN-06 in 01-REVIEW.md). Acceptable.               |
| `app_v2/services/joint_validation_parser.py`          | 114-117 | Same fallback                                                | Info     | See above.                                                                                                              |
| `app_v2/routers/overview.py`                          | 103-204 | "Transitional alias" / "Plan 05 deletes" comments             | Info     | IN-04 in 01-REVIEW.md. Comments document context rationale; not blocking.                                              |
| `app_v2/services/joint_validation_store.py`           | 68-70  | `clear_parse_cache()` test helper callable from app code      | Info     | IN-05 in 01-REVIEW.md. Convention-only; no production caller.                                                          |

No blocker stubs found. No `TODO`/`FIXME`/`PLACEHOLDER` markers in production paths. No `return null`/`return []`/empty handler placeholders flowing to user-visible output. The 4 warnings catalogued in `01-REVIEW.md` (WR-01 through WR-04) are non-blocking quality nits acknowledged by the review.

### Human Verification Required

None. All goal-achieving truths are programmatically verified by the 360-test suite + live TestClient route checks + invariant grep guards. Visual UI quality (Bootstrap chrome, modal animation, popover UX) inherits from Phase 4 + Phase 5 patterns and was not changed by this phase. The iframe-rendered Confluence body is the only user-visible content that this phase introduces; its security posture is byte-pinned by the locked sandbox literal + invariant test, and its rendering correctness depends on the Confluence-export HTML that the user drops into `content/joint_validation/`. No human-only verification gates remain.

### Gaps Summary

No gaps. Phase 1 ships every D-JV-01 through D-JV-17 contract; deletes the obsolete Platform-curated machinery; preserves Browse/Ask/Platforms/Summary tabs; adds 30 new tests (15 routes + 15 invariants) on top of the 56 unit tests added by Plans 01-03; full v2 suite at 360 passed / 5 skipped (zero regressions vs Phase 5 baseline minus the deliberate skips).

---

_Verified: 2026-04-30T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
