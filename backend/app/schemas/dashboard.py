from __future__ import annotations

from .common import ActivityType, CamelModel, RiskLevel


class DashboardStats(CamelModel):
    total_predictions: int
    active_warnings: int
    models_online: int
    regions_monitored: int


class RecentActivity(CamelModel):
    id: str
    type: ActivityType
    title: str
    description: str
    time: str
    risk_level: RiskLevel | None = None
