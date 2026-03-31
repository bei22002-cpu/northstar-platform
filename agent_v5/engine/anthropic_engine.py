"""Anthropic inference engine — Claude API backend with key rotation."""

from __future__ import annotations

import time
from typing import Any, Iterator, Optional

from agent_v5.engine.base import InferenceEngine
from agent_v5.registry import EngineRegistry
from agent_v5.types import GenerationConfig, GenerationResult, ModelSpec

# Pricing per million tokens (USD)
_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-5": (15.0, 75.0),
    "claude-sonnet-4-20250514": (3.0, 15.0),
    "claude-haiku-35-20241022": (0.25, 1.25),
}


@EngineRegistry.register("anthropic")
class AnthropicEngine(InferenceEngine):
    """Inference engine backed by the Anthropic Messages API with key rotation."""

    engine_id = "anthropic"

    def __init__(self, api_keys: list[str]) -> None:
        if not api_keys:
            raise ValueError("At least one Anthropic API key is required")
        self._keys = api_keys
        self._current = 0
        self._dead: set[int] = set()
        self._clients: dict[int, Any] = {}

    def _get_client(self) -> Any:
        import anthropic

        idx = self._current
        if idx not in self._clients:
            self._clients[idx] = anthropic.Anthropic(api_key=self._keys[idx])
        return self._clients[idx]

    def _rotate(self) -> bool:
        """Advance to the next live key.  Returns False if none left."""
        start = self._current
        for _ in range(len(self._keys)):
            self._current = (self._current + 1) % len(self._keys)
            if self._current not in self._dead:
                return True
            if self._current == start:
                break
        return False

    def _call(
        self,
        messages: list[dict[str, Any]],
        model: str,
        config: GenerationConfig,
        tools: Optional[list[dict[str, Any]]],
        system: str,
    ) -> Any:
        import anthropic

        for attempt in range(len(self._keys)):
            client = self._get_client()
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": config.max_tokens,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system
            if tools:
                kwargs["tools"] = tools
            if config.temperature != 0.7:
                kwargs["temperature"] = config.temperature

            try:
                return client.messages.create(**kwargs)
            except anthropic.AuthenticationError:
                self._dead.add(self._current)
                if not self._rotate():
                    raise
            except anthropic.RateLimitError:
                if not self._rotate():
                    raise
            except anthropic.BadRequestError:
                raise  # Don't retry bad requests

        raise RuntimeError("All API keys exhausted")

    def generate(
        self,
        messages: list[dict[str, Any]],
        model: str,
        *,
        config: Optional[GenerationConfig] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        system: str = "",
    ) -> GenerationResult:
        cfg = config or GenerationConfig()
        t0 = time.time()

        resp = self._call(messages, model, cfg, tools, system)

        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for block in resp.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
            elif getattr(block, "type", None) == "tool_use":
                tool_calls.append(
                    {"id": block.id, "name": block.name, "arguments": block.input}
                )

        latency = (time.time() - t0) * 1000
        return GenerationResult(
            text="\n".join(text_parts),
            model=model,
            tokens_in=getattr(resp.usage, "input_tokens", 0),
            tokens_out=getattr(resp.usage, "output_tokens", 0),
            latency_ms=latency,
            finish_reason=resp.stop_reason or "stop",
            tool_calls=tool_calls if tool_calls else None,
        )

    async def agenerate(
        self,
        messages: list[dict[str, Any]],
        model: str,
        *,
        config: Optional[GenerationConfig] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        system: str = "",
    ) -> GenerationResult:
        return self.generate(
            messages, model, config=config, tools=tools, system=system
        )

    def stream(
        self,
        messages: list[dict[str, Any]],
        model: str,
        *,
        config: Optional[GenerationConfig] = None,
        system: str = "",
    ) -> Iterator[str]:
        import anthropic

        cfg = config or GenerationConfig()
        client = self._get_client()
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": cfg.max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        with client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text

    def list_models(self) -> list[ModelSpec]:
        return [
            ModelSpec(
                name="claude-opus-4-5",
                provider="anthropic",
                supports_tools=True,
                supports_streaming=True,
                context_length=200000,
            ),
            ModelSpec(
                name="claude-sonnet-4-20250514",
                provider="anthropic",
                supports_tools=True,
                supports_streaming=True,
                context_length=200000,
            ),
            ModelSpec(
                name="claude-haiku-35-20241022",
                provider="anthropic",
                supports_tools=True,
                supports_streaming=True,
                context_length=200000,
            ),
        ]

    def health(self) -> bool:
        return len(self._dead) < len(self._keys)

    def estimate_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        """Estimate cost in USD."""
        prices = _PRICING.get(model, (3.0, 15.0))
        return (tokens_in * prices[0] + tokens_out * prices[1]) / 1_000_000

    @property
    def active_key_index(self) -> int:
        return self._current + 1

    @property
    def total_keys(self) -> int:
        return len(self._keys)

    @property
    def live_keys(self) -> int:
        return len(self._keys) - len(self._dead)
