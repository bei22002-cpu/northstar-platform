"""Safety layer — command blocking and autonomous action logging."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel

console = Console()

BLOCKED_COMMANDS: list[str] = [
    "rm -rf /",
    "format",
    "del /f /s /q C:\\",
    "shutdown",
    "DROP DATABASE",
    "DROP TABLE",
    ":(){:|:&};:",
]


def is_blocked(command: str) -> bool:
    """Return True if *command* contains a blocked pattern."""
    cmd_lower = command.lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked.lower() in cmd_lower:
            return True
    return False


def log_action(tool_name: str, tool_input: dict[str, Any]) -> None:
    """Log what the agent is about to do (no approval needed)."""
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
