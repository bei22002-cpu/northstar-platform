"""Core agent loop — sends messages to Claude with automatic token rotation."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from agent_v2.config import API_KEYS
from agent_v2.history import SessionHistory
from agent_v2.safety import is_blocked, log_action
from agent_v2.token_manager import TokenManager
from agent_v2.tools import TOOL_DEFINITIONS, execute_tool

console = Console()

SYSTEM_PROMPT = (
    "You are an expert senior software engineer working on the "
    "Cornerstone Platform \u2014 a FastAPI + PostgreSQL backend project. "
    "You have direct access to the project workspace and can read, "
    "write, create, delete files, run commands, and search code.\n\n"
    "Rules:\n"
    "- Always read a file before overwriting it.\n"
    "- Never delete files unless the user explicitly requests it.\n"
    "- Always explain what you are about to do in plain English "
    "before using a tool.\n"
    "- Write clean, production-quality Python code.\n"
    "- Follow the existing project structure and conventions.\n"
    "- After completing a task, summarize what you did."
)

MODEL = "claude-opus-4-5"
MAX_TOKENS = 8096
MAX_PROMPT_CHARS = 600_000  # ~150K tokens — safe margin under 200K limit

# Shared session history (one per process lifetime)
history = SessionHistory()

# Token manager — handles key rotation automatically
token_manager = TokenManager(API_KEYS)


def _has_tool_result(msg: dict[str, Any]) -> bool:
    """Return True if *msg* contains tool_result blocks."""
    content = msg.get("content")
    if not isinstance(content, list):
        return False
    return any(
        isinstance(b, dict) and b.get("type") == "tool_result" for b in content
    )


def _trim_if_too_large(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop older messages if the serialised payload exceeds MAX_PROMPT_CHARS.

    Keeps the most recent messages so the agent stays under the API token limit.
    Always preserves at least the last message (the current user input).
    After trimming, drops any leading messages that contain orphaned
    tool_result blocks (whose matching tool_use was already trimmed away).
    """
    total = len(json.dumps(messages, default=str))
    if total <= MAX_PROMPT_CHARS:
        return messages

    console.print(
        f"[yellow]History too large ({total:,} chars) — trimming oldest messages...[/yellow]"
    )
    trimmed = list(messages)
    while len(trimmed) > 1 and len(json.dumps(trimmed, default=str)) > MAX_PROMPT_CHARS:
        trimmed.pop(0)

    # After trimming, the first message might be a user message with
    # tool_result blocks whose matching assistant tool_use was removed.
    # Drop these orphaned messages to avoid API errors.
    while len(trimmed) > 1 and _has_tool_result(trimmed[0]):
        trimmed.pop(0)

    # Also drop any leading assistant messages (API expects user first).
    while len(trimmed) > 1 and trimmed[0].get("role") == "assistant":
        trimmed.pop(0)

    return trimmed


async def run_agent(user_message: str) -> None:
    """Send *user_message* to Claude and handle tool-use loops.

    Uses the TokenManager to automatically rotate API keys when one key
    hits a rate limit or returns an error, ensuring continuous progress.
    """

    history.add_user(user_message)
    messages = history.get_messages()

    while True:
        # Repair any orphaned tool_use blocks left over from a previous
        # interrupted turn before we send messages to the API.
        history.sanitize()
        messages = history.get_messages()

        # Trim history if it's too large to avoid "prompt is too long" errors.
        messages = _trim_if_too_large(messages)

        console.print(
            f"[dim]Using API key #{token_manager.active_key_index} "
            f"of {token_manager.total_keys}[/dim]"
        )

        try:
            response = token_manager.create_message(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )
        except Exception as exc:
            if "prompt is too long" in str(exc):
                console.print(
                    "[yellow]Prompt too long — trimming history and retrying...[/yellow]"
                )
                history.clear()
                history.add_user(user_message)
                messages = history.get_messages()
                response = token_manager.create_message(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    tools=TOOL_DEFINITIONS,
                    messages=messages,
                )
            else:
                raise

        # Store the raw assistant content for future context
        history.add_assistant(response.content)
        messages = history.get_messages()

        # Print any text blocks the model returned
        for block in response.content:
            if hasattr(block, "text"):
                console.print(
                    Panel(
                        Markdown(block.text),
                        title="Cornerstone AI",
                        border_style="green",
                    )
                )

        # Collect any tool_use blocks regardless of stop_reason.
        # This prevents orphaned tool_use entries when stop_reason is
        # "max_tokens" or another unexpected value.
        tool_use_blocks = [
            b for b in response.content if getattr(b, "type", None) == "tool_use"
        ]

        if not tool_use_blocks:
            # No tools requested — we are done with this turn.
            break

        # Process every tool_use block and guarantee that a matching
        # tool_result is always appended, even if execution fails.
        tool_results: list[dict[str, Any]] = []
        for block in tool_use_blocks:
            tool_name: str = block.name
            tool_input: dict[str, Any] = block.input

            try:
                # Safety check — block dangerous commands
                if tool_name == "run_command" and is_blocked(
                    tool_input.get("command", "")
                ):
                    result = (
                        "BLOCKED: This command matches a dangerous pattern "
                        "and was not executed."
                    )
                    console.print(
                        f"[bold red]BLOCKED:[/bold red] {tool_input.get('command', '')}"
                    )
                else:
                    log_action(tool_name, tool_input)
                    result = execute_tool(tool_name, tool_input)
            except Exception as exc:
                result = f"Error executing tool: {exc}"
                console.print(
                    f"[bold red]Tool error ({tool_name}):[/bold red] {exc}"
                )

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                }
            )

        history.add_tool_results(tool_results)
        messages = history.get_messages()

        # If the original stop_reason was not "tool_use" (e.g. "max_tokens"),
        # do not loop back for another API call — the turn is over.
        if response.stop_reason != "tool_use":
            break
