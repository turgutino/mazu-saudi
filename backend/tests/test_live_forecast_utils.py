"""Unit tests for shared Tier 2 live-forecast helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.data.live_forecast_utils import forecast_days_for, nearest_hour_index


def test_forecast_days_for_covers_near_term_lead_time():
    target = datetime.now(timezone.utc) + timedelta(hours=6)
    assert forecast_days_for(target) >= 1


def test_forecast_days_for_covers_multi_day_lead_time():
    target = datetime.now(timezone.utc) + timedelta(hours=72)
    days = forecast_days_for(target)
    assert days >= 4


def test_forecast_days_for_clamps_to_api_maximum():
    target = datetime.now(timezone.utc) + timedelta(days=365)
    assert forecast_days_for(target) == 16


def test_nearest_hour_index_picks_closest_entry():
    target = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    times = ["2026-08-01T00:00", "2026-08-01T11:00", "2026-08-01T13:00"]
    assert nearest_hour_index(times, target) == 1


def test_nearest_hour_index_returns_none_for_empty_list():
    target = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    assert nearest_hour_index([], target) is None


def test_nearest_hour_index_skips_unparseable_entries():
    target = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    times = ["not-a-date", "2026-08-01T12:00"]
    assert nearest_hour_index(times, target) == 1
