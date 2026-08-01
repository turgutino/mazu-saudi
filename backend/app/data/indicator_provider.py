"""IndicatorProvider: v1 placeholder generator for per-case meteorological indicators.

No NetCDF/ERA5 data is read in v1. Instead, for a given ForecastCase we
deterministically derive a pseudo-random "severity" in [0, 1] from the case's
``input_hash`` and use it to skew each relevant indicator toward its high (or
low) end. The same input always yields the same indicators — nothing is
invented on the fly. The public interface (``generate``) is designed so a
future implementation can swap in real NetCDF-backed extraction without
touching callers.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.domain.forecast_case import ForecastCase


@dataclass(frozen=True)
class IndicatorSpec:
    key: str
    label: str
    unit: str
    min_value: float
    max_value: float
    normal_value: float
    direction: int  # +1: higher value -> more severe; -1: lower value -> more severe


INDICATOR_SPECS: dict[str, IndicatorSpec] = {
    "cape": IndicatorSpec("cape", "CAPE", "J/kg", 50, 3200, 800, +1),
    "pw": IndicatorSpec("pw", "可降水量", "mm", 8, 65, 32, +1),
    "daily_precip": IndicatorSpec("daily_precip", "日降水预测", "mm", 0, 75, 6, +1),
    "vapor_850": IndicatorSpec("vapor_850", "850hPa水汽输送", "g/kg", 3, 26, 9, +1),
    "shear_500": IndicatorSpec("shear_500", "500hPa风切变", "m/s", 4, 32, 13, +1),
    "rh_700": IndicatorSpec("rh_700", "700hPa相对湿度", "%", 30, 96, 58, +1),
    "t850": IndicatorSpec("t850", "850hPa温度", "°C", 18, 38, 27, +1),
    "t2m": IndicatorSpec("t2m", "2m气温预测", "°C", 30, 52, 41, +1),
    "rh_surface": IndicatorSpec("rh_surface", "地表相对湿度", "%", 3, 80, 25, -1),
    "h500": IndicatorSpec("h500", "500hPa位势高度", "gpm", 5850, 6000, 5900, +1),
    "wind_10m": IndicatorSpec("wind_10m", "10m风速", "m/s", 2, 32, 11, +1),
    "soil_moisture": IndicatorSpec("soil_moisture", "土壤湿度", "m³/m³", 0.02, 0.35, 0.15, -1),
    "visibility": IndicatorSpec("visibility", "能见度预测", "km", 0.5, 20, 10, -1),
    # Tier 2 enrichment-only indicators, sourced from Tomorrow.io
    # (frontend/src/services/tomorrowIoApi.ts fetches the same 3 fields
    # client-side). No synthetic Tier 3 baseline exists for these -- they
    # only ever appear in ``indicators`` when a live Tomorrow.io call
    # succeeds (see app/data/tomorrowio_provider.py), so DegradedForecastModel
    # skips them gracefully via its "key not in indicators" guard whenever
    # they're absent.
    "wind_gust": IndicatorSpec("wind_gust", "阵风风速", "m/s", 2, 40, 14, +1),
    "fire_index": IndicatorSpec("fire_index", "火险指数", "", 0, 100, 30, +1),
    "thunderstorm_prob": IndicatorSpec("thunderstorm_prob", "雷暴概率", "%", 0, 100, 20, +1),
}

HAZARD_INDICATORS: dict[str, list[str]] = {
    "heavy-rain": ["cape", "pw", "daily_precip", "vapor_850", "shear_500", "rh_700"],
    "extreme-heat": ["t850", "t2m", "rh_surface", "h500"],
    "flash-flood": ["cape", "pw", "daily_precip", "vapor_850", "rh_700"],
    "dust-storm": ["wind_10m", "soil_moisture", "visibility", "rh_surface"],
}


class IndicatorProvider:
    """Deterministic pseudo-observation generator, seeded by ForecastCase.input_hash."""

    def generate(self, case: ForecastCase) -> dict[str, float]:
        keys = HAZARD_INDICATORS.get(case.hazard, [])
        rng = np.random.RandomState(case.seed)
        severity = float(rng.beta(2, 3))
        indicators: dict[str, float] = {}
        for key in keys:
            spec = INDICATOR_SPECS[key]
            noise = float(rng.normal(0, 0.08))
            t = min(max(severity + noise, 0.0), 1.0)
            if spec.direction > 0:
                value = spec.min_value + t * (spec.max_value - spec.min_value)
            else:
                value = spec.max_value - t * (spec.max_value - spec.min_value)
            indicators[key] = round(value, 3)
        return indicators


indicator_provider = IndicatorProvider()


def normalized_severity(key: str, actual: float) -> float:
    """Map an indicator's actual value to a signed severity in roughly [-1, 1]
    around its ``normal_value``, using ``INDICATOR_SPECS``. Shared by every
    ForecastModel implementation (rule-based, joblib, degraded) so their
    ``important_features`` explanations stay directly comparable regardless
    of which algorithm produced the probability.
    """
    spec = INDICATOR_SPECS[key]
    span = spec.max_value - spec.min_value
    return spec.direction * (actual - spec.normal_value) / span


def with_overrides(case: ForecastCase, overrides: dict[str, float]) -> dict[str, float]:
    """Deterministic placeholder indicators for ``case``, with ``overrides``
    merged on top. The archived provider uses this for its historical
    explanation contract, while additional raw model feature names are simply
    added. Live providers intentionally do not call this helper.
    """
    merged = indicator_provider.generate(case)
    merged.update(overrides)
    return merged
