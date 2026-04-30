---
status: resolved
trigger: "260430-browse-pivot-empty-row-labels: Browse pivot table renders `-` in the row-label column (PLATFORM_ID or Item) instead of values; only the leftmost index column is broken; surfaces against external DB (not in-repo demo)."
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
resolved: 2026-04-30T00:00:00Z
---

## Current Focus

hypothesis: RESOLVED — root cause confirmed and fix verified by user in browser against external MySQL DB.
test: User confirmed (2026-04-30) that the row-label column now shows real PLATFORM_ID values instead of `-` after commit a1ee518.
expecting: n/a
next_action: session archived

## Symptoms

expected: Browse pivot row-label column shows actual PLATFORM_ID values (or Item names when swap_axes=True). Value cells render normally.
actual: Row-label column shows `-` for every row. Value columns appear correct.
errors: None — clean render, data/display defect.
reproduction: Open Browse tab against external (non-demo) MySQL DB, select platforms + items, click Run.
started: User reports surfaces specifically on external DB; in-repo SQLite demo path may mask it.

## Eliminated

- hypothesis: User's guess that `pivot_to_wide` uses `reset_index(drop=True)` removing the index column.
  evidence: app/services/ufs_service.py line 269 reads `wide = wide.reset_index()` — no `drop=True`. The function emits a column literally named "PLATFORM_ID" (or "Item" when swap_axes).
  timestamp: 2026-04-30T00:00:00Z

## Evidence

- timestamp: 2026-04-30T00:00:00Z
  checked: app/services/ufs_service.py pivot_to_wide function
  found: Line 263-269: pivot_table(index="PLATFORM_ID", columns="Item", values="Result", aggfunc="first") then reset_index() (no drop). Resulting DataFrame has a column literally named "PLATFORM_ID" as the first column.
  implication: The pivot output column name for the row label is "PLATFORM_ID" or "Item" (the variable index_col holds this string). Bug is downstream — in the route or template.

- timestamp: 2026-04-30T00:00:00Z
  checked: Knowledge base
  found: Recent resolved bug 260429-ask-tab-prompts-and-popover involved Jinja attribute quoting; no direct match but reinforces that template-side bugs in this codebase are common.
  implication: Template-layer issue is plausible.

- timestamp: 2026-04-30T00:00:00Z
  checked: app_v2/templates/browse/_grid.html (template) + app_v2/static/css/app.css line 138-143
  found: The `-` em-dash is injected by CSS rule `.pivot-table td:empty::after { content: "\2014" }`. So any empty `<td>` in the pivot table renders visually as `-`. The template line 41 cell expression is `{{ row[vm.index_col_name] | string | e if row[vm.index_col_name] is not none else "" }}`. This produces an empty `<td>` when the value is exactly `""` (empty string), since `"" is not none` is True → `"" | string | e` → `""`.
  implication: ANY empty-string value in the PLATFORM_ID column produces the `-` symptom. Demo SQLite seed has no empty PLATFORM_IDs, so the bug doesn't surface there.

- timestamp: 2026-04-30T00:00:00Z
  checked: Reproduced bug end-to-end with the actual `_grid.html` template + a DataFrame containing empty-string PLATFORM_ID rows.
  found: When df_long has any row with `PLATFORM_ID = ""`, `pivot_to_wide` keeps it (no upstream dropna for empty strings). After pivot, that row's `<td>` for PLATFORM_ID renders as `<td></td>`. CSS converts to `-`. Verified in standalone repro.
  implication: ROOT CAUSE confirmed. The user's external DB has PLATFORM_ID rows that are empty strings (or possibly whitespace-only or other "missing" sentinels — the same `is_missing` set already used by `result_normalizer` for the Result column). The demo SQLite is clean.

- timestamp: 2026-04-30T00:00:00Z
  checked: app/services/result_normalizer.py — `is_missing` and `MISSING_SENTINELS`
  found: The codebase ALREADY has a canonical "is missing" definition: None, "None", "", "N/A", "N/a", "null", "NULL", whitespace-only strings, and shell-error prefixes. But it's only applied to the `Result` column in `fetch_cells` line 213-214, not to PLATFORM_ID or Item.
  implication: Fix should reuse `is_missing` for symmetry — drop df_long rows whose index_col value is_missing(...) before pivoting. Same definition used everywhere.

## Resolution

root_cause: The Browse pivot template renders the row-label cell as `{{ row[vm.index_col_name] | string | e if ... is not none else "" }}`. An empty-string PLATFORM_ID (or Item) value passes the `is not none` check, then `"" | string | e` produces `""`, leaving the `<td>` empty. CSS rule `.pivot-table td:empty::after { content: "\2014" }` injects an em-dash for ALL empty `<td>` (intended for missing value cells but matches row-label cells too). External DBs that store empty-string or whitespace PLATFORM_IDs surface the bug; the in-repo demo SQLite seed has clean data so the bug never appears there. The user's stated guess (`reset_index(drop=True)`) was wrong — line 269 calls `wide.reset_index()` with no `drop=True`, and the column is correctly emitted; the bug is the values inside the column being empty strings, not the column being absent.

fix: In `app/services/ufs_service.py::pivot_to_wide`, filter out rows where the index column value is "missing" (per the existing `is_missing()` contract from `result_normalizer.py` — covers None, empty string, whitespace-only, and the documented MISSING_SENTINELS). Logs a WARNING with the dropped count so operators can see data-quality issues. Symmetric for both swap_axes orientations (PLATFORM_ID and Item). Mirrors the pre-existing `list_platforms` `.dropna()` pattern (line 91) so empty platforms are filtered uniformly across the picker AND the grid. When EVERY row has a missing index value, returns an empty wide DataFrame with `[index_col]` shape so the template renders an empty `<tbody>` instead of one row of em-dashes.

files_changed:
- app/services/ufs_service.py (added `is_missing` import; added missing-index-value filter + WARNING + all-missing empty-frame branch in pivot_to_wide before pivot_table call)
- tests/services/test_ufs_service.py (added 4 regression tests: empty-string drop, full sentinel set, all-missing → empty frame, swap_axes Item-side parity)

verification:
- All 537 existing tests pass (full suite green).
- 4 new regression tests pass and assert the exact symptom + fix.
- Standalone end-to-end repro: rendered the actual `_grid.html` template against a DataFrame with mixed empty/valid PLATFORM_IDs — before fix produced `<td></td>` (CSS-rendered as `-`); after fix produces `<td>P1</td>` with empty rows dropped.
- Symmetric verification for swap_axes=True (Item as index): empty Item values are also dropped.
- All-missing case: returns empty DataFrame with canonical column shape; template renders empty `<tbody>` (no `-` artifacts).
- HUMAN VERIFIED (2026-04-30): User confirmed in browser against external MySQL DB that the row-label column now shows real PLATFORM_ID values instead of `-`. No further fixes needed. Fix shipped in commit a1ee518.
