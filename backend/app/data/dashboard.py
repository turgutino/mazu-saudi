"""Static dashboard data for GET /api/v1/dashboard/{stats,activities}.

Mirrors frontend/src/mocks/dashboard.ts. v1 does not aggregate real
prediction/warning counts; ``get_dashboard_stats`` reports these fixed
figures. Once real usage accumulates in ``prediction_store``, this can be
replaced with a live aggregation without changing the route contract.
"""

from __future__ import annotations

from app.data.regions import REGIONS
from app.schemas.dashboard import DashboardStats, RecentActivity

DASHBOARD_STATS = DashboardStats(
    total_predictions=1284,
    active_warnings=7,
    models_online=4,
    regions_monitored=len(REGIONS),
)

RECENT_ACTIVITIES: list[RecentActivity] = [
    RecentActivity(
        id="act-001", type="prediction", title="山洪橙色预警 — 吉赞",
        description="多模型集成预测山洪概率0.82，触发橙色预警",
        time="2026-07-30 18:05", risk_level="orange",
    ),
    RecentActivity(
        id="act-002", type="prediction", title="高温黄色预警 — 利雅得",
        description="XGBoost预测极端高温概率0.68，触发黄色预警",
        time="2026-07-30 15:08", risk_level="yellow",
    ),
    RecentActivity(
        id="act-003", type="report", title="预测报告生成 — 吉赞山洪",
        description="智能体完成吉赞山洪预测报告，包含特征贡献和物理机制解释",
        time="2026-07-30 18:12",
    ),
    RecentActivity(
        id="act-004", type="prediction", title="沙尘暴低风险 — 达曼",
        description="LightGBM预测沙尘暴概率0.49，风险等级为绿色",
        time="2026-07-30 12:08", risk_level="green",
    ),
    RecentActivity(
        id="act-005", type="prediction", title="暴雨黄色预警 — 吉达",
        description="ConvLSTM预测暴雨概率0.69，触发黄色预警",
        time="2026-07-29 18:12", risk_level="yellow",
    ),
    RecentActivity(
        id="act-006", type="warning", title="模型更新 — 多模型集成 v4.1.0",
        description="集成模型已更新至v4.1.0，新增沙尘暴预测支持",
        time="2026-07-25 09:30",
    ),
]


def get_dashboard_stats() -> DashboardStats:
    return DASHBOARD_STATS


def get_recent_activities() -> list[RecentActivity]:
    return RECENT_ACTIVITIES
