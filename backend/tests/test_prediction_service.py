"""End-to-end tests for PredictionService across all 4 in-scope hazards."""

from __future__ import annotations

import pytest

from app.schemas.prediction import PredictionRequest
from app.services.prediction_service import PredictionService, PredictionServiceError

HAZARDS = ["heavy-rain", "extreme-heat", "flash-flood", "dust-storm"]


@pytest.fixture()
def service() -> PredictionService:
    return PredictionService()


@pytest.mark.parametrize("hazard", HAZARDS)
def test_run_prediction_produces_complete_result(service: PredictionService, hazard: str):
    request = PredictionRequest(region_id="jazan", hazard=hazard, lead_time_hours=24)
    result = service.run_prediction(request)

    assert result.hazard == hazard
    assert result.region_id == "jazan"
    assert 0.0 <= result.probability <= 1.0
    assert 0.0 <= result.calibrated_probability <= 1.0
    assert result.risk_level in {"green", "yellow", "orange", "red"}
    assert result.features, "expected at least one feature contribution"
    assert result.rule_hits, "expected at least one rule hit record"
    assert result.mechanisms, "expected at least one mechanism path"
    assert result.input_hash
    assert result.prediction_id and result.case_id


def test_run_prediction_uses_default_model_when_not_specified(service: PredictionService):
    request = PredictionRequest(region_id="jazan", hazard="heavy-rain", lead_time_hours=24)
    result = service.run_prediction(request)
    assert result.model_id


def test_run_prediction_respects_explicit_model_id(service: PredictionService):
    request = PredictionRequest(
        region_id="jazan", hazard="heavy-rain", lead_time_hours=24, model_id="xgb-v3"
    )
    result = service.run_prediction(request)
    assert result.model_id == "xgb-v3"


def test_run_prediction_rejects_unknown_region(service: PredictionService):
    request = PredictionRequest(region_id="atlantis", hazard="heavy-rain", lead_time_hours=24)
    with pytest.raises(PredictionServiceError):
        service.run_prediction(request)


def test_run_prediction_rejects_unknown_hazard(service: PredictionService):
    request = PredictionRequest(region_id="jazan", hazard="wildfire", lead_time_hours=24)
    with pytest.raises(PredictionServiceError):
        service.run_prediction(request)


def test_run_prediction_saves_to_store(service: PredictionService):
    from app.repositories.prediction_store import prediction_store

    request = PredictionRequest(region_id="riyadh", hazard="extreme-heat", lead_time_hours=48)
    result = service.run_prediction(request)
    assert prediction_store.get(result.prediction_id) is result
