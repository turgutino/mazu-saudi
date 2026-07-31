"""DegradedForecastModel: Tier 2 fallback ForecastModel for out-of-archive
dates.

When a ForecastCase's date falls outside the 2025 NetCDF archive (see
real_indicator_provider.py), the trained joblib models cannot be run (they
need indicators, like ivt/pwat/wind850_speed/neigh_*, that no live API
provides). This model instead scores the indicators OpenMeteoIndicatorProvider
/ MirrorEarthIndicatorProvider can supply live (cape, daily_precip, t2m,
rh_surface, wind_10m, visibility), plus -- when a Tomorrow.io call also
succeeds (see app/data/tomorrowio_provider.py) -- its derived risk indicators
(wind_gust, fire_index, thunderstorm_prob). Same linear-scoring-then-sigmoid
shape as RuleBasedForecastModel, just over a smaller, explicitly "degraded"
feature set -- so its lower fidelity is structural and disclosed via
model_name, not hidden. Any weighted key simply absent from ``indicators``
(e.g. Tomorrow.io wasn't configured/reachable) is skipped, never treated as 0.
"""

from __future__ import annotations

import math

from app.data.indicator_provider import normalized_severity
from app.domain.forecast_case import ForecastCase
from app.domain.prediction import RawPrediction

# Per-hazard weights, restricted to indicators available from a live
# Open-Meteo/Mirror Earth call (see openmeteo_provider.py,
# mirrorearth_provider.py) plus Tomorrow.io's enrichment fields
# (tomorrowio_provider.py) when present. A strict subset of
# rule_based_model.HAZARD_WEIGHTS's keys per hazard, plus the enrichment keys.
HAZARD_WEIGHTS: dict[str, dict[str, float]] = {
    "heavy-rain": {"cape": 0.9, "daily_precip": 1.0, "thunderstorm_prob": 0.4},
    "extreme-heat": {"t2m": 1.1, "rh_surface": 0.5, "fire_index": 0.3},
    "flash-flood": {"cape": 1.0, "daily_precip": 1.2, "thunderstorm_prob": 0.5},
    "dust-storm": {"wind_10m": 1.1, "visibility": 0.6, "rh_surface": 0.5, "wind_gust": 0.4},
}

HAZARD_BASE_SCORE: dict[str, float] = {
    "heavy-rain": -0.3,
    "extreme-heat": -0.3,
    "flash-flood": -0.35,
    "dust-storm": -0.5,
}

MODEL_ID = "degraded-live-v1"
MODEL_VERSION = "v1.0.0"
MODEL_NAME = "实时数据退化模型（有限指标）"


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _classify(probability: float) -> str:
    if probability >= 0.7:
        return "high"
    if probability >= 0.4:
        return "moderate"
    return "low"


class DegradedForecastModel:
    """Lightweight rule model over live-API-only indicators (Tier 2)."""

    model_id = MODEL_ID
    model_version = MODEL_VERSION
    model_name = MODEL_NAME

    def predict(self, case: ForecastCase, indicators: dict[str, float]) -> RawPrediction:
        weights = HAZARD_WEIGHTS.get(case.hazard, {})
        score = HAZARD_BASE_SCORE.get(case.hazard, -0.3)
        contributions: dict[str, float] = {}
        for key, weight in weights.items():
            if key not in indicators:
                continue
            contribution = weight * normalized_severity(key, indicators[key])
            contributions[key] = round(contribution, 4)
            score += contribution

        probability = round(_sigmoid(score), 4)
        # wider uncertainty band than the full rule-based/joblib models,
        # reflecting the smaller, live-only feature set backing this score.
        uncertainty = round(min(max(0.45 - 0.3 * abs(probability - 0.5), 0.15), 0.45), 4)

        return RawPrediction(
            model_id=self.model_id,
            model_version=self.model_version,
            model_name=self.model_name,
            probability=probability,
            uncertainty=uncertainty,
            predicted_class=_classify(probability),
            important_features=contributions,
        )


degraded_model = DegradedForecastModel()
