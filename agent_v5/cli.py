"""CLI commands — init, ask, doctor, memory index, serve, stats."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def cmd_init() -> None:
    """Auto-detect hardware and recommend configuration."""
    from agent_v5.config import detect_hardware, recommend_engine, recommend_model

    console.print("[bold]Detecting hardware...[/bold]")
    hw = detect_hardware()

    table = Table(title="Hardware Detection")
    table.add_column("Property", style="bold")
    table.add_column("Value")

    table.add_row("Platform", hw.platform)
    table.add_row("CPU", hw.cpu)
    table.add_row("CPU Cores", str(hw.cpu_cores))
    table.add_row("RAM", f"{hw.ram_gb} GB")
    table.add_row("GPU Vendor", hw.gpu_vendor)
    table.add_row("GPU Name", hw.gpu_name or "N/A")
    table.add_row("VRAM", f"{hw.vram_gb} GB" if hw.vram_gb else "N/A")
    table.add_row("GPU Available", "Yes" if hw.has_gpu else "No")

    console.print(table)

    engine = recommend_engine(hw)
    model = recommend_model(hw, engine)
    console.print(f"\n[green]Recommended engine:[/green] {engine}")
    console.print(f"[green]Recommended model:[/green] {model}")

    if engine == "ollama":
        console.print(
            "\n[dim]To get started with Ollama:\n"
            "  1. Install: curl -fsSL https://ollama.com/install.sh | sh\n"
            "  2. Start:   ollama serve\n"
            f"  3. Pull:    ollama pull {model}\n"
            "  4. Run:     python -m agent_v5.main[/dim]"
        )
    else:
        console.print(
            f"\n[dim]To get started with {engine}:\n"
            "  1. Set your API key in agent_v5/.env\n"
            "  2. Run: python -m agent_v5.main[/dim]"
        )


def cmd_doctor() -> None:
    """Diagnose the environment and report issues."""
    from agent_v5.config import (
        ANTHROPIC_API_KEYS,
        OLLAMA_HOST,
        OPENAI_API_KEY,
        detect_hardware,
    )
    from agent_v5.engine.discovery import discover_engines

    console.print("[bold]Running diagnostics...[/bold]\n")
    issues: list[str] = []

    # Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    console.print(f"  Python: {py_ver}", end="")
    if sys.version_info < (3, 10):
        console.print(" [red]✗ (need 3.10+)[/red]")
        issues.append("Python 3.10+ required")
    else:
        console.print(" [green]OK[/green]")

    # Dependencies
    deps = {
        "anthropic": "Anthropic API",
        "rich": "Rich terminal UI",
        "chromadb": "ChromaDB vector memory (optional)",
        "fastapi": "API server (optional)",
        "uvicorn": "ASGI server (optional)",
    }
    for pkg, desc in deps.items():
        try:
            __import__(pkg)
            console.print(f"  {desc}: [green]installed[/green]")
        except ImportError:
            status = "[yellow]not installed[/yellow]"
            if "optional" not in desc:
                issues.append(f"{desc} not installed")
                status = "[red]not installed[/red]"
            console.print(f"  {desc}: {status}")

    # API keys
    console.print(f"\n  Anthropic keys: {len(ANTHROPIC_API_KEYS)}", end="")
    if ANTHROPIC_API_KEYS:
        console.print(" [green]OK[/green]")
    else:
        console.print(" [yellow]none set[/yellow]")

    console.print(f"  OpenAI key: {'set' if OPENAI_API_KEY else 'not set'}")

    # Engines
    console.print("\n  Discovering engines...")
    engines = discover_engines()
    for e in engines:
        console.print(f"    {e.engine_id}: [green]healthy[/green]")
    if not engines:
        console.print("    [red]No engines available![/red]")
        issues.append("No inference engine available")

    # Hardware
    hw = detect_hardware()
    console.print(f"\n  GPU: {hw.gpu_name or 'none'}")
    console.print(f"  RAM: {hw.ram_gb} GB")

    # Summary
    if issues:
        console.print(f"\n[red]Found {len(issues)} issue(s):[/red]")
        for issue in issues:
            console.print(f"  - {issue}")
    else:
        console.print("\n[green]All checks passed![/green]")


def cmd_memory_index(directory: str) -> None:
    """Index a directory into memory."""
    from agent_v5.config import MEMORY_BACKEND, MEMORY_DB_PATH
    from agent_v5.memory.ingest import ingest_directory
    from agent_v5.registry import MemoryRegistry

    # Force imports to register backends
    import agent_v5.memory.sqlite_backend  # noqa: F401
    import agent_v5.memory.vector_backend  # noqa: F401

    path = Path(directory).resolve()
    if not path.is_dir():
        console.print(f"[red]Error: {directory} is not a directory[/red]")
        return

    console.print(f"[bold]Indexing {path}...[/bold]")
    memory = MemoryRegistry.create(MEMORY_BACKEND, db_path=MEMORY_DB_PATH)

    files, chunks = ingest_directory(path, memory)
    console.print(
        f"[green]Done![/green] Indexed {files} files into {chunks} chunks "
        f"using {MEMORY_BACKEND} backend."
    )


def cmd_memory_stats() -> None:
    """Show memory statistics."""
    from agent_v5.config import MEMORY_BACKEND, MEMORY_DB_PATH
    from agent_v5.registry import MemoryRegistry

    import agent_v5.memory.sqlite_backend  # noqa: F401
    import agent_v5.memory.vector_backend  # noqa: F401

    try:
        memory = MemoryRegistry.create(MEMORY_BACKEND, db_path=MEMORY_DB_PATH)
    except Exception as e:
        console.print(f"[red]Error loading memory: {e}[/red]")
        return

    table = Table(title="Memory System")
    table.add_column("Property", style="bold")
    table.add_column("Value")
    table.add_row("Backend", MEMORY_BACKEND)
    table.add_row("Documents", str(memory.count()))
    table.add_row("DB Path", MEMORY_DB_PATH)
    console.print(table)


def cmd_stats() -> None:
    """Show session and trace statistics."""
    from agent_v5.learning.traces import TraceAnalyzer, TraceStore

    store = TraceStore()
    analyzer = TraceAnalyzer(store)
    stats = analyzer.summary()

    table = Table(title="Session Statistics")
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    table.add_row("Total Queries", str(stats["total_queries"]))
    table.add_row("Total Tokens In", f"{stats['total_tokens_in']:,}")
    table.add_row("Total Tokens Out", f"{stats['total_tokens_out']:,}")
    table.add_row("Total Cost", f"${stats['total_cost_usd']:.4f}")
    table.add_row("Avg Latency", f"{stats['avg_latency_ms']:.0f} ms")
    table.add_row("Tool Calls", str(stats["total_tool_calls"]))
    table.add_row("Errors", str(stats["error_count"]))
    table.add_row("Models Used", ", ".join(stats["models_used"]) or "none")
    table.add_row("Engines Used", ", ".join(stats["engines_used"]) or "none")
    console.print(table)


def cmd_serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the OpenAI-compatible API server."""
    try:
        import uvicorn
    except ImportError:
        console.print(
            "[red]uvicorn is required for the API server. "
            "Install with: pip install uvicorn[/red]"
        )
        return

    console.print(
        f"[bold]Starting Cornerstone AI API server on {host}:{port}[/bold]\n"
        f"OpenAI-compatible endpoint: http://{host}:{port}/v1/chat/completions\n"
        f"Health check: http://{host}:{port}/health\n"
        f"Models: http://{host}:{port}/v1/models\n"
    )
    uvicorn.run("agent_v5.server.api:app", host=host, port=port, reload=False)
