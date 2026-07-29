"""Canonical physical indicator formulas shared by all data pipelines."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeVar

import numpy as np


INDICATOR_FORMULA_VERSION = "1.0.0"
GRAVITY_M_S2 = 9.80665
FYMERG_FRAME_DURATION_HOURS = 0.5
FYMERG_EXPECTED_FRAMES_PER_DAY = 48
DEFAULT_IVT_LEVELS_HPA = (1000, 925, 850, 700, 500, 300)

ArrayLike = TypeVar("ArrayLike")


def kelvin_to_celsius(values: ArrayLike) -> ArrayLike:
    """Convert Kelvin values while preserving NumPy/xarray container behavior."""

    return values - 273.15


def wind_speed(zonal: ArrayLike, meridional: ArrayLike) -> ArrayLike:
    """Return vector magnitude for matching zonal and meridional components."""

    return np.sqrt(zonal**2 + meridional**2)


def vapor_pressure_deficit_kpa(
    temperature_c: ArrayLike,
    relative_humidity_percent: ArrayLike,
) -> ArrayLike:
    """Compute VPD in kPa from air temperature and relative humidity."""

    saturation_kpa = 0.6108 * np.exp(
        (17.27 * temperature_c) / (temperature_c + 237.3)
    )
    return saturation_kpa * (1.0 - relative_humidity_percent / 100.0)


def ivt_pressure_weights(
    levels_hpa: Sequence[int] = DEFAULT_IVT_LEVELS_HPA,
) -> dict[int, float]:
    """Return trapezoidal pressure weights including Pa conversion and 1/g."""

    levels = np.asarray(sorted(set(levels_hpa)), dtype=np.float64)
    if levels.size < 2 or np.any(levels <= 0):
        raise ValueError("At least two positive IVT pressure levels are required")
    weights = np.empty_like(levels)
    weights[0] = (levels[1] - levels[0]) / 2.0
    weights[-1] = (levels[-1] - levels[-2]) / 2.0
    weights[1:-1] = (levels[2:] - levels[:-2]) / 2.0
    return {
        int(level): float(weight * 100.0 / GRAVITY_M_S2)
        for level, weight in zip(levels, weights)
    }


def integrate_ivt(
    humidity: Mapping[int, ArrayLike],
    zonal_wind: Mapping[int, ArrayLike],
    meridional_wind: Mapping[int, ArrayLike],
    levels_hpa: Sequence[int] = DEFAULT_IVT_LEVELS_HPA,
) -> tuple[ArrayLike, ArrayLike, ArrayLike]:
    """Integrate IVT components and magnitude over one explicit level contract."""

    weights = ivt_pressure_weights(levels_hpa)
    missing = {
        variable: sorted(set(weights) - set(fields))
        for variable, fields in {
            "q": humidity,
            "u": zonal_wind,
            "v": meridional_wind,
        }.items()
        if set(weights) - set(fields)
    }
    if missing:
        raise ValueError(f"IVT source levels are incomplete: {missing}")

    first_level = next(iter(weights))
    ivt_u = humidity[first_level] * 0.0
    ivt_v = humidity[first_level] * 0.0
    for level, weight in weights.items():
        ivt_u = ivt_u + humidity[level] * zonal_wind[level] * weight
        ivt_v = ivt_v + humidity[level] * meridional_wind[level] * weight
    magnitude = wind_speed(ivt_u, ivt_v)
    return ivt_u, ivt_v, magnitude


def precipitation_rate_to_amount(
    rate_mm_per_hour: ArrayLike,
    duration_hours: float = FYMERG_FRAME_DURATION_HOURS,
) -> ArrayLike:
    """Convert an interval-average precipitation rate to interval amount."""

    if duration_hours <= 0:
        raise ValueError("Precipitation interval duration must be positive")
    return rate_mm_per_hour * duration_hours


def rolling_precipitation_amount_max(
    rate_stack_mm_per_hour: np.ndarray,
    window_frames: int,
    duration_hours: float = FYMERG_FRAME_DURATION_HOURS,
) -> np.ndarray:
    """Return the maximum accumulated amount over a rolling frame window."""

    if rate_stack_mm_per_hour.shape[0] == 0:
        raise ValueError("Cannot aggregate an empty precipitation-rate stack")
    if window_frames <= 0:
        raise ValueError("Rolling precipitation window must be positive")
    amount_stack = precipitation_rate_to_amount(
        rate_stack_mm_per_hour,
        duration_hours,
    )
    if amount_stack.shape[0] <= window_frames:
        return np.nansum(amount_stack, axis=0)
    best = None
    for start in range(0, amount_stack.shape[0] - window_frames + 1):
        window_sum = np.nansum(
            amount_stack[start : start + window_frames],
            axis=0,
        )
        best = window_sum if best is None else np.maximum(best, window_sum)
    return best
