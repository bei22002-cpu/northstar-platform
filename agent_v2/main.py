"""Entry-point for the Cornerstone AI Agent v2 — Claude Code Edition.

Includes Claude Code-inspired features: frustration detection, auto-compact,
hook system, sub-agents, undercover mode, enhanced permissions, persistent
memory, and improved system prompt.
"""

from __future__ import annotations

import asyncio

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agent_v2.config import API_KEYS, WORKSPACE
from agent_v2.hooks import fire_simple, load_hooks_from_config
from agent_v2.memory import memory_store
from agent_v2.permissions import permissions
from agent_v2.session import history, run_agent, token_manager
from agent_v2.undercover import is_undercover_enabled

console = Console()


def _print_banner() -> None:
    banner = Text()
    banner.append("Cornerstone AI Agent v2 — Claude Code Edition\n", style="bold magenta")
    banner.append(f"Workspace: {WORKSPACE}\n", style="dim")
    banner.append(f"API Keys loaded: {len(API_KEYS)}\n", style="bold cyan")
    banner.append(
        "Fully autonomous with Claude Code-inspired features.\n",
        style="bold green",
    )

    # Feature status
    features: list[str] = [
        "Frustration detection",
        "Auto-compact (summarization)",
        "Hook system",
        "Sub-agents (Task tool)",
        f"Permissions ({permissions.preset_name})",
        f"Memory ({memory_store.count} facts)",
    ]
    if is_undercover_enabled():
        features.append("Undercover mode ACTIVE")
    banner.append(
        "Features: " + ", ".join(features) + "\n",
        style="dim",
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
    banner.append(
        "Commands: /keys /memory /hooks /compact /permissions /undercover /help\n",
        style="dim",
    )
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


def _print_help() -> None:
    """Print available commands."""
    help_text = Table(title="Commands")
    help_text.add_column("Command", style="bold cyan")
    help_text.add_column("Description")
    help_text.add_row("/keys", "Show API key status and rotation stats")
    help_text.add_row("/memory", "Show persistent memory entries")
    help_text.add_row("/memory clear", "Clear all stored memories")
    help_text.add_row("/memory distill", "Consolidate memories via LLM")
    help_text.add_row("/hooks", "Show registered hooks")
    help_text.add_row("/compact", "Show auto-compact status")
    help_text.add_row("/permissions", "Show permission policy status")
    help_text.add_row("/undercover", "Show undercover mode status")
    help_text.add_row("/help", "Show this help message")
    help_text.add_row("exit / quit", "End the session")
    console.print(help_text)


def _print_memory() -> None:
    """Show persistent memory entries."""
    memories = memory_store.get_all()
    if not memories:
        console.print("[dim]No memories stored yet.[/dim]")
        return
    table = Table(title=f"Persistent Memory ({len(memories)} entries)")
    table.add_column("#", style="bold")
    table.add_column("Type", style="cyan")
    table.add_column("Content")
    table.add_column("Tags", style="dim")
    table.add_column("Importance", justify="right")
    for i, mem in enumerate(memories[-20:], 1):  # Show last 20
        table.add_row(
            str(i),
            mem.get("type", "fact"),
            mem.get("content", "")[:80],
            ", ".join(mem.get("tags", [])),
            f"{mem.get('importance', 0.5):.1f}",
        )
    console.print(table)


def _print_hooks() -> None:
    """Show registered hooks."""
    from agent_v2.hooks import get_hook_status
    status = get_hook_status()
    table = Table(title="Hook System")
    table.add_column("Event", style="bold cyan")
    table.add_column("Hooks", justify="right")
    for event, count in status.items():
        table.add_row(event, str(count))
    console.print(table)


def _print_compact_status() -> None:
    """Show auto-compact status."""
    from agent_v2.compact import get_compact_summary, _compaction_disabled, _consecutive_failures
    console.print(Panel(
        f"Disabled: {_compaction_disabled}\n"
        f"Consecutive failures: {_consecutive_failures}\n"
        f"Summary available: {'Yes' if get_compact_summary() else 'No'}",
        title="Auto-Compact Status",
        border_style="cyan",
    ))


def _print_permissions() -> None:
    """Show permission policy status."""
    status = permissions.get_status()
    console.print(Panel(
        f"Preset: {status['preset']}\n"
        f"Description: {status['description']}\n"
        f"Denied tools: {status['denied_tools'] or 'none'}\n"
        f"Denied path patterns: {status['denied_path_patterns']}\n"
        f"Denied command patterns: {status['denied_command_patterns']}",
        title="Permission Policy",
        border_style="cyan",
    ))


def _print_undercover() -> None:
    """Show undercover mode status."""
    if is_undercover_enabled():
        console.print(Panel(
            "Undercover mode is [bold green]ACTIVE[/bold green].\n"
            "AI attribution will be stripped from git commits and PR descriptions.\n"
            "Set CORNERSTONE_UNDERCOVER=0 to disable.",
            title="Undercover Mode",
            border_style="green",
        ))
    else:
        console.print(Panel(
            "Undercover mode is [dim]inactive[/dim].\n"
            "Set CORNERSTONE_UNDERCOVER=1 to enable.",
            title="Undercover Mode",
            border_style="dim",
        ))


def main() -> None:
    # Load hooks from config file if present
    import os
    hooks_config = os.path.join(os.path.dirname(__file__), "hooks.json")
    if os.path.isfile(hooks_config):
        load_hooks_from_config(hooks_config)

    # Fire SessionStart hooks
    fire_simple("SessionStart")

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

            # Handle slash commands
            if user_input.lower() in ("/keys", "keys"):
                _print_key_stats()
                continue
            if user_input.lower() == "/help":
                _print_help()
                continue
            if user_input.lower() == "/memory":
                _print_memory()
                continue
            if user_input.lower() == "/memory clear":
                memory_store.clear()
                continue
            if user_input.lower() == "/memory distill":
                console.print("[dim]Distilling memories...[/dim]")
                result = memory_store.distill(
                    create_message_fn=token_manager.create_message
                )
                console.print(f"[cyan]{result}[/cyan]")
                continue
            if user_input.lower() == "/hooks":
                _print_hooks()
                continue
            if user_input.lower() == "/compact":
                _print_compact_status()
                continue
            if user_input.lower() == "/permissions":
                _print_permissions()
                continue
            if user_input.lower() == "/undercover":
                _print_undercover()
                continue

            asyncio.run(run_agent(user_input))

    except KeyboardInterrupt:
        console.print("\n[yellow]Session interrupted.[/yellow]")

    # Fire SessionEnd hooks
    fire_simple("SessionEnd")

    # Save session log
    log_path = history.save()
    console.print(f"\n[dim]Session log saved to: {log_path}[/dim]")
    _print_key_stats()
    console.print("[bold blue]Goodbye![/bold blue]")


if __name__ == "__main__":
    main()
