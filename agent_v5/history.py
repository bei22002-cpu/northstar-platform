"""Session history — manages conversation messages with persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from agent_v5.config import DATA_DIR


class SessionHistory:
    """Manages the conversation message list with save/load/sanitize."""

    def __init__(self, save_path: str = "") -> None:
        self._messages: List[dict[str, Any]] = []
        self._path = Path(save_path) if save_path else DATA_DIR / "history.json"

    def add_user(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})

    def add_assistant(self, content: Any) -> None:
        self._messages.append({"role": "assistant", "content": content})

    def add_tool_results(self, results: list[dict[str, Any]]) -> None:
        self._messages.append({"role": "user", "content": results})

    def get_messages(self) -> List[dict[str, Any]]:
        return list(self._messages)

    def get_recent(self, n: int = 20) -> List[dict[str, Any]]:
        return self._messages[-n:]

    def clear(self) -> None:
        self._messages.clear()

    def sanitize(self) -> None:
        """Remove orphaned tool_use blocks without matching tool_result."""
        if not self._messages:
            return

        cleaned: List[dict[str, Any]] = []
        for i, msg in enumerate(self._messages):
            if msg["role"] == "assistant" and isinstance(msg["content"], list):
                tool_use_ids = [
                    b["id"]
                    for b in msg["content"]
                    if isinstance(b, dict) and b.get("type") == "tool_use"
                ]
                if tool_use_ids:
                    # Check if next message has matching tool_results
                    if i + 1 < len(self._messages):
                        next_msg = self._messages[i + 1]
                        if next_msg["role"] == "user" and isinstance(
                            next_msg["content"], list
                        ):
                            result_ids = {
                                b.get("tool_use_id")
                                for b in next_msg["content"]
                                if isinstance(b, dict)
                                and b.get("type") == "tool_result"
                            }
                            if tool_use_ids[0] in result_ids:
                                cleaned.append(msg)
                                continue
                    # Orphaned — skip it
                    continue
            cleaned.append(msg)
        self._messages = cleaned

    def save(self) -> None:
        """Persist history to disk."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w") as f:
                json.dump(self._messages, f, indent=2, default=str)
        except OSError:
            pass

    def load(self) -> None:
        """Load history from disk."""
        if not self._path.exists():
            return
        try:
            with open(self._path) as f:
                self._messages = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._messages = []

    def __len__(self) -> int:
        return len(self._messages)
