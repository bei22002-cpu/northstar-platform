"""Multi-agent orchestration (#2).

Allows spawning sub-agents that work in parallel on different tasks.
The main agent acts as an orchestrator, splitting work across workers.

Each worker runs in its own thread with its own history but shares
the token manager for API key rotation.
"""

from __future__ import annotations

import concurrent.futures
import threading
from dataclasses import dataclass, field
from typing import Any

import anthropic

from agent_v4.config import AVAILABLE_MODELS, MAX_TOKENS, get_system_prompt
from agent_v4.cost_tracker import CostTracker
from agent_v4.safety import check_safety, log_action
from agent_v4.token_manager import TokenManager
from agent_v4.tools import TOOL_DEFINITIONS, execute_tool


@dataclass
class WorkerResult:
    """Result from a single worker agent."""
    task: str
    success: bool
    output: str
    tokens_used: int = 0
    error: str = ""


@dataclass
class _WorkerContext:
    task: str
    token_manager: TokenManager
    model: str
    cost_tracker: CostTracker


def _run_worker(ctx: _WorkerContext) -> WorkerResult:
    """Run a single worker agent to completion in its own thread."""
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": ctx.task}
    ]
    output_parts: list[str] = []
    total_tokens = 0
    max_turns = 15  # prevent runaway loops

    system = get_system_prompt() + (
        "\n\nYou are a worker agent executing a specific sub-task. "
        "Complete the task efficiently and report what you did."
    )

    try:
        for _ in range(max_turns):
            response = ctx.token_manager.create_message(
                model=ctx.model,
                max_tokens=MAX_TOKENS,
                system=system,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

            if hasattr(response, "usage"):
                total_tokens += response.usage.input_tokens + response.usage.output_tokens
                ctx.cost_tracker.record(
                    ctx.model,
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                )

            # Serialize assistant content
            content_list = []
            for block in response.content:
                if hasattr(block, "text"):
                    output_parts.append(block.text)
                content_list.append(block)

            messages.append({"role": "assistant", "content": content_list})

            if response.stop_reason == "end_turn":
                break

            if response.stop_reason == "tool_use":
                tool_results: list[dict[str, Any]] = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    block_reason = check_safety(block.name, block.input)
                    if block_reason:
                        result = block_reason
                    else:
                        result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
                messages.append({"role": "user", "content": tool_results})
            else:
                break

        return WorkerResult(
            task=ctx.task,
            success=True,
            output="\n".join(output_parts),
            tokens_used=total_tokens,
        )

    except Exception as exc:
        return WorkerResult(
            task=ctx.task,
            success=False,
            output="",
            tokens_used=total_tokens,
            error=str(exc),
        )


class Orchestrator:
    """Orchestrates multiple worker agents for parallel task execution."""

    def __init__(
        self,
        token_manager: TokenManager,
        cost_tracker: CostTracker,
        model: str = "claude-sonnet-4-5-20250514",
        max_workers: int = 3,
    ) -> None:
        self._token_manager = token_manager
        self._cost_tracker = cost_tracker
        self._model = model
        self._max_workers = max_workers

    def run_parallel(self, tasks: list[str]) -> list[WorkerResult]:
        """Run multiple tasks in parallel using worker agents.

        Returns results in the same order as the input tasks.
        """
        if not tasks:
            return []

        contexts = [
            _WorkerContext(
                task=task,
                token_manager=self._token_manager,
                model=self._model,
                cost_tracker=self._cost_tracker,
            )
            for task in tasks
        ]

        results: list[WorkerResult] = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(self._max_workers, len(tasks))
        ) as executor:
            futures = {
                executor.submit(_run_worker, ctx): i
                for i, ctx in enumerate(contexts)
            }

            # Collect results in order
            indexed_results: dict[int, WorkerResult] = {}
            for future in concurrent.futures.as_completed(futures):
                idx = futures[future]
                try:
                    indexed_results[idx] = future.result()
                except Exception as exc:
                    indexed_results[idx] = WorkerResult(
                        task=tasks[idx],
                        success=False,
                        output="",
                        error=str(exc),
                    )

            results = [indexed_results[i] for i in range(len(tasks))]

        return results

    def format_results(self, results: list[WorkerResult]) -> str:
        """Format worker results into a readable summary."""
        lines: list[str] = [f"## Multi-Agent Results ({len(results)} workers)\n"]
        for i, r in enumerate(results, 1):
            status = "SUCCESS" if r.success else "FAILED"
            lines.append(f"### Worker {i}: {status}")
            lines.append(f"**Task:** {r.task}")
            if r.output:
                lines.append(f"**Output:**\n{r.output[:2000]}")
            if r.error:
                lines.append(f"**Error:** {r.error}")
            lines.append(f"**Tokens:** {r.tokens_used:,}")
            lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool definitions for the agent
# ---------------------------------------------------------------------------

MULTI_AGENT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "run_parallel_tasks",
        "description": (
            "Split work across multiple AI worker agents that execute in parallel. "
            "Each task gets its own agent that can use all available tools. "
            "Great for refactoring multiple files, running parallel analyses, etc. "
            "Maximum 5 parallel workers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of task descriptions for each worker agent",
                    "maxItems": 5,
                },
            },
            "required": ["tasks"],
        },
    },
]
