"""Persistent memory / knowledge base (#5).

Stores project facts, user preferences, and past decisions that persist
across all sessions. Backed by a simple JSON file on disk.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any


_MEMORY_PATH = os.path.join(os.path.dirname(__file__), "memory", "knowledge.json")


class KnowledgeBase:
    """Simple persistent key-value knowledge store."""

    def __init__(self, path: str = _MEMORY_PATH) -> None:
        self._path = path
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if os.path.isfile(self._path):
            try:
                with open(self._path, encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, default=str)

    def remember(self, key: str, value: str) -> str:
        """Store a fact. Overwrites if key already exists."""
        self._data[key] = {
            "value": value,
            "updated_at": datetime.now().isoformat(),
        }
        self._save()
        return f"Remembered: {key} = {value}"

    def recall(self, key: str) -> str | None:
        """Retrieve a fact by key. Returns None if not found."""
        entry = self._data.get(key)
        if entry:
            return entry["value"]
        return None

    def forget(self, key: str) -> str:
        """Remove a fact. Returns confirmation."""
        if key in self._data:
            del self._data[key]
            self._save()
            return f"Forgot: {key}"
        return f"No memory found for: {key}"

    def search(self, query: str) -> list[dict[str, str]]:
        """Search memories by keyword match on key or value."""
        query_lower = query.lower()
        results: list[dict[str, str]] = []
        for key, entry in self._data.items():
            if query_lower in key.lower() or query_lower in entry["value"].lower():
                results.append({
                    "key": key,
                    "value": entry["value"],
                    "updated_at": entry.get("updated_at", "unknown"),
                })
        return results

    def list_all(self) -> list[dict[str, str]]:
        """Return all stored memories."""
        return [
            {"key": k, "value": v["value"], "updated_at": v.get("updated_at", "unknown")}
            for k, v in self._data.items()
        ]

    def get_context_string(self) -> str:
        """Return all memories as a string for injection into system prompt."""
        if not self._data:
            return ""
        lines = ["## Persistent Memory (knowledge from past sessions):"]
        for key, entry in self._data.items():
            lines.append(f"- **{key}**: {entry['value']}")
        return "\n".join(lines)

    @property
    def count(self) -> int:
        return len(self._data)
