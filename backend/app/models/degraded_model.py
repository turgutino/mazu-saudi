"""LiveFusionForecastModel: transparent risk-score baseline for live forecasts.

When a ForecastCase's date falls outside the 2025 NetCDF archive (see
real_indicator_provider.py), the trained joblib models cannot be run (they
need indicators, like ivt/pwat/wind850_speed/neigh_*, that no live API
provides). This model scores the indicators OpenMeteoIndicatorProvider /
MirrorEarthIndicatorProvider can supply live (cape, trailing-24h
precipitation, t2m, rh_surface, wind_10m, visibility). It uses a transparent
linear-score-then-sigmoid baseline over this smaller live feature set. The
result is an uncalibrated risk score, not an observed-frequency probability.
Any weighted key absent from ``indicators`` is skipped, never treated as 0.
"""

from __future__ import annotations

import math

from app.data.indicator_provider import normalized_severity
from app.domain.forecast_case import ForecastCase
from app.domain.prediction import RawPrediction

# Per-hazard weights, restricted to indicators available from a live
# Open-Meteo/Mirror Earth call (see openmeteo_provider.py and
# mirrorearth_provider.py). A strict subset of
# rule_based_model.HAZARD_WEIGHTS's keys per hazard.
HAZARD_WEIGHTS: dict[str, dict[str, float]] = {
    "heavy-rain": {"cape": 0.9, "daily_precip": 1.0},
    "extreme-heat": {"t2m": 1.1, "rh_surface": 0.5},
    "flash-flood": {"cape": 1.0, "daily_precip": 1.2},
    "dust-storm": {"wind_10m": 1.1, "visibility": 0.6, "rh_surface": 0.5},
}

REQUIRED_FEATURES: dict[str, set[str]] = {
    "heavy-rain": {"daily_precip"},
    "extreme-heat": {"t2m"},
    "flash-flood": {"daily_precip"},
    "dust-storm": {"wind_10m"},
}

HAZARD_BASE_SCORE: dict[str, float] = {
    "heavy-rain": -0.3,
    "extreme-heat": -0.3,
    "flash-flood": -0.35,
    "dust-storm": -0.5,
}

MODEL_ID = "live-fusion-v1"
MODEL_VERSION = "v1.1.0"
MODEL_NAME = "实时预报风险评分（规则基线）"


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _classify(probability: float) -> str:
    if probability >= 0.7:
        return "high"
    if probability >= 0.4:
        return "moderate"
    return "low"


class LiveFusionForecastModel:
    """Fuse the real indicators available from live forecast providers."""

    model_id = MODEL_ID
    model_version = MODEL_VERSION
    model_name = MODEL_NAME

    def available_features(self, case: ForecastCase, indicators: dict[str, float]) -> set[str]:
        """Return live fields that can contribute to this hazard's score."""
        if not REQUIRED_FEATURES.get(case.hazard, set()).issubset(indicators):
            return set()
        return set(HAZARD_WEIGHTS.get(case.hazard, {})).intersection(indicators)

    def predict(self, case: ForecastCase, indicators: dict[str, float]) -> RawPrediction:
        weights = HAZARD_WEIGHTS.get(case.hazard, {})
        if not self.available_features(case, indicators):
            raise ValueError(f"No live fusion features available for hazard: {case.hazard}")
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


live_fusion_model = LiveFusionForecastModel()

# Compatibility aliases for callers outside the formal prediction route.
DegradedForecastModel = LiveFusionForecastModel
degraded_model = live_fusion_model
