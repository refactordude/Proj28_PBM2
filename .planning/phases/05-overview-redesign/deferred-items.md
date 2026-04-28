# Phase 05 Deferred Items

## Legacy tests broken by Plan 05-05 (resolution: Plan 05-06)

Plan 05-05 deliberately deletes `_entity_row.html` and `_filter_alert.html`
per D-OV-05, replacing the `<li>` row layout with the sortable Bootstrap
table in `_grid.html`. Plan 05-04 removed `POST /overview/filter`,
`POST /overview/filter/reset`, and `DELETE /overview/{pid}` per D-OV-04.

The following pre-Phase-5 tests assert the legacy markup/routes and now
fail. Plan 05-06 (Wave 4) is the documented follow-on that rewrites the
v2 overview test surface for the redesigned templates and routes.

### tests/v2/test_overview_filter.py (11 failures)
- test_post_filter_brand_samsung_narrows_to_samsung_entities
- test_post_filter_soc_narrows_by_soc_raw
- test_post_filter_year_2022_excludes_year_none_entity
- test_post_filter_empty_year_includes_year_none_entity
- test_post_filter_multiple_filters_apply_and_semantics
- test_post_filter_zero_matches_returns_no_platforms_match_copy
- test_post_filter_response_is_fragment_not_full_page
- test_post_filter_response_contains_oob_badge_with_active_count
- test_post_filter_has_content_true_narrows_to_entities_with_md_file
- test_post_filter_reset_returns_full_list_with_count_zero_badge
- test_post_filter_regression_add_and_delete_still_work
- test_post_filter_no_active_filters_returns_all_entities

Reason: targets `POST /overview/filter` and `POST /overview/filter/reset`
which were removed by Plan 05-04. Plan 05-06 introduces equivalent
coverage for `POST /overview/grid`.

### tests/v2/test_overview_routes.py (9 failures)
- test_get_root_contains_filter_block
- test_post_add_happy_path_returns_200_with_entity_row_fragment
- test_post_add_pixel_returns_year_badge
- test_post_add_duplicate_returns_409_with_warning_alert
- test_post_add_unknown_platform_returns_404_with_danger_alert
- test_delete_existing_returns_200_empty_body
- test_get_root_after_add_shows_entity_row_with_correct_badges
- test_get_root_ai_summary_button_disabled

Reasons:
- `_entity_row.html` markup (badges, brand/SoC/year, ai-btn ms-2 classes)
  removed by Plan 05-05 per D-OV-05 (replaced by Bootstrap table cells)
- `<details>` filter block replaced by 6 popover-checklist multi-filters
- `DELETE /overview/{pid}` removed by Plan 05-04 (D-OV-04 — Remove
  button gone per user lock)
- POST /overview/add now returns plain-text Response on 4xx (Plan 05-04)
  not the legacy alert template
- POST /overview/add success returns 200 + HX-Redirect: /overview, not
  the entity_row fragment swap

Plan 05-06 will rewrite these tests against the new sortable-table /
6-popover surface.

### tests/v2/test_content_routes.py (2 failures)
- test_overview_row_ai_button_disabled_when_no_content
- test_overview_row_ai_button_enabled_when_content_exists

Reason: assert `class="ai-btn ms-2"` (Phase 3 `<li>`-level utility class).
The Phase 5 `_grid.html` AI Summary button uses
`class="btn btn-sm btn-outline-primary ai-btn"` (no `ms-2`) because the
cell layout is a table cell, not a flex `<li>`. The Phase 3 SUMMARY-02
contract on hx-post / hx-target / hx-disabled-elt / disabled+title is
preserved verbatim — only the surrounding utility class is gone.

Plan 05-06 will update these two tests to assert the new button class
prefix while keeping the SUMMARY-02 contract assertions intact.

### Out-of-scope confirmation
- Phase 4 byte-stability: PASS — 30/30 in
  `tests/v2/test_browse_routes.py` + `tests/v2/test_phase04_invariants.py`
- Plan 05-02 frontmatter tests: PASS — all 15 collected
- Plan 05-03 grid-service tests: PASS — all 18 collected

These 22 failures are 100% confined to test files targeting templates /
routes that the v2.0 Wave 3 plans (05-04, 05-05) deliberately delete per
the locked D-OV-04 / D-OV-05 contracts.
