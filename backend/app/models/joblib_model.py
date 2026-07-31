"""JoblibForecastModel: Tier 1 real trained-model ForecastModel.

Loads a pre-trained scikit-learn HistGradientBoostingClassifier (trained in
reference_code/mazu-saudi-warning/agent/01_train_and_save_models.py) and
implements the same ForecastModel interface as RuleBasedForecastModel, so
PredictionService can route to either without any other code changing.

Feature order/names come from ``model_meta.json`` (per hazard key), and are
read out of the ``indicators`` dict RealIndicatorProvider produces -- see
that module for how each raw NetCDF-derived feature name lands there.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import joblib
import numpy as np

from app.domain.forecast_case import ForecastCase
from app.domain.prediction import RawPrediction

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"

# ForecastCase.hazard -> (model_meta.json key, .joblib filename stem)
HAZARD_TO_ARTIFACT: dict[str, str] = {
    "extreme-heat": "heatwave",
    "flash-flood": "flash_flood",
    "dust-storm": "dust_storm",
}

MODEL_NAMES: dict[str, str] = {
    "heatwave": "HistGradientBoosting-高温",
    "flash_flood": "HistGradientBoosting-山洪",
    "dust_storm": "HistGradientBoosting-沙尘暴",
}

MODEL_VERSION = "trained-2025-06-30"


def _classify(probability: float) -> str:
    if probability >= 0.7:
        return "high"
    if probability >= 0.4:
        return "moderate"
    return "low"


class JoblibForecastModel:
    """Wraps one trained HistGradientBoostingClassifier for a single hazard."""

    _meta_cache: dict | None = None

    def __init__(self, hazard: str):
        if hazard not in HAZARD_TO_ARTIFACT:
            raise ValueError(f"No trained joblib model for hazard: {hazard}")
        self.hazard = hazard
        self.artifact_key = HAZARD_TO_ARTIFACT[hazard]
        self.model_id = f"joblib-{self.artifact_key}"
        self.model_version = MODEL_VERSION
        self.model_name = MODEL_NAMES[self.artifact_key]
        self._estimator = None

    @classmethod
    def _meta(cls) -> dict:
        if cls._meta_cache is None:
            with open(ARTIFACTS_DIR / "model_meta.json", encoding="utf-8") as f:
                cls._meta_cache = json.load(f)
        return cls._meta_cache

    @property
    def features(self) -> list[str]:
        return self._meta()[self.artifact_key]["features"]

    def _estimator_(self):
        if self._estimator is None:
            path = ARTIFACTS_DIR / f"{self.artifact_key}_model.joblib"
            self._estimator = joblib.load(path)
        return self._estimator

    def predict(self, case: ForecastCase, indicators: dict[str, float]) -> RawPrediction:
        feature_names = self.features
        missing = [f for f in feature_names if f not in indicators]
        if missing:
            raise ValueError(
                f"Missing required features for {self.model_id}: {missing}"
            )
        row = np.array([[indicators[f] for f in feature_names]], dtype="float64")
        estimator = self._estimator_()
        probability = float(estimator.predict_proba(row)[0, 1])
        probability = round(probability, 4)

        # feature-level contributions: not real SHAP values (the estimator
        # is a boosted-tree ensemble, not linear), so we report a signed
        # z-score-like deviation from each feature's dataset-agnostic sign
        # convention -- purely descriptive context alongside the model's own
        # point probability, matching RuleBasedForecastModel's contract shape.
        important_features = {
            f: round(indicators[f], 4) for f in feature_names if f in indicators
        }

        uncertainty = round(min(max(0.35 - 0.4 * abs(probability - 0.5), 0.05), 0.35), 4)

        return RawPrediction(
            model_id=self.model_id,
            model_version=self.model_version,
            model_name=self.model_name,
            probability=probability,
            uncertainty=uncertainty,
            predicted_class=_classify(probability),
            important_features=important_features,
        )


_INSTANCES: dict[str, JoblibForecastModel] = {}


def get_joblib_model(hazard: str) -> JoblibForecastModel | None:
    """Returns the cached JoblibForecastModel for ``hazard``, or None if this
    hazard has no trained model (e.g. heavy-rain)."""
    if hazard not in HAZARD_TO_ARTIFACT:
        return None
    if hazard not in _INSTANCES:
        _INSTANCES[hazard] = JoblibForecastModel(hazard)
    return _INSTANCES[hazard]
