"""Backfill verified model attribution into persisted legacy predictions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.forecast_case import ForecastCase
from app.explanation.feature_attribution import build_feature_contributions
from app.models.joblib_model import get_joblib_model
from app.models.live_api_model import get_live_api_model
from app.repositories.prediction_store import PredictionStore
from app.schemas.prediction import PredictionResult


@dataclass
class AttributionBackfillReport:
    total: int = 0
    migrated: list[str] = field(default_factory=list)
    unavailable: dict[str, str] = field(default_factory=dict)
    already_current: list[str] = field(default_factory=list)


def _matching_model(prediction: PredictionResult):
    if prediction.model_id.startswith("live-api-hgb-"):
        model = get_live_api_model(prediction.hazard)
    elif prediction.model_id.startswith("joblib-"):
        model = get_joblib_model(prediction.hazard)
    else:
        return None, "legacy_model_artifact_unavailable"

    if model is None or model.model_id != prediction.model_id:
        return None, "model_id_mismatch"
    if model.model_version != prediction.model_version:
        return None, "model_version_mismatch"
    missing = [name for name in model.features if name not in prediction.raw_indicators]
    if missing:
        return None, f"missing_inputs:{','.join(missing)}"
    return model, None


def _without_unverified_features(
    prediction: PredictionResult, reason: str
) -> PredictionResult:
    return prediction.model_copy(
        update={
            "features": [],
            "attribution_method": f"unavailable:{reason}",
            "attribution_output": None,
            "attribution_base_value": None,
            "attribution_model_output": None,
        }
    )


def _with_tree_shap(prediction: PredictionResult, model) -> PredictionResult:
    case = ForecastCase.create(
        case_id=prediction.case_id,
        region_id=prediction.region_id,
        hazard=prediction.hazard,
        lead_time_hours=prediction.lead_time_hours,
        initial_time=datetime.fromisoformat(prediction.initial_time),
    )
    raw = model.predict(case, prediction.raw_indicators)
    if abs(raw.probability - prediction.probability) > 0.00005:
        return _without_unverified_features(prediction, "probability_mismatch")
    return prediction.model_copy(
        update={
            "features": build_feature_contributions(raw, prediction.raw_indicators),
            "attribution_method": raw.attribution_method,
            "attribution_output": raw.attribution_output,
            "attribution_base_value": raw.attribution_base_value,
            "attribution_model_output": raw.attribution_model_output,
        }
    )


def backfill_prediction_attributions(
    store: PredictionStore, *, dry_run: bool = True
) -> AttributionBackfillReport:
    """Recompute attribution only with the exact recorded model artifact.

    Predictions from unavailable legacy models keep their prediction/risk data,
    but their misleading feature-contribution rows are removed.
    """

    predictions = store.list()
    report = AttributionBackfillReport(total=len(predictions))
    for prediction in predictions:
        if (
            prediction.attribution_method == "tree_shap"
            and prediction.attribution_base_value is not None
            and prediction.attribution_model_output is not None
        ):
            report.already_current.append(prediction.prediction_id)
            continue

        model, reason = _matching_model(prediction)
        if model is None:
            updated = _without_unverified_features(prediction, reason)
            report.unavailable[prediction.prediction_id] = reason
        else:
            updated = _with_tree_shap(prediction, model)
            if updated.attribution_method == "tree_shap":
                report.migrated.append(prediction.prediction_id)
            else:
                unavailable_reason = updated.attribution_method.removeprefix("unavailable:")
                report.unavailable[prediction.prediction_id] = unavailable_reason

        if not dry_run:
            store.save(updated)
    return report
