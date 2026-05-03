"""Discovery glob + mtime-keyed in-process memo for Joint Validation pages.

D-JV-02: Source of truth is content/joint_validation/<numeric_id>/index.html.
D-JV-03: Folder name MUST match ^\\d+$ AND contain a readable index.html.
         Anything else silently skipped — also serves as path-traversal backstop.
D-JV-08: Cache key (confluence_page_id, mtime_ns); bounded by len(found_pages).
         Glob NOT cached — re-glob every request so newly-dropped folders
         appear immediately (D-JV-09).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Final, Iterator

from app_v2.services.joint_validation_parser import ParsedJV, parse_index_html


JV_ROOT: Final[Path] = Path("content/joint_validation")
PAGE_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\d+$")


def discover_joint_validations(jv_root: Path = JV_ROOT) -> Iterator[tuple[str, Path]]:
    """Yield (confluence_page_id, index_html_path) for each valid JV folder.

    Valid iff:
      - Folder name matches ^\\d+$ (D-JV-03)
      - Folder contains a readable index.html (file, not directory)

    Anything else silently skipped (D-JV-03). Glob is NOT memoized
    (D-JV-08) — re-globbed every request so newly-dropped folders appear
    immediately (D-JV-09).
    """
    if not jv_root.exists():
        return
    for index_html in jv_root.glob("*/index.html"):
        page_id = index_html.parent.name
        if not PAGE_ID_PATTERN.match(page_id):
            continue
        if not index_html.is_file():
            continue
        yield page_id, index_html


# Module-level memoization dict. Mirrors Phase 5 D-OV-12 pattern at
# app_v2/services/content_store.py:_FRONTMATTER_CACHE. Bounded implicitly by
# directory size; explicit invalidation via clear_parse_cache() for tests.
_PARSE_CACHE: dict[tuple[str, int], ParsedJV] = {}


def get_parsed_jv(page_id: str, index_html: Path) -> ParsedJV:
    """Return parsed metadata; memoized by (page_id, mtime_ns).

    First call reads + parses the file; subsequent calls within the same
    mtime return the cached ParsedJV. A `touch` on the file changes mtime →
    cache miss → re-parse.
    """
    mtime_ns = index_html.stat().st_mtime_ns
    key = (page_id, mtime_ns)
    cached = _PARSE_CACHE.get(key)
    if cached is not None:
        return cached
    parsed = parse_index_html(index_html.read_bytes())
    _PARSE_CACHE[key] = parsed
    return parsed


def clear_parse_cache() -> None:
    """Empty the parse cache. Test helper only — do not call from app code."""
    _PARSE_CACHE.clear()
