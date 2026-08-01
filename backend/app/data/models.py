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

Four additional entries are lightweight API-compatible HGB postprocessors
trained on a reduced feature contract available from both the 2025 archive
and a third-party hourly forecast. Their labels are explicitly documented as
provided or proxy labels; they replace the former hand-written live rule.
"""

from __future__ import annotations

from app.schemas.model import ModelInfo, ModelMetrics

MODELS: list[ModelInfo] = [
    ModelInfo(
        id="joblib-heatwave", name="HistGradientBoosting-高温", version="trained-2025-06-30", type="tree",
        icon="ri-sun-line",
        description="基于前一日ERA5归档指标预测目标日高温（T+1日/24小时）的HistGradientBoostingClassifier，含邻域特征。",
        supported_hazards=["extreme-heat"],
        last_trained="2025-06-30",
        metrics={
            "extreme-heat": ModelMetrics(auc=0.9706, pod=0.8488, far=0.3879, csi=0.5519, f1=0.7112, brier=0.0304),
        },
    ),
    ModelInfo(
        id="joblib-flash_flood", name="HistGradientBoosting-山洪", version="trained-2025-06-30", type="tree",
        icon="ri-flood-line",
        description="基于前一日ERA5归档指标预测目标日山洪风险（T+1日/24小时）的HistGradientBoostingClassifier。",
        supported_hazards=["flash-flood"],
        last_trained="2025-06-30",
        metrics={
            "flash-flood": ModelMetrics(auc=0.8732, pod=0.1004, far=0.8026, csi=0.0713, f1=0.1331, brier=0.0063),
        },
    ),
    ModelInfo(
        id="joblib-dust_storm", name="HistGradientBoosting-沙尘暴", version="trained-2025-06-30", type="tree",
        icon="ri-windy-line",
        description="基于前一日ERA5归档指标预测目标日沙尘暴代理事件（T+1日/24小时）的HistGradientBoostingClassifier。",
        supported_hazards=["dust-storm"],
        last_trained="2025-06-30",
        metrics={
            "dust-storm": ModelMetrics(auc=0.8866, pod=0.5352, far=0.865, csi=0.1208, f1=0.2156, brier=0.0602),
        },
    ),
    ModelInfo(
        id="live-api-hgb-heavy_rain", name="API兼容HGB-强降雨", version="live-api-daily-v1", type="tree",
        icon="ri-rainy-line",
        description="以第三方逐小时预报聚合的24小时要素运行；标签为日降水≥25 mm代理事件。降水同时参与特征和标签，测试分数不代表独立预报技巧。",
        supported_hazards=["heavy-rain"], last_trained="2025-12-31",
        metrics={"heavy-rain": ModelMetrics(auc=1.0, pod=1.0, far=0.0, csi=1.0, f1=1.0, brier=0.0)},
    ),
    ModelInfo(
        id="live-api-hgb-heatwave", name="API兼容HGB-高温", version="live-api-daily-v1", type="tree",
        icon="ri-sun-line",
        description="以第三方逐小时预报聚合的24小时要素运行；使用2025归档 heatwave_day_flag 标签训练，输出尚未校准的事件概率。",
        supported_hazards=["extreme-heat"], last_trained="2025-12-31",
        metrics={"extreme-heat": ModelMetrics(auc=0.9846, pod=0.9258, far=0.5161, csi=0.4658, f1=0.6356, brier=0.0387)},
    ),
    ModelInfo(
        id="live-api-hgb-flash_flood", name="API兼容HGB-山洪", version="live-api-daily-v1", type="tree",
        icon="ri-flood-line",
        description="以第三方逐小时预报聚合的24小时要素运行；使用2025归档 flash_flood_risk 教师代理标签训练，输出尚未校准的代理事件概率。",
        supported_hazards=["flash-flood"], last_trained="2025-12-31",
        metrics={"flash-flood": ModelMetrics(auc=0.8421, pod=0.3406, far=0.8166, csi=0.1354, f1=0.2384, brier=0.0074)},
    ),
    ModelInfo(
        id="live-api-hgb-dust_storm", name="API兼容HGB-沙尘暴", version="live-api-daily-v1", type="tree",
        icon="ri-windy-line",
        description="以第三方逐小时预报聚合的24小时要素运行；使用2025归档指标构造的版本化代理标签训练，输出尚未校准的代理事件概率。",
        supported_hazards=["dust-storm"], last_trained="2025-12-31",
        metrics={"dust-storm": ModelMetrics(auc=0.9901, pod=0.9202, far=0.6236, csi=0.3645, f1=0.5343, brier=0.0241)},
    ),
]

MODELS_BY_ID: dict[str, ModelInfo] = {m.id: m for m in MODELS}
DEFAULT_MODEL_ID = "live-api-hgb-heavy_rain"


def get_model(model_id: str) -> ModelInfo | None:
    return MODELS_BY_ID.get(model_id)
