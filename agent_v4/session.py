"""Core agent loop with streaming, cost tracking, RAG, memory, and multi-agent.

Sends messages to Claude via the TokenManager with automatic key rotation.
Streams responses word-by-word. Injects project context + memory on first
message. Tracks token usage and cost. Handles multi-agent orchestration.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

import anthropic
from rich.console import Console
from rich.panel import Panel

from agent_v4.config import (
    API_KEYS, AVAILABLE_MODELS, DEFAULT_MODEL, MAX_TOKENS, WORKSPACE,
    get_system_prompt,
)
from agent_v4.cost_tracker import CostTracker
from agent_v4.history import SessionHistory
from agent_v4.memory import KnowledgeBase
from agent_v4.multi_agent import Orchestrator
from agent_v4.rag import CodebaseIndex
from agent_v4.safety import check_safety, log_action
from agent_v4.token_manager import TokenManager
from agent_v4.tools import TOOL_DEFINITIONS, execute_tool

console = Console()

# Shared session state
history = SessionHistory()
cost_tracker = CostTracker()
knowledge_base = KnowledgeBase()
codebase_index = CodebaseIndex()

# Current model
current_model: str = AVAILABLE_MODELS.get(DEFAULT_MODEL, "claude-sonnet-4-5-20250514")

# Token manager
token_manager = TokenManager(API_KEYS)

# Track context injection
_context_injected: bool = False


def set_model(model_key: str) -> str:
    """Switch the active model."""
    global current_model
    if model_key in AVAILABLE_MODELS:
        current_model = AVAILABLE_MODELS[model_key]
        return f"Switched to {model_key} ({current_model})"
    return f"Unknown model '{model_key}'. Available: {', '.join(AVAILABLE_MODELS.keys())}"


def index_codebase() -> dict[str, int]:
    """Index the workspace for RAG search."""
    console.print("[dim]Indexing codebase for semantic search...[/dim]")
    stats = codebase_index.index_workspace(WORKSPACE)
    console.print(
        f"[dim]Indexed {stats['files_indexed']} files "
        f"({stats['chunks_created']} chunks)[/dim]"
    )
    # Make index available globally for tools
    import agent_v4
    agent_v4._shared_index = codebase_index
    return stats


def _get_project_context() -> str:
    """Build context string from README + file structure + memory."""
    parts: list[str] = []

    # README
    readme_path = os.path.join(WORKSPACE, "..", "README.md")
    if os.path.isfile(readme_path):
        try:
            with open(readme_path, encoding="utf-8") as f:
                content = f.read()[:2000]
            parts.append(f"## Project README (truncated)\n{content}")
        except OSError:
            pass

    # File structure
    try:
        result = subprocess.run(
            "find . -maxdepth 2 -type f | head -50",
            shell=True, capture_output=True, text=True,
            timeout=5, cwd=WORKSPACE,
        )
        if result.stdout.strip():
            parts.append(f"## Project file structure\n{result.stdout.strip()}")
    except (subprocess.TimeoutExpired, OSError):
        pass

    # Persistent memory
    mem_context = knowledge_base.get_context_string()
    if mem_context:
        parts.append(mem_context)

    if parts:
        return ("\n\n---\n\nHere is context about the project you are working in "
                "(auto-injected on startup):\n\n" + "\n\n".join(parts))
    return ""


def _git_auto_commit(message: str) -> None:
    """Auto-commit for undo/rollback support."""
    try:
        subprocess.run(
            "git add -A && git commit -m " + repr(message) + " --allow-empty",
            shell=True, capture_output=True, text=True,
            timeout=10, cwd=WORKSPACE,
        )
    except (subprocess.TimeoutExpired, OSError):
        pass


async def run_agent(user_message: str) -> None:
    """Send user_message to Claude and handle the tool-use loop with streaming."""
    global _context_injected

    # Inject context on first message
    if not _context_injected:
        context = _get_project_context()
        enriched = user_message + context if context else user_message
        _context_injected = True
    else:
        enriched = user_message

    history.add_user(enriched)
    messages = history.get_messages()

    _git_auto_commit("[agent_v4] checkpoint before agent action")

    while True:
        console.print(
            f"[dim]Using API key #{token_manager.active_key_index} "
            f"of {token_manager.total_keys} | Model: {current_model}[/dim]"
        )

        try:
            with token_manager.create_message_stream(
                model=current_model,
                max_tokens=MAX_TOKENS,
                system=get_system_prompt(),
                tools=TOOL_DEFINITIONS,
                messages=messages,
            ) as stream:
                response = _handle_stream(stream)

        except anthropic.BadRequestError:
            console.print(
                "[yellow]History corrupted — resetting and retrying.[/yellow]"
            )
            history.clear()
            history.add_user(enriched)
            messages = history.get_messages()
            with token_manager.create_message_stream(
                model=current_model,
                max_tokens=MAX_TOKENS,
                system=get_system_prompt(),
                tools=TOOL_DEFINITIONS,
                messages=messages,
            ) as stream:
                response = _handle_stream(stream)

        # Track cost
        if hasattr(response, "usage"):
            cost_tracker.record(
                current_model,
                response.usage.input_tokens,
                response.usage.output_tokens,
            )

        history.add_assistant(response.content)
        messages = history.get_messages()

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            tool_results: list[dict[str, Any]] = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name: str = block.name
                tool_input: dict[str, Any] = block.input

                # Safety check
                block_reason = check_safety(tool_name, tool_input)
                if block_reason:
                    result = block_reason
                    console.print(f"[bold red]{block_reason}[/bold red]")
                else:
                    log_action(tool_name, tool_input)

                    # Handle multi-agent orchestration specially
                    if tool_name == "run_parallel_tasks":
                        tasks = tool_input.get("tasks", [])
                        orchestrator = Orchestrator(
                            token_manager=token_manager,
                            cost_tracker=cost_tracker,
                            model=current_model,
                        )
                        console.print(
                            f"[bold magenta]Spawning {len(tasks)} worker agents...[/bold magenta]"
                        )
                        worker_results = orchestrator.run_parallel(tasks)
                        result = orchestrator.format_results(worker_results)
                    else:
                        result = execute_tool(tool_name, tool_input)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            history.add_tool_results(tool_results)
            messages = history.get_messages()
        else:
            break


def _handle_stream(stream: Any) -> Any:
    """Process a streaming response, printing text in real time."""
    started_text = False

    for event in stream:
        if hasattr(event, "type"):
            if event.type == "content_block_start":
                if hasattr(event, "content_block") and event.content_block.type == "text":
                    started_text = True
                    console.print("\n[green]Cornerstone AI:[/green] ", end="")
            elif event.type == "content_block_delta":
                if hasattr(event, "delta") and hasattr(event.delta, "text"):
                    console.print(event.delta.text, end="", highlight=False)
            elif event.type == "content_block_stop":
                if started_text:
                    console.print()
                    started_text = False

    return stream.get_final_message()
