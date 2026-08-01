"""Live dashboard aggregation for GET /api/v1/dashboard/{stats,activities,weekly-stats}.

Everything here is derived from ``prediction_store`` (the same SQLite-backed
history used by /predictions) plus the static region/model registries -- no
more hardcoded stub figures. Aggregates recompute on every request, which is
fine for v1's SQLite-backed single-process scale.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.data.models import MODELS
from app.data.regions import REGIONS
from app.repositories.prediction_store import prediction_store
from app.schemas.dashboard import DashboardStats, RecentActivity, RegionRiskSummary, WeeklyStat
from app.schemas.prediction import PredictionResult

_WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _parse_created_at(created_at: str) -> datetime | None:
    try:
        return datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return None


def get_dashboard_stats() -> DashboardStats:
    predictions = prediction_store.list()

    latest_by_region_hazard: dict[tuple[str, str], PredictionResult] = {}
    latest_by_region: dict[str, PredictionResult] = {}
    # predictions.list() is already ordered created_at desc, so the first
    # occurrence of each key is the most recent one.
    for p in predictions:
        latest_by_region_hazard.setdefault((p.region_id, p.hazard), p)
        latest_by_region.setdefault(p.region_id, p)

    active_warnings = sum(
        1 for p in latest_by_region_hazard.values() if p.risk_level != "green"
    )
    region_risk = [
        RegionRiskSummary(
            region_id=region.id,
            region_name=region.name,
            risk_level=latest_by_region[region.id].risk_level,
        )
        for region in REGIONS
        if region.id in latest_by_region
    ]

    return DashboardStats(
        total_predictions=len(predictions),
        active_warnings=active_warnings,
        models_online=len(MODELS),
        regions_monitored=len(REGIONS),
        region_risk=region_risk,
    )


def get_recent_activities(limit: int = 10) -> list[RecentActivity]:
    predictions = prediction_store.list()[:limit]
    activities: list[RecentActivity] = []
    for p in predictions:
        status = p.risk_label if p.risk_level != "green" else "风险等级为绿色"
        activities.append(
            RecentActivity(
                id=p.prediction_id,
                type="prediction",
                title=f"{p.hazard_label}{p.risk_label} — {p.region_name}",
                description=(
                    f"{p.model_name}预测{p.hazard_label}概率"
                    f"{p.calibrated_probability:.2f}，{status}"
                ),
                time=p.created_at.replace("T", " ")[:16],
                risk_level=p.risk_level,
            )
        )
    return activities


def get_weekly_stats() -> list[WeeklyStat]:
    """Predictions-per-day for the last 7 calendar days (UTC), oldest first."""
    today = datetime.now(timezone.utc).date()
    days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    counts = {day: {"predictions": 0, "warnings": 0} for day in days}

    for p in prediction_store.list():
        created = _parse_created_at(p.created_at)
        if created is None or created.date() not in counts:
            continue
        bucket = counts[created.date()]
        bucket["predictions"] += 1
        if p.risk_level != "green":
            bucket["warnings"] += 1

    return [
        WeeklyStat(
            day=_WEEKDAY_LABELS[day.weekday()],
            predictions=counts[day]["predictions"],
            warnings=counts[day]["warnings"],
        )
        for day in days
    ]
