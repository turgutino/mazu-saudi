"""Unit tests for DegradedForecastModel (Tier 2 live-data-only fallback)."""

from __future__ import annotations

import pytest

from app.domain.forecast_case import ForecastCase
from app.models.degraded_model import degraded_model

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
    raw = degraded_model.predict(case, indicators)

    assert 0.0 <= raw.probability <= 1.0
    assert 0.0 <= raw.uncertainty <= 1.0
    assert raw.predicted_class in {"low", "moderate", "high"}
    assert raw.model_id == "degraded-live-v1"


def test_predict_only_scores_available_indicators():
    case = _make_case("dust-storm")
    raw = degraded_model.predict(case, {"wind_10m": 25.0})
    assert set(raw.important_features) == {"wind_10m"}


def test_predict_is_deterministic():
    case = _make_case("flash-flood")
    indicators = {"cape": 900.0, "daily_precip": 15.0}
    raw1 = degraded_model.predict(case, indicators)
    raw2 = degraded_model.predict(case, indicators)
    assert raw1.probability == raw2.probability
    assert raw1.important_features == raw2.important_features


def test_predict_scores_tomorrowio_enrichment_when_present():
    # dust-storm's HAZARD_WEIGHTS includes wind_gust; a plain wind_10m-only
    # indicator set must NOT trip it, but adding wind_gust must.
    case = _make_case("dust-storm")
    without_gust = degraded_model.predict(case, {"wind_10m": 25.0})
    assert "wind_gust" not in without_gust.important_features

    with_gust = degraded_model.predict(case, {"wind_10m": 25.0, "wind_gust": 30.0})
    assert "wind_gust" in with_gust.important_features
