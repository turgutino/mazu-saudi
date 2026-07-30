"""Read-only explanation packages across audited knowledge-graph layers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


EXPLANATION_CONTRACT_VERSION = "graph-grounded-explanation-v1"
ABLATION_CONTRACT_VERSION = "graph-explanation-ablation-v1"

HAZARD_TARGET_STATES = {
    "flash_flood": "urn:mazu-saudi:concept:ExtremeRainfallState",
    "heatwave": "urn:mazu-saudi:concept:ExtremeHeatState",
    "dust_storm": "urn:mazu-saudi:concept:DustStormFavourableState",
}

AUDIT_FIELDS = (
    "evidence_class",
    "construction_method",
    "source_ref",
    "confidence",
    "review_status",
    "eligible_for_causal_explanation",
)


class GraphViewStore(Protocol):
    def graph_view(
        self, build_id: str | None = None, *, limit: int = 500
    ) -> dict[str, Any]: ...


def _audit(edge: dict[str, Any]) -> dict[str, Any]:
    return {field: edge.get(field) for field in AUDIT_FIELDS}


class HazardExplanationQuery:
    """Compose evidence without erasing the identity of its source layers."""

    def __init__(self, evidence_graph_file: str | Path, store: GraphViewStore):
        self.evidence_graph_file = Path(evidence_graph_file)
        self.store = store

    def _evidence_graph(self) -> dict[str, Any]:
        if not self.evidence_graph_file.is_file():
            raise RuntimeError(
                f"Audited evidence graph is unavailable: {self.evidence_graph_file}"
            )
        try:
            payload = json.loads(
                self.evidence_graph_file.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("Audited evidence graph cannot be read") from exc
        if not isinstance(payload.get("nodes"), list) or not isinstance(
            payload.get("links"), list
        ):
            raise RuntimeError("Audited evidence graph has an invalid structure")
        return payload

    @staticmethod
    def _prediction_candidates(
        hazard: str, view: dict[str, Any]
    ) -> list[dict[str, Any]]:
        target_state = HAZARD_TARGET_STATES[hazard]
        nodes = {node["node_id"]: node for node in view.get("nodes", [])}
        endpoints: dict[str, dict[str, str]] = {}
        for edge in view.get("edges", []):
            predicate = edge.get("predicate_iri", "")
            if predicate.endswith("sourceState"):
                endpoints.setdefault(edge["source_id"], {})["source"] = edge[
                    "target_id"
                ]
            elif predicate.endswith("targetState"):
                endpoints.setdefault(edge["source_id"], {})["target"] = edge[
                    "target_id"
                ]

        candidates = []
        for assertion_id, endpoint in endpoints.items():
            assertion = nodes.get(assertion_id)
            if (
                assertion is None
                or endpoint.get("target") != target_state
                or not assertion.get("properties", {}).get(
                    "eligible_for_prediction_experiment"
                )
            ):
                continue
            source = nodes.get(endpoint.get("source", ""), {})
            target = nodes.get(endpoint["target"], {})
            properties = assertion.get("properties", {})
            candidates.append(
                {
                    "assertion_id": assertion_id,
                    "label": assertion.get("label", assertion_id),
                    "source_state": {
                        "id": endpoint.get("source"),
                        "label": source.get("label"),
                    },
                    "target_state": {
                        "id": endpoint["target"],
                        "label": target.get("label"),
                    },
                    "support_episode_count": properties.get(
                        "support_episode_count"
                    ),
                    "counterexample_episode_count": properties.get(
                        "counterexample_episode_count"
                    ),
                    "lift": properties.get("lift"),
                    "validation_stage": properties.get("validation_stage"),
                    "eligible_for_prediction_experiment": True,
                    "eligible_for_production_prediction": bool(
                        properties.get("eligible_for_production_prediction")
                    ),
                    "eligible_for_causal_explanation": bool(
                        properties.get("eligible_for_causal_explanation")
                    ),
                }
            )
        return sorted(candidates, key=lambda item: item["assertion_id"])

    def explain(self, hazard: str) -> dict[str, Any]:
        if hazard not in HAZARD_TARGET_STATES:
            raise ValueError(
                f"Unknown hazard '{hazard}'. Known: {sorted(HAZARD_TARGET_STATES)}"
            )

        graph = self._evidence_graph()
        nodes = {node["id"]: node for node in graph["nodes"]}
        hazard_node = nodes.get(hazard)
        if hazard_node is None or hazard_node.get("ntype") != "Hazard":
            raise RuntimeError(
                f"Audited evidence graph does not define hazard '{hazard}'"
            )

        indicator_edges = sorted(
            (
                edge
                for edge in graph["links"]
                if edge.get("etype") == "contributes_to"
                and edge.get("target") == hazard
            ),
            key=lambda edge: edge["source"],
        )
        mechanism_edges = sorted(
            (
                edge
                for edge in graph["links"]
                if edge.get("etype") == "driven_by"
                and edge.get("source") == hazard
            ),
            key=lambda edge: edge["target"],
        )
        grounded_edges: dict[str, list[dict[str, Any]]] = {}
        for edge in graph["links"]:
            if edge.get("etype") == "grounded_by":
                grounded_edges.setdefault(edge["source"], []).append(edge)

        indicators = [
            {
                "id": edge["source"],
                "label": nodes.get(edge["source"], {}).get(
                    "label", edge["source"]
                ),
                "description": nodes.get(edge["source"], {}).get("desc"),
                "relation_audit": _audit(edge),
            }
            for edge in indicator_edges
        ]
        mechanisms = []
        evidence_gaps = []
        for edge in mechanism_edges:
            mechanism_id = edge["target"]
            mechanism_node = nodes.get(mechanism_id, {})
            grounding = grounded_edges.get(mechanism_id, [])
            citations = []
            for grounding_edge in grounding:
                citation_node = nodes.get(grounding_edge["target"], {})
                citations.append(
                    {
                        "id": citation_node.get("id"),
                        "citation": citation_node.get("label"),
                        "title": citation_node.get("desc"),
                        "url": citation_node.get("url"),
                        "evidence": citation_node.get("evidence", []),
                        "source_text_kind": citation_node.get(
                            "source_text_kind"
                        ),
                        "verification_scope": citation_node.get(
                            "verification_scope"
                        ),
                        "review_status": citation_node.get("review_status"),
                        "relation_audit": _audit(grounding_edge),
                    }
                )
                if (
                    citation_node.get("verification_scope")
                    == "substring_matched_in_curated_passage_not_original_publication"
                ):
                    evidence_gaps.append(
                        {
                            "code": "original_publication_wording_not_verified",
                            "subject_id": citation_node.get("id"),
                            "message": (
                                "Citation wording was checked against a curated "
                                "local passage, not the original publication."
                            ),
                            "required_action": (
                                "Verify the quoted wording and locator in the "
                                "original publication before expert use."
                            ),
                        }
                    )
            if not grounding:
                evidence_gaps.append(
                    {
                        "code": "mechanism_without_literature_support",
                        "subject_id": mechanism_id,
                        "message": (
                            "The mechanism is a hand-authored domain assertion "
                            "without a linked literature record."
                        ),
                        "required_action": (
                            "Add an original-publication evidence record and "
                            "expert review; do not infer a citation."
                        ),
                    }
                )
            mechanisms.append(
                {
                    "id": mechanism_id,
                    "label": mechanism_node.get("label", mechanism_id),
                    "description": mechanism_node.get("desc"),
                    "relation_audit": _audit(edge),
                    "literature_support_available": bool(citations),
                    "citations": citations,
                }
            )

        graph_view = self.store.graph_view(limit=2000)
        candidates = self._prediction_candidates(hazard, graph_view)
        if graph_view.get("build") is None:
            feature_status = "global_graph_unavailable"
            evidence_gaps.append(
                {
                    "code": "global_observational_graph_unavailable",
                    "subject_id": HAZARD_TARGET_STATES[hazard],
                    "message": (
                        "No global observational graph build is available for "
                        "feature-candidate retrieval."
                    ),
                    "required_action": (
                        "Build the Saudi-held-out global graph before running "
                        "offline feature-selection experiments."
                    ),
                }
            )
        elif candidates:
            feature_status = "candidates_for_saudi_evaluation"
        else:
            feature_status = "no_eligible_candidate"

        return {
            "contract_version": EXPLANATION_CONTRACT_VERSION,
            "hazard": {
                "id": hazard,
                "label": hazard_node.get("label", hazard),
                "target_state_iri": HAZARD_TARGET_STATES[hazard],
            },
            "source_graph": {
                "name": graph.get("graph", {}).get("name"),
                "schema_version": graph.get("graph", {}).get("schema_version"),
                "purpose": graph.get("graph", {}).get("purpose"),
            },
            "indicators": indicators,
            "mechanisms": mechanisms,
            "evidence_gaps": evidence_gaps,
            "feature_selection": {
                "status": feature_status,
                "global_build_id": (
                    graph_view.get("build") or {}
                ).get("build_id"),
                "offline_candidates": candidates,
                "production_features": [],
                "boundary": (
                    "Candidates may enter a frozen Saudi offline experiment "
                    "only. The graph does not alter the production model."
                ),
            },
            "eligible_for_causal_explanation": False,
            "boundaries": [
                graph.get("graph", {}).get("causal_claim_boundary"),
                (
                    "Mechanism evidence, observational associations, and "
                    "prediction candidates retain separate provenance and use."
                ),
                (
                    "Missing evidence is returned explicitly and must not be "
                    "filled from model background knowledge."
                ),
            ],
        }

    def ablation(self) -> dict[str, Any]:
        cases = []
        mechanism_count = 0
        grounded_mechanism_count = 0
        citation_count = 0
        evidence_gap_count = 0
        for hazard in HAZARD_TARGET_STATES:
            explanation = self.explain(hazard)
            mechanisms = explanation["mechanisms"]
            citations = [
                citation
                for mechanism in mechanisms
                for citation in mechanism["citations"]
            ]
            grounded = sum(
                1
                for mechanism in mechanisms
                if mechanism["literature_support_available"]
            )
            gaps = explanation["evidence_gaps"]
            mechanism_count += len(mechanisms)
            grounded_mechanism_count += grounded
            citation_count += len(citations)
            evidence_gap_count += len(gaps)
            cases.append(
                {
                    "hazard": hazard,
                    "with_graph": {
                        "mechanism_count": len(mechanisms),
                        "grounded_mechanism_count": grounded,
                        "citation_count": len(citations),
                        "evidence_gap_count": len(gaps),
                    },
                    "without_graph": {
                        "mechanism_count": 0,
                        "citation_count": 0,
                        "response_policy": (
                            "state_that_no_graph_grounded_explanation_is_available"
                        ),
                    },
                }
            )
        return {
            "contract_version": ABLATION_CONTRACT_VERSION,
            "scope": "explanation_coverage_only",
            "forecast_model_changed": False,
            "prediction_skill_evaluated": False,
            "hallucination_rate_evaluated": False,
            "with_graph": {
                "mechanism_count": mechanism_count,
                "grounded_mechanism_count": grounded_mechanism_count,
                "citation_count": citation_count,
                "evidence_gap_count": evidence_gap_count,
            },
            "without_graph": {
                "mechanism_count": 0,
                "citation_count": 0,
                "evidence_gap_count": 0,
                "response_policy": (
                    "state_that_no_graph_grounded_explanation_is_available"
                ),
            },
            "cases": cases,
            "boundary": (
                "This deterministic ablation measures explanation availability "
                "only. It does not establish forecast-skill improvement, causal "
                "correctness, or a hallucination rate."
            ),
        }
