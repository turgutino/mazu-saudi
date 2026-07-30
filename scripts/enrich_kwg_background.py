"""Import a saved KWG snapshot or run bounded live background enrichment."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from mazu_saudi.knowledge_graph.external_background import (
    KWGBackgroundStore,
    KWG_DEFAULT_ENDPOINT,
    run_kwg_enrichment,
)


ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=ROOT / "runtime" / "ontology" / "mazu_weather.sqlite3",
    )
    parser.add_argument(
        "--query-manifest",
        type=Path,
        default=ROOT / "ontology" / "kwg_background_queries.json",
    )
    parser.add_argument("--endpoint", default=KWG_DEFAULT_ENDPOINT)
    parser.add_argument("--country-iso3", default="SAU")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Import a previously saved, normalized KWG snapshot instead of querying live.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.snapshot:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        result = KWGBackgroundStore(args.database).import_snapshot(snapshot)
    else:
        result = run_kwg_enrichment(
            database_file=args.database,
            query_manifest_file=args.query_manifest,
            endpoint=args.endpoint,
            country_iso3=args.country_iso3,
            timeout_seconds=args.timeout_seconds,
        )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 2 if result.status == "source_unavailable" else 0


if __name__ == "__main__":
    raise SystemExit(main())
