"""SQLite engine/session plumbing for the v1 backend's persistence layer.

Kept as its own tiny module so repository modules (e.g.
``prediction_store.py``) only deal with a SQLAlchemy ``Session``, not
engine/connection setup. Single-file SQLite is enough for a single-process
dev/demo backend.

The DB path is resolved *lazily* (once per ``PredictionStore()``
construction, via ``build_session_factory``) rather than once at module
import time, so tests can point ``MAZU_DB_PATH`` at a throwaway temp file
via ``monkeypatch.setenv`` before constructing a store, without leaking
state into/from the real dev database (``backend/var/mazu.db``).
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_PATH_ENV = "MAZU_DB_PATH"
# backend/var/mazu.db -- deliberately not backend/data/ (that's the existing
# ``data`` *Python package* with historical_events.py etc.; keeping the
# runtime SQLite file out of it avoids any confusion between the two).
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "var" / "mazu.db"


class Base(DeclarativeBase):
    pass


def resolve_db_path() -> Path:
    override = os.environ.get(DB_PATH_ENV)
    return Path(override) if override else DEFAULT_DB_PATH


def _add_missing_columns(engine: Engine) -> None:
    """Bring pre-existing SQLite tables up to date with the current ORM models.

    ``Base.metadata.create_all`` only creates tables that don't exist yet --
    it never alters an existing table, so a dev/demo DB file created before a
    column (e.g. ``predictions.data_tier``) was added would otherwise keep
    failing every query with ``sqlite3.OperationalError: no such column``
    forever. This is a lightweight substitute for a full migration tool
    (there's no Alembic in this project): for each mapped table that already
    exists, add any column present in the ORM model but missing from the
    live schema, using its SQLAlchemy-rendered type and treating it as
    nullable (existing rows get NULL for the new column).
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            existing_columns = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                conn.execute(
                    text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}')
                )


def build_session_factory(db_path: Path | None = None) -> sessionmaker:
    """Create tables (if needed) and return a bound sessionmaker."""
    path = db_path or resolve_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI's TestClient / uvicorn may hand
    # requests to worker threads; each call still opens/closes its own
    # short-lived Session (see PredictionStore), so this is safe.
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    _add_missing_columns(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)
