---
phase: 03-content-pages-ai-summary
reviewed: 2026-04-25T00:00:00Z
depth: standard
files_reviewed: 30
files_reviewed_list:
  - app_v2/data/atomic_write.py
  - app_v2/data/summary_prompt.py
  - app_v2/main.py
  - app_v2/routers/overview.py
  - app_v2/routers/platforms.py
  - app_v2/routers/summary.py
  - app_v2/services/content_store.py
  - app_v2/services/llm_resolver.py
  - app_v2/services/overview_store.py
  - app_v2/services/summary_service.py
  - app_v2/templates/platforms/detail.html
  - app_v2/templates/platforms/_content_area.html
  - app_v2/templates/platforms/_edit_panel.html
  - app_v2/templates/platforms/_preview_pane.html
  - app_v2/templates/summary/_success.html
  - app_v2/templates/summary/_error.html
  - app_v2/templates/overview/_entity_row.html
  - app_v2/templates/base.html
  - app_v2/static/css/tokens.css
  - app_v2/static/css/app.css
  - .gitignore
  - tests/v2/test_atomic_write.py
  - tests/v2/test_llm_resolver.py
  - tests/v2/test_content_store.py
  - tests/v2/test_content_routes.py
  - tests/v2/test_summary_service.py
  - tests/v2/test_summary_routes.py
  - tests/v2/test_content_store_race.py
  - tests/v2/test_summary_integration.py
  - tests/v2/test_phase03_invariants.py
findings:
  critical: 0
  warning: 3
  info: 7
  total: 10
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-04-25T00:00:00Z
**Depth:** standard
**Files Reviewed:** 30
**Status:** issues_found

## Summary

Phase 03 implements per-platform markdown content pages and the AI Summary feature. The implementation is high-quality and security-conscious overall. The four pitfall axes called out in the brief are all correctly defended:

- **Path traversal (Pitfall 2):** Two-layer defense is present and working — FastAPI `Path(..., pattern=PLATFORM_ID_PATTERN)` on every route, plus `content_store._safe_target` re-asserts containment via `Path.resolve()` + `.relative_to()` before any filesystem call. 15 test cases (3 attack strings × 5 routes) cover the route layer and a unit test exercises `_safe_target` directly.
- **Markdown XSS (Pitfall 1):** `MarkdownIt("js-default")` is the only constructor used in `app_v2/`, enforced by the codebase invariant guard in `test_phase03_invariants.py`. Three positive tests confirm `<script>`, `onerror`, and `javascript:` URI escapes.
- **Sync-in-async (Pitfall 4):** Every Phase 03 route is `def`, not `async def`. A grep-style invariant test guards both `routers/platforms.py` and `routers/summary.py`.
- **Lock not held during LLM call (Pitfall 11):** `summary_service.get_or_generate_summary` releases the lock between cache lookup and the LLM call; a non-blocking-acquire side-effect test in `test_summary_service.py` proves it.

The `<notes>` tag wrapping for prompt-injection defense (T-03-03) is correctly implemented; the system prompt is explicit about treating tag contents as untrusted. mtime_ns (int) is used for cache keying (Pitfall 13). The summary route never returns 5xx — every classified failure flows through the error fragment with HTTP 200. `atomic_write_bytes` is the single shared helper used by both `overview_store` and `content_store`, with a cross-process `multiprocessing.fork()` race test asserting the POSIX `os.replace` invariant.

The findings below are limited to: (1) a real correctness bug in the edit-panel HTMX wiring that the test suite does not catch because the test posts directly to the preview endpoint, (2) two semantic mismatches between the size-limit spec and its implementation, and (3) a handful of minor info-level items (unused imports, doc/comment drift, missing client-side niceties promised in the UI spec). No Critical issues were found.

## Warnings

### WR-01: Preview tab `hx-include="closest form"` cannot find the form — preview never receives textarea content

**File:** `app_v2/templates/platforms/_edit_panel.html:18-29`

**Issue:** The Preview tab `<button>` declares `hx-include="closest form"`, but that button is NOT a descendant of any `<form>` in the rendered DOM. The button lives at line 18-29 inside `<ul class="nav-pills">` → `<div class="panel-header">`. The `<form>` element does not start until line 35, AFTER `</div></div>` of the panel-header. They are siblings inside the outer `.panel` `<div>`, not ancestor/descendant.

HTMX's `closest <selector>` walks up the ancestor chain from the trigger element. Since the button has no ancestor `<form>`, `hx-include="closest form"` resolves to nothing, and the textarea content is omitted from the POST body. The server then receives `content=""` (the Form default) and renders an empty preview pane. UI-SPEC §6 explicitly requires the preview to render the current textarea content, including the debounced 500ms refresh-on-typing flow.

The integration tests in `tests/v2/test_content_routes.py::test_post_preview_renders_markdown` POST directly to `/platforms/{pid}/preview` with `data={"content": "# Hi"}`, so they cannot detect this — the broken `hx-include` only matters for the actual HTMX-driven UX path, which AppTest-style tests don't exercise.

**Fix:** Reference the textarea by id instead of relying on form ancestry:

```html
<button class="nav-link"
        id="preview-tab"
        ...
        hx-post="/platforms/{{ platform_id }}/preview"
        hx-include="#md-textarea"
        hx-target="#preview-pane"
        hx-swap="innerHTML"
        hx-trigger="click, keyup changed delay:500ms from:#md-textarea">Preview</button>
```

`#md-textarea` is the unique id assigned to the textarea (line 42), and `hx-include` accepts any CSS selector. Add a regression test that asserts the rendered HTML contains `hx-include="#md-textarea"` (or a more direct test that mounts the page in a headless browser and exercises Preview, but a string check on the template output is sufficient to lock the contract).

---

### WR-02: `Form(max_length=65536)` counts characters, not bytes — D-31's "64 KB per file" can be exceeded by ~4×

**File:** `app_v2/routers/platforms.py:43, 113, 130` and `app_v2/services/content_store.py:31`

**Issue:** D-31 specifies "Content size limit: 64 KB per file." Pydantic / FastAPI's `Form(max_length=N)` and the textarea's `maxlength="65536"` cap the **codepoint length** of the string, not its UTF-8 byte length. A 65,536-character payload of all 4-byte codepoints (e.g., emoji like 🎉, 4-byte CJK ideographs, mathematical symbols) encodes to **262,144 bytes on disk** — 4× the documented limit. A user pasting Chinese, Japanese, Korean, or emoji-heavy notes can quietly exceed the on-disk cap.

Additionally, `content_store.MAX_CONTENT_BYTES = 65536` is declared as "informational" but is never enforced anywhere in the module. `save_content` accepts any size payload and writes it. The comment explicitly defers to "the route enforces via Form(max_length=...)" — but the route's enforcement is in characters, not bytes, so the constant's stated unit (bytes) does not match the reality of the validation.

This is not a security risk (the path-traversal regex still applies, atomic write still works, `tempfile.mkstemp` won't run out of inodes from a 256KB write), but it does mean the system can store files that violate D-31's stated invariant. Tests `test_post_save_too_large_returns_422` and `test_post_preview_too_large_returns_422` use ASCII (`"x" * (65536 + 1)`) so they never expose the codepoint-vs-byte discrepancy.

**Fix:** Pick one consistent semantics and enforce it at every layer. Recommended: enforce **bytes** server-side in `content_store.save_content` (the canonical I/O point):

```python
# app_v2/services/content_store.py
MAX_CONTENT_BYTES: int = 65536  # D-31 — UTF-8 bytes, enforced here

def save_content(platform_id: str, payload: str, content_dir: Path = DEFAULT_CONTENT_DIR) -> None:
    encoded = payload.encode("utf-8")
    if len(encoded) > MAX_CONTENT_BYTES:
        raise ValueError(
            f"Content exceeds {MAX_CONTENT_BYTES}-byte limit "
            f"({len(encoded)} bytes)"
        )
    target = _safe_target(platform_id, content_dir)
    atomic_write_bytes(target, encoded, default_mode=0o644)
```

Then in `routers/platforms.py::save_content_route`, catch the `ValueError` and return a 422 with the existing copywriting-contract message ("Content too large: 64 KB max…"). Keep `Form(max_length=65536)` as a cheap pre-check (it rejects pathological all-emoji uploads at HTTP boundary), but treat it as a coarse filter, not the authority. Update tests with a payload like `"🎉" * 16385` (4×16385 = 65540 bytes) to assert the byte-level rejection.

Alternatively, if the team accepts "limit is in characters" as the documented semantics, update D-31 (and the UI-SPEC error message that says "64 KB max") to say "65,536 characters" — but the on-disk constant must then be renamed `MAX_CONTENT_CHARS` and `_BYTES` removed for consistency.

---

### WR-03: `_render_error` returns `200 OK` only because `templates.TemplateResponse` defaults to 200 — make it explicit

**File:** `app_v2/routers/summary.py:75-81`

**Issue:** The Phase 03 contract is "summary route ALWAYS returns 200" — verified by `test_phase03_invariants.test_summary_route_never_returns_5xx` and `test_summary_routes.test_post_summary_never_returns_5xx_on_any_exception`. The implementation depends on the implicit default `status_code=200` in `templates.TemplateResponse` when no explicit status is passed.

This works today, but makes the always-200 invariant invisible to a future maintainer reading the helper. A reasonable refactor (e.g., copying the helper to extend it, or wrapping in a `status_code=` plumbing change for some other reason) could silently break the contract. The grep-based invariant guard checks for `status_code\s*=\s*5\d\d` and `raise HTTPException` literals — it would NOT catch a maintainer accidentally writing `status_code=4xx` or letting an exception propagate from the helper.

**Fix:** Make the 200 explicit at the helper boundary, so the contract is encoded at the call site and not just in the template-engine default:

```python
def _render_error(request: Request, platform_id: str, reason: str) -> HTMLResponse:
    """Render the amber-warning error fragment with a classified reason.

    Always status 200 — UI-SPEC mandate. Error fragment swaps inline into
    the per-row summary slot; never escalate to #htmx-error-container.
    """
    return templates.TemplateResponse(
        request,
        "summary/_error.html",
        {"platform_id": platform_id, "reason": reason},
        status_code=200,
    )
```

Add a one-line invariant test that the helper returns `r.status_code == 200` for any reason string.

## Info

### IN-01: `_log = logging.getLogger(__name__)` declared but never used

**Files:** `app_v2/routers/platforms.py:38`, `app_v2/services/content_store.py:28`

**Issue:** Both modules import `logging` and create a module-level `_log` logger but never call any method on it. The line is dead. `summary.py` and `summary_service.py` do use their loggers, so they are fine.

**Fix:** Either remove the unused declarations, or add the missing logging at the obvious sites:

```python
# content_store.py: log when path traversal is rejected (defense-in-depth signal)
def _safe_target(platform_id: str, content_dir: Path) -> Path:
    base = content_dir.resolve()
    candidate = (content_dir / f"{platform_id}.md").resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        _log.warning("Path traversal rejected for platform_id=%r", platform_id)
        raise
    return candidate
```

Logging the rejection at `WARNING` is useful when investigating "where did that 422 come from?" If the team prefers silent rejection (the regex normally pre-empts this code path), just delete the unused declarations.

---

### IN-02: `LLMNotConfiguredError` is defined but never raised

**File:** `app_v2/services/summary_service.py:71-77`

**Issue:** The class is documented in the module docstring ("`LLMNotConfiguredError` — raised when `settings.llms` is empty") but the route handles the empty-LLM case BEFORE calling into `summary_service` (`routers/summary.py:96-99` checks `cfg is None` and returns the error fragment directly). The exception class is dead code. This is harmless but confusing — a reader looking at the module's "Public surface used by routers/summary.py" list would expect this exception to be in the call graph.

**Fix:** Either delete the class, or move the empty-LLM check INSIDE `summary_service.get_or_generate_summary` and raise it there, then have the route catch it. Deleting is simpler:

```python
# Remove the class, update the docstring to drop the LLMNotConfiguredError bullet.
```

---

### IN-03: `<title>` mismatch with UI-SPEC copywriting contract

**File:** `app_v2/templates/base.html:6`

**Issue:** UI-SPEC §Copywriting Contract specifies `<title>{pid} — PBM2`, but `base.html` renders `<title>{{ page_title | default("PBM2") }} — PBM2 v2.0</title>`. The test `test_get_detail_includes_page_title` already locks the actual rendered string (`{_PID} — PBM2 v2.0`), so this is a UI-SPEC drift, not a regression. Either the spec or the template should be updated to match — pick one source of truth.

**Fix:** If `v2.0` in the title is intentional (it is informative for the team during the v1.0/v2.0 parallel-deployment period), update UI-SPEC's Copywriting Contract row to match. Otherwise drop ` v2.0` from the template's `<title>`. The test assertion will need to follow whichever choice is made.

---

### IN-04: Char counter does not update on input — UI-SPEC §6 promised inline JS

**File:** `app_v2/templates/platforms/_edit_panel.html:32`

**Issue:** UI-SPEC §6 states: *"Char counter: Updates client-side via a tiny inline JS `oninput` — counts textarea length, color turns `var(--red)` at >65000 chars. Defensive UX for the 64KB cap (D-31)."* The current template renders the count once at server-render time (`{{ raw_md | length }} / 65536`) and never updates as the user types. There is no `oninput` handler, no warning color near the limit, and no JavaScript bound to `#md-textarea` or `#char-count`.

This is a UX papercut, not a correctness bug — the textarea's `maxlength="65536"` still hard-stops typing at the codepoint limit (and see WR-02 for the byte-vs-char issue). The user just doesn't get visible feedback before they hit the wall.

**Fix:** Add a small inline `<script>` after the textarea (or inside `_edit_panel.html`):

```html
<script>
  (function() {
    const ta = document.getElementById('md-textarea');
    const counter = document.getElementById('char-count');
    if (!ta || !counter) return;
    function update() {
      const n = ta.value.length;
      counter.textContent = n + ' / 65536';
      counter.style.color = (n > 65000) ? 'var(--red)' : '';
    }
    ta.addEventListener('input', update);
  })();
</script>
```

Place this inside the edit panel fragment (it gets re-evaluated on each HTMX swap because the script tag is part of the swapped subtree). Alternatively, defer to a Phase-03-F follow-up if v1 is acceptable without live feedback.

---

### IN-05: Preview `keyup` fires while the Write tab is active too — UI-SPEC said "while Preview tab is active"

**File:** `app_v2/templates/platforms/_edit_panel.html:29`

**Issue:** UI-SPEC §6 (D-07): *"Debounced via `hx-trigger="click, keyup changed delay:500ms from:closest textarea"` on the Preview pill — typing in textarea while Preview tab is active also re-renders (debounced 500ms)."* The current implementation (`hx-trigger="click, keyup changed delay:500ms from:#md-textarea"`) fires the preview request whenever the user types in the textarea, regardless of which tab is active. If WR-01 is fixed, this means every keystroke (debounced 500ms) issues a POST while the user is still in the Write tab, costing one HTTP round trip per pause.

Functionally harmless (the response just lands in the hidden Preview pane), but adds chattiness. UI-SPEC's intent is "only debounce-refresh when Preview is the visible tab."

**Fix (optional):** Add a small `hx-trigger` filter or a JS handler that checks `document.querySelector('#preview-tab').classList.contains('active')` before letting the request go out. Or accept the chattiness as the tradeoff for simpler markup. The user's volume is small (~10-user intranet), so leaving as-is is defensible. Note in a follow-up rather than fixing in this phase.

---

### IN-06: `_loading.html` template referenced in UI-SPEC §Template File Map but not present

**File:** UI-SPEC §Template File Map vs. `app_v2/templates/summary/`

**Issue:** UI-SPEC's Template File Map row says: *"`app_v2/templates/summary/_loading.html` — pre-seeded indicator — The `htmx-indicator` div embedded in the summary slot wrapper."* The actual implementation inlines the `htmx-indicator` markup directly into `_entity_row.html` (lines 47-58) and `detail.html` (lines 65-74). No `_loading.html` file exists.

This is a defensible choice — the indicator must live in the persistent shell of each consumer page (not be swapped in by HTMX), so a separate template would have to be `{% include %}`d at exactly two sites. Inlining is fine. But the UI-SPEC table is now out of sync with reality.

**Fix:** Update UI-SPEC §Template File Map to drop the `_loading.html` row and add a note that the loading indicator is inlined per-consumer in `_entity_row.html` and `detail.html`. Or extract the indicator to `_loading.html` and `{% include %}` it twice — pure cleanup, equivalent runtime behavior.

---

### IN-07: `Path` import collision documentation in `summary.py` is correct but slightly misleading

**File:** `app_v2/routers/summary.py:51-55`

**Issue:** The block comment says "do NOT `from pathlib import Path` here" because it would shadow `fastapi.Path`. That is correct. But the next sentence says "summary.py only uses FastAPI's Path (for path-parameter validation) and reaches pathlib paths transitively via `platforms_router.CONTENT_DIR`" — which is also correct, but it's worth noting the module DOES rely on the pathlib `Path` instance via `platforms_router.CONTENT_DIR` being a pathlib `Path`. If a future refactor changes that constant's type (e.g., to a string), the route silently breaks because `summary_service.get_or_generate_summary` expects a pathlib Path.

**Fix:** Add a one-line type assert inside `get_summary_route`, or — better — change the call to use `app_v2.routers.platforms.CONTENT_DIR` directly (which it already does) and add a `mypy` type annotation on `CONTENT_DIR` in `platforms.py` (it's already annotated as `_Path`, so this is already fine — the comment in `summary.py` is just slightly underspecified). Lowest-effort fix: add one sentence to the comment block clarifying that `platforms_router.CONTENT_DIR` is annotated `_Path`, and a future refactor must preserve that.

No code change is strictly required; this is a documentation refinement to make the cross-module invariant explicit.

---

_Reviewed: 2026-04-25T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
