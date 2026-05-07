---
phase: 260507-ksn
plan: 01
subsystem: joint_validation
tags: [bugfix, parser, bs4, jv, tdd]
requires:
  - app_v2/services/joint_validation_parser.py (existing)
  - tests/v2/test_joint_validation_parser.py (existing)
provides:
  - Correct metadata extraction from real Confluence Page-Properties exports
  - Heading-vs-table-row disambiguation for duplicate labels
  - Per-field Start/End parens-strip cleanup
affects:
  - app_v2/services/joint_validation_store.py (downstream — picks up corrected ParsedJV transparently on next mtime change)
  - app_v2/services/joint_validation_grid_service.py (downstream — same)
tech-stack:
  added: []
  patterns:
    - "BS4 walk-up via find_parent(['th','td']) (drop 'p' from parents) so <p>-wrapped <strong>label</strong> routes to the real cell"
    - "Iterate find_all('strong', ...) matches to disambiguate heading-only vs Page-Properties matches"
    - "Per-field cleanup helper (_strip_parens) called from parse_index_html — keeps _extract_label_value field-agnostic"
key-files:
  created: []
  modified:
    - app_v2/services/joint_validation_parser.py
    - tests/v2/test_joint_validation_parser.py
decisions:
  - "Drop 'p' from find_parent parents list — innermost-match resolution was the root cause of blank fields on real exports; <p> is now reachable only via the inline-paragraph fallback (find_parent('p'))"
  - "Disambiguation iterates ALL <strong> matches and prefers any non-empty Page-Properties result over a captured inline-paragraph candidate — heading-only matches contribute neither path"
  - "Empty-cell behaviour preserved: a Page-Properties row with an empty next-sibling cell stops scanning further matches (honours test_parse_first_match_wins_on_duplicate_label semantics within the table-row shape)"
  - "_strip_parens lives in parse_index_html callsite (start=, end= kwargs only) — applying it inside _extract_label_value would have corrupted Customer values like 'Acme (lead)'"
metrics:
  duration: "~7min"
  completed_date: "2026-05-07"
  tasks: 1
  files: 2
  tests_added: 4
  tests_total_parser: 14
  v2_suite: "546 passed, 5 skipped"
---

# Quick 260507-ksn: JV parser — handle Page-Properties next-sibling-td shape + duplicate-label disambiguation + Start/End paren-strip

**One-liner:** Fix `_extract_label_value` / `_extract_link` to walk up to `<th>/<td>` (not the inner `<p>`) so real Confluence Page-Properties exports populate every metadata field; disambiguate heading-vs-table duplicates; strip `(YYYY-MM-DD)` parens scoped to Start/End only.

## Bug Root Cause

On real Confluence-exported `index.html` files, the Page Properties macro emits this shape:

```html
<tr>
  <td><p><strong>Status</strong></p></td>
  <td><div class="content-wrapper"><p>Planned</p></div></td>
</tr>
```

The pre-fix code did:

```python
strong = soup.find("strong", string=...)
cell = strong.find_parent(["th", "td", "p"])   # ← innermost match wins
```

`find_parent` with multiple tag candidates resolves to the **innermost** matching ancestor — the inner `<p>` wrapping the `<strong>` — not the outer `<td>`. The code then took the `<p>`-fallback branch, called `cell.get_text(strip=True)` → `"Status"`, stripped the leading label + `:`, and returned `""`. The next-sibling `<td>` containing `Planned` was never visited.

The synthetic shipped fixtures (`<th><strong>X</strong></th><td>Y</td>`) accidentally worked because there's no `<p>` between the `<strong>` and the `<th>`.

A second, related failure: when the SAME label appeared in BOTH a heading-style location (`<h1><strong>Status</strong></h1>`) and a Page-Properties row, `soup.find()` (first-match-wins, document order) locked onto the heading, found no usable sibling/value, and returned `""`.

## Fix Mechanism

### 1. Two-pass walk in `_extract_label_value`

```python
matches = soup.find_all("strong", string=lambda s: s.strip() == label)
for strong in matches:
    # Pass 1: Page-Properties shape (preferred)
    cell = strong.find_parent(["th", "td"])     # NB: no "p" — that was the bug
    if cell is not None:
        sibling = cell.find_next_sibling(["td", "th"])
        if sibling is not None:
            value = str(sibling.get_text(strip=True))
            if value:
                return value
            return ""   # empty cell — preserve "first match wins" semantics
        continue        # no sibling — try later matches
    # Pass 2: inline-paragraph fallback — capture FIRST, keep scanning
    if not inline_fallback:
        p_parent = strong.find_parent("p")
        ...
return inline_fallback
```

Disambiguation: iterate all `<strong>` matches; a Page-Properties hit at ANY position wins over any inline-paragraph match captured earlier. A heading-only `<h1><strong>Status</strong></h1>` (no `<th>/<td>` ancestor, no `<p>` ancestor) contributes nothing and the loop falls through to a later table-row match.

### 2. Same walk-up applied to `_extract_link`

Mirrors Pass 1 of `_extract_label_value`. `<th>/<td>` walk-up first, then `<p>`-only fallback. Returns first valid `<a href>` from the resolved cell.

### 3. `_strip_parens` per-field cleanup

```python
def _strip_parens(value: str) -> str:
    if len(value) >= 2 and value.startswith("(") and value.endswith(")"):
        return value[1:-1].strip()
    return value
```

Called only at the `start=` and `end=` kwarg sites in `parse_index_html`. Scoping rationale: legitimate non-date values like `Customer: Acme (lead)` or `AP Model: (SM8650)` must keep their parens — applying the strip globally would corrupt them.

Idempotency: `(2024-03-01)` → `2024-03-01` → `2024-03-01` (subsequent calls are no-ops because the bare value no longer satisfies the leading/trailing paren predicate).

## Tests Added (4 new — TDD-first)

1. `test_parse_page_properties_with_wrapped_value` — covers `<td><p><strong>Field</strong></p></td><td><div class="content-wrapper"><p>value</p></div></td>` plus `<td><strong>Field</strong></td><td>value</td>` and `<td><p><strong>Field</strong></p></td><td>raw</td>` permutations.
2. `test_parse_prefers_page_properties_over_heading_for_duplicate_label` — `<h1><strong>Status</strong></h1>` followed by `<tr><td><p><strong>Status</strong></p></td><td><p>Planned</p></td></tr>` → `"Planned"`.
3. `test_parse_strips_parens_from_start_and_end_only` — both inline-paragraph and Page-Properties shapes; mixes parenthesised and bare values; asserts idempotency on the bare side.
4. `test_parse_paren_strip_does_not_apply_to_other_fields` — `Customer: Acme (lead)` and `AP Model: (SM8650)` keep their parens.

### TDD trace
- **RED (after writing tests, before fix):** 3 new tests failed (`test_parse_page_properties_with_wrapped_value`, `test_parse_prefers_page_properties_over_heading_for_duplicate_label`, `test_parse_strips_parens_from_start_and_end_only`); `test_parse_paren_strip_does_not_apply_to_other_fields` passed even pre-fix because it uses the synthetic `<th>` shape (which already worked) and the existing code returned the raw `"Acme (lead)"` / `"(SM8650)"` text — it serves as a negative-control to lock in non-regression once `_strip_parens` is added.
- **GREEN (after fix):** all 4 new tests pass; all 10 existing tests still pass (14/14 in parser file).

## Tests Preserved (10 existing — zero regressions)

`test_parse_primary_shape_all_13_fields`, `test_parse_fallback_shape_p_strong_colon`, `test_parse_missing_h1_returns_blank_title`, `test_parse_korean_label_byte_equal`, `test_parse_first_match_wins_on_duplicate_label`, `test_parse_empty_value_cell_returns_blank`, `test_parse_link_extracts_first_anchor_href`, `test_parse_label_in_anchor_walks_up_correctly`, `test_parse_strong_with_surrounding_whitespace`, `test_parse_returns_plain_str_not_navigablestring`.

## Verification Results

| Check | Result |
|-------|--------|
| `pytest tests/v2/test_joint_validation_parser.py -x -q` (pre-fix, after writing tests) | 3 failed, 11 passed (RED — expected) |
| `pytest tests/v2/test_joint_validation_parser.py -x -q` (post-fix) | **14 passed** (GREEN) |
| `pytest tests/v2/ -x -q` (full v2 suite) | **546 passed, 5 skipped, 2 warnings in 32.98s** |
| `grep -n 'find_parent(\["th", "td"\])' app_v2/services/joint_validation_parser.py` | 2 hits (lines 95, 139 — `_extract_label_value` + `_extract_link`) |
| `grep -n '_strip_parens' app_v2/services/joint_validation_parser.py` | 3 hits (def + 2 callsites: `start=`, `end=`) |

v2 suite delta: **0 — same 546 passed / 5 skipped count** as the pre-fix baseline (downstream consumers `joint_validation_store.py` and `joint_validation_grid_service.py` use the synthetic shape in their tests, so the fix is transparent).

## Deviations from Plan

None — plan executed exactly as written. The plan's prediction that `test_parse_paren_strip_does_not_apply_to_other_fields` would fail in RED was off (it passed pre-fix because the existing synthetic-shape code already returned the raw text for those fields), but this is a documentation accuracy note, not a deviation. The test still serves its purpose as a regression guard against accidental over-application of `_strip_parens`.

## Files Modified

| File | Lines added | Lines removed | Notes |
|------|-------------|---------------|-------|
| `app_v2/services/joint_validation_parser.py` | +91 | -36 | `_strip_parens` helper added; `_extract_label_value` + `_extract_link` rewritten with two-pass walk; `parse_index_html` start/end kwargs wrapped |
| `tests/v2/test_joint_validation_parser.py` | +72 | -1 | 4 new tests appended after `test_parse_returns_plain_str_not_navigablestring` |

## Commit

| Hash | Message |
|------|---------|
| `4b9a92b` | `fix(jv): handle Page Properties next-sibling-td shape + dedupe header/table labels + strip Start/End parens [quick-260507-ksn]` |

## Self-Check: PASSED

- Created files: SUMMARY.md at `.planning/quick/260507-ksn-jv-parser-handle-page-properties-next-si/260507-ksn-SUMMARY.md` (this file).
- Modified files exist: `app_v2/services/joint_validation_parser.py`, `tests/v2/test_joint_validation_parser.py`.
- Commit `4b9a92b` exists on `ui-improvement` branch.
- All 14 parser tests pass; full v2 suite green (546 passed / 5 skipped).
- No files outside `app_v2/services/joint_validation_parser.py` and `tests/v2/test_joint_validation_parser.py` were modified by this task.
