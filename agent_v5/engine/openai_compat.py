"""OpenAI-compatible inference engine — works with OpenAI, vLLM, SGLang, etc."""

from __future__ import annotations

import json
import time
from typing import Any, Iterator, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from agent_v5.engine.base import InferenceEngine
from agent_v5.registry import EngineRegistry
from agent_v5.types import GenerationConfig, GenerationResult, ModelSpec


@EngineRegistry.register("openai")
class OpenAICompatEngine(InferenceEngine):
    """Engine for any OpenAI-compatible API (OpenAI, vLLM, SGLang, LM Studio)."""

    engine_id = "openai"

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1") -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body).encode()
        req = Request(
            f"{self._base_url}{path}",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        with urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())

    def _get(self, path: str) -> dict[str, Any]:
        req = Request(
            f"{self._base_url}{path}",
            headers={"Authorization": f"Bearer {self._api_key}"},
            method="GET",
        )
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

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

        msgs = list(messages)
        if system:
            msgs.insert(0, {"role": "system", "content": system})

        body: dict[str, Any] = {
            "model": model,
            "messages": msgs,
            "max_tokens": cfg.max_tokens,
            "temperature": cfg.temperature,
            "top_p": cfg.top_p,
        }
        if tools:
            body["tools"] = tools
        if cfg.stop_sequences:
            body["stop"] = cfg.stop_sequences

        resp = self._post("/chat/completions", body)
        choice = resp.get("choices", [{}])[0]
        msg = choice.get("message", {})
        text = msg.get("content", "") or ""
        tool_calls_raw = msg.get("tool_calls")

        tool_calls = None
        if tool_calls_raw:
            tool_calls = []
            for tc in tool_calls_raw:
                fn = tc.get("function", {})
                args = fn.get("arguments", "{}")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"raw": args}
                tool_calls.append(
                    {"id": tc.get("id", ""), "name": fn.get("name", ""), "arguments": args}
                )

        usage = resp.get("usage", {})
        latency = (time.time() - t0) * 1000

        return GenerationResult(
            text=text,
            model=model,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            latency_ms=latency,
            finish_reason=choice.get("finish_reason", "stop"),
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
        msgs = list(messages)
        if system:
            msgs.insert(0, {"role": "system", "content": system})

        body: dict[str, Any] = {
            "model": model,
            "messages": msgs,
            "max_tokens": cfg.max_tokens,
            "temperature": cfg.temperature,
            "stream": True,
        }
        data = json.dumps(body).encode()
        req = Request(
            f"{self._base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        with urlopen(req, timeout=120) as resp:
            for line in resp:
                line_str = line.decode().strip()
                if not line_str or not line_str.startswith("data:"):
                    continue
                payload = line_str[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        yield token
                except json.JSONDecodeError:
                    continue

    def list_models(self) -> list[ModelSpec]:
        try:
            resp = self._get("/models")
        except (URLError, OSError):
            return []
        models: list[ModelSpec] = []
        for m in resp.get("data", []):
            models.append(
                ModelSpec(
                    name=m.get("id", ""),
                    provider="openai",
                    supports_tools=True,
                    supports_streaming=True,
                )
            )
        return models

    def health(self) -> bool:
        try:
            self._get("/models")
            return True
        except (URLError, OSError):
            return False
