"""Unit tests for OpenMeteoIndicatorProvider (Tier 2 live-data source),
using a mocked ``requests.get`` so tests never make real network calls."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from app.data.openmeteo_provider import OpenMeteoUnavailableError, openmeteo_provider
from app.domain.forecast_case import ForecastCase


def _make_case(hazard: str = "extreme-heat") -> ForecastCase:
    return ForecastCase.create(
        case_id="case-test", region_id="jazan", hazard=hazard, lead_time_hours=24
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
        "current": {
            "temperature_2m": 46.5,
            "relative_humidity_2m": 18.0,
            "wind_speed_10m": 22.0,
            "cape": 1500.0,
            "precipitation": 3.2,
            "visibility": 8000.0,
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


def test_generate_falls_back_to_placeholder_values_for_missing_fields():
    with patch("app.data.openmeteo_provider.requests.get", return_value=_FakeResponse({"current": {}})):
        indicators = openmeteo_provider.generate(_make_case())
    # no live override applied, but the narrow placeholder keys still exist
    assert "t2m" in indicators
    assert "rh_surface" in indicators


def test_generate_raises_on_network_error():
    with patch(
        "app.data.openmeteo_provider.requests.get",
        side_effect=requests.ConnectionError("boom"),
    ):
        with pytest.raises(OpenMeteoUnavailableError):
            openmeteo_provider.generate(_make_case())


def test_generate_rejects_unknown_region():
    case = ForecastCase.create(
        case_id="case-test", region_id="atlantis", hazard="extreme-heat", lead_time_hours=24
    )
    with pytest.raises(ValueError):
        openmeteo_provider.generate(case)
