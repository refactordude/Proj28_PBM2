---
quick_id: 260429-ek7
plan: 01
status: complete
files_modified:
  - app_v2/templates/overview/_grid.html
commits:
  - 4fed64d
human_uat:
  status: pending
  items:
    - "Load /overview in browser; confirm active Link button shows chain icon (🔗) with near-black text, matching the AI button's geometric shape."
    - "Confirm row without `link:` frontmatter shows the lighter disabled outlined state (text-muted), same geometry."
---

# Quick Task 260429-ek7 — Restyle Link Button to Match AI Button

## Outcome

Two-line template edit + comment update in `app_v2/templates/overview/_grid.html`.
The Link button and AI button now read as a matched outlined/ghost pair:

| State | Icon | Text color | Geometry |
|---|---|---|---|
| Active Link | `bi-link-45deg` (chain) + `text-dark` | near-black via `text-dark` | `btn btn-sm btn-outline-secondary me-1` |
| Disabled Link | `bi-link-45deg` + `text-muted` (unchanged) | muted grey via `text-muted` | `btn btn-sm btn-outline-secondary disabled me-1` |
| AI button | ✨ emoji | Bootstrap secondary default | `btn btn-sm btn-outline-secondary` |

All three share the same Bootstrap geometry (border-radius, padding, height) so the
Actions cell now reads as a visually consistent button group.

## Changes

**File:** `app_v2/templates/overview/_grid.html`

1. Active branch (`{% if row.link %}`):
   - Icon: `bi bi-box-arrow-up-right` → `bi bi-link-45deg text-dark`
   - Label: bare `Link` text → `<span class="text-dark">Link</span>`
2. Comment block above lines 62-68: added 5 lines documenting that the visual
   treatment matches the AI button (outlined ghost, dark active state, muted disabled).
3. Disabled branch (`{% else %}`): unchanged.
4. AI button block (lines 89-102 prior to edit): unchanged.

## Commits

- `4fed64d` — fix(quick-260429-ek7): restyle Link button to match AI button visual treatment

## Verification

- ✅ `grep -F 'bi bi-link-45deg text-dark' app_v2/templates/overview/_grid.html` → 1 hit
- ✅ `grep -F '<span class="text-dark">Link</span>' app_v2/templates/overview/_grid.html` → 1 hit
- ✅ `grep -F 'bi-box-arrow-up-right' app_v2/templates/overview/_grid.html` → 0 hits (icon removed)
- ✅ Disabled-branch `bi bi-link-45deg text-muted` still present → 1 hit
- ✅ Both `<a class="btn btn-sm btn-outline-secondary` lines still present → 2 hits
- ⏳ Browser HUMAN-UAT — pending user visual confirmation

## Notes

Executed inline rather than via gsd-executor agent due to API rate limit reached
during gsd-planner spawn. PLAN.md was successfully written by gsd-planner before
the limit; the inline implementation matches the plan exactly.
