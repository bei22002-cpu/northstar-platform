"""Configuration loader for the Cornerstone AI Agent v3.

Supports multiple API keys (ANTHROPIC_API_KEY_1 … _10), workspace path,
and multiple Claude model options for mid-session switching.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

# Load .env from the agent_v3 package directory
_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(_env_path)


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------

def get_api_keys() -> list[str]:
    """Return a list of Anthropic API keys from the environment."""
    keys: list[str] = []
    for i in range(1, 11):
        key = os.getenv(f"ANTHROPIC_API_KEY_{i}")
        if key:
            keys.append(key)

    if not keys:
        single = os.getenv("ANTHROPIC_API_KEY")
        if single:
            keys.append(single)

    if not keys:
        if "pytest" in sys.modules:
            return []
        print("[ERROR] No API keys found. Set ANTHROPIC_API_KEY_1 (up to _10) "
              "or ANTHROPIC_API_KEY in agent_v3/.env")
        sys.exit(1)

    return keys


API_KEYS: list[str] = get_api_keys()


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

WORKSPACE: str = os.getenv("WORKSPACE", "./backend")
WORKSPACE = os.path.abspath(WORKSPACE)

if not os.path.isdir(WORKSPACE) and "pytest" not in sys.modules:
    print(f"[WARN] Workspace directory does not exist: {WORKSPACE}")
    print("       Creating it now...")
    os.makedirs(WORKSPACE, exist_ok=True)


# ---------------------------------------------------------------------------
# Model Configuration
# ---------------------------------------------------------------------------

AVAILABLE_MODELS: dict[str, str] = {
    "opus": "claude-opus-4-5",
    "sonnet": "claude-sonnet-4-5-20250514",
    "haiku": "claude-haiku-4-5-20250514",
}

DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "sonnet")

# Token costs per million tokens (USD) for cost tracking
MODEL_COSTS: dict[str, dict[str, float]] = {
    "claude-opus-4-5": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-5-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20250514": {"input": 0.80, "output": 4.0},
}

MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "8096"))
