---
quick_id: 260507-l5w
type: quick
status: complete
completed: 2026-05-04
commit: 790d2a9
files_modified:
  - app_v2/templates/overview/_grid.html
tests:
  baseline: 546
  result: 546 passed, 5 skipped
requirements:
  - QUICK-260507-l5w
references:
  - .planning/quick/260429-ek7-restyle-active-state-link-button-in-over/260429-ek7-SUMMARY.md
---

# Quick 260507-l5w — JV Link Button: relabel `Link` → `edm`, restore active-state contrast

## One-liner

Two-line cosmetic edit to the JV grid Report Link button: relabel `Link` → `edm` (lowercase, both branches) and append `text-dark` to the active-branch class so it reads near-black against the muted disabled outline-secondary state.

## Files Modified

| File | Change |
| ---- | ------ |
| `app_v2/templates/overview/_grid.html` | Active branch: class `btn btn-sm btn-outline-secondary` → `btn btn-sm btn-outline-secondary text-dark`; label `Link` → `edm`. Disabled branch: label `Link` → `edm` (class unchanged). |

Diff stat: `1 file changed, 3 insertions(+), 3 deletions(-)`.

## Edits Applied

**Active branch (`{% if row.link %}`, lines 57-63):**
```diff
-               class="btn btn-sm btn-outline-secondary"
+               class="btn btn-sm btn-outline-secondary text-dark"
                target="_blank" rel="noopener noreferrer"
                aria-label="Open report link for {{ row.title | e }}">
-             <i class="bi bi-link-45deg"></i> Link
+             <i class="bi bi-link-45deg"></i> edm
```

**Disabled branch (`{% else %}`, lines 64-70):**
```diff
              <button type="button"
                      class="btn btn-sm btn-outline-secondary"
                      disabled
                      aria-label="No report link available">
-               <i class="bi bi-link-45deg"></i> Link
+               <i class="bi bi-link-45deg"></i> edm
              </button>
```

`aria-label` attributes preserved on both branches (screen readers still hear "Open report link for …" / "No report link available", not the bare `edm` acronym). Icon (`bi bi-link-45deg`) and surrounding HTMX/Jinja chrome unchanged.

## Verification Outputs

All seven plan-defined grep checks pass:

| # | Check | Expected | Actual |
| - | ----- | -------- | ------ |
| 1 | `class="btn btn-sm btn-outline-secondary text-dark"` count in `_grid.html` | 1 | 1 |
| 2 | `<i class="bi bi-link-45deg"></i> edm` count in `_grid.html` | 2 | 2 |
| 3 | `<i class="bi bi-link-45deg"></i> Link` count in `_grid.html` (legacy) | 0 | 0 |
| 4 | `class="btn btn-sm btn-outline-secondary"$` count (disabled branch, EOL anchor) | 1 | 1 |
| 5 | `<th>Report Link</th>` count in `joint_validation/detail.html` (out-of-scope byte-stability) | 1 | 1 |
| 6 | `aria-label="Open report link for` count in `_grid.html` | 1 | 1 |
| 7 | `aria-label="No report link available"` count in `_grid.html` | 1 | 1 |

**v2 test suite:** `.venv/bin/python -m pytest tests/v2/ -x -q`

```
546 passed, 5 skipped, 2 warnings in 31.38s
```

Result matches the planning baseline (546 passing). Zero test edits required — confirmed by the plan's `grep '> Link\|>Link<'` sweep against `tests/v2/`.

**Out-of-scope file confirmation:** `git status --short` after edit reported only ` M app_v2/templates/overview/_grid.html`. `app_v2/templates/joint_validation/detail.html` is byte-stable (the `<th>Report Link</th>` cell at line 35 and the inline anchor at line 41 remain untouched, per Check 5).

## Reference / Precedent

Restores the visual pattern shipped in quick task **260429-ek7** (`.planning/quick/260429-ek7-restyle-active-state-link-button-in-over/`, commit `4fed64d`), which the user approved on 2026-04-29. That `text-dark`-on-active treatment was inadvertently dropped when commit `52bddfc` rewrote `_grid.html` from scratch for the JV grid pivot (Phase 1 Plan 05). The `edm` label is a new, user-supplied internal acronym (likely an EDM/Confluence tool reference); preserved verbatim, lowercase, no expansion.

## Deviations from Plan

None — plan executed exactly as written. No Rule 1/2/3 auto-fixes triggered; no architectural questions raised.

## HUMAN-UAT Pending

- [ ] Load the JV listing page in the browser (`/`); confirm:
  - Rows with a valid `link:` frontmatter render the active **`edm`** button in clearly near-black ink.
  - Rows without `link:` (or with a sanitizer-rejected scheme) render the disabled **`edm`** button in washed-out grey.
  - The two states are visually discernible at a glance, without needing to hover or read the cursor.
- [ ] Confirm `/joint_validation/<page_id>` detail page still renders the `Report Link` properties row unchanged (out-of-scope file should be visually identical).

## Self-Check: PASSED

- File `app_v2/templates/overview/_grid.html` exists and contains the new edits — confirmed via Read at lines 54-71.
- Commit `790d2a9` exists in `git log` for branch `ui-improvement`.
- No other files staged/modified by this task.
