"""SQLite audit and generated-artifact storage."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4


class AuditStore:
    def __init__(self, database_file: Path, artifact_root: Path):
        self.database_file = Path(database_file)
        self.artifact_root = Path(artifact_root)
        self.database_file.parent.mkdir(parents=True, exist_ok=True)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def _connect(self):
        connection = sqlite3.connect(self.database_file)
        connection.row_factory = sqlite3.Row
        return connection

    def _migrate(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    city TEXT NOT NULL,
                    target_date TEXT NOT NULL,
                    hazard TEXT NOT NULL,
                    locale TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT,
                    error TEXT
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(id)
                );
                CREATE TABLE IF NOT EXISTS assistant_messages (
                    id TEXT PRIMARY KEY,
                    run_id TEXT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_run(self, city: str, target_date: str, hazard: str, locale: str) -> str:
        run_id = uuid4().hex
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, city, target_date, hazard, locale, "running", self._now(), None, None),
            )
        return run_id

    def complete_run(self, run_id: str, payload: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE runs SET status='complete', payload_json=?, error=NULL WHERE id=?",
                (json.dumps(payload, ensure_ascii=False, allow_nan=False), run_id),
            )

    def fail_run(self, run_id: str, error: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE runs SET status='failed', error=? WHERE id=?", (error, run_id)
            )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return self._decode_run(row) if row else None

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._decode_run(row) for row in rows]

    @staticmethod
    def _decode_run(row) -> dict[str, Any]:
        item = dict(row)
        item["result"] = json.loads(item.pop("payload_json")) if item["payload_json"] else None
        return item

    def save_artifact(
        self,
        run_id: str,
        kind: str,
        media_type: str,
        filename: str,
        content: str,
    ) -> dict[str, Any]:
        artifact_id = uuid4().hex
        safe_filename = Path(filename).name
        path = self.artifact_root / f"{artifact_id}-{safe_filename}"
        path.write_text(content, encoding="utf-8")
        created_at = self._now()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?)",
                (artifact_id, run_id, kind, media_type, safe_filename, str(path), created_at),
            )
        return {
            "id": artifact_id,
            "run_id": run_id,
            "kind": kind,
            "media_type": media_type,
            "filename": safe_filename,
            "created_at": created_at,
        }

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE id=?", (artifact_id,)
            ).fetchone()
        return dict(row) if row else None

    def save_message(self, run_id: str | None, role: str, content: str, mode: str) -> dict[str, str]:
        message = {
            "id": uuid4().hex,
            "run_id": run_id,
            "role": role,
            "content": content,
            "mode": mode,
            "created_at": self._now(),
        }
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO assistant_messages VALUES (?, ?, ?, ?, ?, ?)",
                tuple(message.values()),
            )
        return message
