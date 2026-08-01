from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.repositories.forecast_snapshot_store import (
    ForecastSnapshotStore,
    build_forecast_cache_key,
)


def test_snapshot_round_trips_raw_payload_and_indicators(tmp_path, monkeypatch):
    monkeypatch.setenv("MAZU_DB_PATH", str(tmp_path / "snapshots.db"))
    store = ForecastSnapshotStore()
    target = datetime(2026, 8, 2, tzinfo=timezone.utc)
    cache_key = build_forecast_cache_key(
        "open-meteo", "jazan", target, "live-api-daily-v1"
    )
    fetched = datetime(2026, 8, 1, 12, tzinfo=timezone.utc)
    saved = store.save(
        cache_key=cache_key,
        source="open-meteo",
        region_id="jazan",
        target_time=target,
        valid_from="2026-08-01T01:00",
        valid_to="2026-08-02T00:00",
        feature_version="live-api-daily-v1",
        raw_payload={"hourly": {"temperature_2m": [40.0]}},
        indicators={"t2m_c": 40.0},
        fetched_at=fetched,
    )

    loaded = store.get(saved.snapshot_id)
    assert loaded == saved
    assert store.get_fresh(cache_key, fetched + timedelta(minutes=29)) == saved
    assert store.get_fresh(cache_key, fetched + timedelta(minutes=31)) is None


def test_cache_key_is_hourly_and_feature_contract_specific():
    first = build_forecast_cache_key(
        "open-meteo",
        "jazan",
        datetime(2026, 8, 2, 0, 5, tzinfo=timezone.utc),
        "v1",
    )
    same_hour = build_forecast_cache_key(
        "open-meteo",
        "jazan",
        datetime(2026, 8, 2, 0, 59, tzinfo=timezone.utc),
        "v1",
    )
    changed_contract = build_forecast_cache_key(
        "open-meteo",
        "jazan",
        datetime(2026, 8, 2, 0, 5, tzinfo=timezone.utc),
        "v2",
    )
    assert first == same_hour
    assert first != changed_contract
