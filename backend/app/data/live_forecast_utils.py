"""Shared helpers for Tier 2 live *forecast* providers (Open-Meteo, Mirror
Earth). Both call an hourly forecast endpoint and need to pick out the
single hour matching a ForecastCase's ``target_time`` — this replaces the
older "just read whatever `current=...` says right now" approach, which
ignored ``lead_time_hours`` entirely and always returned the same value
regardless of how far out the forecast was for.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

MAX_FORECAST_DAYS = 16
MAX_TARGET_OFFSET_SECONDS = 60 * 60


def forecast_days_for(target_time: datetime) -> int:
    """How many days of hourly forecast to request so ``target_time`` (which
    may be up to 72h -- see app/data/hazards.py lead_times -- beyond "now")
    is covered, clamped to what the API supports."""
    now = datetime.now(timezone.utc)
    delta_days = (target_time - now).total_seconds() / 86400.0
    days = max(1, math.ceil(delta_days) + 1)
    return min(days, MAX_FORECAST_DAYS)


def nearest_hour_index(time_strings: list[str], target_time: datetime) -> int | None:
    """Index into an hourly API response's ``time`` array closest to
    ``target_time``. Returns None if ``time_strings`` is empty."""
    if not time_strings:
        return None
    target = target_time.astimezone(timezone.utc).replace(tzinfo=None)
    best_index = None
    best_diff = None
    for index, raw in enumerate(time_strings):
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            continue
        diff = abs((parsed - target).total_seconds())
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_index = index
    if best_diff is None or best_diff > MAX_TARGET_OFFSET_SECONDS:
        return None
    return best_index


def trailing_hourly_sum(
    time_strings: list[str], values: list[float | None] | None, end_index: int, hours: int
) -> float | None:
    """Sum a complete, contiguous hourly window ending at ``end_index``.

    Hourly precipitation values represent the preceding hour, so 24 values
    ending at the target timestamp form the preceding 24-hour accumulation.
    Incomplete or gapped windows return ``None`` instead of silently treating
    missing hours as zero.
    """
    if values is None or hours <= 0:
        return None
    start_index = end_index - hours + 1
    if start_index < 0 or end_index >= len(values) or end_index >= len(time_strings):
        return None

    parsed_times: list[datetime] = []
    window_values: list[float] = []
    for index in range(start_index, end_index + 1):
        value = values[index]
        if value is None:
            return None
        try:
            parsed_times.append(datetime.fromisoformat(time_strings[index]))
            window_values.append(float(value))
        except (ValueError, TypeError):
            return None

    if any(
        (current - previous).total_seconds() != 3600
        for previous, current in zip(parsed_times, parsed_times[1:])
    ):
        return None
    return round(sum(window_values), 3)


def trailing_hourly_window(
    time_strings: list[str], values: list[float | None] | None, end_index: int, hours: int
) -> list[float] | None:
    """Return a complete contiguous hourly window, or ``None`` when incomplete."""
    if values is None or hours <= 0:
        return None
    start_index = end_index - hours + 1
    if start_index < 0 or end_index >= len(values) or end_index >= len(time_strings):
        return None
    parsed_times: list[datetime] = []
    window: list[float] = []
    for index in range(start_index, end_index + 1):
        value = values[index]
        if value is None:
            return None
        try:
            parsed_times.append(datetime.fromisoformat(time_strings[index]))
            window.append(float(value))
        except (ValueError, TypeError):
            return None
    if any(
        (current - previous).total_seconds() != 3600
        for previous, current in zip(parsed_times, parsed_times[1:])
    ):
        return None
    return window
