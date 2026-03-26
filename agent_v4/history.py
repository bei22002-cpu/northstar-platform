"""Session history with persistent save/load support."""

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

    def add_user(self, message: str) -> None:
        self._messages.append({"role": "user", "content": message})

    def add_assistant(self, content: Any) -> None:
        if isinstance(content, str):
            self._messages.append({"role": "assistant", "content": content})
        else:
            serializable = _make_serializable(content)
            self._messages.append({"role": "assistant", "content": serializable})

    def add_tool_results(self, results: list[dict[str, Any]]) -> None:
        self._messages.append({"role": "user", "content": results})

    def get_messages(self) -> list[dict[str, Any]]:
        """Return sanitised history (strips orphaned tool_use blocks)."""
        msgs = list(self._messages)
        while msgs:
            last = msgs[-1]
            if last["role"] == "assistant" and _has_tool_use(last.get("content")):
                msgs.pop()
                continue
            break
        return msgs

    def get_raw_messages(self) -> list[dict[str, Any]]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    @property
    def message_count(self) -> int:
        return len(self._messages)

    def save(self) -> str:
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        filepath = os.path.join(log_dir, f"session_{timestamp}.json")
        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(self._messages, fh, indent=2, default=str)
        self._session_file = filepath
        return filepath

    def load(self, filepath: str) -> bool:
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
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        if not os.path.isdir(log_dir):
            return []
        sessions: list[dict[str, str]] = []
        for fname in sorted(os.listdir(log_dir), reverse=True):
            if fname.startswith("session_") and fname.endswith(".json"):
                fpath = os.path.join(log_dir, fname)
                ts = fname.replace("session_", "").replace(".json", "")
                sessions.append({"timestamp": ts, "path": fpath, "filename": fname})
        return sessions


def _has_tool_use(content: Any) -> bool:
    if not isinstance(content, list):
        return False
    return any(
        (isinstance(item, dict) and item.get("type") == "tool_use")
        for item in content
    )


def _make_serializable(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_make_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    return obj
