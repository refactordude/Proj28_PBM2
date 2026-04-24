# Pitfalls Research

**Domain:** FastAPI + Bootstrap 5 + HTMX UI layer on top of existing Streamlit/SQLAlchemy/PydanticAI stack — v2.0 Bootstrap Shell migration
**Researched:** 2026-04-23
**Confidence:** HIGH for FastAPI async mechanics (official docs verified); HIGH for HTMX quirks (official docs + GitHub issues); HIGH for markdown-it-py XSS (official docs confirmed); MEDIUM for CSRF/session in intranet context (general patterns, no PBM2-specific measurement)

---

## Critical Pitfalls

### Pitfall 1: markdown-it-py renders raw HTML by default — `<script>` tags in content pages execute

**What goes wrong:**
`MarkdownIt()` (the default constructor, equivalent to `"commonmark"` preset) sets `html=True`, which renders raw HTML tags verbatim. A user who pastes `<script>alert(1)</script>` or `<img src=x onerror="fetch('/exfil?'+document.cookie)">` into a content page markdown file will have that code execute in every browser that views the page. The official markdown-it-py docs state explicitly: *"unlike the original markdown-it JavaScript project, which uses the safe-by-default strategy, markdown-it-py enables the more convenient, but less secure, CommonMark-compliant settings by default."*

This affects the per-platform markdown content pages (`content/platforms/<PLATFORM_ID>.md`) which are user-editable via HTMX forms.

**Why it happens:**
The CommonMark spec requires HTML passthrough. Developers unfamiliar with markdown-it-py's divergence from the JS library's defaults assume it is safe by default.

**How to avoid:**
Use the `"js-default"` preset instead of the default constructor:
```python
from markdown_it import MarkdownIt
md = MarkdownIt("js-default")   # html=False, no raw HTML passthrough
rendered = md.render(user_content)
```
This disables all raw HTML rendering; legitimate markdown formatting (bold, headers, lists, fenced code blocks) still works. Do NOT use `html=True` for user-editable content.

For defense in depth on the client side, add DOMPurify after the Jinja2 template renders the markdown HTML, though this is secondary — the primary fix is server-side with `"js-default"`.

Add a unit test: `assert "<script>" not in MarkdownIt("js-default").render("<script>alert(1)</script>")`.

**Warning signs:**
- `MarkdownIt()` or `MarkdownIt("commonmark")` used anywhere content pages are rendered.
- No unit test covering `<script>` injection in rendered markdown.
- Content pages display raw HTML tags instead of escaping them during a code review.

**Phase to address:** Phase 1 of v2.0 (Foundation) — before any content page rendering is wired up. Add the `"js-default"` constraint as a coding standard in CONVENTIONS.md.
**Criticality:** BLOCKER — intranet XSS can exfiltrate session cookies and pivot to other internal services.

---

### Pitfall 2: Path traversal via `PLATFORM_ID` in content file paths

**What goes wrong:**
A route like `GET /platforms/{platform_id}/content` that reads `content/platforms/{platform_id}.md` is vulnerable to path traversal if `platform_id` is not validated before being used as a filename. A crafted value like `../../etc/passwd` or `../config/settings.yaml` resolves to a file outside `content/platforms/`. Even though `PLATFORM_ID` values come from `ufs_data` (a read-only DB), the route parameter is a user-supplied HTTP value, not a DB value — an attacker does not need to first appear in the DB.

**Why it happens:**
Developers assume "it comes from the DB so it must be safe." The route parameter is resolved from the HTTP request before any DB lookup. FastAPI's path parameter handling does URL-decode the value but does not strip traversal sequences.

**How to avoid:**
Apply a strict regex validator on the `platform_id` path parameter before touching disk:
```python
from fastapi import Path
import re

PLATFORM_ID_RE = re.compile(r'^[A-Za-z0-9_\-]{1,128}$')

@app.get("/platforms/{platform_id}/content")
def get_content(platform_id: str = Path(..., pattern=r'^[A-Za-z0-9_\-]{1,128}$')):
    ...
```
Additionally, use `pathlib.Path.resolve()` and assert the resolved path starts with `BASE_CONTENT_DIR.resolve()` before any `open()` call:
```python
from pathlib import Path
BASE = Path("content/platforms").resolve()
target = (BASE / f"{platform_id}.md").resolve()
assert str(target).startswith(str(BASE)), "Path traversal attempt"
```
The regex constraint is the primary control; the `resolve()` assertion is a defense-in-depth belt-and-suspenders check.

`PLATFORM_ID` values follow `Brand_Model_SoCID` convention (alphanumeric + underscore). The regex `^[A-Za-z0-9_\-]{1,128}$` covers all legitimate values and rejects `../` sequences.

**Warning signs:**
- No regex validation on `platform_id` before file I/O.
- `open(f"content/platforms/{platform_id}.md")` without a `resolve()` check.
- Integration test suite has no `../` traversal test case.

**Phase to address:** Phase 1 of v2.0 (Foundation) — the content file read/write routes must include this validation from first commit. Add a security test: `GET /platforms/../../etc/passwd/content` must return 400 or 404, never 200 with file contents.
**Criticality:** BLOCKER — path traversal exposes server filesystem including `config/settings.yaml`, `.env`, and potentially `config/auth.yaml` to any team member who knows the pattern.

---

### Pitfall 3: `ufs_service.py` is hard-coupled to `@st.cache_data` — importing it in v2.0 crashes the process

**What goes wrong:**
`ufs_service.py` currently imports `streamlit as st` and uses `@st.cache_data` decorators on `list_platforms`, `list_parameters`, and `fetch_cells`. Importing this module in a FastAPI process that has no active Streamlit server raises `streamlit.errors.NoSessionContext` or similar errors at import time (or at first call). The v2.0 app cannot reuse `ufs_service.py` without a refactor.

Additionally, Streamlit's `@st.cache_data` caches by function argument hash and copies the result per-session. `cachetools.TTLCache` does not copy — it returns the same object. If the v2.0 code (or any code path) mutates the cached DataFrame (e.g., `df["Result"] = df["Result"].str.upper()`), subsequent callers get the mutated version.

**Why it happens:**
The service layer was written inside the Streamlit mental model. The `@st.cache_data` decorator is woven into the function signatures (underscore-prefixed `_db` argument, `db_name` cache-key argument) in ways that are Streamlit-specific. A developer doing a quick port might add `cachetools` but miss the mutability difference.

**How to avoid:**
Refactor `ufs_service.py` to extract the pure logic into `_fetch_cells_impl(db, platforms, ...)` functions, then apply the decorator in a thin wrapper:
```python
# In ufs_service.py — framework-agnostic core
def _fetch_cells_impl(db, platforms, infocategories, items, row_cap, db_name):
    # actual SQL logic here
    ...

# Streamlit wrapper (v1.0 path)
@st.cache_data(ttl=60, show_spinner=False)
def fetch_cells(_db, platforms, infocategories, items, row_cap=200, db_name=""):
    return _fetch_cells_impl(_db, platforms, infocategories, items, row_cap, db_name)

# cachetools wrapper (v2.0 path) — must return a copy
import copy
from cachetools import TTLCache, cached
import threading

_cells_cache = TTLCache(maxsize=256, ttl=60)
_cells_lock = threading.Lock()

@cached(cache=_cells_cache, lock=_cells_lock,
        key=lambda db, platforms, infocategories, items, row_cap=200, db_name="":
            (platforms, infocategories, items, row_cap, db_name))
def fetch_cells_v2(db, platforms, infocategories, items, row_cap=200, db_name=""):
    df, capped = _fetch_cells_impl(db, platforms, infocategories, items, row_cap, db_name)
    return df.copy(), capped   # MUST copy — TTLCache returns same object to all callers
```

Note the cache key: Streamlit's `@st.cache_data` automatically excludes underscore-prefixed arguments from hashing. `cachetools` does not — the key lambda must explicitly exclude `db` (the adapter object) and include only the serializable filter arguments. Getting this wrong means either cache misses on every call (key includes unhashable db object) or stale cross-DB data (key is identical when db_name is omitted).

**Warning signs:**
- `import streamlit` at the top of `ufs_service.py` without a conditional guard.
- v2.0 app process exits at startup with `NoSessionContext` or `StreamlitAPIException`.
- Cached DataFrame modified in-place in one request; subsequent request sees modified data (only under `cachetools`, not `st.cache_data`).
- Cache miss rate is 100% in v2.0 (key lambda includes the `db` adapter object which is not hashable by default).

**Phase to address:** Phase 1 of v2.0 (Foundation) — this refactor is a prerequisite for any v2.0 feature. Add a test that imports `ufs_service` in a process with no Streamlit context and asserts no import-time error.
**Criticality:** BLOCKER — without this, v2.0 cannot start.

---

### Pitfall 4: Sync SQLAlchemy inside `async def` FastAPI route blocks the event loop

**What goes wrong:**
The existing `ufs_service.py` uses synchronous SQLAlchemy (`engine.connect()`, `pd.read_sql_query`). If a developer writes `async def` route handlers in v2.0 and calls `fetch_cells()` (or any sync DB function) directly inside them, the entire asyncio event loop blocks for the duration of the query. During a 200ms DB call, no other request can be handled — FastAPI's concurrency advantage is entirely negated, and at peak usage requests queue behind each other.

**Why it happens:**
FastAPI allows `async def` and `def` route handlers in the same app. Developers familiar with async Python often reach for `async def` by default, not realizing that calling a synchronous I/O function inside `async def` is worse than using a `def` route (which FastAPI automatically runs in a threadpool).

**How to avoid:**
The correct pattern for this project (sync SQLAlchemy + sync pandas): declare route handlers as plain `def`, not `async def`. FastAPI runs `def` handlers in an external threadpool (Starlette's `run_in_threadpool`), so they don't block the event loop:
```python
# CORRECT for sync SQLAlchemy
@app.get("/api/platforms")
def get_platforms(db: DBAdapter = Depends(get_db)):
    return list_platforms(db)

# WRONG — blocks event loop
@app.get("/api/platforms")
async def get_platforms(db: DBAdapter = Depends(get_db)):
    return list_platforms(db)   # sync call inside async def = event loop blocked
```

The threadpool is limited to `min(32, os.cpu_count() + 4)` threads by default. For an intranet app with ~5–10 concurrent users this is more than sufficient; no threadpool tuning is needed.

Do NOT introduce async SQLAlchemy (`asyncpg`, `aiomysql`) just to be able to use `async def` routes. That would require replacing the entire DB adapter stack, which is out of scope for v2.0. The `def` route pattern is the correct choice given the existing sync engine.

**Warning signs:**
- `async def` route handlers that call `pd.read_sql_query`, `engine.connect()`, or any `@st.cache_data`/`cachetools.cached` function.
- Profiling shows all requests serializing through one request at a time despite multiple concurrent users.
- `anyio.from_thread.run_sync` or `asyncio.get_event_loop().run_in_executor` added as a workaround — flag these for review.

**Phase to address:** Phase 1 of v2.0 (Foundation) — establish `def` (not `async def`) as the standard for all DB-touching routes. Add a linting rule or code review checklist item.
**Criticality:** SERIOUS — degrades concurrency and response time for all users if even one `async def` + sync DB call pair exists.

---

### Pitfall 5: HTMX 4xx/5xx responses are silently discarded — validation errors and server errors disappear

**What goes wrong:**
By default, HTMX does not swap responses with HTTP 4xx or 5xx status codes. If a FastAPI route returns a `422 Unprocessable Entity` (validation error), `400 Bad Request`, or `500 Internal Server Error`, HTMX silently ignores the response body. The user sees the spinner disappear and nothing happen — no error message, no explanation. This is HTMX's documented behavior and affects form submissions (content save, filter changes, platform add/remove) and the AI Summary button.

The FastAPI validation framework returns `422` by default for Pydantic model validation failures, which makes this especially likely to be hit during normal development.

**Why it happens:**
New HTMX users expect HTTP semantics: "the response body is the response." HTMX's response model is "swap the body into the DOM, but only on success." The distinction between success codes and error codes is not obvious until you hit it in the browser.

**How to avoid:**
Option A (preferred for this project): Add a global `htmx:beforeSwap` handler in `base.html` that allows error responses to swap:
```javascript
document.body.addEventListener('htmx:beforeSwap', function(evt) {
    if (evt.detail.xhr.status >= 400) {
        evt.detail.shouldSwap = true;
        evt.detail.isError = true;
    }
});
```
Then ensure every error-producing FastAPI route returns an HTML fragment (not JSON) with a meaningful error message targeting the appropriate `<div id="error-banner">`.

Option B: Use the `response-targets` HTMX extension to route 4xx responses to a dedicated error target:
```html
<div hx-post="/save" hx-target="#content" hx-target-error="#error-banner"
     hx-ext="response-targets">
```

Do NOT return JSON error bodies from HTMX-facing routes — even if `shouldSwap` is enabled, rendering raw JSON in a DOM node is not user-friendly.

**Warning signs:**
- Form submissions on the content edit page produce no visible response after introducing a validation error.
- Browser DevTools Network tab shows a `422` response with a body, but the page does not update.
- No `htmx:beforeSwap` or `response-targets` extension in `base.html`.

**Phase to address:** Phase 1 of v2.0 (Foundation / Shell) — add the error handling pattern to `base.html` before building any forms. Every form added thereafter inherits it automatically.
**Criticality:** SERIOUS — without this, all validation errors and server errors are invisible to users.

---

### Pitfall 6: HTMX double-submission — AI Summary and content save fire twice on impatient clicks

**What goes wrong:**
HTMX does not prevent double-submission out of the box. If the AI Summary button (which triggers a slow LLM call, potentially 5–30 seconds) or the content save form is clicked twice before the first response arrives, two identical requests are sent. For the AI Summary, this means two concurrent LLM API calls at doubled cost. For content save, it can mean two concurrent writes to the same `.md` file (race condition on disk, last write wins with potential interleaving).

**Why it happens:**
The network latency and LLM response time is longer than a user's patience. `<button>` elements do not auto-disable on click in HTML; HTMX does not add any debouncing by default.

**How to avoid:**
Use `hx-disabled-elt` to disable the triggering element for the duration of the request:
```html
<!-- AI Summary button -->
<button hx-post="/platforms/{{ platform_id }}/summary"
        hx-target="#summary-{{ platform_id }}"
        hx-disabled-elt="this"
        hx-indicator="#spinner-{{ platform_id }}">
  Get AI Summary
</button>

<!-- Content save form -->
<form hx-post="/platforms/{{ platform_id }}/content"
      hx-target="#content-area"
      hx-disabled-elt="find button[type=submit]">
  <textarea name="content">...</textarea>
  <button type="submit">Save</button>
</form>
```

Note the documented `hx-disabled-elt` bug (open as of July 2025): elements are re-enabled when the response arrives, which may be before the DOM has settled after the swap. For the AI Summary button specifically, also swap in a "Loading..." state to the button text via OOB swap so users have clear visual feedback.

**Warning signs:**
- Browser DevTools shows duplicate POST requests for the AI Summary or content save.
- LLM cost spikes when users report the button "not responding" (they kept clicking).
- Content files show occasional corrupted state (truncated or doubled content) after saves.

**Phase to address:** Phase 2 of v2.0 (Content + Overview HTMX interactions) — apply `hx-disabled-elt` to every form and long-running button. Add a test that POSTs to the summary endpoint twice rapidly and asserts the second request is rejected or idempotent.
**Criticality:** SERIOUS — cost (LLM calls) and data integrity (file writes) implications.

---

### Pitfall 7: HTMX OOB swap silently fails when target ID is wrong or missing from the DOM

**What goes wrong:**
Out-of-band (OOB) swaps (`hx-swap-oob="true"`) match by element ID. If the server response includes `<div id="platform-count" hx-swap-oob="true">5</div>` but the page does not have an element with `id="platform-count"`, HTMX silently discards the OOB element with no error or warning. The counter, notification badge, or status area never updates. This is particularly subtle because it works in development (where the page was freshly loaded) but fails after a partial HTMX navigation that replaced the section containing the ID.

**Why it happens:**
OOB swaps depend on the current DOM state, which changes as HTMX navigation progresses. The target ID must exist in the current DOM at the time the response is processed. If `hx-boost` or a prior HTMX swap replaced the container holding the target ID with a fragment that doesn't include it, the OOB target vanishes.

**How to avoid:**
- Keep OOB targets in the persistent shell (`base.html` layout elements — nav bar, tab headers, notification area) rather than in tab content areas that get swapped out.
- Add a JavaScript `htmx:afterSwap` handler during development that warns if an OOB element ID had no match: check `evt.detail.target === null`.
- Test: use HTMX history navigation (back/forward) after a sequence of filter changes, then trigger an OOB-producing action, and assert the OOB target updated.

**Warning signs:**
- Platform count badge or "has content" toggle in the overview tab does not update after adding a platform.
- OOB-containing responses show the response body in DevTools but the DOM element doesn't change.
- The bug only manifests after navigating away and back to the overview tab.

**Phase to address:** Phase 2 of v2.0 (Overview tab with filters) — design OOB targets around the persistent shell layout from the start.
**Criticality:** MODERATE — affects correctness of secondary UI state updates (counters, badges), not primary content.

---

### Pitfall 8: `hx-boost` on the tab navigation pushes fragment URLs to browser history — back button breaks

**What goes wrong:**
If `hx-boost` is applied to the top-nav tab links, HTMX replaces the full page load with an AJAX request and pushes the URL to browser history. When the user hits the browser back button, the browser re-fetches the previous URL. If the server returns an HTML fragment (tab content only) for that URL, the browser renders the fragment without the surrounding shell — a broken page. This is a documented HTMX quirk: history restoration pulls the last cached XHR response for the URL, which may be a fragment, not a full page.

**Why it happens:**
The HTMX history cache stores the HTML content of pages as they were when navigated. If `hx-boost` makes a request that returns a full page but the response is trimmed by `hx-select`, the cached version is the trimmed fragment. On browser back, HTMX restores the fragment without the shell.

**How to avoid:**
For the three-tab shell (Overview / Browse / Ask), do NOT use `hx-boost`. Use explicit `hx-get` + `hx-target="#main-content"` + `hx-push-url="true"` on tab links, and ensure every tab URL also has a server route that returns the full page (not a fragment) when loaded directly:
```python
@app.get("/browse")
def browse_tab(request: Request):
    # If HX-Request header present, return fragment only
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("browse_fragment.html", ...)
    # Otherwise return full page
    return templates.TemplateResponse("browse_full.html", ...)
```
This pattern ensures direct URL navigation (bookmark, back button, refresh) always produces a full page, while HTMX navigation swaps only the content fragment.

Set `historyCacheSize: 0` in `htmx.config` if history support is not needed, to force server requests on back/forward rather than cache restoration.

**Warning signs:**
- Pressing browser back after clicking tabs shows only the tab content without the navigation bar.
- `hx-boost="true"` on `<nav>` or `<ul class="nav-tabs">` elements.
- `history.pushState` entries in browser DevTools pointing to fragment-only responses.

**Phase to address:** Phase 1 of v2.0 (Shell/Navigation) — establish the full-page vs fragment routing pattern before implementing any tab. Adding it retroactively requires updating every tab route.
**Criticality:** MODERATE — UX regression for users who use back button or bookmarks.

---

### Pitfall 9: NL agent safety harness bypassed by transport layer change — v1.0 SAFE guards not wired to v2.0 Ask tab

**What goes wrong:**
The v1.0 NL agent (`app/nl_agent.py`) includes a multi-layer safety harness: `sqlparse` SELECT-only validator, UNION/CTE guard, LIMIT injector, path scrubber, `<db_data>` wrapper, step-cap, and wall-clock timeout. These guards are invoked by the Streamlit `Ask` page at specific call points. When porting the Ask tab to v2.0, a developer might wire the FastAPI route directly to the PydanticAI `agent.run()` call and skip the guard middleware, especially if they are not the same person who wrote v1.0.

The v1.0 safety harness is not inside the agent itself — it is in the service/page layer around the agent. It is therefore NOT automatically inherited by the v2.0 Ask route.

**Why it happens:**
The guard code is in `app/pages/ask_page.py` (Streamlit-specific), not in `app/nl_agent.py` (framework-agnostic). The agent module can be imported and called directly without the guards applying. The v2.0 developer sees "reuse v1.0 nl_agent" in the plan but does not realize the guards live elsewhere.

**How to avoid:**
Before v2.0 development starts, refactor the safety layer into a framework-agnostic `app/services/nl_service.py` that wraps `agent.run()` with all guards applied:
```python
# app/services/nl_service.py — framework-agnostic; safe to import in v1.0 and v2.0
async def run_nl_query(question: str, db: DBAdapter, llm_config: LLMConfig) -> NLResult:
    # 1. Validate question (length, encoding)
    # 2. Call agent.run() with step_cap, timeout
    # 3. Validate generated SQL (sqlparse, SELECT-only, allowed_tables, LIMIT inject)
    # 4. Apply path scrub if OpenAI backend
    # 5. Wrap result rows in <db_data> before returning
    ...
```
Both v1.0 (`ask_page.py`) and v2.0 (FastAPI Ask route) import `nl_service.py`. The guards cannot be bypassed accidentally.

**Warning signs:**
- v2.0 Ask route imports `agent.run()` directly from `app/nl_agent.py` without going through a service wrapper.
- Code review of v2.0 Ask route finds no call to `sqlparse` validator or `allowed_tables` check.
- The SAFE-02 through SAFE-06 tags from v1.0 do not appear in v2.0 Ask route code.

**Phase to address:** Phase 0 of v2.0 (pre-work / shared module refactor) — before v2.0 Ask tab is started, the safety harness must be extracted to `nl_service.py`. This is a prerequisite, not a concurrent task.
**Criticality:** SERIOUS — bypassing the safety harness re-exposes SQL injection, DML generation, full table scan, and data leakage risks that v1.0 specifically closed.

---

### Pitfall 10: `st.session_state`-based LLM backend selection has no equivalent in v2.0 — preference silently defaults

**What goes wrong:**
In v1.0, the user's active LLM backend (OpenAI vs Ollama) is stored in `st.session_state["llm_backend"]`. FastAPI has no `session_state`. Without a replacement, v2.0 has three bad options: (a) hardcode the default at startup (users can't switch at runtime), (b) pass the choice as a form/query parameter on every request (UI complexity, bookmarkable but fragile), or (c) use a server-side session stored in a signed cookie (adds middleware dependency).

Auth is deferred in v2.0 (same as v1.0), which means there is no user identity to hang per-user preferences on. If the backend selection is stored in a cookie without user identity, all users sharing a browser share the preference — which is acceptable for the PBM2 use case (team of users with similar sensitivity preferences) but must be an explicit, documented decision.

**Why it happens:**
Streamlit's `session_state` is invisible to developers until it's absent. v2.0 planning naturally inherits the v1.0 mental model of per-session mutable state without examining the transport mechanism.

**How to avoid:**
For v2.0 (auth-deferred, intranet, small team): store the LLM backend preference in a client-side cookie with `SameSite=Lax`:
```python
from fastapi import Response, Cookie

@app.post("/settings/llm-backend")
def set_llm_backend(backend: str, response: Response):
    if backend not in ("openai", "ollama"):
        raise HTTPException(400, "Invalid backend")
    response.set_cookie("llm_backend", backend, samesite="lax", httponly=False)
    return {"ok": True}

@app.get("/ask")
def ask_tab(request: Request, llm_backend: str = Cookie(default="ollama")):
    # default to Ollama (matches v1.0 decision D-25)
    ...
```
`httponly=False` is intentional here — the UI JavaScript needs to read the current backend to render the radio selection correctly. Do NOT store sensitive data in this cookie.

Document the decision: "LLM backend preference is a browser-scoped cookie, not a per-user server-side state. All users on the same browser share it. This is acceptable for the intranet/team use case."

**Warning signs:**
- v2.0 Ask tab always uses Ollama (or always OpenAI) regardless of user selection.
- Backend selection resets on every page refresh.
- v2.0 routes import `st.session_state` — this will raise `NoSessionContext` in a FastAPI process.

**Phase to address:** Phase 3 of v2.0 (Ask/Browse carry-over) — when implementing the Ask tab, include the cookie-based backend selector from the start. Do not defer to a later phase since it affects the AI Summary feature in Phase 2 as well.
**Criticality:** MODERATE — functional regression from v1.0 if not handled; affects data sensitivity decisions.

---

### Pitfall 11: `cachetools.TTLCache` is not thread-safe by default — concurrent FastAPI requests corrupt the cache

**What goes wrong:**
`cachetools.TTLCache` is documented as NOT thread-safe. FastAPI `def` routes run in a threadpool; multiple concurrent requests can call `list_platforms()` or `fetch_cells()` simultaneously. Without a lock, concurrent access to a shared `TTLCache` can produce `KeyError` during `expire()`, return stale or partially-written entries, or raise `RuntimeError: dictionary changed size during iteration` under cache eviction.

**Why it happens:**
Developers copy `@cached(cache=TTLCache(...))` patterns from examples that omit the lock parameter because they assume single-threaded usage (scripts, Jupyter notebooks). The cachetools docs mention thread safety but it is easy to miss.

**How to avoid:**
Always pair `TTLCache` with a `threading.Lock`:
```python
import threading
from cachetools import TTLCache, cached

_platforms_cache = TTLCache(maxsize=32, ttl=300)
_platforms_lock = threading.Lock()

@cached(cache=_platforms_cache, lock=_platforms_lock,
        key=lambda db, db_name="": db_name)
def list_platforms_v2(db: DBAdapter, db_name: str = "") -> list[str]:
    ...
```
The `key` lambda must exclude unhashable arguments (the `db` adapter) — use only serializable values (`db_name` string) as the cache key.

**Warning signs:**
- `@cached(cache=TTLCache(...))` without a `lock=` parameter anywhere in the codebase.
- `RuntimeError: dictionary changed size during iteration` in logs under load.
- `KeyError` in `cachetools` internals appearing intermittently under concurrent test runs.

**Phase to address:** Phase 1 of v2.0 (Foundation / ufs_service refactor) — add the lock at the same time as the `TTLCache` is introduced. Never introduce a `TTLCache` without a lock in this codebase.
**Criticality:** MODERATE — intermittent data corruption under concurrent requests; hard to reproduce in single-user testing.

---

### Pitfall 12: Two separate DB connection pools (v1.0 Streamlit + v2.0 FastAPI) can exhaust MySQL `max_connections`

**What goes wrong:**
Running both apps in parallel means two separate Python processes, each with their own SQLAlchemy connection pool. SQLAlchemy's default pool is `pool_size=5, max_overflow=10` — so each process can hold up to 15 connections. Two processes = up to 30 connections. If the intranet MySQL server has `max_connections=50` (a common default for small servers), and other services also connect, the DB can run out of connections during peak usage, causing `pymysql.err.OperationalError: (1040, 'Too many connections')`.

**Why it happens:**
Each SQLAlchemy `create_engine()` call creates an independent pool. There is no cross-process pool sharing with SQLAlchemy's default pool. Developers running both apps locally never see this because their local MySQL has `max_connections=151` by default.

**How to avoid:**
- Explicitly set smaller pool sizes for the parallel-running period: `pool_size=2, max_overflow=3` on both apps during parallel operation. This limits each app to 5 connections, totaling 10 for both — well within a conservatively configured MySQL server.
- Document the pool sizing in both apps' DB adapter initialization with a comment: `# Sized small to leave headroom for parallel v1.0 deployment`.
- When v2.0 is confirmed stable and v1.0 is retired, restore normal pool sizes.
- Add a health-check endpoint in v2.0 (`GET /health`) that tests the DB connection — use this to monitor connection availability without consuming a connection slot on every HTTP probe.

**Warning signs:**
- `OperationalError: (1040, 'Too many connections')` in either app's logs, especially during the transition period.
- `SHOW PROCESSLIST` on MySQL shows > 30 connections from the app server host.
- DB pool pre-ping (`pool_pre_ping=True`) logs showing repeated reconnects (connections being recycled frequently due to pool pressure).

**Phase to address:** Phase 1 of v2.0 (Foundation) — before deploying v2.0 alongside v1.0, explicitly configure small pool sizes. Add the pool sizing to the deployment checklist.
**Criticality:** MODERATE — only manifests under concurrent usage with both apps running; single-user testing will not catch it.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Copy `ufs_service.py` into `v2/` rather than refactoring for dual use | No refactor risk | Two diverging codebases; DB bug fixed in one, not the other | Never — imports only, no copies |
| Use `MarkdownIt()` default (CommonMark, html=True) for content pages | Works out of the box | XSS via user content; audit failures | Never for user-editable content |
| Use `async def` routes for all FastAPI handlers | "Best practice" feeling | Sync SQLAlchemy blocks event loop; all concurrency serialized | Never with sync SQLAlchemy |
| Skip `hx-disabled-elt` on forms | Simpler HTML | Double-submit LLM calls (cost), concurrent file writes (data loss) | Never on expensive or non-idempotent operations |
| Validate PLATFORM_ID shape only via DB existence check (not regex) | Simpler code | Race between regex and DB lookup; DB lookup IS the file access | Never — regex must precede all file I/O |
| Store all per-user prefs in server-side session (dict in memory) | Simpler than cookies | State lost on server restart; no cross-process sharing | Acceptable only after auth is enabled (user identity exists) |
| Skip CSRF tokens for intranet app | One less dependency | Acceptable NOW for same-origin SameSite=Lax; unacceptable if app ever moves to internet | Acceptable for current intranet-only deployment with `SameSite=Lax` cookies |
| Return JSON from HTMX-facing routes on error | DRY (one error format) | JSON rendered as text in DOM; users see raw `{"detail": "..."}` | Never for HTMX routes — return HTML fragments for errors |
| Single `TTLCache` without lock | Less boilerplate | Thread-unsafe; `RuntimeError` under concurrent FastAPI routes | Never in FastAPI (multi-threaded by default) |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| HTMX + FastAPI form validation | Route returns 422; HTMX silently discards it | Configure `htmx:beforeSwap` to allow 4xx swap, or use `response-targets` extension; return HTML error fragment |
| markdown-it-py + user content | `MarkdownIt()` with default preset (html=True) | `MarkdownIt("js-default")` disables raw HTML passthrough |
| cachetools.TTLCache + FastAPI threadpool | `@cached(TTLCache(...))` without `lock=` | Always pair with `threading.Lock()`; key lambda must exclude unhashable db object |
| FastAPI + sync SQLAlchemy | `async def` route calling `pd.read_sql_query` | Use `def` route; FastAPI automatically runs it in threadpool |
| HTMX + 4xx responses | Server sends 422; browser shows nothing | Add global `htmx:beforeSwap` handler or `response-targets` extension to `base.html` |
| HTMX + history navigation (hx-boost) | Tab fragment served as full page on browser back | Use `HX-Request` header detection to return fragment vs full page; or disable `hx-boost` for tab nav |
| Content file path + user input | `open(f"content/platforms/{platform_id}.md")` | `Path(..., pattern=r'^[A-Za-z0-9_\-]{1,128}$')` + `Path.resolve()` prefix check |
| v2.0 Ask route + v1.0 safety harness | Import `agent.run()` directly | Extract guards to `nl_service.py`; both v1.0 and v2.0 call `nl_service.run_nl_query()` |
| OOB swap + tab navigation | OOB target ID absent after tab swap | Keep OOB targets in persistent shell elements, not swappable tab content |
| Two processes + MySQL pool | Default `pool_size=5, max_overflow=10` per process | Reduce to `pool_size=2, max_overflow=3` during parallel deployment period |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `MarkdownIt()` default on user content | XSS: `<script>` in content page executes in all browsers that view it | `MarkdownIt("js-default")` — zero raw HTML passthrough |
| No path validation before file I/O on `platform_id` | Path traversal: read `../../config/settings.yaml`, `.env`, `auth.yaml` | Regex `^[A-Za-z0-9_\-]{1,128}$` + `Path.resolve()` prefix assertion before every file open |
| CSRF: For current intranet deployment | LOW: same-origin HTMX posts, `SameSite=Lax` cookies provide adequate protection for intranet-only app | Document the decision; re-evaluate if app is ever exposed to internet or cross-origin iframes |
| NL agent safety harness not wired in v2.0 | DML injection, full table scan, data leakage — same risks as pre-harness v1.0 | Extract harness to `nl_service.py`; mandate its use via code review |
| `async def` route + sync DB call | Not a security risk but causes availability denial under load (event loop blocks) | Enforce `def` routes for all DB-touching handlers |
| LLM backend cookie without `SameSite=Lax` | CSRF risk if app is ever cross-origin embedded | Always set `samesite="lax"` on the backend preference cookie |
| CSP: HTMX + `unsafe-eval` or `unsafe-inline` | HTMX's `hx-on:*` attributes and `hyperscript` require `unsafe-inline` or `unsafe-eval` if used; this weakens CSP | Avoid `hx-on:*` and hyperscript for security-sensitive actions; prefer server-side logic with simple `hx-get`/`hx-post` |
| Direct HTML injection into Jinja2 templates from markdown | If `{{ markdown_html | safe }}` is used without the `"js-default"` preset, the `safe` filter bypasses Jinja2's auto-escape | Use `"js-default"` preset BEFORE applying `| safe` in templates |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Sync DB call inside `async def` route | All requests serialize; 5 concurrent users each wait for prior user's query | Use `def` routes for all DB-touching handlers | Any concurrent usage |
| HTMX AI Summary: no request deduplication or caching | Each click fires a full LLM call even if content hasn't changed | Cache summary in a per-platform file or DB record; serve cached version if content unchanged | Every impatient click |
| Full pivot DataFrame returned in HTMX HTML fragment response | HTML response for 1000-row pivot table is 500KB+ | Apply same row_cap/col_cap as v1.0; paginate or apply client-side Bootstrap table scroll | > 200 rows in pivot |
| TTLCache without lock under concurrent requests | Intermittent `RuntimeError` + cache inconsistency | Always add `threading.Lock()` | > 1 concurrent user |
| Content page markdown file read on every request (no caching) | File I/O on every page view; slow for NFS-backed file storage | Add `TTLCache` on content read with TTL matching write frequency | Network storage; > 50 req/min |
| Two processes + small MySQL `max_connections` | `(1040, 'Too many connections')` | Reduce pool sizes during parallel deployment | > 10 concurrent users across both apps |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| AI Summary loading indicator stays visible if LLM times out or returns error | Spinner never hides; user thinks app is broken | Add `htmx:afterRequest` handler that always hides the indicator; display error message in summary area |
| Content edit textarea with no preview | Users paste markdown, save, navigate to view — slow feedback loop | Add a client-side preview toggle (Bootstrap tab inside the edit modal): Edit tab / Preview tab; marked.js client-side preview is lightweight and adds no server dependency |
| HTMX filter changes have no "Loading..." state during DB query | Rapid filter changes produce flicker or stale data visible during load | Add `hx-indicator` pointing to a subtle spinner near the platform list; debounce filter inputs with `hx-trigger="change delay:300ms"` |
| OOB swap updates counters but doesn't animate, so users miss the change | Users don't notice platform count changed after add/remove | Add a brief CSS highlight animation on elements updated via OOB swap |
| Markdown content pages with no content show a blank area, no call to action | Users don't know they can add content | Explicitly render an "Add content for this platform" empty state with an "Edit" button when no `.md` file exists |
| Ask tab NL-05 two-turn confirmation flow over HTMX: second step (confirm params) requires state from first step | HTMX is stateless; the candidate params from step 1 need to survive to step 2 | Store candidate params in a hidden form field or a signed server-side token in the response; do not rely on session state |

---

## "Looks Done But Isn't" Checklist

- [ ] **markdown-it-py preset:** `MarkdownIt("js-default")` used everywhere content pages are rendered — verify with `assert "<script>" not in md.render("<script>alert(1)</script>")`.
- [ ] **Path traversal:** `GET /platforms/..%2F..%2Fetc%2Fpasswd/content` returns 400/404, never 200 with file content — verify with integration test.
- [ ] **HTMX 4xx handling:** Submitting an invalid content save (e.g., empty `platform_id`) shows a visible error in the page — verify by submitting the form with a malformed value.
- [ ] **Double submit prevention:** Clicking AI Summary button twice in quick succession sends exactly one LLM request — verify with `hx-disabled-elt` and network inspection.
- [ ] **Safety harness:** v2.0 Ask tab route goes through `nl_service.run_nl_query()`, not directly to `agent.run()` — verify by code review of the Ask route handler.
- [ ] **NL agent `allowed_tables` guard active:** Feed v2.0 Ask tab a prompt that should produce `SELECT * FROM mysql.user` — assert it is rejected with an error, not executed.
- [ ] **Sync route handlers:** No `async def` route in v2.0 calls `pd.read_sql_query` or any `cachetools.cached` function directly — verify with a `grep -r "async def" v2/` + manual review.
- [ ] **cachetools lock:** Every `TTLCache` instance has a corresponding `threading.Lock()` in its `@cached` decorator — verify by code search for `TTLCache` without adjacent `Lock`.
- [ ] **ufs_service import isolation:** `import ufs_service` in a plain Python process (no Streamlit) raises no `StreamlitAPIException` — verify with a unit test.
- [ ] **Connection pool sizing:** Both apps running in parallel consume fewer than 20 MySQL connections total — verify with `SHOW STATUS LIKE 'Threads_connected'` under load.
- [ ] **Browser history:** Pressing back button after HTMX tab navigation loads a full page with shell, not a bare fragment — verify with manual browser test.
- [ ] **LLM backend preference:** LLM backend selection persists across page refreshes as a cookie defaulting to Ollama — verify by selecting OpenAI, refreshing, and checking the cookie.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| XSS via markdown-it-py default discovered after content pages deployed | MEDIUM | Switch to `"js-default"` preset immediately; audit all existing `.md` files for `<script>` tags and HTML injection patterns; rotate session cookies (if any were exfiltrated) |
| Path traversal discovered in production | HIGH | Add regex + resolve check immediately; audit access logs for `../` in URL parameters; rotate secrets if `settings.yaml` or `.env` was accessible |
| Safety harness missing from v2.0 Ask tab discovered | HIGH | Immediately disable Ask tab in v2.0; extract guards to `nl_service.py`; add guards to v2.0 route; re-enable only after code review |
| DB connection exhaustion | LOW | Reduce pool sizes on both apps; restart both processes; monitor `SHOW STATUS LIKE 'Threads_connected'` |
| `TTLCache` thread-safety bug causes stale data or crashes | MEDIUM | Add locks immediately; restart v2.0 process; verify no corrupted cache entries served to users |
| HTMX double-submit caused duplicate LLM bills | LOW | Add `hx-disabled-elt`; review OpenAI billing for the period; no persistent data damage if content writes were idempotent |
| NL-05 two-turn flow broken over HTMX (state lost between steps) | MEDIUM | Redesign step-2 to carry step-1 params in a hidden field or signed form token; test round-trip |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| markdown-it-py XSS via default preset | Phase 1 v2.0 (Foundation) | Unit test: `<script>` injection does not appear in rendered output |
| Path traversal via PLATFORM_ID | Phase 1 v2.0 (Foundation) | Integration test: `../` in path param returns 400/404 |
| ufs_service Streamlit import coupling | Phase 0 v2.0 (pre-work) | Import test: no `StreamlitAPIException` in non-Streamlit process |
| Sync SQLAlchemy in async def routes | Phase 1 v2.0 (Foundation) | Code review: all DB-touching routes are `def`, not `async def` |
| HTMX 4xx silent discard | Phase 1 v2.0 (Shell) | Manual test: form validation error shows visible error message |
| HTMX double-submission | Phase 2 v2.0 (Content + Overview) | Network test: two rapid clicks = one request |
| HTMX OOB silent ID mismatch | Phase 2 v2.0 (Overview filters) | Manual test: OOB target updates after HTMX navigation + filter change |
| hx-boost / history fragment breakage | Phase 1 v2.0 (Shell/Navigation) | Manual test: browser back after tab navigation loads full page |
| NL safety harness not wired | Phase 0 v2.0 (pre-work) | Code review: v2.0 Ask route uses nl_service.run_nl_query() |
| Session state migration (LLM backend pref) | Phase 3 v2.0 (Ask carry-over) | Cookie test: backend selection persists across refresh, defaults to Ollama |
| TTLCache thread safety | Phase 1 v2.0 (Foundation) | Code search: every TTLCache has threading.Lock() |
| Dual-process DB pool exhaustion | Phase 1 v2.0 (Foundation / deployment) | Load test: SHOW STATUS under concurrent access shows < 20 connections |

---

## CSRF Assessment for This Project

**Verdict for current deployment: CSRF tokens NOT required — `SameSite=Lax` cookies + intranet-only suffice.**

HTMX POSTs are same-origin requests. For intranet-only deployment with no cross-origin embeds, the `SameSite=Lax` cookie attribute (the default in modern browsers) prevents cross-site request forgery. An attacker would need to be on the same intranet to make same-origin requests, which is equivalent to having physical network access.

**Conditions that would change this verdict:**
- App is exposed to the public internet: add `fastapi-csrf-protect` or `fastapi-csrf-jinja`.
- App is embedded in an iframe from a different domain: `SameSite=Lax` does not protect in this case.
- Auth is enabled and session tokens are stored in cookies: CSRF token required for all mutating routes.

For now: document this as a deliberate decision in `DECISIONS.md` with the conditions that would trigger a revisit.

---

## Sources

- markdown-it-py security docs (confirmed `html=True` default, `"js-default"` recommendation): https://markdown-it-py.readthedocs.io/en/latest/security.html
- HTMX quirks (official): https://htmx.org/quirks/
- HTMX hx-swap attribute: https://htmx.org/attributes/hx-swap/
- HTMX response targets extension: https://htmx.org/extensions/response-targets/
- HTMX hx-disabled-elt attribute: https://htmx.org/attributes/hx-disabled-elt/
- HTMX hx-swap-oob attribute: https://htmx.org/attributes/hx-swap-oob/
- HTMX hx-boost history issue #2278: https://github.com/bigskysoftware/htmx/issues/2278
- HTMX history fragment restore issue #497: https://github.com/bigskysoftware/htmx/issues/497
- HTMX CSP / unsafe-eval analysis (2024): https://www.sjoerdlangkemper.nl/2024/06/26/htmx-content-security-policy/
- FastAPI async docs (sync def threadpool behavior): https://fastapi.tiangolo.com/async/
- FastAPI sync SQLAlchemy event loop blocking (Medium, 2025): https://medium.com/@patrickduch93/the-hidden-trap-in-fastapi-projects-accidently-using-sync-sql-alchemy-in-an-async-app-245b0391a17d
- cachetools thread safety issue #294: https://github.com/tkem/cachetools/issues/294
- cachetools documentation (lock parameter): https://cachetools.readthedocs.io/
- FastAPI path parameters (pattern validation): https://fastapi.tiangolo.com/tutorial/path-params/
- Path traversal prevention — OWASP: https://owasp.org/www-community/attacks/Path_Traversal
- SQLAlchemy connection pooling (multi-process): https://docs.sqlalchemy.org/en/20/core/pooling.html
- fastapi-csrf-protect PyPI: https://pypi.org/project/fastapi-csrf-protect/
- HTMX + FastAPI patterns 2025: https://johal.in/htmx-fastapi-patterns-hypermedia-driven-single-page-applications-2025/
- v1.0 PITFALLS.md (carries forward applicable pitfalls): /home/yh/Desktop/02_Projects/Proj28_PBM2/.planning/research/v1.0/PITFALLS.md

---
*Pitfalls research for: FastAPI + Bootstrap 5 + HTMX v2.0 migration of PBM2 (EAV-MySQL Streamlit → FastAPI parallel rewrite)*
*Researched: 2026-04-23*
