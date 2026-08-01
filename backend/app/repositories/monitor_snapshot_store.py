"""Immutable six-hour cache snapshots for the monitoring map."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from app.repositories.db import build_session_factory
from app.repositories.models import MonitorDataSnapshotRow
from app.schemas.monitor import MonitorDataSnapshot


MONITOR_BUCKET_HOURS = 6


def monitor_bucket_start(now: datetime | None = None) -> datetime:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return current.replace(
        hour=(current.hour // MONITOR_BUCKET_HOURS) * MONITOR_BUCKET_HOURS,
        minute=0,
        second=0,
        microsecond=0,
    )


class MonitorSnapshotStore:
    def __init__(self) -> None:
        self._session_factory = build_session_factory()

    @staticmethod
    def _to_schema(row: MonitorDataSnapshotRow, *, cache_hit: bool) -> MonitorDataSnapshot:
        return MonitorDataSnapshot(
            snapshot_id=row.snapshot_id,
            source=row.source,
            bucket_start=row.bucket_start,
            fetched_at=row.fetched_at,
            expires_at=row.expires_at,
            cache_hit=cache_hit,
            data=json.loads(row.payload),
        )

    def get_current(
        self, source: str, now: datetime | None = None
    ) -> MonitorDataSnapshot | None:
        bucket = monitor_bucket_start(now).isoformat()
        with self._session_factory() as session:
            stmt = (
                select(MonitorDataSnapshotRow)
                .where(MonitorDataSnapshotRow.source == source)
                .where(MonitorDataSnapshotRow.bucket_start == bucket)
                .order_by(MonitorDataSnapshotRow.fetched_at.desc())
            )
            row = session.scalars(stmt).first()
            return self._to_schema(row, cache_hit=True) if row else None

    def save(
        self,
        source: str,
        data: dict[str, Any] | list[Any],
        *,
        fetched_at: datetime | None = None,
    ) -> MonitorDataSnapshot:
        fetched = (fetched_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        bucket = monitor_bucket_start(fetched)
        row = MonitorDataSnapshotRow(
            snapshot_id=f"monitor-{uuid.uuid4().hex[:16]}",
            source=source,
            bucket_start=bucket.isoformat(),
            fetched_at=fetched.isoformat(),
            expires_at=(bucket + timedelta(hours=MONITOR_BUCKET_HOURS)).isoformat(),
            payload=json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        )
        with self._session_factory() as session:
            session.add(row)
            session.commit()
        return self._to_schema(row, cache_hit=False)

    def list(self, source: str | None = None) -> list[MonitorDataSnapshot]:
        with self._session_factory() as session:
            stmt = select(MonitorDataSnapshotRow)
            if source:
                stmt = stmt.where(MonitorDataSnapshotRow.source == source)
            stmt = stmt.order_by(MonitorDataSnapshotRow.fetched_at.desc())
            return [
                self._to_schema(row, cache_hit=False)
                for row in session.scalars(stmt).all()
            ]


monitor_snapshot_store = MonitorSnapshotStore()
