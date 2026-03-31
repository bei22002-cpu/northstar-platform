"""Engine discovery — probes backends and returns healthy engines."""

from __future__ import annotations

from typing import Optional

from agent_v5.config import (
    ANTHROPIC_API_KEYS,
    OLLAMA_HOST,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
)
from agent_v5.engine.base import InferenceEngine
from agent_v5.registry import EngineRegistry

# Force registration by importing concrete engines
import agent_v5.engine.ollama as _ollama  # noqa: F401
import agent_v5.engine.anthropic_engine as _anthropic  # noqa: F401
import agent_v5.engine.openai_compat as _openai  # noqa: F401


def _build_engine(engine_id: str) -> Optional[InferenceEngine]:
    """Instantiate an engine by registry key, or return None on failure."""
    try:
        if engine_id == "ollama":
            return EngineRegistry.create("ollama", host=OLLAMA_HOST)
        if engine_id == "anthropic":
            if not ANTHROPIC_API_KEYS:
                return None
            return EngineRegistry.create("anthropic", api_keys=ANTHROPIC_API_KEYS)
        if engine_id == "openai":
            if not OPENAI_API_KEY:
                return None
            return EngineRegistry.create(
                "openai", api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL
            )
    except Exception:
        return None
    return None


def discover_engines() -> list[InferenceEngine]:
    """Probe all registered backends and return healthy engines."""
    engines: list[InferenceEngine] = []
    for key in EngineRegistry.keys():
        engine = _build_engine(key)
        if engine is not None and engine.health():
            engines.append(engine)
    return engines


def get_engine(preferred: str = "auto") -> InferenceEngine:
    """Return the preferred engine, or the best available one.

    Parameters
    ----------
    preferred:
        Engine id ("ollama", "anthropic", "openai") or "auto" to pick the
        best available.

    Raises
    ------
    RuntimeError
        If no engine is available.
    """
    if preferred != "auto":
        engine = _build_engine(preferred)
        if engine is not None:
            return engine

    # Auto — try each in order of preference
    for eid in ("ollama", "anthropic", "openai"):
        engine = _build_engine(eid)
        if engine is not None:
            # For cloud engines, skip health check (assume reachable)
            if eid in ("anthropic", "openai"):
                return engine
            if engine.health():
                return engine

    raise RuntimeError(
        "No inference engine available. Install Ollama for local models, "
        "or set ANTHROPIC_API_KEY / OPENAI_API_KEY for cloud."
    )
