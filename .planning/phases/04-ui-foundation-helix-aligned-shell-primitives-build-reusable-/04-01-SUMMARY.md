---
phase: 04-ui-foundation-helix-aligned-shell-primitives-build-reusable
plan: 01
subsystem: ui
tags: [css, jinja2, bootstrap5, helix-design-language, fonts, primitives]

# Dependency graph
requires:
  - phase: 02-ui-shell-rewrite-browse-footer-joint-validation-layout-parity
    provides: tokens.css (D-UI2-04 type scale), .panel/.panel-header/.panel-footer rules, .navbar { padding: 16px 0 } rule, .page-head/.page-title/.page-sub/.page-actions rules
  - phase: 03-overhaul-ask-feature-into-multi-step-agentic-chat-replace-on
    provides: chat surface CSS (.chat-* rules), .ai-chip rule, .btn-stop rule
provides:
  - Phase 4 CSS foundation — every Helix primitive class needed by Wave 2 macros and Wave 4 showcase
  - Google Fonts loaded (Inter Tight 400/500/600/700/800 + JetBrains Mono 400/500/600) so .page-title font-weight 800 renders correctly
  - .ph as new shell selector (D-UIF-01 rename path, additive — existing .panel-header rules untouched in Wave 1)
  - .topbar / .brand / .brand-mark / .av / .top-right primitives ready for Wave 3 base.html topbar swap
  - .tabs / .tab / .tab[aria-selected="true"] / .tab .count primitives ready for Wave 3
  - .hero / .hero-bar / .hero .side primitives ready for Wave 4 showcase + future Platform BM page
  - .kpis / .kpis.five / .kpi / .kpi .spark grid primitives ready for Wave 4
  - .pop / .pop-wrap / .pop-head / .pop .qrow / .pop .dates / .pop .grp / .pop .opts / .pop .opt[.on] popover infrastructure ready for Wave 2 date_range_popover.html and filters_popover.html macros
  - .st / .pill status pill primitives + .typ / .oemchip / .ufschip / .lnk inline-chip primitives
  - .tiny-chip with five tone variants (.ok / .info / .warn / .neutral / .err)
  - .table-sticky-corner with z-index ladder (corner=3, thead=2, first-col=1) and explicit backgrounds (Pitfall 5 mitigated)
  - .btn-helix namespaced primary button (.sm / .ghost variants) — co-exists with Bootstrap .btn without collision
affects:
  - Wave 2 Jinja macros under app_v2/templates/_components/ (topbar.html, page_head.html, hero.html, kpi_card.html, sparkline.html, date_range_popover.html, filters_popover.html) — bind to these classes
  - Wave 3 base.html topbar swap — replaces <nav class="navbar"> with topbar() macro that uses .topbar / .brand / .tabs / .tab classes
  - Wave 4 GET /_components showcase route — exercises every primitive
  - Wave 5 .panel-header → .ph atomic markup migration + CSS rule rewrite + Phase 02 invariant test rewrites

# Tech tracking
tech-stack:
  added: [Google Fonts CDN dependency for Inter Tight + JetBrains Mono]
  patterns:
    - "Additive CSS extension at end of app.css with phase banner — no edits to existing rules; preserves byte-stable invariants"
    - ".ph (new) coexists with .panel-header (existing) until Wave 5 atomic migration — same atomicity pattern Wave 3 will use for topbar swap + test_main.py rewrite"
    - "Helix primitives use existing tokens.css vars exclusively — no new tokens added (D-UI2-04 type scale untouched)"
    - "!important on .pop width/min-width to defeat Bootstrap --bs-dropdown-min-width: 10rem default (Pitfall 3)"
    - ".btn-helix namespace prevents collision with Bootstrap .btn — primary button rules apply only when paired with .btn-helix class"
    - "Sticky-corner table z-index ladder with explicit backgrounds prevents bleed-through (Pitfall 5)"

key-files:
  created: []
  modified:
    - app_v2/templates/base.html (3-line Google Fonts <link> insertion in <head>, BEFORE tokens.css link)
    - app_v2/static/css/app.css (Phase 04 banner block appended at end, +514 lines / 540 -> 1054)

key-decisions:
  - "D-UIF-01 rename path: ship .ph as a NEW selector (NOT alias, NOT immediate rename). Existing .panel-header CSS rules at lines 58-74 stay byte-stable in Wave 1. Wave 5 atomically rewrites .panel-header CSS rules to .ph rules together with template markup migration AND Phase 02 invariant test updates — same atomicity pattern as Wave 3's planned topbar swap + test_main.py rewrite. Splitting Wave 1 from Wave 5 keeps each plan small and reviewable while keeping Phase 02 invariants green between waves."
  - "No new tokens added to tokens.css. Researcher and planner confirmed no Phase 4 primitive uses --cyan or --cyan-soft (deferred to chat sidebar per CONTEXT.md §Deferred). All new rules consume existing tokens (--accent, --accent-soft, --accent-ink, --ink, --ink-2, --mute, --dim, --line, --line-2, --green, --green-soft, --red, --red-soft, --amber, --amber-soft, --panel, --shadow-panel, --radius-panel, --radius-card, --radius-btn, --radius-pill)."
  - ".navbar { padding-top: 16px; padding-bottom: 16px } rule preserved in Wave 1. Wave 3 will atomically remove this rule together with the base.html topbar markup swap and the test_main.py / test_phase02_invariants.py test_navbar_padding_override rewrites — same atomicity pattern as Wave 5's panel-header migration."
  - "Google Fonts CDN over vendored fallback. Researcher recommended CDN-first; Helix prototype uses CDN; intranet typically allows fonts.googleapis.com. If CDN access is unreliable on deployment, a follow-up phase can vendor woff2 files and switch to local @font-face rules."
  - "Inter Tight weight 800 added to font request. Existing .page-title { font-weight: 800 } at app.css line 44 was silently degrading to system fallback weight 700 (Pitfall 1). Loading the full 400/500/600/700/800 set per Dashboard_v2.html line 9 fixes this for both .page-title and the new .brand-mark."
  - "btn-helix namespacing: NOT overriding Bootstrap .btn. Phase 4 primary-button rules apply only via .btn-helix class. This avoids site-wide Bootstrap button restyling and keeps Phase 4 primitives opt-in."

patterns-established:
  - "Phase 04 banner pattern: every CSS additions wave under a clearly-labeled `/* ============ Phase 04 — UI Foundation (Helix primitives) ... ============ */` banner with source line refs to Dashboard_v2.html and explicit notes on which existing rules stay byte-stable + why."
  - "Spacing normalization to 4px grid: Dashboard_v2.html non-mod-4 paddings (10px 14px topbar, 18px 26px ph, 30px 32px hero, 38px btn) re-anchored to nearest mod-4 (8px 16px topbar, 16px 24px ph, 32px 32px hero, 40px btn) per UI-SPEC §Spacing — deltas documented in Phase 04 banner comment."
  - "Atomic-migration deferral: when a markup migration would invalidate Phase 02 invariant tests, ship the new selector additively in one wave, atomically rewrite markup + CSS rules + invariant tests in a later wave. Coexistence between waves keeps the suite green and bisectable."

requirements-completed: [D-UIF-01, D-UIF-06, D-UIF-07, D-UIF-09, D-UIF-10]

# Metrics
duration: 5min
completed: 2026-05-03
---

# Phase 04 Plan 01: UI Foundation CSS Primitives Summary

**Helix primitive CSS foundation appended to app.css (.topbar / .brand-mark / .ph / .hero / .kpis / .pop / .tiny-chip / .table-sticky-corner / .btn-helix and 35+ supporting selectors) plus Google Fonts loaded for Inter Tight 400-800 + JetBrains Mono 400-600**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-03T07:51:59Z
- **Completed:** 2026-05-03T07:57:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Google Fonts link added to base.html `<head>` BEFORE tokens.css link, fixing Pitfall 1 (Inter Tight weight 800 was silently degrading to system fallback ~700 because no `<link>` ever loaded the font)
- Every Helix primitive CSS rule from Dashboard_v2.html lines 31-152, 173-219, 263-268, 1155-1177 ported into app.css with 4px-grid normalization (.topbar 10px 14px → 8px 16px; .ph 18px 26px → 16px 24px; .hero 30px 32px → 32px 32px; .btn 38px → 40px)
- `.ph` shipped as NEW selector (D-UIF-01 rename path additive in Wave 1; Wave 5 atomically rewrites .panel-header CSS rules + markup + tests)
- All Phase 02 invariants stay green (57 passed) — `.panel-header { padding: 18px 26px ...}`, `.panel-header .panel-title { font-size: 18px; font-weight: 700; ... margin: 0; ... }`, and `.navbar { padding: 16px 0 }` rules byte-stable
- All test_main.py tests stay green (18 passed, 2 skipped) — existing topbar still renders, will be replaced atomically in Wave 3
- Full v2 test suite green (493 passed, 5 skipped, 0 failures) — no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Google Fonts link to base.html (Pitfall 1 fix)** — `c7c6d56` (feat)
2. **Task 2: Append all Helix primitive CSS rules to app.css** — `ddce7e1` (feat)

## Files Created/Modified

- `app_v2/templates/base.html` — Added 3-line Google Fonts `<link>` block (preconnect + preconnect crossorigin + stylesheet) in `<head>` after bootstrap-icons.css and BEFORE tokens.css. Existing structure (navbar, footer, scripts, htmx-error-container) byte-stable. 96 → 106 lines.
- `app_v2/static/css/app.css` — Appended Phase 04 banner block at end of file with all primitive rules: .topbar / .brand / .brand-mark / .brand-sep / .av / .top-right / .tabs / .tab[aria-selected="true"] / .tab .count / .ph / .ph b / .ph .tag / .ph .spacer / .ph .panel-title / .chips / .chip / .chip.on / .chip .n / .hero / .hero::after / .hero .label / .hero .num / .hero .delta / .hero-bar / .hero .side / .kpis / .kpis.five / .kpi / .kpi .l / .kpi .v / .kpi .d (.up/.down/.flat/.ok) / .kpi .spark / .pop-wrap / .pop / .pop-head / .pop .qrow / .pop .dates / .pop .foot / .pop .grp / .pop .grp-l / .pop .opts / .pop .opt / .pop .opt.on / .st / .pill (.open/.closed/.over) / .typ / .typ-ic / .oemchip / .ufschip / .lnk / .tiny-chip (.ok/.info/.warn/.neutral/.err) / .table-sticky-corner-wrap / .table-sticky-corner / .btn-helix (.sm/.ghost). 540 → 1054 lines (+514). All existing rules byte-stable.

## Decisions Made

- **D-UIF-01 rename path (additive in Wave 1):** `.ph` ships as a NEW selector with normalized 16px 24px padding. Existing `.panel-header { padding: 18px 26px ...}` and `.panel-header .panel-title` rules stay byte-stable until Wave 5 atomically rewrites them together with the template markup migration AND Phase 02 invariant test updates. This pattern (atomic migration in a later wave) keeps the test suite green and bisectable between waves — same approach Wave 3 will use for the topbar swap + test_main.py rewrite.
- **No new tokens:** No `--cyan` / `--cyan-soft` added. Confirmed researcher's audit — no Phase 4 primitive uses cyan; deferred to a future chat-sidebar phase per CONTEXT.md §Deferred.
- **`.navbar { padding: 16px 0 }` preserved:** Wave 3 owns its removal alongside the topbar markup swap.
- **Google Fonts CDN over vendored fallback:** Helix prototype uses CDN; intranet typically allows `fonts.googleapis.com`. Vendored woff2 fallback can be added in a follow-up if outbound DNS is restricted.
- **`btn-helix` namespace:** Avoids collision with Bootstrap `.btn`. Phase 4 primary-button rules apply only via the `.btn-helix` class so existing site-wide Bootstrap buttons are unchanged.
- **`!important` on `.pop` width/min-width:** Required to defeat Bootstrap's `--bs-dropdown-min-width: 10rem` default (Pitfall 3). When Wave 2 macros apply `.pop` to a `.dropdown-menu`, this guarantees the 300px width wins regardless of cascade tie-breaker.

## Deviations from Plan

None — plan executed exactly as written. Both tasks completed sequentially with all acceptance criteria green on first run. The `.panel-header .panel-title` rule grep in the plan's task-2 verify script (`.panel-header .panel-title { font-size: 18px; font-weight: 700; margin: 0;`) was a planner-side typo (the actual existing rule at line 74 is `.panel-header .panel-title { font-size: 18px; font-weight: 700; letter-spacing: -.015em; margin: 0; line-height: 1.2; }` — `letter-spacing` is between `font-weight` and `margin`). The intent of the assertion (rule preserved byte-stable) was satisfied; the actual rule text matches `app.css` line 74 verbatim from before this plan ran. No file changed; only the verify-script substring was inaccurate.

## Issues Encountered

None. Both tasks ran first-time green. Task 1 verification (FastAPI TestClient `r = c.get('/'); 'Inter+Tight' in r.text`) passed. Task 2 verification (full grep matrix + Phase 02 invariants + test_main.py + full v2 suite + static-asset endpoint serving the new CSS) passed.

## User Setup Required

None — no external service configuration required. Google Fonts CDN is fetched directly from the user's browser at page load; no server-side credentials.

## Next Phase Readiness

- **Wave 2 unblocked:** Every macro in `app_v2/templates/_components/` (planned: topbar.html, page_head.html, hero.html, kpi_card.html, sparkline.html, date_range_popover.html, filters_popover.html) now has a concrete CSS rule to bind to. Macro authors can use class names verbatim from this plan's CSS without further token additions.
- **Wave 3 unblocked:** `.topbar` / `.brand` / `.brand-mark` / `.av` / `.tabs` / `.tab[aria-selected="true"]` rules are live and dormant. When Wave 3 swaps base.html's `<nav class="navbar">` for `{{ topbar(active_tab=...) }}`, the new markup will pick up these rules immediately. Wave 3 also owns: removing `.navbar { padding: 16px 0 }` from app.css; rewriting `tests/v2/test_main.py` assertions on `nav-tabs` / `navbar-brand` to assert on `.topbar` / `.brand` / `.brand-mark` / `.tab[aria-selected="true"]`; deleting `tests/v2/test_phase02_invariants.py::test_navbar_padding_override`.
- **Wave 4 unblocked:** GET /_components showcase route can render every section (Topbar, Page-head, Hero full + minimal, KPI 4-up, KPI 5-up, Pills/Chips/Tiny-chips, Date-range popover, Filters popover, Sticky-corner table) against this CSS foundation.
- **Wave 5 unblocked:** Atomic `.panel-header` → `.ph` migration can proceed: rewrite the four `.panel-header*` rules (lines 58, 68, 69, 74) to `.ph*` rules byte-equivalent at the property level (with the 16px 24px padding normalization already shipped on `.ph`); rewrite all `class="panel-header"` markup occurrences to `class="ph"`; rewrite Phase 02 invariant tests (test_panel_title_rule, test_browse_panel_header_byte_stable, test_count_oob_inside_panel_header, test_filter_bar_after_panel_header, test_no_count_in_panel_footer) to assert on `.ph` instead.
- **No blockers.**

## Self-Check: PASSED

- FOUND: `app_v2/templates/base.html` (Task 1 modified, Google Fonts links present)
- FOUND: `app_v2/static/css/app.css` (Task 2 modified, Phase 04 banner present)
- FOUND: `.planning/phases/04-ui-foundation-helix-aligned-shell-primitives-build-reusable-/04-01-SUMMARY.md` (this file)
- FOUND: commit `c7c6d56` (Task 1 — Google Fonts link)
- FOUND: commit `ddce7e1` (Task 2 — Helix primitive CSS)

---
*Phase: 04-ui-foundation-helix-aligned-shell-primitives-build-reusable*
*Completed: 2026-05-03*
