"""ReActAgent — Thought-Action-Observation reasoning loop."""

from __future__ import annotations

from typing import Any, Optional

from rich.console import Console

from agent_v5.agents.base import AgentContext, AgentResult, BaseAgent
from agent_v5.registry import AgentRegistry

console = Console()

_MAX_TURNS = 15

_REACT_SYSTEM = """\
You are a ReAct agent.  For each step, you MUST output exactly one of:

Thought: <your reasoning about what to do next>
Action: <tool_name> <json_arguments>
Observation: (this will be filled in by the system)
Final Answer: <your final response to the user>

Rules:
- Always start with a Thought.
- After each Thought, pick an Action.
- After seeing the Observation, decide whether you need another Thought+Action or can give a Final Answer.
- Never output more than one section at a time.
"""


@AgentRegistry.register("react")
class ReActAgent(BaseAgent):
    """Thought-Action-Observation loop inspired by ReAct."""

    agent_id = "react"
    accepts_tools = True

    def __init__(self, *args: Any, tools: Optional[list[Any]] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._tools = tools or []
        self._tool_map: dict[str, Any] = {}
        for t in self._tools:
            self._tool_map[t.tool_id] = t

    def _tool_descriptions(self) -> str:
        lines: list[str] = ["Available tools:"]
        for t in self._tools:
            defn = t.to_definition()
            lines.append(f"- {defn['name']}: {defn.get('description', '')}")
        return "\n".join(lines)

    def run(
        self,
        user_input: str,
        context: Optional[AgentContext] = None,
        **kwargs: Any,
    ) -> AgentResult:
        system = _REACT_SYSTEM + "\n" + self._tool_descriptions()
        if context and context.system_prompt:
            system = context.system_prompt + "\n\n" + system
        if context and context.memory_context:
            system += f"\n\n## Relevant Context\n{context.memory_context}"

        messages: list[dict[str, Any]] = []
        if context:
            messages.extend(context.conversation_history)
        messages.append({"role": "user", "content": user_input})

        total_in = 0
        total_out = 0
        total_latency = 0.0
        tool_calls_made: list[str] = []
        turns = 0
        final_text = ""

        while turns < _MAX_TURNS:
            turns += 1

            result = self.engine.generate(
                messages, self.model, config=self.config, system=system
            )
            total_in += result.tokens_in
            total_out += result.tokens_out
            total_latency += result.latency_ms

            text = result.text.strip()
            messages.append({"role": "assistant", "content": text})

            # Check for Final Answer
            if "Final Answer:" in text:
                final_text = text.split("Final Answer:", 1)[-1].strip()
                break

            # Parse Action
            if "Action:" in text:
                action_line = ""
                for line in text.split("\n"):
                    if line.strip().startswith("Action:"):
                        action_line = line.split("Action:", 1)[-1].strip()
                        break

                if action_line:
                    # Parse: tool_name {json_args}
                    parts = action_line.split(None, 1)
                    tool_name = parts[0] if parts else ""
                    tool_args_str = parts[1] if len(parts) > 1 else "{}"
                    tool_calls_made.append(tool_name)

                    import json

                    try:
                        tool_args = json.loads(tool_args_str)
                    except json.JSONDecodeError:
                        tool_args = {"raw_input": tool_args_str}

                    console.print(f"[cyan]Action:[/cyan] {tool_name} {tool_args}")

                    tool = self._tool_map.get(tool_name)
                    if tool is None:
                        observation = f"Error: unknown tool '{tool_name}'"
                    else:
                        try:
                            observation = tool.execute(**tool_args)
                        except Exception as exc:
                            observation = f"Error: {exc}"

                    console.print(f"[dim]Observation: {observation[:200]}...[/dim]")
                    messages.append({
                        "role": "user",
                        "content": f"Observation: {observation}",
                    })
                    continue

            # No action and no final answer — treat as final
            final_text = text
            break

        return AgentResult(
            text=final_text or "[No response generated]",
            tool_calls_made=tool_calls_made,
            tokens_in=total_in,
            tokens_out=total_out,
            latency_ms=total_latency,
            turns=turns,
            model=self.model,
        )
