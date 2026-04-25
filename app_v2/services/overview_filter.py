"""Pure filter logic for the Overview tab curated list.

All three functions operate on already-loaded entity dicts (never on the DB) —
filters are client-side-of-the-curated-list semantics, not SQL WHERE clauses.
For < 100 curated entries, the cost is negligible.

Path traversal defense (Pitfall 2): has_content_file resolves the candidate path
and asserts it stays inside the content/platforms directory. Even though routes
(Plan 02-02) already regex-validate PLATFORM_IDs at HTTP entry, this function is
called here with in-process values that include the file-suffix concatenation, so
a redundant check at the filesystem boundary is correct defense in depth.

Contracts:
- apply_filters(entities, brand, soc, year, has_content, content_dir) -> list[dict]
- count_active_filters(brand, soc, year, has_content) -> int
- has_content_file(platform_id, content_dir) -> bool

Year-None semantics (D-21):
- Year filter inactive (None / "" / "None") → entities with year=None ARE INCLUDED
- Year filter active (e.g. 2022) → entities with year=None are EXCLUDED
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

_log = logging.getLogger(__name__)


def count_active_filters(
    brand: str | None,
    soc: str | None,
    year: str | None,
    has_content: bool | None,
) -> int:
    """Return the count of non-default (active) filter dimensions.

    Empty string and None are both treated as inactive (matches HTML form semantics
    where the "All …" option carries value="").
    """
    count = 0
    if brand:
        count += 1
    if soc:
        count += 1
    if year:
        count += 1
    if has_content:
        count += 1
    return count


def has_content_file(platform_id: str, content_dir: Path) -> bool:
    """Return True iff content_dir/<platform_id>.md exists as a regular file.

    Path traversal defense (Pitfall 2): resolve the candidate AND the base, then
    require the candidate be inside the base via Path.relative_to(). Any exception
    or traversal attempt returns False (never raises).
    """
    try:
        base = content_dir.resolve()
        candidate = (content_dir / f"{platform_id}.md").resolve()
        # Pitfall 2: candidate MUST be inside base. relative_to raises ValueError otherwise.
        candidate.relative_to(base)
        return candidate.is_file()
    except (ValueError, OSError) as exc:
        _log.debug("has_content_file rejected %r: %s", platform_id, exc)
        return False


def apply_filters(
    entities: Iterable[dict],
    brand: str | None,
    soc: str | None,
    year: str | int | None,
    has_content: bool | None,
    content_dir: Path,
) -> list[dict]:
    """Return entities matching all active filters (AND semantics).

    Args:
        entities: iterable of dicts with keys platform_id, brand, soc_raw, year.
        brand: exact-match brand filter; None/"" disables this dimension.
        soc: exact-match soc_raw filter; None/"" disables this dimension.
        year: year filter accepted as int OR str (HTML forms always send strings).
            None / "" / "None" disable this dimension. Unparseable strings are
            treated as a sentinel that matches no entity (safer than ignoring).
        has_content: when True, require content_dir/<platform_id>.md exists.
        content_dir: pathlib.Path base for has_content stat checks.

    Year filtering (D-21): entities with year=None are INCLUDED when year filter
    is inactive; EXCLUDED when year filter is active and does not match.
    """
    # Normalize year to int for comparison, accepting str (HTML form) or int.
    year_int: int | None
    if year in (None, "", "None"):
        year_int = None
    else:
        try:
            year_int = int(year)
        except (ValueError, TypeError):
            # Unknown/malformed year value — treat as no-match (empty result is safer
            # than ignoring the filter; user sees zero-results state and can clear).
            year_int = -1  # sentinel impossible year

    result: list[dict] = []
    for e in entities:
        if brand and e.get("brand") != brand:
            continue
        if soc and e.get("soc_raw") != soc:
            continue
        if year_int is not None:
            # D-21: entity.year==None is excluded when user selected a specific year.
            if e.get("year") != year_int:
                continue
        if has_content and not has_content_file(e.get("platform_id", ""), content_dir):
            continue
        result.append(e)
    return result
