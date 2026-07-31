"""Mechanism-compatibility explanations grounded in the versioned catalog."""

from __future__ import annotations

from app.data.indicator_provider import INDICATOR_SPECS, normalized_severity
from app.knowledge_graph.knowledge_base import mechanisms_for
from app.schemas.common import ConfidenceLevel
from app.schemas.prediction import MechanismPath, MechanismStep


def _compatibility(indicator: str, value: float) -> float:
    # Severity direction is part of each indicator's registry: for visibility,
    # humidity and soil moisture, lower values correctly increase compatibility.
    return max(0.0, min(1.0, 0.5 + normalized_severity(indicator, value)))


def _confidence(score: float, coverage: float) -> ConfidenceLevel:
    if score >= 0.72 and coverage >= 0.75:
        return "high"
    if score >= 0.42 and coverage >= 0.5:
        return "medium"
    return "low"


def build_mechanisms(
    hazard: str, region_id: str, indicators: dict[str, float]
) -> list[MechanismPath]:
    paths: list[MechanismPath] = []
    for mechanism in mechanisms_for(hazard, region_id):
        steps: list[MechanismStep] = []
        weighted_score = 0.0
        available_weight = 0.0
        total_weight = sum(float(signal["weight"]) for signal in mechanism["signals"])
        for index, signal in enumerate(mechanism["signals"], start=1):
            key = signal["indicator"]
            if key not in indicators or key not in INDICATOR_SPECS:
                continue
            spec = INDICATOR_SPECS[key]
            score = _compatibility(key, indicators[key])
            weight = float(signal["weight"])
            weighted_score += score * weight
            available_weight += weight
            steps.append(
                MechanismStep(
                    step=index,
                    description=signal["label"],
                    indicator=spec.label,
                    value=f"{indicators[key]:g} {spec.unit}".strip(),
                    compatibility=round(score, 3),
                )
            )
        coverage = available_weight / total_weight if total_weight else 0.0
        score = weighted_score / available_weight if available_weight else 0.0
        paths.append(
            MechanismPath(
                path_id=mechanism["id"],
                path_name=mechanism["label"],
                confidence=_confidence(score, coverage),
                support_score=round(score * coverage, 3),
                summary=mechanism["summary"],
                evidence_ids=mechanism["evidenceIds"],
                steps=steps,
            )
        )
    return paths
