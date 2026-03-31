"""Safety module — blocks dangerous commands and file operations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple

# ── Dangerous command patterns ────────────────────────────────────────────

_BLOCKED_COMMANDS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"rm\s+-rf\s+/",
        r"rm\s+-rf\s+~",
        r"rm\s+-rf\s+\.",
        r"rm\s+-rf\s+\*",
        r"rm\s+-fr\s+/",
        r"mkfs\b",
        r"dd\s+if=",
        r":(){ :\|:& };:",  # fork bomb
        r"format\s+[a-zA-Z]:",
        r"del\s+/f\s+/s\s+/q\s+C:",
        r"shutdown\b",
        r"reboot\b",
        r"halt\b",
        r"poweroff\b",
        r"DROP\s+DATABASE",
        r"DROP\s+TABLE",
        r"TRUNCATE\s+TABLE",
        r"curl\s+.*\|\s*bash",
        r"curl\s+.*\|\s*sh",
        r"wget\s+.*\|\s*bash",
        r"wget\s+.*\|\s*sh",
        r"chmod\s+777",
        r"chmod\s+-R\s+777",
        r">\s*/dev/sd",
        r">\s*/dev/null.*<",
        r"eval\s*\(",
        r"exec\s*\(",
    ]
]

# ── Protected file paths ──────────────────────────────────────────────────

_PROTECTED_PATHS: list[str] = [
    "/etc/",
    "/usr/",
    "/bin/",
    "/sbin/",
    "/boot/",
    "/proc/",
    "/sys/",
    "/dev/",
    "~/.ssh",
    ".env",
]


def is_blocked(command: str) -> Tuple[bool, str]:
    """Check if a command matches any dangerous pattern.

    Returns (is_blocked, reason).
    """
    for pattern in _BLOCKED_COMMANDS:
        if pattern.search(command):
            return True, f"Matches dangerous pattern: {pattern.pattern}"
    return False, ""


def is_path_safe(filepath: str, workspace: str = ".") -> Tuple[bool, str]:
    """Check if a file path is safe to write/delete.

    Returns (is_safe, reason).
    """
    # Check for path traversal
    if ".." in filepath:
        return False, "Path traversal (..) not allowed"

    # Check protected system paths
    for protected in _PROTECTED_PATHS:
        if filepath.startswith(protected) or f"/{protected}" in filepath:
            return False, f"Protected path: {protected}"

    # Ensure within workspace
    try:
        ws = Path(workspace).resolve()
        target = (ws / filepath).resolve()
        if not str(target).startswith(str(ws)):
            return False, "Path outside workspace"
    except (ValueError, OSError):
        return False, "Invalid path"

    return True, ""


def log_action(tool_name: str, tool_input: dict) -> None:
    """Log a tool action for audit trail."""
    import json
    from datetime import datetime

    from agent_v5.config import LOGS_DIR

    log_file = LOGS_DIR / "actions.log"
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "tool": tool_name,
        "input": tool_input,
    }
    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass
