---
phase: 04-ui-foundation-helix-aligned-shell-primitives-build-reusable-
fixed_at: 2026-05-03T20:30:00Z
review_path: .planning/phases/04-ui-foundation-helix-aligned-shell-primitives-build-reusable-/04-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 4: Code Review Fix Report

**Fixed at:** 2026-05-03T20:30:00Z
**Source review:** `.planning/phases/04-ui-foundation-helix-aligned-shell-primitives-build-reusable-/04-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (Critical 0 + Warning 4; Info findings excluded per fix_scope=critical_warning)
- Fixed: 4
- Skipped: 0
- Test result: 542 passed / 5 skipped (baseline 541 passed + 1 new test for empty FilterOption value rejection)

## Fixed Issues

### WR-01: `page_head(actions_html=...)` is a `| safe` foot-gun

**Files modified:** `app_v2/templates/_components/page_head.html`, `app_v2/templates/_components/showcase.html`
**Commit:** c97c46b
**Applied fix:** Replaced the `actions_html=""` keyword argument and `{{ actions_html | safe }}` rendering with a Jinja `{% call %}` block. The macro now renders `{{ caller() }}` only when the caller passes content, and the showcase's "With actions" example uses `{% call page_head(...) %}<button>...</button>{% endcall %}`. Content inside the call block is rendered in the calling template's autoescape context, so `{{ var }}` interpolations are HTML-escaped automatically. The XSS foot-gun (any future caller passing user/DB-derived content via the raw-HTML slot) is structurally eliminated.

### WR-02: Reset link in popovers had no preventDefault and no handler

**Files modified:** `app_v2/templates/_components/date_range_popover.html`, `app_v2/templates/_components/filters_popover.html`, `app_v2/static/js/chip-toggle.js`, `tests/v2/test_phase04_uif_components.py`
**Commit:** 112f2d8 (combined with WR-03 — see note below)
**Applied fix:** (a) Replaced `<a href="#" data-action="reset">Reset</a>` in both popovers with `<button type="button" class="pop-reset-link" data-action="reset">…</button>`, eliminating the browser-default navigation to `#`. (b) Added `onResetClick(e)` to chip-toggle.js: it locates the enclosing `.pop`, removes `.on` from every chip, clears every hidden input with a `data-opt` attribute, and zeroes every `input[type=date]`. Skips clicks inside `.popover-search-root` to preserve the D-UI2-09 byte-stable boundary. (c) Test assertions added to confirm `data-action="reset"` is present and the legacy `<a href="#">` form is gone.

### WR-03: Quick-chip "active" state stubbed — quick chips do nothing

**Files modified:** `app_v2/templates/_components/date_range_popover.html`, `tests/v2/test_phase04_uif_components.py`
**Commit:** 112f2d8 (combined with WR-02 — same files touched)
**Applied fix:** Removed the dead `<div class="qrow">…<button data-quick-days="N">Nd</button>…</div>` row from the date-range popover macro and dropped the `quick_days` keyword argument from the macro signature. Updated the macro docstring to flag that quick-range chips were removed pending a real handler, and to document that re-adding requires JS to read `data-quick-days` and populate the date inputs. Updated the showcase test to assert `class="qrow"` and `data-quick-days=` are NOT in the response — re-add the assertions only when a quick-range handler ships.

**Note on combined commit:** WR-02 and WR-03 were committed together (112f2d8) because both findings cite `date_range_popover.html` and the two changes are interleaved in the same template — splitting one file's hunks across two commits would have required awkward partial staging. The commit message and this report attribute the change to both findings explicitly.

### WR-04: chip-toggle.js conflated `value === ''` with OFF — empty-string options break

**Files modified:** `app_v2/services/filter_spec.py`, `app_v2/static/js/chip-toggle.js`, `app_v2/templates/_components/filters_popover.html`, `tests/v2/test_phase04_uif_hero_spec.py`
**Commit:** 00434aa
**Applied fix:** Three coordinated changes: (a) `FilterOption.value` is now `Field(min_length=1)` so empty values are rejected at construction time. Added a unit test (`test_filter_option_empty_value_raises`) that exercises the validator. (b) `chip-toggle.js` no longer overloads the hidden input's `value` to encode ON/OFF. ON sets `value=chipValue` and `disabled=false`; OFF sets `disabled=true` so the browser excludes the input from form submission per HTML spec. The reset handler also disables hidden inputs (instead of clearing values). (c) `filters_popover.html` server-renders the hidden input with the chip's value always populated and adds the `disabled` attribute when `not opt.on`, mirroring the JS contract.

This change is a candidate for human verification: the JS+template+model trio is internally consistent and unit-tested, but the end-to-end "form submission omits OFF chips" semantics depend on browser behavior that isn't exercised by the current test suite. Recommend manual spot-check via `/_components` once a route consumes filter_groups for real.

## Verification

- Tier 1: All modified files re-read after edits; fix text confirmed present, surrounding code intact.
- Tier 2: `node -c app_v2/static/js/chip-toggle.js` → syntax OK. `python ast.parse` on `app_v2/services/filter_spec.py` → syntax OK.
- Tier 3: Phase 4 UIF tests (`test_phase04_uif_components.py` + `test_phase04_uif_invariants.py` + `test_phase04_uif_hero_spec.py`) → 51 passed. Full v2 suite (`pytest tests/v2/ -q`) → 542 passed / 5 skipped (baseline was 541 passed; +1 new test for empty FilterOption value). No regressions.

---

_Fixed: 2026-05-03T20:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
