from __future__ import annotations

from fastapi import APIRouter

from app.data.regions import REGIONS
from app.schemas.region import Region

router = APIRouter(tags=["regions"])


@router.get("/regions", response_model=list[Region])
def list_regions() -> list[Region]:
    return REGIONS
