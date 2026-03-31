"""Main entry point — CLI dispatcher for agent_v5."""

from __future__ import annotations

import argparse
import sys
import time

from rich.console import Console
from rich.panel import Panel

console = Console()

BANNER = """[bold cyan]Cornerstone AI Agent v5 — Jarvis Edition[/bold cyan]
[dim]Local-first · Multi-backend · Production-grade[/dim]"""


def _interactive_loop(args: argparse.Namespace) -> None:
    """Run the interactive agent REPL."""
    # Lazy imports to avoid loading everything for subcommands
    from agent_v5.config import (
        ANTHROPIC_API_KEYS,
        DEFAULT_ENGINE,
        DEFAULT_MODEL,
        MEMORY_BACKEND,
        MEMORY_DB_PATH,
        WORKSPACE,
    )
    from agent_v5.engine.discovery import get_engine
    from agent_v5.history import SessionHistory
    from agent_v5.learning.telemetry import TelemetryTracker
    from agent_v5.learning.traces import TraceStore
    from agent_v5.memory.context import inject_context
    from agent_v5.registry import AgentRegistry, MemoryRegistry, ToolRegistry
    from agent_v5.types import GenerationConfig

    # Force registrations
    import agent_v5.agents.simple  # noqa: F401
    import agent_v5.agents.orchestrator  # noqa: F401
    import agent_v5.agents.react  # noqa: F401
    import agent_v5.memory.sqlite_backend  # noqa: F401
    import agent_v5.memory.vector_backend  # noqa: F401
    import agent_v5.tools.filesystem  # noqa: F401
    import agent_v5.tools.terminal  # noqa: F401
    import agent_v5.tools.web  # noqa: F401
    import agent_v5.tools.calculator  # noqa: F401
    import agent_v5.sandbox.runner  # noqa: F401

    # Initialize subsystems
    engine = get_engine(DEFAULT_ENGINE)
    agent_type = getattr(args, "agent", "orchestrator")
    agent = AgentRegistry.create(agent_type, engine=engine)

    memory = None
    try:
        memory = MemoryRegistry.create(MEMORY_BACKEND, db_path=MEMORY_DB_PATH)
    except Exception:
        pass

    history = SessionHistory()
    trace_store = TraceStore()
    telemetry = TelemetryTracker()

    tools = ToolRegistry.list_all()
    tool_defs = [t.to_definition() for t in tools]

    console.print(Panel(BANNER, expand=False))
    console.print(f"  Engine: [green]{engine.engine_id}[/green]")
    console.print(f"  Model:  [green]{DEFAULT_MODEL}[/green]")
    console.print(f"  Agent:  [green]{agent_type}[/green]")
    console.print(f"  Memory: [green]{MEMORY_BACKEND}[/green]")
    console.print(f"  Tools:  [green]{len(tools)}[/green]")
    if ANTHROPIC_API_KEYS:
        console.print(f"  API Keys: [green]{len(ANTHROPIC_API_KEYS)}[/green]")
    console.print(
        f"  Workspace: {WORKSPACE}\n"
        f"\n  Type [bold]exit[/bold] to quit, [bold]stats[/bold] for usage, "
        f"[bold]forget[/bold] to clear history.\n"
    )

    while True:
        try:
            user_input = console.input("[bold green]You >[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break
        if user_input.lower() == "stats":
            from agent_v5.cli import cmd_stats
            cmd_stats()
            continue
        if user_input.lower() == "forget":
            history.clear()
            console.print("[yellow]History cleared.[/yellow]")
            continue

        # Build context from memory
        mem_context = ""
        if memory:
            try:
                mem_context = inject_context(user_input, memory)
            except Exception:
                pass

        # Build agent context
        from agent_v5.agents.base import AgentContext
        context = AgentContext(
            conversation_history=history.get_recent(20),
            system_prompt=(
                "You are Cornerstone AI, a helpful and capable assistant. "
                "Use tools when needed. Be concise and accurate."
            ),
            memory_context=mem_context,
        )

        # Run agent
        start = time.time()
        trace = trace_store.new_trace(
            query=user_input,
            agent_type=agent_type,
            engine_id=engine.engine_id,
            model=DEFAULT_MODEL,
        )
        trace.start_time = time.time()

        try:
            result = agent.run(user_input, context, tools=tool_defs)
            elapsed_ms = (time.time() - start) * 1000

            console.print(Panel(result.text, title="Cornerstone AI", border_style="cyan"))

            # Update history
            history.add_user(user_input)
            history.add_assistant(result.text)

            # Update trace
            trace.end_time = time.time()
            trace.tokens_in = result.tokens_in
            trace.tokens_out = result.tokens_out
            trace.latency_ms = elapsed_ms
            trace.tool_calls = [str(tc) for tc in result.tool_calls_made]
            trace.result = result.text
            trace_store.save(trace)

            # Update telemetry
            telemetry.record(
                tokens_in=result.tokens_in,
                tokens_out=result.tokens_out,
                latency_ms=elapsed_ms,
                tool_calls=len(result.tool_calls_made),
                model=result.model,
                engine=engine.engine_id,
            )

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            trace.error = str(e)
            trace.end_time = time.time()
            trace_store.save(trace)

    # Save history on exit
    history.save()
    summary = telemetry.summary()
    console.print(
        f"\n[dim]Session: {summary['total_queries']} queries, "
        f"{summary['total_tokens_in'] + summary['total_tokens_out']:,} tokens, "
        f"${summary['total_cost_usd']:.4f}[/dim]"
    )
    console.print("[bold]Goodbye![/bold]")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agent_v5",
        description="Cornerstone AI Agent v5 — Jarvis Edition",
    )
    sub = parser.add_subparsers(dest="command")

    # init
    sub.add_parser("init", help="Detect hardware and recommend configuration")

    # ask
    ask_p = sub.add_parser("ask", help="Send a single query to the agent")
    ask_p.add_argument("query", nargs="+", help="The question to ask")
    ask_p.add_argument("--agent", default="simple", help="Agent type (default: simple)")
    ask_p.add_argument("--engine", default="auto", help="Engine (default: auto)")
    ask_p.add_argument("--model", default="", help="Model override")

    # doctor
    sub.add_parser("doctor", help="Run environment diagnostics")

    # memory
    mem_p = sub.add_parser("memory", help="Memory management")
    mem_sub = mem_p.add_subparsers(dest="memory_command")
    idx = mem_sub.add_parser("index", help="Index a directory")
    idx.add_argument("directory", help="Directory to index")
    mem_sub.add_parser("stats", help="Show memory statistics")

    # serve
    serve_p = sub.add_parser("serve", help="Start the API server")
    serve_p.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    serve_p.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")

    # stats
    sub.add_parser("stats", help="Show usage statistics")

    # interactive (default)
    interactive_p = sub.add_parser("chat", help="Interactive chat mode")
    interactive_p.add_argument(
        "--agent", default="orchestrator", help="Agent type (default: orchestrator)"
    )

    args = parser.parse_args()

    if args.command is None or args.command == "chat":
        _interactive_loop(args)
    elif args.command == "init":
        from agent_v5.cli import cmd_init
        cmd_init()
    elif args.command == "ask":
        _cmd_ask(args)
    elif args.command == "doctor":
        from agent_v5.cli import cmd_doctor
        cmd_doctor()
    elif args.command == "memory":
        if args.memory_command == "index":
            from agent_v5.cli import cmd_memory_index
            cmd_memory_index(args.directory)
        elif args.memory_command == "stats":
            from agent_v5.cli import cmd_memory_stats
            cmd_memory_stats()
        else:
            mem_p.print_help()
    elif args.command == "serve":
        from agent_v5.cli import cmd_serve
        cmd_serve(args.host, args.port)
    elif args.command == "stats":
        from agent_v5.cli import cmd_stats
        cmd_stats()


def _cmd_ask(args: argparse.Namespace) -> None:
    """Handle the ask subcommand — single query, print result."""
    from agent_v5.config import DEFAULT_ENGINE, DEFAULT_MODEL
    from agent_v5.engine.discovery import get_engine
    from agent_v5.registry import AgentRegistry
    from agent_v5.agents.base import AgentContext

    import agent_v5.agents.simple  # noqa: F401
    import agent_v5.agents.orchestrator  # noqa: F401
    import agent_v5.agents.react  # noqa: F401

    engine_pref = args.engine if args.engine != "auto" else DEFAULT_ENGINE
    engine = get_engine(engine_pref)
    agent = AgentRegistry.create(args.agent, engine=engine)

    query = " ".join(args.query)
    context = AgentContext(
        system_prompt="You are a helpful assistant. Be concise.",
    )

    result = agent.run(query, context)
    console.print(result.text)


if __name__ == "__main__":
    main()
