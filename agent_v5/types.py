"""Core types used across all agent_v5 primitives."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(slots=True)
class Message:
    """A single chat message."""

    role: Role
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.name:
            d["name"] = self.name
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        return d


@dataclass(slots=True)
class ModelSpec:
    """Metadata for a known model."""

    name: str
    provider: str  # "ollama", "anthropic", "openai", etc.
    params_b: float = 0.0  # Parameter count in billions
    context_length: int = 4096
    vram_gb: float = 0.0
    supports_tools: bool = False
    supports_streaming: bool = True


@dataclass(slots=True)
class GenerationConfig:
    """Generation parameters for inference."""

    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    top_k: int = 0
    stop_sequences: list[str] = field(default_factory=list)
    stream: bool = False


@dataclass(slots=True)
class GenerationResult:
    """Result of a single generation call."""

    text: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    finish_reason: str = "stop"
    tool_calls: Optional[list[dict[str, Any]]] = None


@dataclass(slots=True)
class ToolCall:
    """A tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class ToolResult:
    """Result of executing a tool."""

    tool_call_id: str
    content: str
    is_error: bool = False


@dataclass(slots=True)
class RetrievalResult:
    """A single result from memory retrieval."""

    content: str
    score: float = 0.0
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Trace:
    """Captures the full sequence of an agent interaction."""

    trace_id: str
    query: str
    agent_type: str = ""
    engine_id: str = ""
    model: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    tool_calls: list[str] = field(default_factory=list)
    memory_hits: int = 0
    result: str = ""
    error: str = ""
    cost_usd: float = 0.0

    def finish(self, result: str = "", error: str = "") -> None:
        self.end_time = time.time()
        self.latency_ms = (self.end_time - self.start_time) * 1000
        self.result = result
        self.error = error


@dataclass(slots=True)
class HardwareInfo:
    """Detected hardware capabilities."""

    platform: str = ""
    cpu: str = ""
    cpu_cores: int = 0
    ram_gb: float = 0.0
    gpu_vendor: str = ""  # "nvidia", "amd", "apple", "none"
    gpu_name: str = ""
    vram_gb: float = 0.0
    has_gpu: bool = False
