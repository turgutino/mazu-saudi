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

from app.data.live_feature_contract import FEATURE_VERSION, aggregate_live_features
from app.data.live_forecast_utils import nearest_hour_index
from app.data.regions import get_region
from app.domain.forecast_data import ForecastIndicatorBundle
from app.domain.forecast_case import ForecastCase
from app.repositories.forecast_snapshot_store import (
    build_forecast_cache_key,
    forecast_snapshot_store,
)

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
SOURCE_ID = "mirror-earth-cma"


class MirrorEarthUnavailableError(RuntimeError):
    """Raised when Mirror Earth isn't configured, unreachable, or returns bad data."""


def is_configured() -> bool:
    return bool(os.environ.get(API_KEY_ENV))


def _fetch_payload(lat: float, lon: float) -> dict:
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
        "wind_speed_unit": "ms",
        "apikey": api_key,
    }
    try:
        response = requests.get(MIRROR_EARTH_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("response JSON is not an object")
        return payload
    except (requests.RequestException, ValueError) as exc:
        raise MirrorEarthUnavailableError(f"Mirror Earth request failed: {exc}") from exc


class MirrorEarthIndicatorProvider:
    """Live CMA numerical-model forecast indicators from Mirror Earth (Tier 2)."""

    def generate_bundle(
        self, case: ForecastCase, *, use_cache: bool = True
    ) -> ForecastIndicatorBundle:
        region = get_region(case.region_id)
        if region is None:
            raise ValueError(f"Unknown regionId: {case.region_id}")

        cache_key = build_forecast_cache_key(
            SOURCE_ID, case.region_id, case.target_time, FEATURE_VERSION
        )
        if use_cache:
            cached = forecast_snapshot_store.get_fresh(cache_key)
            if cached is not None:
                if cached.status != "valid":
                    raise MirrorEarthUnavailableError(
                        cached.validation_error or "Cached Mirror Earth response is invalid"
                    )
                return ForecastIndicatorBundle(
                    indicators=cached.indicators,
                    snapshot_id=cached.snapshot_id,
                    source=SOURCE_ID,
                    cache_hit=True,
                )

        payload = _fetch_payload(region.lat, region.lon)
        hourly = payload.get("hourly")
        if not isinstance(hourly, dict):
            error = "Mirror Earth response has no hourly object"
            forecast_snapshot_store.save(
                cache_key=cache_key, source=SOURCE_ID, region_id=case.region_id,
                target_time=case.target_time, valid_from="", valid_to="",
                feature_version=FEATURE_VERSION, raw_payload=payload, indicators={},
                status="invalid", validation_error=error,
            )
            raise MirrorEarthUnavailableError(error)
        times = hourly.get("time", [])
        index = nearest_hour_index(hourly.get("time", []), case.target_time)
        if index is None:
            error = "Mirror Earth returned no hourly entries covering target time"
            forecast_snapshot_store.save(
                cache_key=cache_key, source=SOURCE_ID, region_id=case.region_id,
                target_time=case.target_time,
                valid_from=times[0] if times else "", valid_to=times[-1] if times else "",
                feature_version=FEATURE_VERSION, raw_payload=payload, indicators={},
                status="invalid", validation_error=error,
            )
            raise MirrorEarthUnavailableError(error)

        def _at(field: str) -> float | None:
            values = hourly.get(field)
            if not values or index >= len(values) or values[index] is None:
                return None
            return float(values[index])

        try:
            indicators = aggregate_live_features(
                hourly, index, case.target_time, region.lat, region.lon
            )
        except ValueError as exc:
            forecast_snapshot_store.save(
                cache_key=cache_key, source=SOURCE_ID, region_id=case.region_id,
                target_time=case.target_time,
                valid_from=times[0] if times else "", valid_to=times[-1] if times else "",
                feature_version=FEATURE_VERSION, raw_payload=payload, indicators={},
                status="invalid", validation_error=str(exc),
            )
            raise MirrorEarthUnavailableError(str(exc)) from exc
        humidity = _at("relative_humidity_2m")
        if humidity is not None:
            indicators["rh_surface"] = humidity
        visibility = _at("visibility")
        if visibility is not None:
            indicators["visibility"] = visibility / 1000.0

        snapshot = forecast_snapshot_store.save(
            cache_key=cache_key,
            source=SOURCE_ID,
            region_id=case.region_id,
            target_time=case.target_time,
            valid_from=times[0],
            valid_to=times[-1],
            feature_version=FEATURE_VERSION,
            raw_payload=payload,
            indicators=indicators,
        )
        return ForecastIndicatorBundle(
            indicators=indicators,
            snapshot_id=snapshot.snapshot_id,
            source=SOURCE_ID,
            cache_hit=False,
        )

    def generate(self, case: ForecastCase, *, use_cache: bool = True) -> dict[str, float]:
        return self.generate_bundle(case, use_cache=use_cache).indicators


mirrorearth_provider = MirrorEarthIndicatorProvider()
