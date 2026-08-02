from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from app.data.dashboard import get_dashboard_stats, get_recent_activities, get_weekly_stats
from app.schemas.dashboard import DashboardStats, RecentActivity, WeeklyStat

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/stats", response_model=DashboardStats)
def dashboard_stats(lang: Literal["zh", "en"] = Query(default="zh")) -> DashboardStats:
    return get_dashboard_stats(lang)


@router.get("/dashboard/activities", response_model=list[RecentActivity])
def dashboard_activities(lang: Literal["zh", "en"] = Query(default="zh")) -> list[RecentActivity]:
    return get_recent_activities(lang=lang)


@router.get("/dashboard/weekly-stats", response_model=list[WeeklyStat])
def dashboard_weekly_stats(lang: Literal["zh", "en"] = Query(default="zh")) -> list[WeeklyStat]:
    return get_weekly_stats(lang)
