"""PredictionService: orchestrates ForecastCase -> model -> calibration ->
risk policy -> explanation -> PredictionResult (初步设计.md 全流程).

This is the single place that assembles the API-facing PredictionResult DTO
from the framework-agnostic domain layer. Routes never touch domain objects
directly; they only call this service and the repository it saves into.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.data.hazards import get_hazard
from app.data.indicator_provider import indicator_provider
from app.data.models import DEFAULT_MODEL_ID, get_model
from app.data.openmeteo_provider import OpenMeteoUnavailableError, openmeteo_provider
from app.data.real_indicator_provider import available_for as real_data_available
from app.data.real_indicator_provider import real_indicator_provider
from app.data.regions import get_region
from app.domain.forecast_case import ForecastCase
from app.explanation.feature_attribution import build_feature_contributions
from app.explanation.mechanism_explanation import build_mechanisms
from app.explanation.rule_explanation import build_rule_hits
from app.explanation.similar_events import find_similar_events
from app.models.degraded_model import degraded_model
from app.models.joblib_model import get_joblib_model
from app.models.rule_based_model import rule_based_model
from app.repositories.prediction_store import prediction_store
from app.risk.calibration import calibrate
from app.risk.policy import risk_policy
from app.schemas.prediction import PredictionRequest, PredictionResult


class PredictionServiceError(ValueError):
    """Raised when a prediction request references unknown region/hazard/model."""


def _resolve_indicators_and_model(case: ForecastCase) -> tuple[dict[str, float], object]:
    """Three-tier resolution (see 初步设计.md real-data integration notes):

    Tier 1 (best): a real trained joblib model exists for this hazard AND the
    archived 2025 NetCDF indicators cover the feature date -> real data +
    real model.
    Tier 2 (degraded): a real trained model exists but the date falls outside
    the archive -> live Open-Meteo indicators + DegradedForecastModel (the
    joblib models cannot run on Open-Meteo's much smaller feature set).
    Tier 3 (placeholder): heavy-rain (no trained model at all), or Tier 2's
    live API call fails -> synthetic IndicatorProvider + RuleBasedForecastModel.
    """
    joblib_model = get_joblib_model(case.hazard)
    if joblib_model is not None and real_data_available(case):
        return real_indicator_provider.generate(case), joblib_model

    if joblib_model is not None:
        try:
            return openmeteo_provider.generate(case), degraded_model
        except OpenMeteoUnavailableError:
            pass

    return indicator_provider.generate(case), rule_based_model


class PredictionService:
    def run_prediction(self, request: PredictionRequest) -> PredictionResult:
        region = get_region(request.region_id)
        if region is None:
            raise PredictionServiceError(f"Unknown regionId: {request.region_id}")

        hazard = get_hazard(request.hazard)
        if hazard is None:
            raise PredictionServiceError(f"Unknown hazard: {request.hazard}")

        model_id = request.model_id or DEFAULT_MODEL_ID
        model_info = get_model(model_id)
        if model_info is None:
            raise PredictionServiceError(f"Unknown modelId: {model_id}")

        initial_time = (
            datetime.fromisoformat(request.initial_time.replace("Z", "+00:00"))
            if request.initial_time
            else datetime.now(timezone.utc)
        )

        case_id = f"case-{uuid.uuid4().hex[:12]}"
        case = ForecastCase.create(
            case_id=case_id,
            region_id=request.region_id,
            hazard=request.hazard,
            lead_time_hours=request.lead_time_hours,
            initial_time=initial_time,
        )

        # Three-tier resolution: real trained model + archived NetCDF data
        # when available, else a degraded live-data model, else the fully
        # synthetic placeholder (see _resolve_indicators_and_model above).
        # The requested/displayed modelId (model_info) only affects
        # PredictionResult's model_id/version/name metadata below -- it does
        # not select the algorithm, matching v1's existing modelId semantics.
        indicators, active_model = _resolve_indicators_and_model(case)
        raw = active_model.predict(case, indicators)
        calibrated_probability = calibrate(raw.probability, case.hazard, model_info.id)

        risk = risk_policy.assess(case, calibrated_probability, indicators, region)

        features = build_feature_contributions(raw, indicators)
        rule_hits = build_rule_hits(risk.rule_hits)
        mechanisms = build_mechanisms(case.hazard, case.region_id, indicators)
        similar_events = find_similar_events(
            case.hazard, case.region_id, case.initial_time, indicators
        )

        prediction_id = f"pred-{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc)

        result = PredictionResult(
            prediction_id=prediction_id,
            case_id=case.case_id,
            model_id=model_info.id,
            model_version=model_info.version,
            model_name=model_info.name,
            hazard=hazard.id,
            hazard_label=hazard.name,
            region_id=region.id,
            region_name=region.name,
            target_time=case.target_time.isoformat(),
            lead_time_hours=case.lead_time_hours,
            initial_time=case.initial_time.isoformat(),
            probability=raw.probability,
            calibrated_probability=calibrated_probability,
            predicted_class=raw.predicted_class,
            uncertainty=raw.uncertainty,
            features=features,
            rule_hits=rule_hits,
            mechanisms=mechanisms,
            similar_events=similar_events,
            risk_level=risk.risk_level,
            risk_label=risk.risk_label,
            risk_description=risk.risk_description,
            input_hash=case.input_hash,
            created_at=created_at.isoformat(),
        )

        prediction_store.save(result)
        return result


prediction_service = PredictionService()
