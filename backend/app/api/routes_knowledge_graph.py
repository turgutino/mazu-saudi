from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_forecast_snapshot_store, get_prediction_store
from app.knowledge_graph.graph_builder import build_graph
from app.repositories.prediction_store import PredictionStore
from app.repositories.forecast_snapshot_store import ForecastSnapshotStore
from app.schemas.graph import KnowledgeGraph

router = APIRouter(tags=["knowledge-graph"])


@router.get("/knowledge-graph/{prediction_id}", response_model=KnowledgeGraph)
def get_knowledge_graph(
    prediction_id: str,
    store: PredictionStore = Depends(get_prediction_store),
    snapshot_store: ForecastSnapshotStore = Depends(get_forecast_snapshot_store),
) -> KnowledgeGraph:
    prediction = store.get(prediction_id)
    if prediction is None:
        raise HTTPException(status_code=404, detail=f"Prediction not found: {prediction_id}")
    snapshot = (
        snapshot_store.get(prediction.forecast_snapshot_id)
        if prediction.forecast_snapshot_id
        else None
    )
    return build_graph(prediction, forecast_snapshot=snapshot)
