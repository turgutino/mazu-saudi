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
ModelType = Literal["tree", "deep", "physical", "ensemble"]
ActivityType = Literal["prediction", "warning", "report"]
# Which of PredictionService's three data/model tiers produced a prediction's
# indicators (see prediction_service._resolve_indicators_and_model): a real
# trained model + archived NetCDF data, a real model + live forecast API
# data, or the fully synthetic placeholder. Persisted alongside each
# prediction so future dataset-building work can filter for high-quality
# (tier1_real) samples instead of mixing in synthetic placeholder data.
DataTier = Literal["tier1_real", "tier2_live", "tier3_synthetic"]
