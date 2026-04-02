"""Auto-compact — smart conversation compaction with summarization.

Inspired by Claude Code's ``autoCompact.ts``.  Instead of just clearing
history when it gets too large, this module summarizes the old conversation
into a compact context block that preserves key facts, decisions, and
file paths mentioned.

Includes the leaked ``MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3`` safeguard
to stop burning API calls on repeated compaction failures.
"""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console

console = Console()

# After this many consecutive compaction failures, disable for the session
MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3

# Global failure counter (reset on success)
_consecutive_failures: int = 0
_compaction_disabled: bool = False

# Summary of compacted conversation (injected into system prompt)
_compact_summary: str = ""

# Compaction threshold: when message payload exceeds this, compact
COMPACT_THRESHOLD_CHARS = 400_000  # ~100K tokens


def should_compact(messages: list[dict[str, Any]]) -> bool:
    """Return True if the message history is large enough to warrant compaction."""
    if _compaction_disabled:
        return False
    total = len(json.dumps(messages, default=str))
    return total > COMPACT_THRESHOLD_CHARS


def get_compact_summary() -> str:
    """Return the current compaction summary (may be empty)."""
    return _compact_summary


def compact_history(
    messages: list[dict[str, Any]],
    create_message_fn: Any,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 2048,
) -> list[dict[str, Any]]:
    """Summarize old messages and return a trimmed history.

    1. Takes the oldest ~80% of messages and asks Claude to summarize them.
    2. Replaces those messages with a single user message containing the summary.
    3. Keeps the most recent ~20% of messages intact for continuity.

    Uses ``create_message_fn`` (the TokenManager's ``create_message`` method)
    to make the summarization API call.

    Returns the compacted message list.
    """
    global _consecutive_failures, _compaction_disabled, _compact_summary

    if _compaction_disabled:
        console.print(
            "[yellow]Auto-compact disabled after repeated failures. "
            "Falling back to history clear.[/yellow]"
        )
        return _fallback_trim(messages)

    # Split: keep the most recent 20% of messages
    split_point = max(1, int(len(messages) * 0.8))
    old_messages = messages[:split_point]
    recent_messages = messages[split_point:]

    # Build the summarization prompt
    summary_prompt = _build_summary_prompt(old_messages)

    try:
        from agent_v2.hooks import fire_simple
        fire_simple("PreCompact", message_count=len(old_messages))

        response = create_message_fn(
            model=model,
            max_tokens=max_tokens,
            system=(
                "You are a conversation summarizer. Produce a concise summary "
                "of the conversation below. Preserve:\n"
                "- Key decisions and conclusions\n"
                "- File paths and code locations mentioned\n"
                "- Error messages and their resolutions\n"
                "- The user's current goal and context\n"
                "- Any pending tasks or next steps\n\n"
                "Format as a structured summary with bullet points. "
                "Be concise but preserve critical technical details."
            ),
            messages=[{"role": "user", "content": summary_prompt}],
        )

        # Extract the summary text
        summary_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                summary_text += block.text

        if not summary_text.strip():
            raise ValueError("Empty summary returned")

        _compact_summary = summary_text
        _consecutive_failures = 0

        # Build the compacted history
        compacted: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": (
                    "[CONVERSATION SUMMARY — auto-compacted from "
                    f"{len(old_messages)} earlier messages]\n\n"
                    f"{summary_text}\n\n"
                    "[END SUMMARY — conversation continues below]"
                ),
            }
        ]
        compacted.extend(recent_messages)

        console.print(
            f"[green]Auto-compacted {len(old_messages)} messages into summary "
            f"({len(summary_text)} chars). Keeping {len(recent_messages)} recent messages.[/green]"
        )

        fire_simple("PostCompact", summary_length=len(summary_text))
        return compacted

    except Exception as exc:
        _consecutive_failures += 1
        console.print(
            f"[yellow]Auto-compact failed ({_consecutive_failures}/"
            f"{MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES}): {exc}[/yellow]"
        )

        if _consecutive_failures >= MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES:
            _compaction_disabled = True
            console.print(
                "[red]Auto-compact disabled after "
                f"{MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES} consecutive failures. "
                "Will fall back to history clear.[/red]"
            )

        return _fallback_trim(messages)


def _build_summary_prompt(messages: list[dict[str, Any]]) -> str:
    """Convert messages into a readable transcript for the summarizer."""
    lines: list[str] = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if isinstance(content, str):
            lines.append(f"{role.upper()}: {content[:2000]}")
        elif isinstance(content, list):
            # Tool use / tool result blocks
            for block in content:
                if isinstance(block, dict):
                    btype = block.get("type", "")
                    if btype == "text":
                        lines.append(f"{role.upper()}: {block.get('text', '')[:2000]}")
                    elif btype == "tool_use":
                        lines.append(
                            f"{role.upper()} [tool_use]: {block.get('name', '?')}"
                            f"({json.dumps(block.get('input', {}), default=str)[:500]})"
                        )
                    elif btype == "tool_result":
                        result_text = str(block.get("content", ""))[:500]
                        lines.append(f"{role.upper()} [tool_result]: {result_text}")

    return "\n".join(lines)


def _fallback_trim(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Last-resort trim: keep only the last user message."""
    for msg in reversed(messages):
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            return [msg]
    return messages[-1:] if messages else []


def reset_compaction() -> None:
    """Reset compaction state (for new sessions)."""
    global _consecutive_failures, _compaction_disabled, _compact_summary
    _consecutive_failures = 0
    _compaction_disabled = False
    _compact_summary = ""
