"""API server — OpenAI-compatible /v1/chat/completions endpoint."""

from agent_v5.server.api import create_app

__all__ = ["create_app"]
