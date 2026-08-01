from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_monitor_acquisition_service, get_monitor_snapshot_store
from app.repositories.monitor_snapshot_store import MonitorSnapshotStore
from app.schemas.monitor import (
    MonitorDataSnapshot,
    MonitorSource,
    MonitorSourceStatus,
)
from app.services.monitor_acquisition import MonitorAcquisitionError, MonitorAcquisitionService

router = APIRouter(tags=["monitor"])


@router.get("/monitor/snapshots/{source}", response_model=MonitorDataSnapshot)
def get_monitor_snapshot(
    source: MonitorSource,
    store: MonitorSnapshotStore = Depends(get_monitor_snapshot_store),
) -> MonitorDataSnapshot:
    snapshot = store.get_current(source)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No snapshot for current 6-hour bucket")
    return snapshot


@router.get("/monitor/sources", response_model=list[MonitorSourceStatus])
def list_monitor_sources(
    service: MonitorAcquisitionService = Depends(get_monitor_acquisition_service),
) -> list[MonitorSourceStatus]:
    return service.source_status()


@router.post("/monitor/snapshots/{source}/refresh", response_model=MonitorDataSnapshot)
def refresh_monitor_snapshot(
    source: MonitorSource,
    service: MonitorAcquisitionService = Depends(get_monitor_acquisition_service),
) -> MonitorDataSnapshot:
    try:
        return service.get_or_refresh(source, force_refresh=True)
    except MonitorAcquisitionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
