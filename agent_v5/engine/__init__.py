"""Engine primitive — inference runtime backends."""

from agent_v5.engine.base import InferenceEngine
from agent_v5.engine.discovery import discover_engines, get_engine

__all__ = ["InferenceEngine", "discover_engines", "get_engine"]
