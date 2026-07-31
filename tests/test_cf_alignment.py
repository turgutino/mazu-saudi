from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from mazu_saudi.ontology import validate_cf_alignment_manifest


ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "ontology" / "mazu_weather_ontology.jsonld"
ALIGNMENT = ROOT / "ontology" / "cf_standard_name_alignment.json"


def test_curated_cf_alignment_classifies_every_derived_indicator():
    summary = validate_cf_alignment_manifest(ALIGNMENT, ONTOLOGY)

    assert summary.table_version == 94
    assert summary.mapping_count == 11
    assert summary.unmapped_count == 1
    assert summary.derived_indicator_count == 12


def test_cf_alignment_uses_cell_methods_coordinates_and_honest_ivt_boundary():
    manifest = json.loads(ALIGNMENT.read_text(encoding="utf-8"))
    mappings = {item["local_iri"]: item for item in manifest["mappings"]}
    precipitation = mappings["urn:mazu-saudi:concept:DailyPrecipitation"]
    assert (
        precipitation["standard_name"]
        == "lwe_thickness_of_precipitation_amount"
    )
    assert precipitation["cell_methods"] == "time: sum"

    maximum_temperature = mappings[
        "urn:mazu-saudi:concept:MaximumAirTemperature"
    ]
    assert maximum_temperature["standard_name"] == "air_temperature"
    assert maximum_temperature["cell_methods"] == "time: maximum"
    assert maximum_temperature["coordinate_constraints"] == "height=2 m"

    ivt = manifest["unmapped"][0]
    assert ivt["local_iri"].endswith("IntegratedVaporTransport")
    assert ivt["supporting_standard_names"] == [
        "eastward_atmosphere_water_vapor_transport_across_unit_distance",
        "northward_atmosphere_water_vapor_transport_across_unit_distance",
    ]


def test_cf_validator_checks_pinned_xml_version_digest_names_and_units(tmp_path):
    table = tmp_path / "cf-standard-name-table.xml"
    table.write_text(
        """<?xml version="1.0"?>
<standard_name_table>
  <version_number>94</version_number>
  <entry id="air_temperature">
    <canonical_units>K</canonical_units>
    <description>Bulk air temperature.</description>
  </entry>
</standard_name_table>
""",
        encoding="utf-8",
    )
    ontology = tmp_path / "ontology.jsonld"
    ontology.write_text(
        json.dumps(
            {
                "@context": {
                    "@vocab": "urn:test:",
                    "mazu": "urn:mazu-saudi:ontology:",
                    "concept": "urn:mazu-saudi:concept:",
                },
                "@graph": [
                    {
                        "@id": "concept:Temperature",
                        "@type": "mazu:DerivedIndicator",
                        "cfStandardName": "air_temperature",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "alignment.json"
    manifest.write_text(
        json.dumps(
            {
                "alignment_id": "test",
                "source": {
                    "table_version": 94,
                    "xml_url": (
                        "https://cfconventions.org/Data/cf-standard-names/94/"
                        "src/cf-standard-name-table.xml"
                    ),
                    "sha256": sha256(table.read_bytes()).hexdigest(),
                },
                "mappings": [
                    {
                        "local_iri": "urn:mazu-saudi:concept:Temperature",
                        "standard_name": "air_temperature",
                        "canonical_units": "K",
                        "project_units": "degC",
                        "relation": "exact_quantity",
                        "rationale": "Convertible temperature quantity.",
                    }
                ],
                "unmapped": [],
            }
        ),
        encoding="utf-8",
    )

    summary = validate_cf_alignment_manifest(
        manifest,
        ontology,
        cf_table_file=table,
    )
    assert summary.mapping_count == 1

    table.write_text(
        table.read_text(encoding="utf-8").replace(
            "<canonical_units>K</canonical_units>",
            "<canonical_units>Pa</canonical_units>",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="SHA-256 differs"):
        validate_cf_alignment_manifest(
            manifest,
            ontology,
            cf_table_file=table,
        )
