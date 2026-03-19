"""Core agent loop — sends messages to Claude and handles tool-use."""

from __future__ import annotations

from typing import Any

import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from agent.config import ANTHROPIC_API_KEY
from agent.history import SessionHistory
from agent.safety import ask_approval
from agent.tools import TOOL_DEFINITIONS, execute_tool

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

# Shared session history (one per process lifetime)
history = SessionHistory()


async def run_agent(user_message: str) -> None:
    """Send *user_message* to Claude and handle tool-use loops."""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    history.add_user(user_message)

    messages = history.get_messages()

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

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

        # If the model is done talking, break
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

                approved = ask_approval(tool_name, tool_input)
                if approved:
                    result = execute_tool(tool_name, tool_input)
                else:
                    result = "User denied this action."

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

            history.add_tool_results(tool_results)
            messages = history.get_messages()
        else:
            # Unexpected stop reason — break to avoid infinite loops
            break
