from pathlib import Path
import json

from fastapi.testclient import TestClient

from mazu_saudi.competition.app import create_app
from mazu_saudi.competition.settings import AppSettings
from mazu_saudi.competition.storage import AuditStore


class FakeAdapter:
    def forecast(self, city, target_date, hazard):
        return {
            "city": city,
            "target_date": target_date,
            "features_from_date": "2025-08-03",
            "hazard": hazard,
            "probability": 0.82,
            "grid_cell": {"lat": 21.4, "lon": 39.8},
            "elevation_m": 310.0,
            "terrain_note": None,
            "impact_context": None,
            "reflexive_check": {
                "detection_engine_risk_score": 0.75,
                "detection_engine_conditions_fired": ["tmax_c=48.0"],
                "consistency": "consistent_elevated",
            },
            "model_verified_roc_auc": 0.971,
            "meteorological_metrics": {
                "pod": 0.77,
                "far": 0.18,
                "csi": 0.68,
                "hss": 0.79,
            },
            "uncertainty": {"mean": 0.8, "std": 0.04, "range": [0.74, 0.85], "n_members": 5},
        }

    def conditions(self, city, date):
        return {"city": city, "date": date, "conditions": {"tmax_c": 48.0, "heat_index_c": 51.0}}

    def evidence(self, hazard):
        return {
            "hazard": hazard,
            "claim_boundary": "Hand-authored assertions; evidence retrieval only.",
            "contributing_indicators": ["tmax_c"],
            "mechanisms": [{"mechanism": "subtropical_high", "citations": []}],
        }

    def cap(self, city, target_date, hazard):
        return {
            "alert_warranted": True,
            "city": city,
            "target_date": target_date,
            "hazard": hazard,
            "cap_xml": "<alert><status>Exercise</status></alert>",
        }

    def field(self, target_date, hazard, layer):
        return {
            "target_date": target_date,
            "features_from_date": "2025-08-03",
            "hazard": hazard,
            "layer": layer,
            "rows": 1,
            "columns": 2,
            "latitudes": [21.4],
            "longitudes": [39.8, 39.9],
            "values": [0.2, 0.8],
            "minimum": 0.2,
            "maximum": 0.8,
            "cache": "miss",
        }


def make_client(tmp_path):
    settings = AppSettings(runtime_root=tmp_path / "runtime")
    store = AuditStore(settings.database_file, settings.artifact_root)
    return TestClient(create_app(settings, store, FakeAdapter())), settings


def test_full_historical_exercise_flow(tmp_path):
    client, _ = make_client(tmp_path)
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["ready_for_inference"] is True

    created = client.post(
        "/api/v1/runs",
        json={"city": "Mecca", "target_date": "2025-08-04", "hazard": "heatwave", "locale": "zh"},
    )
    assert created.status_code == 201
    run = created.json()
    assert run["status"] == "complete"
    assert run["result"]["mode"] == "historical_exercise"
    assert run["result"]["operational_warning"] is False
    assert run["result"]["forecast"]["features_from_date"] == "2025-08-03"
    assert run["result"]["decision"]["level"] == "elevated"

    field = client.get(f"/api/v1/runs/{run['id']}/field?layer=uncertainty")
    assert field.status_code == 200
    assert field.json()["values"] == [0.2, 0.8]

    evidence = client.get(f"/api/v1/runs/{run['id']}/evidence")
    assert evidence.json()["hazard"] == "heatwave"

    assistant = client.post(
        "/api/v1/assistant/messages",
        json={"run_id": run["id"], "message": "为什么？", "locale": "zh"},
    )
    assert assistant.status_code == 200
    assert assistant.json()["mode"] == "deterministic"
    assert "历史演练" in assistant.json()["content"]

    cap = client.post(f"/api/v1/runs/{run['id']}/cap")
    assert cap.status_code == 200
    assert "<status>Exercise</status>" in cap.json()["cap_xml"]
    assert "Actual" not in cap.json()["cap_xml"]

    report = client.post(f"/api/v1/runs/{run['id']}/report")
    assert report.status_code == 200
    artifact_id = report.json()["report"]["id"]
    download = client.get(f"/api/v1/artifacts/{artifact_id}")
    assert download.status_code == 200
    assert "Historical Exercise" in download.text
    assert "Save as PDF" in download.text

    history = client.get("/api/v1/runs").json()
    assert history[0]["id"] == run["id"]


def test_validation_archive_mode_and_safe_cap(tmp_path):
    client, _ = make_client(tmp_path)
    invalid_city = client.post(
        "/api/v1/runs",
        json={"city": "Unknown", "target_date": "2025-08-04", "hazard": "heatwave"},
    )
    assert invalid_city.status_code == 422
    invalid_date = client.post(
        "/api/v1/runs",
        json={"city": "Mecca", "target_date": "2025-01-01", "hazard": "heatwave"},
    )
    assert invalid_date.status_code == 422

    missing_settings = AppSettings(
        repository_root=tmp_path / "empty-repository",
        runtime_root=tmp_path / "archive-runtime",
    )
    archive_store = AuditStore(missing_settings.database_file, missing_settings.artifact_root)
    archive_client = TestClient(create_app(missing_settings, archive_store, FakeAdapter()))
    assert archive_client.get("/api/v1/health").json()["mode"] == "archive"
    blocked = archive_client.post(
        "/api/v1/runs",
        json={"city": "Mecca", "target_date": "2025-08-04", "hazard": "heatwave"},
    )
    assert blocked.status_code == 503
    assert "Archive mode" in blocked.json()["detail"]


def test_public_contract_has_no_future_model_or_operational_claims(tmp_path):
    client, _ = make_client(tmp_path)
    openapi = client.get("/openapi.json").json()
    payload = str(openapi)
    forbidden = ["MCR", "<status>Actual</status>", '"LIVE"']
    for term in forbidden:
        assert term not in payload
    config = client.get("/api/v1/config").json()
    assert "Not an operational warning" in config["boundaries"]
    assert config["date_range"] == {"start": "2025-01-02", "end": "2025-12-31"}
    routed_page = client.get("/analysis")
    assert routed_page.status_code == 200
    assert "MAZU Saudi" in routed_page.text


def test_optional_llm_reads_frozen_result_and_falls_back_safely(tmp_path, monkeypatch):
    client, _ = make_client(tmp_path)
    created = client.post(
        "/api/v1/runs",
        json={"city": "Mecca", "target_date": "2025-08-04", "hazard": "heatwave", "locale": "en"},
    ).json()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "Bounded analysis from frozen evidence."}}]}
            ).encode()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-key")
    monkeypatch.setattr(
        "mazu_saudi.competition.service.urllib_request.urlopen",
        lambda request, timeout: FakeResponse(),
    )
    response = client.post(
        "/api/v1/assistant/messages",
        json={"run_id": created["id"], "message": "Explain", "locale": "en"},
    )
    assert response.json()["mode"] == "deepseek"
    assert response.json()["content"] == "Bounded analysis from frozen evidence."

    monkeypatch.setattr(
        "mazu_saudi.competition.service.urllib_request.urlopen",
        lambda request, timeout: (_ for _ in ()).throw(TimeoutError()),
    )
    fallback = client.post(
        "/api/v1/assistant/messages",
        json={"run_id": created["id"], "message": "Explain", "locale": "en"},
    )
    assert fallback.json()["mode"] == "deterministic_fallback"
    assert "historical exercise" in fallback.json()["content"]
