"""SQL validator for the NL agent's run_sql tool (SAFE-02).

Pure function — no I/O, no Streamlit, no DB. Caller passes the LLM-generated SQL
string and the allowed_tables allowlist; this module decides accept/reject.

Reject rules (any one is fatal):
  - More than one statement after sqlparse.parse (Pitfall 4)
  - Statement type is not SELECT
  - SQL contains -- or /* comments (reject — do not strip)
  - Any referenced table is not in allowed_tables (case-insensitive)
"""
from __future__ import annotations

import sqlparse
import sqlparse.tokens as T
from pydantic import BaseModel


class ValidationResult(BaseModel):
    ok: bool
    reason: str = ""


def validate_sql(sql: str, allowed_tables: list[str]) -> ValidationResult:
    """Validate that sql is a single SELECT referencing only allowed_tables.

    Returns ValidationResult(ok=True) on success, ok=False with a human-readable
    reason on any rejection.
    """
    if not sql or not sql.strip():
        return ValidationResult(ok=False, reason="Empty SQL")

    # Pitfall 4: filter out blank/whitespace-only pseudo-statements that sqlparse
    # emits for trailing semicolons.  Only count statements that have a declared type.
    statements = [s for s in sqlparse.parse(sql) if s.tokens and s.get_type() is not None]
    if len(statements) != 1:
        return ValidationResult(ok=False, reason="Only a single SELECT statement is allowed")

    stmt = statements[0]

    # Statement type check
    if stmt.get_type() != "SELECT":
        return ValidationResult(
            ok=False, reason=f"Only SELECT is allowed, got {stmt.get_type()}"
        )

    # Set-operation check — UNION / INTERSECT / EXCEPT are not needed for single-table
    # queries and are the primary mechanism for allowed_tables bypass (CR-01).
    _SET_OP_KEYWORDS = {"UNION", "INTERSECT", "EXCEPT"}
    for tok in stmt.flatten():
        if tok.ttype is T.Keyword and tok.normalized.upper().split()[0] in _SET_OP_KEYWORDS:
            return ValidationResult(ok=False, reason="UNION / INTERSECT / EXCEPT are not allowed")

    # Comment check — reject outright, don't attempt to strip (SAFE-02 / T-02-02-06)
    for tok in stmt.flatten():
        if tok.ttype in (T.Comment.Single, T.Comment.Multiline):
            return ValidationResult(ok=False, reason="SQL comments are not allowed")

    # Table name extraction via FROM/JOIN AST walk
    tables = _extract_table_names(stmt)
    allowed_lower = {t.lower() for t in allowed_tables}
    disallowed = tables - allowed_lower
    if disallowed:
        return ValidationResult(
            ok=False, reason=f"Disallowed table(s): {sorted(disallowed)}"
        )

    return ValidationResult(ok=True)


def _extract_table_names(stmt) -> set[str]:
    """Walk tokens after FROM / JOIN collecting table identifiers (lowercased).

    Handles:
    - Simple FROM identifier
    - IdentifierList (comma-separated tables)
    - Parenthesis (subqueries) via recursion
    - JOIN keyword variants
    """
    from sqlparse.sql import Identifier, IdentifierList, Parenthesis

    tables: set[str] = set()

    def _walk(tokens):
        from_seen = False
        for tok in tokens:
            if tok.ttype is T.Keyword and tok.normalized.upper() in (
                "FROM",
                "JOIN",
                "INNER JOIN",
                "LEFT JOIN",
                "LEFT OUTER JOIN",
                "RIGHT JOIN",
                "RIGHT OUTER JOIN",
                "FULL JOIN",
                "CROSS JOIN",
            ):
                from_seen = True
                continue
            if from_seen:
                if isinstance(tok, Identifier):
                    # Check if this Identifier wraps a subquery: (SELECT ...) AS alias
                    # If so, recurse into the Parenthesis but don't add the alias as a table.
                    first_meaningful = [
                        t for t in tok.tokens if not t.is_whitespace and t.ttype not in (T.Punctuation,)
                    ]
                    if first_meaningful and isinstance(first_meaningful[0], Parenthesis):
                        _walk(first_meaningful[0].tokens)
                    else:
                        name = tok.get_real_name()
                        if name:
                            tables.add(name.lower())
                    from_seen = False
                elif isinstance(tok, IdentifierList):
                    for ident in tok.get_identifiers():
                        if isinstance(ident, Identifier):
                            name = ident.get_real_name()
                            if name:
                                tables.add(name.lower())
                    from_seen = False
                elif isinstance(tok, Parenthesis):
                    _walk(tok.tokens)
                    from_seen = False
                elif tok.ttype is T.Keyword:
                    from_seen = False
            # Recurse into compound tokens that are not Identifiers / IdentifierLists
            # (e.g., WHERE clauses, nested Parenthesis in subqueries)
            if hasattr(tok, "tokens") and not isinstance(tok, (Identifier, IdentifierList)):
                _walk(tok.tokens)

    _walk(stmt.tokens)
    return tables
