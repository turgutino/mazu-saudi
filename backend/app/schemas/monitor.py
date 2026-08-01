from __future__ import annotations

from typing import Any, Literal

from .common import CamelModel, RiskLevel, TrendLevel


MonitorSource = Literal["open-meteo", "mirror-earth-cma", "tomorrow-io"]


class MonitorReading(CamelModel):
    temperature: float
    humidity: float
    wind_speed: float
    wind_dir: float
    pressure: float
    cape: float
    pw: float
    visibility: float
    wind_gust: float
    fire_index: float
    thunderstorm_prob: float


class ForecastPoint(CamelModel):
    time: str
    temperature: float
    precipitation: float


class HazardMonitorStatus(CamelModel):
    hazard_id: str
    hazard_name: str
    risk_level: RiskLevel
    probability: float
    trend: TrendLevel


class MonitorRegionData(CamelModel):
    region_id: str
    region_name: str
    name_en: str
    lat: float
    lon: float
    map_x: float
    map_y: float
    readings: MonitorReading
    hazards: list[HazardMonitorStatus]
    active_alert_count: int
    highest_risk_level: RiskLevel
    last_update: str
    forecast: list[ForecastPoint] | None = None


class MonitorSourceStatus(CamelModel):
    source: MonitorSource
    configured: bool


class MonitorDataSnapshot(CamelModel):
    snapshot_id: str
    source: MonitorSource
    bucket_start: str
    fetched_at: str
    expires_at: str
    cache_hit: bool
    data: dict[str, Any] | list[Any]
