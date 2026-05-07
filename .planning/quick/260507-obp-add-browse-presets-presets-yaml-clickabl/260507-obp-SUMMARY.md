---
task: 260507-obp
type: quick
description: Add named filter presets to the Overview (Joint Validation) page — config/presets.yaml + clickable chips above the active-filter summary that OVERRIDE current filter selection via HTMX OOB swap
date: 2026-05-07
duration: ~25min
tasks_completed: 4
files_changed:
  created:
    - config/presets.example.yaml
    - app_v2/services/preset_store.py
    - tests/v2/test_overview_presets.py
  modified:
    - .gitignore
    - app_v2/routers/overview.py
    - app_v2/templates/overview/index.html
    - app_v2/static/css/app.css
    - tests/v2/test_joint_validation_routes.py   # Rule 1 auto-fix (collision with new .ff-preset-chip)
commits:
  - fcbcdf8 — Task 1: preset_store.py + config/presets.example.yaml seed
  - 5f45390 — Task 2: GET /overview/preset/{name} route + thread presets into ctx
  - 631234e — Task 3: render preset chip strip + .ff-preset-* CSS (incl. Rule 1 test fix)
  - 095ab9a — Task 4: tests/v2/test_overview_presets.py — 9 tests
metrics:
  v2_test_count_before: 563
  v2_test_count_after: 572
  new_tests: 9
  pre_existing_skipped: 5
---

# Quick Task 260507-obp: Add filter presets to the Overview page — Summary

One-liner: YAML-backed filter presets for the Joint Validation grid; clicking a preset chip OVERRIDES the current filter selection via GET /overview/preset/{name} returning the same 4 OOB blocks (grid + count_oob + filter_badges_oob + pagination_oob) plus HX-Push-Url with the resolved canonical /overview?... URL.

## What shipped

A horizontal strip of clickable preset chips renders above the active-filter chip strip on `/overview`:

    [ Korean OEMs in progress ]  [ Qualcomm wearables ]  [ Pending UFS 4.0 ]

    Status:    [ In Progress ]
    Customer:  [ Samsung ]
    ...

Clicking a chip:

1. Fires `GET /overview/preset/{slug}` via HTMX.
2. The handler builds the JV grid view-model from the preset's filter dict (other facets default to empty lists — OVERRIDE, not additive).
3. Returns the four OOB blocks the existing POST /overview/grid path emits, so HTMX merges grid + count + active-filter chips + pagination simultaneously.
4. Sets `HX-Push-Url` to the canonical `/overview?<facet>=A&<facet>=B&...` URL so the address bar reflects the applied state and is bookmarkable.
5. Right-click → "Open in new tab" still works because the chip is an `<a href="/overview/preset/...">` (HTMX intercepts the click; the href is the fallback).

## The 3 seed presets (sampled verbatim from the live JV tree)

| Slug                         | Label                  | Filters                                                  | Why this preset                                               |
| ---------------------------- | ---------------------- | -------------------------------------------------------- | ------------------------------------------------------------- |
| `korean-oems-in-progress`    | Korean OEMs in progress | `status=[In Progress]`, `customer=[Samsung, Hyundai]`     | Multi-customer + status — exercises UNION-within-facet.        |
| `qualcomm-wearables`         | Qualcomm wearables     | `ap_company=[Qualcomm]`, `application=[Wearable]`         | Single-value across 2 facets — simplest multi-facet AND case.  |
| `pending-ufs4`               | Pending UFS 4.0        | `status=[Pending]`, `device=[UFS 4.0]`                    | Pairs status + device — exercises a third facet beyond status/customer/ap_company. |

All values verified against the `filter_options` union returned by `build_joint_validation_grid_view_model` against the live `content/joint_validation/` tree (22 JV rows total) so each preset produces a non-empty grid.

## OVERRIDE-vs-additive decision

Clicking a preset chip REPLACES the current filter selection rather than adding to it. Rationale:

- Deterministic end state — clicking "Pending UFS 4.0" always lands on `status=Pending & device=UFS 4.0`, regardless of what the user had selected before. Removes the "did this preset add to my filters or replace them?" ambiguity.
- The handler intentionally does NOT read filter query params from the request — the preset's `filters` dict is the entire filter state.
- Test `test_get_overview_preset_clicked_after_existing_filters_overrides_them` pins this: sending stray `?status=Cancelled&customer=Apple` to `/overview/preset/qualcomm-wearables` produces an HX-Push-Url that contains ONLY `ap_company=Qualcomm&application=Wearable` — no status/customer bleed-through.

## Loader contract (preset_store.py)

Mirrors `starter_prompts.py` deliberately:

- Fallback chain: `config/presets.yaml` (gitignored, user-local) → `config/presets.example.yaml` (committed) → `[]`.
- `yaml.safe_load` discipline (T-05-02-01).
- Per-entry validation:
  - Top-level YAML not a list → `[]`.
  - Entry not a mapping → drop.
  - Missing/empty `name` or `label` → drop.
  - `filters` missing or not a dict → drop.
  - ANY filters key not in `FILTERABLE_COLUMNS` → drop the WHOLE entry (a typoed facet means a broken preset).
  - ANY filters value not a non-empty list of non-empty strings → drop.
- Logs each rejection at WARNING; never raises.
- No caching (matches `starter_prompts.py` rationale — called rarely, keeps live edits visible without restart).

## Visual / styling decisions

- New `.ff-preset-row` + `.ff-preset-chip` rules sibling the existing `.ff-*` family from 260507-nzp (NOT extend). Same chip size/radius/font; new rule layers on the interactive treatment.
- Single neutral hue for ALL preset chips — color is NOT used to differentiate presets (the label text differentiates). Visually distinct from the per-facet `.c-1..c-6` palette so users read the preset row as "actions" (clickable) and the active-filter row below as "state" (passive).
- Hover/focus uses `--accent-soft` / `--accent` / `--accent-ink` to anchor preset chips to Dashboard_v2's primary-action affordance (matches the .btn-helix primary-button hue).
- 1px border on preset chips (NOT on `.ff-chip.c-N` value chips) — the border + hover-ink change signals affordance; passive value chips intentionally have no border.
- No new tokens added to `tokens.css`.
- Strip is hidden entirely when `presets` is empty (no YAML file or all entries malformed) — no empty container claiming vertical space.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assertion collision with new `.ff-preset-chip` base class**
- **Found during:** Task 3 verification (`pytest tests/v2/test_joint_validation_routes.py`).
- **Issue:** `test_overview_filter_chips_no_active_filters_renders_empty_wrapper` asserted `"ff-chip" not in r.text` to prove no active-filter chips render when no filters are selected. The new preset-chip strip uses `class="ff-chip ff-preset-chip"` so the bare substring is now always present, breaking the assertion even though the test's contract (no ACTIVE-filter chips) still holds.
- **Fix:** Tightened the assertion to probe the unambiguous markers — the per-facet color variants `.c-1..c-6`. `.ff-preset-chip` never gets a `c-N` variant, so the contract intent is preserved and the assertion now distinguishes the two chip families. Documented the decision in the test docstring.
- **Files modified:** `tests/v2/test_joint_validation_routes.py`.
- **Commit:** 631234e (folded into Task 3 commit since it's the surface that introduced the collision).

### Lint step skipped

The plan's verification block lists `.venv/bin/ruff check ...`. Ruff is not installed in this venv (no `.venv/bin/ruff`, no `ruff` module). Not a blocker — the project has no `ruff` in `requirements.txt` and other quick tasks have proceeded without it. The 572-test suite + 9 new tests + manual snapshot inspection cover the change.

## Manual UAT observation

No dev server available; used TestClient HTML snapshot fallback (allowed by plan). Verified the live `/overview` response contains the 3-chip strip with the expected `hx-get`/`href`/`hx-push-url`/`data-preset` wiring above the existing `#overview-filter-badges` block. `HX-Push-Url` for `/overview/preset/qualcomm-wearables` resolves to `/overview?ap_company=Qualcomm&application=Wearable&sort=start&order=desc`.

Snippet captured (truncated):

```html
<div class="ff-preset-row px-3 pt-2" id="overview-preset-row" aria-label="Filter presets">
  <span class="ff-label">Presets:</span>
  <a class="ff-chip ff-preset-chip"
     href="/overview/preset/korean-oems-in-progress"
     hx-get="/overview/preset/korean-oems-in-progress"
     hx-target="#overview-grid"
     hx-swap="outerHTML"
     hx-push-url="true"
     data-preset="korean-oems-in-progress">
    Korean OEMs in progress
  </a>
  ... (Qualcomm wearables, Pending UFS 4.0)
</div>
```

## Verification

| Step | Result |
| ---- | ------ |
| `test -f config/presets.example.yaml` + slug grep | PASS |
| `config/presets.yaml` in `.gitignore` | PASS |
| `load_presets()` returns 3 from project root | PASS |
| `GET /overview/preset/qualcomm-wearables` returns 200 + correct HX-Push-Url | PASS |
| `GET /overview/preset/no-such-thing` returns 404 | PASS |
| `GET /overview` renders the 3-chip strip with hx-* wiring | PASS |
| OOB target ids byte-stable (filter_badges=1, pagination=2, count_oob=2) | PASS |
| `tests/v2/test_overview_presets.py` (9 new) | 9 passed |
| `tests/v2/test_joint_validation_routes.py` (existing) | 20 passed |
| Full v2 suite | 572 passed, 5 skipped |
| Backend services untouched (`git diff --stat app_v2/services/joint_validation_*.py`) | empty diff |
| CSS append-only (`git diff app.css \| grep ^-`) | empty (no removed lines) |

## Self-Check: PASSED

- [x] FOUND: config/presets.example.yaml
- [x] FOUND: app_v2/services/preset_store.py
- [x] FOUND: tests/v2/test_overview_presets.py
- [x] FOUND: commit fcbcdf8
- [x] FOUND: commit 5f45390
- [x] FOUND: commit 631234e
- [x] FOUND: commit 095ab9a
