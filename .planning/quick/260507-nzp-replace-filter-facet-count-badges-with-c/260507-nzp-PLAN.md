---
task: 260507-nzp
type: quick
description: Replace filter facet count badges with chips listing actual selected values (up to 10 + "+N more")
files_modified:
  - app_v2/templates/overview/index.html
  - app_v2/static/css/app.css
  - tests/v2/test_joint_validation_routes.py
must_haves:
  truths:
    - "Active filter summary above the JV grid shows actual selected values (not just a count)"
    - "Each facet renders up to 10 value chips; if more selected, shows 10 + '+N more' chip"
    - "Each facet has its own deterministic, distinct color shared by all chips within that facet"
    - "Empty facets (count == 0) render NO row in the active-filters summary"
    - "OOB swap target id #overview-filter-badges remains byte-stable so HTMX merge-by-id keeps working"
    - "Test test_post_overview_grid_returns_oob_blocks (asserts id=overview-filter-badges) still passes unchanged"
    - "Test test_get_overview_with_filters_round_trip_url (asserts 'badge' in r.text) still passes unchanged"
    - "No backend service / view-model / router change — render-layer-only swap"
  artifacts:
    - path: "app_v2/templates/overview/index.html"
      provides: "Updated filter_badges_oob block rendering chips from selected_filters instead of counts from active_filter_counts"
    - path: "app_v2/static/css/app.css"
      provides: "New .ff-row / .ff-label / .ff-chip[.c-N] / .ff-more rules anchored to Dashboard_v2 tiny-chip language"
    - path: "tests/v2/test_joint_validation_routes.py"
      provides: "New test_overview_filter_chips_render_actual_values + test_overview_filter_chips_overflow_shows_plus_n_more covering the chip swap and the +N more behavior"
  key_links:
    - from: "app_v2/templates/overview/index.html (filter_badges_oob block)"
      to: "selected_filters dict in router context"
      via: "Jinja for-loop over FILTERABLE_COLUMNS reading selected_filters[col]"
      pattern: "selected_filters\\[col\\]"
    - from: "app_v2/templates/overview/index.html (filter_badges_oob block)"
      to: "app_v2/static/css/app.css"
      via: "class names .ff-row / .ff-label / .ff-chip.c-N / .ff-more"
      pattern: "ff-(row|label|chip|more)"
---

<objective>
Replace the count-only filter badges in the JV listing's active-filter summary
with small colored chips that list the actual selected values per facet
(up to 10), followed by a "+N more" chip when overflow occurs.

Currently the strip above the JV grid renders rows like:

    [ status: 2 ]  [ customer: 1 ]

It should instead render rows like:

    Status:    [ In Progress ] [ Verified ]
    Customer:  [ Samsung ]

with each facet's chips sharing a single subtle color drawn from the
Dashboard_v2 token palette (greens / accent-blue / amber / violet / red /
neutral). When more than 10 values are selected for one facet, exactly 10
value chips render followed by a "+N more" chip.

Purpose: The current "X: 2" badge tells the user *that* a filter is active
but not *what* is filtered. They have to open the popover to see what's
selected. Listing the actual values turns the strip into a passive,
glanceable summary — closer to the Dashboard_v2 design language.

Output:
- Render-layer-only swap inside `{% block filter_badges_oob %}` of
  `app_v2/templates/overview/index.html`. NO change to
  `joint_validation_grid_service.py`, NO change to `routers/overview.py`,
  NO new template context keys. The router already passes
  `selected_filters` (a dict[str, list[str]] keyed by FILTERABLE_COLUMNS)
  alongside `vm.active_filter_counts`; we simply consume the existing
  values list instead of the count.
</objective>

<context>
@.planning/STATE.md
@CLAUDE.md

@app_v2/templates/overview/index.html
@app_v2/templates/overview/_filter_bar.html
@app_v2/routers/overview.py
@app_v2/services/joint_validation_grid_service.py
@app_v2/static/css/tokens.css
@app_v2/static/css/app.css
@tests/v2/test_joint_validation_routes.py

<interfaces>
<!-- Existing data shape the template already receives. We only consume
     selected_filters (already in context) instead of active_filter_counts. -->

From app_v2/services/joint_validation_grid_service.py:
```python
FILTERABLE_COLUMNS: Final[tuple[str, ...]] = (
    "status", "customer", "ap_company", "device", "controller", "application",
)

class JointValidationGridViewModel(BaseModel):
    active_filter_counts: dict[str, int]   # e.g. {"status": 2, "customer": 1, ...}
    # ... other fields unchanged
```

From app_v2/routers/overview.py (both GET /overview and POST /overview/grid build the same ctx):
```python
ctx = {
    "vm": vm,
    "selected_filters": filters,            # dict[str, list[str]] — KEYS = FILTERABLE_COLUMNS, VALUES = the user's chosen options
    "active_tab": "overview",
    "active_filter_counts": vm.active_filter_counts,
    "all_platform_ids": [],
    "conf_url": conf_url,
}
```

So inside `filter_badges_oob` the template already has:
- `selected_filters["status"]` → `["In Progress", "Verified"]` (list[str])
- `selected_filters["ap_company"]` → `["Qualcomm"]`
- ... one entry per FILTERABLE_COLUMNS key.
</interfaces>

<existing_state>
File `app_v2/templates/overview/index.html`, current filter_badges_oob block
(lines 33-43):

```jinja
{% block filter_badges_oob %}
  <div id="overview-filter-badges" hx-swap-oob="true" class="px-3 pt-2">
    {% for col, count in vm.active_filter_counts.items() %}
      {% if count > 0 %}
        <span class="badge bg-secondary me-1">
          {{ col | e }}: {{ count | e }}
        </span>
      {% endif %}
    {% endfor %}
  </div>
{% endblock %}
```

That block is rendered both in full-page GET /overview AND in POST /overview/grid
(via block_names=["grid", "count_oob", "filter_badges_oob", "pagination_oob"] in
routers/overview.py:231) — HTMX OOB-merges by id="overview-filter-badges".
</existing_state>

<existing_palette>
From `app_v2/static/css/tokens.css` (already defined, do NOT add new tokens):

| Token        | Color (background paired with) |
|--------------|--------------------------------|
| --accent / --accent-soft / --accent-ink | blue       |
| --green  / --green-soft                  | green      |
| --red    / --red-soft                    | red        |
| --amber  / --amber-soft                  | amber      |
| --violet / --violet-soft                 | violet     |
| --ink-2 + #f4f6f8                        | neutral grey |

Existing precedent in `app_v2/static/css/app.css` lines 1074-1088
(`.tiny-chip.ok|info|warn|neutral|err` — Dashboard_v2.html lines 263-268).
The new `.ff-chip` rules MUST mirror this exact pattern (soft background,
saturated foreground, 11px / 600 weight, radius-pill) so the new strip
visually belongs to the same family.
</existing_palette>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add .ff-* chip CSS rules anchored to Dashboard_v2 tiny-chip palette</name>
  <files>app_v2/static/css/app.css</files>
  <action>
Append a new section to `app_v2/static/css/app.css` (after the existing
`.tiny-chip` block at lines 1074-1088) that styles the active-filter
summary as named-color chip rows. Keep the rules scoped to `.ff-*` so they
do NOT conflict with `.tiny-chip` / `.chip` / `.ai-chip`.

Insert this block AT END OF FILE (or immediately after `.tiny-chip.err`,
around line 1088, whichever keeps the diff minimal — append-at-end is
preferred to avoid renumbering nearby comments):

```css
/* §Active-filter summary chips (260507-nzp).
   Anchored to Dashboard_v2.html tiny-chip language (lines 263-268) — soft
   background + saturated ink, 11px / 600, pill radius. One row per facet:
   "Label: chip chip chip +N more". Visible above the JV grid in
   #overview-filter-badges; rendered by overview/index.html
   filter_badges_oob block. */
.ff-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 4px;
}
.ff-row:last-child { margin-bottom: 0; }
.ff-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-2);
  letter-spacing: -.005em;
  margin-right: 2px;
}
.ff-chip {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border-radius: var(--radius-pill);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: -.005em;
  /* default neutral fallback — overridden by .c-N variants */
  background: #f4f6f8;
  color: var(--ink-2);
}
/* 6 deterministic palette slots — one per FILTERABLE_COLUMNS entry.
   c-1 status, c-2 customer, c-3 ap_company, c-4 device, c-5 controller,
   c-6 application. Mapping is done in the template via a Jinja dict so
   both color and slot stay byte-stable. */
.ff-chip.c-1 { background: var(--accent-soft); color: var(--accent-ink); }
.ff-chip.c-2 { background: var(--green-soft);  color: var(--green); }
.ff-chip.c-3 { background: var(--violet-soft); color: var(--violet); }
.ff-chip.c-4 { background: var(--amber-soft);  color: var(--amber); }
.ff-chip.c-5 { background: var(--red-soft);    color: var(--red); }
.ff-chip.c-6 { background: #f4f6f8;            color: var(--ink-2); }
.ff-more {
  /* "+N more" overflow indicator — always neutral so it visually
     subordinates to the colored value chips of its row. */
  background: transparent;
  color: var(--mute);
  font-style: normal;
}
```

Why this CSS shape (and not extending `.tiny-chip` / `.chip`):
- `.tiny-chip` is already used in OEM/UFS table cells (app.css:1023+) with
  semantic suffixes (ok/info/warn/neutral/err). Reusing those suffixes
  here would conflate "filter facet color" with "row status semantics" —
  a filter chip for "Samsung" is neither ok nor warn nor err.
- `.chip` (app.css:760+) is the Dashboard chip-toggle variant with
  hover/active states for interactive picker UI; the active-filter strip
  is read-only and should NOT have hover ink.
- A scoped `.ff-*` namespace is the cheapest way to express "same visual
  vocabulary, different semantic axis" without touching either neighbor.

Constraints:
- NO new tokens added to tokens.css (matches Phase 04 D-UIF-01 / D-UIF-06
  precedent: only consume existing tokens; promote to token only when ≥2
  consumers exist).
- DO NOT introduce a 7th color slot. If FILTERABLE_COLUMNS ever grows past
  6, callers should reuse c-1..c-6 modulo (cycle). For today's 6 facets
  the mapping is 1:1.
  </action>
  <verify>
    <automated>
grep -c "^.ff-row {" app_v2/static/css/app.css | grep -q "^1$" && \
grep -c "^.ff-chip {" app_v2/static/css/app.css | grep -q "^1$" && \
grep -c "^.ff-chip.c-[1-6] {" app_v2/static/css/app.css | grep -q "^6$" && \
grep -q ".ff-more" app_v2/static/css/app.css && \
echo "OK"
    </automated>
  </verify>
  <done>
- `.ff-row`, `.ff-label`, `.ff-chip`, `.ff-chip.c-1` through `.ff-chip.c-6`,
  and `.ff-more` rules exist in app.css.
- All color values are CSS variables from tokens.css OR the literal
  `#f4f6f8` neutral already used elsewhere in app.css (no new hex codes
  introduced).
- No edits anywhere else in app.css; this is an append.
  </done>
</task>

<task type="auto">
  <name>Task 2: Rewrite filter_badges_oob block to render chips from selected_filters</name>
  <files>app_v2/templates/overview/index.html</files>
  <action>
Replace the `{% block filter_badges_oob %} … {% endblock %}` block in
`app_v2/templates/overview/index.html` (currently lines 33-43) with a
chip-emitting version.

Constraints (BLOCKING — verify each before commit):
- Wrapper element MUST keep `id="overview-filter-badges"` and
  `hx-swap-oob="true"` byte-stable (HTMX OOB merge target). Tests
  test_post_overview_grid_returns_oob_blocks (line 148) and the
  block_names registration in routers/overview.py:231 both depend on this.
- Iterate FILTERABLE_COLUMNS in fixed order so chip-row order is
  deterministic across renders (not Python dict insertion order, which
  happens to match today but is not contract).
- Use `selected_filters` (already in context — see <interfaces>) as the
  source of values, NOT vm.active_filter_counts. Counts stay in the
  view-model for tests but no longer drive UI.
- Preserve every dynamic value through Jinja's `| e` autoescape filter
  (status / customer / ap_company / device / controller / application
  values come from BS4-parsed Confluence pages — XSS surface, T-05-03-04
  in Phase 01).
- Show NO row when `selected_filters[col]` is empty — empty facets
  collapse cleanly. Equivalent to today's `{% if count > 0 %}` gate.
- Cap visible chips at 10. When `len(selected_filters[col]) > 10`, render
  the first 10 (slice `[:10]`) followed by a single
  `<span class="ff-chip ff-more">+N more</span>` where N =
  `len(selected_filters[col]) - 10`. Slice must be `[:10]` exactly — NOT
  `[:9]` (i.e. at exactly 10 selected, NO "+N more" appears; at 11
  selected, 10 chips + "+1 more").
- Each chip on a given row gets the same `.c-N` variant — one color per
  facet. Mapping is fixed by the order of FILTERABLE_COLUMNS:

  | col          | variant |
  |--------------|---------|
  | status       | c-1     |
  | customer     | c-2     |
  | ap_company   | c-3     |
  | device       | c-4     |
  | controller   | c-5     |
  | application  | c-6     |

- Each row carries a human-readable label (NOT the raw key). Mapping
  matches the labels already used in `_filter_bar.html` macro calls so
  the summary strip mirrors the picker labels:

  | col          | label        |
  |--------------|--------------|
  | status       | Status       |
  | customer     | Customer     |
  | ap_company   | AP Company   |
  | device       | Device       |
  | controller   | Controller   |
  | application  | Application  |

Replacement block (paste verbatim — comment header explains the swap and
points future readers at the CSS in app.css):

```jinja
{# Active-filter summary (260507-nzp): replaces the prior
   "{{ col }}: {{ count }}" badge strip. Each facet renders one row:
   "<Label>: <chip> <chip> ... [+N more]". Up to 10 value chips per row;
   row is omitted entirely when the facet has zero selected values.
   Chip color is determined per-facet via .c-1..c-6 in app.css
   (anchored to Dashboard_v2.html tiny-chip language, lines 263-268).

   The wrapper #overview-filter-badges + hx-swap-oob is byte-stable —
   POST /overview/grid still emits this block via block_names so HTMX
   merges it back into the page on every filter change. The chip
   markup itself is render-layer only; selected_filters is supplied
   verbatim by the existing router context (see routers/overview.py).

   Inline {% set %} maps below define the col → label and col → variant
   mappings explicitly so the contract is reviewable at the call site
   instead of being scattered across the codebase. #}
{% block filter_badges_oob %}
  {%- set ff_labels = {
      "status":      "Status",
      "customer":    "Customer",
      "ap_company":  "AP Company",
      "device":      "Device",
      "controller":  "Controller",
      "application": "Application",
  } -%}
  {%- set ff_variants = {
      "status":      "c-1",
      "customer":    "c-2",
      "ap_company":  "c-3",
      "device":      "c-4",
      "controller":  "c-5",
      "application": "c-6",
  } -%}
  <div id="overview-filter-badges" hx-swap-oob="true" class="px-3 pt-2">
    {% for col in ["status", "customer", "ap_company", "device", "controller", "application"] %}
      {%- set values = selected_filters.get(col) or [] -%}
      {%- if values -%}
        {%- set total = values | length -%}
        {%- set visible = values[:10] -%}
        {%- set overflow = total - 10 -%}
        <div class="ff-row" data-facet="{{ col | e }}">
          <span class="ff-label">{{ ff_labels[col] | e }}:</span>
          {% for v in visible %}
            <span class="ff-chip {{ ff_variants[col] }}">{{ v | e }}</span>
          {% endfor %}
          {% if overflow > 0 %}
            <span class="ff-chip ff-more">+{{ overflow | e }} more</span>
          {% endif %}
        </div>
      {%- endif -%}
    {% endfor %}
  </div>
{% endblock %}
```

Why iterate the literal column list (not `FILTERABLE_COLUMNS` from Python):
- The view-model exposes `vm.active_filter_counts` whose dict key order
  matches FILTERABLE_COLUMNS, but `selected_filters` is built by
  `_parse_filter_dict` in the router with the literal argument order.
  Hard-coding the same 6-tuple in the template makes column order
  obvious to template readers AND removes a hidden dependency on Python
  dict-ordering semantics. (Same convention the macro calls in
  `_filter_bar.html` already use — six explicit picker_popover() calls
  in column order.)

Why `selected_filters.get(col) or []` (not `selected_filters[col]`):
- Defense in depth: even though _parse_filter_dict always populates all
  6 keys today, a future refactor that merges filter parsing could
  produce a sparse dict; `.get(col) or []` keeps the template a no-op
  rather than 500-ing on KeyError.
  </action>
  <verify>
    <automated>
# Block exists, OOB target byte-stable, references new selected_filters source.
grep -q 'id="overview-filter-badges"' app_v2/templates/overview/index.html && \
grep -q 'hx-swap-oob="true"' app_v2/templates/overview/index.html && \
grep -q 'ff-row' app_v2/templates/overview/index.html && \
grep -q 'ff-chip' app_v2/templates/overview/index.html && \
grep -q 'ff-more' app_v2/templates/overview/index.html && \
grep -q 'selected_filters' app_v2/templates/overview/index.html && \
grep -q 'values\[:10\]' app_v2/templates/overview/index.html && \
# Old "{{ col }}: {{ count }}" pattern is gone.
( ! grep -q '{{ col | e }}: {{ count | e }}' app_v2/templates/overview/index.html ) && \
# Boot the existing test suite to prove no regressions.
.venv/bin/pytest tests/v2/test_joint_validation_routes.py -x -q
    </automated>
  </verify>
  <done>
- `filter_badges_oob` block in overview/index.html renders chip rows from
  `selected_filters` and the new color/label maps.
- `id="overview-filter-badges"` and `hx-swap-oob="true"` preserved
  byte-stable on the wrapper.
- `vm.active_filter_counts` no longer referenced inside the block (the
  field stays on the view-model, just not consumed here — keeps the
  service-layer test `test_active_filter_counts_match_input` green).
- Existing tests `test_post_overview_grid_returns_oob_blocks` and
  `test_get_overview_with_filters_round_trip_url` both still pass.
  </done>
</task>

<task type="auto">
  <name>Task 3: Add tests pinning the new chip rendering + +N more behavior, then manually verify on dev server</name>
  <files>tests/v2/test_joint_validation_routes.py</files>
  <action>
Append two new tests to `tests/v2/test_joint_validation_routes.py`, plus a
small fixture helper that writes 11 fake JV folders so we can exercise
overflow without depending on the existing `jv_dir_with_one` fixture.

The tests are HTML-substring assertions (not BS4 parsing) — keeps the
test fast and matches the style already used elsewhere in this file
(lines 121-148). They pin three contracts:

1. When values are selected, chip(s) appear in the response with the
   correct `.ff-chip.c-N` variant for the facet.
2. When ≤10 values are selected, NO "+N more" chip appears.
3. When >10 values are selected, EXACTLY 10 chips render plus one
   `+N more` chip with the right N.

Append (after `test_post_overview_grid_sets_hx_push_url`, around line 158):

```python
# ---------------------------------------------------------------------------
# 260507-nzp — active-filter summary chips
# ---------------------------------------------------------------------------


def _write_many_jv_status_values(root: Path, n: int) -> list[str]:
    """Create N fake JV folders each with a distinct status value.

    Returns the list of N status strings so callers can request them all
    as filter values. Uses 9-digit numeric folder names so they validate
    against the JointValidationRow.confluence_page_id pattern (^\\d+$).
    """
    statuses: list[str] = []
    for i in range(n):
        page_id = f"99000000{i:02d}"  # 9-digit, distinct per i
        status = f"S{i:02d}"
        folder = root / page_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(
            f"<html><body><h1>Title {i}</h1>"
            f"<table><tr><th>Status</th><td>{status}</td></tr></table>"
            f"</body></html>",
            encoding="utf-8",
        )
        statuses.append(status)
    return statuses


def test_overview_filter_chips_render_actual_values(
    jv_dir_with_one: Path, client: TestClient
) -> None:
    """260507-nzp: facets show chips listing the selected values, not just a count."""
    r = client.get(
        "/overview",
        params=[
            ("status", "In Progress"),
            ("status", "Verified"),
            ("customer", "Samsung"),
        ],
    )
    assert r.status_code == 200
    # Wrapper byte-stable for HTMX OOB merge.
    assert 'id="overview-filter-badges"' in r.text
    # Status row: label + 2 chips, c-1 variant.
    assert 'data-facet="status"' in r.text
    assert 'class="ff-chip c-1">In Progress</span>' in r.text
    assert 'class="ff-chip c-1">Verified</span>' in r.text
    # Customer row: label + 1 chip, c-2 variant.
    assert 'data-facet="customer"' in r.text
    assert 'class="ff-chip c-2">Samsung</span>' in r.text
    # Inactive facets (ap_company etc.) DO NOT render rows.
    assert 'data-facet="ap_company"' not in r.text
    # No "+N more" because each facet has ≤10 selected.
    assert "ff-more" not in r.text


def test_overview_filter_chips_overflow_shows_plus_n_more(
    tmp_path: Path, client: TestClient, monkeypatch
) -> None:
    """260507-nzp: >10 selected values per facet renders 10 chips + '+N more'."""
    # Point JV_ROOT at a tmp dir we control so we can create 11 distinct
    # status values without polluting the real content/joint_validation tree.
    from app_v2.services import joint_validation_store as _store
    monkeypatch.setattr(_store, "JV_ROOT", tmp_path)

    statuses = _write_many_jv_status_values(tmp_path, 11)
    assert len(statuses) == 11

    params = [("status", s) for s in statuses]
    r = client.get("/overview", params=params)
    assert r.status_code == 200

    # Exactly 10 c-1 value chips render — count by occurrences of the
    # c-1 variant attribute (the +N more chip uses ff-more, not c-1).
    visible_chip_count = r.text.count('class="ff-chip c-1">')
    assert visible_chip_count == 10, (
        f"expected 10 visible chips, got {visible_chip_count}"
    )

    # Exactly 1 "+N more" indicator with N == 1 (11 total - 10 visible).
    assert r.text.count("ff-more") == 1
    assert "+1 more" in r.text


def test_overview_filter_chips_no_active_filters_renders_empty_wrapper(
    jv_dir_with_one: Path, client: TestClient
) -> None:
    """260507-nzp: with zero selected values the wrapper renders but contains no rows."""
    r = client.get("/overview")
    assert r.status_code == 200
    # Wrapper present (HTMX needs a stable target).
    assert 'id="overview-filter-badges"' in r.text
    # No facet rows.
    assert "ff-row" not in r.text
    assert "ff-chip" not in r.text
```

Manual UI verification step (record observation in the commit body):
1. Start the dev server: `.venv/bin/uvicorn app_v2.main:app --reload --port 8765`
2. Open http://localhost:8765/overview in a browser.
3. Open the Status picker, select 2 values (e.g. "In Progress", "Verified").
   Confirm a "Status:" row appears above the grid with two soft-blue
   pill chips.
4. Open the Customer picker, select 1 value. Confirm a second row
   appears below in soft-green.
5. Use a fixture or the URL bar to land on /overview?status=A&status=B&...
   with 11+ status values. Confirm 10 chips + "+1 more" (or "+N more"
   for N>1).
6. Click "Clear all". Confirm both rows vanish (wrapper present but
   empty).
7. Note any visual regressions in the commit message under
   "Manual UAT".

If the dev server is unavailable in this environment, fall back to a
representative snapshot: `.venv/bin/python -c "from fastapi.testclient
import TestClient; from app_v2.main import app; c=TestClient(app);
print(c.get('/overview?status=A&status=B&customer=X').text[:5000])"` and
visually inspect the rendered HTML for the new ff-row markup.
  </action>
  <verify>
    <automated>
.venv/bin/pytest tests/v2/test_joint_validation_routes.py -x -q -k "filter_chips or filter_badge or filter_oob or overview_grid"
    </automated>
  </verify>
  <done>
- Three new tests exist in test_joint_validation_routes.py:
  test_overview_filter_chips_render_actual_values,
  test_overview_filter_chips_overflow_shows_plus_n_more,
  test_overview_filter_chips_no_active_filters_renders_empty_wrapper.
- All three tests pass.
- Existing tests in tests/v2/test_joint_validation_routes.py still pass
  (no regressions).
- Manual UI verification performed against the dev server (or representative
  snapshot if no server available); observation noted in the eventual
  commit body.
  </done>
</task>

</tasks>

<verification>
After all three tasks:

1. Full v2 test pass: `.venv/bin/pytest tests/v2/ -x -q`
2. Lint: `.venv/bin/ruff check app_v2/ tests/v2/test_joint_validation_routes.py`
3. Template smoke test: `grep -q 'ff-chip c-' app_v2/templates/overview/index.html`
4. CSS diff is append-only — no rules edited above existing tiny-chip block:
   `git diff app_v2/static/css/app.css | grep -E '^-[^-]' | grep -v '^--- ' | wc -l`
   should print `0` (zero deletions).
5. Backend untouched (must be empty diff):
   `git diff app_v2/services/ app_v2/routers/`
   should print nothing — this is a render-layer-only change.
</verification>

<success_criteria>
- Active-filter summary above the JV grid shows colored chips listing the
  actual selected values (not just counts).
- Each facet has its own deterministic, distinct color drawn from the
  Dashboard_v2 token palette (status=blue, customer=green, ap_company=violet,
  device=amber, controller=red, application=neutral).
- Up to 10 chips per facet; "+N more" chip when overflow.
- Empty facets render no row.
- HTMX OOB swap target id #overview-filter-badges byte-stable; existing
  HTMX merge-by-id mechanism continues to work on POST /overview/grid.
- All existing tests in tests/v2/test_joint_validation_routes.py and
  tests/v2/test_joint_validation_grid_service.py pass unchanged.
- Three new tests pass, locking in:
  - the chip-rendering contract (correct .c-N + label per facet),
  - the +N more overflow behavior at exactly 10/11,
  - the empty-state collapse (wrapper present, no rows).
- Zero diff to backend services/routers — confirms render-layer-only.
</success_criteria>

<output>
After completion:
1. Commit with message:
   `feat(overview): replace filter facet count badges with value chips (+N more) [quick-260507-nzp]`
2. Update STATE.md "Quick Tasks Completed" table with the entry.
3. Write `260507-nzp-SUMMARY.md` in
   `.planning/quick/260507-nzp-replace-filter-facet-count-badges-with-c/`
   capturing: files changed, color mapping decision (subtle palette over
   saturated), and the manual UI observation.
</output>
