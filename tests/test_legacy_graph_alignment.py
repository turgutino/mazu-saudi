from __future__ import annotations

import json
from pathlib import Path

from mazu_saudi.knowledge_graph.legacy_graph import (
    CANONICAL_MECHANISM_IRIS,
    migrate_legacy_evidence_graph,
    validate_legacy_graph_alignment,
)


ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "research" / "historical_warning" / "kg" / "kg_data.json"
ONTOLOGY = ROOT / "ontology" / "mazu_weather_ontology.jsonld"


def test_historical_graph_uses_canonical_mechanisms_and_noncausal_edges():
    summary = validate_legacy_graph_alignment(GRAPH, ONTOLOGY)

    assert summary["mechanism_count"] == 5
    assert summary["aligned_node_count"] >= 16
    assert summary["unmapped_node_count"] > 0


def test_legacy_migration_is_idempotent_and_preserves_unmapped_concepts():
    payload = {
        "graph": {},
        "nodes": [
            {"id": "ARST", "ntype": "Mechanism"},
            {"id": "coastal", "ntype": "Hazard"},
        ],
        "links": [
            {
                "source": "coastal",
                "target": "ARST",
                "eligible_for_causal_explanation": True,
            }
        ],
    }

    first = migrate_legacy_evidence_graph(payload)
    second = migrate_legacy_evidence_graph(first)

    assert second == first
    assert first["nodes"][0]["id"] == CANONICAL_MECHANISM_IRIS["ARST"]
    assert first["nodes"][1]["migration_status"] == "unmapped_legacy_concept"
    assert first["links"][0]["eligible_for_causal_explanation"] is False
    assert first["graph"]["semantic_status"] == "legacy_compatibility_view"


def test_bundled_graph_matches_aligned_source_bytes():
    bundled = ROOT / "competition_app" / "src" / "data" / "kg_data.json"
    assert bundled.read_bytes() == GRAPH.read_bytes()
