"""Expanded safety layer for autonomous execution.

Blocks dangerous commands for run_command, and also guards write_file
and delete_file against risky patterns.
"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel

console = Console()

# ---------------------------------------------------------------------------
# Blocked command patterns (for run_command)
# ---------------------------------------------------------------------------

BLOCKED_COMMANDS: list[str] = [
    # Destructive filesystem
    "rm -rf /",
    "rm -rf ~",
    "rm -rf .",
    "rm -rf *",
    "format",
    "del /f /s /q C:\\",
    "mkfs",
    "dd if=",
    # System control
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    # Database destruction
    "DROP DATABASE",
    "DROP TABLE",
    "TRUNCATE TABLE",
    # Fork bomb
    ":(){:|:&};:",
    # Dangerous downloads / piped execution
    "curl|bash",
    "curl | bash",
    "wget|bash",
    "wget | bash",
    "curl|sh",
    "curl | sh",
    "wget|sh",
    "wget | sh",
    # Permission escalation
    "chmod 777",
    "chmod -R 777",
    # Credential exposure
    "cat /etc/shadow",
    "cat /etc/passwd",
]

# Patterns that should never appear in file paths (write/delete)
BLOCKED_PATHS: list[str] = [
    "..",         # path traversal
    "/etc/",
    "/usr/",
    "/bin/",
    "/sbin/",
    "/boot/",
    "/proc/",
    "/sys/",
    "~/.ssh",
    ".env",       # don't let agent overwrite env files
]


def is_command_blocked(command: str) -> bool:
    """Return True if *command* contains a blocked pattern."""
    cmd_lower = command.lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked.lower() in cmd_lower:
            return True
    return False


def is_path_blocked(filepath: str) -> bool:
    """Return True if *filepath* contains a blocked path pattern."""
    fp_lower = filepath.lower()
    for blocked in BLOCKED_PATHS:
        if blocked.lower() in fp_lower:
            return True
    return False


def check_safety(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """Check if a tool call is safe.

    Returns None if safe, or a string explaining why it was blocked.
    """
    if tool_name == "run_command":
        cmd = tool_input.get("command", "")
        if is_command_blocked(cmd):
            return f"BLOCKED: '{cmd}' matches a dangerous command pattern."

    if tool_name in ("write_file", "delete_file", "patch_file"):
        fp = tool_input.get("filepath", "")
        if is_path_blocked(fp):
            return f"BLOCKED: '{fp}' targets a protected path."

    if tool_name == "delete_file":
        fp = tool_input.get("filepath", "")
        if not fp or fp == "." or fp == "/":
            return "BLOCKED: Cannot delete root or empty path."

    return None


def log_action(tool_name: str, tool_input: dict[str, Any]) -> None:
    """Log what the agent is about to execute (no approval needed)."""
    lines: list[str] = [f"[bold cyan]Tool:[/bold cyan] {tool_name}"]
    for key, value in tool_input.items():
        if key == "content":
            lines.append(
                f"[bold cyan]{key}:[/bold cyan] ({len(value)} characters)"
            )
        else:
            display = str(value)
            if len(display) > 200:
                display = display[:200] + "..."
            lines.append(f"[bold cyan]{key}:[/bold cyan] {display}")

    console.print(
        Panel(
            "\n".join(lines),
            title="Executing",
            border_style="green",
        )
    )
