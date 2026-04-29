---
quick_id: 260429-kc1
plan: 01
status: complete
files_modified:
  - app/services/ufs_service.py
commits:
  - 747a610
---

# Quick Task 260429-kc1 — Source ufs_service Table from Settings

## Outcome

`app/services/ufs_service.py` no longer hardcodes `"ufs_data"`. The module
now reads `settings.app.agent.allowed_tables` at import time:

| Before | After |
|---|---|
| `_TABLE = "ufs_data"` | `_TABLE, _ALLOWED_TABLES = _load_table_config()` |
| `_ALLOWED_TABLES = frozenset({"ufs_data"})` | derived from `settings.app.agent.allowed_tables` |
| Magic literal in 2 places | 0 magic literals (zero `"ufs_data"` strings remain) |
| Diverges silently from agent if user edits settings.yaml | Agent + Browse/Overview share single source of truth |

The first entry of `app.agent.allowed_tables` is the primary table that
Browse and Overview SELECT against. The full list is the SAFE-01 allowlist
guard for `_safe_table()`. No fallback — `RuntimeError` at import if the
list is empty (Pydantic schema default `["ufs_data"]` covers the
"settings.yaml missing" case naturally).

## Changes

**File:** `app/services/ufs_service.py` (+35 / −9)

1. Added `from app.core.config import load_settings`
2. Added `_load_table_config() -> tuple[str, frozenset[str]]` reading from settings
3. Replaced module-level `_TABLE = "ufs_data"` and `_ALLOWED_TABLES = frozenset({"ufs_data"})` literals with `_TABLE, _ALLOWED_TABLES = _load_table_config()`
4. Updated module docstring "Security notes" section: `_TABLE` is now a settings-sourced configured constant; `_safe_table` still validates against the configured allowlist
5. Updated `_safe_table` docstring to reference settings-sourced allowlist

## Verification

- ✅ `grep -F '"ufs_data"' app/services/ufs_service.py` → 0 hits
- ✅ `grep -F "'ufs_data'" app/services/ufs_service.py` → 0 hits
- ✅ `grep -F '_load_table_config' app/services/ufs_service.py` → 4 hits (1 def + 1 call + 2 docstring refs)
- ✅ `grep -F 'load_settings' app/services/ufs_service.py` → 2 hits (import + call)
- ✅ `pytest tests/services/test_ufs_service.py tests/services/test_ufs_service_core.py tests/v2/test_browse_routes.py -q` → 32 passed
- ✅ `pytest tests/ -q` → **506 passed, 2 skipped, 0 failed** (matches baseline — no regressions)

## Commits

- `747a610` — fix(quick-260429-kc1): source ufs_service _TABLE from settings.app.agent.allowed_tables

## Notes

- Settings.yaml is read once at module import. Server restart needed if
  `app.agent.allowed_tables` is edited at runtime — acceptable for a
  parameter that rarely changes.
- Pydantic's `AgentConfig.allowed_tables` field still defaults to
  `["ufs_data"]` (in `app/core/agent/config.py`). That's the schema-level
  default for when settings.yaml is entirely absent — the "no fallback"
  scope was specifically the magic literals inside `ufs_service.py`, which
  are now removed. The schema default keeps v1.0 / v2.0 startup graceful
  in test environments without `config/settings.yaml`.
- Executed inline (no agent spawn) — small, self-contained change. Atomic
  commit + quick task dir + STATE.md tracking preserved per GSD discipline.
