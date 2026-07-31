"""FastAPI dependency accessors.

v1 keeps all services as simple module-level singletons (see
services/prediction_service.py, repositories/prediction_store.py). These
thin ``Depends``-compatible functions are the only thing route modules
import, so swapping in per-request-scoped or app.state-backed instances
later doesn't require touching the routes.
"""

from __future__ import annotations

from app.repositories.prediction_store import PredictionStore, prediction_store
from app.services.prediction_service import PredictionService, prediction_service


def get_prediction_service() -> PredictionService:
    return prediction_service


def get_prediction_store() -> PredictionStore:
    return prediction_store
