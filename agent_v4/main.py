"""CLI entry point for the Cornerstone AI Agent v4.

All v3 features plus:
- RAG codebase search (auto-indexed on startup)
- Multi-agent parallel tasks
- GitHub integration (branches, commits, PRs)
- Auto test generation & running
- Persistent memory across sessions
- Linting & type checking
- Custom system prompts
- Slack bot mode (run with --slack flag)
"""

from __future__ import annotations

import asyncio
import subprocess
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agent_v4.config import API_KEYS, AVAILABLE_MODELS, MAX_TOKENS, WORKSPACE
from agent_v4.session import (
    codebase_index,
    cost_tracker,
    current_model,
    history,
    index_codebase,
    knowledge_base,
    run_agent,
    set_model,
    token_manager,
)

console = Console()


def _show_banner() -> None:
    banner = Text()
    banner.append("Cornerstone AI Agent v4 — Full-Featured + RAG + Multi-Agent\n", style="bold magenta")
    banner.append(f"Workspace: {WORKSPACE}\n", style="dim")
    banner.append(f"API Keys loaded: {len(API_KEYS)}\n", style="bold cyan")
    banner.append(f"Model: {current_model}\n", style="bold cyan")
    banner.append(f"Memory: {knowledge_base.count} stored facts\n", style="bold cyan")
    banner.append(
        "Fully autonomous — executes tools without approval prompts.\n",
        style="bold green",
    )

    banner.append("\nCommands:\n", style="bold")
    banner.append("  exit/quit       — End session\n", style="dim")
    banner.append("  keys            — API key stats\n", style="dim")
    banner.append("  cost            — Token usage & cost\n", style="dim")
    banner.append("  model <name>    — Switch model (opus/sonnet/haiku)\n", style="dim")
    banner.append("  undo            — Revert last agent change\n", style="dim")
    banner.append("  sessions        — List saved sessions\n", style="dim")
    banner.append("  resume <file>   — Resume a saved session\n", style="dim")
    banner.append("  clear           — Clear conversation history\n", style="dim")
    banner.append("  memory          — Show all stored memories\n", style="dim")
    banner.append("  reindex         — Re-index codebase for RAG\n", style="dim")
    banner.append("  --slack         — Launch as Slack bot (pass as CLI arg)\n", style="dim")

    console.print(Panel(banner, title="Welcome", border_style="cyan"))


def _show_keys() -> None:
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
    console.print(Panel(cost_tracker.summary(), title="Token Usage & Cost", border_style="yellow"))


def _show_sessions() -> None:
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


def _show_memory() -> None:
    memories = knowledge_base.list_all()
    if not memories:
        console.print("[dim]No memories stored. The agent can use 'remember' to store facts.[/dim]")
        return
    table = Table(title="Persistent Memory")
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")
    table.add_column("Updated", style="dim")
    for m in memories:
        table.add_row(m["key"], m["value"], m["updated_at"])
    console.print(table)


def _resume_session(arg: str) -> None:
    import os
    sessions = history.list_sessions()
    try:
        idx = int(arg) - 1
        if 0 <= idx < len(sessions):
            filepath = sessions[idx]["path"]
        else:
            console.print("[red]Invalid session number.[/red]")
            return
    except ValueError:
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        filepath = os.path.join(log_dir, arg)

    if history.load(filepath):
        console.print(f"[green]Resumed session from {filepath}[/green]")
        console.print(f"[dim]Loaded {history.message_count} messages.[/dim]")
    else:
        console.print(f"[red]Failed to load session: {filepath}[/red]")


def _undo() -> None:
    try:
        result = subprocess.run(
            "git log --oneline -1",
            shell=True, capture_output=True, text=True,
            timeout=5, cwd=WORKSPACE,
        )
        if "[agent_v4]" in result.stdout:
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
    # Check for --slack flag
    if "--slack" in sys.argv:
        from agent_v4.slack_bot import start_slack_bot
        start_slack_bot()
        return

    _show_banner()

    # Auto-index codebase for RAG on startup
    index_codebase()

    while True:
        try:
            user_input = console.input("[bold green]You > [/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue

        lower = user_input.lower()

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
        if lower == "memory":
            _show_memory()
            continue
        if lower == "clear":
            history.clear()
            console.print("[green]History cleared.[/green]")
            continue
        if lower == "undo":
            _undo()
            continue
        if lower == "reindex":
            index_codebase()
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

        try:
            asyncio.run(run_agent(user_input))
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
        except Exception as exc:
            console.print(f"\n[bold red]Error:[/bold red] {exc}")

    # Cleanup
    log_path = history.save()
    console.print(f"\n[dim]Session log saved to: {log_path}[/dim]")
    _show_keys()
    _show_cost()
    console.print("\n[bold magenta]Goodbye![/bold magenta]")


if __name__ == "__main__":
    main()
