from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_monitor_snapshot_store
from app.data.monitor import get_monitor_regions
from app.repositories.monitor_snapshot_store import MonitorSnapshotStore
from app.schemas.monitor import (
    MonitorDataSnapshot,
    MonitorRegionData,
    MonitorSnapshotCreate,
    MonitorSource,
)

router = APIRouter(tags=["monitor"])


@router.get("/monitor/regions", response_model=list[MonitorRegionData])
def list_monitor_regions() -> list[MonitorRegionData]:
    return get_monitor_regions()


@router.get("/monitor/snapshots/{source}", response_model=MonitorDataSnapshot)
def get_monitor_snapshot(
    source: MonitorSource,
    store: MonitorSnapshotStore = Depends(get_monitor_snapshot_store),
) -> MonitorDataSnapshot:
    snapshot = store.get_current(source)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No snapshot for current 6-hour bucket")
    return snapshot


@router.post("/monitor/snapshots", response_model=MonitorDataSnapshot)
def save_monitor_snapshot(
    request: MonitorSnapshotCreate,
    store: MonitorSnapshotStore = Depends(get_monitor_snapshot_store),
) -> MonitorDataSnapshot:
    return store.save(request.source, request.data)
