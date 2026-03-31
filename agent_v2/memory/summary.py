"""Summary memory — periodically compress older conversation history.

When the short-term message window grows beyond a threshold, the oldest
messages are summarized into a compact paragraph and the originals are
discarded.  This keeps token usage bounded while preserving key context.

The summary is persisted to disk so it survives across sessions.
"""

from __future__ import annotations

import json
import os
from typing import Any

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "summary.json")

_SUMMARY_PROMPT = """\
You are a conversation summarizer.  Given the messages below, produce a
concise summary that preserves:
- Key decisions and outcomes
- Important facts or preferences mentioned
- The user's current intent or goal
- Any tool actions that were taken and their results

Be brief — aim for 3–6 sentences.  Do not include greetings or filler.

Messages:
{messages}

Summary:"""


class SummaryMemory:
    """Manages a rolling summary of past conversation turns."""

    def __init__(self, path: str | None = None) -> None:
        self._path = os.path.abspath(path or _DEFAULT_PATH)
        self._summary: str = ""
        self._turn_count: int = 0
        self._load()

    # -- public API -----------------------------------------------------------

    @property
    def summary(self) -> str:
        """The current compressed summary."""
        return self._summary

    @property
    def turn_count(self) -> int:
        """Number of turns that have been summarized so far."""
        return self._turn_count

    def to_prompt_string(self) -> str:
        """Render the summary for prompt injection.

        Returns an empty string if no summary exists yet.
        """
        if not self._summary:
            return ""
        return f"Conversation summary so far:\n{self._summary}"

    async def maybe_summarize(
        self,
        messages: list[dict[str, Any]],
        *,
        keep_recent: int = 10,
        llm_call: Any,
    ) -> list[dict[str, Any]]:
        """Summarize older messages if the list exceeds *keep_recent*.

        Parameters
        ----------
        messages:
            The full message history (list of ``{"role": ..., "content": ...}``).
        keep_recent:
            Number of most-recent messages to keep verbatim.
        llm_call:
            Async callable ``(system, user_msg) -> str`` for the LLM.

        Returns
        -------
        list
            The trimmed message list (only the most recent *keep_recent*
            messages).  The older ones have been folded into the summary.
        """
        if len(messages) <= keep_recent:
            return messages

        # Split into "old" (to summarize) and "recent" (to keep)
        old_messages = messages[:-keep_recent]
        recent_messages = messages[-keep_recent:]

        # Format the old messages for the summarizer
        formatted = self._format_messages(old_messages)
        if not formatted.strip():
            return recent_messages

        # Include existing summary for continuity
        if self._summary:
            formatted = (
                f"Previous summary:\n{self._summary}\n\n"
                f"New messages to incorporate:\n{formatted}"
            )

        prompt = _SUMMARY_PROMPT.format(messages=formatted)

        try:
            new_summary = await llm_call(
                "You are a concise conversation summarizer.",
                prompt,
            )
            self._summary = new_summary.strip()
            self._turn_count += len(old_messages)
            self._save()
        except Exception:
            # If summarization fails, just keep recent messages anyway
            pass

        return recent_messages

    def clear(self) -> None:
        """Reset the summary."""
        self._summary = ""
        self._turn_count = 0
        self._save()

    # -- persistence ----------------------------------------------------------

    def _load(self) -> None:
        if os.path.isfile(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    self._summary = data.get("summary", "")
                    self._turn_count = data.get("turn_count", 0)
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(
                {"summary": self._summary, "turn_count": self._turn_count},
                fh,
                indent=2,
                ensure_ascii=False,
            )

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _format_messages(messages: list[dict[str, Any]]) -> str:
        """Convert messages to a readable string for the summarizer."""
        parts: list[str] = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, list):
                # Handle structured content (tool_use, tool_result, etc.)
                text_parts: list[str] = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            text_parts.append(
                                f"[Tool: {block.get('name', '?')}]"
                            )
                        elif block.get("type") == "tool_result":
                            result = block.get("content", "")
                            if isinstance(result, str) and len(result) > 200:
                                result = result[:200] + "..."
                            text_parts.append(f"[Result: {result}]")
                content = " ".join(text_parts)
            if isinstance(content, str) and content.strip():
                parts.append(f"{role}: {content.strip()}")
        return "\n".join(parts)
