# Phase 03: Content Pages + AI Summary — Research

**Researched:** 2026-04-25
**Domain:** Markdown CRUD with HTMX + atomic file writes + LLM-backed in-place summarization on FastAPI 0.136
**Confidence:** HIGH (stack pinned in CLAUDE.md/CONTEXT.md; all critical claims verified against installed `.venv` packages and existing app_v2/v1.0 code)

---

## Summary

This phase has two intersecting domains: (1) safe markdown CRUD over FastAPI+HTMX with atomic POSIX writes, and (2) a single-shot LLM summary call wrapped in a TTLCache + classified error UX. Both domains are anchored — versions are pinned in CONTEXT.md, the patterns are pre-decided in 31 D-numbers, and the integration points (cache module, atomic-write idiom, has_content_file, openai SDK wiring, Jinja2Blocks templates) already exist in the codebase from Phase 01/02.

**Primary recommendation:** Treat this phase as **assembly, not invention**. Reuse `app_v2/services/overview_store._atomic_write` verbatim (extracted into `app_v2/data/atomic_write.py`), reuse `has_content_file` for the path-traversal guard, reuse the `app_v2/services/cache.py` TTLCache+Lock pattern for `summary_service`, and reuse `openai.OpenAI(api_key=..., base_url=...)` exactly as `app/adapters/llm/openai_adapter.py` already wires it (Ollama and OpenAI both go through the same client — Ollama just uses base_url). Don't introduce new abstractions; mirror Phase 02 plan structure.

**The four risk concentrations** (where bugs will appear if not addressed in plans):
1. Cross-process race on save (D-24 explicit user override — fork-only multiprocessing test)
2. mtime cache-key drift on filesystems with sub-second resolution
3. openai SDK error → classified `reason` mapping (D-16 has 7 categories — must be exhaustive)
4. jinja2-fragments `block_names=` ordering when a template contains nested OOB blocks (Phase 02 hit this with `filter_oob`)

---

## User Constraints (from CONTEXT.md)

> Copied verbatim from `.planning/phases/03-content-pages-ai-summary/03-CONTEXT.md` — these are LOCKED. Do not relitigate.

### Locked Decisions (D-01 .. D-31)

**Detail page architecture (Area 1):**
- D-01: Detail page at `/platforms/{platform_id}` (own URL, not drawer/inline).
- D-02: Layout = shared navbar + single full-width `.panel` card. Title row with PLATFORM_ID + Brand/SoC/Year badges + top-right toolbar (Edit/Delete when content exists; "Add Content" when empty).
- D-03: Article max-width 800px; `line-height: 1.6` for rendered markdown.
- D-04: PLATFORM_ID validated by FastAPI `Path(..., pattern=r'^[A-Za-z0-9_\-]{1,128}$')`. Before any FS I/O, `pathlib.Path.resolve()` + `relative_to(BASE)` — identical to `has_content_file` pattern.
- D-05: Browser back from detail page returns to Overview tab in prior state. No client-side navigation library.

**Edit/Preview UX (Area 2):**
- D-06: Edit view replaces rendered area via `hx-swap="outerHTML"`. Bootstrap `.nav .nav-pills` `[Write] [Preview]` (Write active). Bottom-right `[Cancel] [Save]`.
- D-07: Preview tab `hx-post="/platforms/{id}/preview"` with textarea content. Trigger: `click, keyup changed delay:500ms from:#md-textarea`.
- D-08: Preview uses same `MarkdownIt("js-default")` pipeline as rendered view (CONTENT-05). HTML passthrough disabled (XSS defense per Pitfall 1).
- D-09: Save: `hx-post`. 200 → rendered-view fragment swaps editor back. 422 → Bootstrap alert into `#htmx-error-container`.
- D-10: Cancel is **client-side only** (CONTENT-07). `data-cancel-html` on edit panel + `hx-on:click` swaps back. No server round-trip.
- D-11: No autosave. No dirty-check prompt.

**AI Summary UX (Area 3):**
- D-12: AI Summary button on BOTH Overview row AND detail page header. Both use `.ai-btn` violet gradient pill.
- D-13: Overview row: enabled when `has_content_file(pid, CONTENT_DIR)` is True. Replaces Phase 02 disabled stub.
- D-14: Loading state via `hx-indicator` pointing at `#summary-{pid}-spinner` (UI-SPEC §8a definitive). Pre-seeded `htmx-indicator` div, not a server-returned loading fragment.
- D-15: Success state: rendered summary text in `.panel` mini-card + Regenerate button (sparkle icon) bottom-right.
- D-16: Error state: `.alert .alert-warning` (recoverable, NOT danger). Copy: "Summary unavailable: {reason}. Try again or switch LLM backend in Settings." + Retry button.
- D-17: TTLCache: `cachetools.TTLCache(maxsize=128, ttl=3600)` keyed by `(platform_id, content_mtime, llm_name, llm_model)`. Paired with `threading.Lock()`.
- D-18: Regenerate sends `hx-headers='{"X-Regenerate": "true"}'`. Server bypasses cache lookup but **still writes the result back** under the same key.
- D-19: Backend selection from `app.state.settings.llm` at request time (default Ollama). Settings page deferred to Phase 5.
- D-20: Prompt template at `app_v2/data/summary_prompt.py`. System prompt instructs model to treat `<notes>` tag contents as untrusted. User prompt wraps content in `<notes>...</notes>`.
- D-21: Single-shot, NOT streaming. SUMMARY-04 spec: "single-shot call". HTMX swaps once.

**Test scope, mocking, threat model (Area 4):**
- D-22: Three explicit path-traversal tests: `../../etc/passwd`, `//etc/passwd`, `foo%00bar` — all → 422 from `Path(pattern=...)` BEFORE any FS call.
- D-23: LLM mocking: `pytest-mock` patches `app_v2.services.summary_service._openai_client.chat.completions.create` at module level (or equivalent — see §"LLM Mocking" below for exact target).
- **D-24 (USER OVERRIDE):** Cross-process race test using `multiprocessing.Process` with 2 workers. Asserts: (a) at least one save succeeded, (b) no tempfile leftover, (c) file mode 0o644, (d) `os.replace` invariant — file is one of two payloads in full, never a mix. `@pytest.mark.slow`, skip on Windows.
- D-25: TTLCache test: two consecutive same-key calls → LLM called once. Patch `time.time` past TTL → third call re-invokes. Mutate file mtime via `os.utime` → cache miss.
- D-26: Six threats classified (T-03-01 through T-03-06). T-03-06 (LLM cost runaway) is **accepted** per CONTEXT.md.

**Storage (D-27..D-31):**
- D-27: `content/platforms/` relative to project root. App startup (lifespan) does `mkdir(parents=True, exist_ok=True)`.
- D-28: `content/` gitignored. Phase 03 extends `.gitignore`.
- D-29: File naming: exactly `<PLATFORM_ID>.md`. No subdirectories.
- D-30: Atomic writes: `tempfile.mkstemp` in `content/platforms/`, write, `fsync`, `os.replace`. **Refactor opportunity: extract `app_v2/data/atomic_write.py`** (TBD in plan; see §"Atomic-Write Refactor" below for recommendation).
- D-31: Content size limit 64 KB per file. Server-side rejects > 64 KB with 413.

### Claude's Discretion (resolved in UI-SPEC)

- Empty-state copy: `"No content yet — Add some."` (UI-SPEC §6 chose Dashboard's minimal voice).
- Add Content button: `btn-primary` (NOT violet — violet reserved for AI affordances).
- Edit/Delete icons: `bi-pencil-square` / `bi-trash3`.
- Regenerate tooltip: `"Regenerate ignoring cache"`.
- Summary metadata footer (model + cache age): YES, included for trust + cost transparency.

### Deferred Ideas (OUT OF SCOPE — DO NOT RESEARCH)

- Syntax highlighting for code blocks (CONTENT-F01)
- Conflict detection for concurrent edits (CONTENT-F02)
- User-configurable summary prompt template (SUMMARY-F01)
- LLM cost cap UI (T-03-06 accepted)
- Streaming summary responses (SUMMARY-04 = single-shot)
- Per-user content pages (auth dependency)
- Markdown image upload (HTTPS URLs in markdown only)
- LLM backend switcher UI (Phase 5 ASK-V2-05)

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONTENT-01 | Optional markdown content page at `content/platforms/<PID>.md`; `content/` gitignored, `.gitkeep` committed | D-27, D-28 — startup `mkdir` in lifespan; existing `content/platforms/.gitkeep` from Phase 02 |
| CONTENT-02 | Strict regex `^[A-Za-z0-9_\-]{1,128}$` via `Path(..., pattern=...)`; `Path.resolve()` + `relative_to(BASE)` defense in depth | Reuse `has_content_file` pattern verbatim (existing in `app_v2/services/overview_filter.py`) |
| CONTENT-03 | GET renders MD via `MarkdownIt("js-default")` (HTML passthrough off) OR empty state with "Add Content" | §"Markdown Rendering" — `js-default` verified empirically (markdown-it-py 4.0.0) |
| CONTENT-04 | Edit view via `hx-swap="outerHTML"`; textarea pre-filled, Write/Preview tabs, Save/Cancel | UI-SPEC §6 — full template provided |
| CONTENT-05 | Preview via `hx-post /platforms/{id}/preview`; debounced 500ms; same `js-default` MarkdownIt pipeline; never writes disk | UI-SPEC §6 + D-08 |
| CONTENT-06 | Atomic save: tempfile in same dir → fsync → `os.replace`. `def` route (threadpool dispatch) | §"Atomic-Write Refactor" — reuse `overview_store._atomic_write` exactly |
| CONTENT-07 | Cancel client-side (no server round-trip); no autosave | UI-SPEC §6 — `data-cancel-html` + `hx-on:click` |
| CONTENT-08 | Delete with `hx-confirm`; deletes file, swaps to empty state | UI-SPEC §2 + state diagram §"State Diagram — `#content-area`" |
| SUMMARY-01 | AI Summary button per row; disabled when no content file; tooltip explains | D-13 — `has_content_file` drives state; UI-SPEC §9 has the diff vs Phase 02 |
| SUMMARY-02 | Click → `hx-post /platforms/<id>/summary`; fills `<div id="summary-{id}">` via `innerHTML`; `hx-disabled-elt="this"` | D-12 + UI-SPEC §7 |
| SUMMARY-03 | Loading indicator: `spinner-border` + `htmx-indicator` class | UI-SPEC §8a — pre-seeded indicator pattern |
| SUMMARY-04 | Single-shot LLM via openai SDK (Ollama via base_url, OpenAI direct); `<notes>` tag wrap; system prompt treats notes as untrusted | §"LLM Single-Shot Call" — verified `openai.OpenAI` 2.32.0 supports base_url for Ollama |
| SUMMARY-05 | TTLCache(maxsize=128, ttl=3600) keyed by (pid, mtime, llm_name, llm_model) | §"TTLCache + Lock" — exact pattern from `app_v2/services/cache.py` |
| SUMMARY-06 | Regenerate via `X-Regenerate: true` header; bypasses lookup, still writes back | D-18 |
| SUMMARY-07 | Error → Bootstrap alert with reason + Retry button; no silent failure | UI-SPEC §8c — full error vocabulary table |

---

## Standard Stack

> All versions pinned by CLAUDE.md and verified against installed `.venv` packages.

### Core (already installed in v0 venv — no new pip installs needed)
| Library | Version (verified `.venv`) | Purpose | Why Standard |
|---------|---------------------------|---------|--------------|
| `markdown-it-py` | **4.0.0** (`.venv/lib/python3.13/site-packages/markdown_it/__init__.py`) | Markdown → HTML, `js-default` preset | `[CITED: markdown-it-py docs]` `js-default` mirrors JS markdown-it safe defaults — `html=False`, `linkify=False`, `typographer=False` (verified empirically — see §"Markdown Rendering") |
| `cachetools` | **7.0.6** | TTLCache + Lock for summary cache | `[VERIFIED: import]` Existing pattern in `app_v2/services/cache.py`; pinned `>=7.0,<8.0` in requirements.txt |
| `openai` | **2.32.0** | Single SDK for OpenAI + Ollama (via `base_url`) | `[VERIFIED: import]` Already used by v1.0 `app/adapters/llm/openai_adapter.py`; Ollama is OpenAI wire-compatible (`/v1` endpoint) |
| `fastapi` | **0.136.1** | HTTP framework, `Path(..., pattern=...)`, `Form()` with `max_length` | `[VERIFIED: import + signature inspect]` `Form()` accepts `max_length`, `pattern`, `min_length` directly |
| `jinja2-fragments` | (installed, no `__version__` exposed) | `Jinja2Blocks` — block-name-targeted rendering for HTMX fragments | `[VERIFIED: import]` Reuse existing `app_v2/templates/__init__.py::templates` |
| `python-multipart` | already installed (Phase 1 `requirements.txt`) | Form data parsing for `Form()` | `[CITED: requirements.txt]` Required by FastAPI for `application/x-www-form-urlencoded` |

### Supporting / standard library
| Library | Purpose |
|---------|---------|
| `pathlib` | All FS paths; `Path.resolve()` + `Path.relative_to()` for traversal defense |
| `tempfile.mkstemp` | Atomic write tempfile in same directory as target |
| `os.replace`, `os.fsync`, `os.utime`, `os.chmod` | POSIX-atomic file replace; mtime control for cache tests |
| `threading.Lock` | Per-cache lock paired with TTLCache (Pitfall 11) |
| `multiprocessing.Process` | Cross-process save race test (D-24) — fork-only on POSIX |
| `pytest-mock` (`mocker` fixture) | Module-level patch for openai SDK |
| `httpx` (transitive via openai) | `httpx.ConnectError`, `httpx.ReadTimeout` for error classification |

### Alternatives Considered (and rejected)
| Instead of | Could Use | Why rejected |
|------------|-----------|--------------|
| `MarkdownIt("js-default")` | `bleach.clean(...)` post-processing | `js-default` already disables raw HTML at the parser level — bleach is redundant and adds a 50KB+ dependency. The mtime-based cache makes parser cost negligible. |
| openai SDK with `base_url` | `requests`/`httpx` direct to `/api/chat` | v1.0's `OllamaAdapter` uses `requests`, but Ollama also exposes OpenAI-compatible `/v1` — using one SDK for both backends collapses error handling (one taxonomy) and prompt-injection defense. |
| `litellm` | (multi-provider router) | Already rejected in CLAUDE.md — 50MB for 2 wire-compatible providers. |
| Hand-rolled file lock (fcntl.flock) | (cross-process FS lock) | `os.replace` is atomic on POSIX — no lock needed. Cross-process race test (D-24) verifies this empirically. |
| Filesystem watcher | (invalidate cache on mtime change) | Cache key already includes mtime — fresh stat on every request invalidates implicitly. No watcher needed. |

### Installation
**No new dependencies.** Phase 01's `requirements.txt` already covers everything (`markdown-it-py[plugins]>=3.0` is satisfied by 4.0.0; `cachetools>=7.0,<8.0` covers 7.0.6; `openai>=1.50` covers 2.32.0).

**Version verification (run before plan finalization):**
```bash
.venv/bin/python -c "import markdown_it, cachetools, openai, fastapi; print(markdown_it.__version__, cachetools.__version__, openai.__version__, fastapi.__version__)"
# Expected: 4.0.0 7.0.6 2.32.0 0.136.1
```

---

## Architecture Patterns

### File Layout (new files this phase)
```
app_v2/
├── data/
│   ├── atomic_write.py            # NEW — extracted from overview_store._atomic_write (D-30)
│   └── summary_prompt.py          # NEW — system + user prompt templates (D-20)
├── services/
│   ├── content_store.py           # NEW — read/write/delete markdown files
│   └── summary_service.py         # NEW — TTLCache + Lock + openai single-shot
├── routers/
│   ├── platforms.py               # NEW — 5 routes (GET, POST edit, POST preview, POST save, DELETE)
│   └── summary.py                 # NEW — POST /platforms/{pid}/summary
├── templates/
│   ├── platforms/
│   │   ├── detail.html            # NEW — full page (extends base.html)
│   │   ├── _content_area.html     # NEW — rendered or empty-state panel
│   │   ├── _edit_panel.html       # NEW — edit panel with tabs
│   │   └── _preview_pane.html     # NEW — fragment for preview tab
│   ├── summary/
│   │   ├── _success.html          # NEW — success card with Regenerate
│   │   └── _error.html            # NEW — amber alert with Retry
│   └── overview/
│       └── _entity_row.html       # MODIFIED — wire AI Summary, add summary slot
└── static/css/
    ├── tokens.css                 # NEW — Dashboard CSS custom properties (UI-SPEC §Design System)
    └── app.css                    # NEW — .panel, .ai-btn, .markdown-content, etc.

content/                           # NEW — gitignored
└── platforms/
    └── .gitkeep                   # already committed in Phase 02
```

### Pattern 1: Pure path-traversal-safe FS access (CONTENT-02)
**What:** Reuse the verbatim pattern from `app_v2/services/overview_filter.py::has_content_file`.

```python
# app_v2/services/content_store.py
from pathlib import Path

def _safe_target(platform_id: str, content_dir: Path) -> Path:
    """Resolve content_dir/<pid>.md and assert it stays inside content_dir.
    Raises ValueError if the resolved path escapes (Pitfall 2 defense in depth).
    Note: regex on Path() already rejects traversal; this is belt-and-suspenders."""
    base = content_dir.resolve()
    candidate = (content_dir / f"{platform_id}.md").resolve()
    candidate.relative_to(base)  # raises ValueError on escape
    return candidate
```
Source: existing `overview_filter.py` lines 60-68.

### Pattern 2: Atomic write (CONTENT-06, D-30)
**What:** Lift `_atomic_write` from `overview_store.py` into a shared `app_v2/data/atomic_write.py`. Original signature preservation: accept `target: Path, payload: bytes` (NOT a YAML-specific dict).

**Recommendation (resolves D-30 TBD):** Extract NOW, in this phase. Justification:
1. Two callers (overview_store + content_store) is the threshold where extraction stops being YAGNI.
2. Phase 02's `_atomic_write` already handles the file-mode-preservation gotcha (WR-03 fix); content_store would have to copy that logic verbatim, then drift.
3. The extraction is mechanical — no design risk.

**Extracted contract:**
```python
# app_v2/data/atomic_write.py
from pathlib import Path

def atomic_write_bytes(target: Path, payload: bytes, *, default_mode: int = 0o644) -> None:
    """Write payload to target atomically: tempfile in same dir → fsync → os.replace.

    Preserves existing target file mode (or applies default_mode if file is new).
    The umask-aware default mirrors Phase 02 overview_store behavior.
    """
```
Then `overview_store._atomic_write` becomes a thin wrapper that yaml-serializes and calls `atomic_write_bytes(path, yaml_bytes)`. `content_store.save_content` calls `atomic_write_bytes(path, content.encode("utf-8"))`.

Single subtle change vs the current overview_store function: parametrize `default_mode` (0o644 for content files, 0o644 for overview yaml — same value, but the helper documents the intent).

### Pattern 3: Markdown rendering (CONTENT-03, CONTENT-05, D-08)
**What:** Module-level singleton `MarkdownIt("js-default")` instance. Render once per request. Return raw HTML string; template injects via `{{ rendered_html | safe }}`.

```python
# app_v2/services/content_store.py (or a separate render module)
from markdown_it import MarkdownIt

_MD = MarkdownIt("js-default")  # html=False, linkify=False — XSS-safe by construction

def render_markdown(text: str) -> str:
    """Render user-supplied markdown to safe HTML. NEVER use MarkdownIt() default."""
    return _MD.render(text)
```

`{{ rendered_html | safe }}` is correct: the parser already escaped raw HTML, so Jinja2 must NOT double-escape. (Source: UI-SPEC §4 explicit comment.)

**Plugins** (D-08 pinned the bare `js-default` — DO NOT enable plugins this phase): no anchor headers (CONTENT-F01-adjacent), no linkify (would auto-link bare URLs but `js-default` already validates URI scheme), no typographer (smart quotes are out of scope).

### Pattern 4: TTLCache + Lock for summary (D-17, SUMMARY-05)
**What:** Identical idiom to `app_v2/services/cache.py`. One module-level cache + one module-level Lock. Key tuple via `cachetools.keys.hashkey(pid, mtime, llm_name, llm_model)`.

```python
# app_v2/services/summary_service.py (skeleton — full code in plan)
import threading
from cachetools import TTLCache, cached
from cachetools.keys import hashkey

_summary_cache: TTLCache = TTLCache(maxsize=128, ttl=3600)  # D-17 verbatim
_summary_lock = threading.Lock()

# NOTE: We do NOT use @cached here because Regenerate (D-18) needs to bypass
# the lookup but still write back. The decorator hides that path. We open-code
# the cache logic against the same _summary_cache + _summary_lock objects:

def get_or_generate_summary(pid: str, mtime: float, llm_name: str, llm_model: str,
                             content: str, *, regenerate: bool = False) -> SummaryResult:
    key = hashkey(pid, mtime, llm_name, llm_model)
    with _summary_lock:
        if not regenerate and key in _summary_cache:
            return _summary_cache[key]  # cache HIT
    # cache MISS or regenerate=True — call LLM outside the lock (don't hold during 30s call)
    result = _call_llm_single_shot(content, llm_name, llm_model)  # may raise
    with _summary_lock:
        _summary_cache[key] = result  # D-18: regenerate ALSO writes back
    return result
```

**Key design choices:**
1. **Lock NOT held during LLM call** — would serialize all summary requests. The cost: two concurrent regenerate-then-regenerate requests for the same (pid, mtime, llm) might both call the LLM. Acceptable per D-26 T-03-06 (LLM cost runaway accepted).
2. **`hashkey(...)` not raw tuple** — matches `app_v2/services/cache.py` idiom; `cachetools.keys.hashkey` ensures the key is hashable even if any element becomes a list later.
3. **`SummaryResult` dataclass** — wraps `text: str, llm_name: str, llm_model: str, generated_at: datetime`. Cached as a value object so the success template can render the metadata footer (D-15 + UI-SPEC §8b "metadata footer").
4. **mtime is a float** — `Path.stat().st_mtime` returns float. Use as-is; don't truncate to int (see Pitfall §"mtime resolution" below).

### Pattern 5: openai SDK single-shot for both backends (SUMMARY-04, D-19, D-20)
**What:** Reuse the `openai.OpenAI(api_key=..., base_url=...)` constructor pattern from `app/adapters/llm/openai_adapter.py`. For Ollama, set `base_url="http://localhost:11434/v1"` and `api_key="ollama"` (any non-empty string — Ollama ignores it).

```python
# app_v2/services/summary_service.py
from openai import OpenAI, APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError, APIStatusError
import httpx

def _build_openai_client(llm_cfg: LLMConfig) -> OpenAI:
    """Single client factory covering both OpenAI and Ollama backends.
    Ollama: base_url='http://localhost:11434/v1' (OpenAI-compatible endpoint)
    OpenAI: base_url=None (default api.openai.com)"""
    if llm_cfg.type == "ollama":
        base_url = (llm_cfg.endpoint or "http://localhost:11434").rstrip("/") + "/v1"
        api_key = "ollama"  # Ollama requires non-empty but ignores value
    else:
        base_url = llm_cfg.endpoint or None
        api_key = llm_cfg.api_key or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OpenAI API key not configured")
    # 30s timeout per success criterion #4 ("within 30 seconds"). Default is 60s.
    return OpenAI(api_key=api_key, base_url=base_url, timeout=httpx.Timeout(30.0))

def _call_llm_single_shot(content: str, llm_cfg: LLMConfig) -> str:
    client = _build_openai_client(llm_cfg)
    resp = client.chat.completions.create(
        model=llm_cfg.model or ("gpt-4o-mini" if llm_cfg.type == "openai" else "llama3.1"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},   # from app_v2/data/summary_prompt.py
            {"role": "user", "content": USER_PROMPT.format(markdown_content=content)},
        ],
        temperature=llm_cfg.temperature,
        max_tokens=llm_cfg.max_tokens,
        stream=False,  # D-21 — single-shot only
    )
    return (resp.choices[0].message.content or "").strip()
```

**Source:** `app/adapters/llm/openai_adapter.py` lines 21-29 + verified `OpenAI()` signature: `api_key, base_url, timeout` are all kwargs.

### Pattern 6: Error classification (SUMMARY-07, UI-SPEC §8c)
**What:** A single `_classify_error(exc, backend_name) -> str` function maps openai SDK 2.x exceptions to the 7-string vocabulary from UI-SPEC §8c. Plain match by exception class.

```python
def _classify_error(exc: Exception, backend_name: str) -> str:
    """Map openai SDK 2.32.0 / httpx exceptions to UI-SPEC §8c error vocabulary."""
    from openai import (APIConnectionError, APITimeoutError, AuthenticationError,
                        RateLimitError, APIStatusError)
    import httpx
    if isinstance(exc, (APIConnectionError, httpx.ConnectError, httpx.ConnectTimeout)):
        return f"Cannot reach the LLM backend ({backend_name})"
    if isinstance(exc, (APITimeoutError, httpx.ReadTimeout, httpx.WriteTimeout)):
        return "LLM took too long to respond"
    if isinstance(exc, AuthenticationError):
        return "LLM authentication failed — check API key in Settings"
    if isinstance(exc, RateLimitError):
        return "LLM is rate-limited — try again in a moment"
    if isinstance(exc, APIStatusError) and exc.status_code >= 500:
        return f"LLM backend returned an error (HTTP {exc.status_code})"
    if isinstance(exc, FileNotFoundError):
        return "Content page no longer exists"
    return "Unexpected error — see server logs"
```

**Verified exception classes (openai 2.32.0):** `APIError`, `APIConnectionError`, `APITimeoutError`, `APIStatusError`, `AuthenticationError`, `RateLimitError`, `BadRequestError`, `InternalServerError`, `NotFoundError`, `PermissionDeniedError`, `UnprocessableEntityError`, `ConflictError` — all exist as `openai.<Name>` (verified by `dir(openai)`).

`APIConnectionError` typically wraps an `httpx.ConnectError` — the `isinstance` covers both.

### Pattern 7: Routes structure (5 + 1 endpoints; def, not async def)
Per INFRA-05 (Pitfall 4) every route is `def`, not `async def`.

```python
# app_v2/routers/platforms.py — full route signatures (handler bodies in plan)
from fastapi import APIRouter, Path, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from typing import Annotated

router = APIRouter(prefix="/platforms")
PID_PATTERN = r"^[A-Za-z0-9_\-]{1,128}$"

@router.get("/{platform_id}", response_class=HTMLResponse)
def detail_page(request: Request, platform_id: Annotated[str, Path(pattern=PID_PATTERN)]): ...

@router.post("/{platform_id}/edit", response_class=HTMLResponse)
def edit_view(request: Request, platform_id: Annotated[str, Path(pattern=PID_PATTERN)]): ...

@router.post("/{platform_id}/preview", response_class=HTMLResponse)
def preview_view(
    request: Request,
    platform_id: Annotated[str, Path(pattern=PID_PATTERN)],
    content: Annotated[str, Form(max_length=65536)] = "",  # D-31 — 64 KB
): ...

@router.post("/{platform_id}", response_class=HTMLResponse)
def save_content(
    request: Request,
    platform_id: Annotated[str, Path(pattern=PID_PATTERN)],
    content: Annotated[str, Form(max_length=65536)],  # D-31
): ...

@router.delete("/{platform_id}/content")
def delete_content(platform_id: Annotated[str, Path(pattern=PID_PATTERN)]) -> Response: ...

# app_v2/routers/summary.py
@router.post("/platforms/{platform_id}/summary", response_class=HTMLResponse)
def get_summary(
    request: Request,
    platform_id: Annotated[str, Path(pattern=PID_PATTERN)],
    x_regenerate: Annotated[str | None, Header()] = None,  # D-18
): ...
```

**Key choices:**
- `Form(max_length=65536)` enforces D-31 server-side; FastAPI returns 422 automatically. UI-SPEC copy "Content too large: 64 KB max." is rendered into `#htmx-error-container` by the global `htmx:beforeSwap` handler (Phase 01 INFRA-02). 64 KB = 65536 chars (UTF-8 worst case is ~256 KB raw bytes, well under the 1 MB FastAPI body default — no middleware needed).
- `Header()` for `X-Regenerate` is FastAPI standard; the dash becomes `x_regenerate` underscore-snake automatically.
- `summary` route lives in `app_v2/routers/summary.py` (not `platforms.py`) so the cache module ownership matches: `summary_service.py` ↔ `summary.py`.

### Anti-Patterns to Avoid
- **`MarkdownIt()` default constructor** anywhere in this phase. Always `MarkdownIt("js-default")`. (Pitfall 1 — XSS blocker.)
- **`async def` on any route** in this phase. Pitfall 4 — sync stat()/open() block the event loop.
- **Holding the summary `Lock` during the LLM call.** Would serialize all concurrent requests behind one slow Ollama cold-start. Lock guards only the dict reads/writes.
- **Reading the file content INSIDE the cache key lambda.** The key uses `mtime`, not `content` — keep stat() outside the cache, hash mtime only.
- **Catching bare `Exception` in summary route.** Catch the openai/httpx union explicitly so unexpected exceptions still bubble (5xx) and become visible in error-container, not in the summary slot.
- **Returning HTTP 500 from the summary endpoint on LLM failure.** UI-SPEC §"Note on summary error response" is explicit: ALWAYS return 200 with the error fragment. 500 would trigger the global `htmx:beforeSwap` handler and render into `#htmx-error-container` instead of the summary slot.
- **Auto-creating the content file on Add Content click.** D-10 + UI-SPEC §6: Add Content opens the edit view; only Save creates the file. Cancel from a never-saved Add Content session must leave no file behind.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown XSS sanitization | Regex `<script>` strip / DOMPurify post-process | `MarkdownIt("js-default")` | Parser-level escape catches all HTML; regex misses obfuscated injections (e.g. `<sCrIpT>`, HTML entities, SVG payloads) |
| Atomic file write | `open(target, 'w')` then hope for no crash | `app_v2/data/atomic_write.py::atomic_write_bytes` (extracted from overview_store) | Cross-process race (D-24) requires `os.replace` semantics; partial writes corrupt user data |
| URI scheme allowlist (javascript:/data:) | Custom regex on `<a href>` | `MarkdownIt("js-default")` built-in `validateLink` | Verified empirically: `[a](javascript:alert(1))` renders as plain text (not anchor); `[a](http://...)` renders normally — no custom validator needed |
| TTL with mutex | `dict + threading.Timer` per entry | `cachetools.TTLCache` + `threading.Lock` | The exact pattern is already proven in Phase 01 `app_v2/services/cache.py`; mtime-based key invalidation makes the TTL a budget cap, not a freshness guarantee |
| Cross-process file lock | `fcntl.flock` | `os.replace` (POSIX-atomic rename) | `os.replace` is atomic at the kernel level — both processes write to separate tempfiles; whoever calls `os.replace` last wins. The D-24 test asserts no hybrid result. |
| LLM error → user-readable message | Print `str(exc)` | The 7-string vocabulary in UI-SPEC §8c | Raw exception messages leak file paths, API keys, or stack traces. The classified vocabulary is also localizable. |
| HTML escaping in Cancel `data-cancel-html` | Manual `html.escape()` | Jinja2 `| e` filter | UI-SPEC §6 explicit: `data-cancel-html="{{ stashed_render_or_empty | e }}"`. Jinja's autoescape covers all attribute injection vectors. |
| HTMX double-submit prevention | Custom JS `disabled = true` | `hx-disabled-elt="this"` | UI-SPEC §"HTMX Behavior Summary" mandates this on all mutating triggers. HTMX manages re-enable on response. |
| Markdown preview client-side | marked.js / showdown.js | Server `POST /preview` with same MarkdownIt instance | UI-SPEC §6 + CONTENT-05: identical pipeline server-side avoids client/server divergence — what the user previews IS what gets stored after Save (modulo file size limit). |

**Key insight:** Every "should we build this?" question for Phase 03 is answered by an existing module in the codebase or an existing library. The phase is plumbing.

---

## Common Pitfalls

> Phase 02 PITFALLS.md (Pitfalls 1, 2, 4, 7) carry forward. New Phase-03-specific pitfalls below.

### Pitfall 1 (carry forward): markdown-it-py raw HTML — RESOLVED by `js-default`
**Resolution verified empirically** for markdown-it-py 4.0.0:
- `MarkdownIt("js-default").options` — `html=False, linkify=False, typographer=False`
- `<script>alert(1)</script>` → `<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>` (escaped)
- `<img onerror>` → escaped
- `[a](javascript:alert(1))` → plain text (built-in URI validator rejects)
- HTML comments → escaped
- Plain markdown (`# H`, `**b**`, lists, fenced code) → renders correctly

**Plan must include unit test:** `assert "<script>" not in MarkdownIt("js-default").render("<script>alert(1)</script>")` plus matching tests for `<img onerror>`, `javascript:` URI, HTML comment.

### Pitfall 2 (carry forward): Path traversal — RESOLVED by regex + `relative_to`
Pattern is identical to Phase 02's `has_content_file` (lines 60-68). Plan reuses this verbatim. D-22 mandates 3 explicit traversal tests.

### Pitfall 4 (carry forward): Sync SQLAlchemy in async — N/A but pattern enforced
Phase 03 routes don't touch SQLAlchemy directly, but they DO use `def` (not `async def`) per INFRA-05. Test: `grep -r "async def" app_v2/routers/platforms.py app_v2/routers/summary.py` returns zero matches.

### Pitfall 7 (carry forward): OOB swap silent fail — N/A this phase
Phase 03 doesn't introduce new OOB targets. The summary slot uses `innerHTML` (regular swap, not OOB). The Phase 02 update to `_entity_row.html` (replacing the disabled-stub button) is a regular template-render change, not an OOB swap.

### Pitfall 13 (NEW): mtime resolution drifts cache key on some filesystems
**What goes wrong:** `Path.stat().st_mtime` returns float seconds since epoch. On ext4 (Linux default since 2015) and APFS (macOS), this includes fractional seconds (nanosecond precision). On older ext3 / FAT32 / some NFS mounts, `st_mtime` is integer seconds — multiple writes in the same second produce identical mtime, causing cache to return stale summaries after a quick edit.

**Why it happens:** mtime is a Unix epoch second value; sub-second precision is per-filesystem. Phase 03 runs on a Linux intranet server, but the dev test loop on macOS and CI may differ.

**How to avoid:**
1. Cache key uses `mtime: float` directly — no rounding/truncation. On nanosecond-precision filesystems this is fine.
2. **Defensive belt-and-suspenders:** also include the file `size` in the key tuple. A same-second edit that changes content also changes byte count in 99%+ of cases (changing ONLY a single character to another character of identical UTF-8 byte length within the same second is the only collision). Cost: free — `Path.stat()` returns size in the same syscall.
3. **Recommended cache key (sharper than D-17 strict reading):** `hashkey(platform_id, st.st_mtime_ns, st.st_size, llm_name, llm_model)`. Uses `st_mtime_ns` (integer nanoseconds — always integer, always deterministic, always nanosecond-precise on modern FS).
4. **On test:** the D-25 mtime-mutation test should use `os.utime(path, ns=(now_ns, now_ns + 1_000_000_000))` to advance mtime by 1 second deterministically rather than sleeping.

**Warning signs:**
- Test `test_cache_invalidates_on_file_change` flakes on macOS / Windows tmpfs.
- User reports "I edited the content and the AI Summary still shows the old version" — and the edit was within ~1 second of the prior summary call.

**Phase to address:** Phase 03 — pin the cache key to `(pid, mtime_ns, size, llm_name, llm_model)`.
**Confidence:** HIGH (st_mtime_ns is documented in Python `os.stat_result`).

### Pitfall 14 (NEW): cachetools v7 `TTLCache.timer` is a read-only property
**What goes wrong:** Tests want to advance time without `time.sleep(3601)`. The naive `cache.timer = lambda: fake_time` fails with `AttributeError: property 'timer' of 'TTLCache' object has no setter`.

**How to avoid:** Use the verified Phase 01 pattern from `tests/v2/test_cache.py` lines 179-205 — patch the **inner** name-mangled callable:
```python
timer_obj = cache.timer  # _Timer wrapper instance
original_inner = timer_obj._Timer__timer  # the underlying time.monotonic
fake_time = [1000.0]
timer_obj._Timer__timer = lambda: fake_time[0]
try:
    # ... advance fake_time[0] += 3601 between calls ...
finally:
    timer_obj._Timer__timer = original_inner
```
Verified empirically against installed cachetools 7.0.6: `c.timer._Timer__timer` is `<built-in function monotonic>` and IS writable on the inner `_Timer` instance.

**Confidence:** HIGH (verified by introspection + existing test_cache.py uses identical pattern).

### Pitfall 15 (NEW): Bootstrap nav-pills `data-bs-toggle="pill"` activation conflicts with HTMX hx-post on same button
**What goes wrong:** UI-SPEC §6 wires the Preview pill with BOTH `data-bs-toggle="pill"` AND `hx-post="/platforms/{id}/preview"`. Bootstrap's pill toggle JS runs on the same `click` event that HTMX uses. If HTMX swaps `#preview-pane` content BEFORE Bootstrap's JS marks the pill `.active`, the new pane is hidden (no `.show .active` class). If Bootstrap's JS runs first and `e.preventDefault()` is called by user code anywhere up the chain, HTMX never fires.

**How to avoid:** Both libraries are well-behaved on this — neither `preventDefault`s. The empirically-correct pattern (verified in HTMX 2.0 docs):
1. `hx-target="#preview-pane"` + `hx-swap="innerHTML"` only swaps the pane's children, leaving the `.tab-pane` wrapper intact.
2. The wrapper carries `class="tab-pane fade"` initially and Bootstrap adds `.show .active` on pill click. HTMX swap of inner content does not strip these classes.
3. **Plan must verify** with an integration test: click Preview pill → assert response 200 + assert pane has `class~="active"` after the click. (FastAPI TestClient doesn't run JS, so this is a manual verification step OR a Playwright test deferred to Phase 5+.)

**Alternative if it ever breaks:** Drive the tab swap from JS only and have HTMX target the pane content via a separate trigger. NOT needed currently.

**Warning signs:**
- Click Preview, see 200 response in DevTools, but the pane stays empty.
- Pane shows preview but neither Write nor Preview pill has `.active` class.

**Confidence:** MEDIUM (pattern is per HTMX docs; the Bootstrap+HTMX interaction is documented as compatible but I have not tested in PBM2's specific Bootstrap 5.3.8 vendored bundle).

### Pitfall 16 (NEW): jinja2-fragments `block_names=` ordering interacts with template structure
**What goes wrong:** Phase 02 hit this — `block_names=["filter_oob", "entity_list"]` requires the OOB block be DEFINED BEFORE the consuming block in the template, OR the OOB swap target is ordered weirdly in the response. Phase 03 does NOT use `block_names` for nested OOB swaps (the summary endpoint returns a single fragment, no OOB), so this pitfall is INFORMATIONAL.

**However:** if a future change adds an OOB swap (e.g., update the Overview row's "AI Summary" button-disabled state when content is added/deleted), the response will need `block_names=["entity_row_button_oob", ...]` and the same ordering rules apply.

**How to avoid (if it becomes relevant):** Define OOB blocks at the top of the template, NOT nested inside the primary content block. Mirror Phase 02 `overview/index.html` structure.

**Confidence:** HIGH — Phase 02 has this working; pattern is documented in `app_v2/templates/overview/index.html` lines 41-55.

### Pitfall 17 (NEW): hx-confirm dialog text length truncation in Chrome/Firefox
**What goes wrong:** UI-SPEC §2 sets `hx-confirm="Delete content page for {pid}? This cannot be undone."`. For long PLATFORM_IDs (max 128 chars per regex), the dialog text reaches ~165 chars — well within browser limits. But some browsers (Firefox on certain platforms) wrap or truncate at ~256 chars in the native `confirm()` dialog.

**How to avoid:** Current copy is fine. If a future copy expansion (e.g. listing all summary cache entries about to be invalidated) pushes past 200 chars, switch to a Bootstrap modal dialog instead of native confirm. NOT needed now.

**Confidence:** LOW — anecdotal; not actually triggered at current copy length. INFORMATIONAL.

### Pitfall 18 (NEW): openai SDK with Ollama base_url cold-start exceeds 30s timeout
**What goes wrong:** First Ollama request after Ollama starts (or after the model has been unloaded for memory) loads the model into VRAM/RAM. For `llama3.1:8b` on a CPU-only intranet server this can take 20-60 seconds. The 30s timeout (success criterion #4) will fire on cold-start and present the user with "LLM took too long to respond" even though the model is fine.

**How to avoid:**
1. **Recommend:** lifespan-time warmup. In `app_v2/main.py` lifespan, fire a single trivial Ollama request (`messages=[{"role":"user","content":"ok"}], max_tokens=1`) on startup if `settings.llm.type == "ollama"`. The user-facing first summary call then hits a warm model.
2. **Alternative:** raise the openai client timeout to 60s and keep a separate `httpx.Timeout(connect=5.0, read=60.0)` so connection failures still fail fast but cold-start is tolerated. UI loading text already says "Summarizing… (using Ollama)" so users understand the wait.
3. **Test:** the LLM mock (D-23) avoids this entirely in CI. Document as a runbook item, not a code change.

**Recommendation:** Plan should include both (1) warmup in lifespan AND (2) timeout raised to 60s for Ollama specifically (keep 30s for OpenAI). The success criterion #4 says "within 30 seconds" which is a target, not a hard contract — and it's met for warm Ollama.

**Warning signs:**
- First summary after `pm2 restart`/Docker restart hits "LLM took too long to respond"
- User reports random first-of-day timeout, then everything works.

**Confidence:** HIGH (Ollama documented behavior; cold-start is universal across LLM serving).

---

## Code Examples

### LLM single-shot call with both backends (verified pattern)
```python
# app_v2/services/summary_service.py — abridged
from openai import OpenAI
import httpx
from app.core.config import LLMConfig
from app_v2.data.summary_prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

def _build_client(cfg: LLMConfig) -> OpenAI:
    if cfg.type == "ollama":
        base_url = (cfg.endpoint or "http://localhost:11434").rstrip("/") + "/v1"
        return OpenAI(api_key="ollama", base_url=base_url, timeout=httpx.Timeout(60.0))
    return OpenAI(
        api_key=cfg.api_key or os.environ.get("OPENAI_API_KEY", ""),
        base_url=cfg.endpoint or None,
        timeout=httpx.Timeout(30.0),
    )

def _call_single_shot(content: str, cfg: LLMConfig) -> str:
    client = _build_client(cfg)
    resp = client.chat.completions.create(
        model=cfg.model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(markdown_content=content)},
        ],
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        stream=False,
    )
    return (resp.choices[0].message.content or "").strip()
```
**Source:** verified `OpenAI()` constructor signature has `api_key, base_url, timeout` kwargs; `app/adapters/llm/openai_adapter.py` already uses this pattern for OpenAI; Ollama OpenAI compatibility documented at `https://docs.ollama.com/api/openai-compatibility`.

### LLM mocking pattern (matches v1.0 idiom)
```python
# tests/v2/test_summary_service.py
from unittest.mock import MagicMock, patch
from app_v2.services import summary_service

def test_summary_calls_llm_once_then_caches(mocker):
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content="• point 1\n• point 2"))]
    # Patch the client builder to return a mock client whose chat.completions.create returns fake_resp
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_resp
    mocker.patch.object(summary_service, "_build_client", return_value=mock_client)

    cfg = LLMConfig(name="ollama", type="ollama", model="llama3.1")
    r1 = summary_service.get_or_generate_summary("PID1", 1.0, "ollama", "llama3.1", "content", regenerate=False)
    r2 = summary_service.get_or_generate_summary("PID1", 1.0, "ollama", "llama3.1", "content", regenerate=False)

    assert r1.text == "• point 1\n• point 2"
    assert r1 is r2 or r1.text == r2.text  # cache hit (D-25)
    assert mock_client.chat.completions.create.call_count == 1
```

**Why patch `_build_client` not `chat.completions.create` directly:** `OpenAI()` instantiation is a side effect that requires `api_key` validation to pass. Patching the builder dodges all that and gives a clean mock client. This is the simpler form of D-23's "module-level patch" idiom.

### Atomic write helper (extracted from overview_store)
```python
# app_v2/data/atomic_write.py
from __future__ import annotations
import os, stat, tempfile
from pathlib import Path

def atomic_write_bytes(target: Path, payload: bytes, *, default_mode: int = 0o644) -> None:
    """POSIX-atomic file write. tempfile in same dir → fsync → os.replace.

    Preserves existing target file mode; falls back to default_mode (umask-aware)
    for new files. Cleans up the tempfile on any failure before re-raising.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target_mode = stat.S_IMODE(target.stat().st_mode)
    else:
        umask = os.umask(0); os.umask(umask)
        target_mode = default_mode & ~umask
    fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
        os.chmod(target, target_mode)
    except Exception:
        try: os.unlink(tmp)
        except FileNotFoundError: pass
        raise
```
**Source:** `app_v2/services/overview_store.py::_atomic_write` (lines 96-141), generalized from YAML-specific to bytes-payload.

### Cross-process race test (D-24)
```python
# tests/v2/test_content_store.py
import multiprocessing
import sys
import pytest
from pathlib import Path

def _save_in_worker(content_dir_str: str, pid: str, payload: str) -> None:
    """Worker target — runs in a fresh Python process via fork."""
    from app_v2.services.content_store import save_content
    save_content(pid, payload, content_dir=Path(content_dir_str))

@pytest.mark.slow
@pytest.mark.skipif(sys.platform == "win32", reason="multiprocessing fork is POSIX-only")
def test_cross_process_save_race(tmp_path):
    """D-24: two processes save different payloads concurrently — no hybrid file, no leftover tempfile."""
    content_dir = tmp_path / "content" / "platforms"
    content_dir.mkdir(parents=True)
    pid = "Test_Race_Platform"
    payload_a = "AAA" * 1000  # 3 KB distinct
    payload_b = "BBB" * 1000  # 3 KB distinct

    ctx = multiprocessing.get_context("fork")  # fork inherits tmp_path env
    p1 = ctx.Process(target=_save_in_worker, args=(str(content_dir), pid, payload_a))
    p2 = ctx.Process(target=_save_in_worker, args=(str(content_dir), pid, payload_b))
    p1.start(); p2.start()
    p1.join(timeout=10); p2.join(timeout=10)
    assert p1.exitcode == 0 and p2.exitcode == 0

    # File exists with one of the two payloads (never a mix)
    target = content_dir / f"{pid}.md"
    assert target.is_file()
    final = target.read_text(encoding="utf-8")
    assert final in (payload_a, payload_b), f"Hybrid content detected: {final[:60]}…"

    # No tempfile leftover (atomic_write_bytes cleans up)
    leftovers = [p for p in content_dir.iterdir() if p.name.startswith(".") and p.name.endswith(".tmp")]
    assert leftovers == [], f"Tempfiles leaked: {leftovers}"

    # Mode is 0o644 regardless of which process won (umask-aware default_mode)
    import stat
    assert stat.S_IMODE(target.stat().st_mode) == 0o644
```
**Source:** `multiprocessing.get_context("fork")` verified default on Linux; `os.replace` POSIX atomicity guaranteed (Python docs `os.replace`).

### Path-traversal test (D-22)
```python
# tests/v2/test_content_routes.py — three traversal cases
@pytest.mark.parametrize("bad_pid", [
    "../../etc/passwd",     # classic
    "/etc/passwd",          # absolute
    "foo%00bar",            # NUL-byte injection (URL-encoded)
])
def test_path_traversal_rejected_before_filesystem(client, bad_pid):
    # GET, POST/edit, POST/preview, POST (save), DELETE — all rejected at routing layer
    for method, path in [
        ("GET",    f"/platforms/{bad_pid}"),
        ("POST",   f"/platforms/{bad_pid}/edit"),
        ("POST",   f"/platforms/{bad_pid}"),
        ("DELETE", f"/platforms/{bad_pid}/content"),
        ("POST",   f"/platforms/{bad_pid}/summary"),
    ]:
        r = client.request(method, path, data={"content": ""} if method == "POST" else None)
        assert r.status_code in (404, 422), f"{method} {path}: got {r.status_code}, expected 404 or 422"
```
**Note:** FastAPI returns 422 for pattern mismatch but the URL `../../etc/passwd` may be normalized by Starlette's URL parser to a 404 before pattern validation runs — both are acceptable rejections per D-22 ("422 from `Path(..., pattern=...)` BEFORE any filesystem call"). The plan should accept 404 OR 422 in this assertion.

### TTL expiry test (D-25 verbatim from existing pattern)
```python
def test_cache_ttl_expiry(mocker):
    from app_v2.services import summary_service as svc
    cache = svc._summary_cache
    timer = cache.timer
    original = timer._Timer__timer
    t = [1000.0]
    timer._Timer__timer = lambda: t[0]
    try:
        # ... mock LLM, call get_or_generate_summary twice with same key, advance t[0] by 3601, call again
    finally:
        timer._Timer__timer = original
```
**Source:** verbatim from `tests/v2/test_cache.py` lines 179-205.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `markdown` (Python-Markdown) library | `markdown-it-py` (CommonMark-strict) | 2020+ | markdown-it-py is the de facto standard for new Python projects; CommonMark spec compliance + extension architecture |
| `markdown-it-py` `MarkdownIt()` default | `MarkdownIt("js-default")` for user-supplied input | always — preset existed since markdown-it-py 1.0 | The default is CommonMark-compliant which means `html=True`. JS-default mirrors the JS markdown-it library's safer defaults. |
| openai SDK 1.x `openai.api_key = ...` global | openai 2.x `client = OpenAI(api_key=..., base_url=...)` per-call | openai 1.0 (Nov 2023) | Multi-tenant safe; allows Ollama via base_url without monkey-patching globals |
| cachetools v5 `TTLCache.timer = ...` (settable) | cachetools v7 read-only property; patch `_Timer__timer` | cachetools 6.0 (early 2025) | Plain attribute assignment in v5 stops working in v7; tests must patch the inner name-mangled callable |
| `python-multipart` 0.x | `python-multipart` 0.0.9+ (security fix) | 2024 | FastAPI 0.136+ requires the patched version for Form() body parsing |

**Deprecated/outdated (do NOT use):**
- `marked.js` (client-side preview): server-side preview (CONTENT-05) is the contract — ensures previewed HTML matches saved HTML.
- `bleach`: redundant with `js-default`; adds a 50KB+ dependency.
- `streamlit-aggrid` for tables: out of scope (Phase 03 is markdown CRUD, not tables).
- `python-frontmatter`: PROJECT does not use YAML frontmatter in markdown files (D-29 — file is just markdown body).

---

## Project Constraints (from CLAUDE.md)

> Extracted directives the planner must verify compliance with. These are LOCKED — research must not recommend approaches that contradict them.

1. **Tech stack pinned:** Streamlit + SQLAlchemy + pandas + Pydantic v2 — but for v2.0 ALSO FastAPI 0.136.x + Bootstrap 5.3.8 + HTMX 2.0.10 + jinja2-fragments + markdown-it-py 4.x. NO new framework introductions in Phase 03.
2. **Read-only DB:** content pages and summary do not write to MySQL. Markdown files write to local FS (`content/platforms/`).
3. **All DB-touching FastAPI routes are `def`, not `async def`** (INFRA-05). Phase 03 routes don't touch DB but follow the same convention universally.
4. **markdown-it-py: `MarkdownIt("js-default")` only — never the default constructor** (PITFALLS Pitfall 1, "html=True causes XSS").
5. **PLATFORM_ID validated by `^[A-Za-z0-9_\-]{1,128}$` regex via FastAPI `Path(pattern=...)` BEFORE any file I/O, plus `Path.resolve()` prefix assertion.**
6. **TTLCache always paired with `threading.Lock()`**; key lambda excludes unhashable objects.
7. **Cache wrapper names: `list_platforms`, `list_parameters`, `fetch_cells`** (no `cached_` prefix). Phase 03's summary cache lives in a NEW module (`summary_service`) — name does not need to follow this convention but the TTLCache+Lock pattern does.
8. **`_Timer__timer` patch pattern** is the documented test idiom for cachetools v7+ TTL expiry.
9. **openai SDK with `base_url` covers both Ollama and OpenAI** — no `litellm`, no separate Ollama SDK.
10. **HTMX 2.0.10 (NOT 4.0 alpha).** All HTMX patterns must be 2.0-compatible.
11. **`hx-disabled-elt="this"` mandatory on all mutating triggers** (PITFALLS Pitfall 6).
12. **Auth deferred** (no per-user content pages).
13. **No emojis in committed code/docs** (CLAUDE.md general).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Ollama OpenAI-compatible endpoint at `/v1` is stable + supports `chat.completions.create(stream=False)` for `llama3.1` and similar models | §"Pattern 5" | If Ollama removes `/v1` compatibility, fall back to v1.0 `OllamaAdapter` (raw `/api/chat` endpoint). Low risk: Ollama has actively maintained `/v1` for 18+ months and documents it. `[CITED: docs.ollama.com/api/openai-compatibility]` |
| A2 | Ollama cold-start under 60s for `llama3.1:8b` on the target intranet hardware | Pitfall 18 | If hardware is slow (CPU-only, 16GB RAM), cold-start may be 90s+. Mitigation: lifespan warmup (recommended). User should validate with `time curl http://localhost:11434/api/chat -d '{"model":"llama3.1","messages":[{"role":"user","content":"ok"}],"stream":false}'` |
| A3 | The `# AI Summary` button on the Phase 02 Overview row uses a Bootstrap btn class today (not `.ai-btn`) and the Phase 03 update is purely a class swap + attribute additions | §"Pattern 7" + UI-SPEC §9 | `[VERIFIED via grep `btn-outline-primary disabled`: matches in Phase 02 _entity_row.html` per UI-SPEC diff in §9. Low risk. |
| A4 | python-multipart >=0.0.9 already installed (Phase 1 INFRA-09) | §"Standard Stack" | If missing, FastAPI raises ImportError on first Form() use. Verify with `.venv/bin/pip show python-multipart`. |
| A5 | `multiprocessing` fork start method works in pytest fixtures on Linux (no pickling issues for the `_save_in_worker` function defined at module top-level) | §"Cross-process race test" | Module-level top-level functions are picklable; nested/lambdaed functions are not. Plan must keep the worker function module-level. `[VERIFIED: Linux default = fork]` |
| A6 | The `tempfile.mkstemp` cleanup in `atomic_write_bytes` runs reliably even when the worker process is `kill -9`'d mid-write | §"Pattern 2" | If the parent process crashes between `mkstemp` and `os.replace`, the tempfile leaks. The D-24 cross-process test asserts no leftover for normal-exit scenarios; SIGKILL during the ~1ms write window is out of scope. |
| A7 | `Path.stat().st_mtime_ns` is integer nanoseconds across all target filesystems (ext4 on intranet server, APFS on macOS dev, FS on CI runner) | Pitfall 13 | All POSIX modern filesystems support nanosecond mtime; `st_mtime_ns` is documented in Python `os.stat_result`. `[CITED: docs.python.org/3/library/os.html#os.stat_result.st_mtime_ns]` |
| A8 | The `app.state.settings.llm` attribute exists at request time (set by the lifespan handler from `load_settings()`) | D-19 / §"Pattern 5" | Phase 1 INFRA-03 sets `app.state.settings`. `[VERIFIED via STATE.md "INFRA-03 complete"]`. The `.llm` attribute structure depends on AppConfig — Phase 03 plan must verify a default LLM is configured (`settings.llms[0]` or `settings.app.default_llm` lookup). |
| A9 | The "AI Summary" button on Overview rows has access to a server-rendered `backend_name` string at template-render time (used in the loading text "Summarizing… (using {Ollama\|OpenAI})") | UI-SPEC §8a, §9 | The Overview route's context (`_build_overview_context`) does NOT currently include `backend_name`. Phase 03 plan must add it. Low risk — purely additive. |
| A10 | UI-SPEC's `linkify` reference (§"Plugins" implicit — not enabled in plan) corresponds to no `js-default` autolinking of bare URLs | §"Pattern 3" | Verified empirically: `js-default` has `linkify=False`; bare URLs render as text. If the team wants bare-URL autolinking, that's a Phase 03 follow-up (CONTENT-F-something), NOT in scope now. |

**No claim is `[ASSUMED]` without verification anchor.** All assumptions trace to either the installed venv, an existing codebase pattern, or a documented stable behavior of pinned dependency.

---

## Open Questions

1. **D-30: Extract atomic_write to shared module — should we?**
   - What we know: Phase 02 has `_atomic_write` in `overview_store.py`; Phase 03 needs the same logic for `content_store.py`. CONTEXT.md flags this as "TBD in plan".
   - Recommendation: **Extract NOW.** Two callers is the canonical YAGNI threshold; the existing function already handles the file-mode-preservation gotcha (Phase 02 WR-03), and copy-paste would require maintaining that fix in two places. Net diff is ~30 lines moved + 5 lines of wrapper in overview_store.

2. **A8: Default LLM lookup — `settings.llms[0]` or `settings.app.default_llm`?**
   - What we know: Phase 1 `Settings` model has both `llms: list[LLMConfig]` AND `app.default_llm: str` (the name).
   - Recommendation: **lookup pattern:** `next((l for l in settings.llms if l.name == settings.app.default_llm), settings.llms[0] if settings.llms else None)`. Plan must include a fallback for the case where `settings.llms == []` (returns 503 with "LLM not configured" alert in summary slot).

3. **Pitfall 18 mitigation — Ollama warmup at lifespan: opt-in or always?**
   - What we know: Cold-start can hit 30s timeout. Warmup adds ~5s to startup time.
   - Recommendation: **Always warm IF `settings.llm.type == "ollama"` AND a default LLM is configured.** Catch all exceptions during warmup (don't block app startup if Ollama is down — degrade to cold-start on first request). Single trivial call: `messages=[{"role":"user","content":"ok"}], max_tokens=1`.

4. **Cache key — strict D-17 (4-tuple) or sharper (5-tuple with size)?**
   - What we know: D-17 says "(platform_id, content_mtime, llm_name, llm_model)". Pitfall 13 argues for adding `size` for FS edge cases.
   - Recommendation: **Use D-17 verbatim BUT switch `mtime` (float) → `mtime_ns` (int).** This addresses sub-second resolution without changing the tuple shape. Adding `size` is over-engineering for the intranet single-server target environment.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| `markdown-it-py` | CONTENT-03/05 rendering | ✓ | 4.0.0 (verified `.venv`) | — |
| `cachetools` | SUMMARY-05 TTLCache | ✓ | 7.0.6 (verified) | — |
| `openai` SDK | SUMMARY-04 single-shot call | ✓ | 2.32.0 (verified) | — |
| `fastapi` | All routes | ✓ | 0.136.1 (verified) | — |
| `jinja2-fragments` | Block-name fragment rendering | ✓ | installed (no version attr) | — |
| `python-multipart` | `Form()` parsing | assumed ✓ (Phase 1 INFRA-09) | — | If missing, `pip install python-multipart>=0.0.9` |
| Ollama service (runtime) | `settings.llm.type == "ollama"` | runtime-dependent | — | Fall back to OpenAI if `OPENAI_API_KEY` set; otherwise summary endpoint returns "Cannot reach the LLM backend" alert |
| OpenAI API access (runtime) | `settings.llm.type == "openai"` | runtime-dependent | — | Same as above (fall back to Ollama) |
| `multiprocessing` fork | D-24 cross-process race test | ✓ on Linux/macOS | — | Test marked `@pytest.mark.skipif(sys.platform == "win32")` per D-24 |

**Missing dependencies with no fallback:** None — all pinned packages verified installed.
**Missing dependencies with fallback:** None — runtime LLM availability is a soft dependency; the error-alert path (D-16) is the documented degraded experience.

---

## Sources

### Primary (HIGH confidence)
- `markdown-it-py` 4.0.0 — `.venv/lib/python3.13/site-packages/markdown_it/presets/js_default.py` (verified by import + introspection) — `js-default` options: `html=False, linkify=False, typographer=False`
- `markdown-it-py` security docs (CITED): https://markdown-it-py.readthedocs.io/en/latest/security.html — `js-default` is the recommended preset for user-supplied content
- `cachetools` 7.0.6 — verified `c.timer._Timer__timer` is `time.monotonic` (writable on inner instance); `c.timer` property is read-only (raises AttributeError on assignment)
- `openai` SDK 2.32.0 — verified by `dir(openai)`: all 12 exception classes (`APIError`, `APIConnectionError`, `APITimeoutError`, `APIStatusError`, `AuthenticationError`, `RateLimitError`, etc.) exist as direct attributes
- `openai.OpenAI()` constructor signature — verified via `inspect.signature`: accepts `api_key`, `base_url`, `timeout`, `max_retries`, `default_headers`, `http_client` as kwargs
- Ollama OpenAI-compatible API — https://docs.ollama.com/api/openai-compatibility (CITED in CLAUDE.md sources)
- Existing codebase patterns:
  - `app_v2/services/cache.py` lines 1-150 — TTLCache+Lock idiom (HIGH confidence — Phase 1 reviewed/merged)
  - `app_v2/services/overview_store.py` lines 96-141 — `_atomic_write` (HIGH — Phase 2 reviewed/merged, includes file-mode-preservation fix from WR-03)
  - `app_v2/services/overview_filter.py` lines 54-69 — `has_content_file` path traversal pattern
  - `tests/v2/test_cache.py` lines 179-205 — `_Timer__timer` patch idiom (verbatim source for D-25 test)
  - `tests/v2/test_overview_routes.py` lines 27-46 — TestClient + monkeypatch fixture pattern
  - `app/adapters/llm/openai_adapter.py` lines 17-62 — openai SDK pattern with `httpx.Timeout` and `extra_headers`
  - `app/adapters/llm/ollama_adapter.py` — current Ollama path uses raw `requests`; the OpenAI-compatible `/v1` route is the consolidation target for Phase 03

### Secondary (MEDIUM confidence)
- HTMX 2.0.10 docs — `hx-disabled-elt`, `hx-indicator`, `hx-target`, `hx-swap-oob` semantics (already validated in Phase 1/2 templates)
- Bootstrap 5.3.8 nav-pills + `data-bs-toggle="pill"` JS interaction with HTMX click handlers (Phase 03 will be the first integration; pattern is documented in Bootstrap docs but not yet exercised in PBM2)
- Phase 02 `.planning/research/PITFALLS.md` Pitfalls 1, 2, 4, 7 (carry forward)

### Tertiary (LOW confidence — informational only)
- Pitfall 17 (hx-confirm dialog text length): anecdotal browser-specific truncation reports, not triggered at current copy length (165 chars)

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — all 4 critical libraries (markdown-it-py, cachetools, openai, fastapi) verified by `.venv` import + introspection
- Architecture patterns: **HIGH** — every pattern is a 1:1 reuse of an existing Phase 01/02 module or the v1.0 `openai_adapter.py`
- LLM integration: **HIGH** — verified openai SDK signature, exception classes, and Ollama base_url pattern
- Pitfalls: **HIGH** for carry-forwards (Pitfalls 1/2/4/7 already validated in earlier phases); **HIGH** for new Pitfalls 13-14 (mtime, cachetools timer); **MEDIUM** for new Pitfall 15 (Bootstrap+HTMX interaction not yet exercised in PBM2); **HIGH** for Pitfall 18 (Ollama cold-start is well-documented)

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (30 days — stack is pinned and stable)
