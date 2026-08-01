"""Backend-owned acquisition for six-hour monitoring snapshots."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from typing import Any

import requests

from app.data.regions import REGIONS
from app.repositories.monitor_snapshot_store import MonitorSnapshotStore
from app.schemas.monitor import MonitorDataSnapshot, MonitorSource, MonitorSourceStatus

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
MIRROR_EARTH_URL = "https://api.mirror-earth.com/v1/forecast"
TOMORROW_IO_URL = "https://api.tomorrow.io/v4/weather/realtime"
MIRROR_EARTH_API_KEY_ENV = "MIRROR_EARTH_API_KEY"
TOMORROW_IO_API_KEY_ENV = "TOMORROW_IO_API_KEY"
REQUEST_TIMEOUT_SECONDS = 8.0

CURRENT_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "surface_pressure",
    "cape",
    "precipitation",
    "cloud_cover",
    "visibility",
]
HOURLY_VARS = ["temperature_2m", "precipitation"]
MIRROR_HOURLY_VARS = [
    "temperature_2m",
    "precipitation",
    "cape",
    "wind_speed_10m",
    "wind_direction_10m",
    "relative_humidity_2m",
    "surface_pressure",
    "visibility",
]
TOMORROW_FIELDS = [
    "temperature",
    "windSpeed",
    "windGust",
    "fireIndex",
    "thunderstormProbability",
    "precipitationIntensity",
]


class MonitorAcquisitionError(RuntimeError):
    """A configured monitoring source could not produce a valid snapshot."""


def _request_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise MonitorAcquisitionError(f"Monitoring request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise MonitorAcquisitionError("Monitoring response is not a JSON object")
    return payload


def collect_open_meteo() -> list[dict[str, Any]]:
    return [
        _request_json(
            OPEN_METEO_URL,
            {
                "latitude": region.lat,
                "longitude": region.lon,
                "current": ",".join(CURRENT_VARS),
                "hourly": ",".join(HOURLY_VARS),
                "forecast_hours": 48,
                "timezone": "UTC",
                "wind_speed_unit": "ms",
            },
        )
        for region in REGIONS
    ]


def collect_mirror_earth() -> list[dict[str, Any]]:
    api_key = os.environ.get(MIRROR_EARTH_API_KEY_ENV)
    if not api_key:
        raise MonitorAcquisitionError(f"{MIRROR_EARTH_API_KEY_ENV} is not configured")
    return [
        _request_json(
            MIRROR_EARTH_URL,
            {
                "latitude": region.lat,
                "longitude": region.lon,
                "models": "cma",
                "current": ",".join(CURRENT_VARS),
                "hourly": ",".join(MIRROR_HOURLY_VARS),
                "forecast_days": 2,
                "temporal_resolution": "hourly_1",
                "timezone": "UTC",
                "wind_speed_unit": "ms",
                "apikey": api_key,
            },
        )
        for region in REGIONS
    ]


def collect_tomorrow_io() -> list[dict[str, Any]]:
    api_key = os.environ.get(TOMORROW_IO_API_KEY_ENV)
    if not api_key:
        raise MonitorAcquisitionError(f"{TOMORROW_IO_API_KEY_ENV} is not configured")
    return [
        _request_json(
            TOMORROW_IO_URL,
            {
                "location": f"{region.lat},{region.lon}",
                "units": "metric",
                "fields": ",".join(TOMORROW_FIELDS),
                "apikey": api_key,
            },
        )
        for region in REGIONS
    ]


Collector = Callable[[], dict[str, Any] | list[Any]]
_SOURCE_LOCKS: dict[MonitorSource, threading.Lock] = {
    "open-meteo": threading.Lock(),
    "mirror-earth-cma": threading.Lock(),
    "tomorrow-io": threading.Lock(),
}


class MonitorAcquisitionService:
    def __init__(
        self,
        store: MonitorSnapshotStore,
        collectors: dict[MonitorSource, Collector] | None = None,
    ) -> None:
        self.store = store
        self.collectors = collectors or {
            "open-meteo": collect_open_meteo,
            "mirror-earth-cma": collect_mirror_earth,
            "tomorrow-io": collect_tomorrow_io,
        }

    def source_status(self) -> list[MonitorSourceStatus]:
        return [
            MonitorSourceStatus(source="open-meteo", configured=True),
            MonitorSourceStatus(
                source="mirror-earth-cma",
                configured=bool(os.environ.get(MIRROR_EARTH_API_KEY_ENV)),
            ),
            MonitorSourceStatus(
                source="tomorrow-io",
                configured=bool(os.environ.get(TOMORROW_IO_API_KEY_ENV)),
            ),
        ]

    def get_or_refresh(
        self, source: MonitorSource, *, force_refresh: bool = False
    ) -> MonitorDataSnapshot:
        with _SOURCE_LOCKS[source]:
            if not force_refresh:
                cached = self.store.get_current(source)
                if cached is not None:
                    return cached
            collector = self.collectors[source]
            data = collector()
            if not isinstance(data, (dict, list)):
                raise MonitorAcquisitionError("Collector returned an unsupported payload")
            if isinstance(data, list) and len(data) != len(REGIONS):
                raise MonitorAcquisitionError(
                    f"Collector returned {len(data)} regions; expected {len(REGIONS)}"
                )
            return self.store.save(source, data)

    def refresh_configured_sources(self) -> dict[MonitorSource, str]:
        outcomes: dict[MonitorSource, str] = {}
        for status in self.source_status():
            if not status.configured:
                outcomes[status.source] = "not-configured"
                continue
            try:
                snapshot = self.get_or_refresh(status.source)
                outcomes[status.source] = snapshot.snapshot_id
            except MonitorAcquisitionError as exc:
                outcomes[status.source] = f"failed: {exc}"
        return outcomes
