# PBM2

Internal parameter browser for the `ufs_data` MySQL database — an EAV-form catalog of UFS subsystem profiles across Android platforms. The app lets non-SQL users (PMs, analysts) slice, pivot, filter, chart, and export the long-form data, and ask natural-language questions on top, without writing SQL or learning the schema.

**Core value:** fast ad-hoc browsing. Even if the NL agent fails, the UI lets a non-SQL user find the platforms and parameters they care about, see them in a wide-form grid, and export. NL query rides on top — it does not replace the browse experience.

---

## Status

| Milestone | Status | Stack | Notes |
|---|---|---|---|
| **v1.0 MVP** | Shipped 2026-04-24 | Streamlit + SQLAlchemy + PydanticAI | 171 passing tests, 87 commits over 2 days. Browse + Ask + Settings. |
| **v2.0 Bootstrap Shell** | Active — Phases 1–3 of 5 | FastAPI + Bootstrap 5 + HTMX + Jinja2 | 413 passing tests. Overview tab + curated watchlist + content pages + AI Summary live. Browse and Ask still pending. |

v1.0 is preserved as-is in `app/` for rollback. v2.0 lives in `app_v2/` and reuses framework-agnostic v1.0 modules (LLM client factory, NL agent, safety harness, result normalizer) by import — not copy.

---

## Stack

- **Web:** Streamlit (v1.0) / FastAPI 0.136 + Bootstrap 5.3.8 + HTMX 2.0.10 + Jinja2 + jinja2-fragments (v2.0)
- **DB:** SQLAlchemy 2.0 (sync) + pymysql, read-only user, single table (`ufs_data`)
- **Data:** pandas 3.x for client-side pivot / coercion / export, openpyxl for Excel
- **NL agent:** PydanticAI 1.x with structured output, `openai` SDK with `base_url` switching between OpenAI Cloud and Ollama
- **Safety harness:** `sqlparse` SELECT-only validator, LIMIT injector, path scrubber, `<db_data>` prompt-injection wrapper, step-cap, MySQL `max_execution_time` timeout
- **Markdown (v2.0):** markdown-it-py with `js-default` preset (HTML passthrough off — XSS-safe)
- **Caching:** `cachetools.TTLCache` paired with `threading.Lock`
- **Auth:** `streamlit-authenticator` scaffolded (intranet, shared-cred). Currently deferred per design decision; re-enable in a pre-deployment phase.

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

### Run v1.0 (Streamlit)

```bash
streamlit run app/main.py
```

Opens at `http://localhost:8501`. Browse / Ask / Settings tabs.

### Run v2.0 (FastAPI + Bootstrap)

```bash
uvicorn app_v2.main:app --port 8000 --reload
```

Opens at `http://localhost:8000`. Overview tab is fully wired through Phase 3 (curated watchlist, content pages, AI Summary). Browse and Ask still serve placeholder stubs until Phases 4–5 land.

### Test

```bash
.venv/bin/pytest tests/                 # full suite (413 passing as of v2.0 Phase 3)
.venv/bin/pytest tests/v2/ -v           # v2.0 only
.venv/bin/pytest tests/ -m "not slow"   # skip cross-process race tests (Linux/macOS only)
```

---

## What works today

### v1.0 (Streamlit) — `app/`

- **Browse:** wide-form pivot grid (platform × parameter), swap-axes, 30-column / 200-row caps, Plotly charts for numeric parameters, Excel + CSV export, shareable URL round-trip on filters
- **Ask:** PydanticAI NL agent with structured `SQLResult | ClarificationNeeded` output, NL-05 two-turn parameter confirmation, OpenAI/Ollama switch in sidebar, full safety harness, 8 starter prompts
- **Settings:** DB and LLM connection CRUD with per-row Test buttons

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

### Phase 4 (Browse) and Phase 5 (Ask) port the v1.0 features under the new shell. Not yet started.

---

## Architecture

```
┌─────────────────────────────┐
│  app/             v1.0      │  ←  Streamlit pages, components, services
│   ├─ pages/       (Browse,  │      Stays archived once v2.0 ports each tab.
│   │   Ask, Settings)        │
│   ├─ adapters/    (DB, LLM) │
│   └─ core/        (config,  │  ←  Framework-agnostic. Imported by both apps.
│       agent, safety,        │
│       result_normalizer)    │
├─────────────────────────────┤
│  app_v2/          v2.0      │  ←  FastAPI + Bootstrap + HTMX
│   ├─ main.py      (lifespan │      Reuses app/core/* and app/adapters/* directly.
│   │   loads settings, DB,   │
│   │   agent registry)       │
│   ├─ routers/     (overview,│
│   │   platforms, summary)   │
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

Both apps point at the same `ufs_data` table via the same `MySQLAdapter`. v2.0 cannot write — the safety harness is rooted in DB-level read-only credentials.

---

## Project structure

| Path | Purpose |
|---|---|
| `app/` | v1.0 Streamlit (shipped, frozen) |
| `app_v2/` | v2.0 FastAPI (active development) |
| `tests/` | pytest suites — `tests/agent/`, `tests/v2/`, `tests/services/`, etc. |
| `config/` | YAML configs — `settings.yaml`, `overview.yaml`, `starter_prompts.yaml`, `auth.yaml` (gitignored, examples committed) |
| `content/platforms/` | Per-platform markdown content pages (gitignored, `.gitkeep` only) |
| `.planning/` | Project planning artifacts — phases, roadmap, requirements, research, plans, summaries, verifications, code reviews. See [`.planning/ROADMAP.md`](.planning/ROADMAP.md) for milestone progress. |
| `.gsd/` (in `~/.claude/`) | The GSD harness drives the development workflow — discuss-phase → plan-phase → execute-phase → verify → review |

---

## Development

This project is built using the **GSD workflow** (Get Shit Done) — a Claude-Code-native process where each phase goes through `discuss → plan → execute → verify → code review → UI review`. All planning and verification artifacts live under `.planning/`.

To resume work autonomously after Phase 3:

```bash
/gsd-autonomous --from 4    # Phases 4-5 (Browse + Ask ports)
```

Or run individual phases:

```bash
/gsd-discuss-phase 4
/gsd-plan-phase 4
/gsd-execute-phase 4
```

See [`.planning/ROADMAP.md`](.planning/ROADMAP.md) for current phase status and [`CLAUDE.md`](CLAUDE.md) for project conventions and tech-stack constraints.

### Test count trajectory

| Milestone | Tests passing |
|---|---|
| v1.0 ship | 171 |
| v2.0 Phase 1 done | 212 |
| v2.0 Phase 2 done | 290 |
| v2.0 Phase 3 done | **413** |

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
