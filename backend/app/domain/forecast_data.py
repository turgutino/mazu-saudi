"""Domain objects for persisted third-party forecast data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ForecastDataSnapshot:
    snapshot_id: str
    cache_key: str
    source: str
    region_id: str
    target_time: str
    fetched_at: str
    expires_at: str
    valid_from: str
    valid_to: str
    feature_version: str
    status: str
    validation_error: str | None
    raw_payload: dict
    indicators: dict[str, float]


@dataclass(frozen=True)
class ForecastIndicatorBundle:
    indicators: dict[str, float]
    snapshot_id: str
    source: str
    cache_hit: bool
