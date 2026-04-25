"""Tests for app_v2.services.content_store — Phase 03 markdown CRUD service.

Covers:
- render_markdown XSS defense (Pitfall 1 — MarkdownIt('js-default') only)
- _safe_target path-traversal defense (D-04, Pitfall 2 — relative_to() check)
- read_content / save_content / delete_content roundtrips
- get_content_mtime_ns integer-ns precision (Pitfall 13)
- atomic_write_bytes spy (verifies save_content delegates to Plan 03-01 helper)
"""
from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# render_markdown — XSS defense via MarkdownIt('js-default')
# ---------------------------------------------------------------------------

def test_render_markdown_escapes_script_tag():
    """Raw <script> tag is escaped (js-default disables HTML passthrough)."""
    from app_v2.services.content_store import render_markdown
    out = render_markdown("<script>alert(1)</script>")
    assert "<script>" not in out.lower(), f"Unescaped <script> in output: {out!r}"


def test_render_markdown_escapes_img_onerror():
    """Raw <img onerror=...> attribute does not survive js-default rendering."""
    from app_v2.services.content_store import render_markdown
    out = render_markdown('<img src=x onerror="alert(1)">')
    # The js-default mode escapes the entire raw HTML — onerror= as a literal
    # attribute should not appear in the output.
    assert 'onerror="alert' not in out.lower(), f"Unescaped onerror= in output: {out!r}"


def test_render_markdown_rejects_javascript_uri():
    """[click](javascript:alert(1)) — markdown-it validateLink rejects javascript: scheme."""
    from app_v2.services.content_store import render_markdown
    out = render_markdown("[click](javascript:alert(1))")
    # The link href should not be a javascript: URI.
    assert 'href="javascript:' not in out.lower(), f"javascript: scheme in href: {out!r}"


def test_render_markdown_renders_basic():
    """Plain markdown still renders correctly (sanity check)."""
    from app_v2.services.content_store import render_markdown
    out = render_markdown("# Hello\n\n**bold**")
    assert "<h1>Hello</h1>" in out
    assert "<strong>bold</strong>" in out


# ---------------------------------------------------------------------------
# _safe_target — path-traversal defense (D-04, Pitfall 2)
# ---------------------------------------------------------------------------

def test_safe_target_inside_content_dir(tmp_path: Path):
    """A clean platform_id resolves inside content_dir."""
    from app_v2.services.content_store import _safe_target
    target = _safe_target("Samsung_S22_SM8450", tmp_path)
    assert target == (tmp_path / "Samsung_S22_SM8450.md").resolve()


def test_safe_target_rejects_traversal(tmp_path: Path):
    """A traversal-shaped platform_id raises ValueError (defense-in-depth)."""
    from app_v2.services.content_store import _safe_target
    with pytest.raises(ValueError):
        _safe_target("..", tmp_path)


# ---------------------------------------------------------------------------
# read_content / save_content / delete_content roundtrips
# ---------------------------------------------------------------------------

def test_read_content_returns_none_when_missing(tmp_path: Path):
    """read_content returns None when file does not exist (no exception)."""
    from app_v2.services.content_store import read_content
    assert read_content("PID1", tmp_path) is None


def test_save_then_read_roundtrip(tmp_path: Path):
    """save_content then read_content returns the same string."""
    from app_v2.services.content_store import read_content, save_content
    save_content("PID1", "# Hello", tmp_path)
    assert read_content("PID1", tmp_path) == "# Hello"


def test_save_content_uses_atomic_write(tmp_path: Path, monkeypatch):
    """save_content delegates to atomic_write_bytes (Plan 03-01 helper)."""
    import app_v2.services.content_store as cs

    calls: list[tuple] = []

    def spy(target, payload, *, default_mode=0o644):
        calls.append((target, payload, default_mode))
        # Still write so the test can verify the path on disk.
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

    monkeypatch.setattr(cs, "atomic_write_bytes", spy)
    cs.save_content("PID1", "# Hello", tmp_path)
    assert len(calls) == 1
    target, payload, default_mode = calls[0]
    assert target == (tmp_path / "PID1.md").resolve()
    assert payload == b"# Hello"
    assert default_mode == 0o644


def test_save_content_with_unicode(tmp_path: Path):
    """Korean / emoji / CJK roundtrip safely through UTF-8."""
    from app_v2.services.content_store import read_content, save_content
    text = "# 안녕\n\n한국어 + 中文 + 🎉"
    save_content("PID_unicode", text, tmp_path)
    assert read_content("PID_unicode", tmp_path) == text


def test_delete_content_returns_true_when_existed(tmp_path: Path):
    """delete_content returns True after deleting an existing file."""
    from app_v2.services.content_store import delete_content, save_content
    save_content("PID_del", "# To delete", tmp_path)
    assert delete_content("PID_del", tmp_path) is True
    assert not (tmp_path / "PID_del.md").exists()


def test_delete_content_returns_false_when_missing(tmp_path: Path):
    """delete_content returns False without raising for a missing file."""
    from app_v2.services.content_store import delete_content
    assert delete_content("NEVER_EXISTED", tmp_path) is False


# ---------------------------------------------------------------------------
# get_content_mtime_ns — integer-ns precision (Pitfall 13)
# ---------------------------------------------------------------------------

def test_get_content_mtime_ns_returns_int(tmp_path: Path):
    """get_content_mtime_ns returns a non-negative int after save."""
    from app_v2.services.content_store import get_content_mtime_ns, save_content
    save_content("PID_mtime", "# stamped", tmp_path)
    ns = get_content_mtime_ns("PID_mtime", tmp_path)
    assert isinstance(ns, int)
    assert ns >= 0


def test_get_content_mtime_ns_returns_none_when_missing(tmp_path: Path):
    """get_content_mtime_ns returns None for a missing file."""
    from app_v2.services.content_store import get_content_mtime_ns
    assert get_content_mtime_ns("NEVER_EXISTED", tmp_path) is None
