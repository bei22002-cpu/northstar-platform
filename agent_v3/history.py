"""Session history with persistent save/load support.

Sessions are stored as JSON in agent_v3/logs/ and can be resumed by
passing a session file path at startup.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any


class SessionHistory:
    """Stores all messages for a single agent session with persistence."""

    def __init__(self) -> None:
        self._messages: list[dict[str, Any]] = []
        self._session_file: str | None = None

    # -- public API ----------------------------------------------------------

    def add_user(self, message: str) -> None:
        """Append a user message."""
        self._messages.append({"role": "user", "content": message})

    def add_assistant(self, content: Any) -> None:
        """Append an assistant message."""
        if isinstance(content, str):
            self._messages.append({"role": "assistant", "content": content})
        else:
            serializable = _make_serializable(content)
            self._messages.append({"role": "assistant", "content": serializable})

    def add_tool_results(self, results: list[dict[str, Any]]) -> None:
        """Append a user message containing tool results."""
        self._messages.append({"role": "user", "content": results})

    def get_messages(self) -> list[dict[str, Any]]:
        """Return the full message history, sanitised for the API.

        Strips trailing assistant messages with orphaned tool_use blocks
        (no matching tool_result) to prevent 400 errors.
        """
        msgs = list(self._messages)
        while msgs:
            last = msgs[-1]
            if last["role"] == "assistant" and _has_tool_use(last.get("content")):
                msgs.pop()
                continue
            break
        return msgs

    def get_raw_messages(self) -> list[dict[str, Any]]:
        """Return full history without sanitisation (for saving)."""
        return list(self._messages)

    def clear(self) -> None:
        """Reset history."""
        self._messages.clear()

    @property
    def message_count(self) -> int:
        return len(self._messages)

    # -- persistence ---------------------------------------------------------

    def save(self) -> str:
        """Persist the session to a JSON file and return the path."""
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        filepath = os.path.join(log_dir, f"session_{timestamp}.json")
        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(self._messages, fh, indent=2, default=str)
        self._session_file = filepath
        return filepath

    def load(self, filepath: str) -> bool:
        """Load a previous session from a JSON file.

        Returns True on success, False on failure.
        """
        try:
            with open(filepath, encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, list):
                return False
            self._messages = data
            self._session_file = filepath
            return True
        except (json.JSONDecodeError, FileNotFoundError, OSError):
            return False

    def list_sessions(self) -> list[dict[str, str]]:
        """List all saved sessions with timestamp and path."""
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        if not os.path.isdir(log_dir):
            return []
        sessions: list[dict[str, str]] = []
        for fname in sorted(os.listdir(log_dir), reverse=True):
            if fname.startswith("session_") and fname.endswith(".json"):
                fpath = os.path.join(log_dir, fname)
                # Parse timestamp from filename
                ts = fname.replace("session_", "").replace(".json", "")
                ts_display = ts.replace("_", "-", 2).replace("_", ":", 2).replace("_", " ", 1)
                sessions.append({"timestamp": ts_display, "path": fpath, "filename": fname})
        return sessions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_tool_use(content: Any) -> bool:
    """Return True if *content* contains at least one tool_use block."""
    if not isinstance(content, list):
        return False
    return any(
        (isinstance(item, dict) and item.get("type") == "tool_use")
        for item in content
    )


def _make_serializable(obj: Any) -> Any:
    """Recursively convert API objects to plain dicts/lists for JSON."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_make_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    return obj
