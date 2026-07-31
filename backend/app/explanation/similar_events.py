"""Auditable analog-case retrieval for prediction explanations.

Cases are filtered by hazard and forecast origin before scoring.  The score
contains weather-pattern, spatial and seasonal dimensions and never uses the
model probability being explained.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from app.data.regions import get_region
from app.knowledge_graph.knowledge_base import cases_for, load_knowledge_base
from app.schemas.prediction import HistoricalEvent, SimilarityDimension


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _month_similarity(origin: datetime, case_date: datetime) -> float:
    distance = abs(origin.month - case_date.month)
    circular_distance = min(distance, 12 - distance)
    return 1.0 - circular_distance / 6.0


def _weather_similarity(
    indicators: dict[str, float], case: dict[str, Any], comparisons: list[dict[str, Any]]
) -> tuple[float, float, str]:
    available_weight = 0.0
    weighted_score = 0.0
    matched: list[str] = []
    case_indicators = case.get("indicators", {})
    total_weight = sum(float(item["weight"]) for item in comparisons)

    for item in comparisons:
        current_key, case_key = item["current"], item["case"]
        if current_key not in indicators or case_key not in case_indicators:
            continue
        weight = float(item["weight"])
        score = 1.0 - min(abs(indicators[current_key] - case_indicators[case_key]) / float(item["range"]), 1.0)
        if item.get("comparability") == "approximate":
            score *= 0.9
        weighted_score += score * weight
        available_weight += weight
        matched.append(f"{item['label']} {score:.0%}")

    coverage = available_weight / total_weight if total_weight else 0.0
    score = weighted_score / available_weight if available_weight else 0.0
    explanation = "、".join(matched) if matched else "无可比较的同名气象指标"
    return score, coverage, explanation


def find_similar_events(
    hazard: str,
    region_id: str,
    initial_time: datetime,
    indicators: dict[str, float],
    limit: int = 3,
) -> list[HistoricalEvent]:
    region = get_region(region_id)
    if region is None:
        return []
    hazard_config = load_knowledge_base()["hazards"][hazard]
    weights = hazard_config["similarityWeights"]
    scored: list[tuple[float, HistoricalEvent]] = []

    for case in cases_for(hazard):
        case_date = datetime.fromisoformat(case["date"])
        origin_naive = initial_time.replace(tzinfo=None)
        if case_date >= origin_naive:
            continue

        weather, coverage, weather_explanation = _weather_similarity(
            indicators, case, hazard_config["comparisons"]
        )
        distance = _haversine_km(region.lat, region.lon, float(case["lat"]), float(case["lon"]))
        spatial = math.exp(-distance / 600.0)
        seasonal = _month_similarity(origin_naive, case_date)
        dimensions = [
            SimilarityDimension(
                key="weather", label="天气形态", score=round(weather, 3),
                weight=weights["weather"], explanation=weather_explanation,
            ),
            SimilarityDimension(
                key="spatial", label="空间背景", score=round(spatial, 3),
                weight=weights["spatial"], explanation=f"中心点距离约 {distance:.0f} km",
            ),
            SimilarityDimension(
                key="seasonal", label="季节窗口", score=round(seasonal, 3),
                weight=weights["seasonal"], explanation=f"月份相差 {min(abs(origin_naive.month-case_date.month), 12-abs(origin_naive.month-case_date.month))} 个月",
            ),
        ]
        base_score = sum(item.score * item.weight for item in dimensions)
        coverage_factor = 0.55 + 0.45 * coverage
        final_score = base_score * coverage_factor * float(case["reliability"])
        source = case["source"]
        event = HistoricalEvent(
            event_id=case["id"],
            date=case["date"],
            region=case["regionLabel"],
            hazard=hazard_config["label"],
            description=case["description"],
            similarity=round(final_score, 3),
            similarity_dimensions=dimensions,
            data_coverage=round(coverage, 3),
            verification_status=case["verificationStatus"],
            source_title=source["title"],
            source_url=source.get("url"),
            max_rainfall=case.get("indicators", {}).get("daily_precip"),
            max_temp=case.get("indicators", {}).get("tmax_c"),
            impact=case["impact"],
        )
        scored.append((final_score, event))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [event for _, event in scored[:limit]]
