<!-- generated-by: gsd-doc-writer -->
# Configuration

PBM2 reads configuration from two layers:

1. **`config/settings.yaml`** — the primary configuration file. Holds connected
   databases, registered LLM backends, and app-wide defaults (including the NL
   agent budget). Loaded at startup by `app/core/config.py::load_settings()` and
   stored on `app.state.settings` (see `app_v2/main.py` lifespan).
2. **`.env`** — environment variables read implicitly. The repo ships an
   `.env.example`; copy it to `.env` and fill values. The application code does
   **not** call `load_dotenv()` itself — environment variables must be present
   in the process environment when uvicorn starts (e.g., `set -a; source .env;
   set +a; uvicorn app_v2.main:app`).
   <!-- VERIFY: whether intranet deployments preload .env via systemd EnvironmentFile or another wrapper -->

`config/settings.yaml` is **gitignored** (it holds plaintext database passwords
and API keys per project decision D-11). The repository tracks
`config/settings.example.yaml`; copy it to `config/settings.yaml` to bootstrap
a local install. Per-feature YAML files (`presets`, `browse_presets`,
`starter_prompts`) follow the same `*.example.yaml` → `*.yaml` pattern.

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Optional* | _(none)_ | OpenAI API key fallback. Used by `app_v2/services/summary_service.py` and `app/adapters/llm/pydantic_model.py` only when the matching `LLMConfig.api_key` is empty. *Required if any active OpenAI-typed LLM in `settings.yaml` has `api_key: ""`. |
| `SETTINGS_PATH` | Optional | `config/settings.yaml` (relative to repo root) | Override the path to the YAML settings file. Read in `app/core/config.py::_settings_path`. Useful for tests and per-environment deployments. |
| `LOG_DIR` | Optional | `logs` | Documented in `.env.example`; the `logs/` directory is gitignored. <!-- VERIFY: whether application logging is wired to read LOG_DIR — current app_v2/main.py uses logging.getLogger only, no FileHandler reads this var --> |

\* "Required" here means: required only if you do not put the key directly into
`config/settings.yaml` under the relevant `llms[].api_key` field. Either source
satisfies the OpenAI client; an empty `api_key` field plus a missing env var
will cause OpenAI calls to fail at request time.

`.env.example` (verbatim from the repo root):

```bash
# Copy to .env and fill in values. Values here are read by python-dotenv at startup.

# OpenAI API key (used by the default LLM adapter).
OPENAI_API_KEY=

# Optional: override the default settings.yaml path.
# SETTINGS_PATH=config/settings.yaml

# Log directory (defaults to ./logs)
# LOG_DIR=logs
```

## `config/settings.yaml`

Defined as a Pydantic v2 model in `app/core/config.py`. The top-level shape:

```yaml
databases: []   # list[DatabaseConfig]
llms:      []   # list[LLMConfig]
app:       {}   # AppConfig (includes nested AgentConfig)
```

A minimal working file (taken from `config/settings.example.yaml`):

```yaml
databases:
  - name: "Production MySQL (Read-only)"
    type: mysql
    host: localhost
    port: 3306
    database: mydb
    user: readonly_user
    password: "change-me"
    readonly: true

llms:
  - name: "GPT-4o Mini"
    type: openai
    model: gpt-4o-mini
    api_key: ""          # blank → falls back to OPENAI_API_KEY env var
    endpoint: ""         # blank → uses OpenAI default endpoint
    temperature: 0.0
    max_tokens: 2000

  - name: "Local Llama (Ollama)"
    type: ollama
    model: "llama3.1:8b"
    endpoint: "http://localhost:11434"
    api_key: ""
    temperature: 0.0
    max_tokens: 2000

app:
  default_database: "Production MySQL (Read-only)"
  default_llm: "GPT-4o Mini"
  query_row_limit: 1000
  recent_query_history: 20
  conf_url: ""
  agent:
    model: ""
    max_steps: 5
    row_cap: 200
    timeout_s: 30
    allowed_tables:
      - "ufs_data"
    max_context_tokens: 30000
    chat_max_steps: 12
```

### `databases[]` — `DatabaseConfig`

Source: `app/core/config.py::DatabaseConfig`.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `name` | **Yes** | _(no default)_ | Display name and lookup key. Referenced from `app.default_database` and from the Settings UI database picker. |
| `type` | No | `mysql` | One of `mysql`, `sqlite`, `postgres`, `mssql`, `bigquery`, `snowflake`. Only `mysql` and `sqlite` adapters are currently registered (`app/adapters/db/registry.py`). Other types will raise `ValueError` at adapter build time. |
| `host` | No | `localhost` | DB host. Ignored for `sqlite`. |
| `port` | No | `3306` | DB port. Ignored for `sqlite`. |
| `database` | No | `""` | MySQL schema name, or SQLite file path (e.g., `data/demo_ufs.db`). |
| `user` | No | `""` | DB username. |
| `password` | No | `""` | DB password (plaintext on disk — `config/settings.yaml` is gitignored for this reason). |
| `readonly` | No | `true` | When `true`, MySQL adapter forces `SET SESSION TRANSACTION READ ONLY` on every connection (see `app/adapters/db/mysql.py`). The agent's `run_sql` tool also relies on this as the SQL-injection backstop. |

### `llms[]` — `LLMConfig`

Source: `app/core/config.py::LLMConfig`.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `name` | **Yes** | _(no default)_ | Display name and lookup key. Referenced from `app.default_llm`. |
| `type` | No | `openai` | One of `openai`, `anthropic`, `ollama`, `vllm`, `custom`. The PydanticAI agent factory (`app/adapters/llm/pydantic_model.py`) supports only `openai` and `ollama`; other values raise `ValueError`. <!-- VERIFY: any production deployment is using anthropic/vllm/custom — code path is not implemented --> |
| `model` | No | `""` | Model identifier (e.g., `gpt-4o-mini`, `llama3.1:8b`). When empty, the PydanticAI factory substitutes `gpt-4o-mini` for OpenAI and `qwen2.5:7b` for Ollama. |
| `endpoint` | No | `""` | Base URL. For OpenAI, empty = OpenAI default (`https://api.openai.com/v1`). For Ollama, empty = `http://localhost:11434`; the `/v1` suffix is appended automatically. |
| `api_key` | No | `""` | API key. For `openai` type, empty falls back to the `OPENAI_API_KEY` env var. Ollama ignores this. |
| `temperature` | No | `0.0` | Sampling temperature. |
| `max_tokens` | No | `2000` | Max output tokens for completion calls. |
| `headers` | No | `{}` | Extra HTTP headers (dict). Currently unused by the PydanticAI path. |

### `app` — `AppConfig`

Source: `app/core/config.py::AppConfig`.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `default_database` | No | `""` | Name of the entry in `databases[]` to use at startup. If empty or unresolved, lifespan falls back to `databases[0]` (see `app_v2/main.py`). |
| `default_llm` | No | `""` | Name of the entry in `llms[]` to use as the default LLM. |
| `query_row_limit` | No | `1000` | Browse-page server-side row cap before pivot. |
| `recent_query_history` | No | `20` | Size of the recent-query history buffer. |
| `conf_url` | No | `""` | Base URL for the Confluence "컨플" link button on the Joint Validation grid. Empty = button rendered disabled. The numeric page id (from `content/joint_validation/<id>/`) is appended as `/<page_id>` to form the final href. Edited directly in `settings.yaml` — no Settings UI surface. |
| `agent` | No | `AgentConfig()` defaults | Nested NL agent budget — see below. |

### `app.agent` — `AgentConfig`

Source: `app/core/agent/config.py::AgentConfig`.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `model` | No | `""` | OpenAI tool-capable model override for the agentic loop. Empty = inherit from the currently-selected `LLMConfig.model`. Set this only when the agent loop should run a *different* model from non-agent calls (accuracy escalation). |
| `max_steps` | No | `5` (range `1..20`) | Tool-call cap for the legacy single-turn NL agent (`app/core/agent/nl_agent.py`). Enforced via PydanticAI `UsageLimits(tool_calls_limit=...)`. |
| `row_cap` | No | `200` (range `1..10000`) | Max rows the `run_sql` tool will return per call. `inject_limit(sql, row_cap)` rewrites the SQL to enforce this server-side. |
| `timeout_s` | No | `30` (range `5..300`) | Per-query timeout in seconds. The MySQL adapter converts it to `MAX_EXECUTION_TIME` ms. |
| `allowed_tables` | No | `["ufs_data"]` | Tables `run_sql` is permitted to query. `validate_sql(sql, allowed_tables)` rejects any SQL referencing other tables. Editable in the Settings UI under "앱 기본값 → 에이전트 허용 테이블". |
| `max_context_tokens` | No | `30000` (range `1000..1_000_000`) | Token budget for the agent context window. |
| `chat_max_steps` | No | `12` (range `1..50`) | Per-turn step budget for the multi-step chat agent loop (`app/core/agent/chat_agent.py`). Independent from `max_steps`. Counts ALL tool calls including the terminal `present_result` call. |

## Auxiliary YAML files

These files live in `config/` and follow a `*.yaml` (gitignored) →
`*.example.yaml` (tracked) fallback chain. The application reads `*.yaml`
first; if absent, it falls back to `*.example.yaml`; if neither exists, it
returns an empty list.

| File | Loaded by | Purpose | Tracked? |
|------|-----------|---------|----------|
| `config/settings.yaml` | `app/core/config.py::load_settings` | Primary settings (above). | Gitignored |
| `config/settings.example.yaml` | (manual copy template) | Bootstrap template for `settings.yaml`. | Tracked |
| `config/presets.yaml` | `app_v2/services/preset_store.py` | Filter presets for the Overview (Joint Validation) page. | Gitignored |
| `config/presets.example.yaml` | Fallback for `preset_store.py` | Tracked default presets. | Tracked |
| `config/browse_presets.yaml` | `app_v2/services/browse_preset_store.py` | Filter presets for the Browse (Pivot grid) page (`platforms[]`, `params[]`, `swap_axes`). | Gitignored |
| `config/browse_presets.example.yaml` | Fallback for `browse_preset_store.py` | Tracked default presets. | Tracked |
| `config/starter_prompts.yaml` | `app_v2/services/starter_prompts.py` | Starter prompt buttons on the Ask page. | Gitignored |
| `config/starter_prompts.example.yaml` | Fallback for `starter_prompts.py` | Tracked default prompts. | Tracked |

The `*.example.yaml` files are designed to be hot-reloadable: edit
`config/<feature>.yaml` and the next request picks it up without a server
restart (see `app_v2/services/starter_prompts.py` docstring).

## Required vs optional settings

PBM2 starts up tolerantly: missing config does not crash the FastAPI app —
features simply degrade. The lifespan hook (`app_v2/main.py`) explicitly
allows Phase 1 smoke tests to run with no configured database.

**Hard requirements at runtime (when the corresponding feature is exercised):**

- A working entry in `databases[]` with `type` registered in
  `app/adapters/db/registry.py` (currently `mysql`, `sqlite`). If `default_database`
  resolves to nothing and `databases[]` is empty, `app.state.db` is `None` and
  any DB-backed page returns an error.
- For OpenAI-typed LLMs: either `LLMConfig.api_key` is non-empty **or**
  `OPENAI_API_KEY` is set in the environment.
- For Ollama: a reachable `endpoint` (default `http://localhost:11434`). The
  app does **not** ping Ollama at startup — first-request cold-start latency
  is accepted (see deviation note in `app_v2/main.py` lifespan).

**Soft requirements:**

- `app.default_database` empty → falls back to `databases[0]`.
- `app.default_llm` empty → no implicit fallback; user must pick from the
  Settings UI.
- `app.conf_url` empty → Joint Validation Confluence button rendered disabled.
- `app.agent.allowed_tables` empty → all `run_sql` calls fail validation.

## Defaults

All defaults below are read directly from the Pydantic model definitions in
`app/core/config.py` and `app/core/agent/config.py`:

| Setting | Default |
|---------|---------|
| `DatabaseConfig.type` | `mysql` |
| `DatabaseConfig.host` | `localhost` |
| `DatabaseConfig.port` | `3306` |
| `DatabaseConfig.readonly` | `true` |
| `LLMConfig.type` | `openai` |
| `LLMConfig.temperature` | `0.0` |
| `LLMConfig.max_tokens` | `2000` |
| `AppConfig.query_row_limit` | `1000` |
| `AppConfig.recent_query_history` | `20` |
| `AppConfig.conf_url` | `""` |
| `AgentConfig.max_steps` | `5` |
| `AgentConfig.row_cap` | `200` |
| `AgentConfig.timeout_s` | `30` |
| `AgentConfig.allowed_tables` | `["ufs_data"]` |
| `AgentConfig.max_context_tokens` | `30000` |
| `AgentConfig.chat_max_steps` | `12` |

## Per-environment overrides

PBM2 has no built-in `NODE_ENV`-style per-environment switch. Environments are
distinguished by:

1. **Different `config/settings.yaml`** per host. The file is gitignored so each
   deployment carries its own copy. CI / dev typically point at `data/demo_ufs.db`
   (SQLite) via `settings.example.yaml`'s `Demo SQLite` entry; production points
   at the read-only MySQL replica.
2. **`SETTINGS_PATH` env var.** Set this to load a different YAML path without
   replacing `config/settings.yaml`. Tests use this to point at fixture YAML.
3. **Direct env vars** for secrets that should not live on disk
   (`OPENAI_API_KEY`).

Deployment-specific values that vary per intranet host (database hostnames,
Confluence base URL, Ollama endpoint) are managed by editing
`config/settings.yaml` on the target host.
<!-- VERIFY: production deployment process — whether settings.yaml is provisioned by Ansible, copied manually, or templated from a secrets vault -->
