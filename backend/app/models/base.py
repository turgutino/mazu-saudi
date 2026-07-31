"""ForecastModel: the single interface every prediction algorithm must implement.

见 初步设计.md 第2节: 模型只负责 "输入特征 -> 输出预测"。To plug in a real
joblib/sklearn model or a rebuilt mcr_precip pipeline later, add a new class
implementing this Protocol and route to it by modelId in
services/prediction_service.py — the API layer never needs to change.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.forecast_case import ForecastCase
from app.domain.prediction import RawPrediction


class ForecastModel(Protocol):
    def predict(self, case: ForecastCase, indicators: dict[str, float]) -> RawPrediction:
        ...
