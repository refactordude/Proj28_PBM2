---
phase: 02-overview-tab-filters
reviewed: 2026-04-25T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - app_v2/data/__init__.py
  - app_v2/data/platform_parser.py
  - app_v2/data/soc_year.py
  - app_v2/services/overview_store.py
  - app_v2/services/overview_filter.py
  - app_v2/routers/overview.py
  - app_v2/routers/root.py
  - app_v2/main.py
  - app_v2/templates/overview/index.html
  - app_v2/templates/overview/_entity_row.html
  - app_v2/templates/overview/_filter_alert.html
  - config/overview.example.yaml
  - tests/v2/test_platform_parser.py
  - tests/v2/test_soc_year.py
  - tests/v2/test_overview_store.py
  - tests/v2/test_overview_routes.py
  - tests/v2/test_overview_filter.py
findings:
  critical: 0
  warning: 4
  info: 8
  total: 12
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-25
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Phase 02 delivers the Overview tab + curated-list filters: a PLATFORM_ID parser,
SoC→year lookup, atomic YAML store, three Jinja templates, and four routes
(`GET /`, `POST /overview/add`, `DELETE /overview/{pid}`, `POST /overview/filter`,
`POST /overview/filter/reset`). Test coverage is thorough (258 tests passing, per
git log) and security-critical pitfalls are addressed:

- **Path traversal (Pitfall 2):** correctly defended at TWO layers — strict regex
  via `fastapi.Path/Form(pattern=...)` AND `Path.resolve()` + `relative_to()` in
  `has_content_file`. Test `test_has_content_false_when_platform_id_escapes_dir`
  verifies the resolve+relative_to defense works against `../`, `../../etc/passwd`.
- **Sync-in-async (Pitfall 4):** every route handler is `def`, not `async def`.
  Confirmed: `overview_page`, `add_platform`, `remove_platform`, `filter_overview`,
  `reset_filters`, plus root.py stubs.
- **YAML atomicity (D-24):** `_atomic_write` uses `tempfile.mkstemp(dir=path.parent)`
  + `fsync` + `os.replace`. Test `test_write_is_atomic_on_os_replace_failure`
  verifies the pre-replace state survives a simulated crash.
- **No markdown / `| safe` paths in Phase 2 templates** — Jinja2 autoescape applies
  to all interpolated values (Pitfall 1 deferred to Phase 3 as planned).
- **HTMX OOB swap (Pitfall 7):** `#filter-count-badge` is rendered inside the
  `entity_list` block so every filter/add/remove response carries it. See WR-01
  for a duplicate-ID concern that, while not a Pitfall 7 violation, can still
  cause OOB updates to silently miss the visible summary badge.

The findings below are non-blocking but worth addressing before this surface
expands further (notably: Phase 3 will introduce concurrent content-page edits
that could amplify WR-02's TOCTOU race).

---

## Warnings

### WR-01: Duplicate HTML element ID `filter-count-badge` in initial full-page render

**File:** `app_v2/templates/overview/index.html:34, app_v2/templates/overview/index.html:88`
**Issue:**
On a full-page `GET /` render, the template emits TWO elements with the same
`id="filter-count-badge"`:

1. Inside `<summary>` (line 34) — visible badge in the Filters disclosure.
2. Inside `{% block entity_list %}` (line 88) — the OOB-swap template element with
   `hx-swap-oob="true"`.

This violates the HTML spec (IDs must be unique per document) and creates two
problems:

- **HTMX OOB ambiguity (Pitfall 7-adjacent):** When a filter response returns the
  fragment, htmx looks up `#filter-count-badge` in the existing DOM to perform the
  OOB swap. With two matching elements, htmx swaps the first one it finds (the
  summary badge), which happens to be what's wanted — but the in-fragment OOB span
  then ALSO renders inline at the top of `#overview-list` because htmx doesn't
  remove OOB elements from their position in the response (it copies them to the
  matching ID, leaving the original in-fragment span where it lands). The result
  is a stray badge inside `<ul id="overview-list">` after every filter, which is
  invalid (a `<span>` is not a valid direct child of `<ul>`) and may render as a
  zombie badge above the list.
- **Browser dev-tools / accessibility:** `document.getElementById('filter-count-badge')`
  returns the first match only; assistive tech may announce both badges.

**Fix:**
Render the OOB span OUTSIDE the `<ul id="overview-list">` (browsers tolerate
OOB elements at the top of an HTMX response body) and give it a different attribute
strategy. Option A: have the route response prepend the OOB span before the list
content. Option B: change the in-summary badge to a different id (e.g. `filter-count-summary`)
and keep `filter-count-badge` only for the OOB carrier. Concrete fix using Option B:

```jinja
{# In <summary> (line 34): rename the visible badge #}
<span id="filter-count-summary"
      class="badge bg-primary {% if active_filter_count == 0 %}d-none{% endif %}">
  {{ active_filter_count }}
</span>

{# In entity_list block (line 88): keep filter-count-badge as OOB target,
   but render it OUTSIDE the <ul> so it isn't an invalid <ul> child.
   Move the OOB span above {% block entity_list %} or split block scope. #}
```

The simplest correct shape is to make the visible summary badge ALSO the OOB
target (single element with that id), which means the route must return a fragment
that targets the summary badge directly via OOB swap and the entity list separately.
Either restructure or rename — the current state is bug-prone.

---

### WR-02: TOCTOU race in `add_overview` / `remove_overview` under concurrent requests

**File:** `app_v2/services/overview_store.py:121-138, app_v2/services/overview_store.py:141-151`
**Issue:**
FastAPI dispatches `def` routes to a threadpool (Pitfall 4 / INFRA-05) — meaning
two concurrent `POST /overview/add` requests can run `add_overview()` simultaneously
in two threads. Both calls execute the read-modify-write sequence:

```python
current = load_overview()        # T1 reads [A]
                                 # T2 reads [A]
# T1 sees no duplicate, writes [B, A]
# T2 sees no duplicate, writes [C, A]   <-- B is now lost
_atomic_write([new_entity, *current])
```

`os.replace` is atomic at the FS layer (no half-written file), but the
read-modify-write across multiple syscalls is NOT atomic across threads. The
losing thread's add silently disappears even though both clients got HTTP 200 +
an entity-row fragment. The same race applies to `remove_overview` — a delete
can resurrect an entity if it interleaves with a concurrent add.

This is unlikely in PBM2's intranet single-user setup but realistic when two
team members curate simultaneously, and it's directly enabled by the threadpool
concurrency the project relies on.

**Fix:**
Wrap the read-modify-write critical section in a module-level `threading.Lock`
(same pattern as `app_v2/services/cache.py`):

```python
import threading

_store_lock = threading.Lock()

def add_overview(platform_id: str) -> OverviewEntity:
    with _store_lock:
        current = load_overview()
        if any(e.platform_id == platform_id for e in current):
            raise DuplicateEntityError(...)
        new_entity = OverviewEntity(
            platform_id=platform_id,
            added_at=datetime.now(timezone.utc),
        )
        _atomic_write([new_entity, *current])
        return new_entity

def remove_overview(platform_id: str) -> bool:
    with _store_lock:
        current = load_overview()
        remaining = [e for e in current if e.platform_id != platform_id]
        if len(remaining) == len(current):
            return False
        _atomic_write(remaining)
        return True
```

Per-process lock is sufficient (only one FastAPI process touches `overview.yaml`).
If the deployment ever runs multiple workers, switch to `fcntl.flock` on the YAML
file or a sidecar `.lock` file.

---

### WR-03: `_atomic_write` drops original file permissions, leaks tempfile umask

**File:** `app_v2/services/overview_store.py:103-111`
**Issue:**
`tempfile.mkstemp` creates files with mode `0o600` regardless of the existing
`overview.yaml` permissions. After `os.replace(tmp_name, path)`, the new
`overview.yaml` inherits `0o600` — even if the original was `0o644` or had ACLs
applied by the deployment. Two concrete consequences:

1. After the first add, only the OS user that started uvicorn can read the YAML
   (e.g., `cat config/overview.yaml` from another teammate's account fails).
2. The first write happens to be `0o600` even when the operator pre-created
   `config/overview.yaml` with explicit `chmod 644`.

Not a security hole — a tighter mode is "fail safe" — but it's an operational
surprise that breaks "I can `cat` the file to debug" workflows.

**Fix:**
Snapshot the existing file mode BEFORE writing, then restore via `os.chmod` after
`os.replace`. If the file doesn't yet exist, fall back to `~umask` (the standard
new-file mode):

```python
import stat

def _atomic_write(entities: list[OverviewEntity]) -> None:
    path = OVERVIEW_YAML
    path.parent.mkdir(parents=True, exist_ok=True)
    # Capture existing mode (or compute from umask for new files).
    if path.exists():
        target_mode = stat.S_IMODE(path.stat().st_mode)
    else:
        umask = os.umask(0); os.umask(umask)
        target_mode = 0o666 & ~umask
    # ... existing tempfile/fsync/replace logic ...
    os.replace(tmp_name, path)
    os.chmod(path, target_mode)
```

---

### WR-04: Unused `has_content_file` import in `routers/overview.py`

**File:** `app_v2/routers/overview.py:31-32`
**Issue:**
`has_content_file` is imported into `routers/overview.py` with the comment
"imported for test-surface parity (tests may monkeypatch)" but no test in
`tests/v2/test_overview_routes.py` or `tests/v2/test_overview_filter.py` patches
`has_content_file` at the router level — tests either call the function directly
from `app_v2.services.overview_filter` (test_overview_filter.py:18) or rely on
real filesystem `.md` files in `tmp_path` (test_overview_filter.py:367-368).

The import is therefore dead code and the docstring rationale is wrong, which
will mislead future readers ("monkeypatch this name to mock"). Linters such as
ruff `F401` will flag it.

**Fix:**
Remove the import. If a future test wants to monkeypatch the filesystem stat
call, it should patch `app_v2.services.overview_filter.has_content_file`
directly (where `apply_filters` calls it) — patching the alias in
`routers.overview` would NOT intercept the call inside `overview_filter.apply_filters`.

```python
# app_v2/routers/overview.py
from app_v2.services.overview_filter import (
    apply_filters,
    count_active_filters,
    # has_content_file,  # <-- delete this line
)
```

---

## Info

### IN-01: Unused `pytest` imports in unit-test modules

**File:** `tests/v2/test_platform_parser.py:4, tests/v2/test_soc_year.py:4`
**Issue:**
Both files do `import pytest` but never reference `pytest` (no `@pytest.mark`,
no `pytest.raises`, no fixtures). Ruff `F401` flags this.

**Fix:** delete the line in both files. (Keep it in `test_overview_store.py` and
the other modules where `pytest.raises` / `pytest.fixture` are used.)

---

### IN-02: `test_write_is_atomic_on_os_replace_failure` saves `original_replace` but never uses it

**File:** `tests/v2/test_overview_store.py:153`
**Issue:**
The test captures `original_replace = os.replace` then patches `os.replace` via
`unittest.mock.patch`, but `original_replace` is never read or restored — `patch`
already restores the original on context exit. The line is dead code that
suggests an incomplete cleanup pattern.

**Fix:** delete `original_replace = os.replace`. The `patch("os.replace", ...)`
context manager handles teardown.

---

### IN-03: Sub-second timestamp loss in YAML serialization vs in-memory entity

**File:** `app_v2/services/overview_store.py:97`
**Issue:**
`add_overview` returns an `OverviewEntity` whose `added_at` is
`datetime.now(timezone.utc)` (microsecond precision). `_atomic_write` formats
the SAME timestamp as `"%Y-%m-%dT%H:%M:%SZ"` (second precision). Subsequent
`load_overview` calls deserialize the second-precision string. Two adds in the
same wall-clock second therefore have IDENTICAL `added_at` values after a
round-trip — the `out.sort(key=lambda e: e.added_at, reverse=True)` order
between them depends on Python's stable-sort + iteration order, not on
which-was-added-first.

The unit tests insert `time.sleep(0.01)` between adds (e.g., line 72, 115-118)
to dodge this — it's a test-only workaround that masks the issue.

**Fix:** serialize to ISO-8601 with microseconds, e.g.
`e.added_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")` —
deterministic ordering survives, the YAML stays human-readable, and tests no
longer need `sleep`.

---

### IN-04: `?tab=overview` query parameter is documented but never inspected

**File:** `app_v2/routers/overview.py:104-110`
**Issue:**
`overview_page` docstring says `?tab=overview` is "accepted (OVERVIEW-01)" but
the function signature has no `tab: str | None = None` parameter. FastAPI
silently ignores the query string, so the URL works — the docstring just
implies more behavior than exists.

This is fine as of Phase 2 (the URL is used as a stable bookmark, nothing
more) but if Phase 4 introduces server-side tab routing on a single root path,
the assumption "GET / handles ?tab=*" needs to be revisited.

**Fix:** clarify the docstring:
```python
"""Render the full Overview tab (OVERVIEW-01).

The `?tab=overview` query string is documented in OVERVIEW-01 as a stable URL
form; FastAPI ignores unknown query params, so this route accepts it without
explicit handling. If future phases route multiple tabs through GET /, this
must read `request.query_params.get("tab")`.
"""
```

---

### IN-05: `load_overview` does not deduplicate hand-edited duplicate `platform_id`s

**File:** `app_v2/services/overview_store.py:53-82`
**Issue:**
`add_overview` rejects duplicates at insertion time (D-10), but if a user
manually edits `config/overview.yaml` and accidentally writes the same
`platform_id` twice, `load_overview` returns BOTH `OverviewEntity` objects.
The Overview page then renders two identical rows; clicking "Remove" on one
only removes the first match (the list comprehension in `remove_overview`
drops ALL matches at once — fine — but the UI showed 2 rows then jumps to 0,
not 1).

**Fix:** in `load_overview`, after sorting, deduplicate while preserving
newest-first order:

```python
seen = set()
deduped: list[OverviewEntity] = []
for e in out:
    if e.platform_id in seen:
        _log.warning("dropping duplicate platform_id in overview.yaml: %s", e.platform_id)
        continue
    seen.add(e.platform_id)
    deduped.append(e)
return deduped
```

---

### IN-06: `filter_overview` / `reset_filters` reload the catalog but never use it for fragment render

**File:** `app_v2/routers/overview.py:226-230, app_v2/routers/overview.py:261-265`
**Issue:**
Both filter routes call `list(list_platforms(db, db_name=""))` to populate
`all_platform_ids` in the context. But the response uses
`block_name="entity_list"` which renders ONLY the entity list block — that
block does not iterate `all_platform_ids` (the datalist lives outside the
block, in the parent `<form>`). The catalog fetch is wasted work on every
filter change.

For a cached `list_platforms` this is cheap (TTLCache hit ~microseconds), but
on the first filter request after cache expiry it triggers a real DB query
that the response throws away.

**Fix:** drop the catalog fetch from filter / reset routes:

```python
ctx = _build_overview_context(
    entities=filtered,
    all_platform_ids=[],   # not rendered in entity_list block; skip the fetch
    selected_brand=brand or None,
    ...
)
```

Or refactor `_build_overview_context` to accept `all_platform_ids=None` and
skip the catalog round-trip when only a fragment is needed.

---

### IN-07: Module docstring in `routers/overview.py` references "Plan 02-03" — orientation aid only

**File:** `app_v2/routers/overview.py:12-15`
**Issue:**
The docstring says "Filter endpoints (...) are implemented in Plan 02-03 — this
module pre-computes the filter dropdown options ..." but Plan 02-03 has been
implemented in this same file (filter_overview + reset_filters at lines 195+).
The docstring is now stale.

**Fix:** update to past tense:
```python
"""Overview tab routes ... GET /, POST /overview/add, DELETE /overview/{pid},
POST /overview/filter, POST /overview/filter/reset.

All routes are def (INFRA-05 — FastAPI dispatches to threadpool so sync
SQLAlchemy never blocks the event loop).

Security (PITFALLS.md Pitfall 2): every user-supplied platform_id is validated
with the ^[A-Za-z0-9_\\-]{1,128}$ regex via FastAPI Path(..., pattern=...) /
Form validation BEFORE it reaches overview_store or any filesystem-adjacent
code. Phase 3 will read content/platforms/<pid>.md; the same regex protects
those routes.
"""
```

---

### IN-08: `_filter_alert.html` interpolates `alert_level` directly into `class` attribute

**File:** `app_v2/templates/overview/_filter_alert.html:3`
**Issue:**
`<div class="alert alert-{{ alert_level }} alert-dismissible fade show">` —
Jinja2 autoescape escapes HTML special chars but does NOT prevent attribute
injection of a value like `"danger" onclick="evil()`; if `alert_level` were
ever populated from user input, the value would be HTML-attribute-escaped (")
becomes `&quot;`, blocking attribute breakout in modern Jinja2 — but a CSS
class like `bg-image:url(...)` is still expressible inside a class attribute
and could exfiltrate data via attribute selectors + CSP-bypass tricks.

In Phase 2 `alert_level` is hardcoded to `"danger"` or `"warning"` by the route,
so this is not exploitable. Flagged as a future-hardening note: when refactoring
this partial, consider an explicit allowlist or use Bootstrap's class names
directly:

**Fix (defensive, not required for Phase 2):**
```jinja
{% set _level = alert_level if alert_level in ("danger","warning","info","success") else "info" %}
<div class="alert alert-{{ _level }} alert-dismissible fade show" role="alert">
```

---

_Reviewed: 2026-04-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
