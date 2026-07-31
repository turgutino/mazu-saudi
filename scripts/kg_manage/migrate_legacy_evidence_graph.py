"""Align the historical JSON graph with the MAZU ontology compatibility contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from mazu_saudi.knowledge_graph.legacy_graph import (
    migrate_legacy_evidence_graph,
    validate_legacy_graph_alignment,
)


ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "research" / "historical_warning" / "kg" / "kg_data.json",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--ontology",
        type=Path,
        default=ROOT / "ontology" / "mazu_weather_ontology.jsonld",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = args.output or args.input
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    migrated = migrate_legacy_evidence_graph(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=output.parent,
        prefix=f".{output.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(migrated, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(output)
    summary = validate_legacy_graph_alignment(output, args.ontology)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
