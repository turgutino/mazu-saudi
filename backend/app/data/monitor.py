"""Static monitor snapshot data for GET /api/v1/monitor/regions.

v1 does not run a live monitoring pipeline; this mirrors
frontend/src/mocks/monitor.ts verbatim (values only, restricted to hazards
in scope) so the frontend integration is a drop-in replacement of its own
mock. Replacing this with a real observation feed later only means
reimplementing ``get_monitor_regions`` — callers (routes/services) don't
change.
"""

from __future__ import annotations

from app.schemas.monitor import HazardMonitorStatus, MonitorRegionData, MonitorReading

_IN_SCOPE_HAZARDS = {"heavy-rain", "extreme-heat", "flash-flood", "dust-storm"}


def _hazards(*rows: tuple[str, str, str, float, str]) -> list[HazardMonitorStatus]:
    return [
        HazardMonitorStatus(hazard_id=hid, hazard_name=name, risk_level=level, probability=prob, trend=trend)
        for hid, name, level, prob, trend in rows
        if hid in _IN_SCOPE_HAZARDS
    ]


MONITOR_REGIONS: list[MonitorRegionData] = [
    MonitorRegionData(
        region_id="jazan", region_name="吉赞", name_en="Jazan", lat=16.8892, lon=42.5511, map_x=38.9, map_y=94.4,
        readings=MonitorReading(temperature=33, humidity=78, wind_speed=8, wind_dir=220, pressure=1008, cape=2350, pw=58, visibility=12, wind_gust=14, fire_index=2, thunderstorm_prob=68),
        hazards=_hazards(
            ("heavy-rain", "暴雨", "yellow", 0.65, "rising"),
            ("extreme-heat", "极端高温", "green", 0.15, "stable"),
            ("flash-flood", "山洪", "orange", 0.82, "rising"),
            ("dust-storm", "沙尘暴", "green", 0.08, "stable"),
        ),
        active_alert_count=2, highest_risk_level="orange", last_update="2026-07-31 06:30",
    ),
    MonitorRegionData(
        region_id="riyadh", region_name="利雅得", name_en="Riyadh", lat=24.7136, lon=46.6753, map_x=57.6, map_y=45.5,
        readings=MonitorReading(temperature=46, humidity=8, wind_speed=12, wind_dir=350, pressure=1012, cape=450, pw=22, visibility=8, wind_gust=18, fire_index=5, thunderstorm_prob=12),
        hazards=_hazards(
            ("heavy-rain", "暴雨", "green", 0.12, "falling"),
            ("extreme-heat", "极端高温", "yellow", 0.68, "rising"),
            ("flash-flood", "山洪", "green", 0.05, "stable"),
            ("dust-storm", "沙尘暴", "yellow", 0.42, "rising"),
        ),
        active_alert_count=1, highest_risk_level="yellow", last_update="2026-07-31 06:30",
    ),
    MonitorRegionData(
        region_id="jeddah", region_name="吉达", name_en="Jeddah", lat=21.5433, lon=39.1728, map_x=23.5, map_y=65.4,
        readings=MonitorReading(temperature=38, humidity=62, wind_speed=10, wind_dir=200, pressure=1006, cape=1850, pw=52, visibility=10, wind_gust=16, fire_index=3, thunderstorm_prob=69),
        hazards=_hazards(
            ("heavy-rain", "暴雨", "yellow", 0.69, "rising"),
            ("extreme-heat", "极端高温", "green", 0.22, "stable"),
            ("flash-flood", "山洪", "green", 0.35, "stable"),
            ("dust-storm", "沙尘暴", "green", 0.15, "stable"),
        ),
        active_alert_count=1, highest_risk_level="yellow", last_update="2026-07-31 06:30",
    ),
    MonitorRegionData(
        region_id="makkah", region_name="麦加", name_en="Makkah", lat=21.3891, lon=39.8579, map_x=26.6, map_y=66.3,
        readings=MonitorReading(temperature=44, humidity=25, wind_speed=6, wind_dir=180, pressure=1009, cape=520, pw=30, visibility=15, wind_gust=10, fire_index=4, thunderstorm_prob=28),
        hazards=_hazards(
            ("heavy-rain", "暴雨", "green", 0.28, "stable"),
            ("extreme-heat", "极端高温", "green", 0.48, "stable"),
            ("flash-flood", "山洪", "green", 0.18, "stable"),
            ("dust-storm", "沙尘暴", "green", 0.25, "stable"),
        ),
        active_alert_count=0, highest_risk_level="green", last_update="2026-07-31 06:30",
    ),
    MonitorRegionData(
        region_id="dammam", region_name="达曼", name_en="Dammam", lat=26.4207, lon=50.0888, map_x=73.1, map_y=34.9,
        readings=MonitorReading(temperature=41, humidity=45, wind_speed=18, wind_dir=310, pressure=1010, cape=380, pw=28, visibility=5, wind_gust=22, fire_index=6, thunderstorm_prob=15),
        hazards=_hazards(
            ("heavy-rain", "暴雨", "green", 0.15, "stable"),
            ("extreme-heat", "极端高温", "green", 0.38, "stable"),
            ("flash-flood", "山洪", "green", 0.08, "stable"),
            ("dust-storm", "沙尘暴", "green", 0.49, "rising"),
        ),
        active_alert_count=0, highest_risk_level="green", last_update="2026-07-31 06:30",
    ),
    MonitorRegionData(
        region_id="abha", region_name="艾卜哈", name_en="Abha", lat=18.2164, lon=42.5053, map_x=38.7, map_y=86.1,
        readings=MonitorReading(temperature=28, humidity=55, wind_speed=5, wind_dir=210, pressure=1015, cape=680, pw=38, visibility=18, wind_gust=9, fire_index=1, thunderstorm_prob=22),
        hazards=_hazards(
            ("heavy-rain", "暴雨", "green", 0.22, "stable"),
            ("extreme-heat", "极端高温", "green", 0.08, "stable"),
            ("flash-flood", "山洪", "green", 0.12, "stable"),
            ("dust-storm", "沙尘暴", "green", 0.10, "stable"),
        ),
        active_alert_count=0, highest_risk_level="green", last_update="2026-07-31 06:30",
    ),
    MonitorRegionData(
        region_id="medina", region_name="麦地那", name_en="Medina", lat=24.5247, lon=39.5692, map_x=25.3, map_y=46.7,
        readings=MonitorReading(temperature=42, humidity=18, wind_speed=9, wind_dir=340, pressure=1011, cape=410, pw=24, visibility=14, wind_gust=13, fire_index=3, thunderstorm_prob=18),
        hazards=_hazards(
            ("heavy-rain", "暴雨", "green", 0.18, "stable"),
            ("extreme-heat", "极端高温", "green", 0.42, "stable"),
            ("flash-flood", "山洪", "green", 0.10, "stable"),
            ("dust-storm", "沙尘暴", "green", 0.30, "stable"),
        ),
        active_alert_count=0, highest_risk_level="green", last_update="2026-07-31 06:30",
    ),
    MonitorRegionData(
        region_id="tabuk", region_name="塔布克", name_en="Tabuk", lat=28.3835, lon=36.5771, map_x=11.7, map_y=22.6,
        readings=MonitorReading(temperature=39, humidity=22, wind_speed=14, wind_dir=300, pressure=1014, cape=290, pw=18, visibility=6, wind_gust=20, fire_index=5, thunderstorm_prob=8),
        hazards=_hazards(
            ("heavy-rain", "暴雨", "green", 0.08, "stable"),
            ("extreme-heat", "极端高温", "green", 0.35, "stable"),
            ("flash-flood", "山洪", "green", 0.05, "stable"),
            ("dust-storm", "沙尘暴", "yellow", 0.52, "rising"),
        ),
        active_alert_count=1, highest_risk_level="yellow", last_update="2026-07-31 06:30",
    ),
]


def get_monitor_regions() -> list[MonitorRegionData]:
    return MONITOR_REGIONS
