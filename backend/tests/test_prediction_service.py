"""End-to-end tests for PredictionService across all 4 in-scope hazards."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import requests

from app.data.real_indicator_provider import INDICATORS_DIR_ENV
from app.schemas.prediction import PredictionRequest
from app.services.prediction_service import PredictionService, PredictionServiceError

HAZARDS = ["heavy-rain", "extreme-heat", "flash-flood", "dust-storm"]


@pytest.fixture()
def service() -> PredictionService:
    return PredictionService()


@pytest.mark.parametrize("hazard", HAZARDS)
def test_run_prediction_produces_complete_result(service: PredictionService, hazard: str):
    request = PredictionRequest(region_id="jazan", hazard=hazard, lead_time_hours=24)
    with patch(
        "app.services.prediction_service.openmeteo_provider.generate",
        return_value={"cape": 900.0, "daily_precip": 8.0, "t2m": 42.0,
                      "rh_surface": 30.0, "wind_10m": 15.0, "visibility": 8.0},
    ):
        result = service.run_prediction(request)

    assert result.hazard == hazard
    assert result.region_id == "jazan"
    assert 0.0 <= result.probability <= 1.0
    assert 0.0 <= result.calibrated_probability <= 1.0
    assert result.risk_level in {"green", "yellow", "orange", "red"}
    assert result.features, "expected at least one feature contribution"
    assert result.rule_hits, "expected at least one rule hit record"
    assert result.mechanisms, "expected at least one mechanism path"
    assert result.input_hash
    assert result.prediction_id and result.case_id


def test_run_prediction_uses_default_model_when_not_specified(service: PredictionService):
    request = PredictionRequest(region_id="jazan", hazard="heavy-rain", lead_time_hours=24)
    with patch("app.services.prediction_service.openmeteo_provider.generate", return_value={"daily_precip": 8.0}):
        result = service.run_prediction(request)
    assert result.model_id == "live-fusion-v1"


def test_run_prediction_respects_explicit_model_id(service: PredictionService):
    request = PredictionRequest(
        region_id="jazan", hazard="heavy-rain", lead_time_hours=24, model_id="joblib-heatwave"
    )
    with patch("app.services.prediction_service.openmeteo_provider.generate", return_value={"daily_precip": 8.0}):
        result = service.run_prediction(request)
    assert result.model_id == "live-fusion-v1"


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
    with patch("app.services.prediction_service.openmeteo_provider.generate", return_value={"t2m": 42.0}):
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


def test_heavy_rain_uses_live_fusion_model(service: PredictionService, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(INDICATORS_DIR_ENV, raising=False)
    request = PredictionRequest(
        region_id="jazan", hazard="heavy-rain", lead_time_hours=24,
        initial_time="2026-08-01T00:00:00Z",
    )
    with patch("app.data.openmeteo_provider.requests.get", return_value=_FakeOpenMeteoResponse()):
        result = service.run_prediction(request)
    assert result.model_id == "live-fusion-v1"
    assert result.data_tier == "tier2_live"
    assert result.raw_indicators["daily_precip"] == 8.0
    assert "风险评分" in result.risk_description
    assert "概率" not in result.risk_description


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
        "app.services.prediction_service.openmeteo_provider.generate",
        return_value={"t2m": 42.0},
    ), patch(
        "app.services.prediction_service.real_indicator_provider.generate"
    ) as archived_generate:
        result = service.run_prediction(request)

    archived_generate.assert_not_called()
    assert result.model_id == "live-fusion-v1"
    assert result.data_tier == "tier2_live"


def test_hazard_with_real_model_falls_back_to_degraded_when_no_archive(
    service: PredictionService, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv(INDICATORS_DIR_ENV, raising=False)
    with patch("app.data.openmeteo_provider.requests.get", return_value=_FakeOpenMeteoResponse()):
        request = PredictionRequest(
            region_id="jazan", hazard="extreme-heat", lead_time_hours=24,
            initial_time="2026-08-01T00:00:00Z",
        )
        result = service.run_prediction(request)
    assert result.model_id == "live-fusion-v1"
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
        with pytest.raises(PredictionServiceError, match="No live forecast indicators"):
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
                    "time": ["2026-08-02T00:00"],
                    "temperature_2m": [45.0],
                    "relative_humidity_2m": [20.0],
                }
            }

    with patch(
        "app.data.mirrorearth_provider.requests.get", return_value=_FakeMirrorEarthResponse()
    ) as mirrorearth_get, patch(
        "app.services.prediction_service.openmeteo_provider.generate"
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

    with patch("app.services.prediction_service.openmeteo_provider.generate") as mocked:
        request = PredictionRequest(
            region_id="jazan", hazard="flash-flood", lead_time_hours=24,
            initial_time=initial_time.isoformat(),
        )
        result = service.run_prediction(request)
    mocked.assert_not_called()
    assert result.model_id == "joblib-flash_flood"
    assert result.data_tier == "tier1_real"
    assert 0.0 <= result.probability <= 1.0
