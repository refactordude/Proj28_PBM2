---
phase: 01-foundation-browsing
reviewed: 2026-04-23T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - streamlit_app.py
  - app/adapters/db/mysql.py
  - app/services/result_normalizer.py
  - app/services/ufs_service.py
  - app/pages/settings.py
  - app/pages/browse.py
  - app/components/export_dialog.py
  - tests/services/test_result_normalizer.py
  - tests/services/test_ufs_service.py
  - .gitignore
  - .streamlit/config.toml
  - requirements.txt
findings:
  critical: 1
  warning: 5
  info: 4
  total: 10
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-04-23T00:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Phase 1 delivers the foundation browsing layer: a MySQL EAV adapter, a result
normalization pipeline, a UFS data service (catalog + cell fetch + pivot), a
Browse page with three tabs, a Settings page, and an export dialog.

The overall code quality is high. SQL injection risk is eliminated through
`sa.bindparam(expanding=True)` on every user-supplied filter value, and
`_TABLE` is a module constant never interpolated from user input. Auth is
correctly deferred with no demo credentials anywhere in the code. The YAML
settings path is protected by the `.gitignore` entry for `config/settings.yaml`
and `config/auth.yaml`.

One critical issue was found: a raw f-string interpolation of `_TABLE` into
SQL in `ufs_service.py` catalog queries that bypasses SQLAlchemy parameter
binding for the table name. While `_TABLE` is currently a module constant
(not user input), this is still a structural violation of the codebase's own
security contract (T-03-01), and the pattern must not be generalised. Three
warnings relate to cache-key correctness, a swallowed-exception path in
`mysql.py`, and a pandas `pd.isna()` call inside `try_numeric` that will raise
`TypeError` on a non-NA scalar. Four info-level items cover an unused import,
a duplicated cache-resource factory, a path traversal gap in the sanitizer
step ordering, and a missing test for the `_sanitize_filename` function.

---

## Critical Issues

### CR-01: f-string table name interpolation in SQL strings (ufs_service.py)

**File:** `app/services/ufs_service.py:57`, `71`, `132`, `150`

**Issue:** `_TABLE` is interpolated with an f-string directly into `sa.text()`
SQL strings in `list_platforms`, `list_parameters`, and both branches of
`fetch_cells`. The module docstring claims "Never interpolated from user data"
and the project threat model (T-03-01) requires all values in SQL to go
through bind parameters. While `_TABLE` is currently a hard-coded module
constant (`"ufs_data"`), the pattern directly contradicts the stated security
contract: if `_TABLE` were ever sourced from settings, user input, or an env
var, SQL injection would be trivially possible. The inconsistency is also
confusing during audit — the code uses parameterised values for user-supplied
filter lists but raw string formatting for the table name.

**Fix:** Use a `sa.table()` / `sa.column()` construct or a validated allowlist
lookup instead of f-string interpolation. The minimal safe change that keeps
the current single-table architecture:

```python
# At module level — explicit allowlist
_ALLOWED_TABLES = frozenset({"ufs_data"})

def _safe_table(name: str) -> str:
    if name not in _ALLOWED_TABLES:
        raise ValueError(f"Table '{name}' is not in the allowed table list")
    return name

# In list_platforms:
tbl = _safe_table(_TABLE)
df = pd.read_sql_query(
    sa.text(f"SELECT DISTINCT PLATFORM_ID FROM {tbl} ORDER BY PLATFORM_ID"),
    conn,
)
```

For a stricter fix that avoids f-strings entirely, use SQLAlchemy Core
expression language:

```python
_ufs_table = sa.table(
    "ufs_data",
    sa.column("PLATFORM_ID"),
    sa.column("InfoCategory"),
    sa.column("Item"),
    sa.column("Result"),
)
# list_platforms:
stmt = sa.select(sa.func.distinct(_ufs_table.c.PLATFORM_ID)).order_by(_ufs_table.c.PLATFORM_ID)
df = pd.read_sql_query(stmt, conn)
```

---

## Warnings

### WR-01: Multi-DB cache collision — `_db` skipped in cache key (ufs_service.py)

**File:** `app/services/ufs_service.py:23-26`, `48`, `63`, `85`

**Issue:** All three `@st.cache_data` functions (`list_platforms`,
`list_parameters`, `fetch_cells`) use `_db` with an underscore prefix, which
tells Streamlit to skip hashing that argument. The module docstring explicitly
acknowledges this as "T-03-04 / Pitfall-8" for `fetch_cells`, but the same
problem exists for `list_platforms` and `list_parameters` and is not
documented there. In the current single-DB deployment this is harmless, but
the warning is warranted because the settings UI allows adding multiple
databases and the sidebar shows a DB selector — a second session choosing a
different DB would get cached catalog data from the first DB.

**Fix:** Add an explicit `db_name: str` argument alongside `_db` to all three
functions so the cache key includes the database identity:

```python
@st.cache_data(ttl=300, show_spinner=False)
def list_platforms(_db: DBAdapter, db_name: str) -> list[str]:
    ...

# Call site in browse.py / ufs_service tests:
list_platforms(adapter, db_name=active_db_name)
```

The `db_name` string is hashable, so `@st.cache_data` will include it in the
key automatically. This is the same pattern recommended for Phase 2 in the
module docstring — apply it now before the first multi-DB user hits the bug.


### WR-02: Bare `except` swallows SQLAlchemy engine errors silently (mysql.py)

**File:** `app/adapters/db/mysql.py:58`

**Issue:** In `get_schema`, the `except Exception: pk_cols = set()` block
silently discards any exception from `inspector.get_pk_constraint(t)`. If
SQLAlchemy raises a real connectivity error here (not just a missing PK
constraint), the error is swallowed, the column list is returned without PK
markings, and the caller has no way to distinguish "no PK" from "DB is down".
The pattern is consistent within the method but is the kind of broad catch
that hides operational problems.

**Fix:** Narrow the catch to the specific exception type that `get_pk_constraint`
raises for missing constraints (typically `sqlalchemy.exc.NoInspectionAvailable`
or `NotImplementedError` depending on the backend), or at minimum log the
exception before swallowing it:

```python
try:
    pk_cols = set(inspector.get_pk_constraint(t).get("constrained_columns") or [])
except Exception as exc:
    logger.debug("get_pk_constraint failed for table %s: %s", t, exc)
    pk_cols = set()
```

At the very least add a `logger.debug(...)` call so the exception appears in
logs during DB troubleshooting.


### WR-03: `pd.isna()` raises `TypeError` on scalar non-NA values in `try_numeric` (result_normalizer.py)

**File:** `app/services/result_normalizer.py:299`

**Issue:** Inside `_coerce` (the inner function of `try_numeric`), the first
guard is `if pd.isna(val): return pd.NA`. For a plain Python `str` such as
`"abc"`, `pd.isna("abc")` returns `False` — that is correct. However, for a
non-scalar array-like value (e.g., a list or numpy array), `pd.isna()` returns
an array rather than a scalar bool, which means the `if` statement silently
evaluates to the truthiness of an array — a well-known pandas footgun that
raises `ValueError: The truth value of an array is ambiguous` in pandas 3.x if
the array is non-empty. The same guard pattern in `is_missing` (line 91)
correctly wraps the `pd.isna` call in a `try/except (TypeError, ValueError)`,
but `try_numeric` does not.

**Fix:** Mirror the safe guard from `is_missing`:

```python
def _coerce(val: Any) -> Any:
    try:
        if pd.isna(val):
            return pd.NA
    except (TypeError, ValueError):
        pass  # array-like — fall through to string coercion
    s = str(val).strip()
    ...
```

Alternatively, restrict the early-exit check to `None` and `pd.NA` explicitly:

```python
if val is None or val is pd.NA:
    return pd.NA
```


### WR-04: `_sanitize_filename` step ordering: `".."` removal before charset clamp leaves `/` unhandled (export_dialog.py)

**File:** `app/components/export_dialog.py:49-51`

**Issue:** Step 2 removes `".."` occurrences, and Step 3 remaps characters
outside `[A-Za-z0-9_-.]` to `"_"` — which would catch `/` and `\`. However,
the step 2 comment says ".." is removed "before charset clamp so path
separators and traversal sequences are eliminated before the allowed-set filter
runs" — but the logic is reversed: the charset clamp (step 3) is what handles
`/` and `\`, not step 2. A string like `"../etc/passwd"` becomes `".etcpasswd"`
after step 2, then `".etcpasswd"` after step 3 (the `/` is already gone), then
`"etcpasswd"` after the strip. The defence does work end-to-end, but step 2
only removes `..` and leaves bare `/` present until step 3. The comment is
misleading and a future edit that reorders steps 2 and 3 could break the
traversal defence.

**Fix:** Either add an explicit `/` and `\` removal step before the charset
clamp (making the defence independent of step ordering), or update the comment
to accurately describe the defence-in-depth layering:

```python
# Step 2a: Remove path separators explicitly (belt-and-suspenders before charset clamp)
s = name.replace("..", "").replace("/", "").replace("\\", "")
# Step 3: Remap any remaining character outside the allowed set to '_'
s = re.sub(r"[^A-Za-z0-9_\-.]", "_", s)
```


### WR-05: `browse.tab` session state written unconditionally in all three `with tab:` blocks (browse.py)

**File:** `app/pages/browse.py:530-542`

**Issue:** The three `with pivot_tab:`, `with detail_tab:`, `with chart_tab:`
blocks each unconditionally write `st.session_state["browse.tab"] = "Pivot"` /
`"Detail"` / `"Chart"`. In Streamlit, all three `with tab:` blocks run on
every rerun regardless of which tab the user is viewing. This means `browse.tab`
is always set to `"Chart"` (the last block that executes), so
`_sync_state_to_url` always writes `?tab=chart` to the URL regardless of the
active tab — the round-trip URL feature is broken for Pivot and Detail tabs.

**Fix:** The active-tab tracking should be driven by a widget key or Streamlit's
tab selection mechanism, not by unconditional assignment in every block. The
simplest correct approach for Streamlit is to track which tab triggered the
current rerun via a `st.session_state` key set only on the tab-switch event,
or to remove the tab sync entirely if it cannot be reliably tracked. If the
tab `key` parameter is used (Streamlit 1.40+ supports `key` on `st.tabs`),
that key can be read from session state.

As a minimal fix, remove the three unconditional assignments and instead rely
on the initial URL-loaded value from `_load_state_from_url`:

```python
# Remove these three lines:
# st.session_state["browse.tab"] = "Pivot"   # line 530
# st.session_state["browse.tab"] = "Detail"  # line 535
# st.session_state["browse.tab"] = "Chart"   # line 539
```

---

## Info

### IN-01: Duplicate `@st.cache_resource` factory — `_get_db_adapter` defined in both `streamlit_app.py` and `browse.py`

**File:** `app/pages/browse.py:37-50` and `streamlit_app.py:37-52`

**Issue:** Two separate `@st.cache_resource` functions with identical logic
(`_get_db_adapter` in browse.py and `get_db_adapter` in streamlit_app.py)
both exist. Streamlit caches `@st.cache_resource` per function object, so
these two functions produce separate cache entries. The engine is constructed
twice when both are called for the same `db_name`. This is not a correctness
bug (both functions return equivalent adapters), but it wastes a DB connection
and makes the codebase harder to maintain.

**Fix:** Extract the shared factory into a dedicated module (e.g.,
`app/adapters/db/factory.py`) and import it in both files, or have `browse.py`
import `get_db_adapter` from `streamlit_app.py` (though that creates a module
dependency that may be uncomfortable). The cleanest resolution is a shared
helper in the adapters package.


### IN-02: Unused import `build_llm_adapter` retained in `settings.py`

**File:** `app/pages/settings.py:26`

**Issue:** `from app.adapters.llm.registry import build_adapter as build_llm_adapter`
is imported but never used. The inline comment says "unused in Phase 1 Test
helper; retained for Phase 2" — this is intentional scaffolding, but it will
cause `ruff` lint warnings and can confuse readers about what is actually active.

**Fix:** Either remove the import and re-add it in Phase 2, or suppress the
lint warning explicitly:

```python
from app.adapters.llm.registry import build_adapter as build_llm_adapter  # noqa: F401 — Phase 2
```


### IN-03: No test for `_sanitize_filename` in export_dialog.py

**File:** `app/components/export_dialog.py:30-59`

**Issue:** `_sanitize_filename` is a security-relevant function (path-traversal
defence, T-07-01/02) with seven explicit rules and multiple edge cases. It has
no corresponding unit test. Given the known risk of step-ordering bugs (see
WR-04) and the safety importance of the function, a test covering at minimum
`None`, `".."`, path traversal sequences, empty-after-strip, and the 128-char
truncation is warranted.

**Fix:** Add a test file `tests/components/test_export_dialog.py` with
parametrized cases:

```python
import pytest
from app.components.export_dialog import _sanitize_filename

@pytest.mark.parametrize("inp, expected", [
    (None,               "ufs_export"),
    ("",                 "ufs_export"),
    ("..",               "ufs_export"),
    ("../etc/passwd",    "etcpasswd"),
    ("../../secret",     "secret"),
    ("valid_name",       "valid_name"),
    ("a" * 200,          "a" * 128),
    ("..foo..",          "foo"),
])
def test_sanitize_filename(inp, expected):
    assert _sanitize_filename(inp) == expected
```


### IN-04: `requirements.txt` pins `pandas>=3.0` without upper bound

**File:** `requirements.txt:5`

**Issue:** `pandas>=3.0` has no upper bound. A future `pandas>=4.0` release
with breaking changes (string dtype API changes are already in motion in
pandas' roadmap) could break the `pd.StringDtype` handling, `pd.NA` semantics,
or the `pd.read_sql_query` signature without warning. The CLAUDE.md
architecture table recommends targeting pandas 3.x idioms.

**Fix:** Add an upper-bound pin consistent with the tested version:

```
pandas>=3.0,<4.0
```

This is low urgency (pandas 4 does not exist yet) but is a good hygiene
practice consistent with how `sqlalchemy`, `streamlit`, and `pydantic-ai` are
already pinned.

---

_Reviewed: 2026-04-23T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
