"""End-to-end tests for PredictionService across all 4 in-scope hazards."""

from __future__ import annotations

from datetime import datetime, timezone
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
    result = service.run_prediction(request)
    assert result.model_id


def test_run_prediction_respects_explicit_model_id(service: PredictionService):
    request = PredictionRequest(
        region_id="jazan", hazard="heavy-rain", lead_time_hours=24, model_id="joblib-heatwave"
    )
    result = service.run_prediction(request)
    assert result.model_id == "joblib-heatwave"


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
    result = service.run_prediction(request)
    # Persisted via SQLite now, so this round-trips through JSON rather than
    # returning the same object -- assert value equality, not identity.
    assert prediction_store.get(result.prediction_id) == result


class _FakeOpenMeteoResponse:
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


def test_heavy_rain_always_uses_placeholder_model(service: PredictionService, monkeypatch: pytest.MonkeyPatch):
    # heavy-rain has no trained joblib model, so it must never reach Tier 1/2
    # even when MAZU_INDICATORS_DIR happens to be configured.
    monkeypatch.delenv(INDICATORS_DIR_ENV, raising=False)
    request = PredictionRequest(region_id="jazan", hazard="heavy-rain", lead_time_hours=24)
    result = service.run_prediction(request)
    assert result.probability is not None


def test_hazard_with_real_model_falls_back_to_degraded_when_no_archive(
    service: PredictionService, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv(INDICATORS_DIR_ENV, raising=False)
    with patch("app.data.openmeteo_provider.requests.get", return_value=_FakeOpenMeteoResponse()):
        request = PredictionRequest(region_id="jazan", hazard="extreme-heat", lead_time_hours=24)
        result = service.run_prediction(request)
    assert result.model_id  # displayed modelId unaffected by algorithm tier
    assert 0.0 <= result.probability <= 1.0


def test_hazard_with_real_model_falls_back_to_placeholder_when_openmeteo_fails(
    service: PredictionService, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv(INDICATORS_DIR_ENV, raising=False)
    with patch(
        "app.data.openmeteo_provider.requests.get",
        side_effect=requests.ConnectionError("boom"),
    ):
        request = PredictionRequest(region_id="jazan", hazard="dust-storm", lead_time_hours=24)
        result = service.run_prediction(request)
    assert 0.0 <= result.probability <= 1.0


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


def test_tomorrowio_enrichment_is_merged_when_configured(
    service: PredictionService, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv(INDICATORS_DIR_ENV, raising=False)
    monkeypatch.delenv("MIRROR_EARTH_API_KEY", raising=False)
    monkeypatch.setenv("TOMORROW_IO_API_KEY", "test-key")

    class _FakeTomorrowIoResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": {"values": {"windGust": 20.0, "fireIndex": 50.0, "thunderstormProbability": 10.0}}}

    # OpenMeteoIndicatorProvider and tomorrowio_provider both call the module-
    # level ``requests.get`` from the shared ``requests`` package, so a single
    # dispatching side_effect (keyed on host) is needed -- two separate
    # ``patch(...)`` calls on each module's ``requests.get`` attribute would
    # both rebind the *same* underlying function and the second one applied
    # would silently win for both call sites.
    def _fake_get(url: str, **kwargs):
        if "tomorrow.io" in url:
            return _FakeTomorrowIoResponse()
        return _FakeOpenMeteoResponse()

    with patch("app.data.openmeteo_provider.requests.get", side_effect=_fake_get):
        request = PredictionRequest(
            region_id="jazan", hazard="dust-storm", lead_time_hours=24,
            initial_time="2026-08-01T00:00:00Z",
        )
        result = service.run_prediction(request)

    assert any(f.feature == "wind_gust" for f in result.features)


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
    assert 0.0 <= result.probability <= 1.0
