"""Multi-provider support — Claude, OpenClaw Zero Token, Ollama, and Gemini.

Provides a unified interface so the agent can seamlessly switch between:
- **Claude** (Anthropic API) — default, paid
- **OpenClaw Zero Token** — FREE, uses browser sessions (Claude/ChatGPT/Gemini/DeepSeek/etc.)
- **Ollama** (local) — free, runs on your machine
- **Gemini** (Google) — free tier available

Each provider adapter wraps the provider's API and returns objects that
match the Anthropic ``Message`` response shape so the rest of the agent
code (session.py, kairos.py, etc.) works without changes.

Usage:
    Set PROVIDER=openclaw in .env for free access via OpenClaw Zero Token.
    Set PROVIDER=ollama or PROVIDER=gemini for other free options.
    Default is claude (uses existing TokenManager).
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console

console = Console()

# ---------------------------------------------------------------------------
# Response shims — mimic anthropic.types.Message shape
# ---------------------------------------------------------------------------


@dataclass
class TextBlock:
    """Mimics anthropic.types.TextBlock."""
    type: str = "text"
    text: str = ""


@dataclass
class ToolUseBlock:
    """Mimics anthropic.types.ToolUseBlock."""
    type: str = "tool_use"
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class ShimMessage:
    """Mimics anthropic.types.Message — enough for session.py/kairos.py."""
    id: str = ""
    type: str = "message"
    role: str = "assistant"
    content: list[Any] = field(default_factory=list)
    model: str = ""
    stop_reason: str | None = "end_turn"
    usage: dict[str, int] = field(default_factory=lambda: {
        "input_tokens": 0, "output_tokens": 0
    })


# ---------------------------------------------------------------------------
# OpenClaw Zero Token provider
# ---------------------------------------------------------------------------

class OpenClawProvider:
    """Calls an OpenClaw gateway for FREE AI model access.

    OpenClaw lets you use Claude, ChatGPT, Gemini, DeepSeek, Qwen, Doubao,
    Kimi, Grok, and more — completely free. It works by driving the official
    web UIs via browser login instead of paid API keys.

    Setup:
        1. Clone: git clone https://github.com/linuxhsj/openclaw-zero-token
        2. Install: cd openclaw-zero-token && pnpm install
        3. Setup:  npx openclaw setup
        4. Start:  npx openclaw gateway
        5. The gateway runs at http://localhost:18789 by default

    The gateway exposes an OpenAI-compatible API at /v1/chat/completions
    on the same port as the WebSocket control plane.
    """

    DEFAULT_BASE_URL = "http://localhost:18789"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        token: str | None = None,
    ) -> None:
        self.base_url = base_url or os.getenv(
            "OPENCLAW_BASE_URL", self.DEFAULT_BASE_URL
        )
        self.model = model or os.getenv("OPENCLAW_MODEL", self.DEFAULT_MODEL)
        self.token = token or os.getenv("OPENCLAW_TOKEN", "")
        self._call_count = 0
        self._errors = 0
        console.print(
            f"[dim]OpenClawProvider initialised — model={self.model}, "
            f"gateway={self.base_url}[/dim]"
        )

    @property
    def active_key_index(self) -> int:
        return 1

    @property
    def total_keys(self) -> int:
        return 1

    def get_stats(self) -> list[dict[str, Any]]:
        return [{
            "key_number": 1,
            "masked_key": f"openclaw/{self.model}",
            "calls": self._call_count,
            "errors": self._errors,
            "rate_limited": False,
            "cooldown_remaining": 0,
        }]

    def create_message(self, **kwargs: Any) -> ShimMessage:
        """Send a chat request via OpenClaw Zero Token gateway.

        The gateway exposes an OpenAI-compatible /v1/chat/completions
        endpoint, so we translate Anthropic-style kwargs to OpenAI format.
        """
        import urllib.request
        import urllib.error

        system = kwargs.get("system", "")
        messages = kwargs.get("messages", [])
        tools = kwargs.get("tools", [])
        max_tokens = kwargs.get("max_tokens", 4096)

        # Build OpenAI-format messages
        oai_messages: list[dict[str, Any]] = []
        if system:
            oai_messages.append({"role": "system", "content": system})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if isinstance(content, str):
                oai_messages.append({"role": role, "content": content})
            elif isinstance(content, list):
                text_parts: list[str] = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_result":
                            text_parts.append(
                                f"[Tool result for {block.get('tool_use_id', '?')}]: "
                                f"{block.get('content', '')}"
                            )
                        elif block.get("type") == "tool_use":
                            text_parts.append(
                                f"[Calling tool {block.get('name', '?')}]"
                            )
                    elif hasattr(block, "text"):
                        text_parts.append(block.text)
                    elif hasattr(block, "type") and block.type == "tool_use":
                        text_parts.append(f"[Calling tool {block.name}]")
                if text_parts:
                    oai_messages.append({
                        "role": role,
                        "content": "\n".join(text_parts),
                    })

        # Convert Anthropic tool schema to OpenAI function format
        oai_tools: list[dict[str, Any]] = []
        for tool in tools:
            oai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                },
            })

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": oai_messages,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if oai_tools:
            payload["tools"] = oai_tools

        data = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url}/v1/chat/completions"

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            self._errors += 1
            error_body = exc.read().decode("utf-8") if exc.fp else ""
            raise RuntimeError(
                f"OpenClaw gateway error {exc.code}: {error_body}\n"
                f"Make sure the gateway is running at {self.base_url} "
                f"and you're logged into a provider."
            ) from exc
        except urllib.error.URLError as exc:
            self._errors += 1
            raise ConnectionError(
                f"Cannot connect to OpenClaw gateway at {self.base_url}.\n"
                f"Setup: git clone https://github.com/linuxhsj/openclaw-zero-token\n"
                f"       cd openclaw-zero-token && pnpm install\n"
                f"       npx openclaw setup && npx openclaw gateway\n"
                f"Error: {exc}"
            ) from exc

        self._call_count += 1

        # Parse OpenAI-format response
        choices = body.get("choices", [])
        if not choices:
            return ShimMessage(
                id=body.get("id", f"openclaw-{self._call_count}"),
                content=[TextBlock(text="(empty response from OpenClaw gateway)")],
                model=self.model,
                stop_reason="end_turn",
            )

        choice = choices[0]
        message = choice.get("message", {})
        content_text = message.get("content", "") or ""
        tool_calls = message.get("tool_calls", [])
        finish_reason = choice.get("finish_reason", "stop")

        blocks: list[Any] = []
        stop_reason = "end_turn"

        if tool_calls:
            stop_reason = "tool_use"
            for i, tc in enumerate(tool_calls):
                fn = tc.get("function", {})
                args = fn.get("arguments", "{}")
                blocks.append(ToolUseBlock(
                    type="tool_use",
                    id=tc.get("id", f"openclaw_tool_{self._call_count}_{i}"),
                    name=fn.get("name", ""),
                    input=json.loads(args) if isinstance(args, str) else args,
                ))

        if content_text:
            # Check for text-based tool calls (some models do this)
            extracted_tool = _extract_tool_call_from_text(content_text, tools)
            if extracted_tool and not tool_calls:
                stop_reason = "tool_use"
                blocks.append(extracted_tool)
                clean_text = _clean_tool_text(content_text)
                if clean_text.strip():
                    blocks.insert(0, TextBlock(text=clean_text))
            else:
                blocks.append(TextBlock(text=content_text))

        if not blocks:
            blocks.append(TextBlock(text="(no content)"))

        return ShimMessage(
            id=body.get("id", f"openclaw-{self._call_count}"),
            content=blocks,
            model=body.get("model", self.model),
            stop_reason=stop_reason,
        )


# ---------------------------------------------------------------------------
# Ollama provider
# ---------------------------------------------------------------------------

class OllamaProvider:
    """Calls a local Ollama instance for chat completions with tool use.

    Ollama exposes an OpenAI-compatible API at http://localhost:11434.
    We use the /api/chat endpoint which supports tool calling.

    Install: https://ollama.com/download
    Start:   ollama serve
    Pull:    ollama pull llama3.1:8b
    """

    DEFAULT_MODEL = "llama3.1:8b"
    DEFAULT_BASE_URL = "http://localhost:11434"

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model or os.getenv("OLLAMA_MODEL", self.DEFAULT_MODEL)
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", self.DEFAULT_BASE_URL)
        self._call_count = 0
        console.print(
            f"[dim]OllamaProvider initialised — model={self.model}, "
            f"url={self.base_url}[/dim]"
        )

    @property
    def active_key_index(self) -> int:
        return 1

    @property
    def total_keys(self) -> int:
        return 1

    def get_stats(self) -> list[dict[str, Any]]:
        return [{
            "key_number": 1,
            "masked_key": f"ollama/{self.model}",
            "calls": self._call_count,
            "errors": 0,
            "rate_limited": False,
            "cooldown_remaining": 0,
        }]

    def create_message(self, **kwargs: Any) -> ShimMessage:
        """Send a chat request to Ollama and return a ShimMessage.

        Accepts the same kwargs as Anthropic's messages.create but
        translates them to Ollama's format.
        """
        import urllib.request
        import urllib.error

        model = kwargs.get("model", self.model)
        # For Ollama, always use the configured local model
        if model.startswith("claude"):
            model = self.model

        system = kwargs.get("system", "")
        messages = kwargs.get("messages", [])
        tools = kwargs.get("tools", [])

        # Build Ollama messages
        ollama_messages: list[dict[str, Any]] = []
        if system:
            ollama_messages.append({"role": "system", "content": system})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if isinstance(content, str):
                ollama_messages.append({"role": role, "content": content})
            elif isinstance(content, list):
                # Handle Anthropic-style content blocks
                text_parts: list[str] = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_result":
                            text_parts.append(
                                f"[Tool result for {block.get('tool_use_id', '?')}]: "
                                f"{block.get('content', '')}"
                            )
                        elif block.get("type") == "tool_use":
                            text_parts.append(
                                f"[Calling tool {block.get('name', '?')}]"
                            )
                    elif hasattr(block, "text"):
                        text_parts.append(block.text)
                    elif hasattr(block, "type") and block.type == "tool_use":
                        text_parts.append(f"[Calling tool {block.name}]")
                if text_parts:
                    ollama_messages.append({
                        "role": role,
                        "content": "\n".join(text_parts),
                    })

        # Convert Anthropic tool schema to Ollama format
        ollama_tools: list[dict[str, Any]] = []
        for tool in tools:
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                },
            })

        payload: dict[str, Any] = {
            "model": model,
            "messages": ollama_messages,
            "stream": False,
        }
        if ollama_tools:
            payload["tools"] = ollama_tools

        data = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url}/api/chat"

        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            self._errors += 1
            error_body = exc.read().decode("utf-8") if exc.fp else ""
            if exc.code == 404:
                raise RuntimeError(
                    f"Ollama returned 404. The model '{model}' may not be "
                    f"pulled yet.\nRun: ollama pull {model}\n"
                    f"Or your Ollama version may be too old — update at "
                    f"https://ollama.com/download\nResponse: {error_body}"
                ) from exc
            raise RuntimeError(
                f"Ollama error {exc.code}: {error_body}"
            ) from exc
        except urllib.error.URLError as exc:
            self._errors += 1
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running (ollama serve). Error: {exc}"
            ) from exc

        self._call_count += 1

        # Parse response
        msg = body.get("message", {})
        content_text = msg.get("content", "")
        tool_calls = msg.get("tool_calls", [])

        blocks: list[Any] = []
        stop_reason = "end_turn"

        if tool_calls:
            stop_reason = "tool_use"
            for i, tc in enumerate(tool_calls):
                fn = tc.get("function", {})
                blocks.append(ToolUseBlock(
                    type="tool_use",
                    id=f"ollama_tool_{self._call_count}_{i}",
                    name=fn.get("name", ""),
                    input=fn.get("arguments", {}) if isinstance(fn.get("arguments"), dict)
                    else _parse_json_safe(fn.get("arguments", "{}")),
                ))

        if content_text:
            # Check if the model is trying to use tools via text (common with smaller models)
            extracted_tool = _extract_tool_call_from_text(content_text, tools)
            if extracted_tool and not tool_calls:
                stop_reason = "tool_use"
                blocks.append(extracted_tool)
                # Remove the tool call portion from text
                clean_text = _clean_tool_text(content_text)
                if clean_text.strip():
                    blocks.insert(0, TextBlock(text=clean_text))
            else:
                blocks.append(TextBlock(text=content_text))

        return ShimMessage(
            id=f"ollama-{self._call_count}",
            content=blocks,
            model=model,
            stop_reason=stop_reason,
        )


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

class GeminiProvider:
    """Calls Google's Gemini API for chat completions.

    Free tier: 15 requests/minute with Gemini 1.5 Flash.
    Get API key: https://aistudio.google.com/app/apikey

    Set GEMINI_API_KEY in .env.
    """

    DEFAULT_MODEL = "gemini-2.0-flash"
    API_BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", self.DEFAULT_MODEL)
        self._call_count = 0
        self._errors = 0

        if not self.api_key:
            console.print(
                "[yellow]Warning: GEMINI_API_KEY not set. "
                "Get one free at https://aistudio.google.com/app/apikey[/yellow]"
            )
        else:
            console.print(
                f"[dim]GeminiProvider initialised — model={self.model}[/dim]"
            )

    @property
    def active_key_index(self) -> int:
        return 1

    @property
    def total_keys(self) -> int:
        return 1

    def get_stats(self) -> list[dict[str, Any]]:
        masked = self.api_key[:8] + "..." + self.api_key[-4:] if self.api_key else "NOT SET"
        return [{
            "key_number": 1,
            "masked_key": f"gemini/{masked}",
            "calls": self._call_count,
            "errors": self._errors,
            "rate_limited": False,
            "cooldown_remaining": 0,
        }]

    def create_message(self, **kwargs: Any) -> ShimMessage:
        """Send a chat request to Gemini and return a ShimMessage."""
        import urllib.request
        import urllib.error

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Get a free key at "
                "https://aistudio.google.com/app/apikey and add it to .env"
            )

        system = kwargs.get("system", "")
        messages = kwargs.get("messages", [])
        tools = kwargs.get("tools", [])
        max_tokens = kwargs.get("max_tokens", 4096)

        # Build Gemini contents
        contents: list[dict[str, Any]] = []
        for msg in messages:
            role = "user" if msg.get("role") == "user" else "model"
            content = msg.get("content", "")

            if isinstance(content, str):
                contents.append({
                    "role": role,
                    "parts": [{"text": content}],
                })
            elif isinstance(content, list):
                text_parts: list[str] = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_result":
                            text_parts.append(
                                f"[Tool result]: {block.get('content', '')}"
                            )
                    elif hasattr(block, "text"):
                        text_parts.append(block.text)
                if text_parts:
                    contents.append({
                        "role": role,
                        "parts": [{"text": "\n".join(text_parts)}],
                    })

        # Build Gemini tool declarations
        gemini_tools: list[dict[str, Any]] = []
        if tools:
            function_declarations: list[dict[str, Any]] = []
            for tool in tools:
                schema = tool.get("input_schema", {})
                # Gemini doesn't support 'required' at the top level the same way
                params = {
                    "type": schema.get("type", "object"),
                    "properties": schema.get("properties", {}),
                }
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": params,
                })
            gemini_tools = [{"function_declarations": function_declarations}]

        # System instruction
        system_instruction = None
        if system:
            system_instruction = {"parts": [{"text": system}]}

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.7,
            },
        }
        if system_instruction:
            payload["system_instruction"] = system_instruction
        if gemini_tools:
            payload["tools"] = gemini_tools

        url = (
            f"{self.API_BASE}/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            self._errors += 1
            error_body = exc.read().decode("utf-8") if exc.fp else ""
            raise RuntimeError(
                f"Gemini API error {exc.code}: {error_body}"
            ) from exc
        except urllib.error.URLError as exc:
            self._errors += 1
            raise ConnectionError(
                f"Cannot connect to Gemini API: {exc}"
            ) from exc

        self._call_count += 1

        # Parse Gemini response
        candidates = body.get("candidates", [])
        if not candidates:
            return ShimMessage(
                id=f"gemini-{self._call_count}",
                content=[TextBlock(text="(empty response from Gemini)")],
                model=self.model,
                stop_reason="end_turn",
            )

        parts = candidates[0].get("content", {}).get("parts", [])
        blocks: list[Any] = []
        stop_reason = "end_turn"

        for part in parts:
            if "text" in part:
                blocks.append(TextBlock(text=part["text"]))
            elif "functionCall" in part:
                fc = part["functionCall"]
                stop_reason = "tool_use"
                blocks.append(ToolUseBlock(
                    type="tool_use",
                    id=f"gemini_tool_{self._call_count}_{len(blocks)}",
                    name=fc.get("name", ""),
                    input=fc.get("args", {}),
                ))

        if not blocks:
            blocks.append(TextBlock(text="(no content in Gemini response)"))

        return ShimMessage(
            id=f"gemini-{self._call_count}",
            content=blocks,
            model=self.model,
            stop_reason=stop_reason,
        )


# ---------------------------------------------------------------------------
# Free multi-provider (chains Groq + Gemini + Cerebras + GitHub Models)
# ---------------------------------------------------------------------------

class FreeMultiProvider:
    """Chains multiple free-tier LLM APIs with automatic failover.

    Inspired by github.com/msmarkgu/RelayFreeLLM and
    github.com/TheSecondChance/freeflow-llm — but built directly into
    the agent with zero extra dependencies.

    Supported free providers (in priority order):
        1. Groq       — 30 req/min free, very fast (Llama, Mixtral)
                         Key: https://console.groq.com/keys
        2. Gemini     — 15 req/min free (Gemini Flash)
                         Key: https://aistudio.google.com/app/apikey
        3. Cerebras   — fast free tier (Llama)
                         Key: https://cloud.cerebras.ai/
        4. GitHub     — free with any GitHub token (GPT-4o, Llama, etc.)
                         Token: https://github.com/settings/tokens

    Set as many keys as you have — the provider will use all of them and
    automatically switch when one hits a rate limit.
    """

    # Provider configs: (env_key, base_url, default_model, name)
    PROVIDERS = [
        ("GROQ_API_KEY", "https://api.groq.com/openai/v1", "llama-3.1-70b-versatile", "Groq"),
        ("GEMINI_API_KEY", None, "gemini-2.0-flash", "Gemini"),  # Gemini uses its own API
        ("CEREBRAS_API_KEY", "https://api.cerebras.ai/v1", "llama3.1-70b", "Cerebras"),
        ("GITHUB_TOKEN", "https://models.inference.ai.azure.com", "gpt-4o", "GitHub Models"),
    ]

    def __init__(self) -> None:
        self._providers: list[dict[str, Any]] = []
        self._current_idx = 0
        self._call_count = 0
        self._errors = 0

        # Discover available free providers from env vars
        for env_key, base_url, default_model, name in self.PROVIDERS:
            key = os.getenv(env_key, "")
            if key:
                if name == "Gemini":
                    # Gemini uses its own provider internally
                    self._providers.append({
                        "name": name,
                        "type": "gemini",
                        "key": key,
                        "model": os.getenv("GEMINI_MODEL", default_model),
                    })
                else:
                    self._providers.append({
                        "name": name,
                        "type": "openai",
                        "key": key,
                        "base_url": base_url,
                        "model": default_model,
                    })

        if not self._providers:
            console.print(
                "[bold red]No free API keys found![/bold red]\n"
                "Set at least one of these in agent_v2/.env:\n"
                "  GROQ_API_KEY=...      (https://console.groq.com/keys)\n"
                "  GEMINI_API_KEY=...    (https://aistudio.google.com/app/apikey)\n"
                "  CEREBRAS_API_KEY=...  (https://cloud.cerebras.ai/)\n"
                "  GITHUB_TOKEN=...      (https://github.com/settings/tokens)\n"
            )
            raise SystemExit(1)

        names = ", ".join(p["name"] for p in self._providers)
        console.print(
            f"[dim]FreeMultiProvider initialised — {len(self._providers)} "
            f"provider(s): {names}[/dim]"
        )

    @property
    def active_key_index(self) -> int:
        return self._current_idx + 1

    @property
    def total_keys(self) -> int:
        return len(self._providers)

    def get_stats(self) -> list[dict[str, Any]]:
        stats = []
        for i, p in enumerate(self._providers):
            stats.append({
                "key_number": i + 1,
                "masked_key": f"{p['name']}/{p['model']}",
                "calls": self._call_count if i == self._current_idx else 0,
                "errors": 0,
                "rate_limited": False,
                "cooldown_remaining": 0,
            })
        return stats

    def create_message(self, **kwargs: Any) -> ShimMessage:
        """Try each provider in order; on rate limit or error, fail over."""
        import urllib.request
        import urllib.error

        last_error: Exception | None = None
        attempts = 0

        for _ in range(len(self._providers)):
            provider = self._providers[self._current_idx]
            attempts += 1

            try:
                if provider["type"] == "gemini":
                    return self._call_gemini(provider, **kwargs)
                else:
                    return self._call_openai_compat(provider, **kwargs)
            except Exception as exc:
                last_error = exc
                self._errors += 1
                error_str = str(exc)
                # Rate limit or server error — try next provider
                if "429" in error_str or "rate" in error_str.lower() or "quota" in error_str.lower() or "500" in error_str or "503" in error_str:
                    console.print(
                        f"[yellow]{provider['name']} rate limited, "
                        f"switching to next provider...[/yellow]"
                    )
                    self._current_idx = (self._current_idx + 1) % len(self._providers)
                    continue
                # Non-rate-limit error — still try next
                console.print(
                    f"[yellow]{provider['name']} error: {error_str[:100]}. "
                    f"Trying next provider...[/yellow]"
                )
                self._current_idx = (self._current_idx + 1) % len(self._providers)
                continue

        raise RuntimeError(
            f"All {len(self._providers)} free providers failed after "
            f"{attempts} attempts. Last error: {last_error}"
        )

    def _call_openai_compat(
        self, provider: dict[str, Any], **kwargs: Any
    ) -> ShimMessage:
        """Call an OpenAI-compatible API (Groq, Cerebras, GitHub Models)."""
        import urllib.request
        import urllib.error

        system = kwargs.get("system", "")
        messages = kwargs.get("messages", [])
        tools = kwargs.get("tools", [])
        max_tokens = kwargs.get("max_tokens", 4096)

        # Build OpenAI-format messages
        oai_messages: list[dict[str, Any]] = []
        if system:
            oai_messages.append({"role": "system", "content": system})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str):
                oai_messages.append({"role": role, "content": content})
            elif isinstance(content, list):
                text_parts: list[str] = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_result":
                            text_parts.append(
                                f"[Tool result for {block.get('tool_use_id', '?')}]: "
                                f"{block.get('content', '')}"
                            )
                        elif block.get("type") == "tool_use":
                            text_parts.append(f"[Calling tool {block.get('name', '?')}]")
                    elif hasattr(block, "text"):
                        text_parts.append(block.text)
                if text_parts:
                    oai_messages.append({"role": role, "content": "\n".join(text_parts)})

        # Convert tool schema
        oai_tools: list[dict[str, Any]] = []
        for tool in tools:
            oai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                },
            })

        payload: dict[str, Any] = {
            "model": provider["model"],
            "messages": oai_messages,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if oai_tools:
            payload["tools"] = oai_tools

        data = json.dumps(payload).encode("utf-8")
        url = f"{provider['base_url']}/chat/completions"

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {provider['key']}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        self._call_count += 1

        choices = body.get("choices", [])
        if not choices:
            return ShimMessage(
                id=body.get("id", f"free-{self._call_count}"),
                content=[TextBlock(text="(empty response)")],
                model=provider["model"],
                stop_reason="end_turn",
            )

        choice = choices[0]
        message = choice.get("message", {})
        content_text = message.get("content", "") or ""
        tool_calls = message.get("tool_calls", [])

        blocks: list[Any] = []
        stop_reason = "end_turn"

        if tool_calls:
            stop_reason = "tool_use"
            for i, tc in enumerate(tool_calls):
                fn = tc.get("function", {})
                args = fn.get("arguments", "{}")
                blocks.append(ToolUseBlock(
                    type="tool_use",
                    id=tc.get("id", f"free_tool_{self._call_count}_{i}"),
                    name=fn.get("name", ""),
                    input=json.loads(args) if isinstance(args, str) else args,
                ))

        if content_text:
            extracted_tool = _extract_tool_call_from_text(content_text, tools)
            if extracted_tool and not tool_calls:
                stop_reason = "tool_use"
                blocks.append(extracted_tool)
                clean_text = _clean_tool_text(content_text)
                if clean_text.strip():
                    blocks.insert(0, TextBlock(text=clean_text))
            else:
                blocks.append(TextBlock(text=content_text))

        if not blocks:
            blocks.append(TextBlock(text="(no content)"))

        return ShimMessage(
            id=body.get("id", f"free-{self._call_count}"),
            content=blocks,
            model=body.get("model", provider["model"]),
            stop_reason=stop_reason,
        )

    def _call_gemini(self, provider: dict[str, Any], **kwargs: Any) -> ShimMessage:
        """Call Google Gemini API (non-OpenAI format)."""
        import urllib.request
        import urllib.error

        system = kwargs.get("system", "")
        messages = kwargs.get("messages", [])
        tools = kwargs.get("tools", [])

        # Build Gemini contents
        contents: list[dict[str, Any]] = []
        for msg in messages:
            role = "user" if msg.get("role") == "user" else "model"
            content = msg.get("content", "")
            if isinstance(content, str):
                contents.append({"role": role, "parts": [{"text": content}]})
            elif isinstance(content, list):
                text_parts: list[str] = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_result":
                            text_parts.append(
                                f"[Tool result]: {block.get('content', '')}"
                            )
                    elif hasattr(block, "text"):
                        text_parts.append(block.text)
                if text_parts:
                    contents.append({
                        "role": role,
                        "parts": [{"text": "\n".join(text_parts)}],
                    })

        payload: dict[str, Any] = {"contents": contents}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        if tools:
            gemini_funcs = []
            for tool in tools:
                params = tool.get("input_schema", {})
                clean_params = {
                    k: v for k, v in params.items() if k != "additionalProperties"
                }
                gemini_funcs.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": clean_params,
                })
            payload["tools"] = [{"functionDeclarations": gemini_funcs}]

        model = provider["model"]
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model}:generateContent?key={provider['key']}"
        )
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        self._call_count += 1

        candidates = body.get("candidates", [])
        if not candidates:
            return ShimMessage(
                id=f"gemini-free-{self._call_count}",
                content=[TextBlock(text="(empty Gemini response)")],
                model=model,
                stop_reason="end_turn",
            )

        parts = candidates[0].get("content", {}).get("parts", [])
        blocks: list[Any] = []
        stop_reason = "end_turn"

        for part in parts:
            if "text" in part:
                blocks.append(TextBlock(text=part["text"]))
            elif "functionCall" in part:
                stop_reason = "tool_use"
                fc = part["functionCall"]
                blocks.append(ToolUseBlock(
                    type="tool_use",
                    id=f"gemini_free_{self._call_count}",
                    name=fc.get("name", ""),
                    input=fc.get("args", {}),
                ))

        if not blocks:
            blocks.append(TextBlock(text="(no content)"))

        return ShimMessage(
            id=f"gemini-free-{self._call_count}",
            content=blocks,
            model=model,
            stop_reason=stop_reason,
        )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _parse_json_safe(text: str) -> dict[str, Any]:
    """Try to parse JSON; return empty dict on failure."""
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _extract_tool_call_from_text(
    text: str, tools: list[dict[str, Any]]
) -> ToolUseBlock | None:
    """Try to extract a tool call from model text output.

    Smaller Ollama models sometimes output tool calls as text instead of
    using the native tool_call API.  This catches common patterns like:

        <tool_call>{"name": "write_file", "arguments": {...}}</tool_call>

    or:

        I'll use the write_file tool:
        ```json
        {"name": "write_file", "arguments": {"filepath": "...", "content": "..."}}
        ```
    """
    tool_names = {t["name"] for t in tools}

    # Pattern 1: <tool_call>JSON</tool_call>
    match = re.search(r"<tool_call>\s*(\{[\s\S]*?\})\s*</tool_call>", text)
    if match:
        data = _parse_json_safe(match.group(1))
        if data.get("name") in tool_names:
            return ToolUseBlock(
                type="tool_use",
                id=f"extracted_{int(time.time())}",
                name=data["name"],
                input=data.get("arguments", data.get("input", {})),
            )

    # Pattern 2: ```json { "name": "tool", ... } ```
    match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if match:
        data = _parse_json_safe(match.group(1))
        if data.get("name") in tool_names:
            return ToolUseBlock(
                type="tool_use",
                id=f"extracted_{int(time.time())}",
                name=data["name"],
                input=data.get("arguments", data.get("input", {})),
            )

    return None


def _clean_tool_text(text: str) -> str:
    """Remove tool call patterns from text, leaving natural language."""
    text = re.sub(r"<tool_call>[\s\S]*?</tool_call>", "", text)
    text = re.sub(r"```(?:json)?\s*\{[\s\S]*?\}\s*```", "", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

def get_provider(provider_name: str | None = None) -> Any:
    """Create and return the configured provider.

    If *provider_name* is not given, reads from PROVIDER env var.
    Returns a TokenManager (claude), OpenClawProvider, OllamaProvider,
    or GeminiProvider.

    All four expose the same interface:
        .create_message(**kwargs) -> Message-like
        .active_key_index -> int
        .total_keys -> int
        .get_stats() -> list[dict]
    """
    name = (provider_name or os.getenv("PROVIDER", "claude")).lower().strip()

    if name in ("claude", "anthropic"):
        # Use existing TokenManager
        from agent_v2.config import API_KEYS
        from agent_v2.token_manager import TokenManager
        return TokenManager(API_KEYS)

    if name in ("openclaw", "openclaw-zero-token", "zerotok"):
        return OpenClawProvider()

    if name == "ollama":
        return OllamaProvider()

    if name in ("gemini", "google"):
        return GeminiProvider()

    if name in ("free", "multi", "freemulti", "relay"):
        return FreeMultiProvider()

    console.print(
        f"[yellow]Unknown provider '{name}'. Falling back to Claude.[/yellow]"
    )
    from agent_v2.config import API_KEYS
    from agent_v2.token_manager import TokenManager
    return TokenManager(API_KEYS)


# Current active provider name (for display)
def get_provider_name() -> str:
    """Return the configured provider name."""
    return os.getenv("PROVIDER", "claude").lower().strip()
