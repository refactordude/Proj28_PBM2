"""Overview tab orchestration — turns curated list + filters/sort into an OverviewGridViewModel.

Single source of truth for GET /overview and POST /overview/grid (D-OV-03).
Pure Python; NO FastAPI / Starlette imports here — routes (Plan 05-04)
construct template context dicts from the returned model. Mirrors Phase 4's
``browse_service.build_view_model`` discipline (one orchestrator, one model,
no framework imports).

Contracts (from .planning/phases/05-overview-redesign/05-CONTEXT.md):

- D-OV-01/02: per-platform PM metadata sourced from YAML frontmatter on
  ``content/platforms/<pid>.md`` via ``content_store.read_frontmatter``.
- D-OV-03: this service is the single source of truth that both routes consume.
- D-OV-07: 12 sortable columns; asc → desc → asc cycle; default
  ``start desc``; tiebreaker ``platform_id`` ASC (stable for both orders).
- D-OV-08: dates expect ISO 8601 (``YYYY-MM-DD``); empty/None/malformed
  sort to END regardless of asc/desc.
- D-OV-09: ``title`` falls back to platform_id; other missing fields stay
  None on the model — template (Plan 05-05) renders None as ``—``.
- D-OV-10: ``has_content_map`` drives AI Summary disabled state (Phase 3 D-13
  preserved).
- D-OV-12: ``read_frontmatter`` is already memoized by ``(pid, mtime_ns)`` —
  this service calls it freely per request.
- D-OV-13: filters arrive as ``dict[col, list[selected values]]``; multi-filter
  is set membership (AND across columns, OR within a column).
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from app_v2.services.content_store import read_frontmatter
from app_v2.services.overview_filter import has_content_file


# ---------------------------------------------------------------------------
# Module constants — public surface (exported for test invariants and Plan 05-04).
# ---------------------------------------------------------------------------

# 12 PM fields from D-OV-01 / D-OV-02 (column order matches table left → right).
ALL_METADATA_KEYS: tuple[str, ...] = (
    "title", "status", "customer", "model_name", "ap_company", "ap_model",
    "device", "controller", "application", "assignee", "start", "end",
)

# 6 filterable columns per D-OV-13 / user lock — Title, Model Name,
# assignee (담당자), Start, End are NOT filterable.
FILTERABLE_COLUMNS: tuple[str, ...] = (
    "status", "customer", "ap_company", "device", "controller", "application",
)

# 12 sortable columns per D-OV-07.
SORTABLE_COLUMNS: tuple[str, ...] = ALL_METADATA_KEYS

# Date columns get parsed as ISO 8601 for sort; empty/malformed → END (D-OV-08).
DATE_COLUMNS: tuple[str, ...] = ("start", "end")

DEFAULT_SORT_COL: str = "start"
DEFAULT_SORT_ORDER: Literal["asc", "desc"] = "desc"


# ---------------------------------------------------------------------------
# Pydantic v2 models (D-OV-03).
# ---------------------------------------------------------------------------


class OverviewRow(BaseModel):
    """One row in the Overview pivot grid.

    Fields use ``str | None = None`` so missing frontmatter values render as
    None at the model layer; the template (Plan 05-05) renders None as the
    em-dash sentinel ``—`` (D-OV-09).

    ``title`` is the exception — D-OV-09 falls back to platform_id when
    frontmatter has no title field. The fallback is computed inside
    ``build_overview_grid_view_model`` (NOT in the model definition) so the
    model itself stays oblivious to fallback policy.
    """

    platform_id: str
    title: str
    status: str | None = None
    customer: str | None = None
    model_name: str | None = None
    ap_company: str | None = None
    ap_model: str | None = None
    device: str | None = None
    controller: str | None = None
    application: str | None = None
    assignee: str | None = None
    start: str | None = None
    end: str | None = None
    has_content: bool = False


class OverviewGridViewModel(BaseModel):
    """View model returned by ``build_overview_grid_view_model``."""

    rows: list[OverviewRow]
    filter_options: dict[str, list[str]]      # keys = FILTERABLE_COLUMNS
    active_filter_counts: dict[str, int]      # keys = FILTERABLE_COLUMNS
    sort_col: str
    sort_order: Literal["asc", "desc"]
    has_content_map: dict[str, bool]


# ---------------------------------------------------------------------------
# Helpers — module-private.
# ---------------------------------------------------------------------------


def _parse_iso_date(value: str | None) -> datetime.date | None:
    """Parse ISO 8601 ``YYYY-MM-DD``. Return None on any malformed input.

    Used for date column sort (D-OV-08). None/empty/non-string → None.
    """
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _validate_sort(
    sort_col: str | None,
    sort_order: str | None,
) -> tuple[str, Literal["asc", "desc"]]:
    """Coerce sort_col / sort_order to valid values; fall back to defaults.

    T-05-03-01 mitigation: ``sort_col`` is hard-whitelisted against
    ``SORTABLE_COLUMNS`` BEFORE it ever reaches ``getattr(row, sort_col)``,
    so dunder attributes (``__class__``, ``__init__``) cannot be reached.
    """
    col = sort_col if sort_col in SORTABLE_COLUMNS else DEFAULT_SORT_COL
    order: Literal["asc", "desc"] = (
        sort_order if sort_order in ("asc", "desc") else DEFAULT_SORT_ORDER
    )
    return col, order


def _normalize_filters(
    filters: dict[str, list[str]] | None,
) -> dict[str, list[str]]:
    """Strip filters to the FILTERABLE_COLUMNS subset; convert None to {}.

    Drops empty / whitespace-only filter values so ``active_filter_counts``
    and the row-matching predicate stay honest. T-05-03-05 mitigation —
    the ``v.strip()`` guard discards empty-string entries that would
    otherwise treat all rows as non-matching.
    """
    if not filters:
        return {}
    out: dict[str, list[str]] = {}
    for col in FILTERABLE_COLUMNS:
        values = filters.get(col) or []
        clean = [v for v in values if isinstance(v, str) and v.strip()]
        if clean:
            out[col] = clean
    return out


def _sort_rows(
    rows: list[OverviewRow],
    sort_col: str,
    sort_order: Literal["asc", "desc"],
) -> list[OverviewRow]:
    """Sort rows so empties always go to END regardless of asc/desc.

    Algorithm (two-pass stable sort, D-OV-07 + D-OV-08):

    1. Partition rows into ``non_empty`` and ``empty`` by the primary sort key
       (date columns: ``_parse_iso_date`` returning None means empty; non-date
       columns: None or empty-string means empty).
    2. Sort ``non_empty`` by ``platform_id`` ASC FIRST (this becomes the
       stable secondary order). Then re-sort by the primary key with
       ``reverse=(sort_order=='desc')``. Python's sort is stable, so the
       platform_id ASC ordering is preserved within each primary-key group —
       even when the primary key is sorted in descending order.
    3. Sort ``empty`` by ``platform_id`` ASC always.
    4. Concatenate ``non_empty + empty`` so empties stay at the END regardless
       of the primary sort order.

    The two-pass stable sort is necessary because a single
    ``sorted(rows, key=..., reverse=...)`` call would also reverse the
    secondary key (platform_id), violating the "tiebreaker always ASC"
    invariant from D-OV-07. See ``test_tiebreaker_platform_id_asc_for_both_orders``.
    """
    is_date = sort_col in DATE_COLUMNS
    non_empty: list[OverviewRow] = []
    empty: list[OverviewRow] = []
    for r in rows:
        raw = getattr(r, sort_col, None)
        if is_date:
            if _parse_iso_date(raw) is None:
                empty.append(r)
            else:
                non_empty.append(r)
        else:
            if raw is None or raw == "":
                empty.append(r)
            else:
                non_empty.append(r)

    # Pass 1: stable order by platform_id ASC (the tiebreaker).
    non_empty.sort(key=lambda r: r.platform_id)

    # Pass 2: sort by primary key with reverse for desc. Python sort is
    # stable, so equal primary keys preserve the platform_id ASC order.
    reverse = sort_order == "desc"
    if is_date:
        # _parse_iso_date is total over the non_empty subset (we filtered
        # None out above), so the key function never returns None here.
        non_empty.sort(
            key=lambda r: _parse_iso_date(getattr(r, sort_col)),
            reverse=reverse,
        )
    else:
        non_empty.sort(
            key=lambda r: (getattr(r, sort_col) or "").lower(),
            reverse=reverse,
        )

    # Empty group: always platform_id ASC, regardless of primary order.
    empty.sort(key=lambda r: r.platform_id)
    return non_empty + empty


# ---------------------------------------------------------------------------
# Public orchestrator.
# ---------------------------------------------------------------------------


def build_overview_grid_view_model(
    curated_pids: list[str],
    content_dir: Path,
    filters: dict[str, list[str]] | None = None,
    sort_col: str | None = None,
    sort_order: str | None = None,
) -> OverviewGridViewModel:
    """Pure orchestrator: read frontmatter → build rows → filter → sort.

    Args:
        curated_pids: ordered list of PLATFORM_IDs from
            ``overview_store.load_overview()``.
        content_dir: filesystem path to ``content/platforms/`` (tests inject
            ``tmp_path``; production routes pass the module-level constant).
        filters: ``dict[col, list[selected values]]`` — multi-filter; ``None``
            and empty dicts are equivalent.
        sort_col: one of ``SORTABLE_COLUMNS``; falls back to ``"start"``
            on invalid / None input.
        sort_order: ``"asc"`` or ``"desc"``; falls back to ``"desc"``
            on invalid / None input.

    Returns:
        ``OverviewGridViewModel`` carrying rows + filter_options +
        active_filter_counts + resolved sort_col/sort_order +
        has_content_map.

    Performance: O(N) ``read_frontmatter`` calls + O(N log N) sort, where
    N = len(curated_pids). ``read_frontmatter`` is memoized by
    ``(pid, mtime_ns)`` (D-OV-12), so steady-state cost is dominated by the
    sort. For curated_pids < ~100 (typical), sub-millisecond.
    """
    col, order = _validate_sort(sort_col, sort_order)
    clean_filters = _normalize_filters(filters)

    # 1) Build all rows from frontmatter (one read_frontmatter per pid).
    all_rows: list[OverviewRow] = []
    has_content_map: dict[str, bool] = {}
    for pid in curated_pids:
        fm = read_frontmatter(pid, content_dir)
        has_content = has_content_file(pid, content_dir)
        has_content_map[pid] = has_content

        # D-OV-09 — title falls back to platform_id when frontmatter is
        # missing OR title is empty. All other fields stay None on the
        # model and the template renders None as ``—``.
        title = fm.get("title") or pid

        row = OverviewRow(
            platform_id=pid,
            title=title,
            status=fm.get("status") or None,
            customer=fm.get("customer") or None,
            model_name=fm.get("model_name") or None,
            ap_company=fm.get("ap_company") or None,
            ap_model=fm.get("ap_model") or None,
            device=fm.get("device") or None,
            controller=fm.get("controller") or None,
            application=fm.get("application") or None,
            assignee=fm.get("assignee") or None,
            start=fm.get("start") or None,
            end=fm.get("end") or None,
            has_content=has_content,
        )
        all_rows.append(row)

    # 2) Build filter_options across ALL rows (NOT the filtered subset) —
    #    picker dropdowns must show every available option so users can
    #    expand selection. Narrowing on filter would create a "trapdoor" UX.
    #    See test_filter_options_use_all_rows_not_filtered_subset.
    filter_options: dict[str, list[str]] = {}
    for col_name in FILTERABLE_COLUMNS:
        values: set[str] = set()
        for r in all_rows:
            v = getattr(r, col_name)
            if v is None or v == "":
                continue
            values.add(v)
        # Sort case-insensitively for display.
        filter_options[col_name] = sorted(values, key=str.lower)

    # 3) Apply filters (AND across columns, OR within a column) — D-OV-13.
    def _row_matches(r: OverviewRow) -> bool:
        for fcol, selected in clean_filters.items():
            if getattr(r, fcol, None) not in selected:
                return False
        return True

    filtered_rows = [r for r in all_rows if _row_matches(r)]

    # 4) Sort the filtered rows (D-OV-07 / D-OV-08 — empties to END).
    sorted_rows = _sort_rows(filtered_rows, col, order)

    # 5) Active filter counts (always present for all 6 keys).
    active_filter_counts = {
        c: len(clean_filters.get(c, [])) for c in FILTERABLE_COLUMNS
    }

    return OverviewGridViewModel(
        rows=sorted_rows,
        filter_options=filter_options,
        active_filter_counts=active_filter_counts,
        sort_col=col,
        sort_order=order,
        has_content_map=has_content_map,
    )
