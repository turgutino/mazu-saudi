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
    best_index = 0
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
    return best_index
