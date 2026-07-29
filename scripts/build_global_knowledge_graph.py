"""Compute global 2025 indicators outside Saudi Arabia, then build the graph."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from mazu_saudi.indicator_definitions import DEFAULT_IVT_LEVELS_HPA
from mazu_saudi.knowledge_graph import BuildConfig, build_statistical_knowledge_graph
from mazu_saudi.knowledge_graph.global_indicators import (
    GlobalIndicatorConfig,
    audit_sources,
    compute_global_indicator_year,
    discover_daily_sources,
)
from mazu_saudi.ontology import materialize_ontology


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/E/气象数据")
DEFAULT_OUTPUT = DEFAULT_DATA_ROOT / "global_excluding_saudi_2025" / "indicators"
DEFAULT_DATABASE = ROOT / "runtime" / "ontology" / "mazu_weather.sqlite3"
DEFAULT_ONTOLOGY = ROOT / "ontology" / "mazu_weather_ontology.jsonld"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    result.add_argument("--indicator-output", type=Path, default=DEFAULT_OUTPUT)
    result.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    result.add_argument("--ontology-source", type=Path, default=DEFAULT_ONTOLOGY)
    result.add_argument("--year", type=int, default=2025)
    result.add_argument("--tile-degrees", type=float, default=10.0)
    result.add_argument("--max-days-with-missing-sources", type=int, default=5)
    result.add_argument("--start", help="First YYYYMMDD to compute.")
    result.add_argument("--end", help="Last YYYYMMDD to compute.")
    result.add_argument("--limit", type=int, help="Limit indicator computation for validation.")
    result.add_argument("--overwrite", action="store_true")
    result.add_argument("--fail-fast", action="store_true")
    result.add_argument(
        "--stage",
        choices=("audit", "indicators", "graph", "all"),
        default="all",
    )
    result.add_argument("--scope-label", default="global-2025-excluding-saudi")
    result.add_argument("--max-lag-days", type=int, default=3)
    result.add_argument("--min-support-episodes", type=int, default=8)
    result.add_argument("--min-lift", type=float, default=1.15)
    result.add_argument("--max-assertions", type=int, default=160)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    indicator_config = GlobalIndicatorConfig(
        year=args.year,
        tile_degrees=args.tile_degrees,
        ivt_levels_hpa=DEFAULT_IVT_LEVELS_HPA,
        max_days_with_missing_sources=args.max_days_with_missing_sources,
    )
    sources = discover_daily_sources(args.data_root, indicator_config)
    audit = audit_sources(sources, indicator_config)
    print(json.dumps(asdict(audit), ensure_ascii=False, indent=2))
    if args.stage == "audit":
        return 0

    if args.stage in {"indicators", "all"}:
        manifest = args.indicator_output.parent / "indicator_build_manifest.jsonl"
        results = compute_global_indicator_year(
            sources,
            args.indicator_output,
            indicator_config,
            start=args.start,
            end=args.end,
            limit=args.limit,
            overwrite=args.overwrite,
            fail_fast=args.fail_fast,
            manifest=manifest,
        )
        errors = [row for row in results if row["status"] == "error"]
        if errors:
            print(
                json.dumps(
                    {"status": "indicator_errors", "count": len(errors), "errors": errors},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 2
        if args.stage == "indicators":
            return 0
        if args.start or args.end or args.limit is not None:
            print(
                "Partial indicator selection completed; graph build was intentionally skipped. "
                "Run again with --stage graph after all 365 output files are ready."
            )
            return 0

    materialize_ontology(args.ontology_source, args.database)
    graph_result = build_statistical_knowledge_graph(
        input_dir=args.indicator_output,
        database_file=args.database,
        config=BuildConfig(
            year=args.year,
            scope_label=args.scope_label,
            tile_degrees=args.tile_degrees,
            max_lag_days=args.max_lag_days,
            min_support_episodes=args.min_support_episodes,
            min_lift=args.min_lift,
            max_assertions=args.max_assertions,
        ),
    )
    print(json.dumps(asdict(graph_result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
