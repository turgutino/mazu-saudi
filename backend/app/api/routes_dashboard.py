from __future__ import annotations

from fastapi import APIRouter

from app.data.dashboard import get_dashboard_stats, get_recent_activities
from app.schemas.dashboard import DashboardStats, RecentActivity

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/stats", response_model=DashboardStats)
def dashboard_stats() -> DashboardStats:
    return get_dashboard_stats()


@router.get("/dashboard/activities", response_model=list[RecentActivity])
def dashboard_activities() -> list[RecentActivity]:
    return get_recent_activities()
