"""MirrorEarthIndicatorProvider: Tier 2 live *forecast-model* indicator
source, using Mirror Earth's CMA (China Meteorological Administration)
numerical weather prediction model.

Ports frontend/src/services/mirrorEarthApi.ts's request server-side. Unlike
OpenMeteoIndicatorProvider (a general-purpose blended forecast), this reads
an actual NWP model's hourly output at ``case.target_time``, so it is tried
FIRST in PredictionService's Tier 2 resolution -- Open-Meteo is the fallback
if Mirror Earth's API key is unset or the request fails.

Requires the ``MIRROR_EARTH_API_KEY`` environment variable (same value as
frontend's ``VITE_PUBLIC_MIRROR_EARTH_KEY`` — see 初步设计.md real-data
integration notes). When unset, ``is_configured()`` returns False and
PredictionService skips straight to Open-Meteo.
"""

from __future__ import annotations

import os

import requests

from app.data.live_forecast_utils import nearest_hour_index
from app.data.regions import get_region
from app.domain.forecast_case import ForecastCase

MIRROR_EARTH_URL = "https://api.mirror-earth.com/v1/forecast"
API_KEY_ENV = "MIRROR_EARTH_API_KEY"
HOURLY_VARS = [
    "temperature_2m",
    "precipitation",
    "cape",
    "wind_speed_10m",
    "relative_humidity_2m",
    "surface_pressure",
    "visibility",
]
FORECAST_DAYS = 2  # matches frontend/src/services/mirrorEarthApi.ts
REQUEST_TIMEOUT_SECONDS = 5.0


class MirrorEarthUnavailableError(RuntimeError):
    """Raised when Mirror Earth isn't configured, unreachable, or returns bad data."""


def is_configured() -> bool:
    return bool(os.environ.get(API_KEY_ENV))


def _fetch_hourly(lat: float, lon: float) -> dict[str, list]:
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        raise MirrorEarthUnavailableError(f"{API_KEY_ENV} is not configured")
    params = {
        "latitude": lat,
        "longitude": lon,
        "models": "cma",
        "hourly": ",".join(HOURLY_VARS),
        "forecast_days": FORECAST_DAYS,
        "temporal_resolution": "hourly_1",
        "timezone": "UTC",
        "apikey": api_key,
    }
    try:
        response = requests.get(MIRROR_EARTH_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        return payload["hourly"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise MirrorEarthUnavailableError(f"Mirror Earth request failed: {exc}") from exc


class MirrorEarthIndicatorProvider:
    """Live CMA numerical-model forecast indicators from Mirror Earth (Tier 2)."""

    def generate(self, case: ForecastCase) -> dict[str, float]:
        region = get_region(case.region_id)
        if region is None:
            raise ValueError(f"Unknown regionId: {case.region_id}")

        hourly = _fetch_hourly(region.lat, region.lon)
        index = nearest_hour_index(hourly.get("time", []), case.target_time)
        if index is None:
            raise MirrorEarthUnavailableError("Mirror Earth returned no hourly time entries")

        def _at(field: str) -> float | None:
            values = hourly.get(field)
            if not values or index >= len(values) or values[index] is None:
                return None
            return float(values[index])

        overrides: dict[str, float] = {}
        cape = _at("cape")
        if cape is not None:
            overrides["cape"] = cape
        precipitation = _at("precipitation")
        if precipitation is not None:
            overrides["daily_precip"] = precipitation
        temperature = _at("temperature_2m")
        if temperature is not None:
            overrides["t2m"] = temperature
        humidity = _at("relative_humidity_2m")
        if humidity is not None:
            overrides["rh_surface"] = humidity
        wind_speed = _at("wind_speed_10m")
        if wind_speed is not None:
            overrides["wind_10m"] = wind_speed
        visibility = _at("visibility")
        if visibility is not None:
            # Mirror Earth reports visibility in meters; placeholder spec uses km.
            overrides["visibility"] = visibility / 1000.0

        return overrides


mirrorearth_provider = MirrorEarthIndicatorProvider()
