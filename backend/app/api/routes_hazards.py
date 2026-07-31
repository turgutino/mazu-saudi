from __future__ import annotations

from fastapi import APIRouter

from app.data.hazards import HAZARDS
from app.schemas.hazard import HazardType

router = APIRouter(tags=["hazards"])


@router.get("/hazards", response_model=list[HazardType])
def list_hazards() -> list[HazardType]:
    return HAZARDS
