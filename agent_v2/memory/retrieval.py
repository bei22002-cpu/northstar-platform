"""Memory retrieval — given a query, return only relevant stored memories.

Combines results from the vector store with a relevance threshold so that
only genuinely useful context is injected into the prompt.
"""

from __future__ import annotations

from typing import Any

from agent_v2.memory.vector_store import VectorStore


# Distance threshold — ChromaDB uses L2 distance by default.
# Lower = more similar.  Memories above this threshold are discarded.
_MAX_DISTANCE = 1.5


class MemoryRetriever:
    """Selective retrieval of relevant past interactions."""

    def __init__(self, vector_store: VectorStore) -> None:
        self._store = vector_store

    def retrieve(
        self,
        query: str,
        n_results: int = 5,
        max_distance: float = _MAX_DISTANCE,
    ) -> list[dict[str, Any]]:
        """Return relevant memories for *query*, filtered by distance.

        Parameters
        ----------
        query:
            The current user message or context to search against.
        n_results:
            Maximum number of results to return.
        max_distance:
            Discard results with distance greater than this.

        Returns
        -------
        list of dict
            Each dict has keys ``text``, ``metadata``, ``distance``.
        """
        if not query.strip():
            return []

        results = self._store.query(query, n_results=n_results)
        # Filter by relevance threshold
        return [r for r in results if r.get("distance", 999) <= max_distance]

    def retrieve_as_prompt(
        self,
        query: str,
        n_results: int = 5,
        max_distance: float = _MAX_DISTANCE,
    ) -> str:
        """Retrieve relevant memories and format them for prompt injection.

        Returns an empty string if no relevant memories are found.
        """
        results = self.retrieve(query, n_results=n_results, max_distance=max_distance)
        if not results:
            return ""

        lines: list[str] = []
        for r in results:
            text = r["text"]
            # Truncate individual memories to keep prompt compact
            if len(text) > 500:
                text = text[:500] + "..."
            lines.append(f"- {text}")

        return "Relevant past context:\n" + "\n".join(lines)

    def store_interaction(
        self,
        text: str,
        role: str = "user",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store a conversation turn for future retrieval."""
        if not text.strip():
            return
        meta = metadata or {}
        meta["role"] = role
        self._store.add(text, metadata=meta)
