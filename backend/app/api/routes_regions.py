from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from app.data.regions import REGIONS
from app.schemas.region import Region

router = APIRouter(tags=["regions"])


@router.get("/regions", response_model=list[Region])
def list_regions(lang: Literal["zh", "en"] = Query(default="zh")) -> list[Region]:
    if lang == "zh":
        return REGIONS
    return [region.model_copy(update={"name": region.name_en}) for region in REGIONS]
