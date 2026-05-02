# Quick Task 260502-jb2 — Summary

**Description:** Add fake joint validation fixture folders to stress-test JV grid with 20+ results
**Date:** 2026-05-02
**Status:** Complete

## What was built

Created 16 new fake `index.html` fixtures under `content/joint_validation/` with distinct numeric IDs in the `319386910x`–`319386917x` range (step of 5). Total fixture count is now **22**, which exceeds the `JV_PAGE_SIZE=15` threshold and forces the grid into a real two-page state (page 1 = 15 tiles, page 2 = 7 tiles).

**New folders:**
3193869100, 3193869105, 3193869110, 3193869115, 3193869120, 3193869125, 3193869130, 3193869135, 3193869140, 3193869145, 3193869150, 3193869155, 3193869160, 3193869165, 3193869170, 3193869175.

Existing six fixtures (3193868109, 3193868200, 3193868300, 3193868400, 3193868500, 3193868600) untouched.

## Variety injected to expose grid issues

| Dimension          | Values now present in the dataset                                                                                                                                              |
|--------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Status**         | Blocked, Cancelled, Completed, In Progress, On Hold, Pending, Planned                                                                                                           |
| **Customer**       | Apple, Garmin, Google, Honor, Huawei, Hyundai, Nothing, OnePlus, OPPO, Realtek, Samsung, Sony, Tesla, Vivo, Xiaomi (15 distinct → tests filter-popover scroll/density)         |
| **AP Company**     | Apple, Custom, Google, HiSilicon, MediaTek, NXP, Qualcomm, Realtek                                                                                                              |
| **Device**         | UFS 2.2, UFS 3.1, UFS 4.0                                                                                                                                                       |
| **Controller**     | 19 distinct firmware strings (FW v1.4.0 → FW v3.2.0-rc2) — exercises overflow in the Controller filter popover                                                                  |
| **Application**    | Auto, Automotive, IoT, Smartphone, Tablet, Wearable                                                                                                                             |
| **Title length**   | 1-word ("Nothing Phone (3) UFS 4.0") through 80+ chars (OnePlus 12 long-title fixture); also one emoji title (🍎) and one fixture with no `<h1>` so the title falls back to id |
| **Date coverage**  | One fixture (3193869115) has no End date → exercises the "empties to END" sort path in `_sort_rows`                                                                             |
| **Empty fields**   | 3193869160 omits Model Name, AP Company, AP Model, Device, Controller, Start, End — exercises the blank-cell render path (D-JV-05)                                              |
| **Link sanitizer** | 3193869140 uses `javascript:alert(1)` → sanitizer drops to `None` (disabled button); 3193869160 uses bare `naver.com` → promoted to `https://naver.com`                          |

## Verification

- `find content/joint_validation -name index.html | wc -l` → **22**
- All new folder names match `^\d+$` (joint_validation_store regex requirement, D-JV-03)
- BeautifulSoup parses every fixture without error
- Live `build_joint_validation_grid_view_model` smoke check:
  - page 1: `total_count=22 page_count=2 rows=15`
  - page 2: `rows=7`
  - 3193869140 title falls back to `'3193869140'`, `link=None` (sanitizer dropped `javascript:`)
  - 3193869160 link sanitized to `https://naver.com`
- `pytest -q tests/v2/test_jv_pagination.py tests/v2/test_joint_validation_routes.py tests/v2/test_joint_validation_grid_service.py tests/v2/test_joint_validation_store.py tests/v2/test_joint_validation_parser.py` → **75 passed**

## Files changed

- `.planning/quick/260502-jb2-add-fake-joint-validation-fixture-folder/260502-jb2-PLAN.md` (new)
- `.planning/quick/260502-jb2-add-fake-joint-validation-fixture-folder/260502-jb2-SUMMARY.md` (new)
- `.planning/STATE.md` (Quick Tasks Completed table row added)
- `content/joint_validation/3193869{100,105,110,115,120,125,130,135,140,145,150,155,160,165,170,175}/index.html` (16 new fixtures)

## What this enables

Loading `/overview` in the browser now exercises:
- the page-link strip and page-2 navigation
- filter-popover scrolling when a column has many distinct values (Customer, Controller)
- tile wrapping with very long titles
- title fallback rendering when `<h1>` is missing
- disabled-state Report Link button when the parsed href is dangerous
- empties-to-END behavior when sorting by End date
