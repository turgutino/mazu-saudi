"""Static model registry.

Metadata (metrics, versions, descriptions) mirrors frontend/src/mocks/models.ts
for presentation purposes only. The requested/displayed modelId here does NOT
select the prediction algorithm — PredictionService (services/prediction_service.py)
independently routes to RuleBasedForecastModel / DegradedForecastModel /
JoblibForecastModel based on hazard + real-data availability (see
_resolve_indicators_and_model). supportedHazards is restricted to the 4
hazards implemented in v1 (severe-convection dropped from the original
frontend mock).
"""

from __future__ import annotations

from app.schemas.model import ModelInfo, ModelMetrics

MODELS: list[ModelInfo] = [
    ModelInfo(
        id="xgb-v3", name="XGBoost", version="v3.2.1", type="tree",
        icon="ri-braces-line",
        description="梯度提升树模型，擅长处理表格气象特征，训练速度快，可解释性好。",
        supported_hazards=["heavy-rain", "extreme-heat", "flash-flood"],
        last_trained="2026-07-15",
        metrics={
            "heavy-rain": ModelMetrics(auc=0.891, pod=0.842, far=0.183, csi=0.714, f1=0.827, brier=0.078),
            "extreme-heat": ModelMetrics(auc=0.937, pod=0.905, far=0.094, csi=0.831, f1=0.903, brier=0.042),
            "flash-flood": ModelMetrics(auc=0.864, pod=0.798, far=0.227, csi=0.658, f1=0.781, brier=0.089),
        },
    ),
    ModelInfo(
        id="lgbm-v2", name="LightGBM", version="v2.8.0", type="tree",
        icon="ri-stack-line",
        description="轻量级梯度提升模型，内存占用低，训练和推理速度极快。",
        supported_hazards=["heavy-rain", "extreme-heat", "dust-storm"],
        last_trained="2026-07-20",
        metrics={
            "heavy-rain": ModelMetrics(auc=0.882, pod=0.831, far=0.195, csi=0.698, f1=0.814, brier=0.083),
            "extreme-heat": ModelMetrics(auc=0.941, pod=0.912, far=0.088, csi=0.842, f1=0.911, brier=0.039),
            "dust-storm": ModelMetrics(auc=0.865, pod=0.791, far=0.224, csi=0.651, f1=0.776, brier=0.092),
        },
    ),
    ModelInfo(
        id="convlstm-v1", name="ConvLSTM", version="v1.5.3", type="deep",
        icon="ri-brain-line",
        description="卷积长短时记忆网络，同时捕捉空间场和时间序列的依赖关系。",
        supported_hazards=["heavy-rain", "flash-flood"],
        last_trained="2026-07-10",
        metrics={
            "heavy-rain": ModelMetrics(auc=0.913, pod=0.871, far=0.152, csi=0.762, f1=0.858, brier=0.068),
            "flash-flood": ModelMetrics(auc=0.885, pod=0.834, far=0.196, csi=0.702, f1=0.820, brier=0.079),
        },
    ),
    ModelInfo(
        id="ensemble-v4", name="多模型集成", version="v4.1.0", type="ensemble",
        icon="ri-group-line",
        description="XGBoost + LightGBM + ConvLSTM 贝叶斯加权集成。",
        supported_hazards=["heavy-rain", "extreme-heat", "flash-flood", "dust-storm"],
        last_trained="2026-07-25",
        metrics={
            "heavy-rain": ModelMetrics(auc=0.926, pod=0.893, far=0.127, csi=0.798, f1=0.883, brier=0.058),
            "extreme-heat": ModelMetrics(auc=0.952, pod=0.928, far=0.071, csi=0.872, f1=0.929, brier=0.035),
            "flash-flood": ModelMetrics(auc=0.907, pod=0.862, far=0.158, csi=0.752, f1=0.843, brier=0.069),
            "dust-storm": ModelMetrics(auc=0.883, pod=0.815, far=0.201, csi=0.683, f1=0.801, brier=0.085),
        },
    ),
]

MODELS_BY_ID: dict[str, ModelInfo] = {m.id: m for m in MODELS}
DEFAULT_MODEL_ID = "ensemble-v4"


def get_model(model_id: str) -> ModelInfo | None:
    return MODELS_BY_ID.get(model_id)
