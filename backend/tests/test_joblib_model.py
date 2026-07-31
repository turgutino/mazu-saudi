"""Unit tests for JoblibForecastModel (Tier 1 real trained-model wrapper)."""

from __future__ import annotations

import pytest

from app.domain.forecast_case import ForecastCase
from app.models.joblib_model import HAZARD_TO_ARTIFACT, get_joblib_model

REAL_MODEL_HAZARDS = ["extreme-heat", "flash-flood", "dust-storm"]


def _make_case(hazard: str) -> ForecastCase:
    return ForecastCase.create(
        case_id="case-test", region_id="jazan", hazard=hazard, lead_time_hours=24
    )


def _synthetic_feature_row(features: list[str]) -> dict[str, float]:
    """A plausible, in-range value for every raw feature name the trained
    models expect (see backend/app/models/artifacts/model_meta.json)."""
    values = {
        "daily_precip_total": 5.0, "daily_convective_precip": 2.0,
        "daily_large_scale_precip": 3.0, "t2m_c": 28.0, "tmax_c": 35.0,
        "tmin_c": 22.0, "heat_index_c": 30.0, "vpd_kpa": 2.5, "cape": 800.0,
        "pwat": 30.0, "ivt": 150.0, "wind850_speed": 12.0,
        "wind_shear_850_200": 15.0, "daily_precip_anomaly": 0.5,
        "t2m_anomaly_c": 1.0, "tmax_anomaly_c": 0.8, "sst_celsius": 29.0,
        "wind10_speed": 6.0, "dewpoint_depression_c": 8.0,
        "neigh_cape": 780.0, "neigh_daily_precip_total": 4.5,
        "neigh_ivt": 145.0, "neigh_vpd_kpa": 2.4,
        "neigh_wind_shear_850_200": 14.0, "neigh_pwat": 29.0,
        "neigh_daily_convective_precip": 1.8,
        "lat": 21.5, "lon": 39.2, "day_of_year": 200.0,
    }
    return {f: values[f] for f in features}


def test_no_trained_model_for_heavy_rain():
    assert get_joblib_model("heavy-rain") is None


@pytest.mark.parametrize("hazard", REAL_MODEL_HAZARDS)
def test_get_joblib_model_returns_cached_instance(hazard: str):
    first = get_joblib_model(hazard)
    second = get_joblib_model(hazard)
    assert first is second
    assert first.hazard == hazard
    assert first.artifact_key == HAZARD_TO_ARTIFACT[hazard]


@pytest.mark.parametrize("hazard", REAL_MODEL_HAZARDS)
def test_predict_produces_valid_raw_prediction(hazard: str):
    model = get_joblib_model(hazard)
    case = _make_case(hazard)
    indicators = _synthetic_feature_row(model.features)

    raw = model.predict(case, indicators)

    assert 0.0 <= raw.probability <= 1.0
    assert 0.0 <= raw.uncertainty <= 1.0
    assert raw.predicted_class in {"low", "moderate", "high"}
    assert raw.model_id == f"joblib-{HAZARD_TO_ARTIFACT[hazard]}"
    assert raw.important_features


@pytest.mark.parametrize("hazard", REAL_MODEL_HAZARDS)
def test_predict_is_deterministic(hazard: str):
    model = get_joblib_model(hazard)
    case = _make_case(hazard)
    indicators = _synthetic_feature_row(model.features)

    raw1 = model.predict(case, indicators)
    raw2 = model.predict(case, indicators)
    assert raw1.probability == raw2.probability


def test_predict_raises_on_missing_features():
    model = get_joblib_model("flash-flood")
    case = _make_case("flash-flood")
    with pytest.raises(ValueError):
        model.predict(case, {})
