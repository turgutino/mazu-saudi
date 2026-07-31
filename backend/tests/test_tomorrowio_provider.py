"""Unit tests for tomorrowio_provider's enrichment fetch (fire_index,
thunderstorm_prob, wind_gust), using a mocked ``requests.get``."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from app.data.tomorrowio_provider import (
    API_KEY_ENV,
    TomorrowIoUnavailableError,
    fetch_enrichment,
    is_configured,
)


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_is_configured_reflects_env_var(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    assert is_configured() is False
    monkeypatch.setenv(API_KEY_ENV, "test-key")
    assert is_configured() is True


def test_fetch_enrichment_raises_when_not_configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    with pytest.raises(TomorrowIoUnavailableError):
        fetch_enrichment(16.8892, 42.5511)


def test_fetch_enrichment_maps_fields_to_placeholder_keys(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(API_KEY_ENV, "test-key")
    payload = {
        "data": {
            "values": {
                "windGust": 18.4,
                "fireIndex": 62.0,
                "thunderstormProbability": 40.0,
            }
        }
    }
    with patch("app.data.tomorrowio_provider.requests.get", return_value=_FakeResponse(payload)):
        overrides = fetch_enrichment(16.8892, 42.5511)

    assert overrides == {"wind_gust": 18.4, "fire_index": 62.0, "thunderstorm_prob": 40.0}


def test_fetch_enrichment_omits_missing_fields(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(API_KEY_ENV, "test-key")
    payload = {"data": {"values": {"windGust": 18.4}}}
    with patch("app.data.tomorrowio_provider.requests.get", return_value=_FakeResponse(payload)):
        overrides = fetch_enrichment(16.8892, 42.5511)
    assert overrides == {"wind_gust": 18.4}


def test_fetch_enrichment_raises_on_network_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(API_KEY_ENV, "test-key")
    with patch(
        "app.data.tomorrowio_provider.requests.get",
        side_effect=requests.ConnectionError("boom"),
    ):
        with pytest.raises(TomorrowIoUnavailableError):
            fetch_enrichment(16.8892, 42.5511)
