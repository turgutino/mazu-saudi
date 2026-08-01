from __future__ import annotations

from .common import ActivityType, CamelModel, RiskLevel


class RegionRiskSummary(CamelModel):
    """Latest known risk level for a region, derived from its most recent
    prediction. Regions with no predictions yet are simply omitted rather
    than defaulted to a guessed level."""

    region_id: str
    region_name: str
    risk_level: RiskLevel


class DashboardStats(CamelModel):
    total_predictions: int
    active_warnings: int
    models_online: int
    regions_monitored: int
    region_risk: list[RegionRiskSummary] = []


class RecentActivity(CamelModel):
    id: str
    type: ActivityType
    title: str
    description: str
    time: str
    risk_level: RiskLevel | None = None


class WeeklyStat(CamelModel):
    day: str
    predictions: int
    warnings: int
