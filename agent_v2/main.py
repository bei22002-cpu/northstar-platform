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

from agent_v2.config import API_KEYS, WORKSPACE, get_provider_name
from agent_v2.hooks import fire_simple, load_hooks_from_config
from agent_v2.kairos import (
    add_goal,
    clear_queue,
    get_state,
    print_config as kairos_print_config,
    print_queue as kairos_print_queue,
    remove_goal,
    reset_state as kairos_reset,
    run_kairos,
    set_budget,
)
from agent_v2.memory import memory_store
from agent_v2.permissions import permissions
from agent_v2.session import history, run_agent, token_manager
from agent_v2.tools import TOOL_DEFINITIONS, execute_tool
from agent_v2.printing3d import print_3d_status
from agent_v2.gamedev import print_gamedev_status
from agent_v2.undercover import is_undercover_enabled

console = Console()


def _print_banner() -> None:
    banner = Text()
    provider = get_provider_name()
    banner.append("Cornerstone AI Agent v2 — Claude Code Edition\n", style="bold magenta")
    banner.append(f"Workspace: {WORKSPACE}\n", style="dim")
    if provider in ("claude", "anthropic"):
        banner.append(f"Provider: Claude | API Keys loaded: {len(API_KEYS)}\n", style="bold cyan")
    elif provider in ("openclaw", "openclaw-zero-token", "zerotok"):
        import os
        oc_model = os.getenv("OPENCLAW_MODEL", "claude-sonnet-4-20250514")
        banner.append(f"Provider: OpenClaw Zero Token | Model: {oc_model} | FREE\n", style="bold green")
    elif provider == "ollama":
        import os
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        banner.append(f"Provider: Ollama (local) | Model: {ollama_model} | FREE\n", style="bold green")
    elif provider in ("gemini", "google"):
        banner.append(f"Provider: Google Gemini | FREE tier\n", style="bold green")
    else:
        banner.append(f"Provider: {provider}\n", style="bold cyan")
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
    # KAIROS queue status
    kairos_state = get_state()
    kairos_pending = sum(1 for g in kairos_state.goals if g.status.value == "pending")
    features.append(f"KAIROS ({kairos_pending} queued)")
    features.append("3D Printing")
    features.append("Game Dev")
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
        "Commands: /keys /model /memory /hooks /compact /permissions /undercover /kairos /3dprint /gamedev /help\n",
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
    help_text.add_row("/model", "Show current AI provider (Claude, Ollama, or Gemini)")
    help_text.add_row("/3dprint", "Show 3D printing module status")
    help_text.add_row("/gamedev", "Show game development module status")
    help_text.add_row("/kairos", "Show KAIROS queue status")
    help_text.add_row("/kairos add <goal>", "Add a goal to the KAIROS queue")
    help_text.add_row("/kairos remove <#>", "Remove a pending goal by index")
    help_text.add_row("/kairos run", "Start autonomous KAIROS run")
    help_text.add_row("/kairos config", "Show KAIROS budget configuration")
    help_text.add_row("/kairos budget <calls> <mins> <turns>", "Set budget limits")
    help_text.add_row("/kairos dream", "Trigger dream distillation now")
    help_text.add_row("/kairos clear", "Clear all pending goals")
    help_text.add_row("/kairos reset", "Full reset of KAIROS state")
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


def _print_model_info() -> None:
    """Show current AI provider and model info."""
    provider = get_provider_name()
    import os
    info = f"Active provider: [bold]{provider}[/bold]\n\n"
    if provider in ("claude", "anthropic"):
        info += (
            f"Model: claude-opus-4-5\n"
            f"API Keys loaded: {len(API_KEYS)}\n"
            f"Cost: ~$15/M input, ~$75/M output tokens\n\n"
            "To switch to a free provider, set in agent_v2/.env:\n"
            "  PROVIDER=openclaw (FREE — uses OpenClaw Zero Token gateway)\n"
            "  PROVIDER=ollama   (FREE — local, needs Ollama installed)\n"
            "  PROVIDER=gemini   (FREE tier — cloud, needs GEMINI_API_KEY)"
        )
    elif provider in ("openclaw", "openclaw-zero-token", "zerotok"):
        oc_model = os.getenv("OPENCLAW_MODEL", "claude-sonnet-4-20250514")
        oc_url = os.getenv("OPENCLAW_BASE_URL", "http://localhost:18789")
        info += (
            f"Model: {oc_model}\n"
            f"Gateway: {oc_url}\n"
            f"Cost: FREE (via browser session)\n\n"
            "Supported: Claude, ChatGPT, Gemini, DeepSeek, Grok, Qwen, and more\n"
            "Change model in .env: OPENCLAW_MODEL=deepseek-chat\n"
            "Setup: github.com/linuxhsj/openclaw-zero-token"
        )
    elif provider == "ollama":
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        info += (
            f"Model: {ollama_model}\n"
            f"URL: {ollama_url}\n"
            f"Cost: FREE (runs locally)\n\n"
            "Change model in .env: OLLAMA_MODEL=mistral\n"
            "Available: tinyllama, phi3:mini, llama3.1:8b, mistral, codellama"
        )
    elif provider in ("gemini", "google"):
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        info += (
            f"Model: {gemini_model}\n"
            f"Cost: FREE tier (15 req/min with Flash)\n\n"
            "Get API key: https://aistudio.google.com/app/apikey\n"
            "Change model in .env: GEMINI_MODEL=gemini-1.5-pro"
        )
    console.print(Panel(info, title="AI Provider", border_style="cyan"))


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

            # --- KAIROS commands ---
            if user_input.lower() == "/kairos":
                kairos_print_queue()
                continue
            if user_input.lower().startswith("/kairos add "):
                goal_text = user_input[len("/kairos add "):].strip()
                if goal_text:
                    add_goal(goal_text)
                else:
                    console.print("[yellow]Usage: /kairos add <goal description>[/yellow]")
                continue
            if user_input.lower().startswith("/kairos remove "):
                try:
                    idx = int(user_input.split()[-1])
                    if not remove_goal(idx):
                        console.print("[yellow]Invalid index. Use /kairos to see the queue.[/yellow]")
                except ValueError:
                    console.print("[yellow]Usage: /kairos remove <index number>[/yellow]")
                continue
            if user_input.lower() == "/kairos run":
                console.print(
                    "[bold magenta]Starting KAIROS autonomous mode...[/bold magenta]"
                )
                result = run_kairos(
                    create_message_fn=token_manager.create_message,
                    tools=[
                        t for t in TOOL_DEFINITIONS if t["name"] != "task"
                    ],
                    execute_tool_fn=execute_tool,
                )
                console.print(f"[cyan]{result}[/cyan]")
                continue
            if user_input.lower() == "/kairos config":
                kairos_print_config()
                continue
            if user_input.lower().startswith("/kairos budget"):
                parts = user_input.split()
                try:
                    calls = int(parts[2]) if len(parts) > 2 else None
                    mins = int(parts[3]) if len(parts) > 3 else None
                    turns = int(parts[4]) if len(parts) > 4 else None
                    set_budget(
                        max_api_calls=calls,
                        max_wall_clock_mins=mins,
                        max_turns_per_goal=turns,
                    )
                except (ValueError, IndexError):
                    console.print(
                        "[yellow]Usage: /kairos budget <max_calls> <max_mins> <max_turns>[/yellow]"
                    )
                continue
            if user_input.lower() == "/kairos dream":
                console.print("[magenta]Triggering dream distillation...[/magenta]")
                from agent_v2.dream import run_dream
                dream_result = run_dream(
                    create_message_fn=token_manager.create_message
                )
                console.print(f"[magenta]{dream_result}[/magenta]")
                continue
            if user_input.lower() == "/kairos clear":
                clear_queue()
                continue
            if user_input.lower() == "/kairos reset":
                kairos_reset()
                continue

            # --- Model/Provider command ---
            if user_input.lower() == "/model":
                _print_model_info()
                continue

            # --- 3D Printing commands ---
            if user_input.lower() == "/3dprint":
                print_3d_status()
                continue

            # --- Game Dev commands ---
            if user_input.lower() == "/gamedev":
                print_gamedev_status()
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
