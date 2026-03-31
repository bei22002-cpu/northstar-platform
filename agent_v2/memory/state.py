"""Structured state — persistent key-value store for high-value user attributes.

Only stable, reusable information is stored here (e.g. name, role, project,
preferences).  Transient data (greetings, filler) is ignored.

The state is persisted to a JSON file so it survives across sessions.
"""

from __future__ import annotations

import json
import os
from typing import Any


_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "state.json")


class StructuredState:
    """Thread-safe structured state backed by a JSON file."""

    def __init__(self, path: str | None = None) -> None:
        self._path = os.path.abspath(path or _DEFAULT_PATH)
        self._data: dict[str, Any] = {}
        self._load()

    # -- public API -----------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for *key*, or *default* if absent."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a single key-value pair and persist."""
        self._data[key] = value
        self._save()

    def update(self, pairs: dict[str, Any]) -> None:
        """Merge multiple key-value pairs and persist."""
        self._data.update(pairs)
        self._save()

    def delete(self, key: str) -> None:
        """Remove a key if it exists."""
        self._data.pop(key, None)
        self._save()

    def all(self) -> dict[str, Any]:
        """Return a shallow copy of the full state."""
        return dict(self._data)

    def clear(self) -> None:
        """Wipe the state entirely."""
        self._data.clear()
        self._save()

    def to_prompt_string(self) -> str:
        """Render the state as a compact string for prompt injection.

        Returns an empty string if the state is empty so the context builder
        can skip it entirely.
        """
        if not self._data:
            return ""
        lines = [f"- {k}: {v}" for k, v in self._data.items()]
        return "Known user attributes:\n" + "\n".join(lines)

    # -- persistence ----------------------------------------------------------

    def _load(self) -> None:
        if os.path.isfile(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as fh:
                    self._data = json.load(fh)
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, ensure_ascii=False)
