from __future__ import annotations

from .common import CamelModel, RiskLevel, TrendLevel


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
