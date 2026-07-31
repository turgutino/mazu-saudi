"""Orchestration for rebuilding the explanation-only evidence graph."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from mazu_saudi.ontology import materialize_ontology
from mazu_saudi.ontology.alignment import validate_alignment_manifest

from .builder import BuildConfig, build_statistical_knowledge_graph
from .external_background import (
    KWGBackgroundStore,
    KWG_DEFAULT_ENDPOINT,
    run_kwg_enrichment,
)


REBUILD_CONTRACT_VERSION = "explanation-evidence-rebuild-v1"


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def rebuild_explanation_graph(
    *,
    stage: str,
    ontology_source: Path,
    alignment_manifest: Path,
    database: Path,
    indicator_dir: Path | None = None,
    sweet_root: Path | None = None,
    kwg_snapshot: Path | None = None,
    kwg_live: bool = False,
    kwg_query_manifest: Path | None = None,
    kwg_endpoint: str = KWG_DEFAULT_ENDPOINT,
    country_iso3: str = "SAU",
    timeout_seconds: float = 30.0,
    graph_config: BuildConfig | None = None,
    manifest_output: Path | None = None,
) -> dict[str, Any]:
    """Rebuild selected layers while preserving their evidence boundaries."""

    if stage not in {"ontology", "graph", "all"}:
        raise ValueError("stage must be one of: ontology, graph, all")
    if kwg_snapshot is not None and kwg_live:
        raise ValueError("kwg_snapshot and kwg_live are mutually exclusive")
    if stage in {"graph", "all"} and indicator_dir is None:
        raise ValueError("indicator_dir is required for graph or all stages")
    if not ontology_source.is_file():
        raise FileNotFoundError(f"Ontology source does not exist: {ontology_source}")
    if not alignment_manifest.is_file():
        raise FileNotFoundError(
            f"SWEET alignment manifest does not exist: {alignment_manifest}"
        )
    if sweet_root is not None and not sweet_root.is_dir():
        raise FileNotFoundError(f"SWEET checkout does not exist: {sweet_root}")
    if indicator_dir is not None and not indicator_dir.is_dir():
        raise FileNotFoundError(
            f"Indicator directory does not exist: {indicator_dir}"
        )
    if kwg_snapshot is not None and not kwg_snapshot.is_file():
        raise FileNotFoundError(f"KWG snapshot does not exist: {kwg_snapshot}")

    alignment = validate_alignment_manifest(
        alignment_manifest,
        ontology_source,
        sweet_root=sweet_root,
    )
    ontology = materialize_ontology(ontology_source, database)
    result: dict[str, Any] = {
        "contract_version": REBUILD_CONTRACT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "database": str(database.resolve()),
        "ontology": ontology["ontology"],
        "sweet_alignment": asdict(alignment),
        "observational_graph": {"status": "not_requested"},
        "kwg_background": {"status": "not_requested"},
        "literature_evidence": {
            "status": "preserved_if_present",
            "boundary": (
                "Literature extraction is a separately audited workflow and is "
                "not fabricated during deterministic rebuilding."
            ),
        },
        "boundaries": [
            "SWEET supplies meteorological concept alignment.",
            (
                "Automatically extracted associations are observational context "
                "for explanation and diagnostics only."
            ),
            "KWG supplies external geography and sourced historical background only.",
            "No rebuilt layer is eligible for automatic prediction or causal promotion.",
        ],
    }

    if stage in {"graph", "all"}:
        graph = build_statistical_knowledge_graph(
            input_dir=Path(indicator_dir),
            database_file=database,
            config=graph_config or BuildConfig(),
        )
        result["observational_graph"] = {
            "status": "built",
            **asdict(graph),
            "use": "explanation_and_research_diagnostics_only",
        }

    if kwg_snapshot is not None:
        snapshot = json.loads(kwg_snapshot.read_text(encoding="utf-8"))
        background = KWGBackgroundStore(database).import_snapshot(snapshot)
        result["kwg_background"] = {
            "operation": "snapshot_import",
            **asdict(background),
        }
    elif kwg_live:
        if kwg_query_manifest is None:
            raise ValueError("kwg_query_manifest is required for live KWG enrichment")
        background = run_kwg_enrichment(
            database_file=database,
            query_manifest_file=kwg_query_manifest,
            endpoint=kwg_endpoint,
            country_iso3=country_iso3,
            timeout_seconds=timeout_seconds,
        )
        result["kwg_background"] = {
            "operation": "live_query",
            **asdict(background),
        }

    if manifest_output is not None:
        _atomic_json(manifest_output, result)
        result["manifest_file"] = str(manifest_output.resolve())
    return result
