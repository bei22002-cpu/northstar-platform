"""Entry-point for the Cornerstone AI Agent v2 — with token rotation."""

from __future__ import annotations

import asyncio

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agent_v2.config import API_KEYS, WORKSPACE
from agent_v2.session import (
    context_builder,
    history,
    memory_retriever,
    run_agent,
    structured_state,
    summary_memory,
    token_manager,
    vector_store,
)

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
    banner.append(
        "Hybrid memory system active (state, summary, semantic).\n",
        style="bold yellow",
    )
    banner.append("Type 'exit' or 'quit' to end the session.\n", style="dim")
    banner.append("Type 'keys' to see token status.\n", style="dim")
    banner.append("Type 'memory' for memory stats.\n", style="dim")
    banner.append("Type 'state' to view structured state.\n", style="dim")
    banner.append("Type 'summary' to view conversation summary.\n", style="dim")
    banner.append("Type 'forget' to clear all memory.", style="dim")
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


def _print_memory_stats() -> None:
    """Display memory system statistics."""
    table = Table(title="Memory System")
    table.add_column("Component", style="bold")
    table.add_column("Details", style="dim")

    # Structured state
    state_data = structured_state.all()
    table.add_row("Structured State", f"{len(state_data)} attribute(s)")

    # Summary memory
    summary = summary_memory.summary
    table.add_row(
        "Summary Memory",
        f"{summary_memory.turn_count} turns summarised"
        + (f" ({len(summary)} chars)" if summary else " (empty)"),
    )

    # Vector store
    count = vector_store.count()
    table.add_row("Semantic Memory", f"{count} stored embedding(s)")

    # Token budget
    usage = context_builder.get_token_usage(
        history.get_messages(), current_query=""
    )
    table.add_row(
        "Token Budget",
        f"{usage['total']:,} / {usage['budget']:,} tokens"
        f" ({usage['total'] * 100 // max(usage['budget'], 1)}% used)",
    )
    table.add_row("  System Prompt", f"{usage['system_prompt']:,} tokens")
    table.add_row("  State", f"{usage['structured_state']:,} tokens")
    table.add_row("  Summary", f"{usage['summary']:,} tokens")
    table.add_row("  Semantic", f"{usage['semantic_memory']:,} tokens")
    table.add_row("  Messages", f"{usage['messages']:,} tokens")

    console.print(table)


def _print_state() -> None:
    """Display the structured state."""
    state_data = structured_state.all()
    if not state_data:
        console.print("[dim]Structured state is empty.[/dim]")
        return
    table = Table(title="Structured State")
    table.add_column("Key", style="bold")
    table.add_column("Value")
    for k, v in state_data.items():
        table.add_row(k, str(v))
    console.print(table)


def _print_summary() -> None:
    """Display the conversation summary."""
    summary = summary_memory.summary
    if not summary:
        console.print("[dim]No conversation summary yet.[/dim]")
        return
    console.print(
        Panel(
            summary,
            title=f"Conversation Summary ({summary_memory.turn_count} turns)",
            border_style="yellow",
        )
    )


def _forget_all() -> None:
    """Clear all memory components."""
    structured_state.clear()
    summary_memory.clear()
    vector_store.clear()
    history.clear()
    console.print("[bold yellow]All memory cleared.[/bold yellow]")


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
            if user_input.lower() == "memory":
                _print_memory_stats()
                continue
            if user_input.lower() == "state":
                _print_state()
                continue
            if user_input.lower() == "summary":
                _print_summary()
                continue
            if user_input.lower() == "forget":
                _forget_all()
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
