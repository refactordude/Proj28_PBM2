---
phase: 04-ui-foundation-helix-aligned-shell-primitives-build-reusable
type: ui-review
audited_at: 2026-05-03
auditor: gsd-ui-review
baseline: 04-UI-SPEC.md (approved)
screenshots: captured (dev server detected on :8000)
screenshot_dir: .planning/ui-reviews/04-20260503-205530/
---

# Phase 04 — UI Review

> Retroactive audit of Phase 04 (UI Foundation — Helix-aligned shell & primitives) against the approved `04-UI-SPEC.md` design contract. Audit method: shipped-template + Phase 04 CSS-block grep + visual spot-check of `/_components`, `/`, `/browse`, `/ask` at desktop / mobile / tablet viewports.

**Baseline:** `04-UI-SPEC.md`
**Stack:** FastAPI + Bootstrap 5 + HTMX + Jinja2 (no React, no shadcn)
**Screenshots captured:** `components-desktop.png`, `components-mobile.png`, `components-tablet.png`, `jv-desktop.png`, `browse-desktop.png`, `ask-desktop.png`

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | Every UI-SPEC §Copywriting label matches verbatim; CTAs are concrete; sparkline edge-case copy is honest. |
| 2. Visuals | 3/4 | Dashboard_v2.html anchoring is faithful at desktop; `/_components` showcase is sectioned and readable; mobile breaks (no `@media` rules) drag the score down. |
| 3. Color | 4/4 | 60/30/10 split holds; accent reserved for the declared elements; no rogue hex values. |
| 4. Typography | 4/4 | Inter Tight 400-800 + JetBrains Mono 400-600 loaded; weight 800 actually renders (Pitfall 1 fix verified); element-bound sizes match UI-SPEC §Typography table. |
| 5. Spacing | 3/4 | Tokens consumed correctly; 4px-grid normalization applied to NEW Helix primitives only (Wave 5 deviation documented and accepted); inline-style scaffolding in showcase is acceptable but pollutes the example surface. |
| 6. Experience Design | 2/4 | Two real interaction bugs ship: (a) `pop-reset-link` button has zero CSS so the Reset link in popover headers renders as a default browser button; (b) no `:focus-visible` rule on `.tab`, `.chip`, `.btn-helix`, `.pop .opt` — keyboard users get only the system default outline (which is removed on `.pop .dates input:focus`). No responsive media queries means narrow viewports clip KPI grids and overflow the topbar. |

**Overall: 20/24**

---

## Top 3 Priority Fixes

1. **Add CSS for `.pop-reset-link`** — `app_v2/static/css/app.css` styles `.pop-head a` (lines 823-824) but the WR-02 fix changed the markup to `<button class="pop-reset-link">` in both `date_range_popover.html:39` and `filters_popover.html:37`. The selector no longer matches — the Reset link inherits `<button>` browser defaults (border, background, system font). User impact: the popover header's Reset control looks like a misplaced form button instead of a small accent-colored link, breaking the visual contract from UI-SPEC §Pop §pop-head. Fix: add `.pop-head .pop-reset-link { background: transparent; border: 0; padding: 0; font: inherit; font-size: 12px; font-weight: 600; color: var(--accent); cursor: pointer; } .pop-head .pop-reset-link:hover { text-decoration: underline; }` in the §Popover block (~line 825).

2. **Add `:focus-visible` rules to interactive primitives** — `app_v2/static/css/app.css` has zero focus styles on `.tab` (line 617), `.chip` (line 658), `.pop .opt` (line 886), `.btn-helix` (line 1039); `.pop .dates input:focus` actively *removes* the outline (line 868) without providing a replacement on the input itself (the border-color shift is subtle). User impact: keyboard-only users (and screen-reader users walking the tab order) cannot tell which tab/chip/button has focus. Fix: add `.tab:focus-visible, .chip:focus-visible, .pop .opt:focus-visible, .btn-helix:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }` and verify the date-input focus ring is visible (current `border-color: var(--accent)` is a 1px shift; consider adding a soft `box-shadow: 0 0 0 3px var(--accent-soft)` on focus).

3. **Add a single mobile/tablet media-query block for the new shell** — `grep '@media' app_v2/static/css/app.css` returns only `prefers-reduced-motion`. At 375px viewport (`components-mobile.png`) the topbar's avatar is partially clipped, the `.kpis` 4-up grid forces card content to overflow horizontally, the `.kpis.five` grid does the same, and the `.hero` 1.3fr/1fr layout never collapses. User impact: any non-desktop visitor — including someone resizing a desktop window narrow — sees broken layouts. Fix: add at minimum:
   ```css
   @media (max-width: 768px) {
     .topbar { margin: 8px 8px 0; padding: 8px 12px; flex-wrap: wrap; }
     .tabs { margin-left: 0; flex-wrap: wrap; gap: 4px; }
     .kpis, .kpis.five { grid-template-columns: repeat(2, 1fr); }
     .hero { grid-template-columns: 1fr !important; gap: 20px; padding: 20px; }
     .hero .num { font-size: 48px; }
   }
   ```
   This is dev-time effort; primitives stay desktop-perfect for the design-anchor goal but no longer break narrow.

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)

**Method:** grep for generic CTAs (`Submit`/`Click Here`/`OK`/`Cancel`/`Save`) and empty/error patterns across `_components/`; cross-check every row of UI-SPEC §Copywriting.

**Evidence:**
- Zero matches for `Submit`, `Click Here`, generic `OK`/`Cancel`/`Save` in `app_v2/templates/_components/`.
- UI-SPEC §Copywriting row-by-row verification:
  - "Component Showcase" / "All Phase 4 UI primitives with sample data" → `showcase.html:21` exact match.
  - "PBM2" wordmark → `topbar.html:16` exact match.
  - "PM" avatar → `topbar.html:33` exact match.
  - "Reset" / "Apply" on date popover → `date_range_popover.html:39, 60, 61` exact match.
  - "Reset Filters" / "Apply Filters" on filters popover → `filters_popover.html:37, 69` exact match.
  - "Start" / "End" labels → `date_range_popover.html:43, 51` exact match.
  - Tab labels "Joint Validation" / "Browse" / "Ask" → `topbar.html:21, 25, 29` exact match.
- HeroSpec sample data uses concrete copy ("Active validation", "Closed this week", "+12 this week") — no lorem-ipsum.
- Sparkline "Empty (svg)" / "Constant (flat)" labels in `showcase.html:108, 112` honestly describe edge-case behavior.
- `page_head` macro (WR-01 fix) uses `{% call %}` block instead of `actions_html | safe`; XSS vector closed.

**No copywriting issues found.**

### Pillar 2: Visuals (3/4)

**Method:** Visual inspection of captured screenshots at 1440×900, 768×1024, and 375×812 viewports.

**Evidence (positive):**
- Topbar at desktop: brand-mark + wordmark + 3-tab strip + avatar all align as Dashboard_v2.html intends.
- `/_components` showcase is sectioned with `.panel` + `.ph` headers; each section is labeled with a `.tag` (D-UIF id). Visual hierarchy is excellent.
- KPI 4-up grid renders sparklines absolutely-positioned top-right per Dashboard_v2.html line 114 — correct.
- Hero full + minimal variants both render. Minimal variant correctly collapses to single-column via inline `style="grid-template-columns: 1fr;"` (only data-driven inline style; UI-SPEC-aligned).
- Sticky-corner table sample renders with the documented z-index ladder.

**Evidence (negative):**
- `components-mobile.png` (375×812): topbar avatar clipped on the right; `.kpis` 4-up forces 4 cards into ~340px of width (each card squashed); `.kpis.five` worse; sticky-corner table forces page horizontal scroll. Root cause: zero responsive `@media` rules for the new primitives (only `prefers-reduced-motion` exists). UI-SPEC does not require mobile parity, but without any breakpoint the primitives are de-facto desktop-only.
- Showcase template has 25+ inline `style="..."` declarations (`showcase.html` lines 26, 38, 53, 56, 58, 64, 76, 84, 92, 94, 96, 100, 104, 108, 112, 119, 122, 123, 132, 133, 140, 141, 149, 150, 160, 164, 170, 173). Some are unavoidable (the section dividers' `margin-bottom: 24px;`), but several encode font sizes (`font-size: 11px;`, `font-size: 12px;`) that should reuse the type scale via classes. This is a showcase surface, not user-facing — but the showcase is the "live design reference" per D-UIF-02, so its inline-style density teaches downstream phases the wrong pattern.
- `.brand-sep` selector exists in CSS (line 598) but no template ever emits it. Dead rule, not visible. Minor.

### Pillar 3: Color (4/4)

**Method:** grep hex literals in the Phase 04 CSS block (lines 556-1058); count `var(--accent)` usage; verify no third hue creeps in.

**Evidence:**
- Hex values in the Phase 04 block are limited to: `#3366ff` / `#5e7cff` (brand-mark + avatar gradients — UI-SPEC §Color row "Accent" + "Brand mark gradient"); `#fff` (white text on accent / on dark chip); `#fafbfc` / `#f4f6f8` / `#f2f4f7` / `#eaecf0` (tertiary surface family — UI-SPEC §Color "Tertiary surface" #fafbfc explicit, others are decremented neutral surfaces from Dashboard_v2.html lines 51, 53, 93, 125 verbatim); `rgba(0,0,0,.06)` / `rgba(255,255,255,.18)` / `rgba(51,102,255,.08)` / `rgba(16,24,40,.18)` (alpha layers — Dashboard verbatim).
- Every other color reference is via tokens: `var(--accent)`, `var(--accent-soft)`, `var(--accent-ink)`, `var(--ink)`, `var(--ink-2)`, `var(--mute)`, `var(--dim)`, `var(--line)`, `var(--line-2)`, `var(--green)`, `var(--green-soft)`, `var(--red)`, `var(--red-soft)`, `var(--amber)`, `var(--amber-soft)`, `var(--panel)`. No `--cyan`/`--cyan-soft` added — matches UI-SPEC's "deferred to chat sidebar" decision.
- Accent reservation verified against UI-SPEC §Color "Accent reserved for" list:
  - `.tab[aria-selected="true"] .count` → accent-soft + accent (line 643-647) ✓
  - `.pop .opt.on` → accent bg + white text (line 897) ✓
  - `.pill.open` / `.st.open` → accent-soft + accent (line 917) ✓
  - `.btn-helix` → accent bg (line 1046) ✓
  - `.brand-mark` / `.av` → accent gradient (lines 592, 602) ✓
  - `.hero .delta` → accent on accent-soft (line 727-728) ✓
  - `.kpi .d.up` → accent (line 793) ✓
  - `.tiny-chip.info` → accent-soft + accent (line 983) ✓
  - `.pop-head a` → accent (line 823) — selector mismatch issue noted under Pillar 6, but the *intent* honors the reservation list.
- `.chip.on` correctly uses `--ink` (#171c24) as background, NOT `--accent`, matching the explicit UI-SPEC §Color note at line 162.
- Destructive `--red` only fires on `.pill.over` / `.st.over` / `.tiny-chip.err` / `.kpi .d.down` / `.hero .side .r .v.red` — phase-correct (no destructive user actions exist).

**No color issues.**

### Pillar 4: Typography (4/4)

**Method:** Inspect `<head>` font-link, count distinct `font-size` and `font-weight` values in the Phase 04 CSS block, cross-check element-bound overrides.

**Evidence:**
- `base.html:21` loads Google Fonts with `family=Inter+Tight:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600` — exactly the range UI-SPEC §Font Loading requires. Pitfall 1 (weight 800 silently degrading to fallback 700) is fixed; visual confirmation: `components-desktop.png` shows the bold "128" hero number and "PBM2" wordmark at heavy weight.
- Distinct font-size values in the Phase 04 block: 11px, 12px, 12.5px, 13px, 14px, 15px, 16px, 18px, 24px, 30px, 72px (eleven). UI-SPEC §Typography distinguishes the 4-role scale (15/13/18/28) from element-bound overrides (12/12.5/14/16/18/22/24/30/72/11). Every Phase 04 size maps onto one of these:
  - 11px → tiny-chip / qrow / `.kpis` p tag / `.pop .grp-l` / `.pop .dates label` (element-bound).
  - 12px → `.ph .tag` / `.tab .count` / `.pill` / `.tiny-chip` parents — wait, 11px on tiny-chip per UI-SPEC line 117 ✓.
  - 12.5px → `.typ` (UI-SPEC line 234 element-bound) ✓.
  - 13px → label/UI scale role ✓ + JetBrains Mono cell rendering.
  - 14px → tab label + `.kpi .v .u` + hero side rows (element-bound) ✓.
  - 15px → body scale + `.hero .side .r .v` (Body role) ✓.
  - 16px → brand wordmark (UI-SPEC line 114 element-bound) ✓.
  - 18px → panel heading + `.ph b` + `.ph .panel-title` (Panel heading scale role) ✓.
  - 24px → `.hero .num .u` (UI-SPEC line 119 element-bound) ✓.
  - 30px → `.kpi .v` (UI-SPEC line 118 element-bound) ✓.
  - 72px → hero stat number (UI-SPEC line 119 element-bound, showcase-only) ✓.
- Distinct font-weight values: 500, 600, 700, 800. Matches UI-SPEC §Typography "Regular (400) + Emphasis (600/700/800)" + the element-bound 500 for `.kpi .l` / `.chip` / `.hero .side .r .k` per UI-SPEC line 121. (Weight 400 is the body default and does not appear because every primitive is non-body text.)
- JetBrains Mono enforced via `.mono` and on `.pivot-table td` / `.chat-pill-tool-call` etc. Phase 04 primitives don't ship a `.mono` class but tokens.css declares the family for parameter cells.

**No typography issues.**

### Pillar 5: Spacing (3/4)

**Method:** Inspect padding/margin/gap values in the Phase 04 CSS block; cross-check 4px-grid normalization against UI-SPEC §Spacing; flag arbitrary inline values.

**Evidence (positive):**
- `.topbar` padding: 8px 16px (line 582) — UI-SPEC §Spacing "10px 14px → 8px 16px" normalized ✓.
- `.hero` padding: 32px 32px (line 694) — UI-SPEC §Spacing "30px 32px → 32px 32px" normalized ✓.
- `.btn-helix` height: 40px (line 1043) — UI-SPEC §Spacing "38px → 40px mod-4" ✓.
- `.brand-mark` 26×26 / `.av` 32×32 / `.tab` 36 height — element-bound dimensions per UI-SPEC §Cosmetic fixed dimensions ✓.
- `.kpis` gap 12px (line 766) — multiple of 4 ✓; `.hero` gap 36px (line 697) — multiple of 4 ✓; `.pop .qrow` gap 6px (line 829) — Dashboard verbatim (acknowledged 4px-grid relaxation in popover internals).
- Every spacing value in the new shell uses the documented scale (4/8/12/16/20/24/32/48).

**Evidence (negative — capping at 3/4):**
- `.ph` padding deviates from UI-SPEC §Spacing: spec says "16px 24px (normalized from 18px 26px)" but Wave 5 atomically reverted to legacy `18px 26px` (app.css line 68) to preserve byte-stable visual layout on shipped Browse/JV/Ask surfaces. **This is a documented accepted deviation** (per Phase 04-05 SUMMARY § Decisions Made: "Padding preservation over 4px-grid normalization"). UI-SPEC text reads as if 16px 24px shipped; the actual implementation chose pragmatism. Recommendation: amend UI-SPEC §Spacing's `.ph` row to read "16px 24px (NEW shell adoption only); 18px 26px preserved on legacy shipped surfaces" so future readers do not mistake the deviation for a regression.
- `showcase.html` has 28 inline `style="..."` declarations encoding spacing (`margin-bottom: 24px;`, `gap: 24px;`, `margin-top: 12px;`). Most map to the scale, but a few (e.g. `margin-bottom: 8px; font-size: 12px;` repeated 4× for caption labels) signal an unwritten "section-caption" primitive that would deserve a CSS class. Not blocking, but the showcase is the live design reference per D-UIF-02 and these inline declarations propagate the wrong copy-paste pattern.
- `.pop` 14px padding (line 806) — not a 4px-grid value. Flagged by spec at UI-SPEC line 221 as "14px padding"; intentional Dashboard verbatim. Acceptable under "popover internals are element-bound" reading.

### Pillar 6: Experience Design (2/4)

**Method:** Audit interactive states (hover, focus, disabled, loading, error) on every Phase 04 interactive primitive; verify accessibility affordances; check responsive behavior.

**Bugs (real, user-visible):**

1. **`.pop-reset-link` has no CSS rule.** `app_v2/static/css/app.css:823-824` styles `.pop-head a { color: var(--accent); ... }` but `date_range_popover.html:39` and `filters_popover.html:37` emit `<button type="button" class="pop-reset-link">` (per WR-02 fix that switched from `<a href="#">` to button to prevent default-anchor scroll-to-top). Result: the Reset link in popover headers renders as a default browser button (system font, gray border, subtle background). This is the most visible interaction defect and is reachable from the showcase by clicking either popover trigger.

2. **No `:focus-visible` rules on Phase 04 interactive primitives.** The audit found only one focus rule in the entire Phase 04 block: `.pop .dates input:focus` at line 868, which *removes* the default outline (`outline: none`) and replaces it with only a `border-color` shift on the input border. This is keyboard-hostile.
   - `.tab` (anchor — keyboard-focusable by default) — no focus style.
   - `.chip` — no focus style.
   - `.pop .opt` (chip toggle) — no focus style.
   - `.btn-helix` — no focus style; Bootstrap's `:focus` ring may show through because `.btn-helix` is paired with `.btn` on the popover triggers, but the popover-internal ghost/primary buttons don't have the `.btn` class.
   - `.lnk` — no focus style.
   - Reference comparison: `.ai-btn:focus-visible` (line 124) and `.btn-stop:focus-visible` (line 544) are properly styled — Phase 04 just didn't carry the convention forward.

3. **No responsive breakpoints.** As noted under Pillar 2; `@media (max-width: 768px)` does not exist for the new primitives.

**Disabled / loading / empty states (where applicable):**
- `.btn-helix:disabled` — no rule. Bootstrap's `.btn:disabled` covers the popover triggers (which carry both `.btn` and `.btn-helix`), but the popover-internal `<button class="btn-helix sm">Apply</button>` has no `.btn` class, so a disabled state would be invisible. Phase 04 doesn't ship a disabled use-case — but this is a foundation primitive expected to be reused, so the lack is a debt for downstream phases.
- Empty hero state — the hero macro gracefully omits `.hero-bar` when `segments` is empty and switches to single-column when `side_stats` is empty. Excellent.
- Empty sparkline → bare `<svg>` (no path). Constant data → flat mid-line. Verified in `sparkline.html:16-17, 28-32`. Excellent.
- KPI delta default: empty string → no `.d` row rendered (`kpi_card.html:22`). Excellent.
- Filters_popover with zero groups: renders `Reset Filters` and `Apply Filters` but no body. Acceptable but not exercised in the showcase.

**Accessibility positives:**
- Sparkline SVG carries `aria-hidden="true"` on both render paths (`sparkline.html:17, 42`) — correct since sparklines are decorative.
- Popover triggers carry `aria-expanded="false"` and `data-bs-toggle="dropdown"`.
- Tabs use `aria-selected="true"` on the active tab (Bootstrap-idiomatic for navigation tabs but technically `<a aria-current="page">` would be more semantic for cross-page nav; Bootstrap's nav-tabs convention permits aria-selected).

**Accessibility gaps:**
- Tab elements emit a Bootstrap Icons `<i class="bi-*">` glyph + visible text. Acceptable; no aria-label needed since the text is present.
- "Reset" links lose accent color due to selector mismatch noted above; sighted users may not recognize them as actionable.
- Date inputs: removing `:focus` outline without a clearly-visible replacement is a WCAG 2.1 SC 2.4.7 (Focus Visible) regression for users who rely on the default browser ring.

**Overall Pillar 6 verdict: 2/4.** Two visible bugs + a missing accessibility convention = "Needs work". The macros themselves are solidly architected (graceful empty states, declarative Pydantic specs, sane edge-case handling) — the gaps are in interactive polish.

---

## Registry Safety

`components.json` does not exist (project uses Bootstrap 5, not shadcn). UI-SPEC §Registry Safety confirms zero third-party registries. **Registry audit skipped — no blocks to verify.**

---

## Files Audited

### Implementation files
- `app_v2/templates/_components/topbar.html` (36 lines)
- `app_v2/templates/_components/page_head.html` (30 lines)
- `app_v2/templates/_components/hero.html` (41 lines)
- `app_v2/templates/_components/kpi_card.html` (25 lines)
- `app_v2/templates/_components/sparkline.html` (44 lines)
- `app_v2/templates/_components/date_range_popover.html` (65 lines)
- `app_v2/templates/_components/filters_popover.html` (73 lines)
- `app_v2/templates/_components/showcase.html` (215 lines)
- `app_v2/templates/_components/__init__.py` (marker)
- `app_v2/templates/base.html` (85 lines — topbar host + Google Fonts link)
- `app_v2/services/hero_spec.py` (49 lines — HeroSpec / HeroSegment / HeroSideStat)
- `app_v2/services/filter_spec.py` (35 lines — FilterGroup / FilterOption with WR-04 non-empty value validation)
- `app_v2/static/js/chip-toggle.js` (auditing first 60 lines — sibling helper of popover-search.js)
- `app_v2/routers/components.py` (showcase route + sample data fixtures)
- `app_v2/static/css/app.css` lines 556-1058 (Phase 04 banner block, ~503 lines)

### Reference / contract files
- `.planning/phases/04-ui-foundation-helix-aligned-shell-primitives-build-reusable-/04-UI-SPEC.md`
- `.planning/phases/04-ui-foundation-helix-aligned-shell-primitives-build-reusable-/04-CONTEXT.md`
- `.planning/phases/04-ui-foundation-helix-aligned-shell-primitives-build-reusable-/04-{01..05}-PLAN.md`
- `.planning/phases/04-ui-foundation-helix-aligned-shell-primitives-build-reusable-/04-{01..05}-SUMMARY.md`

### Screenshots (`.planning/ui-reviews/04-20260503-205530/`)
- `components-desktop.png` (1440×900, full-page)
- `components-mobile.png` (375×812, full-page)
- `components-tablet.png` (768×1024, full-page)
- `jv-desktop.png` (1440×900)
- `browse-desktop.png` (1440×900)
- `ask-desktop.png` (1440×900)

---

## Recommendations Beyond Top 3

- **Strip dead `.brand-sep` rule** from `app.css:598` — no template emits it; either delete or wire it into the topbar between brand wordmark and tabs.
- **Strip dead `.pop .qrow` rules** from `app.css:825-843` — the WR-03 fix removed quick-day chips from `date_range_popover.html` (no JS handler read `data-quick-days`). These rules now have no markup. Either remove the CSS too, or re-add a quick-range handler so the chips become live (UI-SPEC's reference to "7/14/30/60d quick chips" in CONTEXT becomes truthful again).
- **Document `.ph` padding deviation in UI-SPEC** — amend §Spacing to call out Wave 5's 18px 26px legacy preservation so future readers don't mistake it for non-compliance.
- **Extract showcase inline-style scaffolding** into a `.showcase-section` / `.showcase-caption` class pair so the design reference doesn't teach inline styling.
- **Consider a `.btn-helix:disabled` rule** for downstream consumers (mirrors `.ai-btn:disabled` and `.btn-stop:disabled`).

---

## Score Justification Summary

| Pillar | Score | Rationale |
|--------|-------|-----------|
| Copywriting | 4 | UI-SPEC §Copywriting fully honored; no generic CTAs; concrete sample data. |
| Visuals | 3 | Desktop fidelity excellent; mobile breaks; minor inline-style noise. |
| Color | 4 | Token discipline strict; accent reservation honored; no color drift. |
| Typography | 4 | Font loading fix verified; size + weight scales match UI-SPEC tables. |
| Spacing | 3 | 4px-grid honored on new primitives; documented `.ph` deviation; inline-style spacing in showcase. |
| Experience Design | 2 | `.pop-reset-link` has no CSS (visible bug); no `:focus-visible` on tabs/chips/buttons; no responsive breakpoints. |

**Total: 20/24 — Phase 04 is solidly architected and visually faithful at desktop, but ships two interaction-polish gaps (Reset-link styling, focus rings) that would have been caught by a manual click-through and a Tab-key walk on the showcase page. Both fixes are <50 lines of CSS.**

---

*Audit complete. UI-REVIEW.md generated 2026-05-03 by gsd-ui-review.*
