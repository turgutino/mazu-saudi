import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KG_DIR = ROOT / "warning_demo" / "kg"
KG_PATH = KG_DIR / "kg_data.json"
ASSOCIATIONS_PATH = KG_DIR / "kg_observational_associations.json"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_evidence_graph_has_explicit_claim_boundary_and_audited_edges():
    graph = load_json(KG_PATH)

    assert graph["graph"]["name"] == "MAZU Hazard Mechanism & Evidence Graph"
    assert "does not discover causality" in graph["graph"]["causal_claim_boundary"]
    assert all(node.get("ntype") != "Event" for node in graph["nodes"])
    assert all(edge.get("etype") != "correlates_with" for edge in graph["links"])

    required = {
        "evidence_class",
        "construction_method",
        "source_ref",
        "confidence",
        "review_status",
        "eligible_for_causal_explanation",
    }
    for edge in graph["links"]:
        assert required <= edge.keys(), edge


def test_extrema_are_samples_not_verified_disaster_events():
    graph = load_json(KG_PATH)
    samples = [
        node for node in graph["nodes"] if node.get("ntype") == "ExtremeSample"
    ]

    assert len(samples) == 6
    assert all(
        node["verification_status"]
        == "dataset_derived_not_independently_verified_event"
        for node in samples
    )
    assert any(node["hazard"] == "dust_storm" for node in samples)


def test_observational_associations_are_isolated_and_noncausal():
    associations = load_json(ASSOCIATIONS_PATH)

    assert associations["included_in_evidence_graph"] is False
    assert associations["eligible_for_causal_explanation"] is False
    assert any(
        "does not establish direction or causality" in item
        for item in associations["limitations"]
    )
    assert len(associations["associations"]) == 51
    assert all("pearson_r" in item for item in associations["associations"])


def test_citation_records_disclose_local_paraphrase_verification_scope():
    graph = load_json(KG_PATH)
    citations = [node for node in graph["nodes"] if node.get("ntype") == "Citation"]
    grounded_edges = [
        edge for edge in graph["links"] if edge.get("etype") == "grounded_by"
    ]

    assert len(citations) == 6
    assert len(grounded_edges) == 6
    assert all(
        node["source_text_kind"] == "curated_local_paraphrase"
        and node["verification_scope"]
        == "substring_matched_in_curated_passage_not_original_publication"
        for node in citations
    )
    assert all(
        edge["verification_scope"] == "curated_local_passage_only"
        and edge["review_status"] == "original_publication_wording_not_verified"
        for edge in grounded_edges
    )


def test_showcase_counts_match_generated_graph_and_avoids_causal_uplift_claim():
    graph = load_json(KG_PATH)
    index = (ROOT / "warning_demo" / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "warning_demo" / "README.md").read_text(encoding="utf-8")
    expected = f"{len(graph['nodes'])} nodes / {len(graph['links'])}"

    assert expected in readme
    assert f"{len(graph['nodes'])} / {len(graph['links'])}" in index
    assert "not an automatic causal-discovery system" in index
    assert "not used to train or score the forecast model" in readme
    assert not re.search(r"\b60 nodes, 183 edges\b", index + readme)


def test_bundled_frontend_kg_data_matches_source_graph_bytes():
    bundled_path = ROOT / "competition_app" / "src" / "data" / "kg_data.json"
    assert bundled_path.read_bytes() == KG_PATH.read_bytes()
