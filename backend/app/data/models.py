"""Model registry reflecting the actual models used by the system.

Three entries are the real ``HistGradientBoostingClassifier`` models trained
in reference_code/mazu-saudi-warning/agent/01_train_and_save_models.py and
loaded at inference time by JoblibForecastModel
(app/models/joblib_model.py) — their id/version/name here are copied
verbatim from that module's HAZARD_TO_ARTIFACT/MODEL_NAMES/MODEL_VERSION
constants, and their metrics come straight from the held-out test-set
numbers in app/models/artifacts/model_meta.json (roc_auc, and pod/far/csi
under meteorological_metrics) plus the Brier score from the reference
project's model/calibration_report.json (same held-out split). ``f1`` is
derived from pod/far via precision = 1 - far (not separately reported
upstream): f1 = 2·pod·precision / (pod + precision).

The fourth entry is the live multi-source fusion baseline used for all four
hazards when the archived feature contract is unavailable. It is transparent
and not yet fitted against a held-out set, so its metrics remain empty.
"""

from __future__ import annotations

from app.schemas.model import ModelInfo, ModelMetrics

MODELS: list[ModelInfo] = [
    ModelInfo(
        id="joblib-heatwave", name="HistGradientBoosting-高温", version="trained-2025-06-30", type="tree",
        icon="ri-sun-line",
        description="Scikit-learn HistGradientBoostingClassifier，基于 ERA5 归档数据训练的高温预测模型（含邻域特征）。",
        supported_hazards=["extreme-heat"],
        last_trained="2025-06-30",
        metrics={
            "extreme-heat": ModelMetrics(auc=0.9706, pod=0.8488, far=0.3879, csi=0.5519, f1=0.7112, brier=0.0304),
        },
    ),
    ModelInfo(
        id="joblib-flash_flood", name="HistGradientBoosting-山洪", version="trained-2025-06-30", type="tree",
        icon="ri-flood-line",
        description="Scikit-learn HistGradientBoostingClassifier，基于 ERA5 归档数据训练的山洪预测模型。",
        supported_hazards=["flash-flood"],
        last_trained="2025-06-30",
        metrics={
            "flash-flood": ModelMetrics(auc=0.8732, pod=0.1004, far=0.8026, csi=0.0713, f1=0.1331, brier=0.0063),
        },
    ),
    ModelInfo(
        id="joblib-dust_storm", name="HistGradientBoosting-沙尘暴", version="trained-2025-06-30", type="tree",
        icon="ri-windy-line",
        description="Scikit-learn HistGradientBoostingClassifier，基于 ERA5 归档数据训练的沙尘暴预测模型。",
        supported_hazards=["dust-storm"],
        last_trained="2025-06-30",
        metrics={
            "dust-storm": ModelMetrics(auc=0.8866, pod=0.5352, far=0.865, csi=0.1208, f1=0.2156, brier=0.0602),
        },
    ),
    ModelInfo(
        id="live-fusion-v1", name="实时预报风险评分（规则基线）", version="v1.1.0", type="rule",
        icon="ri-node-tree",
        description="使用 CMA 或 Open-Meteo 目标时刻预报与前24小时累计降水计算的透明风险评分；四灾种共用，未经观测频率校准。",
        supported_hazards=["heavy-rain", "extreme-heat", "flash-flood", "dust-storm"],
        last_trained="N/A",
        metrics={},
    ),
]

MODELS_BY_ID: dict[str, ModelInfo] = {m.id: m for m in MODELS}
DEFAULT_MODEL_ID = "live-fusion-v1"


def get_model(model_id: str) -> ModelInfo | None:
    return MODELS_BY_ID.get(model_id)
