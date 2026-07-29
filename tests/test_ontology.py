import json
from pathlib import Path
import sqlite3

import pytest

from mazu_saudi.ontology import OntologyStore, materialize_ontology


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "ontology/mazu_weather_ontology.jsonld"
SHAPES = ROOT / "ontology/mazu_weather_shapes.ttl"
DESIGN = ROOT / "ontology/ontology_design.md"

MAZU = "urn:mazu-saudi:ontology:"
CONCEPT = "urn:mazu-saudi:concept:"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


def load_source():
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def graph_by_id():
    return {node["@id"]: node for node in load_source()["@graph"]}


def test_ontology_declares_standards_version_and_claim_boundary():
    payload = load_source()
    context = payload["@context"]

    assert payload["@type"] == "owl:Ontology"
    assert payload["versionInfo"] == "1.0.0"
    assert "never causal by default" in payload["claimBoundary"]
    assert context["@vocab"] == MAZU
    for prefix in ("sosa", "geo", "time", "prov", "qudt", "uom"):
        assert prefix in context
    assert len(payload["referencesStandard"]) >= 7


def test_resources_have_unique_ids_and_bilingual_definitions():
    graph = load_source()["@graph"]
    identifiers = [node["@id"] for node in graph]

    assert len(identifiers) == len(set(identifiers))
    for node in graph:
        assert node.get("labelEn"), node["@id"]
        assert node.get("labelZh"), node["@id"]
        assert node.get("definitionEn"), node["@id"]
        assert node.get("definitionZh"), node["@id"]


def test_core_domain_boundaries_and_forecast_bridge_are_explicit():
    nodes = graph_by_id()
    for required in (
        "mazu:IndicatorState",
        "mazu:ExtremeWeatherState",
        "mazu:HazardFavourableState",
        "mazu:ObservedHazardEvent",
        "mazu:WeatherEpisode",
        "mazu:LaggedAssociationAssertion",
        "mazu:MechanismApplicabilityAssertion",
        "mazu:CounterexampleAssertion",
        "mazu:GraphDerivedFeature",
        "mazu:ForecastConstraint",
    ):
        assert required in nodes

    serialized = SOURCE.read_text(encoding="utf-8")
    assert '"causes"' not in serialized
    assert "not an observed flash-flood event" in nodes[
        "concept:FlashFloodFavourableState"
    ]["definitionEn"]


def test_seed_indicator_states_link_to_versioned_indicators_and_mechanisms():
    nodes = graph_by_id()

    high_ivt = nodes["concept:HighIVTState"]
    assert high_ivt["derivedFromIndicator"] == "concept:IntegratedVaporTransport"
    assert high_ivt["thresholdDefinition"]

    ivt = nodes["concept:IntegratedVaporTransport"]
    assert ivt["cfStandardName"]
    assert ivt["quantityKind"].startswith("quantitykind:")

    for mechanism in (
        "concept:MoistureAdvection",
        "concept:LocalConvection",
        "concept:OrographicLift",
        "concept:ThermalPersistence",
        "concept:DryWindDustMobilization",
    ):
        assert nodes[mechanism]["@type"] == "mazu:WeatherMechanism"


def test_shacl_shapes_require_scope_provenance_and_causal_flag():
    shapes = SHAPES.read_text(encoding="utf-8")

    for required in (
        "mazu:IndicatorStateShape",
        "mazu:EvidenceAssertionShape",
        "mazu:LaggedAssociationAssertionShape",
        "mazu:ForecastConstraintShape",
        "mazu:applicableUnder",
        "mazu:eligibleForCausalExplanation",
        "prov:wasGeneratedBy",
        "sh:minInclusive 0",
        "sh:maxInclusive 1",
    ):
        assert required in shapes


def test_materializer_builds_queryable_idempotent_database(tmp_path):
    database = tmp_path / "ontology.sqlite3"

    first = materialize_ontology(SOURCE, database)
    second = materialize_ontology(SOURCE, database)

    assert first["ontology"]["version"] == "1.0.0"
    assert first["ontology"]["source_sha256"] == second["ontology"]["source_sha256"]
    assert first["resource_count"] == second["resource_count"] == 68
    assert first["statement_count"] == second["statement_count"]
    assert first["statement_count"] >= 500

    store = OntologyStore(database)
    state = store.get_resource(f"{CONCEPT}HighIVTState")
    assert state["label_zh"] == "高水汽输送状态"
    assert state["resource_type"] == f"{MAZU}IndicatorState"

    statements = store.statements_for(f"{CONCEPT}HighIVTState")
    assert any(
        row["predicate_iri"] == f"{MAZU}derivedFromIndicator"
        and row["object_value"] == f"{CONCEPT}IntegratedVaporTransport"
        and row["object_kind"] == "iri"
        for row in statements
    )
    assert any(
        row["predicate_iri"] == f"{MAZU}thresholdDefinition"
        and row["object_kind"] == "literal"
        for row in statements
    )
    assert len(store.list_resources(module="mechanism")) == 7

    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert {
        "ontology_documents",
        "namespaces",
        "resources",
        "statements",
    } <= tables


def test_materializer_rejects_duplicate_resource_ids(tmp_path):
    payload = load_source()
    payload["@graph"].append(dict(payload["@graph"][0]))
    invalid = tmp_path / "invalid.jsonld"
    invalid.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate ontology resource"):
        materialize_ontology(invalid, tmp_path / "invalid.sqlite3")


def test_design_document_covers_database_extraction_and_saudi_usage():
    design = DESIGN.read_text(encoding="utf-8")

    for required in (
        "SOSA/SSN",
        "OGC OMS 3.0",
        "GeoSPARQL",
        "PROV-O",
        "QUDT",
        "CF Metadata",
        "SQLite",
        "WeatherEpisode",
        "LaggedAssociationAssertion",
        "HGB 图谱特征",
        "MCR 路由软先验",
        "防泄漏",
    ):
        assert required in design
