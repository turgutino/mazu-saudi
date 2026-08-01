from __future__ import annotations

import pytest
from datetime import datetime, timezone

from app.repositories.monitor_snapshot_store import MonitorSnapshotStore
from app.services.monitor_acquisition import (
    MonitorAcquisitionError,
    MonitorAcquisitionService,
    collect_open_meteo,
)
from app.services.monitor_scheduler import seconds_until_next_bucket


def _payload(marker: str) -> list[dict[str, str]]:
    return [{"region": str(index), "marker": marker} for index in range(8)]


def test_database_snapshot_is_used_before_backend_collector(tmp_path, monkeypatch):
    monkeypatch.setenv("MAZU_DB_PATH", str(tmp_path / "monitor-acquisition.db"))
    store = MonitorSnapshotStore()
    calls = 0

    def collector():
        nonlocal calls
        calls += 1
        return _payload(f"call-{calls}")

    service = MonitorAcquisitionService(store, collectors={
        "open-meteo": collector,
        "mirror-earth-cma": collector,
        "tomorrow-io": collector,
    })

    first = service.get_or_refresh("open-meteo")
    cached = service.get_or_refresh("open-meteo")
    refreshed = service.get_or_refresh("open-meteo", force_refresh=True)

    assert calls == 2
    assert first.cache_hit is False
    assert cached.cache_hit is True
    assert cached.snapshot_id == first.snapshot_id
    assert refreshed.snapshot_id != first.snapshot_id


def test_rejects_partial_region_payload_before_persistence(tmp_path, monkeypatch):
    monkeypatch.setenv("MAZU_DB_PATH", str(tmp_path / "monitor-invalid.db"))
    store = MonitorSnapshotStore()
    service = MonitorAcquisitionService(store, collectors={
        "open-meteo": lambda: [{"region": "only-one"}],
        "mirror-earth-cma": lambda: _payload("unused"),
        "tomorrow-io": lambda: _payload("unused"),
    })

    with pytest.raises(MonitorAcquisitionError, match="expected 8"):
        service.get_or_refresh("open-meteo", force_refresh=True)

    assert store.list("open-meteo") == []


def test_optional_source_configuration_is_reported_server_side(tmp_path, monkeypatch):
    monkeypatch.setenv("MAZU_DB_PATH", str(tmp_path / "monitor-status.db"))
    monkeypatch.delenv("MIRROR_EARTH_API_KEY", raising=False)
    monkeypatch.setenv("TOMORROW_IO_API_KEY", "server-secret")
    statuses = MonitorAcquisitionService(MonitorSnapshotStore()).source_status()

    assert [(status.source, status.configured) for status in statuses] == [
        ("open-meteo", True),
        ("mirror-earth-cma", False),
        ("tomorrow-io", True),
    ]


def test_scheduler_waits_for_the_next_fixed_six_hour_bucket():
    now = datetime(2026, 8, 1, 13, 30, tzinfo=timezone.utc)
    assert seconds_until_next_bucket(now) == 4.5 * 60 * 60


def test_open_meteo_collection_is_server_side_and_covers_all_regions(monkeypatch):
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"latitude": 1, "longitude": 2, "current": {}, "hourly": {}}

    def fake_get(url, *, params, timeout):
        calls.append((url, params, timeout))
        return Response()

    monkeypatch.setattr("app.services.monitor_acquisition.requests.get", fake_get)

    payload = collect_open_meteo()

    assert len(payload) == 8
    assert len(calls) == 8
    assert all("current" in params and "hourly" in params for _, params, _ in calls)
    assert all("apikey" not in params for _, params, _ in calls)
