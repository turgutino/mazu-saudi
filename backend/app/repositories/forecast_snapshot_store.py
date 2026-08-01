"""SQLite persistence and bounded reuse for third-party forecast snapshots."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.domain.forecast_data import ForecastDataSnapshot
from app.repositories.db import build_session_factory
from app.repositories.models import ForecastDataSnapshotRow


def build_forecast_cache_key(
    source: str, region_id: str, target_time: datetime, feature_version: str
) -> str:
    target_hour = target_time.astimezone(timezone.utc).replace(
        minute=0, second=0, microsecond=0
    )
    value = f"{source}|{region_id}|{target_hour.isoformat()}|{feature_version}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ForecastSnapshotStore:
    def __init__(self) -> None:
        self._session_factory = build_session_factory()

    @staticmethod
    def _to_domain(row: ForecastDataSnapshotRow) -> ForecastDataSnapshot:
        return ForecastDataSnapshot(
            snapshot_id=row.snapshot_id,
            cache_key=row.cache_key,
            source=row.source,
            region_id=row.region_id,
            target_time=row.target_time,
            fetched_at=row.fetched_at,
            expires_at=row.expires_at,
            valid_from=row.valid_from,
            valid_to=row.valid_to,
            feature_version=row.feature_version,
            status=row.status or "valid",
            validation_error=row.validation_error,
            raw_payload=json.loads(row.raw_payload),
            indicators=json.loads(row.indicators),
        )

    def get_fresh(
        self, cache_key: str, now: datetime | None = None
    ) -> ForecastDataSnapshot | None:
        current = (now or datetime.now(timezone.utc)).isoformat()
        with self._session_factory() as session:
            stmt = (
                select(ForecastDataSnapshotRow)
                .where(ForecastDataSnapshotRow.cache_key == cache_key)
                .where(ForecastDataSnapshotRow.expires_at >= current)
                .order_by(ForecastDataSnapshotRow.fetched_at.desc())
            )
            row = session.scalars(stmt).first()
            return self._to_domain(row) if row else None

    def save(
        self,
        *,
        cache_key: str,
        source: str,
        region_id: str,
        target_time: datetime,
        valid_from: str,
        valid_to: str,
        feature_version: str,
        raw_payload: dict,
        indicators: dict[str, float],
        status: str = "valid",
        validation_error: str | None = None,
        ttl: timedelta = timedelta(minutes=30),
        fetched_at: datetime | None = None,
    ) -> ForecastDataSnapshot:
        fetched = fetched_at or datetime.now(timezone.utc)
        snapshot = ForecastDataSnapshot(
            snapshot_id=f"forecast-{uuid.uuid4().hex[:16]}",
            cache_key=cache_key,
            source=source,
            region_id=region_id,
            target_time=target_time.astimezone(timezone.utc).isoformat(),
            fetched_at=fetched.isoformat(),
            expires_at=(fetched + ttl).isoformat(),
            valid_from=valid_from,
            valid_to=valid_to,
            feature_version=feature_version,
            status=status,
            validation_error=validation_error,
            raw_payload=raw_payload,
            indicators=indicators,
        )
        row = ForecastDataSnapshotRow(
            snapshot_id=snapshot.snapshot_id,
            cache_key=snapshot.cache_key,
            source=snapshot.source,
            region_id=snapshot.region_id,
            target_time=snapshot.target_time,
            fetched_at=snapshot.fetched_at,
            expires_at=snapshot.expires_at,
            valid_from=snapshot.valid_from,
            valid_to=snapshot.valid_to,
            feature_version=snapshot.feature_version,
            status=snapshot.status,
            validation_error=snapshot.validation_error,
            raw_payload=json.dumps(snapshot.raw_payload, separators=(",", ":")),
            indicators=json.dumps(snapshot.indicators, separators=(",", ":")),
        )
        with self._session_factory() as session:
            session.add(row)
            session.commit()
        return snapshot

    def get(self, snapshot_id: str) -> ForecastDataSnapshot | None:
        with self._session_factory() as session:
            row = session.get(ForecastDataSnapshotRow, snapshot_id)
            return self._to_domain(row) if row else None

    def list(self) -> list[ForecastDataSnapshot]:
        with self._session_factory() as session:
            stmt = select(ForecastDataSnapshotRow).order_by(
                ForecastDataSnapshotRow.fetched_at.desc()
            )
            return [self._to_domain(row) for row in session.scalars(stmt).all()]


forecast_snapshot_store = ForecastSnapshotStore()
