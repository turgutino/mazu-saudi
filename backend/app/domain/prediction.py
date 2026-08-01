"""Internal RawPrediction: the pure output of a ForecastModel.

Deliberately separate from ``app.schemas.prediction.PredictionResult`` (the
API DTO). RawPrediction only carries what a model is allowed to produce:
probability, uncertainty and per-feature contributions. Calibration and risk
decisions are layered on top of it by other components (see risk/*.py), never
inside the model itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RawPrediction:
    model_id: str
    model_version: str
    model_name: str
    probability: float
    uncertainty: float
    predicted_class: str
    important_features: dict[str, float] = field(default_factory=dict)
    attribution_method: str | None = None
    attribution_output: str | None = None
    attribution_base_value: float | None = None
    attribution_model_output: float | None = None
