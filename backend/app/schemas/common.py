"""Shared literal types and a common Pydantic base model.

All API-facing schemas use camelCase JSON field names to align exactly with
the TypeScript interfaces in ``frontend/src/mocks/*.ts``. Python code should
use snake_case attribute names; the ``CamelModel`` base takes care of the
camelCase (de)serialization via field aliases.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


def to_camel(snake: str) -> str:
    first, *rest = snake.split("_")
    return first + "".join(word.capitalize() for word in rest)


class CamelModel(BaseModel):
    """Base model that (de)serializes using camelCase aliases."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


RiskLevel = Literal["green", "yellow", "orange", "red"]
SensitivityLevel = Literal["high", "medium", "low"]
ConfidenceLevel = Literal["high", "medium", "low"]
TrendLevel = Literal["rising", "stable", "falling"]
ModelType = Literal["tree", "deep", "physical", "ensemble", "rule"]
ActivityType = Literal["prediction", "warning", "report"]
PredictionMode = Literal["auto", "live", "historical"]
ScoreSemantics = Literal[
    "uncalibrated_event_score",
    "uncalibrated_proxy_event_score",
    "calibrated_hazard_probability",
]
CalibrationMethod = Literal["none", "platt", "isotonic"]
AmbiguityMethod = Literal["heuristic_probability_margin"]
# Which input/model path produced a prediction. ``tier3_synthetic`` remains
# only so legacy and test records can still be read; PredictionService no
# longer emits it.
DataTier = Literal["tier1_real", "tier2_live", "tier3_synthetic"]
