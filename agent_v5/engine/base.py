"""InferenceEngine ABC — all backends implement this interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Optional

from agent_v5.types import GenerationConfig, GenerationResult, ModelSpec


class InferenceEngine(ABC):
    """Abstract base for inference backends (Ollama, Anthropic, OpenAI, etc.)."""

    engine_id: str = ""

    @abstractmethod
    def generate(
        self,
        messages: list[dict[str, Any]],
        model: str,
        *,
        config: Optional[GenerationConfig] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        system: str = "",
    ) -> GenerationResult:
        """Synchronous generation."""

    @abstractmethod
    async def agenerate(
        self,
        messages: list[dict[str, Any]],
        model: str,
        *,
        config: Optional[GenerationConfig] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        system: str = "",
    ) -> GenerationResult:
        """Async generation."""

    @abstractmethod
    def stream(
        self,
        messages: list[dict[str, Any]],
        model: str,
        *,
        config: Optional[GenerationConfig] = None,
        system: str = "",
    ) -> Any:
        """Return a streaming iterator of text chunks."""

    @abstractmethod
    def list_models(self) -> list[ModelSpec]:
        """List available models on this engine."""

    @abstractmethod
    def health(self) -> bool:
        """Return True if the engine is reachable and healthy."""
