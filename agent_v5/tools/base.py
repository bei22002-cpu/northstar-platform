"""BaseTool ABC — all tools implement this interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from agent_v5.registry import ToolRegistry


class BaseTool(ABC):
    """Abstract base for all tool implementations."""

    tool_id: str = ""
    description: str = ""

    @abstractmethod
    def execute(self, **kwargs: Any) -> str:
        """Execute the tool and return a string result."""

    @abstractmethod
    def to_definition(self) -> Dict[str, Any]:
        """Return the Anthropic-compatible tool definition."""
