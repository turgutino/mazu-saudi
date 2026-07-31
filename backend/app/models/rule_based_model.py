"""RuleBasedForecastModel: the v1 deterministic placeholder ForecastModel.

Implements the same interface (ForecastModel) for all 4 in-scope hazards.
No training, no sklearn/joblib — this is a transparent, hand-tuned linear
scoring formula over the indicators produced by IndicatorProvider, run
through a logistic link. It exists so the rest of the architecture (risk
policy, explanation, knowledge graph, API) can be built and tested end to
end; it is the single, explicit point to replace with a real trained model
(see reference_code/mazu-saudi-warning) later, routed by modelId.
"""

from __future__ import annotations

import math

from app.data.indicator_provider import INDICATOR_SPECS
from app.domain.forecast_case import ForecastCase
from app.domain.prediction import RawPrediction

# per-hazard indicator weights and baseline logit offset.
HAZARD_WEIGHTS: dict[str, dict[str, float]] = {
    "heavy-rain": {
        "cape": 0.9, "pw": 0.8, "daily_precip": 1.0,
        "vapor_850": 0.6, "shear_500": 0.4, "rh_700": 0.5,
    },
    "extreme-heat": {
        "t850": 0.7, "t2m": 1.1, "rh_surface": 0.5, "h500": 0.6,
    },
    "flash-flood": {
        "cape": 1.0, "pw": 0.9, "daily_precip": 1.2,
        "vapor_850": 0.6, "rh_700": 0.5,
    },
    "dust-storm": {
        "wind_10m": 1.1, "soil_moisture": 0.7, "visibility": 0.6, "rh_surface": 0.5,
    },
}

HAZARD_BASE_SCORE: dict[str, float] = {
    "heavy-rain": -0.3,
    "extreme-heat": -0.3,
    "flash-flood": -0.35,
    "dust-storm": -0.5,
}

MODEL_ID = "rule-based-v1"
MODEL_VERSION = "v1.0.0"
MODEL_NAME = "确定性规则基线模型"


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _normalized(key: str, actual: float) -> float:
    spec = INDICATOR_SPECS[key]
    span = spec.max_value - spec.min_value
    return spec.direction * (actual - spec.normal_value) / span


def _classify(probability: float) -> str:
    if probability >= 0.7:
        return "high"
    if probability >= 0.4:
        return "moderate"
    return "low"


class RuleBasedForecastModel:
    """Deterministic, explainable placeholder implementation of ForecastModel."""

    model_id = MODEL_ID
    model_version = MODEL_VERSION
    model_name = MODEL_NAME

    def predict(self, case: ForecastCase, indicators: dict[str, float]) -> RawPrediction:
        weights = HAZARD_WEIGHTS[case.hazard]
        score = HAZARD_BASE_SCORE[case.hazard]
        contributions: dict[str, float] = {}
        for key, weight in weights.items():
            contribution = weight * _normalized(key, indicators[key])
            contributions[key] = round(contribution, 4)
            score += contribution

        probability = round(_sigmoid(score), 4)
        # decisive predictions (far from 0.5) carry lower uncertainty.
        uncertainty = round(min(max(0.35 - 0.4 * abs(probability - 0.5), 0.05), 0.35), 4)

        return RawPrediction(
            model_id=self.model_id,
            model_version=self.model_version,
            model_name=self.model_name,
            probability=probability,
            uncertainty=uncertainty,
            predicted_class=_classify(probability),
            important_features=contributions,
        )


rule_based_model = RuleBasedForecastModel()
