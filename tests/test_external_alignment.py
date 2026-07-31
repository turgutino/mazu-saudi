import json
from pathlib import Path

import pytest

from mazu_saudi.ontology import validate_alignment_manifest


ROOT = Path(__file__).parents[1]
ONTOLOGY = ROOT / "ontology/mazu_weather_ontology.jsonld"
ALIGNMENT = ROOT / "ontology/sweet_alignment.json"


def test_curated_sweet_alignment_is_declared_in_the_ontology():
    summary = validate_alignment_manifest(ALIGNMENT, ONTOLOGY)

    assert summary.source_commit == "db60c8ddb1b781fbadae176f69286a2cdd5099a0"
    assert summary.mapping_count == 17
    assert summary.local_concept_count == 16
    assert summary.unmapped_count == 6


def test_sweet_alignment_uses_relation_strength_to_protect_domain_boundaries():
    manifest = json.loads(ALIGNMENT.read_text(encoding="utf-8"))
    mappings = {
        (item["local_iri"], item["target_iri"]): item["relation"]
        for item in manifest["mappings"]
    }

    assert mappings[
        (
            "urn:mazu-saudi:concept:PrecipitableWater",
            "http://sweetontology.net/propSpaceThickness/PrecipitableWater",
        )
    ] == "skos:exactMatch"
    assert mappings[
        (
            "urn:mazu-saudi:concept:TenMetreWindSpeed",
            "http://sweetontology.net/propSpeed/WindSpeed",
        )
    ] == "skos:closeMatch"
    assert mappings[
        (
            "urn:mazu-saudi:concept:FlashFloodFavourableState",
            "http://sweetontology.net/phenHydro/FlashFlood",
        )
    ] == "skos:relatedMatch"


def test_alignment_validator_checks_the_pinned_sweet_module(tmp_path):
    sweet_root = tmp_path / "sweet"
    module = sweet_root / "src/propSpaceThickness.ttl"
    module.parent.mkdir(parents=True)
    module.write_text(
        "<http://sweetontology.net/propSpaceThickness/PrecipitableWater> "
        "a <http://www.w3.org/2002/07/owl#Class> .",
        encoding="utf-8",
    )
    manifest = json.loads(ALIGNMENT.read_text(encoding="utf-8"))
    manifest["mappings"] = [
        item
        for item in manifest["mappings"]
        if item["local_iri"] == "urn:mazu-saudi:concept:PrecipitableWater"
    ]
    manifest["unmapped"] = []
    manifest_file = tmp_path / "alignment.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    summary = validate_alignment_manifest(
        manifest_file,
        ONTOLOGY,
        sweet_root=sweet_root,
    )
    assert summary.mapping_count == 1

    module.write_text("# target removed", encoding="utf-8")
    with pytest.raises(ValueError, match="does not declare target"):
        validate_alignment_manifest(
            manifest_file,
            ONTOLOGY,
            sweet_root=sweet_root,
        )
