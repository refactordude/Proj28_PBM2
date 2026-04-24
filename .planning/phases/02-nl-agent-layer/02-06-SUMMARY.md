---
phase: "02-nl-agent-layer"
plan: "06"
subsystem: ask-page-onboarding
tags: [streamlit, ask-page, starter-prompts, yaml, ONBD-01, ONBD-02]
dependency_graph:
  requires: [02-04]
  provides:
    - config/starter_prompts.example.yaml (8 curated UFS prompts committed as template)
    - app/pages/ask.py load_starter_prompts() (YAML loader with fallback chain)
    - tests/pages/test_starter_prompts.py (6 loader unit tests)
  affects:
    - app/pages/ask.py _render_starter_gallery (stub replaced with YAML-driven gallery)
    - .gitignore (user-local starter_prompts.yaml added)
tech_stack:
  added: []
  patterns:
    - "load_starter_prompts() fallback chain: user yaml -> example yaml -> []"
    - "yaml.safe_load with YAMLError catch + non-dict/missing-key entry filter"
    - "Gallery capped at prompts[:8] per UI-SPEC DoS mitigation (T-02-06-05)"
    - "TDD RED/GREEN: failing ImportError tests committed before implementation"
key_files:
  created:
    - config/starter_prompts.example.yaml
    - tests/pages/test_starter_prompts.py
  modified:
    - app/pages/ask.py
    - .gitignore
decisions:
  - "load_starter_prompts() placed at module level before _DEFAULTS so it is importable by tests without Streamlit context"
  - "pathlib + yaml imports kept inside function body to avoid adding module-level imports that run at ask.py load time"
  - "Fallback chain tries user yaml first then example yaml — consistent with settings.yaml pattern (D-11)"
  - "YAMLError returns [] rather than re-raising — gallery degradation is preferable to page crash"
metrics:
  duration: "3 minutes"
  completed_date: "2026-04-24"
  tasks_completed: 2
  files_changed: 4
requirements_satisfied: [ONBD-01, ONBD-02]
---

# Phase 2 Plan 06: Starter Prompts YAML + Gallery Summary

**One-liner:** YAML-driven starter prompt gallery with 8 curated UFS prompts (3 lookup + 3 compare + 2 filter), fallback loader, and user-local override support closing ONBD-01 and ONBD-02.

## What Was Built

### config/starter_prompts.example.yaml (22 lines)

Committed template with 8 UFS-specific prompts covering the three NL query shapes from D-27:

| Shape | Count | Examples |
|-------|-------|---------|
| Lookup one platform | 3 | WriteProt status, LUN capacities, bkops settings |
| Compare across platforms | 3 | spec_version, bkops, ffu_features |
| Filter platforms by value | 2 | write protection on, purge disabled |

All 8 labels are <=40 characters. The file includes comment headers explaining the format and override mechanism.

### .gitignore

`config/starter_prompts.yaml` added after `config/auth.yaml`, following the D-11 gitignore pattern for user-local config files containing team preferences. The `.example.yaml` variant remains committed.

### app/pages/ask.py — load_starter_prompts() + gallery rewire

**Fallback chain (ONBD-02):**
1. `config/starter_prompts.yaml` (user-local, gitignored — team edits without touching committed files)
2. `config/starter_prompts.example.yaml` (committed template — works out of the box)
3. `[]` (graceful degradation — gallery simply does not render if both files are absent)

**Malformed-entry filter:** After `yaml.safe_load`, each entry is checked for `isinstance(e, dict) and "label" in e and "question" in e`. Non-dict items (bare strings) and dicts missing either key are silently dropped. This satisfies T-02-06-03 without crashing the page.

**`_render_starter_gallery` rewrite:** The 2-item `stub_prompts` list from Plan 02-04 is removed entirely. The function now:
1. Returns early if `ask.history` has any entry (gallery gives way to history panel)
2. Calls `load_starter_prompts()` — returns `[]` if YAML is absent
3. Returns early if prompts list is empty (graceful degradation)
4. Renders `st.subheader("Try asking...")` then iterates `prompts[:8]` in a 4-column grid

### tests/pages/test_starter_prompts.py (6 tests, all passing)

| Test | What it verifies |
|------|-----------------|
| `test_returns_empty_when_both_files_missing` | No files → returns [] |
| `test_falls_back_to_example` | Example file only → reads it |
| `test_user_yaml_overrides_example` | Both present → user file wins |
| `test_returns_empty_on_null_yaml` | Empty file → returns [] |
| `test_filters_out_malformed_entries` | Non-dict + missing-key entries dropped |
| `test_shipped_example_file_is_valid` | Committed example has exactly 8 valid entries, all labels <=40 chars |

All tests use `isolated_config` fixture (`tmp_path` + `monkeypatch.chdir`) so they never read the real `config/` directory (except the meta-test which explicitly uses `__file__.parents[2]`).

**ONBD-02 verified by:** `test_user_yaml_overrides_example` — proves that adding a `config/starter_prompts.yaml` with different content takes precedence over the example file, requiring zero code changes.

## Threat Mitigations Applied

| Threat | Mitigation |
|--------|-----------|
| T-02-06-02: XSS via label | `st.button(prompt["label"])` — Streamlit escapes button labels; no `unsafe_allow_html` |
| T-02-06-03: Malformed YAML crashes page | `yaml.YAMLError` caught → `[]`; non-dict/missing-key entries filtered |
| T-02-06-04: Gitignore bypass | `config/starter_prompts.yaml` in `.gitignore` |
| T-02-06-05: Large YAML DoS | `prompts[:8]` cap — only 8 entries rendered regardless of YAML size |

T-02-06-01 (malicious prompt via YAML) accepted per plan — same intranet filesystem trust model as `config/settings.yaml`.

## Deviations from Plan

None — plan executed exactly as written. TDD RED/GREEN cycle followed: failing tests committed at `e3d47b2` before implementation at `26c5d0a`.

## Known Stubs

None. The `stub_prompts` 2-item list from Plan 02-04 is fully replaced. All gallery content comes from YAML.

## Phase 2 Completion Note

This is the final plan in Phase 2 (02-nl-agent-layer). All 17 requirements tracked across Plans 02-01 through 02-06 are now satisfied. Phase 2 is feature-complete.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 0ccf6b4 | feat | Add starter_prompts.example.yaml with 8 curated UFS prompts |
| e3d47b2 | test | Add failing tests for load_starter_prompts (TDD RED) |
| 26c5d0a | feat | Wire load_starter_prompts() to gallery, replace 2-item stub |

## Self-Check: PASSED
