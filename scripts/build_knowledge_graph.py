"""Build the 2025 statistical knowledge graph from daily indicator NetCDF files."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from mazu_saudi.knowledge_graph import BuildConfig, build_statistical_knowledge_graph
from mazu_saudi.ontology import materialize_ontology


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ONTOLOGY = ROOT / "ontology" / "mazu_weather_ontology.jsonld"
DEFAULT_DATABASE = ROOT / "runtime" / "ontology" / "mazu_weather.sqlite3"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing one daily indicator NetCDF file per YYYYMMDD.",
    )
    parser.add_argument("--file-glob", default="*.nc")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--scope-label", default="global-2025")
    parser.add_argument("--tile-degrees", type=float, default=10.0)
    parser.add_argument("--max-lag-days", type=int, default=3)
    parser.add_argument("--min-support-episodes", type=int, default=8)
    parser.add_argument("--min-lift", type=float, default=1.15)
    parser.add_argument("--max-assertions", type=int, default=160)
    parser.add_argument("--evidence-episode-limit", type=int, default=12)
    parser.add_argument("--min-indicator-file-coverage", type=float, default=0.50)
    parser.add_argument(
        "--min-indicator-season-coverage",
        type=float,
        default=0.75,
    )
    parser.add_argument(
        "--allow-degraded-coverage",
        action="store_true",
        help=(
            "Allow an explicitly labelled validation graph when seasonal "
            "indicator coverage is below the formal gate."
        ),
    )
    parser.add_argument(
        "--allow-incomplete-year",
        action="store_true",
        help="Allow a deliberate partial build; complete-year input is required by default.",
    )
    parser.add_argument("--ontology-source", type=Path, default=DEFAULT_ONTOLOGY)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    scope_label = args.scope_label
    if (
        args.allow_degraded_coverage
        and "validation-degraded" not in scope_label
    ):
        scope_label = f"{scope_label}-validation-degraded"
    config = BuildConfig(
        year=args.year,
        file_glob=args.file_glob,
        scope_label=scope_label,
        tile_degrees=args.tile_degrees,
        max_lag_days=args.max_lag_days,
        min_support_episodes=args.min_support_episodes,
        min_lift=args.min_lift,
        max_assertions=args.max_assertions,
        evidence_episode_limit=args.evidence_episode_limit,
        min_indicator_file_coverage=args.min_indicator_file_coverage,
        min_indicator_season_coverage=args.min_indicator_season_coverage,
        allow_degraded_coverage=args.allow_degraded_coverage,
        require_complete_year=not args.allow_incomplete_year,
    )
    materialize_ontology(args.ontology_source, args.database)
    result = build_statistical_knowledge_graph(
        input_dir=args.input_dir,
        database_file=args.database,
        config=config,
    )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
