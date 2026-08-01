from __future__ import annotations

from typing import Any

from pydantic import model_validator

from .common import (
    AmbiguityMethod,
    CalibrationMethod,
    CamelModel,
    ConfidenceLevel,
    DataTier,
    PredictionMode,
    RiskLevel,
    ScoreSemantics,
)


class FeatureContribution(CamelModel):
    feature: str
    feature_label: str
    contribution: float
    normal_value: float | None = None
    actual_value: float | None = None
    unit: str


class RuleHit(CamelModel):
    rule_id: str
    rule_name: str
    condition: str
    actual_value: str
    threshold: str
    met: bool
    weight: float


class MechanismStep(CamelModel):
    step: int
    description: str
    indicator: str
    value: str
    compatibility: float


class MechanismPath(CamelModel):
    path_id: str
    path_name: str
    confidence: ConfidenceLevel
    support_score: float
    summary: str
    evidence_ids: list[str]
    steps: list[MechanismStep]


class SimilarityDimension(CamelModel):
    key: str
    label: str
    score: float
    weight: float
    explanation: str


class HistoricalEvent(CamelModel):
    event_id: str
    date: str
    region: str
    hazard: str
    description: str
    similarity: float
    similarity_dimensions: list[SimilarityDimension]
    data_coverage: float
    verification_status: str
    source_title: str
    source_url: str | None = None
    max_rainfall: float | None = None
    max_temp: float | None = None
    impact: str


class PredictionResult(CamelModel):
    prediction_id: str
    case_id: str
    model_id: str
    model_version: str
    model_name: str
    hazard: str
    hazard_label: str
    region_id: str
    region_name: str
    target_time: str
    lead_time_hours: int
    initial_time: str
    probability: float
    decision_score: float
    score_semantics: ScoreSemantics
    calibration_method: CalibrationMethod
    is_calibrated: bool
    predicted_class: str
    ambiguity: float
    ambiguity_method: AmbiguityMethod
    attribution_method: str | None = None
    attribution_output: str | None = None
    attribution_base_value: float | None = None
    attribution_model_output: float | None = None
    features: list[FeatureContribution]
    rule_hits: list[RuleHit]
    mechanisms: list[MechanismPath]
    similar_events: list[HistoricalEvent]
    risk_level: RiskLevel
    risk_label: str
    risk_description: str
    input_hash: str
    created_at: str
    # Dataset-building provenance (not shown in the current UI): the raw
    # indicator dict actually fed to the model (distinct from `features`,
    # which are post-hoc contribution scores), and which of the 3 tiers
    # produced it. See app.schemas.common.DataTier.
    raw_indicators: dict[str, float | None] = {}
    data_tier: DataTier
    forecast_snapshot_id: str | None = None
    forecast_source: str | None = None
    indicator_provenance_version: str | None = None

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_score_fields(cls, value: Any) -> Any:
        """Read stored v1 payloads without re-labelling their numeric output.

        Older rows called an identity-transformed score ``calibratedProbability``
        and a probability-margin heuristic ``uncertainty``. They are mapped to
        the explicit v2 semantics on read; the persisted numeric values do not
        change.
        """
        if not isinstance(value, dict):
            return value
        data = dict(value)
        model_id = str(data.get("model_id", data.get("modelId", "")))
        if "decision_score" not in data and "decisionScore" not in data:
            legacy_score = data.get(
                "calibrated_probability", data.get("calibratedProbability", data.get("probability"))
            )
            data["decision_score"] = legacy_score
        if "ambiguity" not in data:
            data["ambiguity"] = data.get("uncertainty", 0.0)
        data.setdefault("calibration_method", data.get("calibrationMethod", "none"))
        data.setdefault("is_calibrated", data.get("isCalibrated", False))
        data.setdefault("ambiguity_method", data.get("ambiguityMethod", "heuristic_probability_margin"))
        if "score_semantics" not in data and "scoreSemantics" not in data:
            is_proxy = (
                model_id.startswith("live-api-hgb-") and not model_id.endswith("heatwave")
            ) or model_id in {"joblib-flash_flood", "joblib-dust_storm"}
            data["score_semantics"] = (
                "uncalibrated_proxy_event_score" if is_proxy else "uncalibrated_event_score"
            )
        return data

    @property
    def calibrated_probability(self) -> float:
        """Deprecated Python compatibility alias; not emitted in API JSON."""
        return self.decision_score

    @property
    def uncertainty(self) -> float:
        """Deprecated Python compatibility alias; not emitted in API JSON."""
        return self.ambiguity


class PredictionRequest(CamelModel):
    region_id: str
    hazard: str
    lead_time_hours: int
    model_id: str | None = None
    initial_time: str | None = None
    prediction_mode: PredictionMode = "auto"
