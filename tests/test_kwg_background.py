import json
from pathlib import Path
import sqlite3

import pytest

import mazu_saudi.knowledge_graph.external_background as background
from mazu_saudi.knowledge_graph.external_background import (
    KWGBackgroundStore,
    query_kwg,
    run_kwg_enrichment,
    snapshot_from_sparql_results,
    validate_kwg_snapshot,
)


ROOT = Path(__file__).parents[1]
QUERY_MANIFEST = ROOT / "ontology/kwg_background_queries.json"
KWG_RESOURCE = "http://stko-kwg.geog.ucsb.edu/lod/resource/"
KWG_ONTOLOGY = "http://stko-kwg.geog.ucsb.edu/lod/ontology/"


def valid_snapshot():
    region = f"{KWG_RESOURCE}administrativeRegion.SAU"
    event = f"{KWG_RESOURCE}historicalEvent.example-saudi-flood"
    return {
        "provider": "KnowWhereGraph",
        "endpoint": "https://stko-kwg.geog.ucsb.edu/sparql",
        "retrieved_at": "2026-07-31T00:00:00+00:00",
        "scope": {
            "country_iso3": "SAU",
            "start_time": "2000-01-01T00:00:00+00:00",
            "end_time": "2025-12-31T23:59:59+00:00",
        },
        "entities": [
            {
                "entity_iri": region,
                "entity_kind": "region",
                "external_type_iri": f"{KWG_ONTOLOGY}AdministrativeRegion_0",
                "label": "Saudi Arabia",
                "geometry_wkt": "POLYGON EMPTY",
                "properties": {"gadm_gid": "SAU"},
            },
            {
                "entity_iri": event,
                "entity_kind": "historical_event",
                "external_type_iri": f"{KWG_ONTOLOGY}FloodEvent",
                "label": "Example sourced historical event",
                "start_time": "2020-11-24T00:00:00+00:00",
                "source_dataset_iri": "https://example.org/source/catalogue",
                "properties": {"review_status": "external-background-only"},
            },
        ],
        "relations": [
            {
                "source_iri": event,
                "predicate_iri": "http://www.w3.org/ns/sosa/hasFeatureOfInterest",
                "target_iri": region,
                "properties": {"role": "historical-background-location"},
            }
        ],
    }


def binding(value, binding_type="uri"):
    return {"type": binding_type, "value": value}


def test_imports_a_provenanced_kwg_snapshot_into_separate_tables(tmp_path):
    database = tmp_path / "graph.sqlite3"
    store = KWGBackgroundStore(database)

    result = store.import_snapshot(valid_snapshot(), query_manifest_sha256="a" * 64)

    assert result.status == "successful"
    assert result.entity_count == 2
    assert result.relation_count == 1
    assert len(result.source_snapshot_sha256) == 64
    view = store.background_view()
    assert {item["entity_kind"] for item in view["entities"]} == {
        "region",
        "historical_event",
    }
    assert view["relations"][0]["properties"]["role"] == (
        "historical-background-location"
    )
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert {
        "kg_external_background_runs",
        "kg_external_background_entities",
        "kg_external_background_relations",
    } <= tables

    store.record_source_unavailable(
        endpoint="https://stko-kwg.geog.ucsb.edu/sparql",
        scope={"country_iso3": "SAU"},
        error="temporary outage",
        retrieved_at="2026-08-01T00:00:00+00:00",
    )
    assert store.latest_run()["status"] == "source_unavailable"
    assert store.latest_available_run()["run_id"] == result.run_id
    assert store.background_view()["run"]["run_id"] == result.run_id


def test_rejects_unsourced_history_and_out_of_scope_regions():
    snapshot = valid_snapshot()
    snapshot["entities"][1].pop("source_dataset_iri")
    with pytest.raises(ValueError, match="lacks source_dataset_iri"):
        validate_kwg_snapshot(snapshot)

    snapshot = valid_snapshot()
    snapshot["entities"][0]["properties"]["gadm_gid"] = "USA"
    with pytest.raises(ValueError, match="outside requested country"):
        validate_kwg_snapshot(snapshot)


def test_normalizes_bounded_sparql_results_without_inventing_missing_rows():
    region = f"{KWG_RESOURCE}administrativeRegion.SAU"
    event = f"{KWG_RESOURCE}historicalEvent.example"
    geography = {
        "results": {
            "bindings": [
                {
                    "entity": binding(region),
                    "type": binding(f"{KWG_ONTOLOGY}AdministrativeRegion_0"),
                    "label": binding("Saudi Arabia", "literal"),
                    "gid": binding("SAU", "literal"),
                }
            ]
        }
    }
    history = {
        "results": {
            "bindings": [
                {
                    "entity": binding(event),
                    "type": binding(f"{KWG_ONTOLOGY}FloodEvent"),
                    "label": binding("Historical flood", "literal"),
                    "start": binding("2020-11-24T00:00:00+00:00", "literal"),
                    "dataset": binding("https://example.org/source/catalogue"),
                    "region": binding(region),
                },
                {
                    "entity": binding(f"{KWG_RESOURCE}incomplete"),
                    "type": binding(f"{KWG_ONTOLOGY}FloodEvent"),
                },
            ]
        }
    }

    snapshot = snapshot_from_sparql_results(
        endpoint="https://stko-kwg.geog.ucsb.edu/sparql",
        scope={"country_iso3": "SAU"},
        retrieved_at="2026-07-31T00:00:00+00:00",
        geography=geography,
        history=history,
    )

    validate_kwg_snapshot(snapshot)
    assert len(snapshot["entities"]) == 2
    assert len(snapshot["relations"]) == 1


def test_live_outage_is_recorded_without_background_entities(tmp_path, monkeypatch):
    database = tmp_path / "graph.sqlite3"

    def unavailable(*args, **kwargs):
        raise RuntimeError("KWG HTTP 500: license key expired")

    monkeypatch.setattr(background, "query_kwg", unavailable)
    result = run_kwg_enrichment(
        database_file=database,
        query_manifest_file=QUERY_MANIFEST,
    )

    assert result.status == "source_unavailable"
    assert result.entity_count == 0
    assert "license key expired" in result.error
    store = KWGBackgroundStore(database)
    assert store.latest_run()["status"] == "source_unavailable"
    assert store.latest_available_run() is None
    assert store.background_view()["run"] is None


def test_query_manifest_has_bounded_geography_and_history_queries():
    manifest = json.loads(QUERY_MANIFEST.read_text(encoding="utf-8"))
    queries = {item["role"]: item["sparql"] for item in manifest["queries"]}

    assert set(queries) == {"geography", "history"}
    assert manifest["country_iso3"] == "SAU"
    for query in queries.values():
        assert 'STRSTARTS(STR(?gid), "SAU")' in query
        assert "LIMIT 500" in query
    assert "prov:wasDerivedFrom ?dataset" in queries["history"]


def test_kwg_client_rejects_non_select_queries_before_network_access():
    with pytest.raises(ValueError, match="only permits SPARQL SELECT"):
        query_kwg(
            "https://stko-kwg.geog.ucsb.edu/sparql",
            "DELETE WHERE { ?s ?p ?o }",
        )
