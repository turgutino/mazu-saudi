"""Unit tests for MirrorEarthIndicatorProvider (Tier 2 CMA-model live-forecast
source), using a mocked ``requests.get`` so tests never make real network
calls or require a real API key."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from app.data.mirrorearth_provider import (
    API_KEY_ENV,
    MirrorEarthUnavailableError,
    is_configured,
    mirrorearth_provider,
)
from app.domain.forecast_case import ForecastCase


def _make_case(hazard: str = "dust-storm") -> ForecastCase:
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


def _hourly_payload(case: ForecastCase, **field_values: float) -> dict:
    target = case.target_time.strftime("%Y-%m-%dT%H:%M")
    payload = {"hourly": {"time": [target]}}
    for field, value in field_values.items():
        payload["hourly"][field] = [value]
    return payload


def test_is_configured_reflects_env_var(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    assert is_configured() is False
    monkeypatch.setenv(API_KEY_ENV, "test-key")
    assert is_configured() is True


def test_generate_raises_when_not_configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    with pytest.raises(MirrorEarthUnavailableError):
        mirrorearth_provider.generate(_make_case())


def test_generate_maps_cma_fields_to_placeholder_keys(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(API_KEY_ENV, "test-key")
    case = _make_case()
    payload = _hourly_payload(
        case,
        temperature_2m=41.0,
        relative_humidity_2m=12.0,
        wind_speed_10m=28.0,
        cape=200.0,
        precipitation=0.0,
        visibility=3000.0,
    )
    with patch("app.data.mirrorearth_provider.requests.get", return_value=_FakeResponse(payload)):
        indicators = mirrorearth_provider.generate(case)

    assert indicators["t2m"] == 41.0
    assert indicators["rh_surface"] == 12.0
    assert indicators["wind_10m"] == 28.0
    assert indicators["cape"] == 200.0
    assert indicators["daily_precip"] == 0.0
    assert indicators["visibility"] == 3.0  # meters -> km


def test_generate_raises_on_network_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(API_KEY_ENV, "test-key")
    with patch(
        "app.data.mirrorearth_provider.requests.get",
        side_effect=requests.ConnectionError("boom"),
    ):
        with pytest.raises(MirrorEarthUnavailableError):
            mirrorearth_provider.generate(_make_case())


def test_generate_rejects_unknown_region(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(API_KEY_ENV, "test-key")
    case = ForecastCase.create(
        case_id="case-test", region_id="atlantis", hazard="dust-storm", lead_time_hours=24
    )
    with pytest.raises(ValueError):
        mirrorearth_provider.generate(case)
