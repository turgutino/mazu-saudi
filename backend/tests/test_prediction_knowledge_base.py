from __future__ import annotations

from datetime import datetime, timezone

from app.explanation.mechanism_explanation import build_mechanisms
from app.explanation.similar_events import find_similar_events
from app.domain.forecast_data import ForecastIndicatorBundle
from app.knowledge_graph.graph_builder import build_graph
from app.knowledge_graph.knowledge_base import load_knowledge_base
from unittest.mock import patch

from app.schemas.prediction import PredictionRequest
from app.services.prediction_service import PredictionService


def test_catalog_references_known_literature_and_fixed_sweet_source():
    knowledge = load_knowledge_base()

    assert knowledge["version"] == "1.0.0"
    assert len(knowledge["mechanisms"]) == 4
    assert knowledge["sweetSource"]["commit"]
    for mechanism in knowledge["mechanisms"]:
        assert mechanism["evidenceIds"]
        assert set(mechanism["evidenceIds"]) <= set(knowledge["literatureById"])


def test_analog_retrieval_excludes_cases_at_or_after_forecast_origin():
    events = find_similar_events(
        "extreme-heat",
        "dammam",
        datetime(2025, 7, 1, tzinfo=timezone.utc),
        {"t2m": 45.0, "t850": 34.0, "rh_surface": 12.0},
    )

    assert [event.event_id for event in events] == ["case-ref-20250616-dammam-heat"]
    assert all(datetime.fromisoformat(event.date) < datetime(2025, 7, 1) for event in events)


def test_analog_result_explains_dimensions_and_missing_data_coverage():
    events = find_similar_events(
        "flash-flood",
        "jazan",
        datetime(2026, 8, 1, tzinfo=timezone.utc),
        {"daily_precip": 42.0, "cape": 1800.0, "pw": 30.0, "rh_700": 80.0},
    )

    assert events
    best = events[0]
    assert {item.key for item in best.similarity_dimensions} == {"weather", "spatial", "seasonal"}
    assert sum(item.weight for item in best.similarity_dimensions) == 1.0
    assert 0 < best.data_coverage < 1
    assert best.source_title


def test_mechanism_compatibility_is_grounded_but_not_causal():
    paths = build_mechanisms(
        "flash-flood",
        "jazan",
        {"vapor_850": 22.0, "pw": 55.0, "cape": 2400.0, "daily_precip": 45.0, "rh_700": 88.0},
    )

    assert {path.path_id for path in paths} == {"moisture-convection", "orographic-enhancement"}
    assert all(path.evidence_ids and 0 <= path.support_score <= 1 for path in paths)
    assert all(0 <= step.compatibility <= 1 for path in paths for step in path.steps)


def test_explanation_graph_keeps_evidence_layers_and_rationales():
    with patch(
        "app.services.prediction_service.openmeteo_provider.generate_bundle",
        return_value=ForecastIndicatorBundle(
            indicators={"daily_precip_total": 8.0, "t2m_c": 42.0,
                        "tmax_c": 46.0, "tmin_c": 35.0, "wind10_speed": 15.0,
                        "lat": 16.8892, "lon": 42.5511, "day_of_year": 214.0,
                        "cape": 900.0, "daily_precip": 8.0, "t2m": 42.0,
                        "wind_10m": 15.0},
            snapshot_id="forecast-test", source="open-meteo", cache_hit=False,
        ),
    ):
        prediction = PredictionService().run_prediction(
            PredictionRequest(
                region_id="jazan",
                hazard="flash-flood",
                lead_time_hours=6,
                initial_time="2026-08-01T00:00:00Z",
            )
        )
    graph = build_graph(prediction)

    assert graph.graph_version == "1.0.0"
    assert any(node.evidence_kind == "literature" for node in graph.nodes)
    assert any(node.evidence_kind == "ontology" for node in graph.nodes)
    assert "causation" in graph.disclaimer
    assert all(edge.rationale for edge in graph.edges)
    assert "SUPPORTED_BY" not in {edge.type for edge in graph.edges}
    assert "CONSISTENT_WITH" in {edge.type for edge in graph.edges}
