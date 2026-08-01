"""Backfill verified Tree SHAP into persisted prediction JSON records."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.repositories.sqlite_backup import create_sqlite_backup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=BACKEND / "var" / "mazu.db")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Without this flag the command is a dry run.",
    )
    parser.add_argument("--backup", type=Path, help="Backup destination for --apply.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    database = args.db.resolve()
    if not database.exists():
        raise SystemExit(f"Database does not exist: {database}")

    backup = create_sqlite_backup(database, args.backup) if args.apply else None
    os.environ["MAZU_DB_PATH"] = str(database)

    from app.repositories.prediction_store import PredictionStore
    from app.services.prediction_attribution_backfill import (
        backfill_prediction_attributions,
    )

    report = backfill_prediction_attributions(
        PredictionStore(), dry_run=not args.apply
    )
    print(
        json.dumps(
            {
                "database": str(database),
                "mode": "apply" if args.apply else "dry-run",
                "backup": str(backup) if backup else None,
                **asdict(report),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
