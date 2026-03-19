"""Configuration loader for the Cornerstone AI Agent."""

import os
import sys

from dotenv import load_dotenv

# Load .env from the agent/ directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def get_api_key() -> str:
    """Return the Anthropic API key or exit with an error."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        print(
            "[ERROR] ANTHROPIC_API_KEY is not set. "
            "Please add it to agent/.env or export it as an environment variable."
        )
        sys.exit(1)
    return key


def get_workspace() -> str:
    """Return the resolved workspace path or exit with an error."""
    raw = os.getenv("WORKSPACE", "./backend")
    workspace = os.path.abspath(raw)
    if not os.path.isdir(workspace):
        print(
            f"[ERROR] WORKSPACE path does not exist: {workspace}\n"
            "Please set a valid WORKSPACE in agent/.env"
        )
        sys.exit(1)
    return workspace


ANTHROPIC_API_KEY: str = get_api_key() if "pytest" not in sys.modules else ""
WORKSPACE: str = get_workspace() if "pytest" not in sys.modules else ""
