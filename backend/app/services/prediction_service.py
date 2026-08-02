"""PredictionService: orchestrates ForecastCase -> model -> calibration ->
risk policy -> explanation -> PredictionResult (初步设计.md 全流程).

This is the single place that assembles the API-facing PredictionResult DTO
from the framework-agnostic domain layer. Routes never touch domain objects
directly; they only call this service and the repository it saves into.
"""

from __future__ import annotations

import math
import uuid
from datetime import date, datetime, timezone

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
from app.models.joblib_model import get_joblib_model
from app.models.live_api_model import get_live_api_model
from app.repositories.prediction_store import prediction_store
from app.risk.calibration import calibrate
from app.risk.policy import risk_policy
from app.schemas.common import DataTier, PredictionMode
from app.schemas.prediction import PredictionRequest, PredictionResult


class PredictionServiceError(ValueError):
    """Raised when a prediction request references unknown region/hazard/model."""


# Model display names are assigned inside each ForecastModel implementation
# (app/models/*.py) before risk policy / language selection runs. Rather
# than threading `lang` through the model interface (used identically by
# every ForecastModel and its tests), the English display name is resolved
# here as a pure display-layer lookup, keyed by the Chinese name the model
# layer always produces.
MODEL_NAME_EN: dict[str, str] = {
    "API兼容HGB-强降雨": "API-Compatible HGB - Heavy Rain",
    "API兼容HGB-高温": "API-Compatible HGB - Extreme Heat",
    "API兼容HGB-山洪": "API-Compatible HGB - Flash Flood",
    "API兼容HGB-沙尘暴": "API-Compatible HGB - Dust Storm",
    "HistGradientBoosting-高温": "HistGradientBoosting - Extreme Heat",
    "HistGradientBoosting-山洪": "HistGradientBoosting - Flash Flood",
    "HistGradientBoosting-沙尘暴": "HistGradientBoosting - Dust Storm",
    "确定性规则基线模型": "Deterministic Rule Baseline Model",
    "实时预报风险评分（规则基线）": "Real-time Forecast Risk Score (Rule Baseline)",
}


def _model_display_name(model_name: str, lang: str) -> str:
    return MODEL_NAME_EN.get(model_name, model_name) if lang == "en" else model_name


HISTORICAL_LEAD_TIME_HOURS = 24
HISTORICAL_FIRST_INITIAL_DATE = date(2025, 1, 1)
HISTORICAL_LAST_INITIAL_DATE = date(2025, 12, 30)


def _resolve_indicators_and_model(
    case: ForecastCase, prediction_mode: PredictionMode = "auto"
) -> tuple[dict[str, float], object, DataTier, str | None, str]:
    """Resolve either the historical full-feature or live API-feature ML model.

    Tier 1 (best): a real trained joblib model exists for this hazard AND the
    archived 2025 NetCDF indicators cover the feature date -> real data +
    real model.
    Live mode uses a 2025-trained HGB model whose feature contract can be
    reproduced from a complete trailing 24-hour third-party hourly forecast.
    Every external response and its derived indicators are persisted as an
    immutable forecast snapshot before inference and reused within its TTL.
    """
    joblib_model = get_joblib_model(case.hazard)
    if prediction_mode == "historical":
        if case.lead_time_hours != HISTORICAL_LEAD_TIME_HOURS:
            raise PredictionServiceError(
                "Historical replay only supports T+1 day (24 hours); "
                f"got {case.lead_time_hours} hours"
            )
        if not (
            HISTORICAL_FIRST_INITIAL_DATE
            <= case.initial_time.date()
            <= HISTORICAL_LAST_INITIAL_DATE
        ):
            raise PredictionServiceError(
                "Historical replay initial date must be between "
                "2025-01-01 and 2025-12-30 so the T+1 target remains in 2025"
            )
        if joblib_model is None:
            raise PredictionServiceError(
                f"No historical trained model for hazard: {case.hazard}"
            )
        if not real_data_available(case):
            raise PredictionServiceError(
                f"No archived indicators available for historical replay: {case.target_time.date()}"
            )
        return (
            real_indicator_provider.generate(case),
            joblib_model,
            "tier1_real",
            None,
            "era5-archive",
        )

    if (
        prediction_mode == "auto"
        and joblib_model is not None
        and real_data_available(case)
    ):
        return (
            real_indicator_provider.generate(case),
            joblib_model,
            "tier1_real",
            None,
            "era5-archive",
        )

    live_model = get_live_api_model(case.hazard)
    if live_model is None:
        raise PredictionServiceError(f"No live trained model for hazard: {case.hazard}")

    failures: list[str] = []
    if mirrorearth_configured():
        try:
            bundle = mirrorearth_provider.generate_bundle(case)
            if not live_model.available_features(case, bundle.indicators):
                raise MirrorEarthUnavailableError("missing required model features")
            return (
                bundle.indicators,
                live_model,
                "tier2_live",
                bundle.snapshot_id,
                bundle.source,
            )
        except MirrorEarthUnavailableError as exc:
            failures.append(f"Mirror Earth: {exc}")
    try:
        bundle = openmeteo_provider.generate_bundle(case)
        if not live_model.available_features(case, bundle.indicators):
            raise OpenMeteoUnavailableError("missing required model features")
        return (
            bundle.indicators,
            live_model,
            "tier2_live",
            bundle.snapshot_id,
            bundle.source,
        )
    except OpenMeteoUnavailableError as exc:
        failures.append(f"Open-Meteo: {exc}")

    raise PredictionServiceError(
        f"No complete live forecast feature set for hazard {case.hazard}. "
        + "; ".join(failures)
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

        # Historical full-feature model when its archive is explicitly used;
        # otherwise the hazard-specific API-compatible trained model. Result
        # metadata always identifies the model and forecast snapshot that ran.
        indicators, active_model, data_tier, snapshot_id, forecast_source = _resolve_indicators_and_model(
            case, request.prediction_mode
        )
        if request.model_id is not None and request.model_id != active_model.model_id:
            raise PredictionServiceError(
                f"Model {request.model_id} is incompatible with the resolved "
                f"{request.prediction_mode} route; expected {active_model.model_id}"
            )
        raw = active_model.predict(case, indicators)
        calibration = calibrate(raw.probability, case.hazard, raw.model_id)

        label_type = getattr(active_model, "label_type", "provided")
        is_proxy_label = label_type in {"proxy", "provided_proxy"}
        score_semantics = (
            "calibrated_hazard_probability"
            if calibration.is_calibrated
            else "uncalibrated_proxy_event_score"
            if is_proxy_label
            else "uncalibrated_event_score"
        )
        lang = request.lang if request.lang in ("zh", "en") else "zh"
        risk = risk_policy.assess(
            case,
            calibration.score,
            indicators,
            region,
            score_kind="proxy_score" if is_proxy_label else "model_score",
            lang=lang,
        )

        hazard_label = hazard.name_en if lang == "en" else hazard.name
        region_name = region.name_en if lang == "en" else region.name

        features = build_feature_contributions(raw, indicators, lang=lang)
        rule_hits = build_rule_hits(risk.rule_hits)
        mechanisms = build_mechanisms(case.hazard, case.region_id, indicators, lang=lang)
        similar_events = find_similar_events(
            case.hazard, case.region_id, case.initial_time, indicators, lang=lang
        )

        prediction_id = f"pred-{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc)

        result = PredictionResult(
            prediction_id=prediction_id,
            case_id=case.case_id,
            model_id=raw.model_id,
            model_version=raw.model_version,
            model_name=_model_display_name(raw.model_name, lang),
            hazard=hazard.id,
            hazard_label=hazard_label,
            region_id=region.id,
            region_name=region_name,
            target_time=case.target_time.isoformat(),
            lead_time_hours=case.lead_time_hours,
            initial_time=case.initial_time.isoformat(),
            probability=raw.probability,
            decision_score=calibration.score,
            score_semantics=score_semantics,
            calibration_method=calibration.method,
            is_calibrated=calibration.is_calibrated,
            predicted_class=raw.predicted_class,
            ambiguity=raw.ambiguity,
            ambiguity_method="heuristic_probability_margin",
            attribution_method=raw.attribution_method,
            attribution_output=raw.attribution_output,
            attribution_base_value=raw.attribution_base_value,
            attribution_model_output=raw.attribution_model_output,
            features=features,
            rule_hits=rule_hits,
            mechanisms=mechanisms,
            similar_events=similar_events,
            risk_level=risk.risk_level,
            risk_label=risk.risk_label,
            risk_description=risk.risk_description,
            input_hash=case.input_hash,
            created_at=created_at.isoformat(),
            raw_indicators={
                key: value if math.isfinite(float(value)) else None
                for key, value in indicators.items()
            },
            data_tier=data_tier,
            forecast_snapshot_id=snapshot_id,
            forecast_source=forecast_source,
            indicator_provenance_version="real-inputs-v1",
        )

        prediction_store.save(result)
        return result


prediction_service = PredictionService()
