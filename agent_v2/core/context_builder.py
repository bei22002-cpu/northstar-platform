"""Context builder — assembles the final prompt from all memory sources.

Combines:
  1. System prompt (base instructions)
  2. Structured state (key user attributes)
  3. Summary memory (compressed past conversation)
  4. Semantic memory (relevant retrieved context)
  5. Recent messages (short-term conversational coherence)

The builder delegates to TokenGuard to ensure the assembled prompt never
exceeds the model's context window.
"""

from __future__ import annotations

from typing import Any

from agent_v2.core.token_guard import TokenGuard
from agent_v2.memory.retrieval import MemoryRetriever
from agent_v2.memory.state import StructuredState
from agent_v2.memory.summary import SummaryMemory


class ContextBuilder:
    """Assembles the final prompt with minimal token usage."""

    def __init__(
        self,
        *,
        state: StructuredState,
        summary: SummaryMemory,
        retriever: MemoryRetriever,
        token_guard: TokenGuard,
        system_prompt: str,
    ) -> None:
        self._state = state
        self._summary = summary
        self._retriever = retriever
        self._guard = token_guard
        self._system_prompt = system_prompt

    def build(
        self,
        messages: list[dict[str, Any]],
        current_query: str = "",
    ) -> tuple[str, list[dict[str, Any]]]:
        """Build the system prompt and trimmed messages for an API call.

        Parameters
        ----------
        messages:
            The recent message history.
        current_query:
            The latest user message, used for semantic retrieval.

        Returns
        -------
        tuple of (system_prompt, messages)
            The enriched system prompt (with state, summary, semantic context
            injected) and the trimmed message list.
        """
        # Gather context from all memory sources
        state_text = self._state.to_prompt_string()
        summary_text = self._summary.to_prompt_string()

        # Retrieve semantically relevant past context
        semantic_text = ""
        if current_query:
            semantic_text = self._retriever.retrieve_as_prompt(
                current_query, n_results=5
            )

        # Let the token guard trim to fit budget
        state_text, summary_text, semantic_text, messages = (
            self._guard.trim_to_budget(
                system_prompt=self._system_prompt,
                state_text=state_text,
                summary_text=summary_text,
                semantic_text=semantic_text,
                messages=messages,
            )
        )

        # Assemble the enriched system prompt
        parts: list[str] = [self._system_prompt]
        if state_text:
            parts.append(state_text)
        if summary_text:
            parts.append(summary_text)
        if semantic_text:
            parts.append(semantic_text)

        enriched_system = "\n\n".join(parts)

        return enriched_system, messages

    def get_token_usage(
        self,
        messages: list[dict[str, Any]],
        current_query: str = "",
    ) -> dict[str, int]:
        """Return a breakdown of estimated token usage by component.

        Useful for debugging and the ``memory`` CLI command.
        """
        state_text = self._state.to_prompt_string()
        summary_text = self._summary.to_prompt_string()
        semantic_text = (
            self._retriever.retrieve_as_prompt(current_query, n_results=5)
            if current_query
            else ""
        )

        return {
            "system_prompt": self._guard.estimate_tokens(self._system_prompt),
            "structured_state": self._guard.estimate_tokens(state_text),
            "summary": self._guard.estimate_tokens(summary_text),
            "semantic_memory": self._guard.estimate_tokens(semantic_text),
            "messages": self._guard.estimate_messages_tokens(messages),
            "total": (
                self._guard.estimate_tokens(self._system_prompt)
                + self._guard.estimate_tokens(state_text)
                + self._guard.estimate_tokens(summary_text)
                + self._guard.estimate_tokens(semantic_text)
                + self._guard.estimate_messages_tokens(messages)
            ),
            "budget": self._guard.max_tokens,
        }
