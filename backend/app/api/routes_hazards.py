from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from app.data.hazards import HAZARDS
from app.schemas.hazard import HazardType

router = APIRouter(tags=["hazards"])


@router.get("/hazards", response_model=list[HazardType])
def list_hazards(lang: Literal["zh", "en"] = Query(default="zh")) -> list[HazardType]:
    if lang == "zh":
        return HAZARDS
    return [
        hazard.model_copy(update={"name": hazard.name_en, "description": hazard.description_en})
        for hazard in HAZARDS
    ]
