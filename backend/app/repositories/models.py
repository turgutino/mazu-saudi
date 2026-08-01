"""SQLAlchemy ORM row for persisted predictions.

The full ``PredictionResult`` (including its nested feature/rule/mechanism/
similar-event lists) is stored as a single JSON blob in ``payload`` rather
than normalized across tables: every read pattern PredictionStore needs
(by id, by caseId, filtered by regionId/hazard, sorted by createdAt) is a
simple equality/order-by on the indexed columns below, so there is no
query that actually needs the nested data in SQL form.
"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.db import Base


class PredictionRow(Base):
    __tablename__ = "predictions"

    prediction_id: Mapped[str] = mapped_column(String, primary_key=True)
    case_id: Mapped[str] = mapped_column(String, index=True)
    region_id: Mapped[str] = mapped_column(String, index=True)
    hazard: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[str] = mapped_column(String, index=True)
    # tier1_real / tier2_live / tier3_synthetic (app.schemas.common.DataTier)
    # -- indexed so future dataset-building can cheaply filter for
    # high-quality (tier1_real) rows without deserializing every payload.
    data_tier: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[str] = mapped_column(Text)


class ForecastDataSnapshotRow(Base):
    __tablename__ = "forecast_data_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String, primary_key=True)
    cache_key: Mapped[str] = mapped_column(String, index=True)
    source: Mapped[str] = mapped_column(String, index=True)
    region_id: Mapped[str] = mapped_column(String, index=True)
    target_time: Mapped[str] = mapped_column(String, index=True)
    fetched_at: Mapped[str] = mapped_column(String, index=True)
    expires_at: Mapped[str] = mapped_column(String, index=True)
    valid_from: Mapped[str] = mapped_column(String)
    valid_to: Mapped[str] = mapped_column(String)
    feature_version: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="valid", index=True)
    validation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[str] = mapped_column(Text)
    indicators: Mapped[str] = mapped_column(Text)
