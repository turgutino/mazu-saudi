"""Validation for curated external concept-alignment manifests."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ALLOWED_RELATIONS = {
    "skos:exactMatch": "alignsWith",
    "skos:closeMatch": "closeMatch",
    "skos:broadMatch": "broadMatch",
    "skos:relatedMatch": "relatedMatch",
}


@dataclass(frozen=True)
class AlignmentSummary:
    alignment_id: str
    source_commit: str
    mapping_count: int
    local_concept_count: int
    unmapped_count: int


def _expanded_ontology_ids(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    prefixes = {
        key: value
        for key, value in payload["@context"].items()
        if isinstance(value, str) and value.endswith(("/", "#", ":"))
    }

    def expand(value: str) -> str:
        if ":" not in value:
            return value
        prefix, local = value.split(":", 1)
        return f"{prefixes[prefix]}{local}" if prefix in prefixes else value

    return {expand(node["@id"]): node for node in payload["@graph"]}


def validate_alignment_manifest(
    manifest_file: Path,
    ontology_file: Path,
    *,
    sweet_root: Path | None = None,
) -> AlignmentSummary:
    """Validate mapping semantics, ontology statements, and optional SWEET files."""

    manifest = json.loads(Path(manifest_file).read_text(encoding="utf-8"))
    ontology = json.loads(Path(ontology_file).read_text(encoding="utf-8"))
    resources = _expanded_ontology_ids(ontology)
    source = manifest.get("source") or {}
    commit = source.get("commit", "")
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise ValueError("SWEET alignment source commit must be a lowercase 40-character SHA")
    if source.get("ontology_iri") != "http://sweetontology.net/sweetAll":
        raise ValueError("SWEET alignment must identify the canonical sweetAll ontology IRI")

    mappings = manifest.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise ValueError("SWEET alignment manifest must contain mappings")
    identities: set[tuple[str, str, str]] = set()
    local_concepts: set[str] = set()
    for mapping in mappings:
        relation = mapping.get("relation")
        if relation not in ALLOWED_RELATIONS:
            raise ValueError(f"Unsupported alignment relation: {relation}")
        local_iri = mapping.get("local_iri", "")
        target_iri = mapping.get("target_iri", "")
        identity = (local_iri, relation, target_iri)
        if identity in identities:
            raise ValueError(f"Duplicate SWEET mapping: {identity}")
        identities.add(identity)
        local_concepts.add(local_iri)
        if local_iri not in resources:
            raise ValueError(f"Alignment references unknown MAZU concept: {local_iri}")
        target = urlparse(target_iri)
        if target.scheme != "http" or target.netloc != "sweetontology.net":
            raise ValueError(f"Alignment target is not a canonical SWEET IRI: {target_iri}")
        if not mapping.get("rationale"):
            raise ValueError(f"Alignment mapping lacks rationale: {identity}")

        ontology_key = ALLOWED_RELATIONS[relation]
        declared = resources[local_iri].get(ontology_key, [])
        declared_targets = {declared} if isinstance(declared, str) else set(declared)
        if target_iri not in declared_targets:
            raise ValueError(
                f"Ontology misses {relation} from {local_iri} to {target_iri}"
            )

        if sweet_root is not None:
            module_file = Path(sweet_root) / mapping["source_module"]
            if not module_file.is_file():
                raise ValueError(f"SWEET source module is missing: {module_file}")
            if target_iri not in module_file.read_text(encoding="utf-8"):
                raise ValueError(
                    f"SWEET source module does not declare target: {target_iri}"
                )

    unmapped = manifest.get("unmapped", [])
    mapped_iris = {item["local_iri"] for item in mappings}
    for item in unmapped:
        local_iri = item.get("local_iri", "")
        if local_iri not in resources:
            raise ValueError(f"Unmapped list references unknown MAZU concept: {local_iri}")
        if local_iri in mapped_iris:
            raise ValueError(f"Concept is both mapped and unmapped: {local_iri}")
        if not item.get("reason"):
            raise ValueError(f"Unmapped concept lacks reason: {local_iri}")

    return AlignmentSummary(
        alignment_id=manifest["alignment_id"],
        source_commit=commit,
        mapping_count=len(mappings),
        local_concept_count=len(local_concepts),
        unmapped_count=len(unmapped),
    )
