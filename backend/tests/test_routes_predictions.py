"""End-to-end FastAPI TestClient tests covering all API contracts."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.domain.forecast_data import ForecastIndicatorBundle
from app.repositories.prediction_store import prediction_store

HAZARDS = ["heavy-rain", "extreme-heat", "flash-flood", "dust-storm"]


@pytest.fixture()
def client() -> TestClient:
    prediction_store.clear()
    return TestClient(app)


@pytest.fixture(autouse=True)
def live_forecast(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.services.prediction_service.openmeteo_provider.generate_bundle",
        lambda case: ForecastIndicatorBundle(
            indicators={"daily_precip_total": 8.0, "t2m_c": 42.0,
                        "tmax_c": 46.0, "tmin_c": 35.0, "wind10_speed": 15.0,
                        "lat": 16.8892, "lon": 42.5511, "day_of_year": 214.0,
                        "cape": 900.0, "daily_precip": 8.0, "t2m": 42.0,
                        "rh_surface": 30.0, "wind_10m": 15.0, "visibility": 8.0},
            snapshot_id="forecast-test", source="open-meteo", cache_hit=False,
        ),
    )


def test_list_regions(client: TestClient):
    r = client.get("/api/v1/regions")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 8
    assert {"id", "name", "nameEn", "lat", "lon", "sensitivity"} <= body[0].keys()


def test_list_hazards(client: TestClient):
    r = client.get("/api/v1/hazards")
    assert r.status_code == 200
    ids = {h["id"] for h in r.json()}
    assert ids == set(HAZARDS)


def test_list_models(client: TestClient):
    r = client.get("/api/v1/models")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_monitor_regions(client: TestClient):
    r = client.get("/api/v1/monitor/regions")
    assert r.status_code == 200
    assert len(r.json()) == 8


def test_dashboard_stats_and_activities(client: TestClient):
    r = client.get("/api/v1/dashboard/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["totalPredictions"] == 0
    assert body["activeWarnings"] == 0
    assert body["regionRisk"] == []
    assert body["lastUpdated"] is None

    r = client.get("/api/v1/dashboard/activities")
    assert r.status_code == 200
    assert r.json() == []

    r = client.get("/api/v1/dashboard/weekly-stats")
    assert r.status_code == 200
    assert len(r.json()) == 7

    # After a prediction, all three endpoints reflect it.
    pred = client.post(
        "/api/v1/predictions",
        json={"regionId": "jazan", "hazard": "flash-flood", "leadTimeHours": 24},
    ).json()

    r = client.get("/api/v1/dashboard/stats")
    stats = r.json()
    assert stats["totalPredictions"] == 1
    assert {"regionId": "jazan", "regionName": "吉赞", "riskLevel": pred["riskLevel"]} in stats["regionRisk"]
    assert stats["lastUpdated"] == pred["createdAt"]

    r = client.get("/api/v1/dashboard/activities")
    activities = r.json()
    assert len(activities) == 1
    assert activities[0]["id"] == pred["predictionId"]

    r = client.get("/api/v1/dashboard/weekly-stats")
    weekly = r.json()
    assert sum(day["predictions"] for day in weekly) == 1


@pytest.mark.parametrize("hazard", HAZARDS)
def test_prediction_end_to_end_per_hazard(client: TestClient, hazard: str):
    r = client.post(
        "/api/v1/predictions",
        json={"regionId": "jazan", "hazard": hazard, "leadTimeHours": 24},
    )
    assert r.status_code == 200, r.text
    body = r.json()

    required_fields = {
        "predictionId", "caseId", "modelId", "modelVersion", "modelName",
        "hazard", "hazardLabel", "regionId", "regionName", "targetTime",
        "leadTimeHours", "initialTime", "probability", "calibratedProbability",
        "predictedClass", "uncertainty", "features", "ruleHits", "mechanisms",
        "similarEvents", "riskLevel", "riskLabel", "riskDescription",
        "inputHash", "createdAt",
    }
    assert required_fields <= body.keys()
    assert body["hazard"] == hazard
    assert body["riskLevel"] in {"green", "yellow", "orange", "red"}

    # GET by id round-trips the same prediction
    get_r = client.get(f"/api/v1/predictions/{body['predictionId']}")
    assert get_r.status_code == 200
    assert get_r.json()["predictionId"] == body["predictionId"]

    # knowledge graph is buildable for this prediction
    graph_r = client.get(f"/api/v1/knowledge-graph/{body['predictionId']}")
    assert graph_r.status_code == 200
    graph = graph_r.json()
    assert graph["predictionId"] == body["predictionId"]
    assert len(graph["nodes"]) > 0
    assert len(graph["edges"]) > 0


def test_list_predictions_filters_by_region_and_hazard(client: TestClient):
    client.post("/api/v1/predictions", json={"regionId": "riyadh", "hazard": "extreme-heat", "leadTimeHours": 48})
    r = client.get("/api/v1/predictions", params={"regionId": "riyadh", "hazard": "extreme-heat"})
    assert r.status_code == 200
    assert all(p["regionId"] == "riyadh" and p["hazard"] == "extreme-heat" for p in r.json())


def test_prediction_rejects_unknown_region(client: TestClient):
    r = client.post("/api/v1/predictions", json={"regionId": "atlantis", "hazard": "heavy-rain", "leadTimeHours": 24})
    assert r.status_code == 422


def test_historical_mode_rejects_hazard_without_trained_model(client: TestClient):
    r = client.post(
        "/api/v1/predictions",
        json={
            "regionId": "jazan",
            "hazard": "heavy-rain",
            "leadTimeHours": 24,
            "initialTime": "2025-06-01T00:00:00Z",
            "predictionMode": "historical",
        },
    )
    assert r.status_code == 422
    assert "No historical trained model" in r.json()["detail"]


def test_get_prediction_404_when_missing(client: TestClient):
    r = client.get("/api/v1/predictions/does-not-exist")
    assert r.status_code == 404


def test_knowledge_graph_404_when_prediction_missing(client: TestClient):
    r = client.get("/api/v1/knowledge-graph/does-not-exist")
    assert r.status_code == 404
