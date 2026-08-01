"""End-to-end tests for PredictionService across all 4 in-scope hazards."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
from unittest.mock import patch

import pytest
import requests

from app.data.real_indicator_provider import INDICATORS_DIR_ENV
from app.domain.forecast_data import ForecastIndicatorBundle
from app.models.joblib_model import get_joblib_model
from app.schemas.prediction import PredictionRequest
from app.services.prediction_service import PredictionService, PredictionServiceError

HAZARDS = ["heavy-rain", "extreme-heat", "flash-flood", "dust-storm"]


def _live_bundle(source: str = "open-meteo") -> ForecastIndicatorBundle:
    return ForecastIndicatorBundle(
        indicators={
            "daily_precip_total": 8.0,
            "t2m_c": 42.0,
            "tmax_c": 46.0,
            "tmin_c": 35.0,
            "wind10_speed": 15.0,
            "lat": 16.8892,
            "lon": 42.5511,
            "day_of_year": 214.0,
            "cape": 900.0,
            "daily_precip": 8.0,
            "t2m": 42.0,
            "rh_surface": 30.0,
            "wind_10m": 15.0,
            "visibility": 8.0,
        },
        snapshot_id="forecast-test",
        source=source,
        cache_hit=False,
    )


@pytest.fixture()
def service() -> PredictionService:
    return PredictionService()


@pytest.mark.parametrize("hazard", HAZARDS)
def test_run_prediction_produces_complete_result(service: PredictionService, hazard: str):
    request = PredictionRequest(region_id="jazan", hazard=hazard, lead_time_hours=24)
    with patch(
        "app.services.prediction_service.openmeteo_provider.generate_bundle",
        return_value=_live_bundle(),
    ):
        result = service.run_prediction(request)

    assert result.hazard == hazard
    assert result.region_id == "jazan"
    assert 0.0 <= result.probability <= 1.0
    assert 0.0 <= result.decision_score <= 1.0
    assert result.calibration_method == "none"
    assert result.is_calibrated is False
    assert result.ambiguity_method == "heuristic_probability_margin"
    assert 0.0 <= result.ambiguity <= 1.0
    expected_semantics = (
        "uncalibrated_event_score"
        if hazard == "extreme-heat"
        else "uncalibrated_proxy_event_score"
    )
    assert result.score_semantics == expected_semantics
    assert result.risk_level in {"green", "yellow", "orange", "red"}
    assert result.features, "expected at least one feature contribution"
    assert result.rule_hits, "expected at least one rule hit record"
    assert result.mechanisms, "expected at least one mechanism path"
    assert result.input_hash
    assert result.prediction_id and result.case_id


def test_run_prediction_uses_default_model_when_not_specified(service: PredictionService):
    request = PredictionRequest(region_id="jazan", hazard="heavy-rain", lead_time_hours=24)
    with patch("app.services.prediction_service.openmeteo_provider.generate_bundle", return_value=_live_bundle()):
        result = service.run_prediction(request)
    assert result.model_id == "live-api-hgb-heavy_rain"


def test_run_prediction_rejects_incompatible_explicit_model_id(service: PredictionService):
    request = PredictionRequest(
        region_id="jazan", hazard="heavy-rain", lead_time_hours=24, model_id="joblib-heatwave"
    )
    with patch("app.services.prediction_service.openmeteo_provider.generate_bundle", return_value=_live_bundle()):
        with pytest.raises(PredictionServiceError, match="incompatible"):
            service.run_prediction(request)


def test_run_prediction_rejects_unknown_region(service: PredictionService):
    request = PredictionRequest(region_id="atlantis", hazard="heavy-rain", lead_time_hours=24)
    with pytest.raises(PredictionServiceError):
        service.run_prediction(request)


def test_run_prediction_rejects_unknown_hazard(service: PredictionService):
    request = PredictionRequest(region_id="jazan", hazard="wildfire", lead_time_hours=24)
    with pytest.raises(PredictionServiceError):
        service.run_prediction(request)


def test_run_prediction_saves_to_store(service: PredictionService):
    from app.repositories.prediction_store import prediction_store

    request = PredictionRequest(region_id="riyadh", hazard="extreme-heat", lead_time_hours=48)
    with patch("app.services.prediction_service.openmeteo_provider.generate_bundle", return_value=_live_bundle()):
        result = service.run_prediction(request)
    # Persisted via SQLite now, so this round-trips through JSON rather than
    # returning the same object -- assert value equality, not identity.
    assert prediction_store.get(result.prediction_id) == result


class _FakeOpenMeteoResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        times = [
            (datetime(2026, 8, 1, 1) + timedelta(hours=offset)).strftime("%Y-%m-%dT%H:%M")
            for offset in range(24)
        ]
        return {
            "hourly": {
                "time": times,
                "temperature_2m": [45.0] * 24,
                "relative_humidity_2m": [20.0] * 24,
                "cape": [900.0] * 24,
                "precipitation": [0.0] * 23 + [8.0],
                "wind_speed_10m": [15.0] * 24,
                "visibility": [8000.0] * 24,
            }
        }


def test_heavy_rain_uses_live_trained_model(service: PredictionService, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(INDICATORS_DIR_ENV, raising=False)
    request = PredictionRequest(
        region_id="jazan", hazard="heavy-rain", lead_time_hours=24,
        initial_time="2026-08-01T00:00:00Z",
    )
    with patch(
        "app.data.openmeteo_provider.forecast_snapshot_store.get_fresh",
        return_value=None,
    ), patch("app.data.openmeteo_provider.requests.get", return_value=_FakeOpenMeteoResponse()):
        result = service.run_prediction(request)
    assert result.model_id == "live-api-hgb-heavy_rain"
    assert result.data_tier == "tier2_live"
    assert result.raw_indicators["daily_precip"] == 8.0
    assert result.forecast_snapshot_id
    assert result.forecast_source == "open-meteo"
    assert "未校准代理事件分数" in result.risk_description


def test_historical_mode_rejects_hazard_without_trained_model(service: PredictionService):
    request = PredictionRequest(
        region_id="jazan",
        hazard="heavy-rain",
        lead_time_hours=24,
        initial_time="2025-06-01T00:00:00Z",
        prediction_mode="historical",
    )
    with pytest.raises(PredictionServiceError, match="No historical trained model"):
        service.run_prediction(request)


@pytest.mark.parametrize("lead_time", [1, 6, 12, 48, 72])
def test_historical_mode_rejects_non_t_plus_one_horizons(
    service: PredictionService, lead_time: int
):
    request = PredictionRequest(
        region_id="riyadh",
        hazard="extreme-heat",
        lead_time_hours=lead_time,
        initial_time="2025-06-01T00:00:00Z",
        prediction_mode="historical",
    )
    with pytest.raises(PredictionServiceError, match=r"T\+1 day \(24 hours\)"):
        service.run_prediction(request)


def test_historical_mode_keeps_t_plus_one_target_inside_2025(
    service: PredictionService,
):
    request = PredictionRequest(
        region_id="riyadh",
        hazard="extreme-heat",
        lead_time_hours=24,
        initial_time="2025-12-31T00:00:00Z",
        prediction_mode="historical",
    )
    with pytest.raises(PredictionServiceError, match="target remains in 2025"):
        service.run_prediction(request)


def test_historical_missing_model_input_is_json_null_not_nan(
    service: PredictionService,
):
    model = get_joblib_model("extreme-heat")
    indicators = {feature: 1.0 for feature in model.features}
    indicators.update(
        {
            "sst_celsius": math.nan,
            "t2m_c": 41.0,
            "tmax_c": 47.0,
            "tmin_c": 34.0,
            "t2m": 41.0,
            "rh_surface": 20.0,
            "t850": 31.0,
            "h500": 5920.0,
        }
    )
    request = PredictionRequest(
        region_id="riyadh",
        hazard="extreme-heat",
        lead_time_hours=24,
        initial_time="2025-06-01T00:00:00Z",
        prediction_mode="historical",
    )
    with patch(
        "app.services.prediction_service.real_data_available", return_value=True
    ), patch(
        "app.services.prediction_service.real_indicator_provider.generate",
        return_value=indicators,
    ):
        result = service.run_prediction(request)

    assert result.raw_indicators["sst_celsius"] is None
    sst_feature = next(
        feature for feature in result.features if feature.feature == "sst_celsius"
    )
    assert sst_feature.actual_value is None
    json.dumps(result.model_dump(by_alias=True), allow_nan=False)


def test_live_mode_does_not_use_archive_even_when_it_is_available(
    service: PredictionService,
):
    request = PredictionRequest(
        region_id="jazan",
        hazard="extreme-heat",
        lead_time_hours=24,
        initial_time="2025-06-01T00:00:00Z",
        prediction_mode="live",
    )
    with patch(
        "app.services.prediction_service.real_data_available", return_value=True
    ), patch(
        "app.services.prediction_service.openmeteo_provider.generate_bundle",
        return_value=_live_bundle(),
    ), patch(
        "app.services.prediction_service.real_indicator_provider.generate"
    ) as archived_generate:
        result = service.run_prediction(request)

    archived_generate.assert_not_called()
    assert result.model_id == "live-api-hgb-heatwave"
    assert result.data_tier == "tier2_live"


def test_hazard_with_real_model_uses_live_api_model_when_no_archive(
    service: PredictionService, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv(INDICATORS_DIR_ENV, raising=False)
    with patch("app.data.openmeteo_provider.requests.get", return_value=_FakeOpenMeteoResponse()):
        request = PredictionRequest(
            region_id="jazan", hazard="extreme-heat", lead_time_hours=24,
            initial_time="2026-08-01T00:00:00Z",
        )
        result = service.run_prediction(request)
    assert result.model_id == "live-api-hgb-heatwave"
    assert 0.0 <= result.probability <= 1.0


def test_prediction_fails_when_all_live_forecast_sources_fail(
    service: PredictionService, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv(INDICATORS_DIR_ENV, raising=False)
    with patch(
        "app.data.openmeteo_provider.requests.get",
        side_effect=requests.ConnectionError("boom"),
    ):
        request = PredictionRequest(region_id="jazan", hazard="dust-storm", lead_time_hours=24)
        with pytest.raises(PredictionServiceError, match="No complete live forecast"):
            service.run_prediction(request)


def test_mirrorearth_is_tried_before_openmeteo_when_configured(
    service: PredictionService, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv(INDICATORS_DIR_ENV, raising=False)
    monkeypatch.setenv("MIRROR_EARTH_API_KEY", "test-key")

    class _FakeMirrorEarthResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "hourly": {
                    "time": [
                        (datetime(2026, 8, 1, 1) + timedelta(hours=offset)).strftime("%Y-%m-%dT%H:%M")
                        for offset in range(24)
                    ],
                    "temperature_2m": [45.0] * 24,
                    "relative_humidity_2m": [20.0] * 24,
                    "precipitation": [0.0] * 24,
                    "wind_speed_10m": [15.0] * 24,
                }
            }

    with patch(
        "app.data.mirrorearth_provider.requests.get", return_value=_FakeMirrorEarthResponse()
    ) as mirrorearth_get, patch(
        "app.services.prediction_service.openmeteo_provider.generate_bundle"
    ) as openmeteo_generate:
        request = PredictionRequest(
            region_id="jazan", hazard="extreme-heat", lead_time_hours=24,
            initial_time="2026-08-01T00:00:00Z",
        )
        result = service.run_prediction(request)

    mirrorearth_get.assert_called_once()
    openmeteo_generate.assert_not_called()
    assert 0.0 <= result.probability <= 1.0


def test_falls_back_to_openmeteo_when_mirrorearth_fails(
    service: PredictionService, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv(INDICATORS_DIR_ENV, raising=False)
    monkeypatch.setenv("MIRROR_EARTH_API_KEY", "test-key")

    # mirrorearth_provider and openmeteo_provider both call the module-level
    # ``requests.get`` from the shared ``requests`` package (see the
    # tomorrowio enrichment test above for why a single dispatching
    # side_effect, not two separate ``patch(...)`` calls, is required here).
    def _fake_get(url: str, **kwargs):
        if "mirror-earth.com" in url:
            raise requests.ConnectionError("boom")
        return _FakeOpenMeteoResponse()

    with patch("app.data.mirrorearth_provider.requests.get", side_effect=_fake_get):
        request = PredictionRequest(
            region_id="jazan", hazard="extreme-heat", lead_time_hours=24,
            initial_time="2026-08-01T00:00:00Z",
        )
        result = service.run_prediction(request)

    assert 0.0 <= result.probability <= 1.0


def test_future_prediction_does_not_use_tomorrowio_realtime_enrichment(
    service: PredictionService, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv(INDICATORS_DIR_ENV, raising=False)
    monkeypatch.delenv("MIRROR_EARTH_API_KEY", raising=False)
    monkeypatch.setenv("TOMORROW_IO_API_KEY", "test-key")

    with patch(
        "app.data.openmeteo_provider.requests.get", return_value=_FakeOpenMeteoResponse()
    ), patch("app.data.tomorrowio_provider.fetch_enrichment") as tomorrow_fetch:
        request = PredictionRequest(
            region_id="jazan", hazard="dust-storm", lead_time_hours=24,
            initial_time="2026-08-01T00:00:00Z",
        )
        result = service.run_prediction(request)

    tomorrow_fetch.assert_not_called()
    assert all(f.feature != "wind_gust" for f in result.features)


def test_real_archive_takes_priority_over_degraded_model(
    service: PredictionService, tmp_path, monkeypatch: pytest.MonkeyPatch
):
    import numpy as np
    import xarray as xr

    lat = np.array([17.0, 16.8])
    lon = np.array([42.4, 42.6])
    ds = xr.Dataset(
        {"daily_precip_total": (("latitude", "longitude"), np.full((2, 2), 5.0)),
         "cape": (("latitude", "longitude"), np.full((2, 2), 800.0)),
         "pwat": (("latitude", "longitude"), np.full((2, 2), 30.0)),
         "wind850_speed": (("latitude", "longitude"), np.full((2, 2), 10.0)),
         "wind_shear_850_200": (("latitude", "longitude"), np.full((2, 2), 12.0)),
         "daily_precip_anomaly": (("latitude", "longitude"), np.full((2, 2), 0.1)),
         "sst_celsius": (("latitude", "longitude"), np.full((2, 2), 29.0)),
         "ivt": (("latitude", "longitude"), np.full((2, 2), 100.0)),
         "vpd_kpa": (("latitude", "longitude"), np.full((2, 2), 2.0)),
         "daily_convective_precip": (("latitude", "longitude"), np.full((2, 2), 1.0)),
         "daily_large_scale_precip": (("latitude", "longitude"), np.full((2, 2), 4.0)),
         "t2m_c": (("latitude", "longitude"), np.full((2, 2), 30.0)),
         "tmax_c": (("latitude", "longitude"), np.full((2, 2), 38.0)),
         "tmin_c": (("latitude", "longitude"), np.full((2, 2), 22.0)),
         "heat_index_c": (("latitude", "longitude"), np.full((2, 2), 33.0)),
         "wind10_speed": (("latitude", "longitude"), np.full((2, 2), 6.0)),
         "dewpoint_depression_c": (("latitude", "longitude"), np.full((2, 2), 8.0)),
         "t2m_anomaly_c": (("latitude", "longitude"), np.full((2, 2), 1.0)),
         "tmax_anomaly_c": (("latitude", "longitude"), np.full((2, 2), 0.5))},
        coords={"latitude": lat, "longitude": lon},
    )
    initial_time = datetime(2025, 3, 15, tzinfo=timezone.utc)
    feature_date = "20250315"
    ds.to_netcdf(tmp_path / f"saudi_indicators_{feature_date}.nc")
    monkeypatch.setenv(INDICATORS_DIR_ENV, str(tmp_path))

    with patch("app.services.prediction_service.openmeteo_provider.generate_bundle") as mocked:
        request = PredictionRequest(
            region_id="jazan", hazard="flash-flood", lead_time_hours=24,
            initial_time=initial_time.isoformat(),
        )
        result = service.run_prediction(request)
    mocked.assert_not_called()
    assert result.model_id == "joblib-flash_flood"
    assert result.data_tier == "tier1_real"
    assert 0.0 <= result.probability <= 1.0
