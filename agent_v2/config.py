"""Configuration loader for the Cornerstone AI Agent v2."""

import os
import sys

from dotenv import load_dotenv

# Load .env from the agent_v2/ directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def get_provider_name() -> str:
    """Return the configured provider name (claude, ollama, or gemini)."""
    return os.getenv("PROVIDER", "claude").lower().strip()


def get_api_keys() -> list[str]:
    """Return a list of Anthropic API keys from the environment.

    Reads ANTHROPIC_API_KEY_1, ANTHROPIC_API_KEY_2, ... up to _10.
    Falls back to a single ANTHROPIC_API_KEY if numbered keys are absent.

    Returns an empty list (instead of exiting) when the provider is not
    Claude, since Ollama/Gemini don't need Anthropic keys.
    """
    keys: list[str] = []
    for i in range(1, 11):
        key = os.getenv(f"ANTHROPIC_API_KEY_{i}")
        if key:
            keys.append(key)

    # Fallback to the single-key variable used by v1
    if not keys:
        single = os.getenv("ANTHROPIC_API_KEY")
        if single:
            keys.append(single)

    # Only error if we're using Claude as the provider
    if not keys and get_provider_name() in ("claude", "anthropic", ""):
        print(
            "[ERROR] No API keys found. Set ANTHROPIC_API_KEY_1, "
            "ANTHROPIC_API_KEY_2, ... (up to _10) or ANTHROPIC_API_KEY "
            "in agent_v2/.env\n"
            "Or set PROVIDER=ollama or PROVIDER=gemini for free alternatives."
        )
        sys.exit(1)

    return keys


def get_workspace() -> str:
    """Return the resolved workspace path or exit with an error."""
    raw = os.getenv("WORKSPACE", "./backend")
    workspace = os.path.abspath(raw)
    if not os.path.isdir(workspace):
        print(
            f"[ERROR] WORKSPACE path does not exist: {workspace}\n"
            "Please set a valid WORKSPACE in agent_v2/.env"
        )
        sys.exit(1)
    return workspace


API_KEYS: list[str] = get_api_keys() if "pytest" not in sys.modules else []
WORKSPACE: str = get_workspace() if "pytest" not in sys.modules else ""
