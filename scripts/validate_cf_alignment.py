"""Validate the curated MAZU-to-CF Standard Name alignment."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from mazu_saudi.ontology import validate_cf_alignment_manifest


ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "ontology" / "cf_standard_name_alignment.json",
    )
    parser.add_argument(
        "--ontology",
        type=Path,
        default=ROOT / "ontology" / "mazu_weather_ontology.jsonld",
    )
    parser.add_argument(
        "--cf-table",
        type=Path,
        help="Optional pinned CF Standard Name Table XML for full offline verification.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = validate_cf_alignment_manifest(
        args.manifest,
        args.ontology,
        cf_table_file=args.cf_table,
    )
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
