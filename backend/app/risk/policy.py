"""RiskPolicy: combines a declared model decision score + region sensitivity + indicator
rules into a RiskAssessment (初步设计.md 第3节).

Strictly downstream of RawPrediction/calibration metadata: this module never
looks at raw model internals beyond the declared decision score and the
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
    "zh": {"green": "低风险", "yellow": "黄色预警", "orange": "橙色预警", "red": "红色预警"},
    "en": {"green": "Low Risk", "yellow": "Yellow Alert", "orange": "Orange Alert", "red": "Red Alert"},
}
_LEVEL_LABELS_SHORT = {
    "zh": {"yellow": "黄色", "orange": "橙色", "red": "红色"},
    "en": {"yellow": "Yellow", "orange": "Orange", "red": "Red"},
}
_SCORE_LABELS = {
    "zh": {"risk_score": "风险评分", "proxy_score": "未校准代理事件分数", "probability": "未校准模型事件分数"},
    "en": {"risk_score": "Risk Score", "proxy_score": "Uncalibrated Proxy Event Score", "probability": "Uncalibrated Model Event Score"},
}


def _compare(actual: float, comparison: str, threshold: float) -> bool:
    if comparison == ">=":
        return actual >= threshold
    if comparison == "<=":
        return actual <= threshold
    raise ValueError(f"Unsupported comparison operator: {comparison}")


def _indicator_hit(rule: IndicatorRule, indicators: dict[str, float], lang: str) -> RuleHitRecord:
    actual = indicators.get(rule.indicator)
    met = actual is not None and _compare(actual, rule.comparison, rule.threshold)
    rule_name = rule.rule_name_en if lang == "en" else rule.rule_name
    return RuleHitRecord(
        rule_id=rule.rule_id,
        rule_name=rule_name,
        condition=f"{rule.indicator} {rule.comparison} {rule.threshold:g}",
        actual_value="n/a" if actual is None else f"{actual:g}",
        threshold=f"{rule.threshold:g}",
        met=met,
        weight=rule.weight if met else 0,
    )


class RiskPolicy:
    """Turns a declared decision score + context into a RiskAssessment."""

    def assess(
        self,
        case: ForecastCase,
        decision_score: float,
        indicators: dict[str, float],
        region: Region,
        score_kind: str = "probability",
        lang: str = "zh",
    ) -> RiskAssessment:
        lang = lang if lang in ("zh", "en") else "zh"
        config: HazardRiskConfig = RISK_CONFIGS[case.hazard]
        hazard_label = config.hazard_label_en if lang == "en" else config.hazard_label
        sensitivity = getattr(region.sensitivity, config.sensitivity_key)
        offset = SENSITIVITY_OFFSET[sensitivity]
        score_field = "risk_score" if score_kind == "risk_score" else "decision_score"
        score_label = _SCORE_LABELS[lang][score_kind if score_kind in _SCORE_LABELS[lang] else "probability"]

        prob_hits: list[RuleHitRecord] = []
        level = "green"
        for pt in config.probability_thresholds:
            effective_threshold = max(0.0, round(pt.threshold + offset, 4))
            met = decision_score >= effective_threshold
            if lang == "en":
                rule_name = f"{hazard_label} {score_label} {_LEVEL_LABELS_SHORT[lang][pt.level]} Threshold"
            else:
                rule_name = f"{hazard_label}{score_label}{_LEVEL_LABELS_SHORT[lang][pt.level]}阈值"
            prob_hits.append(
                RuleHitRecord(
                    rule_id=f"{case.hazard}-prob-{pt.level}",
                    rule_name=rule_name,
                    condition=f"{score_field} >= {effective_threshold:g}",
                    actual_value=f"{decision_score:g}",
                    threshold=f"{effective_threshold:g}",
                    met=met,
                    weight=pt.weight if met else 0,
                )
            )
            if met:
                # probability_thresholds is ordered yellow -> orange -> red,
                # so the last met threshold is the highest level reached.
                level = pt.level

        if lang == "en":
            sensitivity_rule_name = f"{hazard_label} Sensitive Region"
        else:
            sensitivity_rule_name = f"{hazard_label}敏感区域"
        sensitivity_hit = RuleHitRecord(
            rule_id=f"{case.hazard}-sensitivity",
            rule_name=sensitivity_rule_name,
            condition="region_sensitivity == high",
            actual_value=sensitivity,
            threshold="high",
            met=sensitivity == "high",
            weight=2 if sensitivity == "high" else 0,
        )

        indicator_hits = [_indicator_hit(rule, indicators, lang) for rule in config.indicator_rules]

        rule_hits = prob_hits + [sensitivity_hit] + indicator_hits

        if lang == "en":
            met_descriptions = [
                f"{hit.rule_name} met ({hit.condition}, actual {hit.actual_value})"
                for hit in rule_hits
                if hit.met
            ]
            if level == "green":
                risk_description = (
                    f"{hazard_label} {score_label} {decision_score:g} did not exceed the yellow threshold; "
                    + ("; ".join(met_descriptions) + "; " if met_descriptions else "")
                    + "overall assessment: low risk, continued monitoring recommended."
                )
            else:
                risk_description = (
                    f"{'; '.join(met_descriptions)}; therefore {_LEVEL_LABELS_SHORT[lang][level]} {hazard_label} risk is issued."
                )
        else:
            met_descriptions = [
                f"{hit.rule_name}命中（{hit.condition}，实际{hit.actual_value}）"
                for hit in rule_hits
                if hit.met
            ]
            if level == "green":
                risk_description = (
                    f"{hazard_label}{score_label}{decision_score:g}未超过黄色阈值；"
                    + ("；".join(met_descriptions) + "；" if met_descriptions else "")
                    + "综合判断为低风险，建议持续监测。"
                )
            else:
                risk_description = (
                    f"{'；'.join(met_descriptions)}；因此输出{_LEVEL_LABELS_SHORT[lang][level]}{hazard_label}风险。"
                )

        return RiskAssessment(
            risk_level=level,
            risk_label=_LEVEL_LABELS[lang][level],
            risk_description=risk_description,
            rule_hits=rule_hits,
        )


risk_policy = RiskPolicy()
