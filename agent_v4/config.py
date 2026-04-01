"""Configuration loader for the Cornerstone AI Agent v4.

Supports multiple API keys, workspace path, model selection,
custom system prompts, GitHub token, Slack token, and linter config.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

# Load .env from the agent_v4 package directory
_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(_env_path)


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------

def _get_api_keys() -> list[str]:
    keys: list[str] = []
    for i in range(1, 11):
        key = os.getenv(f"ANTHROPIC_API_KEY_{i}")
        if key:
            keys.append(key)
    if not keys:
        single = os.getenv("ANTHROPIC_API_KEY")
        if single:
            keys.append(single)
    if not keys and "pytest" not in sys.modules:
        print("[ERROR] No API keys found. Set ANTHROPIC_API_KEY_1 (up to _10) "
              "or ANTHROPIC_API_KEY in agent_v4/.env")
        sys.exit(1)
    return keys


API_KEYS: list[str] = _get_api_keys()

# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

WORKSPACE: str = os.path.abspath(os.getenv("WORKSPACE", "./backend"))

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

MODEL_COSTS: dict[str, dict[str, float]] = {
    "claude-opus-4-5": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-5-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20250514": {"input": 0.80, "output": 4.0},
}

MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "8096"))

# ---------------------------------------------------------------------------
# Custom System Prompt (#11)
# ---------------------------------------------------------------------------

_CUSTOM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "system_prompt.txt")

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert senior software engineer working on the "
    "Cornerstone Platform — a FastAPI + PostgreSQL backend project. "
    "You have direct access to the project workspace and can read, "
    "write, create, delete, patch files, run commands, and search code.\n\n"
    "Rules:\n"
    "- Always read a file before overwriting it.\n"
    "- Prefer patch_file over write_file when editing existing files.\n"
    "- Never delete files unless the user explicitly requests it.\n"
    "- Always explain what you are about to do in plain English "
    "before using a tool.\n"
    "- Write clean, production-quality Python code.\n"
    "- Follow the existing project structure and conventions.\n"
    "- After completing a task, summarize what you did."
)


def get_system_prompt() -> str:
    """Return the system prompt — custom file if it exists, else default."""
    # Check env var first
    env_prompt = os.getenv("SYSTEM_PROMPT")
    if env_prompt:
        return env_prompt
    # Check file
    if os.path.isfile(_CUSTOM_PROMPT_PATH):
        try:
            with open(_CUSTOM_PROMPT_PATH, encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                return content
        except OSError:
            pass
    return DEFAULT_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# GitHub Integration (#3)
# ---------------------------------------------------------------------------

GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO: str = os.getenv("GITHUB_REPO", "")  # e.g. "owner/repo"

# ---------------------------------------------------------------------------
# Slack Integration (#9)
# ---------------------------------------------------------------------------

SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN: str = os.getenv("SLACK_APP_TOKEN", "")

# ---------------------------------------------------------------------------
# Linting (#8)
# ---------------------------------------------------------------------------

LINT_COMMAND: str = os.getenv("LINT_COMMAND", "")
TYPECHECK_COMMAND: str = os.getenv("TYPECHECK_COMMAND", "")
