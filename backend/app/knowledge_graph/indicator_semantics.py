"""Canonical indicator identities and their formal ontology alignments."""

from __future__ import annotations

from typing import Any

from app.knowledge_graph.knowledge_base import ontology_resource


_ALIASES = {
    "daily_precip": "daily_precip_total",
    "pw": "pwat",
    "t2m": "t2m_c",
    "wind_10m": "wind10_speed",
}

_ONTOLOGY_CONCEPTS = {
    "daily_precip_total": "DailyPrecipitation",
    "sst_celsius": "SeaSurfaceTemperature",
    "ivt": "IntegratedVaporTransport",
    "cape": "CAPE",
    "pwat": "PrecipitableWater",
    "tmax_c": "MaximumAirTemperature",
    "vpd_kpa": "VaporPressureDeficit",
    "wind10_speed": "TenMetreWindSpeed",
}

_CONTEXT_FEATURES = {"lat", "lon", "day_of_year"}


def canonical_indicator_key(key: str) -> str:
    return _ALIASES.get(key, key)


def indicator_role(key: str) -> str:
    return "forecast-context" if canonical_indicator_key(key) in _CONTEXT_FEATURES else "meteorological-indicator"


def indicator_aggregation(key: str, data_tier: str) -> str:
    canonical = canonical_indicator_key(key)
    period = "目标时刻前24小时" if data_tier == "tier2_live" else "起报日/目标日前一日"
    if canonical in {"daily_precip_total", "daily_convective_precip", "daily_large_scale_precip"}:
        return f"{period}累计"
    if canonical in {"t2m_c", "wind10_speed"}:
        return f"{period}平均"
    if canonical == "tmax_c":
        return f"{period}最大"
    if canonical == "tmin_c":
        return f"{period}最小"
    if canonical.startswith("neigh_"):
        return "起报日四邻域空间均值"
    if canonical in _CONTEXT_FEATURES:
        return "由预测空间/有效时间派生"
    return "来源产品派生值（具体聚合见指标定义）"


def indicator_ontology_details(key: str) -> dict[str, Any]:
    canonical = canonical_indicator_key(key)
    suffix = _ONTOLOGY_CONCEPTS.get(canonical)
    resource = ontology_resource(suffix) if suffix else None
    if resource is None:
        return {
            "ontologyIri": None,
            "ontologyMappingStatus": "context" if canonical in _CONTEXT_FEATURES else "unmapped",
            "cfStandardName": None,
            "cfCellMethods": None,
            "cfCoordinateConstraint": None,
        }
    return {
        "ontologyIri": resource["iri"],
        "ontologyMappingStatus": "aligned",
        "cfStandardName": resource.get("cfStandardName"),
        "cfCellMethods": resource.get("cfCellMethods"),
        "cfCoordinateConstraint": resource.get("cfCoordinateConstraint"),
    }
