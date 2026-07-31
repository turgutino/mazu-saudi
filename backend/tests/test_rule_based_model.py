"""Unit tests for the deterministic RuleBasedForecastModel + IndicatorProvider."""

from __future__ import annotations

from datetime import datetime, timezone

from app.data.indicator_provider import indicator_provider
from app.domain.forecast_case import ForecastCase
from app.models.rule_based_model import rule_based_model

HAZARDS = ["heavy-rain", "extreme-heat", "flash-flood", "dust-storm"]


def _make_case(hazard: str, region_id: str = "jazan", lead_time_hours: int = 24) -> ForecastCase:
    return ForecastCase.create(
        case_id="case-test",
        region_id=region_id,
        hazard=hazard,
        lead_time_hours=lead_time_hours,
    )


def test_prediction_is_deterministic_for_same_input():
    initial_time = datetime(2026, 7, 31, tzinfo=timezone.utc)
    case1 = ForecastCase.create(
        case_id="case-a", region_id="jazan", hazard="flash-flood",
        lead_time_hours=24, initial_time=initial_time,
    )
    case2 = ForecastCase.create(
        case_id="case-b", region_id="jazan", hazard="flash-flood",
        lead_time_hours=24, initial_time=initial_time,
    )
    # different case_id, same (region, hazard, lead_time, initial_time) -> same input_hash/seed
    assert case1.input_hash == case2.input_hash

    indicators1 = indicator_provider.generate(case1)
    indicators2 = indicator_provider.generate(case2)
    assert indicators1 == indicators2

    raw1 = rule_based_model.predict(case1, indicators1)
    raw2 = rule_based_model.predict(case2, indicators2)
    assert raw1.probability == raw2.probability
    assert raw1.uncertainty == raw2.uncertainty
    assert raw1.important_features == raw2.important_features


def test_all_four_hazards_supported():
    for hazard in HAZARDS:
        case = _make_case(hazard)
        indicators = indicator_provider.generate(case)
        assert indicators, f"no indicators generated for {hazard}"
        raw = rule_based_model.predict(case, indicators)
        assert 0.0 <= raw.probability <= 1.0
        assert 0.0 <= raw.uncertainty <= 1.0
        assert raw.predicted_class in {"low", "moderate", "high"}
        assert raw.important_features
        assert raw.model_id == "rule-based-v1"


def test_indicators_only_use_hazard_relevant_keys():
    case = _make_case("dust-storm")
    indicators = indicator_provider.generate(case)
    assert set(indicators) == {"wind_10m", "soil_moisture", "visibility", "rh_surface"}
