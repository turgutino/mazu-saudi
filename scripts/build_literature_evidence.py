#!/usr/bin/env python3
"""Fetch, extract, validate, and store literature-grounded mechanism evidence."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from mazu_saudi.knowledge_graph import KnowledgeGraphStore
from mazu_saudi.knowledge_graph.literature import (
    CachedJsonClient,
    LiteratureEvidenceStore,
    ZhipuJsonClient,
    build_literature_layer,
    candidate_statistical_assertions,
    extract_validated_claims,
    fetch_publications,
    load_literature_manifest,
    manifest_sha256,
    snapshot_publication,
)
from mazu_saudi.ontology import materialize_ontology


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "runtime" / "ontology" / "mazu_weather.sqlite3"
DEFAULT_ONTOLOGY = ROOT / "ontology" / "mazu_weather_ontology.jsonld"
DEFAULT_MANIFEST = ROOT / "ontology" / "literature_sources.json"
DEFAULT_RUNTIME = ROOT / "runtime" / "literature"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an immutable literature evidence layer for one frozen "
            "statistical knowledge-graph build."
        )
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--ontology-source", type=Path, default=DEFAULT_ONTOLOGY)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--documents-dir",
        type=Path,
        default=DEFAULT_RUNTIME / "documents",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_RUNTIME / "response_cache",
    )
    parser.add_argument(
        "--audit-dir",
        type=Path,
        default=DEFAULT_RUNTIME / "runs",
    )
    parser.add_argument("--build-id")
    parser.add_argument("--model", default="glm-5.2")
    parser.add_argument("--api-key-env", default="ZHIPU_API_KEY")
    parser.add_argument("--max-candidates", type=int, default=50)
    parser.add_argument("--max-chunks-per-source", type=int, default=6)
    parser.add_argument(
        "--fetch",
        action="store_true",
        help=(
            "Fetch the publisher URLs declared in the versioned manifest before "
            "inspection or graph construction."
        ),
    )
    parser.add_argument(
        "--overwrite-documents",
        action="store_true",
        help="Replace existing saved publication snapshots when fetching.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect sources, snapshots, and candidates without calling BigModel.",
    )
    args = parser.parse_args()
    if args.max_candidates < 1:
        parser.error("--max-candidates must be positive")
    if args.max_chunks_per_source < 1:
        parser.error("--max-chunks-per-source must be positive")
    if args.overwrite_documents and not args.fetch:
        parser.error("--overwrite-documents requires --fetch")
    return args


def _preflight_failure(
    *,
    inspection: dict,
    has_candidates: bool,
    has_snapshots: bool,
) -> dict | None:
    """Return an actionable structured failure instead of hiding fetch diagnostics."""

    if not has_candidates:
        return {
            "status": "blocked",
            "reason": "no_statistical_candidates",
            "message": (
                "No cross-indicator lagged statistical assertions are available."
            ),
            "inspection": inspection,
        }
    if not has_snapshots:
        return {
            "status": "blocked",
            "reason": "no_publication_snapshots",
            "message": (
                "No publication snapshots are available. Publisher HTTP 403/429 "
                "responses are access restrictions, not missing API credentials."
            ),
            "next_steps": [
                (
                    "Review inspection.fetch_errors below; rerun with "
                    "--fetch --dry-run to inspect without calling BigModel."
                ),
                (
                    "Use a browser or institutional access to save a legally "
                    "accessible HTML, TXT, or PDF snapshot."
                ),
                (
                    "Name each file <source_id>.html/.txt/.pdf and place it in "
                    f"{inspection['documents_dir']}."
                ),
            ],
            "inspection": inspection,
        }
    return None


def main() -> int:
    args = parse_args()
    ontology_summary = materialize_ontology(
        args.ontology_source,
        args.database,
    )
    manifest = load_literature_manifest(args.manifest)
    fetch_errors = []
    if args.fetch:
        fetch_publications(
            manifest,
            args.documents_dir,
            overwrite=args.overwrite_documents,
            errors=fetch_errors,
            strict=False,
        )

    candidates = candidate_statistical_assertions(
        args.database,
        build_id=args.build_id,
        limit=args.max_candidates,
    )
    snapshots = []
    snapshot_errors = []
    for source in manifest.sources:
        try:
            snapshots.append(snapshot_publication(source, args.documents_dir))
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            snapshot_errors.append(
                {"source_id": source.source_id, "error": str(exc)}
            )

    inspection = {
        "status": "dry_run" if args.dry_run else "ready",
        "ontology_version": ontology_summary["ontology"]["version"],
        "build_id": candidates[0].build_id if candidates else args.build_id,
        "manifest_version": manifest.version,
        "source_count": len(manifest.sources),
        "snapshot_count": len(snapshots),
        "snapshot_errors": snapshot_errors,
        "fetch_errors": fetch_errors,
        "candidate_count": len(candidates),
        "candidate_stages": {
            stage: sum(
                candidate.validation_stage == stage for candidate in candidates
            )
            for stage in sorted(
                {candidate.validation_stage for candidate in candidates}
            )
        },
        "model": args.model,
        "api_key_environment_variable": args.api_key_env,
        "documents_dir": str(args.documents_dir.resolve()),
    }
    if args.dry_run:
        print(json.dumps(inspection, ensure_ascii=False, indent=2))
        return 0
    failure = _preflight_failure(
        inspection=inspection,
        has_candidates=bool(candidates),
        has_snapshots=bool(snapshots),
    )
    if failure is not None:
        print(json.dumps(failure, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    client = CachedJsonClient(
        ZhipuJsonClient.from_environment(
            variable=args.api_key_env,
            model=args.model,
        ),
        args.cache_dir,
    )
    claims = extract_validated_claims(
        tuple(snapshots),
        candidates,
        client,
        max_chunks_per_source=args.max_chunks_per_source,
    )
    graph_store = KnowledgeGraphStore(args.database)
    build_id = candidates[0].build_id
    config = {
        "manifest_version": manifest.version,
        "documents_dir": str(args.documents_dir),
        "candidate_count": len(candidates),
        "candidate_selection": (
            "lagged_cross_indicator observational evidence selected for "
            "literature interpretation, never for prediction promotion"
        ),
        "max_chunks_per_source": args.max_chunks_per_source,
        "snapshot_errors": snapshot_errors,
        "fetch_errors": fetch_errors,
        "claim_gate": (
            "controlled candidate and mechanism plus exact normalized quote "
            "containment"
        ),
    }
    layer = build_literature_layer(
        build_id=build_id,
        ontology_identity=graph_store.ontology_identity(),
        manifest_digest=manifest_sha256(args.manifest),
        snapshots=tuple(snapshots),
        claims=claims,
        model=args.model,
        config=config,
    )
    LiteratureEvidenceStore(args.database).write_layer(layer)

    args.audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = args.audit_dir / f"{layer.run['run_id']}.json"
    audit_payload = {
        "run": layer.run,
        "inspection": inspection,
        "accepted_claims": [
            {
                **asdict(claim),
                "source": claim.source.model_dump(mode="json"),
                "candidate": asdict(claim.candidate),
            }
            for claim in layer.accepted_claims
        ],
    }
    audit_path.write_text(
        json.dumps(audit_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "stored",
                "run_id": layer.run["run_id"],
                "build_id": build_id,
                "publication_count": layer.run["publication_count"],
                "evidence_record_count": layer.run[
                    "evidence_record_count"
                ],
                "mechanism_assertion_count": layer.run[
                    "mechanism_assertion_count"
                ],
                "snapshot_errors": snapshot_errors,
                "fetch_errors": fetch_errors,
                "audit_file": str(audit_path),
                "claim_boundary": (
                    "Automatic literature evidence remains non-causal, "
                    "non-transfer-validated, and not production-ready."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted; no partial database layer was committed.", file=sys.stderr)
        raise SystemExit(130)
