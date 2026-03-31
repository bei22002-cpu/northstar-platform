"""Token guard — hard limit on total prompt size before API calls.

Uses a fast character-based approximation (1 token ~ 4 characters) to avoid
requiring external tokeniser libraries.  Automatically trims the oldest and
least-useful content when the prompt would exceed the budget.
"""

from __future__ import annotations

from typing import Any

# Conservative approximation: 1 token ≈ 4 characters.
_CHARS_PER_TOKEN = 4

# Default hard limit (tokens).  Claude models support up to 200K context,
# but we target a much smaller window to keep costs low and responses fast.
DEFAULT_MAX_TOKENS = 16_000


class TokenGuard:
    """Enforces a hard token budget on the assembled prompt."""

    def __init__(self, max_tokens: int = DEFAULT_MAX_TOKENS) -> None:
        self._max_tokens = max_tokens

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    # -- public API -----------------------------------------------------------

    def estimate_tokens(self, text: str) -> int:
        """Estimate the token count for a string."""
        return max(1, len(text) // _CHARS_PER_TOKEN)

    def estimate_messages_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Estimate total tokens across a list of messages."""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += self.estimate_tokens(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        for v in block.values():
                            if isinstance(v, str):
                                total += self.estimate_tokens(v)
                    elif isinstance(block, str):
                        total += self.estimate_tokens(block)
            # Per-message overhead (role, formatting)
            total += 4
        return total

    def trim_to_budget(
        self,
        *,
        system_prompt: str,
        state_text: str,
        summary_text: str,
        semantic_text: str,
        messages: list[dict[str, Any]],
        response_reserve: int = 4096,
    ) -> tuple[str, str, str, list[dict[str, Any]]]:
        """Trim context components to fit within the token budget.

        Trimming priority (least important trimmed first):
        1. Semantic memory results
        2. Summary text
        3. Oldest messages from the conversation
        4. State text (last resort — almost never trimmed)

        Parameters
        ----------
        system_prompt:
            The base system prompt (never trimmed).
        state_text:
            Structured state string.
        summary_text:
            Conversation summary string.
        semantic_text:
            Retrieved semantic memories string.
        messages:
            Recent conversation messages.
        response_reserve:
            Tokens reserved for the model's response.

        Returns
        -------
        tuple of (state_text, summary_text, semantic_text, messages)
            Trimmed versions that fit within budget.
        """
        budget = self._max_tokens - response_reserve
        system_cost = self.estimate_tokens(system_prompt)
        budget -= system_cost

        if budget <= 0:
            # System prompt alone exceeds budget — nothing we can do
            return "", "", "", []

        state_cost = self.estimate_tokens(state_text)
        summary_cost = self.estimate_tokens(summary_text)
        semantic_cost = self.estimate_tokens(semantic_text)
        messages_cost = self.estimate_messages_tokens(messages)

        total = state_cost + summary_cost + semantic_cost + messages_cost

        if total <= budget:
            return state_text, summary_text, semantic_text, messages

        # Trim semantic memory first
        if total > budget and semantic_text:
            semantic_text = self._truncate_text(
                semantic_text,
                max(0, budget - state_cost - summary_cost - messages_cost),
            )
            semantic_cost = self.estimate_tokens(semantic_text)
            total = state_cost + summary_cost + semantic_cost + messages_cost

        # Trim summary next
        if total > budget and summary_text:
            summary_text = self._truncate_text(
                summary_text,
                max(0, budget - state_cost - semantic_cost - messages_cost),
            )
            summary_cost = self.estimate_tokens(summary_text)
            total = state_cost + summary_cost + semantic_cost + messages_cost

        # Trim oldest messages
        if total > budget and messages:
            messages = list(messages)  # don't mutate original
            while messages and total > budget:
                removed = messages.pop(0)
                removed_cost = self.estimate_messages_tokens([removed])
                total -= removed_cost
                messages_cost -= removed_cost

        # Last resort — trim state
        if total > budget and state_text:
            state_text = self._truncate_text(
                state_text,
                max(0, budget - summary_cost - semantic_cost - messages_cost),
            )

        return state_text, summary_text, semantic_text, messages

    def is_over_budget(
        self,
        system_prompt: str,
        combined_context: str,
        messages: list[dict[str, Any]],
        response_reserve: int = 4096,
    ) -> bool:
        """Check whether the total prompt exceeds the budget."""
        total = (
            self.estimate_tokens(system_prompt)
            + self.estimate_tokens(combined_context)
            + self.estimate_messages_tokens(messages)
            + response_reserve
        )
        return total > self._max_tokens

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _truncate_text(text: str, max_tokens: int) -> str:
        """Truncate text to fit within *max_tokens*."""
        if max_tokens <= 0:
            return ""
        max_chars = max_tokens * _CHARS_PER_TOKEN
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rsplit(" ", 1)[0] + "..."
