"""Regression test for the auto-migration in ``app.repositories.db``.

Reproduces the real-world scenario that broke ``/api/v1/dashboard/*``: a
SQLite file created by an older version of the ORM model (missing a column
that was added later, e.g. ``predictions.data_tier``) must be transparently
upgraded in place the next time ``build_session_factory`` runs, instead of
every subsequent query raising ``sqlite3.OperationalError: no such column``.
"""

from __future__ import annotations

import sqlite3

from app.repositories.db import build_session_factory
from app.repositories.models import PredictionRow


def _create_legacy_predictions_table(db_path: str) -> None:
    """Create a ``predictions`` table matching the schema *before*
    ``data_tier`` was added, simulating a pre-existing dev database."""
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            """
            CREATE TABLE predictions (
                prediction_id VARCHAR NOT NULL PRIMARY KEY,
                case_id VARCHAR NOT NULL,
                region_id VARCHAR NOT NULL,
                hazard VARCHAR NOT NULL,
                created_at VARCHAR NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        con.commit()
    finally:
        con.close()


def test_build_session_factory_adds_missing_columns_to_legacy_table(tmp_path):
    db_path = str(tmp_path / "legacy.db")
    _create_legacy_predictions_table(db_path)

    session_factory = build_session_factory(tmp_path / "legacy.db")

    with session_factory() as session:
        rows = session.query(PredictionRow).all()
        assert rows == []

    con = sqlite3.connect(db_path)
    try:
        columns = {row[1] for row in con.execute("PRAGMA table_info(predictions)")}
    finally:
        con.close()
    assert "data_tier" in columns


def test_build_session_factory_is_idempotent_on_up_to_date_schema(tmp_path):
    db_path = tmp_path / "fresh.db"

    # First call creates the table from scratch (already up to date).
    build_session_factory(db_path)
    # Second call must not error even though there is nothing left to add.
    session_factory = build_session_factory(db_path)

    with session_factory() as session:
        assert session.query(PredictionRow).all() == []
