"""OpenMeteoIndicatorProvider: Tier 2 degraded live-data indicator source.

Used when a ForecastCase cannot use the archived 2025 NetCDF feature contract
(see real_indicator_provider.py). Calls the same free, keyless Open-Meteo forecast API
frontend/src/services/weatherApi.ts already uses client-side, server-side via
``requests``, and maps its ~8 published variables onto the existing narrow
placeholder indicator keys (cape, pw, daily_precip, t2m, wind_10m,
rh_surface, visibility) so RiskPolicy / explanation modules work unchanged.

Reads the ``hourly`` forecast endpoint (not ``current``) and picks the entry
nearest ``case.target_time`` -- i.e. this returns the forecast MODEL's value
for the actual lead time being predicted, not a snapshot of "right now"
regardless of ``lead_time_hours``.

This is a genuinely smaller feature set than the full archived joblib models
require (no ivt, pwat, wind850_speed, neigh_*, climatological anomalies). It
backs the API-compatible HGB postprocessors in app/models/live_api_model.py.
"""

from __future__ import annotations

import requests

from app.data.live_feature_contract import FEATURE_VERSION, aggregate_live_features
from app.data.live_forecast_utils import forecast_days_for, nearest_hour_index
from app.data.regions import get_region
from app.domain.forecast_data import ForecastIndicatorBundle
from app.domain.forecast_case import ForecastCase
from app.repositories.forecast_snapshot_store import (
    build_forecast_cache_key,
    forecast_snapshot_store,
)

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
SOURCE_ID = "open-meteo"


class OpenMeteoUnavailableError(RuntimeError):
    """Raised when the Open-Meteo API can't be reached or returns bad data."""


def _fetch_payload(lat: float, lon: float, forecast_days: int) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(HOURLY_VARS),
        "forecast_days": forecast_days,
        "past_days": 1,
        "timezone": "UTC",
        "wind_speed_unit": "ms",
    }
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("response JSON is not an object")
        return payload
    except (requests.RequestException, ValueError) as exc:
        raise OpenMeteoUnavailableError(f"Open-Meteo request failed: {exc}") from exc


class OpenMeteoIndicatorProvider:
    """Live forecast indicators from Open-Meteo, at ``case.target_time`` (Tier 2)."""

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
                    raise OpenMeteoUnavailableError(
                        cached.validation_error or "Cached Open-Meteo response is invalid"
                    )
                return ForecastIndicatorBundle(
                    indicators=cached.indicators,
                    snapshot_id=cached.snapshot_id,
                    source=SOURCE_ID,
                    cache_hit=True,
                )

        payload = _fetch_payload(
            region.lat, region.lon, forecast_days_for(case.target_time)
        )
        hourly = payload.get("hourly")
        if not isinstance(hourly, dict):
            error = "Open-Meteo response has no hourly object"
            forecast_snapshot_store.save(
                cache_key=cache_key, source=SOURCE_ID, region_id=case.region_id,
                target_time=case.target_time, valid_from="", valid_to="",
                feature_version=FEATURE_VERSION, raw_payload=payload, indicators={},
                status="invalid", validation_error=error,
            )
            raise OpenMeteoUnavailableError(error)
        times = hourly.get("time", [])
        index = nearest_hour_index(hourly.get("time", []), case.target_time)
        if index is None:
            error = "Open-Meteo returned no hourly entries covering target time"
            forecast_snapshot_store.save(
                cache_key=cache_key, source=SOURCE_ID, region_id=case.region_id,
                target_time=case.target_time,
                valid_from=times[0] if times else "", valid_to=times[-1] if times else "",
                feature_version=FEATURE_VERSION, raw_payload=payload, indicators={},
                status="invalid", validation_error=error,
            )
            raise OpenMeteoUnavailableError(error)

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
            raise OpenMeteoUnavailableError(str(exc)) from exc
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


openmeteo_provider = OpenMeteoIndicatorProvider()
