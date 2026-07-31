from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_prediction_service, get_prediction_store
from app.repositories.prediction_store import PredictionStore
from app.schemas.prediction import PredictionRequest, PredictionResult
from app.services.prediction_service import PredictionService, PredictionServiceError

router = APIRouter(tags=["predictions"])


@router.post("/predictions", response_model=PredictionResult)
def create_prediction(
    request: PredictionRequest,
    service: PredictionService = Depends(get_prediction_service),
) -> PredictionResult:
    try:
        return service.run_prediction(request)
    except PredictionServiceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/predictions", response_model=list[PredictionResult])
def list_predictions(
    region_id: str | None = Query(default=None, alias="regionId"),
    hazard: str | None = Query(default=None),
    store: PredictionStore = Depends(get_prediction_store),
) -> list[PredictionResult]:
    return store.list(region_id=region_id, hazard=hazard)


@router.get("/predictions/{prediction_id}", response_model=PredictionResult)
def get_prediction(
    prediction_id: str,
    store: PredictionStore = Depends(get_prediction_store),
) -> PredictionResult:
    result = store.get(prediction_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Prediction not found: {prediction_id}")
    return result
