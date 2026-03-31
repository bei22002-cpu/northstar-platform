"""Entry-point for the Cornerstone AI Agent v2 — with token rotation."""

from __future__ import annotations

import asyncio

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agent_v2.config import API_KEYS, WORKSPACE
from agent_v2.session import history, run_agent, token_manager

console = Console()


def _print_banner() -> None:
    banner = Text()
    banner.append("Cornerstone AI Agent v2 — Autonomous Mode\n", style="bold magenta")
    banner.append(f"Workspace: {WORKSPACE}\n", style="dim")
    banner.append(f"API Keys loaded: {len(API_KEYS)}\n", style="bold cyan")
    banner.append(
        "Fully autonomous — executes tools without approval prompts.\n",
        style="bold green",
    )
    banner.append(
        "Auto-rotates keys on rate limits for continuous progress.\n",
        style="dim",
    )
    banner.append(
        "Dangerous commands (rm -rf /, DROP DATABASE, etc.) are still blocked.\n",
        style="dim red",
    )
    banner.append("Type 'exit' or 'quit' to end the session.\n", style="dim")
    banner.append("Type 'keys' to see token status.", style="dim")
    console.print(
        Panel(banner, title="Welcome", border_style="bright_blue")
    )


def _print_key_stats() -> None:
    """Display a table of per-key statistics."""
    stats = token_manager.get_stats()
    table = Table(title="API Key Status")
    table.add_column("#", style="bold")
    table.add_column("Key", style="dim")
    table.add_column("Calls", justify="right")
    table.add_column("Errors", justify="right")
    table.add_column("Rate Limited", justify="center")
    table.add_column("Cooldown (s)", justify="right")
    for s in stats:
        rl = "[red]YES[/red]" if s["rate_limited"] else "[green]no[/green]"
        table.add_row(
            str(s["key_number"]),
            s["masked_key"],
            str(s["calls"]),
            str(s["errors"]),
            rl,
            str(s["cooldown_remaining"]),
        )
    console.print(table)


def main() -> None:
    _print_banner()

    try:
        while True:
            try:
                user_input = console.input(
                    "[bold green]You > [/bold green]"
                ).strip()
            except EOFError:
                break

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                break
            if user_input.lower() == "keys":
                _print_key_stats()
                continue

            asyncio.run(run_agent(user_input))

    except KeyboardInterrupt:
        console.print("\n[yellow]Session interrupted.[/yellow]")

    # Save session log
    log_path = history.save()
    console.print(f"\n[dim]Session log saved to: {log_path}[/dim]")
    _print_key_stats()
    console.print("[bold blue]Goodbye![/bold blue]")


if __name__ == "__main__":
    main()
