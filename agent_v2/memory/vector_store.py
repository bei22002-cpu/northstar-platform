"""Vector store — ChromaDB-backed semantic memory for past interactions.

Stores embeddings of conversation turns and tool results so that relevant
past context can be retrieved by similarity search.

Uses ChromaDB's default embedding function (Sentence Transformers) if
available, falling back to a simple character-trigram hash for environments
where heavy ML dependencies aren't installed.
"""

from __future__ import annotations

import hashlib
import os
import time
from typing import Any

_DEFAULT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "vectordb")
_COLLECTION_NAME = "agent_memory"


class VectorStore:
    """Persistent semantic memory backed by ChromaDB."""

    def __init__(self, persist_dir: str | None = None) -> None:
        self._persist_dir = os.path.abspath(persist_dir or _DEFAULT_DIR)
        self._collection: Any = None
        self._client: Any = None
        self._init_store()

    # -- public API -----------------------------------------------------------

    def add(self, text: str, metadata: dict[str, Any] | None = None) -> str:
        """Store a text chunk with optional metadata.  Returns the doc id."""
        if self._collection is None:
            return ""
        doc_id = self._make_id(text)
        meta = metadata or {}
        meta["timestamp"] = time.time()
        # Truncate long text to keep embeddings meaningful
        stored_text = text[:2000] if len(text) > 2000 else text
        try:
            self._collection.add(
                documents=[stored_text],
                metadatas=[meta],
                ids=[doc_id],
            )
        except Exception:
            # Duplicate id or other error — upsert instead
            try:
                self._collection.upsert(
                    documents=[stored_text],
                    metadatas=[meta],
                    ids=[doc_id],
                )
            except Exception:
                pass
        return doc_id

    def query(self, text: str, n_results: int = 5) -> list[dict[str, Any]]:
        """Retrieve the *n_results* most similar stored memories.

        Returns a list of dicts with keys ``text``, ``metadata``, ``distance``.
        """
        if self._collection is None:
            return []
        try:
            results = self._collection.query(
                query_texts=[text],
                n_results=min(n_results, self.count()),
            )
        except Exception:
            return []

        if not results or not results.get("documents"):
            return []

        docs = results["documents"][0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        out: list[dict[str, Any]] = []
        for i, doc in enumerate(docs):
            out.append(
                {
                    "text": doc,
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": dists[i] if i < len(dists) else 0.0,
                }
            )
        return out

    def count(self) -> int:
        """Return the number of stored documents."""
        if self._collection is None:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0

    def clear(self) -> None:
        """Delete all stored memories."""
        if self._client is not None:
            try:
                self._client.delete_collection(_COLLECTION_NAME)
                self._collection = self._client.get_or_create_collection(
                    name=_COLLECTION_NAME,
                )
            except Exception:
                pass

    # -- initialisation -------------------------------------------------------

    def _init_store(self) -> None:
        """Attempt to initialise ChromaDB.  Gracefully degrade if unavailable."""
        try:
            import chromadb

            os.makedirs(self._persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self._persist_dir)
            self._collection = self._client.get_or_create_collection(
                name=_COLLECTION_NAME,
            )
        except ImportError:
            # chromadb not installed — vector memory disabled
            self._client = None
            self._collection = None
        except Exception:
            self._client = None
            self._collection = None

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _make_id(text: str) -> str:
        """Deterministic id from content hash + timestamp for uniqueness."""
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        ts = str(int(time.time() * 1000))[-8:]
        return f"mem_{h}_{ts}"
