from __future__ import annotations

from fastapi import APIRouter

from app.data.dashboard import get_dashboard_stats, get_recent_activities, get_weekly_stats
from app.schemas.dashboard import DashboardStats, RecentActivity, WeeklyStat

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/stats", response_model=DashboardStats)
def dashboard_stats() -> DashboardStats:
    return get_dashboard_stats()


@router.get("/dashboard/activities", response_model=list[RecentActivity])
def dashboard_activities() -> list[RecentActivity]:
    return get_recent_activities()


@router.get("/dashboard/weekly-stats", response_model=list[WeeklyStat])
def dashboard_weekly_stats() -> list[WeeklyStat]:
    return get_weekly_stats()
