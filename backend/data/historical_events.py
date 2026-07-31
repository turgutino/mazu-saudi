"""Static historical event library used by explanation/similar_events.py.

v1 does not query any real event database; this is a small, hand-curated
sample (aligned with frontend/src/mocks/predictions.ts) used only to
demonstrate the "similar historical events" explanation slot.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalEventRecord:
    event_id: str
    date: str
    region_id: str
    region_name: str
    hazard: str
    hazard_label: str
    description: str
    impact: str
    max_rainfall: float | None = None
    max_temp: float | None = None
    reference_probability: float = 0.6


HISTORICAL_EVENTS: list[HistoricalEventRecord] = [
    HistoricalEventRecord(
        "hist-001", "2024-08-12", "jazan", "吉赞", "flash-flood", "山洪",
        "吉赞地区短时强降水引发山洪，24小时降水量达68mm", "局部道路中断，3处居民区受影响",
        max_rainfall=68, reference_probability=0.82,
    ),
    HistoricalEventRecord(
        "hist-002", "2023-07-28", "jeddah", "吉达", "flash-flood", "山洪",
        "吉达北部山区暴雨引发山洪", "交通受阻，无人员伤亡",
        max_rainfall=55, reference_probability=0.7,
    ),
    HistoricalEventRecord(
        "hist-003", "2025-09-03", "makkah", "麦加", "flash-flood", "山洪",
        "麦加地区强对流天气，伴有雷暴和短时强降水", "朝觐区域临时疏散",
        max_rainfall=45, reference_probability=0.65,
    ),
    HistoricalEventRecord(
        "hist-101", "2025-07-15", "riyadh", "利雅得", "extreme-heat", "极端高温",
        "利雅得持续高温，连续3天最高气温超过47°C", "电力负荷创历史新高",
        max_temp=49, reference_probability=0.7,
    ),
    HistoricalEventRecord(
        "hist-102", "2024-08-02", "medina", "麦地那", "extreme-heat", "极端高温",
        "麦地那朝觐季节遭遇极端高温", "多起中暑救治事件",
        max_temp=48, reference_probability=0.65,
    ),
    HistoricalEventRecord(
        "hist-201", "2024-11-22", "jeddah", "吉达", "heavy-rain", "暴雨",
        "吉达地区暴雨导致城市内涝", "部分低洼路段积水严重",
        max_rainfall=35, reference_probability=0.6,
    ),
    HistoricalEventRecord(
        "hist-202", "2023-03-10", "abha", "艾卜哈", "heavy-rain", "暴雨",
        "艾卜哈山区暴雨，局地阵性大风", "山区公路短暂封闭",
        max_rainfall=40, reference_probability=0.58,
    ),
    HistoricalEventRecord(
        "hist-301", "2025-03-18", "dammam", "达曼", "dust-storm", "沙尘暴",
        "强沙尘暴袭击达曼地区，能见度不足1公里", "机场航班大面积延误",
        reference_probability=0.55,
    ),
    HistoricalEventRecord(
        "hist-302", "2024-06-05", "tabuk", "塔布克", "dust-storm", "沙尘暴",
        "塔布克遭遇季节性沙尘暴", "多条公路能见度骤降",
        reference_probability=0.5,
    ),
]
