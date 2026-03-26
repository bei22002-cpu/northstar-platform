"""Core agent loop with streaming responses, cost tracking, and auto-context.

Sends messages to Claude via the TokenManager with automatic key rotation.
Streams responses word-by-word for real-time feedback.  Injects project
context on first message.  Tracks token usage and cost.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from agent_v3.config import API_KEYS, AVAILABLE_MODELS, DEFAULT_MODEL, MAX_TOKENS, WORKSPACE
from agent_v3.cost_tracker import CostTracker
from agent_v3.history import SessionHistory
from agent_v3.safety import check_safety, log_action
from agent_v3.token_manager import TokenManager
from agent_v3.tools import TOOL_DEFINITIONS, execute_tool

console = Console()

SYSTEM_PROMPT = (
    "You are an expert senior software engineer working on the "
    "Cornerstone Platform — a FastAPI + PostgreSQL backend project. "
    "You have direct access to the project workspace and can read, "
    "write, create, delete, patch files, run commands, and search code.\n\n"
    "Rules:\n"
    "- Always read a file before overwriting it.\n"
    "- Prefer patch_file over write_file when editing existing files.\n"
    "- Never delete files unless the user explicitly requests it.\n"
    "- Always explain what you are about to do in plain English "
    "before using a tool.\n"
    "- Write clean, production-quality Python code.\n"
    "- Follow the existing project structure and conventions.\n"
    "- After completing a task, summarize what you did."
)

# Shared session state (one per process lifetime)
history = SessionHistory()
cost_tracker = CostTracker()

# Current model (can be changed mid-session)
current_model: str = AVAILABLE_MODELS.get(DEFAULT_MODEL, "claude-sonnet-4-5-20250514")

# Token manager
token_manager = TokenManager(API_KEYS)

# Track whether we've injected project context
_context_injected: bool = False


def set_model(model_key: str) -> str:
    """Switch the active model. Returns confirmation or error."""
    global current_model
    if model_key in AVAILABLE_MODELS:
        current_model = AVAILABLE_MODELS[model_key]
        return f"Switched to {model_key} ({current_model})"
    return f"Unknown model '{model_key}'. Available: {', '.join(AVAILABLE_MODELS.keys())}"


def _get_project_context() -> str:
    """Read key project files to inject as context on first message."""
    context_parts: list[str] = []

    # Try to read README
    readme_path = os.path.join(WORKSPACE, "..", "README.md")
    if os.path.isfile(readme_path):
        try:
            with open(readme_path, encoding="utf-8") as f:
                content = f.read()[:2000]  # cap at 2000 chars
            context_parts.append(f"## Project README (truncated)\n{content}")
        except OSError:
            pass

    # Get directory structure (top 2 levels)
    try:
        result = subprocess.run(
            "find . -maxdepth 2 -type f | head -50",
            shell=True, capture_output=True, text=True,
            timeout=5, cwd=WORKSPACE,
        )
        if result.stdout.strip():
            context_parts.append(f"## Project file structure\n{result.stdout.strip()}")
    except (subprocess.TimeoutExpired, OSError):
        pass

    if context_parts:
        return ("\n\n---\n\nHere is context about the project you are working in "
                "(auto-injected on startup):\n\n" + "\n\n".join(context_parts))
    return ""


def _git_auto_commit(message: str) -> None:
    """Auto-commit current workspace state for undo/rollback support."""
    try:
        subprocess.run(
            "git add -A && git commit -m " + repr(message) + " --allow-empty",
            shell=True, capture_output=True, text=True,
            timeout=10, cwd=WORKSPACE,
        )
    except (subprocess.TimeoutExpired, OSError):
        pass


async def run_agent(user_message: str) -> None:
    """Send *user_message* to Claude and handle the tool-use loop.

    Streams the response text in real time.  Automatically injects project
    context on the first message.
    """
    global _context_injected

    # Inject project context on first message
    if not _context_injected:
        context = _get_project_context()
        if context:
            enriched = user_message + context
        else:
            enriched = user_message
        _context_injected = True
    else:
        enriched = user_message

    history.add_user(enriched)
    messages = history.get_messages()

    # Auto-commit before agent makes changes (for undo support)
    _git_auto_commit("[agent_v3] checkpoint before agent action")

    while True:
        console.print(
            f"[dim]Using API key #{token_manager.active_key_index} "
            f"of {token_manager.total_keys} | Model: {current_model}[/dim]"
        )

        try:
            # Use streaming for real-time output
            with token_manager.create_message_stream(
                model=current_model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            ) as stream:
                response = _handle_stream(stream)

        except anthropic.BadRequestError:
            console.print(
                "[yellow]History was corrupted — resetting and retrying.[/yellow]"
            )
            history.clear()
            history.add_user(enriched)
            messages = history.get_messages()
            with token_manager.create_message_stream(
                model=current_model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
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

        # Store assistant response in history
        history.add_assistant(response.content)
        messages = history.get_messages()

        # If the model is done, break
        if response.stop_reason == "end_turn":
            break

        # Handle tool_use blocks
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
    collected_text: list[str] = []
    started_text = False

    for event in stream:
        if hasattr(event, "type"):
            if event.type == "content_block_start":
                if hasattr(event, "content_block") and event.content_block.type == "text":
                    started_text = True
                    console.print("\n[green]Cornerstone AI:[/green] ", end="")
            elif event.type == "content_block_delta":
                if hasattr(event, "delta") and hasattr(event.delta, "text"):
                    text = event.delta.text
                    collected_text.append(text)
                    console.print(text, end="", highlight=False)
            elif event.type == "content_block_stop":
                if started_text:
                    console.print()  # newline after text block
                    started_text = False

    return stream.get_final_message()
