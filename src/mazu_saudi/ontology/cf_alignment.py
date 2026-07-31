"""Validation for curated CF Standard Name alignments."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


MAZU_DERIVED_INDICATOR = "urn:mazu-saudi:ontology:DerivedIndicator"
STANDARD_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
ALLOWED_RELATIONS = {
    "exact_quantity",
    "exact_quantity_with_aggregation",
    "exact_quantity_with_coordinate",
}


@dataclass(frozen=True)
class CfAlignmentSummary:
    alignment_id: str
    table_version: int
    table_sha256: str
    mapping_count: int
    unmapped_count: int
    derived_indicator_count: int


def _ontology_resources(
    payload: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
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

    return (
        {expand(node["@id"]): node for node in payload["@graph"]},
        prefixes,
    )


def _cf_entries(table_file: Path) -> tuple[int, dict[str, str]]:
    try:
        root = ET.parse(table_file).getroot()
    except (ET.ParseError, OSError) as exc:
        raise ValueError("CF Standard Name Table XML cannot be read") from exc
    try:
        version = int(root.findtext("version_number", ""))
    except ValueError as exc:
        raise ValueError("CF table version_number must be an integer") from exc
    entries = {
        entry.attrib["id"]: entry.findtext("canonical_units", "")
        for entry in root.findall("entry")
    }
    aliases = {
        alias.attrib["id"]: alias.findtext("entry_id", "")
        for alias in root.findall("alias")
    }
    for alias, target in aliases.items():
        if target in entries:
            entries[alias] = entries[target]
    return version, entries


def validate_cf_alignment_manifest(
    manifest_file: Path,
    ontology_file: Path,
    *,
    cf_table_file: Path | None = None,
) -> CfAlignmentSummary:
    """Validate local coverage and, optionally, a pinned official CF XML table."""

    manifest_file = Path(manifest_file)
    ontology_file = Path(ontology_file)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    ontology = json.loads(ontology_file.read_text(encoding="utf-8"))
    resources, prefixes = _ontology_resources(ontology)
    source = manifest.get("source") or {}
    table_version = source.get("table_version")
    if not isinstance(table_version, int) or table_version < 1:
        raise ValueError("CF table_version must be a positive integer")
    source_sha = source.get("sha256", "")
    if not re.fullmatch(r"[0-9a-f]{64}", source_sha):
        raise ValueError("CF source sha256 must be a lowercase SHA-256 digest")
    parsed_url = urlparse(source.get("xml_url", ""))
    expected_path = (
        f"/Data/cf-standard-names/{table_version}/src/"
        "cf-standard-name-table.xml"
    )
    if (
        parsed_url.scheme != "https"
        or parsed_url.netloc != "cfconventions.org"
        or parsed_url.path != expected_path
    ):
        raise ValueError("CF source must identify the pinned official XML table")

    mappings = manifest.get("mappings")
    unmapped = manifest.get("unmapped")
    if not isinstance(mappings, list) or not mappings:
        raise ValueError("CF alignment manifest must contain mappings")
    if not isinstance(unmapped, list):
        raise ValueError("CF alignment manifest must contain an unmapped list")

    covered: set[str] = set()
    standard_names: dict[str, str] = {}
    for mapping in mappings:
        local_iri = mapping.get("local_iri", "")
        standard_name = mapping.get("standard_name", "")
        if local_iri in covered:
            raise ValueError(f"Duplicate CF local concept: {local_iri}")
        covered.add(local_iri)
        node = resources.get(local_iri)
        if node is None:
            raise ValueError(f"CF alignment references unknown concept: {local_iri}")
        node_type = node.get("@type", "")
        if ":" in node_type:
            prefix, local = node_type.split(":", 1)
            node_type = f"{prefixes.get(prefix, prefix + ':')}{local}"
        if node_type != MAZU_DERIVED_INDICATOR:
            raise ValueError(f"CF mapping target is not a DerivedIndicator: {local_iri}")
        if mapping.get("relation") not in ALLOWED_RELATIONS:
            raise ValueError(f"Unsupported CF relation for {local_iri}")
        if not STANDARD_NAME_PATTERN.fullmatch(standard_name):
            raise ValueError(f"Invalid CF standard name: {standard_name}")
        if node.get("cfStandardName") != standard_name:
            raise ValueError(
                f"Ontology CF standard name differs for {local_iri}: "
                f"{node.get('cfStandardName')!r}"
            )
        if node.get("cfCellMethods") != mapping.get("cell_methods"):
            raise ValueError(f"Ontology CF cell methods differ for {local_iri}")
        if node.get("cfCoordinateConstraint") != mapping.get(
            "coordinate_constraints"
        ):
            raise ValueError(f"Ontology CF coordinate constraint differs for {local_iri}")
        if not mapping.get("canonical_units") or not mapping.get("project_units"):
            raise ValueError(f"CF mapping units are incomplete for {local_iri}")
        if not mapping.get("rationale"):
            raise ValueError(f"CF mapping lacks rationale for {local_iri}")
        standard_names[standard_name] = mapping["canonical_units"]

    for item in unmapped:
        local_iri = item.get("local_iri", "")
        if local_iri in covered:
            raise ValueError(f"CF concept is both mapped and unmapped: {local_iri}")
        covered.add(local_iri)
        node = resources.get(local_iri)
        if node is None:
            raise ValueError(f"CF unmapped concept is unknown: {local_iri}")
        if node.get("cfStandardName"):
            raise ValueError(f"Unmapped concept declares cfStandardName: {local_iri}")
        supporting = item.get("supporting_standard_names")
        if not item.get("reason") or not isinstance(supporting, list) or not supporting:
            raise ValueError(f"CF unmapped rationale is incomplete for {local_iri}")
        if node.get("cfSupportingStandardName") != supporting:
            raise ValueError(f"Ontology CF supporting names differ for {local_iri}")
        for standard_name in supporting:
            if not STANDARD_NAME_PATTERN.fullmatch(standard_name):
                raise ValueError(f"Invalid supporting CF standard name: {standard_name}")
            standard_names[standard_name] = item["canonical_units"]

    derived_indicators = {
        iri
        for iri, node in resources.items()
        if node.get("@type") == "mazu:DerivedIndicator"
    }
    if covered != derived_indicators:
        missing = sorted(derived_indicators - covered)
        extra = sorted(covered - derived_indicators)
        raise ValueError(
            f"CF alignment must classify every DerivedIndicator; "
            f"missing={missing}, extra={extra}"
        )

    if cf_table_file is not None:
        cf_table_file = Path(cf_table_file)
        actual_sha = sha256(cf_table_file.read_bytes()).hexdigest()
        if actual_sha != source_sha:
            raise ValueError("CF table SHA-256 differs from the pinned manifest")
        actual_version, entries = _cf_entries(cf_table_file)
        if actual_version != table_version:
            raise ValueError("CF table version differs from the pinned manifest")
        for standard_name, canonical_units in standard_names.items():
            if standard_name not in entries:
                raise ValueError(
                    f"CF table does not contain standard name: {standard_name}"
                )
            if entries[standard_name] != canonical_units:
                raise ValueError(
                    f"CF canonical units differ for {standard_name}: "
                    f"{entries[standard_name]!r}"
                )

    return CfAlignmentSummary(
        alignment_id=manifest["alignment_id"],
        table_version=table_version,
        table_sha256=source_sha,
        mapping_count=len(mappings),
        unmapped_count=len(unmapped),
        derived_indicator_count=len(derived_indicators),
    )
