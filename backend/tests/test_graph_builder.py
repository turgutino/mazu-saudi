"""Tests for knowledge_graph.graph_builder: node/edge counts and step ordering."""

from __future__ import annotations

from unittest.mock import patch

from app.domain.forecast_data import ForecastDataSnapshot, ForecastIndicatorBundle
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

    indicator_nodes = [n for n in graph.nodes if n.type == "indicator"]
    rule_nodes = [n for n in graph.nodes if n.type == "rule"]
    mechanism_nodes = [n for n in graph.nodes if n.type == "mechanism"]

    assert len(indicator_nodes) >= len(prediction.features)
    assert len([edge for edge in graph.edges if edge.type == "HAS_ATTRIBUTION"]) == len(prediction.features)
    assert len(mechanism_nodes) == len(prediction.mechanisms)
    assert len(rule_nodes) == len([h for h in prediction.rule_hits if h.met])


def test_graph_separates_input_values_from_model_attribution_edges():
    prediction = _build_prediction("dust-storm")
    graph = build_graph(prediction)

    indicator_nodes = [node for node in graph.nodes if node.type == "indicator"]
    indicator_ids = {node.id for node in indicator_nodes}
    assert "indicator-rh_surface" in indicator_ids
    assert "indicator-visibility" in indicator_ids
    assert all(node.evidence_kind != "model" for node in indicator_nodes)

    attribution_edges = [edge for edge in graph.edges if edge.type == "HAS_ATTRIBUTION"]
    assert len(attribution_edges) == len(prediction.features)
    assert all(edge.target in indicator_ids for edge in attribution_edges)
    assert all(edge.details.get("method") == "tree_shap" for edge in attribution_edges)

    mechanism_edges = [edge for edge in graph.edges if edge.type == "CONSISTENT_WITH"]
    assert any(edge.source == "indicator-rh_surface" for edge in mechanism_edges)
    assert any(edge.source == "indicator-visibility" for edge in mechanism_edges)


def test_graph_links_forecast_snapshot_to_indicator_values_and_model():
    prediction = _build_prediction("heavy-rain")
    snapshot = ForecastDataSnapshot(
        snapshot_id="forecast-test",
        cache_key="cache-test",
        source="open-meteo",
        region_id="jazan",
        target_time=prediction.target_time,
        fetched_at="2026-08-01T00:05:00+00:00",
        expires_at="2026-08-01T00:35:00+00:00",
        valid_from="2026-07-31T01:00",
        valid_to="2026-08-02T00:00",
        feature_version="live-api-daily-v1",
        status="valid",
        validation_error=None,
        raw_payload={},
        indicators={key: value for key, value in prediction.raw_indicators.items() if value is not None},
    )

    graph = build_graph(prediction, forecast_snapshot=snapshot)

    snapshot_node = next(node for node in graph.nodes if node.type == "snapshot")
    assert snapshot_node.id == "snapshot-forecast-test"
    assert snapshot_node.details["source"] == "open-meteo"
    assert snapshot_node.details["validFrom"] == "2026-07-31T01:00"
    assert snapshot_node.details["featureVersion"] == "live-api-daily-v1"
    assert any(
        edge.source == snapshot_node.id and edge.type == "PROVIDES"
        for edge in graph.edges
    )
    assert any(
        edge.target == "model-live-api-hgb-heavy_rain" and edge.type == "USED_BY"
        for edge in graph.edges
    )


def test_graph_declares_formal_ontology_version_and_indicator_mapping():
    prediction = _build_prediction("heavy-rain")
    graph = build_graph(prediction)

    assert graph.ontology_id == "urn:mazu-saudi:ontology"
    assert graph.ontology_version == "2.0.0"
    precipitation = next(
        node for node in graph.nodes if node.id == "indicator-daily_precip_total"
    )
    assert precipitation.details["ontologyIri"] == "urn:mazu-saudi:concept:DailyPrecipitation"
    assert precipitation.details["cfStandardName"] == "lwe_thickness_of_precipitation_amount"


def test_graph_hides_unverified_legacy_historical_mechanism_inputs():
    prediction = _build_prediction("dust-storm").model_copy(
        update={
            "data_tier": "tier1_real",
            "indicator_provenance_version": None,
        }
    )

    graph = build_graph(prediction)

    indicator_ids = {node.id for node in graph.nodes if node.type == "indicator"}
    assert "indicator-rh_surface" not in indicator_ids
    assert "indicator-visibility" not in indicator_ids
    mechanism_nodes = [node for node in graph.nodes if node.type == "mechanism"]
    assert mechanism_nodes
    assert all(node.status == "legacy-unverified-inputs" for node in mechanism_nodes)
    assert not [edge for edge in graph.edges if edge.type == "CONSISTENT_WITH"]
    assert all(
        edge.confidence is None for edge in graph.edges if edge.type == "FAVOURS"
    )


def test_graph_records_verified_tree_shap_semantics():
    prediction = _build_prediction("heavy-rain")
    graph = build_graph(prediction)

    prediction_node = next(node for node in graph.nodes if node.type == "prediction")
    assert prediction_node.details["attributionMethod"] == "tree_shap"
    assert prediction_node.details["attributionOutput"] == "raw_log_odds"
    attribution_edges = [edge for edge in graph.edges if edge.type == "HAS_ATTRIBUTION"]
    assert attribution_edges
    assert all("Tree SHAP" in edge.rationale for edge in attribution_edges)


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
