"""SQLite-backed prediction store (v1).

Persists ``PredictionResult`` rows in a local SQLite database (see
``repositories/db.py`` / ``repositories/models.py``) so predictions survive
process restarts, unlike the earlier in-memory dict. The public interface
(``save``/``get``/``get_by_case_id``/``list``) is unchanged, so
``services/prediction_service.py`` and the API routes needed no changes
beyond this file.
"""

from __future__ import annotations

from sqlalchemy import select

from app.repositories.db import build_session_factory
from app.repositories.models import PredictionRow
from app.schemas.prediction import PredictionResult


class PredictionStore:
    def __init__(self) -> None:
        # Resolved at construction time (not import time) so tests can
        # ``monkeypatch.setenv("MAZU_DB_PATH", ...)`` before instantiating a
        # store and get full isolation from the real dev database.
        self._session_factory = build_session_factory()

    def save(self, prediction: PredictionResult) -> None:
        row = PredictionRow(
            prediction_id=prediction.prediction_id,
            case_id=prediction.case_id,
            region_id=prediction.region_id,
            hazard=prediction.hazard,
            created_at=prediction.created_at,
            payload=prediction.model_dump_json(by_alias=True),
        )
        with self._session_factory() as session:
            session.merge(row)
            session.commit()

    def get(self, prediction_id: str) -> PredictionResult | None:
        with self._session_factory() as session:
            row = session.get(PredictionRow, prediction_id)
            return PredictionResult.model_validate_json(row.payload) if row else None

    def get_by_case_id(self, case_id: str) -> PredictionResult | None:
        with self._session_factory() as session:
            stmt = select(PredictionRow).where(PredictionRow.case_id == case_id)
            row = session.scalars(stmt).first()
            return PredictionResult.model_validate_json(row.payload) if row else None

    def list(
        self, region_id: str | None = None, hazard: str | None = None
    ) -> list[PredictionResult]:
        with self._session_factory() as session:
            stmt = select(PredictionRow)
            if region_id:
                stmt = stmt.where(PredictionRow.region_id == region_id)
            if hazard:
                stmt = stmt.where(PredictionRow.hazard == hazard)
            stmt = stmt.order_by(PredictionRow.created_at.desc())
            rows = session.scalars(stmt).all()
            return [PredictionResult.model_validate_json(row.payload) for row in rows]

    def clear(self) -> None:
        """Test-only helper: wipe all rows (keeps the same table/schema)."""
        with self._session_factory() as session:
            session.query(PredictionRow).delete()
            session.commit()


prediction_store = PredictionStore()
