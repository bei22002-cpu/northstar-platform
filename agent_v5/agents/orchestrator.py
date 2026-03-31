"""OrchestratorAgent — multi-turn tool-calling loop."""

from __future__ import annotations

from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel

from agent_v5.agents.base import AgentContext, AgentResult, BaseAgent
from agent_v5.registry import AgentRegistry

console = Console()

_MAX_TURNS = 25


@AgentRegistry.register("orchestrator")
class OrchestratorAgent(BaseAgent):
    """Multi-turn agent that calls tools in a loop until done."""

    agent_id = "orchestrator"
    accepts_tools = True

    def __init__(self, *args: Any, tools: Optional[list[Any]] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._tools = tools or []
        self._tool_map: dict[str, Any] = {}
        for t in self._tools:
            self._tool_map[t.tool_id] = t

    def _tool_definitions(self) -> list[dict[str, Any]]:
        """Convert tools to API-compatible definitions."""
        defs: list[dict[str, Any]] = []
        for t in self._tools:
            defs.append(t.to_definition())
        return defs

    def run(
        self,
        user_input: str,
        context: Optional[AgentContext] = None,
        **kwargs: Any,
    ) -> AgentResult:
        system, messages = self._build_messages(user_input, context)
        tool_defs = self._tool_definitions()

        total_in = 0
        total_out = 0
        total_latency = 0.0
        tool_calls_made: list[str] = []
        turns = 0

        while turns < _MAX_TURNS:
            turns += 1

            result = self.engine.generate(
                messages,
                self.model,
                config=self.config,
                tools=tool_defs if tool_defs else None,
                system=system,
            )

            total_in += result.tokens_in
            total_out += result.tokens_out
            total_latency += result.latency_ms

            # Add assistant response text
            if result.text:
                messages.append({"role": "assistant", "content": result.text})

            # If no tool calls, we're done
            if not result.tool_calls:
                return AgentResult(
                    text=result.text,
                    tool_calls_made=tool_calls_made,
                    tokens_in=total_in,
                    tokens_out=total_out,
                    latency_ms=total_latency,
                    turns=turns,
                    model=result.model,
                )

            # Process tool calls
            # Build assistant message with tool_use content for Anthropic format
            assistant_content: list[dict[str, Any]] = []
            if result.text:
                assistant_content.append({"type": "text", "text": result.text})
            for tc in result.tool_calls:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["arguments"],
                })

            # Replace last assistant message with full content
            if messages and messages[-1].get("role") == "assistant":
                messages[-1] = {"role": "assistant", "content": assistant_content}
            else:
                messages.append({"role": "assistant", "content": assistant_content})

            tool_results: list[dict[str, Any]] = []
            for tc in result.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                tool_calls_made.append(tool_name)

                console.print(
                    Panel(
                        f"Tool: {tool_name}\n"
                        + "\n".join(f"{k}: {v}" for k, v in tool_args.items()),
                        title="Executing",
                        border_style="cyan",
                    )
                )

                tool = self._tool_map.get(tool_name)
                if tool is None:
                    output = f"Error: unknown tool '{tool_name}'"
                else:
                    try:
                        output = tool.execute(**tool_args)
                    except Exception as exc:
                        output = f"Error: {exc}"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": str(output),
                })

            messages.append({"role": "user", "content": tool_results})

        # Max turns reached
        return AgentResult(
            text="[Max turns reached — stopping.]",
            tool_calls_made=tool_calls_made,
            tokens_in=total_in,
            tokens_out=total_out,
            latency_ms=total_latency,
            turns=turns,
            model=self.model,
        )
