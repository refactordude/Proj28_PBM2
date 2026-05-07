---
quick_task: 260507-rmj
type: execute
wave: 1
depends_on: []
autonomous: true
files_modified:
  - app_v2/services/joint_validation_grid_service.py
  - app_v2/routers/overview.py
  - app_v2/templates/overview/_grid.html
  - app_v2/templates/overview/_filter_bar.html
  - app_v2/templates/overview/index.html
  - config/presets.example.yaml
  - tests/v2/test_joint_validation_grid_service.py
  - tests/v2/test_joint_validation_routes.py
  - tests/v2/test_overview_presets.py

must_haves:
  truths:
    - "The Joint Validation listing grid no longer renders Status, 담당자, or End column headers/cells"
    - "The Joint Validation filter bar no longer renders the Status picker popover"
    - "The active-filter chip summary block (filter_badges_oob) no longer renders Status rows"
    - "Both seed presets that previously included Status (`korean-oems-in-progress`, `pending-ufs4`) load successfully without their Status entry, and at least one non-empty facet remains so each preset still validates"
    - "GET /overview returns 200 and POST /overview/grid returns 200 with no Status/assignee/end column markup or status filter param wiring"
    - "GET /overview/preset/<name> returns 200 for the surviving presets; the Status filter is not in the URL bar's HX-Push-Url"
    - "Sort URLs requesting sort=status, sort=assignee, or sort=end fall back to the default sort (start desc) — these are no longer in SORTABLE_COLUMNS"
    - "The full v2 test suite passes green (581 → unchanged total or net change ≤ small as test edits land alongside source edits)"
  artifacts:
    - path: app_v2/templates/overview/_grid.html
      provides: "JV grid template with 9 metadata columns + actions (Title, Customer, Model Name, AP Company, AP Model, Device, Controller, Application, Start, Actions); empty-state colspan=10"
    - path: app_v2/templates/overview/_filter_bar.html
      provides: "JV filter bar with 5 picker popovers (Customer, AP Company, Device, Controller, Application); no Status picker"
    - path: app_v2/services/joint_validation_grid_service.py
      provides: "FILTERABLE_COLUMNS = 5-tuple (no status); SORTABLE_COLUMNS = 9-tuple (no status/assignee/end); DATE_COLUMNS = ('start',) only"
    - path: app_v2/routers/overview.py
      provides: "GET /overview, POST /overview/grid, GET /overview/preset/<name> with no `status` Query/Form/preset-lookup wiring"
    - path: config/presets.example.yaml
      provides: "3 seed presets, none referencing Status; korean-oems-in-progress keeps customer; pending-ufs4 keeps device"
  key_links:
    - from: "app_v2/templates/overview/_filter_bar.html"
      to: "app_v2/services/joint_validation_grid_service.FILTERABLE_COLUMNS"
      via: "5 picker_popover macro calls map 1:1 to the 5 keys in FILTERABLE_COLUMNS"
      pattern: "name=\"customer\"|name=\"ap_company\"|name=\"device\"|name=\"controller\"|name=\"application\""
    - from: "app_v2/templates/overview/index.html (filter_badges_oob block)"
      to: "selected_filters dict keys"
      via: "for-loop iterates over the 5 surviving facet keys (no \"status\")"
      pattern: '\\["customer", "ap_company", "device", "controller", "application"\\]'
    - from: "app_v2/routers/overview.py _parse_filter_dict / _build_overview_url / get_overview / post_overview_grid / get_overview_preset"
      to: "5-key filter dict shape"
      via: "no `status` parameter in any signature; no `status` key in the returned/built dicts"
      pattern: 'status:\\s*list\\[str\\]'
    - from: "tests/v2/test_overview_presets.py"
      to: "config/presets.example.yaml"
      via: "loader test pins exact slugs + non-status facet values for korean-oems-in-progress and pending-ufs4"
      pattern: 'korean\\["filters"\\]'
---

<objective>
The user wants the Joint Validation listing page (route `/overview`, labeled "Joint Validation" in the topbar) cleaned up: ditch three "less important" columns and the Status filter (also from preset YAML).

**Disambiguation note (READ FIRST):** The user said "Browse page" colloquially. The repository has THREE distinct tabs: **Joint Validation** (active_tab="overview", route /overview), **Browse** (active_tab="browse", route /browse, pivot grid), and **Ask**. The columns the user named — Status, 담당자 (assignee), End — and the Status filter only exist on the **Joint Validation** page (templates under `app_v2/templates/overview/`). The actual `/browse` pivot grid renders dynamic platform×parameter columns and has no Status/담당자/End columns or Status filter, so it is NOT the target.

The orchestrator's `task_intent` confirms this: it points at the JV filter popover commit (`260430-wzg`) and explicitly mentions "Status filter from any Browse Presets" — which maps to `config/presets.example.yaml` (the JV/Overview preset file), not `config/browse_presets.example.yaml` (the platforms+params Browse preset file, which has no `status` field at all).

Purpose: Reduce visual noise on the JV listing by hiding three rarely-needed columns and the Status filter that the user no longer cares to facet on.

Output:
- 5 source files touched (1 service, 1 router, 3 templates)
- 1 config YAML edited
- 3 test files updated to keep the v2 suite green
- One atomic commit per CLAUDE.md / GSD discipline (`docs(quick-260507-rmj): ditch Status/담당자/End columns + Status filter from JV listing & presets`)
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@app_v2/services/joint_validation_grid_service.py
@app_v2/routers/overview.py
@app_v2/templates/overview/_grid.html
@app_v2/templates/overview/_filter_bar.html
@app_v2/templates/overview/index.html
@config/presets.example.yaml
@tests/v2/test_joint_validation_grid_service.py
@tests/v2/test_joint_validation_routes.py
@tests/v2/test_overview_presets.py
@tests/v2/test_joint_validation_invariants.py

<interfaces>
<!-- Key contracts the executor needs. -->

From app_v2/services/joint_validation_grid_service.py (CURRENT):
```python
ALL_METADATA_KEYS: tuple = (
    "title", "status", "customer", "model_name", "ap_company", "ap_model",
    "device", "controller", "application", "assignee", "start", "end",
)
FILTERABLE_COLUMNS: tuple = (
    "status", "customer", "ap_company", "device", "controller", "application",
)
SORTABLE_COLUMNS: tuple = ALL_METADATA_KEYS  # alias — 12 entries
DATE_COLUMNS: tuple = ("start", "end")
DEFAULT_SORT_COL = "start"
DEFAULT_SORT_ORDER = "desc"

class JointValidationRow(BaseModel):
    confluence_page_id: str
    title: str = ""
    status: str = ""           # KEEP — parser populates from <Status> row; detail page still uses
    customer: str = ""
    model_name: str = ""
    ap_company: str = ""
    ap_model: str = ""
    device: str = ""
    controller: str = ""
    application: str = ""
    assignee: str = ""         # KEEP — parser populates from <담당자> row; detail page still uses
    start: str = ""
    end: str = ""              # KEEP — parser populates from <End> row; detail page still uses
    link: str | None = None
```

From app_v2/routers/overview.py (CURRENT signatures — must shrink):
```python
def _parse_filter_dict(status, customer, ap_company, device, controller, application) -> dict
def _build_overview_url(filters, sort_col, sort_order, page=1) -> str
def get_overview(request, status, customer, ap_company, device, controller, application, sort, order, page)
def post_overview_grid(request, status, customer, ap_company, device, controller, application, sort, order, page)
def get_overview_preset(request, name)
```

From app_v2/templates/overview/_grid.html (CURRENT):
- 12 sortable_th calls (one per ALL_METADATA_KEYS entry) + 13th plain Actions <th>
- empty-state `<td colspan="13">`
- 12 <td> per row + 13th actions <td>

From app_v2/templates/overview/_filter_bar.html (CURRENT):
- 6 picker_popover calls in this order: status, customer, ap_company, device, controller, application
- All 6 driven by `vm.filter_options[<facet>]` and `selected_filters[<facet>]`

From app_v2/templates/overview/index.html (filter_badges_oob block, lines 66-102):
- Two literal `{% set %}` maps with 6 keys each (ff_labels, ff_variants)
- Outer for-loop literal: `["status", "customer", "ap_company", "device", "controller", "application"]`
- Color variants: status=c-1, customer=c-2, ap_company=c-3, device=c-4, controller=c-5, application=c-6

INVARIANTS that must be preserved (do NOT touch):
- D-JV-04: `app_v2/services/joint_validation_parser.py` keeps `"담당자"` byte-equal as a parser label match — `test_jv_parser_korean_label_byte_equal` (test_joint_validation_invariants.py:198-203) pins this. The parser still extracts assignee from `<담당자>` rows in source HTML; we only stop displaying the field on the listing.
- D-JV-15 / D-OV-16: `_DANGEROUS_LINK_SCHEMES` 5-tuple and `_sanitize_link` — unchanged.
- `app_v2/templates/joint_validation/detail.html` — JV DETAIL page (single-row property view). KEEP Status/담당자/End rows intact. The user asked to remove "columns" (listing-grid concept), not detail-page properties. `test_get_jv_detail_renders_properties_and_iframe` (test_joint_validation_routes.py:171-182) asserts `"담당자" in r.text` against this page — must keep passing.
- D-JV-10 contract docstring text mentions "12 sortable columns" — update to "9 sortable columns" in the docstring + the FILTERABLE_COLUMNS comment that says "6 filterable columns" → "5 filterable columns" + the `assignee` (담당자) callout in that same comment.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Drop Status/assignee/end from the JV grid service core (FILTERABLE_COLUMNS, SORTABLE_COLUMNS, DATE_COLUMNS, docstrings) and from the router wiring (Query/Form params, _parse_filter_dict, _build_overview_url, preset-apply branch)</name>
  <files>app_v2/services/joint_validation_grid_service.py, app_v2/routers/overview.py</files>
  <action>
Edit `app_v2/services/joint_validation_grid_service.py`:

1. **Keep `ALL_METADATA_KEYS` unchanged** — it documents the parser's 12-field extraction surface and is referenced by parser tests. Add a comment above it noting that `status`, `assignee`, and `end` remain in the model + parser but are no longer displayed/sortable/filterable on the listing (per quick task 260507-rmj).

2. **Shrink `FILTERABLE_COLUMNS` to 5 entries** by removing `"status"`:
   ```python
   FILTERABLE_COLUMNS: Final[tuple[str, ...]] = (
       "customer", "ap_company", "device", "controller", "application",
   )
   ```
   Update the surrounding comment block (currently says "6 filterable columns per D-JV-11 — Title, Model Name, AP Model, assignee (담당자), Start, End are NOT filterable") to:
   ```
   # 5 filterable columns (260507-rmj reduces from 6 by dropping Status). Title,
   # Model Name, AP Model, Start are NOT filterable. status / assignee (담당자) /
   # end are still parsed by joint_validation_parser.py and stored on
   # JointValidationRow (used by the JV detail page) but are no longer displayed
   # or filterable on the JV listing.
   ```

3. **Replace `SORTABLE_COLUMNS = ALL_METADATA_KEYS`** with an explicit 9-tuple that drops the three removed columns:
   ```python
   # 9 sortable columns (260507-rmj reduces from 12 by dropping Status, 담당자
   # (assignee), End). The remaining 3 fields stay on JointValidationRow for the
   # detail page but their grid headers no longer render, so they cannot be sort
   # targets — _validate_sort whitelists this tuple.
   SORTABLE_COLUMNS: Final[tuple[str, ...]] = (
       "title", "customer", "model_name", "ap_company", "ap_model",
       "device", "controller", "application", "start",
   )
   ```

4. **Shrink `DATE_COLUMNS` to a 1-tuple**:
   ```python
   DATE_COLUMNS: Final[tuple[str, ...]] = ("start",)
   ```
   `end` was the only other date column; with `end` no longer sortable the date-sort branch only ever sees `start`. Keeping it a tuple (not a single string) preserves the `sort_col in DATE_COLUMNS` set-membership check shape without code changes elsewhere.

5. **DO NOT remove** `status: str = ""`, `assignee: str = ""`, `end: str = ""` from the `JointValidationRow` Pydantic model. The parser still populates them and `joint_validation/detail.html` still renders them (KEEP intact — see invariants in `<context>`).

6. **Update the module docstring** (lines 10-26): in the bullet for `D-JV-10` change "12 sortable columns" → "9 sortable columns (260507-rmj — Status, 담당자, End columns dropped from the listing)". In the bullet for `D-JV-11` change "6 popover-checklist filters (status, customer, ap_company, device, controller, application)" → "5 popover-checklist filters (customer, ap_company, device, controller, application — 260507-rmj dropped Status)".

---

Edit `app_v2/routers/overview.py`:

1. **`_parse_filter_dict`** — drop `status` from the parameter list AND from the returned dict literal. The function comment about "Filter columns enumerated explicitly" stays accurate (just one fewer entry):
   ```python
   def _parse_filter_dict(
       customer: list[str],
       ap_company: list[str],
       device: list[str],
       controller: list[str],
       application: list[str],
   ) -> dict[str, list[str]]:
       return {
           "customer": customer,
           "ap_company": ap_company,
           "device": device,
           "controller": controller,
           "application": application,
       }
   ```

2. **`_build_overview_url`** — drop `"status"` from the iteration tuple at line ~90:
   ```python
   for col in ("customer", "ap_company", "device", "controller", "application"):
   ```
   Update the docstring example URL `/overview?status=A&status=B&...` → `/overview?customer=A&customer=B&...` and the D-JV-14 reference about "?status=A&status=B" — change to `?customer=A&customer=B`.

3. **`get_overview`** — drop the `status: Annotated[list[str], Query(default_factory=list)]` parameter; drop `status` from the `_parse_filter_dict(...)` call argument list. Same shape, one fewer arg.

4. **`post_overview_grid`** — drop the `status: Annotated[list[str], Form()] = []` parameter; drop `status` from `_parse_filter_dict(...)`.

5. **`get_overview_preset`** — drop the `status=pf.get("status", []),` line from the `_parse_filter_dict(...)` call. The remaining 5 facet keys stay.

6. Update the comment block at line ~58-59 (the docstring inside `_parse_filter_dict`) — adding a new filter is now a "3-line edit (sig + dict + form param)" comment that's still accurate.
  </action>
  <verify>
    <automated>cd /home/yh/Desktop/02_Projects/Proj28_PBM2 &amp;&amp; python -c "from app_v2.services.joint_validation_grid_service import FILTERABLE_COLUMNS, SORTABLE_COLUMNS, DATE_COLUMNS, ALL_METADATA_KEYS; assert FILTERABLE_COLUMNS == ('customer', 'ap_company', 'device', 'controller', 'application'), FILTERABLE_COLUMNS; assert 'status' not in SORTABLE_COLUMNS and 'assignee' not in SORTABLE_COLUMNS and 'end' not in SORTABLE_COLUMNS, SORTABLE_COLUMNS; assert len(SORTABLE_COLUMNS) == 9, SORTABLE_COLUMNS; assert DATE_COLUMNS == ('start',), DATE_COLUMNS; assert 'status' in ALL_METADATA_KEYS and 'assignee' in ALL_METADATA_KEYS and 'end' in ALL_METADATA_KEYS, ALL_METADATA_KEYS; from app_v2.routers.overview import _parse_filter_dict, _build_overview_url; import inspect; sig = inspect.signature(_parse_filter_dict); assert 'status' not in sig.parameters, list(sig.parameters); print('OK')"</automated>
  </verify>
  <done>
    `FILTERABLE_COLUMNS` has 5 entries (no `status`); `SORTABLE_COLUMNS` has 9 entries (no `status`/`assignee`/`end`); `DATE_COLUMNS == ('start',)`; `ALL_METADATA_KEYS` unchanged at 12 entries; `JointValidationRow` still has the 3 fields; `_parse_filter_dict` / `_build_overview_url` / `get_overview` / `post_overview_grid` / `get_overview_preset` no longer accept or emit a `status` argument anywhere; module loads without ImportError.
  </done>
</task>

<task type="auto">
  <name>Task 2: Drop Status/담당자/End column markup from the grid template, drop the Status picker from the filter bar, drop the `status` row from the filter_badges_oob block, and update colspan from 13 → 10</name>
  <files>app_v2/templates/overview/_grid.html, app_v2/templates/overview/_filter_bar.html, app_v2/templates/overview/index.html, config/presets.example.yaml</files>
  <action>
Edit `app_v2/templates/overview/_grid.html`:

1. Remove three `{{ sortable_th(...) }}` lines from `<thead>`: `sortable_th("status", "Status")`, `sortable_th("assignee", "담당자")`, `sortable_th("end", "End")`. Header order becomes: Title, Customer, Model Name, AP Company, AP Model, Device, Controller, Application, Start, Actions (9 metadata + Actions = 10 cells).

2. Remove three `<td>` lines from the body row loop: `<td>{{ row.status | e }}</td>`, `<td>{{ row.assignee | e }}</td>`, `<td>{{ row.end | e }}</td>`. Body order matches header — Title, Customer, Model Name, AP Company, AP Model, Device, Controller, Application, Start, then the existing Actions `<td class="text-end">…</td>` (the edm/컨플/AI button trio is byte-stable; do not touch).

3. Update the empty-state row: `<td colspan="13" …>` → `<td colspan="10" …>`. Both header and empty-state row now total 10 cells.

4. Update the comment header (lines 1-7): change "12 sortable column headers" → "9 sortable column headers (260507-rmj dropped Status, 담당자, End)" and "Action column is the 13th column" → "Action column is the 10th column".

---

Edit `app_v2/templates/overview/_filter_bar.html`:

1. Remove the entire `picker_popover(name="status", label="Status", …)` block (lines ~26-36). The remaining 5 picker_popover calls — customer, ap_company, device, controller, application — stay byte-stable in their current order. The flex form's "Clear all" anchor (lines ~98-104) and the `<input type="hidden" name="sort">` / `name="order"` / `name="page"` triplet remain unchanged.

2. Update the docstring at the top of the file (lines 1-11): change "6 picker dropdowns" → "5 picker dropdowns (260507-rmj dropped the Status picker)". The D-UI2-09/10/11 references and form-association/OOB-badge contracts are unchanged.

---

Edit `app_v2/templates/overview/index.html`:

1. In the `{% block filter_badges_oob %}` block (lines ~66-102), update both inline `{% set %}` maps to remove the `"status"` key:
   ```jinja
   {%- set ff_labels = {
       "customer":    "Customer",
       "ap_company":  "AP Company",
       "device":      "Device",
       "controller":  "Controller",
       "application": "Application",
   } -%}
   {%- set ff_variants = {
       "customer":    "c-1",
       "ap_company":  "c-2",
       "device":      "c-3",
       "controller":  "c-4",
       "application": "c-5",
   } -%}
   ```
   Note: I am also re-numbering the variants `c-1..c-5` so the surviving facets re-occupy the lower-index palette slots (status used to claim `c-1`). This keeps the chip palette stable from the user's perspective: Customer chips stay teal-ish, AP Company stays the next color, etc., shifted up by one slot — same visual progression, just one fewer color in use. **Tests will need to update the expected variant per facet (Task 3 covers the test edits — pin: customer=c-1, ap_company=c-2, device=c-3, controller=c-4, application=c-5)**.

2. Update the for-loop literal on line ~84:
   ```jinja
   {% for col in ["customer", "ap_company", "device", "controller", "application"] %}
   ```

3. Update the surrounding comment block (lines 50-65) — the wording "260507-nzp: replaces the prior {{ col }}: {{ count }} badge strip. Each facet renders one row…" stays correct. Just change any literal listing of the 6 facets to 5: e.g., the comment "anchored to Dashboard_v2.html tiny-chip language" mentions "(status/customer/ap_company/device/controller/application)" — drop status from that listing. (See line 54-55.)

---

Edit `config/presets.example.yaml`:

1. **`korean-oems-in-progress`** — remove the `status: ["In Progress"]` entry. Keep `customer: ["Samsung", "Hyundai"]` so the preset still has a non-empty filter list (preset_store rejects entries with all-empty filter values, and rejects entries with NO valid facets at all). Resulting block:
   ```yaml
   - name: korean-oems-in-progress
     label: "Korean OEMs in progress"
     filters:
       customer: ["Samsung", "Hyundai"]
   ```

2. **`qualcomm-wearables`** — UNCHANGED (already has `ap_company: ["Qualcomm"]` + `application: ["Wearable"]`, no status entry).

3. **`pending-ufs4`** — remove the `status: ["Pending"]` entry. Keep `device: ["UFS 4.0"]` so the preset still has a non-empty filter. Resulting block:
   ```yaml
   - name: pending-ufs4
     label: "Pending UFS 4.0"
     filters:
       device: ["UFS 4.0"]
   ```
   The preset's `label: "Pending UFS 4.0"` stays as-is — the user said to remove the **filter**, not rename the preset. The chip text "Pending UFS 4.0" is the user-visible label; semantically it now means "show all UFS 4.0 devices regardless of status," which still matches the preset's intent (UFS 4.0 entries are typically pending anyway).

4. Update the YAML header comment block to:
   - Drop `status` from the example facet enumeration in the `filters:` block-comment (currently lists "status, customer, ap_company, device, controller, application").
   - Add a single line: `# (260507-rmj — Status was dropped as a filterable facet on the JV listing.)`
  </action>
  <verify>
    <automated>cd /home/yh/Desktop/02_Projects/Proj28_PBM2 &amp;&amp; grep -c 'sortable_th("status"\|sortable_th("assignee"\|sortable_th("end"' app_v2/templates/overview/_grid.html | grep -q '^0$' &amp;&amp; grep -c 'name="status"' app_v2/templates/overview/_filter_bar.html | grep -q '^0$' &amp;&amp; grep -q 'colspan="10"' app_v2/templates/overview/_grid.html &amp;&amp; ! grep -q 'colspan="13"' app_v2/templates/overview/_grid.html &amp;&amp; ! grep -q '"status":\s*"Status"' app_v2/templates/overview/index.html &amp;&amp; python -c "from app_v2.services.preset_store import load_presets; p = load_presets(); names = [x['name'] for x in p]; assert names == ['korean-oems-in-progress', 'qualcomm-wearables', 'pending-ufs4'], names; assert all('status' not in x['filters'] for x in p), p; print('OK', p)" &amp;&amp; echo OK</automated>
  </verify>
  <done>
    `_grid.html` has 9 `sortable_th(...)` calls + 1 plain Actions `<th>` and an empty-state `<td colspan="10">`; `_filter_bar.html` has 5 `picker_popover(...)` calls (no Status); `index.html` filter_badges_oob block iterates 5 facets and the variant map runs `c-1..c-5`; `config/presets.example.yaml` has 3 entries, none referencing `status`, all surviving the loader (`load_presets()` returns 3 entries with the same names as before).
  </done>
</task>

<task type="auto">
  <name>Task 3: Update tests to match the 5-facet / 9-column / no-Status reality and run the full v2 suite green</name>
  <files>tests/v2/test_joint_validation_grid_service.py, tests/v2/test_joint_validation_routes.py, tests/v2/test_overview_presets.py</files>
  <action>
Edit `tests/v2/test_joint_validation_grid_service.py`:

1. **`test_filter_status_in_progress_excludes_others`** (lines 78-84) — DELETE this test. Status is no longer filterable. (Don't replace with a `customer` equivalent — `test_six_filter_options_enumerated_from_full_set` is being repurposed in step 2 below to exercise the surviving-facet filter path.)

2. **`test_six_filter_options_enumerated_from_full_set`** (lines 87-92) — RENAME and rewrite to use a surviving facet (customer) and rename the function to `test_five_filter_options_enumerated_from_full_set`. Update the fixture rows to set `customer="X"` / `customer="Y"` and assert `vm.filter_options["customer"] == ["X", "Y"]`. (The `_write_jv` helper already accepts `customer` as a kwarg.)

3. **`test_active_filter_counts_match_input`** (lines 116-125) — drop `"status": ["A", "B"]` from the input filters dict; the expected dict shrinks to 5 keys. Use `customer: ["A", "B"]` instead so the test still has a multi-value entry. Pin:
   ```python
   filters={"customer": ["A", "B"], "ap_company": ["X"]},
   ...
   assert vm.active_filter_counts == {
       "customer": 2, "ap_company": 1,
       "device": 0, "controller": 0, "application": 0,
   }
   ```

4. **`test_invalid_sort_col_falls_back_to_default`** (lines 128-131) — UPDATE: change the invalid sort_col probe from `"link"` to one of the now-removed columns, e.g. `sort_col="status"`. This pins the contract that `status` (and `assignee`, `end`) are no longer sortable: the validator falls back to `DEFAULT_SORT_COL`. Add two more assertions in the same test for `assignee` and `end`:
   ```python
   for removed in ("status", "assignee", "end", "link"):
       vm = build_joint_validation_grid_view_model(tmp_path, sort_col=removed)
       assert vm.sort_col == DEFAULT_SORT_COL, removed
   ```

5. **`test_view_model_shape`** (lines 51-57) — already uses `set(vm.filter_options.keys()) == set(FILTERABLE_COLUMNS)`. No change needed (FILTERABLE_COLUMNS is now 5-tuple, the test follows automatically).

6. **`test_empty_jv_root_returns_zero_rows`** (lines 134-138) — already uses `{c: [] for c in FILTERABLE_COLUMNS}`. No change needed.

7. **The `_write_jv` helper** (lines 28-48): unchanged — it still writes Status/End rows into the source HTML so the parser path stays exercised end-to-end. The test pins the parser still extracts these fields even though the listing doesn't display them.

---

Edit `tests/v2/test_joint_validation_routes.py`:

1. **`test_get_overview_with_filters_round_trip_url`** (lines 132-140) — change the params and assertion:
   - Change `("status", "In Progress")` → `("customer", "Samsung")` in `params=[…]`
   - Change `assert "status: 1" in r.text or "badge" in r.text` → `assert 'data-facet="customer"' in r.text or "Samsung" in r.text` (allow either the chip wrapper marker or the chip text — analogous to the prior either/or assertion).

2. **`test_empty_jv_root_renders_empty_state`** (line 264) — change `assert 'colspan="13"' in r.text` → `assert 'colspan="10"' in r.text`.

3. **`test_overview_filter_chips_render_actual_values`** (lines 361-386) — UPDATE:
   - Replace the `("status", "In Progress")` and `("status", "Verified")` params with multi-value `customer`: e.g. `("customer", "Samsung")`, `("customer", "LG")`. Drop the second-facet customer probe to keep multi-value for facet 1; alternatively use `("customer", "Samsung")`, `("customer", "LG")` for facet 1 and `("ap_company", "Qualcomm")` for facet 2.
   - Update the chip-variant assertions: customer chips are now `c-1` (was `c-2`); the second facet picks up `c-2`. So:
     ```python
     assert 'data-facet="customer"' in r.text
     assert 'class="ff-chip c-1">Samsung</span>' in r.text
     assert 'class="ff-chip c-1">LG</span>' in r.text
     assert 'data-facet="ap_company"' in r.text
     assert 'class="ff-chip c-2">Qualcomm</span>' in r.text
     ```
   - The "inactive facets DO NOT render rows" assertion line (`assert 'data-facet="ap_company"' not in r.text`) needs to change. Pick a still-inactive facet for the negative assertion, e.g. `assert 'data-facet="device"' not in r.text`.

4. **`_write_many_jv_status_values`** helper (lines 338-358) — RENAME to `_write_many_jv_customer_values` and write `<Customer>` rows instead of `<Status>` rows. Used only by `test_overview_filter_chips_overflow_shows_plus_n_more`.

5. **`test_overview_filter_chips_overflow_shows_plus_n_more`** (lines 389-411) — UPDATE accordingly:
   - Call the renamed helper.
   - Use `("customer", s)` not `("status", s)` for the 11 params.
   - Change the chip-class probe from `'class="ff-chip c-1">'` to `'class="ff-chip c-1">'` — actually, this stays `c-1` since customer's new variant IS `c-1`. Update the helper call name only; the variant assertion stays `c-1` accidentally. **Confirm explicitly**: customer = c-1 in the new map, so `r.text.count('class="ff-chip c-1">') == 10` is still the right assertion (now it counts customer chips, not status chips).

---

Edit `tests/v2/test_overview_presets.py`:

1. **`test_load_presets_returns_three_seed_entries`** (lines 69-83) — UPDATE to match the new YAML:
   - Keep the 3-entries / 3-names assertion intact (slugs unchanged).
   - DROP `assert korean["filters"]["status"] == ["In Progress"]`.
   - KEEP `assert korean["filters"]["customer"] == ["Samsung", "Hyundai"]`.
   - The `qc` (qualcomm-wearables) assertions are unchanged.
   - Optionally add a `pending = next(...); assert pending["filters"]["device"] == ["UFS 4.0"]` to pin the surviving filter on the third preset.

2. **`test_load_presets_skips_malformed_entries`** (lines 86-132) — UPDATE the malformed-entries YAML literal: every place it uses `status: …` to drive a malformed-entry case, swap to a still-valid facet name like `customer:`. Specifically:
   - The valid `ok-preset` block: `status: ["Pending"]` → `customer: ["Pending"]`
   - The `missing-label` block: same swap.
   - The `missing-name` block: same swap.
   - The `non-list-value` block: `status: "Pending"` → `customer: "Pending"`
   - The `empty-facet` block: `status: []` → `customer: []`
   - The post-load assertion: `assert presets[0]["filters"] == {"status": ["Pending"]}` → `assert presets[0]["filters"] == {"customer": ["Pending"]}`

3. **`test_get_overview_preset_overrides_filters_and_returns_oob_blocks`** (lines 197-222) — UPDATE the chip-variant assertions for the new palette (qualcomm-wearables uses ap_company + application; under the new map ap_company=c-2, application=c-5):
   - `'class="ff-chip c-3">Qualcomm</span>'` → `'class="ff-chip c-2">Qualcomm</span>'`
   - `'class="ff-chip c-6">Wearable</span>'` → `'class="ff-chip c-5">Wearable</span>'`
   - The `assert 'data-facet="status"' not in r.text` line — KEEP. Status no longer renders, so this assertion gets stronger (now true regardless of preset content).
   - The `assert "status=" not in push` line — KEEP. The URL builder no longer emits `status=`.

4. **`test_get_overview_preset_clicked_after_existing_filters_overrides_them`** (lines 232-253) — UPDATE:
   - The stray-params probe `params=[("status", "Cancelled"), ("customer", "Apple")]` — change `("status", "Cancelled")` → `("device", "X1")` (or another arbitrary still-valid facet). The intent was to send stray params and prove they get ignored; after the changes, sending `status=` no longer gets ignored — it gets rejected by FastAPI as an unknown query param (no, wait — extra query params in FastAPI are silently ignored at the route layer, the route just doesn't see them). Either way, swap to a still-recognized facet so the test demonstrates "preset OVERRIDES even live-recognized stray params."

5. After all source + test edits, run the full v2 suite to confirm green. Iterate on any test breakage with rule-1 auto-fixes (no `--no-verify`).

---

**Run the full suite as the verification:** `cd /home/yh/Desktop/02_Projects/Proj28_PBM2 && pytest tests/v2/ -x --tb=short -q 2>&1 | tail -40`

Expected delta: net test count likely shifts by ~−1 (one deleted test from grid_service: `test_filter_status_in_progress_excludes_others`). Renamed tests don't change the count. All other tests should pass.
  </action>
  <verify>
    <automated>cd /home/yh/Desktop/02_Projects/Proj28_PBM2 &amp;&amp; pytest tests/v2/ --tb=short -q 2>&amp;1 | tail -20</automated>
  </verify>
  <done>
    Full `pytest tests/v2/` runs green (no failures). The 4 known-skip count from the prior baseline is unchanged or shifts by ±1. The Joint Validation invariant test `test_jv_parser_korean_label_byte_equal` still passes (parser source untouched). The detail-page test `test_get_jv_detail_renders_properties_and_iframe` still passes (detail template untouched, still asserts `"담당자" in r.text`). Browse and Ask regression-smoke test (`test_browse_and_ask_tabs_unaffected`) still passes.
  </done>
</task>

</tasks>

<verification>
End-to-end smoke (run after the 3 tasks complete):

1. Source-level invariants:
   ```bash
   # Listing template — 9 sortable columns + 1 Actions = 10 total
   grep -c 'sortable_th(' app_v2/templates/overview/_grid.html  # → 9
   grep -c 'colspan="10"' app_v2/templates/overview/_grid.html  # → 1
   grep -c 'colspan="13"' app_v2/templates/overview/_grid.html  # → 0

   # Filter bar — 5 picker_popovers, no Status
   grep -c 'picker_popover(' app_v2/templates/overview/_filter_bar.html  # → 5
   grep -c 'name="status"' app_v2/templates/overview/_filter_bar.html  # → 0

   # Filter badges OOB block — 5-facet for-loop
   grep -c '"status".*"Status"' app_v2/templates/overview/index.html  # → 0

   # Service module
   python -c "from app_v2.services.joint_validation_grid_service import FILTERABLE_COLUMNS, SORTABLE_COLUMNS, DATE_COLUMNS; print(len(FILTERABLE_COLUMNS), len(SORTABLE_COLUMNS), DATE_COLUMNS)"
   # → 5 9 ('start',)

   # Router — no `status` parameter in any signature
   grep -nE '^\s+status:\s' app_v2/routers/overview.py  # → empty
   ```

2. Functional smoke (TestClient through pytest):
   - `pytest tests/v2/test_joint_validation_routes.py -x` — all green
   - `pytest tests/v2/test_joint_validation_grid_service.py -x` — all green
   - `pytest tests/v2/test_overview_presets.py -x` — all green
   - `pytest tests/v2/ -q` — full suite green (single test deletion + several rewrites; net delta ≈ 0)

3. Parser invariant preserved (D-JV-04):
   ```bash
   grep -c '담당자' app_v2/services/joint_validation_parser.py  # → 1+ (parser still matches)
   ```

4. Detail-page parity (must stay intact):
   ```bash
   grep -c '담당자\|jv.assignee' app_v2/templates/joint_validation/detail.html  # → 2+
   grep -c 'jv.status\|jv.end' app_v2/templates/joint_validation/detail.html  # → 2+
   ```
</verification>

<success_criteria>
1. GET /overview renders the JV listing with 9 metadata columns + Actions (no Status, no 담당자, no End headers or cells).
2. The filter bar above the grid renders 5 picker popovers (Customer, AP Company, Device, Controller, Application) — no Status picker.
3. The active-filter chip summary block iterates 5 facets and uses color variants `c-1..c-5`.
4. POST /overview/grid still returns 200 with the 4 OOB blocks (`grid`, `count_oob`, `filter_badges_oob`, `pagination_oob`); `HX-Push-Url` header no longer emits `status=`.
5. `config/presets.example.yaml` has 3 surviving presets, none referencing `status`. `load_presets()` returns 3 entries.
6. GET /overview/preset/qualcomm-wearables, /overview/preset/korean-oems-in-progress, /overview/preset/pending-ufs4 all return 200.
7. `pytest tests/v2/` is green.
8. `app_v2/services/joint_validation_parser.py` still matches `담당자` byte-equal (D-JV-04 invariant unbroken).
9. `app_v2/templates/joint_validation/detail.html` still renders Status / 담당자 / End rows on the JV detail page (the user only asked to drop them from the listing).
</success_criteria>

<output>
After all 3 tasks complete and the full v2 suite is green, create:
`.planning/quick/260507-rmj-in-browse-page-ditch-status-and-end-colu/260507-rmj-SUMMARY.md`

Per CLAUDE.md / GSD discipline, commit once with message:
```
docs(quick-260507-rmj): ditch Status, 담당자, End columns + Status filter from JV listing & presets

- _grid.html: 12 → 9 sortable columns; empty-state colspan 13 → 10
- _filter_bar.html: 6 → 5 picker_popovers (drop Status)
- index.html filter_badges_oob: 6-facet for-loop → 5; chip palette c-1..c-5
- joint_validation_grid_service.py: FILTERABLE_COLUMNS 6 → 5; SORTABLE_COLUMNS 12 → 9; DATE_COLUMNS ('start', 'end') → ('start',). ALL_METADATA_KEYS unchanged (parser surface preserved). JointValidationRow unchanged (detail page still uses the 3 fields).
- overview.py: drop status param from _parse_filter_dict / _build_overview_url / get_overview / post_overview_grid / get_overview_preset.
- presets.example.yaml: korean-oems-in-progress drops status (keeps customer); pending-ufs4 drops status (keeps device); qualcomm-wearables unchanged.
- tests: rewrite/delete status-flavored cases in test_joint_validation_grid_service.py / test_joint_validation_routes.py / test_overview_presets.py; update colspan + chip-variant assertions; full v2 suite green.

Disambiguation: user said "Browse" but meant the Joint Validation listing (active_tab="overview", route /overview). The actual /browse pivot grid has no Status/담당자/End and was untouched; config/browse_presets.example.yaml (the platforms+params Browse preset file) was also untouched (no status field there).

Invariants preserved: D-JV-04 (parser still matches '담당자' byte-equal); JV detail page unchanged.
```
</output>
