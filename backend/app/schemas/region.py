from __future__ import annotations

from .common import CamelModel, SensitivityLevel


class RegionSensitivity(CamelModel):
    flash_flood: SensitivityLevel
    heatwave: SensitivityLevel
    dust_storm: SensitivityLevel


class Region(CamelModel):
    id: str
    name: str
    name_en: str
    lat: float
    lon: float
    sensitivity: RegionSensitivity
