from __future__ import annotations

from .common import CamelModel, ConfidenceLevel, RiskLevel


class FeatureContribution(CamelModel):
    feature: str
    feature_label: str
    contribution: float
    normal_value: float
    actual_value: float
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


class MechanismPath(CamelModel):
    path_id: str
    path_name: str
    confidence: ConfidenceLevel
    steps: list[MechanismStep]


class HistoricalEvent(CamelModel):
    event_id: str
    date: str
    region: str
    hazard: str
    description: str
    similarity: float
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
    calibrated_probability: float
    predicted_class: str
    uncertainty: float
    features: list[FeatureContribution]
    rule_hits: list[RuleHit]
    mechanisms: list[MechanismPath]
    similar_events: list[HistoricalEvent]
    risk_level: RiskLevel
    risk_label: str
    risk_description: str
    input_hash: str
    created_at: str


class PredictionRequest(CamelModel):
    region_id: str
    hazard: str
    lead_time_hours: int
    model_id: str | None = None
    initial_time: str | None = None
