---
task: 260507-r0k
type: quick
description: Add named filter presets to the Browse (Pivot grid) page — config/browse_presets.yaml + clickable chips above the filter bar that OVERRIDE current platforms+params selection via HTMX OOB swap. Mirrors 260507-obp pattern, adapted to Browse's distinct filter shape (platforms + params + swap_axes, NOT the JV 6-facet model).
status: complete
date: 2026-05-07
tags: [browse, presets, htmx, oob, yaml, override]
commits:
  - d959b76  # feat(browse): add browse_preset_store + browse_presets.example.yaml seed
  - 5bbc103  # feat(browse): add GET /browse/preset/{name} route + thread presets into ctx
  - 10488ce  # feat(browse): render preset chip strip above filter bar
  - 1fc7fbc  # test(browse): add tests/v2/test_browse_presets.py — 9 tests
files_created:
  - config/browse_presets.example.yaml
  - app_v2/services/browse_preset_store.py
  - tests/v2/test_browse_presets.py
files_modified:
  - .gitignore
  - app_v2/routers/browse.py
  - app_v2/templates/browse/index.html
files_unchanged:
  - app_v2/static/css/app.css           # CSS REUSE only — .ff-preset-row + .ff-preset-chip rules from 260507-obp
  - app_v2/services/browse_service.py   # backend untouched
  - app_v2/services/preset_store.py     # Overview loader untouched
  - app_v2/services/joint_validation_grid_service.py
  - app_v2/services/cache.py
metrics:
  tasks: 4
  duration_min: 8
  tests_added: 9
  tests_total_v2: 581
  tests_skipped_v2: 5
---

# Quick Task 260507-r0k: Add filter presets to the Browse page

One-liner: **Browse-page filter presets via `config/browse_presets.yaml` + clickable chip strip above the filter bar that OVERRIDES current platforms+params+swap_axes selection through a `GET /browse/preset/{name}` route returning 5 OOB blocks (grid + count_oob + warnings_oob + picker_badges_oob + params_picker_oob) and HX-Push-Url with the canonical URL.**

## Summary

Added a Browse-page mirror of the Overview presets feature (260507-obp), adapted to Browse's distinct filter shape (2-list `platforms` + `params` + `swap_axes` bool, vs Overview's 6-facet whitelist). Three seed presets with verbatim values sampled from `data/demo_ufs.db` on 2026-05-07 ship in the committed `config/browse_presets.example.yaml`. Each chip click issues an HTMX `GET /browse/preset/<slug>` that resolves to a fully-deterministic filter state (clears + replaces; never additive) and refreshes the grid + count + picker badges + Parameters picker slot together via the existing OOB merge-by-id mechanism. URL bar reflects the canonical `/browse?platforms=…&params=…` so the state is bookmarkable.

## Files Changed

| File | Action | LOC | Purpose |
|------|--------|-----|---------|
| `config/browse_presets.example.yaml` | NEW | ~50 | 3 seed presets (snapdragon-flagships / exynos-lineup / auto-iot-specials) sampled verbatim from `data/demo_ufs.db` |
| `.gitignore` | MOD | +1 | Add `config/browse_presets.yaml` (user-local override) |
| `app_v2/services/browse_preset_store.py` | NEW | 159 | `load_browse_presets()` with YAML fallback chain + per-entry validation + log-and-skip on malformed |
| `app_v2/routers/browse.py` | MOD | +95 / -2 | New `GET /browse/preset/{name}` route + thread `presets` into existing GET/POST contexts |
| `app_v2/templates/browse/index.html` | MOD | +32 | `{% if presets %}` strip rendered AFTER empty form, BEFORE `_filter_bar.html` |
| `tests/v2/test_browse_presets.py` | NEW | 330 | 9 tests mirroring `test_overview_presets.py` shape |

## Seed Presets (verbatim, sampled from `data/demo_ufs.db` 2026-05-07)

| Slug | Label | Platforms | Params | swap_axes |
|------|-------|-----------|--------|-----------|
| `snapdragon-flagships` | Snapdragon flagships | SM8550_rev1, SM8650_v1, SM8650_v2, SM8850_v1 | VendorInfo · ManufacturerName, GeometryDescriptor · RawDeviceCapacity | false |
| `exynos-lineup` | Exynos lineup | EXYNOS1380_c, EXYNOS2200_b, EXYNOS2400_a | DeviceInfo · bDeviceVersion, DeviceInfo · NumberOfLU | false |
| `auto-iot-specials` | Auto + IoT specials | SC8275_auto, QCS6490_iot | AutomotiveProfile · QualGradeLevel, IoTPowerProfile · DeepSleepCurrentUA, VendorInfo · ManufacturerName | **true** |

**Why these three:** the first demonstrates the default rows=platforms layout with multi-platform × multi-param shape; the second exercises two params from the same `InfoCategory` (catalog ordering check); the third uses `swap_axes: true` and partial intersections (Auto + IoT category-specific params) to demonstrate em-dash placeholders for missing pivot cells. Each preset's platforms × params intersection was verified non-empty against the demo DB at planning time.

## Decisions Made

### 1. OVERRIDE semantics (not additive)

Preset click clears the entire filter state and replaces it with the preset's `platforms` / `params` / `swap_axes`. Stray query params on the preset GET (e.g. user had existing filters in the URL when clicking) are deliberately **ignored** — pinned by `test_get_browse_preset_clicked_after_existing_filters_overrides_them`. Avoids the "did this preset add to my filters or replace them?" ambiguity. Same contract as 260507-obp.

### 2. Sibling YAML file (NOT a shared namespace with Overview presets)

`config/browse_presets.example.yaml` is a sibling to `config/presets.example.yaml`, not an extension of it. Justification:

- Overview's `preset_store.py` imports `FILTERABLE_COLUMNS` from `joint_validation_grid_service` and rejects entries whose facet keys aren't in that whitelist — a JV-shape-specific validator.
- Browse facets (`platforms`, `params`, `swap_axes`) are not in `FILTERABLE_COLUMNS`, so generalizing the existing loader would force schema-aware branching or a parameterized whitelist (intrusive churn on 9 already-shipped tests).
- Sibling files keep both loaders single-purpose and let each iterate independently.

Cost: one extra ~160 LOC module (`browse_preset_store.py`) that mirrors `preset_store.py`'s structure and docstrings.

### 3. CSS reuse (NO new rules)

The `.ff-preset-row` and `.ff-preset-chip` rules already shipped in 260507-obp at `app_v2/static/css/app.css` lines 1213-1251. Browse simply adopts them — `git diff app_v2/static/css/app.css` is empty. Each rule still appears exactly once in `app.css`.

### 4. GET (not POST) for `/browse/preset/{name}`

- Idempotent — repeated clicks land on the same state.
- `hx-push-url="true"` with GET produces a clean shareable URL in the address bar.
- Test ergonomics — `client.get(...)` is simpler than form-encoded POST.

### 5. `<a href="/browse/preset/...">` (not `<button>`)

- Right-click → "Open in new tab" works (the new tab spawns a fresh GET that renders the full `/browse` page filtered by the preset — useful for sharing).
- Graceful degradation if HTMX fails to load: the link still navigates.
- HTMX `hx-get` on an `<a>` intercepts the click; `href` is the fallback.

### 6. `hx-swap="innerHTML"` (differs from Overview)

Browse's grid target `#browse-grid` is a `<div>` whose inner content is what changes (the `{% block grid %}`). Overview uses `outerHTML` because the entire wrapper is replaced. Following the existing `POST /browse/grid` swap pattern keeps the swap mechanism byte-stable.

### 7. Always include `params_picker_oob` (no origin check)

A preset click is unambiguously NOT a Parameters-popover toggle — there is no `_origin=params` form field on a preset GET. Preset apply changes the platforms set, which changes the platforms-filtered parameter catalog (per 260429-qyv); the picker MUST re-render or the Parameters popover would show a stale catalog after click.

### 8. 404 (not 422) on unknown preset

Semantically "the browse preset named X" does not exist as a resource. Keeps log filtering simple. Same as 260507-obp.

## Verification

Plan-level checks (all green):

- Loader smoke: `load_browse_presets()` returns 3 entries.
- Route smoke: `GET /browse/preset/snapdragon-flagships` returns 200 with `HX-Push-Url: /browse?platforms=SM8550_rev1&platforms=SM8650_v1&platforms=SM8650_v2&platforms=SM8850_v1&params=VendorInfo%20%C2%B7%20ManufacturerName&params=GeometryDescriptor%20%C2%B7%20RawDeviceCapacity` (no `swap=` because `swap_axes=False`).
- `auto-iot-specials` carries `swap=1` in the URL.
- Backend untouched: zero diff to `browse_service.py`, `preset_store.py`, `joint_validation_grid_service.py`, `cache.py`.
- CSS unmodified: zero diff to `app_v2/static/css/app.css`.
- Existing OOB target ids byte-stable: `grid-count`=2, `picker-platforms-badge`=1, `picker-params-badge`=1, `params-picker-slot`=2, `browse-grid`=1.
- New marker `browse-preset-row` appears exactly once.

Test suite: **`pytest tests/v2/`** → **581 passed, 5 skipped** (572 prior + 9 new — exactly matches plan expectation).

## Deviations from Plan

None — plan executed byte-for-byte as written. The 4-commit per-task granularity matched 260507-obp's pattern (which the plan explicitly recommended). No auto-fix needed (no Rule 1/2/3 deviations). No checkpoints (`type="auto"` only). No CLAUDE.md conflict.

Note: After Task 4's commit, the runtime emitted a `reset` to `HEAD~1` (likely a hook), leaving the test file staged. Re-committed it (final hash `1fc7fbc`) — content is byte-identical to the original commit message. All 4 task commits are present in the linear branch history.

## Manual UI Observation (representative TestClient snapshot)

`GET /browse` renders the strip above `.browse-filter-bar` with the 3 preset chips (`Snapdragon flagships`, `Exynos lineup`, `Auto + IoT specials`). Each `<a class="ff-chip ff-preset-chip">` carries `href`, `hx-get`, `hx-target="#browse-grid"`, `hx-swap="innerHTML"`, `hx-push-url="true"`, `data-preset="<slug>"`. The strip line index precedes the filter bar line index (asserted in `test_get_browse_renders_preset_chip_strip`).

`GET /browse/preset/snapdragon-flagships` returns the 5 OOB block fragments (no `<html>` shell, no navbar). The pivot table is present (`pivot-table` selector matches), `id="grid-count"`, `id="picker-platforms-badge"`, `id="picker-params-badge"`, `id="params-picker-slot"` are all present with `hx-swap-oob="true"`. `HX-Push-Url` matches the canonical URL with repeated `platforms=` keys + URL-encoded params.

Live dev server smoke test deferred to the orchestrator (server is running on http://100.98.86.48:8000 with `--reload`).

## Self-Check: PASSED

**Files exist:**
- FOUND: config/browse_presets.example.yaml
- FOUND: app_v2/services/browse_preset_store.py
- FOUND: tests/v2/test_browse_presets.py

**Commits exist (linear):**
- FOUND: d959b76 (feat: loader + seed YAML)
- FOUND: 5bbc103 (feat: route + ctx threading)
- FOUND: 10488ce (feat: template render)
- FOUND: 1fc7fbc (test: 9 new tests)
