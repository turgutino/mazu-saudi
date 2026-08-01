"""Tests for knowledge_graph.graph_builder: node/edge counts and step ordering."""

from __future__ import annotations

from unittest.mock import patch

from app.domain.forecast_data import ForecastIndicatorBundle
from app.knowledge_graph.graph_builder import build_graph
from app.schemas.prediction import PredictionRequest
from app.services.prediction_service import PredictionService


def _build_prediction(hazard: str):
    service = PredictionService()
    request = PredictionRequest(region_id="jazan", hazard=hazard, lead_time_hours=24)
    with patch(
        "app.services.prediction_service.openmeteo_provider.generate_bundle",
        return_value=ForecastIndicatorBundle(
            indicators={"daily_precip_total": 8.0, "t2m_c": 42.0,
                        "tmax_c": 46.0, "tmin_c": 35.0, "wind10_speed": 15.0,
                        "lat": 16.8892, "lon": 42.5511, "day_of_year": 214.0,
                        "cape": 900.0, "daily_precip": 8.0, "t2m": 42.0,
                        "rh_surface": 30.0, "wind_10m": 15.0, "visibility": 8.0},
            snapshot_id="forecast-test", source="open-meteo", cache_hit=False,
        ),
    ):
        return service.run_prediction(request)


def test_graph_has_case_and_prediction_anchor_nodes():
    prediction = _build_prediction("flash-flood")
    graph = build_graph(prediction)

    assert graph.prediction_id == prediction.prediction_id
    node_types = {n.type for n in graph.nodes}
    assert "case" in node_types
    assert "prediction" in node_types
    assert "risk" in node_types


def test_graph_node_count_matches_feature_rule_mechanism_counts():
    prediction = _build_prediction("heavy-rain")
    graph = build_graph(prediction)

    feature_nodes = [n for n in graph.nodes if n.type == "feature"]
    rule_nodes = [n for n in graph.nodes if n.type == "rule"]
    mechanism_nodes = [n for n in graph.nodes if n.type == "mechanism"]

    assert len(feature_nodes) == len(prediction.features)
    assert len(mechanism_nodes) == len(prediction.mechanisms)
    assert len(rule_nodes) == len([h for h in prediction.rule_hits if h.met])


def test_graph_edges_reference_existing_node_ids():
    prediction = _build_prediction("dust-storm")
    graph = build_graph(prediction)

    node_ids = {n.id for n in graph.nodes}
    for edge in graph.edges:
        assert edge.source in node_ids, f"dangling edge source {edge.source}"
        assert edge.target in node_ids, f"dangling edge target {edge.target}"


def test_warning_node_present_only_when_risk_above_green():
    green_prediction = _build_prediction("dust-storm")
    graph = build_graph(green_prediction)
    has_warning = any(n.type == "warning" for n in graph.nodes)
    assert has_warning == (green_prediction.risk_level != "green")


def test_steps_are_non_decreasing_from_case_to_events():
    prediction = _build_prediction("extreme-heat")
    graph = build_graph(prediction)
    steps = sorted(n.step for n in graph.nodes)
    assert steps[0] == 0
    assert steps[-1] <= 6
