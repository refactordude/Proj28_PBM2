---
quick_id: 260507-lcc
type: quick
wave: 1
depends_on: []
files_modified:
  - app_v2/services/joint_validation_grid_service.py
  - app_v2/templates/overview/_pagination.html
  - tests/v2/test_jv_pagination.py
  - tests/v2/test_phase02_invariants.py
autonomous: true
requirements:
  - QT-260507-lcc-01
must_haves:
  truths:
    - "Pagination bar width stays stable as user navigates within the same group of 10 (always renders the full group when the group has ≥10 pages)"
    - "User on any page in group N (1-indexed) sees a contiguous run of page numbers covering only that group's pages"
    - "Right chevron `>` is visible only when at least one page exists past the current group; clicking it advances to the FIRST page of the next group"
    - "Left chevron `<` is visible only when the current group is not the first; clicking it returns to the LAST page of the previous group"
    - "When `page_count == 1` (or 0 rows) the pagination nav still does not render (preserves existing `{% if vm.page_count > 1 %}` guard)"
    - "All 19 service-layer + template-shape tests in tests/v2/test_jv_pagination.py + tests/v2/test_phase02_invariants.py pass after rewrite; no test outside the pagination scope is touched"
    - "Full v2 suite stays green (the prior 546-passing baseline becomes the new baseline; net delta = test edits inside the pagination scope only)"
  artifacts:
    - path: "app_v2/services/joint_validation_grid_service.py"
      provides: "GROUP_SIZE constant, group-of-10 _build_page_links, prev_group_page/next_group_page on JointValidationGridViewModel, populated by build_joint_validation_grid_view_model"
      contains: "GROUP_SIZE = 10"
    - path: "app_v2/templates/overview/_pagination.html"
      provides: "Group-aware Bootstrap pagination control with conditional chevrons; ellipsis branch removed"
      contains: "vm.prev_group_page"
    - path: "tests/v2/test_jv_pagination.py"
      provides: "Updated P8/P9/P10 + new boundary tests (1, 5, 10, 11, 13, 21, 25 pages); new tests for prev_group_page/next_group_page"
      contains: "prev_group_page"
    - path: "tests/v2/test_phase02_invariants.py"
      provides: "Phase 02 invariant tests updated to reflect group-of-10 contract (Test 45 still asserts pl.label/pl.num loop; outdated ellipsis-only assertions removed if any)"
  key_links:
    - from: "app_v2/templates/overview/_pagination.html"
      to: "app_v2/services/joint_validation_grid_service.py JointValidationGridViewModel"
      via: "vm.prev_group_page, vm.next_group_page, vm.page_links, vm.page, vm.page_count"
      pattern: "vm\\.prev_group_page|vm\\.next_group_page"
    - from: "build_joint_validation_grid_view_model"
      to: "_build_page_links + group_page helpers"
      via: "service-internal call at line ~456 (call site stays byte-stable for _build_page_links signature)"
      pattern: "_build_page_links\\(page_int, page_count\\)"
---

<objective>
Replace the sliding-window-with-ellipsis pagination algorithm in the Joint Validation grid with a fixed page-group-of-10 algorithm so the bar's width stays stable as the user navigates between pages within a group.

Purpose: The current behavior (e.g., 10 pages, current=5 → `1 … 4 5 6 … 10` (7 items); current=1 → `1 2 … 10` (4 items)) makes the bar grow and shrink visibly during navigation, which the user finds "weird." A fixed group-of-10 layout keeps the page-bar width visually stable inside a group; group transitions are visually implied by `<` / `>` chevrons whose targets are the boundary pages of the adjacent group.

Output:
- New `GROUP_SIZE = 10` constant in `app_v2/services/joint_validation_grid_service.py`.
- Rewritten `_build_page_links(page, page_count)` returning ONLY pages in the current group (no ellipsis).
- Two new fields on `JointValidationGridViewModel`: `prev_group_page: int | None` and `next_group_page: int | None`, populated by `build_joint_validation_grid_view_model`.
- Simplified `app_v2/templates/overview/_pagination.html`: chevron `<li>` blocks render only when `vm.prev_group_page`/`vm.next_group_page` is not None; ellipsis branch (`{% if pl.num is none %}`) removed; chevron hx-vals point at the group-boundary page.
- Updated tests in `tests/v2/test_jv_pagination.py` (P8/P9/P10 rewritten; new boundary cases) and `tests/v2/test_phase02_invariants.py` (any ellipsis-pinning assertions retired).
- v2 suite stays green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@./CLAUDE.md
@app_v2/services/joint_validation_grid_service.py
@app_v2/templates/overview/_pagination.html
@app_v2/routers/overview.py
@tests/v2/test_jv_pagination.py
@tests/v2/test_phase02_invariants.py

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From app_v2/services/joint_validation_grid_service.py (lines 106-134):
```python
class PageLink(BaseModel):
    """B3 — Pydantic submodel for pagination links.
    ``num=None`` marks an ellipsis ("…") sentinel.
    """
    label: str
    num: int | None = None  # None marks ellipsis ("…")

class JointValidationGridViewModel(BaseModel):
    rows: list[JointValidationRow]
    filter_options: dict[str, list[str]]
    active_filter_counts: dict[str, int]
    sort_col: str
    sort_order: Literal["asc", "desc"]
    total_count: int
    # Phase 02 Plan 02-04 — pagination (D-UI2-13/14, B3).
    page: int = 1
    page_count: int = 1
    page_links: list[PageLink] = Field(default_factory=list)
```

From app_v2/services/joint_validation_grid_service.py (line 456 — call site):
```python
page_links = _build_page_links(page_int, page_count)
```
Call site signature stays byte-stable (`_build_page_links(page: int, page_count: int) -> list[PageLink]`). Only the body changes.

From app_v2/templates/overview/_pagination.html (current shape — to be simplified):
- Lines 7-11: Prev chevron with `vm.page - 1` target.
- Lines 12-23: page-link loop with ellipsis branch (`{% if pl.num is none %}`).
- Lines 24-28: Next chevron with `vm.page + 1` target.
The `{% if vm.page_count > 1 %}` guard at line 4 stays intact.

From app_v2/routers/overview.py (line 217):
```python
block_names=["grid", "count_oob", "filter_badges_oob", "pagination_oob"]
```
`pagination_oob` block name is correct; no router changes needed.
</interfaces>

<state_supersession>
<!-- Phase 02 STATE.md decision supersession (per CONTEXT.md note). -->
The pagination algorithm in D-UI2-13 was originally specified as a sliding-window-with-ellipsis variant. This quick task supersedes that detail of D-UI2-13 with a fixed group-of-10 algorithm per direct user request 2026-05-07. D-UI2-14 (`JV_PAGE_SIZE=15`, two-layer Query/Form validation, HX-Push-Url default-omit, hidden page input, sortable_th page reset) is unchanged. PageLink Pydantic submodel (B3) is unchanged. Single-source-of-truth `_pagination.html` partial (B5) included twice in `overview/index.html` is unchanged.
</state_supersession>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Atomic group-of-10 pagination rewrite (service + VM + template + tests)</name>
  <files>app_v2/services/joint_validation_grid_service.py, app_v2/templates/overview/_pagination.html, tests/v2/test_jv_pagination.py, tests/v2/test_phase02_invariants.py</files>
  <behavior>
    Service-layer (`_build_page_links` and `JointValidationGridViewModel`) — new contract. ALL examples below assume `GROUP_SIZE = 10`.

    Group math (canonical):
      - Pages are 1-indexed; group_index = (page - 1) // GROUP_SIZE  (0-based).
      - Group `g` covers pages `g * GROUP_SIZE + 1` through `min((g + 1) * GROUP_SIZE, page_count)`.
      - prev_group_page = group_index * GROUP_SIZE  if group_index > 0 else None
        (i.e., the LAST page of the previous group: 11→10, 21→20, 15→10).
      - next_group_page = (group_index + 1) * GROUP_SIZE + 1  if (group_index + 1) * GROUP_SIZE < page_count else None
        (i.e., the FIRST page of the next group: 1..10→11, 11..20→21).

    `_build_page_links(page, page_count)` returns the page numbers in CURRENT group as `PageLink(label=str(n), num=n)` — no ellipsis ever. Boundary cases:
      - page_count == 0: return [] (preserved).
      - page_count == 1: return [PageLink(label="1", num=1)] (preserved).
      - 5 pages, current=3: [1,2,3,4,5] → 5 PageLink objects, label="1".."5", num=1..5.
      - 10 pages, current=5: [1..10] → 10 PageLink objects.
      - 10 pages, current=10: [1..10] → 10 PageLink objects (current is in last/only group).
      - 13 pages, current=1: [1..10] → 10 PageLink objects.
      - 13 pages, current=11: [11,12,13] → 3 PageLink objects (group 2 truncated by page_count).
      - 25 pages, current=15: [11..20] → 10 PageLink objects (full middle group).
      - 25 pages, current=21: [21..25] → 5 PageLink objects (last group truncated).

    `JointValidationGridViewModel` gains TWO new fields:
      - prev_group_page: int | None = None
      - next_group_page: int | None = None

    `build_joint_validation_grid_view_model` populates them per the math above using `page_int` and `page_count` (the same locals already computed at lines 443-456).

    Template (`overview/_pagination.html`) — new contract:
      - Outer `{% if vm.page_count > 1 %}` guard preserved.
      - Prev chevron `<li>` rendered ONLY when `vm.prev_group_page is not none`; hx-vals carries `"page": "{{ vm.prev_group_page }}"`. When None, the entire `<li>` block is omitted (NOT rendered as disabled — recommended to truly minimize bar width).
      - Page-link loop drops the `{% if pl.num is none %}` ellipsis branch entirely (dead branch under group-of-10).
      - Next chevron `<li>` rendered ONLY when `vm.next_group_page is not none`; hx-vals carries `"page": "{{ vm.next_group_page }}"`. When None, the `<li>` block is omitted.
      - Both chevrons retain `<i class="bi bi-chevron-left"></i>` / `<i class="bi bi-chevron-right"></i>` icons, hx-include="#overview-filter-form", hx-target="#overview-grid", hx-swap="outerHTML", hx-push-url="true", aria-label="Previous"/"Next", and the existing `sort` / `order` hx-vals threading (matches the page-link loop pattern at the existing line 18).

    Test contract (`tests/v2/test_jv_pagination.py`) — explicit tests to rewrite/add:

    REWRITE (replace ellipsis examples with group-of-10 equivalents):
      - test_page_links_short (P8): keep as-is — already asserts `[1,2,3]` for 3 pages → still passes byte-equal under new contract.
      - test_page_links_ellipsis_left (P9): RENAME to `test_page_links_group_2` and rewrite to assert `_build_page_links(8, 10)` returns `[1,2,3,4,5,6,7,8,9,10]` (group 1 = pages 1..10, current=8 still inside group 1). Drop ellipsis assertions.
      - test_page_links_ellipsis_both_sides (P10): RENAME to `test_page_links_group_full_middle` and rewrite to assert `_build_page_links(15, 25)` returns model_dumps `[{"label":"11","num":11}, ..., {"label":"20","num":20}]` (10 entries, group 2 of 25-page total).
      - test_page_links_returns_pagelink_instances (P10b): keep as-is — still valid (B3 contract preserved).

    ADD (boundary cases — the user-supplied contract):
      - test_page_links_5_pages_current_3: assert `_build_page_links(3, 5) == [1..5]` (5 entries).
      - test_page_links_10_pages_current_10: assert `_build_page_links(10, 10) == [1..10]` (current is in last/only group).
      - test_page_links_13_pages_current_1: assert `_build_page_links(1, 13) == [1..10]` (10 entries).
      - test_page_links_13_pages_current_11: assert `_build_page_links(11, 13) == [11,12,13]` (3 entries; group 2 truncated by page_count).
      - test_page_links_25_pages_current_15: assert `_build_page_links(15, 25) == [11..20]` (full middle group).
      - test_page_links_25_pages_current_21: assert `_build_page_links(21, 25) == [21..25]` (last group truncated).

    ADD (prev_group_page / next_group_page contract — assert via VM, not standalone helper, since VM is the public surface):
      - test_prev_group_page_none_in_first_group: 13 rows × page_size 15 → 1 page → vm.prev_group_page is None. Then 25 rows × page_size 1 (override fixture or use _build_page_links directly) → vm at page=5 → prev_group_page is None.
        SIMPLER: assert via direct VM construction with N JVs and explicit page param using `_write_n_jvs` + `build_joint_validation_grid_view_model(tmp_path, page=5, page_size=1)` so 25 rows × page_size=1 = 25 pages, page=5 sits in group 1 (group_index=0) → prev_group_page is None, next_group_page=11.
      - test_prev_group_page_at_group_boundary: 25 rows × page_size 1, page=11 → vm.prev_group_page == 10, vm.next_group_page == 21.
      - test_next_group_page_none_in_last_group: 25 rows × page_size 1, page=21 → vm.prev_group_page == 20, vm.next_group_page is None (since (group_index+1)*10 = 30 > 25).
      - test_both_chevrons_none_when_single_group: 5 rows × page_size 15 → 1 page → vm.prev_group_page is None AND vm.next_group_page is None.
      - test_both_chevrons_none_when_exactly_one_full_group: 10 rows × page_size 1 → 10 pages → vm at page=1: prev_group_page is None, next_group_page is None (no next group exists since (0+1)*10 = 10 is NOT < page_count=10).

    PRESERVE (no behavior change):
      - test_page_size_slicing_default_page_1, test_page_size_slicing_page_2, test_page_clamp_too_high, test_page_clamp_zero_or_negative, test_page_count_when_empty, test_page_count_exact_multiple, test_page_count_off_by_one, test_filter_options_built_from_all_rows_not_paged, test_total_count_unchanged_meaning — all still pass byte-equal.
      - All Task-2 router tests (P13-P19, P15a-f) and Task-3 template tests (P20-P24) — assert on infrastructure (HX-Push-Url, OOB id, hidden input, sortable_th hx-vals) that this rewrite preserves; should pass byte-equal.

    Phase 02 invariant test (`tests/v2/test_phase02_invariants.py`):
      - test_pagination_uses_page_links_loop (line 807): KEEP — still asserts `{% for pl in vm.page_links %}` + `pl.label` + `pl.num` references in template. Group-of-10 still uses the same loop.
      - test_pagination_partial_included_twice (line 827): KEEP — still 2 includes.
      - test_pagination_partial_size_sanity (line 839): KEEP — ≤60 lines. New template should be smaller (~24-28 lines) since the ellipsis branch is removed and chevron blocks become simpler. Sanity holds.
      - Search the file for any other ellipsis-specific assertion (`grep -n '"…"\|ellipsis\|pl\.num is none' tests/v2/test_phase02_invariants.py`) and remove if present. The 3 tests above are the only ones touching pagination per the grep results.
  </behavior>
  <action>
    Single atomic commit. Service + template + tests change together so the working tree never has half-implemented contract.

    PART A — `app_v2/services/joint_validation_grid_service.py`:
    1. Add module constant near the existing pagination-helper region (above `_build_page_links`):
       ```python
       # Phase 02 Plan 02-04 superseded 2026-05-07 (quick task 260507-lcc):
       # group-of-10 pagination replaces sliding-window-with-ellipsis. GROUP_SIZE
       # picks 10 because (a) it matches Bootstrap's pagination-sm aesthetic,
       # (b) ≤10 numbered links don't wrap on the standard JV grid width, and
       # (c) >10 leads to too-many-jumps friction; <10 leads to too-many-group-
       # boundaries friction. Treat as a fixed product decision, NOT a setting.
       GROUP_SIZE = 10
       ```

    2. Rewrite `_build_page_links(page, page_count)` body. Signature unchanged. New body:
       ```python
       def _build_page_links(
           page: int,
           page_count: int,
       ) -> list[PageLink]:
           """Return PageLinks for the current group of GROUP_SIZE pages.

           Group-of-10 algorithm (replaces the original Phase 02 sliding-window
           algorithm 2026-05-07 — quick task 260507-lcc). Pages partition into
           groups of GROUP_SIZE: group 1 = pages 1..10, group 2 = pages 11..20,
           etc. The bar always shows ALL pages in the current group; group
           boundaries are signalled by `<` / `>` chevrons in the template (see
           ``prev_group_page`` / ``next_group_page`` on the view model).

           Examples:
             - 5 pages, current=3:  [1,2,3,4,5]            (one group, fully shown)
             - 13 pages, current=1: [1,2,3,4,5,6,7,8,9,10] (group 1 full)
             - 13 pages, current=11:[11,12,13]             (group 2 truncated)
             - 25 pages, current=15:[11,12,...,20]         (group 2 full middle)
             - 25 pages, current=21:[21,22,23,24,25]       (last group truncated)
           """
           if page_count <= 0:
               return []
           if page_count == 1:
               return [PageLink(label="1", num=1)]
           group_index = (page - 1) // GROUP_SIZE
           start_page = group_index * GROUP_SIZE + 1
           end_page = min((group_index + 1) * GROUP_SIZE, page_count)
           return [PageLink(label=str(n), num=n) for n in range(start_page, end_page + 1)]
       ```
       Leave `PageLink.num: int | None = None` definition AS-IS — the ellipsis sentinel branch is no longer reachable from `_build_page_links`, but the model stays byte-stable for B3 invariants. Note in PageLink docstring is updated:
       Replace lines 106-119 PageLink class with the same model but updated docstring last paragraph from `"num=None marks an ellipsis ("…") sentinel."` to `"num=None historically marked an ellipsis sentinel; group-of-10 algorithm (260507-lcc) does not emit ellipses, but the model stays for B3 byte-stability."`.

    3. Add two fields to `JointValidationGridViewModel` (after `page_links`):
       ```python
       # Quick task 260507-lcc (group-of-10 pagination supersedes D-UI2-13's
       # sliding-window): None when the chevron should not render.
       prev_group_page: int | None = None
       next_group_page: int | None = None
       ```

    4. In `build_joint_validation_grid_view_model`, after the existing `page_links = _build_page_links(page_int, page_count)` line, compute and pass the two new fields:
       ```python
       # Quick task 260507-lcc — group-of-10 chevron targets:
       _group_index = (page_int - 1) // GROUP_SIZE
       prev_group_page = _group_index * GROUP_SIZE if _group_index > 0 else None
       _next_group_first_page = (_group_index + 1) * GROUP_SIZE + 1
       next_group_page = (
           _next_group_first_page
           if (_group_index + 1) * GROUP_SIZE < page_count
           else None
       )
       ```
       Then add `prev_group_page=prev_group_page, next_group_page=next_group_page,` to the JointValidationGridViewModel(...) constructor call at the bottom of the function.

    5. KEEP the existing `_build_page_links(page_int, page_count)` call site at line 456 byte-stable. Signature unchanged.

    PART B — `app_v2/templates/overview/_pagination.html` (full rewrite, ≤30 lines):
    ```jinja
    {# _pagination.html — Phase 02 Plan 02-04 (D-UI2-13/14), group-of-10 algorithm
       (260507-lcc supersedes original sliding-window-with-ellipsis).
       B5: single source of truth; included by .panel-footer AND block pagination_oob.
       B3: vm.page_links is list[PageLink]; iterate via pl.label / pl.num. #}
    {% if vm.page_count > 1 %}
    <nav aria-label="Joint Validation pages">
      <ul class="pagination pagination-sm mb-0">
        {% if vm.prev_group_page is not none %}
        <li class="page-item">
          <a class="page-link" href="#"
             hx-post="/overview/grid" hx-include="#overview-filter-form"
             hx-vals='{"page": "{{ vm.prev_group_page }}", "sort": "{{ vm.sort_col | e }}", "order": "{{ vm.sort_order | e }}"}'
             hx-target="#overview-grid" hx-swap="outerHTML" hx-push-url="true"
             aria-label="Previous"><i class="bi bi-chevron-left"></i></a>
        </li>
        {% endif %}
        {% for pl in vm.page_links %}
          <li class="page-item {% if pl.num == vm.page %}active{% endif %}" {% if pl.num == vm.page %}aria-current="page"{% endif %}>
            <a class="page-link"
               {% if pl.num != vm.page %}href="#" hx-post="/overview/grid" hx-include="#overview-filter-form" hx-vals='{"page": "{{ pl.num }}", "sort": "{{ vm.sort_col | e }}", "order": "{{ vm.sort_order | e }}"}' hx-target="#overview-grid" hx-swap="outerHTML" hx-push-url="true"{% endif %}>
              {{ pl.label | e }}
            </a>
          </li>
        {% endfor %}
        {% if vm.next_group_page is not none %}
        <li class="page-item">
          <a class="page-link" href="#"
             hx-post="/overview/grid" hx-include="#overview-filter-form"
             hx-vals='{"page": "{{ vm.next_group_page }}", "sort": "{{ vm.sort_col | e }}", "order": "{{ vm.sort_order | e }}"}'
             hx-target="#overview-grid" hx-swap="outerHTML" hx-push-url="true"
             aria-label="Next"><i class="bi bi-chevron-right"></i></a>
        </li>
        {% endif %}
      </ul>
    </nav>
    {% endif %}
    ```

    Notes on the template:
    - Two top-level `<li>` chevron blocks now wrapped in `{% if vm.prev_group_page is not none %}` / `{% if vm.next_group_page is not none %}` — chevrons truly disappear when there's no adjacent group (per CONTEXT.md §2 user preference).
    - Page-link loop unchanged in shape (still iterates `vm.page_links` accessing `pl.label` + `pl.num`) so Phase 02 invariant `test_pagination_uses_page_links_loop` stays green.
    - The dead `{% if pl.num is none %}` ellipsis branch is REMOVED. PageLink.num is still typed `int | None` but `_build_page_links` no longer emits None values.
    - Line count target: ≤30 lines (under the existing 60-line sanity ceiling).
    - All HTMX attributes (`hx-post`, `hx-include`, `hx-target`, `hx-swap`, `hx-push-url`) on chevrons are byte-equal to the existing pattern, so router-side OOB / push-URL tests stay green.

    PART C — Tests in `tests/v2/test_jv_pagination.py`:
    1. Locate `test_page_links_ellipsis_left` (line 147) — RENAME the test function to `test_page_links_group_1_full` and replace the body:
       ```python
       def test_page_links_group_1_full(tmp_path: Path) -> None:
           """P9 (260507-lcc form): With 10 pages, page=8 (still in group 1), all 10 pages render."""
           links = _build_page_links(8, 10)
           dicts = [pl.model_dump() for pl in links]
           expected = [{"label": str(n), "num": n} for n in range(1, 11)]
           assert dicts == expected, f"Got: {dicts}"
       ```

    2. Locate `test_page_links_ellipsis_both_sides` (line 166) — RENAME to `test_page_links_group_2_full_middle` and replace the body:
       ```python
       def test_page_links_group_2_full_middle(tmp_path: Path) -> None:
           """P10 (260507-lcc form): With 25 pages, page=15 (group 2), pages 11..20 render — no ellipsis."""
           links = _build_page_links(15, 25)
           dicts = [pl.model_dump() for pl in links]
           expected = [{"label": str(n), "num": n} for n in range(11, 21)]
           assert dicts == expected, f"Got: {dicts}"
       ```

    3. After `test_page_links_returns_pagelink_instances` (line 182), ADD the boundary tests:
       ```python
       def test_page_links_5_pages(tmp_path: Path) -> None:
           """260507-lcc: 5 pages, current=3 → [1,2,3,4,5] (one group fully shown)."""
           assert [pl.model_dump() for pl in _build_page_links(3, 5)] == (
               [{"label": str(n), "num": n} for n in range(1, 6)]
           )

       def test_page_links_10_pages_current_10(tmp_path: Path) -> None:
           """260507-lcc: 10 pages, current=10 → [1..10] (current sits in only/last group)."""
           assert [pl.model_dump() for pl in _build_page_links(10, 10)] == (
               [{"label": str(n), "num": n} for n in range(1, 11)]
           )

       def test_page_links_13_pages_current_1(tmp_path: Path) -> None:
           """260507-lcc: 13 pages, current=1 → group 1 [1..10]."""
           assert [pl.model_dump() for pl in _build_page_links(1, 13)] == (
               [{"label": str(n), "num": n} for n in range(1, 11)]
           )

       def test_page_links_13_pages_current_11(tmp_path: Path) -> None:
           """260507-lcc: 13 pages, current=11 → group 2 truncated [11,12,13]."""
           assert [pl.model_dump() for pl in _build_page_links(11, 13)] == [
               {"label": "11", "num": 11},
               {"label": "12", "num": 12},
               {"label": "13", "num": 13},
           ]

       def test_page_links_25_pages_current_21(tmp_path: Path) -> None:
           """260507-lcc: 25 pages, current=21 → last group truncated [21..25]."""
           assert [pl.model_dump() for pl in _build_page_links(21, 25)] == (
               [{"label": str(n), "num": n} for n in range(21, 26)]
           )

       def test_prev_next_group_page_first_group(tmp_path: Path) -> None:
           """260507-lcc: page=5 of 25 (group 1) → prev=None, next=11."""
           # 25 rows × page_size=1 → 25 pages
           for i in range(1, 26):
               _write_jv(tmp_path, str(i).zfill(3), title=f"JV {i}")
           vm = build_joint_validation_grid_view_model(tmp_path, page=5, page_size=1)
           assert vm.page_count == 25
           assert vm.prev_group_page is None
           assert vm.next_group_page == 11

       def test_prev_next_group_page_at_boundary(tmp_path: Path) -> None:
           """260507-lcc: page=11 of 25 (group 2) → prev=10, next=21."""
           for i in range(1, 26):
               _write_jv(tmp_path, str(i).zfill(3), title=f"JV {i}")
           vm = build_joint_validation_grid_view_model(tmp_path, page=11, page_size=1)
           assert vm.prev_group_page == 10
           assert vm.next_group_page == 21

       def test_prev_next_group_page_last_group(tmp_path: Path) -> None:
           """260507-lcc: page=21 of 25 (group 3) → prev=20, next=None."""
           for i in range(1, 26):
               _write_jv(tmp_path, str(i).zfill(3), title=f"JV {i}")
           vm = build_joint_validation_grid_view_model(tmp_path, page=21, page_size=1)
           assert vm.prev_group_page == 20
           assert vm.next_group_page is None

       def test_prev_next_group_page_single_page(tmp_path: Path) -> None:
           """260507-lcc: page_count=1 → both chevron targets are None."""
           _write_jv(tmp_path, "001", title="single")
           vm = build_joint_validation_grid_view_model(tmp_path, page=1, page_size=15)
           assert vm.page_count == 1
           assert vm.prev_group_page is None
           assert vm.next_group_page is None

       def test_prev_next_group_page_exactly_one_full_group(tmp_path: Path) -> None:
           """260507-lcc: page_count == GROUP_SIZE (10) → no next group exists."""
           for i in range(1, 11):
               _write_jv(tmp_path, str(i).zfill(3), title=f"JV {i}")
           vm = build_joint_validation_grid_view_model(tmp_path, page=1, page_size=1)
           assert vm.page_count == 10
           assert vm.prev_group_page is None
           assert vm.next_group_page is None
       ```

    4. Verify NO other test in `tests/v2/test_jv_pagination.py` references `…`, ellipsis, or sliding-window behavior. The remaining tests (slicing, clamping, total_count, filter_options) are orthogonal to the pagination algorithm and must pass byte-equal.

    PART D — Tests in `tests/v2/test_phase02_invariants.py`:
    1. Run `grep -n '"…"\|ellipsis\|pl\.num is none' tests/v2/test_phase02_invariants.py` to confirm nothing else pins ellipsis behavior. The earlier search returned only the 3 tests at lines 807/827/839, none of which assert ellipsis presence — they assert template loop shape, include count, and line-count sanity. NO changes needed in `test_phase02_invariants.py` if grep returns no hits beyond those.
    2. If the grep DOES find other lines, remove the ellipsis-specific assertions and document each removal with a `# 260507-lcc: removed — sliding-window superseded by group-of-10` comment.

    PART E — STATE.md decision log update:
    Append a new line under `### Decisions` in `.planning/STATE.md` (do NOT rewrite Phase 02 entries — append-only):
    ```
    - **2026-05-07 (quick 260507-lcc):** JV pagination algorithm flipped from sliding-window-with-ellipsis to fixed group-of-10 (GROUP_SIZE=10) — bar width stays stable within a group; chevrons advance to first/last page of adjacent group. Supersedes the algorithm portion of D-UI2-13; D-UI2-14 (page_size=15, two-layer Query/Form validation, HX-Push-Url default-omit) unchanged. PageLink Pydantic submodel kept byte-stable (B3); `num=None` ellipsis sentinel no longer reachable but still a valid model.
    ```

    Rule: Single commit. Tests + service + template + STATE.md all land together. No two-step "test red, then green" splits — quick task atomicity.

    Anti-patterns to avoid:
    - Do NOT promote `GROUP_SIZE` to settings or YAML.
    - Do NOT remove `PageLink.num: int | None = None` (preserves B3 byte-stability).
    - Do NOT touch `app_v2/routers/overview.py` block_names (already correct).
    - Do NOT touch any other template, service, or test file.
    - Do NOT change the `_build_page_links` signature.
    - Do NOT change `JV_PAGE_SIZE` or any other D-UI2-14 contract.
    - Do NOT change the `{% if vm.page_count > 1 %}` outer guard or the include count in `overview/index.html`.
  </action>
  <verify>
    <automated>cd /home/yh/Desktop/02_Projects/Proj28_PBM2 && python -m pytest tests/v2/test_jv_pagination.py tests/v2/test_phase02_invariants.py -x -q 2>&1 | tail -30 && python -m pytest tests/v2 -q 2>&1 | tail -15</automated>
  </verify>
  <done>
    - `tests/v2/test_jv_pagination.py` — all tests pass (renamed P9/P10 + 9 new boundary/group tests + preserved slicing/clamping tests).
    - `tests/v2/test_phase02_invariants.py` — all 3 pagination invariants (line 807, 827, 839) still green.
    - Full `tests/v2` suite — no regressions vs. the prior 546-passing baseline.
    - `app_v2/services/joint_validation_grid_service.py` — contains `GROUP_SIZE = 10`, group-of-10 `_build_page_links`, and `prev_group_page` / `next_group_page` populated on the VM.
    - `app_v2/templates/overview/_pagination.html` — ≤30 lines, no ellipsis branch, conditional chevron blocks driven by `vm.prev_group_page` / `vm.next_group_page`.
    - `.planning/STATE.md` — new decision-log entry appended documenting the supersession.
    - One atomic commit on `ui-improvement` branch with subject `fix(jv-pagination): switch to fixed group-of-10 algorithm (260507-lcc)`.
    - Manual smoke (optional, not required for done): visit `/overview` in browser; navigate via `>` chevron — bar width stays stable; click `<` to return.
  </done>
</task>

</tasks>

<verification>
1. `python -m pytest tests/v2/test_jv_pagination.py -v` — all listed tests pass; the renamed P9/P10 tests + 9 new boundary tests + preserved slicing/clamping tests are green.
2. `python -m pytest tests/v2/test_phase02_invariants.py -v -k pagination` — `test_pagination_uses_page_links_loop`, `test_pagination_partial_included_twice`, `test_pagination_partial_size_sanity` pass.
3. `python -m pytest tests/v2 -q` — full v2 suite green; no regressions outside the pagination scope.
4. `grep -c 'GROUP_SIZE' app_v2/services/joint_validation_grid_service.py` ≥ 4 (constant def + 3 usages).
5. `grep -c 'prev_group_page\|next_group_page' app_v2/services/joint_validation_grid_service.py` ≥ 6 (2 field defs + 2 local computations + 2 ctor passes).
6. `grep -c 'prev_group_page\|next_group_page' app_v2/templates/overview/_pagination.html` ≥ 4 (2 `is not none` guards + 2 hx-vals interpolations).
7. `wc -l app_v2/templates/overview/_pagination.html` ≤ 30 (well under the 60-line invariant).
8. `grep -c "is none" app_v2/templates/overview/_pagination.html` ≤ 2 (only the two chevron `is not none` checks; ellipsis branch removed).
9. `grep -n '_build_page_links' app_v2/services/joint_validation_grid_service.py` shows the call site at the existing `~line 456` location with byte-stable signature `_build_page_links(page_int, page_count)`.
10. `grep -n 'block_names' app_v2/routers/overview.py | grep pagination_oob` returns the existing line at 217 unchanged.
</verification>

<success_criteria>
- The Joint Validation pagination bar visibly stops growing/shrinking as the user navigates pages 1..10 of a 13-page result; only the chevron `>` toggles in/out at the group boundary.
- 13 pages, current=1: bar shows `1 2 3 4 5 6 7 8 9 10 >`. Click `>` lands on page 11; bar shows `< 11 12 13`. Click `<` lands on page 10; bar returns to `1 2 3 4 5 6 7 8 9 10 >`.
- 25 pages, current=15: bar shows `< 11 12 13 14 15 16 17 18 19 20 >`. 25 pages, current=21: bar shows `< 21 22 23 24 25`.
- 1 page total: pagination nav does NOT render (preserved guard).
- All 19 pagination + invariant tests pass; full v2 suite green; no test outside the scope is touched.
- No router-level changes; no settings changes; no other template / service / CSS touched.
- STATE.md decision log records the supersession of D-UI2-13's algorithm portion.
- Single atomic commit on `ui-improvement`.
</success_criteria>

<output>
After completion, create `.planning/quick/260507-lcc-pagination-switch-from-sliding-window-el/260507-lcc-SUMMARY.md` documenting the algorithm swap (with the canonical worked examples), test deltas (rewrite + add list), and the STATE.md decision-log entry.
</output>
