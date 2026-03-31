"""Core agent loop — sends messages to Claude with automatic token rotation.

Integrates the hybrid memory system:
- Structured state (persistent user attributes)
- Summary memory (compressed past conversations)
- Semantic memory (vector-based retrieval of relevant context)
- Memory writer (LLM-powered fact extraction)
- Context builder (assembles minimal-token prompts)
- Token guard (hard limit enforcement)
"""

from __future__ import annotations

from typing import Any

import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from agent_v2.config import API_KEYS
from agent_v2.core.context_builder import ContextBuilder
from agent_v2.core.token_guard import TokenGuard
from agent_v2.history import SessionHistory
from agent_v2.memory.retrieval import MemoryRetriever
from agent_v2.memory.state import StructuredState
from agent_v2.memory.summary import SummaryMemory
from agent_v2.memory.vector_store import VectorStore
from agent_v2.memory.writer import extract_facts
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

# ── Memory system configuration ─────────────────────────────────────────
SHORT_TERM_WINDOW = 20       # Recent messages to keep verbatim
SUMMARY_THRESHOLD = 20       # Summarise when history exceeds this
TOKEN_BUDGET = 16_000        # Hard token limit for assembled prompt

# ── Shared instances (one per process lifetime) ─────────────────────────
history = SessionHistory()
token_manager = TokenManager(API_KEYS)

# Memory components
structured_state = StructuredState()
summary_memory = SummaryMemory()
vector_store = VectorStore()
memory_retriever = MemoryRetriever(vector_store)
token_guard = TokenGuard(max_tokens=TOKEN_BUDGET)
context_builder = ContextBuilder(
    state=structured_state,
    summary=summary_memory,
    retriever=memory_retriever,
    token_guard=token_guard,
    system_prompt=SYSTEM_PROMPT,
)


async def _llm_call(system: str, user_msg: str) -> str:
    """Single-turn LLM call used by the memory writer and summariser.

    Uses Sonnet for a balance of speed and quality on internal memory
    management tasks.
    """
    try:
        response = token_manager.create_message(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""
    except Exception:
        return ""


async def run_agent(user_message: str) -> None:
    """Send *user_message* to Claude and handle tool-use loops.

    Integrates the hybrid memory system:
    1. Extract structured facts from the user message
    2. Store the user message in semantic memory
    3. Summarise older messages if history is too long
    4. Build context-enriched prompt via ContextBuilder
    5. Run the agent loop with TokenGuard enforcement
    """

    # ── Step 1: Extract structured facts from user input ────────────────
    facts = await extract_facts(user_message, llm_call=_llm_call)
    if facts:
        structured_state.update(facts)
        console.print(
            f"[dim]Memory: extracted {len(facts)} fact(s): "
            f"{', '.join(facts.keys())}[/dim]"
        )

    # ── Step 2: Store user message in semantic memory ───────────────────
    memory_retriever.store_interaction(user_message, role="user")

    # ── Step 3: Add to history and summarise if needed ──────────────────
    history.add_user(user_message)

    # Summarise old messages to keep the window bounded
    raw_messages = history.get_messages()
    if len(raw_messages) > SUMMARY_THRESHOLD:
        trimmed = await summary_memory.maybe_summarize(
            raw_messages,
            keep_recent=SHORT_TERM_WINDOW,
            llm_call=_llm_call,
        )
        # Replace history with only the recent messages
        history.clear()
        for msg in trimmed:
            if msg["role"] == "user":
                if isinstance(msg["content"], list):
                    history.add_tool_results(msg["content"])
                else:
                    history.add_user(msg["content"])
            elif msg["role"] == "assistant":
                history.add_assistant(msg["content"])
        console.print(
            f"[dim]Memory: summarised {len(raw_messages) - len(trimmed)} "
            f"older messages[/dim]"
        )

    while True:
        # Repair any orphaned tool_use blocks
        history.sanitize()
        messages = history.get_messages()

        # ── Step 4: Build context-enriched prompt ───────────────────────
        enriched_system, trimmed_messages = context_builder.build(
            messages, current_query=user_message
        )

        console.print(
            f"[dim]Using API key #{token_manager.active_key_index} "
            f"of {token_manager.total_keys}[/dim]"
        )

        try:
            response = token_manager.create_message(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=enriched_system,
                tools=TOOL_DEFINITIONS,
                messages=trimmed_messages,
            )
        except anthropic.BadRequestError as exc:
            # Prompt too long — aggressively trim history and retry once
            console.print(
                "[yellow]Prompt too long — trimming history and retrying...[/yellow]"
            )
            # Keep only the last 4 messages (2 turns)
            history.clear()
            history.add_user(user_message)
            messages = history.get_messages()
            enriched_system, trimmed_messages = context_builder.build(
                messages, current_query=user_message
            )
            try:
                response = token_manager.create_message(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=enriched_system,
                    tools=TOOL_DEFINITIONS,
                    messages=trimmed_messages,
                )
            except anthropic.BadRequestError:
                console.print(
                    "[bold red]Error: prompt still too long after trimming. "
                    "Try 'forget' to clear all memory, then retry.[/bold red]"
                )
                return

        # Store the raw assistant content for future context
        history.add_assistant(response.content)

        # Collect assistant text for semantic memory
        assistant_text_parts: list[str] = []

        # Print any text blocks the model returned
        for block in response.content:
            if hasattr(block, "text"):
                assistant_text_parts.append(block.text)
                console.print(
                    Panel(
                        Markdown(block.text),
                        title="Cornerstone AI",
                        border_style="green",
                    )
                )

        # Store assistant response in semantic memory
        if assistant_text_parts:
            full_response = "\n".join(assistant_text_parts)
            memory_retriever.store_interaction(full_response, role="assistant")

        # Collect any tool_use blocks regardless of stop_reason.
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
                    console.print(
                        Panel(
                            f"Tool: {tool_name}\n"
                            + "\n".join(
                                f"{k}: {v}" for k, v in tool_input.items()
                            ),
                            title="Executing",
                            border_style="cyan",
                        )
                    )
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

        if response.stop_reason != "tool_use":
            break
