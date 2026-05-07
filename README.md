<!-- generated-by: gsd-doc-writer -->
# PBM2 — Platform Dashboard V1

Internal FastAPI + Bootstrap 5 + HTMX website for browsing and querying a large EAV-form MySQL parameter database (`ufs_data`) of UFS subsystem profiles across Android platforms — slice, pivot, filter, chart, and ask natural-language questions without writing SQL.

**Core value:** fast ad-hoc browsing of the parameter database. Even if the NL agent fails, the UI lets a non-SQL user (PMs, analysts) find the platforms and parameters they care about, see them in a wide-form grid, and read or compare. NL query rides on top — it does not replace browse.

---

## Status

| Milestone | Status | Tag | Tests |
|---|---|---|---|
| **v1.0 MVP** (Streamlit) | Shipped 2026-04-24 — sunset 2026-04-29 (quick task `260429-kn7`) | `v1.0` | 171 |
| **v2.0 Bootstrap Shell** (FastAPI + Bootstrap 5 + HTMX) | Shipped 2026-04-29 | `v2.0` | 506 |
| **Post-v2.0 phases** (JV auto-discovery, UI shell rewrite, Ask chat overhaul, UI Foundation) | Active | — | 594 (as of 2026-05-08) |

The Streamlit shell was removed in `260429-kn7`; `app_v2/` is the single source of truth. The v1.0 framework-agnostic core (`app/core/`, `app/adapters/`, `app/services/`) is reused by `app_v2/` via direct import.

---

## Stack

- **Web:** FastAPI + Bootstrap 5 + HTMX + Jinja2 + jinja2-fragments
- **DB:** SQLAlchemy 2.0 (sync) + pymysql, read-only user, single table `ufs_data`
- **Data:** pandas 3.x for client-side pivot / lazy per-query type coercion
- **NL agent:** PydanticAI 1.x with structured output and a single `run_sql` tool; chat agent uses `run_stream_events` + SSE for streamed thought / tool-call / tool-result events
- **LLM:** dual backend — OpenAI (cloud) and Ollama (local), user-switchable at runtime via `pbm2_llm` cookie set by the Ask-page `LLM` dropdown; `openai` SDK with different `base_url` covers both
- **Safety harness:** readonly DB user (primary backstop), `sqlparse` SELECT-only validator with UNION/CTE guards, LIMIT injector, path scrubber (`/sys/`, `/proc/`, `/dev/` — applied only when OpenAI active), `<db_data>` prompt-injection wrapper, step-cap, MySQL `max_execution_time` timeout, `allowed_tables=["ufs_data"]`
- **Markdown:** markdown-it-py with `js-default` preset (HTML passthrough off — XSS-safe)
- **Caching:** `cachetools.TTLCache` paired with `threading.Lock`
- **Joint Validation parsing:** BeautifulSoup4 + lxml on `content/joint_validation/<page_id>/index.html` Confluence exports
- **Auth:** deferred per locked decision D-04 (intranet, shared-credential model planned for re-enable in a pre-deployment phase)

---

## Quickstart

### Prerequisites

- Python 3.11+ (development uses 3.13)
- A MySQL instance with the `ufs_data` table (read-only credentials strongly recommended — the safety harness assumes the DB user cannot write)
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
cp config/presets.example.yaml config/presets.yaml             # Joint Validation filter presets
cp config/browse_presets.example.yaml config/browse_presets.yaml # Browse pivot presets
```

Edit `config/settings.yaml` to add at least one database (`databases:`) and one LLM backend (`llms:`). Set `OPENAI_API_KEY` in `.env` if using the OpenAI backend. The optional `app.conf_url` field is the base URL for the per-row Confluence "컨플" link button on the Joint Validation grid (empty string → button renders disabled).

### Run

```bash
uvicorn app_v2.main:app --port 8000 --reload
```

Opens at `http://localhost:8000`. Three top-nav tabs:

- `/` — **Joint Validation**: paginated grid of UFS validation reports auto-discovered from `content/joint_validation/<page_id>/index.html` drops; 5 popover-checklist multi-filters (Customer / AP Company / AP Model / Device / Controller / Application), sortable columns, fixed-group-of-10 pagination, per-row `edm` + `컨플` + `AI ✨` action buttons, detail page with iframe-sandboxed Confluence body
- `/browse` — **Platform 브라우저**: wide-form pivot grid (platforms × parameters), Platform + Parameter pickers (parameters depend on selected platforms), Swap axes + Highlight (minority-cell) toggles, clickable preset chips, `HX-Push-Url` shareable URLs
- `/ask` — **AI 질문하기**: agentic NL chat (PydanticAI tool loop, SSE streaming via `htmx-ext-sse`), 8-prompt starter chip gallery, NL-05 two-turn parameter confirmation, Ask-page `LLM: Ollama ▾` / `LLM: OpenAI ▾` dropdown writing the `pbm2_llm` cookie

### Test

```bash
.venv/bin/pytest tests/v2/                  # v2 suite (594 passing as of 2026-05-08)
.venv/bin/pytest tests/                     # full suite including v1.0 carry-overs
.venv/bin/pytest tests/ -m "not slow"       # skip cross-process race tests
```

---

## Repository layout

| Path | Purpose |
|---|---|
| `app_v2/` | FastAPI app (single source of truth) — `main.py`, `routers/`, `services/`, `templates/`, `static/` |
| `app/` | Framework-agnostic core reused by `app_v2/` — `app/core/config.py`, `app/core/agent/` (`nl_agent.py`, `nl_service.py`, `chat_agent.py`, `chat_loop.py`, `chat_session.py`), `app/adapters/db/` + `app/adapters/llm/`, `app/services/` (`sql_validator.py`, `sql_limiter.py`, `path_scrubber.py`, `result_normalizer.py`, `ufs_service.py`) |
| `tests/v2/` | v2.0+ test suite (594 cases) — routes, services, invariants, race tests, JV parser |
| `tests/agent/`, `tests/services/`, `tests/adapters/` | Framework-agnostic core tests |
| `config/` | YAML configs — `settings.yaml`, `starter_prompts.yaml`, `presets.yaml` (JV), `browse_presets.yaml` (Browse pivot); examples committed, real files gitignored |
| `content/platforms/` | Per-platform markdown content pages (gitignored; `.gitkeep` retained) |
| `content/joint_validation/<page_id>/` | Confluence export drops (`index.html` + assets); auto-discovered by `joint_validation_store.py` |
| `scripts/seed_demo_db.py` | SQLite demo-data seeder for UAT testing |
| `.planning/` | GSD workflow artifacts — `PROJECT.md`, `STATE.md`, milestone roadmaps, phase contexts/plans/summaries/reviews, quick-task records |
| `CLAUDE.md` | Project conventions and tech-stack constraint table |

---

## Architecture (high level)

```
┌──────────────────────────────────────────────────────────┐
│  app_v2/                            FastAPI + HTMX shell │
│   ├─ main.py            (lifespan: settings, DBAdapter,  │
│   │                      agent_registry, chat_turns,     │
│   │                      chat_sessions, static mounts)   │
│   ├─ routers/           overview (= JV listing at /),    │
│   │                     joint_validation, browse, ask,   │
│   │                     platforms, summary, settings,    │
│   │                     components (UI showcase), root   │
│   ├─ services/          browse_service, joint_validation │
│   │                     _{store,parser,grid_service,     │
│   │                     summary}, summary_service,       │
│   │                     llm_resolver, content_store,     │
│   │                     {browse_,}preset_store, cache    │
│   ├─ templates/         Jinja2 + jinja2-fragments        │
│   └─ static/            vendored Bootstrap 5, HTMX,      │
│                         htmx-ext-sse, Plotly,            │
│                         Bootstrap Icons (no CDN)         │
├──────────────────────────────────────────────────────────┤
│  app/                               Framework-agnostic   │
│   ├─ core/config.py     Pydantic Settings (DatabaseCfg,  │
│   │                     LLMConfig, AgentConfig)          │
│   ├─ core/agent/        nl_agent (legacy single-turn) +  │
│   │                     chat_agent + chat_loop +         │
│   │                     chat_session (multi-turn SSE)    │
│   ├─ adapters/db/       MySQLAdapter (+ SQLite for UAT)  │
│   ├─ adapters/llm/      openai SDK with base_url switch  │
│   └─ services/          sql_validator, sql_limiter,      │
│                         path_scrubber, result_normalizer │
└──────────────────────────────────────────────────────────┘
```

Both the NL single-turn agent and the multi-turn chat agent reach the DB through `app/services/ufs_service.py`, whose table allow-list is sourced from `settings.app.agent.allowed_tables`. The agent has exactly one tool (`run_sql`) — no schema inspector — so the safety harness has a single chokepoint.

---

## Conventions worth knowing

- All DB-touching FastAPI routes use `def` (not `async def`) — sync SQLAlchemy + threadpool dispatch (decision INFRA-05)
- `app_v2/` reuses `app/core/` and `app/adapters/` by **import**, never copy
- Markdown rendered with `MarkdownIt("js-default")` only — never the default constructor (HTML passthrough is XSS-prone)
- File writes go through `app_v2/data/atomic_write.py::atomic_write_bytes` (tempfile + `os.fsync` + `os.replace`)
- Path traversal defended at two layers: FastAPI `Path(pattern=...)` + `pathlib.Path.resolve()` + `relative_to()`
- LLM exception taxonomy mapped to a fixed 8-string user-facing vocabulary at the service boundary; raw exception text never crosses the boundary
- Result coercion is **lazy and per-query** — the same `Item` legitimately appears hex on one platform and decimal on another (see `result_normalizer.py`)
- Locked decisions and invariants are guarded by `tests/v2/test_phase0{2,3,4}_invariants.py` and `test_phase03_chat_invariants.py` — grep-style assertions that fail any future PR violating them
- The project uses the **GSD workflow** — see `CLAUDE.md` and `.planning/PROJECT.md` for entry-point commands (`/gsd-quick`, `/gsd-debug`, `/gsd-execute-phase`)

---

## Out of scope (locked)

- Admin data ingestion / Excel upload — DB is read-only by contract; writes belong upstream
- Per-user SSO — intranet shared-credential model planned
- Public-internet deployment / auth hardening — intranet only
- Multi-table or cross-table joins — single-table EAV `ufs_data` is the entire domain
- Editing platform data from the UI — read-only
- Training / fine-tuning an in-house LLM — adapters cover OpenAI cloud and Ollama local
- v2.0 Browse Excel/CSV export — v2.0 Browse is view-only by design (any future export will be v2.0-native, not a Streamlit revival)

---

## License

Internal project. Not for redistribution.
