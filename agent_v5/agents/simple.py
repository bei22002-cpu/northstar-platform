"""SimpleAgent — single-turn generation, no tools."""

from __future__ import annotations

from typing import Any, Optional

from agent_v5.agents.base import AgentContext, AgentResult, BaseAgent
from agent_v5.registry import AgentRegistry


@AgentRegistry.register("simple")
class SimpleAgent(BaseAgent):
    """Single-turn agent: send messages, get a response.  No tool loop."""

    agent_id = "simple"
    accepts_tools = False

    def run(
        self,
        user_input: str,
        context: Optional[AgentContext] = None,
        **kwargs: Any,
    ) -> AgentResult:
        system, messages = self._build_messages(user_input, context)

        result = self.engine.generate(
            messages,
            self.model,
            config=self.config,
            system=system,
        )

        return AgentResult(
            text=result.text,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            latency_ms=result.latency_ms,
            turns=1,
            model=result.model,
        )
