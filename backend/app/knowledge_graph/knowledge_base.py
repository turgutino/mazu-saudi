"""Versioned domain knowledge and analog-case catalog.

The runtime catalog is intentionally a small application profile.  SWEET and
literature files remain source registries; they are linked, not imported into
the per-prediction graph wholesale.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


_ROOT = Path(__file__).resolve().parents[3]
_CATALOG_PATH = _ROOT / "backend" / "data" / "knowledge" / "prediction_knowledge.json"
_SWEET_PATH = _ROOT / "ontology" / "sweet_alignment.json"
_LITERATURE_PATH = _ROOT / "ontology" / "literature_sources.json"
_ONTOLOGY_PATH = _ROOT / "ontology" / "mazu_weather_ontology.jsonld"


class KnowledgeBaseError(ValueError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_knowledge_base() -> dict[str, Any]:
    catalog = _read_json(_CATALOG_PATH)
    sweet = _read_json(_SWEET_PATH)
    literature = _read_json(_LITERATURE_PATH)
    ontology = _read_json(_ONTOLOGY_PATH)

    mechanism_ids = [item["id"] for item in catalog.get("mechanisms", [])]
    case_ids = [item["id"] for item in catalog.get("cases", [])]
    if len(mechanism_ids) != len(set(mechanism_ids)):
        raise KnowledgeBaseError("Duplicate mechanism ids")
    if len(case_ids) != len(set(case_ids)):
        raise KnowledgeBaseError("Duplicate case ids")

    source_ids = {item["source_id"] for item in literature.get("sources", [])}
    for mechanism in catalog.get("mechanisms", []):
        missing = set(mechanism.get("evidenceIds", [])) - source_ids
        if missing:
            raise KnowledgeBaseError(f"Unknown evidence ids for {mechanism['id']}: {sorted(missing)}")

    catalog["literatureById"] = {
        item["source_id"]: item for item in literature.get("sources", [])
    }
    catalog["sweetMappings"] = sweet.get("mappings", [])
    catalog["sweetSource"] = sweet.get("source", {})
    concept_prefix = ontology.get("@context", {}).get("concept", "urn:mazu-saudi:concept:")
    ontology_resources = ontology.get("@graph", [])
    catalog["ontology"] = {
        "id": ontology["@id"],
        "version": ontology["versionInfo"],
        "resourcesById": {
            item["@id"].replace("concept:", concept_prefix): item
            for item in ontology_resources
            if isinstance(item, dict) and isinstance(item.get("@id"), str)
        },
    }
    return catalog


def mechanisms_for(hazard: str, region_id: str) -> list[dict[str, Any]]:
    catalog = load_knowledge_base()
    return [
        item
        for item in catalog["mechanisms"]
        if hazard in item["hazards"]
        and (not item.get("regions") or region_id in item["regions"])
    ]


def cases_for(hazard: str) -> list[dict[str, Any]]:
    return [item for item in load_knowledge_base()["cases"] if hazard in item["hazards"]]


def literature(evidence_id: str) -> dict[str, Any]:
    return load_knowledge_base()["literatureById"][evidence_id]


def sweet_mapping(local_suffix: str) -> dict[str, Any] | None:
    suffix = f":{local_suffix}"
    return next(
        (item for item in load_knowledge_base()["sweetMappings"] if item["local_iri"].endswith(suffix)),
        None,
    )


def ontology_metadata() -> dict[str, Any]:
    return load_knowledge_base()["ontology"]


def ontology_resource(concept_suffix: str) -> dict[str, Any] | None:
    iri = f"urn:mazu-saudi:concept:{concept_suffix}"
    resource = ontology_metadata()["resourcesById"].get(iri)
    if resource is None:
        return None
    return {**resource, "iri": iri}
