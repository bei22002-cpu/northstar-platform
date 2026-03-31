"""Vector memory backend — dense embedding retrieval via ChromaDB."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from agent_v5.memory.base import MemoryBackend
from agent_v5.registry import MemoryRegistry
from agent_v5.types import RetrievalResult


@MemoryRegistry.register("vector")
class VectorMemory(MemoryBackend):
    """Dense vector retrieval using ChromaDB (optional dependency)."""

    backend_id = "vector"

    def __init__(self, persist_dir: str = "") -> None:
        self._available = False
        self._collection: Any = None
        try:
            import chromadb

            if persist_dir:
                from pathlib import Path

                Path(persist_dir).mkdir(parents=True, exist_ok=True)
                client = chromadb.PersistentClient(path=persist_dir)
            else:
                client = chromadb.Client()
            self._collection = client.get_or_create_collection(
                name="agent_v5_memory",
                metadata={"hnsw:space": "cosine"},
            )
            self._available = True
        except ImportError:
            pass

    @property
    def available(self) -> bool:
        return self._available

    def store(
        self,
        content: str,
        *,
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not self._available:
            return ""
        doc_id = uuid.uuid4().hex[:12]
        meta = dict(metadata or {})
        if source:
            meta["source"] = source
        self._collection.add(
            documents=[content],
            ids=[doc_id],
            metadatas=[meta] if meta else None,
        )
        return doc_id

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        **kwargs: Any,
    ) -> List[RetrievalResult]:
        if not self._available or not query.strip():
            return []
        count = self._collection.count()
        if count == 0:
            return []

        results = self._collection.query(
            query_texts=[query],
            n_results=min(top_k, count),
        )

        out: List[RetrievalResult] = []
        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        for i, doc in enumerate(docs):
            dist = distances[i] if i < len(distances) else 1.0
            meta = metadatas[i] if i < len(metadatas) else {}
            source = (meta or {}).pop("source", "")
            out.append(
                RetrievalResult(
                    content=doc,
                    score=1.0 - dist,  # Convert distance to similarity
                    source=source,
                    metadata=meta or {},
                )
            )
        return out

    def delete(self, doc_id: str) -> bool:
        if not self._available:
            return False
        try:
            self._collection.delete(ids=[doc_id])
            return True
        except Exception:
            return False

    def clear(self) -> None:
        if not self._available:
            return
        ids = self._collection.get()["ids"]
        if ids:
            self._collection.delete(ids=ids)

    def count(self) -> int:
        if not self._available:
            return 0
        return self._collection.count()
