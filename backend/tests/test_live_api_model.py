from __future__ import annotations

from datetime import datetime, timezone
import math

import pytest

from app.data.live_feature_contract import MODEL_FEATURES
from app.domain.forecast_case import ForecastCase
from app.models.live_api_model import get_live_api_model

HAZARDS = ["heavy-rain", "extreme-heat", "flash-flood", "dust-storm"]


def _indicators() -> dict[str, float]:
    return {
        "daily_precip_total": 8.0,
        "t2m_c": 39.0,
        "tmax_c": 44.0,
        "tmin_c": 31.0,
        "wind10_speed": 8.0,
        "lat": 16.8892,
        "lon": 42.5511,
        "day_of_year": 214.0,
        "daily_precip": 8.0,
        "t2m": 39.0,
        "wind_10m": 8.0,
    }


@pytest.mark.parametrize("hazard", HAZARDS)
def test_live_api_artifacts_run_real_predict_proba(hazard: str):
    model = get_live_api_model(hazard)
    assert model is not None
    case = ForecastCase.create(
        case_id="case-live-model",
        region_id="jazan",
        hazard=hazard,
        lead_time_hours=24,
        initial_time=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    raw = model.predict(case, _indicators())
    assert model.features == MODEL_FEATURES
    assert raw.model_id.startswith("live-api-hgb-")
    assert 0.0 <= raw.probability <= 1.0
    assert set(raw.important_features) == set(MODEL_FEATURES)
    assert raw.important_features["daily_precip_total"] != _indicators()["daily_precip_total"]
    assert raw.attribution_method == "tree_shap"
    assert raw.attribution_output == "raw_log_odds"
    assert raw.attribution_base_value is not None
    assert raw.attribution_model_output is not None
    reconstructed = raw.attribution_base_value + sum(raw.important_features.values())
    assert reconstructed == pytest.approx(raw.attribution_model_output, abs=1e-5)
    sigmoid = 1 / (1 + math.exp(-raw.attribution_model_output))
    assert sigmoid == pytest.approx(raw.probability, abs=1e-4)


def test_live_api_model_rejects_missing_required_feature():
    model = get_live_api_model("extreme-heat")
    assert model is not None
    case = ForecastCase.create(
        case_id="case-live-model",
        region_id="jazan",
        hazard="extreme-heat",
        lead_time_hours=24,
    )
    indicators = _indicators()
    indicators.pop("wind10_speed")
    with pytest.raises(ValueError, match="wind10_speed"):
        model.predict(case, indicators)
