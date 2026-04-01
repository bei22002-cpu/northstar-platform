"""RAG — Codebase indexing and semantic search (#1).

On startup, indexes all files in the workspace into a TF-IDF-based
in-memory search index. Supports semantic-style queries like
"find the auth middleware" by matching against file content chunks.

Uses only stdlib + basic text processing (no heavy vector DB needed).
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _Chunk:
    filepath: str
    line_start: int
    text: str
    tokens: list[str] = field(default_factory=list)


class CodebaseIndex:
    """TF-IDF based codebase search index."""

    CHUNK_LINES: int = 30  # lines per chunk
    MAX_FILE_SIZE: int = 100_000  # skip files larger than this
    MAX_RESULTS: int = 10

    # File extensions to index
    INDEXED_EXTENSIONS: set[str] = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml",
        ".toml", ".cfg", ".ini", ".md", ".txt", ".html", ".css",
        ".sql", ".sh", ".bash", ".env.example", ".dockerfile",
        ".rs", ".go", ".java", ".rb", ".php", ".c", ".h", ".cpp",
    }

    SKIP_DIRS: set[str] = {
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        ".mypy_cache", ".pytest_cache", "dist", "build", ".next",
        ".tox", "egg-info",
    }

    def __init__(self) -> None:
        self._chunks: list[_Chunk] = []
        self._doc_freq: Counter[str] = Counter()
        self._indexed: bool = False
        self._file_count: int = 0

    @property
    def is_indexed(self) -> bool:
        return self._indexed

    @property
    def file_count(self) -> int:
        return self._file_count

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    def index_workspace(self, workspace: str) -> dict[str, int]:
        """Index all files in the workspace. Returns stats."""
        self._chunks.clear()
        self._doc_freq.clear()
        self._file_count = 0

        for root, dirs, files in os.walk(workspace):
            # Skip hidden/build dirs
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]

            for fname in sorted(files):
                fpath = os.path.join(root, fname)
                ext = os.path.splitext(fname)[1].lower()

                # Also index extensionless files like Makefile, Dockerfile
                base = fname.lower()
                if ext not in self.INDEXED_EXTENSIONS and base not in (
                    "makefile", "dockerfile", "procfile", "gemfile",
                    "rakefile", "vagrantfile",
                ):
                    continue

                try:
                    size = os.path.getsize(fpath)
                    if size > self.MAX_FILE_SIZE:
                        continue

                    with open(fpath, encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                except OSError:
                    continue

                self._file_count += 1
                relpath = os.path.relpath(fpath, workspace)

                # Split into chunks
                for i in range(0, len(lines), self.CHUNK_LINES):
                    chunk_lines = lines[i:i + self.CHUNK_LINES]
                    text = "".join(chunk_lines)
                    tokens = _tokenize(text)

                    if not tokens:
                        continue

                    chunk = _Chunk(
                        filepath=relpath,
                        line_start=i + 1,
                        text=text,
                        tokens=tokens,
                    )
                    self._chunks.append(chunk)

                    # Update document frequency
                    unique_tokens = set(tokens)
                    for t in unique_tokens:
                        self._doc_freq[t] += 1

        self._indexed = True
        return {
            "files_indexed": self._file_count,
            "chunks_created": len(self._chunks),
        }

    def search(self, query: str, max_results: int | None = None) -> list[dict[str, Any]]:
        """Search the index for chunks matching the query."""
        if not self._indexed or not self._chunks:
            return []

        max_results = max_results or self.MAX_RESULTS
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        n_docs = len(self._chunks)
        scores: list[tuple[float, int]] = []

        for idx, chunk in enumerate(self._chunks):
            score = 0.0
            chunk_counter = Counter(chunk.tokens)
            chunk_len = len(chunk.tokens)

            for qt in query_tokens:
                tf = chunk_counter.get(qt, 0) / max(chunk_len, 1)
                df = self._doc_freq.get(qt, 0)
                if df > 0:
                    idf = math.log(n_docs / df)
                    score += tf * idf

            if score > 0:
                scores.append((score, idx))

        scores.sort(key=lambda x: x[0], reverse=True)

        results: list[dict[str, Any]] = []
        for score, idx in scores[:max_results]:
            chunk = self._chunks[idx]
            # Truncate text for display
            preview = chunk.text[:500]
            if len(chunk.text) > 500:
                preview += "..."
            results.append({
                "filepath": chunk.filepath,
                "line_start": chunk.line_start,
                "score": round(score, 4),
                "preview": preview,
            })

        return results


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens (words, identifiers)."""
    # Split camelCase and snake_case
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = text.replace("_", " ").replace("-", " ")
    tokens = re.findall(r"[a-zA-Z]{2,}", text.lower())
    return tokens
