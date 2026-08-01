"""Consistent online backup helper for the local SQLite database."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def create_sqlite_backup(
    source: Path, destination: Path | None = None
) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = destination or source.with_name(f"{source.name}.bak-{timestamp}")
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists():
        raise FileExistsError(f"Backup already exists: {backup}")
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as source_db:
        with sqlite3.connect(backup) as backup_db:
            source_db.backup(backup_db)
    return backup
