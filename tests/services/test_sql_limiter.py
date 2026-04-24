"""Tests for app.services.sql_limiter — SAFE-03.

TDD RED phase: tests written before implementation exists.
Import will fail with ModuleNotFoundError until app/services/sql_limiter.py is created.

Covers:
  - No LIMIT present → append LIMIT {row_cap}
  - Trailing semicolon → stripped before inspection
  - LIMIT present > row_cap → clamped to row_cap
  - LIMIT present < row_cap → left unchanged
  - LIMIT present == row_cap → left unchanged
  - Case-insensitive LIMIT keyword detection
  - Idempotency: calling twice gives same result (Pitfall 5 — no LIMIT 200 LIMIT 200)
  - Trailing whitespace handled correctly
"""
from __future__ import annotations

import pytest

from app.services.sql_limiter import inject_limit


class TestNoLimitPresent:
    def test_appends_limit(self):
        result = inject_limit("SELECT * FROM x", 200)
        assert result == "SELECT * FROM x LIMIT 200"

    def test_trailing_whitespace_stripped(self):
        result = inject_limit("SELECT * FROM x  ", 200)
        assert result == "SELECT * FROM x LIMIT 200"


class TestSemicolonStripping:
    def test_semicolon_stripped_then_limit_appended(self):
        result = inject_limit("SELECT * FROM x;", 200)
        assert result == "SELECT * FROM x LIMIT 200"

    def test_semicolon_with_whitespace_stripped(self):
        result = inject_limit("SELECT * FROM x ;", 200)
        assert result == "SELECT * FROM x LIMIT 200"


class TestLimitClamping:
    def test_limit_above_cap_is_clamped(self):
        result = inject_limit("SELECT * FROM x LIMIT 500", 200)
        assert result == "SELECT * FROM x LIMIT 200"

    def test_limit_below_cap_unchanged(self):
        result = inject_limit("SELECT * FROM x LIMIT 50", 200)
        assert result == "SELECT * FROM x LIMIT 50"

    def test_limit_at_cap_unchanged(self):
        result = inject_limit("SELECT * FROM x LIMIT 200", 200)
        assert result == "SELECT * FROM x LIMIT 200"


class TestCaseInsensitivity:
    def test_lowercase_limit_detected(self):
        """Case-insensitive LIMIT detection — result must have exactly one LIMIT."""
        result = inject_limit("select * from x limit 500", 200)
        # The value must be clamped; there must be exactly one LIMIT occurrence
        import re
        matches = re.findall(r"\bLIMIT\b", result, re.IGNORECASE)
        assert len(matches) == 1
        assert "200" in result

    def test_mixed_case_limit_detected(self):
        result = inject_limit("SELECT * FROM x Limit 999", 200)
        import re
        matches = re.findall(r"\bLIMIT\b", result, re.IGNORECASE)
        assert len(matches) == 1
        assert "200" in result


class TestIdempotency:
    def test_double_call_no_double_limit(self):
        """Pitfall 5: calling inject_limit twice must NOT produce 'LIMIT 200 LIMIT 200'."""
        first = inject_limit("SELECT * FROM x", 200)
        second = inject_limit(first, 200)
        assert first == second
        # Explicitly check there is exactly one LIMIT token
        import re
        assert len(re.findall(r"\bLIMIT\b", second, re.IGNORECASE)) == 1

    def test_triple_call_idempotent(self):
        first = inject_limit("SELECT * FROM x", 200)
        second = inject_limit(first, 200)
        third = inject_limit(second, 200)
        assert first == second == third
