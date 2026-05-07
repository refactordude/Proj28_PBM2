---
task: 260507-nzp
type: quick
description: Replace filter facet count badges with chips listing actual selected values (up to 10 + "+N more")
completed: 2026-05-07
duration: 5min
tasks: 3
files: 3
commits:
  - dd6e8e7  # CSS: .ff-* chip rules
  - f756595  # Template: filter_badges_oob rewrite
  - c527a31  # Tests: chip / overflow / empty-state contracts
tests:
  added: 3
  total_jv_route_pass: 20
  full_v2_suite_pass: 563  # 5 skipped
files_modified:
  - app_v2/static/css/app.css                       # +51 lines (append)
  - app_v2/templates/overview/index.html            # +48/-17 lines (block rewrite)
  - tests/v2/test_joint_validation_routes.py        # +97 lines (3 tests + helper)
backend_diff: empty                                # render-layer-only confirmed
---

# Quick Task 260507-nzp: Replace Filter Facet Count Badges with Value Chips

## One-liner

Active-filter summary above the JV grid now lists the actual selected values
as soft-colored chip rows (one row per facet, capped at 10 chips with a
"+N more" overflow chip) instead of opaque "Status: 2" count badges —
render-layer-only swap; no backend / view-model / router change.

## What Changed

### CSS (`app_v2/static/css/app.css` — append, +51 lines)

New `.ff-*` namespace appended after the existing `.btn-helix.ghost:hover`
rule (line 1160 → 1211 after edit). Defines:

- `.ff-row` — flex row with 6px gap, 4px bottom margin (collapses on `:last-child`)
- `.ff-label` — 12px / 600 weight, ink-2 color, the row's facet label
- `.ff-chip` — base chip: 11px / 600, pill radius, `inline-flex`,
  3px × 9px padding (mirrors `.tiny-chip` exactly)
- `.ff-chip.c-1` … `.ff-chip.c-6` — 6 deterministic per-facet color slots
- `.ff-more` — neutral overflow chip (transparent background, mute color)

### Template (`app_v2/templates/overview/index.html` — block rewrite, +48/-17 lines)

The `filter_badges_oob` block (formerly lines 33–43) now consumes
`selected_filters[col]` (already supplied by the router context) and
renders one `.ff-row` per non-empty facet with:

- A `.ff-label` (human-readable label from the `ff_labels` Jinja dict)
- Up to 10 `.ff-chip` elements (each carrying the facet's `.c-N` variant)
- A `.ff-chip.ff-more` overflow indicator with `+N more` when
  `len(values) > 10` (where `N = len(values) - 10`)

The wrapper element `<div id="overview-filter-badges" hx-swap-oob="true">`
is byte-stable so HTMX OOB merge-by-id continues to work on
`POST /overview/grid` (`block_names=["…", "filter_badges_oob", "…"]`
in `routers/overview.py:231`).

### Tests (`tests/v2/test_joint_validation_routes.py` — +97 lines)

- `_write_many_jv_status_values(root, n)` helper writes N fake JV folders
  with 9-digit numeric ids (`^\d+$` D-JV-03 compliance) and distinct
  status values, returning the list of statuses.
- `test_overview_filter_chips_render_actual_values` — 2 status + 1
  customer selected; asserts `.ff-chip.c-1` chips for "In Progress" /
  "Verified", `.ff-chip.c-2` for "Samsung", no `data-facet="ap_company"`,
  no `ff-more`.
- `test_overview_filter_chips_overflow_shows_plus_n_more` — 11 statuses
  selected; asserts exactly 10 `.ff-chip.c-1` chips + exactly 1
  `ff-more` + the literal "+1 more".
- `test_overview_filter_chips_no_active_filters_renders_empty_wrapper` —
  zero filters; asserts wrapper id is present, but no `ff-row` /
  `ff-chip` markup (HTMX target byte-stable for empty merges).

## Color Mapping Decision

| Facet (FILTERABLE_COLUMNS order) | Variant | Tokens                                   |
|----------------------------------|---------|------------------------------------------|
| `status`                         | `c-1`   | `--accent-soft` / `--accent-ink` (blue)  |
| `customer`                       | `c-2`   | `--green-soft` / `--green`               |
| `ap_company`                     | `c-3`   | `--violet-soft` / `--violet`             |
| `device`                         | `c-4`   | `--amber-soft` / `--amber`               |
| `controller`                     | `c-5`   | `--red-soft` / `--red`                   |
| `application`                    | `c-6`   | `#f4f6f8` / `--ink-2` (neutral)          |

**Why these specific assignments:**

- `status` got `c-1` (accent blue) because it is the most-frequently filtered
  facet in the v2 UI today and the accent token is what the rest of the app
  uses for "primary action" affordances — keeps the eye anchored on the
  primary axis of the dataset.
- `customer` got `c-2` (green) — green carries no semantic warning weight
  and customer is a benign organizational filter.
- `ap_company` got `c-3` (violet) — violet is otherwise reserved for AI
  affordances in the app, but in the active-filter strip it is purely a
  facet color (no AI semantics) and provides a distinct hue from the
  surrounding chips.
- `device`, `controller` got `c-4` / `c-5` (amber/red) — both are typically
  technical filters; amber/red provide enough chromatic separation from the
  cooler colors above without re-using a hue.
- `application` got `c-6` (neutral grey) because it is the lowest-frequency
  facet and the palette intentionally bottoms out in neutral so the
  most-used facets get the most-saturated hues.

**Why subtle (`-soft` background + saturated `var(--<name>)` foreground)
over saturated chips:**

- The active-filter strip is a *passive* read-only summary — it should be
  glanceable but not steal attention from the grid below. Saturated
  backgrounds (which Bootstrap's `bg-success` / `bg-info` / `bg-warning`
  produce) would visually compete with grid content.
- The pattern matches the existing `.tiny-chip.ok|info|warn|err|neutral`
  family already used elsewhere in `app.css` (Dashboard_v2.html lines
  263-268). Using the same vocabulary for the filter strip keeps the design
  language coherent.

**Why no new tokens added to `tokens.css`:**

- All 12 color values consumed are already defined in `tokens.css`
  (`--accent-soft` / `--accent-ink` / `--green-soft` / `--green` /
  `--violet-soft` / `--violet` / `--amber-soft` / `--amber` / `--red-soft`
  / `--red` / `--ink-2` / `--mute`). The lone `#f4f6f8` literal already
  appears in `app.css` (lines 1072, 1087, 1160) for the same neutral
  background. Promoting `#f4f6f8` to a token would have ≥3 callers but
  is out of scope for this quick task — track for a follow-up cleanup.

## Manual UAT (TestClient HTML snapshot)

Dev server start was skipped — the plan's fallback (representative
TestClient snapshot) was used.

**Snapshot 1 — multi-facet selection:**

```
GET /overview?status=In%20Progress&status=Verified&customer=Samsung
```

Rendered `#overview-filter-badges` block:

```html
<div id="overview-filter-badges" hx-swap-oob="true" class="px-3 pt-2">
  <div class="ff-row" data-facet="status">
    <span class="ff-label">Status:</span>
    <span class="ff-chip c-1">In Progress</span>
    <span class="ff-chip c-1">Verified</span>
  </div>
  <div class="ff-row" data-facet="customer">
    <span class="ff-label">Customer:</span>
    <span class="ff-chip c-2">Samsung</span>
  </div>
</div>
```

**Snapshot 2 — overflow (11 status values):**

- `c-1` chip count: 10
- `ff-more` count: 1
- "+1 more" literal: present

**Snapshot 3 — empty state:**

`GET /overview` (no filter params) renders the wrapper with **zero**
`.ff-row` / `.ff-chip` children — HTMX merge target stays stable for
subsequent updates.

## Verification

| Check                                               | Result |
|-----------------------------------------------------|--------|
| `pytest tests/v2/ -x -q`                            | 563 passed, 5 skipped |
| `pytest tests/v2/test_joint_validation_routes.py`   | 20 passed |
| `grep -q 'ff-chip' app_v2/templates/overview/index.html` | OK (2 occurrences) |
| CSS deletions in `app.css`                          | 0 (append-only) |
| `git diff … -- app_v2/services/ app_v2/routers/`    | empty (render-layer-only confirmed) |
| Existing `test_post_overview_grid_returns_oob_blocks` | still passes (id byte-stable) |
| Existing `test_get_overview_with_filters_round_trip_url` | still passes ("badge" branch satisfied via "ff-chip" being a CSS-class substring of the rendered HTML — fixture has 1 row matching `status=In Progress`) |

ruff was not available in `.venv/` so the optional lint step was skipped;
the syntactic correctness is implied by the pytest suite passing.

## Deviations from Plan

None. Plan executed exactly as written.

The fallback (TestClient HTML snapshot) was used in lieu of starting a
dev server — this was an explicit alternative path the plan permitted
("If the dev server is unavailable in this environment, fall back to a
representative snapshot").

## Decisions Made

- **Color slot assignment frozen as the FILTERABLE_COLUMNS-order mapping
  documented in the table above** — both the template `ff_variants` dict
  and the CSS `.c-1`..`.c-6` rules encode this mapping in lockstep. Future
  reordering of FILTERABLE_COLUMNS would also need to update both halves
  (or, preferably, refactor the variant assignment to a shared
  Python-side enum).
- **No new CSS tokens** — `#f4f6f8` neutral was kept inline (matches
  existing `.tiny-chip.neutral` precedent at line 1087 and `.lnk:hover`
  at line 1072). Promoting to `--neutral-soft` is a future cleanup if a
  4th caller emerges.
- **`selected_filters.get(col) or []` over `selected_filters[col]`** —
  defensive empty-list fallback matches the plan's directive; future
  refactors that produce sparse filter dicts will not 500-error the
  template.
- **Iterate the literal column tuple in the template** rather than
  `vm.active_filter_counts.items()` — makes column ordering explicit at
  the call site and removes the hidden dependency on Python dict-insertion
  ordering. Same convention `_filter_bar.html` already uses.

## Commits

| Hash      | Type | Description                                                              |
|-----------|------|--------------------------------------------------------------------------|
| `dd6e8e7` | feat | Add `.ff-*` chip CSS for active-filter summary                           |
| `f756595` | feat | Rewrite `filter_badges_oob` block to render value chips                  |
| `c527a31` | test | Pin chip rendering + overflow + empty-state contracts                    |

## Self-Check: PASSED

- All three commits exist on `ui-improvement` (`git log` confirmed).
- All three modified files exist and contain the expected markers.
- 20/20 JV route tests pass; 563/568 full v2 suite passes (5 pre-existing
  skips unchanged).
- Backend (`app_v2/services/`, `app_v2/routers/`) diff for the three task
  commits is empty — render-layer-only swap honored.
