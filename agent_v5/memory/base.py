"""MemoryBackend ABC — all memory backends implement this interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from agent_v5.types import RetrievalResult


class MemoryBackend(ABC):
    """Abstract base for memory storage backends."""

    backend_id: str = ""

    @abstractmethod
    def store(
        self,
        content: str,
        *,
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Persist *content* and return a unique document id."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        **kwargs: Any,
    ) -> List[RetrievalResult]:
        """Search for *query* and return the top-k results."""

    @abstractmethod
    def delete(self, doc_id: str) -> bool:
        """Delete a document by id.  Return True if it existed."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all stored documents."""

    @abstractmethod
    def count(self) -> int:
        """Return the number of stored documents."""
