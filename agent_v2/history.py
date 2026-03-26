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
        """Return the full message history, sanitised for the API."""
        self._sanitize()
        return list(self._messages)

    def _sanitize(self) -> None:
        """Ensure every assistant ``tool_use`` block has a matching ``tool_result``.

        If an assistant message contains ``tool_use`` blocks but the very next
        message does not supply the corresponding ``tool_result`` entries, this
        method inserts a synthetic ``user`` message with error-style results so
        that the Anthropic API never rejects the conversation.
        """
        i = 0
        while i < len(self._messages):
            msg = self._messages[i]
            if msg["role"] != "assistant":
                i += 1
                continue

            # Collect tool_use ids from this assistant message
            tool_use_ids: list[str] = []
            content = msg.get("content")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_use_ids.append(block["id"])

            if not tool_use_ids:
                i += 1
                continue

            # Check whether the next message supplies all required tool_results
            next_msg = self._messages[i + 1] if i + 1 < len(self._messages) else None
            covered_ids: set[str] = set()
            if (
                next_msg is not None
                and next_msg["role"] == "user"
                and isinstance(next_msg.get("content"), list)
            ):
                for block in next_msg["content"]:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        covered_ids.add(block.get("tool_use_id", ""))

            missing_ids = [uid for uid in tool_use_ids if uid not in covered_ids]
            if missing_ids:
                # Build synthetic tool_result entries for the missing ids
                synthetic_results: list[dict[str, Any]] = []

                # Preserve any existing tool_results that were already correct
                if covered_ids and next_msg is not None:
                    synthetic_results = list(next_msg["content"])

                for uid in missing_ids:
                    synthetic_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": uid,
                            "content": "Error: tool execution was interrupted.",
                        }
                    )

                if covered_ids and next_msg is not None:
                    # Update the existing message in-place
                    next_msg["content"] = synthetic_results
                else:
                    # Insert a brand-new user message right after the assistant
                    self._messages.insert(
                        i + 1,
                        {"role": "user", "content": synthetic_results},
                    )

            i += 1

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
