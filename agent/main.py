"""Entry-point for the Cornerstone AI Agent."""

from __future__ import annotations

import asyncio
import sys

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from agent.config import WORKSPACE
from agent.session import history, run_agent

console = Console()


def _print_banner() -> None:
    banner = Text()
    banner.append("Cornerstone AI Agent\n", style="bold magenta")
    banner.append(f"Workspace: {WORKSPACE}\n", style="dim")
    banner.append("Type 'exit' or 'quit' to end the session.", style="dim")
    console.print(
        Panel(banner, title="Welcome", border_style="bright_blue")
    )


def main() -> None:
    _print_banner()

    try:
        while True:
            try:
                user_input = console.input("[bold green]You > [/bold green]").strip()
            except EOFError:
                break

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                break

            asyncio.run(run_agent(user_input))

    except KeyboardInterrupt:
        console.print("\n[yellow]Session interrupted.[/yellow]")

    # Save session log
    log_path = history.save()
    console.print(f"\n[dim]Session log saved to: {log_path}[/dim]")
    console.print("[bold blue]Goodbye![/bold blue]")


if __name__ == "__main__":
    main()
