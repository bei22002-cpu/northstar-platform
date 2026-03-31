"""Ollama inference engine — local model execution."""

from __future__ import annotations

import json
import time
from typing import Any, Iterator, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from agent_v5.engine.base import InferenceEngine
from agent_v5.registry import EngineRegistry
from agent_v5.types import GenerationConfig, GenerationResult, ModelSpec


@EngineRegistry.register("ollama")
class OllamaEngine(InferenceEngine):
    """Inference engine backed by a local Ollama server."""

    engine_id = "ollama"

    def __init__(self, host: str = "http://localhost:11434") -> None:
        self._host = host.rstrip("/")

    # ── helpers ───────────────────────────────────────────────────────

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body).encode()
        req = Request(
            f"{self._host}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())

    def _get(self, path: str) -> dict[str, Any]:
        req = Request(f"{self._host}{path}", method="GET")
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    @staticmethod
    def _messages_to_ollama(
        messages: list[dict[str, Any]], system: str = ""
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if system:
            out.append({"role": "system", "content": system})
        for m in messages:
            out.append({"role": m["role"], "content": m.get("content", "")})
        return out

    # ── InferenceEngine interface ─────────────────────────────────────

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

        body: dict[str, Any] = {
            "model": model,
            "messages": self._messages_to_ollama(messages, system),
            "stream": False,
            "options": {
                "temperature": cfg.temperature,
                "num_predict": cfg.max_tokens,
                "top_p": cfg.top_p,
            },
        }
        if tools:
            body["tools"] = tools

        resp = self._post("/api/chat", body)
        msg = resp.get("message", {})
        text = msg.get("content", "")
        tool_calls = msg.get("tool_calls")

        latency = (time.time() - t0) * 1000
        tokens_in = resp.get("prompt_eval_count", 0)
        tokens_out = resp.get("eval_count", 0)

        return GenerationResult(
            text=text,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency,
            finish_reason="tool_calls" if tool_calls else "stop",
            tool_calls=tool_calls,
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
        # Ollama's HTTP API is blocking; wrap in sync call
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
        cfg = config or GenerationConfig()
        body: dict[str, Any] = {
            "model": model,
            "messages": self._messages_to_ollama(messages, system),
            "stream": True,
            "options": {
                "temperature": cfg.temperature,
                "num_predict": cfg.max_tokens,
                "top_p": cfg.top_p,
            },
        }
        data = json.dumps(body).encode()
        req = Request(
            f"{self._host}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=120) as resp:
            for line in resp:
                if line.strip():
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token

    def list_models(self) -> list[ModelSpec]:
        try:
            resp = self._get("/api/tags")
        except (URLError, OSError):
            return []
        models: list[ModelSpec] = []
        for m in resp.get("models", []):
            name = m.get("name", "")
            size_bytes = m.get("size", 0)
            params_b = round(size_bytes / 1e9, 1) if size_bytes else 0.0
            models.append(
                ModelSpec(
                    name=name,
                    provider="ollama",
                    params_b=params_b,
                    supports_tools=True,
                    supports_streaming=True,
                )
            )
        return models

    def health(self) -> bool:
        try:
            self._get("/api/tags")
            return True
        except (URLError, OSError):
            return False
