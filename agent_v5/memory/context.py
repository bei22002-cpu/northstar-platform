"""Context injection — retrieve relevant memory and prepend to prompts."""

from __future__ import annotations

from typing import List

from agent_v5.memory.base import MemoryBackend
from agent_v5.types import RetrievalResult


def inject_context(
    query: str,
    memory: MemoryBackend,
    *,
    top_k: int = 5,
    max_chars: int = 3000,
) -> str:
    """Retrieve relevant documents and format them for prompt injection.

    Returns a formatted string suitable for prepending to a system prompt,
    with source attribution.
    """
    if not query.strip():
        return ""

    results = memory.retrieve(query, top_k=top_k)
    if not results:
        return ""

    sections: List[str] = []
    total_chars = 0

    for r in results:
        text = r.content.strip()
        if total_chars + len(text) > max_chars:
            # Truncate to fit budget
            remaining = max_chars - total_chars
            if remaining > 100:
                text = text[:remaining] + "..."
            else:
                break
        source_tag = f" (source: {r.source})" if r.source else ""
        sections.append(f"---\n{text}{source_tag}")
        total_chars += len(text)

    if not sections:
        return ""

    header = "## Retrieved Context\nThe following information was retrieved from memory and may be relevant:\n"
    return header + "\n".join(sections)
