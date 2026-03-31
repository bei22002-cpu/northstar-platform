"""FastAPI server — OpenAI-compatible /v1/chat/completions endpoint."""

from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from agent_v5.config import DEFAULT_ENGINE, DEFAULT_MODEL
from agent_v5.engine.discovery import get_engine
from agent_v5.types import GenerationConfig


def create_app() -> Any:
    """Create and return a FastAPI application with OpenAI-compatible endpoints."""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        from pydantic import BaseModel, Field
    except ImportError:
        raise ImportError(
            "FastAPI is required for the API server. "
            "Install with: pip install fastapi uvicorn"
        )

    app = FastAPI(
        title="Cornerstone AI — Jarvis Edition",
        description="OpenAI-compatible API server powered by Cornerstone AI Agent v5",
        version="5.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request/Response models ───────────────────────────────────────

    class ChatMessage(BaseModel):
        role: str
        content: str
        name: Optional[str] = None

    class ChatRequest(BaseModel):
        model: str = ""
        messages: list[ChatMessage]
        temperature: float = 0.7
        max_tokens: int = 4096
        top_p: float = 1.0
        stream: bool = False

    class Usage(BaseModel):
        prompt_tokens: int = 0
        completion_tokens: int = 0
        total_tokens: int = 0

    class Choice(BaseModel):
        index: int = 0
        message: ChatMessage
        finish_reason: str = "stop"

    class ChatResponse(BaseModel):
        id: str
        object: str = "chat.completion"
        created: int
        model: str
        choices: list[Choice]
        usage: Usage

    class ModelInfo(BaseModel):
        id: str
        object: str = "model"
        created: int = 0
        owned_by: str = ""

    class ModelsResponse(BaseModel):
        object: str = "list"
        data: list[ModelInfo]

    # ── Endpoints ─────────────────────────────────────────────────────

    @app.get("/v1/models")
    def list_models() -> ModelsResponse:
        engine = get_engine(DEFAULT_ENGINE)
        models = engine.list_models()
        return ModelsResponse(
            data=[
                ModelInfo(id=m.name, owned_by=m.provider)
                for m in models
            ]
        )

    @app.post("/v1/chat/completions")
    def chat_completions(req: ChatRequest) -> ChatResponse:
        engine = get_engine(DEFAULT_ENGINE)
        model = req.model or DEFAULT_MODEL

        messages = [{"role": m.role, "content": m.content} for m in req.messages]

        # Extract system message if present
        system = ""
        filtered: list[dict[str, Any]] = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                filtered.append(m)

        config = GenerationConfig(
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            top_p=req.top_p,
        )

        result = engine.generate(
            filtered, model, config=config, system=system
        )

        return ChatResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
            created=int(time.time()),
            model=model,
            choices=[
                Choice(
                    message=ChatMessage(role="assistant", content=result.text),
                    finish_reason=result.finish_reason,
                )
            ],
            usage=Usage(
                prompt_tokens=result.tokens_in,
                completion_tokens=result.tokens_out,
                total_tokens=result.tokens_in + result.tokens_out,
            ),
        )

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok", "version": "5.0.0"}

    return app


# Module-level app instance for `uvicorn agent_v5.server.api:app`
try:
    app = create_app()
except ImportError:
    app = None
