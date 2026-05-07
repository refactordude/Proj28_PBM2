<!-- generated-by: gsd-doc-writer -->
# API Reference

PBM2 is a server-rendered FastAPI + HTMX application. **Endpoints return HTML
fragments**, not JSON, except where explicitly noted (SSE event streams,
204/403/404 status-only responses). HTMX consumers swap fragments into the DOM
either as the primary swap target or via Out-Of-Band (OOB) named blocks
(jinja2-fragments `block_names=[...]` pattern).

The application has no authentication layer (intranet, shared-credential
deployment per `CLAUDE.md`). Two cookies carry per-browser state:

- `pbm2_llm` — selected LLM backend name (set by `POST /settings/llm`).
- `pbm2_session` — per-browser session id used to authenticate Ask SSE streams
  and cancel requests. Uuid4 hex, `HttpOnly`, `SameSite=Lax`, `Secure=False`,
  1-year `Max-Age`.

For request flow, view-model construction, and OOB swap mechanics see
`docs/ARCHITECTURE.md`. For LLM and agent configuration (`AgentConfig.row_cap`,
`AgentConfig.allowed_tables`, `AgentConfig.timeout_s`) see
`docs/CONFIGURATION.md`.

## Conventions

- **Method + Path** — one HTTP method per row. Routes that share a path under
  multiple verbs are listed separately.
- **Params** — Path / Query / Form / Header. `Query()` and `Form()` parameters
  that accept lists use repeated keys (`?customer=A&customer=B`).
- **Response** — one of: full HTML page, HTMX HTML fragment (named blocks
  emitted), Server-Sent Events (SSE), 204/403/404 status-only.
- **OOB blocks** — named Jinja2 blocks emitted via
  `TemplateResponse(..., block_names=[...])`. Consumed by HTMX as either the
  primary swap target or `hx-swap-oob` targets.
- **HX-Push-Url** — when a POST returns a fragment but the route's *canonical*
  shareable URL is a different GET path, the response carries `HX-Push-Url`
  so the address bar reflects a bookmarkable URL.

---

## Joint Validation router (`app_v2/routers/overview.py` + `app_v2/routers/joint_validation.py`)

The Joint Validation tab is the default tab — it owns `/` and `/overview`. The
listing is auto-discovered from `content/joint_validation/<numeric_id>/index.html`
(re-globbed on every request). Detail pages render an iframe sandbox of the
exported Confluence HTML.

### `GET /`
### `GET /overview`

Render the Joint Validation listing (full HTML page).

**Query params (all optional, repeated keys for multi-value):**

| Param | Type | Notes |
|---|---|---|
| `customer` | `list[str]` | Filter facet |
| `ap_company` | `list[str]` | Filter facet |
| `ap_model` | `list[str]` | Filter facet |
| `device` | `list[str]` | Filter facet |
| `controller` | `list[str]` | Filter facet |
| `application` | `list[str]` | Filter facet |
| `sort` | `str \| None` | Sort column key |
| `order` | `str \| None` | `asc` or `desc` |
| `page` | `int` (>=1, <=10000) | Pagination, default 1 |

**Response:** Full HTML page rendering `overview/index.html`.

### `POST /overview/grid`

HTMX fragment swap fired by filter changes, sort, and pagination clicks.

**Form params:** Same six facet lists + `sort`, `order`, `page` as the GET
route, all received as `Form()` instead of `Query()`.

**Response:** HTML fragment with the following named blocks emitted:

- `grid` — primary swap target (`#overview-grid`)
- `count_oob` — row-count badge OOB swap
- `filter_badges_oob` — active filter badge strip OOB swap
- `pagination_oob` — pagination control OOB swap
- `picker_badges_oob` — picker badge counts OOB swap

**Headers:** `HX-Push-Url` set to canonical `/overview?...` URL (clamped page
reflected). The POST URL `/overview/grid` is never pushed to the bar.

### `GET /overview/preset/{name}`

Apply a named filter preset (overrides current filters; does not merge).

**Path params:** `name` — preset key looked up in `load_presets()`.

**Response:** Same five OOB blocks as `POST /overview/grid`. `HX-Push-Url`
reflects the resulting canonical `/overview?...` URL. Returns **404** with
plain-text body `preset '{name}' not found` when the preset key is unknown.

### `GET /joint_validation/{confluence_page_id}`

Detail page: properties table on top, `<iframe sandbox="...">` below pointing
at `/static/joint_validation/<id>/index.html`.

**Path params:** `confluence_page_id` — `^\d+$`, length 1–32. Non-numeric input
returns **422**.

**Response:** Full HTML page rendering `joint_validation/detail.html`. Returns
**404** when `content/joint_validation/<id>/index.html` does not exist.

### `POST /joint_validation/{confluence_page_id}/summary`

AI Summary modal target. **Always returns 200** (error contract — error
fragments swap into the summary slot, not the global error container).

**Path params:** `confluence_page_id` (`^\d+$`, 1–32 chars).

**Headers:**
- `X-Regenerate: true` — bypass cache, force regeneration. Only the literal
  string `"true"` (case-insensitive) triggers regenerate.
- `HX-Target` — id of the slot where the inner Retry/Regenerate button should
  swap. Stripped of leading `#`. Falls back to `summary-{confluence_page_id}`.

**Response (200, always):** Either `summary/_success.html` (markdown summary +
metadata) or `summary/_error.html` (amber-warning fragment with classified
reason string). Errors are classified by
`app_v2.services.summary_service._classify_error`.

---

## Static mount: `/static/joint_validation/`

Registered before the global `/static` mount in `app_v2/main.py`. Serves files
from `content/joint_validation/`. `html=False` (no auto-index), `follow_symlink=False`.
Used by the iframe in the JV detail page.

---

## Platform Browser router (`app_v2/routers/browse.py`)

Owns `/browse` and `/browse/grid`. The pivot grid renders wide-form data with
platforms as columns and parameters as rows (or swapped). Empty selection
short-circuits before any DB query.

### `GET /browse`

Render the Browse page with grid pre-rendered server-side from URL state.

**Query params (all optional):**

| Param | Type | Notes |
|---|---|---|
| `platforms` | `list[str]` | Selected platform IDs (repeated keys) |
| `params` | `list[str]` | Selected parameter labels (`InfoCategory · Item`) |
| `swap` | `str` | `"1"` to swap pivot axes, else empty |
| `highlight` | `str` | `"1"` to enable difference highlighting (render-only) |

**Response:** Full HTML page rendering `browse/index.html` with `vm` view-model.

### `POST /browse/grid`

Fragment swap fired by Apply / swap-axes / Clear-all buttons.

**Form params:** Same as GET plus `_origin` (alias `_origin`) — picker name
that triggered the request (`"params"` suppresses the params-picker OOB swap
to keep the open popover DOM intact).

**Response:** Named blocks emitted:

- `grid` — primary swap (`#browse-grid`)
- `count_oob` — row count
- `warnings_oob` — cap-warning slot
- `picker_badges_oob` — picker badge counts
- `params_picker_oob` — emitted only when `_origin != "params"`

**Headers:** `HX-Push-Url` carries canonical `/browse?platforms=...&params=...&swap=1&highlight=1`.

### `POST /browse/params-fragment`

Re-render only the Parameters picker block when the Platforms picker changes.

**Form params:** `platforms`, `params` (no `swap` — picker doesn't depend on it).

**Response:** Single named block `params_picker`. Used as a graceful-degradation
hook; the primary `POST /browse/grid` already emits `params_picker_oob` for
most user flows.

### `GET /browse/preset/{name}`

Apply a named Browse preset (overrides current selection; does not merge).

**Path params:** `name` — preset key in `load_browse_presets()`.

**Query params:** `highlight` — preserved from the request (not from preset YAML).

**Response:** Same five OOB blocks as `POST /browse/grid`. `HX-Push-Url`
reflects the canonical `/browse?...` URL. Returns **404** with plain-text body
`browse preset '{name}' not found` when the preset key is unknown.

---

## AI 질문하기 router (`app_v2/routers/ask.py`)

Multi-step agentic chat over the EAV `ufs_data` table. The chat orchestration
lives in `app/core/agent/` (chat_loop, chat_session, chat_agent); routes here
manage HTTP / SSE plumbing only.

### Read-only DB safety contract

Every SQL string the agent emits passes through three gates before execution:

1. **`validate_sql(sql, allowed_tables)`** — single-statement parse, single
   `SELECT` enforcement, table allowlist check (case-insensitive). Implemented
   in `app/services/sql_validator.py`.
2. **`inject_limit(sql, row_cap)`** — append `LIMIT row_cap` if absent or
   tighten an existing `LIMIT`. Implemented in `app/services/sql_limiter.py`.
3. **Session pragmas (best-effort)** — `SET SESSION TRANSACTION READ ONLY`
   and `SET SESSION max_execution_time={timeout_s * 1000}` issued before
   `pd.read_sql_query`. Adapters that don't support these pragmas swallow
   the error and continue (the readonly DB user is the primary backstop).

`AgentConfig.allowed_tables`, `AgentConfig.row_cap`, and `AgentConfig.timeout_s`
are loaded from `config/settings.yaml` at lifespan. See `docs/CONFIGURATION.md`
for defaults and override mechanics.

### `GET /ask`

Render the chat shell. Sets the `pbm2_session` cookie if absent.

**Response:** Full HTML page rendering `ask/index.html`. Context exposes
`backend_name`, `llm_cfg`, `llms` for the LLM dropdown.

### `POST /ask/chat`

Start a new chat turn. Registers the turn in the per-app `chat_turns` registry,
returns the user-message fragment + the SSE consumer element (which then
opens an EventSource to `/ask/stream/{turn_id}`).

**Form params:** `question: str` (default `""`; trimmed server-side).

**Response:** HTML fragment rendering `ask/_user_message.html` with
`turn_id` and `question`. `pbm2_session` cookie set on response if absent on
the request.

### `GET /ask/stream/{turn_id}` — SSE

Server-Sent Events stream for the agent's multi-step turn. **`async def`** —
required for streaming. Authenticated via `pbm2_session` cookie ownership of
`turn_id` (`get_session_id_for_turn`).

**Path params:** `turn_id` — uuid4 hex (128-bit entropy).

**Status codes:**
- **404** — unknown `turn_id` (turn not registered or already popped).
- **403** — `pbm2_session` cookie does not match the session that registered
  the turn.
- **200** — `text/event-stream` (via `EventSourceResponse`).

**Events emitted:**
- `event: <step>` — agent thinking / tool-call HTML fragments (pre-rendered by
  `chat_loop.stream_chat_turn`).
- `event: final` — terminal event carrying the rendered `_final_card.html`.
  The router itself runs `validate_sql` + `inject_limit` again, executes the
  SQL via `app.state.db`, builds the table HTML using the Browse `_grid.html`
  macro, and constructs the Plotly chart server-side from the typed `ChartSpec`
  (silent downgrade to no chart when the spec's columns are missing in the
  result frame).
- `event: error` — single error event then close, emitted when no LLM, no DB
  adapter, or no `agent_cfg` is configured.

**Keepalive:** SSE ping every 15 seconds.

**Background:** `BackgroundTask(pop_turn, turn_id)` removes the turn from the
registry on stream close.

### `POST /ask/clear`

Drop the agent message-history for the requesting browser session and return
an empty body. Idempotent.

**Authentication:** `pbm2_session` cookie identifies the session; absent
cookie clears the unnamed session.

**Response:** `200 OK` with empty body. HTMX swaps it into `#chat-transcript`
to wipe the visible chat.

### `POST /ask/cancel/{turn_id}`

Flip the per-turn `cancel_event` so the in-flight SSE generator stops at the
next checkpoint. **`async def`** (pure registry mutation).

**Path params:** `turn_id`.

**Status codes:**
- **404** — unknown `turn_id`.
- **403** — `pbm2_session` cookie does not match the turn owner.
- **204** — cancel event flipped successfully.

---

## AI Summary router (`app_v2/routers/summary.py`)

Owns `POST /platforms/{pid}/summary`. **Always returns 200** — the error
fragment is the canonical failure shape (UI-SPEC summary error contract;
errors swap into the summary slot, not the global error container).

### `POST /platforms/{platform_id}/summary`

**Path params:** `platform_id` — `^[A-Za-z0-9_\-]{1,128}$`. Non-matching values
return **422**.

**Headers:**
- `X-Regenerate: true` — bypass cache, force regeneration.
- `HX-Target` — id of the calling slot. Falls back to `summary-{platform_id}`.

**Response (200, always):** `summary/_success.html` (markdown summary +
metadata footer + Regenerate button) on success, or `summary/_error.html`
(amber-warning fragment) on:

- LLM not configured (`"LLM not configured — set one in Settings"`).
- Content page no longer exists (`"Content page no longer exists"`).
- Any OpenAI / httpx exception (reason classified by
  `summary_service._classify_error`).

<!-- VERIFY: classified-error reason strings — see app_v2/services/summary_service.py _classify_error for the seven canonical strings -->

---

## Platform content CRUD router (`app_v2/routers/platforms.py`)

Markdown content for individual platform IDs lives under `content/platforms/`.
All routes validate `platform_id` against `^[A-Za-z0-9_\-]{1,128}$` at the
FastAPI layer; `content_store._safe_target` re-asserts containment via
`Path.resolve()` + `relative_to()`.

### `GET /platforms/{platform_id}`

Render the platform detail page (full HTML).

### `POST /platforms/{platform_id}/edit`

Return the edit-panel fragment (`platforms/_edit_panel.html`). Replaces
`#content-area` via `outerHTML`. Stashes the rendered-view HTML into
`data-cancel-html` for client-side Cancel restoration.

### `POST /platforms/{platform_id}/preview`

Render markdown to preview HTML — **no disk side-effects**.

**Form params:** `content: str` (max 65536 chars).

**Response:** `platforms/_preview_pane.html`.

### `POST /platforms/{platform_id}`

Atomically save markdown content. Returns the rendered-view fragment.

**Form params:** `content: str` (max 65536 chars; authoritative byte cap is
65536 bytes inside `save_content`).

**Status codes:**
- **413** — UTF-8 byte length exceeds 65536, or `_safe_target` rejects the path.
- **200** — `platforms/_content_area.html` with the new rendered HTML.

### `DELETE /platforms/{platform_id}/content`

Delete the content file. Idempotent — does not raise on missing file. Returns
the empty-state `platforms/_content_area.html` fragment.

---

## Settings router (`app_v2/routers/settings.py`)

### `POST /settings/llm`

Set the `pbm2_llm` cookie that drives the active LLM backend across the entire
app (Ask, AI Summary).

**Form params:** `name: str` — must equal one of `settings.llms[].name`. Any
other value (empty, missing, tampered, stale) silently falls back to
`settings.app.default_llm`. **No 4xx is returned** — invalid input is a UX
fallback, not an attack to be loudly rejected.

**Response:** **204 No Content** with `HX-Refresh: true` header (lowercase
literal). HTMX 2.x interprets this as `window.location.reload()` regardless
of status.

**Cookie attributes:** `Path=/`, `SameSite=Lax`, `Max-Age=31536000` (1 year),
`HttpOnly=True`, `Secure=False` (intranet HTTP).

---

## Components showcase (`app_v2/routers/components.py`)

### `GET /_components`

Render the live Phase 4 component showcase page with hard-coded sample data
(hero variants, KPI cards, chip-group filter popover, sticky-corner table).
Always-on (not dev-gated). Used as the design reference for downstream phases
and as the locus for invariant tests.

**Response:** Full HTML page rendering `_components/showcase.html`.

---

## Root router (`app_v2/routers/root.py`)

Empty `APIRouter` — no routes. The historical `/`, `/browse`, `/ask` stubs
were migrated to the dedicated `overview`, `browse`, and `ask` routers
respectively. Kept registered last in `main.py` so any future commit that
re-adds a stub here does not shadow the real route.

---

## Exception handlers (`app_v2/main.py`)

Two app-level handlers render Bootstrap-styled error pages. HTMX requests
(`HX-Request: true`) get fragment templates so `htmx-error-handler.js` can
swap them into `#htmx-error-container` without re-injecting the base shell.

- `StarletteHTTPException` handler — returns `404.html` / `_404_fragment.html`
  for 404, `500.html` / `_500_fragment.html` for 500. Other status codes fall
  through to a minimal escaped `<h1>HTTP {code}</h1>` body.
- Catch-all `Exception` handler — logs the traceback and renders the 500
  template. Detail string is `{type(exc).__name__}: Internal server error`
  (no internal stack leaked to the client).

---

## OpenAPI / Swagger UI

FastAPI's automatic OpenAPI schema is exposed at `/docs` (Swagger UI). ReDoc is
disabled (`redoc_url=None`). Note that the auto-generated schema describes
declared response classes (`HTMLResponse`) but does **not** capture the actual
HTML fragment shape, OOB block names, or `HX-Push-Url` header behavior — this
document is the authoritative reference for HTMX consumers.
