"""Tests for app.services.sql_validator — SAFE-02.

TDD RED phase: all tests are written before the implementation exists.
The import of validate_sql / ValidationResult must fail with ImportError/ModuleNotFoundError
until app/services/sql_validator.py is created (GREEN).

Covers:
  - Single valid SELECT on allowed table → ok=True
  - SELECT with WHERE / ORDER BY / LIMIT → ok=True
  - Subquery SELECT → ok=True
  - Case-insensitive table name → ok=True
  - Multi-statement (SELECT; SELECT) → ok=False
  - Multi-statement (SELECT; DROP) → ok=False  (Pitfall 4 — count-based check)
  - Non-SELECT: DROP TABLE → ok=False
  - Non-SELECT: INSERT → ok=False
  - Non-SELECT: UPDATE → ok=False
  - Non-SELECT: DELETE → ok=False
  - Line comment (--) → ok=False
  - Block comment (/*  */) → ok=False
  - Disallowed table → ok=False with reason containing "Disallowed" and table name
  - IdentifierList (ufs_data, other_table) → ok=False
  - Empty string → ok=False
  - Whitespace-only string → ok=False
"""
from __future__ import annotations

import pytest

from app.services.sql_validator import ValidationResult, validate_sql

ALLOWED = ["ufs_data"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ok(sql: str) -> ValidationResult:
    return validate_sql(sql, ALLOWED)


def rej(sql: str) -> ValidationResult:
    return validate_sql(sql, ALLOWED)


# ---------------------------------------------------------------------------
# Happy paths — ok=True
# ---------------------------------------------------------------------------

class TestValidSelectAccepted:
    def test_simple_select(self):
        result = ok("SELECT * FROM ufs_data")
        assert result.ok is True

    def test_select_with_where_order_limit(self):
        result = ok(
            "SELECT Item, Result FROM ufs_data WHERE PLATFORM_ID='foo' ORDER BY Item LIMIT 100"
        )
        assert result.ok is True

    def test_select_with_join_on_same_table(self):
        """Self-join is allowed because the same allowed table appears twice."""
        sql = (
            "SELECT a.Item, b.Result FROM ufs_data AS a "
            "JOIN ufs_data AS b ON a.PLATFORM_ID = b.PLATFORM_ID"
        )
        result = ok(sql)
        assert result.ok is True

    def test_subquery_select(self):
        sql = "SELECT * FROM (SELECT Item, Result FROM ufs_data) AS sub"
        result = ok(sql)
        assert result.ok is True

    def test_case_insensitive_table_name_upper(self):
        result = ok("SELECT * FROM UFS_DATA")
        assert result.ok is True

    def test_case_insensitive_table_name_mixed(self):
        result = ok("SELECT * FROM Ufs_Data")
        assert result.ok is True


# ---------------------------------------------------------------------------
# Multi-statement rejection — Pitfall 4
# ---------------------------------------------------------------------------

class TestMultiStatementRejected:
    def test_two_selects(self):
        result = rej("SELECT 1; SELECT 2")
        assert result.ok is False
        assert "single" in result.reason.lower()

    def test_select_then_drop(self):
        """Pitfall 4: get_type() on first statement would return SELECT — must count."""
        result = rej("SELECT * FROM ufs_data; DROP TABLE ufs_data")
        assert result.ok is False


# ---------------------------------------------------------------------------
# Non-SELECT statement types → ok=False with mention of SELECT
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sql", [
    "DROP TABLE ufs_data",
    "INSERT INTO ufs_data VALUES (1, 'x')",
    "UPDATE ufs_data SET Result='y' WHERE Item='x'",
    "DELETE FROM ufs_data WHERE Item='x'",
])
def test_non_select_rejected(sql: str):
    result = validate_sql(sql, ALLOWED)
    assert result.ok is False
    assert "SELECT" in result.reason


# ---------------------------------------------------------------------------
# Comment rejection
# ---------------------------------------------------------------------------

class TestCommentsRejected:
    def test_line_comment(self):
        result = rej("SELECT * FROM ufs_data -- comment")
        assert result.ok is False
        assert "comment" in result.reason.lower()

    def test_block_comment(self):
        result = rej("SELECT /* block */ * FROM ufs_data")
        assert result.ok is False
        assert "comment" in result.reason.lower()


# ---------------------------------------------------------------------------
# Disallowed table names
# ---------------------------------------------------------------------------

class TestDisallowedTables:
    def test_unknown_table(self):
        result = rej("SELECT * FROM other_table")
        assert result.ok is False
        assert "Disallowed" in result.reason
        assert "other_table" in result.reason

    def test_identifier_list_mixed(self):
        """SELECT from two tables — one allowed, one not."""
        result = rej("SELECT * FROM ufs_data, other_table")
        assert result.ok is False
        assert "other_table" in result.reason


# ---------------------------------------------------------------------------
# Edge cases — empty / whitespace SQL
# ---------------------------------------------------------------------------

class TestEmptySql:
    def test_empty_string(self):
        result = validate_sql("", ALLOWED)
        assert result.ok is False

    def test_whitespace_only(self):
        result = validate_sql("   \n\t  ", ALLOWED)
        assert result.ok is False
