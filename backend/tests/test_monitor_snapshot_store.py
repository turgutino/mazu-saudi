from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.deps import get_monitor_acquisition_service, get_monitor_snapshot_store
from app.main import create_app
from app.repositories.monitor_snapshot_store import (
    MonitorSnapshotStore,
    monitor_bucket_start,
)
from app.services.monitor_acquisition import MonitorAcquisitionService


def test_monitor_snapshots_use_fixed_six_hour_utc_buckets(tmp_path, monkeypatch):
    monkeypatch.setenv("MAZU_DB_PATH", str(tmp_path / "monitor.db"))
    store = MonitorSnapshotStore()
    fetched = datetime(2026, 8, 1, 13, 47, tzinfo=timezone.utc)

    first = store.save("open-meteo", {"regions": [1]}, fetched_at=fetched)
    second = store.save(
        "open-meteo", {"regions": [2]}, fetched_at=fetched.replace(hour=14)
    )

    assert monitor_bucket_start(fetched).isoformat() == "2026-08-01T12:00:00+00:00"
    assert first.bucket_start == "2026-08-01T12:00:00+00:00"
    assert first.expires_at == "2026-08-01T18:00:00+00:00"
    assert store.get_current("open-meteo", fetched).snapshot_id == second.snapshot_id
    assert store.get_current(
        "open-meteo", datetime(2026, 8, 1, 18, tzinfo=timezone.utc)
    ) is None
    assert len(store.list("open-meteo")) == 2


def test_monitor_snapshot_api_returns_current_cache_before_refetch(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("MAZU_DB_PATH", str(tmp_path / "monitor-api.db"))
    store = MonitorSnapshotStore()
    app = create_app(monitor_scheduler_enabled=False)
    app.dependency_overrides[get_monitor_snapshot_store] = lambda: store
    client = TestClient(app)

    missing = client.get("/api/v1/monitor/snapshots/open-meteo")
    assert missing.status_code == 404

    payload = [{"regionId": f"region-{index}"} for index in range(8)]
    service = MonitorAcquisitionService(store, collectors={
        "open-meteo": lambda: payload,
        "mirror-earth-cma": lambda: payload,
        "tomorrow-io": lambda: payload,
    })
    app.dependency_overrides[get_monitor_acquisition_service] = lambda: service

    created = client.post("/api/v1/monitor/snapshots/open-meteo/refresh")
    assert created.status_code == 200
    assert created.json()["cacheHit"] is False

    cached = client.get("/api/v1/monitor/snapshots/open-meteo")
    assert cached.status_code == 200
    assert cached.json()["cacheHit"] is True
    assert cached.json()["snapshotId"] == created.json()["snapshotId"]
    assert cached.json()["data"][0]["regionId"] == "region-0"

    removed_public_write = client.post(
        "/api/v1/monitor/snapshots",
        json={"source": "open-meteo", "data": {"arbitrary": True}},
    )
    assert removed_public_write.status_code == 404
