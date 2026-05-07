<!-- generated-by: gsd-doc-writer -->
# Testing

PBM2 is exercised by a `pytest`-based suite that runs the FastAPI app in-process via `fastapi.testclient.TestClient` (httpx under the hood — no live uvicorn server required). The DB and LLM layers are mocked at the import boundary so the suite runs without a MySQL instance, without an OpenAI key, and without an Ollama daemon.

## Test framework and setup

- **Framework:** `pytest` (Python 3.11+; the working `.venv` uses CPython 3.13).
- **Driver:** `fastapi.testclient.TestClient`, instantiated in a `with` block so the app's `lifespan` handler runs (settings load, DBAdapter wiring, agent registry, chat-session/turn registries, static mounts).
- **Mocking:** `unittest.mock` (`MagicMock`, `patch`) and pytest's built-in `monkeypatch` fixture. `pytest-mock` is NOT a project dependency — neither `requirements.txt` nor any test imports `pytest_mock`.
- **Fixture data:** `tests/v2/fixtures/` ships two real-shape Confluence HTML drops (`joint_validation_sample.html`, `joint_validation_fallback_sample.html`) used by the Joint Validation parser tests.

`pytest` itself is not pinned in `requirements.txt`. Install it into the project virtualenv before running the suite:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest
```

`tests/v2/conftest.py` registers a single custom marker:

```text
slow — multiprocessing / fork / IO-heavy tests; deselect with -m 'not slow'
```

The only tests currently marked `@pytest.mark.slow` live in `tests/v2/test_content_store_race.py` (cross-process `multiprocessing.get_context("fork")` race for `atomic_write_bytes`; POSIX-only).

## Running tests

All commands assume `.venv/bin/pytest` (or the activated virtualenv's `pytest`). The same invocations are documented in the project README "Test" section.

```bash
# v2 suite — canonical surface for FastAPI + Bootstrap shell
.venv/bin/pytest tests/v2/

# Full suite — v2 + framework-agnostic core (tests/agent/, tests/services/, tests/adapters/)
.venv/bin/pytest tests/

# Skip cross-process race tests (e.g. on Windows or in fork-restricted CI)
.venv/bin/pytest tests/ -m "not slow"

# Single file
.venv/bin/pytest tests/v2/test_browse_routes.py

# Single test by node id
.venv/bin/pytest tests/v2/test_browse_routes.py::test_get_browse_empty_state

# Tests matching a name expression
.venv/bin/pytest tests/v2/ -k "phase04 and uif"

# Verbose, with print/log output
.venv/bin/pytest tests/v2/ -vv -s

# Just collect — useful for sanity-checking discovery
.venv/bin/pytest tests/v2/ --collect-only -q
```

**Current counts (verified by `--collect-only`):**

| Scope | Tests collected |
|---|---|
| `tests/v2/` (canonical FastAPI + HTMX surface) | 599 |
| `tests/` (full suite — `tests/v2/` + `tests/agent/` + `tests/services/` + `tests/adapters/`) | 775 |

The README cites a 594-test count from 2026-05-08; the live count drifts as quick tasks land. Use `pytest tests/v2/ --collect-only -q | tail -1` for the authoritative number.

## Test layout

```
tests/
├── v2/                            # canonical post-v2.0 suite (FastAPI + HTMX)
│   ├── conftest.py                # registers the `slow` marker
│   ├── fixtures/
│   │   ├── joint_validation_sample.html
│   │   └── joint_validation_fallback_sample.html
│   ├── test_main.py               # app smoke / topbar / tab labels
│   ├── test_browse_routes.py      # GET /browse + POST /browse/grid (HTMX, OOB swaps)
│   ├── test_browse_service.py     # browse view-model construction
│   ├── test_browse_presets.py     # browse preset chips
│   ├── test_ask_routes.py         # /ask + /ask/chat + /ask/stream/{turn} + /ask/cancel/{turn}
│   ├── test_chat_agent_tools.py   # PydanticAI ChatAgent tool wrapping (run_sql, etc.)
│   ├── test_chat_loop.py          # event-loop dispatch
│   ├── test_chat_session.py       # _TURNS / _SESSIONS registries (D-CHAT-11, D-CHAT-15)
│   ├── test_joint_validation_routes.py
│   ├── test_joint_validation_grid_service.py
│   ├── test_joint_validation_parser.py
│   ├── test_joint_validation_store.py
│   ├── test_joint_validation_summary.py
│   ├── test_joint_validation_invariants.py
│   ├── test_jv_pagination.py
│   ├── test_overview_presets.py
│   ├── test_summary_routes.py
│   ├── test_summary_service.py
│   ├── test_summary_integration.py
│   ├── test_content_store.py
│   ├── test_content_store_frontmatter.py
│   ├── test_content_store_race.py        # `slow` — multiprocessing fork race
│   ├── test_atomic_write.py
│   ├── test_cache.py                     # TTLCache wrappers
│   ├── test_settings_routes.py
│   ├── test_llm_resolver.py
│   ├── test_platform_parser.py
│   ├── test_soc_year.py
│   ├── test_phase02_invariants.py        # invariant pin: UI shell rewrite (D-UI2-*)
│   ├── test_phase03_invariants.py        # invariant pin: chat surface (CLAUDE.md banned libs, etc.)
│   ├── test_phase03_chat_invariants.py   # invariant pin: D-CHAT-* decisions
│   ├── test_phase04_invariants.py        # invariant pin: Browse Tab Port (D-03/13/19/22/34)
│   ├── test_phase04_uif_invariants.py    # invariant pin: UI Foundation (CSS/HTML grep guards)
│   ├── test_phase04_uif_components.py    # /_components route + macro args
│   └── test_phase04_uif_hero_spec.py     # HeroSpec Pydantic model
├── adapters/
│   └── test_pydantic_model.py            # DatabaseConfig / LLMConfig / AgentConfig
├── agent/
│   ├── test_nl_agent.py                  # legacy single-turn NL agent
│   └── test_nl_service.py
└── services/
    ├── test_ollama_fallback.py
    ├── test_path_scrubber.py             # /sys/, /proc/, /dev/ scrubbing
    ├── test_result_normalizer.py         # lazy per-query type coercion
    ├── test_sql_limiter.py               # LIMIT injector
    ├── test_sql_validator.py             # SELECT-only + UNION/CTE guards
    └── test_ufs_service.py               # pivot_to_wide
```

## Patterns used by the suite

### 1. FastAPI TestClient for route integration

Every route test imports `from app_v2.main import app` and drives it through `TestClient` inside a `with` block (so the lifespan runs once per fixture scope). The pattern is consistent across `test_main.py`, `test_browse_routes.py`, `test_ask_routes.py`, `test_phase04_uif_components.py`, and the JV route tests.

```python
import pytest
from fastapi.testclient import TestClient
from app_v2.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_get_root_returns_200_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
```

### 2. HTMX response assertions (block_names, OOB swaps, HX-Push-Url)

`test_browse_routes.py` and `test_phase02_invariants.py` verify that `jinja2-fragments` `block_names=` rendering emits the right partials, that out-of-band swap targets (`count_oob`, `warnings_oob`, `picker_badges_oob`) are present in the response body, and that the `HX-Push-Url` header points at the user-facing URL (`/browse`) rather than the form-target URL (`/browse/grid`). XSS regressions are guarded by asserting `| safe` does not appear in chat partials except a small whitelist (see `test_phase03_chat_invariants.py`).

```python
# Repeated form keys (multiple `platforms` selections) — httpx 0.28 dropped
# list-of-tuples on `data=`, so the suite manually url-encodes the body.
from urllib.parse import urlencode
_FORM_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}

def _post_form_pairs(client, url, pairs):
    body = urlencode(list(pairs))
    return client.post(url, content=body, headers=_FORM_HEADERS)
```

### 3. Pydantic Settings + DBAdapter mocking

The DB layer is patched at the import binding inside the calling service (NOT at the cache module), because `browse_service.py` does `from app_v2.services.cache import ...`, which binds the names into `browse_service`'s namespace.

```python
def _patch_cache(monkeypatch, *, platforms=None, params=None, fetch=None):
    if platforms is not None:
        monkeypatch.setattr(
            "app_v2.services.browse_service.list_platforms",
            lambda db, db_name="": list(platforms),
        )
    # ... etc for list_parameters_for_platforms and fetch_cells
```

For routes that need a live `request.app.state.db`, a minimal `DBAdapter` subclass is set on `app.state.db` AFTER `TestClient`'s `lifespan` has run — Pydantic v2's strict `isinstance(value, DBAdapter)` check on `ChatAgentDeps.db` rejects a bare `MagicMock`:

```python
from app.adapters.db.base import DBAdapter

class _FakeDB(DBAdapter):
    def __init__(self, df=None):
        self._df = df if df is not None else pd.DataFrame()
    def test_connection(self):  return True, "ok"
    def list_tables(self):      return ["ufs_data"]
    def get_schema(self, t=None): return {"ufs_data": []}
    def run_query(self, sql):   return self._df.copy()

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        app.state.db = _FakeDB()
        yield c
        app.state.db = None
```

### 4. PydanticAI agent test fixtures (mock LLM)

`test_chat_agent_tools.py` and `test_ask_routes.py` patch `build_chat_agent` at the module level and replace `run_stream_events` with a controlled async generator (RESEARCH Gap 11). No real LLM call is made anywhere in the suite. The chat-session module-level registries (`_TURNS`, `_SESSIONS`) are reset before and after each test by an `autouse=True` fixture (T-03-05-01 mitigation):

```python
from app.core.agent.chat_session import _SESSIONS, _TURNS

@pytest.fixture(autouse=True)
def _reset_chat_registries():
    _TURNS.clear()
    _SESSIONS.clear()
    yield
    _TURNS.clear()
    _SESSIONS.clear()
```

### 5. Phase invariants (markup / contract pinning)

Several files guard locked decisions with grep-style assertions over the source tree — they enforce policy, not behavior, and run in well under a second because they neither start the app nor exercise fixtures:

| File | Guards |
|---|---|
| `test_phase02_invariants.py` | UI shell rewrite (D-UI2-01..D-UI2-05) — type-scale tokens in `app_v2/static/css/tokens.css`, `.shell` full-width contract, sticky-footer block, no `--font-size-nav`, OOB block ordering after `{% block grid %}` |
| `test_phase03_invariants.py` | Phase 03 (Chat surface) — sync `def` only on DB-touching routes (INFRA-05), `MarkdownIt('js-default')` only (XSS — Pitfall 1), no `langchain` / `litellm` / `vanna` / `llama_index` imports (CLAUDE.md banned libs), `TTLCache(maxsize=128, ttl=3600)` verbatim (D-17), `mtime_ns` cache key (Pitfall 13), `atomic_write_bytes` single-source (D-30) |
| `test_phase03_chat_invariants.py` | D-CHAT-* — async narrowed to streaming routes only (D-CHAT-08), NL-05 templates deleted (D-CHAT-09), starter-chips removed from index (D-CHAT-10), LLM dropdown preserved (D-CHAT-11), no `\| safe` on agent strings except the router-rendered final-card whitelist, Plotly only loaded on the Ask page (T-03-04-07), `chat_loop` emits all 8 D-CHAT-04 reasons |
| `test_phase04_invariants.py` | Browse Tab Port — no Plotly under `app_v2/` (D-03), `PARAM_LABEL_SEP = ' · '` U+00B7 NOT slash (D-13), no `openpyxl` / `csv` / `/browse/export` (D-19), no `app.components.export_dialog` import (D-22), browse routes are sync `def` (D-34 + INFRA-05), browse stub removed from `routers/root.py`, no `\| safe` in browse templates |
| `test_phase04_uif_invariants.py` | UI Foundation — Wave-1 CSS rules in `app.css`, Google Fonts link in `base.html` (Pitfall 1), Wave-3 topbar partial replaces legacy navbar, `chip-toggle.js` sibling to `popover-search.js`, `_picker_popover.html` UNCHANGED (D-UIF-05 / D-UI2-09), `.panel-header` rule preserved through Wave 4 |
| `test_phase04_uif_components.py` | UI Foundation runtime — `GET /_components` returns 200, showcase exercises every macro arg path (D-UIF-02), both popovers use Bootstrap 5 dropdown anchoring (D-UIF-03), `filters_popover` emits chip-group `.grp` / `.opts` / `.opt` markup (D-UIF-04), `sparkline` macro handles empty / single / constant data (D-UIF-09) |
| `test_joint_validation_invariants.py` | Joint Validation — `^\d+$` numeric-only regex compiled once at module level (D-JV-03), sync `def` only on JV-touching routes (INFRA-05), iframe sandbox 3-flag attribute literal (T-05-03) |

These are the byte-stability backstop: any future PR that, e.g., flips Markdown-It to default-constructor or reintroduces a `langchain` import will fail invariants before it ever touches the runtime suite. They are deliberately cheap to keep CI fast.

## Writing new tests

- **Filename:** `tests/v2/test_<feature>.py` (snake_case, prefix `test_`).
- **Function name:** `test_<scenario>` — pytest's default discovery picks them up; no class wrapper needed.
- **Imports:** route tests use `from app_v2.main import app`; service tests import the service module directly; framework-agnostic core tests live under `tests/agent/`, `tests/services/`, `tests/adapters/` and import from `app/...`.
- **Fixtures:** prefer pytest's built-in `tmp_path`, `monkeypatch`, and `capsys`. Use module-scoped `client` fixtures for route tests (lifespan once per module). For per-test isolation of module-level state (e.g., chat registries), use an `autouse=True` reset fixture.
- **Mocking the cache layer:** patch at the consuming service's import binding, not at `app_v2.services.cache` (`from ... import` rebinds the names — see `_patch_cache` in `test_browse_routes.py`).
- **Mocking DBAdapter:** subclass `app.adapters.db.base.DBAdapter` and override `test_connection` / `list_tables` / `get_schema` / `run_query` — Pydantic v2 strict validation rejects `MagicMock`.
- **HTMX responses:** assert against `r.text` for fragment markup; assert against `r.headers` for `HX-Push-Url`, `HX-Trigger`, `Content-Type`. OOB blocks appear inline in the same response body — search for the OOB target id (e.g., `id="browse-count-oob"`).
- **No live LLM calls:** patch `build_chat_agent` (chat) or the OpenAI `chat.completions.create` call (single-shot summary) — never let a test reach `api.openai.com` or `localhost:11434`.
- **Slow / multiprocessing tests:** mark with `@pytest.mark.slow` and skip on Windows (`fork` is POSIX-only). Worker functions for `multiprocessing.Process` MUST be defined at module top-level so they are picklable.

## Coverage requirements

No coverage threshold is configured. The repo has no `pyproject.toml`, `setup.cfg`, `pytest.ini`, `.coveragerc`, or `tox.ini`; coverage is not enforced in CI. Test discipline is enforced instead by the **phase-invariant test files** above — they pin specific markup / contract / banned-import claims and fail the suite the moment a regression is introduced.

To get a coverage report locally, install `coverage` separately and run:

```bash
pip install coverage
.venv/bin/coverage run -m pytest tests/v2/
.venv/bin/coverage report -m
```

## CI integration

No `.github/workflows/` directory exists in the repository <!-- VERIFY: CI is run elsewhere (intranet GitLab/Jenkins) or not run at all on push -->. Tests are expected to be run locally before commit. The GSD workflow (`/gsd-quick`, `/gsd-execute-phase`, `/gsd-debug`) reminds the developer to run `pytest tests/v2/` as part of the standard "ship" gate; the project README's "Test" section is the canonical command list.

If a CI pipeline is added later, the required commands are:

```bash
pip install -r requirements.txt
pip install pytest
pytest tests/v2/ -m "not slow"   # core run
pytest tests/v2/                 # full run including the multiprocessing race
```
