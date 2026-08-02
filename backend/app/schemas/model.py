from __future__ import annotations

from .common import CamelModel, ModelType


class ModelMetrics(CamelModel):
    auc: float
    pod: float
    far: float
    csi: float
    f1: float
    brier: float


class ModelInfo(CamelModel):
    id: str
    name: str
    name_en: str
    version: str
    type: ModelType
    icon: str
    description: str
    description_en: str
    supported_hazards: list[str]
    last_trained: str
    metrics: dict[str, ModelMetrics]
