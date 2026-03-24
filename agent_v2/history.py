"""Session history management for the Cornerstone AI Agent v2."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any


class SessionHistory:
    """Stores all messages for a single agent session."""

    def __init__(self) -> None:
        self._messages: list[dict[str, Any]] = []

    # -- public API ----------------------------------------------------------

    def add_user(self, message: str) -> None:
        """Append a user message."""
        self._messages.append({"role": "user", "content": message})

    def add_assistant(self, content: Any) -> None:
        """Append an assistant message.

        *content* can be a plain string or the raw content list returned by the
        Anthropic API.
        """
        if isinstance(content, str):
            self._messages.append({"role": "assistant", "content": content})
        else:
            # Store the raw content blocks (text + tool_use) as-is
            serializable = _make_serializable(content)
            self._messages.append({"role": "assistant", "content": serializable})

    def add_tool_results(self, results: list[dict[str, Any]]) -> None:
        """Append a user message containing tool results."""
        self._messages.append({"role": "user", "content": results})

    def get_messages(self) -> list[dict[str, Any]]:
        """Return the full message history."""
        return list(self._messages)

    def clear(self) -> None:
        """Reset history for a new session."""
        self._messages.clear()

    def save(self) -> str:
        """Persist the session to a JSON file and return the file path."""
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        filepath = os.path.join(log_dir, f"session_{timestamp}.json")
        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(self._messages, fh, indent=2, default=str)
        return filepath


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_serializable(obj: Any) -> Any:
    """Recursively convert API objects to plain dicts/lists for JSON."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_make_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    return obj
