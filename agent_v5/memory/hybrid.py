"""Hybrid memory backend — Reciprocal Rank Fusion of sparse + dense."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agent_v5.memory.base import MemoryBackend
from agent_v5.memory.sqlite_backend import SQLiteMemory
from agent_v5.memory.vector_backend import VectorMemory
from agent_v5.registry import MemoryRegistry
from agent_v5.types import RetrievalResult


@MemoryRegistry.register("hybrid")
class HybridMemory(MemoryBackend):
    """Combines SQLite FTS5 (sparse) and ChromaDB (dense) via RRF fusion."""

    backend_id = "hybrid"

    def __init__(self, db_path: str = ":memory:", vector_dir: str = "") -> None:
        self._sqlite = SQLiteMemory(db_path=db_path)
        self._vector = VectorMemory(persist_dir=vector_dir)

    def store(
        self,
        content: str,
        *,
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        doc_id = self._sqlite.store(content, source=source, metadata=metadata)
        self._vector.store(content, source=source, metadata=metadata)
        return doc_id

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        **kwargs: Any,
    ) -> List[RetrievalResult]:
        k_rrf = 60  # Standard RRF constant
        fetch_k = top_k * 3  # Fetch more for fusion

        sparse = self._sqlite.retrieve(query, top_k=fetch_k)
        dense = self._vector.retrieve(query, top_k=fetch_k)

        # Build content -> RRF score map
        scores: Dict[str, float] = {}
        results_map: Dict[str, RetrievalResult] = {}

        for rank, r in enumerate(sparse):
            key = r.content[:200]  # Use content prefix as key
            scores[key] = scores.get(key, 0) + 1.0 / (k_rrf + rank + 1)
            results_map[key] = r

        for rank, r in enumerate(dense):
            key = r.content[:200]
            scores[key] = scores.get(key, 0) + 1.0 / (k_rrf + rank + 1)
            if key not in results_map:
                results_map[key] = r

        # Sort by fused score and return top_k
        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        out: List[RetrievalResult] = []
        for key in sorted_keys[:top_k]:
            r = results_map[key]
            r.score = scores[key]
            out.append(r)
        return out

    def delete(self, doc_id: str) -> bool:
        a = self._sqlite.delete(doc_id)
        b = self._vector.delete(doc_id)
        return a or b

    def clear(self) -> None:
        self._sqlite.clear()
        self._vector.clear()

    def count(self) -> int:
        return self._sqlite.count()
