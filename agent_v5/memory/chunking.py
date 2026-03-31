"""Document chunking — split text into retrieval-friendly pieces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(slots=True)
class Chunk:
    """A single chunk of a document."""

    text: str
    source: str = ""
    index: int = 0
    total: int = 0


def chunk_text(
    text: str,
    *,
    chunk_size: int = 512,
    overlap: int = 64,
    source: str = "",
) -> List[Chunk]:
    """Split *text* into overlapping chunks of roughly *chunk_size* chars.

    Splits on paragraph boundaries when possible, falling back to sentence
    boundaries, then hard character splits.
    """
    if not text.strip():
        return []

    # Try paragraph-level splitting first
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: List[Chunk] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(Chunk(text=current, source=source))
            # If paragraph itself is too long, split it
            if len(para) > chunk_size:
                words = para.split()
                current = ""
                for word in words:
                    if len(current) + len(word) + 1 <= chunk_size:
                        current = f"{current} {word}" if current else word
                    else:
                        if current:
                            chunks.append(Chunk(text=current, source=source))
                        current = word
            else:
                current = para

    if current:
        chunks.append(Chunk(text=current, source=source))

    # Add overlap between chunks
    if overlap > 0 and len(chunks) > 1:
        overlapped: List[Chunk] = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_text = chunks[i - 1].text
            overlap_text = prev_text[-overlap:] if len(prev_text) > overlap else ""
            overlapped.append(
                Chunk(text=f"{overlap_text} {chunks[i].text}".strip(), source=source)
            )
        chunks = overlapped

    # Set index and total
    total = len(chunks)
    for i, c in enumerate(chunks):
        c.index = i
        c.total = total

    return chunks
