"""OpenMeteoIndicatorProvider: Tier 2 degraded live-data indicator source.

Used when a ForecastCase's date falls outside the archived 2025 NetCDF
dataset (see real_indicator_provider.py), for hazards that otherwise have a
real trained model. Calls the same free, keyless Open-Meteo forecast API
frontend/src/services/weatherApi.ts already uses client-side, server-side via
``requests``, and maps its ~8 published variables onto the existing narrow
placeholder indicator keys (cape, pw, daily_precip, t2m, wind_10m,
rh_surface, visibility) so RiskPolicy / explanation modules work unchanged.

Reads the ``hourly`` forecast endpoint (not ``current``) and picks the entry
nearest ``case.target_time`` -- i.e. this returns the forecast MODEL's value
for the actual lead time being predicted, not a snapshot of "right now"
regardless of ``lead_time_hours``.

This is a genuinely smaller feature set than the joblib models require (no
ivt, pwat, wind850_speed, neigh_*, climatological anomalies) -- it backs
DegradedForecastModel (app/models/degraded_model.py), never JoblibForecastModel.
"""

from __future__ import annotations

import requests

from app.data.indicator_provider import with_overrides
from app.data.live_forecast_utils import forecast_days_for, nearest_hour_index
from app.data.regions import get_region
from app.domain.forecast_case import ForecastCase

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "surface_pressure",
    "cape",
    "precipitation",
    "visibility",
]
REQUEST_TIMEOUT_SECONDS = 5.0


class OpenMeteoUnavailableError(RuntimeError):
    """Raised when the Open-Meteo API can't be reached or returns bad data."""


def _fetch_hourly(lat: float, lon: float, forecast_days: int) -> dict[str, list]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(HOURLY_VARS),
        "forecast_days": forecast_days,
        "timezone": "UTC",
    }
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        return payload["hourly"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise OpenMeteoUnavailableError(f"Open-Meteo request failed: {exc}") from exc


class OpenMeteoIndicatorProvider:
    """Live forecast indicators from Open-Meteo, at ``case.target_time`` (Tier 2)."""

    def generate(self, case: ForecastCase) -> dict[str, float]:
        region = get_region(case.region_id)
        if region is None:
            raise ValueError(f"Unknown regionId: {case.region_id}")

        hourly = _fetch_hourly(region.lat, region.lon, forecast_days_for(case.target_time))
        index = nearest_hour_index(hourly.get("time", []), case.target_time)
        if index is None:
            raise OpenMeteoUnavailableError("Open-Meteo returned no hourly time entries")

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
            # Open-Meteo reports visibility in meters; placeholder spec uses km.
            overrides["visibility"] = visibility / 1000.0

        return with_overrides(case, overrides)


openmeteo_provider = OpenMeteoIndicatorProvider()
