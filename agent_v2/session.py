"""Core agent loop — sends messages to Claude with automatic token rotation.

Integrates Claude Code-inspired features:
- Frustration detection with adaptive tone
- Auto-compact with summarization (instead of just clearing history)
- Hook system for pre/post tool execution
- Sub-agent dispatch via Task tool
- Undercover mode for git operations
- Enhanced permission checks
- Persistent memory across sessions
"""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from agent_v2.compact import compact_history, get_compact_summary, should_compact
from agent_v2.config import API_KEYS
from agent_v2.history import SessionHistory
from agent_v2.hooks import fire_post_tool_use, fire_pre_tool_use, fire_simple
from agent_v2.memory import extract_facts_from_turn, memory_store
from agent_v2.permissions import permissions
from agent_v2.safety import is_blocked, log_action
from agent_v2.sentiment import Sentiment, detect_sentiment
from agent_v2.subagent import run_subagent
from agent_v2.token_manager import TokenManager
from agent_v2.tools import TOOL_DEFINITIONS, execute_tool
from agent_v2.undercover import get_undercover_prompt

console = Console()

# ---------------------------------------------------------------------------
# System prompt — Claude Code-inspired structured instructions
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are Cornerstone AI — an expert autonomous coding agent working on "
    "the user's project. You have direct access to the workspace and can "
    "read, write, create, delete files, run commands, and search code.\n\n"
    "## Core Rules\n"
    "- Always read a file before overwriting it.\n"
    "- Never delete files unless the user explicitly requests it.\n"
    "- Explain what you are about to do before using a tool.\n"
    "- Write clean, production-quality code.\n"
    "- Follow the existing project structure and conventions.\n"
    "- After completing a task, summarize what you did.\n\n"
    "## Tool Use Best Practices\n"
    "- Prefer targeted reads over listing entire directories.\n"
    "- When writing large files, break them into smaller chunks if needed.\n"
    "- Always provide BOTH 'filepath' and 'content' when using write_file.\n"
    "- Use search_in_files to find code before making changes.\n"
    "- Check git_status before and after making changes.\n\n"
    "## Task Tool\n"
    "- Use the 'task' tool to delegate focused sub-tasks.\n"
    "- Sub-tasks get their own context window — use them for complex, "
    "multi-step operations that would bloat the main conversation.\n"
    "- Good candidates: code generation, refactoring, research, analysis.\n\n"
    "## Error Handling\n"
    "- If a tool call fails, analyze the error and retry with corrections.\n"
    "- If write_file fails due to missing content, retry with the content "
    "argument explicitly included.\n"
    "- Never repeat the exact same failing tool call more than twice.\n"
)

MODEL = "claude-opus-4-5"
MAX_TOKENS = 8096
MAX_PROMPT_CHARS = 600_000  # ~150K tokens — safe margin under 200K limit

# Shared session history (one per process lifetime)
history = SessionHistory()

# Token manager — handles key rotation automatically
token_manager = TokenManager(API_KEYS)


def _build_system_prompt(user_message: str) -> str:
    """Build the full system prompt with dynamic additions.

    Incorporates:
    - Base system prompt
    - Sentiment-based tone adjustments
    - Undercover mode instructions
    - Persistent memory context
    - Auto-compact summary (if any)
    """
    prompt = SYSTEM_PROMPT

    # Sentiment detection — adjust tone if user is frustrated/confused/urgent
    sentiment_result = detect_sentiment(user_message)
    if sentiment_result.sentiment != Sentiment.NEUTRAL:
        console.print(
            f"[dim]Sentiment: {sentiment_result.sentiment.value} "
            f"(matched: {sentiment_result.matched_keyword})[/dim]"
        )
    prompt += sentiment_result.tone_instruction

    # Undercover mode
    prompt += get_undercover_prompt()

    # Persistent memory — inject relevant memories
    memory_context = memory_store.get_context_block(query=user_message)
    if memory_context:
        prompt += f"\n\n{memory_context}"

    # Auto-compact summary from previous compaction
    compact_summary = get_compact_summary()
    if compact_summary:
        prompt += (
            f"\n\n[COMPACTED CONTEXT — summary of earlier conversation]\n"
            f"{compact_summary}\n"
            f"[END COMPACTED CONTEXT]"
        )

    return prompt


def _safe_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a clean message list that the API will accept.

    Uses auto-compact when possible (summarizes old messages instead of
    dropping them).  Falls back to clearing history if compaction fails.
    """
    total = len(json.dumps(messages, default=str))
    if total <= MAX_PROMPT_CHARS:
        return messages

    # Try smart compaction first
    if should_compact(messages):
        console.print(
            f"[yellow]History large ({total:,} chars) — attempting auto-compact...[/yellow]"
        )
        try:
            return compact_history(
                messages,
                create_message_fn=token_manager.create_message,
            )
        except Exception as exc:
            console.print(f"[yellow]Auto-compact failed: {exc}[/yellow]")

    # Fallback: clear and keep last user message
    console.print(
        f"[yellow]History too large ({total:,} chars) — clearing and starting fresh...[/yellow]"
    )
    last_user = None
    for msg in reversed(messages):
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            last_user = msg
            break
    if last_user:
        return [last_user]
    return messages[-1:]


async def run_agent(user_message: str) -> None:
    """Send *user_message* to Claude and handle tool-use loops.

    Integrates all Claude Code-inspired features: hooks, permissions,
    sentiment detection, auto-compact, sub-agents, memory.
    """
    # Fire UserPromptSubmit hooks
    from agent_v2.hooks import fire_user_prompt
    prompt_result = fire_user_prompt(user_message)
    if prompt_result["rejected"]:
        console.print(
            f"[yellow]Message rejected by hook: {prompt_result['reason']}[/yellow]"
        )
        return
    user_message = prompt_result["message"]

    history.add_user(user_message)
    messages = history.get_messages()

    # Build dynamic system prompt
    system_prompt = _build_system_prompt(user_message)

    while True:
        # Repair any orphaned tool_use blocks
        history.sanitize()
        messages = history.get_messages()

        # Trim/compact history if too large
        messages = _safe_messages(messages)

        console.print(
            f"[dim]Using API key #{token_manager.active_key_index} "
            f"of {token_manager.total_keys}[/dim]"
        )

        try:
            response = token_manager.create_message(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )
        except Exception as exc:
            err_msg = str(exc)
            if any(kw in err_msg for kw in (
                "prompt is too long", "tool_use_id", "tool_result", "tool_use"
            )):
                console.print(
                    "[yellow]Bad history detected — clearing and retrying...[/yellow]"
                )
                history.clear()
                history.add_user(user_message)
                messages = history.get_messages()
                response = token_manager.create_message(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=system_prompt,
                    tools=TOOL_DEFINITIONS,
                    messages=messages,
                )
            else:
                raise

        # Store the raw assistant content
        history.add_assistant(response.content)
        messages = history.get_messages()

        # Collect assistant text for memory extraction
        assistant_text = ""

        # Print text blocks
        for block in response.content:
            if hasattr(block, "text"):
                assistant_text += block.text
                console.print(
                    Panel(
                        Markdown(block.text),
                        title="Cornerstone AI",
                        border_style="green",
                    )
                )

        # Extract and store facts from this turn (non-blocking)
        try:
            facts = extract_facts_from_turn(user_message, assistant_text)
            for fact in facts:
                memory_store.add(
                    content=fact["content"],
                    memory_type=fact["type"],
                    tags=fact.get("tags", []),
                    importance=fact.get("importance", 0.5),
                )
        except Exception:
            pass  # Memory extraction should never crash the agent

        # Collect tool_use blocks
        tool_use_blocks = [
            b for b in response.content if getattr(b, "type", None) == "tool_use"
        ]

        if not tool_use_blocks:
            break

        # Process every tool_use block
        tool_results: list[dict[str, Any]] = []
        for block in tool_use_blocks:
            tool_name: str = block.name
            tool_input: dict[str, Any] = block.input

            try:
                # Enhanced permission check
                allowed, reason = permissions.check_tool_call(tool_name, tool_input)
                if not allowed:
                    result = f"PERMISSION DENIED: {reason}"
                    console.print(
                        f"[bold red]PERMISSION DENIED:[/bold red] {reason}"
                    )
                # Legacy safety check for run_command
                elif tool_name == "run_command" and is_blocked(
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
                    # Fire PreToolUse hooks
                    pre_result = fire_pre_tool_use(tool_name, tool_input)
                    if pre_result["blocked"]:
                        result = f"BLOCKED by hook: {pre_result['reason']}"
                        console.print(
                            f"[yellow]Tool blocked by hook: {pre_result['reason']}[/yellow]"
                        )
                    else:
                        tool_input = pre_result["tool_input"]
                        log_action(tool_name, tool_input)

                        # Handle sub-agent Task tool specially
                        if tool_name == "task":
                            result = run_subagent(
                                task=tool_input.get("task", ""),
                                context=tool_input.get("context", ""),
                                create_message_fn=token_manager.create_message,
                                tools=[
                                    t for t in TOOL_DEFINITIONS
                                    if t["name"] != "task"
                                ],
                                execute_tool_fn=execute_tool,
                            )
                        else:
                            result = execute_tool(tool_name, tool_input)

                        # Fire PostToolUse hooks
                        result = fire_post_tool_use(tool_name, tool_input, result)

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

        if response.stop_reason != "tool_use":
            break
