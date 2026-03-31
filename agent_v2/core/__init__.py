"""Core infrastructure for the Cornerstone AI Agent.

Components:
- ContextBuilder: assembles the final prompt from all memory sources
- TokenGuard: enforces hard token limits on prompt size
"""

from agent_v2.core.context_builder import ContextBuilder
from agent_v2.core.token_guard import TokenGuard

__all__ = [
    "ContextBuilder",
    "TokenGuard",
]
