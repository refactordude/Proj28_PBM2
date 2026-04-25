"""Markdown content store for Phase 03 (CONTENT-01..06, D-30, D-31).

Pure functions: ``content_dir`` is always passed in (defaults to
``DEFAULT_CONTENT_DIR`` for production; tests inject ``tmp_path``). Routes
(``platforms.py``) are the only callers in Phase 03; Plan 03-03
(``summary_service``) reads via ``get_content_mtime_ns`` + ``read_content``
for cache keying.

XSS defense (Pitfall 1): ``MarkdownIt('js-default')`` only — never the default
constructor. ``js-default`` disables raw HTML passthrough, linkify, and
typographer. The output is safe to inject into a Jinja2 template via
``{{ rendered_html | safe }}``.

Path-traversal defense (D-04, Pitfall 2): ``_safe_target`` uses
``Path.resolve()`` + ``relative_to()`` to assert the candidate stays inside
``content_dir``, even though routes already regex-validate ``platform_id``
at HTTP entry. Defense in depth.
"""
from __future__ import annotations

import logging
from pathlib import Path

from markdown_it import MarkdownIt

from app_v2.data.atomic_write import atomic_write_bytes

_log = logging.getLogger(__name__)

DEFAULT_CONTENT_DIR: Path = Path("content/platforms")
# D-31 — UTF-8 byte limit, enforced inside save_content (authoritative).
# The route's Form(max_length=...) is a coarse first-line guard that counts
# codepoints, not bytes — a 65536-codepoint emoji string is ~262KB, exceeding
# this limit. save_content re-checks ``len(payload.encode("utf-8"))`` and
# raises ValueError so the route can return HTTP 413 (WR-02 fix).
MAX_CONTENT_BYTES: int = 65536

# Module-level singleton renderer. Pitfall 1: js-default disables HTML passthrough.
_MD = MarkdownIt("js-default")


def render_markdown(text: str) -> str:
    """Render user-supplied markdown to safe HTML (XSS-defended via js-default)."""
    return _MD.render(text)


def _safe_target(platform_id: str, content_dir: Path) -> Path:
    """Resolve content_dir/<pid>.md; raise ValueError if it escapes content_dir.

    Pitfall 2 / D-04 — defense-in-depth alongside the FastAPI route regex.
    """
    base = content_dir.resolve()
    candidate = (content_dir / f"{platform_id}.md").resolve()
    candidate.relative_to(base)  # raises ValueError on escape
    return candidate


def read_content(platform_id: str, content_dir: Path = DEFAULT_CONTENT_DIR) -> str | None:
    """Return UTF-8 file contents, or ``None`` if the file does not exist."""
    try:
        target = _safe_target(platform_id, content_dir)
    except ValueError:
        return None
    if not target.is_file():
        return None
    return target.read_text(encoding="utf-8")


def save_content(platform_id: str, payload: str, content_dir: Path = DEFAULT_CONTENT_DIR) -> None:
    """Atomically write ``payload`` to ``content_dir/<pid>.md`` (UTF-8).

    Raises ``ValueError`` on traversal OR on byte-size overflow.

    D-31 size enforcement (WR-02 fix): the authoritative check is here, in
    bytes. The route's ``Form(max_length=65536)`` is a coarse codepoint-count
    pre-filter — a 65536-codepoint emoji payload is ~262KB on disk, which
    would silently violate D-31 if save_content did not re-check. Callers
    (the route) catch ``ValueError`` and return HTTP 413.
    """
    encoded = payload.encode("utf-8")
    if len(encoded) > MAX_CONTENT_BYTES:
        raise ValueError(
            f"Content exceeds {MAX_CONTENT_BYTES}-byte limit "
            f"({len(encoded)} bytes)"
        )
    target = _safe_target(platform_id, content_dir)
    # default_mode=0o644 — content files are world-readable on the shared
    # intranet (T-03-01-05 accepted in Plan 03-01).
    atomic_write_bytes(target, encoded, default_mode=0o644)


def delete_content(platform_id: str, content_dir: Path = DEFAULT_CONTENT_DIR) -> bool:
    """Delete ``content_dir/<pid>.md`` if present.

    Returns ``True`` if the file was deleted, ``False`` if it did not exist
    (idempotent — does not raise on missing).
    """
    try:
        target = _safe_target(platform_id, content_dir)
    except ValueError:
        return False
    try:
        target.unlink()
        return True
    except FileNotFoundError:
        return False


def get_content_mtime_ns(platform_id: str, content_dir: Path = DEFAULT_CONTENT_DIR) -> int | None:
    """Return ``Path.stat().st_mtime_ns`` (integer nanoseconds) or ``None`` if missing.

    Pitfall 13: ns precision avoids sub-second cache-key collisions on
    filesystems that round mtime to whole seconds.
    """
    try:
        target = _safe_target(platform_id, content_dir)
    except ValueError:
        return None
    try:
        return target.stat().st_mtime_ns
    except FileNotFoundError:
        return None
