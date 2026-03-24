"""Safety layer — command blocking and human approval gate."""

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


def ask_approval(tool_name: str, tool_input: dict[str, Any]) -> bool:
    """Show the user what the AI wants to do and ask for approval.

    Returns True only if the user types 'y'.
    """
    # Block dangerous commands immediately
    if tool_name == "run_command" and is_blocked(tool_input.get("command", "")):
        console.print(
            Panel(
                f"[bold red]BLOCKED:[/bold red] The command "
                f"'{tool_input['command']}' matches a blocked pattern and "
                "will not be executed.",
                title="Security Block",
                border_style="red",
            )
        )
        return False

    # Build a summary of what the AI wants to do
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
            title="AI wants to perform an action",
            border_style="yellow",
        )
    )

    answer = console.input("[bold yellow]Approve? (y/n): [/bold yellow]").strip().lower()
    return answer == "y"
