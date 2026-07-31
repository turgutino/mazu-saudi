from __future__ import annotations

from fastapi import APIRouter

from app.data.monitor import get_monitor_regions
from app.schemas.monitor import MonitorRegionData

router = APIRouter(tags=["monitor"])


@router.get("/monitor/regions", response_model=list[MonitorRegionData])
def list_monitor_regions() -> list[MonitorRegionData]:
    return get_monitor_regions()
