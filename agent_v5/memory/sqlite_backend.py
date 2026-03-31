"""SQLite/FTS5 memory backend — zero-dependency full-text search."""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_v5.memory.base import MemoryBackend
from agent_v5.registry import MemoryRegistry
from agent_v5.types import RetrievalResult


@MemoryRegistry.register("sqlite")
class SQLiteMemory(MemoryBackend):
    """Full-text search memory using SQLite FTS5."""

    backend_id = "sqlite"

    def __init__(self, db_path: str = ":memory:") -> None:
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._setup()

    def _setup(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts
                USING fts5(content, source, content=documents, content_rowid=rowid);

            CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
                INSERT INTO documents_fts(rowid, content, source)
                VALUES (new.rowid, new.content, new.source);
            END;
            CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, content, source)
                VALUES ('delete', old.rowid, old.content, old.source);
            END;
            """
        )

    def store(
        self,
        content: str,
        *,
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        import json

        doc_id = uuid.uuid4().hex[:12]
        meta_str = json.dumps(metadata or {})
        self._conn.execute(
            "INSERT INTO documents (id, content, source, metadata) VALUES (?, ?, ?, ?)",
            (doc_id, content, source, meta_str),
        )
        self._conn.commit()
        return doc_id

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        **kwargs: Any,
    ) -> List[RetrievalResult]:
        import json

        if not query.strip():
            return []

        # Escape FTS5 special characters
        safe_query = query.replace('"', '""')

        try:
            rows = self._conn.execute(
                """
                SELECT d.id, d.content, d.source, d.metadata,
                       rank * -1 AS score
                FROM documents_fts f
                JOIN documents d ON d.rowid = f.rowid
                WHERE documents_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (f'"{safe_query}"', top_k),
            ).fetchall()
        except sqlite3.OperationalError:
            # FTS match failed — fall back to LIKE
            rows = self._conn.execute(
                """
                SELECT id, content, source, metadata, 1.0 AS score
                FROM documents
                WHERE content LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (f"%{query}%", top_k),
            ).fetchall()

        results: List[RetrievalResult] = []
        for row in rows:
            meta = {}
            try:
                meta = json.loads(row[3])
            except (json.JSONDecodeError, TypeError):
                pass
            results.append(
                RetrievalResult(
                    content=row[1],
                    score=float(row[4]) if row[4] else 0.0,
                    source=row[2] or "",
                    metadata=meta,
                )
            )
        return results

    def delete(self, doc_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def clear(self) -> None:
        self._conn.execute("DELETE FROM documents")
        self._conn.commit()

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM documents").fetchone()
        return row[0] if row else 0
