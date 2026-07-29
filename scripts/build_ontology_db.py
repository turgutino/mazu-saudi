"""Build or inspect the local MAZU ontology SQLite database."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mazu_saudi.ontology import OntologyStore, materialize_ontology


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "ontology" / "mazu_weather_ontology.jsonld"
DEFAULT_DATABASE = ROOT / "runtime" / "ontology" / "mazu_weather.sqlite3"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument(
        "--inspect",
        metavar="IRI",
        help="Print one resource and all incoming/outgoing statements after loading.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = materialize_ontology(args.source, args.database)
    result: dict = {"database": str(args.database), "summary": summary}
    if args.inspect:
        store = OntologyStore(args.database)
        result["resource"] = store.get_resource(args.inspect)
        result["statements"] = store.statements_for(args.inspect)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
