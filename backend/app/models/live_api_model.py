"""Lightweight ML postprocessors for API-compatible live forecast features."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np

from app.data.live_feature_contract import MODEL_FEATURES
from app.domain.forecast_case import ForecastCase
from app.domain.prediction import RawPrediction
from app.explanation.tree_shap import TreeShapAttributor

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
META_PATH = ARTIFACTS_DIR / "live_api_model_meta.json"
MODEL_VERSION = "live-api-daily-v1"
HAZARD_TO_ARTIFACT = {
    "heavy-rain": "heavy_rain",
    "extreme-heat": "heatwave",
    "flash-flood": "flash_flood",
    "dust-storm": "dust_storm",
}
MODEL_NAMES = {
    "heavy-rain": "API兼容HGB-强降雨",
    "extreme-heat": "API兼容HGB-高温",
    "flash-flood": "API兼容HGB-山洪",
    "dust-storm": "API兼容HGB-沙尘暴",
}


def _classify(probability: float) -> str:
    if probability >= 0.7:
        return "high"
    if probability >= 0.4:
        return "moderate"
    return "low"


class LiveApiForecastModel:
    """Runs one 2025-trained HGB model on aggregated hourly API forecasts."""

    _meta_cache: dict | None = None

    def __init__(self, hazard: str):
        if hazard not in HAZARD_TO_ARTIFACT:
            raise ValueError(f"No live API model for hazard: {hazard}")
        self.hazard = hazard
        self.artifact_key = HAZARD_TO_ARTIFACT[hazard]
        self.model_id = f"live-api-hgb-{self.artifact_key}"
        self.model_version = MODEL_VERSION
        self.model_name = MODEL_NAMES[hazard]
        self._estimator = None
        self._attributor = None

    @classmethod
    def _meta(cls) -> dict:
        if cls._meta_cache is None:
            with open(META_PATH, encoding="utf-8") as handle:
                cls._meta_cache = json.load(handle)
        return cls._meta_cache

    @property
    def features(self) -> list[str]:
        features = self._meta()["features"]
        if features != MODEL_FEATURES:
            raise RuntimeError(
                f"Live model feature contract mismatch: artifact={features}, runtime={MODEL_FEATURES}"
            )
        return features

    @property
    def label_type(self) -> str:
        return self._meta()["models"][self.hazard]["label_type"]

    def _estimator_(self):
        if self._estimator is None:
            path = ARTIFACTS_DIR / f"live_api_{self.artifact_key}_model.joblib"
            self._estimator = joblib.load(path)
        return self._estimator

    def _attributor_(self) -> TreeShapAttributor:
        if self._attributor is None:
            self._attributor = TreeShapAttributor(self._estimator_(), self.features)
        return self._attributor

    def available_features(
        self, case: ForecastCase, indicators: dict[str, float]
    ) -> bool:
        return case.hazard == self.hazard and all(
            feature in indicators for feature in self.features
        )

    def predict(self, case: ForecastCase, indicators: dict[str, float]) -> RawPrediction:
        missing = [feature for feature in self.features if feature not in indicators]
        if missing:
            raise ValueError(f"Missing required features for {self.model_id}: {missing}")
        row = np.array(
            [[indicators[feature] for feature in self.features]], dtype="float64"
        )
        probability = round(float(self._estimator_().predict_proba(row)[0, 1]), 4)
        attribution = self._attributor_().explain(row)
        ambiguity = round(
            min(max(0.35 - 0.4 * abs(probability - 0.5), 0.05), 0.35), 4
        )
        return RawPrediction(
            model_id=self.model_id,
            model_version=self.model_version,
            model_name=self.model_name,
            probability=probability,
            ambiguity=ambiguity,
            predicted_class=_classify(probability),
            important_features=attribution.values,
            attribution_method=attribution.method,
            attribution_output=attribution.output_scale,
            attribution_base_value=attribution.base_value,
            attribution_model_output=attribution.model_output,
        )


_INSTANCES: dict[str, LiveApiForecastModel] = {}


def get_live_api_model(hazard: str) -> LiveApiForecastModel | None:
    if hazard not in HAZARD_TO_ARTIFACT:
        return None
    if hazard not in _INSTANCES:
        _INSTANCES[hazard] = LiveApiForecastModel(hazard)
    return _INSTANCES[hazard]
