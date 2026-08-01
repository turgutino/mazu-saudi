"""TomorrowIoEnrichmentProvider: adds Tomorrow.io's derived risk indicators
(``fire_index``, ``thunderstorm_prob``, ``wind_gust``) on top of whichever
indicator source is already active.

Ports frontend/src/services/tomorrowIoApi.ts server-side. Unlike
OpenMeteoIndicatorProvider / MirrorEarthIndicatorProvider, this is never a
standalone Tier 2 base indicator source -- Tomorrow.io's realtime API has no
raw CAPE/precipitation/wind-speed fields comparable to the others, only
these three enrichment fields with no Tier-1/Tier-3 synthetic equivalent.
PredictionService merges its output into whatever ``indicators`` dict Tier
1/2/3 already produced. It is retained for current-condition monitoring only;
PredictionService deliberately excludes it from 6--72 hour forecasts because
these realtime values are not valid at the forecast target time.

Requires the ``TOMORROW_IO_API_KEY`` environment variable (same value as
frontend's ``VITE_PUBLIC_TOMORROW_IO_KEY``). Failures here are always
swallowed by the caller (best-effort enrichment, not a required data
source) -- see PredictionService._resolve_indicators_and_model.
"""

from __future__ import annotations

import os

import requests

API_KEY_ENV = "TOMORROW_IO_API_KEY"
TOMORROW_IO_URL = "https://api.tomorrow.io/v4/weather/realtime"
REALTIME_FIELDS = ["windGust", "fireIndex", "thunderstormProbability"]
REQUEST_TIMEOUT_SECONDS = 5.0


class TomorrowIoUnavailableError(RuntimeError):
    """Raised when Tomorrow.io isn't configured, unreachable, or returns bad data."""


def is_configured() -> bool:
    return bool(os.environ.get(API_KEY_ENV))


def fetch_enrichment(lat: float, lon: float) -> dict[str, float]:
    """Returns placeholder-indicator-keyed overrides (wind_gust, fire_index,
    thunderstorm_prob) from Tomorrow.io's realtime endpoint, or raises
    TomorrowIoUnavailableError."""
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        raise TomorrowIoUnavailableError(f"{API_KEY_ENV} is not configured")

    params = {
        "location": f"{lat},{lon}",
        "units": "metric",
        "fields": ",".join(REALTIME_FIELDS),
        "apikey": api_key,
    }
    try:
        response = requests.get(TOMORROW_IO_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        values = response.json()["data"]["values"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise TomorrowIoUnavailableError(f"Tomorrow.io request failed: {exc}") from exc

    overrides: dict[str, float] = {}
    if values.get("windGust") is not None:
        overrides["wind_gust"] = float(values["windGust"])
    if values.get("fireIndex") is not None:
        overrides["fire_index"] = float(values["fireIndex"])
    if values.get("thunderstormProbability") is not None:
        overrides["thunderstorm_prob"] = float(values["thunderstormProbability"])
    return overrides
