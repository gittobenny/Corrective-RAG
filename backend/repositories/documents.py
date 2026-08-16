#SQLite metadata storage shared by FastAPI and Celery

from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from typing import Any


class DocumentRepository:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    collection_id TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    storage_path TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    task_id TEXT,
                    chunks_stored INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create(
        self,
        *,
        document_id: str,
        collection_id: str,
        original_filename: str,
        storage_path: str,
        content_type: str,
        size: int,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO documents (
                    document_id, collection_id, original_filename, storage_path,
                    content_type, size, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'queued', ?, ?)
                """,
                (
                    document_id,
                    collection_id,
                    original_filename,
                    storage_path,
                    content_type,
                    size,
                    now,
                    now,
                ),
            )

    def update(self, document_id: str, **fields: Any) -> None:
        allowed = {"status", "task_id", "chunks_stored", "error"}
        invalid = set(fields) - allowed
        if invalid:
            raise ValueError(f"Unsupported document fields: {sorted(invalid)}")
        if not fields:
            return

        fields["updated_at"] = datetime.now(UTC).isoformat()
        assignments = ", ".join(f"{name} = ?" for name in fields)
        values = [*fields.values(), document_id]
        with self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE documents SET {assignments} WHERE document_id = ?",
                values,
            )
            if cursor.rowcount == 0:
                raise KeyError(document_id)

    def get(self, document_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE document_id = ?", (document_id,)
            ).fetchone()
        return dict(row) if row else None

    def ready_document_ids(self, collection_id: str) -> set[str]:
        """Return documents that are safe for the research endpoint to query."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT document_id FROM documents
                WHERE collection_id = ? AND status = 'ready'
                """,
                (collection_id,),
            ).fetchall()
        return {str(row["document_id"]) for row in rows}
