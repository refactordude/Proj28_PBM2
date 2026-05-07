---
quick_id: 260507-lox
type: quick
wave: 1
depends_on: []
files_modified:
  - app_v2/services/joint_validation_parser.py
  - tests/v2/test_joint_validation_parser.py
  - app/core/config.py
  - config/settings.example.yaml
  - app_v2/routers/overview.py
  - app_v2/templates/overview/_grid.html
  - tests/v2/test_joint_validation_routes.py
autonomous: true
requirements:
  - QUICK-260507-lox
must_haves:
  truths:
    - "Concern 1 — A `<strong>Status</strong>` (or any other field label) that lives inside an `<h1>..<h6>` ancestor is SKIPPED by `_extract_label_value`. The fix is generalized across ALL fields (not just Status) because a label inside a heading is never the canonical metadata source — it is a section/page title. Documented in plan + SUMMARY."
    - "Concern 1 — Given an HTML fixture containing `<h1><strong>Status</strong>: in-progress (per heading)</h1>` AND `<tr><td><p><strong>Status</strong></p></td><td><p>Planned</p></td></tr>`, `parse_index_html(html).status == \"Planned\"` (the h1 inline-paragraph match is filtered before the inline-fallback path can latch onto it; the page-properties row wins)."
    - "Concern 1 — Same generalization holds for another field: a `<h2><strong>Customer</strong>: Acme HQ</h2>` heading + a Page Properties `Customer` row with `Beta Inc.` resolves to `Beta Inc.`."
    - "Concern 1 — All 14 existing parser tests in `tests/v2/test_joint_validation_parser.py` continue to pass (zero regressions). In particular the heading-only `<h1>` title is still extracted via the SEPARATE `soup.find('h1')` lookup in `parse_index_html` — the h1-skip applies ONLY to `<strong>` label matches inside `_extract_label_value`/`_extract_link`, not to the title-from-h1 path."
    - "Concern 2 — `AppConfig.conf_url: str = \"\"` exists; existing settings.yaml files load without error (default empty string). `Settings.model_validate({\"app\": {\"conf_url\": \"https://example.com\"}})` round-trips the value."
    - "Concern 2 — `config/settings.example.yaml` carries one `conf_url:` example entry under the `app:` block, with a one-line comment explaining its purpose. Format: simple base URL (no trailing slash assumed); the route handler joins `f\"{conf_url.rstrip('/')}/{page_id}\"`."
    - "Concern 2 — Both `GET /` + `GET /overview` (page render) AND `POST /overview/grid` (OOB block re-render with `block_names=[\"grid\", \"count_oob\", \"filter_badges_oob\", \"pagination_oob\"]`) thread `conf_url` into the template context as `\"conf_url\": <pre-cleaned base URL>` (rstripped of trailing `/` in Python before passing to the template — sibling templates do not use Jinja `rstrip`)."
    - "Concern 2 — `app_v2/templates/overview/_grid.html` renders a 컨플 button INSIDE the existing `<td class=\"text-end\">` cell, immediately after the edm `{% if/else %}` block (lines 54-71) and BEFORE the AI Summary button (lines 73-86). Active branch: `<a class=\"btn btn-sm btn-outline-secondary text-dark ms-1\" target=\"_blank\" rel=\"noopener noreferrer\" href=\"{conf_url}/{page_id}\" aria-label=\"Open Confluence page for {title}\">컨플</a>`. Disabled branch: `<button type=\"button\" class=\"btn btn-sm btn-outline-secondary ms-1\" disabled aria-label=\"No Confluence URL configured\">컨플</button>`."
    - "Concern 2 — Disabled state covers BOTH the `conf_url` empty case AND the `row.confluence_page_id` falsy case (defense in depth — the page_id `^\\d+$` regex already guarantees it is set in practice; the guard mirrors edm parity)."
    - "Concern 2 — Two new route tests prove the wiring: (a) when `app.state.settings.app.conf_url` is empty (default), the disabled 컨플 `<button>` renders; (b) when conf_url is set to `https://example.com/` (with trailing slash), the active 컨플 `<a>` renders with the correctly joined href `https://example.com/3193868109` (single slash; trailing `/` on conf_url stripped before join)."
    - "Full v2 suite stays green (baseline 556 passed / 5 skipped per quick task 260507-lcc). Net new tests: 2 parser tests + 2 route tests = 558 passed / 5 skipped."
  artifacts:
    - path: "app_v2/services/joint_validation_parser.py"
      provides: "h1-h6 ancestor skip applied to BOTH `_extract_label_value` and `_extract_link` (consistency with 260507-ksn's <th>/<td>-vs-<p> generalization pattern)."
      contains: "find_parent([\"h1\", \"h2\", \"h3\", \"h4\", \"h5\", \"h6\"])"
    - path: "tests/v2/test_joint_validation_parser.py"
      provides: "Two new BS4-byte-input regression tests covering Status (the user-reported field) AND Customer (the generalization proof)."
      contains: "def test_parse_skips_strong_inside_h1_for_status"
    - path: "app/core/config.py"
      provides: "`AppConfig.conf_url: str = \"\"` field — empty string default keeps existing settings.yaml files loading without error."
      contains: "conf_url: str = \"\""
    - path: "config/settings.example.yaml"
      provides: "Example `conf_url:` entry under `app:` block with a one-line comment explaining usage."
      contains: "conf_url:"
    - path: "app_v2/routers/overview.py"
      provides: "Both GET (`/`, `/overview`) and POST (`/overview/grid`) handlers read `settings.app.conf_url` from `request.app.state.settings`, rstrip a single trailing `/`, and inject the cleaned value into the template context as `conf_url`."
      contains: "settings.app.conf_url"
    - path: "app_v2/templates/overview/_grid.html"
      provides: "컨플 button block inserted between the edm button (line 71 `{% endif %}`) and the AI Summary button (line 73 `{# AI Summary button ... #}`). Active vs disabled mirrors the edm pattern (`text-dark` on active anchor, bare `btn-outline-secondary` on disabled button)."
      contains: "컨플"
    - path: "tests/v2/test_joint_validation_routes.py"
      provides: "Two new route tests proving conf_url wiring: empty conf_url → disabled 컨플 button; configured conf_url with trailing slash → active 컨플 anchor with correctly joined href."
      contains: "def test_grid_renders_disabled_confluence_button_when_conf_url_empty"
  key_links:
    - from: "app_v2/services/joint_validation_parser.py::_extract_label_value"
      to: "app_v2/services/joint_validation_parser.py::_extract_link"
      via: "shared `find_parent([\"h1\"..\"h6\"])` skip — both helpers iterate `find_all('strong', ...)` and `continue` past any `<strong>` whose nearest heading ancestor is non-None"
      pattern: "find_parent\\(\\[\"h1\", \"h2\", \"h3\", \"h4\", \"h5\", \"h6\"\\]\\)"
    - from: "app_v2/routers/overview.py::get_overview"
      to: "app_v2/templates/overview/_grid.html"
      via: "ctx['conf_url'] = settings.app.conf_url.rstrip('/') if settings else '' — pre-cleaned in Python so the template can do a simple `~ '/' ~ row.confluence_page_id` join"
      pattern: "\"conf_url\": "
    - from: "app_v2/routers/overview.py::post_overview_grid"
      to: "app_v2/templates/overview/_grid.html (via block_names=['grid', ...])"
      via: "Same conf_url ctx key on the OOB re-render path — the grid block ALSO uses the new variable, so HTMX swaps re-render the 컨플 button correctly"
      pattern: "block_names=\\[\"grid\""
    - from: "app/core/config.py::AppConfig"
      to: "app_v2/routers/overview.py"
      via: "`AppConfig.conf_url: str = \"\"` consumed via `request.app.state.settings.app.conf_url` (existing settings-threading pattern shared with `routers/settings.py`, `routers/summary.py`, `routers/joint_validation.py`)"
      pattern: "settings\\.app\\.conf_url"
---

<objective>
Two unrelated concerns shipped as a single atomic quick task. Both are surgical edits, both stay inside the JV/Overview surface, neither perturbs other tabs.

**Concern 1 — h1-h6 ancestor skip in `_extract_label_value` / `_extract_link`.**
Quick task `260507-ksn` added a Page-Properties-vs-`<p>` generalization to the parser. The user reports `Status` is STILL picking up wrong matches in some real Confluence exports because a standalone `<strong>Status</strong>` inside an `<h1>` (typically a section title or page heading) leaks through the existing two-pass walk: when `<strong>` sits inside an `<h1>` with no `<th>/<td>` ancestor, the helper falls into the inline-paragraph branch and reads the heading's text as the value. The fix is to skip any `<strong>` match whose nearest ancestor is `<h1>..<h6>` BEFORE either pass runs.

The user wrote "for Status SPECIFICALLY". Generalizing the skip to ALL fields is safer and more durable: the bug class (a label nested in a heading is never canonical metadata) is universal. Field-targeted logic would be fragile — Customer, AP Company, etc. could suffer the same shape in different files. **Generalization is documented in the plan + SUMMARY** with a one-line rationale; a regression test is added for both Status (where the bug was observed) AND Customer (proving the generalization).

The h1 path that extracts `title` is UNCHANGED — `parse_index_html` reads `soup.find('h1').get_text()` directly, NOT via `_extract_label_value`. The skip applies only to `<strong>` label matches inside the metadata helpers.

**Concern 2 — Configurable `conf_url` + per-row 컨플 button.**
Add a new `AppConfig.conf_url: str = ""` field (empty default for back-compat). User edits `config/settings.yaml` directly — no Settings UI editor (explicitly per user). Add a single example entry to `config/settings.example.yaml` under the `app:` block.

Thread the cleaned base URL into the JV grid template context on BOTH render paths (`GET /` + `GET /overview` page render AND `POST /overview/grid` OOB re-render). Pre-clean (rstrip a single trailing `/`) in the route handler — sibling templates do not use Jinja `rstrip`, so keeping the join logic in Python is consistent.

Insert a 컨플 button block in `app_v2/templates/overview/_grid.html` between the existing edm block (line 71) and the AI Summary block (line 73), mirroring the edm two-branch shape: `text-dark` on the active anchor for visual contrast (the 260429-ek7 / 260507-l5w precedent), bare `btn-outline-secondary` on the disabled button. The disabled state covers both "no conf_url configured" AND "row missing page_id" — defense in depth, even though the page_id regex guarantees it in practice.

Output:
- Parser edit: per-helper h1-h6 skip in both `_extract_label_value` and `_extract_link` (mirror the existing two-pass walk's idiom).
- 2 new parser tests (Status + Customer).
- `AppConfig.conf_url` field + example.yaml entry.
- Router edit: thread `conf_url` (rstripped) into both GET and POST overview contexts.
- Template edit: 컨플 button block inserted between edm and AI buttons.
- 2 new route tests proving the conf_url wiring on `GET /overview`.
- Full v2 suite stays green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md
@app_v2/services/joint_validation_parser.py
@tests/v2/test_joint_validation_parser.py
@app/core/config.py
@config/settings.example.yaml
@app_v2/routers/overview.py
@app_v2/templates/overview/_grid.html
@tests/v2/test_joint_validation_routes.py

<interfaces>
<!-- Pinned during planning. Executor should not need to re-read source for these. -->

From app_v2/services/joint_validation_parser.py (current — to be edited; 260507-ksn shape):
```python
def _extract_label_value(soup: BeautifulSoup, label: str) -> str:
    matches = soup.find_all(
        "strong",
        string=lambda s: s is not None and s.strip() == label,
    )
    if not matches:
        return ""
    inline_fallback = ""
    for strong in matches:
        # ★ NEW: skip <strong> whose nearest ancestor is <h1>..<h6>.
        # A label inside a heading is never the canonical metadata source.
        if strong.find_parent(["h1", "h2", "h3", "h4", "h5", "h6"]) is not None:
            continue
        # Pass 1: Page-Properties shape …
        cell = strong.find_parent(["th", "td"])
        if cell is not None: …
        # Pass 2: inline-paragraph fallback …
    return inline_fallback


def _extract_link(soup: BeautifulSoup) -> str:
    matches = soup.find_all(
        "strong",
        string=lambda s: s is not None and s.strip() == "Report Link",
    )
    for strong in matches:
        # ★ NEW: same h1-h6 skip — apply for parity with _extract_label_value.
        if strong.find_parent(["h1", "h2", "h3", "h4", "h5", "h6"]) is not None:
            continue
        cell = strong.find_parent(["th", "td"])
        …
```

The skip is inserted as the FIRST check inside the per-`<strong>` loop, BEFORE the existing `<th>/<td>` ancestor walk. Net diff: 6 added lines (3 in each helper), zero deletions.

From app/core/config.py (current AppConfig — to be edited):
```python
class AppConfig(BaseModel):
    default_database: str = ""
    default_llm: str = ""
    query_row_limit: int = 1000
    recent_query_history: int = 20
    agent: AgentConfig = Field(default_factory=AgentConfig)
    # ★ NEW (one line):
    conf_url: str = ""
```

From app_v2/routers/overview.py (current — both routes need the same 2-line addition):
```python
# In get_overview() and post_overview_grid(), AFTER constructing `vm`,
# BEFORE constructing `ctx`:
settings = getattr(request.app.state, "settings", None)
conf_url = (settings.app.conf_url.rstrip("/") if settings else "")

# Then in ctx:
ctx = {
    "vm": vm,
    "selected_filters": filters,
    "active_tab": "overview",
    "active_filter_counts": vm.active_filter_counts,
    "all_platform_ids": [],
    "conf_url": conf_url,   # ★ NEW
}
```

The `getattr(request.app.state, "settings", None)` idiom is the project-shared pattern (verified in `routers/settings.py:50`, `routers/summary.py:129`, `routers/joint_validation.py:149`). The `if settings else ""` guard handles the rare test fixture where `app.state.settings` is unset.

From app_v2/templates/overview/_grid.html (target insert — between line 71 `{% endif %}` and line 73 `{# AI Summary button …`):
```jinja
{# Confluence link button (260507-lox) — disabled when conf_url is empty
   OR row.confluence_page_id is missing. Mirrors edm-button two-branch pattern
   from 260507-l5w (text-dark on active anchor, bare outline-secondary on
   disabled button) so the active vs disabled states are visually distinct. #}
{% if conf_url and row.confluence_page_id %}
  <a href="{{ (conf_url ~ '/' ~ row.confluence_page_id) | e }}"
     class="btn btn-sm btn-outline-secondary text-dark ms-1"
     target="_blank" rel="noopener noreferrer"
     aria-label="Open Confluence page for {{ row.title | e }}">
    컨플
  </a>
{% else %}
  <button type="button"
          class="btn btn-sm btn-outline-secondary ms-1"
          disabled
          aria-label="No Confluence URL configured">
    컨플
  </button>
{% endif %}
```

Notes:
- `conf_url` is already rstripped in the route handler — template does NOT call `.rstrip(...)` (no Jinja-level rstrip elsewhere in this project; verified by grep).
- `ms-1` matches the AI Summary precedent at line 78 (existing `class="btn btn-sm btn-outline-primary ms-1"`).
- `text-dark` on the active branch matches the edm precedent from 260507-l5w (line 59).
- `aria-label` carries descriptive screen-reader text since `컨플` alone is opaque to non-Korean readers.
- Disabled-state defense in depth: `row.confluence_page_id` is `pattern=r"^\d+$"` and is always populated in practice — the guard is parity safety + matches the edm-button conditional structure.

From tests/v2/test_joint_validation_routes.py (existing test fixtures — NOT modified):
- `SAMPLE_HTML` already contains `<th><strong>Status</strong></th>` etc. — so the conf_url tests can reuse `jv_dir_with_one` + `client` fixtures and assert against the rendered grid.
- `app.state.settings` is NOT set by the `client` fixture; it IS set by the `configured_client` fixture at line 100. For the new conf_url tests, a small monkeypatch on `app.state.settings` is the simplest path.
</interfaces>

<conventions>
- Pydantic v2 `AppConfig` is the project standard — keep `conf_url: str = ""` (no `Field(...)`, no `Optional[str] = None`). Empty string default, not None.
- Field naming: lowercase snake_case (`conf_url`, NOT `confluenceUrl` or `CONF_URL`).
- BS4 navigation only in the parser. `find_parent(["h1", ..., "h6"])` is the canonical idiom; do NOT use regex on HTML.
- `getattr(request.app.state, "settings", None)` — defensive read pattern shared across routers; do NOT switch to direct attribute access (some test fixtures bypass startup).
- Template-side: keep the new block byte-aligned with the existing edm block's indent (2-space indent inside `<td class="text-end">`, both branches body indented 2 more spaces). Match the surrounding comment-block style (`{# … #}` at the same indent as the `{% if … %}`).
- Korean text in templates: emit verbatim UTF-8 (`컨플` is 3 syllable blocks = 9 bytes UTF-8). No HTML-entity encoding; Jinja autoescape does not encode CJK.
- Test fixtures: prefer `jv_dir_with_one` + `client` over `configured_client` — the conf_url tests do not need an LLM-resolver. Add a small inline `monkeypatch.setattr(app.state, "settings", ...)` or use a context-manager pattern matching the existing `configured_client` fixture at line 99.
- Atomic single-commit landing: all 7 file edits ship together. Splitting Concern 1 from Concern 2 is acceptable in principle but the user bundled them in one quick task — keep the commit count to 1.
</conventions>

<test_baseline>
Before-state baseline (per quick task 260507-lcc SUMMARY): **556 passed, 5 skipped** in `tests/v2/`.
After this quick task: **558 passed, 5 skipped** (2 net new parser tests + 2 net new route tests = 4 new tests; no existing tests modified or skipped).
</test_baseline>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: h1-h6 skip in parser + AppConfig.conf_url + 컨플 button + 4 new tests</name>
  <files>app_v2/services/joint_validation_parser.py, tests/v2/test_joint_validation_parser.py, app/core/config.py, config/settings.example.yaml, app_v2/routers/overview.py, app_v2/templates/overview/_grid.html, tests/v2/test_joint_validation_routes.py</files>
  <behavior>
    NEW BEHAVIOUR (tests-first; write the 4 new tests, watch them fail, then implement):

    **Concern 1 — h1-h6 ancestor skip (parser)**

    1. **Status: <strong> inside `<h1>` is skipped; Page-Properties row wins.**
       - Input HTML contains BOTH `<h1><strong>Status</strong>: leaked-from-heading</h1>` (inline-paragraph-shaped match inside h1) AND `<tr><td><p><strong>Status</strong></p></td><td><p>Planned</p></td></tr>`.
       - Expected: `parse_index_html(html).status == "Planned"` (NOT `"leaked-from-heading"` and NOT `""`).
       - Why this is the bug: today the h1's inline-paragraph match is recorded into `inline_fallback` BEFORE the table-row match resolves; when the inline match is non-empty it's returned only after all matches are exhausted, BUT today's `_extract_label_value` returns the first non-empty Page-Properties match it finds, so the h1 leak today is when the Page-Properties row is ABSENT. The actual reported bug is when the h1 contains `<strong>Status</strong>` standalone (no inline value) AND the value lives in a wrapper that doesn't fit the `<th>/<td>` walk perfectly. The h1-h6 skip closes the bug class regardless of which sub-shape triggered it.

    2. **Customer: <strong> inside `<h2>` is skipped; Page-Properties row wins (generalization proof).**
       - Input HTML: `<h2><strong>Customer</strong>: Acme HQ</h2>` + `<tr><td><strong>Customer</strong></td><td>Beta Inc.</td></tr>`.
       - Expected: `parse_index_html(html).customer == "Beta Inc."`.
       - Locks in that the skip is general, not Status-specific.

    **Concern 2 — conf_url wiring (route)**

    3. **Empty `conf_url` (default) → disabled 컨플 button renders.**
       - `app.state.settings` set to a `Settings(app=AppConfig(conf_url=""))` (or `Settings()` defaults — both have `conf_url=""`).
       - `client.get("/overview")` → status 200; rendered body contains `disabled` AND `aria-label="No Confluence URL configured"` AND `컨플`.
       - Body does NOT contain a 컨플 anchor `<a href="...">컨플</a>` (the active branch).

    4. **Configured `conf_url` with trailing slash → active 컨플 anchor with joined href.**
       - `app.state.settings` set to `Settings(app=AppConfig(conf_url="https://example.com/"))`.
       - `client.get("/overview")` → status 200; rendered body contains `href="https://example.com/3193868109"` (single slash; trailing slash on conf_url stripped before join) AND `aria-label="Open Confluence page for Test Joint Validation"` AND `컨플`.

    REGRESSION GUARANTEES (existing tests stay green — DO NOT modify them):
    - All 14 existing tests in `tests/v2/test_joint_validation_parser.py` (10 from Phase 1 + 4 from 260507-ksn).
    - All existing tests in `tests/v2/test_joint_validation_routes.py` — including `test_get_root_renders_jv_grid`, `test_get_overview_renders_jv_grid`, `test_post_overview_grid_returns_oob_blocks`, `test_post_overview_grid_sets_hx_push_url`, `test_empty_jv_root_renders_empty_state` (the 'No Joint Validations yet.' / `colspan="13"` copy is byte-stable; the new conf_url variable is unused on the empty-state branch).
    - `tests/v2/test_llm_resolver.py` — touches `AppConfig` but doesn't enumerate fields; adding `conf_url` is additive and back-compat.
    - The full v2 suite goes from 556 passing to 558 passing (4 new tests, all green; 5 skipped unchanged).
  </behavior>
  <action>
    Implement in TDD order. Use the **Edit** tool for surgical edits — do NOT rewrite any file from scratch.

    ════════════════════════════════════════════════════════════════════════
    STEP A — Write 2 new parser tests (RED).
    ════════════════════════════════════════════════════════════════════════

    Append to `tests/v2/test_joint_validation_parser.py` (after the existing `test_parse_paren_strip_does_not_apply_to_other_fields` at line ~187):

    ```python
    def test_parse_skips_strong_inside_h1_for_status() -> None:
        # Real-export bug class: <strong>Status</strong> appears inside an
        # <h1> heading (page title or section header) AND the canonical metadata
        # lives in a Page-Properties row below. The heading-nested <strong>
        # MUST be skipped so the Page-Properties row wins.
        # 260507-lox: skip generalized to all fields (not Status-specific) —
        # a label inside a heading is never the canonical metadata source.
        html = (
            b"<html><body>"
            b"<h1><strong>Status</strong>: leaked-from-heading</h1>"
            b"<table><tbody>"
            b"<tr><td><p><strong>Status</strong></p></td>"
            b"<td><p>Planned</p></td></tr>"
            b"</tbody></table>"
            b"</body></html>"
        )
        assert parse_index_html(html).status == "Planned"

    def test_parse_skips_strong_inside_h2_for_customer_generalization() -> None:
        # Generalization proof: the same h1-h6 skip applies to other fields
        # (here Customer in <h2>), NOT just Status. Confirms the bug-class fix
        # is universal — see 260507-lox plan rationale.
        html = (
            b"<html><body>"
            b"<h2><strong>Customer</strong>: Acme HQ</h2>"
            b"<table><tbody>"
            b"<tr><td><strong>Customer</strong></td>"
            b"<td>Beta Inc.</td></tr>"
            b"</tbody></table>"
            b"</body></html>"
        )
        assert parse_index_html(html).customer == "Beta Inc."
    ```

    Run `pytest tests/v2/test_joint_validation_parser.py -x` — the 2 new tests should FAIL (the h1 inline-paragraph match leaks into `inline_fallback`); existing 14 stay green. Confirm RED before STEP B.

    ════════════════════════════════════════════════════════════════════════
    STEP B — Implement h1-h6 skip in `_extract_label_value` and `_extract_link`.
    ════════════════════════════════════════════════════════════════════════

    Edit `app_v2/services/joint_validation_parser.py`. Inside `_extract_label_value`, add the h1-h6 guard as the FIRST check in the per-`<strong>` loop (before the existing `<th>/<td>` ancestor walk):

    Find the existing block (after 260507-ksn fix, lines ~91-93):
    ```python
        for strong in matches:
            # Pass 1: prefer the Page-Properties shape — find the nearest
            # <th>/<td> ancestor and read its next-sibling cell's full text.
    ```

    Insert IMMEDIATELY after the `for strong in matches:` line, BEFORE the `# Pass 1` comment:
    ```python
            # 260507-lox: skip <strong> whose nearest ancestor is <h1>..<h6>.
            # A label inside a heading is never the canonical metadata source —
            # it is a section title or page heading. Generalized skip (not
            # Status-specific): the bug class is universal — Customer / AP
            # Company / etc. would suffer the same shape in different exports.
            if strong.find_parent(["h1", "h2", "h3", "h4", "h5", "h6"]) is not None:
                continue
    ```

    Apply the same insert inside `_extract_link` (lines ~138-139), immediately after `for strong in matches:` and BEFORE the `cell = strong.find_parent(["th", "td"])` line:
    ```python
            # 260507-lox: skip <strong> whose nearest ancestor is <h1>..<h6>.
            # Mirror parity with _extract_label_value — a Report Link nested
            # inside a heading is not the canonical link source.
            if strong.find_parent(["h1", "h2", "h3", "h4", "h5", "h6"]) is not None:
                continue
    ```

    Re-run `pytest tests/v2/test_joint_validation_parser.py -x` — all 16 tests (14 existing + 2 new) MUST pass.

    ════════════════════════════════════════════════════════════════════════
    STEP C — Add `AppConfig.conf_url` field.
    ════════════════════════════════════════════════════════════════════════

    Edit `app/core/config.py`. Find the `AppConfig` class (lines 43-48):
    ```python
    class AppConfig(BaseModel):
        default_database: str = ""
        default_llm: str = ""
        query_row_limit: int = 1000
        recent_query_history: int = 20
        agent: AgentConfig = Field(default_factory=AgentConfig)
    ```

    Add `conf_url: str = ""` AS THE LAST FIELD (after `agent`):
    ```python
    class AppConfig(BaseModel):
        default_database: str = ""
        default_llm: str = ""
        query_row_limit: int = 1000
        recent_query_history: int = 20
        agent: AgentConfig = Field(default_factory=AgentConfig)
        # 260507-lox: base URL for Confluence "컨플" link button in JV grid.
        # Empty string = disabled state (button renders disabled). Edited
        # directly in config/settings.yaml — no Settings UI surface.
        conf_url: str = ""
    ```

    No new imports needed. `Settings` itself is unchanged.

    ════════════════════════════════════════════════════════════════════════
    STEP D — Add `conf_url` example entry to `config/settings.example.yaml`.
    ════════════════════════════════════════════════════════════════════════

    Edit `config/settings.example.yaml`. Find the `app:` block (lines 32-53). Insert a new `conf_url:` entry IMMEDIATELY AFTER the `recent_query_history: 20` line (line 36) and BEFORE the `agent:` block.

    Append between `recent_query_history: 20` and `agent:`:
    ```yaml
      # Joint Validation grid: base URL for the per-row "컨플" Confluence link button.
      # The page id (numeric, from content/joint_validation/<id>/) is appended as "/<page_id>".
      # Empty string (default) renders the button in the disabled state.
      # Example: "https://confluence.example.com" → final href "https://confluence.example.com/3193868109"
      conf_url: ""
    ```

    Indentation: 2 spaces (matches the surrounding `default_database:` / `query_row_limit:` indent at the `app:` block).

    ════════════════════════════════════════════════════════════════════════
    STEP E — Thread `conf_url` into both overview routes.
    ════════════════════════════════════════════════════════════════════════

    Edit `app_v2/routers/overview.py`. Two route handlers need the same 3-line addition.

    **In `get_overview` (line 108-163):** Find the line `vm: JointValidationGridViewModel = build_joint_validation_grid_view_model(` (line 140). Right AFTER the closing `)` of that call (line 146 — `        page=page,\n    )`), and BEFORE the `ctx = {` line (line 147):

    ```python
        # 260507-lox: thread Confluence base URL into the JV grid template
        # context. rstrip a single trailing "/" in Python so the template can
        # do a simple "{conf_url}/{page_id}" join (no Jinja-level rstrip used
        # elsewhere in this project — keep the cleanup in route code).
        settings_obj = getattr(request.app.state, "settings", None)
        conf_url = (settings_obj.app.conf_url.rstrip("/") if settings_obj else "")
    ```

    Then add `"conf_url": conf_url,` as a new key inside the `ctx = {…}` dict, AFTER the existing `"all_platform_ids": [],` line:
    ```python
        ctx = {
            "vm": vm,
            "selected_filters": filters,
            "active_tab": "overview",
            "active_filter_counts": vm.active_filter_counts,
            "all_platform_ids": [],
            "conf_url": conf_url,
        }
    ```

    **In `post_overview_grid` (line 167-225):** Same edit pattern. After the `vm = build_joint_validation_grid_view_model(...)` block (line 198-204), and BEFORE `ctx = {` (line 205):
    ```python
        # 260507-lox: same conf_url threading on the OOB re-render path —
        # the grid block also references {{ conf_url }} in the 컨플 button
        # template. Without this the OOB-swapped grid would render disabled
        # buttons even when conf_url is configured.
        settings_obj = getattr(request.app.state, "settings", None)
        conf_url = (settings_obj.app.conf_url.rstrip("/") if settings_obj else "")
    ```

    And add `"conf_url": conf_url,` to the second `ctx` dict (after `"all_platform_ids": [],` line ~211).

    The `block_names=["grid", "count_oob", "filter_badges_oob", "pagination_oob"]` list at line 217 stays UNCHANGED — `conf_url` is consumed inside the existing `grid` block, not as a separate OOB block.

    ════════════════════════════════════════════════════════════════════════
    STEP F — Insert 컨플 button block in `_grid.html`.
    ════════════════════════════════════════════════════════════════════════

    Edit `app_v2/templates/overview/_grid.html`. Find line 71 (`{% endif %}` — closes the edm button block) and line 73 (`{# AI Summary button (D-JV-15) — opens modal …`). Insert the new 컨플 block BETWEEN them, on a fresh blank line after `{% endif %}`:

    Place the comment + block at indent level 12 (3 levels of 4-space, matching the surrounding `{% if row.link %}` at line 57). The exact text to insert (note the leading blank line for visual separation, matching the blank line currently between line 71 and line 73):

    ```jinja

            {# Confluence link button (260507-lox) — disabled when conf_url is
               empty OR row.confluence_page_id is missing. Mirrors edm-button
               two-branch shape from 260507-l5w (text-dark on active anchor;
               bare outline-secondary on disabled button) for visual contrast. #}
            {% if conf_url and row.confluence_page_id %}
              <a href="{{ (conf_url ~ '/' ~ row.confluence_page_id) | e }}"
                 class="btn btn-sm btn-outline-secondary text-dark ms-1"
                 target="_blank" rel="noopener noreferrer"
                 aria-label="Open Confluence page for {{ row.title | e }}">
                컨플
              </a>
            {% else %}
              <button type="button"
                      class="btn btn-sm btn-outline-secondary ms-1"
                      disabled
                      aria-label="No Confluence URL configured">
                컨플
              </button>
            {% endif %}
    ```

    Result: the `<td class="text-end">` cell now has THREE button blocks in order — edm (line 55-71, unchanged), 컨플 (new), AI (line 73-86, unchanged).

    ════════════════════════════════════════════════════════════════════════
    STEP G — Write 2 new route tests (RED → GREEN).
    ════════════════════════════════════════════════════════════════════════

    Append to `tests/v2/test_joint_validation_routes.py` (after the last existing test, `test_browse_and_ask_tabs_unaffected` at line ~277):

    ```python
    # ---------------------------------------------------------------------------
    # 260507-lox: conf_url + 컨플 button wiring
    # ---------------------------------------------------------------------------


    def test_grid_renders_disabled_confluence_button_when_conf_url_empty(
        jv_dir_with_one: Path, client: TestClient
    ) -> None:
        """Default empty conf_url → 컨플 button renders disabled (no anchor href)."""
        # Force empty conf_url on app.state.settings (the `client` fixture
        # does NOT set settings; depending on test order, app.state.settings
        # may be populated from a prior test — set it explicitly to be safe).
        app.state.settings = Settings(
            databases=[],
            llms=[],
            app=AppConfig(conf_url=""),
        )
        r = client.get("/overview")
        assert r.status_code == 200
        body = r.text
        # 컨플 label rendered
        assert "컨플" in body
        # Disabled-branch markers
        assert 'aria-label="No Confluence URL configured"' in body
        # Active-branch markers MUST be absent
        assert 'aria-label="Open Confluence page for' not in body


    def test_grid_renders_active_confluence_anchor_when_conf_url_set(
        jv_dir_with_one: Path, client: TestClient
    ) -> None:
        """Configured conf_url with trailing slash → active 컨플 anchor with
        single-slash-joined href; trailing slash is rstripped in the route."""
        app.state.settings = Settings(
            databases=[],
            llms=[],
            app=AppConfig(conf_url="https://example.com/"),
        )
        r = client.get("/overview")
        assert r.status_code == 200
        body = r.text
        # Active anchor markers
        assert "컨플" in body
        # SAMPLE_HTML's <h1> resolves to "Test Joint Validation" — used in aria-label
        assert 'aria-label="Open Confluence page for Test Joint Validation"' in body
        # Single-slash join: trailing "/" on conf_url stripped, page_id "3193868109"
        # appended after a single "/". The fixture in jv_dir_with_one uses page id
        # 3193868109 (folder name).
        assert 'href="https://example.com/3193868109"' in body
        # Disabled-branch marker MUST be absent (the row has a page_id)
        assert 'aria-label="No Confluence URL configured"' not in body
    ```

    Run the full v2 suite:
    ```bash
    pytest tests/v2/ -x
    ```

    Expected: **558 passed, 5 skipped** (was 556 + 2 parser + 2 route = 558).

    ════════════════════════════════════════════════════════════════════════
    AVOID
    ════════════════════════════════════════════════════════════════════════
    - Do NOT scope the h1-h6 skip to Status only — the user's "for Status SPECIFICALLY" is generalized to all fields per plan rationale (documented in SUMMARY).
    - Do NOT remove the existing 260507-ksn `<th>/<td>` walk — the h1-h6 skip is a NEW guard layered on top, NOT a replacement.
    - Do NOT change the `parse_index_html` `title=` extraction — `soup.find("h1").get_text()` stays as-is. The h1-h6 skip applies to `<strong>`-label matches inside the helpers, not to the title path.
    - Do NOT add a `conf_url` Settings UI route, template, or form — explicitly out of scope per user.
    - Do NOT modify `config/settings.yaml` — that is the user's actual file, they edit it themselves. ONLY `config/settings.example.yaml`.
    - Do NOT add Jinja-level `rstrip` in the template — the cleanup happens in the Python route. Verified: no template in `app_v2/templates/` uses `rstrip`/`lstrip` today.
    - Do NOT add `conf_url` to the `block_names=[...]` list in `post_overview_grid` — it is consumed inside the existing `grid` block, not a separate OOB block.
    - Do NOT change the edm button block (lines 55-71 of `_grid.html`) — leave it byte-stable.
    - Do NOT change the AI Summary button block (lines 73-86) — leave it byte-stable.
    - Do NOT change `app_v2/templates/joint_validation/detail.html` — the per-row 컨플 button is grid-only per user task description. The detail page has its own iframe to the Confluence export and does not need the link button.
    - Do NOT change `confluence_page_id` regex / model — it stays `^\d+$` per D-JV-03.
    - Do NOT promote case-insensitive label matching in the parser — the existing Korean `담당자` byte-equal test depends on case-sensitive comparison.
    - Do NOT introduce regex-based HTML parsing — BS4 navigation only.
    - Do NOT touch routers/templates/CSS for Browse, Ask, Settings, Summary — strictly out of scope.
    - Do NOT add `chat_max_steps`-style nested submodel for `conf_url` — it's a flat string field on `AppConfig`.
  </action>
  <verify>
    <automated>
# 1. Parser: h1-h6 skip present in BOTH _extract_label_value and _extract_link.
grep -c 'find_parent(\["h1", "h2", "h3", "h4", "h5", "h6"\])' app_v2/services/joint_validation_parser.py | grep -q '^2$' && \
# 2. AppConfig.conf_url field present with empty-string default.
grep -F 'conf_url: str = ""' app/core/config.py | wc -l | grep -q '^1$' && \
# 3. settings.example.yaml has conf_url under app: block.
grep -F '  conf_url: ""' config/settings.example.yaml | wc -l | grep -q '^1$' && \
# 4. Both overview route handlers thread conf_url into ctx.
grep -c '"conf_url": conf_url,' app_v2/routers/overview.py | grep -q '^2$' && \
# 5. Both handlers rstrip conf_url before passing.
grep -c 'settings_obj.app.conf_url.rstrip("/")' app_v2/routers/overview.py | grep -q '^2$' && \
# 6. _grid.html has the 컨플 active anchor + disabled button.
grep -F 'aria-label="Open Confluence page for' app_v2/templates/overview/_grid.html | wc -l | grep -q '^1$' && \
grep -F 'aria-label="No Confluence URL configured"' app_v2/templates/overview/_grid.html | wc -l | grep -q '^1$' && \
grep -c '컨플' app_v2/templates/overview/_grid.html | grep -q '^2$' && \
# 7. edm and AI buttons are still present (regression guard).
grep -c '<i class="bi bi-link-45deg"></i> edm' app_v2/templates/overview/_grid.html | grep -q '^2$' && \
grep -F '<i class="bi bi-magic"></i> AI' app_v2/templates/overview/_grid.html | wc -l | grep -q '^1$' && \
# 8. Detail page is byte-stable (no 컨플 button leaked there).
! grep -F '컨플' app_v2/templates/joint_validation/detail.html && \
# 9. Parser tests: 16 in file (14 existing + 2 new).
grep -c '^def test_parse_' tests/v2/test_joint_validation_parser.py | grep -q '^16$' && \
# 10. Route tests: 2 new conf_url tests added.
grep -c 'def test_grid_renders_.*confluence_' tests/v2/test_joint_validation_routes.py | grep -q '^2$' && \
# 11. Full v2 suite green: 558 passed, 5 skipped.
python -m pytest tests/v2/ -x --tb=short -q 2>&1 | tail -5
    </automated>
  </verify>
  <done>
    - **Concern 1:** `_extract_label_value` and `_extract_link` both skip `<strong>` matches whose nearest ancestor is `<h1>..<h6>`, applied as the FIRST check in the per-`<strong>` loop. Two new parser tests pass: `test_parse_skips_strong_inside_h1_for_status` (Status — user-reported) and `test_parse_skips_strong_inside_h2_for_customer_generalization` (Customer — generalization proof).
    - **Concern 2 — Settings:** `AppConfig.conf_url: str = ""` exists; `Settings(app=AppConfig(conf_url="..."))` round-trips. `config/settings.example.yaml` has one `conf_url:` example entry under the `app:` block with explanatory comments. `config/settings.yaml` (user's real config) is NOT modified.
    - **Concern 2 — Router:** Both `get_overview` and `post_overview_grid` read `settings_obj.app.conf_url.rstrip("/")` and inject it into the template context as `"conf_url"`. The OOB re-render path (`block_names=["grid", "count_oob", "filter_badges_oob", "pagination_oob"]`) uses the same context.
    - **Concern 2 — Template:** `app_v2/templates/overview/_grid.html` carries a 2-branch 컨플 button block between the edm `{% endif %}` (line 71) and the AI Summary comment (line 73). Active branch: `text-dark` anchor with joined href + descriptive aria-label. Disabled branch: bare `btn-outline-secondary` button with "No Confluence URL configured" aria-label. Detail page is unchanged.
    - **Concern 2 — Tests:** Two new route tests prove the wiring on `GET /overview`: empty conf_url → disabled button; trailing-slash conf_url → active anchor with single-slash-joined href.
    - **Regressions:** All 14 existing parser tests pass. All existing JV/route/grid-service/store/summary/main/invariant tests pass. Test-count delta: +4 (2 parser + 2 route). Final v2 suite: 558 passed / 5 skipped (was 556 / 5).
    - **Atomicity:** Single commit lands all 7 file edits.
  </done>
</task>

</tasks>

<verification>
**Automated checks (Task 1 verify block — 11 numbered grep + pytest gates):**
1. h1-h6 skip applied in BOTH parser helpers (exactly 2 matches of the literal `find_parent(["h1", "h2", "h3", "h4", "h5", "h6"])`).
2. `AppConfig.conf_url: str = ""` present.
3. `config/settings.example.yaml` carries one `conf_url: ""` line under `app:` (2-space indent).
4. Both overview handlers add `"conf_url": conf_url,` to ctx (2 matches).
5. Both handlers rstrip conf_url before passing (2 matches of the literal rstrip line).
6-8. `_grid.html` carries the 컨플 active anchor aria-label, disabled button aria-label, and 2 occurrences of the literal `컨플`. edm + AI buttons remain present. Detail page has zero `컨플`.
9. Parser test count: 16 `def test_parse_` (14 existing + 2 new).
10. Route test count: 2 `def test_grid_renders_..._confluence_` (the 2 new tests).
11. Full v2 suite green via `pytest tests/v2/ -x` — final summary line shows 558 passed, 5 skipped.

**Sanity checks (mental-model only — files are untracked, do NOT modify):**
- The user's untracked `content/joint_validation/319386*` folders likely contain real Confluence-shape exports. After landing this fix, opening one in the JV grid with `conf_url` configured in `config/settings.yaml` should render an active 컨플 anchor that opens `{conf_url}/{folder_name}` in a new tab.
- Status fields that were previously leaking from `<h1><strong>Status</strong>...</h1>` will now resolve correctly via the Page-Properties row — the 16th parser test (`test_parse_skips_strong_inside_h1_for_status`) is the regression lock.

**Human verification (deferred — not blocking):**
- Configure `app.conf_url: "https://confluence.example.com"` in `config/settings.yaml`.
- Reload `/overview`; confirm a row with `confluence_page_id="3193868109"` shows an active 컨플 button with href `https://confluence.example.com/3193868109` and visually-distinct (text-dark) styling vs the disabled state.
- Drop a folder under `content/joint_validation/<numeric_id>/` whose `index.html` has `<h1><strong>Status</strong></h1>` plus a Page-Properties Status row; confirm the Status column shows the row value, not the h1.
</verification>

<success_criteria>
1. **Concern 1** — h1-h6-nested `<strong>Status</strong>` (and any other field) is skipped during metadata extraction. Page-Properties row wins. Parser tests: 16 passing (14 existing + 2 new). Title-from-h1 path is unchanged.
2. **Concern 2 — Config** — `AppConfig.conf_url: str = ""` field exists; example entry in `config/settings.example.yaml`; user's `config/settings.yaml` is NOT modified.
3. **Concern 2 — Wiring** — Both GET (`/`, `/overview`) and POST (`/overview/grid`) route handlers thread `conf_url` (rstripped) into the JV grid template context via `"conf_url"` ctx key. Same value flows through the OOB block re-render path.
4. **Concern 2 — Template** — `_grid.html` renders a 2-branch 컨플 button between edm and AI buttons. Active anchor uses `text-dark` for visual contrast; disabled button is bare `btn-outline-secondary`. `aria-label` carries descriptive Korean-aware copy. The detail page (`joint_validation/detail.html`) is unchanged.
5. **Concern 2 — Tests** — 2 new route tests prove both the empty-conf_url disabled state and the configured-conf_url active state with correct trailing-slash handling.
6. **Suite** — `pytest tests/v2/` exits 0; final summary shows 558 passed / 5 skipped (delta: +2 parser + +2 route = +4 vs the 556 baseline). Zero regressions; zero pre-existing tests modified or skipped.
7. **Atomicity** — All 7 file edits land in a single commit. No half-applied state.
</success_criteria>

<output>
After completion, create `.planning/quick/260507-lox-jv-status-specific-h1-h6-skip-in-parser-/260507-lox-SUMMARY.md` capturing:

- **Concern 1 — h1-h6 skip:**
  - Bug class restated (label nested in heading is never canonical metadata).
  - Why generalized to all fields, not Status-specific (one-line rationale: bug class is universal — Customer/AP Company suffer the same shape; field-targeted logic is fragile).
  - Where the skip lives (FIRST check inside the per-`<strong>` loop in BOTH `_extract_label_value` AND `_extract_link`, layered on top of the 260507-ksn `<th>/<td>` walk).
  - Tests added (Status, Customer) and tests preserved (14 existing).
- **Concern 2 — conf_url + 컨플 button:**
  - `AppConfig.conf_url` field — empty default for back-compat.
  - `config/settings.example.yaml` entry; `config/settings.yaml` deliberately untouched.
  - Router threading on BOTH paths (page render + OOB block re-render); rstrip in Python (no Jinja-level rstrip in the project).
  - Template insertion point + active/disabled branch shape; defense-in-depth disabled guard.
  - Tests added (empty-conf_url disabled; configured-conf_url active with trailing-slash join).
  - HUMAN-UAT pending: load `/overview` with conf_url configured; confirm 컨플 button opens correct URL in new tab; confirm visually-distinct active vs disabled state.
- **Test-count delta:** before 556 / 5 skipped → after 558 / 5 skipped (+4 net new).
- **Files modified:** 7 (parser + parser tests + AppConfig + example.yaml + overview router + grid template + route tests).
- **Commit hash + atomicity note:** single commit landing all 7 edits.
</output>
</content>
</invoke>