from __future__ import annotations

from fastapi import APIRouter

from app.data.models import MODELS
from app.schemas.model import ModelInfo

router = APIRouter(tags=["models"])


@router.get("/models", response_model=list[ModelInfo])
def list_models() -> list[ModelInfo]:
    return MODELS
