"""Unit tests for OpenMeteoIndicatorProvider (Tier 2 live-forecast source),
using a mocked ``requests.get`` so tests never make real network calls."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import requests

from app.data.openmeteo_provider import OpenMeteoUnavailableError, openmeteo_provider
from app.domain.forecast_case import ForecastCase


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
    payload = {
        "hourly": {
            "time": ["2026-08-01T00:00", "2026-08-02T00:00"],
            "temperature_2m": [40.0, 46.5],
            "relative_humidity_2m": [30.0, 18.0],
            "wind_speed_10m": [10.0, 22.0],
            "cape": [300.0, 1500.0],
            "precipitation": [0.0, 3.2],
            "visibility": [12000.0, 8000.0],
        }
    }
    with patch("app.data.openmeteo_provider.requests.get", return_value=_FakeResponse(payload)):
        indicators = openmeteo_provider.generate(_make_case())

    assert indicators["t2m"] == 46.5
    assert indicators["rh_surface"] == 18.0
    assert indicators["wind_10m"] == 22.0
    assert indicators["cape"] == 1500.0
    assert indicators["daily_precip"] == 3.2
    assert indicators["visibility"] == 8.0  # meters -> km


def test_generate_does_not_invent_values_for_missing_fields():
    payload = {"hourly": {"time": ["2026-08-02T00:00"]}}
    with patch("app.data.openmeteo_provider.requests.get", return_value=_FakeResponse(payload)):
        indicators = openmeteo_provider.generate(_make_case())
    assert indicators == {}


def test_generate_raises_on_network_error():
    with patch(
        "app.data.openmeteo_provider.requests.get",
        side_effect=requests.ConnectionError("boom"),
    ):
        with pytest.raises(OpenMeteoUnavailableError):
            openmeteo_provider.generate(_make_case())


def test_generate_raises_when_no_hourly_time_entries():
    with patch(
        "app.data.openmeteo_provider.requests.get",
        return_value=_FakeResponse({"hourly": {"time": []}}),
    ):
        with pytest.raises(OpenMeteoUnavailableError):
            openmeteo_provider.generate(_make_case())


def test_generate_rejects_unknown_region():
    case = ForecastCase.create(
        case_id="case-test", region_id="atlantis", hazard="extreme-heat", lead_time_hours=24
    )
    with pytest.raises(ValueError):
        openmeteo_provider.generate(case)
