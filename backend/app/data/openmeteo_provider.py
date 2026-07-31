"""OpenMeteoIndicatorProvider: Tier 2 degraded live-data indicator source.

Used when a ForecastCase's date falls outside the archived 2025 NetCDF
dataset (see real_indicator_provider.py), for hazards that otherwise have a
real trained model. Calls the same free, keyless Open-Meteo forecast API
frontend/src/services/weatherApi.ts already uses client-side, server-side via
``requests``, and maps its ~8 published variables onto the existing narrow
placeholder indicator keys (cape, pw, daily_precip, t2m, wind_10m,
rh_surface, visibility) so RiskPolicy / explanation modules work unchanged.

This is a genuinely smaller feature set than the joblib models require (no
ivt, pwat, wind850_speed, neigh_*, climatological anomalies) -- it backs
DegradedForecastModel (app/models/degraded_model.py), never JoblibForecastModel.
"""

from __future__ import annotations

import requests

from app.data.indicator_provider import with_overrides
from app.data.regions import get_region
from app.domain.forecast_case import ForecastCase

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CURRENT_VARS = [
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


def _fetch_current(lat: float, lon: float) -> dict[str, float]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ",".join(CURRENT_VARS),
        "timezone": "UTC",
    }
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        return payload["current"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise OpenMeteoUnavailableError(f"Open-Meteo request failed: {exc}") from exc


class OpenMeteoIndicatorProvider:
    """Live current-conditions indicators from Open-Meteo (Tier 2)."""

    def generate(self, case: ForecastCase) -> dict[str, float]:
        region = get_region(case.region_id)
        if region is None:
            raise ValueError(f"Unknown regionId: {case.region_id}")

        current = _fetch_current(region.lat, region.lon)

        overrides: dict[str, float] = {}
        if "cape" in current and current["cape"] is not None:
            overrides["cape"] = float(current["cape"])
        if "precipitation" in current and current["precipitation"] is not None:
            overrides["daily_precip"] = float(current["precipitation"])
        if "temperature_2m" in current and current["temperature_2m"] is not None:
            overrides["t2m"] = float(current["temperature_2m"])
        if "relative_humidity_2m" in current and current["relative_humidity_2m"] is not None:
            overrides["rh_surface"] = float(current["relative_humidity_2m"])
        if "wind_speed_10m" in current and current["wind_speed_10m"] is not None:
            overrides["wind_10m"] = float(current["wind_speed_10m"])
        if "visibility" in current and current["visibility"] is not None:
            # Open-Meteo reports visibility in meters; placeholder spec uses km.
            overrides["visibility"] = float(current["visibility"]) / 1000.0

        return with_overrides(case, overrides)


openmeteo_provider = OpenMeteoIndicatorProvider()
