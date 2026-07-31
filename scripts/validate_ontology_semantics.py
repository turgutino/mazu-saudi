"""Validate MAZU ontology 2.0 domain semantics without optional RDF dependencies."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from mazu_saudi.ontology import validate_ontology_semantics


ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ontology",
        type=Path,
        default=ROOT / "ontology" / "mazu_weather_ontology.jsonld",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = json.loads(args.ontology.read_text(encoding="utf-8"))
    summary = validate_ontology_semantics(payload)
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
