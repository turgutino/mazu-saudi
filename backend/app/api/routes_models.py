from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from app.data.models import MODELS
from app.schemas.model import ModelInfo

router = APIRouter(tags=["models"])


@router.get("/models", response_model=list[ModelInfo])
def list_models(lang: Literal["zh", "en"] = Query(default="zh")) -> list[ModelInfo]:
    if lang == "zh":
        return MODELS
    return [
        model.model_copy(update={"name": model.name_en, "description": model.description_en})
        for model in MODELS
    ]
