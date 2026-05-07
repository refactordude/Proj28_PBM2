---
phase: 260507-ksn
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app_v2/services/joint_validation_parser.py
  - tests/v2/test_joint_validation_parser.py
autonomous: true
requirements:
  - QUICK-260507-ksn
must_haves:
  truths:
    - "Real Confluence Page-Properties shape (`<tr><td><p><strong>Field</strong></p></td><td><div class=\"content-wrapper\"><p>value</p></div></td></tr>`) yields the inner-`<td>` value (e.g. `Planned`), not blank — current code returns `\"\"` for this shape because `find_parent(['th','td','p'])` resolves to the inner `<p>` and never reaches the next-sibling `<td>`."
    - "Inline-paragraph shape (`<p><strong>Field</strong>: value</p>`) still extracts `value` (regression-protected by `tests/v2/fixtures/joint_validation_fallback_sample.html`)."
    - "When the SAME label appears in BOTH a heading-like location (e.g. `<h1><strong>Status</strong></h1>` with no value) AND a Page-Properties table row, the table-row value wins — the heading-only match no longer poisons the result."
    - "Start/End values that arrive parenthesised (`(2024-03-01)`) are normalised to `2024-03-01`; bare `2024-03-01` stays `2024-03-01` (idempotent). The cleanup is scoped to `start` and `end` ONLY — `Customer` value `Acme (lead)` is left untouched."
    - "All 9 existing parser tests in `tests/v2/test_joint_validation_parser.py` continue to pass (zero regressions). The synthetic shipped-fixture shape `<th><strong>Field</strong></th><td>value</td>` and the `<a><strong>X</strong></a>`-walks-up case both keep working."
    - "`_extract_link` benefits from the same fix path so `Report Link` lookups inside the real Page-Properties shape return the inner-cell `<a href>` (parity with `_extract_label_value`)."
  artifacts:
    - path: "app_v2/services/joint_validation_parser.py"
      provides: "Updated `_extract_label_value` (and `_extract_link`) that walks up to the nearest `<th>/<td>` ancestor before consulting `.find_next_sibling(['td','th'])`, with disambiguation across multiple `<strong>` matches and a per-field Start/End parens-strip cleanup invoked from `parse_index_html`."
      contains: "find_parents"
    - path: "tests/v2/test_joint_validation_parser.py"
      provides: "Four new BS4-string-input unit tests covering: (a) Page-Properties next-sibling-`<td>` extraction with `<p>` and `<div class=\"content-wrapper\">` wrappers, (b) duplicate-label disambiguation (heading + table row), (c) Start/End parens-strip idempotency, (d) parens-strip non-application to other fields."
      contains: "def test_parse_page_properties_with_wrapped_value"
  key_links:
    - from: "app_v2/services/joint_validation_parser.py::_extract_label_value"
      to: "app_v2/services/joint_validation_parser.py::parse_index_html"
      via: "callsite passes raw label; cleanup applied per-field at the parse_index_html level (NOT inside the helper) so the helper stays generic"
      pattern: "_extract_label_value\\(soup, \"(Start|End)\"\\)"
    - from: "app_v2/services/joint_validation_parser.py::parse_index_html"
      to: "app_v2/services/joint_validation_store.py::get_parsed_jv"
      via: "ParsedJV BaseModel (unchanged) — store/grid_service consumers see corrected values transparently after mtime cache miss; no caller changes needed"
      pattern: "parse_index_html\\(index_html\\.read_bytes\\(\\)\\)"
---

<objective>
Fix `_extract_label_value` (and `_extract_link`) in `app_v2/services/joint_validation_parser.py` so they correctly extract metadata fields from real Confluence-exported `index.html` files that use the Confluence Page Properties macro shape:

```html
<tr>
    <td><p><strong>Status</strong></p></td>
    <td><div class="content-wrapper"><p>Planned</p></div></td>
</tr>
```

Purpose: Today only `title` (sourced from `<h1>`) is correct on real exports. Every other metadata field comes back blank because `strong.find_parent(["th", "td", "p"])` resolves to the INNERMOST matching ancestor — the inner `<p>` wrapping the `<strong>` — and the code then takes the `<p>`-fallback path (`get_text(strip=True)` → `"Status"` → strip-label → `""`). The next-sibling `<td>` containing the actual value (`Planned`, possibly wrapped in `<div class="content-wrapper">` and/or `<p>`) is never visited. The synthetic fixture shape that ships under `tests/v2/fixtures/` (`<th><strong>X</strong></th><td>Y</td>`) accidentally works only because there's no `<p>` between the `<strong>` and the `<th>`.

In addition, real exports sometimes carry the label in TWO places — e.g. `<h1><strong>Status</strong></h1>` at the top AND `<tr><td>...<strong>Status</strong>...</td><td>...</td></tr>` in the Page Properties table. With `soup.find()` (first-match-wins) and the heading appearing first in document order, the parser locks onto the heading, then has no useful sibling to read, and returns `""`.

Finally, Start/End values sometimes arrive parenthesised (`(2024-03-01)`) — the user wants them normalised to `2024-03-01`. This cleanup must be scoped to `Start`/`End` only so values like `Customer: Acme (lead)` are not corrupted.

Output:
- One parser edit (replace `find_parent` with a `<th>/<td>`-preferring walk; loop over all `<strong>` matches and disambiguate; add per-field paren-strip in `parse_index_html` for `start`/`end` only).
- Four new unit tests (BS4-string inputs, no real fixture HTML).
- 9 existing parser tests stay green; full v2 suite stays green.
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
@tests/v2/fixtures/joint_validation_sample.html
@tests/v2/fixtures/joint_validation_fallback_sample.html

<interfaces>
<!-- Pinned during planning. Executor should not need to re-read these. -->

From app_v2/services/joint_validation_parser.py (current — to be edited):
```python
class ParsedJV(BaseModel):
    title: str = ""
    status: str = ""
    customer: str = ""
    model_name: str = ""
    ap_company: str = ""
    ap_model: str = ""
    device: str = ""
    controller: str = ""
    application: str = ""
    assignee: str = ""    # 담당자
    start: str = ""
    end: str = ""
    link: str = ""

def _extract_label_value(soup: BeautifulSoup, label: str) -> str: ...
def _extract_link(soup: BeautifulSoup) -> str: ...
def parse_index_html(html_bytes: bytes) -> ParsedJV: ...
```

The parser is consumed by `app_v2/services/joint_validation_store.py::get_parsed_jv` (mtime-keyed memo) and ultimately by `app_v2/services/joint_validation_grid_service.py`. Both are downstream of `ParsedJV` and require no signature change. After this fix, real Confluence exports under `content/joint_validation/<id>/index.html` populate every field correctly on the next mtime change (or `clear_parse_cache()` in tests).

Current bug-trace on the real Confluence shape:
```
<tr><td><p><strong>Status</strong></p></td><td><div class="content-wrapper"><p>Planned</p></div></td></tr>
                       ^^^^^^^^^
                       soup.find('strong', string='Status')

strong.find_parent(['th','td','p'])  →  <p> (innermost match — NOT the <td>)
cell.name == 'p'  →  fallback branch
cell.get_text(strip=True)  →  "Status"
strip leading "Status" + ":"  →  ""           ← BUG
```

Mental-model fixtures (real shape, NOT shipped to tests):
- `content/joint_validation/3193868109/index.html` etc. use the synthetic `<th><strong>X</strong></th><td>Y</td>` shape and currently work — the bug surfaces only on real Confluence Page Properties exports (which the user has NOT shared and NOT committed).
- The shipped fixtures `tests/v2/fixtures/joint_validation_sample.html` and `joint_validation_fallback_sample.html` cover the two existing shapes; both stay byte-equal so existing tests keep their semantics.
</interfaces>

<conventions>
- Phase 01 D-JV-04 / Pitfall 9: every `get_text()` result wrapped in `str()` (NavigableString carries parent reference). Preserve this in any new code.
- Field-name matching: case-sensitive, exact-string-equal-after-`.strip()` (existing behaviour: `lambda s: s is not None and s.strip() == label`). Keep case-sensitive — the existing fixture `test_parse_strong_with_surrounding_whitespace` and the Korean `담당자` byte-equal test depend on this.
- BS4 navigation only — NO regex on HTML. `find_parents`, `find_next_sibling`, `get_text` are the allowed primitives.
- "First match wins on duplicate labels" (existing test `test_parse_first_match_wins_on_duplicate_label`) is preserved within a SHAPE — i.e. when multiple Page-Properties rows share the same label, the first row wins. The disambiguation rule layers ON TOP: prefer Page-Properties shape over heading-only shape across the whole document.
- Pydantic v2 `ParsedJV` field set is unchanged. No new fields, no removed fields, no renamed fields.
- Cleanup is per-field (Start/End only) and lives in `parse_index_html`, not in `_extract_label_value`. Keeps the helper generic and unit-testable in isolation.
</conventions>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Fix Page-Properties extraction + disambiguation + Start/End paren-strip; add 4 new tests</name>
  <files>app_v2/services/joint_validation_parser.py, tests/v2/test_joint_validation_parser.py</files>
  <behavior>
    NEW BEHAVIOUR (tests-first; write tests, watch them fail, then implement):

    1. **Page-Properties next-sibling-`<td>` extraction (preferred shape).**
       - Input: `b'<table><tr><td><p><strong>Status</strong></p></td><td><div class="content-wrapper"><p>Planned</p></div></td></tr></table>'`
       - Expected: `parse_index_html(html).status == "Planned"`
       - Also covers: `<td><strong>Field</strong></td><td><p>value</p></td>` (no inner `<p>` around the strong).
       - Also covers: `<td><p><strong>Field</strong></p></td><td>raw text</td>` (no wrapper around value).

    2. **Duplicate-label disambiguation (heading + table row).**
       - Input HTML where `<h1><strong>Status</strong></h1>` (or `<h2>` / `<p><strong>Status</strong></p>` with NO trailing colon-and-value) appears BEFORE `<tr><td><p><strong>Status</strong></p></td><td><p>Planned</p></td></tr>`.
       - Expected: `parsed.status == "Planned"` (table-row wins; heading-only match is skipped because it has no usable value).

    3. **Start/End paren-strip idempotency.**
       - `<p><strong>Start</strong>: (2024-03-01)</p>` → `parsed.start == "2024-03-01"`
       - `<p><strong>Start</strong>: 2024-03-01</p>`   → `parsed.start == "2024-03-01"` (idempotent, no double-strip)
       - Page-Properties shape with parens: `<tr><td><p><strong>End</strong></p></td><td><p>(2024-03-01)</p></td></tr>` → `parsed.end == "2024-03-01"`.

    4. **Paren-strip is scoped to Start/End only.**
       - `<tr><th><strong>Customer</strong></th><td>Acme (lead)</td></tr>` → `parsed.customer == "Acme (lead)"` (parens preserved — strip MUST NOT apply to non-Start/End fields).

    REGRESSION GUARANTEES (existing tests stay green — DO NOT modify them):
    - `test_parse_primary_shape_all_13_fields` — synthetic `<th><strong>X</strong></th><td>Y</td>` shape.
    - `test_parse_fallback_shape_p_strong_colon` — `<p><strong>X</strong>: Y</p>` shape.
    - `test_parse_missing_h1_returns_blank_title`.
    - `test_parse_korean_label_byte_equal` — UTF-8 byte sequence for `담당자`.
    - `test_parse_first_match_wins_on_duplicate_label` — two Page-Properties rows with same label, first wins.
    - `test_parse_empty_value_cell_returns_blank` — empty `<td>` → `""`.
    - `test_parse_link_extracts_first_anchor_href` — Report Link via `<th><strong>Report Link</strong></th><td><a href=...>`.
    - `test_parse_label_in_anchor_walks_up_correctly` — `<th><a><strong>Status</strong></a></th><td>OK</td>`.
    - `test_parse_strong_with_surrounding_whitespace` — `<strong>  Customer  </strong>` whitespace preserved-then-stripped match.
    - `test_parse_returns_plain_str_not_navigablestring` — every field is `type(value) is str` (str() wrapping per Pitfall 9).
  </behavior>
  <action>
    STEP A — Add 4 new tests to `tests/v2/test_joint_validation_parser.py` (append after `test_parse_returns_plain_str_not_navigablestring`):

    ```python
    def test_parse_page_properties_with_wrapped_value() -> None:
        # Real Confluence Page Properties macro shape: <strong> wrapped in
        # <p> inside <td>; value lives in next-sibling <td> wrapped in
        # <div class="content-wrapper"><p>...</p></div>.
        html = (
            b"<table><tbody>"
            b"<tr><td><p><strong>Status</strong></p></td>"
            b'<td><div class="content-wrapper"><p>Planned</p></div></td></tr>'
            b"<tr><td><p><strong>Customer</strong></p></td>"
            b"<td><p>Acme Corp</p></td></tr>"
            b"<tr><td><strong>Device</strong></td>"
            b"<td>UFS 4.0</td></tr>"
            b"</tbody></table>"
        )
        parsed = parse_index_html(html)
        assert parsed.status == "Planned"
        assert parsed.customer == "Acme Corp"
        assert parsed.device == "UFS 4.0"

    def test_parse_prefers_page_properties_over_heading_for_duplicate_label() -> None:
        # Same field label in BOTH a standalone heading (no value beside it)
        # AND a Page Properties row. The table row MUST win.
        html = (
            b"<html><body>"
            b"<h1><strong>Status</strong></h1>"   # heading-only — no usable value
            b"<table><tbody>"
            b"<tr><td><p><strong>Status</strong></p></td>"
            b"<td><p>Planned</p></td></tr>"
            b"</tbody></table>"
            b"</body></html>"
        )
        assert parse_index_html(html).status == "Planned"

    def test_parse_strips_parens_from_start_and_end_only() -> None:
        # Start/End: leading "(" + trailing ")" → strip; idempotent on bare value.
        # Inline-paragraph shape:
        html_inline = (
            b"<html><body>"
            b"<h1>X</h1>"
            b"<p><strong>Start</strong>: (2024-03-01)</p>"
            b"<p><strong>End</strong>: 2024-09-30</p>"   # bare — must stay bare
            b"</body></html>"
        )
        parsed = parse_index_html(html_inline)
        assert parsed.start == "2024-03-01"
        assert parsed.end == "2024-09-30"

        # Page-Properties shape with parens:
        html_pp = (
            b"<table><tbody>"
            b"<tr><td><p><strong>Start</strong></p></td>"
            b"<td><p>(2024-03-01)</p></td></tr>"
            b"<tr><td><p><strong>End</strong></p></td>"
            b"<td><p>(2024-09-30)</p></td></tr>"
            b"</tbody></table>"
        )
        parsed_pp = parse_index_html(html_pp)
        assert parsed_pp.start == "2024-03-01"
        assert parsed_pp.end == "2024-09-30"

    def test_parse_paren_strip_does_not_apply_to_other_fields() -> None:
        # Customer: "Acme (lead)" is a legitimate value — parens MUST stay.
        html = (
            b"<table><tbody>"
            b"<tr><th><strong>Customer</strong></th><td>Acme (lead)</td></tr>"
            b"<tr><th><strong>AP Model</strong></th><td>(SM8650)</td></tr>"
            b"</tbody></table>"
        )
        parsed = parse_index_html(html)
        assert parsed.customer == "Acme (lead)"
        assert parsed.ap_model == "(SM8650)"   # parens preserved on non-Start/End fields
    ```

    Run `pytest tests/v2/test_joint_validation_parser.py -x` — confirm the 4 new tests FAIL (RED) and the 10 existing tests still pass.

    STEP B — Implement `_extract_label_value` fix in `app_v2/services/joint_validation_parser.py`.

    Replace the body of `_extract_label_value` with a two-pass walk:

    ```python
    def _extract_label_value(soup: BeautifulSoup, label: str) -> str:
        """Return trimmed text of the cell adjacent to <strong>label</strong>.

        Resolution order:
          1. Page Properties shape (preferred): <strong> sits inside a <th>/<td>
             cell (possibly wrapped in <p>, <a>, etc.). Walk up to the nearest
             <th>/<td> ancestor; the value lives in the next-sibling <th>/<td>.
             Tolerates wrappers in the value cell (<div class="content-wrapper">,
             <p>, nested combos) — full-text-strip is sufficient.
          2. Inline-paragraph fallback: <p><strong>label</strong>: value</p>.
             Same paragraph carries label and value separated by ":".

        Disambiguation: when the same <strong>label</strong> appears in
        MULTIPLE places (e.g. <h1> AND a Page Properties row), prefer the
        first match that produces a non-empty Page-Properties value over any
        heading-only match. Falls through to the inline-paragraph shape only
        if no Page-Properties match anywhere yields a non-empty value.
        """
        matches = soup.find_all(
            "strong",
            string=lambda s: s is not None and s.strip() == label,
        )
        if not matches:
            return ""
        inline_fallback = ""
        for strong in matches:
            # Pass 1: prefer the Page-Properties shape — find the nearest
            # <th>/<td> ancestor and read its next-sibling cell's full text.
            cell = strong.find_parent(["th", "td"])
            if cell is not None:
                sibling = cell.find_next_sibling(["td", "th"])
                if sibling is not None:
                    value = str(sibling.get_text(strip=True))
                    if value:
                        return value
                    # Empty value cell — preserved by existing
                    # test_parse_empty_value_cell_returns_blank. Honour the
                    # "first match wins on duplicate labels" rule WITHIN the
                    # Page-Properties shape: stop scanning further matches.
                    return ""
                # No sibling — keep scanning later matches.
                continue
            # Pass 2 candidate: <p><strong>label</strong>: value</p> shape.
            # Record the FIRST inline-paragraph candidate but keep scanning
            # — a later Page-Properties match should still win.
            if not inline_fallback:
                p_parent = strong.find_parent("p")
                if p_parent is not None:
                    full = p_parent.get_text(strip=True)
                    if full.startswith(label):
                        rest = full[len(label):].lstrip()
                        if rest.startswith(":"):
                            rest = rest[1:].lstrip()
                        inline_fallback = str(rest)
                    else:
                        inline_fallback = str(full)
        return inline_fallback
    ```

    Apply the SAME walk-up-to-`<th>/<td>` pattern to `_extract_link`:

    ```python
    def _extract_link(soup: BeautifulSoup) -> str:
        """First <a href=...> inside the cell adjacent to <strong>Report Link</strong>.

        Walks up to the nearest <th>/<td> ancestor of the matching <strong>
        (mirrors _extract_label_value Pass 1). Inline-paragraph fallback:
        if the strong sits directly in a <p>, search that <p> for an <a>.
        Returns raw href; sanitization happens later in grid_service.
        """
        matches = soup.find_all(
            "strong",
            string=lambda s: s is not None and s.strip() == "Report Link",
        )
        for strong in matches:
            cell = strong.find_parent(["th", "td"])
            if cell is not None:
                sibling = cell.find_next_sibling(["td", "th"])
                if sibling is None:
                    continue
                a = sibling.find("a", href=True)
                if a is not None:
                    return str(a["href"]).strip()
                continue
            # Inline-paragraph fallback.
            p_parent = strong.find_parent("p")
            if p_parent is not None:
                a = p_parent.find("a", href=True)
                if a is not None:
                    return str(a["href"]).strip()
        return ""
    ```

    STEP C — Add the per-field Start/End paren-strip in `parse_index_html`.

    Add a small private helper near the top of the module (just below `_FIELD_LABELS`):

    ```python
    def _strip_parens(value: str) -> str:
        """Strip a single matching pair of leading "(" + trailing ")".

        Safe-by-design: only strips when BOTH endpoints are present and the
        parens are at the very edges of the (already-trimmed) string.
        Idempotent on values without parens. Used ONLY for Start/End fields
        — applying it elsewhere would corrupt legitimate values like
        "Acme (lead)".
        """
        if len(value) >= 2 and value.startswith("(") and value.endswith(")"):
            return value[1:-1].strip()
        return value
    ```

    In `parse_index_html`, change the `start=` and `end=` kwargs to wrap the extracted value:

    ```python
        start=_strip_parens(_extract_label_value(soup, "Start")),
        end=_strip_parens(_extract_label_value(soup, "End")),
    ```

    All other field kwargs stay byte-identical.

    STEP D — Run the full parser test file:

    ```bash
    pytest tests/v2/test_joint_validation_parser.py -x
    ```

    All 14 tests (10 existing + 4 new) MUST pass. Then run the full v2 suite to confirm no downstream regressions:

    ```bash
    pytest tests/v2/ -x
    ```

    Expected: full v2 suite stays green (parser is consumed by `joint_validation_store.py` and `joint_validation_grid_service.py`; their tests use the synthetic shape which still works).

    AVOID:
    - Do NOT introduce regex-based HTML parsing — BS4 navigation only.
    - Do NOT rename `_extract_label_value` or `_extract_link` — both are imported by the test module (`from app_v2.services.joint_validation_parser import _extract_label_value, _extract_link`).
    - Do NOT move the Start/End cleanup INTO `_extract_label_value` — keep the helper field-agnostic so unit tests of the helper stay simple.
    - Do NOT add new fields to `ParsedJV` — out of scope.
    - Do NOT modify the existing fixture HTML files under `tests/v2/fixtures/` — they pin the existing shapes by intention.
    - Do NOT touch routers, templates, CSS, the grid service, the store, `nl_agent.py`, `chat_agent.py`, or `chat_loop.py` — strictly out of scope.
    - Do NOT promote case-insensitive label matching — the existing Korean `담당자` byte-equal test depends on case-sensitive comparison.
  </action>
  <verify>
    <automated>pytest tests/v2/test_joint_validation_parser.py -x && pytest tests/v2/ -x</automated>
  </verify>
  <done>
    - 4 new tests pass: `test_parse_page_properties_with_wrapped_value`, `test_parse_prefers_page_properties_over_heading_for_duplicate_label`, `test_parse_strips_parens_from_start_and_end_only`, `test_parse_paren_strip_does_not_apply_to_other_fields`.
    - All 10 existing parser tests still pass (zero regressions).
    - Full v2 suite stays green (parity with the pre-fix test count: any test failure outside the parser file means a downstream consumer was perturbed and must be investigated).
    - `_extract_label_value` and `_extract_link` use `find_parent(["th", "td"])` (no `"p"` in the parents list) followed by `find_next_sibling(["td", "th"])`; `<p>` is reached only via the inline-paragraph fallback path through `find_parent("p")`.
    - `parse_index_html` wraps `start=` and `end=` extractions in `_strip_parens(...)`; no other field is wrapped.
    - `ParsedJV` field set is unchanged (still 13 fields with `: str = ""` defaults).
  </done>
</task>

</tasks>

<verification>
**Automated:**
- `pytest tests/v2/test_joint_validation_parser.py -x` — 14 tests pass (10 existing + 4 new).
- `pytest tests/v2/ -x` — full v2 suite green.
- `grep -n 'find_parent(\["th", "td"\])' app_v2/services/joint_validation_parser.py` — present in BOTH `_extract_label_value` AND `_extract_link` (the canonical shape-fix marker).
- `grep -n '_strip_parens' app_v2/services/joint_validation_parser.py` — exactly two callsites in `parse_index_html` (`start=` and `end=`), plus the helper definition.

**Sanity check on real fixtures (mental-model only — files are untracked, do NOT modify):**
- After landing the fix, `python3 -c "from app_v2.services.joint_validation_parser import parse_index_html; print(parse_index_html(open('content/joint_validation/3193868109/index.html','rb').read()))"` should still print every field correctly populated (synthetic shape is unaffected).
- If the user later drops a real Confluence-exported `index.html` under `content/joint_validation/<id>/`, the parser will populate Status/Customer/etc. correctly via the new Page-Properties walk-up path.
</verification>

<success_criteria>
- Real Confluence Page-Properties shape extracts values from the next-sibling `<td>`, including through `<div class="content-wrapper">` and `<p>` wrappers.
- Duplicate-label-in-heading-and-table picks the table-row value, not the heading.
- Start/End values: `(2024-03-01)` → `2024-03-01`, `2024-03-01` → `2024-03-01` (idempotent).
- Customer/AP Model and other fields: parens preserved.
- All 9 prior parser tests + 4 new tests + downstream v2 tests pass.
- No changes outside the parser module and its test file.
</success_criteria>

<output>
After completion, create `.planning/quick/260507-ksn-jv-parser-handle-page-properties-next-si/260507-ksn-SUMMARY.md` summarising:
- Bug root cause (innermost `find_parent` resolving to `<p>` instead of `<td>`).
- Fix mechanism (two-pass walk: Page-Properties first via `find_parent(["th","td"])`, then inline-paragraph fallback; disambiguation across multiple `<strong>` matches).
- Start/End paren-strip helper and its scoping rationale.
- Tests added (4 new) and tests preserved (10 existing).
- v2 suite test count delta.
</output>
