from __future__ import annotations

from .common import CamelModel, ConfidenceLevel, DataTier, PredictionMode, RiskLevel


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
    calibrated_probability: float
    predicted_class: str
    uncertainty: float
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


class PredictionRequest(CamelModel):
    region_id: str
    hazard: str
    lead_time_hours: int
    model_id: str | None = None
    initial_time: str | None = None
    prediction_mode: PredictionMode = "auto"
