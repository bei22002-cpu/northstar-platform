"""BaseAgent ABC — all agents implement this interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from agent_v5.engine.base import InferenceEngine
from agent_v5.types import GenerationConfig


@dataclass(slots=True)
class AgentResult:
    """Result of an agent run."""

    text: str
    tool_calls_made: list[str] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    turns: int = 1
    model: str = ""


@dataclass
class AgentContext:
    """Shared context passed into agent runs."""

    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    system_prompt: str = ""
    memory_context: str = ""


class BaseAgent(ABC):
    """Abstract base for all agent implementations."""

    agent_id: str = ""
    accepts_tools: bool = False

    def __init__(
        self,
        engine: InferenceEngine,
        model: str,
        *,
        config: Optional[GenerationConfig] = None,
    ) -> None:
        self.engine = engine
        self.model = model
        self.config = config or GenerationConfig()

    @abstractmethod
    def run(
        self,
        user_input: str,
        context: Optional[AgentContext] = None,
        **kwargs: Any,
    ) -> AgentResult:
        """Execute the agent on *user_input* and return an AgentResult."""

    def _build_messages(
        self,
        user_input: str,
        context: Optional[AgentContext] = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Assemble system prompt and message list."""
        system = ""
        messages: list[dict[str, Any]] = []

        if context:
            system = context.system_prompt
            if context.memory_context:
                system += f"\n\n## Relevant Context\n{context.memory_context}"
            messages.extend(context.conversation_history)

        messages.append({"role": "user", "content": user_input})
        return system, messages
