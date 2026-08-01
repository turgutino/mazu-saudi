"""Feature contract shared by 2025 training data and live forecast APIs."""

from __future__ import annotations

import calendar
from datetime import datetime

import numpy as np

from app.data.live_forecast_utils import trailing_hourly_window

FEATURE_VERSION = "live-api-daily-v1"
MODEL_FEATURES = [
    "daily_precip_total",
    "t2m_c",
    "tmax_c",
    "tmin_c",
    "wind10_speed",
    "lat",
    "lon",
    "day_of_year",
]
HOURLY_SOURCE_FIELDS = {
    "daily_precip_total": "precipitation",
    "temperature": "temperature_2m",
    "cape": "cape",
    "wind": "wind_speed_10m",
}


def day_of_year_365(value: datetime) -> int:
    day = value.timetuple().tm_yday
    if calendar.isleap(value.year):
        if value.month == 2 and value.day == 29:
            return 59
        if day > 59:
            return day - 1
    return day


def aggregate_live_features(
    hourly: dict[str, list], target_index: int, target_time: datetime, lat: float, lon: float
) -> dict[str, float]:
    times = hourly.get("time", [])
    precipitation = trailing_hourly_window(
        times, hourly.get("precipitation"), target_index, 24
    )
    temperature = trailing_hourly_window(
        times, hourly.get("temperature_2m"), target_index, 24
    )
    cape = trailing_hourly_window(times, hourly.get("cape"), target_index, 24)
    wind = trailing_hourly_window(
        times, hourly.get("wind_speed_10m"), target_index, 24
    )
    missing = [
        name
        for name, values in {
            "precipitation": precipitation,
            "temperature_2m": temperature,
            "wind_speed_10m": wind,
        }.items()
        if values is None
    ]
    if missing:
        raise ValueError(f"Incomplete 24-hour API feature window: {missing}")
    assert precipitation is not None and temperature is not None
    assert wind is not None
    features = {
        "daily_precip_total": round(float(np.sum(precipitation)), 4),
        "t2m_c": round(float(np.mean(temperature)), 4),
        "tmax_c": round(float(np.max(temperature)), 4),
        "tmin_c": round(float(np.min(temperature)), 4),
        "wind10_speed": round(float(np.mean(wind)), 4),
        "lat": float(lat),
        "lon": float(lon),
        "day_of_year": float(day_of_year_365(target_time)),
    }
    result = {
        **features,
        "daily_precip": features["daily_precip_total"],
        "t2m": features["t2m_c"],
        "wind_10m": features["wind10_speed"],
    }
    # CAPE is persisted and remains available to risk explanations when the
    # API supplies a complete window, but it is not a required ML feature
    # because it only exists on 293/365 days in the 2025 archive.
    if cape is not None:
        result["cape"] = round(float(np.max(cape)), 4)
    return result
