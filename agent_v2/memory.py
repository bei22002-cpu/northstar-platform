"""Persistent memory — extract and store facts across sessions.

Inspired by Claude Code's self-healing memory and KAIROS dream distillation.

Maintains a lightweight JSON-based knowledge store that persists across
sessions.  After each conversation turn, key facts are extracted and
stored.  On session start, relevant memories are loaded into context.

Memory types:
- ``fact``     — concrete facts (file locations, API endpoints, etc.)
- ``decision`` — decisions made during the session
- ``error``    — errors encountered and their resolutions
- ``context``  — project context and conventions
- ``user``     — user preferences and patterns
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from rich.console import Console

console = Console()

# Memory store location
_MEMORY_DIR = os.path.join(os.path.dirname(__file__), "data")
_MEMORY_FILE = os.path.join(_MEMORY_DIR, "memory.json")

# Maximum number of memories to keep
MAX_MEMORIES = 500

# Maximum memories to inject into context
MAX_CONTEXT_MEMORIES = 20


class MemoryStore:
    """Persistent key-value memory store backed by JSON."""

    def __init__(self, filepath: str = _MEMORY_FILE) -> None:
        self._filepath = filepath
        self._memories: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """Load memories from disk."""
        if os.path.isfile(self._filepath):
            try:
                with open(self._filepath, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, list):
                    self._memories = data
                    console.print(
                        f"[dim]Loaded {len(self._memories)} memories from disk.[/dim]"
                    )
            except (json.JSONDecodeError, OSError) as exc:
                console.print(f"[yellow]Failed to load memories: {exc}[/yellow]")
                self._memories = []
        else:
            self._memories = []

    def _save(self) -> None:
        """Persist memories to disk."""
        os.makedirs(os.path.dirname(self._filepath), exist_ok=True)
        try:
            with open(self._filepath, "w", encoding="utf-8") as fh:
                json.dump(self._memories, fh, indent=2, default=str)
        except OSError as exc:
            console.print(f"[yellow]Failed to save memories: {exc}[/yellow]")

    @property
    def count(self) -> int:
        return len(self._memories)

    def add(
        self,
        content: str,
        memory_type: str = "fact",
        tags: list[str] | None = None,
        importance: float = 0.5,
    ) -> None:
        """Add a memory entry.

        Parameters
        ----------
        content : str
            The fact, decision, or context to remember.
        memory_type : str
            One of: fact, decision, error, context, user
        tags : list[str]
            Optional tags for retrieval.
        importance : float
            0.0 to 1.0 importance score.
        """
        entry: dict[str, Any] = {
            "content": content,
            "type": memory_type,
            "tags": tags or [],
            "importance": min(1.0, max(0.0, importance)),
            "created_at": time.time(),
            "access_count": 0,
            "last_accessed": None,
        }
        self._memories.append(entry)

        # Prune if over limit (remove lowest importance, oldest first)
        if len(self._memories) > MAX_MEMORIES:
            self._memories.sort(
                key=lambda m: (m.get("importance", 0), m.get("created_at", 0))
            )
            self._memories = self._memories[-MAX_MEMORIES:]

        self._save()

    def search(
        self,
        query: str,
        memory_type: str | None = None,
        limit: int = MAX_CONTEXT_MEMORIES,
    ) -> list[dict[str, Any]]:
        """Search memories by keyword matching.

        Simple but effective: matches against content and tags.
        Returns most relevant memories sorted by relevance score.
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        results: list[tuple[float, dict[str, Any]]] = []

        for mem in self._memories:
            if memory_type and mem.get("type") != memory_type:
                continue

            content_lower = mem.get("content", "").lower()
            tags_lower = [t.lower() for t in mem.get("tags", [])]

            # Score based on word overlap
            score = 0.0
            for word in query_words:
                if word in content_lower:
                    score += 1.0
                for tag in tags_lower:
                    if word in tag:
                        score += 0.5

            # Boost by importance
            score *= (1.0 + mem.get("importance", 0.5))

            # Recency boost (newer = higher)
            age_days = (time.time() - mem.get("created_at", 0)) / 86400
            recency_boost = max(0.1, 1.0 - (age_days / 30))
            score *= recency_boost

            if score > 0:
                results.append((score, mem))

        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)

        # Update access counts
        for _, mem in results[:limit]:
            mem["access_count"] = mem.get("access_count", 0) + 1
            mem["last_accessed"] = time.time()

        if results:
            self._save()

        return [mem for _, mem in results[:limit]]

    def get_all(self, memory_type: str | None = None) -> list[dict[str, Any]]:
        """Return all memories, optionally filtered by type."""
        if memory_type:
            return [m for m in self._memories if m.get("type") == memory_type]
        return list(self._memories)

    def get_context_block(self, query: str = "") -> str:
        """Build a context block from relevant memories for injection into the system prompt.

        If *query* is provided, returns memories relevant to the query.
        Otherwise, returns the most important/recent memories.
        """
        if query:
            relevant = self.search(query, limit=MAX_CONTEXT_MEMORIES)
        else:
            # Get most important + most recent
            by_importance = sorted(
                self._memories,
                key=lambda m: m.get("importance", 0),
                reverse=True,
            )[:MAX_CONTEXT_MEMORIES // 2]

            by_recency = sorted(
                self._memories,
                key=lambda m: m.get("created_at", 0),
                reverse=True,
            )[:MAX_CONTEXT_MEMORIES // 2]

            # Deduplicate
            seen_content: set[str] = set()
            relevant: list[dict[str, Any]] = []
            for mem in by_importance + by_recency:
                content = mem.get("content", "")
                if content not in seen_content:
                    seen_content.add(content)
                    relevant.append(mem)

        if not relevant:
            return ""

        lines: list[str] = ["[PERSISTENT MEMORY — recalled from previous sessions]"]
        for mem in relevant:
            mtype = mem.get("type", "fact")
            content = mem.get("content", "")
            tags = mem.get("tags", [])
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            lines.append(f"- [{mtype}]{tag_str} {content}")
        lines.append("[END MEMORY]")

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all memories."""
        self._memories.clear()
        self._save()
        console.print("[yellow]All memories cleared.[/yellow]")

    def distill(self, create_message_fn: Any, model: str = "claude-sonnet-4-20250514") -> str:
        """Dream distillation — compress and consolidate memories.

        Inspired by KAIROS's ``/dream`` command.  Uses an LLM to merge
        similar memories, remove outdated ones, and create higher-quality
        consolidated entries.

        Returns a status message.
        """
        if len(self._memories) < 10:
            return "Not enough memories to distill (need at least 10)."

        # Build a prompt with all current memories
        memory_text = "\n".join(
            f"- [{m.get('type', 'fact')}] {m.get('content', '')} "
            f"(importance: {m.get('importance', 0.5)}, "
            f"tags: {m.get('tags', [])})"
            for m in self._memories
        )

        try:
            response = create_message_fn(
                model=model,
                max_tokens=4096,
                system=(
                    "You are a memory consolidation system. Given a list of "
                    "memories, consolidate them by:\n"
                    "1. Merging duplicate or very similar memories\n"
                    "2. Removing outdated information that's been superseded\n"
                    "3. Increasing importance of frequently accessed memories\n"
                    "4. Creating concise, high-quality consolidated entries\n\n"
                    "Output a JSON array of consolidated memories, each with:\n"
                    '{"content": "...", "type": "fact|decision|error|context|user", '
                    '"tags": [...], "importance": 0.0-1.0}\n\n'
                    "Be aggressive about consolidation — fewer, higher-quality "
                    "memories are better than many low-quality ones."
                ),
                messages=[{
                    "role": "user",
                    "content": f"Consolidate these {len(self._memories)} memories:\n\n{memory_text}",
                }],
            )

            # Parse the response
            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            # Extract JSON array from response
            json_match = _extract_json_array(response_text)
            if json_match:
                new_memories = json.loads(json_match)
                if isinstance(new_memories, list) and new_memories:
                    old_count = len(self._memories)
                    self._memories.clear()
                    for mem in new_memories:
                        self.add(
                            content=mem.get("content", ""),
                            memory_type=mem.get("type", "fact"),
                            tags=mem.get("tags", []),
                            importance=mem.get("importance", 0.5),
                        )
                    return (
                        f"Distilled {old_count} memories into "
                        f"{len(self._memories)} consolidated entries."
                    )

            return "Distillation produced no usable output."

        except Exception as exc:
            return f"Distillation failed: {exc}"


def _extract_json_array(text: str) -> str | None:
    """Extract a JSON array from text that might contain markdown fences."""
    # Try the whole text first
    text = text.strip()
    if text.startswith("["):
        return text

    # Look for ```json ... ``` blocks
    import re
    match = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text)
    if match:
        return match.group(1)

    # Look for bare array
    match = re.search(r"(\[[\s\S]*\])", text)
    if match:
        return match.group(1)

    return None


def extract_facts_from_turn(
    user_message: str,
    assistant_response: str,
    tool_results: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Extract memorable facts from a conversation turn.

    Uses simple heuristics (no LLM call) to identify facts worth remembering:
    - File paths mentioned
    - Error messages and resolutions
    - Commands that were run
    - Decisions stated by the user
    """
    import re

    facts: list[dict[str, Any]] = []

    # Extract file paths
    file_paths = re.findall(
        r"(?:^|\s)([a-zA-Z0-9_./\\-]+\.(?:py|js|ts|json|yaml|yml|toml|md|txt|html|css|sql))\b",
        user_message + " " + assistant_response,
    )
    for fp in set(file_paths):
        facts.append({
            "content": f"File referenced: {fp}",
            "type": "fact",
            "tags": ["file", os.path.splitext(fp)[1]],
            "importance": 0.3,
        })

    # Extract error patterns
    error_patterns = re.findall(
        r"(?:Error|Exception|Traceback|FAILED|error):\s*(.{20,200})",
        assistant_response,
        re.IGNORECASE,
    )
    for err in error_patterns[:3]:
        facts.append({
            "content": f"Error encountered: {err.strip()}",
            "type": "error",
            "tags": ["error"],
            "importance": 0.7,
        })

    # Extract user decisions (strong intent signals)
    decision_patterns = re.findall(
        r"(?:I want|let's|please|we should|go with|use|switch to|change to)\s+(.{10,150})",
        user_message,
        re.IGNORECASE,
    )
    for dec in decision_patterns[:3]:
        facts.append({
            "content": f"User decision: {dec.strip()}",
            "type": "decision",
            "tags": ["decision", "user-intent"],
            "importance": 0.8,
        })

    return facts


# Module-level singleton
memory_store = MemoryStore()
