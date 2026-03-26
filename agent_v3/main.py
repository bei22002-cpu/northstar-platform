"""CLI entry point for the Cornerstone AI Agent v3.

Features:
- Streaming responses (real-time text output)
- Model switching mid-session (type 'model opus/sonnet/haiku')
- Cost tracking (type 'cost')
- Key stats dashboard (type 'keys')
- Undo last agent action (type 'undo')
- Session persistence (type 'sessions' to list, 'resume <file>' to load)
- Plugin system (drop .py files in agent_v3/plugins/)
"""

from __future__ import annotations

import asyncio
import subprocess
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agent_v3.config import API_KEYS, AVAILABLE_MODELS, MAX_TOKENS, WORKSPACE
from agent_v3.session import (
    cost_tracker,
    current_model,
    history,
    run_agent,
    set_model,
    token_manager,
)

console = Console()


def _show_banner() -> None:
    """Display the startup banner."""
    banner = Text()
    banner.append("Cornerstone AI Agent v3 — Full-Featured Autonomous\n", style="bold magenta")
    banner.append(f"Workspace: {WORKSPACE}\n", style="dim")
    banner.append(f"API Keys loaded: {len(API_KEYS)}\n", style="bold cyan")
    banner.append(f"Model: {current_model}\n", style="bold cyan")
    banner.append(
        "Fully autonomous — executes tools without approval prompts.\n",
        style="bold green",
    )
    banner.append(
        "Auto-rotates keys with exponential backoff.\n",
        style="dim",
    )
    banner.append(
        "Dangerous commands and paths are blocked.\n",
        style="dim red",
    )
    banner.append("\nCommands:\n", style="bold")
    banner.append("  exit/quit     — End session\n", style="dim")
    banner.append("  keys          — Show API key stats\n", style="dim")
    banner.append("  cost          — Show token usage & cost\n", style="dim")
    banner.append("  model <name>  — Switch model (opus/sonnet/haiku)\n", style="dim")
    banner.append("  undo          — Revert last agent change (git)\n", style="dim")
    banner.append("  sessions      — List saved sessions\n", style="dim")
    banner.append("  resume <file> — Resume a saved session\n", style="dim")
    banner.append("  clear         — Clear conversation history\n", style="dim")

    console.print(Panel(banner, title="Welcome", border_style="cyan"))


def _show_keys() -> None:
    """Display the API key stats dashboard."""
    table = Table(title="API Key Status")
    table.add_column("#", justify="right", style="bold")
    table.add_column("Key", style="dim")
    table.add_column("Calls", justify="right")
    table.add_column("Errors", justify="right")
    table.add_column("Rate Limited", justify="center")
    table.add_column("Cooldown (s)", justify="right")
    table.add_column("Backoff Failures", justify="right")

    for stat in token_manager.get_stats():
        table.add_row(
            str(stat["key_number"]),
            stat["masked_key"],
            str(stat["calls"]),
            str(stat["errors"]),
            "[red]yes[/red]" if stat["rate_limited"] else "[green]no[/green]",
            str(stat["cooldown_remaining"]),
            str(stat["consecutive_failures"]),
        )

    console.print(table)


def _show_cost() -> None:
    """Display token usage and cost summary."""
    console.print(Panel(
        cost_tracker.summary(),
        title="Token Usage & Cost",
        border_style="yellow",
    ))


def _show_sessions() -> None:
    """List all saved sessions."""
    sessions = history.list_sessions()
    if not sessions:
        console.print("[dim]No saved sessions found.[/dim]")
        return
    table = Table(title="Saved Sessions")
    table.add_column("#", justify="right", style="bold")
    table.add_column("Timestamp")
    table.add_column("File")
    for i, s in enumerate(sessions, 1):
        table.add_row(str(i), s["timestamp"], s["filename"])
    console.print(table)


def _resume_session(arg: str) -> None:
    """Resume a saved session by filename or number."""
    sessions = history.list_sessions()

    # Try as number
    try:
        idx = int(arg) - 1
        if 0 <= idx < len(sessions):
            filepath = sessions[idx]["path"]
        else:
            console.print("[red]Invalid session number.[/red]")
            return
    except ValueError:
        # Try as filename
        log_dir = __import__("os").path.join(
            __import__("os").path.dirname(__file__), "logs"
        )
        filepath = __import__("os").path.join(log_dir, arg)

    if history.load(filepath):
        console.print(f"[green]Resumed session from {filepath}[/green]")
        console.print(f"[dim]Loaded {history.message_count} messages.[/dim]")
    else:
        console.print(f"[red]Failed to load session: {filepath}[/red]")


def _undo() -> None:
    """Revert the last git commit made by the agent (undo support)."""
    try:
        # Check if there's an agent checkpoint to undo
        result = subprocess.run(
            "git log --oneline -1",
            shell=True, capture_output=True, text=True,
            timeout=5, cwd=WORKSPACE,
        )
        if "[agent_v3]" in result.stdout:
            subprocess.run(
                "git revert HEAD --no-edit",
                shell=True, capture_output=True, text=True,
                timeout=10, cwd=WORKSPACE,
            )
            console.print("[green]Reverted last agent change.[/green]")
        else:
            console.print("[yellow]No agent checkpoint found to undo.[/yellow]")
    except Exception as exc:
        console.print(f"[red]Undo failed: {exc}[/red]")


def main() -> None:
    """Run the agent CLI loop."""
    _show_banner()

    while True:
        try:
            user_input = console.input("[bold green]You > [/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue

        lower = user_input.lower()

        # Built-in commands
        if lower in ("exit", "quit"):
            break
        if lower == "keys":
            _show_keys()
            continue
        if lower == "cost":
            _show_cost()
            continue
        if lower == "sessions":
            _show_sessions()
            continue
        if lower == "clear":
            history.clear()
            console.print("[green]History cleared.[/green]")
            continue
        if lower == "undo":
            _undo()
            continue
        if lower.startswith("model "):
            model_key = lower.split(" ", 1)[1].strip()
            result = set_model(model_key)
            console.print(f"[cyan]{result}[/cyan]")
            continue
        if lower.startswith("resume "):
            arg = user_input.split(" ", 1)[1].strip()
            _resume_session(arg)
            continue

        # Send to the agent
        try:
            asyncio.run(run_agent(user_input))
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
        except Exception as exc:
            console.print(f"\n[bold red]Error:[/bold red] {exc}")

    # -- cleanup --
    log_path = history.save()
    console.print(f"\n[dim]Session log saved to: {log_path}[/dim]")

    _show_keys()
    _show_cost()

    console.print("\n[bold magenta]Goodbye![/bold magenta]")


if __name__ == "__main__":
    main()
