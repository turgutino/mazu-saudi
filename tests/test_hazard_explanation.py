from __future__ import annotations

from pathlib import Path

from mazu_saudi.knowledge_graph.explanation import HazardExplanationQuery


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_GRAPH = ROOT / "research" / "historical_warning" / "kg" / "kg_data.json"


class EmptyGraphStore:
    def graph_view(self, build_id=None, *, limit=500):
        return {
            "build": None,
            "nodes": [],
            "edges": [],
            "node_count": 0,
            "edge_count": 0,
        }


class CandidateGraphStore:
    def graph_view(self, build_id=None, *, limit=500):
        assertion = "urn:test:assertion:ivt-rain"
        source = "urn:mazu-saudi:concept:HighIVTState"
        target = "urn:mazu-saudi:concept:ExtremeRainfallState"
        return {
            "build": {"build_id": "kg-test"},
            "nodes": [
                {
                    "node_id": assertion,
                    "ontology_class_iri": (
                        "urn:mazu-saudi:ontology:LaggedAssociationAssertion"
                    ),
                    "label": "高水汽输送状态 → 极端降水状态",
                    "properties": {
                        "validation_stage": "candidate_for_saudi_evaluation",
                        "eligible_for_prediction_experiment": True,
                        "eligible_for_production_prediction": False,
                        "eligible_for_causal_explanation": False,
                        "support_episode_count": 12,
                        "counterexample_episode_count": 3,
                        "lift": 2.4,
                    },
                },
                {
                    "node_id": source,
                    "ontology_class_iri": (
                        "urn:mazu-saudi:ontology:IndicatorState"
                    ),
                    "label": "高水汽输送状态",
                    "properties": {},
                },
                {
                    "node_id": target,
                    "ontology_class_iri": (
                        "urn:mazu-saudi:ontology:ExtremeWeatherState"
                    ),
                    "label": "极端降水状态",
                    "properties": {},
                },
            ],
            "edges": [
                {
                    "source_id": assertion,
                    "predicate_iri": "urn:mazu-saudi:ontology:sourceState",
                    "target_id": source,
                    "properties": {},
                },
                {
                    "source_id": assertion,
                    "predicate_iri": "urn:mazu-saudi:ontology:targetState",
                    "target_id": target,
                    "properties": {},
                },
            ],
            "node_count": 3,
            "edge_count": 2,
        }


def test_explanation_package_preserves_evidence_gaps_and_layer_boundaries():
    query = HazardExplanationQuery(EVIDENCE_GRAPH, EmptyGraphStore())

    result = query.explain("flash_flood")

    assert result["contract_version"] == "graph-grounded-explanation-v1"
    assert result["hazard"]["id"] == "flash_flood"
    assert result["mechanisms"]
    assert result["indicators"]
    assert any(
        gap["code"] == "mechanism_without_literature_support"
        and gap["subject_id"] == "orographic_lift"
        for gap in result["evidence_gaps"]
    )
    assert any(
        gap["code"] == "original_publication_wording_not_verified"
        for gap in result["evidence_gaps"]
    )
    assert result["feature_selection"]["status"] == "global_graph_unavailable"
    assert result["feature_selection"]["production_features"] == []
    assert result["eligible_for_causal_explanation"] is False


def test_explanation_package_exposes_only_offline_prediction_candidates():
    query = HazardExplanationQuery(EVIDENCE_GRAPH, CandidateGraphStore())

    result = query.explain("flash_flood")

    candidates = result["feature_selection"]["offline_candidates"]
    assert result["feature_selection"]["status"] == "candidates_for_saudi_evaluation"
    assert len(candidates) == 1
    assert candidates[0]["source_state"]["id"].endswith("HighIVTState")
    assert candidates[0]["target_state"]["id"].endswith("ExtremeRainfallState")
    assert candidates[0]["eligible_for_prediction_experiment"] is True
    assert candidates[0]["eligible_for_production_prediction"] is False
    assert candidates[0]["eligible_for_causal_explanation"] is False
    assert result["feature_selection"]["production_features"] == []


def test_explanation_ablation_measures_coverage_not_model_skill_or_hallucination():
    query = HazardExplanationQuery(EVIDENCE_GRAPH, EmptyGraphStore())

    result = query.ablation()

    assert result["contract_version"] == "graph-explanation-ablation-v1"
    assert result["scope"] == "explanation_coverage_only"
    assert result["forecast_model_changed"] is False
    assert result["prediction_skill_evaluated"] is False
    assert result["hallucination_rate_evaluated"] is False
    assert result["with_graph"]["grounded_mechanism_count"] > 0
    assert result["without_graph"] == {
        "mechanism_count": 0,
        "citation_count": 0,
        "evidence_gap_count": 0,
        "response_policy": "state_that_no_graph_grounded_explanation_is_available",
    }
    assert len(result["cases"]) == 3
