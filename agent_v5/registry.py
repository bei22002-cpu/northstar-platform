"""Generic registry pattern for runtime component discovery.

Every extensible component (engines, agents, memory backends, tools) uses
a decorator-based registry so new implementations are discovered at import
time with zero factory changes.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type, TypeVar

T = TypeVar("T")


class RegistryBase:
    """Base class for typed registries.

    Subclass this once per component type (EngineRegistry, AgentRegistry, etc.)
    so each gets its own isolated storage.
    """

    _entries: Dict[str, Any] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._entries = {}

    @classmethod
    def register(cls, key: str) -> Any:
        """Decorator that registers a class under *key*."""

        def decorator(klass: Any) -> Any:
            cls._entries[key] = klass
            return klass

        return decorator

    @classmethod
    def register_value(cls, key: str, value: Any) -> None:
        """Imperative registration."""
        cls._entries[key] = value

    @classmethod
    def get(cls, key: str) -> Any:
        """Retrieve by key.  Raises KeyError if missing."""
        if key not in cls._entries:
            raise KeyError(
                f"{cls.__name__}: no entry for {key!r}. "
                f"Available: {list(cls._entries.keys())}"
            )
        return cls._entries[key]

    @classmethod
    def create(cls, key: str, *args: Any, **kwargs: Any) -> Any:
        """Look up and instantiate."""
        klass = cls.get(key)
        return klass(*args, **kwargs)

    @classmethod
    def items(cls) -> list[tuple[str, Any]]:
        return list(cls._entries.items())

    @classmethod
    def keys(cls) -> list[str]:
        return list(cls._entries.keys())

    @classmethod
    def contains(cls, key: str) -> bool:
        return key in cls._entries

    @classmethod
    def clear(cls) -> None:
        cls._entries.clear()


# ── Typed registries ─────────────────────────────────────────────────────

class EngineRegistry(RegistryBase):
    """Registry for inference engine backends."""


class AgentRegistry(RegistryBase):
    """Registry for agent implementations."""


class MemoryRegistry(RegistryBase):
    """Registry for memory backends."""


class ToolRegistry(RegistryBase):
    """Registry for tool implementations."""
