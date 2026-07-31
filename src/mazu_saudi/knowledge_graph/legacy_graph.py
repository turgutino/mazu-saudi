"""Migration and validation for the historical hand-authored graph view."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any


CONCEPT = "urn:mazu-saudi:concept:"
ONTOLOGY = "urn:mazu-saudi:ontology:"

CANONICAL_MECHANISM_IRIS = {
    "ARST": f"{CONCEPT}ActiveRedSeaTrough",
    "moisture_transport": f"{CONCEPT}MoistureAdvection",
    "subtropical_high": f"{CONCEPT}SubtropicalHighInfluence",
    "thermal_low": f"{CONCEPT}ArabianThermalLow",
    "orographic_lift": f"{CONCEPT}OrographicLift",
    "orographic_lifting": f"{CONCEPT}OrographicLift",
}

HAZARD_SCREENING_IRIS = {
    "flash_flood": f"{CONCEPT}FlashFloodFavourableState",
    "heatwave": f"{CONCEPT}HeatwaveFavourableState",
    "dust_storm": f"{CONCEPT}DustStormFavourableState",
}

INDICATOR_IRIS = {
    "daily_precip_total": f"{CONCEPT}DailyPrecipitation",
    "tmax_c": f"{CONCEPT}MaximumAirTemperature",
    "vpd_kpa": f"{CONCEPT}VaporPressureDeficit",
    "cape": f"{CONCEPT}CAPE",
    "pwat": f"{CONCEPT}PrecipitableWater",
    "ivt": f"{CONCEPT}IntegratedVaporTransport",
    "sst_celsius": f"{CONCEPT}SeaSurfaceTemperature",
    "wind10_speed": f"{CONCEPT}TenMetreWindSpeed",
}


def migrate_legacy_evidence_graph(payload: dict[str, Any]) -> dict[str, Any]:
    """Return an idempotently aligned compatibility view of a legacy graph."""

    migrated = deepcopy(payload)
    graph_meta = migrated.setdefault("graph", {})
    graph_meta.update(
        {
            "schema_version": "3.0",
            "ontology_profile": "urn:mazu-saudi:ontology",
            "ontology_version": "2.0.0",
            "semantic_status": "legacy_compatibility_view",
            "semantic_boundary": (
                "Direct legacy edges are retained for display and provenance. "
                "They are not OWL object-property assertions or causal facts."
            ),
        }
    )

    identifier_map = dict(CANONICAL_MECHANISM_IRIS)
    for node in migrated.get("nodes", []):
        original_id = node["id"]
        node_type = node.get("ntype")
        if node_type == "Mechanism":
            canonical = CANONICAL_MECHANISM_IRIS.get(original_id, original_id)
            node["id"] = canonical
            node["ontology_iri"] = canonical
            if original_id != canonical:
                node["legacy_id"] = original_id
            node["migration_status"] = "aligned"
        elif node_type == "Hazard":
            ontology_iri = HAZARD_SCREENING_IRIS.get(original_id)
            node["migration_status"] = (
                "aligned" if ontology_iri else "unmapped_legacy_concept"
            )
            if ontology_iri:
                node["ontology_iri"] = ontology_iri
        elif node_type == "Indicator":
            ontology_iri = INDICATOR_IRIS.get(original_id)
            node["migration_status"] = (
                "aligned" if ontology_iri else "unmapped_legacy_concept"
            )
            if ontology_iri:
                node["ontology_iri"] = ontology_iri
        elif node_type == "Citation":
            node["migration_status"] = (
                "curated_passage_not_original_publication_evidence"
            )

    for edge in migrated.get("links", []):
        edge["source"] = identifier_map.get(edge["source"], edge["source"])
        edge["target"] = identifier_map.get(edge["target"], edge["target"])
        edge["eligible_for_causal_explanation"] = False
        edge["semantic_status"] = "legacy_compatibility_relation"

    return migrated


def validate_legacy_graph_alignment(
    graph_file: Path,
    ontology_file: Path,
) -> dict[str, int]:
    """Validate canonical concept bindings and the non-causal compatibility boundary."""

    graph = json.loads(Path(graph_file).read_text(encoding="utf-8"))
    ontology = json.loads(Path(ontology_file).read_text(encoding="utf-8"))
    context = ontology["@context"]

    def expand(value: str) -> str:
        if ":" not in value:
            return value
        prefix, local = value.split(":", 1)
        namespace = context.get(prefix)
        return f"{namespace}{local}" if isinstance(namespace, str) else value

    resources = {
        expand(node["@id"]): expand(node["@type"])
        for node in ontology["@graph"]
    }
    mechanism_count = 0
    aligned_count = 0
    unmapped_count = 0
    for node in graph.get("nodes", []):
        ontology_iri = node.get("ontology_iri")
        if node.get("ntype") == "Mechanism":
            mechanism_count += 1
            if not ontology_iri or resources.get(ontology_iri) != (
                f"{ONTOLOGY}WeatherMechanism"
            ):
                raise ValueError(
                    f"Legacy mechanism lacks a canonical WeatherMechanism: {node['id']}"
                )
        if ontology_iri:
            aligned_count += 1
            if ontology_iri not in resources:
                raise ValueError(f"Legacy graph references unknown ontology IRI: {ontology_iri}")
        elif node.get("migration_status") == "unmapped_legacy_concept":
            unmapped_count += 1

    unsafe = [
        edge
        for edge in graph.get("links", [])
        if edge.get("eligible_for_causal_explanation") is not False
    ]
    if unsafe:
        raise ValueError(f"Legacy graph contains {len(unsafe)} causally eligible edges")
    if graph.get("graph", {}).get("semantic_status") != "legacy_compatibility_view":
        raise ValueError("Legacy graph is not labelled as a compatibility view")

    return {
        "mechanism_count": mechanism_count,
        "aligned_node_count": aligned_count,
        "unmapped_node_count": unmapped_count,
        "edge_count": len(graph.get("links", [])),
    }
