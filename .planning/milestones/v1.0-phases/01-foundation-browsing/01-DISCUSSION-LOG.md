# Phase 1: Foundation + Browsing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-23
**Phase:** 01-foundation-browsing
**Areas discussed:** Navigation & page structure, Browse page layout, Settings page UX, Chart + export placement

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Nav & page structure | Page count, detail view placement, sidebar contents, login behavior | ✓ |
| Browse page layout | Picker placement, catalog UI, pivot axis, LUN grouping | ✓ |
| Settings page UX | Role access, test-connection flow, secrets handling, save behavior | ✓ |
| Chart + export placement | Chart location, column selection, export scope, button UX | ✓ |

**User's choice:** all four areas.

---

## Nav & Page Structure

### Q1 — Page split

| Option | Description | Selected |
|--------|-------------|----------|
| Browse + Settings (Recommended) | Minimal surface; Home = default landing = Browse | ✓ |
| Home + Browse + Settings | Landing page with onboarding hints | |
| Browse + Detail + Settings | Single-platform detail as its own page | |

**User's choice:** Browse + Settings.

### Q2 — Detail view placement

| Option | Description | Selected |
|--------|-------------|----------|
| Tab next to pivot (Recommended) | Two tabs inside Browse: Pivot / Detail | ✓ |
| Expander below pivot | Collapsible per-platform expanders | |
| Separate page in navigation | Detail as a top-level page | |

**User's choice:** Tab next to pivot.

### Q3 — Sidebar contents

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal: user + DB status + logout (Recommended) | No LLM selector in Phase 1 | |
| Full: DB + LLM selectors + freshness | Pre-wire for Phase 2 | ✓ |
| None — put status/meta in page headers | Empty sidebar | |

**User's choice:** Full sidebar (but freshness was later dropped — see follow-up).

### Q4 — Login behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Login-only, nav hidden (Recommended) | FOUND-01 literal reading | |
| All pages registered, auth-gated redirect | Conventional web-app behavior | |
| **Other** — "for now login is not mandatory" | Free-text response | ✓ |

**User's choice:** Free-text "for now login is not mandatory" — triggered follow-up.

### Follow-up — Scope of "login not mandatory"

| Option | Description | Selected |
|--------|-------------|----------|
| Skip auth entirely in Phase 1 | No streamlit-authenticator in Phase 1 code paths | ✓ |
| Auth wired but permissive | Login accessible but not forced | |
| Auth wired, demo-mode bypass flag | Config flag to toggle auth | |

**User's choice:** Skip auth entirely. FOUND-01/02/03 deferred; auth.yaml stays gitignored regardless.

### Follow-up — Data-freshness source

| Option | Description | Selected |
|--------|-------------|----------|
| Skip for now (Recommended) | No schema support; drop from sidebar | ✓ |
| MAX of assumed timestamp column | Query MAX() per rerun | |
| File-mtime of sidecar last_sync file | Sidecar file touched by ingestion | |

**User's choice:** Skip.

### Follow-up — LLM selector behavior in Phase 1

| Option | Description | Selected |
|--------|-------------|----------|
| Visible but inert in Phase 1 (Recommended) | Writes session_state; nothing reads it | ✓ |
| Hide in Phase 1, add in Phase 2 | Defer the selector | |
| Visible + full Phase-2 scaffolding | Include data-sensitivity warning now | |

**User's choice:** Visible but inert.

---

## Browse Page Layout

### Q1 — Picker placement

| Option | Description | Selected |
|--------|-------------|----------|
| Left sidebar (Recommended) | Classic BI layout; tabs fill the main panel | ✓ |
| Top of main panel, above tabs | Pickers as a collapsible 'Filters' section | |
| Two-column split: filters left + view right | Filters in main panel, 30/70 split | |

**User's choice:** Left sidebar.

### Q2 — Catalog UI

| Option | Description | Selected |
|--------|-------------|----------|
| Searchable two-level multiselect (Recommended) | Single `st.multiselect` with "Category / Item" labels | ✓ |
| Expandable InfoCategory tree with checkboxes | `st.expander` per category | |
| Search bar + filtered table + checkboxes | DataFrame with built-in row selection | |

**User's choice:** Searchable two-level multiselect.

### Q3 — Pivot axis

| Option | Description | Selected |
|--------|-------------|----------|
| Parameters as columns, platforms as rows (Recommended) | PLATFORM_ID is frozen index | |
| Platforms as columns, parameters as rows | Parameters as index | |
| User-selectable via toggle (Recommended to defer) | "Swap axes" toggle in Phase 1 | ✓ |

**User's choice:** User-selectable via toggle — **chosen as an active Phase 1 feature** despite the "defer" hint. Default orientation: parameters-as-columns.

### Q4 — LUN grouping in catalog

| Option | Description | Selected |
|--------|-------------|----------|
| Collapsed per-field, expandable per-LUN (Recommended) | 'WriteProt' once, expandable to 0..7 | |
| All 8 LUNs listed flat | 8 separate entries | ✓ |
| Two-level: roll-up + per-LUN entries | Both representations | |

**User's choice:** Flat. Narrows the BROWSE-02 requirement phrase "grouped under their field name" for Phase 1.

---

## Settings Page UX

### Q1 — Edit access

| Option | Description | Selected |
|--------|-------------|----------|
| Everyone with URL access (Recommended) | No role gate, consistent with no-auth Phase 1 | ✓ |
| Config flag to lock read-only | `app.settings_editable: false` | |
| Hidden behind shared passphrase | Lightweight gate | |

**User's choice:** Everyone.

### Q2 — Test-connection flow

| Option | Description | Selected |
|--------|-------------|----------|
| Per-row 'Test' button + inline badge (Recommended) | Sync, spinner, ✅/❌ badge | ✓ |
| Auto-test on save + Test button | Save gates on test | |
| Single 'Test all' button | Sequential run for all entries | |

**User's choice:** Per-row Test + badge.

### Q3 — Secrets handling

| Option | Description | Selected |
|--------|-------------|----------|
| Plaintext in settings.yaml + .gitignore (Recommended) | Masked UI input, scaffolding-consistent | ✓ |
| Env-var references in YAML | `${PBM2_DB_PASSWORD}` resolved at load | |
| Separate secrets.yaml | Two-file split | |

**User's choice:** Plaintext + gitignore.

### Q4 — Save behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Save + auto-reload caches (Recommended) | `st.cache_resource.clear()` + `st.cache_data.clear()` | ✓ |
| Save + explicit 'Reload' button | User clicks to invalidate | |
| Save + hard restart prompt | Ops-level restart | |

**User's choice:** Auto-reload.

---

## Chart + Export Placement

### Q1 — Chart location

| Option | Description | Selected |
|--------|-------------|----------|
| Third tab: Pivot / Detail / Chart (Recommended) | Sibling tab; shared filter state | ✓ |
| Inline panel below pivot grid | Chart on the Pivot tab | |
| Expander button opening modal/dialog | Chart as action, not view | |

**User's choice:** Third tab.

### Q2 — Chart column selection

| Option | Description | Selected |
|--------|-------------|----------|
| User picks column + chart type explicitly (Recommended) | Selectbox (numeric-coercible) + radio (bar/line/scatter) | ✓ |
| Auto-render first numeric column | Default bar chart; user can swap | |
| Small-multiple charts per numeric column | Grid of charts | |

**User's choice:** Explicit.

### Q3 — Export scope

| Option | Description | Selected |
|--------|-------------|----------|
| Currently-visible view after sort/hide (Recommended) | What you see is what you get | ✓ |
| Raw underlying long-form rows | Pre-pivot DataFrame | |
| Both: dialog lets user pick | Configurable | |

**User's choice:** Currently-visible. (Power-user "Raw rows" option still surfaces in the export dialog as a secondary scope selector — see CONTEXT.md D-16.)

### Q4 — Export button UX

| Option | Description | Selected |
|--------|-------------|----------|
| Two download buttons above each view (Recommended) | `st.download_button` x2 per tab | |
| Single 'Export' button opening dialog | Consolidated `st.dialog` flow | ✓ |
| Toolbar above tabs | Share + export + reset cluster | |

**User's choice:** Single Export dialog.

---

## Claude's Discretion

Areas left to planner/implementer judgment (copied from CONTEXT.md for audit completeness):

- Badge/spinner/illustration visuals
- Typeahead debounce/throttle
- Empty/loading/error message wording (BROWSE-07)
- Export filename sanitization
- Settings form column layout
- AgentConfig readonly display in Phase 1 Settings
- First-launch seed from `settings.example.yaml` to `settings.yaml`

## Deferred Ideas (copied for audit)

- Authentication (FOUND-01, FOUND-03) — pre-deployment work item; FOUND-02 gitignore is NOT deferred
- Data-freshness indicator — blocked on upstream timestamp column
- LUN / DME grouping in pivot — v2 (BROWSE-V2-01, BROWSE-V2-02)
- All NL / agent / safety-visible / starter-prompt behavior — Phase 2
- Heatmap, editable SQL, history page — v1.x or Phase 2+
- Presets, saved sets, cross-session history, similar-platforms, confidence indicator — v2+
