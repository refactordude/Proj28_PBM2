---
phase: 03-content-pages-ai-summary
fixed_at: 2026-04-25T00:00:00Z
review_path: .planning/phases/03-content-pages-ai-summary/03-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-04-25T00:00:00Z
**Source review:** `.planning/phases/03-content-pages-ai-summary/03-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (Critical 0, Warning 3 — Info 7 deferred per fix_scope=critical_warning)
- Fixed: 3
- Skipped: 0
- Test suite after fixes: 413 passed (411 pre-existing + 2 new regression tests)

## Fixed Issues

### WR-01: Preview tab `hx-include="closest form"` cannot find the form

**Files modified:**
- `app_v2/templates/platforms/_edit_panel.html`
- `tests/v2/test_content_routes.py` (new regression test)

**Commit:** `3f7f195`

**Applied fix:** Changed `hx-include="closest form"` to `hx-include="#md-textarea"` on the Preview pill button. The button is a sibling of the `<form>` (both inside `.panel`), not a descendant — `closest form` walks up the ancestor chain and resolves to nothing, so the textarea content was never POSTed to `/preview`. The textarea has the unique id `md-textarea` (line 42); HTMX accepts any CSS selector.

**Regression test added:** `test_post_edit_preview_tab_uses_id_selector_for_hx_include` asserts the rendered edit panel contains `hx-include="#md-textarea"` and does NOT contain `hx-include="closest form"`. Locks the contract at the template-output level.

---

### WR-02: `Form(max_length=65536)` counts codepoints, not bytes — D-31 byte cap can be exceeded ~4×

**Files modified:**
- `app_v2/services/content_store.py` (authoritative byte check inside `save_content`)
- `app_v2/routers/platforms.py` (catch `ValueError`, return HTTP 413)
- `tests/v2/test_content_routes.py` (new regression test)

**Commit:** `377c15c`

**Applied fix:**
1. **`content_store.py`:** `MAX_CONTENT_BYTES = 65536` is now authoritative, not informational. `save_content` now encodes to UTF-8 first, checks `len(encoded) > MAX_CONTENT_BYTES`, and raises `ValueError(f"Content exceeds {MAX_CONTENT_BYTES}-byte limit ({len(encoded)} bytes)")` on overflow. The encoded bytes are passed to `atomic_write_bytes` so we don't re-encode.
2. **`platforms.py`:** `save_content_route` wraps `save_content(...)` in `try/except ValueError` and re-raises as `HTTPException(status_code=413, detail="Content too large: 65536 bytes max")`. Imports updated to include `HTTPException`. The existing `Form(max_length=MAX_CONTENT_LENGTH)` is retained as a coarse first-line codepoint guard (cheap rejection of pathological all-emoji uploads at HTTP boundary, per the user's instruction).
3. **Comment drift fixed:** The constant's docstring no longer says "informational; route enforces" — it now says "enforced inside save_content (authoritative)" with the rationale.

**Regression test added:** `test_post_save_emoji_payload_exceeds_byte_cap_returns_413` posts `"🎉" * 65536` (65536 codepoints, 262144 UTF-8 bytes). It first asserts the payload's codepoint count `len() == 65536` (so it passes `Form(max_length=65536)`) and byte count `== 65536 * 4` (so it must trigger the byte check). Then asserts the route returns 413 and no file was written. The pre-existing `test_post_save_too_large_returns_422` was annotated to clarify it covers the codepoint path; both tests now coexist and lock the dual-layer contract.

**Note:** Logic-correctness review — the byte arithmetic, exception flow, and HTTP status mapping all verified against the test suite (413 from new test, 422 still from old test, no regressions in `test_save_then_read_roundtrip` / unicode tests / atomic-write spy).

---

### WR-03: `_render_error` returns 200 only via implicit `TemplateResponse` default

**Files modified:**
- `app_v2/routers/summary.py`

**Commit:** `8cf8538`

**Applied fix:** Added explicit `status_code=200` to the `templates.TemplateResponse(...)` call inside `_render_error`. Updated the docstring to make the always-200 contract explicit at the helper boundary (was previously inherited from the template engine's default). A future maintainer extending the helper now sees the contract written at the call site, not implied.

**Existing invariant test `test_summary_route_never_returns_5xx` continues to pass** — it forbids `status_code=5xx` and `raise HTTPException`, both of which remain absent. The grep regex `r"status_code\s*=\s*5\d\d"` does not match `status_code=200`.

---

## Verification

- **Tier 1 (re-read):** All modified files re-read post-edit to confirm fixes present and surrounding code intact.
- **Tier 2 (syntax):** `python -c "import ast; ast.parse(...)"` passed for `content_store.py`, `platforms.py`, `summary.py`, `test_content_routes.py`.
- **Tier 3 (test suite):** Full `pytest tests/ -x -q` → **413 passed**, 0 failed (was 411 before; +2 new regression tests for WR-01 and WR-02). 3 pre-existing deprecation warnings (unrelated).

---

_Fixed: 2026-04-25T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
