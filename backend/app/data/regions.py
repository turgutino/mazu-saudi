"""Static region registry, mirrored from frontend/src/mocks/regions.ts."""

from __future__ import annotations

from app.schemas.region import Region, RegionSensitivity

REGIONS: list[Region] = [
    Region(
        id="jazan", name="吉赞", name_en="Jazan", lat=16.8892, lon=42.5511,
        sensitivity=RegionSensitivity(flash_flood="high", heatwave="medium", dust_storm="low"),
    ),
    Region(
        id="riyadh", name="利雅得", name_en="Riyadh", lat=24.7136, lon=46.6753,
        sensitivity=RegionSensitivity(flash_flood="medium", heatwave="high", dust_storm="high"),
    ),
    Region(
        id="jeddah", name="吉达", name_en="Jeddah", lat=21.5433, lon=39.1728,
        sensitivity=RegionSensitivity(flash_flood="high", heatwave="medium", dust_storm="medium"),
    ),
    Region(
        id="makkah", name="麦加", name_en="Makkah", lat=21.3891, lon=39.8579,
        sensitivity=RegionSensitivity(flash_flood="high", heatwave="high", dust_storm="medium"),
    ),
    Region(
        id="dammam", name="达曼", name_en="Dammam", lat=26.4207, lon=50.0888,
        sensitivity=RegionSensitivity(flash_flood="low", heatwave="high", dust_storm="high"),
    ),
    Region(
        id="abha", name="艾卜哈", name_en="Abha", lat=18.2164, lon=42.5053,
        sensitivity=RegionSensitivity(flash_flood="medium", heatwave="low", dust_storm="low"),
    ),
    Region(
        id="medina", name="麦地那", name_en="Medina", lat=24.5247, lon=39.5692,
        sensitivity=RegionSensitivity(flash_flood="medium", heatwave="high", dust_storm="medium"),
    ),
    Region(
        id="tabuk", name="塔布克", name_en="Tabuk", lat=28.3835, lon=36.5771,
        sensitivity=RegionSensitivity(flash_flood="low", heatwave="medium", dust_storm="high"),
    ),
]

REGIONS_BY_ID: dict[str, Region] = {r.id: r for r in REGIONS}


def get_region(region_id: str) -> Region | None:
    return REGIONS_BY_ID.get(region_id)
