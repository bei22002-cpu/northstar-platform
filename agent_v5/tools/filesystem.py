"""Filesystem tools — read, write, delete, list, search files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from agent_v5.tools.base import BaseTool
from agent_v5.registry import ToolRegistry


@ToolRegistry.register("list_files")
class ListFilesTool(BaseTool):
    tool_id = "list_files"
    description = "List files and directories at a given path."

    def __init__(self, workspace: str = ".") -> None:
        self._workspace = Path(workspace).resolve()

    def execute(self, path: str = ".", **kwargs: Any) -> str:
        target = (self._workspace / path).resolve()
        if not str(target).startswith(str(self._workspace)):
            return "Error: path traversal not allowed"
        if not target.exists():
            return f"Error: {path} does not exist"
        if target.is_file():
            return str(target.relative_to(self._workspace))

        entries: list[str] = []
        try:
            for item in sorted(target.iterdir()):
                rel = item.relative_to(self._workspace)
                prefix = "📁 " if item.is_dir() else "📄 "
                entries.append(f"{prefix}{rel}")
        except PermissionError:
            return "Error: permission denied"

        return "\n".join(entries) if entries else "(empty directory)"

    def to_definition(self) -> Dict[str, Any]:
        return {
            "name": "list_files",
            "description": "List files and directories at a given path in the workspace.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to list (default: root)",
                    }
                },
                "required": [],
            },
        }


@ToolRegistry.register("read_file")
class ReadFileTool(BaseTool):
    tool_id = "read_file"
    description = "Read the contents of a file."

    def __init__(self, workspace: str = ".") -> None:
        self._workspace = Path(workspace).resolve()

    def execute(self, filepath: str = "", **kwargs: Any) -> str:
        if not filepath:
            return "Error: filepath is required"
        target = (self._workspace / filepath).resolve()
        if not str(target).startswith(str(self._workspace)):
            return "Error: path traversal not allowed"
        if not target.exists():
            return f"Error: {filepath} does not exist"
        if not target.is_file():
            return f"Error: {filepath} is not a file"
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            if len(content) > 50000:
                content = content[:50000] + "\n... (truncated)"
            return content
        except Exception as e:
            return f"Error reading file: {e}"

    def to_definition(self) -> Dict[str, Any]:
        return {
            "name": "read_file",
            "description": "Read the contents of a file in the workspace.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Relative path to the file to read.",
                    }
                },
                "required": ["filepath"],
            },
        }


@ToolRegistry.register("write_file")
class WriteFileTool(BaseTool):
    tool_id = "write_file"
    description = "Write content to a file, creating directories as needed."

    def __init__(self, workspace: str = ".") -> None:
        self._workspace = Path(workspace).resolve()

    def execute(self, filepath: str = "", content: str = "", **kwargs: Any) -> str:
        if not filepath:
            return "Error: filepath is required"
        if not content:
            return "Error: content is required"
        target = (self._workspace / filepath).resolve()
        if not str(target).startswith(str(self._workspace)):
            return "Error: path traversal not allowed"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"Written {len(content)} characters to {filepath}"
        except Exception as e:
            return f"Error writing file: {e}"

    def to_definition(self) -> Dict[str, Any]:
        return {
            "name": "write_file",
            "description": "Write content to a file (creates parent directories if needed).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Relative path to the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file.",
                    },
                },
                "required": ["filepath", "content"],
            },
        }


@ToolRegistry.register("delete_file")
class DeleteFileTool(BaseTool):
    tool_id = "delete_file"
    description = "Delete a file from the workspace."

    def __init__(self, workspace: str = ".") -> None:
        self._workspace = Path(workspace).resolve()

    def execute(self, filepath: str = "", **kwargs: Any) -> str:
        if not filepath:
            return "Error: filepath is required"
        target = (self._workspace / filepath).resolve()
        if not str(target).startswith(str(self._workspace)):
            return "Error: path traversal not allowed"
        if not target.exists():
            return f"Error: {filepath} does not exist"
        try:
            target.unlink()
            return f"Deleted {filepath}"
        except Exception as e:
            return f"Error deleting file: {e}"

    def to_definition(self) -> Dict[str, Any]:
        return {
            "name": "delete_file",
            "description": "Delete a file from the workspace.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Relative path to the file to delete.",
                    }
                },
                "required": ["filepath"],
            },
        }


@ToolRegistry.register("search_files")
class SearchFilesTool(BaseTool):
    tool_id = "search_files"
    description = "Search for a pattern in files across the workspace."

    def __init__(self, workspace: str = ".") -> None:
        self._workspace = Path(workspace).resolve()

    def execute(self, pattern: str = "", path: str = ".", **kwargs: Any) -> str:
        if not pattern:
            return "Error: pattern is required"
        target = (self._workspace / path).resolve()
        if not str(target).startswith(str(self._workspace)):
            return "Error: path traversal not allowed"

        matches: list[str] = []
        skip_dirs = {"__pycache__", ".git", "node_modules", ".venv", "venv"}

        for root, dirs, files in os.walk(target):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
            for fname in files:
                fpath = Path(root) / fname
                try:
                    text = fpath.read_text(encoding="utf-8", errors="ignore")
                    for i, line in enumerate(text.splitlines(), 1):
                        if pattern.lower() in line.lower():
                            rel = fpath.relative_to(self._workspace)
                            matches.append(f"{rel}:{i}: {line.strip()}")
                            if len(matches) >= 50:
                                return "\n".join(matches) + "\n... (truncated at 50 matches)"
                except (OSError, UnicodeDecodeError):
                    continue

        return "\n".join(matches) if matches else f"No matches for '{pattern}'"

    def to_definition(self) -> Dict[str, Any]:
        return {
            "name": "search_files",
            "description": "Search for a text pattern across files in the workspace.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text pattern to search for (case-insensitive).",
                    },
                    "path": {
                        "type": "string",
                        "description": "Subdirectory to search in (default: root).",
                    },
                },
                "required": ["pattern"],
            },
        }
