"""Unit tests for RiskPolicy: threshold escalation and region sensitivity offset."""

from __future__ import annotations

from app.data.regions import get_region
from app.domain.forecast_case import ForecastCase
from app.risk.policy import risk_policy

VALID_LEVELS = {"green", "yellow", "orange", "red"}


def _assess(hazard: str, indicators: dict[str, float], probability: float, region_id: str = "jazan"):
    case = ForecastCase.create(case_id="case-x", region_id=region_id, hazard=hazard, lead_time_hours=24)
    region = get_region(region_id)
    return risk_policy.assess(case, probability, indicators, region)


def test_risk_level_escalates_with_probability():
    indicators = {"daily_precip": 10, "cape": 500}
    low = _assess("flash-flood", indicators, 0.10)
    high = _assess("flash-flood", indicators, 0.95)
    assert low.risk_level == "green"
    assert high.risk_level == "red"


def test_risk_level_is_one_of_the_four_valid_levels():
    indicators = {"daily_precip": 30, "cape": 2100}
    result = _assess("flash-flood", indicators, 0.7)
    assert result.risk_level in VALID_LEVELS


def test_indicator_rule_hit_recorded_correctly():
    indicators = {"daily_precip": 10, "cape": 2500}
    result = _assess("flash-flood", indicators, 0.3)
    cape_hits = [h for h in result.rule_hits if h.rule_id == "cape-convective"]
    assert len(cape_hits) == 1
    assert cape_hits[0].met is True


def test_high_sensitivity_region_alerts_earlier_than_low_sensitivity():
    # jazan is 'high' flash-flood sensitivity, tabuk is 'low' (see data/regions.py)
    indicators = {"daily_precip": 10, "cape": 500}
    probability = 0.52  # between jazan's shifted (0.45) and tabuk's shifted (0.55) yellow thresholds
    jazan_result = _assess("flash-flood", indicators, probability, region_id="jazan")
    tabuk_result = _assess("flash-flood", indicators, probability, region_id="tabuk")
    assert jazan_result.risk_level != "green"
    assert tabuk_result.risk_level == "green"


def test_risk_description_mentions_hazard_label_when_escalated():
    indicators = {"daily_precip": 45, "cape": 2500}
    result = _assess("flash-flood", indicators, 0.9)
    assert "山洪" in result.risk_description
