---
phase: 02-overview-tab-filters
fixed_at: 2026-04-25T00:00:00Z
review_path: .planning/phases/02-overview-tab-filters/02-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-04-25
**Source review:** `.planning/phases/02-overview-tab-filters/02-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (Critical: 0, Warning: 4)
- Fixed: 4
- Skipped: 0
- Info findings (8) were excluded from scope (`fix_scope=critical_warning`).

Full test suite re-run after all fixes: **290 passed**, no regressions.

## Fixed Issues

### WR-01: Duplicate HTML element ID `filter-count-badge` in initial full-page render

**Files modified:** `app_v2/templates/overview/index.html`
**Commit:** `dbad4b9`
**Applied fix:** Renamed the visible summary badge inside `<summary>` (line 34) to
`id="filter-count-summary"` so the OOB-swap carrier inside the `entity_list` block
remains the single element with `id="filter-count-badge"`. Document IDs are now
unique per HTML spec; htmx OOB swaps target the unambiguous in-block carrier.
The summary badge's class binding (`bg-primary` + `d-none` toggle on `active_filter_count == 0`)
is unchanged so the visible UI behaves identically. Tests in `test_overview_filter.py`
that check `id="filter-count-badge"` on fragment responses still pass because the OOB
carrier name is preserved (Option B from the review).

### WR-02: TOCTOU race in `add_overview` / `remove_overview` under concurrent requests

**Files modified:** `app_v2/services/overview_store.py`
**Commit:** `e07d924`
**Applied fix:** Added a module-level `threading.Lock` (`_store_lock`) — same pattern
as `app_v2/services/cache.py` — and wrapped the read-modify-write critical section
of both `add_overview` and `remove_overview` in `with _store_lock:`. The lock guards
`load_overview()` → membership check → `_atomic_write()` so two concurrent threadpool
requests cannot stomp each other. Per-process scope is sufficient for the single-uvicorn
intranet deployment (documented in code comment with note to switch to `fcntl.flock`
if multi-worker is ever introduced). All 13 store tests + 18 routes tests still pass.

### WR-03: `_atomic_write` drops original file permissions, leaks tempfile umask

**Files modified:** `app_v2/services/overview_store.py`
**Commit:** `72ba3db`
**Applied fix:** Imported `stat`; in `_atomic_write` capture the existing file mode
(`stat.S_IMODE(path.stat().st_mode)`) BEFORE writing, or compute the umask-derived
default (`0o666 & ~umask`) when the file does not yet exist. After the successful
`os.replace(tmp_name, path)`, call `os.chmod(path, target_mode)` to restore the
permission. This prevents `tempfile.mkstemp`'s default `0o600` from silently
tightening operator-applied permissions on `config/overview.yaml` after the first add.

### WR-04: Unused `has_content_file` import in `routers/overview.py`

**Files modified:** `app_v2/routers/overview.py`
**Commit:** `5f92aca`
**Applied fix:** Removed the unused `has_content_file` import from the
`app_v2.services.overview_filter` import block. The misleading "for test-surface
parity" comment was deleted along with it. No tests reference the symbol via
`routers.overview`, so removal is safe and silences the ruff `F401` lint.
The `apply_filters` function (which internally calls `has_content_file`) remains
imported and unchanged.

---

_Fixed: 2026-04-25_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
