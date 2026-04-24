"""LIMIT clause injector / clamper for the NL agent's run_sql tool (SAFE-03).

Pure function — assumes the caller has already passed the SQL through validate_sql.
Idempotent (Pitfall 5): calling twice with the same row_cap is a no-op after the first.

How it works:
  - Strip trailing whitespace and a single trailing semicolon.
  - If no LIMIT clause is present: append LIMIT {row_cap}.
  - If LIMIT is present with a value > row_cap: replace it with row_cap.
  - If LIMIT is present with a value <= row_cap: leave it unchanged.

The regex is case-insensitive so `limit 500` and `LIMIT 500` are both detected.
Only one substitution is made (count=1) to prevent double-replacement on edge cases.
"""
from __future__ import annotations

import re

_LIMIT_RE = re.compile(r"\bLIMIT\s+(\d+)\b", re.IGNORECASE)


def inject_limit(sql: str, row_cap: int) -> str:
    """Ensure sql has a LIMIT no greater than row_cap.

    Args:
        sql: A SQL SELECT string (should be pre-validated by validate_sql).
        row_cap: Maximum number of rows to allow (e.g. AgentConfig.row_cap = 200).

    Returns:
        The SQL string with LIMIT enforced. Trailing semicolons are stripped.
        The returned string never ends with a semicolon.
    """
    sql = sql.rstrip()
    if sql.endswith(";"):
        sql = sql[:-1].rstrip()

    match = _LIMIT_RE.search(sql)
    if match:
        existing = int(match.group(1))
        if existing > row_cap:
            sql = _LIMIT_RE.sub(f"LIMIT {row_cap}", sql, count=1)
        # existing <= row_cap: leave unchanged (idempotent path)
        return sql

    return f"{sql} LIMIT {row_cap}"
