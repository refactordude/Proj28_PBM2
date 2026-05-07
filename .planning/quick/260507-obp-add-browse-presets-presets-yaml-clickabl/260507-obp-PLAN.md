---
task: 260507-obp
type: quick
description: Add named filter presets to the Overview (Joint Validation) page — config/presets.yaml + clickable chips above the active-filter summary that OVERRIDE current filter selection via HTMX OOB swap
files_modified:
  - config/presets.example.yaml          # NEW — committed seed
  - .gitignore                            # add config/presets.yaml line
  - app_v2/services/preset_store.py       # NEW — YAML loader
  - app_v2/routers/overview.py            # add GET /overview/preset/{name}
  - app_v2/templates/overview/index.html  # add preset_chips_oob block + render strip above filter_badges_oob
  - app_v2/static/css/app.css             # append .ff-preset-* rules
  - tests/v2/test_overview_presets.py     # NEW — loader + render + click-apply + malformed-skip
must_haves:
  truths:
    - "config/presets.example.yaml exists with 2-3 seed presets using REAL JV filter values from the live content/joint_validation/ tree (status, customer, ap_company, device, controller, application — at least one preset spans 2+ facets)"
    - "Loader reads config/presets.yaml first (gitignored, user-local), then config/presets.example.yaml (committed), then [] — same fallback chain shape as starter_prompts.py"
    - "Loader silently skips malformed entries (missing name, unknown facet keys, non-list facet values, non-dict entries) and returns valid entries only — never raises"
    - "Preset chip strip renders above the existing #overview-filter-badges block on GET /overview"
    - "Each preset chip is clickable; clicking issues an HTMX request to GET /overview/preset/{name} which OVERRIDES (clears + replaces) the current filter selection"
    - "GET /overview/preset/{name} returns the four OOB blocks (grid + count_oob + filter_badges_oob + pagination_oob) so the grid AND active-filter chips refresh together via merge-by-id"
    - "GET /overview/preset/{name} sets HX-Push-Url to canonical /overview?<facet>=A&<facet>=B&... so the URL bar reflects the applied state and is bookmarkable"
    - "Unknown preset name returns 404; the page does not 500"
    - "Preset chip styling reuses .ff-* family (single neutral chip color — distinct from per-facet .c-1..c-6 palette) and is anchored to Dashboard_v2.html tiny-chip language"
    - "#overview-filter-badges OOB target id remains byte-stable; existing tests test_post_overview_grid_returns_oob_blocks + test_overview_filter_chips_* still pass unchanged"
    - "Empty config/presets.yaml or missing file → strip is omitted entirely (no empty container) — graceful degradation"
  artifacts:
    - path: "config/presets.example.yaml"
      provides: "2-3 seed presets using verified live values from content/joint_validation/ — committed template"
      contains: "name:"
    - path: "app_v2/services/preset_store.py"
      provides: "load_presets() → list[dict] with malformed-entry skip; FILTER_FACETS whitelist re-imported from joint_validation_grid_service.FILTERABLE_COLUMNS"
      exports: ["load_presets", "Preset"]
    - path: "app_v2/routers/overview.py"
      provides: "New GET /overview/preset/{name} route; load_presets() call in get_overview/post_overview_grid contexts so the strip renders"
      contains: "/overview/preset/"
    - path: "app_v2/templates/overview/index.html"
      provides: "New preset chip strip rendered above filter_badges_oob; preset_chips_oob block (currently OOB-emitted alongside the existing 4 blocks IS NOT required for this task — strip is static for now since presets don't change between requests)"
      contains: "ff-preset"
    - path: "app_v2/static/css/app.css"
      provides: "Append .ff-preset-row + .ff-preset-chip rules anchored to Dashboard_v2 tiny-chip language; single neutral hue distinct from .c-1..c-6"
      contains: ".ff-preset-chip"
    - path: "tests/v2/test_overview_presets.py"
      provides: "4 tests: loader-happy-path, loader-skips-malformed, GET /overview renders chips, GET /overview/preset/{name} OVERRIDES filters and returns 4 OOB blocks"
  key_links:
    - from: "app_v2/templates/overview/index.html"
      to: "app_v2/routers/overview.py preset list in ctx"
      via: "ctx['presets'] from load_presets() call"
      pattern: "presets"
    - from: "app_v2/templates/overview/index.html (preset chip)"
      to: "GET /overview/preset/{name}"
      via: "hx-get on each chip + hx-target=#overview-grid + hx-push-url=true"
      pattern: "/overview/preset/"
    - from: "app_v2/routers/overview.py GET /overview/preset/{name}"
      to: "build_joint_validation_grid_view_model"
      via: "_parse_filter_dict(**preset['filters']) → vm; reuse same TemplateResponse(block_names=[...]) pattern as POST /overview/grid"
      pattern: "block_names"
    - from: "app_v2/services/preset_store.py"
      to: "FILTERABLE_COLUMNS"
      via: "import for facet-key whitelist (rejects unknown keys at load time)"
      pattern: "FILTERABLE_COLUMNS"
---

<objective>
Add named filter presets to the Overview (Joint Validation) page. Define
presets in `config/presets.yaml` (with `config/presets.example.yaml` as the
committed seed). Render them as clickable chips ABOVE the existing
active-filter summary (#overview-filter-badges, shipped in 260507-nzp).
Clicking a chip OVERRIDES the current filter selection — the existing
filters are cleared and replaced by the preset's values, then the grid +
active-filter chips re-render together via the existing OOB swap mechanism.

Currently the user has to open each picker popover (Status / Customer /
AP Company / etc.) and tick boxes to compose a multi-facet filter. Common
combinations like "Korean OEMs in progress" or "Qualcomm wearables" need
clicking through 2-3 popovers every time.

Output: A small horizontal strip above the active-filter summary:

    [ Korean OEMs in progress ]  [ Qualcomm wearables ]  [ Pending UFS 4.0 ]

    Status:    [ In Progress ]
    Customer:  [ Samsung ]

clicking a preset chip sends GET /overview/preset/<name> via HTMX, the
server constructs the grid view-model from the preset's filter dict, and
returns the four existing OOB blocks (grid, count_oob, filter_badges_oob,
pagination_oob) plus an HX-Push-Url header carrying the canonical
/overview?status=...&customer=... URL.

Purpose:
- One-click access to common filter combinations.
- Curated, project-specific (the YAML lives next to settings.yaml so the
  team can edit their own preset bank without touching code).
- Bookmarkable: the HX-Push-Url puts the resolved query string in the
  address bar; sharing a URL still works.
- OVERRIDE semantics (NOT additive): clicking a preset gives a deterministic
  end state regardless of what was previously selected. Avoids the "did
  this preset add to my filters or replace them?" ambiguity.
</objective>

<context>
@.planning/STATE.md
@CLAUDE.md

@.planning/quick/260507-nzp-replace-filter-facet-count-badges-with-c/260507-nzp-PLAN.md
@.planning/quick/260507-nzp-replace-filter-facet-count-badges-with-c/260507-nzp-SUMMARY.md

@app_v2/templates/overview/index.html
@app_v2/templates/overview/_filter_bar.html
@app_v2/routers/overview.py
@app_v2/services/joint_validation_grid_service.py
@app_v2/services/joint_validation_store.py
@app_v2/services/starter_prompts.py
@app_v2/static/css/app.css
@tests/v2/test_joint_validation_routes.py
@config/settings.yaml
@config/starter_prompts.example.yaml

<sample_query_used_to_seed_the_yaml>
The plan ran the existing service against the live JV tree to get the
authoritative filter-options union. This is the same code path GET /overview
uses to build the picker popovers (so the seed values ARE valid filter
options that will produce non-empty result sets):

```python
# Run during planning, on host machine (cwd = project root):
from app_v2.services.joint_validation_grid_service import build_joint_validation_grid_view_model
from app_v2.services.joint_validation_store import JV_ROOT
vm = build_joint_validation_grid_view_model(JV_ROOT)
print('TOTAL_ROWS:', vm.total_count)
for k, v in vm.filter_options.items():
    print(f'  {k}: {v}')
```

Output captured 2026-05-07 against the working tree (22 JV rows total):

| Facet         | Live values (sampled verbatim from filter_options)                                                                                                                                                                                              |
|---------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| status        | Blocked, Cancelled, Completed, In Progress, On Hold, Pending, Planned                                                                                                                                                                          |
| customer      | Apple, Garmin, Google, Honor, Huawei, Hyundai, Nothing, OnePlus, OPPO, Realtek, Samsung, Sony, Tesla, Vivo, Xiaomi                                                                                                                              |
| ap_company    | Apple, Custom, Google, HiSilicon, MediaTek, NXP, Qualcomm, Realtek                                                                                                                                                                              |
| device        | UFS 2.2, UFS 3.1, UFS 4.0                                                                                                                                                                                                                       |
| controller    | FW v1.4.0..v3.2.0-rc2 (19 distinct firmware strings — too granular for presets)                                                                                                                                                                |
| application   | Auto, Automotive, IoT, Smartphone, Tablet, Wearable                                                                                                                                                                                            |

The 3 seed presets below are picked from the table above so they will
produce non-empty grids on `tmp_path` test fixtures AND on the real
content/joint_validation/ tree. The executor MUST NOT change these values
without re-running the sampling query — random made-up values like
"Acme Inc." would cause the new tests to fail because no JV row has
customer=Acme Inc..
</sample_query_used_to_seed_the_yaml>

<seed_presets_to_use_verbatim>
The plan freezes these exact 3 presets. The executor pastes the YAML
below into `config/presets.example.yaml` byte-for-byte; the test file
asserts these names, labels, and values literally.

```yaml
# config/presets.example.yaml
# Phase 2 — Filter presets for the Overview (Joint Validation) page (260507-obp).
# Edit this file (or copy to config/presets.yaml) to customize.
# Each entry:
#   name:    machine id used in /overview/preset/<name> (slug, [a-z0-9_-])
#   label:   chip text shown to the user (<= 40 chars recommended)
#   filters: dict keyed by FILTERABLE_COLUMNS (status, customer, ap_company,
#            device, controller, application). Each value is a list of
#            strings — UNION within a facet, INTERSECTION across facets,
#            same semantics as the picker popovers.
# Unknown facet keys, non-list values, or missing name/label cause the
# entry to be silently skipped at load time.

- name: korean-oems-in-progress
  label: "Korean OEMs in progress"
  filters:
    status: ["In Progress"]
    customer: ["Samsung", "Hyundai"]

- name: qualcomm-wearables
  label: "Qualcomm wearables"
  filters:
    ap_company: ["Qualcomm"]
    application: ["Wearable"]

- name: pending-ufs4
  label: "Pending UFS 4.0"
  filters:
    status: ["Pending"]
    device: ["UFS 4.0"]
```

Why these three:
- Korean OEMs in progress — multi-customer + status; exercises 3 list values
  across 2 facets (proves UNION-within-facet semantics).
- Qualcomm wearables — single-value-per-facet across 2 facets; the simplest
  multi-facet AND case.
- Pending UFS 4.0 — pairs a status with a device facet; exercises a third
  facet (device) so all 6 facets aren't just status/customer/ap_company.

Why these names (slugs):
- Lowercase + hyphen-only — URL-safe with no encoding needed, no slashes
  (so the `/overview/preset/{name}` path stays single-segment), and no
  collisions with FILTERABLE_COLUMNS values (which include spaces and
  capitals).
</seed_presets_to_use_verbatim>

<interfaces>
<!-- Existing types and helpers the executor needs. Embedded so no codebase
     exploration is required. -->

From app_v2/services/joint_validation_grid_service.py:
```python
FILTERABLE_COLUMNS: Final[tuple[str, ...]] = (
    "status", "customer", "ap_company", "device", "controller", "application",
)

class JointValidationGridViewModel(BaseModel):
    rows: list[JointValidationRow]
    filter_options: dict[str, list[str]]
    active_filter_counts: dict[str, int]
    sort_col: str
    sort_order: Literal["asc", "desc"]
    total_count: int
    page: int
    page_count: int
    page_links: list[PageLink]
    prev_group_page: int | None
    next_group_page: int | None
```

From app_v2/routers/overview.py (existing helpers — REUSE, do not fork):
```python
def _parse_filter_dict(
    status: list[str], customer: list[str], ap_company: list[str],
    device: list[str], controller: list[str], application: list[str],
) -> dict[str, list[str]]:
    return {"status": status, "customer": customer, "ap_company": ap_company,
            "device": device, "controller": controller, "application": application}

def _build_overview_url(
    filters: dict[str, list[str]],
    sort_col: str, sort_order: str, page: int = 1,
) -> str:
    """Returns canonical /overview?status=A&status=B&...&sort=...&order=... URL.
    Repeated keys for multi-value (?status=A&status=B). page only when > 1."""

# Both GET /overview and POST /overview/grid build the SAME context:
ctx = {
    "vm": vm,
    "selected_filters": filters,
    "active_tab": "overview",
    "active_filter_counts": vm.active_filter_counts,
    "all_platform_ids": [],
    "conf_url": conf_url,
}

# POST /overview/grid renders 4 OOB blocks:
response = templates.TemplateResponse(
    request, "overview/index.html", ctx,
    block_names=["grid", "count_oob", "filter_badges_oob", "pagination_oob"],
)
response.headers["HX-Push-Url"] = _build_overview_url(
    filters, vm.sort_col, vm.sort_order, vm.page
)
```

From app_v2/services/starter_prompts.py — pattern to mirror for preset_store.py:
```python
import yaml
from pathlib import Path

def load_starter_prompts() -> list[dict]:
    for filename in ("config/starter_prompts.yaml", "config/starter_prompts.example.yaml"):
        path = Path(filename)
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or []
                if isinstance(data, list):
                    return [
                        e for e in data
                        if isinstance(e, dict) and "label" in e and "question" in e
                    ]
            except yaml.YAMLError:
                return []
    return []
```

From app_v2/static/css/app.css (existing .ff-* family from 260507-nzp,
which the new preset chip rules will SIBLING — not extend):
```css
.ff-row { display: flex; align-items: center; flex-wrap: wrap;
          gap: 6px; margin-bottom: 4px; }
.ff-label { font-size: 12px; font-weight: 600; color: var(--ink-2); ... }
.ff-chip { display: inline-flex; padding: 3px 9px;
           border-radius: var(--radius-pill); font-size: 11px; font-weight: 600; ... }
.ff-chip.c-1..c-6 { /* per-facet color slots — DO NOT REUSE for presets */ }
.ff-more { background: transparent; color: var(--mute); ... }
```

From tests/v2/test_joint_validation_routes.py (fixture pattern to mirror):
```python
@pytest.fixture
def jv_dir_with_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "3193868109"
    folder.mkdir()
    (folder / "index.html").write_bytes(SAMPLE_HTML)
    monkeypatch.setattr("app_v2.services.joint_validation_store.JV_ROOT", tmp_path)
    monkeypatch.setattr("app_v2.routers.overview.JV_ROOT", tmp_path)
    monkeypatch.setattr("app_v2.routers.joint_validation.JV_ROOT", tmp_path)
    return tmp_path
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Add config/presets.example.yaml seed + .gitignore + preset_store.py loader</name>
  <files>config/presets.example.yaml, .gitignore, app_v2/services/preset_store.py</files>
  <action>
Three sub-steps; commit as ONE feat commit at the end of the task.

### 1a. Write `config/presets.example.yaml`

Paste the YAML byte-for-byte from <seed_presets_to_use_verbatim> above.
Do NOT alter the values — Task 4's tests assert the exact string
"Korean OEMs in progress", the slug "korean-oems-in-progress", the
customer pair ["Samsung", "Hyundai"], and so on. Changing any of these
without also updating the test will produce a red suite.

### 1b. Add `config/presets.yaml` to `.gitignore`

Open `.gitignore` and add a single new line under the existing
`config/settings.yaml` entry (or wherever user-local config files are
listed — grep for `config/settings.yaml` to find the section):

```
config/presets.yaml
```

Mirrors the convention already established for `config/settings.yaml`
and `config/starter_prompts.yaml` — only the `.example.yaml` files
are committed; the live ones are user-local. (If `config/settings.yaml`
is NOT actually in `.gitignore`, add this line at the bottom of the file
under a `# Local config (not committed)` comment.)

### 1c. Create `app_v2/services/preset_store.py`

```python
"""Filter-preset loader for the Overview (Joint Validation) page (260507-obp).

Mirrors ``app_v2/services/starter_prompts.py`` deliberately — same fallback
chain shape (config/presets.yaml → config/presets.example.yaml → []), same
yaml.safe_load discipline (T-05-02-01: never use full Loader on user files).

Each returned entry has ``name`` (slug str), ``label`` (display str), and
``filters`` (dict[str, list[str]] keyed by a subset of FILTERABLE_COLUMNS).
Malformed entries are silently dropped — this never raises.

"Malformed" means ANY of:
  - top-level YAML is not a list → return []
  - entry is not a dict → drop
  - missing ``name`` or ``label`` (or non-string) → drop
  - ``filters`` missing or not a dict → drop
  - ANY filters key is not in FILTERABLE_COLUMNS → drop the entry entirely
    (NOT just the bad key — keep semantics simple: a typoed facet key in a
     preset means the whole preset is broken)
  - ANY filters value is not a list of strings → drop entry
  - empty values list for a facet → drop entry (defeats the point of a
    preset; an empty preset would clear all filters which the existing
    "Clear all" link already does)

Caching: not added. Same rationale as starter_prompts.py — called only on
GET /overview (page render) + GET /overview/preset/<name> (rare); YAML
file is < 4 KB; lru_cache would prevent live edits without restart.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TypedDict

import yaml

from app_v2.services.joint_validation_grid_service import FILTERABLE_COLUMNS

log = logging.getLogger(__name__)


class Preset(TypedDict):
    """Validated preset entry. Plain TypedDict (not Pydantic) — load_presets
    does the validation in plain Python so a malformed entry can be skipped
    without raising; Pydantic would force us into try/except per-entry."""
    name: str
    label: str
    filters: dict[str, list[str]]


def _coerce_entry(raw: object) -> Preset | None:
    """Return a validated Preset or None if anything is malformed.

    Logs the rejection reason at WARNING so users can debug a preset that
    "isn't showing up". Logging never aborts; loader always returns the
    valid subset.
    """
    if not isinstance(raw, dict):
        log.warning("preset rejected: not a mapping (got %s)", type(raw).__name__)
        return None
    name = raw.get("name")
    label = raw.get("label")
    filters = raw.get("filters")
    if not isinstance(name, str) or not name.strip():
        log.warning("preset rejected: missing or non-string 'name'")
        return None
    if not isinstance(label, str) or not label.strip():
        log.warning("preset rejected (%s): missing or non-string 'label'", name)
        return None
    if not isinstance(filters, dict):
        log.warning("preset rejected (%s): 'filters' is missing or not a mapping", name)
        return None
    cleaned: dict[str, list[str]] = {}
    for key, vals in filters.items():
        if key not in FILTERABLE_COLUMNS:
            log.warning(
                "preset rejected (%s): unknown facet '%s' — must be one of %s",
                name, key, FILTERABLE_COLUMNS,
            )
            return None
        if not isinstance(vals, list) or not vals:
            log.warning(
                "preset rejected (%s): facet '%s' must be a non-empty list",
                name, key,
            )
            return None
        if not all(isinstance(v, str) and v for v in vals):
            log.warning(
                "preset rejected (%s): facet '%s' values must be non-empty strings",
                name, key,
            )
            return None
        cleaned[key] = list(vals)
    if not cleaned:
        log.warning("preset rejected (%s): no valid facets", name)
        return None
    return Preset(name=name, label=label, filters=cleaned)


def load_presets() -> list[Preset]:
    """Load + validate presets from the YAML fallback chain.

    Returns:
        list of Preset dicts in YAML file order. Empty list on:
          - file not found in either location,
          - YAML parse error,
          - top-level not a list,
          - all entries malformed.
    """
    for filename in ("config/presets.yaml", "config/presets.example.yaml"):
        path = Path(filename)
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or []
            except yaml.YAMLError as exc:
                log.warning("preset YAML parse error in %s: %s", filename, exc)
                return []
            if not isinstance(data, list):
                log.warning("preset YAML in %s is not a list", filename)
                return []
            return [p for p in (_coerce_entry(e) for e in data) if p is not None]
    return []
```

Constraints:
- DO NOT add `pyyaml` to requirements — already present (transitively via
  the project's existing `yaml.safe_load` callers; verified at planning
  time via `import yaml` in the runtime venv).
- DO NOT add a `Pydantic` model — TypedDict is enough; the explicit
  Python validation gives us per-entry "log and skip" semantics that
  Pydantic would force into try/except.
- DO NOT cache — same rationale as starter_prompts.py.
- DO NOT export anything beyond `load_presets` and `Preset`.
  </action>
  <verify>
    <automated>
test -f config/presets.example.yaml && \
grep -q "korean-oems-in-progress" config/presets.example.yaml && \
grep -q "qualcomm-wearables" config/presets.example.yaml && \
grep -q "pending-ufs4" config/presets.example.yaml && \
grep -q "^config/presets.yaml$" .gitignore && \
test -f app_v2/services/preset_store.py && \
.venv/bin/python -c "from app_v2.services.preset_store import load_presets; ps = load_presets(); assert len(ps) == 3, ps; assert ps[0]['name'] == 'korean-oems-in-progress'; assert ps[0]['filters']['customer'] == ['Samsung', 'Hyundai']; print('OK', len(ps))"
    </automated>
  </verify>
  <done>
- config/presets.example.yaml exists with the 3 seed presets verbatim.
- config/presets.yaml is in .gitignore (so user-local edits don't leak).
- app_v2/services/preset_store.py exports load_presets() and Preset.
- load_presets() returns 3 entries when run from the project root.
- Malformed entries are skipped silently (proven by Task 4 tests).
  </done>
</task>

<task type="auto">
  <name>Task 2: Add GET /overview/preset/{name} route + thread presets into existing GET/POST contexts</name>
  <files>app_v2/routers/overview.py</files>
  <action>
Two edits in `app_v2/routers/overview.py`:

### 2a. Thread `presets` into existing GET /overview and POST /overview/grid contexts

In BOTH `get_overview` (line ~106) and `post_overview_grid` (line ~173)
handlers, add `"presets": load_presets()` to the `ctx` dict (alongside
`vm`, `selected_filters`, etc.). Add the import at the top of the file:

```python
from app_v2.services.preset_store import load_presets
```

Both handlers' `ctx` becomes:

```python
ctx = {
    "vm": vm,
    "selected_filters": filters,
    "active_tab": "overview",
    "active_filter_counts": vm.active_filter_counts,
    "all_platform_ids": [],
    "conf_url": conf_url,
    "presets": load_presets(),   # 260507-obp — preset chip strip
}
```

Why thread presets into POST /overview/grid too: the existing
`block_names` list rendered by POST /overview/grid does NOT include the
preset strip block — the strip is part of the always-on full-page render
above filter_badges_oob, NOT an OOB block — so on filter-change OOB
swaps the strip stays put (it lives outside the swap targets). However,
when the executor adds a preset_chips_oob block in Task 3, having
`presets` available on the POST context will be needed; threading it
into both contexts NOW means Task 3 doesn't need to touch the router
again.

### 2b. Add new GET /overview/preset/{name} route

Insert AFTER `post_overview_grid` (around line 240, before the `__all__`
declaration). Mirrors POST /overview/grid line-by-line for the OOB
swap + HX-Push-Url discipline:

```python
@router.get("/overview/preset/{name}", response_class=HTMLResponse)
def get_overview_preset(request: Request, name: str):
    """Apply a named preset — OVERRIDES current filters (clears + replaces).

    Looks up the preset by ``name`` in load_presets(); 404 if not found.
    Builds the JV grid view-model from the preset's filter dict (other
    facets default to empty lists), and returns the same four OOB blocks
    as POST /overview/grid plus an HX-Push-Url header carrying the
    canonical /overview?<facet>=... URL.

    OVERRIDE semantics (260507-obp design decision): we deliberately do
    NOT merge the preset on top of existing filters from the request. The
    preset is the entire filter state the user wants. Any facets the
    preset doesn't mention default to empty (= "any value matches")
    rather than carrying over from the previous request. This keeps the
    end state deterministic from the chip click alone.

    HTMX call site (overview/index.html):
        <a hx-get="/overview/preset/<name>"
           hx-target="#overview-grid"
           hx-swap="outerHTML"
           hx-push-url="true">…</a>

    The handler uses GET (not POST) because:
      1. It's idempotent — repeated clicks land on the same state.
      2. hx-push-url with GET produces a clean shareable URL in the bar.
      3. Tests can hit it with TestClient.get().
    """
    presets = load_presets()
    preset = next((p for p in presets if p["name"] == name), None)
    if preset is None:
        return HTMLResponse(status_code=404, content=f"preset '{name}' not found")

    # Build the canonical filter dict — preset values for any mentioned
    # facets, [] for the others. Reuses _parse_filter_dict for shape parity
    # with the GET / POST handlers (so the resulting `selected_filters`
    # dict in ctx is byte-equal in shape — same 6 keys always present).
    pf = preset["filters"]
    filters = _parse_filter_dict(
        status=pf.get("status", []),
        customer=pf.get("customer", []),
        ap_company=pf.get("ap_company", []),
        device=pf.get("device", []),
        controller=pf.get("controller", []),
        application=pf.get("application", []),
    )

    vm: JointValidationGridViewModel = build_joint_validation_grid_view_model(
        JV_ROOT,
        filters=filters,
        sort_col=None,    # use service defaults — preset doesn't carry sort
        sort_order=None,
        page=1,           # always reset to page 1 on preset apply
    )

    settings_obj = getattr(request.app.state, "settings", None)
    conf_url = (settings_obj.app.conf_url.rstrip("/") if settings_obj else "")

    ctx = {
        "vm": vm,
        "selected_filters": filters,
        "active_tab": "overview",
        "active_filter_counts": vm.active_filter_counts,
        "all_platform_ids": [],
        "conf_url": conf_url,
        "presets": presets,
    }
    response = templates.TemplateResponse(
        request,
        "overview/index.html",
        ctx,
        block_names=["grid", "count_oob", "filter_badges_oob", "pagination_oob"],
    )
    response.headers["HX-Push-Url"] = _build_overview_url(
        filters, vm.sort_col, vm.sort_order, vm.page
    )
    return response
```

Why GET (not POST):
- Preset apply is idempotent (calling it twice yields the same end state).
- HTMX `hx-push-url="true"` with a GET request leaves a clean shareable
  URL in the bar. With POST + HX-Push-Url-derived URL, the URL is
  shareable but the click semantics suggest a side effect that doesn't
  exist.
- Pragmatic test ergonomics: `client.get(f"/overview/preset/{name}")`
  is simpler than constructing a Form-encoded POST.

Why not return the existing `block_names` PLUS a new `preset_chips_oob`:
- The preset list comes from a YAML file that doesn't change between
  requests within a server lifetime (no live reload). The preset strip
  rendered in the initial GET /overview full-page render is stable; the
  OOB swap on preset apply only needs to refresh what the preset
  CHANGED — the grid, count, and active-filter chip strip. The preset
  strip itself doesn't need re-rendering on a click.

Constraints:
- Reuse `_parse_filter_dict` and `_build_overview_url` verbatim — DO NOT
  fork or re-implement.
- Reuse `block_names=["grid", "count_oob", "filter_badges_oob", "pagination_oob"]`
  exactly — same 4 blocks the existing POST handler emits, so HTMX
  merge-by-id works on every existing OOB target.
- Add `name` to `__all__` is NOT required (route function not imported
  elsewhere; only the `router` is).
- Response code on unknown preset: 404 (not 422) — semantically the
  resource ('the preset named X') doesn't exist. Keeps log filtering
  simple ("count 404s on /overview/preset/" → typos in YAML).
  </action>
  <verify>
    <automated>
.venv/bin/python -c "
from fastapi.testclient import TestClient
from app_v2.main import app
c = TestClient(app)
# 404 for unknown preset
r = c.get('/overview/preset/no-such-thing')
assert r.status_code == 404, r.status_code
# Known preset returns 200 + HX-Push-Url with the resolved query string
r = c.get('/overview/preset/qualcomm-wearables')
assert r.status_code == 200, r.status_code
push = r.headers.get('HX-Push-Url', '')
assert 'ap_company=Qualcomm' in push, push
assert 'application=Wearable' in push, push
print('OK')
"
    </automated>
  </verify>
  <done>
- `from app_v2.services.preset_store import load_presets` imported at top of routers/overview.py.
- Both GET /overview and POST /overview/grid contexts include `presets`.
- New GET /overview/preset/{name} route exists and:
  - Returns 200 + 4 OOB blocks for known preset names.
  - Sets HX-Push-Url to the canonical /overview?... URL with the preset's filters.
  - Returns 404 for unknown names.
  - Uses `_parse_filter_dict` and `_build_overview_url` (no forks).
  - `block_names` list is byte-equal to the POST /overview/grid list.
- Existing tests in tests/v2/test_joint_validation_routes.py still pass.
  </done>
</task>

<task type="auto">
  <name>Task 3: Render preset chip strip in overview/index.html + add .ff-preset-* CSS</name>
  <files>app_v2/templates/overview/index.html, app_v2/static/css/app.css</files>
  <action>
Two sub-steps — template render + CSS append.

### 3a. Insert preset chip strip in `app_v2/templates/overview/index.html`

Insert IMMEDIATELY BEFORE the existing `{% block filter_badges_oob %}`
opening tag (currently around line 38). The strip is render-conditional
on `presets` being non-empty so the empty/missing-YAML case yields no
markup:

```jinja
{# 260507-obp — Preset chip strip. Static (rendered only on full-page
   GET /overview, GET /overview/preset/<name>, POST /overview/grid since
   POST emits this block via the index template's full render layer is
   bypassed; preset list is server-loaded once per request via
   ctx["presets"]). Each chip issues GET /overview/preset/<slug> via
   HTMX, target=#overview-grid, hx-push-url=true so the address bar
   reflects the resolved filter URL after click.

   Hidden entirely when presets is empty (no YAML file, all entries
   malformed, or YAML present but list is empty) — prevents an empty
   container from claiming vertical space. #}
{% if presets %}
  <div class="ff-preset-row px-3 pt-2" id="overview-preset-row" aria-label="Filter presets">
    <span class="ff-label">Presets:</span>
    {% for p in presets %}
      <a class="ff-chip ff-preset-chip"
         href="/overview/preset/{{ p.name | e }}"
         hx-get="/overview/preset/{{ p.name | e }}"
         hx-target="#overview-grid"
         hx-swap="outerHTML"
         hx-push-url="true"
         data-preset="{{ p.name | e }}">
        {{ p.label | e }}
      </a>
    {% endfor %}
  </div>
{% endif %}
```

Why an `<a href="/overview/preset/...">` (not a `<button>`):
- Right-click → "Open in new tab" works (which spawns a fresh GET that
  renders the full /overview page filtered by the preset — useful for
  team workflows where one user wants to share "look at this preset" by
  middle-clicking).
- Graceful degradation if HTMX fails to load: the link still navigates.
- HTMX hx-get on an `<a>` intercepts the click; the href is the fallback.

Why `data-preset="{{ p.name | e }}"`:
- Test hooks: tests can assert `data-preset="qualcomm-wearables"` exists
  in the page without parsing the URL.

Why `aria-label="Filter presets"`:
- The strip has no visible heading; aria-label gives screen readers a
  cue that the row of chips is a related group. Matches pattern used on
  the JV grid scroll container (`aria-label="Joint Validation results"`,
  index.html:79).

### 3b. Append `.ff-preset-row` + `.ff-preset-chip` rules to `app_v2/static/css/app.css`

Append AT END OF FILE (after the existing `.ff-more` rule at ~line 1209):

```css
/* §Filter preset chips (260507-obp).
   Sibling to the .ff-* family from 260507-nzp; visually distinct from
   the per-facet .c-1..c-6 palette so the user reads the preset row as
   "actions" (clickable) and the active-filter row below as "state"
   (passive). Single neutral hue across all preset chips — color is NOT
   used to differentiate presets (the label text is the differentiator). */
.ff-preset-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 4px;
}
.ff-preset-chip {
  /* base .ff-chip already supplies size/radius/font; this rule layers
     on the interactive treatment + the neutral preset hue. */
  background: #f4f6f8;
  color: var(--ink-2);
  border: 1px solid var(--line);
  text-decoration: none;
  cursor: pointer;
  transition: background 120ms ease, border-color 120ms ease, color 120ms ease;
}
.ff-preset-chip:hover,
.ff-preset-chip:focus-visible {
  background: var(--accent-soft);
  border-color: var(--accent);
  color: var(--accent-ink);
  text-decoration: none;
}
.ff-preset-chip:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.ff-preset-chip:active {
  /* htmx-request flash: while the request is in flight, dim slightly so
     the user knows the click registered. */
  opacity: 0.7;
}
```

Why the `border` (not in the original 260507-nzp .ff-chip):
- Preset chips are interactive; the soft 1px border + hover ink change
  signals affordance. The non-interactive value chips (.c-1..c-6) are
  passive labels and intentionally have no border.

Why hover/focus uses `var(--accent-soft)` (blue) and NOT one of the
.c-N facet colors:
- Anchors to Dashboard_v2.html primary-action affordance (--accent is the
  app's "primary" hue per Phase 04 D-UIF-01 / btn-helix). Hovering a
  preset chip should feel like hovering a primary button, not like
  hovering a "status" filter chip.

Constraints:
- DO NOT add new tokens to tokens.css — all tokens (--accent-soft,
  --accent, --accent-ink, --ink-2, --line) already exist (see existing
  .ff-chip.c-1 + .btn-helix CSS rules).
- DO NOT modify existing .ff-chip rules — the new .ff-preset-chip layers
  on top.
- DO NOT introduce new .ff-preset-chip.c-N color slots — the design is
  intentionally one-color.
- The new strip MUST render BEFORE the existing #overview-filter-badges
  div (visual order: presets → active filters → grid).
  </action>
  <verify>
    <automated>
# Template + CSS markers
grep -q 'ff-preset-row' app_v2/templates/overview/index.html && \
grep -q 'ff-preset-chip' app_v2/templates/overview/index.html && \
grep -q '/overview/preset/' app_v2/templates/overview/index.html && \
grep -q '^.ff-preset-row' app_v2/static/css/app.css && \
grep -q '^.ff-preset-chip' app_v2/static/css/app.css && \
# Strip renders BEFORE filter_badges_oob (line numbers ascending)
test "$(grep -n 'ff-preset-row' app_v2/templates/overview/index.html | head -1 | cut -d: -f1)" -lt "$(grep -n 'filter_badges_oob' app_v2/templates/overview/index.html | head -1 | cut -d: -f1)" && \
# Render-time smoke test — strip renders with presets, hidden when empty
.venv/bin/python -c "
from fastapi.testclient import TestClient
from app_v2.main import app
c = TestClient(app)
r = c.get('/overview')
assert r.status_code == 200, r.status_code
assert 'ff-preset-row' in r.text, 'strip missing'
assert 'data-preset=\"qualcomm-wearables\"' in r.text, 'preset chip missing'
assert 'Qualcomm wearables' in r.text, 'label missing'
assert 'hx-get=\"/overview/preset/qualcomm-wearables\"' in r.text, 'hx-get missing'
print('OK')
"
    </automated>
  </verify>
  <done>
- `app_v2/templates/overview/index.html` renders the preset strip
  conditionally on `presets`, BEFORE the filter_badges_oob block.
- Each chip is an `<a>` with both `href` and `hx-get` to
  `/overview/preset/<name>`, target=#overview-grid, hx-push-url=true.
- `app_v2/static/css/app.css` has `.ff-preset-row` + `.ff-preset-chip`
  rules appended at end of file, no edits above.
- All chip-related styling consumes existing tokens — no new tokens.
- The 3 seed presets render visibly on GET /overview against the live
  content/joint_validation/ tree.
- Existing test_overview_filter_chips_* tests still pass (chip strip is
  ABOVE the active-filter strip, doesn't collide with existing markers).
  </done>
</task>

<task type="auto">
  <name>Task 4: Add tests/v2/test_overview_presets.py covering loader + render + click-apply + malformed-skip</name>
  <files>tests/v2/test_overview_presets.py</files>
  <action>
Create a new test file alongside `tests/v2/test_joint_validation_routes.py`.
Keeping it separate (not appending to test_joint_validation_routes.py) is a
deliberate scoping decision — the JV route file is already 600+ lines and a
preset-specific file is easier to find later.

```python
"""Filter-preset tests (260507-obp).

Covers:
  - load_presets() — happy path returns 3 entries from the example YAML.
  - load_presets() — malformed entries are silently skipped.
  - GET /overview — chip strip renders with the 3 preset chips.
  - GET /overview/preset/<name> — overrides current filters and returns
    the 4 OOB blocks plus HX-Push-Url with the resolved filters.
  - GET /overview/preset/<name> — 404 on unknown preset.
"""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from fastapi.testclient import TestClient

from app_v2.main import app
from app_v2.services.joint_validation_store import clear_parse_cache
from app_v2.services.preset_store import load_presets
from app_v2.services.summary_service import clear_summary_cache


SAMPLE_HTML = b"""<!DOCTYPE html><html><body>
<h1>Test Joint Validation</h1>
<table>
  <tr><th><strong>Status</strong></th><td>In Progress</td></tr>
  <tr><th><strong>Customer</strong></th><td>Samsung</td></tr>
  <tr><th><strong>AP Company</strong></th><td>Qualcomm</td></tr>
  <tr><th><strong>Application</strong></th><td>Wearable</td></tr>
  <tr><th><strong>Device</strong></th><td>UFS 4.0</td></tr>
  <tr><th><strong>Start</strong></th><td>2026-04-01</td></tr>
</table>
</body></html>"""


@pytest.fixture(autouse=True)
def _reset_caches():
    clear_parse_cache()
    clear_summary_cache()
    yield
    clear_parse_cache()
    clear_summary_cache()


@pytest.fixture
def jv_dir_with_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Drop one matching JV folder so the preset queries return a row."""
    folder = tmp_path / "3193868200"
    folder.mkdir()
    (folder / "index.html").write_bytes(SAMPLE_HTML)
    monkeypatch.setattr("app_v2.services.joint_validation_store.JV_ROOT", tmp_path)
    monkeypatch.setattr("app_v2.routers.overview.JV_ROOT", tmp_path)
    monkeypatch.setattr("app_v2.routers.joint_validation.JV_ROOT", tmp_path)
    return tmp_path


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def test_load_presets_returns_three_seed_entries() -> None:
    """The committed config/presets.example.yaml seeds 3 entries verbatim."""
    presets = load_presets()
    assert len(presets) == 3, presets
    names = [p["name"] for p in presets]
    assert names == ["korean-oems-in-progress", "qualcomm-wearables", "pending-ufs4"]
    # Multi-value within a facet preserved.
    korean = next(p for p in presets if p["name"] == "korean-oems-in-progress")
    assert korean["label"] == "Korean OEMs in progress"
    assert korean["filters"]["status"] == ["In Progress"]
    assert korean["filters"]["customer"] == ["Samsung", "Hyundai"]
    # Multi-facet (AND-across-facets) preserved.
    qc = next(p for p in presets if p["name"] == "qualcomm-wearables")
    assert qc["filters"]["ap_company"] == ["Qualcomm"]
    assert qc["filters"]["application"] == ["Wearable"]


def test_load_presets_skips_malformed_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each malformed entry is silently dropped; valid entries survive."""
    yaml_text = dedent("""
        # 1 valid + 6 distinct malformed cases — only the valid one survives.
        - name: ok-preset
          label: OK preset
          filters:
            status: ["Pending"]
        - name: missing-label
          filters:
            status: ["Pending"]
        - label: missing-name
          filters:
            status: ["Pending"]
        - name: unknown-facet
          label: Unknown facet
          filters:
            no_such_facet: ["x"]
        - name: non-list-value
          label: Non-list value
          filters:
            status: "Pending"
        - name: empty-facet
          label: Empty facet
          filters:
            status: []
        - name: missing-filters
          label: Missing filters
        - "not even a mapping"
    """).strip()
    yaml_path = tmp_path / "presets.yaml"
    yaml_path.write_text(yaml_text, encoding="utf-8")

    # Point load_presets at our tmp file by chdir-ing into a tmp dir whose
    # `config/presets.yaml` is the test file. This exercises the real
    # fallback chain (the example.yaml in the project root is bypassed
    # because cwd's config/presets.yaml takes precedence — first in the
    # chain).
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "presets.yaml").write_text(yaml_text, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    presets = load_presets()
    assert len(presets) == 1, presets
    assert presets[0]["name"] == "ok-preset"
    assert presets[0]["filters"] == {"status": ["Pending"]}


def test_load_presets_returns_empty_on_unparseable_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Syntactically broken YAML never raises; returns []."""
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "presets.yaml").write_text("[\nthis: is: not: valid: yaml", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert load_presets() == []


def test_load_presets_returns_empty_when_no_yaml_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No presets.yaml AND no presets.example.yaml → empty list."""
    monkeypatch.chdir(tmp_path)   # cwd has no `config/` dir at all
    assert load_presets() == []


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def test_get_overview_renders_preset_chip_strip(
    jv_dir_with_one: Path, client: TestClient
) -> None:
    r = client.get("/overview")
    assert r.status_code == 200
    # Strip wrapper present.
    assert 'id="overview-preset-row"' in r.text
    # 3 chips render with the seed labels and slugs.
    assert 'data-preset="korean-oems-in-progress"' in r.text
    assert 'data-preset="qualcomm-wearables"' in r.text
    assert 'data-preset="pending-ufs4"' in r.text
    assert "Korean OEMs in progress" in r.text
    assert "Qualcomm wearables" in r.text
    assert "Pending UFS 4.0" in r.text
    # Each chip wires hx-get + href + hx-push-url.
    assert 'hx-get="/overview/preset/qualcomm-wearables"' in r.text
    assert 'href="/overview/preset/qualcomm-wearables"' in r.text
    assert 'hx-push-url="true"' in r.text


def test_get_overview_omits_strip_when_no_presets(
    jv_dir_with_one: Path,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty load_presets() → strip wrapper is NOT rendered."""
    monkeypatch.setattr("app_v2.routers.overview.load_presets", lambda: [])
    r = client.get("/overview")
    assert r.status_code == 200
    assert "overview-preset-row" not in r.text
    assert "ff-preset-chip" not in r.text


# ---------------------------------------------------------------------------
# Click-apply
# ---------------------------------------------------------------------------


def test_get_overview_preset_overrides_filters_and_returns_oob_blocks(
    jv_dir_with_one: Path, client: TestClient
) -> None:
    r = client.get("/overview/preset/qualcomm-wearables")
    assert r.status_code == 200
    # Returns OOB blocks (not the full page shell) — same shape as POST /overview/grid.
    assert 'id="overview-grid"' in r.text
    assert 'id="overview-filter-badges" hx-swap-oob="true"' in r.text
    assert 'id="overview-count" hx-swap-oob="true"' in r.text
    assert 'id="overview-pagination" hx-swap-oob="true"' in r.text
    # Active-filter chips reflect the preset's values, not whatever was sent.
    assert 'data-facet="ap_company"' in r.text
    assert 'class="ff-chip c-3">Qualcomm</span>' in r.text
    assert 'data-facet="application"' in r.text
    assert 'class="ff-chip c-6">Wearable</span>' in r.text
    # No status / customer / device / controller chips (preset doesn't mention).
    assert 'data-facet="status"' not in r.text
    assert 'data-facet="customer"' not in r.text
    # HX-Push-Url carries the canonical /overview?... query string.
    push = r.headers.get("HX-Push-Url", "")
    assert push.startswith("/overview?"), push
    assert "ap_company=Qualcomm" in push
    assert "application=Wearable" in push
    # Preset apply does NOT carry over an old status/customer.
    assert "status=" not in push
    assert "customer=" not in push


def test_get_overview_preset_unknown_returns_404(
    jv_dir_with_one: Path, client: TestClient
) -> None:
    r = client.get("/overview/preset/no-such-preset")
    assert r.status_code == 404


def test_get_overview_preset_clicked_after_existing_filters_overrides_them(
    jv_dir_with_one: Path, client: TestClient
) -> None:
    """OVERRIDE semantics: previous filters do NOT bleed into the preset response.

    The HTTP-level test cannot easily simulate "user had existing filters
    then clicked a preset" because /overview/preset/<name> does not read
    filter query params from the request — but THAT is precisely the
    contract: the preset is the entire filter state, regardless of what
    the request URL contains. We pin the contract by sending stray query
    params and asserting they are ignored.
    """
    r = client.get(
        "/overview/preset/qualcomm-wearables",
        params=[("status", "Cancelled"), ("customer", "Apple")],
    )
    assert r.status_code == 200
    push = r.headers.get("HX-Push-Url", "")
    assert "status=" not in push
    assert "customer=" not in push
    assert "ap_company=Qualcomm" in push
    assert "application=Wearable" in push
```

Manual UI verification (record observation in the commit body):
1. Start the dev server: `.venv/bin/uvicorn app_v2.main:app --reload --port 8765`
2. Open http://localhost:8765/overview in a browser.
3. Confirm 3 preset chips render above the active-filter row.
4. Click "Qualcomm wearables". Confirm the grid filters down to Qualcomm
   wearable rows AND the active-filter strip shows
   "AP Company: Qualcomm" + "Application: Wearable". URL bar should
   contain `?ap_company=Qualcomm&application=Wearable`.
5. Manually pre-select something else in the Status picker, then click
   "Pending UFS 4.0". Confirm the previous Status selection is REPLACED
   by `Pending` (not added to it).
6. Edit `config/presets.example.yaml` and break one entry (e.g. set
   `filters: 42`). Reload /overview. That entry vanishes; the others
   still render. Server log shows a WARNING for the malformed entry.
7. Note any visual regressions in the commit message under "Manual UAT".

Fallback when no dev server: representative TestClient snapshot via
`.venv/bin/python -c "from fastapi.testclient import TestClient; from
app_v2.main import app; c=TestClient(app); print(c.get('/overview').text[:6000])"`
and visually inspect for the 3 preset chips above the filter strip.
  </action>
  <verify>
    <automated>
.venv/bin/pytest tests/v2/test_overview_presets.py -x -q && \
# Make sure existing JV route tests still pass — proves preset strip
# doesn't collide with the 260507-nzp chip markers.
.venv/bin/pytest tests/v2/test_joint_validation_routes.py -x -q
    </automated>
  </verify>
  <done>
- `tests/v2/test_overview_presets.py` exists with at least 7 tests:
  - test_load_presets_returns_three_seed_entries
  - test_load_presets_skips_malformed_entries
  - test_load_presets_returns_empty_on_unparseable_yaml
  - test_load_presets_returns_empty_when_no_yaml_present
  - test_get_overview_renders_preset_chip_strip
  - test_get_overview_omits_strip_when_no_presets
  - test_get_overview_preset_overrides_filters_and_returns_oob_blocks
  - test_get_overview_preset_unknown_returns_404
  - test_get_overview_preset_clicked_after_existing_filters_overrides_them
- All tests pass.
- Existing tests in tests/v2/test_joint_validation_routes.py still pass
  (no regression — preset strip doesn't break JV chip markers).
- Manual UI verification performed (or representative snapshot inspected
  if no server available); observations noted in the commit body.
  </done>
</task>

</tasks>

<verification>
After all four tasks:

1. Full v2 test pass:
   `.venv/bin/pytest tests/v2/ -x -q`
   (expect 563 + 9 new = 572 passed; pre-existing 5 skipped unchanged)
2. Lint:
   `.venv/bin/ruff check app_v2/ tests/v2/test_overview_presets.py`
3. Loader smoke test:
   `.venv/bin/python -c "from app_v2.services.preset_store import load_presets; print(len(load_presets()))"`
   prints `3`.
4. Route smoke test:
   `.venv/bin/python -c "from fastapi.testclient import TestClient; from app_v2.main import app; c=TestClient(app); print(c.get('/overview/preset/qualcomm-wearables').headers['HX-Push-Url'])"`
   prints a /overview?... URL containing `ap_company=Qualcomm&application=Wearable`.
5. Backend untouched outside the planned files:
   `git diff --stat app_v2/services/joint_validation_grid_service.py app_v2/services/joint_validation_store.py app_v2/services/joint_validation_parser.py app_v2/services/joint_validation_summary.py`
   should print nothing — preset feature does not modify the existing JV
   service stack.
6. CSS append-only check:
   `git diff app_v2/static/css/app.css | grep -E '^-[^-]' | grep -v '^--- '`
   should print nothing — only additions to app.css.
7. Existing OOB target ids byte-stable:
   `grep -c 'id="overview-filter-badges"' app_v2/templates/overview/index.html` → 1
   `grep -c 'id="overview-pagination"' app_v2/templates/overview/index.html` → 2 (existing)
   `grep -c 'id="overview-count"' app_v2/templates/overview/index.html` → 2 (existing)
</verification>

<success_criteria>
- `config/presets.example.yaml` exists with the 3 seed presets verbatim;
  `config/presets.yaml` listed in `.gitignore`.
- `app_v2/services/preset_store.py` provides `load_presets() -> list[Preset]`
  with the YAML fallback chain + per-entry validation + log-and-skip on
  malformed entries.
- `GET /overview/preset/{name}` route exists, returns 4 OOB blocks
  identical to POST /overview/grid, sets HX-Push-Url to the canonical
  /overview?... URL, and 404s on unknown names.
- Preset chip strip renders above the active-filter chip strip on
  /overview, hidden entirely when no presets are loaded.
- Each preset chip is an `<a>` with `href`, `hx-get`, `hx-push-url=true`
  pointing at /overview/preset/<slug>.
- Preset chip styling reuses the .ff-* family (sibling .ff-preset-chip
  rule, single neutral hue, hover/focus uses --accent-* tokens) — no
  new tokens added.
- OVERRIDE semantics confirmed by test_get_overview_preset_clicked_after_existing_filters_overrides_them.
- Malformed YAML / missing YAML / non-list top-level / unknown-facet keys
  all gracefully degrade — loader returns [] or skips the entry, never
  raises.
- All 9+ new tests in tests/v2/test_overview_presets.py pass.
- Existing tests in tests/v2/test_joint_validation_routes.py and
  tests/v2/test_joint_validation_grid_service.py pass unchanged.
- Zero diff to `app_v2/services/joint_validation_*.py` files (the JV
  service stack is not touched by this task).
</success_criteria>

<output>
After completion:
1. Commit on `ui-improvement` branch:
   `feat(overview): add filter presets — config/presets.yaml + clickable chips that override filter selection [quick-260507-obp]`
   (single commit OR one commit per task — match the granularity used in
   recent quick tasks; 260507-nzp used 3 commits, 260507-mmv used 1
   atomic commit. Either is fine.)
2. Update `.planning/STATE.md` "Quick Tasks Completed" table with the entry.
3. Write `260507-obp-SUMMARY.md` in
   `.planning/quick/260507-obp-add-browse-presets-presets-yaml-clickabl/`
   capturing: files changed, the 3 seed preset values + why those, the
   override-vs-additive decision, and the manual UI observation.
</output>
</content>
</invoke>