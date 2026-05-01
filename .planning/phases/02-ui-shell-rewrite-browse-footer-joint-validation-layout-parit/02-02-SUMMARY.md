---
phase: 02-ui-shell-rewrite-browse-footer-joint-validation-layout-parit
plan: "02"
subsystem: ui-browse-footer
tags: [htmx, footer, oob-swap, tdd, browse, template]
requires: [02-01]
provides: [browse-count-in-footer, grid-count-oob-stable]
affects:
  - app_v2/templates/browse/index.html
  - tests/v2/test_phase02_invariants.py
tech-stack:
  added: []
  patterns: [htmx-oob-merge-by-id, jinja2-block-outside-content, tdd-grep-invariants]
key-files:
  created: []
  modified:
    - app_v2/templates/browse/index.html
    - tests/v2/test_phase02_invariants.py
decisions:
  - "D-UI2-06: Browse count caption (#grid-count span) moved from .panel-header into {% block footer %} of browse/index.html; OOB emitter in count_oob block byte-stable; HTMX merges by id regardless of DOM location"
  - "W6 placement: {% block footer %} placed immediately after {% endblock %} closing block content (no blank/comment lines between) — comments moved inside the block to satisfy grep -B1 acceptance criteria"
  - "W7 tag alignment: receiver tag <span id='grid-count' class='text-muted small' aria-live='polite'> and emitter tag <span id='grid-count' hx-swap-oob='true' class='text-muted small' aria-live='polite'> attribute order consistent"
metrics:
  duration: "6min"
  completed: "2026-05-01"
  tasks: 1
  files: 2
---

# Phase 02 Plan 02: Browse Count Caption → Footer Summary

**One-liner:** Browse's "N platforms × M parameters" count span relocated from `.panel-header` into `{% block footer %}` with byte-stable OOB swap mechanics — HTMX still merges by id after every filter change.

---

## What Was Built

One task (TDD): migrate Browse's count caption from the panel-header right zone into the new sticky footer slot introduced by Plan 02-01.

### Three discrete template edits to `app_v2/templates/browse/index.html`:

**Edit A (panel-header cleanup):** Deleted the `<div class="ms-auto d-flex align-items-center gap-3">` wrapper and its inner `<span id="grid-count">` from `.panel-header`. The panel-header retains `<b>Browse</b>` and `<span class="tag">Pivot grid</span>` — byte-stable otherwise.

**Edit B (footer block addition):** Added `{% block footer %}...<span id="grid-count" class="text-muted small" aria-live="polite">...</span>...{% endblock footer %}` placed immediately after the `{% endblock %}` closing `block content`. Block ordering from bottom of file: `{% endblock picker_badges_oob %}` → `{% endblock %}` → `{% block footer %}...{% endblock footer %}` → `{% block params_picker_oob %}` → `{% block params_picker %}`.

**Edit C (count_oob verification):** `{% block count_oob %}` is byte-stable. The OOB emitter `<span id="grid-count" hx-swap-oob="true" class="text-muted small" aria-live="polite">` continues to target `#grid-count` — HTMX merges by id regardless of whether the receiver is in `.panel-header` or `.site-footer`.

### Six new tests (16-21) appended to `tests/v2/test_phase02_invariants.py`:

| Test | What it enforces |
|------|-----------------|
| Test 16 (`test_browse_panel_header_no_count`) | `ms-auto d-flex align-items-center gap-3` wrapper absent from template |
| Test 17 (`test_browse_footer_block_carries_count`) | `{% block footer %}` present with `#grid-count`, `vm.n_rows`, `vm.n_cols`, `&times;` |
| Test 17b (`test_browse_grid_count_receiver_emitter_tag_alignment`) | W7: receiver and emitter opening tags are attribute-order-consistent (exactly 1 each) |
| Test 18 (`test_browse_count_oob_unchanged`) | `{% block count_oob %}` byte-stable with `hx-swap-oob="true"` + `vm.is_empty_selection` guard |
| Test 19 (`test_get_browse_renders_count_in_footer`) | GET /browse: `#grid-count` appears inside `<footer class="site-footer">` in rendered HTML |
| Test 20 (`test_post_browse_grid_emits_count_oob`) | POST /browse/grid: response contains `id="grid-count"` + `hx-swap-oob="true"` (OOB still emitted) |
| Test 21 (`test_browse_panel_header_byte_stable_otherwise`) | `<b>Browse</b>` and `<span class="tag">Pivot grid</span>` still in template |

---

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 80136af | test | add failing tests for browse count footer migration (RED) |
| fcc4e18 | feat | migrate Browse count caption from panel-header into footer (D-UI2-06) |

---

## Verification Results

- All 47 tests pass: 21 invariants (15 from Plan 02-01 + 6 new) + 26 browse routes tests.
- Zero regressions from the 02-01 baseline.
- All acceptance greps pass:
  - `grep -c 'class="ms-auto d-flex align-items-center gap-3"' ...` → `0`
  - `grep -c '{% block footer %}' ...` → `1`
  - `grep -c '{% endblock footer %}' ...` → `1`
  - `grep -c 'id="grid-count"' ...` → `2` (one receiver in footer, one emitter in count_oob)
  - `grep -c '<b>Browse</b>' ...` → `1`
  - `grep -c '<span class="tag">Pivot grid</span>' ...` → `1`
  - `grep -B1 '{% block footer %}' ...` → line above is `{% endblock %}` (W6)
  - `grep -B1 '{% block params_picker_oob %}' ...` → line above is `{% endblock footer %}` (W6)
  - receiver tag count → `1` (W7)
  - emitter tag count → `1` (W7)

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Comments inside template file matched `grep -c 'id="grid-count"'` criterion**
- **Found during:** GREEN acceptance grep verification
- **Issue:** Two comment lines (one in count_oob preamble, one in the new footer block preamble) contained the exact string `id="grid-count"`, making the grep count return 4 instead of the required 2.
- **Fix 1:** Rewrote the count_oob preamble comment to use `#grid-count span` instead of `<span id="grid-count">`.
- **Fix 2:** Moved the footer block preamble comment inside `{% block footer %}` (so it's counted as part of the block content, not a separator between blocks).
- **Side effect:** This also resolved W6 placement — `{% block footer %}` now immediately follows `{% endblock %}` with no intervening lines, satisfying `grep -B1` checks.
- **Files modified:** `app_v2/templates/browse/index.html`
- **Commit:** fcc4e18

**2. [Rule 1 - Bug] W6: comment between {% endblock footer %} and {% block params_picker_oob %}**
- **Found during:** GREEN W6 placement check
- **Issue:** Same pattern — the comment preamble for `params_picker_oob` sat between `{% endblock footer %}` and `{% block params_picker_oob %}`, breaking the `grep -B1` acceptance criterion.
- **Fix:** Moved the comment inside `{% block params_picker_oob %}` so the block directive immediately follows `{% endblock footer %}`.
- **Files modified:** `app_v2/templates/browse/index.html`
- **Commit:** fcc4e18

---

## Known Stubs

None — the count caption renders real data from `vm.n_rows` and `vm.n_cols`. The `vm.is_empty_selection` conditional is the existing contract (shows nothing when no selection). No stubs or placeholder text introduced.

---

## Threat Surface Scan

No new trust boundaries. The `#grid-count` span renders integers (`vm.n_rows`, `vm.n_cols`) through Jinja's autoescape — no new XSS surface. The receiver moved in DOM from panel-header to site-footer; the OOB emitter is unchanged. This matches T-02-02-01 through T-02-02-04 in the plan's threat model — all mitigations in place.

---

## Self-Check: PASSED

Files exist:
- `app_v2/templates/browse/index.html` — FOUND
- `tests/v2/test_phase02_invariants.py` — FOUND

Commits exist:
- 80136af — FOUND (test RED commit)
- fcc4e18 — FOUND (feat GREEN commit)
