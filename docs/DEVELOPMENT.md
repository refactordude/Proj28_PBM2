<!-- generated-by: gsd-doc-writer -->
# Development

This document covers the local development workflow for PBM2 (Platform Dashboard V1):
how to set up a working tree, the build / lint / test commands that exist today, and the
conventions you must follow when adding routes, services, HTMX out-of-band swaps, or
new tabs. For first-run instructions and the high-level component map, see the
project root [`README.md`](../README.md) and [`docs/ARCHITECTURE.md`](ARCHITECTURE.md).
For the test loop in detail (markers, fixtures, race tests), see
[`docs/TESTING.md`](TESTING.md).

---

## Local setup

PBM2 has no `pyproject.toml`, no `setup.py`, and no compile step — the project is a
plain `requirements.txt`-driven FastAPI application. Setup is three commands plus
copying a handful of YAML examples.

```bash
# 1. Clone and enter the working tree
git clone <repo-url> Proj28_PBM2
cd Proj28_PBM2

# 2. Create a virtualenv and install runtime + dev dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest                # not pinned in requirements.txt; install ad-hoc

# 3. Bootstrap configuration
cp .env.example .env
cp config/settings.example.yaml      config/settings.yaml
cp config/starter_prompts.example.yaml config/starter_prompts.yaml
cp config/presets.example.yaml       config/presets.yaml          # JV preset chips
cp config/browse_presets.example.yaml config/browse_presets.yaml  # Browse preset chips
```

`config/settings.yaml`, `config/auth.yaml`, `config/starter_prompts.yaml`,
`config/presets.yaml`, `config/browse_presets.yaml`, and `config/overview.yaml` are
gitignored — they hold plaintext credentials per locked decision D-11. The
`*.example.yaml` files are tracked. Edit `config/settings.yaml` to add at least one
`databases:` entry and one `llms:` entry; full schema in
[`docs/CONFIGURATION.md`](CONFIGURATION.md).

`OPENAI_API_KEY` only needs to be set in `.env` if you want the OpenAI LLM backend.
The application code does not call `load_dotenv()` itself; preload `.env` into the
process before launching uvicorn (e.g., `set -a; source .env; set +a; uvicorn ...`).

Python 3.11+ is required (the `app_v2/` codebase uses `from __future__ import
annotations` plus `list[str] | None` syntax). Development is done on Python 3.13.

### Run the dev server

```bash
.venv/bin/uvicorn app_v2.main:app --port 8000 --reload
```

`--reload` watches the working tree and restarts on file changes. The app mounts
on `http://localhost:8000`. Routes:

| Path | Tab | Owner |
|---|---|---|
| `/` and `/overview` | Joint Validation | `app_v2/routers/overview.py` |
| `/browse` | Platform 브라우저 (pivot grid) | `app_v2/routers/browse.py` |
| `/ask` | AI 질문하기 (NL chat + SSE) | `app_v2/routers/ask.py` |
| `/joint_validation/{page_id}` | JV detail iframe | `app_v2/routers/joint_validation.py` |
| `/platforms/{pid}` and `/platforms/{pid}/summary` | Platform pages + AI Summary | `app_v2/routers/platforms.py`, `summary.py` |
| `/settings/llm` | LLM cookie write | `app_v2/routers/settings.py` |
| `/_components` | Internal UI showcase (dev-only) | `app_v2/routers/components.py` |
| `/docs` | FastAPI auto-generated OpenAPI | (built-in) |

Static assets (vendored Bootstrap 5.3.8, HTMX 2.0.10, htmx-ext-sse, Bootstrap Icons
1.13.1, Plotly) live in `app_v2/static/` and are served without CDN — intranet
deployments need no outbound internet (INFRA-04).

### Seed a demo database (optional)

`scripts/seed_demo_db.py` creates a SQLite database populated with synthetic
`ufs_data` rows for UAT testing without a real MySQL instance. Run it once and
point a `databases:` entry in `config/settings.yaml` at the produced SQLite file.

---

## Build / run / test commands

There is no `Makefile`, no `pyproject.toml` `[project.scripts]`, and no top-level
runner script. The full set of commands is:

| Command | Purpose |
|---|---|
| `pip install -r requirements.txt` | Install runtime + framework dependencies (fastapi, uvicorn, jinja2, jinja2-fragments, sqlalchemy, pydantic-ai, openai, beautifulsoup4, lxml, ...) |
| `pip install pytest` | Install the test runner — pytest is **not** in `requirements.txt`; install ad-hoc |
| `uvicorn app_v2.main:app --port 8000 --reload` | Start the dev server with auto-reload |
| `uvicorn app_v2.main:app --port 8000` | Start without auto-reload (closer to deployment behavior) |
| `.venv/bin/pytest tests/v2/` | Run the v2 suite (594 cases as of 2026-05-08) |
| `.venv/bin/pytest tests/` | Full suite including framework-agnostic core tests under `tests/agent/`, `tests/services/`, `tests/adapters/` |
| `.venv/bin/pytest tests/ -m "not slow"` | Skip multiprocessing / cross-process race tests (the `slow` marker is registered in `tests/v2/conftest.py`) |
| `python scripts/seed_demo_db.py` | Generate a SQLite demo DB for UAT testing |

There are no separate `lint`, `format`, `typecheck`, `build`, `release`, or `clean`
commands — they don't exist in this repository today.

---

## Code style

<!-- VERIFY: ruff is recommended in CLAUDE.md "Recommended Stack" but no .ruff.toml, ruff.toml, or pyproject.toml [tool.ruff] config is present in the repo; the project does not currently enforce ruff -->
<!-- VERIFY: mypy is recommended in CLAUDE.md but no mypy.ini, .mypy.ini, or pyproject.toml [tool.mypy] is present; mypy is not currently run -->
<!-- VERIFY: no .pre-commit-config.yaml exists in the repo; pre-commit hooks are not currently installed -->
<!-- VERIFY: no .editorconfig exists in the repo -->

The repository ships **no automated formatter or linter configuration**. The
`CLAUDE.md` "Recommended Stack" table names `ruff` and `mypy` as the intended
tools, but neither is wired up: there is no `pyproject.toml`, no `.ruff.toml`, no
`mypy.ini`, and no `.pre-commit-config.yaml`. Style conformance is enforced by
review and by the test-driven invariants under `tests/v2/test_phase0{2,3,4}_invariants.py`
and `tests/v2/test_phase03_chat_invariants.py` — these are grep-style assertions
that fail any PR violating a locked decision.

The cache directories `.ruff_cache/` and `.mypy_cache/` **are** listed in
`.gitignore` (anticipating future adoption), but as of 2026-05-08 those tools are
not part of the developer loop.

### In-repo conventions enforced by code & tests

The conventions below are not enforced by a linter — they are enforced by hand-written
assertions in the invariant test files and by review. Violating one will typically
break a test in `tests/v2/test_phase0*_invariants.py`.

- **Sync `def` for routes (INFRA-05 / D-34).** All FastAPI route handlers in
  `app_v2/routers/` use `def`, never `async def`. SQLAlchemy is sync, and FastAPI
  dispatches `def` routes to the threadpool. Adding `async def` to a route silently
  blocks the event loop on the first DB call.
- **Pydantic v2 only.** Pinned via `pydantic>=2.7` in `requirements.txt`; never
  mix v1 and v2 models. v2 idioms in active use: `Annotated[..., Field(...)]`,
  `model_validate`, `model_dump`, `Query(default_factory=list)` (note the v2.13.x
  + FastAPI 0.136.x rule: `default_factory=list` and `= []` cannot both appear on
  the same parameter — use `default_factory` for `Query()` and the literal `= []`
  for `Form()`; see comments in `app_v2/routers/browse.py:60-65` and
  `app_v2/routers/overview.py:120-127`).
- **SQLAlchemy 2.0 Core, no ORM.** Use `sa.text(...)` with parameter binding via
  `sa.bindparam(..., expanding=True)`; never construct SQL by string formatting.
  Engine is created once in the DB adapter and reused. The single-table EAV model
  (`ufs_data`) makes the ORM unnecessary.
- **`openai` SDK as the dual LLM client.** Both OpenAI and Ollama traffic flows
  through `openai.OpenAI(base_url=..., api_key=...)`. Do not add `litellm` or
  any other LLM router — the CLAUDE.md "What NOT to Use" list explicitly forbids
  it. Ollama uses the OpenAI-compatible `/v1` base URL.
- **Markdown via `MarkdownIt("js-default")` only.** Never the default constructor —
  HTML passthrough is XSS-prone for user-supplied markdown.
- **Atomic file writes** through `app_v2/data/atomic_write.py::atomic_write_bytes`
  (tempfile + `os.fsync` + `os.replace`). Never write to `content/` or `config/`
  with a plain `open(..., "w")`.
- **Path traversal defense at two layers.** FastAPI `Path(pattern=...)` validates
  the URL segment; `pathlib.Path.resolve()` + `relative_to()` validates the
  resolved filesystem path before any read/write.
- **`app_v2/` reuses `app/core/` and `app/adapters/` by import — never copy.**
  Anything framework-agnostic (config loader, DB adapter, NL agent, service-layer
  validators) lives under `app/`. FastAPI/Starlette imports are forbidden in
  `app/services/` and `app/adapters/`.
- **GSD workflow.** Use `/gsd-quick`, `/gsd-debug`, or `/gsd-execute-phase` to
  start work. Direct edits without a GSD entry point break the planning ↔
  execution sync expected by `.planning/STATE.md`. See `CLAUDE.md` "GSD Workflow
  Enforcement".

---

## Branch and commit conventions

The repo currently has these branches (as of 2026-05-08): `master` (default),
`ui-improvement`, `feature/post-v2.1`, `feature/post-v2.1-pr`, plus remote-only
`release/v2.1` and `docs/drift-sweep-2026-05-02`. There is no PR template
(`.github/PULL_REQUEST_TEMPLATE.md`) and no `CONTRIBUTING.md` — branch naming and
PR mechanics are governed by the GSD planning workflow rather than a standalone
checklist.

### Commit message format

Recent commit history follows a **Conventional-Commits-flavored** convention with a
trailing GSD quick-task tag:

```
<type>(<scope>): <subject> [quick-<YYMMDD-xxx>]
```

Verified examples from `git log`:

```
fix(ask): bump user + assistant message fonts +2 (...) [quick-260508-...]
fix(browse): Korean empty-state copy — '비교할 Platforms의 Parameters를 선택해 주세요...'
docs(quick-260508-099): rebrand browser <title> to Platform Dashboard V1
test(quick-260508-099): align v2 wordmark + title-suffix assertions with rebrand
feat(ui): rename Browse/Ask page headings to Korean labels [quick-260508-01a]
```

Common `<type>` prefixes seen in history: `feat`, `fix`, `docs`, `test`, `chore`.
The quick-task ID (`260508-099` etc.) cross-references the entry under
`.planning/quick/<id>-<slug>/` where the plan and summary live.

---

## How to add a new tab / route

The tabs visible in the topbar are owned by routers under `app_v2/routers/`. Adding
a new tab is a four-file change:

1. **Create the router module** at `app_v2/routers/<name>.py`. Use the pattern from
   `app_v2/routers/browse.py` or `overview.py`:

   ```python
   from fastapi import APIRouter, Request
   from app.adapters.db.base import DBAdapter
   from app_v2.templates import templates

   router = APIRouter()

   def get_db(request: Request) -> DBAdapter | None:
       return getattr(request.app.state, "db", None)

   @router.get("/<name>", response_class=HTMLResponse)
   def page(request: Request, db: DBAdapter | None = Depends(get_db)):
       ctx = {"active_tab": "<name>", "page_title": "..."}
       return templates.TemplateResponse(request, "<name>/index.html", ctx)
   ```

   Use `def`, not `async def` (INFRA-05).

2. **Register the router in `app_v2/main.py`.** Add the import in the bottom block
   (the imports are at the bottom by design — see comment at `app_v2/main.py:188`)
   and call `app.include_router(<name>.router)`. Order matters when two routers
   share a prefix or a wildcard — see the `summary` AFTER `platforms` ordering note
   and the "ask + settings registered BEFORE root" defense-in-depth note in
   `main.py:188-197`.

3. **Add the template directory** under `app_v2/templates/<name>/` with at least
   `index.html` extending `base.html`. The `active_tab` value passed in the route's
   `ctx` is consumed by `_components/topbar.html` to highlight the correct tab; if
   the new tab should appear in the topbar itself, edit
   `app_v2/templates/_components/topbar.html`.

4. **Write the route tests** under `tests/v2/test_<name>_routes.py`. Mirror the
   shape of `tests/v2/test_browse_routes.py` (TestClient, assertion against
   response.status_code and rendered HTML fragments).

If the new tab queries the database, add a thin service module under
`app_v2/services/<name>_service.py` with a `build_view_model(...)` function that
takes the `DBAdapter`, the `db_name` (for cache partitioning), and the inbound
filter parameters; route handlers should never call `engine.connect()` directly.

---

## How to add a new HTMX OOB swap

Out-of-band (OOB) swaps are the project's primary mechanism for updating multiple
DOM regions from a single HTMX response — count badges, picker badges, pagination
controls, the parameters picker slot, and so on. The pattern is implemented with
**`jinja2-fragments`** (`Jinja2Blocks` from `jinja2_fragments.fastapi`, configured
in `app_v2/templates/__init__.py`) and a small set of tightly-scoped conventions.

### The mechanic

1. The OOB target lives in the persistent shell (the part of the page **not**
   replaced by the primary HTMX swap). For example, on `/browse` the
   `#grid-count` span lives in `.panel-footer` (inside `index.html` but **outside**
   `#browse-grid`), so the primary `innerHTML` swap on `#browse-grid` never
   destroys it. This is **Pitfall 7** — "stable OOB target": OOB receivers must
   be in DOM that survives the primary swap.

2. The response template defines a named Jinja block whose body is a single element
   carrying both the matching `id` and `hx-swap-oob="true"`:

   ```jinja
   {% block count_oob %}
     <span id="grid-count" hx-swap-oob="true" class="text-muted small" aria-live="polite">
       {% if not vm.is_empty_selection %}{{ vm.n_rows }} platforms &times; {{ vm.n_cols }} parameters{% endif %}
     </span>
   {% endblock count_oob %}
   ```

   **The block must be defined OUTSIDE `{% block content %}`** (at the file's top
   level, after the `{% endblock content %}`). If you nest it inside `content`,
   the full-page GET render of the same template will emit a duplicate `#grid-count`
   span outside the panel. See the comments at `app_v2/templates/browse/index.html:120-124`
   and `163-167` for the canonical statement of this rule (the "DEFINED OUTSIDE
   `{% block content %}` so jinja2-fragments can render this block in isolation"
   pattern).

3. The route handler renders **only** the named blocks the response should carry,
   by passing `block_names=[...]` to `templates.TemplateResponse`:

   ```python
   block_names = ["grid", "count_oob", "warnings_oob", "picker_badges_oob"]
   if origin != "params":
       block_names.append("params_picker_oob")
   response = templates.TemplateResponse(
       request,
       "browse/index.html",
       ctx,
       block_names=block_names,
   )
   response.headers["HX-Push-Url"] = _build_browse_url(...)
   return response
   ```

   The first entry in `block_names` is the **primary** swap target (`grid` swaps
   into `#browse-grid` via `hx-target` on the form); every subsequent entry is an
   OOB block that HTMX detaches from the response and merges into the matching
   `id` in the persistent shell.

4. The `hx-target` / `hx-swap` attributes on the **client-side** form or button
   point at the primary block's host element — `#browse-grid` for the Browse grid,
   `#overview-grid` for the JV grid, etc. The OOB merges happen automatically
   wherever HTMX finds elements with `hx-swap-oob` in the response body.

### The four invariants

These four rules are enforced by review and by the invariant tests in
`tests/v2/test_phase0{2,3,4}_invariants.py` — break one and CI fails.

1. **Stable OOB target (Pitfall 7).** The receiver `id` must live in a part of the
   DOM that the primary swap does **not** replace. For Browse, `#grid-count` lives
   in `.panel-footer` outside `#browse-grid`. For Overview, picker badges live in
   `.browse-filter-bar` outside `#overview-grid`.

2. **OOB blocks defined outside `{% block content %}`.** This is the
   `jinja2-fragments` rule that prevents OOB markup from leaking into the full-page
   GET render. See the long-form comments at `app_v2/templates/browse/index.html:120-124`
   and `app_v2/templates/browse/index.html:148-153`.

3. **Form association for off-form inputs (Pitfall 4).** Checkboxes inside Bootstrap
   dropdown menus are NOT children of the visible filter form (Bootstrap reparents
   the dropdown), so they need an explicit `form="<form-id>"` attribute. The Browse
   tab declares an empty `<form id="browse-filter-form">` BEFORE the filter bar
   include and points every dropdown checkbox at it via `form="browse-filter-form"`.
   See `app_v2/templates/browse/index.html:34-37`.

4. **Sticky-thead requires a vertical-scroll container (Pitfall 1).** `<thead
   class="sticky-top">` only engages when the **table's nearest scrollable
   ancestor** is a vertical-scroll container — for Browse this is the
   `.browse-grid-body` div with `max-height: 70vh`. Putting the table at the bottom
   of `<main>` with body-level scroll defeats sticky-thead silently.

### When to skip an OOB block

Sometimes a block must be conditionally omitted from the response — see
`app_v2/routers/browse.py:152-158` (the `_origin` form field hotfix `260429-qyv`):
when the user is toggling a checkbox **inside** the Parameters popover, emitting
`params_picker_oob` would replace `#params-picker-slot` (including its open
dropdown menu) and abruptly close the popover. The route reads the `_origin` form
field (set by `hx-vals='{"_origin": "<name>"}'` on the picker macro) and skips
`params_picker_oob` when `origin == "params"`. Use the same pattern for any future
"swap me except when I'm the trigger" cases.

### `HX-Push-Url` for shareable URLs (Pitfall 2)

When a POST returns OOB blocks, set `HX-Push-Url` on the response to the canonical
GET URL, **not** the POST URL. Otherwise the address bar shows `/browse/grid` and
reload returns 405. The Browse and Overview routers both use a `_build_*_url`
helper that emits the same URL the GET handler accepts; see
`app_v2/services/browse_service.py::_build_browse_url` and
`app_v2/routers/overview.py::_build_overview_url`.

---

## Test loop

Run the v2 suite with `.venv/bin/pytest tests/v2/`. The full suite is
`.venv/bin/pytest tests/`. Use `-m "not slow"` to skip multiprocessing / fork
race tests (slow marker registered in `tests/v2/conftest.py`).

For test framework details, fixtures, naming conventions, and the invariant-test
pattern, see [`docs/TESTING.md`](TESTING.md).

---

## Pre-commit hooks

<!-- VERIFY: no .pre-commit-config.yaml exists in the repo as of 2026-05-08 — pre-commit hooks are not currently installed -->

PBM2 does not currently use pre-commit. There is no `.pre-commit-config.yaml`,
no `.husky/`, and no `.git/hooks/` config managed by the repo. The CLAUDE.md
"Recommended Stack" suggests `ruff` for linting/formatting, but it has not been
adopted yet — gating happens via the `tests/v2/test_phase0*_invariants.py` files
during CI/local pytest runs rather than via a commit-time hook.
