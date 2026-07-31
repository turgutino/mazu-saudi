"""Per-hazard risk threshold configuration (初步设计.md 第3节 校准与风险决策层).

RiskPolicy (app/risk/policy.py) is the only consumer of this configuration.
Changing warning standards only means editing the values here — never the
model in app/models/.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProbabilityThreshold:
    level: str  # yellow | orange | red
    threshold: float
    weight: float


@dataclass(frozen=True)
class IndicatorRule:
    rule_id: str
    rule_name: str
    indicator: str
    comparison: str  # ">=" or "<="
    threshold: float
    weight: float


@dataclass(frozen=True)
class HazardRiskConfig:
    hazard: str
    hazard_label: str
    sensitivity_key: str  # attribute name on RegionSensitivity: flash_flood | heatwave | dust_storm
    probability_thresholds: tuple[ProbabilityThreshold, ...]
    indicator_rules: tuple[IndicatorRule, ...]


# sensitivity shifts the effective probability bar: 'high' regions alert earlier.
SENSITIVITY_OFFSET: dict[str, float] = {"high": -0.05, "medium": 0.0, "low": 0.05}

RISK_CONFIGS: dict[str, HazardRiskConfig] = {
    "heavy-rain": HazardRiskConfig(
        hazard="heavy-rain", hazard_label="暴雨", sensitivity_key="flash_flood",
        probability_thresholds=(
            ProbabilityThreshold("yellow", 0.55, 2),
            ProbabilityThreshold("orange", 0.70, 3),
            ProbabilityThreshold("red", 0.85, 4),
        ),
        indicator_rules=(
            IndicatorRule("daily-precip-yellow", "日降水黄色阈值", "daily_precip", ">=", 25, 1),
            IndicatorRule("daily-precip-orange", "日降水橙色阈值", "daily_precip", ">=", 40, 1),
            IndicatorRule("cape-convective", "CAPE强对流阈值", "cape", ">=", 2000, 2),
        ),
    ),
    "extreme-heat": HazardRiskConfig(
        hazard="extreme-heat", hazard_label="极端高温", sensitivity_key="heatwave",
        probability_thresholds=(
            ProbabilityThreshold("yellow", 0.55, 2),
            ProbabilityThreshold("orange", 0.72, 3),
            ProbabilityThreshold("red", 0.88, 4),
        ),
        indicator_rules=(
            IndicatorRule("t2m-yellow", "高温黄色阈值", "t2m", ">=", 45, 1),
            IndicatorRule("t2m-orange", "高温橙色阈值", "t2m", ">=", 48, 2),
        ),
    ),
    "flash-flood": HazardRiskConfig(
        hazard="flash-flood", hazard_label="山洪", sensitivity_key="flash_flood",
        probability_thresholds=(
            ProbabilityThreshold("yellow", 0.50, 2),
            ProbabilityThreshold("orange", 0.68, 3),
            ProbabilityThreshold("red", 0.82, 4),
        ),
        indicator_rules=(
            IndicatorRule("daily-precip-yellow", "日降水黄色阈值", "daily_precip", ">=", 30, 1),
            IndicatorRule("daily-precip-red", "红色预警降水阈值", "daily_precip", ">=", 50, 2),
            IndicatorRule("cape-convective", "CAPE强对流阈值", "cape", ">=", 2000, 2),
        ),
    ),
    "dust-storm": HazardRiskConfig(
        hazard="dust-storm", hazard_label="沙尘暴", sensitivity_key="dust_storm",
        probability_thresholds=(
            ProbabilityThreshold("yellow", 0.40, 1),
            ProbabilityThreshold("orange", 0.60, 2),
            ProbabilityThreshold("red", 0.78, 3),
        ),
        indicator_rules=(
            IndicatorRule("wind-10m-yellow", "沙尘暴黄色阈值", "wind_10m", ">=", 20, 1),
            IndicatorRule("wind-10m-orange", "沙尘暴橙色阈值", "wind_10m", ">=", 28, 2),
        ),
    ),
}
