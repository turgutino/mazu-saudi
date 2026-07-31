from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from mazu_saudi.ontology import validate_ontology_semantics
from mazu_saudi.ontology.semantics import validate_graph_semantics


ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "ontology" / "mazu_weather_ontology.jsonld"


def load_ontology():
    return json.loads(ONTOLOGY.read_text(encoding="utf-8"))


def test_ontology_v2_semantic_gate_accepts_the_curated_profile():
    summary = validate_ontology_semantics(load_ontology())

    assert summary.version == "2.0.0"
    assert summary.resource_count == 94
    assert summary.threshold_state_count == 8
    assert summary.hazard_screening_state_count == 3
    assert summary.cf_property_count == 4


def test_ontology_gate_rejects_extreme_state_without_indicator_lineage():
    payload = deepcopy(load_ontology())
    rainfall = next(
        node
        for node in payload["@graph"]
        if node["@id"] == "concept:ExtremeRainfallState"
    )
    rainfall.pop("derivedFromIndicator")

    with pytest.raises(ValueError, match="lacks indicator or threshold"):
        validate_ontology_semantics(payload)


def test_graph_gate_rejects_causally_eligible_assertion():
    node_id = "urn:test:assertion"
    nodes = [
        {
            "node_id": node_id,
            "ontology_class_iri": (
                "urn:mazu-saudi:ontology:LaggedAssociationAssertion"
            ),
            "properties": {
                "evidence_class": "observational-statistical",
                "eligible_for_causal_explanation": True,
            },
        }
    ]
    edges = [
        {
            "source_id": node_id,
            "predicate_iri": predicate,
            "target_id": f"urn:test:{index}",
        }
        for index, predicate in enumerate(
            (
                "urn:mazu-saudi:ontology:sourceState",
                "urn:mazu-saudi:ontology:targetState",
                "urn:mazu-saudi:ontology:applicableUnder",
                "http://www.w3.org/ns/prov#wasGeneratedBy",
            )
        )
    ]

    with pytest.raises(ValueError, match="causally eligible"):
        validate_graph_semantics(nodes, edges, [])
