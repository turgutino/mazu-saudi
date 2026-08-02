from __future__ import annotations

from .common import CamelModel


class HazardType(CamelModel):
    id: str
    name: str
    name_en: str
    icon: str
    color: str
    description: str
    description_en: str
    lead_times: list[int]
