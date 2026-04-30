"""Joint Validation tab orchestration — turns auto-discovered HTML pages into a
JointValidationGridViewModel.

Single source of truth for GET /overview and POST /overview/grid (D-JV-12).
Pure Python; NO FastAPI / Starlette imports here — routes (Plan 04) construct
template context dicts from the returned model. Mirrors Phase 5's
``overview_grid_service`` discipline (one orchestrator, one model, no
framework imports) — replaces it for the JV tab.

Contracts (from .planning/phases/01-overview-tab-auto-discover-platforms-from-html-files/01-CONTEXT.md):

- D-JV-02/03: source-of-truth is content/joint_validation/<numeric_id>/index.html;
  invalid folder names silently skipped at the discovery layer.
- D-JV-04: per-JV metadata sourced from the BS4 13-field extraction
  (joint_validation_parser.parse_index_html) via joint_validation_store.get_parsed_jv.
- D-JV-05: missing fields render as blank empty string "" (NOT em-dash).
  Title falls back to confluence_page_id when <h1> is missing.
- D-JV-08: get_parsed_jv is memoized by (page_id, mtime_ns) — this service
  calls it freely per request.
- D-JV-10: 12 sortable columns; default ``start desc``; tiebreaker
  ``confluence_page_id`` ASC (stable for both orders); blank start to END.
- D-JV-11: 6 popover-checklist filters (status, customer, ap_company, device,
  controller, application). Multi-filter is set membership (AND across
  columns, OR within a column).
- D-JV-15: link sanitizer ports D-OV-16 verbatim — drops dangerous schemes,
  promotes bare domains to https://.
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Module constants — public surface (exported for test invariants and Plan 04).
# ---------------------------------------------------------------------------

# 12 metadata fields from D-JV-04 (column order matches table left → right).
ALL_METADATA_KEYS: Final[tuple[str, ...]] = (
    "title", "status", "customer", "model_name", "ap_company", "ap_model",
    "device", "controller", "application", "assignee", "start", "end",
)

# Verbatim port of D-OV-16 / Phase 5 ``_DANGEROUS_LINK_SCHEMES``. The 5-tuple
# below is matched literally by Plan 06's invariant grep — do not reorder.
_DANGEROUS_LINK_SCHEMES: Final[tuple[str, ...]] = (
    "javascript:", "data:", "vbscript:", "file:", "about:",
)

# 6 filterable columns per D-JV-11 — Title, Model Name, AP Model, assignee
# (담당자), Start, End are NOT filterable.
FILTERABLE_COLUMNS: Final[tuple[str, ...]] = (
    "status", "customer", "ap_company", "device", "controller", "application",
)

# 12 sortable columns per D-JV-10.
SORTABLE_COLUMNS: Final[tuple[str, ...]] = ALL_METADATA_KEYS

# Date columns get parsed as ISO 8601 for sort; empty/malformed → END (D-JV-10).
DATE_COLUMNS: Final[tuple[str, ...]] = ("start", "end")

DEFAULT_SORT_COL: Final[str] = "start"
DEFAULT_SORT_ORDER: Final[Literal["asc", "desc"]] = "desc"


# ---------------------------------------------------------------------------
# Pydantic v2 models.
# ---------------------------------------------------------------------------


class JointValidationRow(BaseModel):
    """One row in the Joint Validation grid.

    Per D-JV-05, missing string fields default to ``""`` (blank) — NOT
    the Phase 5 ``"—"`` em-dash sentinel and NOT ``None``. The template
    renders ``""`` cells as visually empty.

    ``link`` is the exception — it is sanitized at the service layer
    (D-JV-15 ports D-OV-16 verbatim). ``None`` signals "no usable link"
    so the template renders the Report Link button in its disabled state.
    """

    confluence_page_id: str = Field(..., pattern=r"^\d+$")
    title: str = ""
    status: str = ""
    customer: str = ""
    model_name: str = ""
    ap_company: str = ""
    ap_model: str = ""
    device: str = ""
    controller: str = ""
    application: str = ""
    assignee: str = ""
    start: str = ""
    end: str = ""
    link: str | None = None


class JointValidationGridViewModel(BaseModel):
    """View model returned by ``build_joint_validation_grid_view_model``."""

    rows: list[JointValidationRow]
    filter_options: dict[str, list[str]]      # keys = FILTERABLE_COLUMNS
    active_filter_counts: dict[str, int]      # keys = FILTERABLE_COLUMNS
    sort_col: str
    sort_order: Literal["asc", "desc"]
    total_count: int


# ---------------------------------------------------------------------------
# Helpers — module-private. Verbatim ports from Phase 5 grid service.
# ---------------------------------------------------------------------------


def _sanitize_link(raw: str | None) -> str | None:
    """Coerce a parsed ``link`` value to a safe http(s) URL or None.

    Verbatim port of ``app_v2/services/overview_grid_service.py:130-159``
    (D-OV-16). Plan 06 will run an invariant grep to confirm the
    ``_DANGEROUS_LINK_SCHEMES`` tuple is byte-equal.

    Contract:
      - None / empty / whitespace      → None
      - Dangerous scheme prefix        → None  (javascript:, data:, vbscript:,
                                                file:, about: — case-insensitive)
      - Already http:// or https://    → returned verbatim (trimmed)
      - Protocol-relative ``//host``   → ``https://host``
      - Anything else (e.g. ``www.x``,
        ``naver.com``)                 → ``https://`` prefix added

    Returning None signals "no usable link" so the template renders the
    button in its disabled state.
    """
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None
    lower = s.lower()
    if any(lower.startswith(scheme) for scheme in _DANGEROUS_LINK_SCHEMES):
        return None
    if lower.startswith("http://") or lower.startswith("https://"):
        return s
    if s.startswith("//"):
        return "https:" + s
    return "https://" + s


def _parse_iso_date(value: str | None) -> datetime.date | None:
    """Parse ISO 8601 ``YYYY-MM-DD``. Return None on any malformed input.

    Verbatim port of ``app_v2/services/overview_grid_service.py:162-172``.
    Used for date column sort (D-JV-10). None/empty/non-string → None.
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

    Verbatim port of ``app_v2/services/overview_grid_service.py:175-189``
    (T-05-03-01 mitigation pattern).  ``sort_col`` is hard-whitelisted
    against ``SORTABLE_COLUMNS`` BEFORE it ever reaches
    ``getattr(row, sort_col)``, so dunder attributes (``__class__``,
    ``__init__``) cannot be reached.
    """
    col = sort_col if sort_col in SORTABLE_COLUMNS else DEFAULT_SORT_COL
    order: Literal["asc", "desc"] = (
        sort_order if sort_order in ("asc", "desc") else DEFAULT_SORT_ORDER
    )
    return col, order


def _normalize_filters(
    filters: dict[str, list[str]] | None,
) -> dict[str, list[str]]:
    """Strip filters to FILTERABLE_COLUMNS subset; convert None to {}.

    Verbatim port of ``app_v2/services/overview_grid_service.py:192-210``.
    Drops empty / whitespace-only filter values so ``active_filter_counts``
    and the row-matching predicate stay honest.
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
    rows: list[JointValidationRow],
    sort_col: str,
    sort_order: Literal["asc", "desc"],
) -> list[JointValidationRow]:
    """Sort rows so empties always go to END regardless of asc/desc.

    Verbatim port of ``app_v2/services/overview_grid_service.py:213-276``
    (D-JV-10 / D-OV-07 + D-OV-08). Type annotation changed from
    ``OverviewRow`` to ``JointValidationRow``; tiebreaker key changed from
    ``r.platform_id`` to ``r.confluence_page_id``.

    Algorithm (two-pass stable sort):

    1. Partition rows into ``non_empty`` and ``empty`` by the primary sort key
       (date columns: ``_parse_iso_date`` returning None means empty;
       non-date columns: empty-string means empty — note JV uses ``""``
       blank instead of Phase 5's ``None``).
    2. Sort ``non_empty`` by ``confluence_page_id`` ASC FIRST (stable secondary).
    3. Re-sort by primary key with ``reverse=(sort_order=='desc')``.
    4. Sort ``empty`` by ``confluence_page_id`` ASC always.
    5. Concatenate ``non_empty + empty`` so empties stay at END regardless
       of primary sort order.
    """
    is_date = sort_col in DATE_COLUMNS
    non_empty: list[JointValidationRow] = []
    empty: list[JointValidationRow] = []
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

    # Pass 1: stable order by confluence_page_id ASC (the tiebreaker).
    non_empty.sort(key=lambda r: r.confluence_page_id)

    # Pass 2: sort by primary key with reverse for desc. Python sort is
    # stable, so equal primary keys preserve the page_id ASC order.
    reverse = sort_order == "desc"
    if is_date:
        non_empty.sort(
            key=lambda r: _parse_iso_date(getattr(r, sort_col)),
            reverse=reverse,
        )
    else:
        non_empty.sort(
            key=lambda r: (getattr(r, sort_col) or "").lower(),
            reverse=reverse,
        )

    # Empty group: always confluence_page_id ASC, regardless of primary order.
    empty.sort(key=lambda r: r.confluence_page_id)
    return non_empty + empty


# ---------------------------------------------------------------------------
# Public orchestrator.
# ---------------------------------------------------------------------------


def build_joint_validation_grid_view_model(
    jv_root: Path,
    filters: dict[str, list[str]] | None = None,
    sort_col: str | None = None,
    sort_order: Literal["asc", "desc"] | None = None,
) -> JointValidationGridViewModel:
    """Pure orchestrator: discover + parse → build rows → filter → sort.

    Replaces ``app_v2/services/overview_grid_service.build_overview_grid_view_model``:
    - Source loop changes: per-pid frontmatter loop becomes per-discovered-jv
      parsed-metadata loop (joint_validation_store.discover_joint_validations
      + get_parsed_jv).
    - Em-dash sentinel removed (D-JV-05 — blank "" everywhere).
    - has_content / has_content_map removed (every JV has index.html, or
      it's filtered out at discovery).
    - link is sanitized via _sanitize_link before row construction.
    - Title falls back to confluence_page_id when parsed.title == "" (D-JV-05).

    Args:
        jv_root: filesystem path to ``content/joint_validation/`` (tests
            inject ``tmp_path``; production routes pass JV_ROOT).
        filters: ``dict[col, list[selected values]]`` — multi-filter; ``None``
            and empty dicts are equivalent.
        sort_col: one of ``SORTABLE_COLUMNS``; falls back to ``"start"``
            on invalid / None input.
        sort_order: ``"asc"`` or ``"desc"``; falls back to ``"desc"``
            on invalid / None input.

    Returns:
        ``JointValidationGridViewModel`` carrying rows + filter_options +
        active_filter_counts + resolved sort_col/sort_order + total_count.

    Performance: O(N) ``get_parsed_jv`` calls + O(N log N) sort. Per-JV
    parsing memoized by ``(page_id, mtime_ns)`` (D-JV-08), so steady-state
    cost is dominated by the sort + the directory glob.
    """
    # Local import to avoid a circular import at module load time
    # (joint_validation_store imports joint_validation_parser; this module
    # is the only consumer that depends on the store module).
    from app_v2.services.joint_validation_store import (
        discover_joint_validations,
        get_parsed_jv,
    )

    col, order = _validate_sort(sort_col, sort_order)
    clean_filters = _normalize_filters(filters)

    # 1) Build all rows from parsed JV metadata.
    all_rows: list[JointValidationRow] = []
    for page_id, idx_path in discover_joint_validations(jv_root):
        parsed = get_parsed_jv(page_id, idx_path)
        all_rows.append(JointValidationRow(
            confluence_page_id=page_id,
            title=parsed.title or page_id,        # D-JV-05 fallback
            status=parsed.status,
            customer=parsed.customer,
            model_name=parsed.model_name,
            ap_company=parsed.ap_company,
            ap_model=parsed.ap_model,
            device=parsed.device,
            controller=parsed.controller,
            application=parsed.application,
            assignee=parsed.assignee,
            start=parsed.start,
            end=parsed.end,
            link=_sanitize_link(parsed.link or None),
        ))

    # 2) Build filter_options across ALL rows (NOT the filtered subset) —
    #    picker dropdowns must show every available option so users can
    #    expand selection. Same Phase 5 invariant.
    filter_options: dict[str, list[str]] = {}
    for col_name in FILTERABLE_COLUMNS:
        values: set[str] = set()
        for r in all_rows:
            v = getattr(r, col_name)
            if v is None or v == "":
                continue
            values.add(v)
        filter_options[col_name] = sorted(values, key=str.lower)

    # 3) Apply filters (AND across columns, OR within a column) — D-JV-11.
    def _row_matches(r: JointValidationRow) -> bool:
        for fcol, selected in clean_filters.items():
            if getattr(r, fcol, None) not in selected:
                return False
        return True

    filtered_rows = [r for r in all_rows if _row_matches(r)]

    # 4) Sort filtered rows (D-JV-10 — empties to END).
    sorted_rows = _sort_rows(filtered_rows, col, order)

    # 5) Active filter counts (always present for all 6 keys).
    active_filter_counts = {
        c: len(clean_filters.get(c, [])) for c in FILTERABLE_COLUMNS
    }

    return JointValidationGridViewModel(
        rows=sorted_rows,
        filter_options=filter_options,
        active_filter_counts=active_filter_counts,
        sort_col=col,
        sort_order=order,
        total_count=len(sorted_rows),
    )
