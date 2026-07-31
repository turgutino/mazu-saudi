"""In-process prediction store (v1).

A plain dict keyed by predictionId, indexed additionally by caseId. Good
enough for a single-process dev/demo backend; replace with a real database
repository later without changing the service-layer interface
(``services/prediction_service.py`` only calls ``save``/``get``/``list``).
"""

from __future__ import annotations

from app.schemas.prediction import PredictionResult


class PredictionStore:
    def __init__(self) -> None:
        self._by_id: dict[str, PredictionResult] = {}
        self._by_case_id: dict[str, str] = {}

    def save(self, prediction: PredictionResult) -> None:
        self._by_id[prediction.prediction_id] = prediction
        self._by_case_id[prediction.case_id] = prediction.prediction_id

    def get(self, prediction_id: str) -> PredictionResult | None:
        return self._by_id.get(prediction_id)

    def get_by_case_id(self, case_id: str) -> PredictionResult | None:
        prediction_id = self._by_case_id.get(case_id)
        return self._by_id.get(prediction_id) if prediction_id else None

    def list(
        self, region_id: str | None = None, hazard: str | None = None
    ) -> list[PredictionResult]:
        results = list(self._by_id.values())
        if region_id:
            results = [p for p in results if p.region_id == region_id]
        if hazard:
            results = [p for p in results if p.hazard == hazard]
        return sorted(results, key=lambda p: p.created_at, reverse=True)


prediction_store = PredictionStore()
