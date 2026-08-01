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
from app.data.mirrorearth_provider import MirrorEarthUnavailableError, mirrorearth_provider
from app.data.mirrorearth_provider import is_configured as mirrorearth_configured
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
from app.models.degraded_model import live_fusion_model
from app.models.joblib_model import get_joblib_model
from app.repositories.prediction_store import prediction_store
from app.risk.calibration import calibrate
from app.risk.policy import risk_policy
from app.schemas.common import DataTier, PredictionMode
from app.schemas.prediction import PredictionRequest, PredictionResult


class PredictionServiceError(ValueError):
    """Raised when a prediction request references unknown region/hazard/model."""


def _resolve_indicators_and_model(
    case: ForecastCase, prediction_mode: PredictionMode = "auto"
) -> tuple[dict[str, float], object, DataTier]:
    """Resolve either the historical ML model or the live fusion model.

    Tier 1 (best): a real trained joblib model exists for this hazard AND the
    archived 2025 NetCDF indicators cover the feature date -> real data +
    real model.
    Live fusion: every hazard whose historical ML inputs are unavailable uses
    a live *forecast-model* indicator source, tried in order
    of forecast fidelity -- Mirror Earth's CMA numerical model first (a real
    NWP model, closer in spirit to Tier 1's archive), Open-Meteo's blended
    forecast second -- plus LiveFusionForecastModel (the joblib models cannot
    run on either's much smaller feature set). Tomorrow.io's realtime fields
    are deliberately excluded because they are not valid at a 6--72 hour
    forecast target time.
    Returns (indicators, model, data_tier) -- ``data_tier`` is persisted on
    the resulting PredictionResult for future dataset-building (see
    app.schemas.common.DataTier).
    """
    joblib_model = get_joblib_model(case.hazard)
    if prediction_mode == "historical":
        if joblib_model is None:
            raise PredictionServiceError(
                f"No historical trained model for hazard: {case.hazard}"
            )
        if not real_data_available(case):
            raise PredictionServiceError(
                f"No archived indicators available for historical replay: {case.target_time.date()}"
            )
        return real_indicator_provider.generate(case), joblib_model, "tier1_real"

    if (
        prediction_mode == "auto"
        and joblib_model is not None
        and real_data_available(case)
    ):
        return real_indicator_provider.generate(case), joblib_model, "tier1_real"

    if mirrorearth_configured():
        try:
            indicators = mirrorearth_provider.generate(case)
            if live_fusion_model.available_features(case, indicators):
                return indicators, live_fusion_model, "tier2_live"
        except MirrorEarthUnavailableError:
            pass
    try:
        indicators = openmeteo_provider.generate(case)
        if live_fusion_model.available_features(case, indicators):
            return indicators, live_fusion_model, "tier2_live"
    except OpenMeteoUnavailableError:
        pass

    raise PredictionServiceError(
        f"No live forecast indicators available for hazard: {case.hazard}"
    )


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

        # Historical trained model when its archived feature contract is
        # available, otherwise the live fusion model. The optional request
        # modelId remains a known-model validation hint for API compatibility;
        # result metadata always identifies the model that actually ran.
        indicators, active_model, data_tier = _resolve_indicators_and_model(
            case, request.prediction_mode
        )
        raw = active_model.predict(case, indicators)
        calibrated_probability = calibrate(raw.probability, case.hazard, raw.model_id)

        score_kind = "risk_score" if raw.model_id == live_fusion_model.model_id else "probability"
        risk = risk_policy.assess(
            case, calibrated_probability, indicators, region, score_kind=score_kind
        )

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
            model_id=raw.model_id,
            model_version=raw.model_version,
            model_name=raw.model_name,
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
            raw_indicators=indicators,
            data_tier=data_tier,
        )

        prediction_store.save(result)
        return result


prediction_service = PredictionService()
