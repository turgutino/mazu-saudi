from __future__ import annotations

import json
from pathlib import Path

import pytest

from mazu_saudi.knowledge_graph.rebuild import rebuild_explanation_graph


ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "ontology" / "mazu_weather_ontology.jsonld"
ALIGNMENT = ROOT / "ontology" / "sweet_alignment.json"


def test_ontology_only_rebuild_validates_sweet_and_writes_audit_manifest(tmp_path):
    database = tmp_path / "ontology.sqlite3"
    manifest = tmp_path / "rebuild.json"

    result = rebuild_explanation_graph(
        stage="ontology",
        ontology_source=ONTOLOGY,
        alignment_manifest=ALIGNMENT,
        database=database,
        manifest_output=manifest,
    )

    assert result["contract_version"] == "explanation-evidence-rebuild-v1"
    assert result["ontology"]["version"] == "1.5.0"
    assert result["sweet_alignment"]["mapping_count"] > 0
    assert result["observational_graph"] == {"status": "not_requested"}
    assert result["kwg_background"] == {"status": "not_requested"}
    assert database.is_file()
    saved = json.loads(manifest.read_text(encoding="utf-8"))
    assert saved["boundaries"][-1].startswith("No rebuilt layer")


def test_graph_rebuild_requires_an_explicit_indicator_directory(tmp_path):
    with pytest.raises(ValueError, match="indicator_dir is required"):
        rebuild_explanation_graph(
            stage="all",
            ontology_source=ONTOLOGY,
            alignment_manifest=ALIGNMENT,
            database=tmp_path / "ontology.sqlite3",
        )


def test_kwg_live_and_snapshot_modes_are_mutually_exclusive(tmp_path):
    with pytest.raises(ValueError, match="mutually exclusive"):
        rebuild_explanation_graph(
            stage="ontology",
            ontology_source=ONTOLOGY,
            alignment_manifest=ALIGNMENT,
            database=tmp_path / "ontology.sqlite3",
            kwg_snapshot=tmp_path / "snapshot.json",
            kwg_live=True,
        )


def test_rebuild_rejects_a_missing_kwg_snapshot_before_building(tmp_path):
    with pytest.raises(FileNotFoundError, match="KWG snapshot does not exist"):
        rebuild_explanation_graph(
            stage="ontology",
            ontology_source=ONTOLOGY,
            alignment_manifest=ALIGNMENT,
            database=tmp_path / "ontology.sqlite3",
            kwg_snapshot=tmp_path / "missing.json",
        )
