# Phase 04: Browse Tab Port — Research

**Researched:** 2026-04-26
**Domain:** v1.0 pivot-grid Browse experience ported to FastAPI 0.136 + Bootstrap 5.3.8 + HTMX 2.0.10 + Jinja2Blocks under sync `def` routes
**Confidence:** HIGH (every locked decision has a confirmed implementation idiom; all stack versions verified against installed `.venv`; URL-encoding round-trip and Jinja2Blocks API confirmed empirically)

---

## Summary

Phase 4 is **mechanical assembly**, not invention. CONTEXT.md locks 34 decisions (D-01..D-34) covering UI layout, widget choice, trigger model, caps, URL contract, and sync/async — leaving Phase 4's research scope narrow: confirm the implementation idiom for each locked decision against the **already-shipped Phase 02/03 patterns** in `app_v2/`. Three new technical patterns appear here that did not appear in Phase 02 (multiselect with chip badges) or Phase 03 (single-text editor): the **popover-checklist with client-side search**, **HTMX URL composition with repeated-key query params**, and **Bootstrap sticky-header inside a vertical-scroll panel**.

The popover-checklist is a Bootstrap 5.3 dropdown-with-`data-bs-auto-close="outside"` plus ~30 lines of vanilla JS (search filter + Apply hides dropdown via `bootstrap.Dropdown.getInstance(el).hide()`). The HTMX form aggregates checkbox state from both pickers via `hx-include` CSS-selector list; `hx-push-url="true"` works because the request URL already encodes the full state. The sticky header requires a wrapping element with `overflow-y: auto` (the Bootstrap `.table-responsive` provides only `overflow-x: auto`, so the panel itself takes `max-height: 600px; overflow: auto` — verified against installed `bootstrap.min.css`).

**Primary recommendation:** Ship in 4 plans, mirror the Phase 03 plan structure: (1) Wave 0 — upstream edits + cache extension + invariant guard scaffolding, (2) Browse service + GET/POST routes with full URL round-trip, (3) Templates + popover-search.js + sticky-header CSS, (4) Tests + invariant-guard tests. The pre-planning prerequisite from CONTEXT.md (move BROWSE-V2-04 to "Out of Scope" in REQUIREMENTS.md, ROADMAP.md, PROJECT.md) MUST happen before plans are written or the traceability table will be inconsistent.

**Five risk concentrations** (where bugs will appear if not pre-empted):

1. **Sticky-thead inside `.table-responsive`** — the wrapper provides `overflow-x: auto` only; vertical sticky needs a separate scroll container. Documented but easy to miss.
2. **`hx-push-url="true"` URL drift** — pushes the request URL. If the route is `/browse/grid` but you want `/browse?...` in the address bar, set `HX-Push-Url` response header on `/browse/grid` to the desired `/browse?...`.
3. **Param-label parsing collision** — D-13 changes the v1.0 separator from ` / ` to ` · ` (middle dot, U+00B7). v1.0 source uses ` / `; do **not** copy v1.0's `_parse_param_label` verbatim. The middle dot URL-encodes to `%C2%B7` (verified) and is unambiguous in real DB names (no InfoCategory or Item contains it).
4. **Local checkbox state vs server state** — D-14/D-15 require restoring popover checkboxes on close-without-Apply. This is purely client-side; no HTMX involvement. Stash original selection in a `data-original-selection` attribute on dropdown open; restore on `hidden.bs.dropdown` if Apply was not clicked.
5. **Pivot DataFrame copy semantics** — `app_v2/services/cache.py::fetch_cells` already returns a defensive `df.copy()`. `pivot_to_wide_core` is NOT cached (and shouldn't be — pivot is cheap and per-view-state). Do NOT wrap it in `@cached`; just call directly with the cached `df_long`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

> Copied verbatim from `.planning/phases/04-browse-tab-port/04-CONTEXT.md` — these are LOCKED. Do not relitigate.

### Locked Decisions (D-01 .. D-34)

**Surface scope (Area 1):**
- D-01: Phase 4 ports **only the Pivot grid**. Detail and Chart surfaces from v1.0 are NOT ported.
- D-02: v1.0 Streamlit Browse remains running on port 8501 as fallback for Detail/Chart. v2.0 lives in parallel on port 8000.
- D-03: Plotly stays in `requirements.txt` (v1.0 still imports it). v2.0 must NOT import Plotly anywhere under `app_v2/`. A Phase 4 invariant test enforces this.

**Filter UI layout (Area 2.1):**
- D-04: Filter controls in a top inline filter bar inside the Browse `.panel`, above the pivot grid. Single-row layout: `[Platforms ▾ N] [Parameters ▾ N] [⇄ Swap axes] ............ [Clear all] [count caption]`.
- D-05: `d-flex align-items-center gap-2 mb-3`. Picker triggers use `btn btn-outline-secondary btn-sm` with `bi-chevron-down` and selection-count badge. Swap-axes is `btn-check`-styled toggle.
- D-06: Count caption right end: "{N} platforms × {K} parameters" with `text-muted small`.

**Multiselect widget (Area 2.2):**
- D-07: Both Platforms and Parameters use **popover-checklist-with-search**. NOT typeahead-add-chip. NOT `<select multiple>`. NOT a JS lib (Choices.js, TomSelect). Pure Bootstrap dropdown + ~30 lines vanilla JS.
- D-08: Trigger button shows count badge: `[Platforms ▾ 3]`. Empty selection = `[Platforms ▾]`.
- D-09: Popover content (Bootstrap `.dropdown-menu`, `data-bs-toggle="dropdown"`, `data-bs-auto-close="outside"`):
  - Header: `<input type="search" class="form-control form-control-sm">`, focused on open
  - Body: scrollable `ul.list-unstyled`, each row = `<label class="dropdown-item d-flex"><input type="checkbox">{label}</label>`. `max-height: 320px; overflow-y: auto`
  - Footer: sticky bottom bar with `[Clear]` (left) and `[Apply (N)]` (right, `btn-primary`)
- D-10: Search input is **client-side substring filter**, case-insensitive. Vanilla JS hides `<li>` rows where `data-label.toLowerCase().includes(query)` is false. Reusable `app_v2/static/js/popover-search.js` via document event-delegation.
- D-11: Server renders the FULL candidate list once on page load. Cached via `cached_list_platforms` and `cached_list_parameters` (Phase 1 INFRA-08).

**Filter source (Area 2.3):**
- D-12: Both pickers draw from the **full DB catalog**, NOT the curated Overview list.
- D-13: Parameter labels use combined-label format `"{InfoCategory} · {Item}"` (middle dot U+00B7), sorted alphabetically by combined label. NOTE: v1.0 used ` / `; v2.0 uses ` · `. Do NOT carry the v1.0 parser over.

**Filter trigger model (Area 3.1):**
- D-14: Selections inside popover are **LOCAL until Apply**. Apply: closes popover, updates count badge, fires single `hx-post=/browse/grid`. NO change-triggered re-query per checkbox click.
- D-15: Popover-internal Clear empties checkbox state but does NOT trigger grid swap until Apply. Closing without Apply discards changes (restore via `data-original-selection`).
- D-16: Swap-axes toggle is a **view transform**, not a re-query. Triggers immediately via `hx-post=/browse/grid` with `swap=1`. Cached `_core` DataFrame is re-pivoted server-side.

**Clear all (Area 3.2):**
- D-17: Top-level `Clear all` text link in filter bar. Hidden via `d-none` when no filters set. Resets BOTH platforms and parameters AND triggers single grid swap (empty grid + empty-state).
- D-18: Single `hx-post=/browse/clear` (or `/browse/grid` with empty form), NOT two separate per-popover Clears.

**Export UX — REMOVED (Area 4):**
- D-19: **Phase 4 ships no export feature.** No Export button, no `/browse/export/xlsx`, no `/browse/export/csv`, no openpyxl in `app_v2/`.
- D-20: **BROWSE-V2-04 must be moved to REQUIREMENTS.md "Out of Scope"** before planning starts.
- D-21: ROADMAP.md Phase 4 success criterion #3 (Excel/CSV download) **must be deleted**.
- D-22: `app/components/export_dialog.py` and `_sanitize_filename` from v1.0 are NOT touched, NOT copied, NOT imported.

**Caps + warnings:**
- D-23: Row cap = 200, column cap = 30 (v1.0 defaults — NO change). Server-enforced.
- D-24: Cap-warning copy verbatim from v1.0:
  - Row-cap: `"Result capped at 200 rows. Narrow your platform or parameter selection to see all data."`
  - Col-cap: `"Showing first 30 of {N} parameters. Narrow your selection to see all."`
  - Rendered as `alert alert-warning py-2 small` ABOVE the pivot grid.
- D-25: Empty-state copy UPDATED for v2.0: `"Select platforms and parameters above to build the pivot grid."` Rendered as `alert alert-info` in the grid slot.

**Pivot grid rendering (BROWSE-V2-02):**
- D-26: `<table class="table table-striped table-hover table-sm">`. `<thead>` uses `class="sticky-top bg-light"`.
- D-27: Every cell rendered as text via Jinja2 `| e` autoescape. NO column type config. `font-family: var(--mono)` (JetBrains Mono) on cells.
- D-28: `<div class="table-responsive">` wrapper. NO sticky-left first column.
- D-29: `aggfunc="first"` for pivot duplicates (same as v1.0). Re-uses `pivot_to_wide_core()`.

**URL round-trip (BROWSE-V2-05):**
- D-30: Query params use **repeated keys** (`?platforms=A&platforms=B`).
- D-31: `swap` param is `"1"` if axes swapped, omitted otherwise.
- D-32: `hx-push-url="true"` on grid swap. Server-rendered initial GET reads same query params and pre-checks popover checkboxes.
- D-33: Param-label encoding: pass raw combined label `"attribute · vendor_id"`; FastAPI/Starlette URL-encodes on the wire. Server splits on literal ` · ` to recover `(InfoCategory, Item)`. Round-trip integration test required.

**Routes:**
| Method | Path | Purpose | Returns |
|--------|------|---------|---------|
| GET | `/browse` | Browse page (full HTML; pre-filtered grid from query params) | Full page via Jinja2Blocks |
| GET | `/?tab=browse` | Redirect/alias | 302 to `/browse` |
| POST | `/browse/grid` | Grid fragment for filter Apply / swap-axes / Clear-all | `<table>` + cap-warning + count caption (OOB swap) |

**Sync vs async:**
- D-34: All Browse routes use `def` (NOT `async def`) per INFRA-05.

### Claude's Discretion (resolve in plans/UI-SPEC)

- Bootstrap Icons: `bi-chevron-down`, `bi-arrow-left-right`, `bi-x` — replaceable.
- Dropdown popover width: suggest `min-width: 320px; max-width: 480px`.
- Popover row label truncation: yes, with `title=` tooltip for full label.
- `[Apply (N)]` shows count: yes (recommended for trust).
- Search input debounce: 50ms client-side or zero.
- Discard popover-internal selection draft on close-without-apply: yes (simpler mental model).
- HTMX swap animation: `hx-swap="innerHTML swap:200ms"` for subtle fade.
- `autocomplete="off"` on search input: yes.

### Deferred Ideas (OUT OF SCOPE — do NOT research)

- Detail surface port (single-platform long-form view).
- Chart surface port (Plotly bar/line/scatter).
- Excel/CSV export under v2.0 (REMOVED; v1.0 stays the export surface).
- Sticky-left first-column on the wide pivot grid.
- Faceted filtering by Brand/SoC/Year on the Platforms picker.
- InfoCategory grouping in the Parameters picker.
- Saved filter presets per user.
- Per-user filter persistence in cookie (Phase 5 introduces LLM-backend cookie).
- Keyboard shortcuts.
- "Select all matching search" button.
- Streaming long-form export.
- Sort-by-column-click.
- Aggregated-difference views.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BROWSE-V2-01 | Browse tab at `/browse` re-implements v1.0 pivot grid (platform × parameter) under Bootstrap + HTMX. Filter selectors HTMX-swapped on change — no full page reload. | §"Architecture Patterns" — POST `/browse/grid` returns grid fragment via `block_names=["grid", "count_oob", "warnings_oob"]`; one-orchestration-function powers GET and POST |
| BROWSE-V2-02 | Pivot grid uses Bootstrap `table table-striped table-hover` with `<thead class="sticky-top">`. Every cell rendered as text. | §"Sticky-Header Inside Panel" — wrapping panel needs `max-height + overflow-y: auto`; `.table-responsive` provides only `overflow-x` |
| BROWSE-V2-03 | Row-count + column-count indicators, 30-col cap warning, 200-row cap warning — exact v1.0 copy preserved. | §"Cap Warnings + Empty State" — D-24 verbatim copy; alert above table; OOB swap for count caption |
| ~~BROWSE-V2-04~~ | ~~Excel/CSV export~~ | **SCOPE-REMOVED per D-19..D-22**; pre-planning edits required (Required Upstream Edits §) |
| BROWSE-V2-05 | Filter state round-trips via URL query params so links are shareable. | §"URL Round-Trip" — `Query(default_factory=list)` + repeated keys + `hx-push-url`/`HX-Push-Url`; round-trip verified empirically |

**MUST NOT plan for BROWSE-V2-04.** It is moved to "Out of Scope" by D-20 and the planner's first work item is the upstream-edits prerequisite (REQUIREMENTS.md, ROADMAP.md, PROJECT.md changes).
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

These are non-negotiable directives that override any research finding suggesting otherwise.

| Directive | Source | Implication for Phase 4 |
|-----------|--------|-------------------------|
| All DB-touching FastAPI routes use `def` (sync), not `async def` | CLAUDE.md "All DB-touching FastAPI routes must be `def`…" + INFRA-05 + D-34 | All Browse routes are sync `def`. Invariant test enforces. |
| `cachetools.TTLCache` always paired with `threading.Lock()` | CLAUDE.md "cachetools TTLCache always paired with threading.Lock()" | New `cached_fetch_cells` wrapper (already exists in `app_v2/services/cache.py`); no new locks needed |
| Cache key lambda excludes unhashable `db` adapter | CLAUDE.md key contract; PITFALLS.md Pitfall 11 | Already handled in `app_v2/services/cache.py::fetch_cells` (`hashkey(platforms, infocategories, items, row_cap, db_name)`) |
| Pool sizes during parallel deployment: `pool_size=2, max_overflow=3` | CLAUDE.md | No change needed; Phase 1 set this |
| Cache wrapper names: `list_platforms`/`list_parameters`/`fetch_cells` (NOT `cached_` prefix) | STATE.md | Use existing names; phase 4 just imports `from app_v2.services.cache import fetch_cells, list_platforms, list_parameters` |
| `MarkdownIt('js-default')` only — never default constructor | CLAUDE.md | Not relevant to Phase 4 (no markdown rendering on Browse page) |
| No LangChain / litellm / Vanna / LlamaIndex anywhere in `app_v2/` | CLAUDE.md "What NOT to Use" | Existing invariant guard already covers this; extend in Phase 4 |
| No Streamlit-aggrid, ORM, full-table loads | CLAUDE.md | Already locked into the architecture |
| No openpyxl under `app_v2/`; no `import csv`; no Plotly under `app_v2/` | D-03, D-19, D-22 | NEW invariant guards required this phase |
| **No `from app.components.export_dialog`** anywhere in `app_v2/` | D-22 | NEW invariant guard required this phase |
| HTMX 4.0 alpha — stay on 2.0.10 | CLAUDE.md | Vendored at `app_v2/static/vendor/htmx/htmx.min.js` (verified 2.0.10) |

---

## Standard Stack

> All versions verified against installed `.venv` (run `.venv/bin/python -c "import importlib.metadata as md; print(md.version('fastapi'))"` etc.).

### Core (already installed — no new pip installs needed for Phase 4)
| Library | Verified Version | Purpose | Why Standard |
|---------|------------------|---------|--------------|
| FastAPI | 0.136.1 `[VERIFIED: importlib.metadata]` | HTTP framework, `Query(default_factory=list)` for repeated query keys | `[CITED: docs.fastapi.com/reference/parameters]` `Query(default_factory=list)` is the canonical idiom for `?key=A&key=B&key=C` |
| Starlette | 1.0.0 `[VERIFIED]` | Underlying ASGI; native repeated-query-key support | `[CITED: starlette docs]` `request.query_params.getlist("key")` is the substrate FastAPI builds on |
| Jinja2 | 3.1.6 `[VERIFIED]` | Template engine (autoescape on by default for `.html`) | Already used by Phase 1-3 |
| jinja2-fragments | 1.12.0 `[VERIFIED]` | `Jinja2Blocks` wrapper — `block_names=[...]` for multi-block fragment rendering | `[VERIFIED: source inspect]` confirmed kwarg is `block_names: list[str]` (plural); empty list = full page |
| python-multipart | 0.0.26 `[VERIFIED]` | `Form()` parsing (used by POST /browse/grid hx-include payload) | Already in `requirements.txt` |
| pandas | 3.0.2 `[VERIFIED]` | Pivot via `pivot_to_wide_core` (existing pure function) | No new code; reuse `app/services/ufs_service.py::pivot_to_wide_core` verbatim |
| SQLAlchemy | 2.0.49 `[VERIFIED]` | DB engine via existing adapter | No change |
| pymysql | 1.1.2 `[VERIFIED]` | MySQL driver | No change |
| cachetools | 7.0.6 `[VERIFIED]` | `TTLCache + threading.Lock` for `fetch_cells` wrapper (already exists in `app_v2/services/cache.py`) | Already pinned `>=7.0,<8.0` |
| Bootstrap | 5.3.8 (vendored at `app_v2/static/vendor/bootstrap/`) `[VERIFIED: VERSIONS.txt]` | Dropdown w/ `data-bs-auto-close="outside"`, `table-striped`, `table-sm`, `sticky-top`, `btn-check` | `[CITED: getbootstrap.com/docs/5.3/components/dropdowns]` |
| HTMX | 2.0.10 (vendored at `app_v2/static/vendor/htmx/`) `[VERIFIED: VERSIONS.txt]` | `hx-include`, `hx-push-url`, `hx-swap-oob`, `HX-Push-Url` response header | `[CITED: htmx.org/docs/]` |
| Bootstrap Icons | 1.13.1 (vendored) | `bi-chevron-down`, `bi-arrow-left-right`, `bi-x` | Phase 1 |

### Supporting (Python stdlib only — no new imports beyond Phase 1-3)
| Library | Purpose |
|---------|---------|
| `urllib.parse` | URL-encoding test asserts; not needed in production code (Starlette handles encoding) |
| `pathlib.Path` | (For invariant-guard tests only) |
| `re` | (Invariant-guard regexes only) |
| `pytest`, `pytest-mock`, `httpx.AsyncClient` (TestClient) | Test infrastructure already wired |

### Alternatives Considered (and rejected by CONTEXT.md)
| Instead of | Could Use | Why rejected |
|------------|-----------|--------------|
| Bootstrap dropdown + ~30 LOC JS | Choices.js, TomSelect, MultiSelect.js | D-07 explicit; adds JS dependency, build step, intranet vendor work |
| Repeated query keys `?platforms=A&platforms=B` | Comma-separated `?platforms=A,B` | D-30 explicit; FastAPI parses repeated keys natively into `list[str]`; comma collides with values that contain commas (none in PLATFORM_ID/Item, but still cleaner with repeated keys) |
| Ajax fetch + manual JSON parsing | HTMX hypermedia | Phase 1 set the model; HTMX is the project default |
| `<select multiple>` | Native browser multiselect | D-07 explicit; native multiselect UX is poor (Ctrl-click discoverability) |
| Server-rendered checkboxes via lazy load on popover open | Render full list once on page load | D-11 explicit; up-front cost is acceptable (~50KB for 500 platforms); instant interaction afterward |
| `pivot_to_wide_core` cached behind TTLCache | Direct call (no cache) | Pivot is cheap (sub-10ms on 200×30 grid); cache key would have to hash the entire long-DataFrame, which is more expensive than the pivot itself |
| openpyxl/CSV export | None — feature scope-removed (D-19..D-22) | Out of scope this phase |

### Installation
**No new dependencies for Phase 4.** Every library is already in `requirements.txt` and installed in `.venv`.

**Version verification (run before plan finalization):**
```bash
.venv/bin/python -c "import importlib.metadata as md; \
  print('fastapi=' + md.version('fastapi'), \
        'starlette=' + md.version('starlette'), \
        'jinja2-fragments=' + md.version('jinja2-fragments'), \
        'pandas=' + md.version('pandas'), \
        'cachetools=' + md.version('cachetools'))"
# Expected: fastapi=0.136.1 starlette=1.0.0 jinja2-fragments=1.12.0 pandas=3.0.2 cachetools=7.0.6
```

---

## Architecture Patterns

### File Layout (new files this phase)
```
app_v2/
├── routers/
│   └── browse.py                     # NEW — GET /browse, POST /browse/grid (D-34: sync def)
├── services/
│   └── browse_service.py             # NEW — orchestration: parse filter form → fetch_cells → pivot → view-model
├── templates/browse/
│   ├── index.html                    # NEW — full page; defines blocks "grid", "count_oob", "warnings_oob"
│   ├── _filter_bar.html              # NEW — inline filter bar (Platforms picker, Parameters picker, Swap, Clear-all)
│   ├── _picker_popover.html          # NEW — REUSABLE Jinja MACRO (one source for both pickers)
│   ├── _grid.html                    # NEW — pivot table fragment
│   ├── _empty_state.html             # NEW — D-25 empty alert
│   └── _cap_warnings.html            # NEW — D-24 verbatim row/col warnings
├── static/
│   ├── js/popover-search.js          # NEW — ~30 lines vanilla JS (search filter + Apply close)
│   └── css/app.css                   # MODIFIED — add .pivot-table cell font, sticky-thead helper
└── services/cache.py                 # NO CHANGE — existing fetch_cells already covers needs

app_v2/routers/root.py                # MODIFIED — DELETE Phase 1 GET /browse stub
app_v2/main.py                        # MODIFIED — register browse router BEFORE root

tests/v2/
├── test_browse_routes.py             # NEW — route smoke + URL round-trip + caps
├── test_browse_service.py            # NEW — pure orchestration tests (no DB)
└── test_phase04_invariants.py        # NEW — codebase invariant guards (no plotly/openpyxl/csv/async)
```

### Pattern 1: One orchestration function powers BOTH GET and POST

**What:** GET `/browse` and POST `/browse/grid` produce the **same view model** — the only difference is whether Jinja2Blocks renders the full page or fragment blocks. Centralize the orchestration in a single pure function in `browse_service.py`.

```python
# app_v2/services/browse_service.py
from dataclasses import dataclass
import pandas as pd
from app_v2.services.cache import fetch_cells, list_platforms, list_parameters
from app.services.ufs_service import pivot_to_wide_core

PARAM_LABEL_SEP = " · "  # D-13 — middle dot U+00B7

@dataclass
class BrowseViewModel:
    df_wide: pd.DataFrame              # may be empty if selection is empty
    row_capped: bool
    col_capped: bool
    n_value_cols_total: int            # N for "Showing first 30 of {N}"
    n_rows: int
    n_cols: int                        # value-cols actually shown (≤ 30)
    swap_axes: bool
    selected_platforms: list[str]
    selected_params: list[str]         # combined labels "attribute · vendor_id"
    all_platforms: list[str]
    all_param_labels: list[str]
    is_empty_selection: bool
    index_col_name: str                # "PLATFORM_ID" or "Item"

def _parse_param_label(label: str) -> tuple[str, str] | None:
    """Split 'InfoCategory · Item' on the literal middle-dot separator.
    Returns (cat, item) or None if the label is malformed."""
    parts = label.split(PARAM_LABEL_SEP, 1)  # split first occurrence only
    return (parts[0], parts[1]) if len(parts) == 2 else None

def build_view_model(
    db, db_name: str,
    selected_platforms: list[str],
    selected_param_labels: list[str],
    swap_axes: bool,
) -> BrowseViewModel:
    all_platforms = list_platforms(db, db_name=db_name)
    all_params_raw = list_parameters(db, db_name=db_name)
    all_param_labels = sorted(
        f"{p['InfoCategory']}{PARAM_LABEL_SEP}{p['Item']}" for p in all_params_raw
    )  # D-13 — sort by combined label
    is_empty = not selected_platforms or not selected_param_labels
    if is_empty:
        return BrowseViewModel(
            df_wide=pd.DataFrame(),
            row_capped=False, col_capped=False,
            n_value_cols_total=0, n_rows=0, n_cols=0,
            swap_axes=swap_axes,
            selected_platforms=selected_platforms,
            selected_params=selected_param_labels,
            all_platforms=all_platforms,
            all_param_labels=all_param_labels,
            is_empty_selection=True,
            index_col_name="Item" if swap_axes else "PLATFORM_ID",
        )
    parsed = [p for lbl in selected_param_labels if (p := _parse_param_label(lbl))]
    infocategories = tuple(sorted({p[0] for p in parsed}))
    items = tuple(sorted({p[1] for p in parsed}))
    df_long, row_capped = fetch_cells(
        db, tuple(selected_platforms), infocategories, items,
        row_cap=200, db_name=db_name,
    )
    df_wide, col_capped = pivot_to_wide_core(df_long, swap_axes=swap_axes, col_cap=30)
    index_col = "Item" if swap_axes else "PLATFORM_ID"
    n_value_cols_shown = max(0, len(df_wide.columns) - 1)  # subtract index col
    return BrowseViewModel(
        df_wide=df_wide,
        row_capped=row_capped,
        col_capped=col_capped,
        n_value_cols_total=len(selected_param_labels),  # for "first 30 of {N}"
        n_rows=len(df_wide),
        n_cols=n_value_cols_shown,
        swap_axes=swap_axes,
        selected_platforms=selected_platforms,
        selected_params=selected_param_labels,
        all_platforms=all_platforms,
        all_param_labels=all_param_labels,
        is_empty_selection=False,
        index_col_name=index_col,
    )
```

**Why:** GET `/browse` calls `build_view_model(...)` and renders `index.html` full-page. POST `/browse/grid` calls the SAME function and renders `block_names=["grid", "count_oob", "warnings_oob"]`. URL round-trip becomes a one-line test (GET with full query string → assert pre-rendered grid).

### Pattern 2: FastAPI `Query(default_factory=list)` for repeated query keys (D-30, BROWSE-V2-05)

**What:** FastAPI's canonical idiom for `?platforms=A&platforms=B&platforms=C` is `Annotated[list[str], Query(default_factory=list)]`. Empty omitted key returns `[]` (not `None`).

```python
# app_v2/routers/browse.py
from typing import Annotated
from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse
from app.adapters.db.base import DBAdapter
from app_v2.services.browse_service import build_view_model
from app_v2.templates import templates

router = APIRouter()

def get_db(request: Request) -> DBAdapter | None:
    return getattr(request.app.state, "db", None)

@router.get("/browse", response_class=HTMLResponse)
def browse_page(
    request: Request,
    platforms: Annotated[list[str], Query(default_factory=list)] = [],
    params:    Annotated[list[str], Query(default_factory=list)] = [],
    swap:      Annotated[str, Query()] = "",        # "1" or ""
    db: DBAdapter | None = Depends(get_db),
):
    """Initial GET — pre-renders the grid from URL state (BROWSE-V2-05)."""
    db_name = getattr(getattr(db, "config", None), "name", "") if db else ""
    vm = build_view_model(db, db_name, platforms, params, swap_axes=(swap == "1"))
    ctx = {"active_tab": "browse", "page_title": "Browse", "vm": vm}
    return templates.TemplateResponse(request, "browse/index.html", ctx)

@router.post("/browse/grid", response_class=HTMLResponse)
def browse_grid(
    request: Request,
    platforms: Annotated[list[str], Form()] = [],
    params:    Annotated[list[str], Form()] = [],
    swap:      Annotated[str, Form()] = "",
    db: DBAdapter | None = Depends(get_db),
):
    """Filter Apply / swap-axes / Clear-all swap target. Returns grid + OOB count + OOB warnings."""
    db_name = getattr(getattr(db, "config", None), "name", "") if db else ""
    vm = build_view_model(db, db_name, platforms, params, swap_axes=(swap == "1"))
    ctx = {"vm": vm}
    response = templates.TemplateResponse(
        request,
        "browse/index.html",
        ctx,
        block_names=["grid", "count_oob", "warnings_oob"],
    )
    # D-32: server-set HX-Push-Url so the address bar reflects the canonical
    # /browse URL (request was POST /browse/grid; we don't want THAT in history).
    push_url = _build_browse_url(platforms, params, swap == "1")
    response.headers["HX-Push-Url"] = push_url
    return response

def _build_browse_url(platforms: list[str], params: list[str], swap: bool) -> str:
    """Compose /browse?platforms=...&params=...&swap=1 with repeated keys."""
    from urllib.parse import urlencode
    pairs: list[tuple[str, str]] = []
    pairs += [("platforms", p) for p in platforms]
    pairs += [("params", p) for p in params]
    if swap:
        pairs.append(("swap", "1"))
    qs = urlencode(pairs)  # urlencode handles repeated keys via list-of-pairs
    return f"/browse?{qs}" if qs else "/browse"
```

**Verification (run-tested):**
```python
# verified empirically with FastAPI 0.136.1 + Starlette 1.0.0
# GET /test?platforms=A&platforms=B&platforms=C → ['A', 'B', 'C']
# GET /test                                       → []
# GET /test?platforms=A                           → ['A']
# URL-encoded ' · ' label: 'attribute%20%C2%B7%20vendor_id' decodes to 'attribute · vendor_id'
```
[VERIFIED: empirical test in research session, 2026-04-26]

### Pattern 3: HTMX form aggregation across both pickers (D-14, D-16, D-17)

**What:** Each popover renders hidden `<input>`s representing checked items. The Apply button uses `hx-include` with a CSS selector that matches inputs from BOTH pickers + the swap toggle.

```html
{# app_v2/templates/browse/_filter_bar.html — outline (full impl in plan) #}
<div class="d-flex align-items-center gap-2 mb-3" id="browse-filter-bar">

  {# Platforms picker — see _picker_popover.html macro #}
  {{ picker_popover("platforms", "Platforms", vm.all_platforms, vm.selected_platforms) }}

  {# Parameters picker #}
  {{ picker_popover("params", "Parameters", vm.all_param_labels, vm.selected_params) }}

  {# Swap-axes toggle (D-16: triggers immediately, no Apply needed) #}
  <input type="checkbox" class="btn-check" id="swap-axes" name="swap" value="1"
         {% if vm.swap_axes %}checked{% endif %}
         hx-post="/browse/grid"
         hx-include="#browse-filter-form input[name='platforms']:checked, #browse-filter-form input[name='params']:checked, #swap-axes:checked"
         hx-target="#browse-grid"
         hx-swap="innerHTML"
         hx-push-url="true"
         hx-trigger="change">
  <label class="btn btn-outline-secondary btn-sm" for="swap-axes">
    <i class="bi bi-arrow-left-right"></i> Swap axes
  </label>

  {# D-17: Clear-all link — single hx-post, no form data #}
  <a href="#" id="clear-all-link"
     class="ms-auto small {% if not vm.selected_platforms and not vm.selected_params %}d-none{% endif %}"
     hx-post="/browse/grid"
     hx-vals='{}'
     hx-target="#browse-grid"
     hx-swap="innerHTML"
     hx-push-url="true">Clear all</a>

  {# OOB count caption (D-06) — kept here AND in the grid response for OOB swap #}
  <span id="grid-count" class="text-muted small">
    {% if not vm.is_empty_selection %}{{ vm.n_rows }} platforms × {{ vm.n_cols }} parameters{% endif %}
  </span>
</div>
```

The form wrapping all checkboxes ensures `hx-include` selectors find them:

```html
{# app_v2/templates/browse/_picker_popover.html — Jinja macro reused for both pickers #}
{% macro picker_popover(name, label, options, selected) %}
<div class="dropdown">
  <button class="btn btn-outline-secondary btn-sm dropdown-toggle"
          type="button"
          id="picker-{{ name }}-trigger"
          data-bs-toggle="dropdown"
          data-bs-auto-close="outside"
          aria-expanded="false"
          data-original-selection="{{ selected | tojson | e }}">
    {{ label }}
    {% if selected %}<span class="badge bg-secondary ms-1">{{ selected | length }}</span>{% endif %}
  </button>
  <div class="dropdown-menu p-0 popover-search-root" style="min-width: 320px; max-width: 480px;">
    <div class="p-2 border-bottom">
      <input type="search" class="form-control form-control-sm popover-search-input"
             placeholder="Search {{ label | lower }}…" autocomplete="off">
    </div>
    <ul class="list-unstyled m-0 popover-search-list"
        style="max-height: 320px; overflow-y: auto;">
      {% for opt in options %}
        <li data-label="{{ opt | e }}">
          <label class="dropdown-item d-flex gap-2" title="{{ opt | e }}">
            <input type="checkbox" class="form-check-input" name="{{ name }}"
                   value="{{ opt | e }}" form="browse-filter-form"
                   {% if opt in selected %}checked{% endif %}>
            <span class="text-truncate">{{ opt | e }}</span>
          </label>
        </li>
      {% endfor %}
    </ul>
    <div class="p-2 border-top d-flex justify-content-between bg-light">
      <button type="button" class="btn btn-link btn-sm popover-clear-btn">Clear</button>
      <button type="button"
              class="btn btn-primary btn-sm popover-apply-btn"
              hx-post="/browse/grid"
              hx-include="#browse-filter-form input:checked"
              hx-target="#browse-grid"
              hx-swap="innerHTML"
              hx-push-url="true"
              hx-on:click="bootstrap.Dropdown.getInstance(document.getElementById('picker-{{ name }}-trigger')).hide()">
        Apply <span class="popover-apply-count badge bg-light text-primary">{{ selected | length }}</span>
      </button>
    </div>
  </div>
</div>
{% endmacro %}
```

The wrapping `<form id="browse-filter-form">` exists once on the page; checkboxes use `form="browse-filter-form"` to associate even though they're DOM-ancestrally inside dropdowns. `hx-include="#browse-filter-form input:checked"` then aggregates all checked items in one request.

[CITED: htmx.org/docs - hx-include accepts CSS selector list; element associations via `form=` attribute are honored]

### Pattern 4: `popover-search.js` — ~30 lines vanilla JS (D-10)

**What:** Document-level event delegation handles BOTH pickers. Three responsibilities: (1) substring filter on search input, (2) update Apply count badge as checkboxes toggle, (3) Clear button empties checkboxes (no HTMX fire).

```javascript
// app_v2/static/js/popover-search.js — D-10 client-side substring filter
(function () {
  "use strict";

  function onInput(e) {
    if (!e.target.matches('.popover-search-input')) return;
    const root = e.target.closest('.popover-search-root');
    const q = e.target.value.toLowerCase();
    root.querySelectorAll('.popover-search-list > li').forEach(li => {
      const label = (li.dataset.label || '').toLowerCase();
      li.style.display = label.includes(q) ? '' : 'none';
    });
  }

  function onCheckboxChange(e) {
    if (!e.target.matches('.popover-search-root input[type="checkbox"]')) return;
    const root = e.target.closest('.popover-search-root');
    const count = root.querySelectorAll('input[type="checkbox"]:checked').length;
    const badge = root.querySelector('.popover-apply-count');
    if (badge) badge.textContent = count;
  }

  function onClearClick(e) {
    if (!e.target.matches('.popover-clear-btn')) return;
    const root = e.target.closest('.popover-search-root');
    root.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
    // Trigger change event so the count badge updates
    root.querySelectorAll('input[type="checkbox"]').forEach(cb =>
      cb.dispatchEvent(new Event('change', { bubbles: true }))
    );
    // D-15: do NOT fire HTMX. Apply must be clicked separately.
  }

  function onDropdownShow(e) {
    // Stash original selection so close-without-Apply can restore (D-15).
    const root = e.target.querySelector?.('.popover-search-root');
    if (!root) return;
    const checked = Array.from(
      root.querySelectorAll('input[type="checkbox"]:checked')
    ).map(cb => cb.value);
    root.dataset.originalSelection = JSON.stringify(checked);
    // Focus the search input on open (D-09).
    setTimeout(() => root.querySelector('.popover-search-input')?.focus(), 0);
  }

  function onDropdownHide(e) {
    // If the user clicked Apply, the request is already firing — leave state.
    // Otherwise restore from data-original-selection (D-15).
    const root = e.target.querySelector?.('.popover-search-root');
    if (!root || !root.dataset.applied) {
      // Apply sets data-applied="1"; missing = restore.
      const original = JSON.parse(root.dataset.originalSelection || '[]');
      const set = new Set(original);
      root.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        cb.checked = set.has(cb.value);
      });
      // Reset the count badge.
      const count = original.length;
      const badge = root.querySelector('.popover-apply-count');
      if (badge) badge.textContent = count;
    }
    delete root.dataset.applied;
  }

  function onApplyClick(e) {
    if (!e.target.matches('.popover-apply-btn, .popover-apply-btn *')) return;
    const root = e.target.closest('.popover-search-root');
    if (root) root.dataset.applied = "1";
    // HTMX fires from hx-post on the button itself; Bootstrap dropdown closes
    // via hx-on:click on the button.
  }

  document.addEventListener('input',  onInput,            true);
  document.addEventListener('change', onCheckboxChange,   true);
  document.addEventListener('click',  onClearClick,       true);
  document.addEventListener('click',  onApplyClick,       true);
  document.addEventListener('show.bs.dropdown',   onDropdownShow);
  document.addEventListener('hidden.bs.dropdown', onDropdownHide);
})();
```

**Wire it in `base.html`** alongside `htmx-error-handler.js`:
```html
<script src="{{ url_for('static', path='js/popover-search.js') }}" defer></script>
```

[CITED: getbootstrap.com/docs/5.3/components/dropdowns#methods] — `bootstrap.Dropdown.getInstance(el).hide()` and the `show.bs.dropdown` / `hidden.bs.dropdown` events are documented Bootstrap 5.3 API.

### Pattern 5: Sticky-header inside panel (D-26, BROWSE-V2-02)

**What:** Bootstrap's `.table-responsive` provides ONLY `overflow-x: auto` (verified in `app_v2/static/vendor/bootstrap/bootstrap.min.css`):
```css
.table-responsive { overflow-x: auto; -webkit-overflow-scrolling: touch; }
```
`.sticky-top` uses `position: sticky; top: 0; z-index: 1020`. For sticky to engage, the **nearest scrolling ancestor** must be a scroll container. `.table-responsive` is a horizontal scroll container, so `position: sticky` on `<thead>` would stick relative to the table-responsive box, not the viewport.

**Two viable layouts** (pick one in plan):

**Option A (RECOMMENDED — matches CONTEXT.md "inside the panel" intent):**
The Browse `.panel-body` itself is the vertical scroll container, with the `.table-responsive` nested inside for horizontal overflow. Sticky-thead sticks to the panel viewport.

```html
<div class="panel">
  <div class="panel-body" style="max-height: 70vh; overflow-y: auto;">  {# vertical scroll #}
    <div class="table-responsive">                                       {# horizontal scroll #}
      <table class="table table-striped table-hover table-sm pivot-table">
        <thead class="sticky-top bg-light">
          <tr>
            <th>{{ vm.index_col_name }}</th>
            {% for col in vm.df_wide.columns if col != vm.index_col_name %}
              <th>{{ col | e }}</th>
            {% endfor %}
          </tr>
        </thead>
        <tbody>
          {% for _, row in vm.df_wide.iterrows() %}
            <tr>
              {% for col in vm.df_wide.columns %}
                <td>{{ row[col] | e if row[col] is not none else "" }}</td>
              {% endfor %}
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>
```

CSS additions in `app.css`:
```css
.pivot-table td { font-family: var(--mono); font-size: 13px; white-space: nowrap; }
.pivot-table thead.sticky-top { z-index: 2; }   /* above tbody but below dropdowns (z-index: 1000) */
.pivot-table thead th { background: var(--bs-light); border-bottom: 2px solid var(--line-2); }
```

**Option B:** Use `.table-responsive` only (no panel-body scroll), accept that sticky-top will be relative to the viewport (the entire page scrolls). This is simpler but means the filter bar scrolls away. NOT recommended — D-26 implies the header sticks within the panel.

[CITED: caniuse.com/css-sticky] — `position: sticky` is supported in all evergreen browsers since 2017; no fallback needed for an intranet app.

### Pattern 6: Block-named fragment rendering with OOB swaps (BROWSE-V2-01, D-06)

**What:** `templates.TemplateResponse(..., block_names=["grid", "count_oob", "warnings_oob"])` returns the concatenated rendered blocks in declaration order. The OOB-swap mechanism is HTMX's: the server emits an element with `id="grid-count"` AND `hx-swap-oob="true"` — HTMX swaps it into the existing `<span id="grid-count">` regardless of the primary `hx-target`.

```html
{# app_v2/templates/browse/index.html — full page + named blocks for fragment renders #}
{% extends "base.html" %}
{% block content %}
<div class="shell">
  <div class="panel">
    <div class="panel-header">
      <b>Browse</b>
      <span class="tag">Pivot grid</span>
    </div>

    {# Filter bar (single instance; checkboxes use form="browse-filter-form") #}
    <form id="browse-filter-form" autocomplete="off"></form>
    {% include "browse/_filter_bar.html" %}

    {# Pivot grid slot #}
    <div class="panel-body" style="max-height: 70vh; overflow-y: auto;">
      <div id="browse-grid">
        {% block grid %}
          {% include "browse/_warnings.html" %}
          {% if vm.is_empty_selection %}
            {% include "browse/_empty_state.html" %}
          {% else %}
            {% include "browse/_grid.html" %}
          {% endif %}
        {% endblock grid %}
      </div>
    </div>
  </div>
</div>

{# OOB blocks — emitted by POST /browse/grid alongside the primary swap. #}
{% block count_oob %}
  <span id="grid-count" hx-swap-oob="true" class="text-muted small">
    {% if not vm.is_empty_selection %}{{ vm.n_rows }} platforms × {{ vm.n_cols }} parameters{% endif %}
  </span>
{% endblock count_oob %}

{% block warnings_oob %}
  {# Warnings render INSIDE #browse-grid via the grid block; this OOB slot is reserved
     for any future "above the panel" warnings. Currently empty — kept for future use. #}
{% endblock warnings_oob %}
{% endblock %}
```

For this phase the count OOB is the only one strictly needed; warnings live inside `#browse-grid` via the `grid` block.

[VERIFIED: source inspect of `jinja2_fragments.fastapi.Jinja2Blocks.TemplateResponse`] — `block_names: list[str] = []` is the kwarg; defaults to full-page render.

### Pattern 7: Cap warnings + empty state (D-23, D-24, D-25)

**What:** Three distinct UI states, each a separate template fragment include. Verbatim copy from D-24, D-25.

```html
{# app_v2/templates/browse/_warnings.html — D-24 verbatim copy #}
{% if vm.row_capped %}
  <div class="alert alert-warning py-2 small mb-2" role="alert">
    Result capped at 200 rows. Narrow your platform or parameter selection to see all data.
  </div>
{% endif %}
{% if vm.col_capped %}
  <div class="alert alert-warning py-2 small mb-2" role="alert">
    Showing first 30 of {{ vm.n_value_cols_total }} parameters. Narrow your selection to see all.
  </div>
{% endif %}
```
```html
{# app_v2/templates/browse/_empty_state.html — D-25 (UPDATED from v1.0 — note "above" not "in the sidebar") #}
<div class="alert alert-info" role="alert">
  Select platforms and parameters above to build the pivot grid.
</div>
```

### Pattern 8: Cache wrappers — REUSE existing `app_v2/services/cache.py`

**What:** `fetch_cells`, `list_platforms`, `list_parameters` ALREADY EXIST in `app_v2/services/cache.py` (Phase 1 INFRA-08). They're TTLCache-backed with `threading.Lock()` and key on `db_name` (excluding the unhashable adapter). **No new cache wrappers needed.**

`pivot_to_wide_core` is already exposed as an alias at the bottom of `app/services/ufs_service.py` (line 289: `pivot_to_wide_core = pivot_to_wide`). Import via:
```python
from app.services.ufs_service import pivot_to_wide_core
```
Do NOT cache `pivot_to_wide_core` — pivoting a 200-row × 30-col DataFrame is sub-10ms; cache key cost (hashing the long DataFrame) exceeds compute cost.

### Anti-Patterns to Avoid

- **Calling `fetch_cells_core` directly from a route.** Always go through `app_v2.services.cache.fetch_cells` so TTLCache + Lock are honored. (PITFALLS Pitfall 11.)
- **Hashing the `db` adapter in cache keys.** TypeError; 100% miss. Already correct in `app_v2/services/cache.py`.
- **`hx-target="closest .panel"`.** The dropdown menu is a child of the panel; "closest" would target the entire panel. Use `hx-target="#browse-grid"` explicitly.
- **Forgetting `form="browse-filter-form"` on checkboxes.** Without the explicit form attribute, checkboxes inside a `<div class="dropdown">` are NOT part of any `<form>`, and `hx-include` selectors that look for `[form='browse-filter-form'] input:checked` won't match. The trick: the wrapping `<form id="browse-filter-form">` is empty; checkboxes anywhere on the page join it via the `form=` attribute.
- **Parsing the URL on the client.** Server reads `request.query_params` directly via `Query(default_factory=list)`. No JS URL handling needed beyond what HTMX does for `hx-push-url`.
- **`hx-push-url="true"` with `POST /browse/grid` request URL.** That would push `/browse/grid` into history — useless on reload. Use `HX-Push-Url` response header to push `/browse?...` instead. (Both are documented HTMX features; the response header takes precedence — `[CITED: htmx.org/headers/hx-push-url]`.)
- **Streamlit-style `st.session_state.setdefault(...)` on initial load.** v2.0 has no session state for filter selection; the URL IS the state. Render directly from URL params on every GET.
- **Double-encoding the middle dot.** Pass the raw label `"attribute · vendor_id"` in a Form/Query value; Starlette handles UTF-8 encoding/decoding. Do NOT call `urllib.parse.quote(label)` before submission.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multiselect with search | TomSelect / Choices.js / Select2 / custom typeahead | Bootstrap dropdown + 30 LOC vanilla JS | D-07 explicit; no JS build pipeline; fewer transitive deps |
| Repeated query keys parsing | Custom CSV split / JSON-encoded list | `Query(default_factory=list)` | FastAPI handles natively; URL standard |
| URL composition | String concat with manual encoding | `urllib.parse.urlencode([...])` with list-of-pairs | Handles repeated keys + special chars correctly |
| Pivot to wide form | New pandas pivot logic | `app.services.ufs_service.pivot_to_wide_core` | Already exists, tested, handles `aggfunc="first"` and col-cap (D-29) |
| Long-form fetch | New SQLAlchemy code | `app_v2.services.cache.fetch_cells` | Already cached, locked, parameterized; honors row-cap |
| OOB swap | Custom JS DOM manipulation | `hx-swap-oob="true"` on the OOB element + `block_names` | HTMX native; same pattern Phase 02 used for filter badge |
| Sticky header | Custom JS scroll listener | CSS `position: sticky` via `.sticky-top` | Native browser behavior; no JS |
| Atomic file writes | (Not relevant this phase — no writes) | — | Browse is read-only |
| URL push without page reload | `history.pushState` JS | `hx-push-url="true"` or `HX-Push-Url` response header | HTMX native |
| Client-side substring filter | Re-fetch from server | Vanilla JS `.toLowerCase().includes(q)` per row | D-10 explicit; zero round-trips |
| Bootstrap dropdown manual close | Manual class toggling | `bootstrap.Dropdown.getInstance(el).hide()` | Documented Bootstrap 5.3 API |

**Key insight:** Every domain in Phase 4 has a battle-tested idiom either in Bootstrap, HTMX, FastAPI, or already-shipped `app_v2/` code. Net new code is ~150 LOC: ~30 JS, ~50 Python (browse_service + browse router), ~70 templates. The remaining cost is plumbing (template includes, route wiring, tests).

---

## Common Pitfalls

### Pitfall 1: Sticky `<thead>` doesn't stick when nested inside `.table-responsive` only

**What goes wrong:** `<thead class="sticky-top">` appears NOT to stick on vertical scroll.

**Why it happens:** Bootstrap 5.3.8's `.table-responsive` is `overflow-x: auto` (horizontal only — verified in installed CSS). `position: sticky` engages relative to the **nearest scrolling ancestor**. With only `.table-responsive` as the wrapper, sticky-top sticks to the table-responsive box (which doesn't vertically scroll), so on page-level vertical scroll the header doesn't appear sticky.

**How to avoid:** Wrap the `.table-responsive` in a `.panel-body` (or any element) with explicit `max-height` + `overflow-y: auto`. The thead now sticks relative to the panel-body's vertical scroll container.

**Warning signs:** Manual test — scroll the page; the header doesn't follow. Or scroll horizontally only; the header DOES follow (because table-responsive IS horizontal-scroll).

[VERIFIED: bootstrap.min.css inspection — `.table-responsive { overflow-x: auto; -webkit-overflow-scrolling: touch }`]

### Pitfall 2: `hx-push-url="true"` on POST /browse/grid pushes `/browse/grid` (useless)

**What goes wrong:** After Apply, the URL changes to `/browse/grid?platforms=...&params=...` — but reloading that URL (because POST URLs aren't replayed by browsers) returns 405 Method Not Allowed.

**Why it happens:** `hx-push-url="true"` pushes the **request URL**. For POST /browse/grid that's `/browse/grid` — useless. We want `/browse?platforms=...&params=...` in the address bar.

**How to avoid:** EITHER (a) set `hx-push-url="/browse?{computed}"` (string mode — but we'd need JS to compute the URL on the client), OR (b) — the cleaner path — use the `HX-Push-Url` response header on POST /browse/grid:
```python
response.headers["HX-Push-Url"] = _build_browse_url(platforms, params, swap)
```
The response header takes precedence over the attribute (`[CITED: htmx.org/headers/hx-push-url]`).

**Warning signs:** Browser address bar shows `/browse/grid?...` after a filter change. Or browser back/forward navigates between fragment-style URLs that don't render.

### Pitfall 3: Param label parser collides with v1.0's ` / ` separator

**What goes wrong:** Developer copies `_parse_param_label` from `app/pages/browse.py:113` verbatim. The function uses `label.partition(" / ")` — but D-13 changed v2.0 to ` · ` (middle dot). Result: every label fails to parse, query returns empty results.

**Why it happens:** v1.0 source uses ` / `; v2.0 CONTEXT.md decided ` · ` for visual clarity (slash collides with directory-path mental model in some labels). The developer assumes "carry from v1.0" means verbatim copy.

**How to avoid:**
1. Define `PARAM_LABEL_SEP = " · "` as a module constant in `browse_service.py`.
2. Add a unit test that round-trips a label: `assert _parse_param_label(f"{cat}{PARAM_LABEL_SEP}{item}") == (cat, item)`.
3. Add an invariant guard test that searches for `" / "` in `app_v2/templates/browse/` and `app_v2/services/browse_service.py` — flag if found (likely a v1.0 carry-over bug).

**Warning signs:** Selected parameters in URL render as 0 results. Browser DevTools shows the request payload contains the right labels but the response is empty.

### Pitfall 4: Checkboxes in a Bootstrap dropdown are not part of any form

**What goes wrong:** `hx-include="#browse-filter-form input:checked"` matches zero elements because the checkboxes are inside `<div class="dropdown">` siblings — not inside the form.

**Why it happens:** Bootstrap dropdowns are not form elements. Inputs inside them are detached from the surrounding form unless explicitly associated.

**How to avoid:** Two parts:
1. Add an empty `<form id="browse-filter-form" autocomplete="off"></form>` somewhere on the page.
2. On every checkbox: `<input type="checkbox" name="platforms" value="..." form="browse-filter-form">`. The `form=` attribute associates an input with a form by ID even when it's not a DOM descendant. (HTML standard; works in all browsers.)
3. Then the selector `#browse-filter-form input:checked` works — but in fact since the inputs aren't DOM-children, you'd select `input[form='browse-filter-form']:checked` for clarity, OR (simpler) use `hx-include="input[name='platforms']:checked, input[name='params']:checked, [name='swap']:checked"`.

**Warning signs:** The Apply button HTMX request body has zero checkboxes; server sees empty `platforms=` and `params=`.

### Pitfall 5: `pd.DataFrame.iterrows()` is slow for 200×30 grids? (verify before assuming)

**What goes wrong:** Naive `{% for _, row in vm.df_wide.iterrows() %}` is the textbook idiom but can be slow.

**Why it happens:** `iterrows` boxes each row as a Series, which adds overhead.

**How to avoid:** For 200 rows it's fine (~10ms). If the col-cap stays at 30 and row-cap at 200, total cells = 6000; pandas can render this trivially. If profiling shows iterrows is the bottleneck (unlikely), switch to `df.values.tolist()` or `df.to_dict("records")`. **Recommendation:** start with iterrows; only optimize if profiled.

**Warning signs:** Browser-side render >500ms with the 200×30 grid. (Threshold for "feels slow" on intranet.)

### Pitfall 6: Browser does not URL-encode middle dot consistently

**What goes wrong:** The label `attribute · vendor_id` is sent in a Form value; the browser encodes ` · ` as `+%C2%B7+` (space → `+`, U+00B7 → `%C2%B7`). Server `Form()` parses it correctly. But manual URL composition for `HX-Push-Url` might use `%20` for space (URL form), giving the user a different-but-equivalent URL.

**Why it happens:** `application/x-www-form-urlencoded` uses `+` for space; URL paths/queries use `%20`. Both decode to the same string, but `urllib.parse.urlencode([...])` defaults to form-style (`+`).

**How to avoid:** Use `urllib.parse.urlencode(pairs, quote_via=urllib.parse.quote)` to force `%20` for space. This makes the visible address-bar URL match what's emitted by manual `<a href="?platforms=...">` construction. Verified empirically:
```python
>>> import urllib.parse
>>> urllib.parse.urlencode([("params", "attribute · vendor_id")], quote_via=urllib.parse.quote)
'params=attribute%20%C2%B7%20vendor_id'  # %20 (URL-style)
>>> urllib.parse.urlencode([("params", "attribute · vendor_id")])
'params=attribute+%C2%B7+vendor_id'      # + (form-style)
```
Both decode to the same value server-side; the difference is cosmetic (address-bar appearance + shareable-URL aesthetics).

**Warning signs:** A user copies a URL from the address bar and pastes it into a chat; the recipient gets a slightly different URL. (Both work; just inconsistent.)

### Pitfall 7: `hx-swap="innerHTML"` on the grid replaces the OOB slot too

**What goes wrong:** If `<span id="grid-count">` lives INSIDE `#browse-grid`, then `hx-swap="innerHTML"` to `#browse-grid` replaces it — but the OOB swap runs AFTER the primary swap, so it lands correctly. However if the OOB slot is INSIDE the swap target AND the response doesn't emit a new `<span id="grid-count">`, the DOM ends up with no `grid-count` element at all.

**Why it happens:** OOB swap matches by `id`. If the response template emits `<span id="grid-count" hx-swap-oob="true">` AS PART OF the body, HTMX detaches it and re-inserts at the matching id elsewhere. If it's not emitted, the DOM is left without the element.

**How to avoid:** Place `<span id="grid-count">` OUTSIDE `#browse-grid` (in the filter bar, per D-06). The grid response emits an OOB span which lands in the persistent shell. Mirrors Phase 02's `filter-count-badge` pattern (`app_v2/templates/overview/index.html:43-48`).

**Warning signs:** After a filter change the count caption disappears.

### Pitfall 8: `min-width: 320px` on dropdown clips the right edge on narrow viewports

**What goes wrong:** The dropdown opens with `min-width: 320px` but the parent container is narrower; dropdown extends past the viewport.

**Why it happens:** Bootstrap's Popper.js positioning handles overflow by flipping/shifting, but the `min-width` is enforced.

**How to avoid:** Set `min-width: min(320px, calc(100vw - 32px))` or apply `max-width: 100vw`. For the intranet target (1280-2560px monitors) this is unlikely to bite; recommend just `min-width: 320px; max-width: 480px` and verify on a 1024px-wide test.

**Warning signs:** On a narrow window, the dropdown right edge is cut off or the page horizontal-scrolls.

---

## Code Examples

Verified patterns from official sources or the existing codebase.

### Reading repeated query keys (FastAPI 0.136.1)

```python
# Source: fastapi.tiangolo.com/tutorial/query-params; verified empirically 2026-04-26
from typing import Annotated
from fastapi import FastAPI, Query

app = FastAPI()

@app.get("/browse")
def browse(
    platforms: Annotated[list[str], Query(default_factory=list)] = [],
    params:    Annotated[list[str], Query(default_factory=list)] = [],
    swap:      Annotated[str, Query()] = "",
):
    return {"platforms": platforms, "params": params, "swap": swap}

# GET /browse?platforms=A&platforms=B&params=attribute%20%C2%B7%20vendor_id&swap=1
# → {"platforms": ["A", "B"], "params": ["attribute · vendor_id"], "swap": "1"}
```

### Composing URL with repeated keys for HX-Push-Url

```python
# Source: docs.python.org/3/library/urllib.parse.html#urllib.parse.urlencode
import urllib.parse

def _build_browse_url(platforms: list[str], params: list[str], swap: bool) -> str:
    pairs: list[tuple[str, str]] = []
    pairs += [("platforms", p) for p in platforms]
    pairs += [("params", p)    for p in params]
    if swap:
        pairs.append(("swap", "1"))
    qs = urllib.parse.urlencode(pairs, quote_via=urllib.parse.quote)  # %20 for space
    return f"/browse?{qs}" if qs else "/browse"

# >>> _build_browse_url(["A", "B"], ["attribute · vendor_id"], True)
# '/browse?platforms=A&platforms=B&params=attribute%20%C2%B7%20vendor_id&swap=1'
```

### Multi-block fragment render (jinja2-fragments 1.12.0)

```python
# Source: jinja2_fragments.fastapi source inspect (2026-04-26)
return templates.TemplateResponse(
    request,
    "browse/index.html",
    ctx,
    block_names=["grid", "count_oob"],   # plural; concatenated in declaration order
)
# Pattern already used by Phase 02: app_v2/routers/overview.py:275
```

### Bootstrap dropdown manual close

```javascript
// Source: getbootstrap.com/docs/5.3/components/dropdowns#methods
const trigger = document.getElementById('picker-platforms-trigger');
bootstrap.Dropdown.getInstance(trigger).hide();
// Use after Apply HTMX request fires; do NOT use before — the click on the
// Apply button must be allowed to propagate to HTMX's hx-post handler.
```

### Reusing `pivot_to_wide_core` (existing pure function)

```python
# Source: app/services/ufs_service.py:227 (verbatim signature)
from app.services.ufs_service import pivot_to_wide_core

df_wide, col_capped = pivot_to_wide_core(df_long, swap_axes=False, col_cap=30)
# Returns (DataFrame_with_index_reset, bool). `aggfunc="first"` baked in (D-29).
```

### Reusing `fetch_cells` (existing cached wrapper)

```python
# Source: app_v2/services/cache.py:106 (verbatim signature)
from app_v2.services.cache import fetch_cells

df_long, row_capped = fetch_cells(
    db,
    platforms=tuple(["P1", "P2"]),
    infocategories=tuple(["attribute"]),
    items=tuple(["vendor_id"]),
    row_cap=200,
    db_name="ufs_data",
)
# Returns a defensive copy on every call (Pitfall 3 contract).
```

### Codebase invariant guard (extends `tests/v2/test_phase03_invariants.py` pattern)

```python
# Source: tests/v2/test_phase03_invariants.py — Phase 04 extends with these tests
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_V2_ROOT = REPO_ROOT / "app_v2"

def test_no_plotly_imported_in_app_v2():
    """D-03: Plotly stays in v1.0 only; v2.0 must not import it anywhere."""
    violations = []
    for path in APP_V2_ROOT.rglob("*.py"):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"^\s*(import|from)\s+plotly\b", line):
                violations.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}")
    assert violations == [], "D-03 violation:\n" + "\n".join(violations)

def test_no_openpyxl_imported_in_app_v2():
    """D-19: Excel export feature removed; openpyxl must not be imported in v2.0."""
    # Same pattern, replace plotly with openpyxl

def test_no_csv_imported_in_app_v2():
    """D-19: CSV export feature removed; csv module must not be imported in v2.0."""
    # Same pattern

def test_no_export_dialog_imported_in_app_v2():
    """D-22: app/components/export_dialog stays exclusively v1.0."""
    violations = []
    for path in APP_V2_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"\bfrom\s+app\.components\.export_dialog\b", text):
            violations.append(str(path.relative_to(REPO_ROOT)))
        if re.search(r"\bimport\s+app\.components\.export_dialog\b", text):
            violations.append(str(path.relative_to(REPO_ROOT)))
    assert violations == [], "D-22 violation:\n" + "\n".join(violations)

def test_no_async_def_in_browse_router():
    """D-34 + INFRA-05: browse routes must be sync def (threadpool dispatch)."""
    src = (APP_V2_ROOT / "routers/browse.py").read_text(encoding="utf-8")
    offending = [
        line.rstrip()
        for line in src.splitlines()
        if re.match(r"^\s*async\s+def\s+", line)
    ]
    assert offending == [], f"D-34 violation:\n" + "\n".join(offending)

def test_param_label_separator_is_middle_dot_not_slash():
    """D-13: v2.0 uses ' · ' (middle dot U+00B7), not v1.0's ' / '. Catch carryover."""
    svc = (APP_V2_ROOT / "services/browse_service.py").read_text(encoding="utf-8")
    # Must contain the middle-dot constant
    assert ' · ' in svc or '·' in svc, "D-13: PARAM_LABEL_SEP must use middle dot"
    # Must NOT split on v1.0's ' / '
    assert '" / "' not in svc and "' / '" not in svc, "D-13: do not carry v1.0 ' / ' separator"
```

---

## State of the Art

| Old Approach (v1.0 / training data) | Current Approach (v2.0 + 2026 standards) | When Changed | Impact |
|--------------------------------------|------------------------------------------|--------------|--------|
| `st.session_state` for filter state | URL query params + server-side render | v2.0 (D-30..D-33) | Shareable URLs out of the box; no session-state coupling |
| `,`-separated filter list in URL | Repeated query keys (`?p=A&p=B`) | D-30 | FastAPI parses natively; cleaner with values containing punctuation |
| `st.dataframe(df, column_config=...)` | Bootstrap `<table class="table table-striped">` | v2.0 | No JS DataGrid library; native HTML table |
| `st.toggle("Swap axes")` | Bootstrap `btn-check` toggle button | v2.0 | Hypermedia-driven; no callbacks |
| `st.cache_data` | `cachetools.TTLCache + threading.Lock` | Phase 1 INFRA-08 | Streamlit-decoupled; reusable from FastAPI threadpool |
| ` / ` (slash) param-label separator | ` · ` (middle dot U+00B7) | D-13 | Visual clarity; no collision with directory-path mental model |
| `xlsx`/`csv` export via openpyxl | NO export in v2.0 (v1.0 stays the export surface) | D-19 | Phase scope tightened; removes 50% of router complexity |

**Deprecated / outdated:**
- `pd.read_sql` with raw SQL string — deprecated in pandas 2.x; use `pd.read_sql_query(sa.text(...), conn)`. Already followed in `app/services/ufs_service.py`.
- `streamlit-aggrid` — community-maintained, unnecessary for this read-only grid; D-07 explicit.
- Comma-separated query lists in URLs — fine if values don't contain commas, but repeated-key form is the FastAPI/Starlette idiom.

---

## Assumptions Log

> All claims tagged `[ASSUMED]` in this research that the planner / discuss-phase should confirm before locking.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Pivot of 200×30 cells renders in <500ms with naive `iterrows` in Jinja2 | §"Pitfall 5" | If false, plan should add a `to_dict("records")` optimization to the template helper. Mitigation: profile in plan-04-04 review. |
| A2 | Bootstrap 5.3.8's `.dropdown-menu` Popper-positioning handles right-edge overflow on a 1024px viewport | §"Pitfall 8" | If false, dropdowns clip on narrow monitors (unlikely on 1280-2560px intranet target). Mitigation: visual smoke test in UAT. |
| A3 | `bootstrap.Dropdown.getInstance(el)` returns a non-null instance after `data-bs-toggle="dropdown"` initial open | Pattern 4 | If false, `.hide()` throws null-deref. Mitigation: guard with `?.hide()`. Verified pattern by Bootstrap docs but not run-tested in this session. |
| A4 | The `form=` attribute on inputs inside Bootstrap dropdowns correctly associates them with the form by ID | Pattern 3 | If false, hx-include misses checkboxes. Verified by HTML spec; expected to work in all evergreen browsers. |
| A5 | The `<form id="browse-filter-form">` wrapper does not need to be physically wrapping the checkboxes — the `form=` attribute is sufficient | Pattern 3 | Same as A4; HTML spec compliant. |
| A6 | Per `hx-include` interactions: `hx-include` selector matches elements at request-time (not at attribute-parse time), so checkboxes added/removed dynamically still work | Pattern 3 | Likely true (HTMX docs say `hx-include` is evaluated per-request); not run-tested. Mitigation: smoke test in plan. |

**These items are LOW-MEDIUM risk only.** No security or compliance assumption is in this list. Items A1, A3, A6 should be smoke-tested in the plan; A2 covered by UAT; A4-A5 are HTML-spec compliant.

---

## Open Questions

1. **Should the filter bar's count caption update via OOB swap on EVERY filter change, or only when the grid is rendered?**
   - What we know: D-06 says count caption is part of the filter bar. It must reflect the current state.
   - What's unclear: When the user clears all (D-17 → empty grid), does the caption hide entirely, or show `"0 platforms × 0 parameters"`?
   - Recommendation: **Hide caption when selection is empty** (see Pattern 6 — the OOB span renders empty when `vm.is_empty_selection`). UX is cleaner; matches Phase 02's pattern of hiding the filter-count-badge when count=0.

2. **Should `pivot_to_wide_core` be called on the cached `df_long` returned by `fetch_cells`, even though `fetch_cells` returns a defensive copy?**
   - What we know: `fetch_cells` returns `df.copy()` (`app_v2/services/cache.py:129`). Defensive copy means each route call gets its own DataFrame.
   - What's unclear: Calling `pivot_to_wide_core` on the copy mutates only the copy, but is the copy expensive enough to matter?
   - Recommendation: **Don't worry about it.** 200 rows × 4 columns = ~6KB DataFrame; copy is sub-1ms. Cost of pre-emptive optimization > cost of the copy.

3. **For the swap-axes toggle, should it fire even when no platforms or parameters are selected (showing the empty state with `index_col_name="Item"` instead of `"PLATFORM_ID"`)?**
   - What we know: D-16 says swap-axes is a view transform of the cached DataFrame. With no selection, there is no DataFrame.
   - What's unclear: The trigger fires regardless; the server returns the empty-state alert. Does the toggle remember its state across the empty→non-empty transition?
   - Recommendation: **Yes, fire and persist.** The `swap=1` query param round-trips via the URL; the empty-state render still includes `swap=1` in the grid response's `HX-Push-Url`. When the user adds a selection, the next Apply respects `swap=1`. UX consistent with v1.0.

4. **Is there a use case for not pre-rendering the grid on initial GET when the URL has full filter state?**
   - What we know: D-32 says the server-rendered initial GET reads query params and pre-checks popover checkboxes accordingly.
   - What's unclear: Does this mean ONLY the popovers are pre-checked (lazy-load grid via HTMX trigger on page load), or are BOTH popovers + grid rendered server-side?
   - Recommendation: **Render grid server-side too.** Rationale: (a) it avoids a redundant HTMX request after page load, (b) the canonical "shareable link" UX is "click link → see the grid", not "click link → wait for additional request → see the grid". Plan should call this out as a deliberate choice.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13+ | All `app_v2/` code | ✓ | (verified `.venv`) | — |
| FastAPI | All routes | ✓ | 0.136.1 | — |
| jinja2-fragments | Block-named rendering | ✓ | 1.12.0 | — |
| pandas | Pivot | ✓ | 3.0.2 | — |
| SQLAlchemy + pymysql | DB | ✓ | 2.0.49 / 1.1.2 | — |
| cachetools | TTLCache | ✓ | 7.0.6 | — |
| Bootstrap 5.3.8 | UI | ✓ | vendored | — |
| HTMX 2.0.10 | UI behavior | ✓ | vendored | — |
| Bootstrap Icons 1.13.1 | Icons | ✓ | vendored | — |
| Real `ufs_data` MySQL DB | Live grid render | runtime-dependent (not required for tests) | — | Mock adapter for unit tests; integration tests require real DB |

**No missing dependencies.** Phase 4 has zero new pip installs and zero new vendored assets.

---

## Validation Architecture

> SKIPPED — `workflow.nyquist_validation` is `false` in `.planning/config.json` (verified). Per the orchestrator instructions: "Validation Architecture: Skip — Nyquist validation is disabled for this run."

---

## Security Domain

> Browse is a read-only surface. No file writes, no LLM calls, no markdown rendering, no auth boundary. Security domain has narrow scope.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | NO | Auth deferred per v1.0 D-04 |
| V3 Session Management | NO | No session state on Browse |
| V4 Access Control | NO | DB read-only user is the access boundary |
| V5 Input Validation | YES | `Query(default_factory=list)` types; pivot route validates platform/param strings via `_parse_param_label` |
| V6 Cryptography | NO | No crypto on Browse |
| V7 Error Handling | YES | INFRA-02 HTMX error handler routes 4xx/5xx to `#htmx-error-container` |
| V8 Logging | NO | Phase out of scope |
| V12 Files & Resources | NO | No file I/O |

### Known Threat Patterns for FastAPI + HTMX + read-only EAV DB

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via repeated query key | Tampering | `fetch_cells_core` uses `sa.bindparam(..., expanding=True)` — already parameterized (verified `app/services/ufs_service.py:155-187`); no f-string interpolation |
| Reflected XSS via parameter label echoed in template | Tampering / Information disclosure | Jinja2 autoescape ON for `.html` templates; explicit `| e` on every cell (D-27); template never uses `| safe` for user-supplied content |
| HTML injection via PLATFORM_ID in checkbox label | Same | Same — autoescape covers it. Belt-and-suspenders: PLATFORM_ID matches `^[A-Za-z0-9_\-]{1,128}$` upstream (Phase 1) |
| Resource exhaustion via huge `?platforms=` list | DoS | Server-side caps: row_cap=200 + col_cap=30 are independent of input list size; `fetch_cells_core` LIMIT in SQL caps at 201 rows regardless. URL length capped by browser to ~8KB; even 500 PLATFORM_IDs at ~30 chars each = 15KB which exceeds typical browser limit |
| URL length DoS for shareable links | DoS | Browsers cap URL at ~8KB; PLATFORM_ID list of ~150 items with 30-char names + 30 param labels ≈ 6.5KB which fits. For 500-platform corner case, app should silently degrade — no special handling required |
| Path traversal via PLATFORM_ID | Tampering | Not applicable — Browse never reads files based on PLATFORM_ID |
| Open redirect | Tampering | Not applicable — no redirect routes |

**No new security primitives needed.** All defenses are inherited from existing infrastructure (parameterized SQL, autoescape, regex validation, HTMX error handler).

---

## Required Upstream Edits BEFORE Planning Starts

These follow from D-19..D-22 (BROWSE-V2-04 scope-out). The planner MUST treat these as Plan 04-00 prerequisites. **Skipping them leaves the traceability tables inconsistent.**

### Edit 1: `.planning/REQUIREMENTS.md`

- **Move BROWSE-V2-04** from "Browse Tab (Port)" Pending to "Out of Scope" with reason:
  ```
  Excel/CSV export under v2.0 shell — v1.0 Streamlit Browse remains the export surface
  until v1.0 sunset; v2.0 Browse is view-only by design choice (2026-04-26).
  ```
- **Update Traceability table** — remove the BROWSE-V2-04 → Phase 4 row.
- **Update Totals** — v2.0 Requirements: 46 → 45; Phase 4 mapped: 5 → 4 (`Phase 4: 5` → `Phase 4: 4`).

### Edit 2: `.planning/ROADMAP.md`

- **Phase 4 section: delete success criterion #3** (`"User can download the current pivot grid as Excel (.xlsx) or CSV..."`). Phase 4 success criteria become 3 items: filter swap + sticky header, caps mirror v1.0, URL round-trip.
- **Update Requirements line:** `**Requirements**: BROWSE-V2-01, BROWSE-V2-02, BROWSE-V2-03, BROWSE-V2-04, BROWSE-V2-05` → drop BROWSE-V2-04.

### Edit 3: `.planning/PROJECT.md`

- **Under "Browse carry-over (v2.0)" Active section**: the `[ ] Excel + CSV export` line moves to "Out of Scope" with reason.
- **Add to "Key Decisions" table**:
  ```
  | Drop v2.0 Browse export to keep the port view-only | Simpler shell migration; v1.0 Streamlit Browse still serves the export workflow until v1.0 sunset | ⚠️ Revisit at v1.0 sunset planning |
  ```

These edits are mechanical and do not require any code changes. They MUST happen before plan files are written, otherwise plan-04-XX-PLAN.md will reference 5 requirements while REQUIREMENTS.md tracks only 4.

---

## Sources

### Primary (HIGH confidence)
- `[VERIFIED]` `.venv` package versions (importlib.metadata) — fastapi 0.136.1, starlette 1.0.0, jinja2-fragments 1.12.0, pandas 3.0.2, cachetools 7.0.6, sqlalchemy 2.0.49, pymysql 1.1.2
- `[VERIFIED]` Source inspect of `jinja2_fragments.fastapi.Jinja2Blocks.TemplateResponse` — confirmed `block_names: list[str]` is the correct kwarg
- `[VERIFIED]` `app_v2/static/vendor/bootstrap/bootstrap.min.css` — `.table-responsive { overflow-x: auto }` (only); `.sticky-top { position: sticky; top: 0; z-index: 1020 }`
- `[VERIFIED]` `app_v2/static/vendor/bootstrap/VERSIONS.txt` — Bootstrap 5.3.8 (downloaded 2026-04-24)
- `[VERIFIED]` `app_v2/static/vendor/htmx/VERSIONS.txt` — HTMX 2.0.10 (pinned per CLAUDE.md "HTMX 4.0 is alpha")
- `[VERIFIED]` Empirical test of `Query(default_factory=list)` in research session — repeated keys, single key, empty key, URL-encoded middle-dot all parse correctly
- `[CITED]` https://htmx.org/docs/ — `hx-include` accepts CSS selectors, `hx-push-url` (attribute and `HX-Push-Url` response header), OOB swap matching by id
- `[CITED]` https://htmx.org/headers/hx-push-url/ — server response header overrides `hx-push-url` attribute
- `[CITED]` https://getbootstrap.com/docs/5.3/components/dropdowns/ — `data-bs-auto-close="outside"`, `bootstrap.Dropdown.getInstance(el).hide()`, dropdown events `show.bs.dropdown`/`hidden.bs.dropdown`
- `[CITED]` https://getbootstrap.com/docs/5.3/content/tables/ — `.table-striped`, `.table-hover`, `.table-sm` classes
- `[CITED]` https://fastapi.tiangolo.com/reference/parameters/ — `Query(default_factory=...)` for repeated query keys
- `[CITED]` https://jinja2-fragments.readthedocs.io/latest/ — Jinja2Blocks for FastAPI

### Secondary (MEDIUM confidence)
- `app/pages/browse.py:212-326` — v1.0 Pivot tab logic (semantic reference; v2.0 doesn't carry the parser literally because of D-13 separator change)
- `app/services/ufs_service.py:74-289` — `list_platforms_core`, `list_parameters_core`, `fetch_cells_core`, `pivot_to_wide_core` (reuse verbatim)
- `app_v2/services/cache.py:62-129` — `fetch_cells`, `list_platforms`, `list_parameters` wrapper pattern (reuse verbatim)
- `app_v2/routers/overview.py:271-308` — Phase 2 reference for `block_names=["filter_oob", "entity_list"]` rendering
- `app_v2/routers/platforms.py:1-80` — Phase 3 reference for sync `def` route + `Path(pattern=...)` + `app.state.db` access
- `app_v2/templates/overview/index.html` — reference for OOB swap pattern (`hx-swap-oob="true"` on a span at top of file)
- `tests/v2/test_phase03_invariants.py` — reference for codebase invariant guard test pattern (will be extended in Phase 04)

### Tertiary (LOW confidence — verified or noted as assumed)
- WebFetch of `https://getbootstrap.com/docs/5.3/content/tables/` claimed `.table-responsive` uses `overflow-y: hidden` — **incorrect for Bootstrap 5.3.8**; the installed CSS only sets `overflow-x: auto`. The claim was rejected via direct inspection of the vendored stylesheet. (Documents the WebFetch reliability caveat.)
- WebSearch results on multiselect patterns — used as background; D-07 made the decision authoritatively.

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — every version verified against installed `.venv`; no new deps
- Architecture (templates, routes, view-model): HIGH — patterns are direct extensions of Phase 02/03 idioms in app_v2/
- Pitfalls: HIGH for sticky-thead and HX-Push-Url (verified empirically); MEDIUM for popover restore-on-close (assumed, A3-A6)
- URL round-trip: HIGH — empirical FastAPI test in research session confirms repeated-key parsing + middle-dot encoding
- Reusable v1.0 modules: HIGH — pivot_to_wide_core / fetch_cells_core / list_platforms_core are pure functions with explicit unit-test coverage from Phase 1 (171 v1.0 tests pass)

**Research date:** 2026-04-26
**Valid until:** 2026-05-26 (30 days for stable stack); re-verify if FastAPI, jinja2-fragments, or Bootstrap rev a major version inside this window.

---

*Phase: 04-browse-tab-port*
*Researched: 2026-04-26*
*Source-of-truth for plan-04-XX-PLAN.md authors: this file + .planning/phases/04-browse-tab-port/04-CONTEXT.md (CONTEXT.md is authoritative on user decisions; this RESEARCH.md is authoritative on implementation idiom).*
