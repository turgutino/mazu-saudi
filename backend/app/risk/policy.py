"""RiskPolicy: combines calibrated probability + region sensitivity + indicator
rules into a RiskAssessment (初步设计.md 第3节).

Strictly downstream of RawPrediction/calibration: this module never looks at
raw model internals beyond the already-calibrated probability and the
indicators used to compute it. Changing warning standards only means editing
``backend/data/risk_thresholds.py`` — this file is policy-agnostic.
"""

from __future__ import annotations

from app.domain.forecast_case import ForecastCase
from app.domain.risk import RiskAssessment, RuleHitRecord
from app.schemas.region import Region
from data.risk_thresholds import (
    RISK_CONFIGS,
    SENSITIVITY_OFFSET,
    HazardRiskConfig,
    IndicatorRule,
)

_LEVEL_LABELS = {
    "green": "低风险",
    "yellow": "黄色预警",
    "orange": "橙色预警",
    "red": "红色预警",
}
_LEVEL_LABELS_SHORT = {"yellow": "黄色", "orange": "橙色", "red": "红色"}


def _compare(actual: float, comparison: str, threshold: float) -> bool:
    if comparison == ">=":
        return actual >= threshold
    if comparison == "<=":
        return actual <= threshold
    raise ValueError(f"Unsupported comparison operator: {comparison}")


def _indicator_hit(rule: IndicatorRule, indicators: dict[str, float]) -> RuleHitRecord:
    actual = indicators.get(rule.indicator)
    met = actual is not None and _compare(actual, rule.comparison, rule.threshold)
    return RuleHitRecord(
        rule_id=rule.rule_id,
        rule_name=rule.rule_name,
        condition=f"{rule.indicator} {rule.comparison} {rule.threshold:g}",
        actual_value="n/a" if actual is None else f"{actual:g}",
        threshold=f"{rule.threshold:g}",
        met=met,
        weight=rule.weight if met else 0,
    )


class RiskPolicy:
    """Turns a calibrated probability + context into a RiskAssessment."""

    def assess(
        self,
        case: ForecastCase,
        calibrated_probability: float,
        indicators: dict[str, float],
        region: Region,
        score_kind: str = "probability",
    ) -> RiskAssessment:
        config: HazardRiskConfig = RISK_CONFIGS[case.hazard]
        sensitivity = getattr(region.sensitivity, config.sensitivity_key)
        offset = SENSITIVITY_OFFSET[sensitivity]
        if score_kind == "risk_score":
            score_label = "风险评分"
            score_field = "risk_score"
        elif score_kind == "proxy_probability":
            score_label = "代理事件概率"
            score_field = "proxy_probability"
        else:
            score_label = "概率"
            score_field = "calibrated_probability"

        prob_hits: list[RuleHitRecord] = []
        level = "green"
        for pt in config.probability_thresholds:
            effective_threshold = max(0.0, round(pt.threshold + offset, 4))
            met = calibrated_probability >= effective_threshold
            prob_hits.append(
                RuleHitRecord(
                    rule_id=f"{case.hazard}-prob-{pt.level}",
                    rule_name=f"{config.hazard_label}{score_label}{_LEVEL_LABELS_SHORT[pt.level]}阈值",
                    condition=f"{score_field} >= {effective_threshold:g}",
                    actual_value=f"{calibrated_probability:g}",
                    threshold=f"{effective_threshold:g}",
                    met=met,
                    weight=pt.weight if met else 0,
                )
            )
            if met:
                # probability_thresholds is ordered yellow -> orange -> red,
                # so the last met threshold is the highest level reached.
                level = pt.level

        sensitivity_hit = RuleHitRecord(
            rule_id=f"{case.hazard}-sensitivity",
            rule_name=f"{config.hazard_label}敏感区域",
            condition="region_sensitivity == high",
            actual_value=sensitivity,
            threshold="high",
            met=sensitivity == "high",
            weight=2 if sensitivity == "high" else 0,
        )

        indicator_hits = [_indicator_hit(rule, indicators) for rule in config.indicator_rules]

        rule_hits = prob_hits + [sensitivity_hit] + indicator_hits

        met_descriptions = [
            f"{hit.rule_name}命中（{hit.condition}，实际{hit.actual_value}）"
            for hit in rule_hits
            if hit.met
        ]
        if level == "green":
            risk_description = (
                f"{config.hazard_label}{score_label}{calibrated_probability:g}未超过黄色阈值；"
                + ("；".join(met_descriptions) + "；" if met_descriptions else "")
                + "综合判断为低风险，建议持续监测。"
            )
        else:
            risk_description = (
                f"{'；'.join(met_descriptions)}；因此输出{_LEVEL_LABELS_SHORT[level]}{config.hazard_label}风险。"
            )

        return RiskAssessment(
            risk_level=level,
            risk_label=_LEVEL_LABELS[level],
            risk_description=risk_description,
            rule_hits=rule_hits,
        )


risk_policy = RiskPolicy()
