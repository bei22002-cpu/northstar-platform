"""Agentic Logic primitive — pluggable agents."""

from agent_v5.agents.base import BaseAgent, AgentResult
from agent_v5.agents.simple import SimpleAgent
from agent_v5.agents.orchestrator import OrchestratorAgent
from agent_v5.agents.react import ReActAgent

__all__ = ["BaseAgent", "AgentResult", "SimpleAgent", "OrchestratorAgent", "ReActAgent"]
