"""Static hazard registry for the v1 backend.

Only the 4 hazards implemented in v1 are exposed (see plan: severe-convection
本版暂不接入). Field values mirror frontend/src/mocks/hazards.ts for the
hazards that are in scope.
"""

from __future__ import annotations

from app.schemas.hazard import HazardType

HAZARDS: list[HazardType] = [
    HazardType(
        id="heavy-rain", name="暴雨", name_en="Heavy Rain",
        icon="ri-showers-line", color="#0d9488",
        description="短时强降水可能引发城市内涝和山洪灾害",
        description_en="Short-duration heavy precipitation can trigger urban flooding and flash-flood disasters.",
        lead_times=[3, 6, 12, 24, 48],
    ),
    HazardType(
        id="extreme-heat", name="极端高温", name_en="Extreme Heat",
        icon="ri-sun-line", color="#ea580c",
        description="持续高温天气对人体健康和能源供应构成威胁",
        description_en="Sustained extreme heat threatens public health and energy supply.",
        lead_times=[24, 48, 72],
    ),
    HazardType(
        id="flash-flood", name="山洪", name_en="Flash Flood",
        icon="ri-flood-line", color="#dc2626",
        description="山区短时强降水导致的突发性洪水",
        description_en="Short-duration heavy precipitation in mountainous areas causing sudden flash floods.",
        lead_times=[1, 3, 6, 12],
    ),
    HazardType(
        id="dust-storm", name="沙尘暴", name_en="Dust Storm",
        icon="ri-windy-line", color="#a16207",
        description="强风携带大量沙尘导致能见度急剧下降",
        description_en="Strong winds carrying large amounts of dust cause a sharp drop in visibility.",
        lead_times=[6, 12, 24, 48],
    ),
]

HAZARDS_BY_ID: dict[str, HazardType] = {h.id: h for h in HAZARDS}


def get_hazard(hazard_id: str) -> HazardType | None:
    return HAZARDS_BY_ID.get(hazard_id)


SUPPORTED_HAZARD_IDS: set[str] = set(HAZARDS_BY_ID)
