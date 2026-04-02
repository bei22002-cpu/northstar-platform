"""Sub-agent / Task tool — spawn focused sub-agents with separate context.

Inspired by Claude Code's Agent Teams and ``Task`` tool.  A sub-agent
gets its own conversation history and a narrowly scoped system prompt,
executes a focused task, and returns the result to the parent agent.

This prevents context pollution: the sub-agent's tool calls don't bloat
the parent's history.
"""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel

console = Console()

# Maximum turns a sub-agent can take before forced termination
MAX_SUBAGENT_TURNS = 15

# Maximum chars for sub-agent output returned to parent
MAX_SUBAGENT_OUTPUT = 10_000


def run_subagent(
    task: str,
    context: str = "",
    create_message_fn: Any = None,
    tools: list[dict[str, Any]] | None = None,
    execute_tool_fn: Any = None,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
) -> str:
    """Spawn a sub-agent to handle a focused task.

    Parameters
    ----------
    task : str
        The task description for the sub-agent.
    context : str
        Optional context from the parent conversation.
    create_message_fn : callable
        The TokenManager's ``create_message`` method.
    tools : list
        Tool definitions available to the sub-agent.
    execute_tool_fn : callable
        Function to execute tools (from tools.py).
    model : str
        Model to use for the sub-agent (defaults to Sonnet for speed/cost).
    max_tokens : int
        Max tokens per sub-agent response.

    Returns
    -------
    str
        The sub-agent's final text output, or an error message.
    """
    if create_message_fn is None:
        return "Error: Sub-agent requires a create_message function."

    console.print(
        Panel(
            f"[bold]Task:[/bold] {task[:200]}",
            title="Sub-Agent Spawned",
            border_style="cyan",
        )
    )

    sub_system_prompt = (
        "You are a focused sub-agent working on a specific task. "
        "You have access to workspace tools. Complete the task efficiently "
        "and report your results clearly.\n\n"
        "Rules:\n"
        "- Stay focused on the assigned task only.\n"
        "- Be concise in your responses.\n"
        "- Report what you did and what you found.\n"
        "- If you cannot complete the task, explain why.\n"
    )

    if context:
        sub_system_prompt += f"\n\nParent context:\n{context}"

    # Sub-agent's own history — completely isolated from parent
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": task},
    ]

    collected_output: list[str] = []
    turns = 0

    while turns < MAX_SUBAGENT_TURNS:
        turns += 1

        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "system": sub_system_prompt,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools

            response = create_message_fn(**kwargs)
        except Exception as exc:
            error_msg = f"Sub-agent API error on turn {turns}: {exc}"
            console.print(f"[red]{error_msg}[/red]")
            collected_output.append(error_msg)
            break

        # Store assistant response
        assistant_content = _make_serializable(response.content)
        messages.append({"role": "assistant", "content": assistant_content})

        # Collect text output
        for block in response.content:
            if hasattr(block, "text") and block.text:
                collected_output.append(block.text)

        # Check for tool use
        tool_use_blocks = [
            b for b in response.content if getattr(b, "type", None) == "tool_use"
        ]

        if not tool_use_blocks:
            # Sub-agent is done
            break

        if execute_tool_fn is None:
            collected_output.append("Sub-agent has no tool executor — stopping.")
            break

        # Execute tools
        tool_results: list[dict[str, Any]] = []
        for block in tool_use_blocks:
            try:
                from agent_v2.safety import is_blocked
                if block.name == "run_command" and is_blocked(
                    block.input.get("command", "")
                ):
                    result = "BLOCKED: Dangerous command blocked in sub-agent."
                else:
                    result = execute_tool_fn(block.name, block.input)
            except Exception as exc:
                result = f"Sub-agent tool error: {exc}"

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

            console.print(
                f"[dim]  Sub-agent tool: {block.name} -> "
                f"{result[:100]}{'...' if len(result) > 100 else ''}[/dim]"
            )

        messages.append({"role": "user", "content": tool_results})

        if response.stop_reason != "tool_use":
            break

    # Build final output
    final_output = "\n\n".join(collected_output)
    if len(final_output) > MAX_SUBAGENT_OUTPUT:
        final_output = (
            final_output[:MAX_SUBAGENT_OUTPUT]
            + f"\n\n... (sub-agent output truncated at {MAX_SUBAGENT_OUTPUT:,} chars)"
        )

    console.print(
        Panel(
            f"Completed in {turns} turn(s)",
            title="Sub-Agent Done",
            border_style="green",
        )
    )

    return final_output


def _make_serializable(obj: Any) -> Any:
    """Recursively convert API objects to plain dicts/lists for JSON."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_make_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    return obj
