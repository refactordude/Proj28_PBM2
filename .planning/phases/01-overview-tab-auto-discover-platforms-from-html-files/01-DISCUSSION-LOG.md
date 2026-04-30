# Phase 1: Overview Tab — Auto-discover Joint Validations from HTML Files — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `01-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 01-overview-tab-auto-discover-platforms-from-html-files
**Areas discussed:** Discovery contract, Fate of config/overview.yaml, Add platform UX, Edge cases & refresh

---

## Pre-discussion gate (no CONTEXT.md found)

| Option | Description | Selected |
|--------|-------------|----------|
| Run discuss-phase first | Capture goal, scope, design decisions before planning | ✓ |
| Continue without context | Plan from research + roadmap title only | |

**User's choice:** Run discuss-phase first.
**Notes:** Roadmap entry had only `Goal: TBD` and `Requirements: TBD` — too thin to plan against.

---

## Tab scope (foundational reframe)

The user clarified mid-discovery that this phase is NOT about Platforms. They named a new domain entity **Joint Validation** (Confluence-exported HTML) that is unrelated to `PLATFORM_ID`/`ufs_data`.

| Option | Description | Selected |
|--------|-------------|----------|
| Replace Overview with Joint Validation | Overview tab content swaps Platforms → Joint Validations; curated yaml + Add form go away | ✓ |
| New 'Joint Validation' tab; keep Overview as-is | Add a new top-nav tab; keep Platform Overview alongside | |
| Rename Overview → 'Joint Validation' | Same as Replace + relabel routes /overview → /joint-validation | |
| Two sub-views inside one tab | Toggle inside Overview between 'Platforms' and 'Joint Validations' | |

**User's choice:** Replace Overview with Joint Validation.
**Notes:** Locks the foundation — Joint Validation becomes THE primary Overview surface; Platform-curated Overview machinery is deprecated.

---

## Discovery contract

### Source files

| Option | Description | Selected |
|--------|-------------|----------|
| `content/platforms/*.md` | Reuse existing Platform markdown files | |
| A different `*.html` directory | Separate HTML directory drives Overview | ✓ |
| Both `.md` and `.html` | Merge by PLATFORM_ID | |

**User's choice:** A different `*.html` directory.
**Notes:** User specified the convention `content/Joint Validation/<confluence_page_id>/index.html`, one HTML per folder, NOT mapped to PLATFORM_ID. Sample referenced: `content/Joint Validation/3193868109/index.html` (does not yet exist on disk).

### Metadata source

| Option | Description | Selected |
|--------|-------------|----------|
| Parse the index.html itself | Extract from `<title>` / `<h1>` / `<meta>` / table rows | ✓ |
| Sidecar `meta.yaml` per folder | Frontmatter pattern, separate file | |
| Frontmatter inside index.html | Embedded YAML in a comment / script tag | |
| Confluence API at index time | Live REST fetch, cache locally | |

**User's choice:** Parse the index.html itself.
**Notes:** User then provided the explicit extraction rules — title from first `<h1>`, plus 12 fields from `<strong>Field</strong>` rows (Status / Customer / Model Name / AP Company / AP Model / Device / Controller / Application / 담당자 / Start / End / Report Link). Missing field → blank cell (not em-dash).

### Directory name

| Option | Description | Selected |
|--------|-------------|----------|
| Keep 'Joint Validation' (with space) | Path includes the literal space | |
| Slug: `content/joint-validation/` | Lowercase + hyphen | |
| Slug: `content/joint_validation/` | Lowercase + underscore | ✓ |

**User's choice:** `content/joint_validation/` (lowercase underscore).
**Notes:** Matches Python module-naming convention used in `app_v2/`; avoids URL-encoding spaces in static-mount path.

### ID pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Numeric only (`^\d+$`) | Digits — Confluence page ID shape | ✓ |
| Alphanumeric + hyphen/underscore | `^[A-Za-z0-9_\-]{1,128}$` (PLATFORM_ID shape) | |
| Anything with index.html | No name validation | |

**User's choice:** Numeric only.
**Notes:** Path-traversal backstop + cheap "silently skip non-Joint-Validation folders" guard.

---

## Fate of `config/overview.yaml`

### Yaml + curated machinery

| Option | Description | Selected |
|--------|-------------|----------|
| Delete all of it | Remove yaml + overview_store + curated-list code paths | ✓ |
| Delete yaml only, keep platforms/*.md | Surgical | |
| Keep both as pure data, unwired from Overview | Lowest-risk diff, dead modules left | |
| Repurpose yaml as 'pinned/hidden' override | Auto-discovery primary + thin override layer | |

**User's choice:** Delete all of it.
**Notes:** `content/platforms/*.md` stays (Browse/Ask still need PLATFORM_IDs); only the Overview-side curated machinery is removed.

### Two existing routes

| Option | Description | Selected |
|--------|-------------|----------|
| Remove both | Drop POST /overview/add (the Platform Add form) | ✓ |
| Remove /overview/add, keep /platforms/<PID> detail | | |
| Keep both as orphaned paths | Not recommended | |

**User's choice:** Remove POST /overview/add (and any other curated-list routes still in tree). `/platforms/<PID>` detail/edit page stays — Browse + Ask still depend on it.

---

## Add platform UX

### Onboarding workflow

| Option | Description | Selected |
|--------|-------------|----------|
| Drop folder → next request shows it | Pure auto-discover; no UI affordance | ✓ |
| Drop folder + manual 'Refresh' button | Same + cache-invalidation button | |
| In-app 'Import from Confluence URL' form | App fetches HTML; new scope | |

**User's choice:** Drop folder → next request shows it.
**Notes:** Auto-discover semantics; no in-app onboarding for v1.

---

## Edge cases & refresh

### Cache strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Re-glob on every request | Always-fresh, no cache | |
| mtime-keyed cache per file | Mirror Phase 5 D-OV-12 | ✓ |
| TTL cache (60s) | Up-to-60s lag | |

**User's choice:** mtime-keyed cache per file.
**Notes:** Glob itself stays uncached; only the parsed metadata per file is memoized by mtime_ns.

### Default sort

| Option | Description | Selected |
|--------|-------------|----------|
| start desc, tiebreaker page_id asc | Matches Phase 5 D-OV-07 | ✓ |
| end desc | Latest deadline at top | |
| title asc | Alphabetical | |
| Last modified desc (file mtime) | What changed today | |

**User's choice:** start desc, tiebreaker page_id asc.

### Filters

| Option | Description | Selected |
|--------|-------------|----------|
| Same 6 as v2.0 | Status / Customer / AP Company / Device / Controller / Application | ✓ |
| Same 6 + Assignee + AP Model | 8 popovers | |
| Status + Customer only | Two filters | |

**User's choice:** Same 6 as v2.0.

### Row click

| Option | Description | Selected |
|--------|-------------|----------|
| New /joint_validation/<id> detail page | Server-rendered properties + iframe of body | ✓ |
| Open Report Link in a new tab | No in-app detail | |
| Inline expand row in place | Drawer pattern | |
| No row click, only Report Link button | Title is plain text | |

**User's choice:** New /joint_validation/<id> detail page.

### Routes

| Option | Description | Selected |
|--------|-------------|----------|
| Keep /overview + /overview/grid | URL stable; only content changes | ✓ |
| Rename to /joint_validation everywhere | Cleanest mental model; breaks bookmarks | |
| Keep /overview but change human label | Lowest churn for URLs and humans | |

**User's choice:** Keep /overview + /overview/grid (listing). New /joint_validation/<id> for the detail page.
**Notes:** Top-nav label changes to "Joint Validation" (Claude's discretion derived from the Replace Overview decision).

### Detail page rendering

| Option | Description | Selected |
|--------|-------------|----------|
| <iframe sandbox> the index.html | Confluence styling intact; sandboxed | ✓ |
| Inline render the parsed body | Sanitize + render in app shell | |
| Properties table only + 'Open in Confluence' button | Smallest surface | |

**User's choice:** <iframe sandbox> the index.html. Static-mount `content/joint_validation/` so the iframe can resolve.

### Row actions

| Option | Description | Selected |
|--------|-------------|----------|
| View + Report Link | No AI Summary in v1 | |
| View + Report Link + AI Summary | Carry Phase 3 + D-OV-15 forward | |
| Title-as-link only | Title is the click target; Report Link still in its own column | |
| **Other (user freeform)** | **"Two buttons. Report Link and AI Summary. AI Summary button does LLM-summarize the parse text of index.html."** | ✓ |

**User's choice:** Two buttons in the action column — Report Link + AI Summary. Title cell itself is the link to the detail page (no separate View button). AI Summary input = parsed text of index.html.

### Empty state

| Option | Description | Selected |
|--------|-------------|----------|
| Empty grid + helper text | Onboarding hint without an Add button | ✓ |
| Empty grid only | Minimal | |
| Hide table + big CTA | Centered card | |

**User's choice:** Empty grid + helper text.
**Notes:** Helper copy: "Drop a Confluence export at content/joint_validation/<page_id>/index.html". Filter popovers disabled when zero rows.

### AI Summary input

| Option | Description | Selected |
|--------|-------------|----------|
| BeautifulSoup get_text() with separator | Strip ALL tags; preserve text | |
| Properties table + first <h1> + first paragraph | Targeted extraction | |
| Full HTML (no stripping) | Raw HTML | |
| **Other (user freeform)** | **"From html file, images are very long text and will make context overload. Make sure to remove images and only use text. (`<img>` tag's `src` part for example.) Use method of your choice for this."** | ✓ |

**User's choice:** Strip `<img>` (and `<script>`, `<style>`) before extracting text. Method: BeautifulSoup decompose noisy tags + `get_text(separator='\n')` + collapse blanks. Existing `nl_service.max_context_tokens=30000` clamps final input.

---

## Claude's Discretion

- HTML parser selector strategy (find_parent('tr') vs. find_next_sibling('td') etc.)
- Date parsing fallback behavior (treat as blank for sort; render raw string)
- AI Summary prompt copy (carry tone from Platform AI Summary)
- Sample HTML fixture for tests (user has no real sample to provide)
- Top-nav label color/icon (Bootstrap defaults)

---

## Deferred Ideas

- In-app Confluence import (URL paste → fetch → save)
- Date-range filter on Start / End
- Filter on Title / Model Name / Assignee
- Bulk-select / batch operations
- Repurposing config/overview.yaml as a pin/hide override
- Manual 'Refresh' button to force cache invalidation
- Live Confluence API metadata fetch (alternative to HTML scrape)
- Removing content/platforms/*.md or /platforms/<PID> detail page (explicitly out of scope)
