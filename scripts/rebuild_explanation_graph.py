#!/usr/bin/env python3
"""Rebuild the SWEET-aligned, explanation-only evidence graph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mazu_saudi.knowledge_graph import BuildConfig
from mazu_saudi.knowledge_graph.external_background import KWG_DEFAULT_ENDPOINT
from mazu_saudi.knowledge_graph.rebuild import rebuild_explanation_graph


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "runtime" / "ontology" / "mazu_weather.sqlite3"
DEFAULT_ONTOLOGY = ROOT / "ontology" / "mazu_weather_ontology.jsonld"
DEFAULT_ALIGNMENT = ROOT / "ontology" / "sweet_alignment.json"
DEFAULT_KWG_QUERIES = ROOT / "ontology" / "kwg_background_queries.json"
DEFAULT_MANIFEST = ROOT / "runtime" / "evidence_graph" / "rebuild_manifest.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        choices=("ontology", "graph", "all"),
        default="all",
        help="Rebuild only ontology materialization, graph instances, or both.",
    )
    parser.add_argument(
        "--indicator-dir",
        type=Path,
        help=(
            "Daily indicator NetCDF directory. Required for graph/all; no "
            "regional directory is assumed to avoid mislabelling Saudi data as global."
        ),
    )
    parser.add_argument("--ontology-source", type=Path, default=DEFAULT_ONTOLOGY)
    parser.add_argument("--alignment-manifest", type=Path, default=DEFAULT_ALIGNMENT)
    parser.add_argument("--sweet-root", type=Path)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--manifest-output", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--scope-label", default="global-2025-excluding-saudi")
    parser.add_argument("--file-glob", default="*.nc")
    parser.add_argument("--tile-degrees", type=float, default=10.0)
    parser.add_argument("--max-lag-days", type=int, default=3)
    parser.add_argument("--min-support-episodes", type=int, default=8)
    parser.add_argument("--min-lift", type=float, default=1.15)
    parser.add_argument("--max-assertions", type=int, default=160)
    parser.add_argument("--evidence-episode-limit", type=int, default=12)
    parser.add_argument("--allow-incomplete-year", action="store_true")
    parser.add_argument(
        "--allow-degraded-coverage",
        action="store_true",
        help=(
            "Build a validation-only graph when seasonal indicator coverage is "
            "below the formal gate; the scope is labelled validation-degraded."
        ),
    )
    parser.add_argument("--kwg-snapshot", type=Path)
    parser.add_argument("--kwg-live", action="store_true")
    parser.add_argument("--kwg-query-manifest", type=Path, default=DEFAULT_KWG_QUERIES)
    parser.add_argument("--kwg-endpoint", default=KWG_DEFAULT_ENDPOINT)
    parser.add_argument("--country-iso3", default="SAU")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.stage in {"graph", "all"} and args.indicator_dir is None:
        parser.error("--indicator-dir is required when --stage is graph or all")
    if args.kwg_snapshot and args.kwg_live:
        parser.error("--kwg-snapshot and --kwg-live are mutually exclusive")
    scope_label = args.scope_label
    if (
        args.allow_degraded_coverage
        and "validation-degraded" not in scope_label
    ):
        scope_label = f"{scope_label}-validation-degraded"

    result = rebuild_explanation_graph(
        stage=args.stage,
        ontology_source=args.ontology_source,
        alignment_manifest=args.alignment_manifest,
        database=args.database,
        indicator_dir=args.indicator_dir,
        sweet_root=args.sweet_root,
        kwg_snapshot=args.kwg_snapshot,
        kwg_live=args.kwg_live,
        kwg_query_manifest=args.kwg_query_manifest,
        kwg_endpoint=args.kwg_endpoint,
        country_iso3=args.country_iso3,
        timeout_seconds=args.timeout_seconds,
        graph_config=BuildConfig(
            year=args.year,
            file_glob=args.file_glob,
            scope_label=scope_label,
            tile_degrees=args.tile_degrees,
            max_lag_days=args.max_lag_days,
            min_support_episodes=args.min_support_episodes,
            min_lift=args.min_lift,
            max_assertions=args.max_assertions,
            evidence_episode_limit=args.evidence_episode_limit,
            allow_degraded_coverage=args.allow_degraded_coverage,
            require_complete_year=not args.allow_incomplete_year,
        ),
        manifest_output=args.manifest_output,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["kwg_background"].get("status") == "source_unavailable" else 0


if __name__ == "__main__":
    raise SystemExit(main())
