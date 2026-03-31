"""Document ingestion — read files and directories into memory."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from agent_v5.memory.base import MemoryBackend
from agent_v5.memory.chunking import Chunk, chunk_text

# File extensions we know how to read as plain text
_TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml",
    ".toml", ".cfg", ".ini", ".env", ".sh", ".bash", ".zsh",
    ".md", ".txt", ".rst", ".csv", ".html", ".css", ".scss",
    ".sql", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp",
    ".rb", ".php", ".swift", ".kt", ".scala", ".r", ".R",
    ".xml", ".svg", ".dockerfile", ".gitignore", ".editorconfig",
}

_SKIP_DIRS = {
    "__pycache__", ".git", ".hg", ".svn", "node_modules", ".venv",
    "venv", "env", ".env", ".tox", ".mypy_cache", ".pytest_cache",
    "dist", "build", ".next", ".nuxt", "target", "vendor",
}

_MAX_FILE_SIZE = 1024 * 1024  # 1 MB


def _is_text_file(path: Path) -> bool:
    if path.suffix.lower() in _TEXT_EXTENSIONS:
        return True
    if path.name in ("Makefile", "Dockerfile", "Procfile", "Gemfile", "Rakefile"):
        return True
    return False


def ingest_file(
    path: Path,
    memory: MemoryBackend,
    *,
    chunk_size: int = 512,
    overlap: int = 64,
) -> int:
    """Ingest a single file into memory.  Returns number of chunks stored."""
    path = Path(path)
    if not path.is_file():
        return 0
    if path.stat().st_size > _MAX_FILE_SIZE:
        return 0
    if not _is_text_file(path):
        return 0

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeDecodeError):
        return 0

    if not text.strip():
        return 0

    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap, source=str(path))

    for chunk in chunks:
        memory.store(
            chunk.text,
            source=str(path),
            metadata={"chunk_index": chunk.index, "chunk_total": chunk.total},
        )

    return len(chunks)


def ingest_directory(
    directory: Path,
    memory: MemoryBackend,
    *,
    chunk_size: int = 512,
    overlap: int = 64,
    extensions: Optional[set[str]] = None,
) -> tuple[int, int]:
    """Recursively ingest all text files in *directory*.

    Returns (files_ingested, total_chunks).
    """
    directory = Path(directory)
    if not directory.is_dir():
        return 0, 0

    allowed = extensions or _TEXT_EXTENSIONS
    files_count = 0
    chunks_count = 0

    for path in sorted(directory.rglob("*")):
        # Skip hidden and known-noisy directories
        parts = path.parts
        if any(p in _SKIP_DIRS for p in parts):
            continue
        if any(p.startswith(".") for p in parts if p != "."):
            continue

        if not path.is_file():
            continue
        if path.suffix.lower() not in allowed and not _is_text_file(path):
            continue

        n = ingest_file(path, memory, chunk_size=chunk_size, overlap=overlap)
        if n > 0:
            files_count += 1
            chunks_count += n

    return files_count, chunks_count
