# PBM2

Internal parameter browser for the `ufs_data` MySQL database — an EAV-form catalog of UFS subsystem profiles across Android platforms. The app lets non-SQL users (PMs, analysts) slice, pivot, filter, chart, and export the long-form data, and ask natural-language questions on top, without writing SQL or learning the schema.

**Core value:** fast ad-hoc browsing. Even if the NL agent fails, the UI lets a non-SQL user find the platforms and parameters they care about, see them in a wide-form grid, and export. NL query rides on top — it does not replace the browse experience.

---

## Status

| Milestone | Status | Stack | Notes |
|---|---|---|---|
| **v1.0 MVP** | Shipped 2026-04-24 | Streamlit + SQLAlchemy + PydanticAI | 171 passing tests, 87 commits over 2 days. Browse + Ask + Settings. |
| **v2.0 Bootstrap Shell** | Shipped 2026-04-29 | FastAPI + Bootstrap 5 + HTMX + Jinja2 | 526 passing tests. 6 phases: Foundation → Overview → Content/AI Summary → Browse → Overview Redesign → Ask. |

`app_v2/` is the single UI. v1.0 Streamlit shell removed in quick task 260429-kn7; `app/` retains only the framework-agnostic core/adapters/services consumed by `app_v2/`.

---

## Stack

- **Web:** FastAPI 0.136 + Bootstrap 5.3.8 + HTMX 2.0.10 + Jinja2 + jinja2-fragments
- **DB:** SQLAlchemy 2.0 (sync) + pymysql, read-only user, single table (`ufs_data`)
- **Data:** pandas 3.x for client-side pivot / coercion / export, openpyxl for Excel
- **NL agent:** PydanticAI 1.x with structured output, `openai` SDK with `base_url` switching between OpenAI Cloud and Ollama
- **Safety harness:** `sqlparse` SELECT-only validator, LIMIT injector, path scrubber, `<db_data>` prompt-injection wrapper, step-cap, MySQL `max_execution_time` timeout
- **Markdown (v2.0):** markdown-it-py with `js-default` preset (HTML passthrough off — XSS-safe)
- **Caching:** `cachetools.TTLCache` paired with `threading.Lock`
- **Auth:** Deferred to pre-deployment phase (D-04); `streamlit-authenticator` removed in 260429-kn7. Credential strategy TBD when auth is re-enabled.

---

## Quickstart

### Prerequisites
- Python 3.13
- A MySQL instance with `ufs_data` (read-only credentials recommended — the safety harness assumes the DB user cannot write)
- Optional: [Ollama](https://ollama.com/) running locally on `http://localhost:11434` for offline NL queries

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
cp config/settings.example.yaml config/settings.yaml
cp config/starter_prompts.example.yaml config/starter_prompts.yaml
# v2.0 only:
cp config/overview.example.yaml config/overview.yaml
```

Edit `config/settings.yaml` to add at least one database (`databases:`) and one LLM backend (`llms:`). Set `OPENAI_API_KEY` in `.env` if using OpenAI.

### Run

```bash
uvicorn app_v2.main:app --port 8000 --reload
```

Opens at `http://localhost:8000`. Overview / Browse / Ask tabs all live.

### Test

```bash
.venv/bin/pytest tests/                 # full suite (526 passing as of v2.0)
.venv/bin/pytest tests/v2/ -v           # v2.0 only
.venv/bin/pytest tests/ -m "not slow"   # skip cross-process race tests (Linux/macOS only)
```

---

## What works today

### v2.0 (FastAPI + Bootstrap) — `app_v2/`

- **Phase 1 — Foundation:** FastAPI shell with vendored Bootstrap/HTMX/Bootstrap Icons (no CDN), `def`-only DB-touching routes (sync SQLAlchemy + threadpool), `app_v2/services/cache.py` TTLCache wrappers, base template + 404/500 pages
- **Phase 2 — Overview tab:** curated watchlist at `config/overview.yaml`, HTMX add / remove, HTMX-swapped Brand / SoC / Year / Has-content filters with OOB filter-count badge, brand/SoC/year metadata badges per row, atomic YAML writes with `os.replace` + `os.fsync`, threading.Lock for concurrent add/remove
- **Phase 3 — Content pages + AI Summary:**
  - Markdown content at `content/platforms/<PLATFORM_ID>.md` (gitignored except `.gitkeep`)
  - `/platforms/<id>` detail page with rendered markdown OR empty-state Add Content
  - HTMX edit view with Bootstrap nav-pills Write / Preview tabs, debounced 500ms preview re-render, atomic save via `tempfile + fsync + os.replace`, client-side Cancel via `data-cancel-html` (no server round-trip)
  - AI Summary button on Overview row (enabled when content exists) and detail page header — violet `.ai-btn` pill matching the Dashboard reference
  - `cachetools.TTLCache(maxsize=128, ttl=3600)` keyed by `(platform_id, mtime_ns, llm_name, llm_model)` — avoids stale results on same-second edits via integer-nanosecond mtime
  - `X-Regenerate: true` header bypasses cache lookup but writes back
  - Classified 8-string error vocabulary (network / timeout / auth / rate-limit / 5xx / missing / fallback / not-configured) — route NEVER returns 5xx, always 200 with inline alert + Retry
  - Two-layer path-traversal defense: FastAPI `Path(pattern=^[A-Za-z0-9_\-]{1,128}$)` + `Path.resolve()` + `relative_to()`
  - Cross-process race test using `multiprocessing.get_context("fork")` — proves `os.replace` atomicity on POSIX

- **Phase 4 — Browse tab:** Pivot grid ported to Bootstrap; popover-search.js; `HX-Push-Url` URL round-trip; Parameters filter depends on selected Platforms (server-side intersection, OOB picker refresh)
- **Phase 5 — Overview Redesign:** Sortable Bootstrap table + 6 popover-checklist multi-filters; AI Summary modal; Link button with URL sanitizer; frontmatter properties table on detail page
- **Phase 6 — Ask tab:** NL agent ported under FastAPI/HTMX; NL-05 two-turn confirmation; Ask-page-only LLM dropdown with `pbm2_llm` cookie; 8 starter chips; v1.0 Streamlit Ask deleted

---

## Architecture

```
┌─────────────────────────────┐
│  app/             shared    │  ←  Framework-agnostic library modules
│   ├─ adapters/    (DB, LLM) │      Streamlit shell removed in 260429-kn7;
│   ├─ core/        (config,  │      core/adapters/services consumed by app_v2/.
│   │   agent, safety)        │
│   └─ services/   (normaliz- │
│       er, validator, etc.)  │
├─────────────────────────────┤
│  app_v2/          v2.0      │  ←  FastAPI + Bootstrap + HTMX (single UI)
│   ├─ main.py      (lifespan │      Reuses app/core/* and app/adapters/* directly.
│   │   loads settings, DB,   │
│   │   agent registry)       │
│   ├─ routers/     (overview,│
│   │   platforms, browse,    │
│   │   ask, summary)         │
│   ├─ services/    (content, │
│   │   summary, llm_resolver,│
│   │   cache)                │
│   ├─ data/        (atomic_  │
│   │   write, parser, lookup)│
│   ├─ templates/   (Jinja2 + │
│   │   jinja2-fragments)     │
│   └─ static/      (vendored │
│       Bootstrap/HTMX)       │
└─────────────────────────────┘
```

The app points at the `ufs_data` table via `MySQLAdapter`. It cannot write — the safety harness is rooted in DB-level read-only credentials.

---

## Project structure

| Path | Purpose |
|---|---|
| `app/` | Framework-agnostic shared modules (core, adapters, services) — imported by `app_v2/` |
| `app_v2/` | v2.0 FastAPI app (shipped 2026-04-29) |
| `tests/` | pytest suites — `tests/agent/`, `tests/v2/`, `tests/services/`, etc. |
| `config/` | YAML configs — `settings.yaml`, `overview.yaml`, `starter_prompts.yaml`, `auth.yaml` (gitignored, examples committed) |
| `content/platforms/` | Per-platform markdown content pages (gitignored, `.gitkeep` only) |
| `.planning/` | Project planning artifacts — phases, roadmap, requirements, research, plans, summaries, verifications, code reviews. See [`.planning/ROADMAP.md`](.planning/ROADMAP.md) for milestone progress. |
| `.gsd/` (in `~/.claude/`) | The GSD harness drives the development workflow — discuss-phase → plan-phase → execute-phase → verify → review |

---

## Development

This project is built using the **GSD workflow** (Get Shit Done) — a Claude-Code-native process where each phase goes through `discuss → plan → execute → verify → code review → UI review`. All planning and verification artifacts live under `.planning/`.

v2.0 is complete. Run `/gsd-new-milestone` to define v2.1+ work when ready.

See [`.planning/ROADMAP.md`](.planning/ROADMAP.md) for milestone history and [`CLAUDE.md`](CLAUDE.md) for project conventions and tech-stack constraints.

### Test count trajectory

| Milestone | Tests passing |
|---|---|
| v1.0 ship | 171 |
| v2.0 Phase 1 done | 212 |
| v2.0 Phase 2 done | 290 |
| v2.0 Phase 3 done | 413 |
| v2.0 ship (all 6 phases + quick tasks) | **526** |

### Conventions worth knowing

- All DB-touching FastAPI routes use `def` (not `async def`) — sync SQLAlchemy + threadpool dispatch (decision INFRA-05)
- Markdown is rendered with `MarkdownIt("js-default")` only — never the default constructor (HTML passthrough is XSS-prone)
- `app_v2/services/cache.py` wrappers are named `list_platforms` / `list_parameters` / `fetch_cells` (no `cached_` prefix)
- File writes use `app_v2/data/atomic_write.py::atomic_write_bytes` (tempfile + `os.fsync` + `os.replace`) — single source of truth
- Path traversal defended at two layers: FastAPI `Path(pattern=...)` + `pathlib.Path.resolve()` + `relative_to()`
- LLM exception taxonomy is mapped to a fixed 8-string user-facing vocabulary at the service boundary; raw exception text never crosses the boundary
- Codebase invariants are guarded by `tests/v2/test_phase03_invariants.py` — grep-style assertions that fail any future PR violating a locked decision

---

## License

Internal project. Not for redistribution.
