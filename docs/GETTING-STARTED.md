<!-- generated-by: gsd-doc-writer -->
# Getting Started

Your first five minutes with PBM2 — clone, install, point the app at a database, run `app_v2/`, and land on the Joint Validation tab. For configuration deep-dives (every environment variable, every YAML field, per-environment overrides), see `docs/CONFIGURATION.md`. For the wider system map and module breakdown, see `docs/ARCHITECTURE.md`.

> **Heads up:** `app_v2/` is the canonical entrypoint as of the v2.0 milestone (tag `v2.0`, 2026-04-29). The legacy Streamlit shell under `app/` is sunset — do **not** start it. The v2.0 FastAPI app reuses `app/core/` and `app/adapters/` by direct import.

---

## Prerequisites

Install these before cloning the repo:

- **Python `>=3.11`** — required by pandas 3.x (see `requirements.txt`); development uses Python 3.13.
- **MySQL** instance reachable from the host running the app, with a **read-only** user that has SELECT on the `ufs_data` table. The safety harness assumes the DB user cannot write — using a read-write user defeats one of the project's primary safety backstops.
  - For UAT or local exploration without a real MySQL, the repo ships `scripts/seed_demo_db.py` which writes a SQLite demo DB to `data/demo_ufs.db` (20 demo platforms, 12 base parameters across five tiers). See "First run with demo data" below.
- **Git** — for `git clone`.
- **Ollama** *(optional)* — only needed if you want the local LLM backend for the AI Summary feature or the Ask tab. Default is `http://localhost:11434` (matches `config/settings.example.yaml`). If you intend to use only OpenAI, skip Ollama and set `OPENAI_API_KEY`.
- **Outbound internet access** *(optional)* — required at runtime only if you call the OpenAI backend. The Bootstrap, HTMX, and Plotly assets are vendored under `app_v2/static/`, so the UI itself works on an air-gapped intranet.

`<!-- VERIFY: exact internal git remote URL -->` — substitute your team's clone URL in step 1 below.

---

## Installation steps

```bash
# 1. Clone the repository.
git clone <your-internal-remote-url> Proj28_PBM2
cd Proj28_PBM2

# 2. Create and activate a virtualenv (Python 3.11+).
python3 -m venv .venv
source .venv/bin/activate

# 3. Install runtime dependencies.
pip install -r requirements.txt
```

There is no `pyproject.toml` and no Makefile — `pip install -r requirements.txt` is the entire dependency install. Key pins (see `requirements.txt`): `fastapi>=0.136,<0.137`, `uvicorn[standard]>=0.32`, `sqlalchemy>=2.0,<2.1`, `pandas>=3.0`, `pydantic-ai>=1.0,<2.0`, `jinja2-fragments>=1.3`.

### Configure the app

Copy the four YAML examples and the env file, then edit `config/settings.yaml` for your DB and LLM:

```bash
cp .env.example .env
cp config/settings.example.yaml config/settings.yaml
cp config/starter_prompts.example.yaml config/starter_prompts.yaml
cp config/presets.example.yaml config/presets.yaml             # Joint Validation filter presets
cp config/browse_presets.example.yaml config/browse_presets.yaml # Browse pivot presets
```

Minimum edits to land on a working app:

1. **`config/settings.yaml` → `databases[0]`** — set `host`, `port`, `database`, `user`, `password` to a real MySQL with `ufs_data`. Keep `readonly: true`.
2. **`config/settings.yaml` → `llms[]`** — keep the two example backends; if you only have OpenAI, you can leave the Ollama entry in place (it is only used when selected from the Ask-page LLM dropdown).
3. **`config/settings.yaml` → `app.default_database`** must match the `name:` of the database entry you want loaded at startup (lifespan picks the first entry if no match is found).
4. **`.env` → `OPENAI_API_KEY=...`** — required only if you plan to use the OpenAI backend. Note: `app/core/config.py` does **not** call `load_dotenv()`; export the variable into the process environment before launching uvicorn (e.g., `set -a; source .env; set +a`). See `docs/CONFIGURATION.md` for the full env-var table.

---

## First run

With config in place, start the app from the repo root with the venv active:

```bash
uvicorn app_v2.main:app --port 8000 --reload
```

- `app_v2.main:app` — the FastAPI instance defined in `app_v2/main.py`.
- `--port 8000` — matches the project convention shown in the `app_v2/main.py` module docstring.
- `--reload` — auto-restart on code change; drop this flag for a non-dev run.

Open `http://localhost:8000` in your browser. You should see the **Joint Validation** listing tab (the overview router owns `GET /`). Two more top-nav tabs:

- `/browse` — Platform 브라우저 (wide-form pivot grid).
- `/ask` — AI 질문하기 (NL chat with SSE streaming; the in-page LLM dropdown writes the `pbm2_llm` cookie that selects OpenAI vs Ollama).

The lifespan hook in `app_v2/main.py` creates `content/platforms/` and `content/joint_validation/` automatically on first boot — no manual `mkdir` needed.

### First run with demo data (no MySQL required)

If you don't have MySQL handy and just want to see the UI light up:

```bash
python scripts/seed_demo_db.py
```

This writes `data/demo_ufs.db` (a SQLite file). Wire it into `config/settings.yaml` by adding a `type: sqlite` entry pointing at that file and setting `app.default_database` to its name. The framework-agnostic adapter layer under `app/adapters/db/` supports SQLite for UAT.

---

## Common setup issues

- **`uvicorn app.main:app` fails / serves the wrong app.** You're starting the legacy entry. The canonical target is `app_v2.main:app`. The `app/` directory still exists because v2.0 imports `app/core/` and `app/adapters/`, but it has no FastAPI shell.
- **`pip install` complains about Python version.** `pandas>=3.0` requires Python `>=3.11`. Check `python3 --version`; if it's older, install a newer Python (the project is developed against 3.13) and recreate the venv.
- **OpenAI calls fail with auth errors even though `.env` is filled.** The codebase does **not** auto-load `.env`. Either export the variables into the shell before running uvicorn (`set -a; source .env; set +a; uvicorn …`), or paste the key directly into `config/settings.yaml` under the matching `llms[].api_key` field. See `docs/CONFIGURATION.md` for details.
- **App starts but DB queries fail at request time.** `app_v2/main.py` lifespan deliberately tolerates a missing/unreachable database at startup (Phase 1 smoke-test concession) — it logs a warning and sets `app.state.db = None`. Routes that need the DB will fail later. Re-check `databases[0]` host/port/credentials in `config/settings.yaml` and that the user has `SELECT` on `ufs_data`.
- **`config/settings.yaml` not found.** `app/core/config.py` reads `SETTINGS_PATH` if set, else `config/settings.yaml` relative to the repo root. Confirm you ran `cp config/settings.example.yaml config/settings.yaml` (the real file is gitignored to keep credentials out of git).
- **Joint Validation tab is empty.** The grid is built from Confluence export drops at `content/joint_validation/<page_id>/index.html`. The directory is auto-created at startup but is intentionally empty until you drop in real exports. The `content/joint_validation/` tree in this repo (under git) contains sample exports if you cloned the working branch — otherwise it will be a freshly-created empty folder.
- **Ollama unreachable.** The app does not warm up Ollama at startup (deliberate deviation, see `app_v2/main.py` lifespan comment). The first Ask/AI Summary request that targets Ollama eats the cold-start latency, governed by a 60 s read timeout in `summary_service`. If `http://localhost:11434` is not running, requests fail with a mapped user-facing error string — switch the Ask-page dropdown to OpenAI to bypass.

---

## Next steps

- **Configuration reference:** `docs/CONFIGURATION.md` — every environment variable, every `settings.yaml` field, required vs optional, and per-environment guidance.
- **Architecture map:** `docs/ARCHITECTURE.md` — module boundaries, request flow from HTMX → router → service → adapter, and the safety harness chokepoint.
- **Conventions and contributor workflow:** `CLAUDE.md` (project root) — locked decisions, the GSD workflow entry points (`/gsd-quick`, `/gsd-debug`, `/gsd-execute-phase`), and stack constraints.
- **Tests:** the v2 suite lives at `tests/v2/`. Run with `.venv/bin/pytest tests/v2/` (594 cases as of 2026-05-08); add `-m "not slow"` to skip cross-process race tests.
