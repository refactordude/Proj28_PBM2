# Phase 03 — UI Review

**Audited:** 2026-04-25
**Baseline:** 03-UI-SPEC.md (Dashboard_v2.html anchor, locked decisions D-01..D-31)
**Screenshots:** not captured (no dev server detected on :3000 / :5173 / :8000) — code-only audit
**Scope:** templates `platforms/*.html`, `summary/*.html`, `overview/_entity_row.html`; `tokens.css`; `app.css`

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | Every UI-SPEC verbatim string present; 7-entry error vocabulary intact; aria-labels on all icon-only buttons. |
| 2. Visuals | 4/4 | Distinct focal point per state; violet `.ai-btn` is the singular AI affordance; no icon-only buttons without label or aria-label. |
| 3. Color | 4/4 | tokens.css verbatim from Dashboard; zero hardcoded hex in templates; violet/accent/amber/red usage matches the SPEC reservation table exactly. |
| 4. Typography | 3/4 | Type ladder matches SPEC; Inter Tight declared first in `font-family`; **but the Google Fonts `<link>` is absent from base.html, so Inter Tight never loads — every render uses system-ui silently.** |
| 5. Spacing | 4/4 | Bootstrap utilities dominate; the two inline `padding: 16px 20px` / `padding: 18px 22px` values are explicitly prescribed by UI-SPEC §8a/§8b (spinner mini-card and success panel-body). |
| 6. Experience Design | 3/4 | Loading/error/empty/disabled/confirmation states all wired; aria-live polite on summary slot; **but two SPEC affordances are missing: (a) char-counter `oninput` updater + red-at->65000 colour, (b) `hx-on::after-swap` focus-return on Save success.** |

**Overall: 22/24**

---

## Top 3 Priority Fixes

1. **Google Fonts `<link>` missing in `base.html` — Inter Tight never loads** — Every page renders with the system-ui fallback, so the carefully-tuned letter-spacing and 800-weight `.page-title` (28px) look notably different from the Dashboard reference. UI-SPEC §Design System explicitly prescribes `<link rel="preconnect">` + the `media="print"` non-render-blocking swap; none of those tags are in `app_v2/templates/base.html` (lines 1–21). **Fix:** Add the four lines from UI-SPEC §Design System "Font loading strategy" verbatim into `<head>` of `base.html`, between the bootstrap-icons stylesheet (line 10) and the tokens stylesheet (line 14). Intranet-safe degradation already works because `font-family` lists `system-ui` after Inter Tight.

2. **`#char-count` is stale — no `oninput` updater + no red-at-65000 colour swap** — UI-SPEC §6 specifies "Updates client-side via a tiny inline JS `oninput` — counts textarea length, color turns `var(--red)` at >65000 chars. Defensive UX for the 64KB cap (D-31)." The template at `app_v2/templates/platforms/_edit_panel.html:32` renders the counter once at server-render time (`{{ raw_md | length }} / 65536`) but never updates as the user types. A user pasting near-64KB content sees the same `0 / 65536` until they Save and hit the 422. **Fix:** Add `oninput="document.getElementById('char-count').textContent=this.value.length+' / 65536';document.getElementById('char-count').style.color=this.value.length>65000?'var(--red)':''"` (or extract to `app_v2/static/js/char-counter.js`) on the textarea at `_edit_panel.html:41-47`.

3. **No `hx-on::after-swap` focus return on Save success** — UI-SPEC §Accessibility prescribes "After Save success, focus returns to the Edit button (server adds `hx-on::after-swap=\"document.querySelector('[hx-post*=edit]')?.focus()\"` on the rendered view)." The rendered-view fragment in `_content_area.html` does not carry this handler, so a keyboard-only user who saves loses focus to `<body>` after the swap and must Tab back into the page to reach the next action. **Fix:** Add `hx-on::after-swap="document.querySelector('[hx-post*=\"/edit\"]')?.focus()"` to the `<div class="panel" id="content-area">` at `_content_area.html:6`.

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)

**Verbatim copy contract (UI-SPEC §Copywriting Contract) — every string accounted for:**

- `_content_area.html:16` — `No content yet — Add some.` PASS
- `_content_area.html:21` + `detail.html:54` — `Add Content` PASS
- `detail.html:32` + `_entity_row.html:33` — `AI Summary` PASS
- `detail.html:39` — `Edit`; `detail.html:47` — `Delete`; `detail.html:45` — `Delete content page for {pid}? This cannot be undone.` PASS
- `_edit_panel.html:60` — `Cancel`; `_edit_panel.html:63` — `Save`; `_edit_panel.html:15` — `Write`; `_edit_panel.html:29` — `Preview` PASS
- `_edit_panel.html:51` — `Click Preview to render, or start typing — preview will refresh after 500ms.` PASS
- `_edit_panel.html:32` — `{n} / 65536` PASS (server-rendered; see Top-3 fix #2 for client-side dynamism)
- `_edit_panel.html:46` — placeholder `# {pid}\n\nWrite notes in markdown…` PASS
- `_entity_row.html:32` — `Content page must exist first — open the platform to Add some` PASS
- `detail.html:72` + `_entity_row.html:55` — `Summarizing… (using {backend_name})` PASS
- `_success.html:33` — `Regenerate`; `_success.html:31` — `Regenerate ignoring cache` (title) PASS
- `_error.html:13` — `Summary unavailable: {reason}. Try again or switch LLM backend in Settings.` PASS
- `_error.html:21` — `Retry` PASS

**aria-label coverage (icon-only / icon-with-text but visually icon-led):**
- `detail.html:31` — `Generate AI summary for {pid}`
- `detail.html:38` — `Edit content for {pid}`
- `detail.html:46` — `Delete content for {pid}`
- `_entity_row.html:20` — `View {pid}` (the `bi-arrow-right-circle` link)
- `_entity_row.html:31` — `Generate AI summary for {pid}`
- `_entity_row.html:37` — `Remove {pid}` (Phase 02 inherited)
- `_success.html:32` — `Regenerate AI summary for {pid} ignoring cache`

**Generic-CTA grep (`Submit / Click Here / OK button`):** zero hits across `app_v2/templates/`. No generic copywriting anywhere in Phase 03 surface.

**No raw exception text leaks** — `_error.html` only renders `{{ reason }}` from the 7-string classified vocabulary (verified by `tests/v2/test_phase03_invariants.py::test_summary_route_never_returns_5xx` plus runtime tests).

### Pillar 2: Visuals (4/4)

**Focal points (per UI-SPEC §Focal Points):**
- Detail page (has content) → rendered article body (`.markdown-content` 800px-centered inside `.panel`) ✓
- Detail page (empty) → single `Add Content` `btn-primary` CTA, vertically centred (`py-5 text-center`) ✓
- Edit view → textarea (rows=20, monospace) is the visual centre; Save/Cancel buttons sit bottom-right with `justify-content-end` ✓
- AI Summary success → first markdown bullet (max-width 720px); metadata footer is grey small-text below ✓
- AI Summary error → amber alert with `Retry` button on the right (`justify-content-between`) ✓

**Visual hierarchy via size + weight + colour:**
- `.page-title` 28px / 800 weight / -.035em letter-spacing (`app.css:9`) — clearly dominant
- `.panel-header b` 18px / 700 — secondary section heading
- Body text 15px / 400 — readable baseline
- `.tag` chip 12px / 500 / `--mute` — tertiary metadata

**Icon-only button audit:** every `<button>` whose visible content is just `<i class="bi …"></i>` carries an `aria-label`. The `<a>` arrow-link (`_entity_row.html:18-22`) and the row Remove button (`_entity_row.html:36-43`) are aria-labelled. **No naked icon-only buttons.**

**Single AI affordance** — `.ai-btn` violet pill appears in exactly 3 places (Overview row, detail header, success-card Regenerate). The `.ai-btn.regen` variant flips the icon to `bi-arrow-clockwise` so the user can distinguish the action at a glance — matches UI-SPEC §8b "Regenerate icon" rule.

### Pillar 3: Color (4/4)

**Token compliance — `tokens.css` (lines 4–33) is verbatim from UI-SPEC §Design System:**
- `--bg: #f3f4f6` ✓ `--ink: #171c24` ✓ `--accent: #3366ff` ✓ `--violet: #7a5af8` ✓ `--accent-soft: #ebf1ff` ✓ `--violet-soft: #efebfe` ✓ `--amber: #f59e0b` ✓ `--red: #ef3e4a` ✓ `--green: #17a963` ✓ `--radius-panel: 22px` ✓ `--shadow-panel: 0 1px 2px rgba(16,24,40,.04)` ✓

**Hardcoded hex in templates:** zero hits across `platforms/`, `summary/`, and `_entity_row.html`. Every colour reference goes through Bootstrap utilities (`bg-primary`, `text-muted`, `alert-warning`, etc.) or `var(--*)` (used in 4 inline styles, all on the violet spinner/text in the htmx-indicator and the `border-top: 1px solid var(--line)` on the success metadata divider).

**Accent (#3366ff) reservation matrix (UI-SPEC §Color):**

| Reserved use | Found in |
|--------------|----------|
| Save button | `_edit_panel.html:62` (`btn btn-primary btn-sm`) ✓ |
| Add Content empty-state CTA | `_content_area.html:17` and `detail.html:50` ✓ |
| Active nav-pill | `app.css:36-39` (`.nav-pills .nav-link.active { background: var(--accent-soft); color: var(--accent); }`) ✓ |
| Brand badge | `_entity_row.html:8` and `detail.html:13` (`badge rounded-pill bg-primary`) ✓ |
| Inline links | `app.css:78` `.markdown-content blockquote` border uses `var(--accent-soft)` — no `<a>` colour rule needed (Bootstrap default uses `--bs-primary` ≈ `#3366ff` is close enough; not exact match but within design system) |

**Violet (#7a5af8) reservation:** appears only on `.ai-btn` (3 placements), spinner colour, "Summarizing…" text, success metadata footer (mono span colour inherited via parent). **Never used for non-AI affordances.** This is the single most important visual contract for the Dashboard anchor and it is honoured exactly.

**Amber (warning) reservation:** appears only on `_error.html:9` (`alert-warning`) + `_error.html:15` (`btn-outline-warning` Retry). Not used elsewhere. Per D-16: recoverable failure, not destructive.

**Red (destructive) reservation:** appears only on `detail.html:41` (`btn-outline-danger` Delete) and the inherited row `bi-x` Remove button (`_entity_row.html:36`). Not used for non-destructive actions.

**Bootstrap class distribution** (only Phase 03 templates):

```
btn-primary       3 (Save, Add Content, empty-state Add Content)
btn-outline-danger 2 (Delete header, Remove row inherited)
btn-outline-warning 1 (Retry)
btn-white          1 (Edit)
btn-sec            1 (Cancel)
bg-primary         2 (Brand badges; Phase 02 inherited)
bg-info            2 (SoC badges; Phase 02 inherited)
bg-success         2 (Year badges; Phase 02 inherited)
bg-secondary       2 (Unknown year badges)
alert-warning      1 (LLM error)
text-muted         3 (empty-state copy, summary metadata, preview-pane initial copy)
```

Distribution is balanced; no overuse of any single accent.

### Pillar 4: Typography (3/4)

**Font-family stack declared (`tokens.css:37`):**
```
"Inter Tight", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif
```
Mono: `"JetBrains Mono", ui-monospace, monospace` (`tokens.css:43`).

**FINDING — Inter Tight never actually loads in this build.** Searched `app_v2/templates/base.html` and the rest of the templates for `fonts.googleapis`, `fonts.gstatic`, `preconnect`, `@font-face` — **zero hits**. UI-SPEC §Design System "Font loading strategy (intranet-safe)" prescribes:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
```

None of these tags are in `base.html`. Result: every `font-family: "Inter Tight", system-ui, …` declaration silently falls through to system-ui on every render. The 28px / 800-weight `.page-title` rendered in Helvetica Neue (macOS) or Segoe UI (Windows) at 800 weight is visually heavier and tighter than Inter Tight at 800. The carefully-tuned `letter-spacing: -.035em` was tuned against Inter Tight's metrics; on system-ui it looks slightly off.

This is the single biggest visual deviation from the Dashboard anchor. **The deviation may be intentional** (intranet without outbound DNS, INFRA-04 vendor-only requirement), but UI-SPEC §Design System claims the "non-render-blocking" load strategy is in use — it is not. Either:
- (a) Add the `<link>` tags per UI-SPEC, OR
- (b) Self-host the Inter Tight + JetBrains Mono `.woff2` files in `app_v2/static/vendor/fonts/` and add `@font-face` rules to `tokens.css` (the path the SPEC marks as `CONTENT-F03` "informally tracked").

**Type ladder distribution:**

Distinct font sizes in `app.css` (sorted): 12, 13, 13.5, 14, 17, 18, 20, 24, 28 — **9 sizes**, exceeds the abstract 4-size guideline. However, these match UI-SPEC §Typography ladder exactly (28/24/20/18/17/14/13.5/13/12 + body 15px from tokens). Each size has a documented role (page title / panel header / article H1-H3 / nav-pill / code / tag chip). Justifies as a designed type scale, not arbitrary growth.

Distinct font weights: 4 (500/600/700/800). Below the abstract 2-weight guideline but appropriate for a Dashboard-style design with prominent display weights. UI-SPEC explicitly approves these weights.

**Inline font-size in templates:** 2 hits — `_content_area.html:16` (16px on empty-state body copy) and `_entity_row.html:51` (13px on row spinner text). Both deviate from the .css ladder slightly. The 16px on empty-state is a one-off bump for readability of the single line; the 13px is a "small chip" treatment for the inline spinner. Acceptable but could be folded into utility classes (`fs-6` Bootstrap utility = ~14.4px, not exact). Minor finding.

**Mono usage:** `_success.html:17` `<span class="mono">{{ llm_name }} · {{ llm_model }}</span>` ✓ correctly applied. Edit-view textarea uses `font-monospace` Bootstrap utility (`_edit_panel.html:43`) — Bootstrap's built-in monospace stack, which falls back gracefully but is NOT JetBrains Mono. The textarea's mono is functionally correct; visually it would benefit from `class="font-monospace mono"` (combine the utility with the JetBrains stack) for full Dashboard fidelity. Minor.

### Pillar 5: Spacing (4/4)

**Bootstrap utility dominance:** 27 unique spacing utility uses across the 7 Phase 03 templates (`mt-2/3`, `mb-1/3`, `me-2`, `ms-2`, `gap-2`, `py-2/5`, `px-3`, `pt-2`, `pb-2`, `p-0`). Reads as a small, consistent vocabulary.

**Custom spacing in `app.css` (Dashboard-traceable):**
- `.shell { padding: 18px 24px 56px }` ✓ matches Dashboard line 29
- `.panel-body { padding: 26px 32px }` — UI-SPEC §3 explicitly justifies the 26/32 inset (vs Dashboard's 18/26 `.ph` row) as "content reading benefits from more horizontal space"
- `.panel-header { padding: 18px 26px }` ✓ Dashboard `.ph` verbatim
- `.page-head { margin: 26px 4px 16px }` ✓ Dashboard line 64
- `.ai-btn { height: 26px; padding: 0 10px }` ✓ Dashboard line 216 verbatim
- `.ai-btn.ai-btn-md { height: 32px; padding: 0 14px }` ✓ UI-SPEC §7 detail-page variant

**Inline arbitrary spacing — 2 hits, both UI-SPEC-prescribed:**
- `detail.html:68` — `style="padding: 16px 20px;"` on the htmx-indicator panel — **explicitly listed in UI-SPEC §8a** ("`<div class="panel mt-2" style="padding: 16px 20px;">`")
- `_success.html:10` — `style="padding: 18px 22px;"` on the success panel-body — **explicitly listed in UI-SPEC §8b** ("`<div class="panel-body" style="padding: 18px 22px;">`")

These are intentional deviations from `.panel-body { padding: 26px 32px }` to make the inline summary mini-card visually lighter than a full content panel. Spec-compliant.

**Article max-width:** `app.css:69` `.markdown-content { max-width: 800px; margin: 0 auto; line-height: 1.6 }` ✓ matches D-03 verbatim. Success summary overrides to 720px (`_success.html:11`) per UI-SPEC §8b.

**No layout regression on Phase 02 row geometry:** the per-row summary slot is rendered as a separate `<li class="list-group-item p-0">` (`_entity_row.html:47`) — `p-0` collapses padding so the slot doesn't introduce a duplicate top border. Phase 02 60px row contract preserved.

### Pillar 6: Experience Design (3/4)

**State coverage matrix (UI-SPEC §State Diagrams):**

| State | Implementation | Status |
|-------|---------------|--------|
| Detail page — has_content (rendered) | `_content_area.html:5-12` | ✓ |
| Detail page — empty | `_content_area.html:13-25` (`py-5 text-center` + Add Content CTA) | ✓ |
| Edit view (Write tab) | `_edit_panel.html:40-48` (textarea, monospace, maxlength=65536) | ✓ |
| Edit view (Preview tab initial) | `_edit_panel.html:49-53` ("Click Preview to render…") | ✓ |
| Edit view (Preview rendered) | `_preview_pane.html` swapped via `POST /preview` | ✓ |
| Save → rendered view | `outerHTML` swap on `#content-area` | ✓ |
| Cancel (client-side) | `_edit_panel.html:58-60` `hx-on:click` reads `data-cancel-html` | ✓ |
| Delete confirmation | `detail.html:45` `hx-confirm="Delete content page for {pid}?"` | ✓ |
| AI Summary — loading | `htmx-indicator` pre-seeded in slot (detail + entity_row) | ✓ |
| AI Summary — success | `_success.html` with metadata footer + Regenerate | ✓ |
| AI Summary — error | `_error.html` amber alert + Retry (UI-SPEC §8c verbatim) | ✓ |
| AI Summary — disabled (no content) | `_entity_row.html:32` `disabled title=...` | ✓ |
| AI Summary — in-flight double-submit prevention | `hx-disabled-elt="this"` on every trigger | ✓ |

**Accessibility audit:**
- `aria-live="polite" aria-atomic="true"` on summary slot ✓ (`detail.html:65`, `_entity_row.html:48`)
- `role="status"` on every spinner ✓
- `role="alert"` on amber alert ✓ (`_error.html:10`)
- `aria-labelledby` paired tab/tabpanel ✓ (`_edit_panel.html:40`/`49`)
- `aria-label` for textarea (`_edit_panel.html:47`) ✓
- `aria-selected` on nav-pill buttons ✓ (`_edit_panel.html:15, 24`)
- `visually-hidden` "Loading…" inside spinners ✓

**FINDING (gap 1) — `#char-count` is server-rendered-only.** UI-SPEC §6 says: "Updates client-side via a tiny inline JS `oninput` — counts textarea length, color turns `var(--red)` at >65000 chars. Defensive UX for the 64KB cap (D-31)." Implementation at `_edit_panel.html:32`:

```html
<span class="tag ms-auto" id="char-count">{{ raw_md | length }} / 65536</span>
```

No `oninput` handler on the textarea, no `id="md-textarea"` listener. Counter freezes at server-render-time value until next server round-trip. A user pasting 70KB of content sees `0 / 65536` and only learns it was rejected after clicking Save → 422. Cheap fix; meaningful UX upgrade.

**FINDING (gap 2) — No `hx-on::after-swap` focus return on Save success.** UI-SPEC §Accessibility prescribes "After Save success, focus returns to the Edit button (server adds `hx-on::after-swap=\"document.querySelector('[hx-post*=edit]')?.focus()\"` on the rendered view)." Searched `_content_area.html` and `detail.html` — zero hits for `hx-on::after-swap` or `after-swap`. Keyboard-only users will lose focus to `<body>` after the outerHTML swap and must Tab back through the navbar to reach the action toolbar. Single-attribute fix on the `#content-area` div.

**Cache age disclosure (success metadata):** `_success.html:18-22` shows `(fresh)` when `cached_age_s == 0`, otherwise `cached {n}s ago`. Excellent trust UX — users can tell at a glance whether they're seeing a real-time call or a TTL hit.

**Error vocabulary boundary:** `_error.html` only renders `{{ reason }}` — never raw exception text. Coupled with the runtime guard `test_summary_route_never_returns_5xx` in `tests/v2/test_phase03_invariants.py`, the security/UX boundary is enforced both at-render and at-runtime.

---

## Files Audited

**Templates (Phase 03):**
- `app_v2/templates/platforms/detail.html` (76 lines)
- `app_v2/templates/platforms/_content_area.html` (25 lines)
- `app_v2/templates/platforms/_edit_panel.html` (67 lines)
- `app_v2/templates/platforms/_preview_pane.html` (6 lines)
- `app_v2/templates/summary/_success.html` (37 lines)
- `app_v2/templates/summary/_error.html` (23 lines)
- `app_v2/templates/overview/_entity_row.html` (58 lines, Phase 03 update)
- `app_v2/templates/base.html` (72 lines, audited for stylesheet wiring + font loading)

**CSS:**
- `app_v2/static/css/tokens.css` (43 lines, verbatim Dashboard tokens)
- `app_v2/static/css/app.css` (78 lines, .shell / .panel / .ai-btn / .markdown-content / nav-pills overrides)

**Visual reference anchor:**
- `/home/yh/Desktop/02_Projects/Proj27_PBM1_fork_bootstrap/Dashboard_v2.html` (1438 lines, lines 11–219 cross-referenced for token + .ai-btn + .panel verbatim compliance)

**Phase 03 baselines:**
- `.planning/phases/03-content-pages-ai-summary/03-UI-SPEC.md` (1046 lines — design contract)
- `.planning/phases/03-content-pages-ai-summary/03-CONTEXT.md` (D-01..D-31 locked decisions)
- `.planning/phases/03-content-pages-ai-summary/03-{01,02,03,04}-SUMMARY.md` (implementation evidence)
- `.planning/phases/03-content-pages-ai-summary/03-{01,02,03,04}-PLAN.md` (referenced via SUMMARY for plan fidelity)

---

## Notes for the Orchestrator

- **No screenshots captured** — no FastAPI dev server was running on :8000, :3000, or :5173 at audit time. The audit relied on template + CSS source review against UI-SPEC and Dashboard_v2.html. A follow-up pass with the dev server live (and Playwright on :8000) would let us catch any runtime CSS-cascade surprises (especially the Inter Tight loading question — the visual evidence would be conclusive).
- **No registry safety section** — `components.json` does not exist; this is a Python/Jinja2/Bootstrap project, not shadcn/React. UI-SPEC §Registry Safety explicitly marks "Not applicable."
- **Locked decisions D-01..D-31 honoured** — every decision has a ≥1 backing test per the traceability matrix in `03-04-SUMMARY.md`. None of the three priority fixes above conflict with a locked decision; they are unaddressed UI-SPEC clauses, not deviations from CONTEXT.md.
- **Test count stewardship** — the three priority fixes are small (one `<link>` block, one `oninput` attribute, one `hx-on::after-swap` attribute). Each can ship without breaking the existing 411 passing tests; if anything, fix #1 (font loading) may want a small acceptance test that base.html contains the Google Fonts `<link>` so the regression is guarded.
