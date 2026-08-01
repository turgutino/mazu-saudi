"""Unit tests for OpenMeteoIndicatorProvider (Tier 2 live-forecast source),
using a mocked ``requests.get`` so tests never make real network calls."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import requests

from app.data.openmeteo_provider import OpenMeteoUnavailableError, openmeteo_provider
from app.domain.forecast_case import ForecastCase
from app.repositories.forecast_snapshot_store import ForecastSnapshotStore


def _make_case(hazard: str = "extreme-heat", lead_time_hours: int = 24) -> ForecastCase:
    return ForecastCase.create(
        case_id="case-test", region_id="jazan", hazard=hazard, lead_time_hours=lead_time_hours,
        initial_time=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_generate_maps_open_meteo_fields_to_placeholder_keys():
    times = [
        (datetime(2026, 8, 1, 1) + timedelta(hours=offset)).strftime("%Y-%m-%dT%H:%M")
        for offset in range(24)
    ]
    payload = {
        "hourly": {
            "time": times,
            "temperature_2m": [40.0] * 23 + [46.5],
            "relative_humidity_2m": [30.0] * 23 + [18.0],
            "wind_speed_10m": [10.0] * 23 + [22.0],
            "cape": [300.0] * 23 + [1500.0],
            "precipitation": [1.0] * 23 + [3.2],
            "visibility": [12000.0] * 23 + [8000.0],
        }
    }
    with patch(
        "app.data.openmeteo_provider.requests.get", return_value=_FakeResponse(payload)
    ) as mocked_get:
        indicators = openmeteo_provider.generate(_make_case(), use_cache=False)

    assert indicators["t2m"] == pytest.approx(40.2708)
    assert indicators["tmax_c"] == 46.5
    assert indicators["rh_surface"] == 18.0
    assert indicators["wind_10m"] == 10.5
    assert indicators["cape"] == 1500.0
    assert indicators["daily_precip"] == 26.2
    assert indicators["visibility"] == 8.0  # meters -> km
    assert mocked_get.call_args.kwargs["params"]["past_days"] == 1


def test_generate_rejects_incomplete_required_24h_window():
    payload = {
        "hourly": {
            "time": ["2026-08-02T00:00"],
            "temperature_2m": [46.5],
            "precipitation": [3.2],
        }
    }
    with patch("app.data.openmeteo_provider.requests.get", return_value=_FakeResponse(payload)):
        with pytest.raises(OpenMeteoUnavailableError, match="Incomplete 24-hour"):
            openmeteo_provider.generate(_make_case(), use_cache=False)


def test_generate_rejects_missing_required_fields():
    payload = {"hourly": {"time": ["2026-08-02T00:00"]}}
    with patch("app.data.openmeteo_provider.requests.get", return_value=_FakeResponse(payload)):
        with pytest.raises(OpenMeteoUnavailableError, match="Incomplete 24-hour"):
            openmeteo_provider.generate(_make_case(), use_cache=False)


def test_generate_raises_on_network_error():
    with patch(
        "app.data.openmeteo_provider.requests.get",
        side_effect=requests.ConnectionError("boom"),
    ):
        with pytest.raises(OpenMeteoUnavailableError):
            openmeteo_provider.generate(_make_case(), use_cache=False)


def test_generate_raises_when_no_hourly_time_entries():
    with patch(
        "app.data.openmeteo_provider.requests.get",
        return_value=_FakeResponse({"hourly": {"time": []}}),
    ):
        with pytest.raises(OpenMeteoUnavailableError):
            openmeteo_provider.generate(_make_case(), use_cache=False)


def test_generate_rejects_hourly_data_that_does_not_cover_target_time():
    payload = {"hourly": {"time": ["2026-07-01T00:00"], "temperature_2m": [40.0]}}
    with patch(
        "app.data.openmeteo_provider.requests.get", return_value=_FakeResponse(payload)
    ):
        with pytest.raises(OpenMeteoUnavailableError):
            openmeteo_provider.generate(_make_case(), use_cache=False)


def test_generate_rejects_unknown_region():
    case = ForecastCase.create(
        case_id="case-test", region_id="atlantis", hazard="extreme-heat", lead_time_hours=24
    )
    with pytest.raises(ValueError):
        openmeteo_provider.generate(case)


def test_generate_persists_and_reuses_complete_api_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("MAZU_DB_PATH", str(tmp_path / "forecast-cache.db"))
    store = ForecastSnapshotStore()
    monkeypatch.setattr("app.data.openmeteo_provider.forecast_snapshot_store", store)
    case = _make_case()
    times = [
        (case.target_time - timedelta(hours=23 - offset)).strftime("%Y-%m-%dT%H:%M")
        for offset in range(24)
    ]
    payload = {
        "hourly": {
            "time": times,
            "temperature_2m": [40.0] * 24,
            "wind_speed_10m": [8.0] * 24,
            "cape": [500.0] * 24,
            "precipitation": [1.0] * 24,
        }
    }
    with patch(
        "app.data.openmeteo_provider.requests.get", return_value=_FakeResponse(payload)
    ) as mocked_get:
        first = openmeteo_provider.generate_bundle(case)
        second = openmeteo_provider.generate_bundle(case)

    assert mocked_get.call_count == 1
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.snapshot_id == first.snapshot_id
    persisted = store.get(first.snapshot_id)
    assert persisted is not None
    assert persisted.raw_payload == payload
    assert persisted.indicators["daily_precip_total"] == 24.0


def test_invalid_api_response_is_persisted_and_not_refetched(tmp_path, monkeypatch):
    monkeypatch.setenv("MAZU_DB_PATH", str(tmp_path / "invalid-cache.db"))
    store = ForecastSnapshotStore()
    monkeypatch.setattr("app.data.openmeteo_provider.forecast_snapshot_store", store)
    payload = {"reason": "hourly data unavailable"}
    with patch(
        "app.data.openmeteo_provider.requests.get", return_value=_FakeResponse(payload)
    ) as mocked_get:
        with pytest.raises(OpenMeteoUnavailableError, match="no hourly object"):
            openmeteo_provider.generate_bundle(_make_case())
        with pytest.raises(OpenMeteoUnavailableError, match="no hourly object"):
            openmeteo_provider.generate_bundle(_make_case())

    assert mocked_get.call_count == 1
    snapshots = store.list()
    assert len(snapshots) == 1
    assert snapshots[0].status == "invalid"
    assert snapshots[0].raw_payload == payload
