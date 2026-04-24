"""Path scrubber for SAFE-06 — applied to DB Result values before sending to cloud LLM.

Per D-26, this is applied inside run_sql *only when* the active LLM backend is OpenAI.
The scrub intentionally replaces every /sys/*, /proc/*, /dev/* path (including /dev/null).

Pure function — no I/O, no Streamlit, no DB.
"""
from __future__ import annotations

import re

_PATH_PATTERN = re.compile(r"/(?:sys|proc|dev)/\S*")


def scrub_paths(text: str) -> str:
    """Replace /sys/*, /proc/*, /dev/* substrings with the literal placeholder <path>.

    Args:
        text: Any string — typically a pipe-delimited result row from run_sql.

    Returns:
        The input string with all matching path substrings replaced by ``<path>``.
        Non-matching text is returned unchanged. Empty input returns empty string.
    """
    return _PATH_PATTERN.sub("<path>", text)
