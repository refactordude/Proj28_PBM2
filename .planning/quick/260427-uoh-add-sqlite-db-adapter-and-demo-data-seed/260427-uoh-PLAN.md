---
phase: 260427-uoh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/core/config.py
  - app/adapters/db/sqlite.py
  - app/adapters/db/registry.py
  - scripts/seed_demo_db.py
  - config/settings.yaml
autonomous: true
requirements:
  - QUICK-260427-UOH
must_haves:
  truths:
    - "Running `python scripts/seed_demo_db.py` creates data/demo_ufs.db with ~150 EAV rows across ~20 platforms and 12 (InfoCategory, Item) parameter pairs"
    - "build_adapter(DatabaseConfig(type='sqlite', database='data/demo_ufs.db')) returns a working adapter whose test_connection() passes and list_tables() includes 'ufs_data'"
    - "Starting `uvicorn app_v2.main:app` with the new config/settings.yaml loads the SQLite adapter at lifespan startup and serves /browse with HTTP 200"
    - "MySQLAdapter behavior is unchanged — no edits to app/adapters/db/mysql.py or app/services/ufs_service.py"
    - "Existing tests are not modified"
  artifacts:
    - path: "app/core/config.py"
      provides: "DatabaseConfig.type Literal extended with 'sqlite'"
      contains: "sqlite"
    - path: "app/adapters/db/sqlite.py"
      provides: "SQLiteAdapter implementing DBAdapter interface"
      exports: ["SQLiteAdapter"]
    - path: "app/adapters/db/registry.py"
      provides: "Registry mapping with 'sqlite' entry"
      contains: "SQLiteAdapter"
    - path: "scripts/seed_demo_db.py"
      provides: "Idempotent SQLite demo data seeder using sqlite3 stdlib"
      min_lines: 60
    - path: "config/settings.yaml"
      provides: "Default runtime config pointing at the demo SQLite DB"
      contains: "type: sqlite"
    - path: "data/demo_ufs.db"
      provides: "Seeded SQLite file with ufs_data table populated"
  key_links:
    - from: "app/adapters/db/registry.py"
      to: "app/adapters/db/sqlite.py"
      via: "import + _REGISTRY['sqlite'] entry"
      pattern: "from app.adapters.db.sqlite import SQLiteAdapter"
    - from: "app_v2/main.py lifespan"
      to: "config/settings.yaml databases[0]"
      via: "load_settings() -> build_adapter() -> SQLiteAdapter"
      pattern: "type: sqlite"
    - from: "app/services/ufs_service.py fetch_cells_core"
      to: "SQLiteAdapter._get_engine()"
      via: "db._get_engine().connect() context manager"
      pattern: "_get_engine"
---

<objective>
Add a SQLite DB adapter and an idempotent demo-data seeder so users can exercise the v2.0 Browse tab end-to-end without provisioning a real MySQL instance. This is purely additive dev-fixture work — it unblocks Phase 4 UAT (`/gsd-uat-phase 4`) and lets new contributors clone, seed, and `uvicorn app_v2.main:app` in under a minute.

Purpose:
- Phase 4 (browse-tab-port) is complete and pending UAT. UAT requires a live database. Provisioning MySQL is friction; SQLite (file-based, in-process, stdlib) eliminates it.
- The DBAdapter abstraction was designed for exactly this — a new database type drops in by registering a class. SQLAlchemy's `sqlite:///path` URL means the existing `pd.read_sql_query(sa.text(...), conn)` machinery in `ufs_service` works unchanged.

Output:
- A `"sqlite"` member in `DatabaseConfig.type` Literal
- A `SQLiteAdapter` class mirroring `MySQLAdapter`'s shape
- A registry entry routing `"sqlite"` to `SQLiteAdapter`
- A `scripts/seed_demo_db.py` that creates `data/demo_ufs.db` with realistic UFS-shaped EAV data
- A starter `config/settings.yaml` (only if absent) wired to the demo DB

Out of scope (executor MUST NOT do):
- Modify any existing test files
- Touch ROADMAP / STATE / phase PLAN.md
- Edit MySQLAdapter or ufs_service
- Add new top-level dependencies (sqlite3 is stdlib; SQLAlchemy already supports SQLite)
- gitignore data/demo_ufs.db
- Clobber an existing config/settings.yaml
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md
@app/adapters/db/base.py
@app/adapters/db/mysql.py
@app/adapters/db/registry.py
@app/core/config.py
@app/services/ufs_service.py
@app_v2/main.py
@config/settings.example.yaml

<interfaces>
<!-- Contracts the executor must implement against. Extracted from the codebase. -->

DBAdapter abstract base (app/adapters/db/base.py):
```python
class DBAdapter(ABC):
    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]: ...

    @abstractmethod
    def list_tables(self) -> list[str]: ...

    @abstractmethod
    def get_schema(self, tables: list[str] | None = None) -> dict[str, list[dict]]: ...

    @abstractmethod
    def run_query(self, sql: str) -> pd.DataFrame: ...

    def dispose(self) -> None: ...
```

DatabaseConfig (app/core/config.py — current state, the Literal must be extended):
```python
class DatabaseConfig(BaseModel):
    name: str
    type: Literal["mysql", "postgres", "mssql", "bigquery", "snowflake"] = "mysql"  # ADD "sqlite"
    host: str = "localhost"
    port: int = 3306
    database: str = ""        # repurposed as filesystem path for sqlite
    user: str = ""            # ignored for sqlite
    password: str = ""        # ignored for sqlite
    readonly: bool = True     # honored for sqlite (used by run_query path; SQLite has no SET TRANSACTION READ ONLY equivalent — silently skipped)
```

MySQLAdapter shape to mirror (app/adapters/db/mysql.py):
- `__init__` calls super().__init__(config); sets `self._engine: Engine | None = None`
- `_get_engine()` lazily constructs and caches an Engine
- `test_connection()` returns `(bool, str)` — Korean message "연결 성공" / "연결 실패: {exc}"
- `list_tables()` uses `sqlalchemy.inspect(engine)`
- `get_schema()` uses inspector for columns + PK metadata
- `run_query()` opens a connection, optionally sets read-only, returns `pd.read_sql_query(text(sql), conn)`
- `dispose()` calls `engine.dispose()` and resets `_engine` to None

ufs_service consumer contract (app/services/ufs_service.py — DO NOT MODIFY):
- Calls `db._get_engine().connect() as conn` (so `_get_engine` must exist on the adapter, even though it is "private" by Python convention — this is a leaky abstraction the codebase already relies on)
- Issues `SELECT DISTINCT PLATFORM_ID FROM ufs_data ORDER BY PLATFORM_ID` (SQLite-compatible)
- Issues `SELECT DISTINCT InfoCategory, Item FROM ufs_data ORDER BY InfoCategory, Item` (SQLite-compatible)
- Issues parameterized `SELECT ... FROM ufs_data WHERE PLATFORM_ID IN :platforms AND ... LIMIT :cap` with `sa.bindparam(expanding=True)` (SQLite-compatible)
- Wraps `SET SESSION TRANSACTION READ ONLY` in try/except (so SQLite raising on this statement is a harmless skip — but the SQLiteAdapter's run_query SHOULD NOT issue this statement at all)

Lifespan consumer (app_v2/main.py):
- `load_settings()` parses config/settings.yaml into a Settings object
- `build_adapter(db_cfg)` is called for `settings.databases[0]` (or the named default)
- Adapter must be ready for `db._get_engine().connect()` immediately after construction
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add SQLiteAdapter, extend DatabaseConfig Literal, register in registry</name>
  <files>app/core/config.py, app/adapters/db/sqlite.py, app/adapters/db/registry.py</files>
  <action>
Three coordinated edits — all three or none, because the `"sqlite"` literal value flows from config.py → registry lookup → adapter class.

**1. Edit `app/core/config.py`:**
- Locate the `DatabaseConfig.type` field (currently `Literal["mysql", "postgres", "mssql", "bigquery", "snowflake"] = "mysql"`).
- Add `"sqlite"` to the Literal. Place it anywhere — order is not enforced. Suggested placement: alongside other RDBMS entries, e.g. `Literal["mysql", "sqlite", "postgres", "mssql", "bigquery", "snowflake"] = "mysql"`.
- Default stays `"mysql"`. Do NOT change `host`/`port`/`user`/`password`/`database` field defaults — SQLite re-uses `database` as the filesystem path; the unused fields stay at their inert defaults.
- Do NOT touch `LLMConfig`, `AppConfig`, `Settings`, `load_settings`, `save_settings`, `find_database`, `find_llm`.

**2. Create `app/adapters/db/sqlite.py`** mirroring the shape of `app/adapters/db/mysql.py`:

```python
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
```

**3. Edit `app/adapters/db/registry.py`:**
- Add the import line: `from app.adapters.db.sqlite import SQLiteAdapter`
- Add `"sqlite": SQLiteAdapter,` to the `_REGISTRY` dict (place it next to `"mysql"`).
- Do NOT change `supported_types()` or `build_adapter()` — they read `_REGISTRY` dynamically.

Rationale notes for the executor:
- `pool_pre_ping=True` is harmless for SQLite (the ping is an in-process round-trip with negligible cost) — keeping it consistent with MySQL means future engineers don't wonder why one adapter has it and the other doesn't.
- `pool_recycle` is dropped because SQLite connections never time out (no `wait_timeout`).
- `connect_args={"connect_timeout": 5}` is dropped because SQLite has no network connect step.
- `c.password` / `c.user` are not URL-quoted because they are not part of the SQLite URL.
- The `readonly` config field is intentionally NOT enforced via SQLAlchemy events for SQLite — sql_validator + sql_limiter (SELECT-only) is the existing 1st-line defense, and Phase 4 Browse never issues writes.
  </action>
  <verify>
    <automated>python -c "from app.core.config import DatabaseConfig; cfg = DatabaseConfig(name='t', type='sqlite', database=':memory:'); from app.adapters.db.registry import build_adapter, supported_types; assert 'sqlite' in supported_types(); a = build_adapter(cfg); ok, msg = a.test_connection(); assert ok, msg; print('OK', supported_types(), msg)"</automated>
  </verify>
  <done>
- `DatabaseConfig.type` Literal includes `"sqlite"`; constructing `DatabaseConfig(type='sqlite', ...)` does not raise a ValidationError
- `app/adapters/db/sqlite.py` exists with `SQLiteAdapter` class implementing all four abstract methods plus `dispose`
- `from app.adapters.db.registry import build_adapter; build_adapter(DatabaseConfig(type='sqlite', database=':memory:')).test_connection()` returns `(True, '연결 성공')`
- `supported_types()` returns a sorted list containing both `"mysql"` and `"sqlite"`
- `app/adapters/db/mysql.py` is byte-identical to its prior state (no diff)
- `app/services/ufs_service.py` is byte-identical to its prior state (no diff)
  </done>
</task>

<task type="auto">
  <name>Task 2: Create idempotent SQLite demo-data seeder</name>
  <files>scripts/seed_demo_db.py</files>
  <action>
Create `scripts/seed_demo_db.py` — a standalone, idempotent CLI script that builds `data/demo_ufs.db` with realistic UFS-shaped EAV rows.

Constraints:
- Use only `sqlite3` (stdlib) + `random` + `pathlib`. Do NOT import SQLAlchemy or pandas — keep the seeder dependency-light so it runs even before the venv is set up beyond the bare requirements.
- The script must be runnable from the repo root via `python scripts/seed_demo_db.py`. It must also work if invoked from another CWD — resolve the repo root by walking up from `__file__`.
- Idempotent: if `data/demo_ufs.db` exists, delete and recreate. Print a one-line note when deleting so users see the script is doing real work on re-runs.
- Schema: `CREATE TABLE ufs_data (PLATFORM_ID TEXT, InfoCategory TEXT, Item TEXT, Result TEXT)`. No primary key (matches the EAV-form ufs_data shape from CLAUDE.md). Add a single non-unique index on PLATFORM_ID for query speed: `CREATE INDEX idx_platform ON ufs_data (PLATFORM_ID)`.
- Seed ~20 PLATFORM_IDs with realistic UFS subsystem profile names. Use this exact list (so the test platforms are deterministic and the count is exactly 20):
  ```
  "SM8650_v1", "SM8650_v2", "SM8550_rev1",
  "MTK6989_rev2", "MTK6985_a", "MTK6983_b",
  "EXYNOS2400_a", "EXYNOS2200_b", "EXYNOS1380_c",
  "TENSOR_G3_x1", "TENSOR_G2_x2",
  "KIRIN9000s_a",
  "DIMENSITY9300_v1", "DIMENSITY9200_v2",
  "SDM_X75_v1", "MSM8998_legacy",
  "SC8275_auto", "QCS6490_iot",
  "MT8195_chrome", "RK3588_dev",
  ```
- Seed exactly 12 (InfoCategory, Item) parameter pairs, each with a distinct value-shape so users see the heterogeneous Result column the EAV schema produces. For each parameter, define a small pool of plausible Result strings — the seeder picks one per platform pseudo-randomly (with `random.seed(42)` for reproducibility):

  | InfoCategory | Item | Value pool |
  |---|---|---|
  | VendorInfo | ManufacturerName | "Samsung", "SK Hynix", "Micron", "Kioxia" |
  | VendorInfo | ProductName | "KLUFG8RJ4C-B0C1", "H58Q2G8DDK", "MTFC512GAJDQ", "THGJFGT0T43BAIL" |
  | DeviceInfo | NumberOfLU | "8", "16", "32" |
  | DeviceInfo | bDeviceVersion | "0x0310", "0x0220", "0x0400" |
  | GeometryDescriptor | RawDeviceCapacity | "1024209543168", "512104771584", "256052385792" |
  | GeometryDescriptor | SegmentSize | "0x00080000", "0x00100000", "0x00200000" |
  | GeometryDescriptor | AllocationUnitSize | "1", "2", "4" |
  | UnitDescriptor | dCapacityAdjFactor | "1.0000", "0.9842", "0.9521" |
  | UnitDescriptor | bLogicalBlockSize | "0x0C", "0x09" |
  | PowerParameters | bActiveICCLevelsForVCC | "0x14", "0x1F", "0x0A" |
  | InterconnectDescriptor | bMaxRxHsGear | "4", "5" |
  | StringDescriptor | oManufacturerName | "0x80", "0xC0" |

- Cross-product = 20 platforms × 12 params = 240 candidate rows. Skip a deterministic subset so real "missing cell" gaps appear in the pivot grid:
  - For each (platform, param) pair, draw a uniform random 0..99. Skip the row if the draw is < 38 (this skips ~38% on average → ~150 rows seeded). Use `random.seed(42)` ONCE at the top of the seeding loop so the gap pattern is reproducible across runs.
  - Independently: when keeping a row, pick the Result value with `random.choice(pool)` against the same seeded RNG.
- Wrap all inserts in a single transaction (`with conn:` context manager auto-commits on exit) so the file flush is atomic.
- Final prints (each on its own line):
  - `f"Seeded {n_rows} rows into {db_path}"`
  - `f"Platforms: {n_platforms}, parameters: {n_params}"`
- Exit code: 0 on success. Bare `if __name__ == "__main__":` guard.

Skeleton:

```python
"""Seed data/demo_ufs.db with realistic UFS-shaped EAV rows for v2.0 Browse UAT.

Idempotent: re-running deletes and recreates the file. Uses sqlite3 stdlib
only — no SQLAlchemy / pandas dependency.

Usage:
    python scripts/seed_demo_db.py
"""
from __future__ import annotations

import random
import sqlite3
from pathlib import Path

# Resolve repo root by walking up from this file (works from any CWD).
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DATA_DIR = _REPO_ROOT / "data"
_DB_PATH = _DATA_DIR / "demo_ufs.db"

PLATFORMS: tuple[str, ...] = (
    # ... 20 entries from the table above
)

PARAMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("VendorInfo", "ManufacturerName", ("Samsung", "SK Hynix", "Micron", "Kioxia")),
    # ... 11 more entries
)


def main() -> int:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if _DB_PATH.exists():
        print(f"Removing existing {_DB_PATH}")
        _DB_PATH.unlink()

    rng = random.Random(42)  # local RNG instance — does not pollute global state

    rows: list[tuple[str, str, str, str]] = []
    for pid in PLATFORMS:
        for category, item, pool in PARAMS:
            if rng.randrange(100) < 38:
                continue  # leave a gap so the pivot grid has visible holes
            rows.append((pid, category, item, rng.choice(pool)))

    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE ufs_data ("
            "PLATFORM_ID TEXT, InfoCategory TEXT, Item TEXT, Result TEXT)"
        )
        conn.execute("CREATE INDEX idx_platform ON ufs_data (PLATFORM_ID)")
        conn.executemany(
            "INSERT INTO ufs_data (PLATFORM_ID, InfoCategory, Item, Result) "
            "VALUES (?, ?, ?, ?)",
            rows,
        )

    print(f"Seeded {len(rows)} rows into {_DB_PATH}")
    print(f"Platforms: {len(PLATFORMS)}, parameters: {len(PARAMS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

The executor must fully populate the `PLATFORMS` and `PARAMS` constants from the tables above (do NOT abbreviate with `...` in the actual file).

A note on idempotency: deleting and recreating is preferred over `CREATE TABLE IF NOT EXISTS` + `DELETE FROM` because the seeder may grow new columns / indexes in future and the cleanest "rerun = same result" contract is to start from an empty file every time.
  </action>
  <verify>
    <automated>cd /home/yh/Desktop/02_Projects/Proj28_PBM2 && python scripts/seed_demo_db.py && python -c "import sqlite3; conn = sqlite3.connect('data/demo_ufs.db'); n = conn.execute('SELECT COUNT(*) FROM ufs_data').fetchone()[0]; p = conn.execute('SELECT COUNT(DISTINCT PLATFORM_ID) FROM ufs_data').fetchone()[0]; ic = conn.execute('SELECT COUNT(DISTINCT InfoCategory || Item) FROM ufs_data').fetchone()[0]; conn.close(); assert 100 < n < 200, f'expected ~150 rows, got {n}'; assert p == 20, f'expected 20 platforms, got {p}'; assert ic == 12, f'expected 12 (cat,item) pairs, got {ic}'; print(f'rows={n} platforms={p} params={ic}')"</automated>
  </verify>
  <done>
- `scripts/seed_demo_db.py` is created, `chmod +x` not required
- Running `python scripts/seed_demo_db.py` from the repo root exits 0 and prints the two summary lines
- `data/demo_ufs.db` is created (or recreated) with the `ufs_data` table populated
- Row count is in the 100-200 range (the random skip yields ~150 with seed=42)
- Distinct PLATFORM_ID count is exactly 20
- Distinct (InfoCategory, Item) pair count is exactly 12
- Re-running the script removes the previous file and creates a fresh one (idempotent)
- Script does NOT import SQLAlchemy, pandas, or any non-stdlib package
  </done>
</task>

<task type="auto">
  <name>Task 3: Create config/settings.yaml (only if absent) and end-to-end smoke-test the lifespan + /browse path</name>
  <files>config/settings.yaml</files>
  <action>
**Step 1 — Guard against clobbering an existing config.**

Run `ls config/settings.yaml` first. If the file exists, SKIP the file creation step and only run the smoke test (Step 3). Print a clear note: `"config/settings.yaml already exists — skipping creation; using existing config for smoke test"`. Do NOT overwrite, do NOT diff, do NOT prompt.

If the file does NOT exist, proceed to Step 2.

**Step 2 — Create config/settings.yaml** with the following exact contents:

```yaml
databases:
  - name: "Demo SQLite"
    type: sqlite
    database: data/demo_ufs.db
    readonly: true

llms:
  - name: "GPT-4o Mini"
    type: openai
    model: gpt-4o-mini
    api_key: ""
    endpoint: ""
    temperature: 0.0
    max_tokens: 2000

  - name: "Local Llama (Ollama)"
    type: ollama
    model: "llama3.1:8b"
    endpoint: "http://localhost:11434"
    api_key: ""
    temperature: 0.0
    max_tokens: 2000

app:
  default_database: "Demo SQLite"
  default_llm: "GPT-4o Mini"
  query_row_limit: 1000
  recent_query_history: 20
  agent:
    model: ""
    max_steps: 5
    row_cap: 200
    timeout_s: 30
    allowed_tables:
      - "ufs_data"
    max_context_tokens: 30000
```

Notes for the executor:
- The `Demo SQLite` entry intentionally omits `host`/`port`/`user`/`password` — Pydantic supplies defaults for all of them. SQLiteAdapter ignores them anyway.
- The two LLM entries are placeholders matching `config/settings.example.yaml` so the Settings UI has something to render, even though Phase 4 Browse does not touch the LLM path.
- `default_database: "Demo SQLite"` matches the `databases[0].name` value exactly — load_settings() resolves this string to the DatabaseConfig in main.py:60.

**Step 3 — End-to-end smoke test the lifespan + /browse route.**

Run this sequence (assumes the seeder from Task 2 has completed and `data/demo_ufs.db` exists):

```bash
cd /home/yh/Desktop/02_Projects/Proj28_PBM2
# 1. Verify build_adapter resolves a working SQLite adapter from a real DatabaseConfig
python -c "
from app.adapters.db.registry import build_adapter
from app.core.config import DatabaseConfig
a = build_adapter(DatabaseConfig(name='t', type='sqlite', database='data/demo_ufs.db'))
ok, msg = a.test_connection()
print('connect:', ok, msg)
print('tables:', a.list_tables())
assert ok and 'ufs_data' in a.list_tables()
print('OK')
"

# 2. Smoke-test the FastAPI app — uvicorn on a non-default port to avoid collisions
.venv/bin/uvicorn app_v2.main:app --port 8765 --log-level error &
UVICORN_PID=$!
sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/browse)
kill $UVICORN_PID 2>/dev/null || true
wait $UVICORN_PID 2>/dev/null || true
echo "GET /browse -> $HTTP_CODE"
test "$HTTP_CODE" = "200"
```

If the uvicorn binary is at a different path (e.g. `python -m uvicorn ...`), the executor may substitute equivalently. The /browse status code is the gate.

If port 8765 is already in use, retry with port 8766. Do NOT use port 8000 (collides with the user's default dev server).
  </action>
  <verify>
    <automated>cd /home/yh/Desktop/02_Projects/Proj28_PBM2 && test -f config/settings.yaml && python -c "from app.core.config import load_settings; s = load_settings(); db = next((d for d in s.databases if d.name == s.app.default_database), None); assert db is not None and db.type == 'sqlite' and db.database == 'data/demo_ufs.db', f'unexpected default db: {db}'; print('settings OK:', db.name, db.type, db.database)" && python -c "from app.adapters.db.registry import build_adapter; from app.core.config import DatabaseConfig; a = build_adapter(DatabaseConfig(name='t', type='sqlite', database='data/demo_ufs.db')); ok, msg = a.test_connection(); assert ok, msg; assert 'ufs_data' in a.list_tables(); print('adapter OK:', a.list_tables())" && (PORT=8765; .venv/bin/uvicorn app_v2.main:app --port $PORT --log-level error &> /tmp/uvicorn_smoke.log & UV_PID=$!; sleep 2; HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/browse); kill $UV_PID 2>/dev/null; wait $UV_PID 2>/dev/null; echo "GET /browse -> $HTTP_CODE"; test "$HTTP_CODE" = "200")</automated>
  </verify>
  <done>
- `config/settings.yaml` exists with `default_database: "Demo SQLite"` and a `databases[0]` entry whose `type: sqlite` and `database: data/demo_ufs.db`
- (Or, if the file pre-existed: it was NOT overwritten; the executor explicitly logged that it was skipped)
- `load_settings()` parses the file without error and the resolved default DatabaseConfig has `type='sqlite'`
- `build_adapter(...)` on the resolved DatabaseConfig returns a SQLiteAdapter whose `test_connection()` is `(True, '연결 성공')` and whose `list_tables()` includes `'ufs_data'`
- `uvicorn app_v2.main:app` starts cleanly with the new config (no exception in lifespan), and `GET /browse` returns HTTP 200
- The uvicorn process is killed cleanly after the smoke test (no leftover background processes)
- `app/adapters/db/mysql.py`, `app/services/ufs_service.py`, all files under `tests/` are byte-identical to their prior state
- `.planning/ROADMAP.md`, `.planning/STATE.md`, and any `.planning/phases/**/PLAN.md` files are untouched
  </done>
</task>

</tasks>

<verification>

Phase-level checks (run after all three tasks complete):

1. **Adapter contract:** `python -c "from app.adapters.db.registry import build_adapter, supported_types; from app.core.config import DatabaseConfig; assert 'sqlite' in supported_types(); a = build_adapter(DatabaseConfig(name='t', type='sqlite', database='data/demo_ufs.db')); assert a.test_connection()[0]; assert 'ufs_data' in a.list_tables(); print('OK')"`

2. **No regression on existing tests:** `pytest -q tests/ -x --no-header 2>&1 | tail -20` — the Phase 4 invariant guards (test_no_banned_libraries_imported_in_app_v2, etc.) and all 171 v1.0 tests must still pass. The SQLiteAdapter is new code with no existing tests asserting its absence; existing tests should be unaffected.

3. **MySQL path unchanged:** `git diff app/adapters/db/mysql.py app/services/ufs_service.py` returns empty. (Only the three deliberately-modified files plus the three created files should appear in `git status`.)

4. **End-to-end:** `python scripts/seed_demo_db.py` exits 0; uvicorn starts with new config; `GET /browse` returns 200.

5. **Out-of-scope guard:** `git status` shows ONLY the following changes:
   - Modified: `app/core/config.py`, `app/adapters/db/registry.py`
   - Added: `app/adapters/db/sqlite.py`, `scripts/seed_demo_db.py`, `config/settings.yaml` (if not pre-existing), `data/demo_ufs.db` (untracked unless gitignored)
   - NO changes to: `tests/`, `.planning/`, `app/adapters/db/mysql.py`, `app/services/ufs_service.py`, `ROADMAP.md`, `STATE.md`

</verification>

<success_criteria>

- [ ] `DatabaseConfig.type` Literal includes `"sqlite"`; `DatabaseConfig(type='sqlite', ...)` constructs without error
- [ ] `app/adapters/db/sqlite.py` exists and `SQLiteAdapter` implements all four `DBAdapter` abstract methods plus `dispose`
- [ ] `app/adapters/db/registry.py` `_REGISTRY` has the `"sqlite"` key mapping to `SQLiteAdapter`
- [ ] `scripts/seed_demo_db.py` runs to completion, prints summary, creates `data/demo_ufs.db` with ~150 rows / 20 platforms / 12 params
- [ ] `scripts/seed_demo_db.py` is idempotent — running twice in a row succeeds both times with identical output
- [ ] `config/settings.yaml` exists (created by this plan only if absent) with the demo SQLite as default
- [ ] `uvicorn app_v2.main:app` starts cleanly with the new config and serves `GET /browse` → HTTP 200
- [ ] All 171+ existing v1.0 tests + Phase 4 invariant guards still pass
- [ ] `app/adapters/db/mysql.py`, `app/services/ufs_service.py`, every file under `tests/`, every file under `.planning/` are byte-identical to their prior state
- [ ] No new top-level dependencies added to `requirements.txt`

</success_criteria>

<output>
After completion, create `.planning/quick/260427-uoh-add-sqlite-db-adapter-and-demo-data-seed/260427-uoh-SUMMARY.md` describing:
- Files created / modified
- Verification command outputs (test_connection result, row count, GET /browse status code)
- Any deviations from the plan (e.g. if config/settings.yaml pre-existed and was preserved)
- Out-of-scope items confirmed untouched (mysql.py, ufs_service.py, tests/, .planning/)
</output>
