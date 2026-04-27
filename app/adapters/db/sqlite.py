"""SQLite DB 어댑터 (개발/데모용).

In-process SQLAlchemy engine over a local .db file.
- `database` 필드를 파일 경로로 해석 (host/port/user/password 무시).
- pool_recycle / connect_timeout 미지정 — SQLite는 네트워크 연결이 없음.
- run_query는 SET SESSION TRANSACTION READ ONLY 문을 실행하지 않음
  (SQLite는 해당 statement를 지원하지 않으며, ufs_service의 try/except는
   network DB용 보호막이지 SQLite path를 위한 것이 아님).
"""
from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from app.adapters.db.base import DBAdapter
from app.core.config import DatabaseConfig

logger = logging.getLogger(__name__)


class SQLiteAdapter(DBAdapter):
    def __init__(self, config: DatabaseConfig) -> None:
        super().__init__(config)
        self._engine: Engine | None = None

    def _get_engine(self) -> Engine:
        if self._engine is not None:
            return self._engine
        c = self.config
        # `database` is the filesystem path. Empty string -> in-memory DB
        # (useful for tests; the seeder produces a file path).
        url = f"sqlite:///{c.database}"
        self._engine = create_engine(url, pool_pre_ping=True)
        return self._engine

    def test_connection(self) -> tuple[bool, str]:
        try:
            with self._get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, "연결 성공"
        except Exception as exc:  # pragma: no cover - filesystem dependent
            return False, f"연결 실패: {exc}"

    def list_tables(self) -> list[str]:
        inspector = inspect(self._get_engine())
        return sorted(inspector.get_table_names())

    def get_schema(self, tables: list[str] | None = None) -> dict[str, list[dict]]:
        inspector = inspect(self._get_engine())
        target = tables or self.list_tables()
        schema: dict[str, list[dict]] = {}
        for t in target:
            try:
                pk_cols = set(inspector.get_pk_constraint(t).get("constrained_columns") or [])
            except Exception as exc:
                logger.debug("get_pk_constraint failed for table %s: %s", t, exc)
                pk_cols = set()
            cols = []
            for col in inspector.get_columns(t):
                cols.append(
                    {
                        "name": col["name"],
                        "type": str(col.get("type", "")),
                        "nullable": bool(col.get("nullable", True)),
                        "pk": col["name"] in pk_cols,
                    }
                )
            schema[t] = cols
        return schema

    def run_query(self, sql: str) -> pd.DataFrame:
        # SQLite has no SET SESSION TRANSACTION READ ONLY equivalent; the
        # readonly contract for SQLite is enforced upstream by sql_validator
        # / sql_limiter (SELECT-only) plus filesystem permissions. We simply
        # do not emit any session-level statement here.
        with self._get_engine().connect() as conn:
            return pd.read_sql_query(text(sql), conn)

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
