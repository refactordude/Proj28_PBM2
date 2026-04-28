---
phase: 05-overview-redesign
plan: 05
subsystem: app_v2/templates/overview
tags: [templates, jinja2, bootstrap, htmx, sortable-table, picker-popover, sticky-header, macro-reuse]
requires:
  - 05-01 (picker_popover macro parameterized with form_id/hx_post/hx_target kwargs)
  - 05-03 (OverviewGridViewModel + OverviewRow Pydantic models exposed by overview_grid_service)
  - 05-04 (POST /overview/grid route with block_names=["grid","count_oob","filter_badges_oob"])
  - 04 (Phase 4 _picker_popover.html macro source-of-truth — REUSED, NOT forked)
provides:
  - app_v2/templates/overview/index.html (full Overview page; defines blocks grid, count_oob, filter_badges_oob; sortable_th macro at template-top scope)
  - app_v2/templates/overview/_grid.html (<tbody> partial with maybe macro, AI Summary cell, empty-state row)
  - app_v2/templates/overview/_filter_bar.html (6 picker popovers via cross-template macro import + Clear-all link)
  - app_v2/static/css/app.css Phase 5 block (.overview-grid-body + .overview-table)
affects:
  - app_v2/templates/overview/_filter_alert.html (DELETED — D-OV-05)
  - app_v2/templates/overview/_entity_row.html (DELETED — D-OV-05)
tech-stack:
  patterns:
    - "Cross-template macro import for shared UI primitives ({% from 'browse/_picker_popover.html' import picker_popover %})"
    - "Template-top-level macro placement (between {% extends %} and {% block content %}) so macros are visible from nested {% block %} children"
    - "Inline-macro-in-partial for include-scoped helpers (maybe in _grid.html avoids macro-scope ambiguity)"
    - "OOB swap target stability — count caption + picker badges live OUTSIDE the primary swap target #overview-grid (Pitfall 7 from Phase 4)"
    - "Defense-in-depth XSS — Jinja2 autoescape + explicit escape filter on every dynamic output"
    - "Audit-grep-friendly comment hygiene — banned tokens (escape-bypass filter, inline scripts) avoided in source comments so acceptance grep stays strict (Plan 05-02 convention)"
key-files:
  created:
    - app_v2/templates/overview/_grid.html
    - app_v2/templates/overview/_filter_bar.html
    - .planning/phases/05-overview-redesign/deferred-items.md
  modified:
    - app_v2/templates/overview/index.html (full rewrite; 134 lines deleted, 163 lines added)
    - app_v2/static/css/app.css (Phase 5 block appended; 56 lines added)
  deleted:
    - app_v2/templates/overview/_filter_alert.html
    - app_v2/templates/overview/_entity_row.html
decisions:
  - sortable_th macro lives at template-top scope (between extends and block content) so it is visible from nested grid block; maybe macro lives inline at top of _grid.html (consumed only by that partial) to sidestep Jinja2 macro-scope ambiguity across {% include %} boundaries
  - OOB filter_badges_oob block iterates active_filter_counts dict (which always has all 6 FILTERABLE_COLUMNS keys) so the loop emits exactly 6 spans on every POST /overview/grid; d-none class toggles when count==0 (D-08 from Phase 4 mirrored)
  - Empty-state row distinguishes "no curated yet" (zero active filters → friendly alert) from "filters narrowed to zero" (any active filter → muted text); discrimination uses {{ active_filter_counts.values() | sum }} == 0
  - .overview-grid-body uses 70vh max-height + overflow-y auto matching .browse-grid-body to engage thead.sticky-top (Pattern 5 / Pitfall 1 from Phase 4)
  - 22 legacy test failures (test_overview_filter.py / test_overview_routes.py / test_content_routes.py) explicitly deferred to Plan 05-06 — they target deleted markup/routes per D-OV-04 / D-OV-05 locks; Plan 05-06 (Wave 4) is the documented follow-on for the v2 overview test rewrite
metrics:
  duration: ~25min
  completed: "2026-04-28"
  commits: 6
  tasks: 6
  files_created: 3
  files_modified: 2
  files_deleted: 2
  lines_added: ~398
  lines_deleted: ~136
---

# Phase 5 Plan 5: Overview Templates (Sortable Bootstrap Table) Summary

Built the Phase 5 user-facing surface: full Jinja2 template rewrite that turns the Plan 05-03 `OverviewGridViewModel` into a 14-column sortable Bootstrap table mirroring the Phase 4 Browse pivot grid. Reuses the Phase 4 `picker_popover` macro AS-IS (cross-template import — no fork) for the 6 multi-filter popovers (Status, Customer, AP Company, Device, Controller, Application).

## What Shipped

### Final template inventory under `app_v2/templates/overview/`

```
app_v2/templates/overview/
├── _filter_bar.html   (NEW — 86 lines; 6 picker_popover calls + Clear-all link)
├── _grid.html         (NEW — 93 lines; <tbody> partial + maybe macro + AI Summary cell)
└── index.html         (REWRITE — 163 lines; sortable_th macro + 14-col table + 3 OOB blocks)

DELETED:
├── _filter_alert.html (legacy 409/404 alert — POST /overview/add 4xx now returns plain-text Response per Plan 05-04)
└── _entity_row.html   (legacy <li> entity row — replaced by Bootstrap table cells in _grid.html)
```

3 files, 0 legacy. Plan 05-04 confirmed the legacy `_filter_alert.html` has no remaining caller (4xx error paths return `Response` directly).

### Macro reuse — NO fork (D-OV-06)

The Phase 4 picker macro is imported AS-IS via cross-template path:

```jinja
{% from "browse/_picker_popover.html" import picker_popover %}
```

The 3 kwargs added in Plan 05-01 (`form_id`, `hx_post`, `hx_target`) make this work — Phase 5 calls override all 3 to point at the Overview's form id, route, and grid target. Phase 4 callers continue to use the byte-stable defaults (`browse-filter-form` / `/browse/grid` / `#browse-grid`), so Phase 4 byte-stability is preserved.

`grep -c "picker_popover(" app_v2/templates/overview/_filter_bar.html` returns 6 (one call per FILTERABLE_COLUMN). `grep -c "form_id='overview-filter-form'"` returns 6, `grep -c "hx_post='/overview/grid'"` returns 6, `grep -c "hx_target='#overview-grid'"` returns 6 — all 6 calls override all 3 defaults consistently.

### 14-column order rendered in index.html

The 12 sortable columns are emitted via 12 explicit `sortable_th` macro calls in the exact order locked by must_haves.truths #2:

```jinja
{{ sortable_th('title',       'Title') }}
{{ sortable_th('status',      'Status') }}
{{ sortable_th('customer',    'Customer') }}
{{ sortable_th('model_name',  'Model Name') }}
{{ sortable_th('ap_company',  'AP Company') }}
{{ sortable_th('ap_model',    'AP Model') }}
{{ sortable_th('device',      'Device') }}
{{ sortable_th('controller',  'Controller') }}
{{ sortable_th('application', 'Application') }}
{{ sortable_th('assignee',    '담당자') }}
{{ sortable_th('start',       'Start') }}
{{ sortable_th('end',         'End') }}
<th scope="col" class="text-end">Link</th>
<th scope="col" class="text-end">AI Summary</th>
```

The 12 sortable columns match `SORTABLE_COLUMNS = ALL_METADATA_KEYS` from `overview_grid_service.py`. `Link` and `AI Summary` are non-sortable (no `sortable_th` call).

### Sort cycle (D-OV-07)

The `sortable_th` macro encodes the asc↔desc 2-state cycle inline via `hx-vals`:

```jinja
hx-vals='{"sort": "{{ col | e }}", "order": "{% if vm.sort_col == col and vm.sort_order == 'asc' %}desc{% else %}asc{% endif %}"}'
```

- Click currently-asc column → next order = desc
- Click currently-desc column → next order = asc
- Click any other column → next order = asc (default first-click)

Per D-OV-07 "asc → desc → asc" lock. The active sort header shows `bi-arrow-down-short` (desc) or `bi-arrow-up-short` (asc) glyph; inactive headers show no glyph.

### AI Summary cell — Phase 3 SUMMARY-02 contract preserved (D-OV-10)

```jinja
<button type="button"
        class="btn btn-sm btn-outline-primary ai-btn"
        hx-post="/platforms/{{ row.platform_id | e }}/summary"
        hx-target="#summary-{{ row.platform_id | e }}"
        hx-swap="innerHTML"
        hx-disabled-elt="this"
        {% if not row.has_content %}disabled title="No content page to summarize yet"{% endif %}
        aria-label="Generate AI summary for {{ row.title | e }}">
  AI Summary
</button>
<div id="summary-{{ row.platform_id | e }}" class="mt-1"></div>
```

`hx-post` URL, `hx-target` slot, `hx-disabled-elt`, and `disabled` driven by `row.has_content` are all verbatim from Phase 3 D-13. Only the surrounding utility class differs (`btn btn-sm btn-outline-primary ai-btn` vs Phase 3's `ai-btn ms-2`) — adapted for the table-cell layout vs the legacy flex `<li>`.

### OOB swap blocks (Pitfall 7 from Phase 4)

The `count_oob` and `filter_badges_oob` blocks live OUTSIDE `<div id="overview-grid">` so they are stable OOB swap targets that the primary `innerHTML` swap on `#overview-grid` never touches:

- `count_oob` → `<span id="overview-count">` in panel-header
- `filter_badges_oob` → 6 picker badge spans (`id="picker-{name}-badge"`) in the persistent picker triggers

Both are emitted on every POST /overview/grid alongside the primary grid swap (block_names=["grid","count_oob","filter_badges_oob"] from Plan 05-04).

### Smoke render output

End-to-end Jinja smoke render with stub `OverviewGridViewModel` passes all 14 sanity assertions (full Task 6 verify):

```
overview smoke render OK
```

Empty-state render (zero rows, zero active filters) also passes:

```
empty-state render OK
```

FastAPI app boots cleanly with all 3 expected `/overview` routes registered:

```
['/overview', '/overview/add', '/overview/grid']
```

Phase 4 byte-stability regression test PASSES — 30/30 in `tests/v2/test_browse_routes.py` + `tests/v2/test_phase04_invariants.py`. The picker macro's Phase 4 default kwargs continue to render byte-identical Browse markup; cross-page reuse changed nothing for Phase 4 callers.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Hoist sortable_th macro out of `{% block content %}`**

- **Found during:** Task 6 smoke render verification.
- **Issue:** `jinja2.exceptions.UndefinedError: 'sortable_th' is undefined` raised when the macro lived inside `{% block content %}` but was called from the nested `{% block grid %}`. Jinja2 block scoping does not propagate macros from a parent block to a child block.
- **Fix:** Moved `{% macro sortable_th %}` OUTSIDE `{% block content %}`, between `{% extends "base.html" %}` and `{% block content %}`. Macros at template-top scope are visible from all blocks in the same template (canonical Jinja2 idiom for shared markup helpers across child blocks).
- **Files modified:** `app_v2/templates/overview/index.html`
- **Commit:** `a0d3dd8`
- **Symmetry:** This is consistent with the `maybe` macro choice in `_grid.html` (kept inline in the partial, NOT in `index.html`). Both decisions sidestep Jinja2 macro-scope ambiguity. Inline comment in `index.html` documents the constraint for future readers.

### Auth Gates

None — no API authentication touched in this plan.

## Plan 05-06 Dependency / Out-of-Scope

22 pre-existing tests now fail because they target legacy markup (`_entity_row.html` `<li>` shape, `<details>` filter block, `class="ai-btn ms-2"`) or removed routes (`POST /overview/filter`, `POST /overview/filter/reset`, `DELETE /overview/{pid}`). These deletions are deliberate per D-OV-04 / D-OV-05 locks — and Plan 05-05's `<output>` explicitly defers test resurfacing to Plan 05-06.

Documented in `.planning/phases/05-overview-redesign/deferred-items.md` (78 lines):

| Test file | Failures | Reason |
|-----------|----------|--------|
| `tests/v2/test_overview_filter.py` | 11 | Targets removed `POST /overview/filter` + `POST /overview/filter/reset` |
| `tests/v2/test_overview_routes.py` | 9 | Targets removed `DELETE /overview/{pid}`, deleted `_entity_row.html` markup, deleted `<details>` filter block, removed legacy 4xx alert template |
| `tests/v2/test_content_routes.py` | 2 | Asserts `class="ai-btn ms-2"` (Phase 3 utility class); Phase 5 cell uses `class="btn btn-sm btn-outline-primary ai-btn"` for table-cell layout |

Plan 05-06 invariant tests should additionally verify (per `<output>`):

- NO `| safe` filter in any `app_v2/templates/overview/*.html`
- Picker macro is shared NOT forked (no copy of `_picker_popover.html` under `overview/`)
- NO `hx-delete=/overview/<pid>` anywhere in templates (DELETE removed)
- The 4 pivot-grid table classes (`table table-striped table-hover table-sm`) appear in `overview/index.html` (Phase 4 visual parity)
- 14-column header order matches must_haves.truths #2 exactly
- `담당자` literal present (Korean unicode round-trip)
- `<form id="overview-filter-form">` precedes the filter bar include in source order (gap-2 mechanism)
- The `sortable_th` macro lives OUTSIDE `{% block content %}` (template-top scope) to remain visible from `{% block grid %}` (Plan 05-05 deviation lesson)

## Visual Issues for User Review (post Plan 05-06)

When Plan 05-06 lands and a manual browser pass becomes feasible, flag these for visual QA:

1. **Sticky thead engagement** — confirm `thead.sticky-top` actually sticks while scrolling the table body (relies on `.overview-grid-body { max-height: 70vh; overflow-y: auto }` from Task 5 CSS).
2. **Picker popover overflow** — confirm picker dropdowns escape the panel (`.panel:has(.browse-filter-bar) { overflow: visible }` is Browse-scoped via `:has()`; Overview may need an analogous scope rule if dropdowns clip on a short panel).
3. **AI Summary disabled state visual** — confirm the Phase 3 `.ai-btn:disabled` opacity 0.5 + cursor not-allowed renders correctly on the new `btn btn-sm btn-outline-primary ai-btn` cell button.
4. **Sort glyph alignment** — confirm `bi-arrow-down-short` / `bi-arrow-up-short` icons are vertically centered in the column header button next to the label.
5. **Korean column header (`담당자`) wrapping** — confirm the 3-char Korean string does not wrap differently from the English headers under narrow viewports.
6. **Empty-state alert positioning** — confirm the `colspan="14"` alert centers correctly under the sticky thead (verified via empty-state smoke render; visual confirmation pending).

## Self-Check: PASSED

- File `app_v2/templates/overview/index.html`: FOUND
- File `app_v2/templates/overview/_grid.html`: FOUND
- File `app_v2/templates/overview/_filter_bar.html`: FOUND
- File `app_v2/templates/overview/_filter_alert.html`: ABSENT (deleted as planned)
- File `app_v2/templates/overview/_entity_row.html`: ABSENT (deleted as planned)
- Phase 5 CSS block in `app_v2/static/css/app.css`: FOUND (grep "Phase 05 — Overview Tab Redesign")
- File `.planning/phases/05-overview-redesign/deferred-items.md`: FOUND
- Commit b056c6e (Task 1): FOUND in git log
- Commit f6d4c8d (Task 2): FOUND in git log
- Commit 2a62c8d (Task 3): FOUND in git log
- Commit 30b25ee (Task 4): FOUND in git log
- Commit 1c42c2b (Task 5): FOUND in git log
- Commit a0d3dd8 (Task 6 + Rule-1 fix): FOUND in git log
- All 14 Task 6 smoke assertions: PASS
- Empty-state smoke render: PASS
- Phase 4 byte-stability regression (30 tests): PASS
- FastAPI app boot (3 /overview routes): PASS
