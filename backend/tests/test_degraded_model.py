"""Unit tests for the live multi-source fusion baseline."""

from __future__ import annotations

import pytest

from app.data.indicator_provider import normalized_severity
from app.domain.forecast_case import ForecastCase
from app.models.degraded_model import live_fusion_model

HAZARDS = ["heavy-rain", "extreme-heat", "flash-flood", "dust-storm"]


def _make_case(hazard: str) -> ForecastCase:
    return ForecastCase.create(
        case_id="case-test", region_id="jazan", hazard=hazard, lead_time_hours=24
    )


@pytest.mark.parametrize("hazard", HAZARDS)
def test_predict_produces_valid_raw_prediction(hazard: str):
    case = _make_case(hazard)
    indicators = {
        "cape": 1200.0, "daily_precip": 20.0, "t2m": 44.0,
        "rh_surface": 30.0, "wind_10m": 18.0, "visibility": 6.0,
    }
    raw = live_fusion_model.predict(case, indicators)

    assert 0.0 <= raw.probability <= 1.0
    assert 0.0 <= raw.uncertainty <= 1.0
    assert raw.predicted_class in {"low", "moderate", "high"}
    assert raw.model_id == "live-fusion-v1"


def test_predict_only_scores_available_indicators():
    case = _make_case("dust-storm")
    raw = live_fusion_model.predict(case, {"wind_10m": 25.0})
    assert set(raw.important_features) == {"wind_10m"}


def test_predict_rejects_when_no_relevant_live_feature_exists():
    with pytest.raises(ValueError, match="No live fusion features"):
        live_fusion_model.predict(_make_case("heavy-rain"), {"t2m": 40.0})


def test_rain_score_requires_complete_24h_precipitation():
    with pytest.raises(ValueError, match="No live fusion features"):
        live_fusion_model.predict(_make_case("heavy-rain"), {"cape": 3000.0})


def test_predict_is_deterministic():
    case = _make_case("flash-flood")
    indicators = {"cape": 900.0, "daily_precip": 15.0}
    raw1 = live_fusion_model.predict(case, indicators)
    raw2 = live_fusion_model.predict(case, indicators)
    assert raw1.probability == raw2.probability
    assert raw1.important_features == raw2.important_features


def test_predict_ignores_realtime_only_enrichment_fields():
    case = _make_case("dust-storm")
    without_gust = live_fusion_model.predict(case, {"wind_10m": 25.0})
    with_gust = live_fusion_model.predict(case, {"wind_10m": 25.0, "wind_gust": 30.0})
    assert without_gust.probability == with_gust.probability
    assert "wind_gust" not in with_gust.important_features


def test_normalized_severity_is_directional_and_clamped():
    assert normalized_severity("cape", 800.0) == 0.0
    assert normalized_severity("cape", 3200.0) == 1.0
    assert normalized_severity("cape", 6000.0) == 1.0
    assert normalized_severity("cape", 50.0) == -1.0
    assert normalized_severity("visibility", 10.0) == 0.0
    assert normalized_severity("visibility", 0.5) == 1.0
    assert normalized_severity("visibility", 20.0) == -1.0
